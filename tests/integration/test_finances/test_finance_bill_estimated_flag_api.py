"""Session 65 — Bill.amount_is_estimated exposed read-only on the API + transitions via the
action endpoints (generate_month/pay/bulk_pay/update_with_lines)."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from finances.models import Bill
from finances.services.bill_generation_service import BillGenerationService
from tests.factories import make_bill, make_bill_line_item, make_billing_account, make_condominium

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-01 12:00:00"


def test_bill_serializer_exposes_amount_is_estimated(authenticated_api_client):
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    resp = authenticated_api_client.get(f"/api/finances/bills/{bill.id}/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_is_estimated"] is False


def test_patch_cannot_set_amount_is_estimated(authenticated_api_client):
    bill = make_bill(competence_month=date(2026, 6, 1))
    resp = authenticated_api_client.patch(
        f"/api/finances/bills/{bill.id}/",
        {"amount_is_estimated": True},
        format="json",
    )
    # PATCH bills/{id} delegates to BillService.update_header — not 405 (P2.3 confirmed contract).
    assert resp.status_code == status.HTTP_200_OK
    bill.refresh_from_db()
    assert bill.amount_is_estimated is False


def test_generate_month_marks_new_bills_estimated(authenticated_api_client):
    make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
    resp = authenticated_api_client.post(
        "/api/finances/bills/generate_month/",
        {"year": 2026, "month": 6},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["created"] == 1
    assert resp.data["bills"][0]["amount_is_estimated"] is True


@freeze_time(FROZEN)
def test_pay_action_clears_flag(authenticated_api_client):
    make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
    bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
    assert bill.amount_is_estimated is True

    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_is_estimated"] is False


@freeze_time(FROZEN)
def test_bulk_pay_clears_flag(authenticated_api_client):
    cond = make_condominium()
    a1 = make_billing_account(condominium=cond, expected_amount=Decimal("100.00"))
    a2 = make_billing_account(condominium=cond, expected_amount=Decimal("200.00"))
    bills = BillGenerationService.ensure_month_bills(2026, 6)
    ids = [b.id for b in bills if b.billing_account_id in {a1.id, a2.id}]
    assert all(Bill.objects.get(pk=pk).amount_is_estimated for pk in ids)

    resp = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {"bill_ids": ids, "payment_date": "2026-06-05"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert all(item["amount_is_estimated"] is False for item in resp.data)


def test_update_with_lines_clears_flag_via_api(authenticated_api_client):
    make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
    bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
    assert bill.amount_is_estimated is True

    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": [{"description": "Água — fatura real", "amount": "650.00"}]},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_is_estimated"] is False
