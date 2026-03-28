# Person Payment Scheduling & Daily Control Enhancements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable payment schedules per person per month, aggregate person expenses in daily control, and allow skipping expenses for specific months.

**Architecture:** Two new models (`PersonPaymentSchedule`, `ExpenseMonthSkip`) with CRUD endpoints. The `DailyControlService` is modified to group person expenses when a schedule exists. `CashFlowService` and `FinancialDashboardService` respect expense skips. Frontend gets a schedule configuration UI and modified daily control with aggregated person entries + pay modal.

**Tech Stack:** Django 5.2 + DRF (backend), Next.js 14 + React 18 + TanStack Query + Zod (frontend), PostgreSQL, Vitest + MSW (frontend tests), pytest (backend tests).

**Spec:** `docs/superpowers/specs/2026-03-28-person-payment-scheduling-daily-control.md`

---

## File Structure

### Backend — New Files
- `core/migrations/0030_person_payment_schedule.py` — migration for PersonPaymentSchedule
- `core/migrations/0031_expense_month_skip.py` — migration for ExpenseMonthSkip
- `core/services/person_payment_schedule_service.py` — person total calculation + schedule logic
- `tests/unit/test_financial/test_person_payment_schedule_service.py` — service tests

### Backend — Modified Files
- `core/models.py` — add PersonPaymentSchedule and ExpenseMonthSkip models
- `core/serializers.py` — add PersonPaymentScheduleSerializer and ExpenseMonthSkipSerializer
- `core/views.py` — add PersonPaymentScheduleViewSet and ExpenseMonthSkipViewSet
- `core/urls.py` — register new viewsets
- `core/signals.py` — add cache invalidation for new models
- `core/services/daily_control_service.py` — aggregate person entries, skip logic, new mark_paid type
- `core/services/cash_flow_service.py` — respect ExpenseMonthSkip
- `core/services/financial_dashboard_service.py` — respect ExpenseMonthSkip
- `core/viewsets/financial_dashboard_views.py` — add person_schedule mark_paid type

### Frontend — New Files
- `frontend/lib/schemas/person-payment-schedule.schema.ts` — Zod schema
- `frontend/lib/schemas/expense-month-skip.schema.ts` — Zod schema
- `frontend/lib/api/hooks/use-person-payment-schedules.ts` — TanStack Query hooks
- `frontend/lib/api/hooks/use-expense-month-skips.ts` — TanStack Query hooks
- `frontend/app/(dashboard)/financial/expenses/_components/payment-schedule-section.tsx` — schedule config UI
- `frontend/app/(dashboard)/financial/daily/_components/person-pay-modal.tsx` — pay modal with suggested amount
- `frontend/tests/mocks/data/person-payment-schedules.ts` — mock data
- `frontend/tests/mocks/data/expense-month-skips.ts` — mock data

### Frontend — Modified Files
- `frontend/lib/api/hooks/use-daily-control.ts` — new types + person_schedule mark_paid
- `frontend/app/(dashboard)/financial/expenses/page.tsx` — add payment schedule section
- `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx` — aggregated person entries + skip button
- `frontend/app/(dashboard)/financial/daily/_components/day-detail-drawer.tsx` — aggregated person entries
- `frontend/tests/mocks/handlers.ts` — new MSW handlers
- `frontend/tests/mocks/data/index.ts` — export new mock data

---

## Task 1: Backend Models + Migrations

**Files:**
- Modify: `core/models.py` (after PersonPayment, ~line 1152)
- Create: `core/migrations/0030_person_payment_schedule.py` (auto-generated)
- Create: `core/migrations/0031_expense_month_skip.py` (auto-generated)

- [ ] **Step 1: Add PersonPaymentSchedule model**

In `core/models.py`, after the `PersonPayment` class (line ~1152), add:

```python
class PersonPaymentSchedule(AuditMixin, SoftDeleteMixin, models.Model):
    """Configurable payment schedule entry for a person in a specific month."""

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="payment_schedules",
    )
    reference_month = models.DateField(
        help_text="First day of the month (e.g., 2026-03-01)",
    )
    due_day = models.PositiveSmallIntegerField(
        help_text="Day of month for this payment (1-31, capped to last day)",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["reference_month", "due_day"]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "reference_month", "due_day"],
                condition=models.Q(is_deleted=False),
                name="unique_person_schedule_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person.name} - {self.reference_month:%m/%Y} day {self.due_day}: R${self.amount}"
```

- [ ] **Step 2: Add ExpenseMonthSkip model**

After `PersonPaymentSchedule`, add:

```python
class ExpenseMonthSkip(AuditMixin, models.Model):
    """Marks an expense as not charged in a specific month."""

    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="month_skips",
    )
    reference_month = models.DateField(
        help_text="First day of the month (e.g., 2026-03-01)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "reference_month"],
                name="unique_expense_skip_per_month",
            ),
        ]

    def __str__(self) -> str:
        return f"Skip: {self.expense.description} - {self.reference_month:%m/%Y}"
```

- [ ] **Step 3: Generate migrations**

```bash
python manage.py makemigrations core --name person_payment_schedule
python manage.py makemigrations core --name expense_month_skip
```

- [ ] **Step 4: Apply migrations and verify**

```bash
python manage.py migrate
```

- [ ] **Step 5: Commit**

```bash
git add core/models.py core/migrations/0030_*.py core/migrations/0031_*.py
git commit -m "feat(models): add PersonPaymentSchedule and ExpenseMonthSkip models"
```

---

## Task 2: Backend Serializers

**Files:**
- Modify: `core/serializers.py` (after PersonPaymentSerializer, ~line 1031)

- [ ] **Step 1: Add imports for new models**

At the top of `core/serializers.py`, add `PersonPaymentSchedule` and `ExpenseMonthSkip` to the model imports (around line 11-32).

- [ ] **Step 2: Add PersonPaymentScheduleSerializer**

After `PersonPaymentSerializer`:

```python
class PersonPaymentScheduleSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="person",
        write_only=True,
    )

    class Meta:
        model = PersonPaymentSchedule
        fields = [
            "id",
            "person",
            "person_id",
            "reference_month",
            "due_day",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_reference_month(self, value: date) -> date:
        if value.day != 1:
            msg = "reference_month must be the first day of the month."
            raise serializers.ValidationError(msg)
        return value

    def validate_due_day(self, value: int) -> int:
        if not 1 <= value <= 31:
            msg = "due_day must be between 1 and 31."
            raise serializers.ValidationError(msg)
        return value
```

- [ ] **Step 3: Add ExpenseMonthSkipSerializer**

```python
class ExpenseMonthSkipSerializer(serializers.ModelSerializer):
    expense_id = serializers.PrimaryKeyRelatedField(
        queryset=Expense.objects.all(),
        source="expense",
        write_only=True,
    )
    expense_description = serializers.CharField(source="expense.description", read_only=True)

    class Meta:
        model = ExpenseMonthSkip
        fields = [
            "id",
            "expense_id",
            "expense_description",
            "reference_month",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "expense_description", "created_at", "updated_at"]

    def validate_reference_month(self, value: date) -> date:
        if value.day != 1:
            msg = "reference_month must be the first day of the month."
            raise serializers.ValidationError(msg)
        return value
```

- [ ] **Step 4: Run type checking**

```bash
mypy core/serializers.py
```

- [ ] **Step 5: Commit**

```bash
git add core/serializers.py
git commit -m "feat(serializers): add PersonPaymentSchedule and ExpenseMonthSkip serializers"
```

---

## Task 3: Backend Person Payment Schedule Service

**Files:**
- Create: `core/services/person_payment_schedule_service.py`
- Create: `tests/unit/test_financial/test_person_payment_schedule_service.py`

- [ ] **Step 1: Write tests for person_month_total calculation**

