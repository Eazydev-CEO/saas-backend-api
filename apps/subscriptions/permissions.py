"""Subscription-driven permission classes."""
from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class HasActiveSubscription(BasePermission):
    """User has an active, non-expired subscription."""

    message = "An active subscription is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        sub = getattr(request, "subscription", None)
        return bool(sub and sub.is_active)


class HasFeature(BasePermission):
    """Plan-feature gate. Use as `permission_classes = [HasFeature('api_keys')]`.

    Instantiating with an arg requires this factory pattern:
        permission_classes = [HasFeature.with_key("api_keys")]
    """

    feature_key: str = ""
    message = "Your current plan does not include this feature."

    @classmethod
    def with_key(cls, key: str):
        return type(f"HasFeature_{key}", (cls,), {"feature_key": key})

    def has_permission(self, request: Request, view: APIView) -> bool:
        sub = getattr(request, "subscription", None)
        if not sub or not sub.is_active:
            return False
        return bool(sub.plan.features.get(self.feature_key))
