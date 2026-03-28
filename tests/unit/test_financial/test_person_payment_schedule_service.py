"""Tests for PersonPaymentScheduleService.

Covers month total calculation, bulk schedule configuration,
suggested payment amounts, and helper methods.
"""

from datetime import date
from decimal import Decimal

import pytest

from core.models import (
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    ExpenseType,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
)
from core.services.person_payment_schedule_service import PersonPaymentScheduleService


@pytest.fixture
def person() -> Person:
    return Person.objects.create(name="Camila", relationship="Esposa")


@pytest.fixture
def other_person() -> Person:
    return Person.objects.create(name="Rodrigo", relationship="Filho")


MARCH_2026 = date(2026, 3, 1)
APRIL_2026 = date(2026, 4, 1)


@pytest.mark.django_db
@pytest.mark.unit
class TestPersonMonthTotal:
    def test_total_due_from_installments(self, person: Person) -> None:
        """Installments with due_date in month are included in total_due."""
        expense = Expense.objects.create(
            description="Cartão Nubank",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 1, 10),
            person=person,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=3,
            amount=Decimal("100.00"),
            due_date=date(2026, 3, 10),
        )

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_due"] == Decimal("100.00")
        assert result["net_total"] == Decimal("100.00")

    def test_total_due_from_fixed_recurring(self, person: Person) -> None:
        """Fixed recurring expenses contribute their expected_monthly_amount to total_due."""
        Expense.objects.create(
            description="Academia",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("150.00"),
            recurrence_day=5,
        )

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_due"] == Decimal("150.00")

    def test_total_due_excludes_offsets(self, person: Person) -> None:
        """is_offset expenses reduce net_total rather than adding to total_due."""
        # Regular expense
        Expense.objects.create(
            description="Mercado",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 15),
            person=person,
            is_offset=False,
        )
        # Offset expense (discount)
        Expense.objects.create(
            description="Desconto sogros",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 3, 20),
            person=person,
            is_offset=True,
        )

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_due"] == Decimal("500.00")
        assert result["total_offsets"] == Decimal("200.00")
        assert result["net_total"] == Decimal("300.00")

    def test_total_due_excludes_skipped_expenses(self, person: Person) -> None:
        """Expenses with an ExpenseMonthSkip for the month are not counted."""
        expense = Expense.objects.create(
            description="Academia",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("150.00"),
            recurrence_day=5,
        )
        ExpenseMonthSkip.objects.create(expense=expense, reference_month=MARCH_2026)

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_due"] == Decimal("0.00")

    def test_total_scheduled_and_paid(self, person: Person) -> None:
        """total_scheduled and total_paid reflect PersonPaymentSchedule and PersonPayment records."""
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=10,
            amount=Decimal("300.00"),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=20,
            amount=Decimal("200.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=MARCH_2026,
            amount=Decimal("300.00"),
            payment_date=date(2026, 3, 10),
        )

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_scheduled"] == Decimal("500.00")
        assert result["total_paid"] == Decimal("300.00")
        assert result["pending"] == Decimal("-300.00")  # 0 net_total - 300 paid

    def test_only_counts_current_person_expenses(
        self, person: Person, other_person: Person
    ) -> None:
        """Expenses belonging to a different person are not included."""
        Expense.objects.create(
            description="Outro gasto",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("999.00"),
            expense_date=date(2026, 3, 5),
            person=other_person,
        )

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_due"] == Decimal("0.00")

    def test_recurring_expense_with_end_date_in_past_is_excluded(self, person: Person) -> None:
        """Recurring expense with end_date before month_start is excluded."""
        Expense.objects.create(
            description="Plano Antigo",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("80.00"),
            expense_date=date(2025, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("80.00"),
            recurrence_day=1,
            end_date=date(2026, 2, 28),  # ended before March
        )

        result = PersonPaymentScheduleService.get_person_month_total(person.pk, 2026, 3)

        assert result["total_due"] == Decimal("0.00")


@pytest.mark.django_db
@pytest.mark.unit
class TestBulkConfigure:
    def test_creates_schedules(self, person: Person) -> None:
        """bulk_configure creates new schedule entries for the given month."""
        entries = [
            {"due_day": 10, "amount": Decimal("500.00")},
            {"due_day": 25, "amount": Decimal("300.00")},
        ]

        created = PersonPaymentScheduleService.bulk_configure(person.pk, MARCH_2026, entries)

        assert len(created) == 2
        assert created[0].due_day == 10
        assert created[0].amount == Decimal("500.00")
        assert created[1].due_day == 25
        assert created[1].amount == Decimal("300.00")

        db_count = PersonPaymentSchedule.objects.filter(
            person=person, reference_month=MARCH_2026
        ).count()
        assert db_count == 2

    def test_replaces_existing_schedules(self, person: Person) -> None:
        """bulk_configure soft-deletes existing schedules before creating new ones."""
        # Create initial schedules
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=5,
            amount=Decimal("100.00"),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=15,
            amount=Decimal("200.00"),
        )

        # Replace with new entries
        new_entries = [{"due_day": 20, "amount": Decimal("750.00")}]
        created = PersonPaymentScheduleService.bulk_configure(person.pk, MARCH_2026, new_entries)

        # Only new schedules remain in the default (non-deleted) queryset
        active = list(
            PersonPaymentSchedule.objects.filter(person=person, reference_month=MARCH_2026)
        )
        assert len(active) == 1
        assert active[0].due_day == 20

        # Old schedules are soft-deleted
        deleted = PersonPaymentSchedule.all_objects.filter(
            person=person, reference_month=MARCH_2026, is_deleted=True
        )
        assert deleted.count() == 2

        assert len(created) == 1

    def test_does_not_affect_other_months(self, person: Person) -> None:
        """bulk_configure only replaces schedules for the target month."""
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=APRIL_2026,
            due_day=10,
            amount=Decimal("400.00"),
        )

        PersonPaymentScheduleService.bulk_configure(
            person.pk, MARCH_2026, [{"due_day": 5, "amount": Decimal("200.00")}]
        )

        april_count = PersonPaymentSchedule.objects.filter(
            person=person, reference_month=APRIL_2026
        ).count()
        assert april_count == 1


