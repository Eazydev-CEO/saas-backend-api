"""Analytics request-recording middleware.

Runs after all auth/permission middleware. Logs API requests to RequestLog
and increments the user's subscription quota. Failures are swallowed so a
broken analytics path can never break the API.
"""
from __future__ import annotations

import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse

from apps.common.utils import client_ip

logger = logging.getLogger(__name__)

API_PREFIXES = ("/api/v1/",)


class RequestAnalyticsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if not request.path.startswith(API_PREFIXES):
            return response

        # Skip schema/docs
        if request.path.startswith("/api/v1/") and request.path.endswith(("/schema/", "/docs/", "/redoc/")):
            return response

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response

        try:
            self._record(request, response, user)
        except Exception:  # pragma: no cover
            logger.exception("Failed to record analytics for %s %s", request.method, request.path)

        return response

    def _record(self, request: HttpRequest, response: HttpResponse, user) -> None:
        from apps.analytics.models import RequestLog
        from apps.api_keys.models import APIKey

        api_key = request.auth if isinstance(getattr(request, "auth", None), APIKey) else None

        RequestLog.objects.create(
            user=user,
            api_key=api_key,
            method=request.method or "",
            path=request.path[:512],
            status_code=response.status_code,
            response_ms=getattr(request, "_duration_ms", 0),
            ip_address=client_ip(request) or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
        )

        # Record against the subscription quota (don't fail the response if over —
        # the actual quota enforcement happens up-front via the throttle / a
        # service-level check; this is for accounting).
        from apps.subscriptions.services import record_request

        try:
            record_request(user)
        except Exception:
            # Quota errors during write-back are intentionally swallowed: by
            # the time we reach this middleware the response is already sent.
            pass
