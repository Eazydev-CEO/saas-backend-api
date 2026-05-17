"""Analytics models: append-only request log + pre-aggregated daily rollup."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class RequestLog(BaseModel):
    """Per-request audit log. Append-only. Hot table — keep narrow.

    Retention is application-policy: a periodic Celery task can purge rows
    older than N days; the daily rollup preserves history.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_logs",
    )
    api_key = models.ForeignKey(
        "api_keys.APIKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_logs",
    )
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=512)
    status_code = models.PositiveSmallIntegerField()
    response_ms = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    class Meta:
        db_table = "analytics_request_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["api_key", "created_at"]),
            models.Index(fields=["status_code"]),
        ]


class DailyUsage(BaseModel):
    """Daily rollup, one row per user per day. Read by dashboard."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_usage",
    )
    date = models.DateField(db_index=True)
    request_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    avg_response_ms = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "analytics_daily_usage"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"], name="uniq_daily_usage_per_user_per_day"
            ),
        ]
        indexes = [models.Index(fields=["user", "date"])]
