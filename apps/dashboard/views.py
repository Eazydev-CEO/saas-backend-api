"""Dashboard endpoints."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.selectors import (
    daily_chart,
    monthly_chart,
    recent_requests,
    usage_summary,
)
from apps.api_keys.models import APIKey
from apps.common.responses import success
from apps.subscriptions.selectors import get_active_subscription
from apps.subscriptions.serializers import SubscriptionSerializer
from apps.users.serializers import UserSerializer

from .serializers import (
    DailyChartPointSerializer,
    MonthlyChartPointSerializer,
    OverviewSerializer,
    RecentRequestSerializer,
    UsageSummarySerializer,
)


def _parse_int_param(value, default: int, min_v: int, max_v: int) -> int:
    try:
        n = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, n))


class OverviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=OverviewSerializer,
        tags=["Dashboard"],
        summary="Single-call overview: user, subscription, usage, key count",
    )
    def get(self, request: Request) -> Response:
        user = request.user
        sub = get_active_subscription(user)
        data = {
            "user_summary": UserSerializer(user).data,
            "subscription": SubscriptionSerializer(sub).data if sub else None,
            "usage": usage_summary(user, days=30),
            "api_keys_active": APIKey.objects.filter(
                user=user, revoked_at__isnull=True
            ).count(),
        }
        return success(data)


class UsageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="Window in days (1–90)")],
        responses=UsageSummarySerializer,
        tags=["Dashboard"],
        summary="Usage summary card",
    )
    def get(self, request: Request) -> Response:
        days = _parse_int_param(request.query_params.get("days"), 30, 1, 90)
        return success(usage_summary(request.user, days=days))


class DailyUsageChartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="Window in days (1–90)")],
        responses=DailyChartPointSerializer(many=True),
        tags=["Dashboard"],
        summary="Daily request counts (for line chart)",
    )
    def get(self, request: Request) -> Response:
        days = _parse_int_param(request.query_params.get("days"), 30, 1, 90)
        return success(daily_chart(request.user, days=days))


class MonthlyUsageChartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("months", int, description="Window in months (1–12)")],
        responses=MonthlyChartPointSerializer(many=True),
        tags=["Dashboard"],
        summary="Monthly request totals (for bar chart)",
    )
    def get(self, request: Request) -> Response:
        months = _parse_int_param(request.query_params.get("months"), 6, 1, 12)
        return success(monthly_chart(request.user, months=months))


class RecentRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("limit", int, description="Up to 100")],
        responses=RecentRequestSerializer(many=True),
        tags=["Dashboard"],
        summary="Most recent API requests",
    )
    def get(self, request: Request) -> Response:
        limit = _parse_int_param(request.query_params.get("limit"), 20, 1, 100)
        return success(recent_requests(request.user, limit=limit))
