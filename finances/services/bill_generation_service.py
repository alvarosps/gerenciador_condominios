"""Recurring bill generation for the condominium (Phase 2 Session 37, extended Phase 3 Session 41).

Generates the month's recurring Bills from active BillingAccounts (idempotent,
race-safe) plus the "paid up to X" seed line so unfilled bills surface as overdue.

Session 41 extends ensure_month_bills with installments (standalone -> own Bill;
embedded -> a line on the recurring account's Bill, dedup) and payroll
(Bill(employee=…) with base + salary-offset lines). Deterministic order:
recurring/seed -> embedded -> standalone -> payroll, then mark fully-materialized
plans as PAID.
"""

import logging
from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from core.services.rent_schedule_service import RentScheduleService
from finances.models import (
    Bill,
    BillBehavior,
    BillingAccount,
    BillingAccountState,
    BillLifecycleState,
    BillLineItem,
    BillSkip,
    Employee,
    EmployeePaymentType,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
)

logger = logging.getLogger(__name__)


class BillGenerationService:
    """Stateless recurring-bill generation."""

    @staticmethod
    def _due_date_for(account: BillingAccount, year: int, month: int) -> date:
        """Pure date generator: account.default_due_day clamped to the month (31 -> 28/29/30)."""
        return date(
            year, month, RentScheduleService.clamp_due_day(account.default_due_day, year, month)
        )

    @staticmethod
    def _is_account_eligible(account: BillingAccount, month_start: date) -> bool:
        """Active, within tracking_start_month..end_date, and not skipped for the month."""
        if account.lifecycle_state != BillingAccountState.ACTIVE:
            return False
        if account.tracking_start_month is not None and account.tracking_start_month > month_start:
            return False
        if account.end_date is not None and account.end_date < month_start:
            return False
        return not BillSkip.objects.filter(
            billing_account=account, reference_month=month_start
        ).exists()

    @staticmethod
    def ensure_month_bills(year: int, month: int, user: User | None = None) -> list[Bill]:
        """Ensure one recurring Bill per eligible BillingAccount for (year, month).

        Idempotent and race-safe (get_or_create on the partial uniques + IntegrityError
        tolerance). Deterministic order: (1) recurring + seed, (2) embedded installments
        (a line on the recurring Bill from step 1), (3) standalone installments (own Bill),
        (4) payroll. Then mark fully-materialized plans as PAID. Returns the ensured bills.
        """
        month_start = date(year, month, 1)
        bills: list[Bill] = []
        # (1) recurring accounts + seed line (S37).
        for account in BillingAccount.objects.filter(lifecycle_state=BillingAccountState.ACTIVE):
            if not BillGenerationService._is_account_eligible(account, month_start):
                continue
            bills.append(BillGenerationService._ensure_account_bill(account, year, month, user))
        # (2) embedded installments -> line on the recurring account's Bill (needs step 1).
        BillGenerationService._generate_embedded_lines(year, month, user)
        # (3) standalone installments -> own Bill.
        bills.extend(BillGenerationService._generate_installment_bills(year, month, user))
        # (4) payroll -> Bill(employee=…) with base + salary-offset lines.
        bills.extend(BillGenerationService._generate_payroll_bills(year, month, user))
        # A plan whose every installment is now materialized is fully scheduled -> PAID.
        BillGenerationService._mark_completed_plans_paid()
        return bills

    @staticmethod
    def _ensure_account_bill(
        account: BillingAccount, year: int, month: int, user: User | None
    ) -> Bill:
        month_start = date(year, month, 1)
        defaults = {
            "condominium": account.condominium,
            "building": account.building,
            "category": account.category,
            "behavior": BillBehavior.RECURRING,
            "lifecycle_state": BillLifecycleState.ACTIVE,
            "due_date": BillGenerationService._due_date_for(account, year, month),
            "description": account.name,
            "external_identifier": account.external_identifier,
            "created_by": user,
            "updated_by": user,
        }
        with transaction.atomic():
            try:
                bill, created = Bill.all_objects.get_or_create(
                    billing_account=account,
                    competence_month=month_start,
                    is_deleted=False,
                    defaults=defaults,
                )
            except IntegrityError:
                # Lost the race on the partial unique — re-fetch the active bill.
                bill = Bill.objects.get(billing_account=account, competence_month=month_start)
                created = False
            # Seed only a freshly created bill (idempotent re-runs add no duplicate lines).
            if created and account.expected_amount > 0:
                BillLineItem.objects.create(
                    bill=bill,
                    description=account.name,
                    amount=account.expected_amount,
                    is_offset=False,
                    category=account.category,
                    created_by=user,
                    updated_by=user,
                )
        return bill

    @staticmethod
    def _active_installments_for_month(
        year: int, month: int, *, embedded: bool
    ) -> list[Installment]:
        """Active installments of active, non-deleted plans whose due_date falls in the month."""
        return list(
            Installment.objects.filter(
                due_date__year=year,
                due_date__month=month,
                plan__is_deleted=False,
                plan__lifecycle_state=InstallmentPlanState.ACTIVE,
                plan__embedded=embedded,
            ).select_related(
                "plan",
                "plan__condominium",
                "plan__building",
                "plan__category",
                "plan__linked_billing_account",
            )
        )

    @staticmethod
    def _generate_embedded_lines(year: int, month: int, user: User | None) -> None:
        """Embedded installment -> a line on the recurring account's Bill (dedup, never own Bill)."""
        for installment in BillGenerationService._active_installments_for_month(
            year, month, embedded=True
        ):
            plan = installment.plan
            account = plan.linked_billing_account
            if account is None:  # defensive — clean() enforces embedded ⇒ linked set.
                continue
            bill = BillGenerationService._ensure_account_bill(account, year, month, user)
            # Dedup on (bill, installment): one active embedded line per installment.
            if BillLineItem.objects.filter(bill=bill, installment=installment).exists():
                continue
            BillLineItem.objects.create(
                bill=bill,
                installment=installment,
                amount=installment.amount,  # schedule -> realized copy at materialization.
                description=f"Parcela {installment.number}/{plan.installment_count}",
                category=plan.category,
                is_offset=False,
                created_by=user,
                updated_by=user,
            )

    @staticmethod
    def _generate_installment_bills(year: int, month: int, user: User | None) -> list[Bill]:
        """Standalone installment -> its own Bill(installment=…, behavior=INSTALLMENT) + 1 line."""
        month_start = date(year, month, 1)
        bills: list[Bill] = []
        for installment in BillGenerationService._active_installments_for_month(
            year, month, embedded=False
        ):
            plan = installment.plan
            defaults = {
                "condominium": plan.condominium,
                "building": plan.building,
                "category": plan.category,
                "behavior": BillBehavior.INSTALLMENT,
                "lifecycle_state": BillLifecycleState.ACTIVE,
                "competence_month": month_start,
                "due_date": installment.due_date,
                "description": plan.description,
                "created_by": user,
                "updated_by": user,
            }
            with transaction.atomic():
                try:
                    bill, created = Bill.all_objects.get_or_create(
                        installment=installment, is_deleted=False, defaults=defaults
                    )
                except IntegrityError:
                    bill = Bill.objects.get(installment=installment)
                    created = False
                if created:
                    BillLineItem.objects.create(
                        bill=bill,
                        amount=installment.amount,  # schedule -> realized copy.
                        description=plan.description,
                        category=plan.category,
                        is_offset=False,
                        created_by=user,
                        updated_by=user,
                    )
            bills.append(bill)
        return bills

    @staticmethod
    def _payroll_due_date(employee: Employee, year: int, month: int) -> date:
        return date(
            year, month, RentScheduleService.clamp_due_day(employee.default_due_day, year, month)
        )

    @staticmethod
    def _generate_payroll_bills(year: int, month: int, user: User | None) -> list[Bill]:
        """Payroll -> Bill(employee=…, behavior=RECURRING) with base + salary-offset lines."""
        month_start = date(year, month, 1)
        bills: list[Bill] = []
        for employee in Employee.objects.filter(is_active=True).select_related("lease"):
            defaults = {
                "condominium": employee.condominium,
                "behavior": BillBehavior.RECURRING,
                "lifecycle_state": BillLifecycleState.ACTIVE,
                "competence_month": month_start,
                "due_date": BillGenerationService._payroll_due_date(employee, year, month),
                "description": f"Folha {employee.name}",
                "created_by": user,
                "updated_by": user,
            }
            with transaction.atomic():
                try:
                    bill, created = Bill.all_objects.get_or_create(
                        employee=employee,
                        competence_month=month_start,
                        is_deleted=False,
                        defaults=defaults,
                    )
                except IntegrityError:
                    bill = Bill.objects.get(employee=employee, competence_month=month_start)
                    created = False
                if created:
                    BillGenerationService._seed_payroll_lines(bill, employee, month_start, user)
            bills.append(bill)
        return bills

    @staticmethod
    def _seed_payroll_lines(
        bill: Bill, employee: Employee, month_start: date, user: User | None
    ) -> None:
        """Base salary line (fixed/mixed) + salary-offset line (= effective_rental_value, §4.6).

        The variable amount is entered manually later (S42) — never generated speculatively.
        The offset stops when the lease is soft-deleted (is_deleted), not on FK null (§5.2).
        """
        needs_base = employee.payment_type in (
            EmployeePaymentType.FIXED,
            EmployeePaymentType.MIXED,
        )
        if needs_base and employee.base_salary is not None and employee.base_salary > 0:
            BillLineItem.objects.create(
                bill=bill,
                amount=employee.base_salary,
                description="Salário base",
                is_offset=False,
                created_by=user,
                updated_by=user,
            )
        lease = employee.lease
        if lease is not None and lease.is_salary_offset and not lease.is_deleted:
            offset = RentScheduleService.effective_rental_value(lease, month_start)
            if offset > 0:
                BillLineItem.objects.create(
                    bill=bill,
                    amount=offset,
                    description="Abatimento aluguel",
                    is_offset=True,
                    created_by=user,
                    updated_by=user,
                )

    @staticmethod
    def _mark_completed_plans_paid() -> None:
        """Mark an ACTIVE plan PAID once every installment is materialized (bill/line exists)."""
        for plan in InstallmentPlan.objects.filter(lifecycle_state=InstallmentPlanState.ACTIVE):
            installments = list(Installment.objects.filter(plan=plan))
            if not installments:
                continue
            if plan.embedded:
                materialized = all(
                    BillLineItem.objects.filter(installment=inst).exists() for inst in installments
                )
            else:
                materialized = all(
                    Bill.objects.filter(installment=inst).exists() for inst in installments
                )
            if materialized:
                plan.lifecycle_state = InstallmentPlanState.PAID
                plan.save(update_fields=["lifecycle_state", "updated_at"])
