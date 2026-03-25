import asyncio
import json
import os
from loguru import logger
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.tokens import AccessToken as JWTToken
from rest_framework_simplejwt.exceptions import TokenError

from agent.framework.agent import get_agent

# PROVIDER = os.environ.get("AGENT_PROVIDER", "openai")
PROVIDER = os.environ.get("AGENT_PROVIDER", "nanobot")
_agent = get_agent(PROVIDER)
get_agent_loop = _agent.get_agent_loop
_task_queues = _agent._task_queues
_user_role = _agent._user_role
_user_id = _agent._user_id
from agent.models import AgentAction, AgentTemplate
from agent.utils.streaming import stream_queue


def _parse_token(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, "viewer"
    try:
        token = JWTToken(auth[7:])
        return token.get("user_id"), token.get("role", "viewer")
    except TokenError:
        return None, "viewer"


async def _parse_api_key(request):
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return None, None
    from asgiref.sync import sync_to_async
    from django.utils import timezone
    from users.models import User
    try:
        user = await sync_to_async(User.objects.get)(api_key=api_key, is_active=True)
        if user.api_key_expires_at and user.api_key_expires_at < timezone.now():
            return None, None
        return str(user.id), user.role
    except Exception:
        return None, None


async def _require_auth(request, admin_only=False):
    user_id, role = _parse_token(request)
    if not user_id:
        user_id, role = await _parse_api_key(request)
    if not user_id:
        return None, None, JsonResponse({"error": "Unauthorized"}, status=401)
    if admin_only and role != "admin":
        return None, None, JsonResponse({"error": "Forbidden"}, status=403)
    return user_id, role, None


@csrf_exempt
@require_POST
async def chat(request):
    user_id, role, err = await _require_auth(request)
    if err:
        return err

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = body.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    session_key = body.get("session_key", "api:default")
    _user_role.set(role)
    _user_id.set(user_id)
    queue = asyncio.Queue()

    async def on_progress(content, **_):
        await queue.put({"type": "progress", "content": content})

    async def run_agent():
        agent_loop = get_agent_loop()
        try:
            response = await agent_loop.process_direct(
                content=message,
                session_key=session_key,
                on_progress=on_progress,
            )
            await queue.put({"type": "response", "content": response})
        except Exception as e:
            logger.error(f"[agent] error: {e}")
            await queue.put({"type": "response", "content": f"Error: {e}"})
        finally:
            await queue.put(None)

    async def _on_confirmation(event):
        if event.get("type") != "confirmation":
            return None
        return f"data: {json.dumps({'type': 'confirmation', 'action_id': event['action_id'], 'summary': event['summary']})}\n\n"

    task = asyncio.create_task(run_agent())
    _task_queues[id(task)] = queue
    task.add_done_callback(lambda t: _task_queues.pop(id(t), None))
    return StreamingHttpResponse(stream_queue(queue, task, on_event=_on_confirmation), content_type="text/event-stream")


@csrf_exempt
@require_POST
async def confirm_action(request, action_id):
    user_id, role, err = await _require_auth(request)
    if err:
        return err

    try:
        action = await AgentAction.objects.aget(id=action_id, status=AgentAction.Status.PENDING)
    except AgentAction.DoesNotExist:
        return JsonResponse({"error": "Action not found or already resolved"}, status=404)

    _user_role.set(role)
    _user_id.set(user_id)
    queue = asyncio.Queue()

    async def run_confirmed():
        _task_queues[id(asyncio.current_task())] = queue
        try:
            agent_loop = get_agent_loop()
            dispatch = agent_loop.tools._tools.get("dispatch")
            pending_summary = action.output.get("pending_summary", action.intent)
            confirmed_task = pending_summary + "\nUser has confirmed. Proceed with the write operation. CONFIRMED."
            result = await dispatch.execute(agent_name=action.agent_name, task=confirmed_task)
            await AgentAction.objects.filter(id=action_id).aupdate(
                status=AgentAction.Status.SUCCESS,
                output={"result": result},
                approved_by_id=_user_id.get(),
            )
            await queue.put({"type": "response", "content": result})
        except Exception as e:
            await AgentAction.objects.filter(id=action_id).aupdate(
                status=AgentAction.Status.FAILED,
                output={"error": str(e)},
            )
            await queue.put({"type": "response", "content": f"Action failed: {e}"})
        finally:
            _task_queues.pop(id(asyncio.current_task()), None)
            await queue.put(None)

    task = asyncio.create_task(run_confirmed())
    task.add_done_callback(lambda t: _task_queues.pop(id(t), None))
    return StreamingHttpResponse(stream_queue(queue, task), content_type="text/event-stream")


@csrf_exempt
@require_POST
async def cancel_action(request, action_id):
    updated = await AgentAction.objects.filter(
        id=action_id, status=AgentAction.Status.PENDING
    ).aupdate(status=AgentAction.Status.FAILED, output={"result": "Cancelled by user"})
    if not updated:
        return JsonResponse({"error": "Action not found or already resolved"}, status=404)
    return JsonResponse({"status": "cancelled"})


async def pending_actions(_request):
    _, _, err = await _require_auth(_request)
    if err:
        return err
    rows = AgentAction.objects.filter(status=AgentAction.Status.PENDING).order_by("timestamp").values(
        "id", "intent", "agent_name", "timestamp"
    )
    results = [
        {
            "action_id": str(r["id"]),
            "summary": r["intent"],
            "agent_name": r["agent_name"],
            "timestamp": r["timestamp"].isoformat(),
        }
        async for r in rows
    ]
    return JsonResponse(results, safe=False)


async def agent_logs(request):
    _, _, err = await _require_auth(request, admin_only=True)
    if err:
        return err
    rows = AgentAction.objects.order_by("-timestamp").values(
        "id", "intent", "agent_name", "tool_called", "status", "timestamp", "output", "artifacts"
    )
    results = [
        {
            "id": str(r["id"]),
            "intent": r["intent"],
            "agent_name": r["agent_name"],
            "tool_called": r["tool_called"],
            "status": r["status"],
            "timestamp": r["timestamp"].isoformat(),
            "output": r["output"],
            "artifacts": r["artifacts"],
        }
        async for r in rows
    ]
    return JsonResponse(results, safe=False)


@csrf_exempt
async def agent_templates(request):
    from agent.framework.nanobot.agents.sub_agents_odoo import AGENTS as _ODOO_AGENTS
    from agent.framework.nanobot.agents.sub_agents_demo import AGENTS as _DEMO_AGENTS
    AGENTS = _ODOO_AGENTS + _DEMO_AGENTS

    if request.method == "GET":
        _, _, err = await _require_auth(request)
        if err:
            return err
        db_names = set()
        results = []
        async for r in AgentTemplate.objects.filter(is_active=True).order_by("created_at").values("id", "name", "type", "instructions", "allowed_tools", "created_at"):
            db_names.add(r["name"])
            results.append({"id": str(r["id"]), "name": r["name"], "type": r["type"], "instructions": r["instructions"], "allowed_tools": r["allowed_tools"], "created_at": r["created_at"].isoformat(), "builtin": False})
        for a in AGENTS:
            if a["name"] not in db_names:
                results.append({"id": None, "name": a["name"], "type": "builtin", "description": a.get("description", ""), "system_prompt": a.get("system_prompt", ""), "allowed_tools": a["allowed_tools"], "builtin": True})
        return JsonResponse(results, safe=False)

    if request.method == "POST":
        user_id, _, err = await _require_auth(request, admin_only=True)
        if err:
            return err
        body = json.loads(request.body)
        template = await AgentTemplate.objects.acreate(
            name=body["name"],
            type=body["type"],
            instructions=body["instructions"],
            allowed_tools=body.get("allowed_tools", []),
            created_by_id=user_id,
        )
        return JsonResponse({"id": str(template.id), "name": template.name}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def agent_template_detail(request, template_id):
    _, _, err = await _require_auth(request, admin_only=True)
    if err:
        return err

    try:
        template = await AgentTemplate.objects.aget(id=template_id)
    except AgentTemplate.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "PUT":
        body = json.loads(request.body)
        template.name = body.get("name", template.name)
        template.type = body.get("type", template.type)
        template.instructions = body.get("instructions", template.instructions)
        template.allowed_tools = body.get("allowed_tools", template.allowed_tools)
        await template.asave()
        return JsonResponse({"id": str(template.id), "name": template.name})

    if request.method == "DELETE":
        await template.adelete()
        return JsonResponse({"status": "deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


async def available_tools(_request):
    _, _, err = await _require_auth(_request)
    if err:
        return err
    from agent.framework.nanobot.agents.sub_agents_odoo import AGENTS as _ODOO_AGENTS
    from agent.framework.nanobot.agents.sub_agents_demo import AGENTS as _DEMO_AGENTS
    AGENTS = _ODOO_AGENTS + _DEMO_AGENTS
    tools: set[str] = set()
    for a in AGENTS:
        tools.update(a["allowed_tools"])
    return JsonResponse(sorted(tools), safe=False)


@csrf_exempt
@require_POST
async def export(request):
    _, _, err = await _require_auth(request)
    if err:
        return err
    body = json.loads(request.body)
    fmt = body.get("format", "csv")
    title = body.get("title", "export")

    if fmt == "pdf":
        from agent.utils.pdf import generate_pdf_bytes
        data = generate_pdf_bytes(body["columns"], body["rows"], title=title)
        content_type = "application/pdf"
    elif fmt == "xlsx":
        from agent.utils.xlsx_export import generate_xlsx_bytes
        data = generate_xlsx_bytes(body["columns"], body["rows"])
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        from agent.utils.csv_export import generate_csv_bytes
        data = generate_csv_bytes(body["columns"], body["rows"])
        content_type = "text/csv"

    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{title}.{fmt}"'
    return response


async def mcp_health(_request):
    from MCP.utils.health import check_all
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, check_all)
    return JsonResponse(
        [{"name": name, "status": "ok" if ok else "error"} for name, ok in results.items()],
        safe=False,
    )
