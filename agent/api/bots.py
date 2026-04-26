import asyncio
import json

from django.http import JsonResponse
# from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from agent.api.auth import require_auth
from agent.models import BotInstance, ChatSession, ChatMessage
from agent.bots.tunnel import start_tunnel, stop_tunnel, get_tunnel

_running_bots: dict[str, asyncio.Task] = {}
# _bot_progress_queues: dict[str, asyncio.Queue] = {}


def _bot_runner(platform: str):
    if platform == BotInstance.Platform.DISCORD:
        from agent.bots.discord.main import run
    elif platform == BotInstance.Platform.TELEGRAM:
        from agent.bots.telegram.main import run
    elif platform == BotInstance.Platform.WHATSAPP:
        return None
    elif platform == BotInstance.Platform.SLACK:
        from agent.bots.slack.main import run
    else:
        raise ValueError(f"Unknown platform: {platform}")
    return run


async def _start(bot: BotInstance):
    bot_id = str(bot.id)
    if bot_id in _running_bots:
        return
    run = _bot_runner(bot.platform)
    if run is None:
        start_tunnel(bot_id, f"/api/agent/bots/whatsapp/webhook/{bot_id}/")
        return
    # progress_queue = asyncio.Queue()
    # _bot_progress_queues[bot_id] = progress_queue
    # task = asyncio.create_task(run(bot.token, bot_id, bot.role, progress_queue))
    task = asyncio.create_task(run(bot.token, bot_id, bot.role))
    _running_bots[bot_id] = task
    # task.add_done_callback(lambda t: (_running_bots.pop(bot_id, None), _bot_progress_queues.pop(bot_id, None)))
    task.add_done_callback(lambda t: _running_bots.pop(bot_id, None))


async def _stop(bot_id: str):
    task = _running_bots.pop(bot_id, None)
    if task:
        task.cancel()
    stop_tunnel(bot_id)


async def list_bots(request):
    _, _, err = await require_auth(request)
    if err:
        return err
    rows = BotInstance.objects.order_by("created_at").values("id", "name", "platform", "role", "is_active")
    results = [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "platform": r["platform"],
            "role": r["role"],
            "is_active": r["is_active"],
            "running": str(r["id"]) in _running_bots or (r["platform"] == BotInstance.Platform.WHATSAPP and r["is_active"]),
            "webhook_url": get_tunnel(str(r["id"])),
        }
        async for r in rows
    ]
    return JsonResponse(results, safe=False)


@csrf_exempt
async def create_bot(request):
    user_id, _, err = await require_auth(request)
    if err:
        return err
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = body.get("name", "").strip()
    platform = body.get("platform", "").strip()
    token = body.get("token", "").strip()
    role = body.get("role", BotInstance.Role.VIEWER).strip()

    if not name or not platform or not token:
        return JsonResponse({"error": "name, platform, and token are required"}, status=400)
    if platform not in BotInstance.Platform.values:
        return JsonResponse({"error": f"Invalid platform. Choose from: {BotInstance.Platform.values}"}, status=400)
    if role not in BotInstance.Role.values:
        return JsonResponse({"error": f"Invalid role. Choose from: {BotInstance.Role.values}"}, status=400)

    bot = await BotInstance.objects.acreate(
        name=name,
        platform=platform,
        token=token,
        role=role,
        is_active=False,
        created_by_id=user_id,
    )
    return JsonResponse({"id": str(bot.id), "name": bot.name, "platform": bot.platform, "role": bot.role, "is_active": bot.is_active, "running": False})


@csrf_exempt
async def update_bot(request, bot_id):
    _, _, err = await require_auth(request)
    if err:
        return err

    try:
        bot = await BotInstance.objects.aget(id=bot_id)
    except BotInstance.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        await _stop(str(bot_id))
        await BotInstance.objects.filter(id=bot_id).adelete()
        return JsonResponse({"status": "deleted"})

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    updated = {}
    if "name" in body:
        updated["name"] = body["name"]
    if "token" in body:
        updated["token"] = body["token"]
    if "role" in body and body["role"] in BotInstance.Role.values:
        updated["role"] = body["role"]

    if "is_active" in body:
        new_active = bool(body["is_active"])
        updated["is_active"] = new_active
        if new_active:
            bot.token = body.get("token", bot.token)
            await _start(bot)
        else:
            await _stop(str(bot_id))

    if updated:
        await BotInstance.objects.filter(id=bot_id).aupdate(**updated)

    return JsonResponse({"status": "ok", "running": str(bot_id) in _running_bots})


async def list_bot_sessions(request, bot_id):
    _, _, err = await require_auth(request)
    if err:
        return err
    try:
        await BotInstance.objects.aget(id=bot_id)
    except BotInstance.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    rows = ChatSession.objects.filter(bot_id=bot_id).order_by("-updated_at").values(
        "id", "label", "updated_at"
    )
    results = [
        {"id": str(r["id"]), "label": r["label"], "updated_at": r["updated_at"].isoformat()}
        async for r in rows
    ]
    return JsonResponse(results, safe=False)


@csrf_exempt
async def bot_chat(request, bot_id, session_id):
    _, _, err = await require_auth(request)
    if err:
        return err
    try:
        bot = await BotInstance.objects.aget(id=bot_id)
        session = await ChatSession.objects.aget(id=session_id, bot_id=bot_id)
    except (BotInstance.DoesNotExist, ChatSession.DoesNotExist):
        return JsonResponse({"error": "Not found"}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    content = body.get("content", "").strip()
    if not content:
        return JsonResponse({"error": "content is required"}, status=400)

    await ChatMessage.objects.acreate(
        session=session, user=None, role=ChatMessage.Role.USER, content=content, artifacts=[],
    )

    from agent.framework.agent import get_agent
    _agent = get_agent("nanobot")
    # _agent._user_role.set(bot.role)
    # _agent._user_id.set(None)
    _agent.set_context(user_role=bot.role, user_id=None)

    agent_loop = _agent.get_agent_loop()
    try:
        response = await agent_loop.process_direct(content=content, session_key=str(session.id))
    except Exception as e:
        response = f"Error: {e}"

    await ChatMessage.objects.acreate(
        session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response, artifacts=[],
    )

    return JsonResponse({"response": response})


# async def bot_progress(request, bot_id):
#     _, _, err = await require_auth(request)
#     if err:
#         return err
#
#     async def _stream():
#         while True:
#             queue = _bot_progress_queues.get(str(bot_id))
#             if not queue:
#                 yield "data: [KEEPALIVE]\n\n"
#                 await asyncio.sleep(2)
#                 continue
#             try:
#                 event = await asyncio.wait_for(queue.get(), timeout=30)
#                 if event is None:
#                     yield "data: [DONE]\n\n"
#                     continue
#                 yield f"data: {json.dumps(event)}\n\n"
#             except asyncio.TimeoutError:
#                 yield "data: [KEEPALIVE]\n\n"
#
#     return StreamingHttpResponse(_stream(), content_type="text/event-stream")
