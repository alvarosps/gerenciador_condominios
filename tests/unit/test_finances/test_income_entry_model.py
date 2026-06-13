"""Session 44 — model tests for IncomeEntry (Phase 4).

Inheritance/managers, amount > 0 (CheckConstraint + clean PT), building/category
SET_NULL, is_received <-> received_date consistency (clean PT, both directions),
ordering (most recent first), soft-delete.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from finances.models import IncomeEntry
from tests.factories import (
    make_building,
    make_condominium,
    make_finance_category,
    make_income_entry,
)

pytestmark = pytest.mark.django_db


def test_income_entry_inherits_mixins() -> None:
    entry = make_income_entry()
    assert entry.created_at is not None
    assert entry.updated_at is not None
    assert entry.is_deleted is False


def test_objects_excludes_soft_deleted_all_objects_includes() -> None:
    entry = make_income_entry()
    entry.delete()  # soft delete
    assert not IncomeEntry.objects.filter(pk=entry.pk).exists()
    assert IncomeEntry.objects.with_deleted().filter(pk=entry.pk).exists()
    assert IncomeEntry.all_objects.filter(pk=entry.pk).exists()


def test_income_entry_has_condominium() -> None:
    cond = make_condominium()
    assert make_income_entry(condominium=cond).condominium_id == cond.id


def test_building_and_category_set_null_on_hard_delete() -> None:
    cond = make_condominium()
    building = make_building(condominium=cond)
    category = make_finance_category(condominium=cond)
    entry = make_income_entry(condominium=cond, building=building, category=category)
    building.delete(hard_delete=True)
    category.delete(hard_delete=True)
    entry.refresh_from_db()
    assert entry.building_id is None
    assert entry.category_id is None
    assert IncomeEntry.objects.filter(pk=entry.pk).exists()  # the income survives


def test_amount_positive_constraint() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_income_entry(amount=Decimal("0.00"))
    with pytest.raises(IntegrityError), transaction.atomic():
        make_income_entry(amount=Decimal("-1.00"))


def test_amount_positive_clean_pt() -> None:
    entry = make_income_entry()
    entry.amount = Decimal("0.00")
    with pytest.raises(ValidationError):
        entry.full_clean()


def test_is_received_received_date_consistency_clean_pt() -> None:
    cond = make_condominium()
    # received but no received_date -> invalid
    received_without_date = make_income_entry(
        condominium=cond, is_received=True, received_date=None
    )
    with pytest.raises(ValidationError):
        received_without_date.full_clean()
    # not received but received_date set -> invalid
    not_received_with_date = make_income_entry(
        condominium=cond, is_received=False, received_date=date(2026, 6, 10)
    )
    with pytest.raises(ValidationError):
        not_received_with_date.full_clean()
    # received with received_date -> ok
    received_ok = make_income_entry(
        condominium=cond, is_received=True, received_date=date(2026, 6, 10)
    )
    received_ok.full_clean()
    # not received without received_date -> ok
    pending_ok = make_income_entry(condominium=cond, is_received=False, received_date=None)
    pending_ok.full_clean()


def test_ordering_most_recent_first() -> None:
    cond = make_condominium()
    older = make_income_entry(condominium=cond, income_date=date(2026, 6, 1))
    newer = make_income_entry(condominium=cond, income_date=date(2026, 6, 20))
    assert list(IncomeEntry.objects.filter(condominium=cond)) == [newer, older]


def test_str_smoke() -> None:
    assert str(make_income_entry(description="Proventos de empréstimo"))
