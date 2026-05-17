"""Analytics background jobs."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="analytics.rollup_daily_usage")
def rollup_daily_usage_task(target_date_iso: str | None = None) -> int:
    """Compute DailyUsage rows for yesterday (or a specific date)."""
    from datetime import date as date_cls

    from .selectors import rollup_daily_usage

    target = date_cls.fromisoformat(target_date_iso) if target_date_iso else None
    n = rollup_daily_usage(target)
    logger.info("Rolled up DailyUsage for %s user(s)", n)
    return n
