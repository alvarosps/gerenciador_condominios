"""Installment plan service (Phase 3, Session 41).

convert_deferred turns a deferred Bill (e.g. an annual IPTU marked deferred) into a
standalone InstallmentPlan atomically — without duplicating or losing value — and leaves
the deferred Bill in a terminal state (CANCELED) outside every sum (design §4.4/§8).
"""

import logging
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Protocol, cast

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from core.services.rent_schedule_service import RentScheduleService
from finances.models import (
    Bill,
    BillingAccountType,
    BillLifecycleState,
    Category,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
)
from finances.services.timezone import today_sp

logger = logging.getLogger(__name__)


class _BillTotal(Protocol):
    # Bill.objects.with_amounts(today) annotates amount_total; django-stubs does not
    # know about dynamic annotations, so a Protocol cast keeps the read type-safe.
    amount_total: Decimal


_CENTS = Decimal("0.01")
_NOT_DEFERRED_MSG = "Só é possível reparcelar uma conta adiada."
_COUNT_POSITIVE_MSG = "O número de parcelas deve ser positivo."
_TOTAL_NON_NEGATIVE_MSG = "O valor da conta a reparcelar não pode ser negativo."
_DEFERRED_NEEDS_IPTU_MSG = "A dívida diferida precisa estar vinculada a uma conta de IPTU."


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
        - total = with_amounts(today).amount_total (never summed in Python).
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
            total: Decimal = annotated.amount_total
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
