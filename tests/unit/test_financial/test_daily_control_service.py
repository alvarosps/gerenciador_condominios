"""Tests for DailyControlService.

Covers daily breakdown, month summary, and mark-paid functionality.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ObjectDoesNotExist
from freezegun import freeze_time

from core.models import (
    Apartment,
    Building,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    Income,
    Lease,
    Person,
    RentPayment,
    Tenant,
)
from core.services.daily_control_service import DailyControlService


@pytest.fixture
def building() -> Building:
    return Building.objects.create(street_number=836, name="Edifício 836", address="Rua Teste, 836")


@pytest.fixture
def apartment(building: Building) -> Apartment:
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1200.00"),
        max_tenants=2,
        is_rented=True,
    )


@pytest.fixture
def tenant() -> Tenant:
    return Tenant.objects.create(
        name="João Silva",
        cpf_cnpj="98765432100",
        phone="11999999999",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=7,
    )


@pytest.fixture
def lease(apartment: Apartment, tenant: Tenant) -> Lease:
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2025, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
    )


@pytest.fixture
def person() -> Person:
    return Person.objects.create(name="Rodrigo", relationship="Filho")


@pytest.mark.django_db
class TestDailyBreakdown:
    def test_returns_all_days_of_month(self, lease: Lease) -> None:
        """Should return exactly the number of days in the month."""
        result = DailyControlService.get_daily_breakdown(2026, 3)
        assert len(result) == 31  # March has 31 days

        # February 2026 (non-leap year)
        result_feb = DailyControlService.get_daily_breakdown(2026, 2)
        assert len(result_feb) == 28

    def test_rent_entries_on_due_day(self, lease: Lease) -> None:
        """Rent should appear on the responsible_tenant's due_day."""
        result = DailyControlService.get_daily_breakdown(2026, 3)
        # Tenant due_day=7, so day 7 (index 6) should have rent entry
        day_7 = result[6]
        assert day_7["date"] == "2026-03-07"

        rent_entries = [e for e in day_7["entries"] if e["type"] == "rent"]
        assert len(rent_entries) == 1
        assert rent_entries[0]["amount"] == 1200.0
        assert rent_entries[0]["paid"] is False

    def test_recurring_income_on_correct_day(self) -> None:
        """Recurring income should appear on its income_date day of month."""
        Income.objects.create(
            description="Aposentadoria",
            amount=Decimal("1500.00"),
            income_date=date(2026, 3, 7),
            is_recurring=True,
            expected_monthly_amount=Decimal("1500.00"),
        )
        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_7 = result[6]
        income_entries = [e for e in day_7["entries"] if e["type"] == "income"]
        assert len(income_entries) == 1
        assert income_entries[0]["description"] == "Aposentadoria"
        assert income_entries[0]["amount"] == 1500.0

    def test_installments_on_due_date(self, person: Person) -> None:
        """Expense installments should appear on their due_date."""
        expense = Expense.objects.create(
            description="MEGA BRICK",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            expense_date=date(2025, 10, 15),
            person=person,
            is_installment=True,
            total_installments=10,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=5,
            total_installments=10,
            amount=Decimal("60.00"),
            due_date=date(2026, 3, 15),
        )
        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_15 = result[14]
        exits = [e for e in day_15["exits"] if e["type"] == "installment"]
        assert len(exits) == 1
        assert exits[0]["amount"] == 60.0
        assert "MEGA BRICK" in exits[0]["description"]
        assert exits[0]["person"] == "Rodrigo"

    def test_paid_items_marked(self, lease: Lease) -> None:
        """Paid items should show paid=True."""
        RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 7),
        )
        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_7 = result[6]
        rent_entries = [e for e in day_7["entries"] if e["type"] == "rent"]
        assert len(rent_entries) == 1
        assert rent_entries[0]["paid"] is True

    def test_cumulative_balance(self, lease: Lease) -> None:
        """Cumulative balance should accumulate correctly across days."""
        result = DailyControlService.get_daily_breakdown(2026, 3)
        # Day 7 has rent +1200, days 1-6 have nothing
        # Cumulative on day 7 = 1200
        assert result[6]["cumulative_balance"] == Decimal("1200.00")
        # Day 8 has no events, cumulative stays 1200
        assert result[7]["cumulative_balance"] == Decimal("1200.00")

    def test_excludes_offset_expenses(self, person: Person) -> None:
        """Offset expenses should not appear in exits."""
        expense = Expense.objects.create(
            description="Desconto Sogros",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 3, 1),
            person=person,
            is_installment=True,
            total_installments=4,
            is_offset=True,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=4,
            amount=Decimal("50.00"),
            due_date=date(2026, 3, 10),
        )
        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_10 = result[9]
        assert len(day_10["exits"]) == 0


