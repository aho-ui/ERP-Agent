from django.urls import path
from agent.api.chat import chat, confirm_action, cancel_action
from agent.api.sessions import sessions, update_session, session_messages
from agent.api.audit import actions, action_detail, dashboard
from agent.api.templates import agent_templates, agent_template_detail, available_tools
from agent.api.files import upload, export, po_document
from agent.api.health import mcp
from agent.api.bots import bots, update_bot, list_bot_sessions, bot_chat
from agent.bots.whatsapp.main import webhook as whatsapp_webhook
from agent.bots.media import serve as media_serve

urlpatterns = [
    # Chat (streaming SSE) — already ideal
    path("chat/", chat, name="agent-chat"),

    path("mcp/", mcp, name="mcp"),

    path("actions/", actions, name="actions"),
    path("actions/<uuid:action_id>/", action_detail, name="action-detail"),
    path("actions/<uuid:action_id>/confirm/", confirm_action, name="action-confirm"),
    path("actions/<uuid:action_id>/cancel/", cancel_action, name="action-cancel"),

    path("sessions/", sessions, name="sessions"),
    path("sessions/<uuid:session_id>/", update_session, name="session-detail"),
    path("sessions/<uuid:session_id>/messages/", session_messages, name="session-messages"),

    path("templates/", agent_templates, name="templates"),
    path("templates/<uuid:template_id>/", agent_template_detail, name="template-detail"),
    path("tools/", available_tools, name="tools"),

    path("documents/po/", po_document, name="document-po"),
    path("export/", export, name="export"),
    path("upload/", upload, name="upload"),

    path("bots/", bots, name="bots"),
    path("bots/<uuid:bot_id>/", update_bot, name="bot-detail"),
    path("bots/<uuid:bot_id>/sessions/", list_bot_sessions, name="bot-sessions"),
    path("bots/<uuid:bot_id>/sessions/<uuid:session_id>/chat/", bot_chat, name="bot-chat"),
    path("bots/whatsapp/webhook/<uuid:bot_id>/", whatsapp_webhook, name="bot-whatsapp-webhook"),
    path("bots/media/<str:key>/", media_serve, name="bot-media"),

    # Dashboard (aggregates only — after restructure, drops `mcps` section since /mcp/?detail=full covers it)
    path("dashboard/", dashboard, name="agent-dashboard"),
]
