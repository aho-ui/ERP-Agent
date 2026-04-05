import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

_django_app = get_asgi_application()


async def _on_startup():
    from agent.api.bots import _start
    from agent.models import BotInstance
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
