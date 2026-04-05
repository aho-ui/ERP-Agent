import asyncio
import base64
import io

import discord
from loguru import logger

from agent.framework.agent import get_agent
from agent.utils.queue import CollectingQueue

_agent = get_agent("nanobot")


async def run(token: str, bot_id: str, role: str):
    # progress_queue: asyncio.Queue | None = None
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    agent_loop = _agent.get_agent_loop()

    @client.event
    async def on_ready():
        logger.info(f"Discord bot connected as {client.user}")

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user:
            return
        if not (client.user in message.mentions or isinstance(message.channel, discord.DMChannel)):
            return
        text = message.content.replace(f"<@{client.user.id}>", "").strip()
        if not text:
            return

        from agent.models import ChatSession, ChatMessage
        session_label = f"discord:{message.author.id}"
        session, _ = await ChatSession.objects.aget_or_create(
            bot_id=bot_id,
            label=session_label,
        )

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.USER, content=text, artifacts=[],
        )

        _agent._user_role.set(role)
        _agent._user_id.set(None)
        _agent._source.set("discord")
        _agent._bot_id.set(bot_id)

        queue = CollectingQueue()
        thinking_msg = await message.channel.send("_Thinking..._")

        async def on_progress(content, **_):
            await queue.put({"type": "progress", "content": content})
            # if progress_queue:
            #     progress_queue.put_nowait({"type": "progress", "content": content})
            try:
                await thinking_msg.edit(content=f"_{content[:200]}_")
            except Exception:
                pass

        async def run_agent():
            try:
                response = await agent_loop.process_direct(content=text, session_key=str(session.id), on_progress=on_progress)
                await queue.put({"type": "response", "content": response})
                # if progress_queue:
                #     progress_queue.put_nowait({"type": "response", "content": response})
            except Exception as e:
                logger.error(f"[discord bot] agent error: {e}")
                await queue.put({"type": "response", "content": "An error occurred. Please try again."})
            finally:
                await queue.put(None)
                # if progress_queue:
                #     progress_queue.put_nowait(None)

        task = asyncio.create_task(run_agent())
        _agent._task_queues[id(task)] = queue
        task.add_done_callback(lambda t: _agent._task_queues.pop(id(t), None))

        await task

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        response = ""
        while not queue.empty():
            item = queue.get_nowait()
            if not item:
                continue
            if item.get("type") == "progress":
                await ChatMessage.objects.acreate(
                    session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=f"[thinking] {item['content']}", artifacts=[],
                )
            elif item.get("type") == "response":
                response = item["content"]

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response[:2000], artifacts=queue.artifacts,
        )

        await message.reply(response[:2000])
        for artifact in queue.artifacts:
            if artifact.get("type") == "image":
                try:
                    img_bytes = base64.b64decode(artifact["content"])
                    await message.channel.send(file=discord.File(io.BytesIO(img_bytes), filename="table.png"))
                except Exception as e:
                    logger.warning(f"[discord bot] failed to send image: {e}")
            elif artifact.get("type") == "pdf":
                try:
                    pdf_bytes = base64.b64decode(artifact["content"])
                    await message.channel.send(file=discord.File(io.BytesIO(pdf_bytes), filename=f"{artifact.get('title', 'document')}.pdf"))
                except Exception as e:
                    logger.warning(f"[discord bot] failed to send pdf: {e}")

    try:
        await client.start(token)
    except asyncio.CancelledError:
        await client.close()
        logger.info("Discord bot stopped.")
