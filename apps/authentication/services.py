"""Authentication business logic.

All HTTP concerns live in views; this module is reusable from CLI, admin,
and Celery tasks.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from apps.common.exceptions import (
    AuthenticationFailed,
    Conflict,
    NotFound,
    ValidationError,
)
from apps.common.utils import generate_secure_token, hash_token
from apps.users.models import User
from apps.users.selectors import get_user_by_email
from apps.users.services import create_user as create_user_service

from .models import EmailVerificationToken, PasswordResetToken, UserSession
from .tasks import send_password_reset_email, send_verification_email

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registration & verification
# ---------------------------------------------------------------------------
@transaction.atomic
def register_user(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
) -> User:
    """Create a user and dispatch the verification email."""
    user = create_user_service(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    issue_verification_token(user)
    return user


def issue_verification_token(user: User) -> str:
    """Generate a new email verification token, store its hash, send email.

    Returns the plaintext token (for testing); never log it.
    """
    plaintext = generate_secure_token()
    EmailVerificationToken.objects.create(
        user=user,
        token_hash=hash_token(plaintext),
        expires_at=EmailVerificationToken.default_expiry(),
    )
    # Hand off to Celery so the API call isn't blocked on SMTP latency
    send_verification_email.delay(user_id=str(user.id), token=plaintext)
    return plaintext


def verify_email(token: str) -> User:
    """Consume a verification token and mark the user as verified."""
    token_obj = (
        EmailVerificationToken.objects.select_related("user")
        .filter(token_hash=hash_token(token))
        .first()
    )
    if not token_obj or not token_obj.is_valid():
        raise ValidationError("Invalid or expired verification token.", code="invalid_token")

    user = token_obj.user
    with transaction.atomic():
        token_obj.consume()
        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified", "updated_at"])
    return user


def resend_verification(email: str) -> None:
    """Issue a fresh verification token for an unverified account.

    For security, this returns silently whether or not the email exists.
    """
    user = get_user_by_email(email)
    if not user or user.is_verified:
        return
    issue_verification_token(user)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
def request_password_reset(email: str) -> None:
    """Issue a password-reset token. Always returns silently to avoid leaking
    which emails are registered."""
    user = get_user_by_email(email)
    if not user or not user.is_active:
        return
    plaintext = generate_secure_token()
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(plaintext),
        expires_at=PasswordResetToken.default_expiry(),
    )
    send_password_reset_email.delay(user_id=str(user.id), token=plaintext)


@transaction.atomic
def confirm_password_reset(*, token: str, new_password: str) -> User:
    """Consume a reset token and update the password."""
    token_obj = (
        PasswordResetToken.objects.select_related("user")
        .filter(token_hash=hash_token(token))
        .first()
    )
    if not token_obj or not token_obj.is_valid():
        raise ValidationError("Invalid or expired reset token.", code="invalid_token")

    user = token_obj.user
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    token_obj.consume()

    # Invalidate any other outstanding reset tokens for this user
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).exclude(
        id=token_obj.id
    ).update(used_at=token_obj.used_at)
    return user


# ---------------------------------------------------------------------------
# Session tracking
# ---------------------------------------------------------------------------
def record_session(
    *, user: User, refresh_token: RefreshToken, user_agent: str, ip_address: str | None
) -> UserSession:
    """Create a session row for an issued refresh token."""
    return UserSession.objects.create(
        user=user,
        refresh_jti=refresh_token["jti"],
        user_agent=user_agent[:512],
        ip_address=ip_address or None,
    )


def logout(refresh_token_str: str) -> None:
    """Blacklist a refresh token and revoke its session record."""
    try:
        token = RefreshToken(refresh_token_str)
    except TokenError as exc:
        raise AuthenticationFailed("Invalid refresh token.", code="invalid_refresh_token") from exc

    jti = token.get("jti")
    token.blacklist()
    session = UserSession.objects.filter(refresh_jti=jti, revoked_at__isnull=True).first()
    if session:
        session.revoke()


def revoke_session(*, user: User, session_id: Any) -> None:
    """Revoke a specific session belonging to the user."""
    session = UserSession.objects.filter(id=session_id, user=user).first()
    if not session:
        raise NotFound("Session not found.", code="session_not_found")
    if session.revoked_at:
        raise Conflict("Session already revoked.", code="already_revoked")
    session.revoke()
