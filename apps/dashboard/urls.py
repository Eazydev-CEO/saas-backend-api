"""Dashboard routes."""
from __future__ import annotations

from django.urls import path

from .views import (
    DailyUsageChartView,
    MonthlyUsageChartView,
    OverviewView,
    RecentRequestsView,
    UsageSummaryView,
)

app_name = "dashboard"

urlpatterns = [
    path("overview/", OverviewView.as_view(), name="overview"),
    path("usage/summary/", UsageSummaryView.as_view(), name="usage-summary"),
    path("usage/daily/", DailyUsageChartView.as_view(), name="usage-daily"),
    path("usage/monthly/", MonthlyUsageChartView.as_view(), name="usage-monthly"),
    path("requests/recent/", RecentRequestsView.as_view(), name="requests-recent"),
]
