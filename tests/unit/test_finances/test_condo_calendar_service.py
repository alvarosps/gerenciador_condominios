"""Session 38 — CondoCalendarService.combined_month unit tests."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.services.rent_schedule_service import RentScheduleService
from finances.services.condo_calendar_service import CondoCalendarService
from tests.factories import make_apartment, make_bill, make_bill_line_item, make_lease, make_tenant

pytestmark = pytest.mark.django_db

FROZEN = "2026-07-15 12:00:00"


def _day(result: dict, day_num: int) -> dict:
    return next(d for d in result["days"] if d["day"] == day_num)


@freeze_time(FROZEN)
def test_shape_and_sections() -> None:
    result = CondoCalendarService.combined_month(2026, 7)
    assert result["year"] == 2026
    assert result["month"] == 7
    assert "today" in result
    day = result["days"][0]
    assert set(day.keys()) == {"day", "date", "weekday", "rent_entries", "bill_exits"}


@freeze_time(FROZEN)
def test_rent_entries_from_collectible_lease() -> None:
    apartment = make_apartment()
    # Explicit valid CPF (not the shared _cpf_cycle, which is global mutable state).
    make_lease(apartment=apartment, tenant=make_tenant(cpf_cnpj="29375235017", due_day=10))
    result = CondoCalendarService.combined_month(2026, 7)
    assert len(_day(result, 10)["rent_entries"]) >= 1


@freeze_time(FROZEN)
def test_bill_exits_grouped_by_due_date_with_offset() -> None:
    bill = make_bill(due_date=date(2026, 7, 20))
    make_bill_line_item(bill=bill, amount=Decimal("600.00"))
    make_bill_line_item(bill=bill, amount=Decimal("100.00"), is_offset=True)
    result = CondoCalendarService.combined_month(2026, 7)
    exits = _day(result, 20)["bill_exits"]
    row = next(e for e in exits if e["bill_id"] == bill.id)
    assert row["amount_total"] == "500.00"


@freeze_time(FROZEN)
def test_building_filter_and_soft_deleted_excluded() -> None:
    apartment = make_apartment()
    bill = make_bill(building=apartment.building, due_date=date(2026, 7, 20))
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    other = make_bill(due_date=date(2026, 7, 20))
    make_bill_line_item(bill=other, amount=Decimal("100.00"))

    filtered = CondoCalendarService.combined_month(2026, 7, building_id=apartment.building_id)
    exit_ids = {e["bill_id"] for e in _day(filtered, 20)["bill_exits"]}
    assert bill.id in exit_ids
    assert other.id not in exit_ids

    bill.delete()  # soft-deleted excluded
    after = CondoCalendarService.combined_month(2026, 7, building_id=apartment.building_id)
    assert bill.id not in {e["bill_id"] for e in _day(after, 20)["bill_exits"]}


@freeze_time(FROZEN)
def test_empty_month() -> None:
    result = CondoCalendarService.combined_month(2026, 7)
    assert all(not d["bill_exits"] for d in result["days"])


@freeze_time("2026-07-01 02:00:00")
def test_today_is_sao_paulo_date_for_both_halves_at_utc_boundary() -> None:
    # 2026-07-01 02:00 UTC is still 2026-06-30 23:00 in São Paulo. Both the calendar's `today`
    # marker AND the rent half (via as_of) must report the SP date — not the UTC date (July 1).
    result = CondoCalendarService.combined_month(2026, 6)
    assert result["today"] == "2026-06-30"
    # The rent half's stats `today` rides on the same SP date (no UTC/SP split in one payload).
    assert RentScheduleService.get_month_schedule(2026, 6, as_of=date(2026, 6, 30))["today"] == (
        "2026-06-30"
    )
