import logging
import os
import sys
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path

_ADDON_DIR = Path(__file__).parent        # odoo/erp_agent/

LOG_BUFFER = deque(maxlen=500)


def _record(level, message):
    LOG_BUFFER.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    })


class _BufferHandler(logging.Handler):
    def emit(self, record):
        try:
            _record(record.levelname, self.format(record))
        except Exception:
            pass


def _install_log_capture():
    handler = _BufferHandler()
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
    try:
        from loguru import logger as _loguru
        _loguru.add(lambda msg: _record("INFO", msg.record["message"]), level="INFO")
    except Exception:
        pass


def start():
    _install_log_capture()
    _record("INFO", "starting erp_agent backend thread")

    def _run():
        try:
            if str(_ADDON_DIR) not in sys.path:
                sys.path.insert(0, str(_ADDON_DIR))

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

            import django
            from django.apps import apps
            if not apps.ready:
                django.setup()
            _record("INFO", "django setup complete")

            from backend.mcp_servers.seed import ensure_seeded
            ensure_seeded()
            _record("INFO", "demo.db ready")

            import uvicorn
            _record("INFO", "starting uvicorn on 127.0.0.1:8001")
            uvicorn.run(
                "backend.asgi:application",
                host="127.0.0.1",
                port=8001,
                log_level="info",
            )
        except Exception as e:
            _record("ERROR", f"backend crashed: {e}")
            _record("ERROR", traceback.format_exc())

    t = threading.Thread(target=_run, name="erp-agent-backend", daemon=True)
    t.start()
