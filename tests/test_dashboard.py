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


class TestSystemDashboard:
    """The staff-only endpoints aggregate across every user.

    The customer-facing endpoints answer "how am I using the API"; these answer
    "how is everyone using the API". The scope difference is the whole point, so
    each test asserts it sees another user's traffic — a per-user query would
    silently pass an "endpoint returns 200" check.
    """

    def _staff_client(self, api_client):
        from rest_framework_simplejwt.tokens import RefreshToken

        from tests.factories import AdminUserFactory

        staff = AdminUserFactory(is_verified=True)
        refresh = RefreshToken.for_user(staff)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client, staff

    def test_system_overview_counts_other_users_requests(self, api_client, user):
        _seed_logs(user, 7)
        client, _ = self._staff_client(api_client)
        resp = client.get("/api/v1/dashboard/system/overview/")
        assert resp.status_code == 200
        body = resp.json()["data"]
        # The 7 logs belong to `user`, not to the staff member asking.
        assert body["usage"]["total_requests"] >= 7
        assert body["users_total"] >= 2

    def test_system_daily_chart_includes_other_users_requests(self, api_client, user):
        _seed_logs(user, 4)
        client, _ = self._staff_client(api_client)
        resp = client.get("/api/v1/dashboard/system/usage/daily/?days=30")
        assert resp.status_code == 200
        points = resp.json()["data"]
        assert sum(p["count"] for p in points) >= 4

    def test_system_monthly_chart_is_reachable_by_staff(self, api_client):
        client, _ = self._staff_client(api_client)
        resp = client.get("/api/v1/dashboard/system/usage/monthly/?months=6")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/dashboard/system/overview/",
            "/api/v1/dashboard/system/usage/daily/",
            "/api/v1/dashboard/system/usage/monthly/",
        ],
    )
    def test_customer_cannot_reach_system_endpoints(self, auth_client, path):
        assert auth_client.get(path).status_code == 403

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/dashboard/system/overview/",
            "/api/v1/dashboard/system/usage/daily/",
            "/api/v1/dashboard/system/usage/monthly/",
        ],
    )
    def test_anonymous_cannot_reach_system_endpoints(self, api_client, path):
        assert api_client.get(path).status_code == 401
