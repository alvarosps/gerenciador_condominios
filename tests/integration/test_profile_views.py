"""Integration tests for user profile management endpoints.

Covers:
    PATCH /api/auth/me/update/  — update_profile
    POST  /api/auth/change-password/ — change_password
"""

import pytest
from rest_framework import status

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

UPDATE_URL = "/api/auth/me/update/"
CHANGE_PASSWORD_URL = "/api/auth/change-password/"


class TestUpdateProfile:
    def test_update_first_name(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.patch(
            UPDATE_URL, {"first_name": "Alvaro"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.first_name == "Alvaro"

    def test_update_last_name(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.patch(UPDATE_URL, {"last_name": "Souza"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.last_name == "Souza"

    def test_update_both_names(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.patch(
            UPDATE_URL, {"first_name": "Alvaro", "last_name": "Souza"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.first_name == "Alvaro"
        assert admin_user.last_name == "Souza"

    def test_returns_full_profile(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.patch(UPDATE_URL, {"first_name": "Test"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "id" in data
        assert "email" in data
        assert "is_staff" in data
        assert data["id"] == admin_user.pk
        assert data["email"] == admin_user.email
        assert data["is_staff"] == admin_user.is_staff

    def test_no_fields_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.patch(UPDATE_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.patch(UPDATE_URL, {"first_name": "Test"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChangePassword:
    def test_change_password_success(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.post(
            CHANGE_PASSWORD_URL,
            {"old_password": "testpass123", "new_password": "newpass456"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.check_password("newpass456")

    def test_wrong_old_password_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            CHANGE_PASSWORD_URL,
            {"old_password": "wrongpassword", "new_password": "newpass456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Senha atual incorreta" in response.data["error"]

    def test_short_new_password_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            CHANGE_PASSWORD_URL,
            {"old_password": "testpass123", "new_password": "abc"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "8 caracteres" in response.data["error"]

    def test_missing_old_password_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            CHANGE_PASSWORD_URL,
            {"new_password": "newpass456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_missing_new_password_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            CHANGE_PASSWORD_URL,
            {"old_password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(
            CHANGE_PASSWORD_URL,
            {"old_password": "testpass123", "new_password": "newpass456"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