Create `tests/unit/test_financial/test_person_payment_schedule_service.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from core.models import (
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
)
from core.services.person_payment_schedule_service import PersonPaymentScheduleService


@pytest.mark.unit
class TestPersonMonthTotal:
    def test_total_due_from_installments(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        expense = Expense.objects.create(
            description="Cartão Nubank",
            expense_type="card_purchase",
            total_amount=Decimal("6000.00"),
            expense_date=date(2026, 1, 15),
            person=person,
            is_installment=True,
            total_installments=6,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=6,
            amount=Decimal("1000.00"),
            due_date=date(2026, 3, 15),
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=4,
            total_installments=6,
            amount=Decimal("1000.00"),
            due_date=date(2026, 4, 15),
        )

        result = PersonPaymentScheduleService.get_person_month_total(
            person_id=person.pk, year=2026, month=3
        )
        assert result["total_due"] == Decimal("1000.00")

    def test_total_due_from_fixed_recurring(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        Expense.objects.create(
            description="Aluguel escritório",
            expense_type="fixed_expense",
            total_amount=Decimal("2000.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("2000.00"),
            recurrence_day=10,
        )

        result = PersonPaymentScheduleService.get_person_month_total(
            person_id=person.pk, year=2026, month=3
        )
        assert result["total_due"] == Decimal("2000.00")

    def test_total_due_excludes_offsets(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        expense = Expense.objects.create(
            description="Cartão Nubank",
            expense_type="card_purchase",
            total_amount=Decimal("3000.00"),
            expense_date=date(2026, 1, 15),
            person=person,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=3,
            amount=Decimal("1000.00"),
            due_date=date(2026, 3, 15),
        )
        offset_expense = Expense.objects.create(
            description="Desconto sogros",
            expense_type="card_purchase",
            total_amount=Decimal("600.00"),
            expense_date=date(2026, 1, 15),
            person=person,
            is_offset=True,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=offset_expense,
            installment_number=3,
            total_installments=3,
            amount=Decimal("200.00"),
            due_date=date(2026, 3, 15),
        )

        result = PersonPaymentScheduleService.get_person_month_total(
            person_id=person.pk, year=2026, month=3
        )
        assert result["total_due"] == Decimal("1000.00")
        assert result["total_offsets"] == Decimal("200.00")
        assert result["net_total"] == Decimal("800.00")

    def test_total_due_excludes_skipped_expenses(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        expense = Expense.objects.create(
            description="Aluguel escritório",
            expense_type="fixed_expense",
            total_amount=Decimal("2000.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("2000.00"),
            recurrence_day=10,
        )
        ExpenseMonthSkip.objects.create(
            expense=expense, reference_month=date(2026, 3, 1)
        )

        result = PersonPaymentScheduleService.get_person_month_total(
            person_id=person.pk, year=2026, month=3
        )
        assert result["total_due"] == Decimal("0.00")

    def test_total_scheduled_and_paid(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        Expense.objects.create(
            description="Fixo",
            expense_type="fixed_expense",
            total_amount=Decimal("10000.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("10000.00"),
            recurrence_day=10,
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=5,
            amount=Decimal("4000.00"),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=27,
            amount=Decimal("5000.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            amount=Decimal("3000.00"),
            payment_date=date(2026, 3, 3),
        )

        result = PersonPaymentScheduleService.get_person_month_total(
            person_id=person.pk, year=2026, month=3
        )
        assert result["total_scheduled"] == Decimal("9000.00")
        assert result["total_paid"] == Decimal("3000.00")
        assert result["pending"] == Decimal("7000.00")


@pytest.mark.unit
class TestBulkConfigure:
    def test_creates_schedules(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        entries = [
            {"due_day": 5, "amount": Decimal("4000.00")},
            {"due_day": 27, "amount": Decimal("5000.00")},
        ]
        result = PersonPaymentScheduleService.bulk_configure(
            person_id=person.pk,
            reference_month=date(2026, 3, 1),
            entries=entries,
        )
        assert len(result) == 2
        assert PersonPaymentSchedule.objects.filter(
            person=person, reference_month=date(2026, 3, 1)
        ).count() == 2

    def test_replaces_existing_schedules(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=10,
            amount=Decimal("5000.00"),
        )
        entries = [{"due_day": 5, "amount": Decimal("4000.00")}]
        PersonPaymentScheduleService.bulk_configure(
            person_id=person.pk,
            reference_month=date(2026, 3, 1),
            entries=entries,
        )
        schedules = PersonPaymentSchedule.objects.filter(
            person=person, reference_month=date(2026, 3, 1)
        )
        assert schedules.count() == 1
        assert schedules.first().due_day == 5


@pytest.mark.unit
class TestSuggestedPaymentAmount:
    def test_suggested_amount_no_prior_payments(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=5,
            amount=Decimal("4000.00"),
        )

        result = PersonPaymentScheduleService.get_suggested_payment(
            person_id=person.pk,
            reference_month=date(2026, 3, 1),
            due_day=5,
        )
        assert result["expected_until_date"] == Decimal("4000.00")
        assert result["already_paid"] == Decimal("0.00")
        assert result["suggested_amount"] == Decimal("4000.00")

    def test_suggested_amount_with_prior_payments(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=5,
            amount=Decimal("4000.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            amount=Decimal("1000.00"),
            payment_date=date(2026, 3, 1),
        )

        result = PersonPaymentScheduleService.get_suggested_payment(
            person_id=person.pk,
            reference_month=date(2026, 3, 1),
            due_day=5,
        )
        assert result["suggested_amount"] == Decimal("3000.00")

    def test_suggested_amount_overpaid(self, db: None, admin_user) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=5,
            amount=Decimal("4000.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            amount=Decimal("5000.00"),
            payment_date=date(2026, 3, 1),
        )

        result = PersonPaymentScheduleService.get_suggested_payment(
            person_id=person.pk,
            reference_month=date(2026, 3, 1),
            due_day=5,
        )
        assert result["suggested_amount"] == Decimal("0.00")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_financial/test_person_payment_schedule_service.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: Implement PersonPaymentScheduleService**

Create `core/services/person_payment_schedule_service.py`:

```python
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum

from core.models import (
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
)


