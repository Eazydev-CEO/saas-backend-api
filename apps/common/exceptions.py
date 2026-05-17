"""Domain-level exception hierarchy.

Service-layer code raises these; the DRF exception handler translates them to
HTTP responses with a consistent JSON envelope. Keeps business logic free of
HTTP concerns.
"""
from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException


class DomainError(APIException):
    """Base class for all domain/business-rule errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A domain error occurred."
    default_code = "domain_error"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail=message or self.default_detail, code=code or self.default_code)
        self.extra_details = details or {}


class ValidationError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input."
    default_code = "validation_error"


class AuthenticationFailed(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = "authentication_failed"


class PermissionDenied(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied."
    default_code = "permission_denied"


class NotFound(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "not_found"


class Conflict(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict with current resource state."
    default_code = "conflict"


class QuotaExceeded(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Subscription quota exceeded."
    default_code = "quota_exceeded"


class ServiceUnavailable(DomainError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"
