"""Factory Boy factories for test data."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.api_keys.models import APIKey, compute_hash, generate_plaintext_key, split_prefix
from apps.subscriptions.models import Plan, Subscription, UsageQuota
from apps.users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = "Test"
    last_name = "User"
    role = "customer"
    is_active = True
    is_verified = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or "StrongPass!123")
        self.save()


class AdminUserFactory(UserFactory):
    role = "admin"
    is_staff = True
    is_superuser = True


class PlanFactory(DjangoModelFactory):
    class Meta:
        model = Plan
        django_get_or_create = ("slug",)

    name = "Pro"
    slug = "pro"
    price = Decimal("29.00")
    currency = "USD"
    request_quota = 100_000
    rate_limit_per_minute = 600
    max_api_keys = 10
    duration_days = 30
    features = {"api_keys": True, "advanced_analytics": True}
    is_active = True


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    plan = factory.SubFactory(PlanFactory)
    status = "active"
    started_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyAttribute(
        lambda o: timezone.now() + timedelta(days=o.plan.duration_days)
        if o.plan.duration_days
        else None
    )
    auto_renew = True

    @factory.post_generation
    def quota(self, create, extracted, **kwargs):
        if not create:
            return
        UsageQuota.objects.create(
            subscription=self,
            period_start=self.started_at,
            period_end=self.expires_at or (self.started_at + timedelta(days=365 * 50)),
        )


class APIKeyFactory(DjangoModelFactory):
    """Creates an APIKey and stashes the plaintext on `_plaintext` for tests."""

    class Meta:
        model = APIKey

    user = factory.SubFactory(UserFactory)
    name = "test-key"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        plaintext = generate_plaintext_key()
        kwargs["prefix"] = split_prefix(plaintext)
        kwargs["key_hash"] = compute_hash(plaintext)
        instance = super()._create(model_class, *args, **kwargs)
        instance._plaintext = plaintext  # type: ignore[attr-defined]
        return instance
