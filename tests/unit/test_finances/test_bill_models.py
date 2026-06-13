"""Session 36 — model tests for the finances bill core.

Inheritance/managers, constraints, clean() (PT), partial-unique idempotency,
is_offset sign, BillSkip (no soft-delete).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from finances.models import Bill, BillSkip
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_bill_skip,
    make_billing_account,
    make_condominium,
    make_finance_category,
    make_payment,
    make_payment_allocation,
)

pytestmark = pytest.mark.django_db


def test_soft_delete_models_inherit_mixins() -> None:
    for obj in (
        make_finance_category(),
        make_billing_account(),
        make_bill(),
        make_bill_line_item(),
        make_payment(),
        make_payment_allocation(),
    ):
        assert obj.created_at is not None
        assert obj.updated_at is not None
        assert obj.is_deleted is False


def test_bill_skip_has_audit_but_no_soft_delete() -> None:
    skip = make_bill_skip()
    assert skip.created_at is not None
    assert not hasattr(skip, "is_deleted")
    # BillSkip uses a plain manager (no with_deleted)
    assert not hasattr(BillSkip.objects, "with_deleted")


def test_objects_excludes_soft_deleted_all_objects_includes() -> None:
    bill = make_bill()
    bill.delete()  # soft delete
    assert not Bill.objects.filter(pk=bill.pk).exists()
    assert Bill.objects.with_deleted().filter(pk=bill.pk).exists()
    assert Bill.all_objects.filter(pk=bill.pk).exists()


def test_top_models_have_condominium() -> None:
    cond = make_condominium()
    assert make_finance_category(condominium=cond).condominium_id == cond.id
    assert make_billing_account(condominium=cond).condominium_id == cond.id
    assert make_bill(condominium=cond).condominium_id == cond.id
    assert make_payment(condominium=cond).condominium_id == cond.id


def test_bill_line_item_amount_non_negative() -> None:
    bill = make_bill()
    # zero is allowed
    make_bill_line_item(bill=bill, amount=Decimal("0.00"))
    with pytest.raises(IntegrityError), transaction.atomic():
        make_bill_line_item(bill=bill, amount=Decimal("-1.00"))


def test_payment_amount_positive() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_payment(amount=Decimal("0.00"))


def test_payment_allocation_amount_positive() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_payment_allocation(amount=Decimal("0.00"))


def test_billing_account_expected_amount_non_negative() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_billing_account(expected_amount=Decimal("-1.00"))


def test_bill_partial_unique_idempotent_and_frees_on_soft_delete() -> None:
    account = make_billing_account()
    month = date(2026, 6, 1)
    first = make_bill(
        condominium=account.condominium, billing_account=account, competence_month=month
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        make_bill(condominium=account.condominium, billing_account=account, competence_month=month)
    first.delete()  # soft delete frees the slot
    second = make_bill(
        condominium=account.condominium, billing_account=account, competence_month=month
    )
    assert second.pk != first.pk


def test_bill_unique_does_not_apply_when_billing_account_null() -> None:
    cond = make_condominium()
    month = date(2026, 6, 1)
    make_bill(condominium=cond, billing_account=None, competence_month=month)
    # two avulsa bills with same competence_month do not collide
    make_bill(condominium=cond, billing_account=None, competence_month=month)


def test_category_partial_unique() -> None:
    cond = make_condominium()
    first = make_finance_category(condominium=cond, name="Água", parent=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_finance_category(condominium=cond, name="Água", parent=None)
    # same name under a different parent is fine
    parent = make_finance_category(condominium=cond, name="Utilidades")
    make_finance_category(condominium=cond, name="Água", parent=parent)
    # soft-delete frees the slot
    first.delete()
    make_finance_category(condominium=cond, name="Água", parent=None)


def test_bill_skip_unique_and_hard_delete_unskips() -> None:
    account = make_billing_account()
    month = date(2026, 6, 1)
    skip = make_bill_skip(billing_account=account, reference_month=month)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_bill_skip(billing_account=account, reference_month=month)
    skip.delete()  # hard delete (no soft-delete) un-skips
    assert not BillSkip.objects.filter(pk=skip.pk).exists()
    make_bill_skip(billing_account=account, reference_month=month)


def test_clean_normalizes_dates_to_first_day() -> None:
    bill = make_bill(competence_month=date(2026, 6, 15))
    bill.competence_month = date(2026, 6, 15)
    bill.full_clean()
    assert bill.competence_month == date(2026, 6, 1)

    account = make_billing_account(tracking_start_month=date(2026, 6, 1))
    account.tracking_start_month = date(2026, 6, 20)
    account.full_clean()
    assert account.tracking_start_month == date(2026, 6, 1)

    skip = make_bill_skip()
    skip.reference_month = date(2026, 6, 20)
    skip.full_clean()
    assert skip.reference_month == date(2026, 6, 1)


def test_clean_rejects_negative_values_pt() -> None:
    line = make_bill_line_item()
    line.amount = Decimal("-1.00")
    with pytest.raises(ValidationError):
        line.full_clean()
    payment = make_payment()
    payment.amount = Decimal("0.00")
    with pytest.raises(ValidationError):
        payment.full_clean()
    allocation = make_payment_allocation()
    allocation.amount = Decimal("-5.00")
    with pytest.raises(ValidationError):
        allocation.full_clean()
    account = make_billing_account()
    account.expected_amount = Decimal("-1.00")
    with pytest.raises(ValidationError):
        account.full_clean()


def test_str_smoke() -> None:
    assert str(make_finance_category(name="Carros"))
    assert str(make_billing_account(name="Luz"))
    assert "06/2026" in str(make_bill(competence_month=date(2026, 6, 1)))
    assert str(make_bill_line_item())
    assert str(make_payment())
    assert str(make_payment_allocation())
    assert str(make_bill_skip())


def test_category_str_with_parent() -> None:
    cond = make_condominium()
    parent = make_finance_category(condominium=cond, name="Pessoal")
    child = make_finance_category(condominium=cond, name="Camila", parent=parent)
    assert str(child) == "Pessoal > Camila"
