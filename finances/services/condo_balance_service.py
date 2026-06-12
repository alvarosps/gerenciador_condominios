"""Condominium balance service (Phase 4, Session 45, design §4.2/§4.3/§4.4/§4.5/§8).

The money core of the condominium: competence result, cash change, condo-scoped cash
balance anchored on the last CondoMonthClose, reserve balance (no double counting),
total balance, overdue bills, and the wedge identity that reconciles the two KPIs.

Rules (design §4):
- Rent revenue is ALWAYS collectibility-filtered (received_collectible_total / collectible_leases
  from RentScheduleService) — never received_total (which would count owner-repass / salary-offset).
- Competence and overdue read Bill.objects.with_amounts(today) annotations — never summed in Python.
- Cash is condo-scoped: baseline = last closed CondoMonthClose.cash_balance_end, fallback
  FinancialSettings.initial_balance; only the open tail is re-walked (mirrors
  DailyControlService._get_starting_balance but condo-scoped, not the commingled MonthSnapshot).
- Reserve is the deposit/withdrawal ledger; transfers are zero-sum on the total balance.
- Internal sums are raw Decimals; the figure is quantized once at the output boundary
  (quantize_money), so the dashboard and the frozen CondoMonthClose never differ by a cent.
- "today / current month" only via core.services.timezone (settings is UTC).
"""

from datetime import date
from decimal import Decimal
from typing import Any, NamedTuple

from django.db.models import QuerySet, Sum

from core.models import FinancialSettings, RentPayment
from core.services.rent_schedule_service import RentScheduleService
from core.services.timezone import current_month_sp, today_sp
from finances.models import (
    Bill,
    BillLifecycleState,
    CondoMonthClose,
    CondoMonthCloseStatus,
    FundedFrom,
    IncomeEntry,
    PaymentAllocation,
    ReserveMovement,
    ReserveMovementKind,
)
from finances.money import quantize_money

ZERO = Decimal(0)
ZERO_MONEY = Decimal("0.00")


