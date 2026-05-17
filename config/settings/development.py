"""Development settings."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE  # noqa: F401

DEBUG = True

# Optional debug toolbar (only if package is installed and DEBUG)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Make logging chattier in dev
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # type: ignore[index]  # noqa: F405
