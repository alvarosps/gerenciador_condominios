"""Review follow-ups — payment/reserve write-path integrity + query-param coercion.

Regression tests for the deep-review findings: CRUD DELETE of a payment must route through the
reversal path (not orphan allocations), payment amount/funded_from are immutable over the API,
reserve-movements is a read-only ledger, funded_from is validated, and malformed filter params
fail closed with a 400 (never a 500).
"""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill, Payment, PaymentAllocation
from finances.services.condo_balance_service import CondoBalanceService
from freezegun import freeze_time
from rest_framework import status

from tests.factories import make_bill, make_bill_line_item, make_reserve, make_reserve_movement

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-01 12:00:00"


def _bill_with_total(amount: str, **kwargs) -> Bill:
    bill = make_bill(**kwargs)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time(FROZEN)
def test_delete_payment_reverses_allocation_and_reopens_bill(authenticated_api_client):
    bill = _bill_with_total("900.00")
    pay = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )
    assert pay.data["payment_status"] == "paid"
    payment = Payment.objects.get()

    resp = authenticated_api_client.delete(f"/api/finances/payments/{payment.id}/")

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.payment_status == "open"  # not falsely "paid"
    assert annotated.amount_remaining == Decimal("900.00")
    assert PaymentAllocation.objects.filter(bill=bill).count() == 0  # allocation soft-deleted too


@freeze_time(FROZEN)
def test_delete_reserve_funded_payment_restores_reserve(authenticated_api_client):
    bill = _bill_with_total("300.00")
    reserve = make_reserve(condominium=bill.condominium)
    make_reserve_movement(reserve=reserve, kind="deposit", amount=Decimal("500.00"))
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("500.00")

    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "funded_from": "reserve"},
        format="json",
    )
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("200.00")
    payment = Payment.objects.get()

    resp = authenticated_api_client.delete(f"/api/finances/payments/{payment.id}/")

    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("500.00")  # restored


@freeze_time(FROZEN)
def test_patch_payment_cannot_mutate_amount_or_funded_from(authenticated_api_client):
    bill = _bill_with_total("900.00")
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "amount": "300.00"},
        format="json",
    )
    payment = Payment.objects.get()

    resp = authenticated_api_client.patch(
        f"/api/finances/payments/{payment.id}/",
        {"amount": "999.00", "funded_from": "reserve"},
        format="json",
    )

    # The default payment write route is blocked (405 PT) — change a payment only via unpay()+pay().
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    payment.refresh_from_db()
    assert payment.amount == Decimal("300.00")  # unchanged
    assert payment.funded_from == "caixa"


def test_reserve_movements_create_is_method_not_allowed(authenticated_api_client):
    reserve = make_reserve()
    resp = authenticated_api_client.post(
        "/api/finances/reserve-movements/",
        {
            "reserve_id": reserve.id,
            "kind": "withdrawal",
            "amount": "999.00",
            "movement_date": "2026-06-05",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@freeze_time(FROZEN)
def test_pay_rejects_unknown_funded_from(authenticated_api_client):
    bill = _bill_with_total("100.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "funded_from": "xpto"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert Payment.objects.count() == 0


def test_malformed_building_id_filter_is_400(authenticated_api_client):
    resp = authenticated_api_client.get("/api/finances/bills/?building_id=abc")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
