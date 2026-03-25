import base64
import io
import json
import logging
import os

import aiohttp
from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(find_dotenv())

# --- Setup ---
# 1. Message @BotFather on Telegram → /newbot → copy the token
# 2. Create a bot user via /users admin UI and issue a long-lived JWT
# 3. Set the following in .env:
#    TELEGRAM_BOT_TOKEN=<token from BotFather>
#    BOT_USER_TOKEN=<long-lived JWT for bot user>
#    BACKEND_URL=http://localhost:8000

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# BOT_USER_TOKEN = os.getenv("BOT_USER_TOKEN", "")
BOT_API_KEY = os.getenv("BOT_API_KEY", "")

logging.basicConfig(level=logging.INFO)


async def _call_agent(message: str, session_key: str) -> tuple[str, list[bytes]]:
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": BOT_API_KEY,
    }
    payload = {"message": message, "session_key": session_key}

    collected_text: list[str] = []
    collected_images: list[bytes] = []
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/agent/chat/",
            headers=headers,
            json=payload,
        ) as resp:
            buffer = ""
            async for chunk in resp.content:
                buffer += chunk.decode("utf-8")
                lines = buffer.split("\n")
                buffer = lines.pop()
                for line in lines:
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        event = json.loads(raw)
                        if event.get("type") == "response":
                            collected_text.append(event.get("content", ""))
                        elif event.get("type") == "image":
                            collected_images.append(base64.b64decode(event["content"]))
                    except json.JSONDecodeError:
                        pass

    text = "\n".join(collected_text) if collected_text else "No response from agent."
    return text, collected_images


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (update.message.text or "").strip()
    if not message:
        return

    session_key = f"telegram:{update.effective_user.id}"

    await update.message.chat.send_action("typing")
    reply, images = await _call_agent(message, session_key)
    await update.message.reply_text(reply)
    for i, img_bytes in enumerate(images):
        # await update.message.reply_photo(io.BytesIO(img_bytes))
        await update.message.reply_document(document=io.BytesIO(img_bytes), filename=f"table_{i+1}.png")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")
    if not BOT_API_KEY:
        raise RuntimeError("BOT_API_KEY not set in .env")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
