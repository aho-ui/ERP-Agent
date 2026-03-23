from django.urls import path
from agent.views import chat, mcp_health, confirm_action, cancel_action, pending_actions, agent_logs, agent_templates, agent_template_detail, available_tools, export_csv, export_pdf

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
    path("export/csv/", export_csv, name="agent-export-csv"),
    path("export/pdf/", export_pdf, name="agent-export-pdf"),
]
