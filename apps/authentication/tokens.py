"""Custom JWT serializer that embeds RBAC and subscription claims.

Downstream services can authorize from the JWT payload alone, avoiding a DB
round-trip per request.
"""
from __future__ import annotations

from typing import Any

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import AuthenticationFailed


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extends the default JWT serializer:

    - Enriches the access token with `role`, `email`, `plan`.
    - Rejects inactive or unverified accounts.
    """

    @classmethod
    def get_token(cls, user) -> RefreshToken:
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["is_verified"] = user.is_verified
        plan_slug = "free"
        active_sub = getattr(user, "subscriptions", None)
        if active_sub is not None:
            sub = active_sub.filter(status="active").select_related("plan").first()
            if sub:
                plan_slug = sub.plan.slug
        token["plan"] = plan_slug
        return token

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(attrs)
        if not self.user.is_active:
            raise AuthenticationFailed("Account is disabled.", code="account_disabled")
        if not self.user.is_verified:
            raise AuthenticationFailed(
                "Email not verified. Please verify your email before logging in.",
                code="email_not_verified",
            )
        # Include user representation alongside tokens
        from apps.users.serializers import UserSerializer

        data["user"] = UserSerializer(self.user).data
        return data
