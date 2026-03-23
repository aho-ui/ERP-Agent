import asyncio
import json
import os
import urllib.request
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.tokens import AccessToken as JWTToken
from rest_framework_simplejwt.exceptions import TokenError

from agent.framework.agent import get_agent
from agent.framework.nanobot import _user_role, _user_id

PROVIDER = "openai"  # groq || openai
_agent = get_agent(PROVIDER)
get_agent_loop = _agent.get_agent_loop
_task_queues = _agent._task_queues
from agent.models import AgentAction, AgentTemplate
from agent.utils.streaming import stream_queue
from MCP.config import SERVERS


def _parse_token(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, "viewer"
    try:
        token = JWTToken(auth[7:])
        return token.get("user_id"), token.get("role", "viewer")
    except TokenError:
        return None, "viewer"


def _require_auth(request, admin_only=False):
    user_id, role = _parse_token(request)
    if not user_id:
        return None, None, JsonResponse({"error": "Unauthorized"}, status=401)
    if admin_only and role != "admin":
        return None, None, JsonResponse({"error": "Forbidden"}, status=403)
    return user_id, role, None


async def _on_confirmation(event):
    if event.get("type") != "confirmation":
        return None
    return f"data: {json.dumps({'type': 'confirmation', 'action_id': event['action_id'], 'summary': event['summary']})}\n\n"


@csrf_exempt
@require_POST
async def chat(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = body.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    session_key = body.get("session_key", "api:default")
    user_id, role = _parse_token(request)
    _user_role.set(role)
    _user_id.set(user_id)
    queue = asyncio.Queue()

    async def on_progress(content):
        await queue.put({"type": "progress", "content": content})

    async def run_agent():
        agent_loop = get_agent_loop()
        response = await agent_loop.process_direct(
            content=message,
            session_key=session_key,
            on_progress=on_progress,
        )
        await queue.put({"type": "response", "content": response})
        await queue.put(None)

    task = asyncio.create_task(run_agent())
    _task_queues[id(task)] = queue
    task.add_done_callback(lambda t: _task_queues.pop(id(t), None))
    return StreamingHttpResponse(stream_queue(queue, task, on_event=_on_confirmation), content_type="text/event-stream")


@csrf_exempt
@require_POST
async def confirm_action(_request, action_id):
    try:
        action = await AgentAction.objects.aget(id=action_id, status=AgentAction.Status.PENDING)
    except AgentAction.DoesNotExist:
        return JsonResponse({"error": "Action not found or already resolved"}, status=404)

    user_id, role = _parse_token(_request)
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
    _, _, err = _require_auth(_request)
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
    _, _, err = _require_auth(request, admin_only=True)
    if err:
        return err
    qs = AgentAction.objects.order_by("-timestamp")

    rows = qs.values(
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
    from agent.framework.agents import AGENTS

    if request.method == "GET":
        _, _, err = _require_auth(request)
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
        user_id, _, err = _require_auth(request, admin_only=True)
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
    try:
        template = await AgentTemplate.objects.aget(id=template_id)
    except AgentTemplate.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "PUT":
        _, _, err = _require_auth(request, admin_only=True)
        if err:
            return err
        body = json.loads(request.body)
        template.name = body.get("name", template.name)
        template.type = body.get("type", template.type)
        template.instructions = body.get("instructions", template.instructions)
        template.allowed_tools = body.get("allowed_tools", template.allowed_tools)
        await template.asave()
        return JsonResponse({"id": str(template.id), "name": template.name})

    if request.method == "DELETE":
        _, _, err = _require_auth(request, admin_only=True)
        if err:
            return err
        await template.adelete()
        return JsonResponse({"status": "deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


async def available_tools(_request):
    _, _, err = _require_auth(_request)
    if err:
        return err
    from agent.framework.agents import AGENTS
    tools: set[str] = set()
    for a in AGENTS:
        tools.update(a["allowed_tools"])
    return JsonResponse(sorted(tools), safe=False)


@csrf_exempt
@require_POST
async def export_csv(request):
    _, _, err = _require_auth(request)
    if err:
        return err
    from agent.utils.csv_export import generate_csv_bytes
    body = json.loads(request.body)
    data = generate_csv_bytes(body["columns"], body["rows"])
    from django.http import HttpResponse
    response = HttpResponse(data, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{body.get("title", "export")}.csv"'
    return response


@csrf_exempt
@require_POST
async def export_pdf(request):
    _, _, err = _require_auth(request)
    if err:
        return err
    from agent.utils.pdf import generate_pdf_bytes
    body = json.loads(request.body)
    data = generate_pdf_bytes(body["columns"], body["rows"], title=body.get("title", ""))
    from django.http import HttpResponse
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{body.get("title", "export")}.pdf"'
    return response


async def mcp_health(_request):
    results = []
    loop = asyncio.get_event_loop()
    for name, cfg in SERVERS.items():
        if cfg.get("url"):
            transport = "http"
            try:
                await loop.run_in_executor(None, lambda: urllib.request.urlopen(cfg["url"], timeout=3))
                status = "ok"
            except Exception:
                status = "error"
        else:
            transport = "stdio"
            args = cfg.get("args", [])
            path = args[0] if args else ""
            status = "ok" if os.path.exists(path) else "error"
        results.append({"name": name, "transport": transport, "status": status})
    return JsonResponse(results, safe=False)
