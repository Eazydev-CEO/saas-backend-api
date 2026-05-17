"""Subscription background tasks."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="subscriptions.expire_due_subscriptions")
def expire_due_subscriptions_task() -> int:
    """Nightly sweep: expire subscriptions whose end date has passed."""
    from .services import expire_due_subscriptions

    count = expire_due_subscriptions()
    logger.info("Expired %s subscription(s)", count)
    return count
