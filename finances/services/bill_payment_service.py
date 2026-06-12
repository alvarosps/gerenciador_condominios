"""Bill payment (partial / total) with over-allocation guard (Phase 2, Session 37;
reserve funding + closed-month guard added in Session 45).

pay() creates a Payment + one PaymentAllocation; unpay() reverses via soft-delete.
amount_remaining is read from Bill.objects.with_amounts (never summed in Python).

Session 45 extensions:
- CondoMonthCloseService.assert_open(bill.competence_month) rejects pay/unpay on a closed month.
- funded_from='reserve' also records a ReserveMovement(withdrawal, bill=...) on the condominium's
  reserve, guarded so the reserve never goes negative; unpay reverses that movement too. A
  reserve-funded payment debits only the reserve, never the cash (design §4.3).
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Protocol, cast

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from finances.models import (
    Bill,
    BillLifecycleState,
    FundedFrom,
    Payment,
    PaymentAllocation,
    Reserve,
    ReserveMovement,
)
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.reserve_service import ReserveService
from finances.services.timezone import today_sp

logger = logging.getLogger(__name__)


class _BillRemaining(Protocol):
    # Bill.objects.with_amounts(today) annotates amount_remaining; django-stubs does not
    # propagate dynamic annotations onto the model instance, so we read it via this cast.
    amount_remaining: Decimal


_AMOUNT_NON_POSITIVE = "O valor do pagamento deve ser positivo."
_OVER_ALLOCATION = "O valor do pagamento excede o saldo devedor da conta."
_NO_RESERVE = "Nenhuma reserva configurada para o condomínio."
_BILL_NOT_ACTIVE = "Só é possível pagar uma conta ativa."


class BillPaymentService:
    """Stateless bill payment / reversal."""

    @staticmethod
    def pay(
        bill: Bill,
        payment_date: date,
        amount: Decimal | None = None,
        funded_from: str = FundedFrom.CAIXA,
        user: User | None = None,
    ) -> Payment:
        """Pay a Bill (partial or total). Σ(allocation) == payment.amount; over-allocation rejected.

        funded_from='reserve' additionally debits the condominium reserve via a
        ReserveMovement(withdrawal, bill=..., payment=...) with a balance guard (design §4.3).
        Only an ACTIVE bill is payable — a CANCELED/SUSPENDED/DEFERRED one would be a double
        charge (its expense is already excluded from the result), so it is rejected (PT 400).
        """
        CondoMonthCloseService.assert_open(bill.competence_month)
        if bill.lifecycle_state != BillLifecycleState.ACTIVE:
            raise ValidationError(_BILL_NOT_ACTIVE)
        today = today_sp()
        with transaction.atomic():
            locked = Bill.objects.select_for_update().get(pk=bill.pk)
            # amount_remaining is the with_amounts annotation (never sum in Python, design §4.4).
            annotated = cast(_BillRemaining, Bill.objects.with_amounts(today).get(pk=locked.pk))
            remaining: Decimal = annotated.amount_remaining
            if amount is None:
                amount = remaining
            if amount <= 0:
                raise ValidationError(_AMOUNT_NON_POSITIVE)
            if amount > remaining:
                raise ValidationError(_OVER_ALLOCATION)
            payment = Payment.objects.create(
                condominium=locked.condominium,
                payment_date=payment_date,
                amount=amount,
                funded_from=funded_from,
                created_by=user,
                updated_by=user,
            )
            PaymentAllocation.objects.create(
                payment=payment,
                bill=locked,
                amount=amount,
                created_by=user,
                updated_by=user,
            )
            if payment.funded_from == FundedFrom.RESERVE:
                BillPaymentService._withdraw_reserve_for_bill(
                    locked, payment, amount, payment_date, user
                )
            logger.info("Bill %s paid %s (funded_from=%s)", locked.pk, amount, funded_from)
        return payment

    @staticmethod
    def unpay(payment: Payment, user: User | None = None) -> None:
        """Reverse a payment by soft-deleting it and its allocations (recomposes amount_remaining).

        A reserve-funded payment also reverses every ReserveMovement(withdrawal) linked to it by
        the deterministic ``payment`` FK (never the old bill+kind+amount heuristic, which could
        reverse a sibling payment's movement). Rejected on a closed competence month (assert_open).
        """
        with transaction.atomic():
            for allocation in payment.allocations.all():
                CondoMonthCloseService.assert_open(allocation.bill.competence_month)
                allocation.delete(deleted_by=user)
            for movement in ReserveMovement.objects.filter(payment=payment):
                movement.delete(deleted_by=user)
            payment.delete(deleted_by=user)
            logger.info("Payment %s reversed", payment.pk)

    @staticmethod
    def _withdraw_reserve_for_bill(
        bill: Bill, payment: Payment, amount: Decimal, movement_date: date, user: User | None
    ) -> None:
        """Debit the condominium reserve for a bill payment (guard lives in ReserveService.withdraw).

        The withdrawal carries the driving ``payment`` so unpay can reverse it deterministically.
        """
        reserve = Reserve.objects.filter(condominium=bill.condominium).order_by("id").first()
        if reserve is None:
            raise ValidationError(_NO_RESERVE)
        ReserveService.withdraw(
            reserve, amount, movement_date, bill=bill, payment=payment, user=user
        )
