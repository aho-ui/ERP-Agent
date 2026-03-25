import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        OPERATOR = "operator", "Operator"
        ADMIN = "admin", "Admin"
        BOT = "bot", "Bot"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)
    api_key = models.UUIDField(null=True, blank=True, unique=True)
    api_key_expires_at = models.DateTimeField(null=True, blank=True)
