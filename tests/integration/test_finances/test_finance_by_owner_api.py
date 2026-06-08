"""Session 49 — finance-dashboard/by_owner: household + external owners, cache, permissions."""

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
    make_lease,
    make_person,
    make_rent_payment,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

BY_OWNER_URL = "/api/finances/finance-dashboard/by_owner/"
JULY = date(2026, 7, 1)


def _active_bill(amount: str):
    bill = make_bill(competence_month=JULY, lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time("2026-07-15 12:00:00")
def test_by_owner_shape_household_and_externals(authenticated_api_client):
    lease = make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_rent_payment(lease=lease, reference_month=JULY, amount_paid=Decimal("1000.00"))
    _active_bill("400.00")
    make_lease(
        apartment=make_apartment(
            building=make_building(street_number=9010),
            number=901,
            owner=make_person(name="Tiago", is_owner=True),
        ),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
    )
    resp = authenticated_api_client.get(f"{BY_OWNER_URL}?year=2026&month=7")
    assert resp.status_code == status.HTTP_200_OK
    household = resp.data["household"]
    assert household["name"] == "Raul & Célia"
    assert household["result_of_month"] == "600.00"  # owner rent NOT in the household net
    assert isinstance(household["available"], str)
    assert resp.data["external_owners"][0]["owner_name"] == "Tiago"
    assert resp.data["external_total"] == "800.00"


@freeze_time("2026-07-15 12:00:00")
def test_by_owner_defaults_to_current_sp_month(authenticated_api_client):
    resp = authenticated_api_client.get(BY_OWNER_URL)
    assert resp.status_code == status.HTTP_200_OK
    assert (resp.data["year"], resp.data["month"]) == (2026, 7)


@freeze_time("2026-07-15 12:00:00")
def test_by_owner_invalid_params(authenticated_api_client):
    assert (
        authenticated_api_client.get(f"{BY_OWNER_URL}?year=2026&month=13").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{BY_OWNER_URL}?year=abc&month=7").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{BY_OWNER_URL}?building_id=abc").status_code
        == status.HTTP_400_BAD_REQUEST
    )


@freeze_time("2026-07-15 12:00:00")
def test_by_owner_cached_and_invalidated(authenticated_api_client):
    bill = _active_bill("100.00")
    url = f"{BY_OWNER_URL}?year=2026&month=7"
    first = authenticated_api_client.get(url)
    assert first.data["household"]["result_of_month"] == "-100.00"  # now cached
    # bulk update bypasses signals → cache NOT invalidated → stale value still served
    BillLineItem.objects.filter(bill=bill).update(amount=Decimal("500.00"))
    cached = authenticated_api_client.get(url)
    assert cached.data["household"]["result_of_month"] == "-100.00"
    # a normal save fires the finance-* signal → cache invalidated → fresh value
    bill.save()
    fresh = authenticated_api_client.get(url)
    assert fresh.data["household"]["result_of_month"] == "-500.00"


@freeze_time("2026-07-15 12:00:00")
def test_by_owner_does_not_share_cache_with_overview(authenticated_api_client):
    # Same (year, month, building_id) on both endpoints, no cache clear between → the cached helpers
    # must use distinct keys, else by_owner would serve overview's dict payload (cache_result keys
    # on (prefix, *args) and ignores the function name).
    overview = authenticated_api_client.get(
        "/api/finances/finance-dashboard/overview/?year=2026&month=7"
    )
    by_owner = authenticated_api_client.get(f"{BY_OWNER_URL}?year=2026&month=7")
    assert "household" in by_owner.data
    assert "external_total" in by_owner.data
    assert "household" not in overview.data  # not the by_owner payload
    assert "result_of_month" in overview.data


@freeze_time("2026-07-15 12:00:00")
def test_by_owner_readable_by_non_admin(regular_authenticated_api_client):
    resp = regular_authenticated_api_client.get(f"{BY_OWNER_URL}?year=2026&month=7")
    assert resp.status_code == status.HTTP_200_OK


def test_by_owner_requires_authentication(api_client):
    resp = api_client.get(f"{BY_OWNER_URL}?year=2026&month=7")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
