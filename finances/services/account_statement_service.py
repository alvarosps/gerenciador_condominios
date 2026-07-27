"""Session 67 — per-account statement (design §3.4). WRITES NOTHING (read-only, uncached).

Assembles the three sections the cockpit's account detail page needs: stats (open balance,
open bills count, average delay), the month-by-month line list (both FK arms — direct
``billing_account`` and standalone-parcela ``installment->plan->billing_account``), and the
linked installment plans with materialization progress. ``today`` always comes from the caller
(today_sp()); money is always read from ORM annotations (with_amounts / with_open_balance),
never recomputed from line items in Python (design §10).
"""

from datetime import date
from decimal import Decimal
from typing import TypedDict

from django.db.models import Max, OuterRef, Q, Subquery

from finances.models import (
    Bill,
    BillingAccount,
    BillLifecycleState,
    BillLineItem,
    Installment,
    InstallmentPlan,
    PaymentAllocation,
)
from finances.money import money_str
from finances.serializers import BillingAccountSerializer

# Only the last N settled bills feed avg_delay_days (design §3.4 / SESSION_STATE S67).
_AVG_DELAY_WINDOW = 12


class StatementStats(TypedDict):
    open_balance: str
    open_bills_count: int
    avg_delay_days: int | None


class StatementMonthRow(TypedDict):
    bill_id: int
    competence_month: date
    due_date: date
    description: str
    amount_total: str
    amount_paid: str
    amount_remaining: str
    payment_status: str
    lifecycle_state: str
    amount_is_estimated: bool
    paid_date: date | None


class StatementPlanRow(TypedDict):
    id: int
    description: str
    installment_count: int
    materialized_count: int
    lifecycle_state: str
    embedded: bool


class AccountStatement(TypedDict):
    """Payload shape returned by ``build`` (S67 authoritative contract — SESSION_STATE)."""

    account: dict[str, object]
    stats: StatementStats
    months: list[StatementMonthRow]
    plans: list[StatementPlanRow]


def _account_bills(account: BillingAccount, today: date) -> list[Bill]:
    """Both-arms bills of ``account`` (direct FK OR standalone parcela), CANCELED/deleted
    excluded, ordered most-recent-first (competence_month desc, then due_date desc).

    The paid_date figure is annotated here (not in with_amounts, which is shared by every
    other Bill consumer) as a scalar correlated subquery mirroring the payment__is_deleted=False
    guard in with_amounts' paid_subquery (models.py:242-248): live allocation + live payment.
    """
    paid_date_subquery = Subquery(
        PaymentAllocation.objects.filter(bill=OuterRef("pk"), payment__is_deleted=False)
        .values("bill")
        .annotate(max_paid_date=Max("payment__payment_date"))
        .values("max_paid_date"),
    )
    return list(
        Bill.objects.with_amounts(today)
        .filter(Q(billing_account=account) | Q(installment__plan__billing_account=account))
        .exclude(lifecycle_state=BillLifecycleState.CANCELED)
        .annotate(paid_date=paid_date_subquery)
        .select_related("billing_account", "installment__plan__billing_account")
        .order_by("-competence_month", "-due_date")
    )


def _month_row(bill: Bill) -> StatementMonthRow:
    return {
        "bill_id": bill.pk,
        "competence_month": bill.competence_month,
        "due_date": bill.due_date,
        "description": bill.description,
        "amount_total": money_str(getattr(bill, "amount_total", Decimal(0))),
        "amount_paid": money_str(getattr(bill, "amount_paid", Decimal(0))),
        "amount_remaining": money_str(getattr(bill, "amount_remaining", Decimal(0))),
        # getattr (not direct attribute access) only to satisfy mypy/django-stubs, which cannot
        # see the with_amounts() dynamic annotation — the default never actually fires, since
        # _account_bills always annotates payment_status (mirrors BillSerializer.get_payment_status,
        # serializers.py:408-409).
        "payment_status": str(getattr(bill, "payment_status", "")),
        "lifecycle_state": bill.lifecycle_state,
        "amount_is_estimated": bill.amount_is_estimated,
        "paid_date": getattr(bill, "paid_date", None),
    }


