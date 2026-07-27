"""Session 38 — Bill action endpoints (pay/bulk_pay/lifecycle/generate_month/create_with_lines)."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from finances.models import Bill, BillLifecycleState, BillLineItem, Payment, PaymentAllocation
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


# --- B4: a paid Bill cannot be destroyed/suspended/canceled (unpay first) ---


@freeze_time(FROZEN)
def test_destroy_rejects_paid_bill(authenticated_api_client):
    bill = _bill_total("300.00")
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )
    resp = authenticated_api_client.delete(f"/api/finances/bills/{bill.id}/")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.filter(pk=bill.id).exists()


@freeze_time(FROZEN)
def test_suspend_rejects_paid_bill(authenticated_api_client):
    bill = _bill_total("300.00")
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )
    resp = authenticated_api_client.post(f"/api/finances/bills/{bill.id}/suspend/")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.ACTIVE


@freeze_time(FROZEN)
def test_cancel_rejects_paid_bill(authenticated_api_client):
    bill = _bill_total("300.00")
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )
    resp = authenticated_api_client.post(f"/api/finances/bills/{bill.id}/cancel/")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.ACTIVE


# --- Session 68: pay(new_total=...) at the action level ---


@freeze_time(FROZEN)
def test_pay_action_accepts_new_total_string(authenticated_api_client):
    """Action repassa new_total (decimal string) e devolve a bill ajustada."""
    bill = make_bill(amount_is_estimated=True)
    make_bill_line_item(bill=bill, amount=Decimal("200.00"), description=bill.description)
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "amount": "230.00", "new_total": "230.00"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_total"] == "230.00"
    assert resp.data["amount_is_estimated"] is False


@freeze_time(FROZEN)
def test_pay_action_invalid_new_total_returns_400(authenticated_api_client):
    """new_total inválido (não-numérico) -> 400 PT.

    _parse_new_total intercepts InvalidOperation before the generic amount/date/funded_from
    catch-all (Round 2 fix, I-1), so a non-numeric new_total now gets the specific PT format
    message instead of the generic one — still 400, still PT, just more precise.
    """
    bill = _bill_total("300.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "new_total": "abc"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["error"] == "Valor inválido: use no máximo 2 casas decimais."


@freeze_time(FROZEN)
def test_pay_action_new_total_too_many_decimal_places_returns_pt_400(authenticated_api_client):
    """new_total com 3+ casas decimais -> 400 PT (nunca a mensagem em inglês do Django)."""
    bill = _bill_total("300.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "new_total": "230.005"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["error"] == "Valor inválido: use no máximo 2 casas decimais."


@freeze_time(FROZEN)
@pytest.mark.parametrize("bad_value", ["Infinity", "-Infinity", "NaN"])
def test_pay_action_new_total_non_finite_returns_pt_400(authenticated_api_client, bad_value):
    """new_total não-finito (Infinity/NaN) -> 400 PT (nunca a mensagem em inglês do Django)."""
    bill = _bill_total("300.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "new_total": bad_value},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["error"] == "Valor inválido: use no máximo 2 casas decimais."


@freeze_time(FROZEN)
def test_pay_action_new_total_two_decimal_places_still_works(authenticated_api_client):
    """Casos válidos (<=2 casas decimais) continuam funcionando após o guard de formato."""
    bill = make_bill(amount_is_estimated=True)
    make_bill_line_item(bill=bill, amount=Decimal("200.00"), description=bill.description)
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "amount": "230.00", "new_total": "230.00"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_total"] == "230.00"


@freeze_time(FROZEN)
def test_pay_action_confirmed_reduction_returns_400(authenticated_api_client):
    """Erro de negócio PT atravessa a action como 400."""
    bill = _bill_total("300.00")
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05", "new_total": "280.00"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["error"] == "Edite a conta para reduzir o valor."


@freeze_time(FROZEN)
def test_bulk_pay_ignores_new_total(authenticated_api_client):
    """bulk_pay não ganha ajuste (contrato S68)."""
    cond = make_condominium()
    bill = _bill_total("100.00", condominium=cond)
    resp = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {"bill_ids": [bill.id], "payment_date": "2026-06-05", "new_total": "500.00"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data[0]["amount_total"] == "100.00"
    assert resp.data[0]["payment_status"] == "paid"
    assert not BillLineItem.objects.filter(bill=bill, description="Juros/multa").exists()


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
