"""Read-side queries for users."""
from __future__ import annotations

from .models import User


def get_user_by_email(email: str) -> User | None:
    return User.objects.filter(email__iexact=email.strip()).first()


def get_active_user_by_id(user_id) -> User | None:
    return User.objects.filter(id=user_id, is_active=True).first()
