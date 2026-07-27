"""Installment plan service (Phase 3, Session 41; consolidate_open_bills — Session 70).

convert_deferred turns a deferred Bill (e.g. an annual IPTU marked deferred) into a
standalone InstallmentPlan atomically — without duplicating or losing value — and leaves
the deferred Bill in a terminal state (CANCELED) outside every sum (design §4.4/§8).

consolidate_open_bills generalizes the same idiom (lock -> validate -> plan -> installments ->
cancel origins) to N open bills of any account type — the "cortada, acumulando, teria que ser
parcelada" (DMAE) case: several open bills of one account become 1 InstallmentPlan and the
origins are canceled atomically, so the debt lives in exactly one place afterwards.
"""

import logging
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Protocol, cast

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from core.services.rent_schedule_service import RentScheduleService
from core.services.timezone import today_sp
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLifecycleState,
    Category,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
)
from finances.services.condo_month_close_service import CondoMonthCloseService

logger = logging.getLogger(__name__)


class _BillTotal(Protocol):
    # Bill.objects.with_amounts(today) annotates amount_remaining; django-stubs does not
    # know about dynamic annotations, so a Protocol cast keeps the read type-safe.
    amount_remaining: Decimal


_CENTS = Decimal("0.01")
_NOT_DEFERRED_MSG = "Só é possível reparcelar uma conta adiada."
_COUNT_POSITIVE_MSG = "O número de parcelas deve ser positivo."
_TOTAL_NON_NEGATIVE_MSG = "O valor da conta a reparcelar não pode ser negativo."
_DEFERRED_NEEDS_IPTU_MSG = "A dívida diferida precisa estar vinculada a uma conta de IPTU."

# Session 70 — consolidate_open_bills.
_BILL_IDS_INVALID = "Informe uma lista de contas sem repetições."
_BILLS_NOT_FOUND = (
    "Uma ou mais contas não foram encontradas ou não pertencem a esta conta cadastrada."
)
_BILL_CANCELED = "Não é possível consolidar uma conta cancelada."
_BILL_NOT_OPEN = "A conta {description} não tem saldo em aberto."
_BILL_FROM_PLAN = "A conta #{id} é parcela de um plano ativo — cancele o plano antes de consolidar."


def _split_amount(total: Decimal, count: int) -> list[Decimal]:
    """Split total into count parts (2 decimals), remainder on the last; every part >= 0.

    The base is rounded DOWN so Σ(base * (count-1)) <= total and the leftover cents land on the
    LAST installment, which is therefore always >= base >= 0. (ROUND_HALF_UP could round the base UP
    and make the last installment negative for tiny totals, e.g. 0.05/9, violating the
    amount >= 0 constraint.) Σ result == total exactly. Example: 100/3 -> [33.33, 33.33, 33.34].
    """
    base = (total / count).quantize(_CENTS, rounding=ROUND_DOWN)
    amounts = [base for _ in range(count - 1)]
    last = total - base * (count - 1)
    amounts.append(last)
    return amounts


def _schedule_due_dates(start_due_date: date, count: int, default_due_day: int) -> list[date]:
    """Due date per installment: start month + (k-1) months, day clamped to the month."""
    dates: list[date] = []
    for offset in range(count):
        base = start_due_date + relativedelta(months=offset)
        day = RentScheduleService.clamp_due_day(default_due_day, base.year, base.month)
        dates.append(date(base.year, base.month, day))
    return dates


