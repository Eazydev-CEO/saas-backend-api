"""API key endpoints (JWT-authenticated; not API-key authenticated)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import success

from . import services
from .models import APIKey
from .serializers import (
    APIKeyCreateSerializer,
    APIKeyIssuedSerializer,
    APIKeySerializer,
)


class APIKeyListCreateView(APIView):
    """List your API keys (hashed; no plaintext). Create a new one."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=APIKeySerializer(many=True),
        tags=["API Keys"],
        summary="List my API keys",
    )
    def get(self, request: Request) -> Response:
        keys = APIKey.objects.filter(user=request.user).order_by("-created_at")
        return success(APIKeySerializer(keys, many=True).data)

    @extend_schema(
        request=APIKeyCreateSerializer,
        responses={201: APIKeyIssuedSerializer},
        tags=["API Keys"],
        summary="Create a new API key (plaintext shown once)",
    )
    def post(self, request: Request) -> Response:
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issued = services.create_api_key(
            user=request.user, name=serializer.validated_data["name"]
        )
        return success(
            APIKeyIssuedSerializer(
                {"key": issued.plaintext, "api_key": issued.api_key}
            ).data,
            "API key created. Save it now — it will not be shown again.",
            status=status.HTTP_201_CREATED,
        )


class APIKeyRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=APIKeySerializer,
        tags=["API Keys"],
        summary="Revoke an API key",
    )
    def post(self, request: Request, key_id) -> Response:
        key = services.revoke_api_key(user=request.user, key_id=key_id)
        return success(APIKeySerializer(key).data, "API key revoked.")


class APIKeyRotateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: APIKeyIssuedSerializer},
        tags=["API Keys"],
        summary="Rotate an API key (revoke + reissue)",
    )
    def post(self, request: Request, key_id) -> Response:
        issued = services.rotate_api_key(user=request.user, key_id=key_id)
        return success(
            APIKeyIssuedSerializer(
                {"key": issued.plaintext, "api_key": issued.api_key}
            ).data,
            "API key rotated.",
        )
