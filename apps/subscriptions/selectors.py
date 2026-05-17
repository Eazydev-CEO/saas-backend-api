"""Read-side queries for subscriptions."""
from __future__ import annotations

from django.utils import timezone

from .models import Plan, Subscription, SubscriptionStatus, UsageQuota


def get_active_subscription(user) -> Subscription | None:
    return (
        Subscription.objects.select_related("plan")
        .filter(user=user, status=SubscriptionStatus.ACTIVE)
        .first()
    )


def get_current_quota(subscription: Subscription) -> UsageQuota | None:
    now = timezone.now()
    return (
        UsageQuota.objects.filter(
            subscription=subscription,
            period_start__lte=now,
            period_end__gt=now,
        )
        .order_by("-period_start")
        .first()
    )


def get_plan_by_slug(slug: str) -> Plan | None:
    return Plan.objects.filter(slug=slug, is_active=True).first()
