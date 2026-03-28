import asyncio

from loguru import logger
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from agent.framework.agent import get_agent

_agent = get_agent("nanobot")


async def run(token: str, bot_id: str, role: str):
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

        _agent._user_role.set(role)
        _agent._user_id.set(None)

        await update.message.chat.send_action("typing")
        try:
            response = await agent_loop.process_direct(content=text, session_key=str(session.id))
        except Exception as e:
            logger.error(f"[telegram bot] agent error: {e}")
            response = "An error occurred. Please try again."

        await ChatMessage.objects.acreate(
            session=session, user=None, role=ChatMessage.Role.ASSISTANT, content=response, artifacts=[],
        )

        await update.message.reply_text(response)

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot polling...")
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Telegram bot stopped.")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
