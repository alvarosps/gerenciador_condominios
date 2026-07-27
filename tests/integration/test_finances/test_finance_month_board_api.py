"""Session 66 — GET finance-dashboard/month_board (uncached)."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from tests.factories import make_bill, make_bill_line_item

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"
MONTH_BOARD_URL = "/api/finances/finance-dashboard/month_board/"


@freeze_time(FROZEN)
def test_month_board_returns_full_shape(authenticated_api_client):
    resp = authenticated_api_client.get(f"{MONTH_BOARD_URL}?year=2026&month=7")

    assert resp.status_code == status.HTTP_200_OK
    assert set(resp.data.keys()) == {
        "overdue",
        "deferred_suspended",
        "groups",
        "totals",
        "generation",
    }
    assert set(resp.data["totals"].keys()) == {"due", "paid", "remaining", "overdue"}
    assert set(resp.data["generation"].keys()) == {"missing_count"}


@freeze_time(FROZEN)
def test_month_board_defaults_to_current_sp_month(authenticated_api_client):
    bill = make_bill(competence_month=date(2026, 7, 1))
    make_bill_line_item(bill=bill, amount=Decimal("50.00"))

    resp = authenticated_api_client.get(MONTH_BOARD_URL)

    assert resp.status_code == status.HTTP_200_OK
    group_ids = {b["id"] for g in resp.data["groups"] for b in g["bills"]}
    assert bill.id in group_ids


@freeze_time(FROZEN)
def test_month_board_invalid_month_returns_400(authenticated_api_client):
    resp = authenticated_api_client.get(f"{MONTH_BOARD_URL}?year=2026&month=13")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_month_board_non_numeric_year_returns_400(authenticated_api_client):
    resp = authenticated_api_client.get(f"{MONTH_BOARD_URL}?year=abc&month=7")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_month_board_forbidden_for_non_admin(regular_authenticated_api_client):
    resp = regular_authenticated_api_client.get(MONTH_BOARD_URL)

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@freeze_time(FROZEN)
def test_month_board_requires_authentication(api_client):
    resp = api_client.get(MONTH_BOARD_URL)

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@freeze_time(FROZEN)
def test_month_board_uncached_reflects_payment(authenticated_api_client):
    bill = make_bill(competence_month=date(2026, 6, 1), due_date=date(2026, 6, 10))
    make_bill_line_item(bill=bill, amount=Decimal("500.00"))

    first = authenticated_api_client.get(f"{MONTH_BOARD_URL}?year=2026&month=7")
    ids_before = {b["id"] for b in first.data["overdue"]}
    assert bill.id in ids_before

    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )

    second = authenticated_api_client.get(f"{MONTH_BOARD_URL}?year=2026&month=7")
    ids_after = {b["id"] for b in second.data["overdue"]}
    assert bill.id not in ids_after
