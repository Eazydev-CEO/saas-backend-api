"""Subscription business logic.

Handles enrollment, upgrades/downgrades, expiry, usage recording. Every
state transition is wrapped in a transaction and respects the partial
unique constraint that allows only one active subscription per user.
"""
from __future__ import annotations

import logging

from django.db import models, transaction
from django.utils import timezone

from apps.common.exceptions import Conflict, NotFound, QuotaExceeded

from .models import (
    Plan,
    PlanSlug,
    Subscription,
    SubscriptionStatus,
    UsageQuota,
    default_period_window,
)
from .selectors import get_active_subscription, get_current_quota, get_plan_by_slug

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enrollment & changes
# ---------------------------------------------------------------------------
@transaction.atomic
def enroll_in_free_plan(user) -> Subscription:
    """Auto-subscribe a brand-new user to the Free plan."""
    plan = get_plan_by_slug(PlanSlug.FREE)
    if not plan:
        raise NotFound("Free plan is not configured.", code="plan_missing")
    return _create_subscription(user=user, plan=plan, expires=False)


@transaction.atomic
def subscribe(*, user, plan_slug: str) -> Subscription:
    """Subscribe a user to a plan, replacing any existing active subscription."""
    plan = get_plan_by_slug(plan_slug)
    if not plan:
        raise NotFound("Plan not found.", code="plan_not_found")

    current = get_active_subscription(user)
    if current and current.plan_id == plan.id:
        raise Conflict("Already subscribed to this plan.", code="already_subscribed")

    # Mark the existing subscription as canceled before creating a new one
    if current:
        current.status = SubscriptionStatus.CANCELED
        current.canceled_at = timezone.now()
        current.save(update_fields=["status", "canceled_at", "updated_at"])

    return _create_subscription(
        user=user,
        plan=plan,
        expires=plan.duration_days > 0,
    )


def upgrade(*, user, plan_slug: str) -> Subscription:
    """Alias for subscribe; semantically clearer in API."""
    return subscribe(user=user, plan_slug=plan_slug)


def downgrade(*, user, plan_slug: str = PlanSlug.FREE) -> Subscription:
    return subscribe(user=user, plan_slug=plan_slug)


@transaction.atomic
def cancel(*, user) -> Subscription:
    """Cancel the user's active subscription (immediate)."""
    sub = get_active_subscription(user)
    if not sub:
        raise NotFound("No active subscription to cancel.", code="no_active_subscription")
    sub.status = SubscriptionStatus.CANCELED
    sub.canceled_at = timezone.now()
    sub.auto_renew = False
    sub.save(update_fields=["status", "canceled_at", "auto_renew", "updated_at"])
    # Re-enroll in Free so the user keeps a baseline plan
    return enroll_in_free_plan(user)


def _create_subscription(*, user, plan: Plan, expires: bool) -> Subscription:
    """Internal: actually create the Subscription + opening UsageQuota."""
    start, end = default_period_window(plan)
    sub = Subscription.objects.create(
        user=user,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        started_at=start,
        expires_at=end if expires else None,
        auto_renew=expires,
    )
    UsageQuota.objects.create(
        subscription=sub,
        period_start=start,
        period_end=end if expires else start.replace(year=start.year + 50),
    )
    return sub


# ---------------------------------------------------------------------------
# Usage accounting
# ---------------------------------------------------------------------------
def record_request(user) -> None:
    """Increment the current period's usage counter atomically.

    Raises QuotaExceeded if the user is over their plan's request_quota.
    """
    sub = get_active_subscription(user)
    if not sub:
        # No subscription means no quota; users without a sub shouldn't reach
        # billed endpoints. Auto-enroll free as a safety net.
        sub = enroll_in_free_plan(user)

    quota = _current_or_rotate_quota(sub)
    limit = sub.plan.request_quota

    if limit and quota.requests_used >= limit:
        raise QuotaExceeded(
            f"Monthly quota of {limit} requests exceeded for plan '{sub.plan.slug}'.",
            code="quota_exceeded",
            details={"plan": sub.plan.slug, "limit": limit, "used": quota.requests_used},
        )

    # Atomic increment to survive concurrent requests
    UsageQuota.objects.filter(pk=quota.pk).update(
        requests_used=models.F("requests_used") + 1
    )


def _current_or_rotate_quota(sub: Subscription) -> UsageQuota:
    """Return the current period's quota, rotating to a new period if needed."""
    quota = get_current_quota(sub)
    if quota:
        return quota
    start, end = default_period_window(sub.plan)
    return UsageQuota.objects.create(
        subscription=sub, period_start=start, period_end=end
    )


# ---------------------------------------------------------------------------
# Expiry sweep (called by Celery beat)
# ---------------------------------------------------------------------------
def expire_due_subscriptions() -> int:
    """Mark active subscriptions whose `expires_at` has passed as expired.

    Returns the number affected. Idempotent.
    """
    now = timezone.now()
    qs = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        expires_at__lte=now,
        expires_at__isnull=False,
    )
    affected = 0
    for sub in qs.select_related("user", "plan"):
        try:
            with transaction.atomic():
                sub.status = SubscriptionStatus.EXPIRED
                sub.save(update_fields=["status", "updated_at"])
                enroll_in_free_plan(sub.user)
                affected += 1
        except Exception:  # pragma: no cover
            logger.exception("Failed to expire subscription %s", sub.id)
    return affected


# ---------------------------------------------------------------------------
# Feature gates
# ---------------------------------------------------------------------------
def has_feature(user, feature_key: str) -> bool:
    sub = get_active_subscription(user)
    if not sub:
        return False
    return bool(sub.plan.features.get(feature_key))
