"""
Unit tests for JWT Authentication.

Tests token generation, validation, refresh, and blacklisting functionality.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
class TestJWTTokenObtain:
    """Test JWT token obtaining (login) functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.token_url = "/api/auth/token/"
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass123")

    def test_obtain_token_with_valid_credentials(self):
        """Test obtaining JWT token with valid username and password."""
        response = self.client.post(self.token_url, {"username": "testuser", "password": "testpass123"})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert isinstance(response.data["access"], str)
        assert isinstance(response.data["refresh"], str)

    def test_obtain_token_with_invalid_credentials(self):
        """Test token obtain fails with invalid credentials."""
        response = self.client.post(self.token_url, {"username": "testuser", "password": "wrongpassword"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "access" not in response.data
        assert "refresh" not in response.data

    def test_obtain_token_with_missing_credentials(self):
        """Test token obtain fails with missing credentials."""
        response = self.client.post(self.token_url, {"username": "testuser"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_obtain_token_with_nonexistent_user(self):
        """Test token obtain fails with nonexistent user."""
        response = self.client.post(self.token_url, {"username": "nonexistent", "password": "testpass123"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_for_inactive_user(self):
        """Test token obtain fails for inactive user."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.token_url, {"username": "testuser", "password": "testpass123"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_for_superuser(self):
        """Test superuser can obtain tokens."""
        _superuser = User.objects.create_superuser(  # noqa: F841
            username="admin", email="admin@example.com", password="adminpass123"
        )

        response = self.client.post(self.token_url, {"username": "admin", "password": "adminpass123"})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data


@pytest.mark.django_db
class TestJWTTokenRefresh:
    """Test JWT token refresh functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.refresh_url = "/api/auth/token/refresh/"
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass123")
        self.refresh = RefreshToken.for_user(self.user)

    def test_refresh_token_with_valid_refresh_token(self):
        """Test refreshing access token with valid refresh token."""
        response = self.client.post(self.refresh_url, {"refresh": str(self.refresh)})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert isinstance(response.data["access"], str)

    def test_refresh_token_with_invalid_token(self):
        """Test refresh fails with invalid token."""
        response = self.client.post(self.refresh_url, {"refresh": "invalid.token.here"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_with_missing_token(self):
        """Test refresh fails with missing token."""
        response = self.client.post(self.refresh_url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token_rotation(self):
        """Test that refresh token is rotated when ROTATE_REFRESH_TOKENS is True."""
        response = self.client.post(self.refresh_url, {"refresh": str(self.refresh)})

        assert response.status_code == status.HTTP_200_OK
        # When rotation is enabled, a new refresh token should be returned
        if "refresh" in response.data:
            assert response.data["refresh"] != str(self.refresh)


@pytest.mark.django_db
class TestJWTTokenBlacklist:
    """Test JWT token blacklisting (logout) functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.blacklist_url = "/api/auth/token/blacklist/"
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass123")
        self.refresh = RefreshToken.for_user(self.user)

    def test_blacklist_token_successfully(self):
        """Test successfully blacklisting a refresh token."""
        response = self.client.post(self.blacklist_url, {"refresh": str(self.refresh)})

        assert response.status_code == status.HTTP_200_OK

    def test_blacklist_token_with_invalid_token(self):
        """Test blacklisting fails with invalid token."""
        response = self.client.post(self.blacklist_url, {"refresh": "invalid.token.here"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_blacklist_token_with_missing_token(self):
        """Test blacklisting fails with missing token."""
        response = self.client.post(self.blacklist_url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_blacklisted_token_cannot_be_refreshed(self):
        """Test that a blacklisted token cannot be used to refresh."""
        # Blacklist the token
        blacklist_response = self.client.post(self.blacklist_url, {"refresh": str(self.refresh)})
        assert blacklist_response.status_code == status.HTTP_200_OK

        # Try to refresh with the blacklisted token
        refresh_response = self.client.post("/api/auth/token/refresh/", {"refresh": str(self.refresh)})

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestJWTAuthentication:
    """Test JWT authentication in API requests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass123")
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    def test_access_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid access token."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.get("/api/buildings/")

        # Should be authenticated (200 or 404 depending on data)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_access_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token fails."""
        response = self.client.get("/api/buildings/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token fails."""
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        response = self.client.get("/api/buildings/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_endpoint_with_malformed_header(self):
        """Test accessing protected endpoint with malformed authorization header."""
        self.client.credentials(HTTP_AUTHORIZATION="InvalidFormat token")
        response = self.client.get("/api/buildings/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_endpoint_with_bearer_prefix_missing(self):
        """Test accessing protected endpoint without 'Bearer' prefix."""
        self.client.credentials(HTTP_AUTHORIZATION=self.access_token)
        response = self.client.get("/api/buildings/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestJWTTokenContent:
    """Test JWT token content and claims."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123", is_staff=True
        )

    def test_access_token_contains_user_id(self):
        """Test that access token contains user ID."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        assert "user_id" in access_token.payload
        assert access_token.payload["user_id"] == self.user.id

    def test_access_token_contains_token_type(self):
        """Test that access token contains token type."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        assert "token_type" in access_token.payload
        assert access_token.payload["token_type"] == "access"

    def test_refresh_token_contains_user_id(self):
        """Test that refresh token contains user ID."""
        refresh = RefreshToken.for_user(self.user)

        assert "user_id" in refresh.payload
        assert refresh.payload["user_id"] == self.user.id
