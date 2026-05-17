"""Reusable RBAC permission classes.

Composable: combine with bitwise `&` / `|` in views, e.g.
    permission_classes = [IsAuthenticated & (IsAdmin | IsStaff)]
"""
from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAuthenticatedAndVerified(BasePermission):
    """Authenticated user whose email is verified."""

    message = "Email verification required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_verified", False))


class IsAdmin(BasePermission):
    """User has the Admin role."""

    message = "Admin role required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "admin")


class IsStaffOrAbove(BasePermission):
    """User is Staff or Admin."""

    message = "Staff or Admin role required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in {"admin", "staff"}
        )


class IsOwner(BasePermission):
    """Object-level: the requesting user owns the object (by `user` attribute)."""

    message = "You do not own this resource."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        owner = getattr(obj, "user", None) or getattr(obj, "owner", None)
        return owner is not None and owner == request.user


class ReadOnly(BasePermission):
    """Allows GET/HEAD/OPTIONS regardless."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in {"GET", "HEAD", "OPTIONS"}
