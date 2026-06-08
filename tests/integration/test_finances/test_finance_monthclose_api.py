"""Session 45 — condo-month-closes API: list, close/reopen, chronological gap, closed-month write block."""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import BillLifecycleState
from freezegun import freeze_time
from rest_framework import status

from core.models import FinancialSettings
from tests.factories import make_bill, make_bill_line_item

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _active_bill(amount: str, competence_month: date):
    bill = make_bill(competence_month=competence_month, lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time("2026-07-15")
def test_list_and_close(authenticated_api_client):
    resp = authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "closed"
    assert resp.data["closed_at"] is not None
    listing = authenticated_api_client.get("/api/finances/condo-month-closes/")
    assert listing.status_code == status.HTTP_200_OK
    assert any(c["reference_month"] == "2026-07-01" for c in listing.data["results"])


@freeze_time("2026-07-15")
def test_close_invalid_month(authenticated_api_client):
    resp = authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 13}, format="json"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-15")
def test_close_chronological_gap(authenticated_api_client):
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 5, 1),
        rent_tracking_start_date=date(2026, 5, 1),
    )
    gap = authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    assert gap.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-15")
def test_close_already_closed(authenticated_api_client):
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    again = authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    assert again.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-15")
def test_reopen(authenticated_api_client):
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    reopened = authenticated_api_client.post(
        "/api/finances/condo-month-closes/reopen/", {"year": 2026, "month": 7}, format="json"
    )
    assert reopened.status_code == status.HTTP_200_OK
    assert reopened.data["status"] == "open"
    missing = authenticated_api_client.post(
        "/api/finances/condo-month-closes/reopen/", {"year": 2026, "month": 8}, format="json"
    )
    assert missing.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-15")
def test_pay_blocked_on_closed_month(authenticated_api_client):
    bill = _active_bill("200.00", date(2026, 7, 1))
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 7}, format="json"
    )
    blocked = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-07-16", "amount": "200.00"},
        format="json",
    )
    assert blocked.status_code == status.HTTP_400_BAD_REQUEST
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/reopen/", {"year": 2026, "month": 7}, format="json"
    )
    allowed = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-07-16", "amount": "200.00"},
        format="json",
    )
    assert allowed.status_code == status.HTTP_200_OK
