"""Idempotently seed the canonical Free / Pro / Enterprise plans.

Run automatically on container startup. Safe to invoke any number of times.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.subscriptions.models import Plan, PlanSlug


PLANS = [
    {
        "name": "Free",
        "slug": PlanSlug.FREE,
        "description": "Get started for free. Limited quota, basic features.",
        "price": Decimal("0.00"),
        "request_quota": 1_000,
        "rate_limit_per_minute": 60,
        "max_api_keys": 1,
        "duration_days": 0,  # perpetual
        "features": {"api_keys": True, "advanced_analytics": False},
    },
    {
        "name": "Pro",
        "slug": PlanSlug.PRO,
        "description": "For growing teams. Higher quota, more keys, full analytics.",
        "price": Decimal("29.00"),
        "request_quota": 100_000,
        "rate_limit_per_minute": 600,
        "max_api_keys": 10,
        "duration_days": 30,
        "features": {"api_keys": True, "advanced_analytics": True},
    },
    {
        "name": "Enterprise",
        "slug": PlanSlug.ENTERPRISE,
        "description": "Unlimited usage and dedicated support.",
        "price": Decimal("299.00"),
        "request_quota": 0,  # unlimited
        "rate_limit_per_minute": 6_000,
        "max_api_keys": 100,
        "duration_days": 30,
        "features": {
            "api_keys": True,
            "advanced_analytics": True,
            "sso": True,
            "priority_support": True,
        },
    },
]


class Command(BaseCommand):
    help = "Seed canonical subscription plans (idempotent)."

    def handle(self, *args, **options) -> None:
        created = updated = 0
        for spec in PLANS:
            plan, was_created = Plan.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "price": spec["price"],
                    "currency": "USD",
                    "request_quota": spec["request_quota"],
                    "rate_limit_per_minute": spec["rate_limit_per_minute"],
                    "max_api_keys": spec["max_api_keys"],
                    "duration_days": spec["duration_days"],
                    "features": spec["features"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Plans seeded: {created} created, {updated} updated.")
        )
