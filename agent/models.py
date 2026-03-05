import uuid
from django.db import models
from django.conf import settings


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
    output_artifact = models.ForeignKey("OutputArtifact", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent_name} — {self.status} — {self.timestamp}"


class OutputArtifact(models.Model):
    class Type(models.TextChoices):
        CHART = "chart", "Chart"
        PDF = "pdf", "PDF"
        CSV = "csv", "CSV"
        TEXT = "text", "Text"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="artifacts")
    audit_log = models.ForeignKey("AgentAction", on_delete=models.SET_NULL, null=True, blank=True, related_name="artifacts")
    type = models.CharField(max_length=20, choices=Type.choices)
    format = models.CharField(max_length=50)
    storage_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} — {self.storage_path}"
