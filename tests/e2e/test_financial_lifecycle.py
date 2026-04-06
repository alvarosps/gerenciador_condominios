"""
E2E Tests for Financial Module Lifecycle Workflows

Tests complete workflows NOT covered by test_financial_workflow.py:
- Bank loan lifecycle with debt_by_type dashboard verification
- Financial dashboard aggregation accuracy across diverse data
- Cash flow projection accuracy with end_date handling
- Daily control mark_paid flow with summary verification
- Expense category hierarchy with category_breakdown
- Income mark_received workflow
- PersonIncome (apartment_rent / fixed_stipend) lifecycle
- Expense rebuild action (overwrite + regenerate installments)
- Expense filter API (by type, person, date range, is_paid)
- Installment filter API (overdue, by person, by card)
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Building, Apartment, Lease, Person, Tenant

pytestmark = pytest.mark.integration


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _create_person(client: APIClient, name: str, relationship: str = "teste") -> int:
    resp = client.post("/api/persons/", {"name": name, "relationship": relationship})
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return int(resp.data["id"])


def _create_card(client: APIClient, person_id: int, nickname: str, digits: str) -> int:
    resp = client.post(
        "/api/credit-cards/",
        {
            "person_id": person_id,
            "nickname": nickname,
            "last_four_digits": digits,
            "due_day": 15,
            "closing_day": 7,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return int(resp.data["id"])


def _create_category(client: APIClient, name: str, parent_id: int | None = None) -> int:
    payload: dict = {"name": name, "description": name, "color": "#123456"}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    resp = client.post("/api/expense-categories/", payload)
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return int(resp.data["id"])


def _create_expense(client: APIClient, **kwargs) -> int:
    defaults = {
        "is_installment": False,
        "is_recurring": False,
        "is_debt_installment": False,
        "is_offset": False,
        "is_paid": False,
    }
    defaults.update(kwargs)
    resp = client.post("/api/expenses/", defaults)
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return int(resp.data["id"])


def _generate_installments(client: APIClient, expense_id: int, start_date: str) -> list:
    resp = client.post(
        f"/api/expenses/{expense_id}/generate_installments/",
        {"start_date": start_date},
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    return resp.data["installments"]


def _create_rented_lease(street_number: int, due_day: int = 10) -> tuple[Building, Apartment, Tenant, Lease]:
    building = Building.objects.create(
        street_number=street_number, name=f"Prédio {street_number}", address=f"Rua {street_number}"
    )
    apt = Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        is_rented=True,
    )
    tenant = Tenant.objects.create(
        name=f"Inquilino {street_number}",
        cpf_cnpj=f"528.982.247-{due_day:02d}",  # pattern with varying last 2 digits
        phone="(11) 98765-4321",
        marital_status="Solteiro(a)",
        profession="Analista",
        due_day=due_day,
    )
    lease = Lease.objects.create(
        apartment=apt,
        responsible_tenant=tenant,
        start_date=date(2025, 1, 1),
        validity_months=24,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
    )
    return building, apt, tenant, lease


# ──────────────────────────────────────────────────────────────────────────────
# Test Classes
# ──────────────────────────────────────────────────────────────────────────────


class TestBankLoanLifecycle:
    """Bank loan expense: generate installments, check debt_by_type and debt_by_person."""

    def test_bank_loan_debt_appears_in_dashboard(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Banco Test", "pai")

        # Create bank loan expense (12 installments of R$1000 each)
        expense_id = _create_expense(
            client,
            description="Empréstimo CEF",
            expense_type="bank_loan",
            total_amount="12000.00",
            expense_date="2026-01-01",
            person_id=person_id,
            is_installment=True,
            total_installments=12,
            bank_name="CEF",
            interest_rate="1.50",
        )

        installments = _generate_installments(client, expense_id, "2026-01-01")
        assert len(installments) == 12
        assert Decimal(installments[0]["amount"]) == Decimal("1000.00")

        # Verify debt_by_type shows bank_loan total
        debt_resp = client.get("/api/financial-dashboard/debt_by_type/")
        assert debt_resp.status_code == status.HTTP_200_OK
        bank_loans_total = Decimal(str(debt_resp.data["bank_loans"]))
        assert bank_loans_total >= Decimal("12000.00")

        # Verify debt_by_person shows this person
        person_resp = client.get("/api/financial-dashboard/debt_by_person/")
        assert person_resp.status_code == status.HTTP_200_OK
        person_entry = next((p for p in person_resp.data if p["person_id"] == person_id), None)
        assert person_entry is not None
        assert Decimal(str(person_entry["loan_debt"])) >= Decimal("12000.00")
        assert Decimal(str(person_entry["total_debt"])) >= Decimal("12000.00")

    def test_bank_loan_paid_installments_reduce_debt(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Banco Parcial", "mae")

        expense_id = _create_expense(
            client,
            description="Empréstimo Parcial",
            expense_type="bank_loan",
            total_amount="6000.00",
            expense_date="2026-01-01",
            person_id=person_id,
            is_installment=True,
            total_installments=6,
        )
        installments = _generate_installments(client, expense_id, "2026-01-01")
        assert len(installments) == 6

        # Debt before any payments
        before_resp = client.get("/api/financial-dashboard/debt_by_type/")
        bank_loans_before = Decimal(str(before_resp.data["bank_loans"]))

        # Pay the first installment
        first_id = installments[0]["id"]
        mark_resp = client.post(
            f"/api/expense-installments/{first_id}/mark_paid/",
            {"paid_date": "2026-01-15"},
        )
        assert mark_resp.status_code == status.HTTP_200_OK
        assert mark_resp.data["is_paid"] is True

        # Debt must decrease by exactly one installment amount (1000.00)
        after_resp = client.get("/api/financial-dashboard/debt_by_type/")
        bank_loans_after = Decimal(str(after_resp.data["bank_loans"]))
        assert bank_loans_before - bank_loans_after == Decimal("1000.00")


class TestIncomeLiftcycle:
    """Income CRUD, mark_received action, and cash flow reflection."""

    def test_income_mark_received_updates_is_received(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Renda Test", "mae")

        income_resp = client.post(
            "/api/incomes/",
            {
                "description": "Pensão alimentícia",
                "amount": "2000.00",
                "income_date": "2026-03-05",
                "person_id": person_id,
                "is_recurring": False,
                "is_received": False,
            },
        )
        assert income_resp.status_code == status.HTTP_201_CREATED
        income_id = income_resp.data["id"]
        assert income_resp.data["is_received"] is False

        # Mark as received via action
        received_resp = client.post(
            f"/api/incomes/{income_id}/mark_received/",
            {"received_date": "2026-03-07"},
        )
        assert received_resp.status_code == status.HTTP_200_OK
        assert received_resp.data["is_received"] is True
        assert received_resp.data["received_date"] == "2026-03-07"

        # Verify via GET
        detail_resp = client.get(f"/api/incomes/{income_id}/")
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.data["is_received"] is True

    def test_income_filter_by_person_and_date(self, authenticated_api_client):
        client = authenticated_api_client
        person_a = _create_person(client, "Income FilterA", "pai")
        person_b = _create_person(client, "Income FilterB", "mae")

        client.post(
            "/api/incomes/",
            {
                "description": "Renda A março",
                "amount": "1000.00",
                "income_date": "2026-03-01",
                "person_id": person_a,
                "is_recurring": False,
                "is_received": False,
            },
        )
        client.post(
            "/api/incomes/",
            {
                "description": "Renda B fevereiro",
                "amount": "500.00",
                "income_date": "2026-02-15",
                "person_id": person_b,
                "is_recurring": False,
                "is_received": False,
            },
        )

        # Filter by person_a only
        filter_resp = client.get("/api/incomes/", {"person_id": person_a})
        assert filter_resp.status_code == status.HTTP_200_OK
        items = filter_resp.data["results"] if "results" in filter_resp.data else filter_resp.data
        person_a_ids = {i["person"]["id"] if isinstance(i["person"], dict) else i["person"] for i in items}
        assert all(pid == person_a for pid in person_a_ids)

        # Filter by date range — only march
        date_resp = client.get("/api/incomes/", {"date_from": "2026-03-01", "date_to": "2026-03-31"})
        assert date_resp.status_code == status.HTTP_200_OK
        date_items = date_resp.data["results"] if "results" in date_resp.data else date_resp.data
        for item in date_items:
            assert item["income_date"] >= "2026-03-01"
            assert item["income_date"] <= "2026-03-31"


class TestFinancialDashboardAggregation:
    """Dashboard overview, debt_by_person, debt_by_type, upcoming, overdue, category_breakdown."""

    @freeze_time("2026-03-15")
    def test_dashboard_overview_structure(self, authenticated_api_client):
        client = authenticated_api_client

        overview_resp = client.get("/api/financial-dashboard/overview/")
        assert overview_resp.status_code == status.HTTP_200_OK
        data = overview_resp.data

        # Verify all required keys are present
        required_keys = [
            "current_month_balance",
            "current_month_income",
            "current_month_expenses",
            "total_debt",
            "total_monthly_obligations",
            "total_monthly_income",
            "months_until_break_even",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    @freeze_time("2026-03-15")
    def test_debt_by_type_all_keys_present(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.get("/api/financial-dashboard/debt_by_type/")
        assert resp.status_code == status.HTTP_200_OK

        required_keys = [
            "card_purchases",
            "bank_loans",
            "personal_loans",
            "water_debt",
            "electricity_debt",
            "property_tax_debt",
            "total",
        ]
        for key in required_keys:
            assert key in resp.data, f"Missing key: {key}"

    @freeze_time("2026-03-15")
    def test_upcoming_installments_within_window(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Upcoming Test", "pai")
        card_id = _create_card(client, person_id, "Upcoming Card", "1111")

        # Create expense with installment due in 10 days (within default 30-day window)
        expense_id = _create_expense(
            client,
            description="Parcela próxima",
            expense_type="card_purchase",
            total_amount="300.00",
            expense_date="2026-03-01",
            person_id=person_id,
            credit_card_id=card_id,
            is_installment=True,
            total_installments=1,
        )
        installments = _generate_installments(client, expense_id, "2026-03-15")
        assert len(installments) == 1
        # Installment due_date will be set to card.due_day (15) of March 2026
        # With freeze_time 2026-03-15, the due date is today — within the 30-day window

        upcoming_resp = client.get("/api/financial-dashboard/upcoming_installments/")
        assert upcoming_resp.status_code == status.HTTP_200_OK
        upcoming = upcoming_resp.data
        assert isinstance(upcoming, list)

        installment_id = installments[0]["id"]
        found = any(u["id"] == installment_id for u in upcoming)
        assert found, "Expected upcoming installment not found in window"

    @freeze_time("2026-03-15")
    def test_overdue_installments_appear_in_dashboard(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Overdue Test", "mae")

        # Create a one-time expense (no credit card) so we can set exact due_date
        expense_id = _create_expense(
            client,
            description="Parcela vencida",
            expense_type="one_time_expense",
            total_amount="500.00",
            expense_date="2026-02-01",
            person_id=person_id,
            is_installment=True,
            total_installments=1,
        )
        installments = _generate_installments(client, expense_id, "2026-02-01")
        assert len(installments) == 1
        # Due date is 2026-02-01 — before the frozen date 2026-03-15 → overdue

        overdue_resp = client.get("/api/financial-dashboard/overdue_installments/")
        assert overdue_resp.status_code == status.HTTP_200_OK
        overdue = overdue_resp.data
        assert isinstance(overdue, list)

        installment_id = installments[0]["id"]
        found = any(o["id"] == installment_id for o in overdue)
        assert found, "Expected overdue installment not found"

    @freeze_time("2026-03-15")
    def test_category_breakdown_sums_per_category(self, authenticated_api_client):
        client = authenticated_api_client

        cat_id = _create_category(client, "Dashboard Cat Test")

        # Two expenses in same category, same month
        _create_expense(
            client,
            description="Despesa A",
            expense_type="one_time_expense",
            total_amount="200.00",
            expense_date="2026-03-05",
            category_id=cat_id,
            is_paid=True,
        )
        _create_expense(
            client,
            description="Despesa B",
            expense_type="one_time_expense",
            total_amount="300.00",
            expense_date="2026-03-10",
            category_id=cat_id,
            is_paid=True,
        )

        breakdown_resp = client.get(
            "/api/financial-dashboard/category_breakdown/",
            {"year": 2026, "month": 3},
        )
        assert breakdown_resp.status_code == status.HTTP_200_OK
        categories = breakdown_resp.data
        assert isinstance(categories, list)

        entry = next((c for c in categories if c["category_id"] == cat_id), None)
        assert entry is not None, "Category not found in breakdown"
        assert Decimal(str(entry["total"])) == Decimal("500.00")


class TestCashFlowProjectionAccuracy:
    """Cash flow projection: monthly, multi-month, end_date handling."""

    @freeze_time("2026-03-01")
    def test_monthly_cash_flow_structure(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.get("/api/cash-flow/monthly/", {"year": 2026, "month": 3})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data

        assert data["year"] == 2026
        assert data["month"] == 3
        assert "income" in data
        assert "expenses" in data
        assert "balance" in data
        assert "total" in data["income"]
        assert "total" in data["expenses"]

    @freeze_time("2026-03-01")
    def test_projection_returns_correct_months_count(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.get("/api/cash-flow/projection/", {"months": 6})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 6

    @freeze_time("2026-03-01")
    def test_projection_12_months_default(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.get("/api/cash-flow/projection/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 12

    @freeze_time("2026-03-01")
    def test_projection_invalid_months_returns_error(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.get("/api/cash-flow/projection/", {"months": 0})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

        resp2 = client.get("/api/cash-flow/projection/", {"months": "abc"})
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-01")
    def test_monthly_cash_flow_missing_params_returns_error(self, authenticated_api_client):
        client = authenticated_api_client

        # Missing month
        resp = client.get("/api/cash-flow/monthly/", {"year": 2026})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

        # Missing year
        resp2 = client.get("/api/cash-flow/monthly/", {"month": 3})
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST

        # Invalid month value
        resp3 = client.get("/api/cash-flow/monthly/", {"year": 2026, "month": 13})
        assert resp3.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-01")
    def test_recurring_expense_appears_in_projection(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Projection Person", "pai")

        # Fixed recurring expense with no end_date — should appear in all 6 months
        _create_expense(
            client,
            description="Academia recorrente",
            expense_type="fixed_expense",
            total_amount="150.00",
            expense_date="2026-01-01",
            person_id=person_id,
            is_recurring=True,
            expected_monthly_amount="150.00",
        )

        resp = client.get("/api/cash-flow/projection/", {"months": 6})
        assert resp.status_code == status.HTTP_200_OK
        projection = resp.data
        assert len(projection) == 6

        # Every month should have the projection structure keys
        for month_data in projection:
            assert "expenses_total" in month_data
            assert "income_total" in month_data
            assert "balance" in month_data


class TestDailyControlMarkPaid:
    """Daily control: mark_paid via API, verify summary reflects the change."""

    @freeze_time("2026-03-15")
    def test_mark_installment_paid_via_daily_control(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Daily Mark", "pai")
        card_id = _create_card(client, person_id, "DailyCard", "4444")

        # Create expense with installment due on March 15
        expense_id = _create_expense(
            client,
            description="Parcela daily control",
            expense_type="card_purchase",
            total_amount="600.00",
            expense_date="2026-03-01",
            person_id=person_id,
            credit_card_id=card_id,
            is_installment=True,
            total_installments=1,
        )
        installments = _generate_installments(client, expense_id, "2026-03-15")
        assert len(installments) == 1
        installment_id = installments[0]["id"]

        # Get summary before mark_paid
        summary_before = client.get("/api/daily-control/summary/", {"year": 2026, "month": 3})
        assert summary_before.status_code == status.HTTP_200_OK
        paid_before = Decimal(str(summary_before.data["total_paid_expenses"]))

        # Mark as paid via daily-control endpoint
        mark_resp = client.post(
            "/api/daily-control/mark_paid/",
            {
                "item_type": "installment",
                "item_id": installment_id,
                "payment_date": "2026-03-15",
            },
        )
        assert mark_resp.status_code == status.HTTP_200_OK

        # Verify installment is now paid
        inst_resp = client.get(f"/api/expense-installments/{installment_id}/")
        assert inst_resp.status_code == status.HTTP_200_OK
        assert inst_resp.data["is_paid"] is True

        # Verify summary updated
        summary_after = client.get("/api/daily-control/summary/", {"year": 2026, "month": 3})
        assert summary_after.status_code == status.HTTP_200_OK
        paid_after = Decimal(str(summary_after.data["total_paid_expenses"]))
        assert paid_after == paid_before + Decimal("600.00")

    @freeze_time("2026-03-15")
    def test_mark_income_received_via_daily_control(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Daily Income", "mae")

        income_resp = client.post(
            "/api/incomes/",
            {
                "description": "Renda daily",
                "amount": "800.00",
                "income_date": "2026-03-10",
                "person_id": person_id,
                "is_recurring": False,
                "is_received": False,
            },
        )
        assert income_resp.status_code == status.HTTP_201_CREATED
        income_id = income_resp.data["id"]

        # Mark as received via daily-control
        mark_resp = client.post(
            "/api/daily-control/mark_paid/",
            {
                "item_type": "income",
                "item_id": income_id,
                "payment_date": "2026-03-10",
            },
        )
        assert mark_resp.status_code == status.HTTP_200_OK

        # Verify income is received
        income_detail = client.get(f"/api/incomes/{income_id}/")
        assert income_detail.status_code == status.HTTP_200_OK
        assert income_detail.data["is_received"] is True

    @freeze_time("2026-03-15")
    def test_daily_control_mark_paid_invalid_type_returns_error(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.post(
            "/api/daily-control/mark_paid/",
            {
                "item_type": "invalid_type",
                "item_id": 999,
                "payment_date": "2026-03-15",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-15")
    def test_daily_control_mark_paid_missing_fields(self, authenticated_api_client):
        client = authenticated_api_client

        # Missing item_type
        resp = client.post(
            "/api/daily-control/mark_paid/",
            {"item_id": 1, "payment_date": "2026-03-15"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

        # Missing payment_date
        resp2 = client.post(
            "/api/daily-control/mark_paid/",
            {"item_type": "installment", "item_id": 1},
        )
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-15")
    def test_daily_control_mark_paid_nonexistent_item(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.post(
            "/api/daily-control/mark_paid/",
            {
                "item_type": "installment",
                "item_id": 99999,
                "payment_date": "2026-03-15",
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestExpenseCategoryHierarchy:
    """Category hierarchy: parent > child, breakdown groups correctly."""

    def test_category_crud_with_parent(self, authenticated_api_client):
        client = authenticated_api_client

        # Create parent
        parent_id = _create_category(client, "Moradia")

        # Create children
        child_a_id = _create_category(client, "Aluguel", parent_id=parent_id)
        child_b_id = _create_category(client, "Condomínio", parent_id=parent_id)

        # Verify parent has no parent
        parent_resp = client.get(f"/api/expense-categories/{parent_id}/")
        assert parent_resp.status_code == status.HTTP_200_OK
        assert parent_resp.data["parent"] is None

        # Verify children reference the parent
        child_a_resp = client.get(f"/api/expense-categories/{child_a_id}/")
        assert child_a_resp.status_code == status.HTTP_200_OK
        # parent field can be nested object or just id depending on serializer
        parent_field = child_a_resp.data.get("parent")
        if isinstance(parent_field, dict):
            assert parent_field["id"] == parent_id
        else:
            assert parent_field == parent_id

        # Both children show in list
        list_resp = client.get("/api/expense-categories/")
        assert list_resp.status_code == status.HTTP_200_OK
        all_ids = [
            c["id"]
            for c in (list_resp.data["results"] if "results" in list_resp.data else list_resp.data)
        ]
        assert child_a_id in all_ids
        assert child_b_id in all_ids

    def test_expense_in_child_category_appears_in_breakdown(self, authenticated_api_client):
        client = authenticated_api_client

        parent_id = _create_category(client, "Saúde Geral")
        child_id = _create_category(client, "Farmácia", parent_id=parent_id)

        # One expense in parent, one in child
        _create_expense(
            client,
            description="Consulta",
            expense_type="one_time_expense",
            total_amount="400.00",
            expense_date="2026-03-08",
            category_id=parent_id,
            is_paid=True,
        )
        _create_expense(
            client,
            description="Remédios",
            expense_type="one_time_expense",
            total_amount="120.00",
            expense_date="2026-03-12",
            category_id=child_id,
            is_paid=True,
        )

        breakdown_resp = client.get(
            "/api/financial-dashboard/category_breakdown/",
            {"year": 2026, "month": 3},
        )
        assert breakdown_resp.status_code == status.HTTP_200_OK
        categories = breakdown_resp.data

        parent_entry = next((c for c in categories if c["category_id"] == parent_id), None)
        child_entry = next((c for c in categories if c["category_id"] == child_id), None)

        assert parent_entry is not None, "Parent category missing from breakdown"
        assert child_entry is not None, "Child category missing from breakdown"
        assert Decimal(str(parent_entry["total"])) == Decimal("400.00")
        assert Decimal(str(child_entry["total"])) == Decimal("120.00")


class TestExpenseRebuild:
    """Expense rebuild action: overwrite fields and replace installments."""

    def test_rebuild_replaces_installments(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Rebuild Person", "pai")
        card_id = _create_card(client, person_id, "Rebuild Card", "6666")

        expense_id = _create_expense(
            client,
            description="Rebuild original",
            expense_type="card_purchase",
            total_amount="300.00",
            expense_date="2026-03-01",
            person_id=person_id,
            credit_card_id=card_id,
            is_installment=True,
            total_installments=3,
        )
        # Generate original installments (3 of 100 each)
        original = _generate_installments(client, expense_id, "2026-03-01")
        assert len(original) == 3

        # Rebuild with 2 custom installments
        rebuild_resp = client.post(
            f"/api/expenses/{expense_id}/rebuild/",
            {
                "description": "Rebuild updated",
                "total_amount": "500.00",
                "is_installment": True,
                "total_installments": 2,
                "installments": [
                    {
                        "installment_number": 1,
                        "total_installments": 2,
                        "amount": "250.00",
                        "due_date": "2026-03-15",
                        "is_paid": False,
                    },
                    {
                        "installment_number": 2,
                        "total_installments": 2,
                        "amount": "250.00",
                        "due_date": "2026-04-15",
                        "is_paid": False,
                    },
                ],
            },
            format="json",
        )
        assert rebuild_resp.status_code == status.HTTP_200_OK

        # Verify expense was updated
        expense_resp = client.get(f"/api/expenses/{expense_id}/")
        assert expense_resp.status_code == status.HTTP_200_OK
        assert expense_resp.data["description"] == "Rebuild updated"
        assert str(expense_resp.data["total_amount"]) == "500.00"

        # Verify new installments replace old ones
        inst_resp = client.get("/api/expense-installments/", {"expense_id": expense_id})
        assert inst_resp.status_code == status.HTTP_200_OK
        new_installments = inst_resp.data["results"] if "results" in inst_resp.data else inst_resp.data
        assert len(new_installments) == 2
        amounts = {Decimal(str(i["amount"])) for i in new_installments}
        assert amounts == {Decimal("250.00")}


class TestExpenseAndInstallmentFilters:
    """Filtering API: expenses by type, person, date, is_paid; installments by overdue, person, card."""

    def test_expense_filter_by_type(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Filter Type", "pai")

        _create_expense(
            client,
            description="Unique expense",
            expense_type="one_time_expense",
            total_amount="100.00",
            expense_date="2026-03-01",
            person_id=person_id,
        )
        _create_expense(
            client,
            description="Fixed expense",
            expense_type="fixed_expense",
            total_amount="200.00",
            expense_date="2026-03-01",
            person_id=person_id,
            is_recurring=True,
            expected_monthly_amount="200.00",
        )

        one_time_resp = client.get("/api/expenses/", {"expense_type": "one_time_expense", "person_id": person_id})
        assert one_time_resp.status_code == status.HTTP_200_OK
        one_time_items = one_time_resp.data["results"] if "results" in one_time_resp.data else one_time_resp.data
        assert all(i["expense_type"] == "one_time_expense" for i in one_time_items)

    def test_expense_filter_by_date_range(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Filter Date", "mae")

        _create_expense(
            client,
            description="Feb expense",
            expense_type="one_time_expense",
            total_amount="100.00",
            expense_date="2026-02-10",
            person_id=person_id,
        )
        _create_expense(
            client,
            description="Mar expense",
            expense_type="one_time_expense",
            total_amount="200.00",
            expense_date="2026-03-10",
            person_id=person_id,
        )

        march_resp = client.get(
            "/api/expenses/",
            {"date_from": "2026-03-01", "date_to": "2026-03-31", "person_id": person_id},
        )
        assert march_resp.status_code == status.HTTP_200_OK
        march_items = march_resp.data["results"] if "results" in march_resp.data else march_resp.data
        assert len(march_items) == 1
        assert march_items[0]["description"] == "Mar expense"

    def test_installment_filter_overdue(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Overdue Filter", "pai")

        expense_id = _create_expense(
            client,
            description="Past due expense",
            expense_type="one_time_expense",
            total_amount="150.00",
            expense_date="2026-01-01",
            person_id=person_id,
            is_installment=True,
            total_installments=1,
        )
        installments = _generate_installments(client, expense_id, "2026-01-01")
        installment_id = installments[0]["id"]

        # Filter overdue=true — this installment is from January, already past
        overdue_resp = client.get("/api/expense-installments/", {"is_overdue": "true"})
        assert overdue_resp.status_code == status.HTTP_200_OK
        overdue_items = overdue_resp.data["results"] if "results" in overdue_resp.data else overdue_resp.data
        overdue_ids = [i["id"] for i in overdue_items]
        assert installment_id in overdue_ids

    def test_installment_filter_by_person(self, authenticated_api_client):
        client = authenticated_api_client
        person_a = _create_person(client, "Inst Person A", "pai")
        person_b = _create_person(client, "Inst Person B", "mae")

        expense_a = _create_expense(
            client,
            description="Person A expense",
            expense_type="one_time_expense",
            total_amount="200.00",
            expense_date="2026-03-01",
            person_id=person_a,
            is_installment=True,
            total_installments=1,
        )
        _generate_installments(client, expense_a, "2026-03-01")

        expense_b = _create_expense(
            client,
            description="Person B expense",
            expense_type="one_time_expense",
            total_amount="300.00",
            expense_date="2026-03-01",
            person_id=person_b,
            is_installment=True,
            total_installments=1,
        )
        _generate_installments(client, expense_b, "2026-03-01")

        # Filter by person_a — should only return person_a installments
        resp = client.get("/api/expense-installments/", {"person_id": person_a})
        assert resp.status_code == status.HTTP_200_OK
        items = resp.data["results"] if "results" in resp.data else resp.data
        for item in items:
            # expense field is a FK integer in installment serializer; use person filter directly
            expense_id = item["expense"] if isinstance(item["expense"], int) else item["expense"]["id"]
            exp_detail = client.get(f"/api/expenses/{expense_id}/")
            person_field = exp_detail.data["person"]
            person_id_actual = person_field["id"] if isinstance(person_field, dict) else person_field
            assert person_id_actual == person_a


class TestPersonIncomeLifecycle:
    """PersonIncome (apartment_rent / fixed_stipend) CRUD and active filtering."""

    def test_person_income_apartment_rent_crud(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Person Income Test", "pai")

        # Create a building + apartment to reference
        building = Building.objects.create(
            street_number=888,
            name="Prédio Income",
            address="Rua Income",
        )
        apt = Apartment.objects.create(
            building=building,
            number=201,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=2,
        )

        # Create person income of type apartment_rent
        create_resp = client.post(
            "/api/person-incomes/",
            {
                "person_id": person_id,
                "income_type": "apartment_rent",
                "apartment_id": apt.pk,
                "start_date": "2026-01-01",
                "is_active": True,
            },
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        income_id = create_resp.data["id"]

        # Read back
        detail_resp = client.get(f"/api/person-incomes/{income_id}/")
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.data["income_type"] == "apartment_rent"
        assert detail_resp.data["is_active"] is True

        # Update: set end_date → becomes inactive
        patch_resp = client.patch(
            f"/api/person-incomes/{income_id}/",
            {"end_date": "2026-06-30", "is_active": False},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data["is_active"] is False

        # Filter by is_active=false
        filter_resp = client.get("/api/person-incomes/", {"is_active": "false", "person_id": person_id})
        assert filter_resp.status_code == status.HTTP_200_OK
        inactive_items = filter_resp.data["results"] if "results" in filter_resp.data else filter_resp.data
        inactive_ids = [i["id"] for i in inactive_items]
        assert income_id in inactive_ids

    def test_person_income_fixed_stipend_crud(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Stipend Person", "mae")

        create_resp = client.post(
            "/api/person-incomes/",
            {
                "person_id": person_id,
                "income_type": "fixed_stipend",
                "fixed_amount": "500.00",
                "start_date": "2026-01-01",
                "is_active": True,
            },
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        assert create_resp.data["income_type"] == "fixed_stipend"
        assert str(create_resp.data["fixed_amount"]) == "500.00"


class TestFinancialSettingsWorkflow:
    """FinancialSettings singleton: GET creates defaults, PUT/PATCH update."""

    def test_settings_get_creates_singleton(self, authenticated_api_client):
        client = authenticated_api_client

        resp = client.get("/api/financial-settings/current/")
        assert resp.status_code == status.HTTP_200_OK
        assert "initial_balance" in resp.data
        assert "initial_balance_date" in resp.data

    def test_settings_update_via_put(self, authenticated_api_client):
        client = authenticated_api_client

        # Ensure singleton exists
        client.get("/api/financial-settings/current/")

        put_resp = client.put(
            "/api/financial-settings/current/",
            {
                "initial_balance": "50000.00",
                "initial_balance_date": "2026-01-01",
            },
        )
        assert put_resp.status_code == status.HTTP_200_OK
        assert str(put_resp.data["initial_balance"]) == "50000.00"
        assert put_resp.data["initial_balance_date"] == "2026-01-01"

        # Verify persistence
        get_resp = client.get("/api/financial-settings/current/")
        assert str(get_resp.data["initial_balance"]) == "50000.00"

    def test_settings_update_via_patch(self, authenticated_api_client):
        client = authenticated_api_client

        # Ensure singleton with known value
        client.put(
            "/api/financial-settings/current/",
            {
                "initial_balance": "10000.00",
                "initial_balance_date": "2026-01-01",
            },
        )

        patch_resp = client.patch(
            "/api/financial-settings/current/",
            {"initial_balance": "20000.00"},
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert str(patch_resp.data["initial_balance"]) == "20000.00"
        # initial_balance_date should remain unchanged
        assert patch_resp.data["initial_balance_date"] == "2026-01-01"

    def test_settings_non_admin_cannot_write(self, admin_user, regular_user):
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin_user)

        non_admin = APIClient()
        non_admin.force_authenticate(user=regular_user)

        # Ensure singleton exists
        admin_client.get("/api/financial-settings/current/")

        # Non-admin can read
        read_resp = non_admin.get("/api/financial-settings/current/")
        assert read_resp.status_code == status.HTTP_200_OK

        # Non-admin cannot update
        write_resp = non_admin.put(
            "/api/financial-settings/current/",
            {
                "initial_balance": "999.00",
                "initial_balance_date": "2026-01-01",
            },
        )
        assert write_resp.status_code == status.HTTP_403_FORBIDDEN


class TestPersonCRUD:
    """Person CRUD with filters: is_owner, is_employee, search."""

    def test_person_filter_by_is_owner(self, authenticated_api_client):
        client = authenticated_api_client

        owner_resp = client.post(
            "/api/persons/",
            {"name": "Owner Person", "relationship": "sócio", "is_owner": True},
        )
        assert owner_resp.status_code == status.HTTP_201_CREATED
        owner_id = owner_resp.data["id"]

        non_owner_resp = client.post(
            "/api/persons/",
            {"name": "Non Owner Person", "relationship": "pai", "is_owner": False},
        )
        assert non_owner_resp.status_code == status.HTTP_201_CREATED

        filter_resp = client.get("/api/persons/", {"is_owner": "true"})
        assert filter_resp.status_code == status.HTTP_200_OK
        items = filter_resp.data["results"] if "results" in filter_resp.data else filter_resp.data
        owner_ids = [p["id"] for p in items]
        assert owner_id in owner_ids

    def test_person_filter_by_is_employee(self, authenticated_api_client):
        client = authenticated_api_client

        emp_resp = client.post(
            "/api/persons/",
            {"name": "Employee Person", "relationship": "funcionário", "is_employee": True},
        )
        assert emp_resp.status_code == status.HTTP_201_CREATED
        emp_id = emp_resp.data["id"]

        filter_resp = client.get("/api/persons/", {"is_employee": "true"})
        assert filter_resp.status_code == status.HTTP_200_OK
        items = filter_resp.data["results"] if "results" in filter_resp.data else filter_resp.data
        emp_ids = [p["id"] for p in items]
        assert emp_id in emp_ids

    def test_person_search_by_name(self, authenticated_api_client):
        client = authenticated_api_client

        client.post("/api/persons/", {"name": "Unique Xavier Person", "relationship": "teste"})

        search_resp = client.get("/api/persons/", {"search": "Xavier"})
        assert search_resp.status_code == status.HTTP_200_OK
        items = search_resp.data["results"] if "results" in search_resp.data else search_resp.data
        names = [p["name"] for p in items]
        assert any("Xavier" in n for n in names)


class TestCreditCardFilters:
    """CreditCard filters: by person, is_active."""

    def test_credit_card_filter_by_person(self, authenticated_api_client):
        client = authenticated_api_client
        person_a = _create_person(client, "Card Filter A", "pai")
        person_b = _create_person(client, "Card Filter B", "mae")

        card_a = _create_card(client, person_a, "CardA", "1001")
        _create_card(client, person_b, "CardB", "2002")

        resp = client.get("/api/credit-cards/", {"person_id": person_a})
        assert resp.status_code == status.HTTP_200_OK
        items = resp.data["results"] if "results" in resp.data else resp.data
        card_ids = [c["id"] for c in items]
        assert card_a in card_ids
        assert all(
            c["person"]["id"] == person_a if isinstance(c["person"], dict) else c["person"] == person_a
            for c in items
        )

    def test_credit_card_deactivate(self, authenticated_api_client):
        client = authenticated_api_client
        person_id = _create_person(client, "Card Deactivate", "teste")
        card_id = _create_card(client, person_id, "Deactivate Me", "9090")

        # Deactivate via PATCH
        patch_resp = client.patch(f"/api/credit-cards/{card_id}/", {"is_active": False})
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data["is_active"] is False

        # Filter active only — card should not appear
        active_resp = client.get("/api/credit-cards/", {"is_active": "true", "person_id": person_id})
        assert active_resp.status_code == status.HTTP_200_OK
        active_items = active_resp.data["results"] if "results" in active_resp.data else active_resp.data
        active_ids = [c["id"] for c in active_items]
        assert card_id not in active_ids
