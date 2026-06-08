"""Session 45 — finance-dashboard/{overview,monthly_balance,by_category}: KPIs, series, donut, cache."""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import BillLifecycleState, BillLineItem
from freezegun import freeze_time
from rest_framework import status

from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_building,
    make_condominium,
    make_finance_category,
    make_lease,
    make_rent_payment,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

JULY = date(2026, 7, 1)


def _active_bill(amount: str, *, category=None):
    bill = make_bill(
        competence_month=JULY, lifecycle_state=BillLifecycleState.ACTIVE, category=category
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time("2026-07-01 12:00:00")
def test_overview_kpis(authenticated_api_client):
    building = make_building(street_number=7001)
    apartment = make_apartment(building=building)
    lease = make_lease(
        apartment=apartment, rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1)
    )
    make_rent_payment(lease=lease, reference_month=JULY, amount_paid=Decimal("1000.00"))
    _active_bill("400.00")
    resp = authenticated_api_client.get(
        "/api/finances/finance-dashboard/overview/?year=2026&month=7"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["result_of_month"] == "600.00"
    assert resp.data["cash_change_of_month"] == "1000.00"  # received rent only; bill unpaid
    assert isinstance(resp.data["overdue_bills_count"], int)
    assert resp.data["wedge_ok"] is True
    assert "total_fee" in resp.data["rent_overdue"]


@freeze_time("2026-07-01 12:00:00")
def test_monthly_balance_series(authenticated_api_client):
    make_condominium()  # close() needs the default condominium (self-contained, no ambient state)
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    resp = authenticated_api_client.get(
        "/api/finances/finance-dashboard/monthly_balance/?year=2026"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["months"]) == 12
    july = next(m for m in resp.data["months"] if m["month"] == 7)
    august = next(m for m in resp.data["months"] if m["month"] == 8)
    assert july["is_closed"] is True
    assert august["is_closed"] is False
    assert isinstance(july["cash_balance_end"], str)


@pytest.mark.parametrize(
    "url",
    [
        "/api/finances/finance-dashboard/overview/?year=2026&month=7&building_id=abc",
        "/api/finances/finance-dashboard/monthly_balance/?year=2026&building_id=abc",
        "/api/finances/finance-dashboard/by_category/?year=2026&month=7&building_id=abc",
        "/api/finances/finance-dashboard/combined_calendar/?year=2026&month=7&building_id=abc",
        "/api/finances/finance-dashboard/overdue/?building_id=abc",
    ],
)
def test_malformed_building_id_is_400_not_500(authenticated_api_client, url):
    assert authenticated_api_client.get(url).status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-01 12:00:00")
def test_by_category_donut(authenticated_api_client):
    energia = make_finance_category(name="Energia", color="#f59e0b")
    _active_bill("250.00", category=energia)
    resp = authenticated_api_client.get(
        "/api/finances/finance-dashboard/by_category/?year=2026&month=7"
    )
    assert resp.status_code == status.HTTP_200_OK
    energia_row = next(c for c in resp.data["categories"] if c["name"] == "Energia")
    assert energia_row["total"] == "250.00"
    assert energia_row["color"] == "#f59e0b"


@freeze_time("2026-07-01 12:00:00")
def test_invalid_params(authenticated_api_client):
    bad_month = authenticated_api_client.get(
        "/api/finances/finance-dashboard/overview/?year=2026&month=13"
    )
    assert bad_month.status_code == status.HTTP_400_BAD_REQUEST
    bad_year = authenticated_api_client.get(
        "/api/finances/finance-dashboard/overview/?year=abc&month=7"
    )
    assert bad_year.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-01 12:00:00")
def test_overview_and_by_category_do_not_share_cache(authenticated_api_client):
    # Same (year, month, building_id) on both endpoints, no cache clear between → the two cached
    # helpers must use distinct keys, else by_category would serve overview's dict payload.
    energia = make_finance_category(name="Energia", color="#f59e0b")
    _active_bill("250.00", category=energia)
    overview = authenticated_api_client.get(
        "/api/finances/finance-dashboard/overview/?year=2026&month=7"
    )
    by_cat = authenticated_api_client.get(
        "/api/finances/finance-dashboard/by_category/?year=2026&month=7"
    )
    assert "result_of_month" in overview.data
    assert "categories" in by_cat.data
    assert "result_of_month" not in by_cat.data  # not the overview payload


@freeze_time("2026-07-01 12:00:00")
def test_overview_cached_and_invalidated(authenticated_api_client):
    bill = _active_bill("100.00")
    url = "/api/finances/finance-dashboard/overview/?year=2026&month=7"
    first = authenticated_api_client.get(url)
    assert first.data["result_of_month"] == "-100.00"  # now cached
    # bulk update bypasses signals → cache NOT invalidated → stale value still served
    BillLineItem.objects.filter(bill=bill).update(amount=Decimal("500.00"))
    cached = authenticated_api_client.get(url)
    assert cached.data["result_of_month"] == "-100.00"
    # a normal save fires the finance-* signal → cache invalidated → fresh value
    bill.save()
    fresh = authenticated_api_client.get(url)
    assert fresh.data["result_of_month"] == "-500.00"
