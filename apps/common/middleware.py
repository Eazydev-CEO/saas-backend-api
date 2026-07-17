"""Cross-cutting middleware.

`RequestIDMiddleware` attaches a UUID4 request ID to every request, exposed
both as `request.request_id` and on the response as `X-Request-ID`. Combined
with `RequestIDLogFilter`, every log line within a request carries the same
ID — essential for tracing in production.
"""
from __future__ import annotations

import contextvars
import logging
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

# Carries the current request ID so RequestIDLogFilter can reach it without
# threading the request through every call site.
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIDLogFilter(logging.Filter):
    """Inject the current request ID into log records as `request_id`."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


class RequestIDMiddleware:
    HEADER = "HTTP_X_REQUEST_ID"
    RESPONSE_HEADER = "X-Request-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(self.HEADER) or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        token = _request_id_ctx.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id_ctx.reset(token)
        response[self.RESPONSE_HEADER] = request_id
        return response


class RequestLoggingMiddleware:
    """Log each request with method, path, status, and duration."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        # Skip noisy health/static
        if not request.path.startswith(("/static/", "/health")):
            logger.info(
                "%s %s -> %s in %sms",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        # Stash duration so analytics middleware can read it
        request._duration_ms = duration_ms  # type: ignore[attr-defined]
        return response
