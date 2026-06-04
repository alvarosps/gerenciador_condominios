"""Integration tests for WebPushViewSet — vapid-public-key, subscribe, unsubscribe.

Mirrors ``test_device_api.py``. Real DB, no internal mocks. The subscribe
payload uses the exact shape sent by the frontend (``subscription.toJSON()``):
``{ endpoint, keys: { p256dh, auth } }``.
"""

import pytest
from django.test import override_settings
from rest_framework import status

from core.models import WebPushSubscription

_ENDPOINT = "https://push.example.com/sub-1"
_ENDPOINT_DUP = "https://push.example.com/sub-dup"
_ENDPOINT_DEL = "https://push.example.com/sub-del"


@pytest.mark.integration
class TestWebPushAPI:
    vapid_url = "/api/web-push/vapid-public-key/"
    subscribe_url = "/api/web-push/subscribe/"
    unsubscribe_url = "/api/web-push/unsubscribe/"

    @override_settings(VAPID_PUBLIC_KEY="test-pub-key")
    def test_vapid_public_key_returns_key(self, authenticated_api_client):
        response = authenticated_api_client.get(self.vapid_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["publicKey"] == "test-pub-key"

    def test_subscribe_creates_subscription(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.post(
            self.subscribe_url,
            {"endpoint": _ENDPOINT, "keys": {"p256dh": "p256dh-key", "auth": "auth-secret"}},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["endpoint"] == _ENDPOINT
        assert WebPushSubscription.objects.filter(
            endpoint=_ENDPOINT, user=admin_user, is_active=True
        ).exists()

    def test_subscribe_same_endpoint_updates_existing(self, authenticated_api_client):
        authenticated_api_client.post(
            self.subscribe_url,
            {"endpoint": _ENDPOINT_DUP, "keys": {"p256dh": "old-p256dh", "auth": "old-auth"}},
            format="json",
        )

        response = authenticated_api_client.post(
            self.subscribe_url,
            {"endpoint": _ENDPOINT_DUP, "keys": {"p256dh": "new-p256dh", "auth": "new-auth"}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert WebPushSubscription.objects.filter(endpoint=_ENDPOINT_DUP).count() == 1
        sub = WebPushSubscription.objects.get(endpoint=_ENDPOINT_DUP)
        assert sub.p256dh == "new-p256dh"
        assert sub.auth == "new-auth"

    def test_subscribe_missing_keys_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.subscribe_url,
            {"endpoint": _ENDPOINT},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_subscribe_missing_endpoint_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.subscribe_url,
            {"keys": {"p256dh": "p256dh-key", "auth": "auth-secret"}},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unsubscribe_deactivates_subscription(self, authenticated_api_client):
        authenticated_api_client.post(
            self.subscribe_url,
            {"endpoint": _ENDPOINT_DEL, "keys": {"p256dh": "p256dh-key", "auth": "auth-secret"}},
            format="json",
        )

        response = authenticated_api_client.post(
            self.unsubscribe_url,
            {"endpoint": _ENDPOINT_DEL},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert WebPushSubscription.objects.filter(endpoint=_ENDPOINT_DEL, is_active=False).exists()

    def test_unsubscribe_nonexistent_returns_404(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.unsubscribe_url,
            {"endpoint": "https://push.example.com/ghost"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unsubscribe_missing_endpoint_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.unsubscribe_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_subscribe_requires_authentication(self, api_client):
        response = api_client.post(
            self.subscribe_url,
            {"endpoint": _ENDPOINT, "keys": {"p256dh": "p256dh-key", "auth": "auth-secret"}},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
