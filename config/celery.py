"""Celery application factory.

Tasks are auto-discovered from every Django app in INSTALLED_APPS. Beat schedules
are managed via django-celery-beat so they can be edited in the admin without
redeployment.
"""
from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("saas_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, name="debug.ping")
def ping(self) -> str:  # pragma: no cover - debugging helper
    """Smoke-test task. Returns 'pong'."""
    return "pong"
