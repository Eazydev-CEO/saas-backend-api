"""drf-spectacular extension registering APIKeyAuthentication in the schema."""
from __future__ import annotations

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class APIKeyAuthScheme(OpenApiAuthenticationExtension):
    target_class = "apps.api_keys.authentication.APIKeyAuthentication"
    name = "APIKeyAuth"

    def get_security_definition(self, auto_schema):  # type: ignore[override]
        return {"type": "apiKey", "in": "header", "name": "X-API-Key"}
