"""Integration tests for HttpOnly cookie-based JWT authentication."""

import os
import subprocess
import sys

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.constants import TEST_PASSWORD


@pytest.mark.integration
class TestCookieLogin:
    def test_login_sets_httponly_cookies(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"]["httponly"]
        assert response.cookies["refresh_token"]["httponly"]

    def test_login_sets_readable_csrftoken_cookie(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "csrftoken" in response.cookies
        # Must be JS-readable (axios reads it to echo back as X-CSRFToken) — not HttpOnly.
        assert not response.cookies["csrftoken"]["httponly"]

    def test_production_settings_keep_csrftoken_readable(self):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "condominios_manager.settings_production",
                "REDIS_URL": "redis://localhost:6379/0",
            }
        )
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import django; django.setup(); "
                    "from django.conf import settings; "
                    "print(settings.CSRF_COOKIE_HTTPONLY)"
                ),
            ],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )

        assert result.stdout.strip() == "False"

    def test_login_returns_user_in_body_not_tokens(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" not in response.data
        assert "refresh" not in response.data
        assert "user" in response.data
        user_data = response.data["user"]
        assert user_data["email"] == "admin@test.com"
        assert user_data["is_staff"] is True

    def test_login_sets_is_authenticated_readable_cookie(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "is_authenticated" in response.cookies
        # is_authenticated is readable by JS (not httponly)
        assert not response.cookies["is_authenticated"]["httponly"]
        assert response.cookies["is_authenticated"].value == "1"


@pytest.mark.integration
class TestCookieAuthentication:
    def test_cookie_auth_grants_access(self, api_client, admin_user):
        # Set access cookie directly (avoids hitting the throttled login endpoint).
        access_token = RefreshToken.for_user(admin_user).access_token
        api_client.cookies["access_token"] = str(access_token)

        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "admin@test.com"

    def test_authorization_header_takes_priority_over_cookie(self, api_client, admin_user):
        # Cookie is present but Authorization header should win.
        access_token = RefreshToken.for_user(admin_user).access_token
        api_client.cookies["access_token"] = str(access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK

    def test_no_credentials_returns_401(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestCookieRefresh:
    def test_refresh_sets_new_access_cookie(self, api_client, admin_user):
        # Set refresh cookie directly (avoids hitting the throttled login endpoint).
        refresh = RefreshToken.for_user(admin_user)
        api_client.cookies["refresh_token"] = str(refresh)

        response = api_client.post("/api/auth/token/refresh/", format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert response.cookies["access_token"]["httponly"]

    def test_refresh_body_is_empty(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.cookies["refresh_token"] = str(refresh)

        response = api_client.post("/api/auth/token/refresh/", format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {}

    def test_refresh_with_invalid_cookie_returns_401(self, api_client):
        api_client.cookies["refresh_token"] = "invalid.token.value"
        response = api_client.post("/api/auth/token/refresh/", format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestCookieLogout:
    def test_logout_clears_cookies(self, api_client, admin_user):
        # Set auth cookies directly (avoids hitting the throttled login endpoint).
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        api_client.cookies["refresh_token"] = str(refresh)

        response = api_client.post("/api/auth/logout/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Cookies should be cleared (empty value)
        assert response.cookies["access_token"].value == ""
        assert response.cookies["refresh_token"].value == ""
        assert response.cookies["is_authenticated"].value == ""

    def test_logout_blacklists_refresh_token(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        api_client.cookies["refresh_token"] = str(refresh)

        api_client.post("/api/auth/logout/")

        # The blacklisted refresh token can no longer be used
        response = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_requires_authentication(self, api_client):
        response = api_client.post("/api/auth/logout/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestOAuthCookieFlow:
    def test_exchange_oauth_code_sets_cookies(self, api_client, admin_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        from core.models import OAuthExchangeCode

        refresh = RefreshToken.for_user(admin_user)
        exchange = OAuthExchangeCode.objects.create(
            user=admin_user,
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
        )

        response = api_client.post(
            "/api/auth/oauth/exchange/",
            {"code": str(exchange.code)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert response.cookies["access_token"]["httponly"] is True
        assert "access" not in response.data
        assert "user" in response.data

    def test_exchange_oauth_code_returns_user_info(self, api_client, admin_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        from core.models import OAuthExchangeCode

        refresh = RefreshToken.for_user(admin_user)
        exchange = OAuthExchangeCode.objects.create(
            user=admin_user,
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
        )

        response = api_client.post(
            "/api/auth/oauth/exchange/",
            {"code": str(exchange.code)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        user_data = response.data["user"]
        assert user_data["email"] == admin_user.email
        assert "is_staff" in user_data

    def test_exchange_oauth_code_invalid_code_returns_400(self, api_client):
        import uuid

        response = api_client.post(
            "/api/auth/oauth/exchange/",
            {"code": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_exchange_oauth_code_missing_code_returns_400(self, api_client):
        response = api_client.post(
            "/api/auth/oauth/exchange/",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestCookieAuthenticationCsrfEnforcement:
    """CookieJWTAuthentication.enforce_csrf — only the cookie path is protected; Bearer
    (Authorization header) stays exempt since it is never sent automatically by a browser.

    Uses a real APIClient(enforce_csrf_checks=True) because the project's default `api_client`
    fixture (plain APIClient()) disables CSRF enforcement, as DRF's test client does for every
    other test in the suite.
    """

    def _csrf_client(self) -> APIClient:
        return APIClient(enforce_csrf_checks=True)

    def test_cookie_write_without_csrf_header_returns_403(self, admin_user):
        client = self._csrf_client()
        access_token = RefreshToken.for_user(admin_user).access_token
        client.cookies["access_token"] = str(access_token)

        response = client.post("/api/auth/logout/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "CSRF" in str(response.data["detail"])

    def test_cookie_write_with_matching_csrf_header_succeeds(self, admin_user):
        client = self._csrf_client()
        login_response = client.post(
            "/api/auth/token/",
            {"username": "admin", "password": TEST_PASSWORD},
            format="json",
        )
        csrf_cookie = login_response.cookies["csrftoken"]

        response = client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=csrf_cookie.value)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_bearer_write_without_csrf_header_still_succeeds(self, admin_user):
        # Authorization header path is exempt: a browser never attaches it automatically,
        # so it cannot be forged cross-site the way a cookie can.
        client = self._csrf_client()
        refresh = RefreshToken.for_user(admin_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        client.cookies["refresh_token"] = str(refresh)

        response = client.post("/api/auth/logout/")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cookie_read_without_csrf_header_succeeds(self, admin_user):
        # Safe methods (GET) are never subject to CSRF checks.
        client = self._csrf_client()
        access_token = RefreshToken.for_user(admin_user).access_token
        client.cookies["access_token"] = str(access_token)

        response = client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_200_OK
