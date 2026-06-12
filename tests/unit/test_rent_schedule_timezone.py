"""São Paulo timezone boundary for the active core rent/dashboard paths (P2.5).

settings.TIME_ZONE is "UTC", so timezone.now().date() yields the UTC date. Between
21:00 and 23:59 in São Paulo (UTC-3) the UTC clock is already on the next day, so the
unpay guard fired early, the late fee counted +1 day and the month stats rolled over at
21:00 on the last day of the month. These tests pin that the active core paths
(RentScheduleService toggle / schedule / stats and DashboardService late-payment summary)
use the São Paulo "today" from core.services.timezone.today_sp, not the UTC date.

The frozen instant 2026-01-31 23:30 UTC == 2026-01-31 20:30 SP (same SP day, Jan 31),
and 2026-02-01 01:00 UTC == 2026-01-31 22:00 SP (UTC already Feb 1, SP still Jan 31).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker

from core.services.dashboard_service import DashboardService
from core.services.rent_schedule_service import RentScheduleService
from tests.factories import (
    make_apartment,
    make_building,
    make_lease,
    make_tenant,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    return baker.make(User, username="admin-tz", is_staff=True)


@pytest.fixture
def lease():
    """Collectible lease due on the 31st (clamps to the last day each month)."""
    building = make_building(street_number=901, name="Edifício 901", address="Rua TZ, 901")
    apartment = make_apartment(
        building=building, number=201, rental_value=Decimal("1000.00"), is_rented=True
    )
    tenant = make_tenant(cpf_cnpj="11122233396", name="Inquilino TZ", due_day=31)
    return make_lease(
        apartment=apartment,
        tenant=tenant,
        start_date=date(2025, 6, 1),
        rental_value=Decimal("1000.00"),
    )


# ──────────────────────────────────────────
# toggle_payment — unpay guard uses SP "today"
# ──────────────────────────────────────────


@freeze_time("2026-02-01 01:00:00")
def test_toggle_payment_unpay_guard_uses_sp_date(lease, admin_user) -> None:
    """At 22:00 SP on Jan 31 (= 01:00 UTC Feb 1) the rent due Jan 31 may still be
    unmarked: SP today is still the due day, not past it. The UTC date (Feb 1) would
    wrongly forbid it (clamped_due_date 2026-01-31 < UTC today 2026-02-01)."""
    reference_month = date(2026, 1, 1)
    # UTC has already rolled to February — this is the bug the SP helper avoids.
    assert timezone.now().date() == date(2026, 2, 1)

    marked = RentScheduleService.toggle_payment(lease.id, reference_month, admin_user)
    assert marked["is_paid"] is True

    unmarked = RentScheduleService.toggle_payment(lease.id, reference_month, admin_user)
    assert unmarked["status"] == "ok"
    assert unmarked["is_paid"] is False


@freeze_time("2026-02-01 01:00:00")
def test_toggle_payment_marks_payment_date_in_sp(lease, admin_user) -> None:
    """payment_date recorded on the created RentPayment is the São Paulo date
    (Jan 31), not the UTC date (Feb 1)."""
    from core.models import RentPayment

    reference_month = date(2026, 1, 1)
    RentScheduleService.toggle_payment(lease.id, reference_month, admin_user)

    payment = RentPayment.objects.get(lease_id=lease.id, reference_month=reference_month)
    assert payment.payment_date == date(2026, 1, 31)


# ──────────────────────────────────────────
# get_month_stats / get_month_schedule — no 21h month rollover
# ──────────────────────────────────────────


@freeze_time("2026-02-01 01:00:00")
def test_get_month_stats_does_not_roll_month_at_21h_sp(lease) -> None:
    """On the last day of January at 22:00 SP (= 01:00 UTC Feb 1), the January stats
    must treat January as the current month (is_current_or_past) — the unpaid rent due
    on Jan 31 is NOT overdue yet (today is the due day, not past it)."""
    stats = RentScheduleService.get_month_stats(2026, 1)
    # Due day is Jan 31 == SP today; not past, so not overdue.
    assert stats["overdue_count"] == 0
    assert stats["due_count"] == 1
    assert stats["to_receive_total"] == "1000.00"


@freeze_time("2026-02-01 01:00:00")
def test_get_month_schedule_today_is_sp(lease) -> None:
    """The schedule payload's ``today`` is the São Paulo ISO date (Jan 31), not UTC."""
    schedule = RentScheduleService.get_month_schedule(2026, 1)
    assert schedule["today"] == "2026-01-31"


@freeze_time("2026-02-01 01:00:00")
def test_as_of_override_still_respected(lease) -> None:
    """Passing ``as_of`` keeps overriding "today" (the condo-finance calendar relies on
    this); only the default changed from UTC to SP."""
    schedule = RentScheduleService.get_month_schedule(2026, 1, as_of=date(2026, 1, 15))
    assert schedule["today"] == "2026-01-15"
    stats = RentScheduleService.get_month_stats(2026, 1, as_of=date(2026, 1, 15))
    # Jan 15: rent due Jan 31 is in the future, not overdue.
    assert stats["overdue_count"] == 0


# ──────────────────────────────────────────
# dashboard_service — late payment summary uses SP "today"
# ──────────────────────────────────────────


@freeze_time("2026-02-01 01:00:00")
def test_late_payment_summary_today_is_sp(lease) -> None:
    """At 22:00 SP on Jan 31 (UTC already Feb 1), the late-payment summary's ``today`` is
    the São Paulo date (Jan 31). The rent tracking starts in January so only January is
    scanned: with rent due exactly on Jan 31 (== SP today) and unpaid, the lease is NOT
    late (``today > due_date`` is false). With the UTC bug ``today`` would be Feb 1, so
    Feb 1 > Jan 31 would wrongly mark it late."""
    from core.models import FinancialSettings

    # Bound the back-scan to January so the months before tracking (Jun-Dec 2025) don't
    # dominate — this isolates the timezone effect on the current month.
    FinancialSettings.objects.create(
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 1, 1),
        rent_tracking_start_date=date(2026, 1, 1),
    )

    summary = DashboardService.get_late_payment_summary()
    # SP today is exactly the Jan 31 due day → not late. UTC (Feb 1) would mark it late.
    assert summary["total_late_leases"] == 0
