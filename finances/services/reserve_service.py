"""Reserve deposit / withdraw service (Phase 4, Session 45, design §4.3).

deposit = cash -> reserve transfer; withdraw = reserve -> cash (bill=null) or reserve-funded
bill payment (bill set). Both are zero-sum on the total balance. withdraw guards the TARGET
reserve's OWN balance so it never goes negative (B10a — a condominium may hold 2+ reserves;
guarding the condo-wide aggregate, as CondoBalanceService.reserve_balance does for the dashboard,
would let one reserve go negative while a sibling reserve's surplus masks it). amount stored
positive; sign comes from kind.
"""

import logging
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from finances.models import Bill, Payment, Reserve, ReserveMovement, ReserveMovementKind
from finances.services.condo_month_close_service import CondoMonthCloseService

logger = logging.getLogger(__name__)

_ZERO = Decimal(0)
_AMOUNT_POSITIVE = "O valor deve ser positivo."
_RESERVE_INSUFFICIENT = "Saldo da reserva insuficiente."


class ReserveService:
    """Stateless reserve deposit / withdraw with the negative-balance guard."""

    @staticmethod
    def deposit(
        reserve: Reserve,
        amount: Decimal,
        movement_date: date,
        *,
        reference: str = "",
        notes: str = "",
        user: User | None = None,
    ) -> ReserveMovement:
        """Cash -> reserve transfer. Total balance unchanged (cash -amount, reserve +amount).

        Rejected (PT 400) when the movement_date's competence month is closed — a reserve transfer
        in a frozen month would silently change that month's reserve_balance_end (design §4.3/§4.7).
        """
        if amount <= 0:
            raise ValidationError(_AMOUNT_POSITIVE)
        CondoMonthCloseService.assert_open(movement_date.replace(day=1))
        with transaction.atomic():
            movement = ReserveMovement.objects.create(
                reserve=reserve,
                kind=ReserveMovementKind.DEPOSIT,
                amount=amount,
                movement_date=movement_date,
                reference=reference,
                notes=notes,
                created_by=user,
                updated_by=user,
            )
            logger.info("Reserve %s deposit %s", reserve.pk, amount)
        return movement

    @staticmethod
    def withdraw(
        reserve: Reserve,
        amount: Decimal,
        movement_date: date,
        *,
        bill: Bill | None = None,
        payment: Payment | None = None,
        reference: str = "",
        notes: str = "",
        user: User | None = None,
    ) -> ReserveMovement:
        """Reserve -> cash (bill=null) or reserve-funded bill payment (bill set). Reserve never negative.

        Rejected (PT 400) when the movement_date's competence month is closed (mirrors deposit).
        ``payment`` (set by BillPaymentService.pay) is the deterministic link unpay reverses by.
        The guard is on THIS reserve's own balance (B10a), not the condominium-wide aggregate.
        """
        if amount <= 0:
            raise ValidationError(_AMOUNT_POSITIVE)
        CondoMonthCloseService.assert_open(movement_date.replace(day=1))
        with transaction.atomic():
            locked = Reserve.objects.select_for_update().get(pk=reserve.pk)
            if amount > ReserveService._balance_of(locked):
                raise ValidationError(_RESERVE_INSUFFICIENT)
            movement = ReserveMovement.objects.create(
                reserve=locked,
                kind=ReserveMovementKind.WITHDRAWAL,
                amount=amount,
                movement_date=movement_date,
                bill=bill,
                payment=payment,
                reference=reference,
                notes=notes,
                created_by=user,
                updated_by=user,
            )
            logger.info(
                "Reserve %s withdraw %s (bill=%s)", locked.pk, amount, bill.pk if bill else None
            )
        return movement

    @staticmethod
    def _balance_of(reserve: Reserve) -> Decimal:
        """Σ deposits - Σ withdrawals for THIS reserve only (B10a — never the condo-wide
        aggregate, which would let a sibling reserve's surplus mask this one going negative)."""
        movements = ReserveMovement.objects.filter(reserve=reserve)
        deposits = (
            movements.filter(kind=ReserveMovementKind.DEPOSIT).aggregate(total=Sum("amount"))[
                "total"
            ]
            or _ZERO
        )
        withdrawals = (
            movements.filter(kind=ReserveMovementKind.WITHDRAWAL).aggregate(total=Sum("amount"))[
                "total"
            ]
            or _ZERO
        )
        return deposits - withdrawals
