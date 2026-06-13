"""P2.3 — assert_open coverage on every finances write path that mutates a closed month.

The closed-month guard (CondoMonthCloseService.assert_open) previously only covered
pay/unpay/update_with_lines. A closed CondoMonthClose freezes the month's net/cash/reserve, so
ANY later mutation of that month (create/delete a bill, change its lifecycle state, deposit/
withdraw reserve, add income) would silently drift the frozen snapshot. These tests prove each
path now rejects (PT 400) while the open month stays fully writable. freezegun + real ORM only.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from finances.models import BillLifecycleState, Reserve
from finances.services.bill_lifecycle_service import BillLifecycleService
from finances.services.bill_service import BillDraft, BillService
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.reserve_service import ReserveService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_condominium,
    make_reserve,
    make_reserve_movement,
)

pytestmark = pytest.mark.django_db

CLOSED_MONTH = date(2026, 6, 1)
OPEN_MONTH = date(2026, 7, 1)


def _draft(condominium, competence_month: date) -> BillDraft:
    return BillDraft(
        condominium=condominium,
        competence_month=competence_month,
        due_date=competence_month.replace(day=10),
        description="Conta Teste",
        behavior="one_time",
    )


@freeze_time("2026-07-15")
def test_create_with_lines_rejected_on_closed_month() -> None:
    condominium = make_condominium()
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        BillService.create_with_lines(
            _draft(condominium, CLOSED_MONTH),
            [{"description": "X", "amount": Decimal("50.00")}],
        )


@freeze_time("2026-07-15")
def test_create_with_lines_ok_on_open_month() -> None:
    condominium = make_condominium()
    CondoMonthCloseService.close(2026, 6)
    bill = BillService.create_with_lines(
        _draft(condominium, OPEN_MONTH),
        [{"description": "X", "amount": Decimal("50.00")}],
    )
    assert bill.competence_month == OPEN_MONTH


@freeze_time("2026-07-15")
def test_delete_rejected_on_closed_month() -> None:
    make_condominium()
    bill = make_bill(competence_month=CLOSED_MONTH)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        BillService.delete(bill)


@freeze_time("2026-07-15")
def test_set_state_rejected_on_closed_month() -> None:
    make_condominium()
    bill = make_bill(competence_month=CLOSED_MONTH, lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        BillLifecycleService.set_state(bill, BillLifecycleState.SUSPENDED)


@freeze_time("2026-07-15")
def test_reactivate_rejected_on_closed_month() -> None:
    make_condominium()
    bill = make_bill(competence_month=CLOSED_MONTH, lifecycle_state=BillLifecycleState.SUSPENDED)
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        BillLifecycleService.reactivate(bill)


@freeze_time("2026-07-15")
def test_set_state_ok_on_open_month() -> None:
    make_condominium()
    bill = make_bill(competence_month=OPEN_MONTH, lifecycle_state=BillLifecycleState.ACTIVE)
    CondoMonthCloseService.close(2026, 6)  # a DIFFERENT month is closed
    BillLifecycleService.set_state(bill, BillLifecycleState.SUSPENDED)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.SUSPENDED


def _reserve_with_balance(condominium, balance: str) -> Reserve:
    reserve = make_reserve(condominium=condominium)
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal(balance), movement_date=OPEN_MONTH
    )
    return reserve


@freeze_time("2026-07-15")
def test_reserve_deposit_rejected_on_closed_month() -> None:
    condominium = make_condominium()
    reserve = make_reserve(condominium=condominium)
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        ReserveService.deposit(reserve, Decimal("100.00"), date(2026, 6, 20))


@freeze_time("2026-07-15")
def test_reserve_withdraw_rejected_on_closed_month() -> None:
    condominium = make_condominium()
    reserve = _reserve_with_balance(condominium, "500.00")
    CondoMonthCloseService.close(2026, 6)
    with pytest.raises(ValidationError):
        ReserveService.withdraw(reserve, Decimal("100.00"), date(2026, 6, 20))


@freeze_time("2026-07-15")
def test_reserve_deposit_ok_on_open_month() -> None:
    condominium = make_condominium()
    reserve = make_reserve(condominium=condominium)
    CondoMonthCloseService.close(2026, 6)
    movement = ReserveService.deposit(reserve, Decimal("100.00"), date(2026, 7, 20))
    assert movement.amount == Decimal("100.00")
