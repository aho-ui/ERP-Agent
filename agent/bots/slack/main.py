import asyncio
import base64
import io
import json

from loguru import logger
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from agent.framework.agent import get_agent
from agent.utils.queue import CollectingQueue

_agent = get_agent("nanobot")


async def run(token: str, bot_id: str, role: str):
    creds = json.loads(token)
    bot_token = creds["bot_token"]
    app_token = creds["app_token"]

    app = AsyncApp(token=bot_token)
    agent_loop = _agent.get_agent_loop()

    @app.event("message")
    async def handle_message(event, say):
        if event.get("bot_id") or event.get("subtype"):
            return
        text = (event.get("text") or "").strip()
        if not text:
            return

        from agent.models import ChatSession, ChatMessage
        user_id = event.get("user", "unknown")
        channel = event.get("channel", "")
        session_label = f"slack:{user_id}:{channel}"
        session, _ = await ChatSession.objects.aget_or_create(
            bot_id=bot_id,
            label=session_label,
        )

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.USER, content=text, artifacts=[],
        )

        # _agent._user_role.set(role)
        # _agent._user_id.set(None)
        # _agent._source.set("slack")
        # _agent._bot_id.set(bot_id)
        _agent.set_context(user_role=role, user_id=None, source="slack", bot_id=bot_id)

        queue = CollectingQueue()
        thinking_res = await say("_Thinking..._")
        thinking_ts = thinking_res.get("ts")

        async def on_progress(content, **_):
            if not thinking_ts:
                return
            try:
                await app.client.chat_update(
                    channel=channel,
                    ts=thinking_ts,
                    text=f"_{content[:200]}_",
                )
            except Exception:
                pass

        async def run_agent():
            try:
                response = await agent_loop.process_direct(content=text, session_key=str(session.id), on_progress=on_progress)
                await queue.put({"type": "response", "content": response})
            except Exception as e:
                logger.error(f"[slack bot] agent error: {e}")
                await queue.put({"type": "response", "content": "An error occurred. Please try again."})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_agent())
        _agent._task_queues[id(task)] = queue
        task.add_done_callback(lambda t: _agent._task_queues.pop(id(t), None))

        await task

        if thinking_ts:
            try:
                await app.client.chat_delete(channel=channel, ts=thinking_ts)
            except Exception:
                pass

        response = ""
        while not queue.empty():
            item = queue.get_nowait()
            if item and item.get("type") == "response":
                response = item["content"]

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response, artifacts=queue.artifacts,
        )

        await say(response[:3000])

        for artifact in queue.artifacts:
            if artifact.get("type") == "image":
                try:
                    img_bytes = base64.b64decode(artifact["content"])
                    await app.client.files_upload_v2(
                        channel=channel,
                        file=io.BytesIO(img_bytes),
                        filename="chart.png",
                        title="Chart",
                    )
                except Exception as e:
                    logger.warning(f"[slack bot] failed to send image: {e}")

    handler = AsyncSocketModeHandler(app, app_token)
    try:
        await handler.start_async()
        logger.info("Slack bot connected via Socket Mode.")
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        await handler.close_async()
        logger.info("Slack bot stopped.")
    except Exception as e:
        logger.error(f"[slack bot] failed to start: {e}")
