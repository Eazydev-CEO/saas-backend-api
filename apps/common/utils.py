"""General-purpose helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_secure_token(num_bytes: int = 32) -> str:
    """Generate a URL-safe random token (e.g., for email verification)."""
    return secrets.token_urlsafe(num_bytes)


def hash_token(token: str) -> str:
    """SHA-256 hash of a token for safe DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Timing-attack-resistant string equality check."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def client_ip(request) -> str:
    """Best-effort client IP extraction respecting X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
