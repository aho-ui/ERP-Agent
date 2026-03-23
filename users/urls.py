from django.urls import path
from users.views import login, users_list, user_detail

urlpatterns = [
    path("login/", login, name="user-login"),
    path("", users_list, name="users-list"),
    path("<uuid:user_id>/", user_detail, name="user-detail"),
]
