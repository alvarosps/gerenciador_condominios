"""Integration tests for DeviceTokenViewSet — register, update duplicate, unregister."""

import pytest
from rest_framework import status

from core.models import DeviceToken

_EXPO_PUSH_ID = "ExpoToken[test123]"
_EXPO_PUSH_ID_DUP = "ExpoToken[dup-test]"
_EXPO_PUSH_ID_DEL = "ExpoToken[to-delete]"


@pytest.mark.integration
class TestDeviceTokenAPI:
    register_url = "/api/devices/register/"
    unregister_url = "/api/devices/unregister/"

    def test_register_new_token(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID, "platform": "android"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["token"] == _EXPO_PUSH_ID
        assert response.data["platform"] == "android"
        assert DeviceToken.objects.filter(token=_EXPO_PUSH_ID, user=admin_user).exists()

    def test_register_duplicate_token_updates_existing(self, authenticated_api_client, admin_user):
        # First registration
        authenticated_api_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID_DUP, "platform": "ios"},
            format="json",
        )

        # Second registration with same token — should update, not create
        response = authenticated_api_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID_DUP, "platform": "android"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["platform"] == "android"
        assert DeviceToken.objects.filter(token=_EXPO_PUSH_ID_DUP).count() == 1

    def test_unregister_token(self, authenticated_api_client, admin_user):
        # Register first
        authenticated_api_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID_DEL, "platform": "ios"},
            format="json",
        )

        response = authenticated_api_client.post(
            self.unregister_url,
            {"token": _EXPO_PUSH_ID_DEL},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert DeviceToken.objects.filter(token=_EXPO_PUSH_ID_DEL, is_active=False).exists()

    def test_register_missing_fields_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.register_url,
            {"token": "ExpoToken[x]"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_platform_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.register_url,
            {"token": "ExpoToken[x]", "platform": "windows"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unregister_nonexistent_token_returns_404(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.unregister_url,
            {"token": "ExpoToken[ghost]"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_register_requires_authentication(self, api_client):
        response = api_client.post(
            self.register_url,
            {"token": "ExpoToken[x]", "platform": "ios"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
