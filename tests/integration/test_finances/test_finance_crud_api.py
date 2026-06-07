"""Session 38 — finances CRUD API (dual serializer, filters, pagination, soft-delete)."""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill
from freezegun import freeze_time
from rest_framework import status

from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_bill_skip,
    make_billing_account,
    make_building,
    make_condominium,
    make_finance_category,
    make_payment,
    make_payment_allocation,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-01 12:00:00"


def test_category_list_and_create_dual(authenticated_api_client):
    cond = make_condominium()
    parent = make_finance_category(condominium=cond, name="Utilidades")
    resp = authenticated_api_client.post(
        "/api/finances/finance-categories/",
        {"condominium_id": cond.id, "parent_id": parent.id, "name": "Água"},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["parent"] == {"id": parent.id, "name": "Utilidades"}
    assert "parent_id" not in resp.data
    listing = authenticated_api_client.get("/api/finances/finance-categories/")
    assert listing.status_code == status.HTTP_200_OK
    assert "results" in listing.data


def test_billing_account_filter_and_decimal_string(authenticated_api_client):
    cond = make_condominium()
    account = make_billing_account(condominium=cond, expected_amount=Decimal("123.45"))
    resp = authenticated_api_client.get(
        f"/api/finances/billing-accounts/?lifecycle_state=active&building_id={account.building_id or 0}"
    )
    assert resp.status_code == status.HTTP_200_OK
    account_resp = authenticated_api_client.get(
        "/api/finances/billing-accounts/?lifecycle_state=active"
    )
    found = [a for a in account_resp.data["results"] if a["id"] == account.id]
    assert found
    assert found[0]["expected_amount"] == "123.45"


@freeze_time(FROZEN)
def test_bill_list_exposes_annotations(authenticated_api_client):
    bill = make_bill(due_date=date(2026, 6, 10))
    make_bill_line_item(bill=bill, amount=Decimal("600.00"))
    make_bill_line_item(bill=bill, amount=Decimal("400.00"))
    make_bill_line_item(bill=bill, amount=Decimal("100.00"), is_offset=True)
    resp = authenticated_api_client.get("/api/finances/bills/")
    row = next(b for b in resp.data["results"] if b["id"] == bill.id)
    assert row["amount_total"] == "900.00"
    assert row["amount_paid"] == "0.00"
    assert row["payment_status"] == "open"
    assert row["is_overdue"] is True
    assert len(row["line_items"]) == 3


@freeze_time(FROZEN)
def test_bill_filter_by_payment_status_and_overdue(authenticated_api_client):
    overdue = make_bill(due_date=date(2026, 6, 10))
    make_bill_line_item(bill=overdue, amount=Decimal("100.00"))
    future = make_bill(due_date=date(2026, 8, 10))
    make_bill_line_item(bill=future, amount=Decimal("100.00"))
    resp = authenticated_api_client.get("/api/finances/bills/?is_overdue=true")
    ids = {b["id"] for b in resp.data["results"]}
    assert overdue.id in ids
    assert future.id not in ids
    open_resp = authenticated_api_client.get("/api/finances/bills/?payment_status=open")
    assert overdue.id in {b["id"] for b in open_resp.data["results"]}


@freeze_time(FROZEN)
def test_bill_pagination(authenticated_api_client):
    cond = make_condominium()
    for i in range(25):
        make_bill(condominium=cond, description=f"Bill {i}")
    resp = authenticated_api_client.get("/api/finances/bills/?page_size=10")
    assert len(resp.data["results"]) == 10
    assert resp.data["count"] >= 25
    page2 = authenticated_api_client.get("/api/finances/bills/?page_size=10&page=2")
    assert page2.status_code == status.HTTP_200_OK


def test_bill_create_and_soft_delete(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/bills/",
        {
            "condominium_id": cond.id,
            "competence_month": "2026-06-15",
            "due_date": "2026-06-10",
            "description": "Conta avulsa",
            "behavior": "one_time",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    bill_id = resp.data["id"]
    assert resp.data["competence_month"] == "2026-06-01"  # normalized to day 1
    delete = authenticated_api_client.delete(f"/api/finances/bills/{bill_id}/")
    assert delete.status_code == status.HTTP_204_NO_CONTENT
    listing = authenticated_api_client.get("/api/finances/bills/")
    assert bill_id not in {b["id"] for b in listing.data["results"]}
    assert Bill.objects.with_deleted().filter(pk=bill_id).exists()


@freeze_time(FROZEN)
def test_query_param_filters(authenticated_api_client):
    cond = make_condominium()
    building = make_building(condominium=cond)
    category = make_finance_category(condominium=cond, name="Água")
    account = make_billing_account(condominium=cond, building=building, category=category)
    bill = make_bill(
        condominium=cond,
        building=building,
        category=category,
        behavior="recurring",
        competence_month=date(2026, 6, 1),
        lifecycle_state="active",
    )
    make_bill(condominium=cond, behavior="one_time", lifecycle_state="suspended")
    # Bill filters
    by_category = authenticated_api_client.get(f"/api/finances/bills/?category_id={category.id}")
    assert {b["id"] for b in by_category.data["results"]} == {bill.id}
    by_behavior = authenticated_api_client.get("/api/finances/bills/?behavior=recurring")
    assert bill.id in {b["id"] for b in by_behavior.data["results"]}
    by_competence = authenticated_api_client.get(
        "/api/finances/bills/?competence_month=2026-06-01&lifecycle_state=active"
    )
    assert bill.id in {b["id"] for b in by_competence.data["results"]}
    by_building = authenticated_api_client.get(f"/api/finances/bills/?building_id={building.id}")
    assert bill.id in {b["id"] for b in by_building.data["results"]}
    # Category / BillingAccount / Payment / BillSkip filters
    cats = authenticated_api_client.get(
        f"/api/finances/finance-categories/?condominium_id={cond.id}"
    )
    assert category.id in {c["id"] for c in cats.data["results"]}
    accounts = authenticated_api_client.get(
        f"/api/finances/billing-accounts/?category_id={category.id}"
    )
    assert account.id in {a["id"] for a in accounts.data["results"]}
    skip = make_bill_skip(billing_account=account)
    skips = authenticated_api_client.get(
        f"/api/finances/bill-skips/?billing_account_id={account.id}"
    )
    assert skip.id in {s["id"] for s in skips.data["results"]}
    payment = make_payment(condominium=cond, payment_date=date(2026, 6, 15))
    payments = authenticated_api_client.get(
        "/api/finances/payments/?date_from=2026-06-01&date_to=2026-06-30"
    )
    assert payment.id in {p["id"] for p in payments.data["results"]}


def test_payment_list_with_allocations(authenticated_api_client):
    bill = make_bill()
    payment = make_payment(condominium=bill.condominium)
    make_payment_allocation(payment=payment, bill=bill, amount=Decimal("50.00"))
    resp = authenticated_api_client.get("/api/finances/payments/?funded_from=caixa")
    row = next(p for p in resp.data["results"] if p["id"] == payment.id)
    assert len(row["allocations"]) == 1
    assert row["allocations"][0]["amount"] == "50.00"
