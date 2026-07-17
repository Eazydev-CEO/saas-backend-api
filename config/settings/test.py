"""Test settings: fast, deterministic, in-memory where possible.

These settings are self-sufficient: `pytest` runs on a fresh clone with nothing
but a PostgreSQL server reachable on the defaults below. Base settings require a
fully populated environment, which developers get from a .env file that is not
in the repository — so importing base alone would make the suite unrunnable for
anyone who has not set one up, and unrunnable in CI.

Every value here is a throwaway for ephemeral test databases. Real deployments
read config.settings.production, which takes all of this from the environment.
"""
from __future__ import annotations

import os
from pathlib import Path

import environ

# Load .env first, if the developer has one, so their choices (a non-default
# PostgreSQL port, say) still win. base.py reads the same file; doing it here as
# well is a no-op repeat, but it has to happen before the setdefault calls below
# or those would take precedence over the file.
_env_file = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))

# Fill in whatever is still missing. base.py requires these with no default, and
# reads them at import time, so they must be set before it is imported.
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-used-outside-tests")
os.environ.setdefault("POSTGRES_DB", "saas_db")
os.environ.setdefault("POSTGRES_USER", "saas_user")
os.environ.setdefault("POSTGRES_PASSWORD", "saas_password")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("DEFAULT_FROM_EMAIL", "test@example.com")

from .base import *  # noqa: E402,F401,F403

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
