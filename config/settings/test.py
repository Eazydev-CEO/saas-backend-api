"""Test settings: fast, deterministic, in-memory where possible."""
from __future__ import annotations

from .base import *  # noqa: F401,F403

DEBUG = False

# Faster password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Run Celery tasks eagerly
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# In-memory email backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable throttling noise in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()  # type: ignore[index]  # noqa: F405

# Use a dummy cache (still works with our IGNORE_EXCEPTIONS pattern)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
