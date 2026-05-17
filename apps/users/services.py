"""User-domain business logic.

Orchestrates user creation and profile updates. Subscription assignment is
delegated to `apps.subscriptions.services` to keep concerns isolated.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.common.exceptions import Conflict

from .models import User, UserRole
from .selectors import get_user_by_email


@transaction.atomic
def create_user(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    role: str = UserRole.CUSTOMER,
) -> User:
    """Create a new user. Caller is responsible for sending verification email."""
    if get_user_by_email(email):
        raise Conflict("An account with this email already exists.", code="email_taken")

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        role=role,
    )

    # Auto-enroll new users in the Free plan. Imported lazily to avoid circular imports.
    from apps.subscriptions.services import enroll_in_free_plan

    enroll_in_free_plan(user)
    return user


def update_profile(user: User, **fields: Any) -> User:
    """Patch allowed profile fields on a user."""
    allowed = {"first_name", "last_name"}
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(user, key, value)
    user.save(update_fields=list(allowed & fields.keys()) + ["updated_at"])
    return user


def change_password(user: User, current_password: str, new_password: str) -> None:
    """Validate the current password and update to a new one."""
    if not user.check_password(current_password):
        from apps.common.exceptions import AuthenticationFailed

        raise AuthenticationFailed("Current password is incorrect.", code="invalid_password")
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
