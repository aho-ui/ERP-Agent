import json
import logging
import os

import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

load_dotenv()

# --- Setup ---
# 1. Message @BotFather on Telegram → /newbot → copy the token
# 2. Create a bot user via /users admin UI and issue a long-lived JWT
# 3. Set the following in .env:
#    TELEGRAM_BOT_TOKEN=<token from BotFather>
#    BOT_USER_TOKEN=<long-lived JWT for bot user>
#    BACKEND_URL=http://localhost:8000

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BOT_USER_TOKEN = os.getenv("BOT_USER_TOKEN", "")

logging.basicConfig(level=logging.INFO)


async def _call_agent(message: str, session_key: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BOT_USER_TOKEN}",
    }
    payload = {"message": message, "session_key": session_key}

    collected: list[str] = []
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/agent/chat/",
            headers=headers,
            json=payload,
        ) as resp:
            async for raw in resp.content:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                    if event.get("type") == "response":
                        collected.append(event.get("content", ""))
                except json.JSONDecodeError:
                    pass

    return "\n".join(collected) if collected else "No response from agent."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (update.message.text or "").strip()
    if not message:
        return

    # Each Telegram user gets their own agent session
    session_key = f"telegram:{update.effective_user.id}"

    await update.message.chat.send_action("typing")
    reply = await _call_agent(message, session_key)
    await update.message.reply_text(reply)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
