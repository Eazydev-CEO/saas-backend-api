"""User serializers."""
from __future__ import annotations

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Public-safe user representation."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_verified",
            "is_active",
            "created_at",
            "last_login_at",
        )
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=10)

    def validate_new_password(self, value: str) -> str:
        from apps.common.validators import validate_strong_password

        validate_strong_password(value)
        return value
