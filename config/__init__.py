"""Project package. Eagerly imports the Celery app so @shared_task works at startup."""
from .celery import app as celery_app

__all__ = ("celery_app",)
