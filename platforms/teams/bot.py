import json
import os

import aiohttp
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity

# Set in .env after creating a bot user via /users admin UI and issuing a long-lived token
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BOT_USER_TOKEN = os.getenv("BOT_USER_TOKEN", "")


class TeamsBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        message = (turn_context.activity.text or "").strip()
        if not message:
            return

        # Each Teams user gets their own agent session
        teams_user_id = turn_context.activity.from_property.id
        session_key = f"teams:{teams_user_id}"

        reply = await _call_agent(message, session_key)
        await turn_context.send_activity(Activity(type="message", text=reply))


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
