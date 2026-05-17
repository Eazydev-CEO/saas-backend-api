"""API key serializers."""
from __future__ import annotations

from rest_framework import serializers

from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    """Safe representation — never includes the plaintext key."""

    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = APIKey
        fields = (
            "id",
            "name",
            "prefix",
            "is_active",
            "last_used_at",
            "revoked_at",
            "created_at",
        )
        read_only_fields = fields


class APIKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)


class APIKeyIssuedSerializer(serializers.Serializer):
    """Response payload when a new key is generated. `key` is shown once."""

    key = serializers.CharField()
    api_key = APIKeySerializer()
