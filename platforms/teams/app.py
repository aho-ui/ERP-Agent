import os

from aiohttp import web
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity
from dotenv import load_dotenv

load_dotenv()

# --- Placeholders: fill these in .env after registering the bot on Azure ---
# TEAMS_APP_ID=<your-microsoft-app-id>
# TEAMS_APP_PASSWORD=<your-microsoft-app-password>
# TEAMS_BOT_PORT=3978
#
# --- Bot user: create via /users admin UI, then paste the JWT here ---
# BOT_USER_TOKEN=<long-lived-jwt-for-bot-user>
# BACKEND_URL=http://localhost:8000
# ---------------------------------------------------------------------------

MICROSOFT_APP_ID = os.getenv("TEAMS_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.getenv("TEAMS_APP_PASSWORD", "")

settings = BotFrameworkAdapterSettings(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
adapter = BotFrameworkAdapter(settings)

from platforms.teams.bot import TeamsBot  # noqa: E402
bot = TeamsBot()


async def messages(req: web.Request) -> web.Response:
    if "application/json" not in req.headers.get("Content-Type", ""):
        return web.Response(status=415)

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    await adapter.process_activity(activity, auth_header, bot.on_turn)
    return web.Response(status=200)


app = web.Application()
app.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    port = int(os.getenv("TEAMS_BOT_PORT", "3978"))
    print(f"Teams bot listening on port {port}")
    web.run_app(app, host="0.0.0.0", port=port)
