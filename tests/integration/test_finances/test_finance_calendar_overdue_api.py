"""Session 38 — combined_calendar (entries/exits) + overdue endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_lease,
    make_tenant,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"
CAL_URL = "/api/finances/finance-dashboard/combined_calendar/"
OVERDUE_URL = "/api/finances/finance-dashboard/overdue/"


def _day(days: list[dict], day_num: int) -> dict:
    return next(d for d in days if d["day"] == day_num)


@freeze_time(FROZEN)
def test_combined_calendar_shape_entries_and_exits(authenticated_api_client):
    apartment = make_apartment()
    # Explicit valid CPF (not the shared _cpf_cycle, which is global mutable state).
    make_lease(apartment=apartment, tenant=make_tenant(cpf_cnpj="52998224725", due_day=10))
    bill = make_bill(building=apartment.building, due_date=date(2026, 7, 20))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))

    resp = authenticated_api_client.get(f"{CAL_URL}?year=2026&month=7")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["year"] == 2026
    assert resp.data["month"] == 7
    assert "today" in resp.data
    # rent entry on the lease's clamped due day (10)
    assert len(_day(resp.data["days"], 10)["rent_entries"]) >= 1
    # bill exit on the bill's due day (20)
    exits = _day(resp.data["days"], 20)["bill_exits"]
    assert any(e["bill_id"] == bill.id for e in exits)


@freeze_time(FROZEN)
def test_combined_calendar_no_cache_reflects_payment(authenticated_api_client):
    bill = make_bill(due_date=date(2026, 7, 20))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))
    first = authenticated_api_client.get(f"{CAL_URL}?year=2026&month=7")
    exit_before = next(
        e for e in _day(first.data["days"], 20)["bill_exits"] if e["bill_id"] == bill.id
    )
    assert exit_before["payment_status"] == "open"
    # pay it via the API, then GET again — must reflect immediately (uncached)
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-07-05"}, format="json"
    )
    second = authenticated_api_client.get(f"{CAL_URL}?year=2026&month=7")
    exit_after = next(
        e for e in _day(second.data["days"], 20)["bill_exits"] if e["bill_id"] == bill.id
    )
    assert exit_after["payment_status"] == "paid"


@freeze_time(FROZEN)
def test_combined_calendar_invalid_params(authenticated_api_client):
    assert (
        authenticated_api_client.get(f"{CAL_URL}?year=2026&month=13").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{CAL_URL}?year=abc&month=7").status_code
        == status.HTTP_400_BAD_REQUEST
    )


@freeze_time(FROZEN)
def test_overdue_endpoint(authenticated_api_client):
    overdue = make_bill(due_date=date(2026, 6, 10))
    make_bill_line_item(bill=overdue, amount=Decimal("500.00"))
    deferred = make_bill(due_date=date(2026, 6, 10), lifecycle_state="deferred")
    make_bill_line_item(bill=deferred, amount=Decimal("700.00"))
    paid = make_bill(due_date=date(2026, 6, 10))
    make_bill_line_item(bill=paid, amount=Decimal("100.00"))
    authenticated_api_client.post(
        f"/api/finances/bills/{paid.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )

    resp = authenticated_api_client.get(OVERDUE_URL)
    assert resp.status_code == status.HTTP_200_OK
    ids = {b["id"] for b in resp.data["bills"]}
    assert overdue.id in ids
    assert deferred.id not in ids  # deferred excluded
    assert paid.id not in ids  # fully paid excluded
    assert resp.data["overdue_bills_total"] == "500.00"  # Σ amount_remaining, not amount_total
    assert "rent_overdue" in resp.data
    assert set(resp.data["rent_overdue"].keys()) == {"count", "total_fee"}
