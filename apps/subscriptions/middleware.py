"""Attaches subscription context to each authenticated request.

Runs after AuthenticationMiddleware and before permission checks. The result
is cached per-request so downstream throttles, permissions, and analytics
don't each re-query.
"""
from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from .selectors import get_active_subscription


class SubscriptionContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.subscription = None  # type: ignore[attr-defined]
        request.subscription_plan_slug = "free"  # type: ignore[attr-defined]

        # Authentication runs lazily in DRF, so request.user here is the
        # Django AnonymousUser for unauthenticated requests; we tolerate that.
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            sub = get_active_subscription(user)
            if sub:
                request.subscription = sub  # type: ignore[attr-defined]
                request.subscription_plan_slug = sub.plan.slug  # type: ignore[attr-defined]

        return self.get_response(request)
