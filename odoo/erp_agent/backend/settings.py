import os
import sys
import tempfile
from pathlib import Path

_ADDON_DIR = Path(__file__).parent.parent   # odoo/erp_agent/

if str(_ADDON_DIR) not in sys.path:
    sys.path.insert(0, str(_ADDON_DIR))

try:
    from odoo.tools import config as _odoo_config
    _DATA_DIR = Path(_odoo_config["data_dir"]) / "erp_agent"
except Exception:
    _DATA_DIR = Path(tempfile.gettempdir()) / "erp_agent"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = "erp-agent-slim-backend-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "corsheaders",
    "backend.chat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-api-key",
]

ROOT_URLCONF = "backend.urls"
ASGI_APPLICATION = "backend.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # "NAME": _ADDON_DIR / "agent.db",
        "NAME": _DATA_DIR / "agent.db",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
