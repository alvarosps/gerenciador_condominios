"""
Service for advancing financial months.

Handles: validation, snapshot creation, pre-creation of next month records,
and rollback of month advancement.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.models import (
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    FinancialSettings,
    Lease,
    MonthSnapshot,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
    RentPayment,
)
from core.services.cash_flow_service import CashFlowService

_DECEMBER = 12


class MonthAdvanceService:
    """Orchestrates month advancement: validate → snapshot → prepare next month."""

    def __init__(self) -> None:
        self.cash_flow_service = CashFlowService()

    # ──────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────

    def get_status(self, year: int, month: int) -> dict[str, Any]:
        """Check current status of a month: finalized? validation warnings?"""
        reference_month = date(year, month, 1)
        snapshot = MonthSnapshot.objects.filter(reference_month=reference_month).first()

        validation = self._validate_month(year, month)

        return {
            "year": year,
            "month": month,
            "is_finalized": snapshot.is_finalized if snapshot else False,
            "snapshot_id": snapshot.pk if snapshot else None,
            "validation": validation,
        }

    def advance_month(
        self, year: int, month: int, *, force: bool = False, notes: str = ""
    ) -> dict[str, Any]:
        """
        Advance (close) a month: validate, create snapshot, prepare next month.

        Args:
            year: Year to close
            month: Month to close (1-12)
            force: If True, proceed despite validation warnings
            notes: Optional notes to attach to the snapshot

        Returns:
            Dict with snapshot data, warnings, and next month preview
        """
        reference_month = date(year, month, 1)

        # Check idempotency
        existing = MonthSnapshot.objects.filter(
            reference_month=reference_month, is_finalized=True
        ).first()
        if existing:
            msg = f"Mês {month:02d}/{year} já foi finalizado. Use rollback primeiro se precisar reprocessar."
            raise ValueError(msg)

        # Check chronological order
        self._validate_chronological_order(reference_month)

        # Validate
        validation = self._validate_month(year, month)
        warnings = self._extract_warnings(validation)

        if warnings and not force:
            msg = f"Validação falhou com {len(warnings)} aviso(s). Use force=True para prosseguir. Avisos: {'; '.join(warnings)}"
            raise ValueError(msg)

        # Execute in transaction
        with transaction.atomic():
            # Phase 1: Create snapshot
            snapshot = self._create_snapshot(year, month, warnings, notes)

            # Phase 2: Pre-create next month records
            next_month_info = self._prepare_next_month(year, month)

            # Phase 3: Finalize
            snapshot.is_finalized = True
            snapshot.finalized_at = timezone.now()
            snapshot.save()

        return {
            "success": True,
            "snapshot_id": snapshot.pk,
            "reference_month": str(reference_month),
            "warnings": warnings,
            "summary": {
                "total_income": float(snapshot.total_income),
                "total_expenses": float(snapshot.total_expenses),
                "net_balance": float(snapshot.net_balance),
                "cumulative_ending_balance": float(snapshot.cumulative_ending_balance),
            },
            "next_month_preview": next_month_info,
        }

    def rollback_month(self, year: int, month: int, *, confirm: bool = False) -> dict[str, Any]:
        """
        Rollback a finalized month. Deletes snapshot and auto-created records.

        Args:
            year: Year to rollback
            month: Month to rollback
            confirm: Must be True to proceed (destructive operation)
        """
        if not confirm:
            msg = "Rollback requer confirm=True (operação destrutiva)"
            raise ValueError(msg)

        reference_month = date(year, month, 1)

        # Verify this is the last finalized month
        latest = (
            MonthSnapshot.objects.filter(is_finalized=True).order_by("-reference_month").first()
        )
        if not latest or latest.reference_month != reference_month:
            last = latest.reference_month if latest else "nenhum"
            msg = f"Só é possível reverter o último mês finalizado. Último mês: {last}"
            raise ValueError(msg)

        with transaction.atomic():
            # Calculate next month for cleanup
            next_month = self._next_month_date(reference_month)

            # Delete auto-created EmployeePayments for next month
            # (only those not yet paid — don't delete if user already edited)
            emp_deleted, _ = EmployeePayment.objects.filter(
                reference_month=next_month, is_paid=False
            ).delete()

            # Delete auto-created PersonPaymentSchedules for next month
            schedules_deleted, _ = PersonPaymentSchedule.objects.filter(
                reference_month=next_month
            ).delete()

            # Delete the snapshot (MonthSnapshot has no SoftDeleteMixin, so .delete() is real)
            snapshot = MonthSnapshot.objects.get(reference_month=reference_month)
            snapshot_id = snapshot.pk
            snapshot.delete()

        return {
            "success": True,
            "rolled_back_month": str(reference_month),
            "details": {
                "snapshot_deleted": True,
                "snapshot_id": snapshot_id,
                "employee_payments_deleted": emp_deleted,
                "schedules_deleted": schedules_deleted,
            },
        }

    def get_next_month_preview(self, year: int, month: int) -> dict[str, Any]:
        """Preview what the next month will look like without advancing."""
        next_date = self._next_month_date(date(year, month, 1))
        return self._build_next_month_preview(next_date.year, next_date.month)

    # ──────────────────────────────────────────────
    # VALIDATION
    # ──────────────────────────────────────────────

    def _validate_month(self, year: int, month: int) -> dict[str, Any]:
        """Validate all obligations for a month."""
        month_start = date(year, month, 1)
        next_month = self._next_month_date(month_start)

        return {
            "unpaid_rent": self._check_unpaid_rent(month_start),
            "unpaid_installments": self._check_unpaid_installments(month_start, next_month),
            "unpaid_employees": self._check_unpaid_employees(month_start),
            "missing_utility_bills": self._check_missing_utility_bills(month_start, next_month),
            "unpaid_person_schedules": self._check_unpaid_person_schedules(month_start),
        }

    def _check_unpaid_rent(self, month_start: date) -> list[dict]:
        """Check for active leases without RentPayment for this month."""
        active_leases = (
            Lease.objects.filter(
                apartment__is_rented=True,
                apartment__owner__isnull=True,
            )
            .exclude(prepaid_until__gte=month_start)
            .exclude(is_salary_offset=True)
            .select_related("apartment", "apartment__building", "responsible_tenant")
        )

        unpaid = []
        for lease in active_leases:
            has_payment = RentPayment.objects.filter(
                lease=lease,
                reference_month=month_start,
            ).exists()
            if not has_payment:
                unpaid.append(
                    {
                        "lease_id": lease.pk,
                        "apartment": f"{lease.apartment.number}/{lease.apartment.building.street_number}",
                        "tenant": lease.responsible_tenant.name,
                        "rental_value": float(lease.rental_value),
                    }
                )
        return unpaid

    def _check_unpaid_installments(self, month_start: date, next_month: date) -> list[dict]:
        """Check for unpaid installments due this month."""
        unpaid = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            is_paid=False,
            expense__is_offset=False,
        ).select_related("expense", "expense__person", "expense__credit_card")

        return [
            {
                "installment_id": inst.pk,
                "description": inst.expense.description,
                "person": inst.expense.person.name if inst.expense.person else None,
                "amount": float(inst.amount),
                "due_date": str(inst.due_date),
                "installment": f"{inst.installment_number}/{inst.total_installments}",
            }
            for inst in unpaid
        ]

    def _check_unpaid_employees(self, month_start: date) -> list[dict]:
        """Check for employees without EmployeePayment for this month."""
        employees = Person.objects.filter(is_employee=True)

        unpaid = []
        for emp in employees:
            payment = EmployeePayment.objects.filter(
                person=emp,
                reference_month=month_start,
            ).first()
            if not payment:
                unpaid.append(
                    {
                        "person_id": emp.pk,
                        "name": emp.name,
                        "status": "not_created",
                    }
                )
            elif not payment.is_paid:
                unpaid.append(
                    {
                        "person_id": emp.pk,
                        "name": emp.name,
                        "status": "not_paid",
                        "amount": float(payment.total_paid),
                    }
                )
        return unpaid

    def _check_missing_utility_bills(self, month_start: date, next_month: date) -> list[dict]:
        """Check if water/electricity bills exist for this month."""
        missing = []
        for bill_type, label in [
            ("water_bill", "Conta de Água"),
            ("electricity_bill", "Conta de Luz"),
        ]:
            exists = Expense.objects.filter(
                expense_type=bill_type,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            ).exists()
            if not exists:
                missing.append({"type": bill_type, "label": label})
        return missing

    def _check_unpaid_person_schedules(self, month_start: date) -> list[dict]:
        """Check PersonPaymentSchedule entries without corresponding PersonPayment."""
        schedules = PersonPaymentSchedule.objects.filter(
            reference_month=month_start,
        ).select_related("person")

        unpaid = []
        for schedule in schedules:
            payments = PersonPayment.objects.filter(
                person=schedule.person,
                reference_month=month_start,
            )
            total_paid = sum(p.amount for p in payments)
            if total_paid < schedule.amount:
                unpaid.append(
                    {
                        "person_id": schedule.person.pk,
                        "person_name": schedule.person.name,
                        "expected": float(schedule.amount),
                        "paid": float(total_paid),
                        "remaining": float(schedule.amount - total_paid),
                    }
                )
        return unpaid

    def _extract_warnings(self, validation: dict) -> list[str]:
        """Convert validation results into human-readable warnings."""
        warnings = [
            f"Aluguel não recebido: {rent['apartment']} ({rent['tenant']}) - R${rent['rental_value']:.2f}"
            for rent in validation["unpaid_rent"]
        ]
        warnings.extend(
            f"Parcela não paga: {inst['description']} {inst['installment']} - R${inst['amount']:.2f}"
            for inst in validation["unpaid_installments"]
        )
        for emp in validation["unpaid_employees"]:
            status_text = "não criado" if emp["status"] == "not_created" else "não pago"
            warnings.append(f"Funcionário {status_text}: {emp['name']}")
        warnings.extend(
            f"{bill['label']} não registrada para o mês"
            for bill in validation["missing_utility_bills"]
        )
        warnings.extend(
            f"Pagamento programado pendente: {schedule['person_name']} - Falta R${schedule['remaining']:.2f}"
            for schedule in validation["unpaid_person_schedules"]
        )

        return warnings

    # ──────────────────────────────────────────────
    # SNAPSHOT CREATION
    # ──────────────────────────────────────────────

    def _create_snapshot(
        self, year: int, month: int, warnings: list[str], notes: str
    ) -> MonthSnapshot:
        """Create MonthSnapshot using CashFlowService data."""
        cash_flow = self.cash_flow_service.get_monthly_cash_flow(year, month)

        income = cash_flow["income"]
        expenses = cash_flow["expenses"]

        # Calculate person payments received
        month_start = date(year, month, 1)
        person_payments = PersonPayment.objects.filter(
            reference_month=month_start,
        )
        total_person_payments = sum(p.amount for p in person_payments)

        # Build detailed breakdown
        breakdown = {
            "rent_details": income.get("rent_details", []),
            "extra_income_details": income.get("extra_income_details", []),
            "card_installments": expenses.get("card_installments_details", []),
            "loan_installments": expenses.get("loan_installments_details", []),
            "utility_bills": expenses.get("utility_bills_details", []),
            "debt_installments": expenses.get("debt_installments_details", []),
            "property_tax": expenses.get("property_tax_details", []),
            "employee_salaries": expenses.get("employee_salary_details", []),
            "fixed_expenses": expenses.get("fixed_expenses_details", []),
            "one_time_expenses": expenses.get("one_time_expenses_details", []),
            "owner_repayments": expenses.get("owner_repayments_details", []),
            "person_stipends": expenses.get("person_stipends_details", []),
            "person_payments": [
                {
                    "person_id": p.person_id,
                    "person_name": p.person.name,
                    "amount": float(p.amount),
                    "payment_date": str(p.payment_date),
                }
                for p in person_payments.select_related("person")
            ],
            "validation_warnings": warnings,
        }

        # Serialize Decimal values in breakdown
        breakdown = self._serialize_breakdown(breakdown)

        # Calculate net balance
        net_balance = Decimal(str(income.get("total", 0))) - Decimal(str(expenses.get("total", 0)))

        # Calculate cumulative ending balance
        previous_snapshot = (
            MonthSnapshot.objects.filter(
                reference_month__lt=month_start,
                is_finalized=True,
            )
            .order_by("-reference_month")
            .first()
        )

        if previous_snapshot:
            cumulative_starting = previous_snapshot.cumulative_ending_balance
        else:
            settings = FinancialSettings.objects.first()
            cumulative_starting = settings.initial_balance if settings else Decimal("0.00")

        cumulative_ending = cumulative_starting + net_balance

        return MonthSnapshot.objects.create(
            reference_month=month_start,
            total_rent_income=income.get("rent_income", 0),
            total_extra_income=income.get("extra_income", 0),
            total_person_payments_received=total_person_payments,
            total_income=Decimal(str(income.get("total", 0))) + total_person_payments,
            total_card_installments=expenses.get("card_installments", 0),
            total_loan_installments=expenses.get("loan_installments", 0),
            total_utility_bills=expenses.get("utility_bills", 0),
            total_fixed_expenses=expenses.get("fixed_expenses", 0),
            total_one_time_expenses=expenses.get("one_time_expenses", 0),
            total_employee_salary=expenses.get("employee_salary", 0),
            total_owner_repayments=expenses.get("owner_repayments", 0),
            total_person_stipends=expenses.get("person_stipends", 0),
            total_debt_installments=expenses.get("debt_installments", 0),
            total_property_tax=expenses.get("property_tax", 0),
            total_expenses=expenses.get("total", 0),
            net_balance=net_balance,
            cumulative_ending_balance=cumulative_ending,
            detailed_breakdown=breakdown,
            notes=notes,
        )

    def _serialize_breakdown(self, data: Any) -> Any:
        """Recursively convert Decimal/date values to JSON-serializable types."""
        if isinstance(data, dict):
            return {k: self._serialize_breakdown(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._serialize_breakdown(item) for item in data]
        if isinstance(data, Decimal):
            return float(data)
        if isinstance(data, date):
            return str(data)
        return data

    # ──────────────────────────────────────────────
    # NEXT MONTH PREPARATION
    # ──────────────────────────────────────────────

    def _prepare_next_month(self, year: int, month: int) -> dict[str, Any]:
        """Pre-create records for the next month and return preview."""
        current_month = date(year, month, 1)
        next_month = self._next_month_date(current_month)

        created = {
            "employee_payments_created": self._carry_forward_employee_payments(
                current_month, next_month
            ),
            "payment_schedules_created": self._carry_forward_payment_schedules(
                current_month, next_month
            ),
        }

        preview = self._build_next_month_preview(next_month.year, next_month.month)
        preview["auto_created"] = created

        return preview

    def _carry_forward_employee_payments(self, current_month: date, next_month: date) -> int:
        """Create EmployeePayment entries for next month based on current month."""
        current_payments = EmployeePayment.objects.filter(
            reference_month=current_month,
        )

        created = 0
        for payment in current_payments:
            exists = EmployeePayment.objects.filter(
                person=payment.person,
                reference_month=next_month,
            ).exists()
            if not exists:
                EmployeePayment.objects.create(
                    person=payment.person,
                    reference_month=next_month,
                    base_salary=payment.base_salary,
                    variable_amount=Decimal(0),
                    rent_offset=payment.rent_offset,
                    cleaning_count=0,
                    is_paid=False,
                )
                created += 1
        return created

    def _carry_forward_payment_schedules(self, current_month: date, next_month: date) -> int:
        """Carry forward PersonPaymentSchedule entries to next month."""
        current_schedules = PersonPaymentSchedule.objects.filter(
            reference_month=current_month,
        )

        created = 0
        for schedule in current_schedules:
            exists = PersonPaymentSchedule.objects.filter(
                person=schedule.person,
                reference_month=next_month,
                due_day=schedule.due_day,
            ).exists()
            if not exists:
                PersonPaymentSchedule.objects.create(
                    person=schedule.person,
                    reference_month=next_month,
                    due_day=schedule.due_day,
                    amount=schedule.amount,
                )
                created += 1
        return created

    def _build_next_month_preview(self, year: int, month: int) -> dict[str, Any]:
        """Build a preview of what the next month looks like."""
        month_start = date(year, month, 1)
        next_month = self._next_month_date(month_start)

        # Upcoming installments
        upcoming_installments = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__is_offset=False,
            )
            .select_related("expense")
            .count()
        )

        # Expected rent
        expected_rent_count = (
            Lease.objects.filter(
                apartment__is_rented=True,
                apartment__owner__isnull=True,
            )
            .exclude(prepaid_until__gte=month_start)
            .exclude(is_salary_offset=True)
            .count()
        )

        reminders = [
            "Adicionar conta de água do mês",
            "Adicionar conta de luz do mês",
        ]

        return {
            "year": year,
            "month": month,
            "upcoming_installments_count": upcoming_installments,
            "expected_rent_count": expected_rent_count,
            "reminders": reminders,
        }

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _next_month_date(self, current: date) -> date:
        """Get first day of next month."""
        if current.month == _DECEMBER:
            return date(current.year + 1, 1, 1)
        return date(current.year, current.month + 1, 1)

    def _validate_chronological_order(self, reference_month: date) -> None:
        """Ensure no gaps: previous month must be finalized."""
        if reference_month.month == 1:
            prev_month = date(reference_month.year - 1, _DECEMBER, 1)
        else:
            prev_month = date(reference_month.year, reference_month.month - 1, 1)

        # Check if there are ANY finalized months
        any_finalized = MonthSnapshot.objects.filter(is_finalized=True).exists()
        if not any_finalized:
            return

        # If there are finalized months, the previous month must be finalized
        prev_finalized = MonthSnapshot.objects.filter(
            reference_month=prev_month, is_finalized=True
        ).exists()
        if not prev_finalized:
            msg = f"O mês anterior ({prev_month.strftime('%m/%Y')}) não foi finalizado. Não é possível pular meses."
            raise ValueError(msg)