@pytest.mark.django_db
class TestMonthSummary:
    @freeze_time("2026-03-22")
    def test_summary_totals(self, lease: Lease) -> None:
        """Summary should calculate expected and received totals."""
        RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 7),
        )
        result = DailyControlService.get_month_summary(2026, 3)
        assert result["total_expected_income"] >= Decimal("1200.00")
        assert result["total_received_income"] >= Decimal("1200.00")

    @freeze_time("2026-03-22")
    def test_overdue_count(self, person: Person) -> None:
        """Should count overdue items correctly."""
        expense = Expense.objects.create(
            description="Parcela Vencida",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 2, 1),
            person=person,
            is_installment=True,
            total_installments=5,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=2,
            total_installments=5,
            amount=Decimal("20.00"),
            due_date=date(2026, 3, 10),
            is_paid=False,
        )
        result = DailyControlService.get_month_summary(2026, 3)
        assert result["overdue_count"] >= 1
        assert result["overdue_total"] >= Decimal("20.00")

    @freeze_time("2026-03-22")
    def test_current_balance(self, lease: Lease, person: Person) -> None:
        """Current balance = received - paid."""
        RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 7),
        )
        expense = Expense.objects.create(
            description="Parcela Paga",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 2, 1),
            person=person,
            is_installment=True,
            total_installments=5,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=2,
            total_installments=5,
            amount=Decimal("100.00"),
            due_date=date(2026, 3, 10),
            is_paid=True,
            paid_date=date(2026, 3, 10),
        )
        result = DailyControlService.get_month_summary(2026, 3)
        assert result["current_balance"] >= Decimal("1100.00")


@pytest.mark.django_db
class TestMarkPaid:
    def test_mark_installment_paid(self, person: Person) -> None:
        """Should mark an installment as paid."""
        expense = Expense.objects.create(
            description="Test Parcela",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_installment=True,
            total_installments=6,
        )
        inst = ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=6,
            amount=Decimal("100.00"),
            due_date=date(2026, 3, 15),
        )
        result = DailyControlService.mark_item_paid("installment", inst.id, date(2026, 3, 15))
        assert result["status"] == "ok"

        inst.refresh_from_db()
        assert inst.is_paid is True
        assert inst.paid_date == date(2026, 3, 15)

    def test_mark_expense_paid(self) -> None:
        """Should mark an expense as paid."""
        expense = Expense.objects.create(
            description="Conta de Luz",
            expense_type=ExpenseType.ELECTRICITY_BILL,
            total_amount=Decimal("250.00"),
            expense_date=date(2026, 3, 10),
        )
        result = DailyControlService.mark_item_paid("expense", expense.id, date(2026, 3, 10))
        assert result["status"] == "ok"

        expense.refresh_from_db()
        assert expense.is_paid is True
        assert expense.paid_date == date(2026, 3, 10)

    def test_mark_income_received(self) -> None:
        """Should mark an income as received."""
        income = Income.objects.create(
            description="Aposentadoria",
            amount=Decimal("1500.00"),
            income_date=date(2026, 3, 7),
        )
        result = DailyControlService.mark_item_paid("income", income.id, date(2026, 3, 7))
        assert result["status"] == "ok"

        income.refresh_from_db()
        assert income.is_received is True
        assert income.received_date == date(2026, 3, 7)

    def test_mark_already_paid_returns_status(self, person: Person) -> None:
        """Should return already_paid status if item is already paid."""
        expense = Expense.objects.create(
            description="Já Pago",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("50.00"),
            expense_date=date(2026, 3, 1),
            is_paid=True,
            paid_date=date(2026, 3, 1),
        )
        result = DailyControlService.mark_item_paid("expense", expense.id, date(2026, 3, 1))
        assert result["status"] == "already_paid"

    def test_mark_nonexistent_raises(self) -> None:
        """Should raise ObjectDoesNotExist for invalid IDs."""
        with pytest.raises(ObjectDoesNotExist):
            DailyControlService.mark_item_paid("installment", 999999, date(2026, 3, 1))

    def test_invalid_type_raises(self) -> None:
        """Should raise ValueError for invalid item_type."""
        with pytest.raises(ValueError, match="Tipo de item inválido"):
            DailyControlService.mark_item_paid("invalid_type", 1, date(2026, 3, 1))
