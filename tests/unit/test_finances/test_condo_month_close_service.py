"""Session 45 — CondoMonthCloseService unit tests (design §4.7/§8).

close() freezes the right figures chronologically; the fold carry-forward is sequential;
the anchor respects the rent-tracking start; reopen recomputes the cascade; assert_open is
the single closed-month guard (consumed by BillPaymentService.pay). freezegun only.
"""

import itertools
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from core.models import FinancialSettings
from finances.models import BillLifecycleState, CondoMonthCloseStatus, FundedFrom
from finances.services.bill_payment_service import BillPaymentService
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService
from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_building,
    make_condominium,
    make_lease,
    make_rent_payment,
    make_reserve,
    make_reserve_movement,
)

pytestmark = pytest.mark.django_db

_street_numbers = itertools.count(5000)


def _paid_lease(rent: str, reference_month: date):
    building = make_building(street_number=next(_street_numbers))
    apartment = make_apartment(building=building)
    lease = make_lease(apartment=apartment, rental_value=Decimal(rent), start_date=date(2026, 1, 1))
    make_rent_payment(lease=lease, reference_month=reference_month, amount_paid=Decimal(rent))
    return lease


def _active_bill(amount: str, competence_month: date):
    bill = make_bill(competence_month=competence_month, lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time("2026-06-15")
def test_close_freezes_values() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("0.00"), initial_balance_date=date(2026, 5, 1)
    )
    _paid_lease("1000.00", date(2026, 6, 1))
    bill = _active_bill("400.00", date(2026, 6, 1))
    BillPaymentService.pay(bill, date(2026, 6, 7), Decimal("400.00"), FundedFrom.CAIXA)

    close = CondoMonthCloseService.close(2026, 6)
    assert close.status == CondoMonthCloseStatus.CLOSED
    assert close.closed_at is not None
    assert close.net_result == Decimal("600.00")  # 1000 - 400
    assert close.cash_balance_end == Decimal("600.00")  # 1000 in - 400 out
    assert close.reserve_balance_end == Decimal("0.00")
    assert close.carry_forward_out == Decimal("0.00")  # net positive → no carry
    assert close.breakdown["result_of_month"] == "600.00"


@freeze_time("2026-06-15")
def test_close_rejects_chronological_gap() -> None:
    make_condominium()  # close() resolves the default condominium (self-contained, no ambient state)
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 4, 1),
        rent_tracking_start_date=date(2026, 4, 1),
    )
    # April is the anchor; closing June while April/May are open is a gap.
    with pytest.raises(ValidationError):
        CondoMonthCloseService.close(2026, 6)
    CondoMonthCloseService.close(2026, 4)
    CondoMonthCloseService.close(2026, 5)
    CondoMonthCloseService.close(2026, 6)  # now in order
    assert CondoMonthCloseService._fold_anchor(date(2026, 6, 1)) == date(2026, 4, 1)


@freeze_time("2026-06-15")
def test_close_already_closed_rejected() -> None:
    make_condominium()
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        CondoMonthCloseService.close(2026, 6)


@freeze_time("2026-06-15")
def test_carry_forward_fold_sequential() -> None:
    _active_bill("100.00", date(2026, 5, 1))  # May net = -100
    _active_bill("50.00", date(2026, 6, 1))  # June net = -50
    may = CondoMonthCloseService.close(2026, 5)
    assert may.carry_forward_out == Decimal("-100.00")  # min(0, -100 + 0)
    june = CondoMonthCloseService.close(2026, 6)
    assert june.carry_forward_out == Decimal("-150.00")  # min(0, -50 + (-100))


@freeze_time("2026-06-15")
def test_fold_anchor_excludes_pre_tracking_month() -> None:
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 6, 1),
        rent_tracking_start_date=date(2026, 6, 1),
    )
    _active_bill("80.00", date(2026, 5, 1))  # pre-tracking month
    # June is the anchor; it can be closed without closing May first (May precedes the anchor).
    june = CondoMonthCloseService.close(2026, 6)
    assert june.carry_forward_out == Decimal("0.00")  # June net 0, May's -80 not folded in


@freeze_time("2026-06-15")
def test_closing_pre_tracking_month_does_not_leak_into_first_tracked_fold() -> None:
    """§18: a pre-tracking month CAN be closed (it precedes the anchor), but its net is ISOLATED —
    it freezes carry_forward_out=0.00 and never accumulates into the first tracked month's fold,
    so the frozen snapshot and OwnerDistributionService agree (§4.7)."""
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 5, 1),
        rent_tracking_start_date=date(2026, 6, 1),
    )
    _active_bill("80.00", date(2026, 5, 1))  # pre-tracking month → net -80
    _active_bill("50.00", date(2026, 6, 1))  # first tracked month → net -50

    may = CondoMonthCloseService.close(2026, 5)  # closing the pre-tracking month directly
    assert may.net_result == Decimal("-80.00")  # net is still SHOWN
    assert may.carry_forward_out == Decimal("0.00")  # but NOT folded forward (isolated)

    june = CondoMonthCloseService.close(2026, 6)
    # Only June's own -50 — NOT -130 (the pre-tracking -80 must not leak into the tracked fold).
    assert june.carry_forward_out == Decimal("-50.00")


