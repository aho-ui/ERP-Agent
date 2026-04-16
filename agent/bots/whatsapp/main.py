import asyncio
import base64
import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from loguru import logger
from twilio.rest import Client

from agent.framework.agent import get_agent
from agent.utils.queue import CollectingQueue
from asgiref.sync import sync_to_async
from agent.bots.media import store as _media_store

media_store = sync_to_async(_media_store)
from agent.bots.tunnel import get_tunnel_base

_agent = get_agent("nanobot")


@csrf_exempt
async def webhook(request, bot_id):
    from agent.models import BotInstance, ChatSession, ChatMessage

    try:
        bot = await BotInstance.objects.aget(id=bot_id)
    except BotInstance.DoesNotExist:
        return HttpResponse(status=404)

    body = request.POST.get("Body", "").strip()
    sender = request.POST.get("From", "").strip()

    if not body or not sender:
        return HttpResponse("<Response></Response>", content_type="text/xml")

    creds = json.loads(bot.token)
    account_sid = creds["account_sid"]
    auth_token = creds["auth_token"]
    from_number = creds["from"]
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"
    if not sender.startswith("whatsapp:"):
        sender = f"whatsapp:{sender}"

    session_label = f"whatsapp:{sender}"
    session, _ = await ChatSession.objects.aget_or_create(
        bot_id=bot_id,
        label=session_label,
    )

    await ChatMessage.objects.acreate(
        session=session, user=None, role=ChatMessage.Role.USER, content=body, artifacts=[],
    )

    _agent._user_role.set(bot.role)
    _agent._user_id.set(None)
    _agent._source.set("whatsapp")
    _agent._bot_id.set(str(bot_id))

    agent_loop = _agent.get_agent_loop()

    async def process_and_reply():
        queue = CollectingQueue()
        current_task = asyncio.current_task()
        if current_task:
            _agent._task_queues[id(current_task)] = queue

        try:
            response = await agent_loop.process_direct(content=body, session_key=str(session.id))
        except Exception as e:
            logger.error(f"[whatsapp bot] agent error: {e}")
            response = "An error occurred. Please try again."
        finally:
            if current_task:
                _agent._task_queues.pop(id(current_task), None)

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response, artifacts=queue.artifacts,
        )

        client = Client(account_sid, auth_token)
        try:
            client.messages.create(body=response[:1600], from_=from_number, to=sender)
        except Exception as e:
            logger.error(f"[whatsapp bot] failed to send message: {e}")

        base_url = get_tunnel_base(str(bot_id))
        if base_url:
            for artifact in queue.artifacts:
                if artifact.get("type") == "image":
                    try:
                        img_bytes = base64.b64decode(artifact["content"])
                        key = await media_store(img_bytes, "image/png")
                        media_url = f"{base_url}/api/agent/bots/media/{key}/"
                        client.messages.create(from_=from_number, to=sender, media_url=[media_url])
                    except Exception as e:
                        logger.warning(f"[whatsapp bot] failed to send image: {e}")

    asyncio.create_task(process_and_reply())

    return HttpResponse("<Response></Response>", content_type="text/xml")
