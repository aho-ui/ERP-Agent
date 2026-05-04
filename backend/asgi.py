import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

_django_app = get_asgi_application()


async def _on_startup():
    # lazy: avoid loading agent module chain before django.setup() completes
    from asgiref.sync import sync_to_async
    from agent.api.bots import _start
    from agent.models import AgentTemplate, BotInstance
    from agent.framework.nanobot import main as agent_main
    from agent.framework.nanobot.agents.factory import seed_from_yaml
    from agent.framework.nanobot.agents.dispatch import DispatchTool
    from agent.utils.mcp import health

    if await AgentTemplate.objects.acount() == 0:
        await sync_to_async(seed_from_yaml)(["odoo.yaml", "demo.yaml"])

    agent_loop = agent_main.get_agent_loop()
    await agent_loop._connect_mcp()
    await health()
    await DispatchTool.refresh()

    async for bot in BotInstance.objects.filter(is_active=True):
        try:
            await _start(bot)
        except Exception:
            pass


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    await _on_startup()
                finally:
                    await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        await _django_app(scope, receive, send)
