import asyncio
import base64
import io

from loguru import logger
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from agent.framework.agent import get_agent

_agent = get_agent("nanobot")


async def run(token: str, bot_id: str, role: str, progress_queue: asyncio.Queue | None = None):
    agent_loop = _agent.get_agent_loop()

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (update.message.text or "").strip()
        if not text:
            return

        from agent.models import ChatSession, ChatMessage
        session_label = f"telegram:{update.effective_user.id}"
        session, _ = await ChatSession.objects.aget_or_create(
            bot_id=bot_id,
            label=session_label,
        )

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.USER, content=text, artifacts=[],
        )

        # _agent._user_role.set(role)
        # _agent._user_id.set(None)
        # _agent._source.set("telegram")
        # _agent._bot_id.set(bot_id)
        _agent.set_context(user_role=role, user_id=None, source="telegram", bot_id=bot_id)

        artifact_queue = asyncio.Queue()
        current_task = asyncio.current_task()
        if current_task:
            _agent._task_queues[id(current_task)] = artifact_queue

        thinking_msg = None
        try:
            thinking_msg = await update.message.reply_text("_Thinking..._", parse_mode="Markdown")
        except Exception:
            pass

        async def on_progress(content, **_):
            if progress_queue:
                progress_queue.put_nowait({"type": "progress", "content": content})
            if not thinking_msg:
                return
            try:
                await thinking_msg.edit_text(f"_{content[:200]}_", parse_mode="Markdown")
            except Exception:
                pass

        try:
            response = await agent_loop.process_direct(content=text, session_key=str(session.id), on_progress=on_progress)
        except Exception as e:
            logger.error(f"[telegram bot] agent error: {e}")
            response = "An error occurred. Please try again."
        finally:
            if current_task:
                _agent._task_queues.pop(id(current_task), None)

        if thinking_msg:
            try:
                await thinking_msg.delete()
            except Exception:
                pass

        images: list[bytes] = []
        pdfs: list[tuple[bytes, str]] = []
        while not artifact_queue.empty():
            item = artifact_queue.get_nowait()
            if item.get("type") == "image":
                try:
                    images.append(base64.b64decode(item["content"]))
                except Exception:
                    pass
            elif item.get("type") == "pdf":
                try:
                    pdfs.append((base64.b64decode(item["content"]), item.get("title", "document")))
                except Exception:
                    pass

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response, artifacts=[],
        )

        for attempt in range(3):
            try:
                await update.message.reply_text(response)
                break
            except Exception as e:
                if attempt == 2:
                    logger.error(f"[telegram bot] failed to send reply after 3 attempts: {e}")
                else:
                    await asyncio.sleep(2)

        for img_bytes in images:
            try:
                await update.message.reply_document(document=io.BytesIO(img_bytes), filename="table.png")
            except Exception as e:
                logger.warning(f"[telegram bot] failed to send image: {e}")
        for pdf_bytes, title in pdfs:
            try:
                await update.message.reply_document(document=io.BytesIO(pdf_bytes), filename=f"{title}.pdf")
            except Exception as e:
                logger.warning(f"[telegram bot] failed to send pdf: {e}")

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.warning(f"[telegram bot] update error: {context.error}")

    app = (
        Application.builder()
        .token(token)
        .connect_timeout(120)
        .read_timeout(120)
        .write_timeout(120)
        .pool_timeout(120)
        .get_updates_connect_timeout(120)
        .get_updates_read_timeout(120)
        .get_updates_write_timeout(120)
        .get_updates_pool_timeout(120)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    initialized = False
    try:
        await app.initialize()
        initialized = True
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot polling...")
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Telegram bot stopped.")
    except Exception as e:
        logger.error(f"[telegram bot] failed to start: {e}")
    finally:
        if initialized:
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception:
                pass
