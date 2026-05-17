"""Shared pytest fixtures."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _seed_plans(db):
    """Every test gets the canonical plans available."""
    from django.core.management import call_command

    call_command("seed_plans")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    from apps.subscriptions.services import enroll_in_free_plan

    u = UserFactory(is_verified=True)
    enroll_in_free_plan(u)
    return u


@pytest.fixture
def auth_client(api_client, user) -> APIClient:
    """An APIClient pre-authenticated as `user` via JWT."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
