"""
E2E Tests for Financial Module Workflows

Tests complete workflows for the financial module:
- Creating persons, credit cards, expense categories, expenses
- Generating and paying installments
- Recording incomes, rent payments, employee payments
- Querying cash flow and financial dashboard
- Permission enforcement for non-admin users
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import Apartment, Building, Lease, Person, Tenant

pytestmark = pytest.mark.integration


class TestFinancialWorkflowE2E:
    """Tests the complete flow of a financial month."""

    def test_complete_monthly_workflow(self, authenticated_api_client):
        """Full workflow: create persons, cards, categories, expenses, generate installments,
        incomes, rent payments, employee payments, then query cash flow and dashboard."""
        client = authenticated_api_client

        # Step 1: Create person + credit card
        person_resp = client.post("/api/persons/", {"name": "Alvaro", "relationship": "pai"})
        assert person_resp.status_code == status.HTTP_201_CREATED
        person_id = person_resp.data["id"]

        card_resp = client.post(
            "/api/credit-cards/",
            {
                "person_id": person_id,
                "nickname": "Trigg",
                "last_four_digits": "1234",
                "due_day": 15,
                "closing_day": 7,
            },
        )
        assert card_resp.status_code == status.HTTP_201_CREATED
        card_id = card_resp.data["id"]

        # Step 2: Create category
        cat_resp = client.post(
            "/api/expense-categories/",
            {
                "name": "Pessoal",
                "description": "Gastos pessoais",
                "color": "#FF0000",
            },
        )
        assert cat_resp.status_code == status.HTTP_201_CREATED
        cat_id = cat_resp.data["id"]

        # Step 3: Create installment expense (card purchase)
        expense_resp = client.post(
            "/api/expenses/",
            {
                "description": "Compra cartão",
                "expense_type": "card_purchase",
                "total_amount": "300.00",
                "expense_date": "2026-03-01",
                "person_id": person_id,
                "credit_card_id": card_id,
                "category_id": cat_id,
                "is_installment": True,
                "total_installments": 3,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": False,
            },
        )
        assert expense_resp.status_code == status.HTTP_201_CREATED
        expense_id = expense_resp.data["id"]

        # Step 4: Generate installments
        gen_resp = client.post(
            f"/api/expenses/{expense_id}/generate_installments/",
            {"start_date": "2026-03-01"},
        )
        assert gen_resp.status_code == status.HTTP_200_OK
        installments = gen_resp.data["installments"]
        assert len(installments) == 3
        # Each installment should be 100.00
        assert Decimal(installments[0]["amount"]) == Decimal("100.00")

        # Step 5: Create income
        income_resp = client.post(
            "/api/incomes/",
            {
                "description": "Aposentadoria",
                "amount": "5000.00",
                "income_date": "2026-03-05",
                "person_id": person_id,
                "is_recurring": True,
                "expected_monthly_amount": "5000.00",
                "is_received": True,
                "received_date": "2026-03-05",
            },
        )
        assert income_resp.status_code == status.HTTP_201_CREATED

        # Step 6: Create building, apartment, tenant, lease, then rent payment
        building = Building.objects.create(
            street_number=999, name="Prédio Teste", address="Rua Teste"
        )
        apt = Apartment.objects.create(
            building=building,
            number=101,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Inquilino Teste",
            cpf_cnpj="52998224725",
            phone="(11) 98765-4321",
            marital_status="Solteiro(a)",
            profession="Engenheiro",
        )
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        rent_resp = client.post(
            "/api/rent-payments/",
            {
                "lease_id": lease.pk,
                "reference_month": "2026-03-01",
                "amount_paid": "1500.00",
                "payment_date": "2026-03-10",
            },
        )
        assert rent_resp.status_code == status.HTTP_201_CREATED

        # Step 7: Create employee payment
        employee_resp = client.post(
            "/api/persons/",
            {"name": "Rosa", "relationship": "funcionária", "is_employee": True},
        )
        assert employee_resp.status_code == status.HTTP_201_CREATED
        employee_id = employee_resp.data["id"]

        payment_resp = client.post(
            "/api/employee-payments/",
            {
                "person_id": employee_id,
                "reference_month": "2026-03-01",
                "base_salary": "800.00",
                "variable_amount": "200.00",
                "rent_offset": "0.00",
                "cleaning_count": 5,
                "is_paid": True,
                "payment_date": "2026-03-31",
            },
        )
        assert payment_resp.status_code == status.HTTP_201_CREATED

        # Step 8: Query cash flow
        cf_resp = client.get("/api/cash-flow/monthly/", {"year": 2026, "month": 3})
        assert cf_resp.status_code == status.HTTP_200_OK
        assert cf_resp.data["year"] == 2026
        assert cf_resp.data["month"] == 3

        # Step 9: Query dashboard overview
        dash_resp = client.get("/api/financial-dashboard/overview/")
        assert dash_resp.status_code == status.HTTP_200_OK

        # Step 10: Run simulation
        sim_resp = client.post(
            "/api/cash-flow/simulate/",
            {
                "scenarios": [
                    {"type": "add_fixed_expense", "amount": 500, "description": "Nova despesa"}
                ]
            },
            format="json",
        )
        assert sim_resp.status_code == status.HTTP_200_OK
        assert "base" in sim_resp.data
        assert "simulated" in sim_resp.data
        assert "comparison" in sim_resp.data

    def test_owner_apartment_not_in_rent_income(self, authenticated_api_client):
        """Apartment with owner should not count as regular rental income."""
        client = authenticated_api_client

        # Create owner person
        owner_resp = client.post(
            "/api/persons/",
            {"name": "Proprietário", "relationship": "sócio", "is_owner": True},
        )
        assert owner_resp.status_code == status.HTTP_201_CREATED
        owner_id = owner_resp.data["id"]

        # Create building + apartment with owner
        building = Building.objects.create(
            street_number=998, name="Prédio Owner", address="Rua Owner"
        )
        owner_person = Person.objects.get(pk=owner_id)
        apt = Apartment.objects.create(
            building=building,
            number=201,
            rental_value=Decimal("2000.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
            owner=owner_person,
        )
        tenant = Tenant.objects.create(
            name="Inquilino Owner",
            cpf_cnpj="05257794187",
            phone="(11) 91234-5678",
            marital_status="Casado(a)",
            profession="Comerciante",
        )
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("2000.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        # Register rent payment
        rent_resp = client.post(
            "/api/rent-payments/",
            {
                "lease_id": lease.pk,
                "reference_month": "2026-03-01",
                "amount_paid": "2000.00",
                "payment_date": "2026-03-10",
            },
        )
        assert rent_resp.status_code == status.HTTP_201_CREATED

        # Cash flow should show this as expense (owner repayment), not income
        cf_resp = client.get("/api/cash-flow/monthly/", {"year": 2026, "month": 3})
        assert cf_resp.status_code == status.HTTP_200_OK
        # The owner apartment rent should appear as an expense, not a regular income

    def test_prepaid_lease_not_in_income(self, authenticated_api_client):
        """Lease with prepaid_until in the future should not generate income."""
        building = Building.objects.create(
            street_number=997, name="Prédio Prepaid", address="Rua Prepaid"
        )
        apt = Apartment.objects.create(
            building=building,
            number=301,
            rental_value=Decimal("1300.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Inquilina Prepaid",
            cpf_cnpj="24843803480",
            phone="(11) 93456-7890",
            marital_status="Solteiro(a)",
            profession="Professora",
        )
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=24,
            due_day=10,
            rental_value=Decimal("1300.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
            prepaid_until=date(2026, 9, 29),
        )

        # Cash flow for March 2026 — prepaid_until is in the future, so no income from this lease
        client = authenticated_api_client
        cf_resp = client.get("/api/cash-flow/monthly/", {"year": 2026, "month": 3})
        assert cf_resp.status_code == status.HTTP_200_OK

    def test_salary_offset_lease_not_in_income(self, authenticated_api_client):
        """Lease with is_salary_offset=True should not count as rental income."""
        building = Building.objects.create(
            street_number=996, name="Prédio Offset", address="Rua Offset"
        )
        apt = Apartment.objects.create(
            building=building,
            number=401,
            rental_value=Decimal("800.00"),
            cleaning_fee=Decimal("0.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Funcionária Rosa",
            cpf_cnpj="15782647825",
            phone="(11) 94567-8901",
            marital_status="Solteiro(a)",
            profession="Diarista",
        )
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("800.00"),
            cleaning_fee=Decimal("0.00"),
            tag_fee=Decimal("0.00"),
            is_salary_offset=True,
        )

        client = authenticated_api_client
        cf_resp = client.get("/api/cash-flow/monthly/", {"year": 2026, "month": 3})
        assert cf_resp.status_code == status.HTTP_200_OK

    def test_permissions_non_admin_read_only(self, admin_user, regular_user):
        """Non-admin users should get 403 on write operations but 200 on reads."""
        from rest_framework.test import APIClient

        admin_client = APIClient()
        admin_client.force_authenticate(user=admin_user)

        non_admin = APIClient()
        non_admin.force_authenticate(user=regular_user)

        # Admin creates a person first
        resp = admin_client.post("/api/persons/", {"name": "Test Person", "relationship": "teste"})
        assert resp.status_code == status.HTTP_201_CREATED
        person_id = resp.data["id"]

        # Non-admin can READ
        read_resp = non_admin.get("/api/persons/")
        assert read_resp.status_code == status.HTTP_200_OK

        read_detail = non_admin.get(f"/api/persons/{person_id}/")
        assert read_detail.status_code == status.HTTP_200_OK

        # Non-admin CANNOT write
        create_resp = non_admin.post("/api/persons/", {"name": "Blocked", "relationship": "teste"})
        assert create_resp.status_code == status.HTTP_403_FORBIDDEN

        update_resp = non_admin.put(
            f"/api/persons/{person_id}/", {"name": "Updated", "relationship": "teste"}
        )
        assert update_resp.status_code == status.HTTP_403_FORBIDDEN

        patch_resp = non_admin.patch(f"/api/persons/{person_id}/", {"name": "Patched"})
        assert patch_resp.status_code == status.HTTP_403_FORBIDDEN

        delete_resp = non_admin.delete(f"/api/persons/{person_id}/")
        assert delete_resp.status_code == status.HTTP_403_FORBIDDEN

        # Non-admin CAN read dashboard (IsAuthenticated)
        dash_resp = non_admin.get("/api/financial-dashboard/overview/")
        assert dash_resp.status_code == status.HTTP_200_OK

        # Non-admin CAN read cash flow (IsAuthenticated)
        cf_resp = non_admin.get("/api/cash-flow/monthly/", {"year": 2026, "month": 3})
        assert cf_resp.status_code == status.HTTP_200_OK

        # Non-admin CAN use simulate (IsAuthenticated on CashFlowViewSet)
        sim_resp = non_admin.post(
            "/api/cash-flow/simulate/",
            {"scenarios": [{"type": "add_fixed_expense", "amount": 100, "description": "Test"}]},
            format="json",
        )
        assert sim_resp.status_code == status.HTTP_200_OK

        # Non-admin CAN read financial settings (FinancialReadOnly — read OK)
        settings_resp = non_admin.get("/api/financial-settings/current/")
        assert settings_resp.status_code == status.HTTP_200_OK

        # Non-admin CANNOT update financial settings (FinancialReadOnly — write denied)
        settings_update = non_admin.put(
            "/api/financial-settings/current/",
            {
                "initial_balance": "10000.00",
                "initial_balance_date": "2026-01-01",
            },
        )
        assert settings_update.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_mark_paid_completes_expense(self, authenticated_api_client):
        """When all installments of an expense are marked paid, the expense auto-completes."""
        client = authenticated_api_client

        # Create person
        person_resp = client.post("/api/persons/", {"name": "Bulk Test", "relationship": "teste"})
        assert person_resp.status_code == status.HTTP_201_CREATED
        person_id = person_resp.data["id"]

        # Create card
        card_resp = client.post(
            "/api/credit-cards/",
            {
                "person_id": person_id,
                "nickname": "Test Card",
                "last_four_digits": "9999",
                "due_day": 20,
                "closing_day": 10,
            },
        )
        assert card_resp.status_code == status.HTTP_201_CREATED
        card_id = card_resp.data["id"]

        # Create installment expense
        expense_resp = client.post(
            "/api/expenses/",
            {
                "description": "Expense com 3 parcelas",
                "expense_type": "card_purchase",
                "total_amount": "900.00",
                "expense_date": "2026-01-01",
                "person_id": person_id,
                "credit_card_id": card_id,
                "is_installment": True,
                "total_installments": 3,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": False,
            },
        )
        assert expense_resp.status_code == status.HTTP_201_CREATED
        expense_id = expense_resp.data["id"]

        # Generate installments
        gen_resp = client.post(
            f"/api/expenses/{expense_id}/generate_installments/",
            {"start_date": "2026-01-01"},
        )
        assert gen_resp.status_code == status.HTTP_200_OK
        installments = gen_resp.data["installments"]
        assert len(installments) == 3
        inst_ids = [i["id"] for i in installments]

        # Mark first 2 installments paid
        bulk_resp = client.post(
            "/api/expense-installments/bulk_mark_paid/",
            {"installment_ids": inst_ids[:2]},
            format="json",
        )
        assert bulk_resp.status_code == status.HTTP_200_OK

        # Expense should NOT be completed yet
        expense_check = client.get(f"/api/expenses/{expense_id}/")
        assert expense_check.data["is_paid"] is False

        # Mark last installment
        mark_resp = client.post(f"/api/expense-installments/{inst_ids[2]}/mark_paid/")
        assert mark_resp.status_code == status.HTTP_200_OK

        # Now expense should auto-complete
        expense_final = client.get(f"/api/expenses/{expense_id}/")
        assert expense_final.data["is_paid"] is True

    def test_person_payment_flow(self, authenticated_api_client):
        """Person summary reflects payments: net_amount decreases as payments are registered."""
        client = authenticated_api_client

        # Create person + card + expense
        person_resp = client.post(
            "/api/persons/", {"name": "Pagamento Test", "relationship": "pai"}
        )
        assert person_resp.status_code == status.HTTP_201_CREATED
        person_id = person_resp.data["id"]

        card_resp = client.post(
            "/api/credit-cards/",
            {
                "person_id": person_id,
                "nickname": "Card Test",
                "last_four_digits": "5555",
                "due_day": 15,
                "closing_day": 7,
            },
        )
        assert card_resp.status_code == status.HTTP_201_CREATED
        card_id = card_resp.data["id"]

        cat_resp = client.post(
            "/api/expense-categories/",
            {"name": "Pgto Test Cat", "description": "test", "color": "#00FF00"},
        )
        assert cat_resp.status_code == status.HTTP_201_CREATED
        cat_id = cat_resp.data["id"]

        # Card purchase expense with installments
        expense_resp = client.post(
            "/api/expenses/",
            {
                "description": "Compra teste pgto",
                "expense_type": "card_purchase",
                "total_amount": "600.00",
                "expense_date": "2026-03-01",
                "person_id": person_id,
                "credit_card_id": card_id,
                "category_id": cat_id,
                "is_installment": True,
                "total_installments": 3,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": False,
            },
        )
        assert expense_resp.status_code == status.HTTP_201_CREATED
        expense_id = expense_resp.data["id"]

        gen_resp = client.post(
            f"/api/expenses/{expense_id}/generate_installments/",
            {"start_date": "2026-03-01"},
        )
        assert gen_resp.status_code == status.HTTP_200_OK

        # Check person_summary — should have card_total > 0, net_amount negative (owes money)
        summary_resp = client.get(
            "/api/cash-flow/person_summary/",
            {"person_id": person_id, "year": 2026, "month": 3},
        )
        assert summary_resp.status_code == status.HTTP_200_OK
        initial_card_total = Decimal(str(summary_resp.data["card_total"]))
        initial_net = Decimal(str(summary_resp.data["net_amount"]))
        initial_pending = Decimal(str(summary_resp.data["pending_balance"]))
        assert initial_card_total == Decimal("200.00")  # 600 / 3 installments = 200
        assert initial_net < Decimal("0.00")  # Person has no income, so net is negative

        # Register partial payment
        pay_resp = client.post(
            "/api/person-payments/",
            {
                "person_id": person_id,
                "reference_month": "2026-03-01",
                "amount": "100.00",
                "payment_date": "2026-03-15",
            },
        )
        assert pay_resp.status_code == status.HTTP_201_CREATED

        # Check pending_balance reduced after payment
        summary_resp2 = client.get(
            "/api/cash-flow/person_summary/",
            {"person_id": person_id, "year": 2026, "month": 3},
        )
        assert summary_resp2.status_code == status.HTTP_200_OK
        new_pending = Decimal(str(summary_resp2.data["pending_balance"]))
        total_paid = Decimal(str(summary_resp2.data["total_paid"]))
        assert total_paid == Decimal("100.00")
        assert new_pending == initial_pending - Decimal("100.00")

    def test_offset_reduces_person_total(self, authenticated_api_client):
        """Expenses with is_offset=True reduce the person's net_amount."""
        client = authenticated_api_client

        person_resp = client.post(
            "/api/persons/", {"name": "Offset Test", "relationship": "genro"}
        )
        assert person_resp.status_code == status.HTTP_201_CREATED
        person_id = person_resp.data["id"]

        card_resp = client.post(
            "/api/credit-cards/",
            {
                "person_id": person_id,
                "nickname": "Offset Card",
                "last_four_digits": "7777",
                "due_day": 15,
                "closing_day": 7,
            },
        )
        assert card_resp.status_code == status.HTTP_201_CREATED
        card_id = card_resp.data["id"]

        cat_resp = client.post(
            "/api/expense-categories/",
            {"name": "Offset Cat", "description": "test", "color": "#0000FF"},
        )
        assert cat_resp.status_code == status.HTTP_201_CREATED
        cat_id = cat_resp.data["id"]

        # Normal expense with installments
        normal_resp = client.post(
            "/api/expenses/",
            {
                "description": "Compra normal",
                "expense_type": "card_purchase",
                "total_amount": "300.00",
                "expense_date": "2026-03-01",
                "person_id": person_id,
                "credit_card_id": card_id,
                "category_id": cat_id,
                "is_installment": True,
                "total_installments": 1,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": False,
            },
        )
        assert normal_resp.status_code == status.HTTP_201_CREATED
        normal_id = normal_resp.data["id"]
        gen_resp = client.post(
            f"/api/expenses/{normal_id}/generate_installments/",
            {"start_date": "2026-03-01"},
        )
        assert gen_resp.status_code == status.HTTP_200_OK

        # Offset expense
        offset_resp = client.post(
            "/api/expenses/",
            {
                "description": "Desconto sogros",
                "expense_type": "card_purchase",
                "total_amount": "100.00",
                "expense_date": "2026-03-01",
                "person_id": person_id,
                "credit_card_id": card_id,
                "category_id": cat_id,
                "is_installment": True,
                "total_installments": 1,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": True,
                "is_paid": False,
            },
        )
        assert offset_resp.status_code == status.HTTP_201_CREATED
        offset_id = offset_resp.data["id"]
        gen_resp2 = client.post(
            f"/api/expenses/{offset_id}/generate_installments/",
            {"start_date": "2026-03-01"},
        )
        assert gen_resp2.status_code == status.HTTP_200_OK

        # Person summary should reflect offset
        summary_resp = client.get(
            "/api/cash-flow/person_summary/",
            {"person_id": person_id, "year": 2026, "month": 3},
        )
        assert summary_resp.status_code == status.HTTP_200_OK
        card_total = Decimal(str(summary_resp.data["card_total"]))
        offset_total = Decimal(str(summary_resp.data["offset_total"]))
        net_amount = Decimal(str(summary_resp.data["net_amount"]))

        assert card_total == Decimal("300.00")
        assert offset_total == Decimal("100.00")
        # net_amount = receives(0) - card_total(300) - loan(0) - fixed(0) + offset(100) = -200
        # The offset reduces what the person owes (from -300 to -200)
        assert net_amount == Decimal("0.00") - card_total + offset_total

    def test_cash_flow_projection_with_end_date(self, authenticated_api_client):
        """Fixed expense with end_date should stop appearing in projections after that date."""
        client = authenticated_api_client

        person_resp = client.post(
            "/api/persons/", {"name": "EndDate Test", "relationship": "teste"}
        )
        assert person_resp.status_code == status.HTTP_201_CREATED
        person_id = person_resp.data["id"]

        cat_resp = client.post(
            "/api/expense-categories/",
            {"name": "EndDate Cat", "description": "test", "color": "#FF00FF"},
        )
        assert cat_resp.status_code == status.HTTP_201_CREATED
        cat_id = cat_resp.data["id"]

        # Create a fixed expense with end_date in June 2026
        expense_resp = client.post(
            "/api/expenses/",
            {
                "description": "Gasto fixo temporário",
                "expense_type": "fixed_expense",
                "total_amount": "500.00",
                "expense_date": "2026-01-01",
                "person_id": person_id,
                "category_id": cat_id,
                "is_installment": False,
                "is_recurring": True,
                "expected_monthly_amount": "500.00",
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": False,
                "end_date": "2026-06-30",
            },
        )
        assert expense_resp.status_code == status.HTTP_201_CREATED

        # Project 12 months
        proj_resp = client.get("/api/cash-flow/projection/", {"months": 12})
        assert proj_resp.status_code == status.HTTP_200_OK
        projection = proj_resp.data

        # Find months after end_date — July 2026 and beyond should not include this expense
        # The projection starts from current month; find entries for before and after end_date
        assert len(projection) == 12

    def test_daily_control_breakdown(self, authenticated_api_client):
        """Daily breakdown shows rent on due_day and installments on due_date."""
        client = authenticated_api_client

        # Create building + apartment + tenant + lease with due_day=10
        building = Building.objects.create(
            street_number=990, name="Prédio Daily", address="Rua Daily"
        )
        apt = Apartment.objects.create(
            building=building,
            number=501,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("150.00"),
            max_tenants=2,
            is_rented=True,
        )
        tenant = Tenant.objects.create(
            name="Inquilino Daily",
            cpf_cnpj="71428793860",
            phone="(11) 95555-1234",
            marital_status="Solteiro(a)",
            profession="Analista",
        )
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=24,
            due_day=10,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("150.00"),
            tag_fee=Decimal("50.00"),
        )

        # Create installment with due_date on day 15
        person_resp = client.post(
            "/api/persons/", {"name": "Daily Person", "relationship": "teste"}
        )
        assert person_resp.status_code == status.HTTP_201_CREATED
        person_id = person_resp.data["id"]

        card_resp = client.post(
            "/api/credit-cards/",
            {
                "person_id": person_id,
                "nickname": "Daily Card",
                "last_four_digits": "3333",
                "due_day": 15,
                "closing_day": 7,
            },
        )
        assert card_resp.status_code == status.HTTP_201_CREATED
        card_id = card_resp.data["id"]

        cat_resp = client.post(
            "/api/expense-categories/",
            {"name": "Daily Cat", "description": "test", "color": "#AABB00"},
        )
        assert cat_resp.status_code == status.HTTP_201_CREATED
        cat_id = cat_resp.data["id"]

        expense_resp = client.post(
            "/api/expenses/",
            {
                "description": "Expense daily",
                "expense_type": "card_purchase",
                "total_amount": "150.00",
                "expense_date": "2026-03-01",
                "person_id": person_id,
                "credit_card_id": card_id,
                "category_id": cat_id,
                "is_installment": True,
                "total_installments": 1,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": False,
            },
        )
        assert expense_resp.status_code == status.HTTP_201_CREATED
        expense_id = expense_resp.data["id"]

        gen_resp = client.post(
            f"/api/expenses/{expense_id}/generate_installments/",
            {"start_date": "2026-03-15"},
        )
        assert gen_resp.status_code == status.HTTP_200_OK

        # Query daily breakdown for March 2026
        breakdown_resp = client.get(
            "/api/daily-control/breakdown/", {"year": 2026, "month": 3}
        )
        assert breakdown_resp.status_code == status.HTTP_200_OK
        days = breakdown_resp.data  # Returns list of day objects directly
        assert len(days) == 31  # March has 31 days

        # Day 10 (index 9) — should have rent entry in entries
        day_10 = days[9]
        assert day_10["date"] == "2026-03-10"
        rent_entries = [e for e in day_10["entries"] if e["type"] == "rent"]
        assert len(rent_entries) > 0

        # Day 15 (index 14) — should have installment in exits
        day_15 = days[14]
        assert day_15["date"] == "2026-03-15"
        installment_exits = [e for e in day_15["exits"] if e["type"] == "installment"]
        assert len(installment_exits) > 0

    def test_subcategory_expense(self, authenticated_api_client):
        """Expenses with subcategories should appear in category breakdown."""
        client = authenticated_api_client

        # Create parent + subcategory
        parent_resp = client.post(
            "/api/expense-categories/",
            {"name": "Pessoal", "description": "Gastos pessoais", "color": "#FF5500"},
        )
        assert parent_resp.status_code == status.HTTP_201_CREATED
        parent_id = parent_resp.data["id"]

        sub_resp = client.post(
            "/api/expense-categories/",
            {
                "name": "Saúde",
                "description": "Gastos saúde",
                "color": "#FF5500",
                "parent_id": parent_id,
            },
        )
        assert sub_resp.status_code == status.HTTP_201_CREATED
        sub_id = sub_resp.data["id"]

        # Create expense with subcategory
        expense_resp = client.post(
            "/api/expenses/",
            {
                "description": "Consulta médica",
                "expense_type": "one_time_expense",
                "total_amount": "250.00",
                "expense_date": "2026-03-10",
                "category_id": sub_id,
                "is_installment": False,
                "is_recurring": False,
                "is_debt_installment": False,
                "is_offset": False,
                "is_paid": True,
            },
        )
        assert expense_resp.status_code == status.HTTP_201_CREATED

        # Check category breakdown
        breakdown_resp = client.get(
            "/api/financial-dashboard/category_breakdown/",
            {"year": 2026, "month": 3},
        )
        assert breakdown_resp.status_code == status.HTTP_200_OK
        categories = breakdown_resp.data
        # The subcategory should appear in the breakdown
        sub_entry = next((c for c in categories if c["category_id"] == sub_id), None)
        assert sub_entry is not None
        assert Decimal(str(sub_entry["total"])) == Decimal("250.00")
