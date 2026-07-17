"""Aggregation queries powering the dashboard.

Queries are scoped to a single user, or system-wide when `user` is None (used by
the staff-only endpoints). All use indexed columns and are pre-shaped for chart
consumption.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import DailyUsage, RequestLog


def _scope(qs, user):
    """Limit a queryset to one user, or leave it system-wide when user is None.

    This cannot be expressed as `filter(user=user)`: passing None there means
    "user IS NULL" — anonymous traffic only — rather than "every user". The
    distinction has to be explicit.
    """
    return qs if user is None else qs.filter(user=user)


def usage_summary(user, days: int = 30) -> dict[str, Any]:
    """High-level summary card data. `user=None` aggregates across all users."""
    since = timezone.now() - timedelta(days=days)
    qs = _scope(RequestLog.objects.filter(created_at__gte=since), user)
    aggregates = qs.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(status_code__gte=400)),
        avg_ms=Avg("response_ms"),
    )
    total = aggregates["total"] or 0
    errors = aggregates["errors"] or 0
    return {
        "window_days": days,
        "total_requests": total,
        "error_requests": errors,
        "success_rate": round(((total - errors) / total) * 100, 2) if total else 100.0,
        "avg_response_ms": int(aggregates["avg_ms"] or 0),
    }


def daily_chart(user, days: int = 30) -> list[dict[str, Any]]:
    """Daily request counts for chart consumption.

    Reads from `RequestLog` for the trailing window. For longer windows or
    higher scale, switch to `DailyUsage`. `user=None` aggregates across all users.
    """
    today = timezone.now().date()
    start = today - timedelta(days=days - 1)
    qs = (
        _scope(RequestLog.objects.filter(created_at__date__gte=start), user)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            count=Count("id"),
            errors=Count("id", filter=Q(status_code__gte=400)),
        )
        .order_by("day")
    )
    by_day = {row["day"]: row for row in qs}

    # Fill missing days with zeros for clean charting
    out: list[dict[str, Any]] = []
    for i in range(days):
        day = start + timedelta(days=i)
        row = by_day.get(day, {"count": 0, "errors": 0})
        out.append(
            {
                "date": day.isoformat(),
                "count": row["count"],
                "errors": row["errors"],
            }
        )
    return out


def monthly_chart(user, months: int = 6) -> list[dict[str, Any]]:
    """Monthly aggregates from the DailyUsage rollup.

    `user=None` aggregates across all users.
    """
    today = timezone.now().date().replace(day=1)
    earliest = (today.replace(day=1) - timedelta(days=31 * (months - 1))).replace(day=1)
    qs = _scope(DailyUsage.objects.filter(date__gte=earliest), user)
    buckets: dict[str, dict[str, int]] = {}
    for row in qs:
        key = row.date.strftime("%Y-%m")
        b = buckets.setdefault(key, {"count": 0, "errors": 0})
        b["count"] += row.request_count
        b["errors"] += row.error_count
    return [{"month": k, **v} for k, v in sorted(buckets.items())]


def recent_requests(user, limit: int = 20) -> list[dict[str, Any]]:
    qs = RequestLog.objects.filter(user=user).order_by("-created_at")[:limit]
    return [
        {
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "response_ms": r.response_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in qs
    ]


# ---------------------------------------------------------------------------
# Rollup helper used by Celery task
# ---------------------------------------------------------------------------
def rollup_daily_usage(target_date: date | None = None) -> int:
    """Compute DailyUsage rows for `target_date` (default: yesterday).

    Idempotent: uses update_or_create keyed on (user, date).
    """
    target_date = target_date or (timezone.now().date() - timedelta(days=1))
    qs = (
        RequestLog.objects.filter(created_at__date=target_date, user__isnull=False)
        .values("user_id")
        .annotate(
            request_count=Count("id"),
            error_count=Count("id", filter=Q(status_code__gte=400)),
            avg_ms=Avg("response_ms"),
        )
    )
    count = 0
    for row in qs:
        DailyUsage.objects.update_or_create(
            user_id=row["user_id"],
            date=target_date,
            defaults={
                "request_count": row["request_count"],
                "error_count": row["error_count"],
                "avg_response_ms": int(row["avg_ms"] or 0),
            },
        )
        count += 1
    return count
