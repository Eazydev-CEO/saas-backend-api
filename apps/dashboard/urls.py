"""Dashboard routes."""
from __future__ import annotations

from django.urls import path

from .views import (
    DailyUsageChartView,
    MonthlyUsageChartView,
    OverviewView,
    RecentRequestsView,
    SystemDailyChartView,
    SystemMonthlyChartView,
    SystemOverviewView,
    UsageSummaryView,
)

app_name = "dashboard"

urlpatterns = [
    # Scoped to the requesting user.
    path("overview/", OverviewView.as_view(), name="overview"),
    path("usage/summary/", UsageSummaryView.as_view(), name="usage-summary"),
    path("usage/daily/", DailyUsageChartView.as_view(), name="usage-daily"),
    path("usage/monthly/", MonthlyUsageChartView.as_view(), name="usage-monthly"),
    path("requests/recent/", RecentRequestsView.as_view(), name="requests-recent"),
    # System-wide, staff only.
    path("system/overview/", SystemOverviewView.as_view(), name="system-overview"),
    path("system/usage/daily/", SystemDailyChartView.as_view(), name="system-usage-daily"),
    path("system/usage/monthly/", SystemMonthlyChartView.as_view(), name="system-usage-monthly"),
]
