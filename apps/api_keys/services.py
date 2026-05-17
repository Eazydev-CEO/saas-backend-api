"""API key business logic."""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.common.exceptions import Conflict, NotFound, PermissionDenied
from apps.subscriptions.selectors import get_active_subscription

from .models import APIKey, compute_hash, generate_plaintext_key, split_prefix


@dataclass
class IssuedKey:
    """Plaintext key + persisted record. Plaintext is returned once only."""

    plaintext: str
    api_key: APIKey


@transaction.atomic
def create_api_key(*, user, name: str) -> IssuedKey:
    """Issue a new API key for the user, subject to plan limits."""
    sub = get_active_subscription(user)
    plan_max = sub.plan.max_api_keys if sub else 1
    current_active = APIKey.objects.filter(user=user, revoked_at__isnull=True).count()
    if current_active >= plan_max:
        raise PermissionDenied(
            f"Your plan allows at most {plan_max} active API key(s).",
            code="api_key_limit_reached",
            details={"limit": plan_max, "current": current_active},
        )

    plaintext = generate_plaintext_key()
    key = APIKey.objects.create(
        user=user,
        name=name.strip()[:120] or "default",
        prefix=split_prefix(plaintext),
        key_hash=compute_hash(plaintext),
    )
    return IssuedKey(plaintext=plaintext, api_key=key)


def revoke_api_key(*, user, key_id) -> APIKey:
    key = APIKey.objects.filter(id=key_id, user=user).first()
    if not key:
        raise NotFound("API key not found.", code="api_key_not_found")
    if not key.is_active:
        raise Conflict("API key already revoked.", code="already_revoked")
    key.revoke()
    return key


@transaction.atomic
def rotate_api_key(*, user, key_id) -> IssuedKey:
    """Revoke the existing key and issue a new one with the same name."""
    old = APIKey.objects.select_for_update().filter(id=key_id, user=user).first()
    if not old:
        raise NotFound("API key not found.", code="api_key_not_found")
    if not old.is_active:
        raise Conflict("Cannot rotate a revoked key.", code="already_revoked")
    name = old.name
    old.revoke()
    return create_api_key(user=user, name=name)
