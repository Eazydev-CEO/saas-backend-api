"""User-facing endpoints: me, profile update, change password, admin list."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import DefaultPagination
from apps.common.permissions import IsStaffOrAbove
from apps.common.responses import success

from . import services
from .models import User
from .serializers import (
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
    UserSerializer,
)


class MeView(APIView):
    """Return / update the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer, tags=["Users"], summary="Get current user")
    def get(self, request: Request) -> Response:
        return success(UserSerializer(request.user).data)

    @extend_schema(
        request=ProfileUpdateSerializer,
        responses=UserSerializer,
        tags=["Users"],
        summary="Update current user's profile",
    )
    def patch(self, request: Request) -> Response:
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.update_profile(request.user, **serializer.validated_data)
        return success(UserSerializer(user).data, "Profile updated.")


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed.")},
        tags=["Users"],
        summary="Change password",
    )
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(
            request.user,
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
        )
        return success(message="Password changed.")


class UserListView(APIView):
    """Admin/staff: list users."""

    permission_classes = [IsStaffOrAbove]
    pagination_class = DefaultPagination

    @extend_schema(responses=UserSerializer(many=True), tags=["Users"], summary="List users (admin)")
    def get(self, request: Request) -> Response:
        qs = User.objects.all().order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
