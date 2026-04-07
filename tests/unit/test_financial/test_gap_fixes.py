"""Regression tests for session 16 gap fixes.

Tests cover:
- Fix 1: SyntaxError in SimulationService (Python 2 except syntax)
- Fix 2: Expense.end_date field
- Fix 3: _collect_fixed_expenses respects end_date + person in person_summary
- Fix 4: Projected installments exclude is_offset=True
- Fix 5: _collect_utility_bills excludes is_offset=True
- Fix 6: get_expense_category_breakdown excludes is_offset=True
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import (
    ExpenseType,
)
from core.services.cash_flow_service import CashFlowService
from core.services.financial_dashboard_service import FinancialDashboardService
from core.services.simulation_service import SimulationService
from tests.factories import (
    make_building,
    make_expense,
    make_expense_category,
    make_expense_installment,
    make_person,
)


@pytest.fixture
def person_alvaro():
    return make_person(name="Alvaro", relationship="Pai")


@pytest.fixture
def person_rodrigo():
    return make_person(name="Rodrigo", relationship="Filho")


@pytest.fixture
def category_pessoal():
    return make_expense_category(name="Pessoal", color="#EF4444")


@pytest.fixture
def building_836():
    return make_building(street_number=836, name="Edifício 836", address="Rua Teste, 836")


class TestSimulationServiceSyntaxFix:
    """Fix 1: SimulationService must import without SyntaxError."""

    def test_simulate_from_db_does_not_crash(self) -> None:
        """Module imports successfully (no Python 2 except syntax)."""

        assert SimulationService is not None

    def test_change_rent_scenario(self) -> None:
        """_db_change_rent handles missing apartment gracefully."""

        projection = [
            {
                "year": 2026,
                "month": 3,
                "income_total": Decimal("5000.00"),
                "expenses_total": Decimal("3000.00"),
                "balance": Decimal("2000.00"),
                "cumulative_balance": Decimal("2000.00"),
                "is_projected": True,
            }
        ]
        scenarios = [{"type": "change_rent", "apartment_id": 99999, "new_value": "2000.00"}]
        result = SimulationService.simulate_from_db(projection, scenarios)
        # Should not crash — apartment doesn't exist, so no delta applied
        assert result[0]["income_total"] == Decimal("5000.00")

    def test_remove_tenant_scenario(self) -> None:
        """_db_remove_tenant handles missing apartment gracefully."""

        projection = [
            {
                "year": 2026,
                "month": 3,
                "income_total": Decimal("5000.00"),
                "expenses_total": Decimal("3000.00"),
                "balance": Decimal("2000.00"),
                "cumulative_balance": Decimal("2000.00"),
                "is_projected": True,
            }
        ]
        scenarios = [{"type": "remove_tenant", "apartment_id": 99999}]
        result = SimulationService.simulate_from_db(projection, scenarios)
        # Should not crash — apartment doesn't exist, so no delta applied
        assert result[0]["income_total"] == Decimal("5000.00")


class TestExpenseEndDate:
    """Fix 2: Expense model must support end_date field."""

    def test_create_expense_with_end_date(self, category_pessoal) -> None:
        expense = make_expense(
            description="Unimed",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("2230.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("2230.00"),
            end_date=date(2026, 12, 31),
            category=category_pessoal,
        )
        expense.refresh_from_db()
        assert expense.end_date == date(2026, 12, 31)

    def test_end_date_nullable(self, category_pessoal) -> None:
        expense = make_expense(
            description="Internet",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("150.00"),
            category=category_pessoal,
        )
        expense.refresh_from_db()
        assert expense.end_date is None


class TestFixedExpenseEndDate:
    """Fix 3: Fixed expenses must respect end_date and appear in person summary."""

    @freeze_time("2026-03-15")
    def test_fixed_expense_with_end_date_excluded_after(
        self, category_pessoal
    ) -> None:
        """A fixed expense with end_date=2026-02-28 should NOT appear in March cash flow."""
        make_expense(
            description="Seguro antigo",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("500.00"),
            expense_date=date(2025, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("500.00"),
            end_date=date(2026, 2, 28),
            category=category_pessoal,
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["fixed_expenses"] == Decimal("0.00")

    @freeze_time("2026-03-15")
    def test_fixed_expense_without_end_date_projects_forever(
        self, category_pessoal
    ) -> None:
        """A fixed expense with end_date=None should always appear."""
        make_expense(
            description="Internet",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2025, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("150.00"),
            category=category_pessoal,
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["fixed_expenses"] == Decimal("150.00")

    @freeze_time("2026-03-15")
    def test_fixed_expense_with_person_in_person_summary(
        self,
        person_rodrigo,
        category_pessoal,
    ) -> None:
        """Fixed expenses linked to a person should appear in their person summary."""
        make_expense(
            description="Unimed via Rodrigo",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("2230.00"),
            expense_date=date(2025, 1, 1),
            person=person_rodrigo,
            is_recurring=True,
            expected_monthly_amount=Decimal("2230.00"),
            is_offset=False,
            category=category_pessoal,
        )
        result = CashFlowService.get_person_summary(person_rodrigo.id, 2026, 3)
        # net_amount should subtract the fixed expense
        assert result["fixed_total"] == Decimal("2230.00")
        assert result["net_amount"] == Decimal("0.00") - Decimal("2230.00")


class TestIsOffsetFiltering:
    """Fixes 4, 5, 6: is_offset=True expenses must be excluded from projections and breakdowns."""

    @freeze_time("2026-03-15")
    def test_projected_installments_exclude_offset(
        self,
        person_alvaro,
    ) -> None:
        """Projected expenses should not include offset installments."""
        # Normal expense with installment in April (future month = projected)
        normal = make_expense(
            description="Compra normal",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            expense_date=date(2026, 1, 1),
            person=person_alvaro,
            is_installment=True,
            total_installments=3,
            is_offset=False,
        )
        make_expense_installment(
            expense=normal,
            installment_number=3,
            total_installments=3,
            amount=Decimal("200.00"),
            due_date=date(2026, 4, 15),
        )

        # Get projection including April
        projection_without_offset = CashFlowService.get_cash_flow_projection(months=2)
        april_without = next(m for m in projection_without_offset if m["month"] == 4)

        # Now add an offset installment in April — should NOT change the total
        offset = make_expense(
            description="Compra para sogros",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 1, 1),
            person=person_alvaro,
            is_installment=True,
            total_installments=3,
            is_offset=True,
        )
        make_expense_installment(
            expense=offset,
            installment_number=3,
            total_installments=3,
            amount=Decimal("100.00"),
            due_date=date(2026, 4, 15),
        )

        projection_with_offset = CashFlowService.get_cash_flow_projection(months=2)
        april_with = next(m for m in projection_with_offset if m["month"] == 4)

        # Offset installment must not affect projected expenses
        assert april_with["expenses_total"] == april_without["expenses_total"]

    @freeze_time("2026-03-15")
    def test_utility_bills_exclude_offset(
        self,
        building_836,
    ) -> None:
        """Utility bills with is_offset=True should not be included."""
        make_expense(
            description="Conta de água normal",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 3, 10),
            building=building_836,
            is_offset=False,
        )
        make_expense(
            description="Conta de água offset",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 3, 10),
            building=building_836,
            is_offset=True,
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["utility_bills"] == Decimal("200.00")

    @freeze_time("2026-03-15")
    def test_category_breakdown_excludes_offset(
        self,
        category_pessoal,
    ) -> None:
        """Category breakdown should not include offset expenses."""
        make_expense(
            description="Gasto real",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 5),
            category=category_pessoal,
            is_offset=False,
        )
        make_expense(
            description="Gasto offset",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 3, 5),
            category=category_pessoal,
            is_offset=True,
        )
        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)
        total = sum(item["total"] for item in result)
        assert total == Decimal("500.00")