class PersonPaymentScheduleService:
    @staticmethod
    def get_person_month_total(person_id: int, year: int, month: int) -> dict[str, Decimal]:
        """Calculate total due for a person in a given month, respecting skips and offsets."""
        reference_month = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        skipped_expense_ids = set(
            ExpenseMonthSkip.objects.filter(
                reference_month=reference_month,
                expense__person_id=person_id,
            ).values_list("expense_id", flat=True)
        )

        # Installments due this month (non-offset, non-skipped)
        installment_total = (
            ExpenseInstallment.objects.filter(
                expense__person_id=person_id,
                expense__is_offset=False,
                due_date__gte=month_start,
                due_date__lte=month_end,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        # Fixed recurring expenses (non-offset, non-skipped, active in this month)
        recurring_expenses = Expense.objects.filter(
            person_id=person_id,
            is_recurring=True,
            is_offset=False,
            expense_date__lte=month_end,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=month_start))

        recurring_total = Decimal("0.00")
        for exp in recurring_expenses:
            if exp.pk not in skipped_expense_ids:
                recurring_total += exp.expected_monthly_amount or Decimal("0.00")

        # One-time expenses in this month (non-offset, non-skipped, non-installment, non-recurring)
        one_time_total = (
            Expense.objects.filter(
                person_id=person_id,
                is_offset=False,
                is_recurring=False,
                is_installment=False,
                expense_date__gte=month_start,
                expense_date__lte=month_end,
            )
            .exclude(pk__in=skipped_expense_ids)
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        total_due = installment_total + recurring_total + one_time_total

        # Offsets (discounts) — same filters but is_offset=True
        offset_installments = (
            ExpenseInstallment.objects.filter(
                expense__person_id=person_id,
                expense__is_offset=True,
                due_date__gte=month_start,
                due_date__lte=month_end,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        offset_recurring = Decimal("0.00")
        offset_recurring_expenses = Expense.objects.filter(
            person_id=person_id,
            is_recurring=True,
            is_offset=True,
            expense_date__lte=month_end,
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=month_start))
        for exp in offset_recurring_expenses:
            if exp.pk not in skipped_expense_ids:
                offset_recurring += exp.expected_monthly_amount or Decimal("0.00")

        offset_one_time = (
            Expense.objects.filter(
                person_id=person_id,
                is_offset=True,
                is_recurring=False,
                is_installment=False,
                expense_date__gte=month_start,
                expense_date__lte=month_end,
            )
            .exclude(pk__in=skipped_expense_ids)
            .aggregate(total=Sum("total_amount"))["total"]
            or Decimal("0.00")
        )

        total_offsets = offset_installments + offset_recurring + offset_one_time
        net_total = total_due - total_offsets

        # Scheduled amounts
        total_scheduled = (
            PersonPaymentSchedule.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        # Paid amounts
        total_paid = (
            PersonPayment.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        return {
            "total_due": total_due,
            "total_offsets": total_offsets,
            "net_total": net_total,
            "total_scheduled": total_scheduled,
            "total_paid": total_paid,
            "pending": net_total - total_paid,
        }

    @staticmethod
    def bulk_configure(
        person_id: int,
        reference_month: date,
        entries: list[dict[str, Any]],
    ) -> list[PersonPaymentSchedule]:
        """Replace all schedules for a person/month with new entries."""
        person = Person.objects.get(pk=person_id)

        # Soft-delete existing schedules
        PersonPaymentSchedule.objects.filter(
            person=person,
            reference_month=reference_month,
        ).delete()

        # Create new schedules
        schedules = []
        for entry in entries:
            schedule = PersonPaymentSchedule.objects.create(
                person=person,
                reference_month=reference_month,
                due_day=entry["due_day"],
                amount=entry["amount"],
            )
            schedules.append(schedule)
        return schedules

    @staticmethod
    def get_suggested_payment(
        person_id: int,
        reference_month: date,
        due_day: int,
    ) -> dict[str, Decimal]:
        """Calculate suggested payment amount for a specific schedule entry."""
        expected_until_date = (
            PersonPaymentSchedule.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
                due_day__lte=due_day,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        already_paid = (
            PersonPayment.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        suggested = max(Decimal("0.00"), expected_until_date - already_paid)

        return {
            "expected_until_date": expected_until_date,
            "already_paid": already_paid,
            "suggested_amount": suggested,
        }

    @staticmethod
    def has_schedule(person_id: int, reference_month: date) -> bool:
        """Check if a person has payment schedules configured for a month."""
        return PersonPaymentSchedule.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
        ).exists()

    @staticmethod
    def get_schedules_for_month(
        person_id: int, reference_month: date
    ) -> list[PersonPaymentSchedule]:
        """Get all schedules for a person in a month, ordered by due_day."""
        return list(
            PersonPaymentSchedule.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
            ).order_by("due_day")
        )

    @staticmethod
    def is_schedule_paid(
        person_id: int, reference_month: date, due_day: int
    ) -> bool:
        """Check if a specific schedule entry is effectively paid."""
        expected = (
            PersonPaymentSchedule.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
                due_day__lte=due_day,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        paid = (
            PersonPayment.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        return paid >= expected
```

- [ ] **Step 4: Remove `from __future__ import annotations`**

The project rule says never use `from __future__ import annotations`. Fix the import at the top — use direct type imports instead.

Replace the top of the file:
```python
import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum

from core.models import (
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_financial/test_person_payment_schedule_service.py -v
```

Expected: All PASS

- [ ] **Step 6: Run type checking**

```bash
mypy core/services/person_payment_schedule_service.py
```

- [ ] **Step 7: Commit**

```bash
git add core/services/person_payment_schedule_service.py tests/unit/test_financial/test_person_payment_schedule_service.py
git commit -m "feat(service): add PersonPaymentScheduleService with total calculation, bulk configure, suggested payment"
```

---

## Task 4: Backend ViewSets + URL Registration

**Files:**
- Modify: `core/views.py` (add new ViewSets)
- Modify: `core/urls.py` (register routes, ~line 58)
- Modify: `core/viewsets/financial_dashboard_views.py` (add person_schedule to mark_paid)

- [ ] **Step 1: Add PersonPaymentScheduleViewSet to core/views.py**

Find the existing `PersonPaymentViewSet` in `core/views.py` and add after it:

```python
class PersonPaymentScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = PersonPaymentScheduleSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[PersonPaymentSchedule]:
        qs = PersonPaymentSchedule.objects.select_related("person")
        person_id = self.request.query_params.get("person_id")
        reference_month = self.request.query_params.get("reference_month")
        if person_id:
            qs = qs.filter(person_id=person_id)
        if reference_month:
            qs = qs.filter(reference_month=reference_month)
        return qs

    @action(detail=False, methods=["post"])
    def bulk_configure(self, request: Request) -> Response:
        person_id = request.data.get("person_id")
        reference_month_str = request.data.get("reference_month")
        entries = request.data.get("entries", [])

        if not person_id or not reference_month_str or not entries:
            return Response(
                {"error": "person_id, reference_month, and entries are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reference_month = date.fromisoformat(reference_month_str)
        schedules = PersonPaymentScheduleService.bulk_configure(
            person_id=int(person_id),
            reference_month=reference_month,
            entries=[
                {"due_day": int(e["due_day"]), "amount": Decimal(str(e["amount"]))}
                for e in entries
            ],
        )

        total_info = PersonPaymentScheduleService.get_person_month_total(
            person_id=int(person_id),
            year=reference_month.year,
            month=reference_month.month,
        )

        serializer = PersonPaymentScheduleSerializer(schedules, many=True)
        return Response({
            "schedules": serializer.data,
            "total_configured": str(total_info["total_scheduled"]),
            "total_due": str(total_info["net_total"]),
        })

    @action(detail=False, methods=["get"])
    def person_month_total(self, request: Request) -> Response:
        person_id = request.query_params.get("person_id")
        reference_month_str = request.query_params.get("reference_month")

        if not person_id or not reference_month_str:
            return Response(
                {"error": "person_id and reference_month are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reference_month = date.fromisoformat(reference_month_str)
        result = PersonPaymentScheduleService.get_person_month_total(
            person_id=int(person_id),
            year=reference_month.year,
            month=reference_month.month,
        )

        return Response({k: str(v) for k, v in result.items()})
```

- [ ] **Step 2: Add ExpenseMonthSkipViewSet to core/views.py**

```python
class ExpenseMonthSkipViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseMonthSkipSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[ExpenseMonthSkip]:
        qs = ExpenseMonthSkip.objects.select_related("expense")
        reference_month = self.request.query_params.get("reference_month")
        expense_id = self.request.query_params.get("expense_id")
        if reference_month:
            qs = qs.filter(reference_month=reference_month)
        if expense_id:
            qs = qs.filter(expense_id=expense_id)
        return qs
```

- [ ] **Step 3: Add imports to core/views.py**

Add the new models, serializers, and service to the imports at the top of `core/views.py`.

- [ ] **Step 4: Register routes in core/urls.py**

After the existing `person-payments` registration (~line 55), add:

```python
router.register(r"person-payment-schedules", PersonPaymentScheduleViewSet, basename="person-payment-schedules")
router.register(r"expense-month-skips", ExpenseMonthSkipViewSet, basename="expense-month-skips")
```

- [ ] **Step 5: Add person_schedule to DailyControlViewSet mark_paid**

In `core/viewsets/financial_dashboard_views.py`, in the `mark_paid` action, add a new item_type handler:

```python
elif item_type == "person_schedule":
    person_id = request.data.get("person_id")
    amount = request.data.get("amount")
    if not person_id or not amount:
        return Response(
            {"error": "person_id and amount are required for person_schedule."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    reference_month = date(
        int(request.data.get("year", date.today().year)),
        int(request.data.get("month", date.today().month)),
        1,
    )
    PersonPayment.objects.create(
        person_id=int(person_id),
        reference_month=reference_month,
        amount=Decimal(str(amount)),
        payment_date=payment_date,
    )
    return Response({"status": "ok", "message": "Person payment recorded."})
```

Also update the `MarkPaidRequest` item_type validation to include `"person_schedule"`.

- [ ] **Step 6: Run type checking and linting**

```bash
ruff check core/views.py core/urls.py core/viewsets/financial_dashboard_views.py
mypy core/views.py core/viewsets/financial_dashboard_views.py
```

- [ ] **Step 7: Commit**

```bash
git add core/views.py core/urls.py core/viewsets/financial_dashboard_views.py
git commit -m "feat(api): add PersonPaymentSchedule and ExpenseMonthSkip endpoints with bulk_configure"
```

---

## Task 5: Modify Daily Control Service

**Files:**
- Modify: `core/services/daily_control_service.py`
- Modify: `tests/unit/test_financial/test_daily_control_service.py`

- [ ] **Step 1: Write tests for aggregated person entries in daily control**

Add to `tests/unit/test_financial/test_daily_control_service.py`:

```python
@pytest.mark.unit
class TestDailyBreakdownPersonSchedule:
    def test_person_with_schedule_shows_aggregated_entries(self, db: None) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        expense = Expense.objects.create(
            description="Cartão Nubank",
            expense_type="card_purchase",
            total_amount=Decimal("3000.00"),
            expense_date=date(2026, 1, 15),
            person=person,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=3,
            amount=Decimal("1000.00"),
            due_date=date(2026, 3, 15),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=5,
            amount=Decimal("500.00"),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=27,
            amount=Decimal("500.00"),
        )

        result = DailyControlService.get_daily_breakdown(2026, 3)

        # Day 5 should have aggregated person entry
        day_5 = next(d for d in result if d["date"] == "2026-03-05")
        person_exits = [e for e in day_5["exits"] if e["type"] == "person_schedule"]
        assert len(person_exits) == 1
        assert person_exits[0]["person"] == "Rodrigo"
        assert person_exits[0]["amount"] == 500.0

        # Day 15 should NOT have the individual installment (person has schedule)
        day_15 = next(d for d in result if d["date"] == "2026-03-15")
        individual_exits = [
            e for e in day_15["exits"]
            if e.get("person") == "Rodrigo" and e["type"] != "person_schedule"
        ]
        assert len(individual_exits) == 0

    def test_person_without_schedule_shows_individual_entries(self, db: None) -> None:
        person = Person.objects.create(name="Maria", relationship="Contractor")
        expense = Expense.objects.create(
            description="Empréstimo",
            expense_type="personal_loan",
            total_amount=Decimal("6000.00"),
            expense_date=date(2026, 1, 15),
            person=person,
            is_installment=True,
            total_installments=6,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=6,
            amount=Decimal("1000.00"),
            due_date=date(2026, 3, 15),
        )
        # No schedule for Maria

        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_15 = next(d for d in result if d["date"] == "2026-03-15")
        individual_exits = [
            e for e in day_15["exits"] if e.get("person") == "Maria"
        ]
        assert len(individual_exits) == 1

    def test_schedule_paid_status_with_early_payment(self, db: None) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=5,
            amount=Decimal("4000.00"),
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            due_day=27,
            amount=Decimal("5000.00"),
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            amount=Decimal("10000.00"),
            payment_date=date(2026, 3, 3),
        )

        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_5 = next(d for d in result if d["date"] == "2026-03-05")
        day_27 = next(d for d in result if d["date"] == "2026-03-27")
        person_day5 = [e for e in day_5["exits"] if e["type"] == "person_schedule"]
        person_day27 = [e for e in day_27["exits"] if e["type"] == "person_schedule"]
        assert person_day5[0]["paid"] is True
        assert person_day27[0]["paid"] is True


@pytest.mark.unit
class TestDailyBreakdownSkippedExpenses:
    def test_skipped_expense_excluded_from_breakdown(self, db: None) -> None:
        expense = Expense.objects.create(
            description="Aluguel escritório",
            expense_type="fixed_expense",
            total_amount=Decimal("2000.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("2000.00"),
            recurrence_day=10,
        )
        ExpenseMonthSkip.objects.create(
            expense=expense, reference_month=date(2026, 3, 1)
        )

        result = DailyControlService.get_daily_breakdown(2026, 3)
        day_10 = next(d for d in result if d["date"] == "2026-03-10")
        matching = [
            e for e in day_10["exits"] if e["description"] == "Aluguel escritório"
        ]
        assert len(matching) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_financial/test_daily_control_service.py -k "PersonSchedule or SkippedExpenses" -v
```

Expected: FAIL

- [ ] **Step 3: Modify DailyControlService.get_daily_breakdown**

In `core/services/daily_control_service.py`, modify the `get_daily_breakdown` method:

1. At the start of the method, load:
   - All `ExpenseMonthSkip` for the month → `skipped_expense_ids: set[int]`
   - All persons with `PersonPaymentSchedule` for the month → `scheduled_person_ids: set[int]`

2. In exit collection:
   - When collecting installments, recurring, and one-time expenses: exclude `expense_id in skipped_expense_ids`
   - When collecting person-linked expenses: if `expense.person_id in scheduled_person_ids`, skip the individual entry

3. After regular exit collection, add aggregated person entries:
   - For each person with schedule, get their schedules
   - For each schedule entry, create an exit with `type="person_schedule"`, `person=person.name`, `amount=schedule.amount`
   - Calculate `paid` status using `PersonPaymentScheduleService.is_schedule_paid()`
   - Add `person_id`, `reference_month` for the frontend to use in mark_paid

Key code additions in the exit collection section:

```python
from core.models import ExpenseMonthSkip, PersonPaymentSchedule
from core.services.person_payment_schedule_service import PersonPaymentScheduleService

# At the start of get_daily_breakdown:
skipped_expense_ids = set(
    ExpenseMonthSkip.objects.filter(
        reference_month=date(year, month, 1),
    ).values_list("expense_id", flat=True)
)
scheduled_person_ids = set(
    PersonPaymentSchedule.objects.filter(
        reference_month=date(year, month, 1),
    ).values_list("person_id", flat=True).distinct()
)

# When collecting installment exits, add to the queryset filter:
.exclude(expense_id__in=skipped_expense_ids)
# And for person-linked ones:
# Skip if expense.person_id in scheduled_person_ids

# After all regular exits are collected, add person schedule entries:
for person_id in scheduled_person_ids:
    schedules = PersonPaymentScheduleService.get_schedules_for_month(
        person_id, date(year, month, 1)
    )
    person_name = Person.objects.get(pk=person_id).name
    total_paid = (
        PersonPayment.objects.filter(
            person_id=person_id,
            reference_month=date(year, month, 1),
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    for schedule in schedules:
        capped_day = min(schedule.due_day, days_in_month)
        is_paid = PersonPaymentScheduleService.is_schedule_paid(
            person_id, date(year, month, 1), schedule.due_day
        )
        # Find or create the day entry and add the exit
        day_exits = exits_by_day.setdefault(capped_day, [])
        day_exits.append({
            "type": "person_schedule",
            "id": schedule.pk,
            "description": person_name,
            "amount": float(schedule.amount),
            "due": True,
            "paid": is_paid,
            "person": person_name,
            "person_id": person_id,
            "reference_month": str(date(year, month, 1)),
            "total_paid_month": float(total_paid),
            "payment_date": None,  # Will be set from PersonPayment if exists
        })
```

The exact modification will depend on the internal structure of `get_daily_breakdown`. The key principle is:
- Filter out skipped expenses from all exit queries
- Filter out individual person expenses when person has a schedule
- Add aggregated person entries from the schedule

- [ ] **Step 4: Also modify `get_month_summary` to handle schedules and skips**

Apply the same skipped_expense_ids filtering to the summary queries. For persons with schedules, use the schedule totals instead of individual expense totals to avoid double-counting.

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_financial/test_daily_control_service.py -v
```

Expected: All PASS

- [ ] **Step 6: Run full financial test suite**

```bash
python -m pytest tests/unit/test_financial/ -v
```

Expected: All PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add core/services/daily_control_service.py tests/unit/test_financial/test_daily_control_service.py
git commit -m "feat(daily-control): aggregate person expenses by schedule, exclude skipped expenses"
```

---

## Task 6: Modify Cash Flow + Dashboard Services

**Files:**
- Modify: `core/services/cash_flow_service.py`
- Modify: `core/services/financial_dashboard_service.py`

- [ ] **Step 1: Write tests for skip-aware cash flow**

Add to `tests/unit/test_financial/test_cash_flow_service.py`:

```python
@pytest.mark.unit
class TestCashFlowSkippedExpenses:
    def test_monthly_expenses_excludes_skipped(self, db: None) -> None:
        expense = Expense.objects.create(
            description="Fixo",
            expense_type="fixed_expense",
            total_amount=Decimal("2000.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("2000.00"),
            recurrence_day=10,
        )
        ExpenseMonthSkip.objects.create(
            expense=expense, reference_month=date(2026, 3, 1)
        )

        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["fixed_expenses"]["total"] == Decimal("0.00")

    def test_person_summary_excludes_skipped(self, db: None) -> None:
        person = Person.objects.create(name="Rodrigo", relationship="Contractor")
        expense = Expense.objects.create(
            description="Fixo",
            expense_type="fixed_expense",
            total_amount=Decimal("2000.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            is_recurring=True,
            expected_monthly_amount=Decimal("2000.00"),
            recurrence_day=10,
        )
        ExpenseMonthSkip.objects.create(
            expense=expense, reference_month=date(2026, 3, 1)
        )

        result = CashFlowService.get_person_summary(person.pk, 2026, 3)
        assert result["fixed_expenses"]["total"] == Decimal("0.00")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_financial/test_cash_flow_service.py -k "Skipped" -v
```

- [ ] **Step 3: Modify CashFlowService to respect ExpenseMonthSkip**

In `core/services/cash_flow_service.py`:

1. In `get_monthly_expenses()`: at the start, load `skipped_expense_ids` for the month. Add `.exclude(pk__in=skipped_expense_ids)` or `.exclude(expense_id__in=skipped_expense_ids)` to all expense/installment queries.

2. In `get_person_summary()`: same approach — load skipped IDs and exclude from all queries.

```python
# At the start of get_monthly_expenses and get_person_summary:
skipped_expense_ids = set(
    ExpenseMonthSkip.objects.filter(
        reference_month=date(year, month, 1),
    ).values_list("expense_id", flat=True)
)

# Then add to each queryset:
.exclude(expense_id__in=skipped_expense_ids)  # for installments
.exclude(pk__in=skipped_expense_ids)           # for expenses
```

- [ ] **Step 4: Modify FinancialDashboardService similarly**

In `core/services/financial_dashboard_service.py`:

1. `get_overview()`: exclude skipped expenses from current month calculations
2. `get_dashboard_summary()`: exclude skipped expenses

Same pattern: load `skipped_expense_ids`, add `.exclude()` to queries.

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/unit/test_financial/ -v
```

Expected: All PASS

- [ ] **Step 6: Run type checking**

```bash
mypy core/services/cash_flow_service.py core/services/financial_dashboard_service.py
```

- [ ] **Step 7: Commit**

```bash
git add core/services/cash_flow_service.py core/services/financial_dashboard_service.py tests/unit/test_financial/
git commit -m "feat(services): respect ExpenseMonthSkip in cash flow and dashboard calculations"
```

---

## Task 7: Cache Invalidation Signals

**Files:**
- Modify: `core/signals.py`

- [ ] **Step 1: Add signal handlers for new models**

In `core/signals.py`, add signal handlers following the existing pattern:

```python
@receiver(post_save, sender=PersonPaymentSchedule)
def invalidate_schedule_cache_on_save(
    sender: type[PersonPaymentSchedule],
    instance: PersonPaymentSchedule,
    created: bool,
    **kwargs: Any,
) -> None:
    action = "created" if created else "updated"
    logger.info(f"PersonPaymentSchedule {instance.pk} {action}, invalidating caches")
    CacheManager.invalidate_pattern("daily-control:*")
    CacheManager.invalidate_pattern("cash-flow:*")
    CacheManager.invalidate_pattern("financial-dashboard:*")


@receiver(post_delete, sender=PersonPaymentSchedule)
def invalidate_schedule_cache_on_delete(
    sender: type[PersonPaymentSchedule],
    instance: PersonPaymentSchedule,
    **kwargs: Any,
) -> None:
    logger.info(f"PersonPaymentSchedule {instance.pk} deleted, invalidating caches")
    CacheManager.invalidate_pattern("daily-control:*")
    CacheManager.invalidate_pattern("cash-flow:*")
    CacheManager.invalidate_pattern("financial-dashboard:*")


@receiver(post_save, sender=ExpenseMonthSkip)
def invalidate_skip_cache_on_save(
    sender: type[ExpenseMonthSkip],
    instance: ExpenseMonthSkip,
    created: bool,
    **kwargs: Any,
) -> None:
    action = "created" if created else "updated"
    logger.info(f"ExpenseMonthSkip {instance.pk} {action}, invalidating caches")
    CacheManager.invalidate_pattern("daily-control:*")
    CacheManager.invalidate_pattern("cash-flow:*")
    CacheManager.invalidate_pattern("financial-dashboard:*")


@receiver(post_delete, sender=ExpenseMonthSkip)
def invalidate_skip_cache_on_delete(
    sender: type[ExpenseMonthSkip],
    instance: ExpenseMonthSkip,
    **kwargs: Any,
) -> None:
    logger.info(f"ExpenseMonthSkip {instance.pk} deleted, invalidating caches")
    CacheManager.invalidate_pattern("daily-control:*")
    CacheManager.invalidate_pattern("cash-flow:*")
    CacheManager.invalidate_pattern("financial-dashboard:*")
```

Add the model imports at the top of `core/signals.py`.

- [ ] **Step 2: Verify PersonPayment signal invalidates daily-control**

Check if the existing `PersonPayment` signal handler in `core/signals.py` invalidates `daily-control:*`. If not, add it.

- [ ] **Step 3: Run linting**

```bash
ruff check core/signals.py
```

- [ ] **Step 4: Commit**

```bash
git add core/signals.py
git commit -m "feat(signals): add cache invalidation for PersonPaymentSchedule and ExpenseMonthSkip"
```

---

## Task 8: Frontend Schemas + Mock Data

**Files:**
- Create: `frontend/lib/schemas/person-payment-schedule.schema.ts`
- Create: `frontend/lib/schemas/expense-month-skip.schema.ts`
- Create: `frontend/tests/mocks/data/person-payment-schedules.ts`
- Create: `frontend/tests/mocks/data/expense-month-skips.ts`
- Modify: `frontend/tests/mocks/data/index.ts`

- [ ] **Step 1: Create PersonPaymentSchedule schema**

Create `frontend/lib/schemas/person-payment-schedule.schema.ts`:

```typescript
import { z } from 'zod';

import { personSimpleSchema } from '@/lib/schemas/person.schema';

export const personPaymentScheduleSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  reference_month: z.string(),
  due_day: z.number().min(1).max(31),
  amount: z
    .string()
    .or(z.number())
    .transform((val) => Number(val)),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type PersonPaymentSchedule = z.infer<typeof personPaymentScheduleSchema>;

export const bulkConfigureRequestSchema = z.object({
  person_id: z.number(),
  reference_month: z.string(),
  entries: z.array(
    z.object({
      due_day: z.number().min(1).max(31),
      amount: z
        .string()
        .or(z.number())
        .transform((val) => Number(val)),
    })
  ),
});

export type BulkConfigureRequest = z.infer<typeof bulkConfigureRequestSchema>;

export const personMonthTotalSchema = z.object({
  total_due: z.string().or(z.number()).transform((val) => Number(val)),
  total_offsets: z.string().or(z.number()).transform((val) => Number(val)),
  net_total: z.string().or(z.number()).transform((val) => Number(val)),
  total_scheduled: z.string().or(z.number()).transform((val) => Number(val)),
  total_paid: z.string().or(z.number()).transform((val) => Number(val)),
  pending: z.string().or(z.number()).transform((val) => Number(val)),
});

export type PersonMonthTotal = z.infer<typeof personMonthTotalSchema>;
```

- [ ] **Step 2: Create ExpenseMonthSkip schema**

Create `frontend/lib/schemas/expense-month-skip.schema.ts`:

```typescript
import { z } from 'zod';

export const expenseMonthSkipSchema = z.object({
  id: z.number().optional(),
  expense_id: z.number().optional(),
  expense_description: z.string().optional(),
  reference_month: z.string(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type ExpenseMonthSkip = z.infer<typeof expenseMonthSkipSchema>;
```

- [ ] **Step 3: Create mock data files**

Create `frontend/tests/mocks/data/person-payment-schedules.ts`:

```typescript
import type { PersonPaymentSchedule } from '@/lib/schemas/person-payment-schedule.schema';

export const mockPersonPaymentSchedules: PersonPaymentSchedule[] = [
  {
    id: 1,
    person: { id: 1, name: 'Rodrigo' },
    person_id: 1,
    reference_month: '2026-03-01',
    due_day: 5,
    amount: 4000,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
  {
    id: 2,
    person: { id: 1, name: 'Rodrigo' },
    person_id: 1,
    reference_month: '2026-03-01',
    due_day: 27,
    amount: 5000,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
];

let nextId = 100;

export function createMockPersonPaymentSchedule(
  overrides?: Partial<PersonPaymentSchedule>
): PersonPaymentSchedule {
  return {
    id: nextId++,
    person: { id: 1, name: 'Rodrigo' },
    person_id: 1,
    reference_month: '2026-03-01',
    due_day: 10,
    amount: 3000,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
    ...overrides,
  };
}
```

Create `frontend/tests/mocks/data/expense-month-skips.ts`:

```typescript
import type { ExpenseMonthSkip } from '@/lib/schemas/expense-month-skip.schema';

export const mockExpenseMonthSkips: ExpenseMonthSkip[] = [
  {
    id: 1,
    expense_id: 1,
    expense_description: 'Aluguel escritório',
    reference_month: '2026-03-01',
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
];

let nextId = 100;

export function createMockExpenseMonthSkip(
  overrides?: Partial<ExpenseMonthSkip>
): ExpenseMonthSkip {
  return {
    id: nextId++,
    expense_id: 1,
    expense_description: 'Some expense',
    reference_month: '2026-03-01',
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
    ...overrides,
  };
}
```

- [ ] **Step 4: Update mock data index**

In `frontend/tests/mocks/data/index.ts`, add:

```typescript
export * from './person-payment-schedules';
export * from './expense-month-skips';
```

- [ ] **Step 5: Run type checking**

```bash
cd frontend && npm run type-check
```

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/schemas/person-payment-schedule.schema.ts frontend/lib/schemas/expense-month-skip.schema.ts frontend/tests/mocks/data/person-payment-schedules.ts frontend/tests/mocks/data/expense-month-skips.ts frontend/tests/mocks/data/index.ts
git commit -m "feat(frontend): add schemas and mock data for payment schedules and expense skips"
```

---

## Task 9: Frontend Hooks

**Files:**
- Create: `frontend/lib/api/hooks/use-person-payment-schedules.ts`
- Create: `frontend/lib/api/hooks/use-expense-month-skips.ts`
- Modify: `frontend/lib/api/hooks/use-daily-control.ts`

- [ ] **Step 1: Create PersonPaymentSchedule hooks**

Create `frontend/lib/api/hooks/use-person-payment-schedules.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, extractResults } from '@/lib/api/client';
import type {
  BulkConfigureRequest,
  PersonMonthTotal,
  PersonPaymentSchedule,
} from '@/lib/schemas/person-payment-schedule.schema';

interface ScheduleFilters {
  person_id?: number;
  reference_month?: string;
}

function cleanFilters(filters: ScheduleFilters): Record<string, string> {
  const cleaned: Record<string, string> = {};
  if (filters.person_id) cleaned.person_id = String(filters.person_id);
  if (filters.reference_month) cleaned.reference_month = filters.reference_month;
  return cleaned;
}

export function usePersonPaymentSchedules(filters: ScheduleFilters = {}) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: ['person-payment-schedules', params],
    queryFn: () =>
      api
        .get<PersonPaymentSchedule[]>('person-payment-schedules/', {
          params: { ...params, page_size: 10000 },
        })
        .then(extractResults),
    enabled: !!filters.person_id && !!filters.reference_month,
  });
}

export function usePersonMonthTotal(personId: number | undefined, referenceMonth: string | undefined) {
  return useQuery({
    queryKey: ['person-month-total', personId, referenceMonth],
    queryFn: () =>
      api
        .get<PersonMonthTotal>('person-payment-schedules/person_month_total/', {
          params: { person_id: personId, reference_month: referenceMonth },
        })
        .then((res) => res.data),
    enabled: !!personId && !!referenceMonth,
  });
}

export function useBulkConfigureSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkConfigureRequest) =>
      api.post('person-payment-schedules/bulk_configure/', data).then((res) => res.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['person-payment-schedules'] });
      void queryClient.invalidateQueries({ queryKey: ['person-month-total'] });
      void queryClient.invalidateQueries({ queryKey: ['daily-control'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
    },
  });
}

export function useDeletePersonPaymentSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`person-payment-schedules/${id}/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['person-payment-schedules'] });
      void queryClient.invalidateQueries({ queryKey: ['person-month-total'] });
      void queryClient.invalidateQueries({ queryKey: ['daily-control'] });
    },
  });
}
```

- [ ] **Step 2: Create ExpenseMonthSkip hooks**

Create `frontend/lib/api/hooks/use-expense-month-skips.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, extractResults } from '@/lib/api/client';
import type { ExpenseMonthSkip } from '@/lib/schemas/expense-month-skip.schema';

interface SkipFilters {
  reference_month?: string;
  expense_id?: number;
}

function cleanFilters(filters: SkipFilters): Record<string, string> {
  const cleaned: Record<string, string> = {};
  if (filters.reference_month) cleaned.reference_month = filters.reference_month;
  if (filters.expense_id) cleaned.expense_id = String(filters.expense_id);
  return cleaned;
}

export function useExpenseMonthSkips(filters: SkipFilters = {}) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: ['expense-month-skips', params],
    queryFn: () =>
      api
        .get<ExpenseMonthSkip[]>('expense-month-skips/', {
          params: { ...params, page_size: 10000 },
        })
        .then(extractResults),
  });
}

export function useCreateExpenseMonthSkip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { expense_id: number; reference_month: string }) =>
      api.post('expense-month-skips/', data).then((res) => res.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['expense-month-skips'] });
      void queryClient.invalidateQueries({ queryKey: ['daily-control'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['person-month-total'] });
    },
  });
}

export function useDeleteExpenseMonthSkip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`expense-month-skips/${id}/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['expense-month-skips'] });
      void queryClient.invalidateQueries({ queryKey: ['daily-control'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['person-month-total'] });
    },
  });
}
```

- [ ] **Step 3: Update daily control types and hook**

In `frontend/lib/api/hooks/use-daily-control.ts`:

Update `DailyExit` interface to include new fields:

```typescript
export interface DailyExit {
  type: string;
  id: number;
  description: string;
  amount: number;
  due: boolean;
  paid: boolean;
  person?: string;
  person_id?: number;
  card?: string;
  building?: string;
  payment_date?: string;
  installment_ids?: number[];
  reference_month?: string;
  total_paid_month?: number;
}
```

Update `MarkPaidRequest` to include person_schedule:

```typescript
export interface MarkPaidRequest {
  item_type: 'installment' | 'expense' | 'income' | 'credit_card' | 'person_schedule';
  item_id: number;
  payment_date: string;
  person_id?: number;
  amount?: number;
  year?: number;
  month?: number;
}
```

- [ ] **Step 4: Run type checking and linting**

```bash
cd frontend && npm run type-check && npm run lint
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api/hooks/use-person-payment-schedules.ts frontend/lib/api/hooks/use-expense-month-skips.ts frontend/lib/api/hooks/use-daily-control.ts
git commit -m "feat(frontend): add hooks for payment schedules, expense skips, and updated daily control types"
```

---

## Task 10: Payment Schedule Configuration UI

**Files:**
- Create: `frontend/app/(dashboard)/financial/expenses/_components/payment-schedule-section.tsx`
- Modify: `frontend/app/(dashboard)/financial/expenses/page.tsx`

- [ ] **Step 1: Create PaymentScheduleSection component**

Create `frontend/app/(dashboard)/financial/expenses/_components/payment-schedule-section.tsx`:

This component renders:
1. Person dropdown + Month navigator
2. Summary card (total due, offsets, net total, scheduled, paid)
3. Editable table of schedule entries (day | amount | remove)
4. "Add date" button
5. "Save configuration" button calling `useBulkConfigureSchedule`
6. Confirmation dialog if sum > net_total

```typescript
'use client';

import { useState } from 'react';
import { CalendarDays, Plus, Save, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/components/ui/use-toast';
import { formatCurrency } from '@/lib/utils';
import { usePersons } from '@/lib/api/hooks/use-persons';
import {
  usePersonPaymentSchedules,
  usePersonMonthTotal,
  useBulkConfigureSchedule,
} from '@/lib/api/hooks/use-person-payment-schedules';

interface ScheduleEntry {
  due_day: number;
  amount: number;
}

export function PaymentScheduleSection() {
  const { toast } = useToast();
  const [selectedPersonId, setSelectedPersonId] = useState<number | undefined>();
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [entries, setEntries] = useState<ScheduleEntry[]>([]);
  const [showConfirm, setShowConfirm] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const referenceMonth = `${year}-${String(month).padStart(2, '0')}-01`;

  const { data: persons } = usePersons();
  const { data: schedules } = usePersonPaymentSchedules({
    person_id: selectedPersonId,
    reference_month: referenceMonth,
  });
  const { data: monthTotal } = usePersonMonthTotal(selectedPersonId, referenceMonth);
  const bulkConfigure = useBulkConfigureSchedule();

  // Sync schedules from server when loaded
  // (Use useEffect to load server data into local state)

  const totalConfigured = entries.reduce((sum, e) => sum + e.amount, 0);
  const netTotal = monthTotal?.net_total ?? 0;

  function handleAddEntry() {
    setEntries([...entries, { due_day: 1, amount: 0 }]);
    setHasUnsavedChanges(true);
  }

  function handleRemoveEntry(index: number) {
    setEntries(entries.filter((_, i) => i !== index));
    setHasUnsavedChanges(true);
  }

  function handleUpdateEntry(index: number, field: keyof ScheduleEntry, value: number) {
    const updated = [...entries];
    updated[index] = { ...updated[index], [field]: value };
    setEntries(updated);
    setHasUnsavedChanges(true);
  }

  function handleSave() {
    if (totalConfigured > netTotal && netTotal > 0) {
      setShowConfirm(true);
      return;
    }
    doSave();
  }

  function doSave() {
    if (!selectedPersonId) return;
    bulkConfigure.mutate(
      {
        person_id: selectedPersonId,
        reference_month: referenceMonth,
        entries: entries.filter((e) => e.amount > 0),
      },
      {
        onSuccess: () => {
          toast({ title: 'Configuração salva com sucesso' });
          setHasUnsavedChanges(false);
        },
        onError: () => {
          toast({ title: 'Erro ao salvar configuração', variant: 'destructive' });
        },
      }
    );
  }

  function handlePrevMonth() {
    if (month === 1) {
      setMonth(12);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  }

  function handleNextMonth() {
    if (month === 12) {
      setMonth(1);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  }

  const monthNames = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
  ];

  // Filter persons that have expenses (non-owner, non-employee only — or all)
  const personsWithExpenses = persons ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5" />
          Agenda de Pagamentos
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Person + Month selectors */}
        <div className="flex flex-wrap items-center gap-4">
          <Select
            value={selectedPersonId?.toString() ?? ''}
            onValueChange={(val) => {
              setSelectedPersonId(Number(val));
              setHasUnsavedChanges(false);
            }}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Selecione a pessoa" />
            </SelectTrigger>
            <SelectContent>
              {personsWithExpenses.map((p) => (
                <SelectItem key={p.id} value={String(p.id)}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={handlePrevMonth}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-[140px] text-center font-medium">
              {monthNames[month - 1]} {year}
            </span>
            <Button variant="outline" size="icon" onClick={handleNextMonth}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Summary cards */}
        {selectedPersonId && monthTotal && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <SummaryItem label="Total Devido" value={monthTotal.total_due} />
            <SummaryItem label="Descontos" value={monthTotal.total_offsets} />
            <SummaryItem label="Valor Líquido" value={monthTotal.net_total} highlight />
            <SummaryItem label="Configurado" value={totalConfigured} />
            <SummaryItem label="Pago" value={monthTotal.total_paid} />
            <SummaryItem label="Pendente" value={monthTotal.pending} />
          </div>
        )}

        {/* Schedule entries table */}
        {selectedPersonId && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[120px]">Dia</TableHead>
                  <TableHead>Valor</TableHead>
                  <TableHead className="w-[60px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <Input
                        type="number"
                        min={1}
                        max={31}
                        value={entry.due_day}
                        onChange={(e) =>
                          handleUpdateEntry(index, 'due_day', Number(e.target.value))
                        }
                        className="w-[80px]"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={0}
                        step={0.01}
                        value={entry.amount}
                        onChange={(e) =>
                          handleUpdateEntry(index, 'amount', Number(e.target.value))
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveEntry(index)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleAddEntry}>
                <Plus className="mr-1 h-4 w-4" />
                Adicionar data
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={bulkConfigure.isPending || entries.length === 0}
              >
                <Save className="mr-1 h-4 w-4" />
                Salvar configuração
              </Button>
            </div>
          </>
        )}

        {/* Confirmation dialog */}
        <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Total excede o valor devido</AlertDialogTitle>
              <AlertDialogDescription>
                O total configurado ({formatCurrency(totalConfigured)}) excede o valor
                devido ({formatCurrency(netTotal)}). Deseja continuar?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => {
                  setShowConfirm(false);
                  doSave();
                }}
              >
                Continuar
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  );
}

function SummaryItem({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-2 text-center ${highlight ? 'border-primary bg-primary/5' : ''}`}
    >
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold">{formatCurrency(value)}</div>
    </div>
  );
}
```

- [ ] **Step 2: Add useEffect to sync server schedules to local state**

In the `PaymentScheduleSection` component, add a `useEffect` that populates `entries` from `schedules` when they load (and `hasUnsavedChanges` is false):

```typescript
import { useEffect } from 'react';

// Inside the component:
useEffect(() => {
  if (schedules && !hasUnsavedChanges) {
    setEntries(
      schedules.map((s) => ({ due_day: s.due_day, amount: s.amount }))
    );
  }
}, [schedules, hasUnsavedChanges]);
```

- [ ] **Step 3: Add PaymentScheduleSection to expenses page**

In `frontend/app/(dashboard)/financial/expenses/page.tsx`, import and render the section:

```typescript
import { PaymentScheduleSection } from './_components/payment-schedule-section';

// In the JSX, add after the expense list:
<PaymentScheduleSection />
```

- [ ] **Step 4: Run type checking and build**

```bash
cd frontend && npm run type-check && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(dashboard)/financial/expenses/_components/payment-schedule-section.tsx frontend/app/(dashboard)/financial/expenses/page.tsx
git commit -m "feat(frontend): add payment schedule configuration section to expenses page"
```

---

## Task 11: Person Pay Modal in Daily Control

**Files:**
- Create: `frontend/app/(dashboard)/financial/daily/_components/person-pay-modal.tsx`

- [ ] **Step 1: Create PersonPayModal component**

Create `frontend/app/(dashboard)/financial/daily/_components/person-pay-modal.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { formatCurrency } from '@/lib/utils';
import { useMarkItemPaid } from '@/lib/api/hooks/use-daily-control';
import { usePersonMonthTotal } from '@/lib/api/hooks/use-person-payment-schedules';
import { useToast } from '@/components/ui/use-toast';

interface PersonPayModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  personId: number;
  personName: string;
  referenceMonth: string;
  dueDay: number;
  scheduledAmount: number;
  paymentDate: string;
}

export function PersonPayModal({
  open,
  onOpenChange,
  personId,
  personName,
  referenceMonth,
  dueDay,
  scheduledAmount,
  paymentDate,
}: PersonPayModalProps) {
  const { toast } = useToast();
  const [amount, setAmount] = useState(0);
  const markPaid = useMarkItemPaid();
  const { data: monthTotal } = usePersonMonthTotal(
    open ? personId : undefined,
    open ? referenceMonth : undefined
  );

  // Calculate suggested amount
  const alreadyPaid = monthTotal?.total_paid ?? 0;
  const expectedUntilDate = scheduledAmount; // This is cumulative from the backend
  const suggestedAmount = Math.max(0, scheduledAmount - alreadyPaid);

  useEffect(() => {
    if (open) {
      setAmount(suggestedAmount);
    }
  }, [open, suggestedAmount]);

  function handleConfirm() {
    const [yearStr, monthStr] = referenceMonth.split('-');
    markPaid.mutate(
      {
        item_type: 'person_schedule',
        item_id: personId,
        payment_date: paymentDate,
        person_id: personId,
        amount,
        year: Number(yearStr),
        month: Number(monthStr),
      },
      {
        onSuccess: () => {
          toast({ title: `Pagamento de ${formatCurrency(amount)} registrado para ${personName}` });
          onOpenChange(false);
        },
        onError: () => {
          toast({ title: 'Erro ao registrar pagamento', variant: 'destructive' });
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pagar — {personName}</DialogTitle>
          <DialogDescription>
            Registrar pagamento para {personName} no dia {dueDay}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="rounded-lg border p-2 text-center">
              <div className="text-xs text-muted-foreground">Esperado até esta data</div>
              <div className="font-semibold">{formatCurrency(scheduledAmount)}</div>
            </div>
            <div className="rounded-lg border p-2 text-center">
              <div className="text-xs text-muted-foreground">Já pago no mês</div>
              <div className="font-semibold">{formatCurrency(alreadyPaid)}</div>
            </div>
            <div className="rounded-lg border border-primary bg-primary/5 p-2 text-center">
              <div className="text-xs text-muted-foreground">Sugerido</div>
              <div className="font-semibold">{formatCurrency(suggestedAmount)}</div>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="pay-amount">Valor do pagamento</Label>
            <Input
              id="pay-amount"
              type="number"
              min={0}
              step={0.01}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={markPaid.isPending || amount <= 0}
          >
            Confirmar pagamento
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Run type checking**

```bash
cd frontend && npm run type-check
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/(dashboard)/financial/daily/_components/person-pay-modal.tsx
git commit -m "feat(frontend): add person pay modal with suggested amount calculation"
```

---

## Task 12: Modify Daily Timeline for Aggregated Entries + Skip

**Files:**
- Modify: `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx`
- Modify: `frontend/app/(dashboard)/financial/daily/_components/day-detail-drawer.tsx`

- [ ] **Step 1: Add person schedule rendering to DailyTimeline**

In `daily-timeline.tsx`, modify the exit rendering logic:

1. Import `PersonPayModal` and `useCreateExpenseMonthSkip`
2. Add state for person pay modal (`selectedPersonExit`, `showPayModal`)
3. For exits with `type === "person_schedule"`:
   - Render with `User` icon instead of `ArrowUpCircle`
   - Show person name as description
   - Add progress badge showing total paid vs total for month
   - "Pay" button opens `PersonPayModal` instead of direct `markPaid`
4. For regular exits (non-person_schedule):
   - Add "Skip" button (SkipForward icon) that calls `useCreateExpenseMonthSkip`
   - Only show for recurring/fixed expenses (not installments already created)

Key additions:

```typescript
import { User, SkipForward } from 'lucide-react';
import { PersonPayModal } from './person-pay-modal';
import { useCreateExpenseMonthSkip } from '@/lib/api/hooks/use-expense-month-skips';

// In the component:
const [payModalExit, setPayModalExit] = useState<DailyExit | null>(null);
const [payModalDay, setPayModalDay] = useState<string>('');
const createSkip = useCreateExpenseMonthSkip();

// In exit rendering, check exit.type:
{exit.type === 'person_schedule' ? (
  <>
    <User className="h-4 w-4 text-blue-500" />
    <span>{exit.description}</span>
    <Badge variant="outline">
      {formatCurrency(exit.total_paid_month ?? 0)} pago no mês
    </Badge>
    {isAdmin && !exit.paid && (
      <Button
        size="sm"
        variant="outline"
        onClick={() => {
          setPayModalExit(exit);
          setPayModalDay(day.date);
        }}
      >
        Pagar
      </Button>
    )}
  </>
) : (
  // existing exit rendering
  <>
    {/* ... existing code ... */}
    {/* Add skip button for skippable expenses */}
    {isAdmin && exit.type === 'expense' && (
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          createSkip.mutate({
            expense_id: exit.id,
            reference_month: `${year}-${String(month).padStart(2, '0')}-01`,
          });
        }}
      >
        <SkipForward className="h-3 w-3" />
      </Button>
    )}
  </>
)}

// PersonPayModal at the bottom:
{payModalExit && (
  <PersonPayModal
    open={!!payModalExit}
    onOpenChange={(open) => !open && setPayModalExit(null)}
    personId={payModalExit.person_id!}
    personName={payModalExit.person!}
    referenceMonth={payModalExit.reference_month!}
    dueDay={/* extract day from payModalDay */}
    scheduledAmount={payModalExit.amount}
    paymentDate={payModalDay}
  />
)}
```

- [ ] **Step 2: Update DayDetailDrawer similarly**

In `day-detail-drawer.tsx`, apply the same changes:
- Person schedule exits render with User icon, progress info, and PersonPayModal
- Skip button on eligible expenses

- [ ] **Step 3: Run type checking and build**

```bash
cd frontend && npm run type-check && npm run build
```

- [ ] **Step 4: Manual testing checklist**

- [ ] Verify person with schedule shows aggregated entries on correct days
- [ ] Verify person without schedule shows individual entries (unchanged)
- [ ] Verify "Pagar" opens modal with correct suggested amount
- [ ] Verify paying updates status across related schedule entries
- [ ] Verify skip button removes expense from timeline
- [ ] Verify skipped expenses excluded from person totals

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx frontend/app/(dashboard)/financial/daily/_components/day-detail-drawer.tsx
git commit -m "feat(frontend): render aggregated person entries and skip buttons in daily control"
```

---

## Task 13: Add MSW Handlers for Tests

**Files:**
- Modify: `frontend/tests/mocks/handlers.ts`

- [ ] **Step 1: Add MSW handlers for new endpoints**

In `frontend/tests/mocks/handlers.ts`, add handlers:

```typescript
import {
  mockPersonPaymentSchedules,
  mockExpenseMonthSkips,
} from './data';

// Add mutable copies:
let personPaymentSchedules = [...mockPersonPaymentSchedules];
let expenseMonthSkips = [...mockExpenseMonthSkips];

// In resetMockData():
personPaymentSchedules = [...mockPersonPaymentSchedules];
expenseMonthSkips = [...mockExpenseMonthSkips];

// Add handlers:
const personPaymentScheduleHandlers = [
  http.get(`${API_BASE}/person-payment-schedules/`, async () => {
    await delay(50);
    return HttpResponse.json({ results: personPaymentSchedules });
  }),
  http.get(`${API_BASE}/person-payment-schedules/person_month_total/`, async () => {
    await delay(50);
    return HttpResponse.json({
      total_due: '10000.00',
      total_offsets: '200.00',
      net_total: '9800.00',
      total_scheduled: '9000.00',
      total_paid: '3000.00',
      pending: '6800.00',
    });
  }),
  http.post(`${API_BASE}/person-payment-schedules/bulk_configure/`, async () => {
    await delay(50);
    return HttpResponse.json({
      schedules: personPaymentSchedules,
      total_configured: '9000.00',
      total_due: '9800.00',
    });
  }),
];

const expenseMonthSkipHandlers = [
  http.get(`${API_BASE}/expense-month-skips/`, async () => {
    await delay(50);
    return HttpResponse.json({ results: expenseMonthSkips });
  }),
  http.post(`${API_BASE}/expense-month-skips/`, async ({ request }) => {
    await delay(50);
    const body = await request.json();
    const newSkip = { id: Date.now(), ...body };
    expenseMonthSkips.push(newSkip);
    return HttpResponse.json(newSkip, { status: 201 });
  }),
  http.delete(`${API_BASE}/expense-month-skips/:id`, async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),
];

// Export in the handlers array:
export const handlers = [
  ...existingHandlers,
  ...personPaymentScheduleHandlers,
  ...expenseMonthSkipHandlers,
];
```

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend && npm run test:unit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/mocks/handlers.ts
git commit -m "feat(frontend): add MSW handlers for payment schedules and expense skips"
```

---

## Task 14: Final Integration + Type Checking + Linting

**Files:** All modified files

- [ ] **Step 1: Run backend linting and type checking**

```bash
ruff check && ruff format --check
mypy core/
```

Fix any issues.

- [ ] **Step 2: Run backend tests**

```bash
python -m pytest tests/unit/test_financial/ -v
```

All must pass.

- [ ] **Step 3: Run frontend linting and type checking**

```bash
cd frontend && npm run lint && npm run type-check
```

Fix any issues.

- [ ] **Step 4: Run frontend build**

```bash
cd frontend && npm run build
```

Must succeed.

- [ ] **Step 5: Run frontend tests**

```bash
cd frontend && npm run test:unit
```

All must pass.

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve linting and type errors from payment scheduling feature"
```
