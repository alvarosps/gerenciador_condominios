"""P2.3 — viewset/serializer write-guard integrity for the finances API.

The default DRF CRUD write routes of Bill / Payment / CondoMonthClose bypassed the rich-path
guards, letting a client: rewrite competence_month / pay a frozen bill via PATCH /bills/, 500 on
POST /payments/ (amount read-only), HARD-DELETE a closed CondoMonthClose snapshot (destroying the
cash-fold baseline), and persist BillSkip.reference_month un-normalized (DRF skips Model.clean()).
These tests pin the closed routes (405) while the canonical rich paths (create_with_lines /
update_with_lines / pay / close / reopen) and the still-needed default routes stay intact.
"""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill, BillSkip, CondoMonthClose, Payment
from freezegun import freeze_time
from rest_framework import status

from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condominium,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-01 12:00:00"


def _bill_with_total(amount: str, **kwargs) -> Bill:
    bill = make_bill(**kwargs)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


# --- BillSkip reference_month day-1 normalization (P2.3 step 8) ---


def test_bill_skip_normalizes_reference_month_to_day_one(authenticated_api_client):
    account = make_billing_account()
    resp = authenticated_api_client.post(
        "/api/finances/bill-skips/",
        {"billing_account_id": account.id, "reference_month": "2026-06-15"},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    skip = BillSkip.objects.get()
    assert skip.reference_month == date(2026, 6, 1)  # normalized, not 06-15


# --- BillViewSet default writes (P2.3 step 4) ---


def test_bill_default_post_is_405(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/bills/",
        {
            "condominium_id": cond.id,
            "competence_month": "2026-06-01",
            "due_date": "2026-06-10",
            "description": "Avulsa",
            "behavior": "one_time",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_bill_default_patch_cannot_change_competence_month(authenticated_api_client):
    bill = _bill_with_total("100.00", competence_month=date(2026, 6, 1))
    resp = authenticated_api_client.patch(
        f"/api/finances/bills/{bill.id}/",
        {"competence_month": "2026-05-01"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    bill.refresh_from_db()
    assert bill.competence_month == date(2026, 6, 1)  # immutable — PATCH ignores it


@freeze_time(FROZEN)
def test_bill_default_patch_cannot_pay_or_touch_lines(authenticated_api_client):
    """A header-only PATCH of an editable field succeeds; it never alters lines/payment."""
    bill = _bill_with_total("100.00", competence_month=date(2026, 6, 1))
    resp = authenticated_api_client.patch(
        f"/api/finances/bills/{bill.id}/",
        {"description": "Editado"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    bill.refresh_from_db()
    assert bill.description == "Editado"
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("100.00")  # lines untouched
    assert annotated.payment_status == "open"


@freeze_time(FROZEN)
def test_bill_default_patch_rejected_on_closed_month(authenticated_api_client):
    bill = _bill_with_total("100.00", competence_month=date(2026, 6, 1))
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}, format="json"
    )
    resp = authenticated_api_client.patch(
        f"/api/finances/bills/{bill.id}/",
        {"description": "Editado"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    bill.refresh_from_db()
    assert bill.description == "Conta Teste"  # unchanged


@freeze_time(FROZEN)
def test_bill_create_with_lines_still_works(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/bills/create_with_lines/",
        {
            "bill": {
                "condominium_id": cond.id,
                "competence_month": "2026-06-01",
                "due_date": "2026-06-10",
                "description": "Avulsa",
                "behavior": "one_time",
            },
            "line_items": [{"description": "Item", "amount": "150.00"}],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["amount_total"] == "150.00"


@freeze_time(FROZEN)
def test_bill_update_with_lines_still_works(authenticated_api_client):
    bill = _bill_with_total("100.00", competence_month=date(2026, 6, 1))
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": [{"description": "Novo", "amount": "200.00"}]},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_total"] == "200.00"


# --- PaymentViewSet default writes (P2.3 step 3) ---


@freeze_time(FROZEN)
def test_payment_default_post_is_405(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/payments/",
        {"condominium_id": cond.id, "payment_date": "2026-06-05", "amount": "100.00"},
        format="json",
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_payment_default_patch_is_405(authenticated_api_client):
    bill = _bill_with_total("100.00")
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05"},
        format="json",
    )
    payment = Payment.objects.get()
    resp = authenticated_api_client.patch(
        f"/api/finances/payments/{payment.id}/",
        {"payment_date": "2026-06-09"},
        format="json",
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    payment.refresh_from_db()
    assert payment.payment_date == date(2026, 6, 5)  # unchanged


@freeze_time(FROZEN)
def test_payment_destroy_still_unpays(authenticated_api_client):
    bill = _bill_with_total("100.00")
    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/",
        {"payment_date": "2026-06-05"},
        format="json",
    )
    payment = Payment.objects.get()
    resp = authenticated_api_client.delete(f"/api/finances/payments/{payment.id}/")
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.payment_status == "open"


# --- CondoMonthCloseViewSet read-only (P2.3 step 5) ---


@freeze_time(FROZEN)
def test_condo_month_close_delete_is_405(authenticated_api_client):
    make_condominium()
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}, format="json"
    )
    close = CondoMonthClose.objects.get()
    resp = authenticated_api_client.delete(f"/api/finances/condo-month-closes/{close.id}/")
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert CondoMonthClose.objects.filter(pk=close.pk).exists()  # baseline NOT destroyed


@freeze_time(FROZEN)
def test_condo_month_close_default_post_is_405(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/condo-month-closes/",
        {"condominium_id": cond.id, "reference_month": "2026-06-01"},
        format="json",
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@freeze_time(FROZEN)
def test_condo_month_close_default_patch_is_405(authenticated_api_client):
    make_condominium()
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}, format="json"
    )
    close = CondoMonthClose.objects.get()
    resp = authenticated_api_client.patch(
        f"/api/finances/condo-month-closes/{close.id}/",
        {"reference_month": "2026-05-01"},
        format="json",
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@freeze_time(FROZEN)
def test_condo_month_close_close_and_reopen_actions_still_work(authenticated_api_client):
    make_condominium()
    closed = authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}, format="json"
    )
    assert closed.status_code == status.HTTP_200_OK
    assert closed.data["status"] == "closed"
    reopened = authenticated_api_client.post(
        "/api/finances/condo-month-closes/reopen/", {"year": 2026, "month": 6}, format="json"
    )
    assert reopened.status_code == status.HTTP_200_OK
    assert reopened.data["status"] == "open"


# --- IncomeEntry write guard on a closed month (P2.3 step 2) ---


@freeze_time(FROZEN)
def test_income_entry_create_rejected_on_closed_month(authenticated_api_client):
    cond = make_condominium()
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}, format="json"
    )
    resp = authenticated_api_client.post(
        "/api/finances/income-entries/",
        {
            "condominium_id": cond.id,
            "description": "Receita avulsa",
            "amount": "100.00",
            "income_date": "2026-06-20",
            "is_received": False,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_income_entry_create_ok_on_open_month(authenticated_api_client):
    cond = make_condominium()
    authenticated_api_client.post(
        "/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}, format="json"
    )
    resp = authenticated_api_client.post(
        "/api/finances/income-entries/",
        {
            "condominium_id": cond.id,
            "description": "Receita julho",
            "amount": "100.00",
            "income_date": "2026-07-20",
            "is_received": False,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