@freeze_time("2026-06-15")
def test_reopen_recomputes_following_closed_months() -> None:
    _active_bill("100.00", date(2026, 4, 1))
    _active_bill("100.00", date(2026, 5, 1))
    _active_bill("100.00", date(2026, 6, 1))
    CondoMonthCloseService.close(2026, 4)
    may = CondoMonthCloseService.close(2026, 5)
    june = CondoMonthCloseService.close(2026, 6)
    assert may.carry_forward_out == Decimal("-200.00")  # -100 + (-100)
    assert june.carry_forward_out == Decimal("-300.00")  # -100 + (-200)

    reopened = CondoMonthCloseService.reopen(2026, 4)
    assert reopened.status == CondoMonthCloseStatus.OPEN
    may.refresh_from_db()
    june.refresh_from_db()
    # April no longer folds in → May/June carry recompute from the new baseline
    assert may.carry_forward_out == Decimal("-100.00")
    assert june.carry_forward_out == Decimal("-200.00")
    assert may.status == CondoMonthCloseStatus.CLOSED  # following months stay closed


@freeze_time("2026-06-15")
def test_close_in_the_middle_recomputes_following_carry_forward() -> None:
    """REGRESSÃO (P2.3 step 6): close M+1 first (gap-free anchor at M+1), then close M (earlier).
    M+1 must recompute its carried_in from M's new carry_forward_out — not keep its stale value."""
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 4, 1),
        rent_tracking_start_date=date(2026, 4, 1),
    )
    _active_bill("100.00", date(2026, 4, 1))  # April net -100
    _active_bill("100.00", date(2026, 5, 1))  # May net -100
    CondoMonthCloseService.close(2026, 4)
    may = CondoMonthCloseService.close(2026, 5)
    assert may.carry_forward_out == Decimal("-200.00")  # -100 + (-100)

    # Reopen April, then re-close it; closing April (with May still closed) must roll forward into
    # May so May's carry stays -200 (April -100 folded into May -100).
    CondoMonthCloseService.reopen(2026, 4)
    may.refresh_from_db()
    assert may.carry_forward_out == Decimal("-100.00")  # April no longer folded
    CondoMonthCloseService.close(2026, 4)  # close-in-the-middle (May already closed)
    may.refresh_from_db()
    assert may.carry_forward_out == Decimal("-200.00")  # recomputed forward from April


@freeze_time("2026-06-15")
def test_reopen_nonexistent_month_rejected() -> None:
    with pytest.raises(ValidationError):
        CondoMonthCloseService.reopen(2026, 6)


@freeze_time("2026-06-15")
def test_reserve_balance_end_freezes_only_movements_through_month_end() -> None:
    """REGRESSÃO (P2.3 step 7): a reserve deposit in M+1 must NOT inflate M's frozen
    reserve_balance_end (it freezes movements with movement_date < 1st of M+1, not all-time)."""
    condominium = make_condominium()
    reserve = make_reserve(condominium=condominium)
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("500.00"), movement_date=date(2026, 6, 10)
    )
    # A deposit in the NEXT month (July) — must be excluded from June's frozen figure.
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("300.00"), movement_date=date(2026, 7, 5)
    )

    june = CondoMonthCloseService.close(2026, 6)

    assert june.reserve_balance_end == Decimal("500.00")  # NOT 800 (July deposit excluded)


@freeze_time("2026-06-15")
def test_reserve_balance_as_of_filters_movement_date() -> None:
    condominium = make_condominium()
    reserve = make_reserve(condominium=condominium)
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("500.00"), movement_date=date(2026, 6, 10)
    )
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("300.00"), movement_date=date(2026, 7, 5)
    )
    # as_of=1st of July → only movements strictly before July count.
    assert CondoBalanceService.reserve_balance(condominium.id, as_of=date(2026, 7, 1)) == Decimal(
        "500.00"
    )
    # No as_of → all-time (dashboard) unchanged.
    assert CondoBalanceService.reserve_balance(condominium.id) == Decimal("800.00")


@freeze_time("2026-06-15")
def test_assert_open() -> None:
    make_condominium()
    CondoMonthCloseService.assert_open(date(2026, 6, 1))  # no close → no-op
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        CondoMonthCloseService.assert_open(date(2026, 6, 15))  # normalized to month → closed


@freeze_time("2026-06-15")
def test_pay_blocked_on_closed_month_and_unblocked_on_reopen() -> None:
    bill = _active_bill("200.00", date(2026, 6, 1))
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, date(2026, 6, 9), Decimal("200.00"), FundedFrom.CAIXA)
    CondoMonthCloseService.reopen(2026, 6)
    payment = BillPaymentService.pay(bill, date(2026, 6, 9), Decimal("200.00"), FundedFrom.CAIXA)
    assert payment.amount == Decimal("200.00")


@freeze_time("2026-01-15")
def test_close_january_handles_year_boundary() -> None:
    # _prev_month(January) crosses to December of the prior year (chronological guard path).
    make_condominium()
    close = CondoMonthCloseService.close(2026, 1)
    assert close.status == CondoMonthCloseStatus.CLOSED
    assert close.reference_month == date(2026, 1, 1)


@freeze_time("2026-06-15")
def test_close_has_no_off_by_cent_vs_on_read() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("0.00"), initial_balance_date=date(2026, 6, 1)
    )
    for _ in range(3):
        _paid_lease("333.33", date(2026, 6, 1))  # 999.99 received
    bill = _active_bill("100.00", date(2026, 6, 1))
    BillPaymentService.pay(bill, date(2026, 6, 7), Decimal("100.00"), FundedFrom.CAIXA)
    expected_cash = CondoBalanceService.cash_balance(date(2026, 7, 1))
    expected_net = CondoBalanceService.result_of_month(2026, 6)
    close = CondoMonthCloseService.close(2026, 6)
    assert close.cash_balance_end == expected_cash
    assert close.net_result == expected_net
