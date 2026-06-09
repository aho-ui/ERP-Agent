import asyncio
import os

import django
from django.apps import apps
from loguru import logger

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

if not apps.ready:
    django.setup()

from django.core.asgi import get_asgi_application

_django_app = get_asgi_application()


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    from backend import agent_loop as AL
                    AL.set_daemon_loop(asyncio.get_running_loop())
                    from backend.monitor import run_monitor, wait_ready
                    asyncio.create_task(run_monitor())
                    await wait_ready()
                except Exception as e:
                    logger.error(f"[asgi] monitor startup failed: {e}")
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        await _django_app(scope, receive, send)
