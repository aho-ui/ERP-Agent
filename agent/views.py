import asyncio
import json
import os
import urllib.request
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from agent.framework.nanobot import get_agent_loop, _task_queues
from agent.models import AgentAction
from agent.utils.streaming import stream_queue
from MCP.config import SERVERS


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

    queue = asyncio.Queue()

    async def run_confirmed():
        _task_queues[id(asyncio.current_task())] = queue
        try:
            agent_loop = get_agent_loop()
            dispatch = agent_loop.tools._tools.get("dispatch")
            confirmed_task = action.intent + "\nUser has confirmed. Proceed with the write operation. CONFIRMED."
            result = await dispatch.execute(agent_name=action.agent_name, task=confirmed_task)
            await AgentAction.objects.filter(id=action_id).aupdate(
                status=AgentAction.Status.SUCCESS,
                output={"result": result},
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
