from django.urls import path
from backend.chat import views

urlpatterns = [
    path("chat/", views.chat),
    path("health/", views.health),
]
