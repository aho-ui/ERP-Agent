import uuid
from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions", null=True, blank=True)
    bot = models.ForeignKey("BotInstance", on_delete=models.CASCADE, related_name="sessions", null=True, blank=True)
    label = models.CharField(max_length=255, default="New Chat")
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} — {self.label}"


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="chat_messages")
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    artifacts = models.JSONField(default=list)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.session_id} — {self.role} — {self.timestamp}"


class BotInstance(models.Model):
    class Platform(models.TextChoices):
        DISCORD = "discord", "Discord"
        TELEGRAM = "telegram", "Telegram"

    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    token = models.TextField()
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="bot_instances")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.platform})"


class AgentTemplate(models.Model):
    class Type(models.TextChoices):
        TRANSACTION = "transaction", "Transaction"
        ANALYTICS = "analytics", "Analytics"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="agent_templates")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    instructions = models.TextField()
    allowed_tools = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class AgentAction(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    intent = models.CharField(max_length=500)
    agent_name = models.CharField(max_length=255)
    tool_called = models.CharField(max_length=255)
    input_params = models.JSONField(default=dict)
    output = models.JSONField(default=dict)
    erp_record_ref = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_logs")
    artifacts = models.JSONField(default=list)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent_name} — {self.status} — {self.timestamp}"


