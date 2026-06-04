"""Unit tests for the Web Push channel of notification_service.

Mocks only the external boundary (``pywebpush.webpush`` for web push and the
channel functions ``send_expo_push``/``send_web_push`` when asserting that
``send_push_notification`` fans out to both — these are the send boundaries,
mirroring ``test_notification_service.py``). The ORM, the model and the
internal logic of ``send_web_push`` are exercised for real.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.conf import settings
from pywebpush import WebPushException

from core.models import WebPushSubscription
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
    def test_send_push_notification_calls_both_channels(self, admin_user):
        with (
            patch("core.services.notification_service.send_expo_push") as mock_expo,
            patch("core.services.notification_service.send_web_push") as mock_web,
        ):
            send_push_notification(admin_user, "T", "B", {"k": "v"})

        mock_expo.assert_called_once_with(admin_user, "T", "B", {"k": "v"})
        mock_web.assert_called_once_with(admin_user, "T", "B", {"k": "v"})
