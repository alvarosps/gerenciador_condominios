"""Integration tests for DeviceTokenViewSet — register, update duplicate, unregister."""

import logging

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import DeviceToken

_EXPO_PUSH_ID = "ExpoToken[test123]"
_EXPO_PUSH_ID_DUP = "ExpoToken[dup-test]"
_EXPO_PUSH_ID_DEL = "ExpoToken[to-delete]"
_EXPO_PUSH_ID_HANDOVER = "ExpoToken[handover]"


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


@pytest.mark.integration
class TestDeviceTokenHandoverSemantics:
    """B7: re-registering an existing token under a different authenticated user is a
    legitimate device-owner handover (Expo/shared-device pattern) — allowed, but logged as a
    structured warning for audit visibility, and it must not touch any other token belonging
    to the previous owner."""

    register_url = "/api/devices/register/"

    def test_reassigning_token_to_another_user_logs_warning(
        self, authenticated_api_client, admin_user, regular_user, caplog
    ):
        # admin_user registers the token first.
        authenticated_api_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID_HANDOVER, "platform": "android"},
            format="json",
        )

        # regular_user re-registers the same token — a legitimate handover.
        other_client = APIClient()
        other_client.force_authenticate(user=regular_user)
        with caplog.at_level(logging.WARNING, logger="core.viewsets.device_views"):
            response = other_client.post(
                self.register_url,
                {"token": _EXPO_PUSH_ID_HANDOVER, "platform": "ios"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        device = DeviceToken.objects.get(token=_EXPO_PUSH_ID_HANDOVER)
        assert device.user_id == regular_user.id
        assert any(
            str(admin_user.pk) in record.getMessage()
            and str(regular_user.pk) in record.getMessage()
            for record in caplog.records
        )

    def test_reassignment_does_not_affect_other_tokens_of_previous_owner(
        self, authenticated_api_client, admin_user, regular_user
    ):
        # admin_user owns two tokens.
        authenticated_api_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID_HANDOVER, "platform": "android"},
            format="json",
        )
        untouched_token = "ExpoToken[untouched]"
        authenticated_api_client.post(
            self.register_url,
            {"token": untouched_token, "platform": "android"},
            format="json",
        )

        # regular_user takes over only the first token.
        other_client = APIClient()
        other_client.force_authenticate(user=regular_user)
        other_client.post(
            self.register_url,
            {"token": _EXPO_PUSH_ID_HANDOVER, "platform": "ios"},
            format="json",
        )

        assert DeviceToken.objects.get(token=untouched_token).user_id == admin_user.id


@pytest.mark.integration
class TestDeviceTokenViewSetExposesNoListOrDestroy:
    """B7: the viewset only exposes register/unregister — never list/retrieve/destroy — so
    there is no route through which a user could enumerate or delete another user's tokens."""

    def test_list_route_does_not_exist(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/devices/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_route_does_not_exist(self, authenticated_api_client, admin_user):
        device = DeviceToken.objects.create(
            token="ExpoToken[no-destroy-route]",
            platform="ios",
            user=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )
        response = authenticated_api_client.delete(f"/api/devices/{device.pk}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
