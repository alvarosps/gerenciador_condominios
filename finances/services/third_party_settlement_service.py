"""Session 80 — third-party settlement writes, guarded by the closed month (design §4.4 / §4c).

A settlement is real cash leaving the condominium (``CondoBalanceService`` counts it in
``settlements_out``, S78), and ``CondoMonthClose.cash_balance_end`` is frozen. Creating, moving or
deleting a settlement in an already-closed month would silently corrupt that snapshot — the exact
bug class the project already fixed for payments (B3, ``bill_payment_service.py``).

Therefore ``ThirdPartySettlement`` is NEVER written by a bare ``ModelViewSet``: every create,
update and delete goes through this service, which asserts the settlement month is open. On an
update BOTH months are guarded — the one it is leaving and the one it is entering — because moving
a settlement OUT of a closed month corrupts that month just as much as moving one in.
"""

import logging
from datetime import date

from django.contrib.auth.models import User
from django.db import transaction

from finances.models import ThirdPartySettlement
from finances.services.condo_month_close_service import CondoMonthCloseService

logger = logging.getLogger(__name__)


class ThirdPartySettlementService:
    """Stateless settlement writes with the closed-month guard (design §4.4)."""

    @staticmethod
    def create(settlement: ThirdPartySettlement, user: User | None = None) -> ThirdPartySettlement:
        """Persist a new settlement after asserting its cash month is open."""
        CondoMonthCloseService.assert_open(settlement.settlement_date.replace(day=1))
        with transaction.atomic():
            settlement.created_by = user
            settlement.updated_by = user
            settlement.full_clean()
            settlement.save()
        logger.info("Third-party settlement %s created", settlement.pk)
        return settlement

    @staticmethod
    def update(
        settlement: ThirdPartySettlement,
        previous_date: date,
        user: User | None = None,
    ) -> ThirdPartySettlement:
        """Persist an edited settlement, guarding the OLD and the NEW cash month.

        ``previous_date`` is the date the record had before the serializer applied the payload;
        guarding only the new one would let an edit drag a settlement out of a frozen month.
        """
        CondoMonthCloseService.assert_open(previous_date.replace(day=1))
        CondoMonthCloseService.assert_open(settlement.settlement_date.replace(day=1))
        with transaction.atomic():
            settlement.updated_by = user
            settlement.full_clean()
            settlement.save()
        logger.info("Third-party settlement %s updated", settlement.pk)
        return settlement

    @staticmethod
    def delete(settlement: ThirdPartySettlement, user: User | None = None) -> None:
        """Soft-delete a settlement after asserting its cash month is open."""
        CondoMonthCloseService.assert_open(settlement.settlement_date.replace(day=1))
        settlement.delete(deleted_by=user)
        logger.info("Third-party settlement %s deleted", settlement.pk)
