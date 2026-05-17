"""APIKey model: hashed key storage with prefix for identification."""
from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.common.utils import hash_token

KEY_PREFIX = "sk_live_"
PREFIX_LEN_FOR_DISPLAY = 12  # e.g. "sk_live_a1b2"


class APIKey(BaseModel):
    """Hashed API key.

    The full key (`sk_live_xxx...`) is shown to the user exactly once at
    creation. We persist:
      - `prefix`: first 12 chars, for human identification
      - `key_hash`: SHA-256 of the full key, for authentication

    Authentication path looks up by prefix (indexed) and compares hash in
    constant time.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys"
    )
    name = models.CharField(max_length=120)
    prefix = models.CharField(max_length=16, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_keys_api_key"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "revoked_at"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def mark_used(self) -> None:
        APIKey.objects.filter(pk=self.pk).update(last_used_at=timezone.now())

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])


def generate_plaintext_key() -> str:
    """Generate a new opaque key, prefixed for identification."""
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def split_prefix(plaintext: str) -> str:
    return plaintext[:PREFIX_LEN_FOR_DISPLAY]


def compute_hash(plaintext: str) -> str:
    return hash_token(plaintext)
