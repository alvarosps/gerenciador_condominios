"""Integration tests for the two password-setting flows.

Both flows must run the new password through Django's AUTH_PASSWORD_VALIDATORS:
- POST /api/auth/change-password/  (any authenticated user, requires old password)
- POST /api/auth/set-password/     (admin only)

Mock policy: nothing internal is mocked — real User, real validators, real DB.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

CHANGE_URL = "/api/auth/change-password/"
SET_URL = "/api/auth/set-password/"

_OLD_PASSWORD = "Str0ng-Old-Pass!42"
_STRONG_PASSWORD = "Tr0ubadour-Xylophone-91"


_USERNAME = "marianafernandes"


@pytest.fixture
def user_with_password(django_user_model):
    return django_user_model.objects.create_user(
        username=_USERNAME,
        email="marianafernandes@test.com",
        password=_OLD_PASSWORD,
        is_staff=False,
        is_active=True,
    )


@pytest.fixture
def client_for(user_with_password):
    client = APIClient()
    client.force_authenticate(user=user_with_password)
    return client


@pytest.mark.integration
class TestChangePasswordValidation:
    def test_change_password_too_short_returns_400(self, client_for):
        response = client_for.post(
            CHANGE_URL,
            {"old_password": _OLD_PASSWORD, "new_password": "Ab1!c"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_too_common_returns_400(self, client_for):
        response = client_for.post(
            CHANGE_URL,
            {"old_password": _OLD_PASSWORD, "new_password": "password123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_all_numeric_returns_400(self, client_for):
        response = client_for.post(
            CHANGE_URL,
            {"old_password": _OLD_PASSWORD, "new_password": "84736251902"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_similar_to_username_returns_400(self, client_for):
        response = client_for.post(
            CHANGE_URL,
            {"old_password": _OLD_PASSWORD, "new_password": _USERNAME},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_wrong_old_returns_400(self, client_for):
        response = client_for.post(
            CHANGE_URL,
            {"old_password": "definitely-not-the-old", "new_password": _STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_strong_succeeds(self, client_for, user_with_password):
        response = client_for.post(
            CHANGE_URL,
            {"old_password": _OLD_PASSWORD, "new_password": _STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        user_with_password.refresh_from_db()
        assert user_with_password.check_password(_STRONG_PASSWORD)


@pytest.mark.integration
class TestSetPasswordValidation:
    def test_set_password_weak_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(SET_URL, {"password": "12345678"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_set_password_strong_succeeds(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.post(
            SET_URL, {"password": _STRONG_PASSWORD}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        refreshed = User.objects.get(pk=admin_user.pk)
        assert refreshed.check_password(_STRONG_PASSWORD)

    def test_set_password_missing_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(SET_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
