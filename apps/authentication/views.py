"""Authentication API views.

Endpoints:
    POST /auth/register/              - Sign up
    POST /auth/login/                 - Obtain JWT pair
    POST /auth/token/refresh/         - Refresh JWT
    POST /auth/logout/                - Blacklist refresh + revoke session
    POST /auth/verify-email/          - Confirm email
    POST /auth/resend-verification/   - Resend verification email
    POST /auth/password/reset/        - Request reset
    POST /auth/password/reset/confirm/- Confirm reset
    GET  /auth/sessions/              - List my active sessions
    POST /auth/sessions/{id}/revoke/  - Revoke a session
"""
from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.common.responses import success
from apps.common.utils import client_ip
from apps.users.serializers import UserSerializer

from . import services
from .models import UserSession
from .serializers import (
    EmailVerificationSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
    ResendVerificationSerializer,
    SessionSerializer,
)
from .tokens import CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=RegistrationSerializer,
        responses={201: UserSerializer},
        tags=["Authentication"],
        summary="Register a new user",
    )
    def post(self, request: Request) -> Response:
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        return success(
            UserSerializer(user).data,
            "Account created. Check your email to verify.",
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Custom token-obtain view that records a session row."""

    permission_classes = [AllowAny]
    # Keep JWTAuthentication in the list so DRF can produce a proper 401
    # (WWW-Authenticate header) when AuthenticationFailed is raised.

    @extend_schema(
        request=CustomTokenObtainPairSerializer,
        responses={
            200: OpenApiResponse(description="JWT tokens issued."),
        },
        tags=["Authentication"],
        summary="Login (obtain JWT pair)",
    )
    def post(self, request: Request) -> Response:
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = serializer.user
        refresh = RefreshToken(data["refresh"])
        services.record_session(
            user=user,
            refresh_token=refresh,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_address=client_ip(request),
        )
        user.mark_logged_in()
        return success(data, "Login successful.")


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(tags=["Authentication"], summary="Refresh JWT access token")
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: OpenApiResponse(description="Logged out.")},
        tags=["Authentication"],
        summary="Logout (blacklist refresh token)",
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.logout(serializer.validated_data["refresh"])
        return success(message="Logged out.")


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={200: UserSerializer},
        tags=["Authentication"],
        summary="Verify email address",
    )
    def post(self, request: Request) -> Response:
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.verify_email(serializer.validated_data["token"])
        return success(UserSerializer(user).data, "Email verified.")


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=ResendVerificationSerializer,
        responses={200: OpenApiResponse(description="Email queued if account exists.")},
        tags=["Authentication"],
        summary="Resend verification email",
    )
    def post(self, request: Request) -> Response:
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.resend_verification(serializer.validated_data["email"])
        return success(message="If the email is registered and unverified, a new link has been sent.")


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Email queued if account exists.")},
        tags=["Authentication"],
        summary="Request a password reset email",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return success(message="If the email is registered, a reset link has been sent.")


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password updated.")},
        tags=["Authentication"],
        summary="Confirm password reset",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_password_reset(**serializer.validated_data)
        return success(message="Password updated.")


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=SessionSerializer(many=True),
        tags=["Authentication"],
        summary="List my active sessions",
    )
    def get(self, request: Request) -> Response:
        qs = UserSession.objects.filter(user=request.user).order_by("-created_at")
        data = SessionSerializer(qs, many=True).data
        # `is_active` is derived; emit it explicitly
        for row, session in zip(data, qs):
            row["is_active"] = session.is_active
        return success(data)


class SessionRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="Session revoked.")},
        tags=["Authentication"],
        summary="Revoke a session",
    )
    def post(self, request: Request, session_id) -> Response:
        services.revoke_session(user=request.user, session_id=session_id)
        return success(message="Session revoked.")
