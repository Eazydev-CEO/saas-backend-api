"""Centralized DRF exception handler.

Every error response from the API follows this envelope:
    {
        "error": {
            "code": "validation_error",
            "message": "Invalid input.",
            "details": {...optional field-level info...}
        }
    }
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from apps.common.exceptions import DomainError

logger = logging.getLogger(__name__)


def _normalize_details(detail: Any) -> tuple[str, dict[str, Any]]:
    """Reduce DRF's varied error detail shapes to (message, details)."""
    if isinstance(detail, dict):
        # Field errors. First field/first message becomes the headline.
        try:
            first_field, first_errs = next(iter(detail.items()))
            first_message = first_errs[0] if isinstance(first_errs, list) else str(first_errs)
            return f"{first_field}: {first_message}", {"fields": detail}
        except StopIteration:
            return "Invalid input.", {}
    if isinstance(detail, list):
        return str(detail[0]) if detail else "Invalid input.", {"errors": detail}
    return str(detail), {}


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF exception handler hook. Returns a uniform error envelope."""
    # Translate Django built-ins so DRF handles them too
    if isinstance(exc, Http404):
        exc = APIException(detail="Resource not found.", code="not_found")
        exc.status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, DjangoPermissionDenied):
        exc = APIException(detail="Permission denied.", code="permission_denied")
        exc.status_code = status.HTTP_403_FORBIDDEN

    response = drf_default_handler(exc, context)

    if response is None:
        # Unhandled exception — log and return generic 500
        logger.exception("Unhandled exception in API view", exc_info=exc)
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Prefer the per-instance code on the ErrorDetail (set when the exception
    # was raised with code="..."), falling back to the class default.
    code = getattr(exc, "default_code", "error")
    detail = getattr(exc, "detail", None)
    detail_code = getattr(detail, "code", None)
    if isinstance(detail_code, str):
        code = detail_code
    elif isinstance(detail, dict):
        # field-level errors: pick the first field's first error code
        for field_errs in detail.values():
            first = field_errs[0] if isinstance(field_errs, list) and field_errs else field_errs
            inner = getattr(first, "code", None)
            if isinstance(inner, str):
                code = inner
                break

    if isinstance(exc, APIException) and isinstance(exc.detail, (str, list, dict)):
        message, details = _normalize_details(exc.detail)
    else:
        message = str(exc)
        details = {}

    if isinstance(exc, DomainError):
        details = {**details, **exc.extra_details}

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return response
