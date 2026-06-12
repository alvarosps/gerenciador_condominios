"""Session 34 — tests for the single São Paulo timezone helper.

settings.TIME_ZONE is "UTC", so timezone.now().date() is the UTC date and is
wrong around the month boundary in São Paulo (UTC-3). These tests pin that the
helper returns the São Paulo date/month, not the UTC one.
"""

from datetime import date, datetime

from django.utils import timezone
from freezegun import freeze_time

from core.services.timezone import (
    SAO_PAULO_TZ,
    current_month_sp,
    now_sp,
    today_sp,
)


@freeze_time("2026-06-15 12:00:00")
def test_current_month_sp_is_first_day() -> None:
    assert current_month_sp().day == 1


@freeze_time("2026-07-01 02:00:00")
def test_month_boundary_utc_ahead_of_sp() -> None:
    """UTC has rolled into July while São Paulo is still on June 30, 23:00."""
    # UTC date would be July 1 — the bug the helper exists to avoid.
    assert timezone.now().date() == date(2026, 7, 1)
    # São Paulo (UTC-3) is still June.
    assert today_sp() == date(2026, 6, 30)
    assert current_month_sp() == date(2026, 6, 1)


@freeze_time("2026-08-01 12:00:00")
def test_month_boundary_both_in_new_month() -> None:
    """Mid-day UTC: both UTC and São Paulo agree it is August."""
    assert today_sp() == date(2026, 8, 1)
    assert current_month_sp() == date(2026, 8, 1)
    assert timezone.now().date() == date(2026, 8, 1)


@freeze_time("2026-06-15 12:00:00")
def test_now_sp_timezone_and_today_is_date() -> None:
    assert now_sp().tzinfo is SAO_PAULO_TZ
    today = today_sp()
    assert isinstance(today, date)
    assert not isinstance(today, datetime)