@pytest.mark.django_db
@pytest.mark.unit
class TestSuggestedPaymentAmount:
    def test_suggested_amount_no_prior_payments(self, person: Person) -> None:
        """With no payments made, suggested amount equals expected until the given day."""
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=10,
            amount=Decimal("300.00"),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=25,
            amount=Decimal("200.00"),
        )

        # On day 10, only the first schedule is due
        result = PersonPaymentScheduleService.get_suggested_payment(person.pk, MARCH_2026, 10)

        assert result["expected_until_date"] == Decimal("300.00")
        assert result["already_paid"] == Decimal("0.00")
        assert result["suggested_amount"] == Decimal("300.00")

    def test_suggested_amount_with_prior_payments(self, person: Person) -> None:
        """Suggested amount is reduced by prior payments in the same month."""
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=10,
            amount=Decimal("300.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=MARCH_2026,
            amount=Decimal("150.00"),
            payment_date=date(2026, 3, 8),
        )

        result = PersonPaymentScheduleService.get_suggested_payment(person.pk, MARCH_2026, 10)

        assert result["expected_until_date"] == Decimal("300.00")
        assert result["already_paid"] == Decimal("150.00")
        assert result["suggested_amount"] == Decimal("150.00")

    def test_suggested_amount_overpaid_returns_zero(self, person: Person) -> None:
        """If person already paid more than expected, suggested amount is 0 (not negative)."""
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=10,
            amount=Decimal("200.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=MARCH_2026,
            amount=Decimal("500.00"),
            payment_date=date(2026, 3, 5),
        )

        result = PersonPaymentScheduleService.get_suggested_payment(person.pk, MARCH_2026, 10)

        assert result["suggested_amount"] == Decimal("0.00")


@pytest.mark.django_db
@pytest.mark.unit
class TestHelperMethods:
    def test_has_schedule_returns_true_when_schedules_exist(self, person: Person) -> None:
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=MARCH_2026,
            due_day=10,
            amount=Decimal("100.00"),
        )
        assert PersonPaymentScheduleService.has_schedule(person.pk, MARCH_2026) is True

    def test_has_schedule_returns_false_when_no_schedules(self, person: Person) -> None:
        assert PersonPaymentScheduleService.has_schedule(person.pk, MARCH_2026) is False

    def test_get_schedules_for_month_ordered_by_due_day(self, person: Person) -> None:
        PersonPaymentSchedule.objects.create(
            person=person, reference_month=MARCH_2026, due_day=25, amount=Decimal("100.00")
        )
        PersonPaymentSchedule.objects.create(
            person=person, reference_month=MARCH_2026, due_day=5, amount=Decimal("200.00")
        )
        PersonPaymentSchedule.objects.create(
            person=person, reference_month=MARCH_2026, due_day=15, amount=Decimal("150.00")
        )

        schedules = PersonPaymentScheduleService.get_schedules_for_month(person.pk, MARCH_2026)

        assert len(schedules) == 3
        assert [s.due_day for s in schedules] == [5, 15, 25]

    def test_is_schedule_paid_when_fully_paid(self, person: Person) -> None:
        PersonPaymentSchedule.objects.create(
            person=person, reference_month=MARCH_2026, due_day=10, amount=Decimal("300.00")
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=MARCH_2026,
            amount=Decimal("300.00"),
            payment_date=date(2026, 3, 10),
        )

        assert PersonPaymentScheduleService.is_schedule_paid(person.pk, MARCH_2026, 10) is True

    def test_is_schedule_paid_when_underpaid(self, person: Person) -> None:
        PersonPaymentSchedule.objects.create(
            person=person, reference_month=MARCH_2026, due_day=10, amount=Decimal("300.00")
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=MARCH_2026,
            amount=Decimal("100.00"),
            payment_date=date(2026, 3, 8),
        )

        assert PersonPaymentScheduleService.is_schedule_paid(person.pk, MARCH_2026, 10) is False

    def test_is_schedule_paid_returns_false_when_no_schedules(self, person: Person) -> None:
        """Returns False when there are no schedules (expected is 0)."""
        assert PersonPaymentScheduleService.is_schedule_paid(person.pk, MARCH_2026, 10) is False
