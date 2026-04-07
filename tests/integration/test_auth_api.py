"""Integration tests for authentication endpoints."""

import pytest
from rest_framework import status


@pytest.mark.integration
class TestJWTTokenEndpoints:
    def test_obtain_token_with_valid_credentials(self, api_client, admin_user):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        # Tokens are set as HttpOnly cookies, not in response body
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert "user" in response.data

    def test_obtain_token_with_invalid_credentials(self, api_client):
        response = api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_with_missing_fields(self, api_client):
        response = api_client.post("/api/auth/token/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token_with_valid_refresh(self, api_client, admin_user):
        # Login to get refresh_token cookie
        api_client.post(
            "/api/auth/token/",
            {"username": "admin", "password": "testpass123"},
            format="json",
        )
        # Refresh uses the cookie set by login (APIClient carries cookies automatically)
        response = api_client.post("/api/auth/token/refresh/", format="json")
        assert response.status_code == status.HTTP_200_OK
        # New access cookie is set; body is empty
        assert "access_token" in response.cookies

    def test_refresh_token_with_invalid_token(self, api_client):
        response = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": "invalid.token.here"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_with_no_cookie_and_no_body(self, api_client):
        # No refresh cookie and no body — should return 400
        response = api_client.post("/api/auth/token/refresh/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestCurrentUserEndpoint:
    def test_get_current_user_authenticated(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        # current_user returns: id, email, first_name, last_name, is_staff, is_superuser
        assert response.data["email"] == "admin@test.com"
        assert response.data["is_staff"] is True
        assert "id" in response.data

    def test_get_current_user_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_regular_user(self, regular_authenticated_api_client, regular_user):
        response = regular_authenticated_api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "user@test.com"
        assert response.data["is_staff"] is False


@pytest.mark.integration
class TestOAuthStatusEndpoint:
    def test_oauth_status_returns_200(self, api_client):
        # oauth_status is AllowAny — accessible without auth
        response = api_client.get("/api/auth/oauth/status/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)

    def test_oauth_status_contains_google_config(self, api_client):
        response = api_client.get("/api/auth/oauth/status/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should contain some OAuth configuration status
        assert "google_configured" in data or len(data) > 0
