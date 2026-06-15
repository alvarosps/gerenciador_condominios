"""Session 44 — model tests for Reserve / ReserveMovement (Phase 4).

Inheritance/managers, kind choices, amount > 0 (CheckConstraint + clean PT),
bill optional (caixa vs conta) + SET_NULL, deterministic ledger ordering, soft-delete.

The "withdrawal <= reserve balance" guard is a SERVICE concern (S45,
CondoBalanceService / ReserveService.withdraw) — it is NOT modeled or tested here
(design §4.3 + pinned decision). This file only locks sign/positivity and ledger order.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from finances.models import Reserve, ReserveMovement
from tests.factories import (
    make_bill,
    make_condominium,
    make_reserve,
    make_reserve_movement,
)

pytestmark = pytest.mark.django_db


def test_reserve_and_movement_inherit_mixins() -> None:
    reserve = make_reserve()
    movement = make_reserve_movement(reserve=reserve)
    for obj in (reserve, movement):
        assert obj.created_at is not None
        assert obj.updated_at is not None
        assert obj.is_deleted is False


def test_objects_excludes_soft_deleted_all_objects_includes() -> None:
    reserve = make_reserve()
    movement = make_reserve_movement(reserve=reserve)
    movement.delete()  # soft delete
    assert not ReserveMovement.objects.filter(pk=movement.pk).exists()
    assert ReserveMovement.objects.with_deleted().filter(pk=movement.pk).exists()
    assert ReserveMovement.all_objects.filter(pk=movement.pk).exists()
    reserve.delete()  # soft delete follows the mixin
    assert not Reserve.objects.filter(pk=reserve.pk).exists()
    assert Reserve.objects.with_deleted().filter(pk=reserve.pk).exists()
    assert Reserve.all_objects.filter(pk=reserve.pk).exists()


def test_reserve_has_condominium() -> None:
    cond = make_condominium()
    assert make_reserve(condominium=cond).condominium_id == cond.id


def test_movement_reserve_cascade_on_hard_delete() -> None:
    reserve = make_reserve()
    movement = make_reserve_movement(reserve=reserve)
    reserve.delete(hard_delete=True)
    assert not ReserveMovement.all_objects.filter(pk=movement.pk).exists()


def test_movement_kind_choices_required() -> None:
    field = ReserveMovement._meta.get_field("kind")
    assert {choice[0] for choice in (field.choices or [])} == {"deposit", "withdrawal"}
    assert not field.has_default()
    reserve = make_reserve()
    assert make_reserve_movement(reserve=reserve, kind="deposit").kind == "deposit"
    assert make_reserve_movement(reserve=reserve, kind="withdrawal").kind == "withdrawal"


def test_movement_amount_positive_constraint() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_reserve_movement(amount=Decimal("0.00"))
    with pytest.raises(IntegrityError), transaction.atomic():
        make_reserve_movement(amount=Decimal("-5.00"))


def test_movement_amount_positive_clean_pt() -> None:
    movement = make_reserve_movement()
    movement.full_clean()  # valid (positive) amount passes clean
    movement.amount = Decimal("0.00")
    with pytest.raises(ValidationError):
        movement.full_clean()
    movement.amount = Decimal("-1.00")
    with pytest.raises(ValidationError):
        movement.full_clean()


def test_movement_bill_optional_caixa_vs_conta() -> None:
    reserve = make_reserve()
    bill = make_bill(condominium=reserve.condominium)
    to_account = make_reserve_movement(reserve=reserve, kind="withdrawal", bill=bill)
    transfer = make_reserve_movement(reserve=reserve, kind="withdrawal", bill=None)
    assert to_account.bill_id == bill.pk  # withdrawal to pay a bill
    assert transfer.bill_id is None  # cash <-> reserve transfer


def test_movement_bill_set_null_on_hard_delete_persists_on_soft_delete() -> None:
    reserve = make_reserve()
    bill = make_bill(condominium=reserve.condominium)
    movement = make_reserve_movement(reserve=reserve, kind="withdrawal", bill=bill)
    bill.delete()  # soft delete does NOT trigger SET_NULL — the FK keeps pointing
    movement.refresh_from_db()
    assert movement.bill_id is not None
    bill.delete(hard_delete=True)  # hard delete frees the FK (SET_NULL)
    movement.refresh_from_db()
    assert movement.bill_id is None  # the ledger movement survives the bill
    assert ReserveMovement.objects.filter(pk=movement.pk).exists()


def test_ledger_deterministic_ordering() -> None:
    reserve = make_reserve()
    # Inserted out of date order; two share the same movement_date (tie broken by id).
    m_late = make_reserve_movement(reserve=reserve, movement_date=date(2026, 6, 20))
    m_same_1 = make_reserve_movement(reserve=reserve, movement_date=date(2026, 6, 10))
    m_same_2 = make_reserve_movement(reserve=reserve, movement_date=date(2026, 6, 10))
    m_early = make_reserve_movement(reserve=reserve, movement_date=date(2026, 6, 1))
    expected = [m_early.pk, m_same_1.pk, m_same_2.pk, m_late.pk]
    assert [m.pk for m in reserve.movements.all()] == expected
    assert [m.pk for m in ReserveMovement.objects.filter(reserve=reserve)] == expected


def test_str_smoke() -> None:
    assert str(make_reserve(name="Poupança"))
    assert str(make_reserve_movement())
