"""Response envelope helpers for consistent success payloads."""
from __future__ import annotations

from typing import Any

from rest_framework import status as http_status
from rest_framework.response import Response


def success(data: Any = None, message: str = "", status: int = http_status.HTTP_200_OK) -> Response:
    """Wrap a successful response in a consistent envelope.

    Example:
        return success({"id": ...}, "Created", status=201)
    """
    payload: dict[str, Any] = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status)
