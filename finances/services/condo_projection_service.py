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
cent. "Today / current month" comes only from core.services.timezone (settings is UTC).

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
from core.services.timezone import current_month_sp, today_sp
from finances.models import (
    Bill,
    BillingAccount,
    BillLifecycleState,
    BillSkip,
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
        # Preload every BillSkip across the projected horizon once, so each future month's
        # eligibility checks read an in-memory set instead of a BillSkip.exists() per account
        # per month (N*months queries -> 1 — P5.1).
        last_month = current
        for _ in range(max(months - 1, 0)):
            last_month = _next_month(last_month)
        skip_index: set[tuple[int, date]] = {
            (ba_id, ref_month)
            for ba_id, ref_month in BillSkip.objects.filter(
                reference_month__gte=current, reference_month__lte=last_month
            ).values_list("billing_account_id", "reference_month")
        }
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
                    cursor.year, cursor.month, building_id, skip_index=skip_index
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
    def _projected_expenses(
        year: int,
        month: int,
        building_id: int | None = None,
        *,
        skip_index: set[tuple[int, date]] | None = None,
    ) -> Decimal:
        """Projected expenses (raw Decimal) of a future month (design §3.2/§7/§8 — embedded dedup).

        For each eligible recurring account (the SAME predicate as BillGenerationService — active,
        within tracking_start_month..end_date, not skipped): the REAL materialized Bill's
        amount_total when one already exists for (account, month) — it already carries any
        embedded parcela line, so nothing is added on top — else the projected expected_amount +
        the projected embedded parcela (Installment.amount) added separately (B10d — a future
        month can already have a real Bill, e.g. imported ahead of time or edited after
        generation; using expected_amount then would silently diverge from what will actually be
        billed). Standalone parcelas mirror the same real-Bill-wins rule. Plus projected payroll
        (condo level — only in the condo-wide view). ``building_id`` scopes to a building; the
        condo-level (building=null) items enter only when ``building_id`` is None.

        ``skip_index`` (preloaded by :meth:`project` over the whole horizon) lets both eligibility
        loops check skips in memory instead of one BillSkip.exists() per (account, month) — P5.1.
        """
        reference_month = date(year, month, 1)
        total = ZERO

        # Same recurring predicate as generation (ACTIVE + exclude IPTU — design §10.3), so the
        # projection never diverges from ensure_month_bills; is_account_eligible adds the per-month
        # tracking/end/skip checks.
        accounts = BillingAccount.objects.recurring_for_generation()
        if building_id is not None:
            accounts = accounts.filter(building_id=building_id)
        real_totals_by_account = CondoProjectionService._real_bill_totals(
            year, month, "billing_account_id", building_id=building_id
        )
        for account in accounts:
            if not BillGenerationService.is_account_eligible(
                account, reference_month, skip_index=skip_index
            ):
                continue
            real_total = real_totals_by_account.get(account.pk)
            # The real Bill already carries any embedded parcela line — use it whole, on its own
            # (the embedded loop below skips any installment whose host Bill already materialized).
            total += real_total if real_total is not None else account.expected_amount

        # Standalone parcelas always count when active+due; embedded parcelas count ONLY when their
        # host recurring account is eligible that month (they ride on its bill — design §7/§8/§18),
        # mirroring BillGenerationService._generate_embedded_lines so projection never diverges from
        # generation. Real-Bill-wins (B10d): an installment whose Bill/line is already materialized
        # contributes via the real total above (standalone: its own Bill; embedded: the host
        # account's Bill) instead of the projected schedule amount.
        standalone = Installment.objects.filter(
            due_date__year=year,
            due_date__month=month,
            plan__is_deleted=False,
            plan__lifecycle_state=InstallmentPlanState.ACTIVE,
            plan__embedded=False,
        )
        if building_id is not None:
            standalone = standalone.filter(plan__building_id=building_id)
        materialized_standalone_ids = set(
            Bill.objects.filter(installment__in=standalone).values_list("installment_id", flat=True)
        )
        real_totals_by_installment = CondoProjectionService._real_bill_totals(
            year, month, "installment_id", building_id=building_id
        )
        for installment in standalone:
            if installment.pk in materialized_standalone_ids:
                total += real_totals_by_installment.get(installment.pk, ZERO)
            else:
                total += installment.amount

        embedded = Installment.objects.filter(
            due_date__year=year,
            due_date__month=month,
            plan__is_deleted=False,
            plan__lifecycle_state=InstallmentPlanState.ACTIVE,
            plan__embedded=True,
        ).select_related("plan__billing_account")
        if building_id is not None:
            embedded = embedded.filter(plan__building_id=building_id)
        for installment in embedded:
            host_account = installment.plan.billing_account
            if host_account is None or not BillGenerationService.is_account_eligible(
                host_account, reference_month, skip_index=skip_index
            ):
                continue
            # Already counted via the host account's real Bill total above — skip to avoid
            # double-counting (the real Bill's amount_total already includes this line).
            if host_account.pk in real_totals_by_account:
                continue
            total += installment.amount

        if building_id is None:
            total += CondoProjectionService._projected_payroll(reference_month)
        return total

    @staticmethod
    def _real_bill_totals(
        year: int, month: int, source_fk: str, *, building_id: int | None
    ) -> dict[int, Decimal]:
        """{source_fk value: amount_total} of every real, active Bill in (year, month) — B10d.

        ``source_fk`` is 'billing_account_id' or 'installment_id' (the Bill FK that ties it back
        to its projected source). Only ACTIVE bills count (a canceled/suspended/deferred one is
        excluded from every other sum too — design §4.4), read via with_amounts (never summed in
        Python).
        """
        month_start = date(year, month, 1)
        lookup: dict[str, object] = {f"{source_fk}__isnull": False}
        queryset = Bill.objects.with_amounts(today_sp()).filter(
            competence_month=month_start, lifecycle_state=BillLifecycleState.ACTIVE, **lookup
        )
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        return {
            row[source_fk]: row["amount_total"]
            for row in queryset.values(source_fk, "amount_total")
        }

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
