"""Session 77 — Third-party payment models: FundedFrom.THIRD_PARTY, Payment.paid_by,
Bill.paid_by_person (orthogonal), Bill source-FK exclusivity and ThirdPartySettlement."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from finances.models import (
    ERR_BILL_MULTIPLE_SOURCES,
    ERR_PERSON_ONLY_THIRD_PARTY,
    ERR_THIRD_PARTY_NEEDS_PERSON,
    Bill,
    FundedFrom,
    Payment,
    ThirdPartySettlement,
)
from tests.factories import (
    make_bill,
    make_billing_account,
    make_condominium,
    make_employee,
    make_installment,
    make_payment,
    make_person,
)

pytestmark = pytest.mark.django_db

_SETTLEMENT_DATE = date(2026, 7, 1)


def make_settlement(**kwargs: Any) -> ThirdPartySettlement:
    defaults: dict[str, Any] = {
        "condominium": make_condominium(),
        "person": make_person(),
        "settlement_date": _SETTLEMENT_DATE,
        "amount": Decimal("100.00"),
    }
    defaults.update(kwargs)
    return ThirdPartySettlement.objects.create(**defaults)


# --- 1/2/3: Payment.funded_from x paid_by invariant ---------------------------------


def test_funded_from_has_third_party_choice() -> None:
    assert FundedFrom.THIRD_PARTY == "third_party"
    assert {c[0] for c in FundedFrom.choices} == {"caixa", "reserve", "third_party"}


def test_third_party_without_paid_by_is_invalid() -> None:
    payment = make_payment(funded_from=FundedFrom.CAIXA)
    payment.funded_from = FundedFrom.THIRD_PARTY
    payment.paid_by = None
    with pytest.raises(ValidationError) as exc:
        payment.clean()
    assert exc.value.message_dict["paid_by"] == [ERR_THIRD_PARTY_NEEDS_PERSON]


def test_caixa_with_paid_by_is_invalid() -> None:
    payment = make_payment(funded_from=FundedFrom.CAIXA, paid_by=make_person())
    with pytest.raises(ValidationError) as exc:
        payment.clean()
    assert exc.value.message_dict["paid_by"] == [ERR_PERSON_ONLY_THIRD_PARTY]


def test_third_party_with_paid_by_is_valid_and_round_trips_through_db() -> None:
    """Guards the max_length=10 -> 20 widening: "third_party" is 11 chars, so a column
    that was not widened raises `value too long for type character varying(10)`."""
    person = make_person()
    payment = make_payment(funded_from=FundedFrom.THIRD_PARTY, paid_by=person)
    payment.full_clean(exclude=["condominium"])

    reloaded = Payment.objects.get(pk=payment.pk)
    assert reloaded.funded_from == "third_party"
    assert reloaded.paid_by_id == person.pk


# --- 4/5/5b/5c: Bill source-FK exclusivity, paid_by_person orthogonal ---------------


def test_bill_with_two_real_sources_is_invalid() -> None:
    condominium = make_condominium()
    bill = make_bill(
        condominium=condominium,
        billing_account=make_billing_account(condominium=condominium),
        installment=make_installment(),
    )
    with pytest.raises(ValidationError) as exc:
        bill.clean()
    assert exc.value.message_dict["__all__"] == [ERR_BILL_MULTIPLE_SOURCES]


def test_bill_with_employee_and_billing_account_is_invalid() -> None:
    condominium = make_condominium()
    bill = make_bill(
        condominium=condominium,
        billing_account=make_billing_account(condominium=condominium),
        employee=make_employee(condominium=condominium),
    )
    with pytest.raises(ValidationError):
        bill.clean()


def test_bill_with_single_source_or_none_is_valid() -> None:
    condominium = make_condominium()
    make_bill(
        condominium=condominium, billing_account=make_billing_account(condominium=condominium)
    ).clean()
    make_bill(condominium=condominium, installment=make_installment()).clean()
    make_bill(condominium=condominium, employee=make_employee(condominium=condominium)).clean()
    make_bill(condominium=condominium).clean()  # avulsa


def test_bill_with_installment_and_paid_by_person_is_valid() -> None:
    """Compra parcelada de terceiro — paid_by_person is orthogonal, never a source FK."""
    bill = make_bill(installment=make_installment(), paid_by_person=make_person())
    bill.clean()


def test_bill_with_billing_account_and_paid_by_person_is_valid() -> None:
    """Terceiro pagou a conta de água."""
    condominium = make_condominium()
    bill = make_bill(
        condominium=condominium,
        billing_account=make_billing_account(condominium=condominium),
        paid_by_person=make_person(),
    )
    bill.clean()


def test_bill_paid_by_person_round_trips_and_has_related_name() -> None:
    person = make_person()
    bill = make_bill(paid_by_person=person)
    assert Bill.objects.get(pk=bill.pk).paid_by_person_id == person.pk
    assert list(person.finance_bills_purchased.all()) == [bill]


# --- 6/7/8: ThirdPartySettlement ---------------------------------------------------


def test_settlement_amount_must_be_positive() -> None:
    settlement = ThirdPartySettlement(
        condominium=make_condominium(),
        person=make_person(),
        settlement_date=_SETTLEMENT_DATE,
        amount=Decimal("0.00"),
    )
    with pytest.raises(ValidationError) as exc:
        settlement.clean()
    assert "amount" in exc.value.message_dict

    settlement.amount = Decimal("150.00")
    settlement.clean()  # valid


def test_settlement_amount_check_constraint_at_db_level() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        ThirdPartySettlement.objects.create(
            condominium=make_condominium(),
            person=make_person(),
            settlement_date=_SETTLEMENT_DATE,
            amount=Decimal("-1.00"),
        )


def test_settlement_soft_delete_hides_from_objects_but_not_all_objects() -> None:
    settlement = make_settlement()
    settlement.delete()
    assert ThirdPartySettlement.objects.filter(pk=settlement.pk).count() == 0
    assert ThirdPartySettlement.all_objects.filter(pk=settlement.pk).count() == 1


def test_settlement_has_audit_fields_and_portuguese_str() -> None:
    settlement = make_settlement(amount=Decimal("250.00"))
    assert settlement.created_at is not None
    assert "Acerto" in str(settlement)
    assert settlement.person.name in str(settlement)


def test_deleting_person_with_settlement_is_protected() -> None:
    settlement = make_settlement()
    with pytest.raises(ProtectedError), transaction.atomic():
        settlement.person.delete(hard_delete=True)


def test_deleting_person_with_third_party_payment_is_protected() -> None:
    person = make_person()
    make_payment(funded_from=FundedFrom.THIRD_PARTY, paid_by=person)
    with pytest.raises(ProtectedError), transaction.atomic():
        person.delete(hard_delete=True)


def test_deleting_person_with_purchased_bill_is_protected() -> None:
    person = make_person()
    make_bill(paid_by_person=person)
    with pytest.raises(ProtectedError), transaction.atomic():
        person.delete(hard_delete=True)
