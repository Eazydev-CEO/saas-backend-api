"""Authentication request/response serializers."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.validators import validate_strong_password

# Re-export the custom JWT serializer so settings.SIMPLE_JWT can find it
from .tokens import CustomTokenObtainPairSerializer  # noqa: F401


class RegistrationSerializer(serializers.Serializer):
    """Validates new user signup."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=120)

    def validate_password(self, value: str) -> str:
        validate_strong_password(value)
        return value

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=10)

    def validate_new_password(self, value: str) -> str:
        validate_strong_password(value)
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class SessionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    user_agent = serializers.CharField(read_only=True)
    ip_address = serializers.IPAddressField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    last_seen_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
