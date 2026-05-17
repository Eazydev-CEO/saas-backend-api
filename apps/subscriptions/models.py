"""Subscription-domain models."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class PlanSlug(models.TextChoices):
    FREE = "free", "Free"
    PRO = "pro", "Pro"
    ENTERPRISE = "enterprise", "Enterprise"


class Plan(BaseModel):
    """A purchasable plan.

    `features` is a JSON blob of feature flags (e.g. {"api_keys": True,
    "advanced_analytics": False}). Marketing can add tiers without migrations.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=64, unique=True, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="USD")
    # Request quota per billing period; 0 = unlimited
    request_quota = models.PositiveIntegerField(default=0)
    # Rate limit per minute; 0 = unlimited
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    # Allowed API keys
    max_api_keys = models.PositiveIntegerField(default=1)
    # Duration of one billing period in days. 0 = perpetual (free tier).
    duration_days = models.PositiveIntegerField(default=30)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscriptions_plan"
        ordering = ["price"]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    EXPIRED = "expired", "Expired"
    PAST_DUE = "past_due", "Past due"


class Subscription(BaseModel):
    """A user's subscription instance."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
        db_index=True,
    )
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)

    class Meta:
        db_table = "subscriptions_subscription"
        ordering = ["-created_at"]
        constraints = [
            # Only one active subscription per user
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="uniq_active_subscription_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.plan.slug} [{self.status}]"

    @property
    def is_active(self) -> bool:
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True


class UsageQuota(BaseModel):
    """Per-period usage counter for a subscription.

    Reset by starting a new period; never decremented mid-period. Atomic
    increments via F() expressions in services.
    """

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="quotas"
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    requests_used = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "subscriptions_usage_quota"
        ordering = ["-period_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "period_start"],
                name="uniq_quota_per_period",
            ),
        ]
        indexes = [models.Index(fields=["subscription", "period_end"])]

    @property
    def is_current(self) -> bool:
        now = timezone.now()
        return self.period_start <= now < self.period_end

    @property
    def quota_remaining(self) -> int:
        limit = self.subscription.plan.request_quota
        if limit == 0:
            return -1  # unlimited sentinel
        return max(0, limit - self.requests_used)


def default_period_window(plan: Plan, start=None) -> tuple:
    """Compute (period_start, period_end) for a plan."""
    start = start or timezone.now()
    days = plan.duration_days or 30
    return start, start + timedelta(days=days)
