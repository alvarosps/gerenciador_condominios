"""Unit tests for notification_service."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from freezegun import freeze_time

from core.models import Apartment, Building, DeviceToken, Lease, Notification, Tenant
from core.services.notification_service import (
    create_notification,
    is_notification_sent_today,
    send_push_notification,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=8801,
        name="Prédio Notif",
        address="Rua Notif, 8801",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=301,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Inquilino Notif",
        cpf_cnpj="11144477735",
        is_company=False,
        phone="11999990002",
        marital_status="Solteiro(a)",
        profession="Analista",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateNotification:
    def test_create_notification_persists_to_db(self, admin_user):
        with patch("core.services.notification_service.http_requests.post"):
            notif = create_notification(
                recipient=admin_user,
                notification_type="admin_notice",
                title="Aviso",
                body="Mensagem de teste",
                data={"extra": "value"},
            )

        assert notif.pk is not None
        db_notif = Notification.objects.get(pk=notif.pk)
        assert db_notif.recipient == admin_user
        assert db_notif.type == "admin_notice"
        assert db_notif.title == "Aviso"
        assert db_notif.body == "Mensagem de teste"
        assert db_notif.data == {"extra": "value"}


@pytest.mark.unit
class TestSendPushNotification:
    def test_send_push_calls_expo_api(self, admin_user):
        DeviceToken.objects.create(
            user=admin_user,
            token="ExpoToken[push-test]",
            platform="android",
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        with patch("core.services.notification_service.http_requests.post") as mock_post:
            send_push_notification(admin_user, "Título", "Corpo", {"key": "val"})

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "https://exp.host/--/api/v2/push/send"

    def test_send_push_skips_call_when_no_devices(self, admin_user):
        with patch("core.services.notification_service.http_requests.post") as mock_post:
            send_push_notification(admin_user, "Título", "Corpo")

        mock_post.assert_not_called()


@pytest.mark.unit
class TestIsNotificationSentToday:
    @freeze_time("2026-03-15 10:00:00")
    def test_returns_true_when_sent_today(self, admin_user):
        Notification.objects.create(
            recipient=admin_user,
            type="due_today",
            title="Vencimento",
            body="Aluguel vence hoje",
            sent_at=timezone.now(),
        )

        assert is_notification_sent_today(admin_user, "due_today") is True

    @freeze_time("2026-03-15 10:00:00")
    def test_returns_false_when_not_sent_today(self, admin_user):
        assert is_notification_sent_today(admin_user, "due_today") is False

    @freeze_time("2026-03-15 10:00:00")
    def test_returns_false_for_different_type(self, admin_user):
        Notification.objects.create(
            recipient=admin_user,
            type="due_reminder",
            title="Lembrete",
            body="Vencimento em 3 dias",
            sent_at=timezone.now(),
        )

        assert is_notification_sent_today(admin_user, "due_today") is False
