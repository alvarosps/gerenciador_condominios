"""Session 44 — model tests for CondoMonthClose (Phase 4).

AuditMixin WITHOUT SoftDelete; status open/closed; unique (condominium,
reference_month) with NO condition (hard delete frees the slot); carry_forward_out <= 0;
reference_month day-1 normalization; status=closed => closed_at required;
net/cash/reserve may be negative; breakdown JSON default {}.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from finances.models import CondoMonthClose

from tests.factories import make_condo_month_close, make_condominium

pytestmark = pytest.mark.django_db


def test_has_audit_but_no_soft_delete() -> None:
    close = make_condo_month_close()
    assert close.created_at is not None
    assert close.updated_at is not None
    assert not hasattr(close, "is_deleted")
    # plain manager — no SoftDeleteManager helpers
    assert not hasattr(CondoMonthClose.objects, "with_deleted")


def test_status_choices_and_default() -> None:
    assert CondoMonthClose().status == "open"  # field-level default
    valid = {choice[0] for choice in CondoMonthClose._meta.get_field("status").choices}
    assert valid == {"open", "closed"}


def test_unique_condo_month_no_condition_hard_delete_frees_slot() -> None:
    cond = make_condominium()
    month = date(2026, 6, 1)
    first = make_condo_month_close(condominium=cond, reference_month=month)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_condo_month_close(condominium=cond, reference_month=month)
    first.delete()  # hard delete (no soft-delete) frees the slot
    assert not CondoMonthClose.objects.filter(pk=first.pk).exists()
    make_condo_month_close(condominium=cond, reference_month=month)


def test_unique_allows_same_month_for_different_condominium() -> None:
    month = date(2026, 6, 1)
    make_condo_month_close(condominium=make_condominium(), reference_month=month)
    make_condo_month_close(condominium=make_condominium(), reference_month=month)


def test_reference_month_normalized_to_first_day() -> None:
    close = make_condo_month_close(reference_month=date(2026, 6, 1))
    close.reference_month = date(2026, 6, 15)
    close.full_clean()
    assert close.reference_month == date(2026, 6, 1)


def test_clean_tolerates_missing_reference_month() -> None:
    # reference_month is required; clean()'s guard must defer to field validation
    # (raise the required-field error) instead of crashing on None.replace(day=1).
    close = make_condo_month_close()
    close.reference_month = None
    with pytest.raises(ValidationError):
        close.full_clean()


def test_carry_forward_out_non_positive_constraint() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_condo_month_close(carry_forward_out=Decimal("50.00"))


def test_carry_forward_out_zero_and_negative_allowed() -> None:
    make_condo_month_close(carry_forward_out=Decimal("0.00"))
    make_condo_month_close(condominium=make_condominium(), carry_forward_out=Decimal("-100.00"))


def test_carry_forward_out_positive_clean_pt() -> None:
    close = make_condo_month_close()
    close.carry_forward_out = Decimal("10.00")
    with pytest.raises(ValidationError):
        close.full_clean()


def test_closed_status_requires_closed_at_clean_pt() -> None:
    close = make_condo_month_close(status="closed", closed_at=None)
    with pytest.raises(ValidationError):
        close.full_clean()
    # open without closed_at is fine
    open_close = make_condo_month_close(
        condominium=make_condominium(), status="open", closed_at=None
    )
    open_close.full_clean()
    # closed with closed_at is fine
    closed_ok = make_condo_month_close(
        condominium=make_condominium(), status="closed", closed_at=timezone.now()
    )
    closed_ok.full_clean()


def test_net_cash_reserve_allow_negative() -> None:
    close = make_condo_month_close(
        net_result=Decimal("-500.00"),
        cash_balance_end=Decimal("-100.00"),
        reserve_balance_end=Decimal("-50.00"),
    )
    close.refresh_from_db()
    assert close.net_result == Decimal("-500.00")
    assert close.cash_balance_end == Decimal("-100.00")
    assert close.reserve_balance_end == Decimal("-50.00")


def test_breakdown_json_default_empty_and_accepts_dict() -> None:
    assert CondoMonthClose().breakdown == {}  # field-level default
    close = make_condo_month_close(breakdown={"net": "100.00", "lines": [1, 2, 3]})
    close.refresh_from_db()
    assert close.breakdown["net"] == "100.00"
    assert close.breakdown["lines"] == [1, 2, 3]


def test_str_smoke() -> None:
    assert str(make_condo_month_close(reference_month=date(2026, 6, 1)))
