"""Reusable validators."""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError


def validate_strong_password(password: str) -> None:
    """Enforce: 10+ chars, at least one letter, one digit, one special char."""
    if len(password) < 10:
        raise ValidationError("Password must be at least 10 characters.")
    if not re.search(r"[A-Za-z]", password):
        raise ValidationError("Password must contain a letter.")
    if not re.search(r"\d", password):
        raise ValidationError("Password must contain a digit.")
    if not re.search(r"[^\w\s]", password):
        raise ValidationError("Password must contain a special character.")
