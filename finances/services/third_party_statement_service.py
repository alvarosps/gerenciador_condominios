"""Session 79 — per-person third-party statement (design §6). WRITES NOTHING (read-only, uncached).

The rule in one sentence: chronological FIFO allocation of the person's settlement pool over the
month-by-month "devido", **computed at every read and never persisted**. Not persisting is an
architectural decision, not a detail: a retroactive correction (a purchase entered in the wrong
month, a settlement fixed) is absorbed by the next read, with no data migration and no orphan
allocation rows to clean up.

No cache, deliberately: the statement depends on ``today`` (which month is "current" decides
overdue vs open), and midnight rollover is not a write — a cache would never invalidate. Same
reasoning as ``month_board`` (dashboard_views.py) and ``AccountStatementService``.

``devido(M)`` = Σ third-party Payments made by the person with ``payment_date`` in M
              + Σ ``amount_total`` of the person's purchase Bills with ``competence_month`` == M
                (CANCELED excluded; SUSPENDED/DEFERRED included — the debt to the person exists
                independently of the bill's lifecycle state). ``amount_total`` always comes from
``Bill.objects.with_amounts(today)``, never from summing BillLineItem in Python (design §4.4).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple, TypedDict

from django.db.models import QuerySet, Sum

from core.models import Condominium, Person
from finances.models import (
    Bill,
    BillLifecycleState,
    FundedFrom,
    Payment,
    ThirdPartySettlement,
)
from finances.money import money_str

ZERO = Decimal(0)

# Status vocabulary (derived at read time, never a column — design §6.3).
STATUS_CREDIT = "credit"
STATUS_PAID = "paid"
STATUS_OVERDUE = "overdue"
STATUS_PARTIALLY_PAID = "partially_paid"
STATUS_OPEN = "open"

ITEM_PAYMENT = "payment"
ITEM_PURCHASE = "purchase"


class MonthCharge(NamedTuple):
    """What the person is charged in one month (already aggregated by the ORM)."""

    month: date
    devido: Decimal


class Settlement(NamedTuple):
    """One settlement collapsed to the month it lands in (design §6.2 temporal cut)."""

    month: date
    amount: Decimal


@dataclass(frozen=True)
class AllocatedMonth:
    """One month after FIFO allocation — raw Decimals, quantized only at the output boundary."""

    month: date
    devido: Decimal
    aplicado: Decimal
    resto: Decimal
    status: str


class AllocationTotals(TypedDict):
    total_devido: Decimal
    total_pago: Decimal
    total_em_aberto: Decimal
    total_atrasado: Decimal
    saldo_credor: Decimal


class StatementItem(TypedDict):
    kind: str
    id: int
    description: str
    amount: str
    date: date


class StatementMonth(TypedDict):
    month: date
    devido: str
    aplicado: str
    resto: str
    status: str
    items: list[StatementItem]


class StatementTotals(TypedDict):
    total_devido: str
    total_pago: str
    total_em_aberto: str
    total_atrasado: str
    saldo_credor: str


class ThirdPartyStatement(TypedDict):
    """Payload shape returned by ``build`` (S79 authoritative contract — design §6.5)."""

    person_id: int
    person_name: str
    months: list[StatementMonth]
    totals: StatementTotals


def _next_month(value: date) -> date:
    return date(value.year + value.month // 12, value.month % 12 + 1, 1)


def _month_status(
    *, devido: Decimal, aplicado: Decimal, resto: Decimal, month: date, current_month: date
) -> str:
    """Evaluation order matters (design §6.3): credit first, then paid, then overdue."""
    if devido < ZERO:
        return STATUS_CREDIT
    if resto == ZERO:
        return STATUS_PAID
    if month < current_month:
        return STATUS_OVERDUE
    if aplicado > ZERO:
        return STATUS_PARTIALLY_PAID
    return STATUS_OPEN


def allocate_fifo(
    charges: list[MonthCharge],
    settlements: list[Settlement],
    *,
    current_month: date,
) -> tuple[list[AllocatedMonth], AllocationTotals]:
    """Chronological FIFO allocation of the settlement pool over the monthly charges (design §6.2).

    Pure function over already-fetched lists — no I/O, so it is testable in isolation and the
    ORM work stays in ``build``.

    **Temporal cut**: at month M only settlements whose ``settlement_date`` falls in M or earlier
    enter the pool. Without it a January settlement would clear a June purchase, painting a month
    green before the debt even existed and making ``total_atrasado`` — the one number the owners
    actually look at — lie.

    A month with negative ``devido`` (offset lines outweigh charges) is a credit: its absolute
    value joins the pool and propagates forward instead of being "collected".

    ``total_devido`` sums ``max(0, devido)`` (design §6.3): summing signed months would let a
    credit month cancel a charge month and report "R$ 0 owed" to someone who is owed money.
    """
    pending = sorted(settlements, key=lambda settlement: settlement.month)
    next_settlement = 0

    pool = ZERO
    total_devido = ZERO
    total_pago = ZERO
    total_em_aberto = ZERO
    total_atrasado = ZERO
    rows: list[AllocatedMonth] = []

    for charge in charges:
        # Temporal cut: only settlements dated in this month or earlier join the pool. The
        # pointer advances monotonically because both lists are chronological.
        while next_settlement < len(pending) and pending[next_settlement].month <= charge.month:
            pool += pending[next_settlement].amount
            next_settlement += 1
        devido = charge.devido
        if devido < ZERO:
            pool += -devido
            fillable = ZERO
        else:
            fillable = devido
        aplicado = min(pool, fillable)
        pool -= aplicado
        resto = fillable - aplicado

        total_devido += fillable
        total_pago += aplicado
        if charge.month <= current_month:
            total_em_aberto += resto
        if charge.month < current_month:
            total_atrasado += resto

        rows.append(
            AllocatedMonth(
                month=charge.month,
                devido=devido,
                aplicado=aplicado,
                resto=resto,
                status=_month_status(
                    devido=devido,
                    aplicado=aplicado,
                    resto=resto,
                    month=charge.month,
                    current_month=current_month,
                ),
            )
        )

    # Settlements dated after the last charge month still belong to the person's credit balance
    # (they are money already handed over), so they drain into saldo_credor.
    for settlement in pending[next_settlement:]:
        pool += settlement.amount

    totals: AllocationTotals = {
        "total_devido": total_devido,
        "total_pago": total_pago,
        "total_em_aberto": total_em_aberto,
        "total_atrasado": total_atrasado,
        "saldo_credor": pool,
    }
    return rows, totals


def _month_window(months_with_movement: set[date], current_month: date) -> list[date]:
    """Every month from the first with movement to max(current month, last with movement).

    Gap months inside the window are materialized with ``devido = 0`` — without them the
    statement would have holes and the reader could not tell "nothing happened" from
    "the row is missing".
    """
    if not months_with_movement:
        return []
    cursor = min(months_with_movement)
    last = max(*months_with_movement, current_month)
    window: list[date] = []
    while cursor <= last:
        window.append(cursor)
        cursor = _next_month(cursor)
    return window


def _default_condominium_id() -> int:
    """Id of the singleton condominium — same "lowest live id" rule as ``Condominium.get_default``,
    read as a scalar so no instance is materialized.

    ``-1`` when no condominium exists at all: the migration creates one and ``Building.save``
    bootstraps it, so this is a value that matches no row rather than a branch to test. The
    statement then comes back empty, the truthful answer for a system with no data.
    """
    return Condominium.objects.order_by("id").values_list("pk", flat=True).first() or -1


def _payments_queryset(person_id: int, condominium_id: int) -> QuerySet[Payment]:
    return Payment.objects.filter(
        condominium_id=condominium_id,
        funded_from=FundedFrom.THIRD_PARTY,
        paid_by_id=person_id,
    )


def _purchases_queryset(person_id: int, condominium_id: int, today: date) -> QuerySet[Bill]:
    return (
        Bill.objects.with_amounts(today)
        .filter(condominium_id=condominium_id, paid_by_person_id=person_id)
        .exclude(lifecycle_state=BillLifecycleState.CANCELED)
    )


class ThirdPartyStatementService:
    """Stateless read-only per-person third-party statement (design §6)."""

    @staticmethod
    def build(
        person_id: int, today: date, condominium_id: int | None = None
    ) -> ThirdPartyStatement:
        """Extrato da pessoa (design §6). Read-only, uncached. Sempre chamado com today_sp().

        ``condominium_id`` defaults to the singleton condominium and scopes BOTH sides of the
        statement — charges and settlements (design §6.3.1); scoping only one side would be a
        latent bug the day a second condominium exists.

        The person's name is resolved through ``Person.all_objects`` so a soft-deleted person
        still shows her name: PROTECT stops a hard delete, not a soft one, and a debt owed to
        her must not become anonymous (precedent: owner_distribution_service).

        Constant query count — two aggregations for the monthly figures, one settlement fetch,
        two row fetches (name + item detail) — regardless of how many months the window spans.
        """
        if condominium_id is None:
            condominium_id = _default_condominium_id()
        current_month = today.replace(day=1)

        payments = _payments_queryset(person_id, condominium_id)
        purchases = _purchases_queryset(person_id, condominium_id, today)
        settlements = ThirdPartySettlement.objects.filter(
            condominium_id=condominium_id, person_id=person_id
        )

        devido_by_month: dict[date, Decimal] = {}
        for row in payments.values("payment_date").annotate(total=Sum("amount")):
            month = row["payment_date"].replace(day=1)
            devido_by_month[month] = devido_by_month.get(month, ZERO) + row["total"]
        for row in purchases.values("competence_month").annotate(total=Sum("amount_total")):
            month = row["competence_month"]
            devido_by_month[month] = devido_by_month.get(month, ZERO) + row["total"]

        settlement_rows = [
            Settlement(month=settlement_date.replace(day=1), amount=amount)
            for settlement_date, amount in settlements.values_list("settlement_date", "amount")
        ]

        months_with_movement = {*devido_by_month, *(row.month for row in settlement_rows)}
        window = _month_window(months_with_movement, current_month)
        charges = [
            MonthCharge(month=month, devido=devido_by_month.get(month, ZERO)) for month in window
        ]
        allocated, totals = allocate_fifo(charges, settlement_rows, current_month=current_month)

        items_by_month = _items_by_month(payments, purchases)
        return {
            "person_id": person_id,
            "person_name": _person_name(person_id),
            "months": [
                {
                    "month": row.month,
                    "devido": money_str(row.devido),
                    "aplicado": money_str(row.aplicado),
                    "resto": money_str(row.resto),
                    "status": row.status,
                    "items": items_by_month.get(row.month, []),
                }
                for row in allocated
            ],
            "totals": {
                "total_devido": money_str(totals["total_devido"]),
                "total_pago": money_str(totals["total_pago"]),
                "total_em_aberto": money_str(totals["total_em_aberto"]),
                "total_atrasado": money_str(totals["total_atrasado"]),
                "saldo_credor": money_str(totals["saldo_credor"]),
            },
        }


def _person_name(person_id: int) -> str:
    """all_objects mirrors FK access — a soft-deleted person still shows her name (design §6.3.1)."""
    return Person.all_objects.filter(pk=person_id).values_list("name", flat=True).first() or ""


def _items_by_month(
    payments: QuerySet[Payment], purchases: QuerySet[Bill]
) -> dict[date, list[StatementItem]]:
    """Per-month detail rows (what composes the ``devido``) — ONE query per kind, never per month.

    Purchases carry ``amount_total`` from the ``with_amounts`` annotation, so the item amount and
    the month aggregate come from the same source and can never disagree.
    """
    grouped: dict[date, list[StatementItem]] = {}
    for payment_id, payment_date, amount, reference in payments.values_list(
        "id", "payment_date", "amount", "reference"
    ):
        grouped.setdefault(payment_date.replace(day=1), []).append(
            {
                "kind": ITEM_PAYMENT,
                "id": payment_id,
                "description": reference,
                "amount": money_str(amount),
                "date": payment_date,
            }
        )
    # Bill instances (not values/values_list): amount_total is a with_amounts() annotation, which
    # django-stubs cannot resolve as a values() field name. getattr mirrors
    # AccountStatementService._month_row — the default never fires, since ``purchases`` is always
    # annotated by _purchases_queryset.
    for bill in purchases.only("id", "competence_month", "description"):
        grouped.setdefault(bill.competence_month, []).append(
            {
                "kind": ITEM_PURCHASE,
                "id": bill.pk,
                "description": bill.description,
                "amount": money_str(getattr(bill, "amount_total", ZERO)),
                "date": bill.competence_month,
            }
        )
    return grouped
