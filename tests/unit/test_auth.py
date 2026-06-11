"""Unit/Integration tests for core/auth.py and core/adapters.py.

Tests:
- current_user endpoint
- oauth_status endpoint
- GoogleOAuthCallbackView.handle_callback (session-based, one-time code)
- exchange_oauth_code endpoint
- AdminAllowlistSocialAccountAdapter allowlist promotion
"""

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from core.adapters import AdminAllowlistSocialAccountAdapter
from core.models import OAuthExchangeCode


@pytest.mark.integration
class TestCurrentUser:
    url = "/api/auth/me/"

    def test_returns_user_data_when_authenticated(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == admin_user.email
        assert data["is_staff"] is True
        assert data["is_superuser"] is True
        assert "id" in data
        assert "first_name" in data
        assert "last_name" in data

    def test_regular_user_gets_correct_flags(self, regular_authenticated_api_client, regular_user):
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_staff"] is False
        assert data["is_superuser"] is False
        assert data["email"] == regular_user.email

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestOauthStatus:
    url = "/api/auth/oauth/status/"

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {"APP": {"client_id": "test-id", "secret": "test-secret"}}
        },
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
        SITE_ID=1,
    )
    def test_returns_configured_when_credentials_present(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["google_oauth_configured"] is True
        assert data["google_client_id_present"] is True
        assert data["google_client_secret_present"] is True
        assert "frontend_url" in data
        assert "oauth_callback_path" in data
        assert "site_id" in data

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={},
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
        SITE_ID=1,
    )
    def test_returns_not_configured_when_no_credentials(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["google_oauth_configured"] is False
        assert data["google_client_id_present"] is False
        assert data["google_client_secret_present"] is False

    def test_requires_admin(self, regular_authenticated_api_client):
        # IsAdminUser permission — non-admin must be forbidden
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestGoogleOAuthCallbackView:
    url = "/api/auth/oauth/google/callback/"

    @override_settings(
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
    )
    def test_unauthenticated_redirects_to_frontend_with_error(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_302_FOUND
        location = response.get("Location", "")
        assert "localhost:4000" in location
        assert "error=oauth_failed" in location

    @override_settings(
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
    )
    def test_authenticated_session_user_redirects_with_code(self, client, admin_user):
        # Session-authenticated request (allauth logs the user into the Django session).
        client.force_login(admin_user)
        response = client.get(self.url)
        assert response.status_code == status.HTTP_302_FOUND
        location = response.headers["Location"]
        assert location.startswith("http://localhost:4000/auth/callback?code=")
        assert "access_token" not in location
        assert "refresh_token" not in location

        codes = OAuthExchangeCode.objects.filter(user=admin_user)
        assert codes.count() == 1
        assert str(codes.get().code) in location


@pytest.mark.integration
class TestExchangeOauthCode:
    url = "/api/auth/oauth/exchange/"

    def _make_code(self, user) -> OAuthExchangeCode:
        return OAuthExchangeCode.objects.create(
            user=user,
            access_token="access-token-value",
            refresh_token="refresh-token-value",
        )

    def test_valid_unused_code_returns_200_and_deletes_row(self, api_client, admin_user):
        exchange = self._make_code(admin_user)
        response = api_client.post(self.url, {"code": str(exchange.code)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["id"] == admin_user.id
        assert data["user"]["email"] == admin_user.email
        assert data["user"]["is_staff"] is True

        assert response.cookies["access_token"].value == "access-token-value"
        assert response.cookies["refresh_token"].value == "refresh-token-value"
        assert response.cookies["is_authenticated"].value == "1"

        # The row (and its plaintext tokens) must be gone after a successful exchange.
        assert not OAuthExchangeCode.objects.filter(pk=exchange.pk).exists()

    def test_missing_code_returns_400(self, api_client):
        response = api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reused_code_after_success_returns_400(self, api_client, admin_user):
        exchange = self._make_code(admin_user)
        first = api_client.post(self.url, {"code": str(exchange.code)}, format="json")
        assert first.status_code == status.HTTP_200_OK

        # The code was deleted on success → a replay from a fresh client must fail with 400.
        replay_client = APIClient()
        second = replay_client.post(self.url, {"code": str(exchange.code)}, format="json")
        assert second.status_code == status.HTTP_400_BAD_REQUEST

    def test_already_used_code_returns_400(self, api_client, admin_user):
        exchange = self._make_code(admin_user)
        exchange.is_used = True
        exchange.save(update_fields=["is_used"])

        response = api_client.post(self.url, {"code": str(exchange.code)}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_code_returns_400(self, api_client, admin_user):
        with freeze_time("2026-01-01 12:00:00"):
            exchange = self._make_code(admin_user)
        # More than TTL_SECONDS (60s) later → expired.
        with freeze_time("2026-01-01 12:02:00"):
            response = api_client.post(self.url, {"code": str(exchange.code)}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_unused_codes_are_purged_on_exchange(self, api_client, admin_user):
        with freeze_time("2026-01-01 12:00:00"):
            stale = self._make_code(admin_user)
        with freeze_time("2026-01-01 12:02:00"):
            fresh = self._make_code(admin_user)
            response = api_client.post(self.url, {"code": str(fresh.code)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        # The exchanged code is deleted AND the abandoned expired one is purged.
        assert not OAuthExchangeCode.objects.filter(pk=fresh.pk).exists()
        assert not OAuthExchangeCode.objects.filter(pk=stale.pk).exists()

    def test_non_admin_code_returns_403_and_deletes_row(self, api_client, regular_user):
        exchange = OAuthExchangeCode.objects.create(
            user=regular_user,
            access_token="access-token-value",
            refresh_token="refresh-token-value",
        )
        response = api_client.post(self.url, {"code": str(exchange.code)}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Even on a rejected (non-admin) exchange the plaintext tokens must not linger.
        assert not OAuthExchangeCode.objects.filter(pk=exchange.pk).exists()


@pytest.mark.unit
class TestPurgeExpired:
    def test_purge_expired_classmethod_deletes_only_old(self, admin_user):
        with freeze_time("2026-01-01 12:00:00"):
            stale = OAuthExchangeCode.objects.create(
                user=admin_user, access_token="a", refresh_token="r"
            )
        with freeze_time("2026-01-01 12:02:00"):
            recent = OAuthExchangeCode.objects.create(
                user=admin_user, access_token="a", refresh_token="r"
            )
            OAuthExchangeCode.purge_expired()

        assert not OAuthExchangeCode.objects.filter(pk=stale.pk).exists()
        assert OAuthExchangeCode.objects.filter(pk=recent.pk).exists()


@pytest.mark.integration
class TestAdminAllowlistAdapter:
    @override_settings(ADMIN_GOOGLE_EMAILS=["admin@allow.com"])
    def test_allowlisted_email_is_promoted(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="allowed",
            email="admin@allow.com",
            password="x",
            is_staff=False,
            is_superuser=False,
        )
        adapter = AdminAllowlistSocialAccountAdapter()

        changed = adapter.apply_admin_allowlist(user)

        assert changed is True
        assert user.is_staff is True
        assert user.is_superuser is True

    @override_settings(ADMIN_GOOGLE_EMAILS=["admin@allow.com"])
    def test_allowlist_is_case_insensitive_and_trims(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="allowed-mixed",
            email="  Admin@Allow.COM ",
            password="x",
            is_staff=False,
            is_superuser=False,
        )
        adapter = AdminAllowlistSocialAccountAdapter()

        changed = adapter.apply_admin_allowlist(user)

        assert changed is True
        assert user.is_staff is True
        assert user.is_superuser is True

    @override_settings(ADMIN_GOOGLE_EMAILS=["admin@allow.com"])
    def test_non_allowlisted_email_is_not_promoted(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="regular",
            email="someone@other.com",
            password="x",
            is_staff=False,
            is_superuser=False,
        )
        adapter = AdminAllowlistSocialAccountAdapter()

        changed = adapter.apply_admin_allowlist(user)

        assert changed is False
        assert user.is_staff is False
        assert user.is_superuser is False

    @override_settings(ADMIN_GOOGLE_EMAILS=["admin@allow.com"])
    def test_empty_email_is_never_promoted(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="noemail",
            email="",
            password="x",
            is_staff=False,
            is_superuser=False,
        )
        adapter = AdminAllowlistSocialAccountAdapter()

        changed = adapter.apply_admin_allowlist(user)

        assert changed is False
        assert user.is_staff is False
        assert user.is_superuser is False

    @override_settings(ADMIN_GOOGLE_EMAILS=[])
    def test_never_demotes_manually_promoted_user(self, django_user_model):
        user = django_user_model.objects.create_user(
            username="manual-admin",
            email="someone@other.com",
            password="x",
            is_staff=True,
            is_superuser=True,
        )
        adapter = AdminAllowlistSocialAccountAdapter()

        changed = adapter.apply_admin_allowlist(user)

        assert changed is False
        assert user.is_staff is True
        assert user.is_superuser is True


@pytest.mark.unit
def test_oauth_exchange_code_expiry_boundary(admin_user):
    """Sanity check on the model's TTL boundary used by the exchange endpoint."""
    with freeze_time("2026-01-01 12:00:00"):
        exchange = OAuthExchangeCode.objects.create(
            user=admin_user,
            access_token="a",
            refresh_token="r",
        )
    # Backdate created_at past the TTL window.
    expired_created_at = timezone.now() - timedelta(seconds=OAuthExchangeCode.TTL_SECONDS + 5)
    OAuthExchangeCode.objects.filter(pk=exchange.pk).update(created_at=expired_created_at)
    exchange.refresh_from_db()
    assert exchange.is_valid() is False
