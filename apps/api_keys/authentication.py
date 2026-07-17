"""DRF authentication class for API key auth.

Accepts the key via either:
  - `X-API-Key: sk_live_xxx`
  - `Authorization: Api-Key sk_live_xxx`
"""
from __future__ import annotations

import logging

from rest_framework import authentication, exceptions
from rest_framework.request import Request

from apps.common.utils import constant_time_compare

from .models import APIKey, compute_hash, split_prefix

logger = logging.getLogger(__name__)


class APIKeyAuthentication(authentication.BaseAuthentication):
    """Authenticates a request via an API key header."""

    keyword = "Api-Key"
    header_name = "HTTP_X_API_KEY"

    def authenticate(self, request: Request) -> tuple | None:
        plaintext = self._extract_key(request)
        if not plaintext:
            return None  # Fall through to other auth classes

        prefix = split_prefix(plaintext)
        provided_hash = compute_hash(plaintext)

        # Narrow candidates by indexed prefix, then compare hashes constant-time
        candidates = APIKey.objects.select_related("user").filter(
            prefix=prefix, revoked_at__isnull=True
        )
        for candidate in candidates:
            if constant_time_compare(candidate.key_hash, provided_hash):
                if not candidate.user.is_active:
                    raise exceptions.AuthenticationFailed("User account is disabled.")
                try:
                    candidate.mark_used()
                except Exception:  # pragma: no cover
                    logger.exception("Failed to update last_used_at for APIKey %s", candidate.id)
                # The 2nd tuple element is `auth` — surfaced as `request.auth`.
                # Downstream code can detect API-key auth via isinstance(request.auth, APIKey).
                return (candidate.user, candidate)

        raise exceptions.AuthenticationFailed("Invalid API key.")

    def authenticate_header(self, request: Request) -> str:
        return self.keyword

    def _extract_key(self, request: Request) -> str | None:
        # X-API-Key header
        value = request.META.get(self.header_name)
        if value:
            return value.strip()

        # Authorization: Api-Key xxx
        auth = authentication.get_authorization_header(request).split()
        if len(auth) == 2 and auth[0].decode("ascii").lower() == self.keyword.lower():
            try:
                return auth[1].decode("ascii")
            except UnicodeDecodeError:
                # `from None`: the decode error quotes the raw bytes the client
                # sent, which should not surface in an auth failure response.
                raise exceptions.AuthenticationFailed("Invalid API key header.") from None
        return None
