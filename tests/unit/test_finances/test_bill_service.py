"""Session 37 — BillService.create_with_lines tests (atomicity, offset, normalization)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from finances.models import Bill, BillBehavior
from finances.services.bill_service import BillDraft, BillService
from tests.factories import make_condominium

pytestmark = pytest.mark.django_db

User = get_user_model()


def _create(cond, lines, *, user=None, **draft_kwargs):
    draft_defaults = {
        "condominium": cond,
        "competence_month": date(2026, 6, 1),
        "due_date": date(2026, 6, 10),
        "description": "Conta avulsa",
        "behavior": BillBehavior.ONE_TIME,
    }
    draft_defaults.update(draft_kwargs)
    return BillService.create_with_lines(BillDraft(**draft_defaults), lines, user=user)


def test_create_with_two_lines_sums_total() -> None:
    cond = make_condominium()
    bill = _create(
        cond,
        [
            {"description": "Consumo", "amount": Decimal("600.00")},
            {"description": "Extra", "amount": Decimal("400.00")},
        ],
    )
    assert bill.line_items.count() == 2
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("1000.00")


def test_offset_line_is_subtracted() -> None:
    cond = make_condominium()
    bill = _create(
        cond,
        [
            {"description": "A", "amount": Decimal("600.00")},
            {"description": "B", "amount": Decimal("400.00")},
            {"description": "Desconto", "amount": Decimal("100.00"), "is_offset": True},
        ],
    )
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("900.00")


def test_negative_line_rolls_back_whole_bill() -> None:
    cond = make_condominium()
    before = Bill.all_objects.count()
    with pytest.raises(ValidationError):
        _create(
            cond,
            [
                {"description": "Ok", "amount": Decimal("100.00")},
                {"description": "Ruim", "amount": Decimal("-1.00")},
            ],
        )
    assert Bill.all_objects.count() == before


def test_competence_month_normalized_to_day_one() -> None:
    cond = make_condominium()
    bill = _create(cond, [], competence_month=date(2026, 6, 15))
    assert bill.competence_month == date(2026, 6, 1)


def test_one_time_bill_persists_identifier_and_notes() -> None:
    cond = make_condominium()
    bill = _create(
        cond,
        [{"description": "X", "amount": Decimal("50.00")}],
        external_identifier="NF-123",
        notes="obs",
    )
    bill.refresh_from_db()
    assert bill.billing_account_id is None
    assert bill.behavior == BillBehavior.ONE_TIME
    assert bill.external_identifier == "NF-123"
    assert bill.notes == "obs"


def test_empty_lines_allowed() -> None:
    cond = make_condominium()
    bill = _create(cond, [])
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("0.00")


def test_user_propagated_to_bill_and_lines() -> None:
    cond = make_condominium()
    user = User.objects.create(username="creator")
    bill = _create(cond, [{"description": "X", "amount": Decimal("50.00")}], user=user)
    assert bill.created_by_id == user.id
    assert bill.updated_by_id == user.id
    line = bill.line_items.first()
    assert line is not None
    assert line.created_by_id == user.id
