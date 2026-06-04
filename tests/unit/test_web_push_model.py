"""Tests for the WebPushSubscription model (__str__, defaults, uniqueness, AuditMixin)."""

import pytest
from django.db import transaction
from django.db.utils import IntegrityError

from core.models import WebPushSubscription


@pytest.mark.django_db
class TestWebPushSubscription:
    def test_create_with_valid_fields(self, regular_user) -> None:
        sub = WebPushSubscription.objects.create(
            user=regular_user,
            endpoint="https://push.example/abc",
            p256dh="pkey",
            auth="akey",
        )

        assert sub.pk is not None
        assert sub.user == regular_user
        assert sub.endpoint == "https://push.example/abc"
        assert sub.p256dh == "pkey"
        assert sub.auth == "akey"

    def test_is_active_defaults_to_true(self, regular_user) -> None:
        sub = WebPushSubscription.objects.create(
            user=regular_user,
            endpoint="https://push.example/default",
            p256dh="pkey",
            auth="akey",
        )

        assert sub.is_active is True

    def test_endpoint_is_unique(self, regular_user) -> None:
        WebPushSubscription.objects.create(
            user=regular_user,
            endpoint="https://push.example/dup",
            p256dh="pkey",
            auth="akey",
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            WebPushSubscription.objects.create(
                user=regular_user,
                endpoint="https://push.example/dup",
                p256dh="other",
                auth="other",
            )

    def test_str_representation(self, regular_user) -> None:
        sub = WebPushSubscription.objects.create(
            user=regular_user,
            endpoint="https://push.example/str",
            p256dh="pkey",
            auth="akey",
        )

        assert str(sub) == f"Web push for {regular_user}"

    def test_related_name_from_user(self, regular_user) -> None:
        sub = WebPushSubscription.objects.create(
            user=regular_user,
            endpoint="https://push.example/related",
            p256dh="pkey",
            auth="akey",
        )

        assert regular_user.web_push_subscriptions.count() == 1
        assert regular_user.web_push_subscriptions.first() == sub

    def test_inherits_audit_mixin_without_soft_delete(self, regular_user) -> None:
        sub = WebPushSubscription.objects.create(
            user=regular_user,
            endpoint="https://push.example/audit",
            p256dh="pkey",
            auth="akey",
        )

        assert sub.created_at is not None
        assert sub.updated_at is not None
        assert not hasattr(sub, "is_deleted")
