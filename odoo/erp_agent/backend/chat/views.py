import asyncio
import json
import os
import uuid

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from loguru import logger

# from backend.agent_loop import get_agent_loop, set_context, _task_queues
from backend.agent_loop import get_agent_loop, set_context, _task_queues, _accepting
from backend.utils.streaming import stream_queue
from backend.utils.queue import CollectingQueue

API_KEY = os.environ.get("AGENT_API_KEY", "")


def _check_key(request):
    if not API_KEY:
        return None
    if request.headers.get("X-API-Key", "") != API_KEY:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    return None


@csrf_exempt
@require_POST
async def chat(request):
    err = _check_key(request)
    if err:
        return err

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = body.get("message", "").strip()
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    # session_key is the conversation key (odoo:conv:<id>) — drives nanobot's
    # per-conversation working memory. Persistence lives in Odoo, not here.
    session_key = body.get("session_key", "odoo:default")
    profile_id = body.get("profile_id")
    uid = body.get("uid")
    user_id = str(uid) if uid is not None else None
    set_context(user_role="admin", user_id=user_id, run_id=str(uuid.uuid4()), source="odoo", profile_id=profile_id)

    queue = CollectingQueue()

    async def on_progress(content, **_):
        await queue.put({"type": "progress", "content": content})

    async def run_agent():
        try:
            agent_loop = get_agent_loop()
            response = await agent_loop.process_direct(
                content=message,
                session_key=session_key,
                on_progress=on_progress,
            )
            await queue.put({"type": "response", "content": response})
        except Exception as e:
            logger.error(f"[agent] {e}")
            await queue.put({"type": "response", "content": f"Error: {e}"})
        finally:
            await queue.put(None)

    await _accepting.wait()   # blocks new runs while a rebuild is draining
    task = asyncio.create_task(run_agent())
    _task_queues[id(task)] = queue
    task.add_done_callback(lambda t: _task_queues.pop(id(t), None))
    return StreamingHttpResponse(stream_queue(queue, task), content_type="text/event-stream")


@csrf_exempt
async def health(request):
    try:
        get_agent_loop()
        return JsonResponse({"status": "ok", "agent": "ready"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