class InstallmentPlanService:
    """Stateless installment-plan operations."""

    @staticmethod
    def materialize_schedule(plan: InstallmentPlan, user: User | None = None) -> InstallmentPlan:
        """Materialize plan.installments (the schedule) from total_amount/installment_count/
        start_due_date/default_due_day (B5).

        Every other creation path (convert_deferred, seed_condo_utilities) materializes its
        Installment rows at creation time — a plan with none is an inert shell that generation
        never fills (BillGenerationService reads Installment rows, it does not create them from
        the plan's schedule fields). Idempotent no-op when installments already exist (a caller
        must not double-materialize an existing plan).
        """
        if plan.installments.exists():
            return plan
        amounts = _split_amount(plan.total_amount, plan.installment_count)
        due_dates = _schedule_due_dates(
            plan.start_due_date, plan.installment_count, plan.default_due_day
        )
        for number, (amount, due) in enumerate(zip(amounts, due_dates, strict=True), start=1):
            Installment.objects.create(
                plan=plan,
                number=number,
                due_date=due,
                amount=amount,
                created_by=user,
                updated_by=user,
            )
        return plan

    @staticmethod
    def convert_deferred(
        *,
        deferred_bill: Bill,
        installment_count: int,
        start_due_date: date,
        default_due_day: int,
        category: Category | None = None,
        user: User | None = None,
    ) -> InstallmentPlan:
        """Convert a deferred Bill into a standalone InstallmentPlan, atomically.

        - select_for_update on the bill; precondition lifecycle_state == DEFERRED.
        - total = with_amounts(today).amount_remaining (never summed in Python) — B9: a Bill
          deferred after a partial payment must reschedule only what is still owed; parceling
          amount_total would double-charge the part already paid (its PaymentAllocation stays
          live — the deferred bill goes CANCELED, not deleted, so its payment history persists).
        - Creates the plan + N installments (Σ amount == total, remainder on the last).
        - Deferred bill -> CANCELED (terminal, outside every competence/overdue sum,
          design §4.4). Not soft-deleted: the real Bill history stays auditable.
        """
        if installment_count <= 0:
            raise ValidationError({"installment_count": _COUNT_POSITIVE_MSG})

        with transaction.atomic():
            locked = Bill.all_objects.select_for_update().get(pk=deferred_bill.pk)
            if locked.lifecycle_state != BillLifecycleState.DEFERRED:
                raise ValidationError(_NOT_DEFERRED_MSG)

            # The deferred debt always belongs to an IPTU account (design §3.4/§10.2); the plan
            # inherits it so IptuAlertService (S61) still sees the rescheduled debt via
            # billing_account__account_type=IPTU.
            if (
                locked.billing_account is None
                or locked.billing_account.account_type != BillingAccountType.IPTU
            ):
                raise ValidationError({"billing_account": _DEFERRED_NEEDS_IPTU_MSG})

            annotated = cast(_BillTotal, Bill.objects.with_amounts(today_sp()).get(pk=locked.pk))
            total: Decimal = annotated.amount_remaining
            if total < 0:
                # An offset-heavy bill can annotate a negative total; a plan with a negative
                # total_amount/installments would violate the non-negative constraints. Reject (400).
                raise ValidationError({"total": _TOTAL_NON_NEGATIVE_MSG})

            plan = InstallmentPlan.objects.create(
                condominium=locked.condominium,
                building=locked.building,
                category=category if category is not None else locked.category,
                description=locked.description,
                total_amount=total,
                installment_count=installment_count,
                start_due_date=start_due_date,
                default_due_day=default_due_day,
                lifecycle_state=InstallmentPlanState.ACTIVE,
                embedded=False,
                billing_account=locked.billing_account,
                created_by=user,
                updated_by=user,
            )

            amounts = _split_amount(total, installment_count)
            due_dates = _schedule_due_dates(start_due_date, installment_count, default_due_day)
            for number, (amount, due) in enumerate(zip(amounts, due_dates, strict=True), start=1):
                Installment.objects.create(
                    plan=plan,
                    number=number,
                    due_date=due,
                    amount=amount,
                    created_by=user,
                    updated_by=user,
                )

            locked.lifecycle_state = BillLifecycleState.CANCELED
            locked.updated_by = user
            # AuditMixin.save appends updated_at to update_fields automatically.
            locked.save(update_fields=["lifecycle_state", "updated_by"])

        logger.info(
            "Converted deferred bill %s into installment plan %s (%s installments)",
            locked.pk,
            plan.pk,
            installment_count,
        )
        return plan

    @staticmethod
    def consolidate_open_bills(
        *,
        account: BillingAccount,
        bill_ids: list[int],
        embedded: bool,
        installment_count: int,
        start_due_date: date,
        default_due_day: int,
        user: User | None = None,
    ) -> InstallmentPlan:
        """Consolidate N open bills of the account into 1 InstallmentPlan and CANCEL the origins,
        atomically.

        Own service path that ADMITS canceling a bill with a live partial payment (unlike the
        viewset guard / BillLifecycleService.set_state's assert_not_paid): the paid part stays
        live as real history (its PaymentAllocation is never touched — precedent
        convert_deferred/B9) and only the REST (amount_remaining) enters the plan, so there is no
        double charge and no money lost.

        Ownership is resolved WITHOUT a lock first (a select_for_update over the OR of the two FK
        arms — billing_account / installment__plan__billing_account — raises NotSupportedError on
        Postgres: "FOR UPDATE cannot be applied to the nullable side of an outer join"); the rows
        are then locked by pk (no join).
        """
        if installment_count <= 0:
            raise ValidationError({"installment_count": _COUNT_POSITIVE_MSG})
        if not bill_ids or len(set(bill_ids)) != len(bill_ids):
            raise ValidationError(_BILL_IDS_INVALID)

        with transaction.atomic():
            found = list(
                Bill.objects.filter(pk__in=bill_ids).filter(
                    Q(billing_account=account) | Q(installment__plan__billing_account=account)
                )
            )
            if len(found) != len(bill_ids):
                raise ValidationError(_BILLS_NOT_FOUND)

            # Lock by pk only — NO select_related here: installment is nullable, and
            # select_for_update() over that LEFT OUTER JOIN raises NotSupportedError on Postgres
            # ("FOR UPDATE cannot be applied to the nullable side of an outer join"), same failure
            # mode as locking the two-arm OR above. prefetch_related is safe (separate queries,
            # no JOIN in the locked SELECT) and avoids N+1 on the relation walks
            # _assert_consolidatable does per bill (installment.plan.lifecycle_state,
            # line_items__installment__plan).
            locked_bills = list(
                Bill.objects.select_for_update()
                .filter(pk__in=[bill.pk for bill in found])
                .prefetch_related("installment__plan", "line_items__installment__plan")
                .order_by("pk")
            )
            InstallmentPlanService._assert_consolidatable(locked_bills)

            annotated_by_id = {
                bill.pk: cast(_BillTotal, bill)
                for bill in Bill.objects.with_amounts(today_sp()).filter(
                    pk__in=[bill.pk for bill in locked_bills]
                )
            }
            total = Decimal("0.00")
            for bill in locked_bills:
                remaining = annotated_by_id[bill.pk].amount_remaining
                if remaining <= 0:
                    raise ValidationError(_BILL_NOT_OPEN.format(description=bill.description))
                total += remaining

            plan = InstallmentPlan(
                condominium=account.condominium,
                building=account.building,
                category=account.category,
                description=f"Consolidação de dívida — {account.name}",
                total_amount=total,
                installment_count=installment_count,
                start_due_date=start_due_date,
                default_due_day=default_due_day,
                lifecycle_state=InstallmentPlanState.ACTIVE,
                embedded=embedded,
                billing_account=account,
                created_by=user,
                updated_by=user,
            )
            plan.full_clean()
            plan.save()

            InstallmentPlanService.materialize_schedule(plan, user)

            for bill in locked_bills:
                reference = f"Consolidada no plano #{plan.pk}"
                bill.notes = f"{bill.notes}\n{reference}" if bill.notes else reference
                bill.lifecycle_state = BillLifecycleState.CANCELED
                bill.updated_by = user
                # AuditMixin.save appends updated_at to update_fields automatically.
                bill.save(update_fields=["lifecycle_state", "notes", "updated_by"])

        logger.info(
            "Consolidated %s open bills of billing account %s into installment plan %s (%s installments)",
            len(locked_bills),
            account.pk,
            plan.pk,
            installment_count,
        )
        return plan

    @staticmethod
    def _assert_consolidatable(bills: list[Bill]) -> None:
        """Reject (PT) a CANCELED bill or a plan-owned bill (pureza v1) and assert every
        competence month is open — BEFORE any write (design contract S70).
        """
        for bill in bills:
            if bill.lifecycle_state == BillLifecycleState.CANCELED:
                raise ValidationError(_BILL_CANCELED)
            if InstallmentPlanService._is_from_installment_plan(bill):
                raise ValidationError(_BILL_FROM_PLAN.format(id=bill.pk))
            CondoMonthCloseService.assert_open(bill.competence_month)

    @staticmethod
    def _is_from_installment_plan(bill: Bill) -> bool:
        """Pureza v1 (design contract S70): reject a bill with FK ``installment`` set
        UNCONDITIONALLY (the bill IS a standalone parcela — its plan owns it regardless of the
        plan's own lifecycle_state, e.g. PAID/DEFERRED/CANCELED); reject a bill that carries an
        embedded parcela line (BillLineItem.installment) ONLY when that line's plan is still
        ACTIVE/MATERIALIZED (a live plan would keep generating in parallel, doubling the debt, and
        the S67 statement's N/M progress would lie — a plan already PAID/DEFERRED/CANCELED
        generates nothing more, so its past embedded line does not block consolidation).

        Consolidating a standalone parcela bill unconditionally — even of a PAID/DEFERRED/CANCELED
        plan — would cancel the bill while its Installment row survives pointing at a now-CANCELED
        bill: account_statement_service still counts that Installment as materialized, so the
        extrato's N/M progress lies. That risk exists independent of the origin plan's state, so
        this branch has no live_states qualifier (unlike the embedded-line branch below).

        Reads bill.installment / bill.line_items.all() (prefetched by the caller) rather than
        re-querying with .filter() — a fresh queryset call on a prefetched relation manager
        bypasses the prefetch cache and reintroduces the N+1 this helper is meant to avoid.
        """
        if bill.installment_id is not None:
            return True
        live_states = {InstallmentPlanState.ACTIVE.value, InstallmentPlanState.MATERIALIZED.value}
        for line in bill.line_items.all():
            line_installment = line.installment
            if (
                line_installment is not None
                and line_installment.plan.lifecycle_state in live_states
            ):
                return True
        return False
