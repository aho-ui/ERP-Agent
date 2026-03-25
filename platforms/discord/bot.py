import base64
import io
import json
import os

import aiohttp
import discord
from dotenv import load_dotenv

load_dotenv()

# --- Setup ---
# 1. Go to https://discord.com/developers/applications → New Application → Bot → copy token
# 2. Enable "Message Content Intent" under Bot → Privileged Gateway Intents
# 3. Invite bot to server: OAuth2 → URL Generator → scopes: bot → permissions: Send Messages, Read Messages
# 4. Create a bot user via /users admin UI and issue a long-lived JWT
# 5. Set the following in .env:
#    DISCORD_BOT_TOKEN=<token from Discord Developer Portal>
#    BOT_API_KEY=<api key for bot user>
#    BACKEND_URL=http://localhost:8000


DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# BOT_USER_TOKEN = os.getenv("BOT_USER_TOKEN", "")
BOT_API_KEY = os.getenv("BOT_API_KEY", "")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# ANSI_RESET  = "\u001b[0m"
# ANSI_HEADER = "\u001b[1;33m"  # bold yellow
# ANSI_ROW    = "\u001b[0;37m"  # normal white


# def _table_chunks(artifact: dict) -> list[str]:
#     columns = [str(c) for c in artifact.get("columns", [])]
#     rows = [[str(v) for v in row] for row in artifact.get("rows", [])]
#     if not columns or not rows:
#         return []
#
#     widths = [len(c) for c in columns]
#     for row in rows:
#         for i, val in enumerate(row):
#             if i < len(widths):
#                 widths[i] = max(widths[i], len(val))
#
#     sep = "-+-".join("-" * w for w in widths)
#
#     def fmt_header():
#         return " | ".join(f"{ANSI_HEADER}{c.ljust(widths[i])}{ANSI_RESET}" for i, c in enumerate(columns))
#
#     def fmt_row(cells):
#         return " | ".join(f"{ANSI_ROW}{c.ljust(widths[i])}{ANSI_RESET}" for i, c in enumerate(cells))
#
#     # Build chunks: keep adding rows until chunk would exceed 1900 chars
#     chunks: list[str] = []
#     header_block = f"{fmt_header()}\n{sep}"
#     current_rows: list[str] = []
#
#     def flush():
#         if current_rows:
#             body = "\n".join(current_rows)
#             chunks.append(f"```ansi\n{header_block}\n{body}\n```")
#             current_rows.clear()
#
#     for row in rows:
#         rendered = fmt_row(row)
#         candidate = f"```ansi\n{header_block}\n" + "\n".join(current_rows + [rendered]) + "\n```"
#         if len(candidate) > 1900 and current_rows:
#             flush()
#         current_rows.append(rendered)
#     flush()
#
#     return chunks


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


@client.event
async def on_ready():
    print(f"Discord bot connected as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # Only respond to direct mentions or DMs
    if not (client.user in message.mentions or isinstance(message.channel, discord.DMChannel)):
        return

    text = message.content.replace(f"<@{client.user.id}>", "").strip()
    if not text:
        return

    # Each Discord user gets their own agent session
    session_key = f"discord:{message.author.id}"

    async with message.channel.typing():
        reply, images = await _call_agent(text, session_key)

    await message.reply(reply[:2000])

    for i, img_bytes in enumerate(images):
        await message.channel.send(file=discord.File(io.BytesIO(img_bytes), filename=f"table_{i+1}.png"))

    # for artifact in artifacts:
    #     for chunk in _table_chunks(artifact):
    #         await message.channel.send(chunk)


def main():
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN not set in .env")
    if not BOT_API_KEY:
        raise RuntimeError("BOT_API_KEY not set in .env")
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
