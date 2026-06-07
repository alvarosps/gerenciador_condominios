"""Condominium month-close service (Phase 4, Session 45, design §4.7/§5.2/§8).

close() freezes the month's figures (net/cash/reserve/carry_forward) chronologically — it
refuses to close M while an earlier trackable month is still open (no gap) and refuses to
re-close. reopen() flips M back to 'open' and recomputes the still-closed following months
from the new baseline (running fold, so a month is never its own baseline). assert_open() is
the single closed-month guard consumed by BillPaymentService.pay/unpay.

The frozen figures come from CondoBalanceService through the same quantize_money boundary, so
a CondoMonthClose snapshot can never differ from the on-read dashboard by a cent.
"""

import logging
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Condominium
from core.services.rent_schedule_service import RentScheduleService
from finances.models import CondoMonthClose, CondoMonthCloseStatus
from finances.money import money_str, quantize_money
from finances.services.condo_balance_service import CondoBalanceService, _next_month
from finances.services.timezone import now_sp

logger = logging.getLogger(__name__)

ZERO_MONEY = Decimal("0.00")

_MONTH_CLOSED = "Este mês está fechado e não aceita lançamentos."
_GAP = "Feche os meses anteriores antes de fechar este mês."
_ALREADY_CLOSED = "Este mês já está fechado."
_NOT_FOUND = "Não há fechamento registrado para este mês."
_NO_CONDOMINIUM = "Nenhum condomínio configurado."


def _prev_month(value: date) -> date:
    """First day of the month before ``value``'s month."""
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)


