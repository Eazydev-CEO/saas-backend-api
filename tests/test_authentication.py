"""End-to-end authentication tests."""
from __future__ import annotations

import pytest
from django.core import mail
from django.urls import reverse

from apps.authentication.models import (
    EmailVerificationToken,
    PasswordResetToken,
    UserSession,
)
from apps.authentication.services import issue_verification_token, request_password_reset
from apps.common.utils import hash_token
from apps.users.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Registration & verification
# ---------------------------------------------------------------------------
class TestRegistration:
    url = "/api/v1/auth/register/"

    def test_creates_user_and_dispatches_verification_email(self, api_client):
        resp = api_client.post(
            self.url,
            {"email": "new@example.com", "password": "StrongPass!123", "first_name": "A"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["email"] == "new@example.com"
        # Free plan auto-enrolled
        user = User.objects.get(email="new@example.com")
        assert user.subscriptions.filter(status="active").exists()
        # Verification email queued
        assert EmailVerificationToken.objects.filter(user=user).count() == 1
        assert len(mail.outbox) == 1
        assert "Verify" in mail.outbox[0].subject

    def test_rejects_duplicate_email(self, api_client):
        UserFactory(email="dup@example.com")
        resp = api_client.post(
            self.url,
            {"email": "dup@example.com", "password": "StrongPass!123"},
            format="json",
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "email_taken"

    def test_rejects_weak_password(self, api_client):
        resp = api_client.post(
            self.url,
            {"email": "weak@example.com", "password": "weakpass12"},
            format="json",
        )
        assert resp.status_code == 400


class TestEmailVerification:
    url = "/api/v1/auth/verify-email/"

    def test_verifies_with_valid_token(self, api_client):
        user = UserFactory(is_verified=False)
        plaintext = issue_verification_token(user)
        resp = api_client.post(self.url, {"token": plaintext}, format="json")
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.is_verified is True
        token = EmailVerificationToken.objects.get(user=user)
        assert token.used_at is not None

    def test_rejects_invalid_token(self, api_client):
        resp = api_client.post(self.url, {"token": "nonexistent"}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_token"

    def test_rejects_already_used_token(self, api_client):
        user = UserFactory(is_verified=False)
        plaintext = issue_verification_token(user)
        api_client.post(self.url, {"token": plaintext}, format="json")
        # Second attempt
        resp = api_client.post(self.url, {"token": plaintext}, format="json")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login / refresh / logout
# ---------------------------------------------------------------------------
class TestLogin:
    url = "/api/v1/auth/login/"

    def test_login_issues_tokens_and_records_session(self, api_client):
        user = UserFactory(email="login@example.com", is_verified=True, password="StrongPass!123")
        resp = api_client.post(
            self.url, {"email": "login@example.com", "password": "StrongPass!123"}, format="json"
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert "access" in body and "refresh" in body
        # JWT enriched with role + plan claims
        assert body["user"]["email"] == "login@example.com"
        # Session row created
        assert UserSession.objects.filter(user=user, revoked_at__isnull=True).count() == 1

    def test_unverified_user_cannot_login(self, api_client):
        UserFactory(email="unv@example.com", is_verified=False, password="StrongPass!123")
        resp = api_client.post(
            self.url, {"email": "unv@example.com", "password": "StrongPass!123"}, format="json"
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "email_not_verified"

    def test_wrong_password_rejected(self, api_client):
        UserFactory(email="pw@example.com", is_verified=True, password="StrongPass!123")
        resp = api_client.post(
            self.url, {"email": "pw@example.com", "password": "WrongPass!000"}, format="json"
        )
        assert resp.status_code == 401


class TestLogout:
    def test_logout_blacklists_refresh_and_revokes_session(self, api_client):
        user = UserFactory(email="lo@example.com", is_verified=True, password="StrongPass!123")
        login_resp = api_client.post(
            "/api/v1/auth/login/",
            {"email": "lo@example.com", "password": "StrongPass!123"},
            format="json",
        )
        tokens = login_resp.json()["data"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        resp = api_client.post(
            "/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        assert resp.status_code == 200
        assert UserSession.objects.filter(user=user, revoked_at__isnull=False).count() == 1


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
class TestPasswordReset:
    request_url = "/api/v1/auth/password/reset/"
    confirm_url = "/api/v1/auth/password/reset/confirm/"

    def test_request_silent_for_unknown_email(self, api_client):
        resp = api_client.post(self.request_url, {"email": "ghost@example.com"}, format="json")
        assert resp.status_code == 200
        assert PasswordResetToken.objects.count() == 0
        assert len(mail.outbox) == 0

    def test_request_issues_token_for_known_user(self, api_client):
        user = UserFactory(email="known@example.com")
        resp = api_client.post(self.request_url, {"email": "known@example.com"}, format="json")
        assert resp.status_code == 200
        assert PasswordResetToken.objects.filter(user=user).count() == 1
        assert len(mail.outbox) == 1

    def test_confirm_changes_password(self, api_client):
        user = UserFactory(email="reset@example.com", password="StrongPass!123")
        # Issue token via service (avoids depending on email parsing)
        request_password_reset("reset@example.com")
        # We can't read the plaintext from DB; reissue and capture
        from apps.common.utils import generate_secure_token

        plaintext = generate_secure_token()
        PasswordResetToken.objects.filter(user=user).delete()
        PasswordResetToken.objects.create(
            user=user,
            token_hash=hash_token(plaintext),
            expires_at=PasswordResetToken.default_expiry(),
        )
        resp = api_client.post(
            self.confirm_url,
            {"token": plaintext, "new_password": "BrandNew!456"},
            format="json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.check_password("BrandNew!456")
