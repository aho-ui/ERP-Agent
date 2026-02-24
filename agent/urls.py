from django.urls import path
from agent.views import chat

urlpatterns = [
    path("chat/", chat, name="agent-chat"),
]
