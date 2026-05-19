import os
import django
from django.apps import apps

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

if not apps.ready:
    django.setup()

from django.core.asgi import get_asgi_application

application = get_asgi_application()
