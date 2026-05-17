"""Authentication-domain models.

All tokens are stored as SHA-256 hashes so a database leak does not yield
valid verification links or reset tokens.
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class _ActiveTokenManager(models.Manager):
    """Convenience manager that filters out expired/used tokens."""

    def active(self):
        now = timezone.now()
        return self.filter(used_at__isnull=True, expires_at__gt=now)


class EmailVerificationToken(BaseModel):
    """One-shot email verification token, hashed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    objects = _ActiveTokenManager()

    class Meta:
        db_table = "auth_email_verification_token"
        indexes = [models.Index(fields=["user", "used_at"])]

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(
            hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS
        )

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def consume(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])


class PasswordResetToken(BaseModel):
    """One-shot password reset token, hashed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    objects = _ActiveTokenManager()

    class Meta:
        db_table = "auth_password_reset_token"
        indexes = [models.Index(fields=["user", "used_at"])]

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(
            hours=settings.PASSWORD_RESET_TOKEN_TTL_HOURS
        )

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def consume(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])


class UserSession(BaseModel):
    """Lightweight session/device record for refresh tokens.

    Created on login, marked revoked on logout. Lets a user see and revoke
    active devices in the dashboard.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    refresh_jti = models.CharField(max_length=64, unique=True, db_index=True)
    user_agent = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auth_user_session"
        indexes = [models.Index(fields=["user", "revoked_at"])]
        ordering = ["-created_at"]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])
