from django.urls import path
from agent.views import chat, mcp_health, confirm_action, cancel_action, pending_actions, agent_logs, agent_templates, agent_template_detail, available_tools, export

urlpatterns = [
    path("chat/", chat, name="agent-chat"),
    path("mcp/health/", mcp_health, name="mcp-health"),
    path("confirm/<uuid:action_id>/", confirm_action, name="agent-confirm"),
    path("cancel/<uuid:action_id>/", cancel_action, name="agent-cancel"),
    path("pending/", pending_actions, name="agent-pending"),
    path("logs/", agent_logs, name="agent-logs"),
    path("templates/", agent_templates, name="agent-templates"),
    path("templates/tools/", available_tools, name="agent-available-tools"),
    path("templates/<uuid:template_id>/", agent_template_detail, name="agent-template-detail"),
    path("export/", export, name="agent-export"),
    path("export/csv/", export, name="agent-export-csv"),
    path("export/pdf/", export, name="agent-export-pdf"),
    path("export/xlsx/", export, name="agent-export-xlsx"),
]
