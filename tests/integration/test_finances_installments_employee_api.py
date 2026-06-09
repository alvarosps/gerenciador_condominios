"""Session 42 — integration tests for installment-plans / installments / employees API."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from finances.models import (
    BillingAccountType,
    BillLifecycleState,
    InstallmentPlan,
    InstallmentPlanState,
)
from finances.services.timezone import today_sp

from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condominium,
    make_employee,
    make_installment,
    make_installment_plan,
    make_lease,
    make_person,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

PLANS_URL = "/api/finances/installment-plans/"
INSTALLMENTS_URL = "/api/finances/installments/"
EMPLOYEES_URL = "/api/finances/employees/"
CONVERT_URL = "/api/finances/installment-plans/convert_deferred/"


# --- installment-plans CRUD + dual serializer ---


def test_create_plan_returns_nested_read_and_string_money(authenticated_api_client) -> None:
    condo = make_condominium()
    payload = {
        "condominium_id": condo.id,
        "description": "Notebook 12x",
        "total_amount": "1200.00",
        "installment_count": 12,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(PLANS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["building"] is None
    assert response.data["embedded"] is False
    assert response.data["total_amount"] == "1200.00"  # Decimal -> string
    assert "category_id" not in response.data


def test_create_embedded_plan_with_billing_account_id(authenticated_api_client) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="UC-100"
    )
    payload = {
        "condominium_id": account.condominium_id,
        "description": "TV embutida",
        "total_amount": "400.00",
        "installment_count": 4,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
        "embedded": True,
        "billing_account_id": account.id,
    }
    response = authenticated_api_client.post(PLANS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["embedded"] is True
    assert response.data["billing_account"]["id"] == account.id


def test_create_embedded_plan_with_iptu_account_id_is_rejected(authenticated_api_client) -> None:
    account = make_billing_account(account_type=BillingAccountType.IPTU, external_identifier="9988")
    payload = {
        "condominium_id": account.condominium_id,
        "description": "IPTU embutido inválido",
        "total_amount": "400.00",
        "installment_count": 4,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
        "embedded": True,
        "billing_account_id": account.id,
    }
    response = authenticated_api_client.post(PLANS_URL, payload, format="json")
    assert response.status_code == 400
    assert "billing_account_id" in response.data


def test_create_standalone_plan_with_iptu_account_id(authenticated_api_client) -> None:
    account = make_billing_account(account_type=BillingAccountType.IPTU, external_identifier="7766")
    payload = {
        "condominium_id": account.condominium_id,
        "description": "IPTU avulso",
        "total_amount": "1500.00",
        "installment_count": 3,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
        "embedded": False,
        "billing_account_id": account.id,
    }
    response = authenticated_api_client.post(PLANS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["embedded"] is False
    assert response.data["billing_account"]["id"] == account.id


def test_embedded_without_linked_account_is_rejected(authenticated_api_client) -> None:
    condo = make_condominium()
    payload = {
        "condominium_id": condo.id,
        "description": "Inconsistente",
        "total_amount": "100.00",
        "installment_count": 2,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
        "embedded": True,
    }
    response = authenticated_api_client.post(PLANS_URL, payload, format="json")
    assert response.status_code == 400


def test_list_plans_paginated_and_filtered(authenticated_api_client) -> None:
    active = make_installment_plan(lifecycle_state=InstallmentPlanState.ACTIVE)
    make_installment_plan(lifecycle_state=InstallmentPlanState.PAID)
    response = authenticated_api_client.get(PLANS_URL, {"lifecycle_state": "active"})
    assert response.status_code == 200
    assert "results" in response.data
    ids = {row["id"] for row in response.data["results"]}
    assert active.id in ids
    assert all(row["lifecycle_state"] == "active" for row in response.data["results"])


def test_retrieve_plan_includes_nested_installments(authenticated_api_client) -> None:
    plan = make_installment_plan(installment_count=2)
    make_installment(plan=plan, number=2, due_date=date(2026, 8, 10), amount=Decimal("50.00"))
    make_installment(plan=plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("50.00"))
    response = authenticated_api_client.get(f"{PLANS_URL}{plan.id}/")
    assert response.status_code == 200
    numbers = [inst["number"] for inst in response.data["installments"]]
    assert numbers == [1, 2]  # ordered by due_date/number


def test_patch_and_soft_delete_plan(authenticated_api_client) -> None:
    plan = make_installment_plan()
    patch = authenticated_api_client.patch(
        f"{PLANS_URL}{plan.id}/", {"description": "Renomeado"}, format="json"
    )
    assert patch.status_code == 200
    assert patch.data["description"] == "Renomeado"

    delete = authenticated_api_client.delete(f"{PLANS_URL}{plan.id}/")
    assert delete.status_code == 204
    assert InstallmentPlan.objects.filter(pk=plan.id).count() == 0
    assert InstallmentPlan.all_objects.get(pk=plan.id).is_deleted is True


# --- convert_deferred (delegates to S41 service) ---


def test_convert_deferred_creates_plan_and_terminates_bill(authenticated_api_client) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="IPTU-42"
    )
    bill = make_bill(
        condominium=account.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.DEFERRED,
        billing_account=account,
    )
    make_bill_line_item(bill=bill, amount=Decimal("1200.00"))
    payload = {
        "bill_id": bill.id,
        "installment_count": 12,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(CONVERT_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["total_amount"] == "1200.00"  # value migrated whole (no dup/loss)
    assert len(response.data["installments"]) == 12
    assert response.data["billing_account"]["id"] == account.id  # inherits the IPTU account (§10.2)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.CANCELED  # terminal, outside all sums


def test_convert_deferred_missing_params_is_400(authenticated_api_client) -> None:
    response = authenticated_api_client.post(CONVERT_URL, {"installment_count": 3}, format="json")
    assert response.status_code == 400
    assert "error" in response.data


def test_convert_deferred_on_active_bill_is_400(authenticated_api_client) -> None:
    bill = make_bill(behavior="one_time", lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    payload = {
        "bill_id": bill.id,
        "installment_count": 3,
        "start_due_date": "2026-07-10",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(CONVERT_URL, payload, format="json")
    assert response.status_code == 400


# --- installments (read + schedule edit) ---


def test_list_installments_filtered_by_plan(authenticated_api_client) -> None:
    plan = make_installment_plan(installment_count=2)
    make_installment(plan=plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("50.00"))
    other = make_installment_plan(installment_count=1)
    make_installment(plan=other, number=1, due_date=date(2026, 7, 10), amount=Decimal("50.00"))
    response = authenticated_api_client.get(INSTALLMENTS_URL, {"plan_id": plan.id})
    assert response.status_code == 200
    assert all(row["plan"] == plan.id for row in response.data["results"])


def test_patch_installment_amount_edits_schedule(authenticated_api_client) -> None:
    inst = make_installment(amount=Decimal("400.00"))
    response = authenticated_api_client.patch(
        f"{INSTALLMENTS_URL}{inst.id}/", {"amount": "420.00"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["amount"] == "420.00"


def test_installments_post_and_delete_not_allowed(authenticated_api_client) -> None:
    inst = make_installment()
    assert authenticated_api_client.post(INSTALLMENTS_URL, {}, format="json").status_code == 405
    assert authenticated_api_client.delete(f"{INSTALLMENTS_URL}{inst.id}/").status_code == 405


def test_installment_is_overdue_flag(authenticated_api_client) -> None:
    # Real-today-relative dates (no freezegun: a frozen clock + the test client + coverage
    # trips Django's DB connection health check). is_overdue = past-due AND plan active.
    today = today_sp()
    plan = make_installment_plan(installment_count=2)
    overdue = make_installment(
        plan=plan, number=1, due_date=today - timedelta(days=40), amount=Decimal(50)
    )
    future = make_installment(
        plan=plan, number=2, due_date=today + timedelta(days=40), amount=Decimal(50)
    )
    overdue_resp = authenticated_api_client.get(f"{INSTALLMENTS_URL}{overdue.id}/")
    future_resp = authenticated_api_client.get(f"{INSTALLMENTS_URL}{future.id}/")
    assert overdue_resp.data["is_overdue"] is True
    assert future_resp.data["is_overdue"] is False


# --- employees CRUD + dual serializer ---


def test_create_employee_mixed_with_person_and_lease(authenticated_api_client) -> None:
    condo = make_condominium()
    person = make_person()
    lease = make_lease(is_salary_offset=True)
    payload = {
        "condominium_id": condo.id,
        "person_id": person.id,
        "lease_id": lease.id,
        "name": "Rosa",
        "payment_type": "mixed",
        "base_salary": "2000.00",
        "default_due_day": 5,
    }
    response = authenticated_api_client.post(EMPLOYEES_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["person"]["id"] == person.id
    assert response.data["lease"]["id"] == lease.id
    assert response.data["base_salary"] == "2000.00"


def test_create_employee_variable_only_and_unbound(authenticated_api_client) -> None:
    condo = make_condominium()
    variable = authenticated_api_client.post(
        EMPLOYEES_URL,
        {
            "condominium_id": condo.id,
            "name": "Raymel",
            "payment_type": "variable",
            "base_salary": None,
            "default_due_day": 5,
        },
        format="json",
    )
    assert variable.status_code == 201
    assert variable.data["base_salary"] is None
    assert variable.data["person"] is None
    assert variable.data["lease"] is None


def test_list_employees_filtered_and_soft_delete(authenticated_api_client) -> None:
    condo = make_condominium()
    active = make_employee(condominium=condo, is_active=True, payment_type="fixed")
    make_employee(condominium=condo, is_active=False, payment_type="variable", base_salary=None)
    response = authenticated_api_client.get(EMPLOYEES_URL, {"is_active": "true"})
    assert response.status_code == 200
    ids = {row["id"] for row in response.data["results"]}
    assert active.id in ids
    assert all(row["is_active"] is True for row in response.data["results"])

    delete = authenticated_api_client.delete(f"{EMPLOYEES_URL}{active.id}/")
    assert delete.status_code == 204
    from finances.models import Employee

    assert Employee.objects.filter(pk=active.id).count() == 0
    assert Employee.all_objects.get(pk=active.id).is_deleted is True


# --- FinancialReadOnly permission matrix ---


def test_non_admin_can_read_but_not_write(regular_authenticated_api_client) -> None:
    make_installment_plan()
    assert regular_authenticated_api_client.get(PLANS_URL).status_code == 200
    assert regular_authenticated_api_client.get(EMPLOYEES_URL).status_code == 200
    write = regular_authenticated_api_client.post(
        EMPLOYEES_URL,
        {"condominium_id": 1, "name": "X", "payment_type": "variable", "default_due_day": 5},
        format="json",
    )
    assert write.status_code == 403
    convert = regular_authenticated_api_client.post(CONVERT_URL, {}, format="json")
    assert convert.status_code == 403


def test_anonymous_is_unauthorized(api_client) -> None:
    assert api_client.get(PLANS_URL).status_code == 401
    assert api_client.post(CONVERT_URL, {}, format="json").status_code == 401


# --- cache invalidation (S41 signals cover the 3 models) ---


def test_plan_write_invalidates_finance_cache(authenticated_api_client) -> None:
    # LocMem cache: invalidation is asserted by a probe key disappearing after the write
    # (same pattern as test_finance_cache_signals; no internal mocking).
    from django.core.cache import cache
    from finances.cache import FINANCE_CACHE_PREFIXES

    condo = make_condominium()
    for prefix in FINANCE_CACHE_PREFIXES:
        cache.set(f"{prefix}:probe", "x")
    authenticated_api_client.post(
        PLANS_URL,
        {
            "condominium_id": condo.id,
            "description": "Cache",
            "total_amount": "100.00",
            "installment_count": 1,
            "start_due_date": "2026-07-10",
            "default_due_day": 10,
        },
        format="json",
    )
    assert all(cache.get(f"{prefix}:probe") is None for prefix in FINANCE_CACHE_PREFIXES)
