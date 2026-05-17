"""API key tests."""
from __future__ import annotations

import pytest

from apps.api_keys.models import APIKey
from apps.subscriptions.services import subscribe

pytestmark = pytest.mark.django_db


class TestAPIKeyCreation:
    def test_create_returns_plaintext_only_once(self, auth_client, user):
        resp = auth_client.post("/api/v1/api-keys/", {"name": "ci-bot"}, format="json")
        assert resp.status_code == 201
        body = resp.json()["data"]
        assert body["key"].startswith("sk_live_")
        list_resp = auth_client.get("/api/v1/api-keys/")
        for row in list_resp.json()["data"]:
            assert "key" not in row or row.get("key") is None

    def test_enforces_plan_limit(self, auth_client, user):
        # Free plan allows 1
        auth_client.post("/api/v1/api-keys/", {"name": "k1"}, format="json")
        resp = auth_client.post("/api/v1/api-keys/", {"name": "k2"}, format="json")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "api_key_limit_reached"

    def test_pro_plan_allows_more_keys(self, auth_client, user):
        subscribe(user=user, plan_slug="pro")  # Pro allows 10
        for i in range(3):
            r = auth_client.post("/api/v1/api-keys/", {"name": f"k{i}"}, format="json")
            assert r.status_code == 201


class TestAPIKeyAuth:
    def test_request_authenticated_via_x_api_key_header(self, api_client, user):
        from apps.api_keys.services import create_api_key

        issued = create_api_key(user=user, name="auth-test")
        api_client.credentials(HTTP_X_API_KEY=issued.plaintext)
        resp = api_client.get("/api/v1/users/me/")
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == user.email

    def test_invalid_key_rejected(self, api_client):
        api_client.credentials(HTTP_X_API_KEY="sk_live_totallyfake")
        resp = api_client.get("/api/v1/users/me/")
        assert resp.status_code == 401

    def test_revoked_key_rejected(self, api_client, user):
        from apps.api_keys.services import create_api_key, revoke_api_key

        issued = create_api_key(user=user, name="revokeme")
        revoke_api_key(user=user, key_id=issued.api_key.id)
        api_client.credentials(HTTP_X_API_KEY=issued.plaintext)
        resp = api_client.get("/api/v1/users/me/")
        assert resp.status_code == 401


class TestAPIKeyRotation:
    def test_rotation_revokes_old_and_returns_new(self, auth_client, user):
        create_resp = auth_client.post("/api/v1/api-keys/", {"name": "to-rotate"}, format="json")
        key_id = create_resp.json()["data"]["api_key"]["id"]
        rotate_resp = auth_client.post(f"/api/v1/api-keys/{key_id}/rotate/")
        assert rotate_resp.status_code == 200
        body = rotate_resp.json()["data"]
        assert body["key"].startswith("sk_live_")
        old = APIKey.objects.get(id=key_id)
        assert old.revoked_at is not None
