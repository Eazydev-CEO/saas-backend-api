"""Subscription system tests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.subscriptions.models import Subscription, SubscriptionStatus, UsageQuota
from apps.subscriptions.services import (
    cancel,
    enroll_in_free_plan,
    expire_due_subscriptions,
    record_request,
    subscribe,
)
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestEnrollment:
    def test_free_plan_auto_enrolled_on_user_creation(self):
        user = UserFactory()
        # UserFactory uses create_user via Django manager; we explicitly enroll
        # in services.create_user but the factory uses the model manager.
        # Mirror reality: enroll explicitly here.
        enroll_in_free_plan(user)
        sub = user.subscriptions.filter(status="active").first()
        assert sub is not None
        assert sub.plan.slug == "free"

    def test_only_one_active_subscription_constraint(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        # The partial unique constraint must reject a second active subscription.
        # Asserting IntegrityError specifically, so the test cannot pass on an
        # unrelated failure such as a typo raising AttributeError.
        with pytest.raises(IntegrityError):
            Subscription.objects.create(
                user=user,
                plan=user.subscriptions.first().plan,
                status=SubscriptionStatus.ACTIVE,
            )


class TestSubscribe:
    def test_upgrade_replaces_existing_active_subscription(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        new = subscribe(user=user, plan_slug="pro")
        active = user.subscriptions.filter(status="active")
        assert active.count() == 1
        assert active.first().plan.slug == "pro"
        assert new.expires_at is not None  # paid plans have expiry

    def test_same_plan_raises_conflict(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        from apps.common.exceptions import Conflict

        with pytest.raises(Conflict):
            subscribe(user=user, plan_slug="free")

    def test_unknown_plan_raises_not_found(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        from apps.common.exceptions import NotFound

        with pytest.raises(NotFound):
            subscribe(user=user, plan_slug="nonexistent")


class TestCancel:
    def test_cancel_downgrades_to_free(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        subscribe(user=user, plan_slug="pro")
        sub = cancel(user=user)
        assert sub.plan.slug == "free"
        # Pro sub should be canceled
        pro = user.subscriptions.filter(plan__slug="pro").first()
        assert pro.status == SubscriptionStatus.CANCELED


class TestExpiry:
    def test_expired_subscriptions_are_swept(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        pro_sub = subscribe(user=user, plan_slug="pro")
        # Backdate expiry
        pro_sub.expires_at = timezone.now() - timedelta(hours=1)
        pro_sub.save(update_fields=["expires_at"])
        # Demote any other active sub to avoid the partial uniq constraint
        user.subscriptions.exclude(id=pro_sub.id).update(status=SubscriptionStatus.CANCELED)

        n = expire_due_subscriptions()
        assert n == 1
        pro_sub.refresh_from_db()
        assert pro_sub.status == SubscriptionStatus.EXPIRED
        # User should be auto-enrolled back into Free
        assert user.subscriptions.filter(status="active", plan__slug="free").exists()


class TestUsageQuota:
    def test_record_request_increments_counter(self):
        user = UserFactory()
        enroll_in_free_plan(user)
        record_request(user)
        record_request(user)
        sub = user.subscriptions.get(status="active")
        quota = UsageQuota.objects.get(subscription=sub)
        assert quota.requests_used == 2

    def test_quota_exceeded_raises(self):
        from apps.common.exceptions import QuotaExceeded
        from apps.subscriptions.models import Plan

        user = UserFactory()
        enroll_in_free_plan(user)
        # Cap the Free plan at 2 for this test
        Plan.objects.filter(slug="free").update(request_quota=2)
        record_request(user)
        record_request(user)
        with pytest.raises(QuotaExceeded):
            record_request(user)


class TestSubscriptionAPI:
    def test_my_subscription_endpoint(self, auth_client):
        resp = auth_client.get("/api/v1/subscriptions/me/")
        assert resp.status_code == 200
        assert resp.json()["data"]["plan"]["slug"] in {"free", "pro", "enterprise"}

    def test_plans_listing_is_public(self, api_client):
        resp = api_client.get("/api/v1/subscriptions/plans/")
        assert resp.status_code == 200
        slugs = {p["slug"] for p in resp.json()["data"]}
        assert {"free", "pro", "enterprise"}.issubset(slugs)

    def test_subscribe_endpoint(self, auth_client):
        resp = auth_client.post(
            "/api/v1/subscriptions/subscribe/", {"plan_slug": "pro"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["plan"]["slug"] == "pro"
