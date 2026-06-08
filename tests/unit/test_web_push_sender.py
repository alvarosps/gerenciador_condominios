"""Unit tests for the Web Push channel of notification_service.

Mocks ONLY the external send boundaries — ``pywebpush.webpush`` (web push) and
``http_requests.post`` (the Expo HTTP API). The ORM, the models, and the real internal logic of
``send_web_push``/``send_expo_push``/``send_push_notification`` are exercised for real, so a bug in
any of them fails the test instead of being hidden behind a mocked internal function.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.conf import settings
from pywebpush import WebPushException

from core.models import DeviceToken, WebPushSubscription
from core.services.notification_service import send_push_notification, send_web_push


@pytest.fixture
def subscription(admin_user):
    return WebPushSubscription.objects.create(
        user=admin_user,
        endpoint="https://push.example.com/sub-active",
        p256dh="p256dh-key",
        auth="auth-secret",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.unit
class TestSendWebPush:
    def test_send_web_push_calls_webpush_for_active_subscription(self, admin_user, subscription):
        with patch("core.services.notification_service.webpush") as mock_webpush:
            send_web_push(admin_user, "Título", "Corpo", {"key": "val"})

        mock_webpush.assert_called_once()
        kwargs = mock_webpush.call_args.kwargs
        assert kwargs["subscription_info"] == {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        assert json.loads(kwargs["data"]) == {
            "title": "Título",
            "body": "Corpo",
            "data": {"key": "val"},
        }
        assert kwargs["vapid_private_key"] == settings.VAPID_PRIVATE_KEY
        assert kwargs["vapid_claims"] == {"sub": settings.VAPID_SUBJECT}

    def test_send_web_push_skips_inactive_subscription(self, admin_user):
        WebPushSubscription.objects.create(
            user=admin_user,
            endpoint="https://push.example.com/sub-inactive",
            p256dh="p256dh-key",
            auth="auth-secret",
            is_active=False,
            created_by=admin_user,
            updated_by=admin_user,
        )

        with patch("core.services.notification_service.webpush") as mock_webpush:
            send_web_push(admin_user, "Título", "Corpo")

        mock_webpush.assert_not_called()

    def test_send_web_push_deactivates_on_410(self, admin_user, subscription):
        gone = WebPushException("gone", response=SimpleNamespace(status_code=410))

        with patch("core.services.notification_service.webpush", side_effect=gone):
            send_web_push(admin_user, "Título", "Corpo")

        subscription.refresh_from_db()
        assert subscription.is_active is False

    def test_send_web_push_keeps_subscription_on_other_error(self, admin_user, subscription):
        server_error = WebPushException("boom", response=SimpleNamespace(status_code=500))

        with patch("core.services.notification_service.webpush", side_effect=server_error):
            send_web_push(admin_user, "Título", "Corpo")

        subscription.refresh_from_db()
        assert subscription.is_active is True


@pytest.mark.unit
class TestSendPushNotificationDualChannel:
    def test_send_push_notification_reaches_both_external_channels(self, admin_user, subscription):
        """The real dispatcher runs the real Expo + Web Push channels; only the external send
        boundaries are mocked. ``subscription`` seeds an active Web Push sub; add an active Expo
        device so both real channels reach their boundary."""
        DeviceToken.objects.create(
            user=admin_user,
            token="ExpoToken[dual-channel]",
            platform="android",
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        with (
            patch("core.services.notification_service.http_requests.post") as mock_expo_post,
            patch("core.services.notification_service.webpush") as mock_webpush,
        ):
            send_push_notification(admin_user, "T", "B", {"k": "v"})

        # The real send_expo_push and send_web_push each hit their external boundary exactly once.
        mock_expo_post.assert_called_once()
        mock_webpush.assert_called_once()
