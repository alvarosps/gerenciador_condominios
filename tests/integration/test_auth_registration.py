"""Integration tests for registration and logout endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.integration
class TestRegisterEndpoint:
    def test_register_creates_user_and_returns_tokens(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "newuser@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "first_name": "João",
                "last_name": "Silva",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert "user" in data
        user_data = data["user"]
        assert user_data["email"] == "newuser@example.com"
        assert user_data["first_name"] == "João"
        assert user_data["last_name"] == "Silva"
        assert "is_staff" in user_data
        assert "id" in user_data
        # Verify user was actually created in DB
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_rejects_mismatched_passwords(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "mismatch@example.com",
                "password": "StrongPass123!",
                "password2": "DifferentPass123!",
                "first_name": "Ana",
                "last_name": "Costa",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password2" in response.data
        assert "As senhas não conferem." in response.data["password2"]

    def test_register_rejects_duplicate_email(self, api_client, admin_user):
        # admin_user has email admin@test.com
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "admin@test.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "first_name": "Dup",
                "last_name": "User",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        assert "Um usuário com este email já existe." in response.data["email"]

    def test_register_rejects_weak_password(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "weakpass@example.com",
                "password": "123",
                "password2": "123",
                "first_name": "Weak",
                "last_name": "Pass",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_register_requires_all_fields(self, api_client):
        response = api_client.post(
            "/api/auth/register/",
            {"email": "incomplete@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_does_not_create_staff_user(self, api_client):
        api_client.post(
            "/api/auth/register/",
            {
                "email": "staff_attempt@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "first_name": "Normal",
                "last_name": "User",
            },
            format="json",
        )
        user = User.objects.filter(email="staff_attempt@example.com").first()
        assert user is not None
        assert user.is_staff is False


@pytest.mark.integration
class TestLogoutEndpoint:
    def test_logout_blacklists_refresh_token(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = api_client.post(
            "/api/auth/logout/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Token should now be blacklisted — using it again returns 401
        response2 = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_requires_authentication(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)

        response = api_client.post(
            "/api/auth/logout/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_returns_400_when_refresh_token_missing(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = api_client.post("/api/auth/logout/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_returns_400_for_invalid_refresh_token(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = api_client.post(
            "/api/auth/logout/",
            {"refresh": "not.a.valid.token"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
