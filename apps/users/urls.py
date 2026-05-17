"""User app routes."""
from __future__ import annotations

from django.urls import path

from .views import ChangePasswordView, MeView, UserListView

app_name = "users"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("me/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("", UserListView.as_view(), name="list"),
]
