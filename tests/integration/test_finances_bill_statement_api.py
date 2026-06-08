"""Session 58 — bills/update_with_lines + create_with_lines (statement) + nested + destroy.

View -> Service -> Model (no internal mocks). freezegun fixes today_sp() for the
UNPAID/overdue annotation. Throttling disabled via the test_finances conftest fixture.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from finances.models import (
    Bill,
    BillBehavior,
    BillingAccountType,
    BillLineItem,
    WaterBillStatement,
)
from finances.services.bill_payment_service import BillPaymentService
from freezegun import freeze_time
from rest_framework import status

from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condo_month_close,
    make_condominium,
    make_installment,
    make_water_statement,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-06-05 12:00:00"


def _water_bill(cond=None):
    if cond is None:
        cond = make_condominium()
    account = make_billing_account(
        condominium=cond, account_type=BillingAccountType.WATER, external_identifier="UC-1"
    )
    bill = make_bill(
        condominium=cond,
        billing_account=account,
        competence_month=date(2026, 6, 1),
        due_date=date(2026, 6, 10),
        behavior=BillBehavior.RECURRING,
    )
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    return bill


@freeze_time(FROZEN)
def test_update_with_lines_replaces_unpaid_open(authenticated_api_client) -> None:
    bill = _water_bill()
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {
            "line_items": [{"description": "Nova", "amount": "250.00"}],
            "statement": {"consumo_m3": 158},
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_total"] == "250.00"
    assert resp.data["water_statement"]["consumo_m3"] == 158
    assert BillLineItem.objects.filter(bill=bill).count() == 1


@freeze_time(FROZEN)
def test_update_with_lines_rejects_paid_bill(authenticated_api_client, admin_user) -> None:
    bill = _water_bill()
    BillPaymentService.pay(bill, date(2026, 6, 5), None, user=admin_user)
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": [{"description": "X", "amount": "50.00"}]},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "pagamento" in resp.data["error"].lower()


@freeze_time(FROZEN)
def test_update_with_lines_rejects_closed_month(authenticated_api_client) -> None:
    cond = make_condominium()
    bill = _water_bill(cond)
    make_condo_month_close(
        condominium=cond,
        reference_month=date(2026, 6, 1),
        status="closed",
        closed_at=timezone.now(),
    )
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": [{"description": "X", "amount": "50.00"}]},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "mês" in resp.data["error"].lower()


@freeze_time(FROZEN)
def test_create_with_lines_persists_statement_and_installment(authenticated_api_client) -> None:
    cond = make_condominium()
    account = make_billing_account(
        condominium=cond, account_type=BillingAccountType.WATER, external_identifier="UC-9"
    )
    installment = make_installment()
    resp = authenticated_api_client.post(
        "/api/finances/bills/create_with_lines/",
        {
            "bill": {
                "condominium_id": cond.id,
                "billing_account_id": account.id,
                "competence_month": "2026-06-01",
                "due_date": "2026-06-10",
                "description": "Água Junho",
                "behavior": BillBehavior.RECURRING,
            },
            "line_items": [
                {"description": "Consumo", "amount": "120.00", "installment_id": installment.id}
            ],
            "statement": {"consumo_m3": 158, "leitura_atual": 1158},
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    bill_id = resp.data["id"]
    get_resp = authenticated_api_client.get(f"/api/finances/bills/{bill_id}/")
    assert get_resp.data["water_statement"]["consumo_m3"] == 158
    line = BillLineItem.objects.get(bill_id=bill_id)
    assert line.installment_id == installment.id


@freeze_time(FROZEN)
def test_get_bill_nests_statement(authenticated_api_client) -> None:
    bill = _water_bill()
    make_water_statement(bill=bill, consumo_m3=200)
    resp = authenticated_api_client.get(f"/api/finances/bills/{bill.id}/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["water_statement"]["consumo_m3"] == 200
    assert resp.data["electricity_statement"] is None


@freeze_time(FROZEN)
def test_destroy_bill_cascades_statement(authenticated_api_client) -> None:
    bill = _water_bill()
    statement = make_water_statement(bill=bill, consumo_m3=200)
    resp = authenticated_api_client.delete(f"/api/finances/bills/{bill.id}/")
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert Bill.objects.filter(pk=bill.pk).exists() is False
    assert WaterBillStatement.objects.filter(pk=statement.pk).exists() is False
    assert WaterBillStatement.objects.with_deleted().get(pk=statement.pk).is_deleted is True


def test_update_with_lines_forbidden_for_non_staff(regular_authenticated_api_client) -> None:
    bill = _water_bill()
    url = f"/api/finances/bills/{bill.id}/update_with_lines/"
    forbidden = regular_authenticated_api_client.post(url, {"line_items": []}, format="json")
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN


def test_update_with_lines_unauthorized_for_anonymous(api_client) -> None:
    bill = _water_bill()
    url = f"/api/finances/bills/{bill.id}/update_with_lines/"
    unauthenticated = api_client.post(url, {"line_items": []}, format="json")
    assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED


@freeze_time(FROZEN)
def test_update_with_lines_rejects_non_list_line_items(authenticated_api_client) -> None:
    bill = _water_bill()
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": "not-a-list"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_update_with_lines_rejects_statement_not_object(authenticated_api_client) -> None:
    bill = _water_bill()
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": [{"description": "X", "amount": "10.00"}], "statement": "nope"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_update_with_lines_rejects_line_not_object(authenticated_api_client) -> None:
    bill = _water_bill()
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {"line_items": ["not-an-object"]},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_update_with_lines_persists_statement_fields(authenticated_api_client) -> None:
    """Exercises the viewset statement coercion: int (consumo), date (data_leitura), string
    (agua_status) and an explicit null (leitura_anterior) field."""
    bill = _water_bill()
    resp = authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/update_with_lines/",
        {
            "line_items": [{"description": "Consumo", "amount": "100.00"}],
            "statement": {
                "consumo_m3": 158,
                "data_leitura": "2026-06-01",
                "agua_status": "cut",
                "leitura_anterior": None,
            },
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    statement = resp.data["water_statement"]
    assert statement["data_leitura"] == "2026-06-01"
    assert statement["agua_status"] == "cut"
    assert statement["leitura_anterior"] is None


@freeze_time(FROZEN)
def test_create_with_lines_rejects_statement_for_generic_account(authenticated_api_client) -> None:
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/bills/create_with_lines/",
        {
            "bill": {
                "condominium_id": cond.id,
                "competence_month": "2026-06-01",
                "due_date": "2026-06-10",
                "description": "Avulsa",
                "behavior": BillBehavior.ONE_TIME,
            },
            "line_items": [{"description": "X", "amount": "10.00"}],
            "statement": {"consumo_m3": 10},
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
