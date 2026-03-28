import asyncio
import json
import os

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from loguru import logger

from agent.api.auth import require_auth
from agent.framework.agent import get_agent
from agent.models import AgentAction, ChatMessage, ChatSession
from agent.utils.streaming import stream_queue

_ARTIFACT_TYPES = {"pdf", "image", "artifact"}


async def _save_message(session_id: str, user_id, role, content: str, artifacts: list = None):
    try:
        session = await ChatSession.objects.aget(id=session_id)
        await ChatMessage.objects.acreate(
            session=session,
            user_id=user_id,
            role=role,
            content=content,
            artifacts=artifacts or [],
        )
    except (ChatSession.DoesNotExist, Exception):
        pass


class _CollectingQueue(asyncio.Queue):
    def __init__(self):
        super().__init__()
        self.artifacts: list = []

    def put_nowait(self, item):
        if isinstance(item, dict) and item.get("type") in _ARTIFACT_TYPES:
            self.artifacts.append(item)
        super().put_nowait(item)

PROVIDER = os.environ.get("AGENT_PROVIDER", "nanobot")
_agent = get_agent(PROVIDER)
get_agent_loop = _agent.get_agent_loop
_task_queues = _agent._task_queues
_user_role = _agent._user_role
_user_id = _agent._user_id


@csrf_exempt
@require_POST
async def chat(request):
    user_id, role, err = await require_auth(request)
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
    queue = _CollectingQueue()

    await _save_message(session_key, user_id, ChatMessage.Role.USER, message)

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
            await _save_message(session_key, user_id, ChatMessage.Role.ASSISTANT, response, queue.artifacts)
            await queue.put({"type": "response", "content": response})
        except Exception as e:
            logger.error(f"[agent] error: {e}")
            await queue.put({"type": "response", "content": f"Error: {e}"})
        finally:
            await queue.put(None)

    async def _on_confirmation(event):
        if event.get("type") != "confirmation":
            return None
        return f"data: {json.dumps({'type': 'confirmation', 'action_id': event['action_id'], 'summary': event['summary'], 'details': event.get('details', {})})}\n\n"

    task = asyncio.create_task(run_agent())
    _task_queues[id(task)] = queue
    task.add_done_callback(lambda t: _task_queues.pop(id(t), None))
    return StreamingHttpResponse(stream_queue(queue, task, on_event=_on_confirmation), content_type="text/event-stream")


@csrf_exempt
@require_POST
async def confirm_action(request, action_id):
    user_id, role, err = await require_auth(request)
    if err:
        return err

    try:
        action = await AgentAction.objects.aget(id=action_id)
    except AgentAction.DoesNotExist:
        return JsonResponse({"error": "Action not found"}, status=404)

    if action.status == AgentAction.Status.APPROVED:
        return JsonResponse({"error": "already_processing"}, status=409)
    if action.status not in (AgentAction.Status.PENDING,):
        return JsonResponse({"error": "Action already resolved"}, status=409)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    session_key = body.get("session_key", "")

    _user_role.set(role)
    _user_id.set(user_id)
    queue = asyncio.Queue()

    async def run_confirmed():
        _task_queues[id(asyncio.current_task())] = queue
        new_action = None
        try:
            agent_loop = get_agent_loop()
            dispatch = agent_loop.tools._tools.get("dispatch")
            pending_summary = action.output.get("pending_summary", action.intent)
            confirmed_task = pending_summary + "\nUser has confirmed. Proceed with the write operation. CONFIRMED."
            await AgentAction.objects.filter(id=action_id).aupdate(
                status=AgentAction.Status.APPROVED,
                approved_by_id=_user_id.get(),
            )
            result = await dispatch.execute(agent_name=action.agent_name, task=confirmed_task)
            # store result in approved action for stream-drop recovery
            try:
                new_action = await AgentAction.objects.filter(
                    agent_name=action.agent_name,
                    status=AgentAction.Status.SUCCESS,
                    intent=confirmed_task[:500],
                ).order_by("-timestamp").afirst()
                current_output = action.output.copy()
                current_output["result_summary"] = result
                await AgentAction.objects.filter(id=action_id).aupdate(
                    output=current_output,
                    artifacts=new_action.artifacts if new_action else [],
                )
            except Exception:
                pass
            if session_key:
                await _save_message(session_key, _user_id.get(), ChatMessage.Role.ASSISTANT, result, new_action.artifacts if new_action else [])
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
    user_id, _, err = await require_auth(request)
    if err:
        return err
    updated = await AgentAction.objects.filter(
        id=action_id, status=AgentAction.Status.PENDING
    ).aupdate(status=AgentAction.Status.FAILED, output={"result": "Cancelled by user"})
    if not updated:
        return JsonResponse({"error": "Action not found or already resolved"}, status=404)
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    session_key = body.get("session_key", "")
    if session_key:
        await _save_message(session_key, user_id, ChatMessage.Role.ASSISTANT, "Action cancelled.")
    return JsonResponse({"status": "cancelled"})


async def pending_actions(request):
    _, _, err = await require_auth(request)
    if err:
        return err
    rows = AgentAction.objects.filter(status=AgentAction.Status.PENDING).order_by("timestamp").values(
        "id", "intent", "agent_name", "timestamp", "output"
    )
    results = [
        {
            "action_id": str(r["id"]),
            "summary": r["output"].get("pending_summary", r["intent"]),
            "details": r["output"].get("details", {}),
            "agent_name": r["agent_name"],
            "timestamp": r["timestamp"].isoformat(),
        }
        async for r in rows
    ]
    return JsonResponse(results, safe=False)


async def action_status(request, action_id):
    _, _, err = await require_auth(request)
    if err:
        return err
    try:
        action = await AgentAction.objects.aget(id=action_id)
    except AgentAction.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({
        "status": action.status,
        "output": action.output,
        "artifacts": action.artifacts,
    })


# session_messages moved to agent/api/sessions.py
