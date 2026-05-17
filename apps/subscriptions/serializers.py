"""Subscription serializers."""
from __future__ import annotations

from rest_framework import serializers

from .models import Plan, Subscription, UsageQuota


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "price",
            "currency",
            "request_quota",
            "rate_limit_per_minute",
            "max_api_keys",
            "duration_days",
            "features",
            "is_active",
        )
        read_only_fields = fields


class SubscribeSerializer(serializers.Serializer):
    plan_slug = serializers.SlugField()


class UsageQuotaSerializer(serializers.ModelSerializer):
    quota_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = UsageQuota
        fields = (
            "id",
            "period_start",
            "period_end",
            "requests_used",
            "quota_remaining",
        )
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    current_quota = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "status",
            "started_at",
            "expires_at",
            "canceled_at",
            "auto_renew",
            "current_quota",
            "created_at",
        )
        read_only_fields = fields

    def get_current_quota(self, obj: Subscription) -> dict | None:
        from .selectors import get_current_quota

        q = get_current_quota(obj)
        return UsageQuotaSerializer(q).data if q else None