def _next_month(value: date) -> date:
    """First day of the month after ``value``'s month."""
    return date(value.year + value.month // 12, value.month % 12 + 1, 1)


class _Components(NamedTuple):
    """Raw (un-quantized) monthly figures feeding result/cash_change/wedge from one source."""

    received_collectible: Decimal  # rent received from collectible leases (cash + accrual base)
    expected_unpaid: Decimal  # effective rent of collectible leases NOT paid (accrual only)
    income_competence: Decimal  # IncomeEntry by income_date in the month (accrual)
    income_cash: Decimal  # IncomeEntry received (is_received) by received_date in the month (cash)
    expense_competence: Decimal  # Σ Bill.amount_total of active bills with competence in the month
    caixa_outflow: Decimal  # Σ caixa-funded PaymentAllocation by payment_date in the month
    reserve_to_cash: Decimal  # Σ withdrawal(bill=null) = reserve -> cash transfer (cash in)
    deposit_out: Decimal  # Σ deposit = cash -> reserve transfer (cash out)


class CondoBalanceService:
    """Stateless condominium balance/result/cash/reserve service."""

    @staticmethod
    def result_of_month(
        year: int,
        month: int,
        building_id: int | None = None,
        *,
        components: "_Components | None" = None,
    ) -> Decimal:
        """Competence result = competence revenue - competence expense (design §4.2/§4.5).

        Revenue = received_collectible_total + Σ effective_rental_value of collectible leases
        NOT paid in the month + Σ IncomeEntry by income_date (accrual — received or not).
        Expense = Σ Bill.amount_total of bills with competence_month == M and lifecycle_state
        == 'active' (suspended/deferred/canceled excluded). Reserve transfers do NOT enter
        (cash movement, not competence — design §4.7).

        ``components`` lets a caller (overview/_wedge_residual) pass the already-computed
        :class:`_Components` for (year, month, building_id) so the figures are not re-queried
        within one computation — explicit and request-scoped, never a process-global cache (P5.1).
        """
        comp = components or CondoBalanceService._components(year, month, building_id)
        revenue = comp.received_collectible + comp.expected_unpaid + comp.income_competence
        return quantize_money(revenue - comp.expense_competence)

    @staticmethod
    def competence_pontas(
        year: int,
        month: int,
        building_id: int | None = None,
        *,
        components: "_Components | None" = None,
    ) -> tuple[Decimal, Decimal]:
        """(revenue, expense) competence pontas of the month (raw Decimals), from one source.

        Surfaces the same component split that feeds result_of_month, so a consumer can show the
        income/expense halves without re-deriving them: ``revenue - expense`` equals
        result_of_month by construction. Used by CondoProjectionService for the current/closed
        month display pontas (DRY — design §8). ``components`` shares an already-computed split.
        """
        comp = components or CondoBalanceService._components(year, month, building_id)
        revenue = comp.received_collectible + comp.expected_unpaid + comp.income_competence
        return revenue, comp.expense_competence

    @staticmethod
    def cash_change_of_month(
        year: int,
        month: int,
        building_id: int | None = None,
        *,
        components: "_Components | None" = None,
    ) -> Decimal:
        """Cash change (by payment date) = cash in - cash out (design §4.2/§4.3).

        In = received_collectible_total + IncomeEntry received in the month + reserve->cash
        withdrawals (bill=null). Out = caixa-funded PaymentAllocation in the month + cash->reserve
        deposits. A funded_from='reserve' payment is NOT a cash outflow (it debits only the
        reserve — design §4.3). ``components`` shares an already-computed split (P5.1).
        """
        comp = components or CondoBalanceService._components(year, month, building_id)
        cash_in = comp.received_collectible + comp.income_cash + comp.reserve_to_cash
        cash_out = comp.caixa_outflow + comp.deposit_out
        return quantize_money(cash_in - cash_out)

    @staticmethod
    def cash_balance(as_of_month: date | None = None, building_id: int | None = None) -> Decimal:
        """Condo-scoped cash at the first instant of ``as_of_month`` (= end of the prior month).

        baseline = cash_balance_end of the last 'closed' CondoMonthClose before as_of_month, else
        FinancialSettings.initial_balance (if initial_balance_date <= as_of_month), else 0.00.
        Only the open tail [month after the last closed .. as_of_month) is re-walked, summing
        cash_change_of_month (mirrors DailyControlService._get_starting_balance but condo-scoped).
        as_of_month None = current SP month. Cash MAY go negative (informational, not blocked).
        """
        if as_of_month is None:
            as_of_month = current_month_sp()
        as_of_month = as_of_month.replace(day=1)
        baseline, walk_from = CondoBalanceService._cash_baseline(as_of_month)
        total = baseline
        cursor = walk_from
        while cursor < as_of_month:
            total += CondoBalanceService.cash_change_of_month(
                cursor.year, cursor.month, building_id
            )
            cursor = _next_month(cursor)
        return quantize_money(total)

    @staticmethod
    def reserve_balance(condominium_id: int | None = None, as_of: date | None = None) -> Decimal:
        """Reserve = Σ deposits - Σ withdrawals (never negative; the guard lives in withdraw/pay).

        Movements of a soft-deleted Reserve are excluded (a forward-FK join does not apply the
        parent's default manager, so this must be explicit — soft-delete rule). ``as_of`` (the 1st
        of M+1, exclusive) bounds the ledger to movements through the end of month M, so a frozen
        CondoMonthClose freezes the reserve at the month end, not the all-time balance (P2.3 step 7);
        without ``as_of`` it is the live all-time balance (the dashboard / total_balance).
        """
        movements = ReserveMovement.objects.filter(reserve__is_deleted=False)
        if condominium_id is not None:
            movements = movements.filter(reserve__condominium_id=condominium_id)
        if as_of is not None:
            movements = movements.filter(movement_date__lt=as_of)
        deposits = (
            movements.filter(kind=ReserveMovementKind.DEPOSIT).aggregate(total=Sum("amount"))[
                "total"
            ]
            or ZERO
        )
        withdrawals = (
            movements.filter(kind=ReserveMovementKind.WITHDRAWAL).aggregate(total=Sum("amount"))[
                "total"
            ]
            or ZERO
        )
        return quantize_money(deposits - withdrawals)

    @staticmethod
    def total_balance(as_of_month: date | None = None) -> Decimal:
        """Total balance = cash balance + reserve balance (design §4.2)."""
        cash = CondoBalanceService.cash_balance(as_of_month)
        reserve = CondoBalanceService.reserve_balance()
        return quantize_money(cash + reserve)

    @staticmethod
    def overdue_bills_total(building_id: int | None = None) -> Decimal:
        """'Atrasados' (bills) = Σ amount_remaining of overdue active bills (design §4.4).

        is_overdue = due_date < today ∧ amount_remaining > 0 ∧ lifecycle_state == 'active'
        (with_amounts annotation). NOT amount_total; deferred/suspended/canceled excluded. Rent
        overdue is a SEPARATE figure (get_month_stats.overdue_total_fee) — never summed here.
        """
        overdue = CondoBalanceService._overdue_bills(building_id)
        total = overdue.aggregate(total=Sum("amount_remaining"))["total"] or ZERO
        return quantize_money(total)

    @staticmethod
    def overdue_bills_count(building_id: int | None = None) -> int:
        """Count of overdue active bills (companion to overdue_bills_total)."""
        return CondoBalanceService._overdue_bills(building_id).count()

    @staticmethod
    def overview(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Month KPIs (money as quantized string at the boundary), consuming the figures (DRY).

        Reserve and total_balance are CONDO-LEVEL (one Reserve per condominium); a per-building
        request (building_id set) reports them as None instead of mixing one building's cash with
        the whole-condo reserve into a meaningless total.
        """
        reference_month = date(year, month, 1)
        # Compute the month's components ONCE and share them across result/cash_change/wedge for
        # the reference month (cash_balance still walks its own months) — P5.1 memoization.
        comp = CondoBalanceService._components(year, month, building_id)
        result = CondoBalanceService.result_of_month(year, month, building_id, components=comp)
        cash_change = CondoBalanceService.cash_change_of_month(
            year, month, building_id, components=comp
        )
        cash = CondoBalanceService.cash_balance(_next_month(reference_month), building_id)
        condo_wide = building_id is None
        reserve = CondoBalanceService.reserve_balance() if condo_wide else None
        total = quantize_money(cash + reserve) if reserve is not None else None
        # as_of=today_sp(): the rent overdue/late-fee sub-block stays on SP's date, like every other
        # finances "today" — never the UTC server date.
        rent_stats = RentScheduleService.get_month_stats(year, month, building_id, as_of=today_sp())
        residual = CondoBalanceService._wedge_residual(year, month, building_id, components=comp)
        return {
            "year": year,
            "month": month,
            "result_of_month": str(result),
            "cash_change_of_month": str(cash_change),
            "cash_balance": str(cash),
            "reserve_balance": str(reserve) if reserve is not None else None,
            "total_balance": str(total) if total is not None else None,
            "overdue_bills_total": str(CondoBalanceService.overdue_bills_total(building_id)),
            "overdue_bills_count": CondoBalanceService.overdue_bills_count(building_id),
            "rent_overdue": {
                "count": rent_stats["overdue_count"],
                "total_fee": rent_stats["overdue_total_fee"],
            },
            "wedge_ok": residual == ZERO_MONEY,
        }

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _components(year: int, month: int, building_id: int | None) -> _Components:
        """All raw monthly figures from one place (so result/cash_change/wedge stay consistent)."""
        reference_month = date(year, month, 1)
        received_collectible = RentScheduleService.received_collectible_total(
            reference_month, building_id
        )

        collectible = list(RentScheduleService.collectible_leases(reference_month, building_id))
        paid_lease_ids = set(
            RentPayment.objects.filter(
                reference_month=reference_month, lease__in=collectible
            ).values_list("lease_id", flat=True)
        )
        expected_unpaid = sum(
            (
                RentScheduleService.effective_rental_value(lease, reference_month)
                for lease in collectible
                if lease.pk not in paid_lease_ids
            ),
            ZERO,
        )

        income_competence = CondoBalanceService._income_sum(
            building_id, income_date__year=year, income_date__month=month
        )
        income_cash = CondoBalanceService._income_sum(
            building_id, is_received=True, received_date__year=year, received_date__month=month
        )

        expense_competence = CondoBalanceService._expense_competence(reference_month, building_id)
        caixa_outflow = CondoBalanceService._caixa_outflow(year, month, building_id)

        # Reserve transfers are condo-level (no building) — only in the condo-wide view.
        reserve_to_cash = ZERO
        deposit_out = ZERO
        if building_id is None:
            reserve_to_cash = CondoBalanceService._reserve_movement_sum(
                year, month, ReserveMovementKind.WITHDRAWAL, bill_isnull=True
            )
            deposit_out = CondoBalanceService._reserve_movement_sum(
                year, month, ReserveMovementKind.DEPOSIT, bill_isnull=None
            )

        return _Components(
            received_collectible=received_collectible,
            expected_unpaid=expected_unpaid,
            income_competence=income_competence,
            income_cash=income_cash,
            expense_competence=expense_competence,
            caixa_outflow=caixa_outflow,
            reserve_to_cash=reserve_to_cash,
            deposit_out=deposit_out,
        )

    @staticmethod
    def _income_sum(building_id: int | None, **filters: object) -> Decimal:
        queryset = IncomeEntry.objects.filter(**filters)
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        return queryset.aggregate(total=Sum("amount"))["total"] or ZERO

    @staticmethod
    def _expense_competence(reference_month: date, building_id: int | None) -> Decimal:
        queryset = Bill.objects.with_amounts(today_sp()).filter(
            competence_month=reference_month, lifecycle_state=BillLifecycleState.ACTIVE
        )
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        return queryset.aggregate(total=Sum("amount_total"))["total"] or ZERO

    @staticmethod
    def _caixa_outflow(year: int, month: int, building_id: int | None) -> Decimal:
        # payment__is_deleted=False: a soft-deleted Payment's allocation must not count (the forward
        # FK join does not apply Payment's default manager) — defense in depth with unpay's cascade.
        queryset = PaymentAllocation.objects.filter(
            payment__is_deleted=False,
            payment__funded_from=FundedFrom.CAIXA,
            payment__payment_date__year=year,
            payment__payment_date__month=month,
        )
        if building_id is not None:
            queryset = queryset.filter(bill__building_id=building_id)
        return queryset.aggregate(total=Sum("amount"))["total"] or ZERO

    @staticmethod
    def _reserve_movement_sum(
        year: int, month: int, kind: str, bill_isnull: bool | None
    ) -> Decimal:
        queryset = ReserveMovement.objects.filter(
            reserve__is_deleted=False,
            kind=kind,
            movement_date__year=year,
            movement_date__month=month,
        )
        if bill_isnull is not None:
            queryset = queryset.filter(bill__isnull=bill_isnull)
        return queryset.aggregate(total=Sum("amount"))["total"] or ZERO

    @staticmethod
    def _overdue_bills(building_id: int | None) -> QuerySet[Bill]:
        # is_overdue / amount_remaining are with_amounts annotations — pass the lookup through a
        # dict variable so the django-stubs plugin does not reject the annotation name.
        overdue_lookup: dict[str, object] = {"is_overdue": True}
        queryset = Bill.objects.with_amounts(today_sp()).filter(**overdue_lookup)
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        return queryset

    @staticmethod
    def _cash_baseline(as_of_month: date) -> tuple[Decimal, date]:
        """(baseline cash, first month to walk). Mirrors _get_starting_balance, condo-scoped."""
        last_closed = (
            CondoMonthClose.objects.filter(
                reference_month__lt=as_of_month, status=CondoMonthCloseStatus.CLOSED
            )
            .order_by("-reference_month")
            .first()
        )
        if last_closed is not None:
            return last_closed.cash_balance_end, _next_month(last_closed.reference_month)
        settings = FinancialSettings.objects.first()
        if (
            settings is not None
            and settings.initial_balance_date is not None
            and settings.initial_balance_date <= as_of_month
        ):
            return settings.initial_balance, settings.initial_balance_date.replace(day=1)
        return ZERO_MONEY, as_of_month

    @staticmethod
    def _wedge_residual(
        year: int,
        month: int,
        building_id: int | None = None,
        *,
        components: "_Components | None" = None,
    ) -> Decimal:
        """Reconcile the two PUBLIC KPIs against an INDEPENDENT component delta (design §4.2):

            result_of_month - cash_change_of_month == Δreceivables - Δpayables - reserve_net, where
            Δreceivables = expected_unpaid + (income_competence - income_cash),
            Δpayables    = expense_competence - caixa_outflow,
            reserve_net  = reserve_to_cash - deposit_out.

        The left side reads the public, quantized result_of_month()/cash_change_of_month() — NOT an
        inline copy of their formulas — so a real definitional or quantization drift in either KPI
        yields a non-zero residual. overview.wedge_ok therefore reports a genuine reconciliation,
        not an algebraic tautology that can never fail.
        """
        comp = components or CondoBalanceService._components(year, month, building_id)
        result = CondoBalanceService.result_of_month(year, month, building_id, components=comp)
        cash_change = CondoBalanceService.cash_change_of_month(
            year, month, building_id, components=comp
        )
        delta_receivables = comp.expected_unpaid + (comp.income_competence - comp.income_cash)
        delta_payables = comp.expense_competence - comp.caixa_outflow
        reserve_net = comp.reserve_to_cash - comp.deposit_out
        expected_difference = delta_receivables - delta_payables - reserve_net
        return quantize_money((result - cash_change) - expected_difference)
