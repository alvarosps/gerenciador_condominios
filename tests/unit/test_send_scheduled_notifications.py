"""Unit tests for send_scheduled_notifications management command.

Verifies that due/overdue push notifications only fire for leases that are
collectible in the current month (via RentScheduleService.collectible_leases SSOT),
while contract-expiry notifications still fire for all leases regardless of
collectibility.

External push calls (Expo HTTP + web push) are mocked so no outbound network
traffic is made. Behavior is asserted via Notification DB rows (real ORM).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.management import call_command
from freezegun import freeze_time

from core.models import (
    Apartment,
    Building,
    FinancialSettings,
    Lease,
    Notification,
    Person,
    Tenant,
)
from tests.constants import TEST_PASSWORD
from tests.factories import make_rent_payment

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=9900,
        name="Prédio Notif Sched",
        address="Rua Notif Sched, 9900",
        created_by=admin_user,
        updated_by=admin_user,
    )


def _make_tenant_with_user(cpf: str, name: str, due_day: int, admin_user: User) -> Tenant:
    """Create a tenant that has an associated User account (required for push notifications)."""
    user = User.objects.create_user(
        username=f"user_{cpf}",
        email=f"{cpf}@test.com",
        password=TEST_PASSWORD,
        is_active=True,
    )
    return Tenant.objects.create(
        name=name,
        cpf_cnpj=cpf,
        is_company=False,
        phone="11999990099",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=due_day,
        user=user,
        created_by=admin_user,
        updated_by=admin_user,
    )


def _make_lease(apartment: Apartment, tenant: Tenant, admin_user: User, **kwargs) -> Lease:
    defaults = {
        "start_date": date(2026, 1, 1),
        "validity_months": 24,
        "tag_fee": Decimal("50.00"),
        "rental_value": Decimal("1200.00"),
    }
    defaults.update(kwargs)
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        created_by=admin_user,
        updated_by=admin_user,
        **defaults,
    )


def _make_apartment(building: Building, number: int, admin_user: User, **kwargs) -> Apartment:
    defaults = {
        "rental_value": Decimal("1200.00"),
        "cleaning_fee": Decimal("100.00"),
        "max_tenants": 1,
    }
    defaults.update(kwargs)
    return Apartment.objects.create(
        building=building,
        number=number,
        created_by=admin_user,
        updated_by=admin_user,
        **defaults,
    )


# ---------------------------------------------------------------------------
# Helper: run the command with mocked external push
# ---------------------------------------------------------------------------


def _run_command():
    """Run send_scheduled_notifications with external push mocked out."""
    with (
        patch("core.services.notification_service.http_requests.post"),
        patch("core.services.notification_service.webpush"),
    ):
        call_command("send_scheduled_notifications")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSendScheduledNotificationsCollectibility:
    """Verify that due/overdue notifications follow the collectibility SSOT.

    All ``freeze_time`` calls below use noon UTC (not midnight) so ``today_sp()``
    stays on the same calendar day as the frozen date — midnight UTC is 21:00 the
    previous day in São Paulo (UTC-3) and would shift the day-count assertions by one.
    """

    @freeze_time("2026-06-16 12:00:00")
    def test_overdue_notification_sent_for_collectible_lease(self, building, admin_user):
        """A collectible lease past due receives an 'overdue' notification.

        today=2026-06-16, due_day=11 → days_past_due=5 ∈ _OVERDUE_CHECK_DAYS.
        """
        apartment = _make_apartment(building, 101, admin_user)
        tenant = _make_tenant_with_user("11144477735", "Inquilino Normal", 11, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert Notification.objects.filter(recipient=tenant.user, type="overdue").exists()

    @freeze_time("2026-06-16 12:00:00")
    def test_no_overdue_for_pre_boundary_month_lease(self, building, admin_user):
        """When the current month is before the tracking boundary, no overdue notification is sent.

        today=2026-06-16, boundary=2026-07-01 → June is untracked →
        collectible_leases returns empty → no due/overdue notifications.
        """
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 7, 1),
        )
        apartment = _make_apartment(building, 102, admin_user)
        tenant = _make_tenant_with_user("12345678909", "Inquilino Pre-Boundary", 11, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert not Notification.objects.filter(recipient=tenant.user, type="overdue").exists()
        assert not Notification.objects.filter(recipient=tenant.user, type="due_today").exists()
        assert not Notification.objects.filter(recipient=tenant.user, type="due_reminder").exists()

    @freeze_time("2026-06-16 12:00:00")
    def test_no_overdue_for_prepaid_lease(self, building, admin_user):
        """A prepaid lease (prepaid_until strictly after the clamped due date for June)
        is excluded from collectible leases → no overdue notification.

        today=2026-06-16, due_day=11 → due_date=2026-06-11; prepaid_until=2026-07-01
        (after June-11) → prepaid → not collectible → no overdue.
        """
        apartment = _make_apartment(building, 103, admin_user)
        tenant = _make_tenant_with_user("98765432100", "Inquilino Prepaid", 11, admin_user)
        _make_lease(apartment, tenant, admin_user, prepaid_until=date(2026, 7, 1))

        _run_command()

        assert not Notification.objects.filter(recipient=tenant.user, type="overdue").exists()

    @freeze_time("2026-06-16 12:00:00")
    def test_no_overdue_for_owner_repass_lease(self, building, admin_user):
        """An owner-repass lease is not collectible → no overdue notification.
        Contract-expiry notification still fires when within 30 days of end.
        """
        owner = Person.objects.create(
            name="Proprietário",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment = _make_apartment(building, 104, admin_user, owner=owner)
        tenant = _make_tenant_with_user("71428793860", "Inquilino Repasse", 11, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert not Notification.objects.filter(recipient=tenant.user, type="overdue").exists()

    @freeze_time("2026-06-16 12:00:00")
    def test_contract_expiry_fires_for_owner_repass_lease(self, building, admin_user):
        """Contract-expiry notification fires for all leases, including owner-repass.

        today=2026-06-16, lease ends 30 days from now = 2026-07-16.
        start_date + validity_months = end_date → we set start_date so end is exactly 30 days out.
        """
        owner = Person.objects.create(
            name="Proprietário Contrato",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment = _make_apartment(building, 105, admin_user, owner=owner)
        tenant = _make_tenant_with_user("15782647825", "Repasse Contrato", 11, admin_user)
        # end_date = start_date + 12 months = 2026-07-16 → start = 2025-07-16
        # 2026-06-16 + 30 days = 2026-07-16
        target_end = date(2026, 7, 16)
        validity = 12
        start = target_end - relativedelta(months=validity)
        _make_lease(apartment, tenant, admin_user, start_date=start, validity_months=validity)

        _run_command()

        assert Notification.objects.filter(recipient=tenant.user, type="contract_expiring").exists()


@pytest.mark.unit
class TestSendScheduledNotificationsTimezoneAndDueWindow:
    """B12: SP-aware "today" (not UTC), no reminder for already-paid rent, and the
    3-day-before window correctly crossing a month boundary for due_day 1-3."""

    @freeze_time("2026-06-16 01:30:00")
    def test_sp_day_lags_behind_utc_day_across_midnight(self, building, admin_user):
        """01:30 UTC on June 16 is 22:30 on June 15 in São Paulo (UTC-3): the UTC date
        has already rolled to June 16, but today_sp() must still report June 15."""
        apartment = _make_apartment(building, 202, admin_user)
        # due_day=18 → SP today=June 15 → days_until_due=3 → due_reminder fires.
        # If the UTC date (June 16) were used instead, days_until_due would be 2 → no reminder.
        tenant = _make_tenant_with_user("46959416000", "Inquilino SP Lag", 18, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert Notification.objects.filter(recipient=tenant.user, type="due_reminder").exists()

    @freeze_time("2026-06-15 21:30:00")
    def test_sp_day_still_lags_within_21_to_midnight_utc_window(self, building, admin_user):
        """21:30 UTC on June 15 is 18:30 on June 15 in São Paulo (UTC-3) — inside the
        21:00-00:00 UTC window where a naive UTC 'today' has NOT yet rolled over but
        must still resolve consistently through today_sp() to June 15."""
        apartment = _make_apartment(building, 206, admin_user)
        # due_day=15 → SP today=June 15 → days_until_due=0 → due_today fires.
        tenant = _make_tenant_with_user("56789123482", "Inquilino Janela 21h", 15, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert Notification.objects.filter(recipient=tenant.user, type="due_today").exists()

    @freeze_time("2026-06-16 12:00:00")
    def test_no_due_reminder_when_month_already_paid(self, building, admin_user):
        """A tenant who already paid the month's rent gets no due_reminder, even
        though the day-count would otherwise trigger one."""
        apartment = _make_apartment(building, 203, admin_user)
        tenant = _make_tenant_with_user("23456789173", "Inquilino Pago", 19, admin_user)
        lease = _make_lease(apartment, tenant, admin_user)
        make_rent_payment(
            lease=lease,
            user=admin_user,
            reference_month=date(2026, 6, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 6, 10),
        )

        _run_command()

        assert not Notification.objects.filter(
            recipient=tenant.user, type__in=["due_reminder", "due_today", "overdue"]
        ).exists()

    @freeze_time("2026-05-29 12:00:00")
    def test_due_reminder_fires_for_due_day_crossing_into_next_month(self, building, admin_user):
        """Regression: due_day=1 with today=2026-05-29 must fire a due_reminder for the
        June 1st due date (3 days away), not silently fail to fire because
        today.replace(day=1) would point at an already-past date (May 1st) in the
        current month.
        """
        apartment = _make_apartment(building, 204, admin_user)
        tenant = _make_tenant_with_user("34567891228", "Inquilino Dia 1", 1, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert Notification.objects.filter(recipient=tenant.user, type="due_reminder").exists()

    @freeze_time("2026-05-30 12:00:00")
    def test_due_today_fires_for_due_day_2_crossing_into_next_month(self, building, admin_user):
        """Regression: due_day=2 with today=2026-05-30 is 3 days before the June 2nd
        due date — due_reminder must fire (previously the buggy same-month
        `today.replace(day=2)` pointed at an already-past date)."""
        apartment = _make_apartment(building, 205, admin_user)
        tenant = _make_tenant_with_user("45678912364", "Inquilino Dia 2", 2, admin_user)
        _make_lease(apartment, tenant, admin_user)

        _run_command()

        assert Notification.objects.filter(recipient=tenant.user, type="due_reminder").exists()
