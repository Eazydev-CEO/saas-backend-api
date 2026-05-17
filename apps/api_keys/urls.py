"""API key routes."""
from __future__ import annotations

from django.urls import path

from .views import APIKeyListCreateView, APIKeyRevokeView, APIKeyRotateView

app_name = "api_keys"

urlpatterns = [
    path("", APIKeyListCreateView.as_view(), name="list-create"),
    path("<uuid:key_id>/revoke/", APIKeyRevokeView.as_view(), name="revoke"),
    path("<uuid:key_id>/rotate/", APIKeyRotateView.as_view(), name="rotate"),
]
