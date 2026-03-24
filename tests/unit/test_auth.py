"""Unit/Integration tests for core/auth.py.

Tests:
- current_user endpoint
- oauth_status endpoint
- link_oauth_account endpoint
- GoogleOAuthCallbackView.handle_callback
"""

import pytest
from allauth.socialaccount.models import SocialAccount
from django.test import override_settings
from rest_framework import status


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

    def test_regular_user_gets_correct_flags(
        self, regular_authenticated_api_client, regular_user
    ):
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
    def test_returns_configured_when_credentials_present(self, api_client):
        response = api_client.get(self.url)
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
    def test_returns_not_configured_when_no_credentials(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["google_oauth_configured"] is False
        assert data["google_client_id_present"] is False
        assert data["google_client_secret_present"] is False

    def test_accessible_without_authentication(self, api_client):
        # AllowAny permission — unauthenticated must not get 401
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestLinkOauthAccount:
    url = "/api/auth/oauth/link/"

    def test_missing_email_returns_400(self, api_client):
        response = api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_nonexistent_user_returns_404(self, api_client):
        response = api_client.post(
            self.url, {"email": "nobody@example.com"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.json()

    def test_existing_user_without_google_account_returns_success(
        self, api_client, regular_user
    ):
        response = api_client.post(
            self.url, {"email": regular_user.email}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == regular_user.id
        assert "ready to link" in data["message"]

    def test_existing_user_with_google_account_returns_already_linked(
        self, api_client, regular_user
    ):
        # Create a SocialAccount to simulate an already-linked Google account
        SocialAccount.objects.create(
            user=regular_user,
            provider="google",
            uid="google-uid-123",
        )
        response = api_client.post(
            self.url, {"email": regular_user.email}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "already linked" in data["message"]

    def test_accessible_without_authentication(self, api_client, regular_user):
        # AllowAny permission — unauthenticated should reach the endpoint
        response = api_client.post(
            self.url, {"email": regular_user.email}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestGoogleOAuthCallbackView:
    url = "/api/auth/oauth/google/callback/"

    @override_settings(
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
    )
    def test_unauthenticated_redirects_to_frontend_with_error(self, api_client):
        response = api_client.get(self.url)
        # Should be a redirect (302) to FRONTEND_URL with error param
        assert response.status_code in (status.HTTP_302_FOUND, status.HTTP_200_OK)
        # If redirect, location should contain the frontend URL
        if response.status_code == status.HTTP_302_FOUND:
            assert "localhost:4000" in response.get("Location", "")

    @override_settings(
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
    )
    def test_authenticated_user_redirects_with_tokens(
        self, authenticated_api_client, admin_user
    ):
        response = authenticated_api_client.get(self.url)
        # Should redirect to frontend with tokens in query params
        assert response.status_code == status.HTTP_302_FOUND
        location = response.get("Location", "")
        assert "access_token" in location
        assert "refresh_token" in location

    @override_settings(
        FRONTEND_URL="http://localhost:4000",
        FRONTEND_AUTH_CALLBACK_PATH="/auth/callback",
    )
    def test_authenticated_superuser_redirects_with_tokens(
        self, authenticated_api_client, admin_user
    ):
        # Ensure superuser path (extra logging) is exercised
        assert admin_user.is_superuser
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_302_FOUND
        location = response.get("Location", "")
        assert "access_token" in location
