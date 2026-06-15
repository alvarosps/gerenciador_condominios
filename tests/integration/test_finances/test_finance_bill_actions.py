"""Session 38 — Bill action endpoints (pay/bulk_pay/lifecycle/generate_month/create_with_lines)."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from finances.models import Bill, BillLifecycleState, Payment, PaymentAllocation
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_bill_skip,
    make_billing_account,
    make_condominium,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-01 12:00:00"


def _bill_total(amount: str, **kwargs) -> Bill:
    bill = make_bill(**kwargs)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time(FROZEN)
def test_pay_total(authenticated_api_client):
    bill = _bill_total("900.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["payment_status"] == "paid"
    assert resp.data["amount_remaining"] == "0.00"
    assert PaymentAllocation.objects.filter(bill=bill).count() == 1


@freeze_time(FROZEN)
def test_pay_partial(authenticated_api_client):
    bill = _bill_total("900.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "amount": "300.00"},
        format="json",
    )
    assert resp.data["payment_status"] == "partial"
    assert resp.data["amount_remaining"] == "600.00"


@freeze_time(FROZEN)
def test_pay_over_allocation_rejected(authenticated_api_client):
    bill = _bill_total("900.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "amount": "1000.00"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_bulk_pay_atomic(authenticated_api_client):
    cond = make_condominium()
    b1 = _bill_total("100.00", condominium=cond)
    b2 = _bill_total("200.00", condominium=cond)
    resp = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {"bill_ids": [b1.id, b2.id], "payment_date": "2026-06-05"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert Payment.objects.count() == 2
    # one missing id rolls everything back
    b3 = _bill_total("50.00", condominium=cond)
    before = Payment.objects.count()
    bad = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {"bill_ids": [b3.id, 999999], "payment_date": "2026-06-05"},
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST
    assert Payment.objects.count() == before


def test_bulk_pay_empty_rejected(authenticated_api_client):
    resp = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {"bill_ids": [], "payment_date": "2026-06-05"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_lifecycle_transitions(authenticated_api_client):
    bill = _bill_total("100.00", due_date=date(2026, 6, 10))
    suspend = authenticated_api_client.post(f"/api/finances/bills/{bill.id}/suspend/")
    assert suspend.data["lifecycle_state"] == "suspended"
    assert suspend.data["is_overdue"] is False  # suspended is never overdue
    react = authenticated_api_client.post(f"/api/finances/bills/{bill.id}/reactivate/")
    assert react.data["lifecycle_state"] == "active"


def test_reactivate_from_canceled_rejected(authenticated_api_client):
    bill = make_bill(lifecycle_state=BillLifecycleState.CANCELED)
    resp = authenticated_api_client.post(f"/api/finances/bills/{bill.id}/reactivate/")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_generate_month_idempotent_and_validates(authenticated_api_client):
    make_billing_account(expected_amount=Decimal("100.00"))
    r1 = authenticated_api_client.post(
        "/api/finances/bills/generate_month/", {"year": 2026, "month": 6}, format="json"
    )
    assert r1.status_code == status.HTTP_200_OK
    assert r1.data["created"] == 1
    authenticated_api_client.post(
        "/api/finances/bills/generate_month/", {"year": 2026, "month": 6}, format="json"
    )
    assert Bill.all_objects.filter(competence_month=date(2026, 6, 1)).count() == 1
    bad = authenticated_api_client.post(
        "/api/finances/bills/generate_month/", {"year": 2026, "month": 13}, format="json"
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST


def test_generate_month_respects_skip(authenticated_api_client):
    account = make_billing_account(expected_amount=Decimal("100.00"))
    make_bill_skip(billing_account=account, reference_month=date(2026, 6, 1))
    resp = authenticated_api_client.post(
        "/api/finances/bills/generate_month/", {"year": 2026, "month": 6}, format="json"
    )
    assert resp.data["created"] == 0


@freeze_time(FROZEN)
def test_create_with_lines(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/bills/create_with_lines/",
        {
            "bill": {
                "condominium_id": cond.id,
                "competence_month": "2026-06-01",
                "due_date": "2026-06-10",
                "description": "Conta com linhas",
                "behavior": "one_time",
            },
            "line_items": [
                {"description": "Consumo", "amount": "600.00"},
                {"description": "Desconto", "amount": "100.00", "is_offset": True},
            ],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["amount_total"] == "500.00"


def test_create_with_lines_negative_rejected(authenticated_api_client):
    cond = make_condominium()
    before = Bill.all_objects.count()
    resp = authenticated_api_client.post(
        "/api/finances/bills/create_with_lines/",
        {
            "bill": {
                "condominium_id": cond.id,
                "competence_month": "2026-06-01",
                "due_date": "2026-06-10",
                "description": "Ruim",
                "behavior": "one_time",
            },
            "line_items": [{"description": "Neg", "amount": "-1.00"}],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.all_objects.count() == before
