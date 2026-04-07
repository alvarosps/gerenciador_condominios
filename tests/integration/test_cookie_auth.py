"""Integration tests for HttpOnly cookie-based JWT authentication."""

import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.integration
class TestCookieLogin:
    def test_login_sets_httponly_cookies(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"]["httponly"]
        assert response.cookies["refresh_token"]["httponly"]

    def test_login_returns_user_in_body_not_tokens(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "testpass123"},
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
            {"username": "admin", "password": "testpass123"},
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
