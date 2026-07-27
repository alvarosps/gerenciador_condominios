"""Session 70 — POST billing-accounts/{id}/consolidate_debt (N open bills -> 1 plan, atomic)."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from finances.models import Bill, BillingAccountType, BillLifecycleState, InstallmentPlan
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condo_month_close,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"


def _url(account_id: object) -> str:
    return f"/api/finances/billing-accounts/{account_id}/consolidate_debt/"


def _open_bill(account, amount: str, **kwargs) -> Bill:
    bill = make_bill(condominium=account.condominium, billing_account=account, **kwargs)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


def _payload(bill_ids: list[int], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "bill_ids": bill_ids,
        "embedded": False,
        "installment_count": 3,
        "start_due_date": "2026-08-10",
        "default_due_day": 10,
    }
    payload.update(overrides)
    return payload


@freeze_time(FROZEN)
def test_consolidate_debt_requires_authentication(api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)
    bill = _open_bill(account, "100.00")

    resp = api_client.post(_url(account.id), _payload([bill.id]), format="json")

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@freeze_time(FROZEN)
def test_consolidate_debt_forbidden_for_non_admin(regular_authenticated_api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)
    bill = _open_bill(account, "100.00")

    resp = regular_authenticated_api_client.post(
        _url(account.id), _payload([bill.id]), format="json"
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@freeze_time(FROZEN)
def test_consolidate_debt_happy_path_returns_201_plan(authenticated_api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)
    bill1 = _open_bill(account, "300.00", competence_month=date(2026, 5, 1))
    bill2 = _open_bill(account, "200.00", competence_month=date(2026, 6, 1))

    resp = authenticated_api_client.post(
        _url(account.id), _payload([bill1.id, bill2.id]), format="json"
    )

    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["total_amount"] == "500.00"
    assert len(resp.data["installments"]) == 3
    assert resp.data["billing_account"]["id"] == account.id

    bill1.refresh_from_db()
    bill2.refresh_from_db()
    assert bill1.lifecycle_state == BillLifecycleState.CANCELED
    assert bill2.lifecycle_state == BillLifecycleState.CANCELED


@freeze_time(FROZEN)
def test_consolidate_debt_invalid_payload_returns_400(authenticated_api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)

    resp_missing = authenticated_api_client.post(
        _url(account.id),
        {
            "embedded": False,
            "installment_count": 3,
            "start_due_date": "2026-08-10",
            "default_due_day": 10,
        },
        format="json",
    )
    assert resp_missing.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp_missing.data

    bill = _open_bill(account, "100.00")
    resp_bad_date = authenticated_api_client.post(
        _url(account.id), _payload([bill.id], start_due_date="not-a-date"), format="json"
    )
    assert resp_bad_date.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp_bad_date.data

    resp_empty_ids = authenticated_api_client.post(_url(account.id), _payload([]), format="json")
    assert resp_empty_ids.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp_empty_ids.data


@freeze_time(FROZEN)
def test_consolidate_debt_non_bool_embedded_returns_400(authenticated_api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)
    bill = _open_bill(account, "100.00")

    resp = authenticated_api_client.post(
        _url(account.id), _payload([bill.id], embedded="false"), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.data
    assert InstallmentPlan.objects.count() == 0
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.ACTIVE


@freeze_time(FROZEN)
def test_consolidate_debt_non_int_bill_ids_returns_400(authenticated_api_client):
    """bool/float bill_ids items must be rejected, not silently coerced (True -> 1, 3.7 -> 3)."""
    account = make_billing_account(account_type=BillingAccountType.WATER)
    bill = _open_bill(account, "100.00")

    resp_bool = authenticated_api_client.post(_url(account.id), _payload([True]), format="json")
    assert resp_bool.status_code == status.HTTP_400_BAD_REQUEST
    assert InstallmentPlan.objects.count() == 0

    resp_float_count = authenticated_api_client.post(
        _url(account.id), _payload([bill.id], installment_count=3.7), format="json"
    )
    assert resp_float_count.status_code == status.HTTP_400_BAD_REQUEST
    assert InstallmentPlan.objects.count() == 0
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.ACTIVE


@freeze_time(FROZEN)
def test_consolidate_debt_cross_account_bill_returns_400(authenticated_api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)
    other_account = make_billing_account(
        condominium=account.condominium,
        account_type=BillingAccountType.ELECTRICITY,
        external_identifier="UC-OTHER",
    )
    foreign_bill = _open_bill(other_account, "150.00")

    resp = authenticated_api_client.post(
        _url(account.id), _payload([foreign_bill.id]), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert InstallmentPlan.objects.count() == 0
    foreign_bill.refresh_from_db()
    assert foreign_bill.lifecycle_state == BillLifecycleState.ACTIVE


@freeze_time(FROZEN)
def test_consolidate_debt_closed_month_returns_400(authenticated_api_client):
    account = make_billing_account(account_type=BillingAccountType.WATER)
    closed_bill = _open_bill(account, "200.00", competence_month=date(2026, 6, 1))
    make_condo_month_close(
        condominium=account.condominium, reference_month=date(2026, 6, 1), status="closed"
    )

    resp = authenticated_api_client.post(
        _url(account.id), _payload([closed_bill.id]), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "fechado" in resp.data["error"]
    assert InstallmentPlan.objects.count() == 0


@freeze_time(FROZEN)
def test_consolidate_debt_embedded_iptu_returns_400(authenticated_api_client):
    account = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="IPTU-70API"
    )
    bill = _open_bill(account, "100.00")

    resp = authenticated_api_client.post(
        _url(account.id), _payload([bill.id], embedded=True, installment_count=1), format="json"
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert InstallmentPlan.objects.count() == 0


@freeze_time(FROZEN)
def test_consolidate_debt_unknown_account_returns_404(authenticated_api_client):
    resp = authenticated_api_client.post(_url(999999), _payload([1]), format="json")

    assert resp.status_code == status.HTTP_404_NOT_FOUND
