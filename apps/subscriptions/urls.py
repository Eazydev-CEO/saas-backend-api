"""Subscription routes."""
from __future__ import annotations

from django.urls import path

from .views import (
    CancelSubscriptionView,
    MySubscriptionView,
    PlanListView,
    SubscribeView,
)

app_name = "subscriptions"

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plans"),
    path("me/", MySubscriptionView.as_view(), name="me"),
    path("subscribe/", SubscribeView.as_view(), name="subscribe"),
    path("cancel/", CancelSubscriptionView.as_view(), name="cancel"),
]