def _avg_delay_days(bills: list[Bill]) -> int | None:
    """Mean (paid_date - due_date).days of the last _AVG_DELAY_WINDOW SETTLED bills (already
    ordered most-recent-first by ``_account_bills``) — settled = amount_remaining == 0 AND
    amount_total > 0 (excludes zero-total bills); a settled bill missing paid_date is skipped
    defensively. Can be negative (paid early). None when no settled bill qualifies."""
    settled = [
        bill
        for bill in bills
        if getattr(bill, "amount_remaining", Decimal(0)) == 0
        and getattr(bill, "amount_total", Decimal(0)) > 0
    ]
    delays: list[int] = []
    for bill in settled[:_AVG_DELAY_WINDOW]:
        paid_date = getattr(bill, "paid_date", None)
        if paid_date is None:
            continue
        delays.append((paid_date - bill.due_date).days)
    if not delays:
        return None
    return round(sum(delays) / len(delays))


def _materialized_installment_ids(plan_ids: list[int]) -> set[int]:
    """Installment ids of ``plan_ids`` that already have a materialized BillLineItem OR Bill —
    TWO queries total (one per source), never one per plan/installment. Mirrors
    BillGenerationService._mark_completed_plans_materialized (bill_generation_service.py:325-349):
    embedded plans materialize via BillLineItem, standalone plans materialize via Bill — a given
    plan is only ever one or the other, so taking the union of both sources is safe and avoids a
    per-plan branch query."""
    from_line_items = BillLineItem.objects.filter(installment__plan_id__in=plan_ids).values_list(
        "installment_id", flat=True
    )
    from_bills = Bill.objects.filter(installment__plan_id__in=plan_ids).values_list(
        "installment_id", flat=True
    )
    return {*from_line_items, *from_bills}


def _plan_rows(plans: list[InstallmentPlan]) -> list[StatementPlanRow]:
    """materialized_count per plan, built from a single preloaded index (no N+1): one query for
    ALL plans' installments, two queries for the materialized ids (_materialized_installment_ids)
    — independent of how many plans or installments the account has (design §10 / review S67)."""
    plan_ids = [plan.pk for plan in plans]
    installments_by_plan: dict[int, list[int]] = {plan_id: [] for plan_id in plan_ids}
    for installment_id, plan_id in Installment.objects.filter(plan_id__in=plan_ids).values_list(
        "id", "plan_id"
    ):
        installments_by_plan[plan_id].append(installment_id)
    materialized_ids = _materialized_installment_ids(plan_ids)
    return [
        {
            "id": plan.pk,
            "description": plan.description,
            "installment_count": plan.installment_count,
            "materialized_count": sum(
                1 for inst_id in installments_by_plan[plan.pk] if inst_id in materialized_ids
            ),
            "lifecycle_state": plan.lifecycle_state,
            "embedded": plan.embedded,
        }
        for plan in plans
    ]


class AccountStatementService:
    """Stateless read-only per-account statement for the cockpit's account detail page."""

    @staticmethod
    def build(account_id: int, today: date) -> AccountStatement:
        """Extrato da conta (design §3.4). Read-only, uncached. Sempre chamado com today_sp().
        Bills agregadas pelos DOIS braços: Q(billing_account=conta) | Q(installment__plan__
        billing_account=conta)."""
        account = BillingAccount.objects.with_open_balance(today).get(pk=account_id)
        bills = _account_bills(account, today)
        open_bills_count = sum(
            1 for bill in bills if getattr(bill, "amount_remaining", Decimal(0)) > 0
        )
        plans = list(
            InstallmentPlan.objects.filter(billing_account=account).select_related(
                "billing_account"
            )
        )
        return {
            "account": dict(BillingAccountSerializer(account).data),
            "stats": {
                "open_balance": money_str(getattr(account, "open_balance", Decimal(0))),
                "open_bills_count": open_bills_count,
                "avg_delay_days": _avg_delay_days(bills),
            },
            "months": [_month_row(bill) for bill in bills],
            "plans": _plan_rows(plans),
        }
