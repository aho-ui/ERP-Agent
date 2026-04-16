from django.urls import path
from agent.api.chat import chat, confirm_action, cancel_action, pending_actions, action_status
from agent.api.sessions import list_sessions, list_closed_sessions, create_session, update_session, session_messages
from agent.api.logs import agent_logs, export_logs
from agent.api.templates import agent_templates, agent_template_detail, available_tools, toggle_agent
from agent.api.export import export
from agent.api.health import mcp_health
from agent.api.documents import po_document
from agent.api.bots import list_bots, create_bot, update_bot, list_bot_sessions, bot_chat
from agent.bots.whatsapp.main import webhook as whatsapp_webhook
from agent.bots.media import serve as media_serve
# from agent.api.bots import bot_progress
from agent.api.dashboard import dashboard, dashboard_calls
from agent.api.upload import upload

urlpatterns = [
    path("chat/", chat, name="agent-chat"),
    path("mcp/health/", mcp_health, name="mcp-health"),
    path("confirm/<uuid:action_id>/", confirm_action, name="agent-confirm"),
    path("cancel/<uuid:action_id>/", cancel_action, name="agent-cancel"),
    path("pending/", pending_actions, name="agent-pending"),
    path("actions/<uuid:action_id>/", action_status, name="agent-action-status"),
    path("sessions/", list_sessions, name="agent-sessions-list"),
    path("sessions/closed/", list_closed_sessions, name="agent-sessions-closed"),
    path("sessions/create/", create_session, name="agent-sessions-create"),
    path("sessions/<uuid:session_id>/", update_session, name="agent-sessions-update"),
    path("sessions/<uuid:session_id>/messages/", session_messages, name="agent-session-messages"),
    path("logs/", agent_logs, name="agent-logs"),
    path("logs/export/", export_logs, name="agent-logs-export"),
    path("templates/", agent_templates, name="agent-templates"),
    path("templates/toggle/", toggle_agent, name="agent-templates-toggle"),
    path("templates/tools/", available_tools, name="agent-available-tools"),
    path("templates/<uuid:template_id>/", agent_template_detail, name="agent-template-detail"),
    path("documents/po/", po_document, name="document-po"),
    path("export/", export, name="agent-export"),
    path("export/csv/", export, name="agent-export-csv"),
    path("export/pdf/", export, name="agent-export-pdf"),
    path("export/xlsx/", export, name="agent-export-xlsx"),
    path("bots/", list_bots, name="agent-bots-list"),
    path("bots/create/", create_bot, name="agent-bots-create"),
    path("bots/<uuid:bot_id>/", update_bot, name="agent-bots-update"),
    path("bots/<uuid:bot_id>/sessions/", list_bot_sessions, name="agent-bots-sessions"),
    path("bots/<uuid:bot_id>/sessions/<uuid:session_id>/chat/", bot_chat, name="agent-bots-chat"),
    path("bots/whatsapp/webhook/<uuid:bot_id>/", whatsapp_webhook, name="agent-bots-whatsapp-webhook"),
    path("bots/media/<str:key>/", media_serve, name="agent-bots-media"),
    # path("bots/<uuid:bot_id>/progress/", bot_progress, name="agent-bots-progress"),
    path("upload/", upload, name="agent-upload"),
    path("dashboard/", dashboard, name="agent-dashboard"),
    path("dashboard/calls/", dashboard_calls, name="agent-dashboard-calls"),
]
