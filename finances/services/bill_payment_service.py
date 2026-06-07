"""Bill payment (partial / total) with over-allocation guard (Phase 2, Session 37).

pay() creates a Payment + one PaymentAllocation; unpay() reverses via soft-delete.
amount_remaining is read from Bill.objects.with_amounts (never summed in Python).

Phase-4 extension points (anchored here in prose, not stubs):
- Session 49 inserts CondoMonthCloseService.assert_open(bill.competence_month) before
  the select_for_update so pay/unpay are rejected on a closed month.
- Session 48 extends pay() so funded_from='reserve' creates a
  ReserveMovement(withdrawal, bill=...) with a balance guard; here it only persists
  the funded_from value (Reserve/ReserveMovement do not exist yet).
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Protocol, cast

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from finances.models import Bill, FundedFrom, Payment, PaymentAllocation
from finances.services.timezone import today_sp

logger = logging.getLogger(__name__)


class _BillRemaining(Protocol):
    # Bill.objects.with_amounts(today) annotates amount_remaining; django-stubs does not
    # propagate dynamic annotations onto the model instance, so we read it via this cast.
    amount_remaining: Decimal


_AMOUNT_NON_POSITIVE = "O valor do pagamento deve ser positivo."
_OVER_ALLOCATION = "O valor do pagamento excede o saldo devedor da conta."


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
        """Pay a Bill (partial or total). Σ(allocation) == payment.amount; over-allocation rejected."""
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
            logger.info("Bill %s paid %s (funded_from=%s)", locked.pk, amount, funded_from)
        return payment

    @staticmethod
    def unpay(payment: Payment, user: User | None = None) -> None:
        """Reverse a payment by soft-deleting it and its allocations (recomposes amount_remaining)."""
        with transaction.atomic():
            for allocation in payment.allocations.all():
                allocation.delete(deleted_by=user)
            payment.delete(deleted_by=user)
            logger.info("Payment %s reversed", payment.pk)
