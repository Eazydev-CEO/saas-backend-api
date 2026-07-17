"""Dashboard response serializers — documented in OpenAPI."""
from __future__ import annotations

from rest_framework import serializers


class UsageSummarySerializer(serializers.Serializer):
    window_days = serializers.IntegerField()
    total_requests = serializers.IntegerField()
    error_requests = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_response_ms = serializers.IntegerField()


class DailyChartPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()
    errors = serializers.IntegerField()


class MonthlyChartPointSerializer(serializers.Serializer):
    month = serializers.CharField()
    count = serializers.IntegerField()
    errors = serializers.IntegerField()


class RecentRequestSerializer(serializers.Serializer):
    method = serializers.CharField()
    path = serializers.CharField()
    status_code = serializers.IntegerField()
    response_ms = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class OverviewSerializer(serializers.Serializer):
    user_summary = serializers.DictField()
    subscription = serializers.DictField(allow_null=True)
    usage = UsageSummarySerializer()
    api_keys_active = serializers.IntegerField()


class SystemOverviewSerializer(serializers.Serializer):
    """System-wide totals for the staff dashboard."""

    usage = UsageSummarySerializer()
    api_keys_active = serializers.IntegerField()
    users_total = serializers.IntegerField()
