"""
Unit tests for OAuth authentication views.

Tests Google OAuth callback handling, token generation, and OAuth status endpoints.
"""

from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APIClient

import pytest

from core.auth import (
    GoogleOAuthCallbackView,
    get_tokens_for_user,
    google_oauth_callback,
    link_oauth_account,
    oauth_status,
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")


@pytest.fixture
def superuser(db):
    """Create a superuser."""
    return User.objects.create_superuser(username="admin", email="admin@example.com", password="admin123")


@pytest.fixture
def request_factory():
    """Create request factory."""
    return RequestFactory()


@pytest.mark.django_db
class TestGetTokensForUser:
    """Test get_tokens_for_user function."""

    def test_generates_refresh_and_access_tokens(self, test_user):
        """Test that JWT tokens are generated for a user."""
        tokens = get_tokens_for_user(test_user)

        assert "refresh" in tokens
        assert "access" in tokens
        assert isinstance(tokens["refresh"], str)
        assert isinstance(tokens["access"], str)
        assert len(tokens["refresh"]) > 0
        assert len(tokens["access"]) > 0

    def test_tokens_are_unique_per_user(self, test_user, superuser):
        """Test that different users get different tokens."""
        tokens1 = get_tokens_for_user(test_user)
        tokens2 = get_tokens_for_user(superuser)

        assert tokens1["access"] != tokens2["access"]
        assert tokens1["refresh"] != tokens2["refresh"]


@pytest.mark.django_db
class TestGoogleOAuthCallbackView:
    """Test GoogleOAuthCallbackView.handle_callback method."""

    def test_callback_with_unauthenticated_user(self, request_factory):
        """Test callback when user is not authenticated."""
        request = request_factory.get("/callback/")
        request.user = Mock()
        request.user.is_authenticated = False

        response = GoogleOAuthCallbackView.handle_callback(request)

        assert response.status_code == 302  # Redirect
        assert "error=oauth_failed" in response.url
        # URL encoding converts spaces to +
        assert "message=Authentication" in response.url

    def test_callback_with_authenticated_user(self, request_factory, test_user):
        """Test successful callback with authenticated user."""
        request = request_factory.get("/callback/")
        request.user = test_user

        response = GoogleOAuthCallbackView.handle_callback(request)

        assert response.status_code == 302  # Redirect
        assert "access_token=" in response.url
        assert "refresh_token=" in response.url
        assert f"user_id={test_user.id}" in response.url
        assert f"username={test_user.username}" in response.url
        # Email is URL-encoded (@ becomes %40)
        assert "email=" in response.url

    def test_callback_with_superuser(self, request_factory, superuser):
        """Test callback with superuser logs appropriately."""
        request = request_factory.get("/callback/")
        request.user = superuser

        response = GoogleOAuthCallbackView.handle_callback(request)

        assert response.status_code == 302
        assert "access_token=" in response.url
        assert "is_superuser=True" in response.url

    def test_callback_includes_user_info(self, request_factory, test_user):
        """Test that callback includes complete user info in redirect."""
        request = request_factory.get("/callback/")
        request.user = test_user

        response = GoogleOAuthCallbackView.handle_callback(request)

        url = response.url
        assert f"user_id={test_user.id}" in url
        assert f"username={test_user.username}" in url
        assert "email=" in url  # URL-encoded
        assert "is_staff=" in url
        assert "is_superuser=" in url

    @patch("core.auth.get_tokens_for_user")
    def test_callback_error_handling(self, mock_get_tokens, request_factory, test_user):
        """Test error handling when token generation fails."""
        mock_get_tokens.side_effect = Exception("Token generation error")

        request = request_factory.get("/callback/")
        request.user = test_user

        response = GoogleOAuthCallbackView.handle_callback(request)

        assert response.status_code == 302
        assert "error=token_generation_failed" in response.url
        # Error message is URL-encoded
        assert "message=" in response.url


@pytest.mark.django_db
class TestGoogleOAuthCallbackEndpoint:
    """Test google_oauth_callback API endpoint."""

    def test_endpoint_calls_callback_handler(self, request_factory, test_user):
        """Test that endpoint properly delegates to callback handler."""
        request = request_factory.get("/api/auth/oauth/google/callback/")
        request.user = test_user

        response = google_oauth_callback(request)

        assert response.status_code == 302
        assert "access_token=" in response.url


@pytest.mark.django_db
class TestLinkOAuthAccount:
    """Test link_oauth_account endpoint."""

    def test_link_account_without_email(self, api_client):
        """Test that missing email returns 400."""
        response = api_client.post("/api/auth/oauth/link/", {}, format="json")

        assert response.status_code == 400
        assert "error" in response.json()
        assert "Email is required" in response.json()["error"]

    def test_link_account_user_not_found(self, api_client):
        """Test linking with non-existent user email."""
        response = api_client.post("/api/auth/oauth/link/", {"email": "nonexistent@example.com"}, format="json")

        assert response.status_code == 404
        assert "error" in response.json()
        assert "does not exist" in response.json()["error"]

    def test_link_account_user_found(self, api_client, test_user):
        """Test linking when user is found but no Google account linked."""
        response = api_client.post("/api/auth/oauth/link/", {"email": test_user.email}, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ready to link" in data["message"]
        assert data["user_id"] == test_user.id

    @patch("core.auth.SocialAccount.objects.filter")
    def test_link_account_already_linked(self, mock_social_filter, api_client, test_user):
        """Test when Google account is already linked."""
        mock_account = Mock()
        mock_social_filter.return_value.first.return_value = mock_account

        response = api_client.post("/api/auth/oauth/link/", {"email": test_user.email}, format="json")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "already linked" in data["message"]

    @patch("core.auth.User.objects.get")
    def test_link_account_error_handling(self, mock_get_user, api_client):
        """Test error handling in link_oauth_account."""
        mock_get_user.side_effect = Exception("Database error")

        response = api_client.post("/api/auth/oauth/link/", {"email": "test@example.com"}, format="json")

        assert response.status_code == 500
        assert "error" in response.json()
        assert "Failed to link account" in response.json()["error"]


@pytest.mark.django_db
class TestOAuthStatus:
    """Test oauth_status endpoint."""

    def test_oauth_status_returns_configuration(self, api_client):
        """Test that oauth_status returns OAuth configuration details."""
        response = api_client.get("/api/auth/oauth/status/")

        assert response.status_code == 200
        data = response.json()

        assert "google_oauth_configured" in data
        assert "google_client_id_present" in data
        assert "google_client_secret_present" in data
        assert "frontend_url" in data
        assert "oauth_callback_path" in data
        assert "site_id" in data

    def test_oauth_status_checks_google_credentials(self, api_client):
        """Test that oauth_status correctly checks Google credentials."""
        response = api_client.get("/api/auth/oauth/status/")
        data = response.json()

        # Check that it returns boolean values
        assert isinstance(data["google_oauth_configured"], bool)
        assert isinstance(data["google_client_id_present"], bool)
        assert isinstance(data["google_client_secret_present"], bool)

    def test_oauth_status_includes_settings(self, api_client):
        """Test that oauth_status includes relevant settings."""
        response = api_client.get("/api/auth/oauth/status/")
        data = response.json()

        # Should include settings values
        assert data["frontend_url"] == settings.FRONTEND_URL
        assert data["oauth_callback_path"] == settings.FRONTEND_AUTH_CALLBACK_PATH
        assert data["site_id"] == settings.SITE_ID


@pytest.mark.django_db
class TestOAuthIntegration:
    """Integration tests for complete OAuth flow."""

    def test_full_oauth_callback_flow(self, request_factory, test_user):
        """Test complete OAuth callback flow."""
        # Simulate OAuth callback with authenticated user
        request = request_factory.get("/callback/")
        request.user = test_user

        # Handle callback
        response = GoogleOAuthCallbackView.handle_callback(request)

        # Verify redirect to frontend
        assert response.status_code == 302
        assert settings.FRONTEND_URL in response.url
        assert settings.FRONTEND_AUTH_CALLBACK_PATH in response.url

        # Verify tokens in URL
        assert "access_token=" in response.url
        assert "refresh_token=" in response.url

        # Verify user info in URL
        assert f"user_id={test_user.id}" in response.url
        assert "email=" in response.url  # URL-encoded

    def test_oauth_error_flow(self, request_factory):
        """Test OAuth error handling flow."""
        # Create request with unauthenticated user
        request = request_factory.get("/callback/")
        request.user = Mock()
        request.user.is_authenticated = False

        # Handle callback
        response = GoogleOAuthCallbackView.handle_callback(request)

        # Verify error redirect
        assert response.status_code == 302
        assert settings.FRONTEND_URL in response.url
        assert "error=" in response.url

    def test_token_generation_consistency(self, test_user):
        """Test that tokens are consistently generated."""
        tokens1 = get_tokens_for_user(test_user)
        tokens2 = get_tokens_for_user(test_user)

        # Tokens should be generated but may differ each time
        assert tokens1["access"] is not None
        assert tokens2["access"] is not None
        assert tokens1["refresh"] is not None
        assert tokens2["refresh"] is not None