class CondoMonthCloseService:
    """Stateless chronological close / reopen / closed-month guard."""

    @staticmethod
    def assert_open(competence_month: date) -> None:
        """Raise (PT) if the competence month is closed. No CondoMonthClose = open (no-op)."""
        reference_month = competence_month.replace(day=1)
        is_closed = CondoMonthClose.objects.filter(
            reference_month=reference_month, status=CondoMonthCloseStatus.CLOSED
        ).exists()
        if is_closed:
            raise ValidationError(_MONTH_CLOSED)

    @staticmethod
    def close(year: int, month: int, user: User | None = None) -> CondoMonthClose:
        """Close month M chronologically; freeze net/cash/reserve/carry_forward/breakdown."""
        reference_month = date(year, month, 1)
        condominium = CondoMonthCloseService._condominium()
        with transaction.atomic():
            existing = (
                CondoMonthClose.objects.select_for_update()
                .filter(condominium=condominium, reference_month=reference_month)
                .first()
            )
            if existing is not None and existing.status == CondoMonthCloseStatus.CLOSED:
                raise ValidationError(_ALREADY_CLOSED)
            CondoMonthCloseService._guard_no_gap(reference_month)

            snapshot = existing or CondoMonthClose(
                condominium=condominium, reference_month=reference_month, created_by=user
            )
            CondoMonthCloseService._apply_frozen_figures(
                snapshot,
                cash_balance_end=CondoBalanceService.cash_balance(_next_month(reference_month)),
                user=user,
            )
            snapshot.status = CondoMonthCloseStatus.CLOSED
            snapshot.closed_at = now_sp()
            snapshot.save()
            logger.info("Closed condo month %s", reference_month)
        return snapshot

    @staticmethod
    def reopen(year: int, month: int, user: User | None = None) -> CondoMonthClose:
        """Reopen month M and recompute the still-closed following months from the new baseline."""
        reference_month = date(year, month, 1)
        condominium = CondoMonthCloseService._condominium()
        with transaction.atomic():
            snapshot = (
                CondoMonthClose.objects.select_for_update()
                .filter(condominium=condominium, reference_month=reference_month)
                .first()
            )
            if snapshot is None:
                raise ValidationError(_NOT_FOUND)
            snapshot.status = CondoMonthCloseStatus.OPEN
            snapshot.closed_at = None
            snapshot.updated_by = user
            snapshot.save()

            subsequent = list(
                CondoMonthClose.objects.select_for_update()
                .filter(
                    condominium=condominium,
                    reference_month__gt=reference_month,
                    status=CondoMonthCloseStatus.CLOSED,
                )
                .order_by("reference_month")
            )
            if subsequent:
                # Running fold: start from the cash at the end of the reopened month (M is now
                # open, so cash_balance(first day of M+1) walks the open tail through M without
                # referencing any still-closed month's frozen value).
                running_cash = CondoBalanceService.cash_balance(subsequent[0].reference_month)
                for snap in subsequent:
                    running_cash += CondoBalanceService.cash_change_of_month(
                        snap.reference_month.year, snap.reference_month.month
                    )
                    CondoMonthCloseService._apply_frozen_figures(
                        snap, cash_balance_end=running_cash, user=user
                    )
                    snap.save()
            logger.info(
                "Reopened condo month %s (recomputed %d following)",
                reference_month,
                len(subsequent),
            )
        return snapshot

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _apply_frozen_figures(
        snapshot: CondoMonthClose, cash_balance_end: Decimal, user: User | None
    ) -> None:
        """Set the frozen figures on a snapshot (DRY between close and the reopen cascade)."""
        year, month = snapshot.reference_month.year, snapshot.reference_month.month
        net_result = CondoBalanceService.result_of_month(year, month)
        carry_in = CondoMonthCloseService._carry_in(snapshot.reference_month)
        reserve_balance_end = CondoBalanceService.reserve_balance()
        snapshot.net_result = net_result
        snapshot.cash_balance_end = cash_balance_end
        snapshot.reserve_balance_end = reserve_balance_end
        snapshot.carry_forward_out = min(ZERO_MONEY, net_result + carry_in)
        # overview()'s live cash_balance re-derives from sibling closes; during the reopen cascade
        # those are not yet persisted, so pin breakdown's cash/total to the frozen figures already
        # computed for THIS row (keeps the breakdown consistent with the stored columns).
        breakdown = CondoBalanceService.overview(year, month)
        breakdown["cash_balance"] = money_str(cash_balance_end)
        breakdown["total_balance"] = money_str(
            quantize_money(cash_balance_end + reserve_balance_end)
        )
        snapshot.breakdown = breakdown
        snapshot.updated_by = user

    @staticmethod
    def _carry_in(reference_month: date) -> Decimal:
        """carry_forward_out of the most recent closed month before ``reference_month`` (else 0)."""
        previous = (
            CondoMonthClose.objects.filter(
                reference_month__lt=reference_month, status=CondoMonthCloseStatus.CLOSED
            )
            .order_by("-reference_month")
            .first()
        )
        return previous.carry_forward_out if previous is not None else ZERO_MONEY

    @staticmethod
    def _guard_no_gap(reference_month: date) -> None:
        """Reject closing M if the previous trackable month is still open (design §8, no gap).

        The fold anchor is the rent-tracking start (FinancialSettings) when set, else the
        earliest existing close, else M itself. A month at/before the anchor needs no predecessor.
        """
        anchor = CondoMonthCloseService._fold_anchor(reference_month)
        previous = _prev_month(reference_month)
        if previous >= anchor:
            previous_closed = CondoMonthClose.objects.filter(
                reference_month=previous, status=CondoMonthCloseStatus.CLOSED
            ).exists()
            if not previous_closed:
                raise ValidationError(_GAP)

    @staticmethod
    def _fold_anchor(reference_month: date) -> date:
        start = RentScheduleService.rent_tracking_start_month()
        if start is not None:
            return start
        earliest = CondoMonthClose.objects.order_by("reference_month").first()
        if earliest is not None:
            return earliest.reference_month
        return reference_month

    @staticmethod
    def _condominium() -> Condominium:
        condominium = Condominium.objects.order_by("id").first()
        if condominium is None:
            raise ValidationError(_NO_CONDOMINIUM)
        return condominium
