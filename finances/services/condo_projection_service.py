"""Condominium projection service (Phase 5, Session 47, design §3.2/§4.5/§4.7/§8).

CondoProjectionService.project(months) walks N months forward from the current São Paulo
month and folds the cash balance:

- a CLOSED month (CondoMonthClose.status='closed') reads its frozen net/cash and RE-ANCHORS the
  running cash — the frozen figures win over any later edit (design §3.2);
- the CURRENT (open, real) month delegates its net to CondoBalanceService.result_of_month — the
  projection never re-derives net/cash (DRY, design §8/§14);
- every FUTURE month is COMPUTED: projected collectibility-filtered rent + IncomeEntry (income)
  minus eligible recurring accounts' expected_amount + all active installments due + payroll.

The baseline of the running cash is CondoBalanceService.cash_balance(current month), anchored on
the last closed month. Internal sums stay raw Decimals; quantize_money is applied once at the
output boundary so the projection, the dashboard and a frozen CondoMonthClose never differ by a
cent. "Today / current month" comes only from finances.services.timezone (settings is UTC).

Embedded-installment dedup (design §7/§8): a recurring account's expected_amount is the CONSUMO;
the embedded parcela is its Installment, counted on top — exactly as ensure_month_bills
materializes the bill (600 consumo + 400 parcela). So expected_amount is counted once and every
active installment due (embedded OR standalone) once; nothing is doubled.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Sum

from core.services.rent_schedule_service import RentScheduleService
from finances.models import (
    BillingAccount,
    CondoMonthClose,
    CondoMonthCloseStatus,
    Employee,
    EmployeePaymentType,
    IncomeEntry,
    Installment,
    InstallmentPlanState,
)
from finances.money import money_str, quantize_money
from finances.services.bill_generation_service import BillGenerationService
from finances.services.condo_balance_service import CondoBalanceService, _next_month
from finances.services.timezone import current_month_sp

ZERO = Decimal(0)

_PAYROLL_BASE_TYPES = (EmployeePaymentType.FIXED, EmployeePaymentType.MIXED)


class CondoProjectionService:
    """Stateless condominium cash-flow projection (materialize real / compute future / anchor fold)."""

    @staticmethod
    def project(months: int = 12, building_id: int | None = None) -> list[dict[str, Any]]:
        """Project the condominium cash flow for ``months`` months from the current SP month.

        Returns one dict per chronological month: ``year``, ``month``, ``income_total``,
        ``expenses_total``, ``net``, ``cumulative_cash`` (Decimals as quantized strings),
        ``is_actual`` (the month is real/locked — closed or the current open month) and
        ``is_closed``. The running cash starts at the anchored baseline and re-anchors on each
        closed month; net/cash are never re-derived for closed or current months (DRY).
        """
        current = current_month_sp()
        running = CondoBalanceService.cash_balance(current, building_id)
        rows: list[dict[str, Any]] = []
        cursor = current
        for _ in range(months):
            close = CondoMonthClose.objects.filter(
                reference_month=cursor, status=CondoMonthCloseStatus.CLOSED
            ).first()
            is_closed = close is not None
            is_actual = is_closed or cursor <= current

            if close is not None:
                # Frozen month wins over the computed figures and re-anchors the running cash.
                # The pontas come from the frozen breakdown so income_total - expenses_total == net
                # even after a later edit to the month's bills (congelado vence — design §3.2).
                revenue, expense = CondoProjectionService._frozen_pontas(close)
                net = close.net_result
                running = close.cash_balance_end
            elif cursor == current:
                # Open real month — delegate net to CondoBalanceService (no re-derivation).
                revenue, expense = CondoBalanceService.competence_pontas(
                    cursor.year, cursor.month, building_id
                )
                net = quantize_money(revenue - expense)  # == result_of_month (same components)
                running = quantize_money(running + net)
            else:
                # Future month — computed projection.
                revenue = CondoProjectionService._projected_income(
                    cursor.year, cursor.month, building_id
                )
                expense = CondoProjectionService._projected_expenses(
                    cursor.year, cursor.month, building_id
                )
                net = quantize_money(revenue - expense)
                running = quantize_money(running + net)

            rows.append(
                {
                    "year": cursor.year,
                    "month": cursor.month,
                    "income_total": money_str(revenue),
                    "expenses_total": money_str(expense),
                    "net": money_str(net),
                    "cumulative_cash": money_str(running),
                    "is_actual": is_actual,
                    "is_closed": is_closed,
                }
            )
            cursor = _next_month(cursor)
        return rows

    @staticmethod
    def _frozen_pontas(close: CondoMonthClose) -> tuple[Decimal, Decimal]:
        """Frozen (revenue, expense) pontas of a closed month, from the persisted breakdown.

        CondoMonthCloseService.close freezes income_total/expenses_total into the breakdown, so the
        displayed bars never drift from the frozen net (revenue - expense == net_result). A legacy
        close whose breakdown predates those keys falls back to a live, condo-wide recompute (which
        matches the condo-wide frozen net the projection also reads for a closed month).
        """
        income = close.breakdown.get("income_total")
        expense = close.breakdown.get("expenses_total")
        if income is not None and expense is not None:
            return Decimal(str(income)), Decimal(str(expense))
        return CondoBalanceService.competence_pontas(
            close.reference_month.year, close.reference_month.month
        )

    @staticmethod
    def _projected_income(year: int, month: int, building_id: int | None = None) -> Decimal:
        """Projected income (raw Decimal) of a future month (design §4.5, prepaid PER MONTH).

        Σ effective_rental_value of RentScheduleService.collectible_leases(M) — prepaid is
        evaluated month by month and a pre-tracking month yields none, so rent is structurally 0
        there — plus Σ IncomeEntry.amount by income_date in the month. Owner-repass and
        salary-offset leases are already excluded by collectible_leases; rent is never the raw
        rental_value and never received_total (SSOT only).
        """
        reference_month = date(year, month, 1)
        rent = sum(
            (
                RentScheduleService.effective_rental_value(lease, reference_month)
                for lease in RentScheduleService.collectible_leases(reference_month, building_id)
            ),
            ZERO,
        )
        income_entries = IncomeEntry.objects.filter(
            income_date__year=year, income_date__month=month
        )
        if building_id is not None:
            income_entries = income_entries.filter(building_id=building_id)
        income = income_entries.aggregate(total=Sum("amount"))["total"] or ZERO
        return rent + income

    @staticmethod
    def _projected_expenses(year: int, month: int, building_id: int | None = None) -> Decimal:
        """Projected expenses (raw Decimal) of a future month (design §3.2/§7/§8 — embedded dedup).

        Σ expected_amount of eligible recurring accounts (the SAME eligibility predicate as
        BillGenerationService — active, within tracking_start_month..end_date, not skipped) +
        Σ Installment.amount of every active plan's installment due in the month (embedded AND
        standalone — the embedded parcela rides on top of the account's consumo, never doubled) +
        projected payroll (condo level — only in the condo-wide view). ``building_id`` scopes to a
        building; the condo-level (building=null) items enter only when ``building_id`` is None.
        """
        reference_month = date(year, month, 1)
        total = ZERO

        accounts = BillingAccount.objects.all()
        if building_id is not None:
            accounts = accounts.filter(building_id=building_id)
        for account in accounts:
            if BillGenerationService.is_account_eligible(account, reference_month):
                total += account.expected_amount

        installments = Installment.objects.filter(
            due_date__year=year,
            due_date__month=month,
            plan__is_deleted=False,
            plan__lifecycle_state=InstallmentPlanState.ACTIVE,
        )
        if building_id is not None:
            installments = installments.filter(plan__building_id=building_id)
        total += installments.aggregate(total=Sum("amount"))["total"] or ZERO

        if building_id is None:
            total += CondoProjectionService._projected_payroll(reference_month)
        return total

    @staticmethod
    def _projected_payroll(reference_month: date) -> Decimal:
        """Projected payroll (raw Decimal): Σ base salary − salary-offset abatimento (design §4.6).

        Mirrors BillGenerationService._seed_payroll_lines: a fixed/mixed employee contributes its
        base salary; a salary-offset lease (active, not soft-deleted) subtracts its
        effective_rental_value (so the offset rent is neither income nor a separate expense). The
        variable amount is entered manually later (never projected speculatively).
        """
        total = ZERO
        for employee in Employee.objects.filter(is_active=True).select_related("lease"):
            if (
                employee.payment_type in _PAYROLL_BASE_TYPES
                and employee.base_salary is not None
                and employee.base_salary > 0
            ):
                total += employee.base_salary
            lease = employee.lease
            if lease is not None and lease.is_salary_offset and not lease.is_deleted:
                total -= RentScheduleService.effective_rental_value(lease, reference_month)
        return total
