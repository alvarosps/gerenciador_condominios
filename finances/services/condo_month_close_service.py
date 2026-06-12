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


def _prev_month(value: date) -> date:
    """First day of the month before ``value``'s month."""
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)


def fold_step(net: Decimal, carried_in: Decimal) -> tuple[Decimal, Decimal]:
    """One carry-forward fold step (design §4.7) — the single source of the formula.

    available = max(0, net + carried_in) (the distributable result of the month);
    carried_out = min(0, net + carried_in) (<= 0, carried into the next month).
    Shared by CondoMonthCloseService.close (which freezes carried_out) and
    OwnerDistributionService.compute (which shows both) so the fold is defined once.
    """
    combined = net + carried_in
    return max(ZERO_MONEY, combined), min(ZERO_MONEY, combined)


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
        """Close month M chronologically; freeze net/cash/reserve/carry_forward/breakdown.

        If a later month is already closed (a close-in-the-middle, allowed by _guard_no_gap when
        the gap is forward), the following closed months are recomputed in the same transaction so
        their carried_in/running_cash anchor on M's NEW frozen figures (design §4.7 / P2.3 step 6).
        """
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
            CondoMonthCloseService._recompute_following(reference_month, condominium, user)
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
            count = CondoMonthCloseService._recompute_following(reference_month, condominium, user)
            logger.info("Reopened condo month %s (recomputed %d following)", reference_month, count)
        return snapshot

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _recompute_following(
        reference_month: date, condominium: Condominium, user: User | None
    ) -> int:
        """Re-freeze every still-closed month after M from M's current state (a running cash fold).

        The cash baseline is re-derived from the persisted state of M (closed → its frozen
        cash_balance_end; open → the walked open tail), so a month is never its own baseline. The
        carry_forward fold is anchored each step on the running carried_in computed here, not re-read
        from the DB, so the cascade is correct even before the intermediate saves land (design §4.7).
        Returns the number of following months recomputed (for logging). Caller is inside atomic().
        """
        subsequent = list(
            CondoMonthClose.objects.select_for_update()
            .filter(
                condominium=condominium,
                reference_month__gt=reference_month,
                status=CondoMonthCloseStatus.CLOSED,
            )
            .order_by("reference_month")
        )
        if not subsequent:
            return 0
        running_cash = CondoBalanceService.cash_balance(subsequent[0].reference_month)
        running_carried_in = CondoMonthCloseService.carried_in_for(subsequent[0].reference_month)
        for snap in subsequent:
            running_cash += CondoBalanceService.cash_change_of_month(
                snap.reference_month.year, snap.reference_month.month
            )
            running_carried_in = CondoMonthCloseService._apply_frozen_figures(
                snap, cash_balance_end=running_cash, user=user, carried_in=running_carried_in
            )
            snap.save()
        return len(subsequent)

    @staticmethod
    def _apply_frozen_figures(
        snapshot: CondoMonthClose,
        cash_balance_end: Decimal,
        user: User | None,
        carried_in: Decimal | None = None,
    ) -> Decimal:
        """Set the frozen figures on a snapshot (DRY between close and the cascade recompute).

        ``carried_in`` (the cascade's running fold value) overrides the DB-read anchor so the
        recompute does not depend on intermediate saves landing first. Returns this month's
        carry_forward_out so the caller can chain it as the next month's carried_in.
        """
        year, month = snapshot.reference_month.year, snapshot.reference_month.month
        net_result = CondoBalanceService.result_of_month(year, month)
        # Freeze the reserve at the END of this month (as_of = 1st of M+1, exclusive) — NOT the
        # all-time balance, so a later deposit/withdrawal never drifts a closed snapshot (§4.7).
        reserve_balance_end = CondoBalanceService.reserve_balance(
            as_of=_next_month(snapshot.reference_month)
        )
        snapshot.net_result = net_result
        snapshot.cash_balance_end = cash_balance_end
        snapshot.reserve_balance_end = reserve_balance_end
        # Pre-tracking isolation lives in folded_distribution: an untracked month freezes
        # carry_forward_out = 0.00 so its net never leaks into the first tracked month's fold (§4.7).
        _, _, snapshot.carry_forward_out = CondoMonthCloseService.folded_distribution(
            snapshot.reference_month, net_result, carried_in=carried_in
        )
        # overview()'s live cash_balance re-derives from sibling closes; during the reopen cascade
        # those are not yet persisted, so pin breakdown's cash/total to the frozen figures already
        # computed for THIS row (keeps the breakdown consistent with the stored columns).
        breakdown = CondoBalanceService.overview(year, month)
        breakdown["cash_balance"] = money_str(cash_balance_end)
        breakdown["total_balance"] = money_str(
            quantize_money(cash_balance_end + reserve_balance_end)
        )
        # Freeze the competence pontas (income/expense halves) so a consumer (the projection)
        # can show a closed month's bars without a live recompute drifting from the frozen net.
        revenue, expense = CondoBalanceService.competence_pontas(year, month)
        breakdown["income_total"] = money_str(revenue)
        breakdown["expenses_total"] = money_str(expense)
        snapshot.breakdown = breakdown
        snapshot.updated_by = user
        return snapshot.carry_forward_out

    @staticmethod
    def folded_distribution(
        reference_month: date, net: Decimal, carried_in: Decimal | None = None
    ) -> tuple[Decimal, Decimal, Decimal]:
        """(carried_in, available, carried_out) for a month's net, honoring pre-tracking isolation.

        A TRACKED month folds the net with the anchored carried_in (§4.7 fold_step). When the caller
        supplies ``carried_in`` (the cascade's running value), it is used instead of re-reading the
        DB, so a forward recompute does not depend on intermediate saves landing first. A pre-tracking
        month (before FinancialSettings.rent_tracking_start_date) is ISOLATED: its net is shown but
        never accumulated — carried_in = carried_out = 0.00 — so it can never leak a spurious
        negative into the first tracked month's fold. This is the SINGLE place that decision lives,
        consumed by both close (which freezes carried_out) and OwnerDistributionService (which shows
        all three), so the frozen snapshot and the distribution can never contradict each other.
        """
        if RentScheduleService.is_month_tracked(reference_month.year, reference_month.month):
            anchored_carried_in = (
                carried_in
                if carried_in is not None
                else CondoMonthCloseService.carried_in_for(reference_month)
            )
            available, carried_out = fold_step(net, anchored_carried_in)
            return anchored_carried_in, available, carried_out
        return ZERO_MONEY, max(ZERO_MONEY, net), ZERO_MONEY

    @staticmethod
    def carried_in_for(reference_month: date) -> Decimal:
        """carry_forward_out (<= 0) of the most recent closed month before ``reference_month``
        (else 0.00) — the anchored fold's carried_in. Consumed by close and OwnerDistributionService."""
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
        condominium = Condominium.get_default()
        if condominium is None:
            raise ValidationError(Condominium.NOT_CONFIGURED_MESSAGE)
        return condominium
