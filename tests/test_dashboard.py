"""Dashboard endpoint tests."""
from __future__ import annotations

import pytest

from apps.analytics.models import RequestLog

pytestmark = pytest.mark.django_db


def _seed_logs(user, count: int = 5, status_code: int = 200) -> None:
    for _ in range(count):
        RequestLog.objects.create(
            user=user,
            method="GET",
            path="/api/v1/whatever/",
            status_code=status_code,
            response_ms=50,
        )


class TestDashboardOverview:
    def test_overview_includes_user_subscription_usage(self, auth_client, user):
        _seed_logs(user, 3)
        resp = auth_client.get("/api/v1/dashboard/overview/")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["user_summary"]["email"] == user.email
        assert body["subscription"]["plan"]["slug"] == "free"
        # >=3 because the dashboard GET above is also a logged API request
        assert body["usage"]["total_requests"] >= 3
        assert body["api_keys_active"] == 0


class TestUsageSummary:
    def test_summary_reports_counts_and_error_rate(self, auth_client, user):
        _seed_logs(user, 8, status_code=200)
        _seed_logs(user, 2, status_code=500)
        resp = auth_client.get("/api/v1/dashboard/usage/summary/")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 10 seeded + 1 from this GET (recorded by middleware)
        assert data["total_requests"] >= 10
        assert data["error_requests"] == 2


class TestDailyChart:
    def test_daily_chart_returns_padded_window(self, auth_client, user):
        _seed_logs(user, 4)
        resp = auth_client.get("/api/v1/dashboard/usage/daily/?days=7")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 7  # zero-filled days


class TestRecentRequests:
    def test_recent_endpoint_returns_latest(self, auth_client, user):
        _seed_logs(user, 25)
        resp = auth_client.get("/api/v1/dashboard/requests/recent/?limit=10")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 10
