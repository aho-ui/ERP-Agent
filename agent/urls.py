from django.urls import path
from agent.views import chat, mcp_health, confirm_action, cancel_action, pending_actions

urlpatterns = [
    path("chat/", chat, name="agent-chat"),
    path("mcp/health/", mcp_health, name="mcp-health"),
    path("confirm/<uuid:action_id>/", confirm_action, name="agent-confirm"),
    path("cancel/<uuid:action_id>/", cancel_action, name="agent-cancel"),
    path("pending/", pending_actions, name="agent-pending"),
]
