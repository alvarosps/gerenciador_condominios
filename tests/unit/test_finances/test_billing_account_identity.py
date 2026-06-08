"""Session 56 — BillingAccount account_type + identity model tests.

Enums (BillingAccountType/SupplyStatus), the 5 new fields + defaults, the partial
unique identity (building, account_type, external_identifier), and the clean() rule
rejecting a blank external_identifier for typed accounts (water/electricity/IPTU).
Real ORM + real constraints (IntegrityError asserted inside transaction.atomic()).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from finances.models import BillingAccount, BillingAccountType, SupplyStatus

from tests.factories import make_billing_account, make_building, make_condominium

pytestmark = pytest.mark.django_db


def test_account_type_defaults_to_generic_and_supply_status_to_active() -> None:
    account = make_billing_account()
    assert account.account_type == BillingAccountType.GENERIC
    assert account.supply_status == SupplyStatus.ACTIVE


def test_account_type_and_supply_status_choices() -> None:
    assert BillingAccountType.WATER.value == "water"
    assert BillingAccountType.WATER.label == "Água"
    assert BillingAccountType.ELECTRICITY.value == "electricity"
    assert BillingAccountType.ELECTRICITY.label == "Luz"
    assert BillingAccountType.IPTU.value == "iptu"
    assert BillingAccountType.IPTU.label == "IPTU"
    assert BillingAccountType.INTERNET.value == "internet"
    assert BillingAccountType.INTERNET.label == "Internet"
    assert BillingAccountType.GENERIC.value == "generic"
    assert BillingAccountType.GENERIC.label == "Genérica"
    assert set(BillingAccountType.values) == {
        "water",
        "electricity",
        "iptu",
        "internet",
        "generic",
    }
    assert SupplyStatus.ACTIVE.value == "active"
    assert SupplyStatus.ACTIVE.label == "Ligada"
    assert SupplyStatus.CUT.value == "cut"
    assert SupplyStatus.CUT.label == "Cortada"
    assert set(SupplyStatus.values) == {"active", "cut"}


def test_identity_fields_persist() -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier="650.847.010-16",
        holder_name="Maria das Dores",
        registered_address="Rua das Flores, 836",
        secondary_identifier="516481",
        supply_status=SupplyStatus.CUT,
    )
    account.refresh_from_db()
    assert account.holder_name == "Maria das Dores"
    assert account.registered_address == "Rua das Flores, 836"
    assert account.secondary_identifier == "516481"
    assert account.supply_status == SupplyStatus.CUT


def test_identity_fields_default_blank() -> None:
    account = make_billing_account()
    assert account.holder_name == ""
    assert account.registered_address == ""
    assert account.secondary_identifier == ""


def test_four_real_same_building_accounts_coexist() -> None:
    """Appendix B Phase 1: 2 electricity at 836 + 2 IPTU at 850 — distinct identifiers insert."""
    condo = make_condominium()
    b836 = make_building(street_number=836, condominium=condo)
    b850 = make_building(street_number=850, condominium=condo)
    make_billing_account(
        condominium=condo,
        building=b836,
        account_type=BillingAccountType.ELECTRICITY,
        external_identifier="010798...-05",
    )
    make_billing_account(
        condominium=condo,
        building=b836,
        account_type=BillingAccountType.ELECTRICITY,
        external_identifier="650.847.010-16",
    )
    make_billing_account(
        condominium=condo,
        building=b850,
        account_type=BillingAccountType.IPTU,
        external_identifier="516481",
    )
    make_billing_account(
        condominium=condo,
        building=b850,
        account_type=BillingAccountType.IPTU,
        external_identifier="516503",
    )
    assert BillingAccount.objects.count() == 4


def test_duplicate_active_identity_rejected() -> None:
    condo = make_condominium()
    building = make_building(street_number=836, condominium=condo)
    make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-12345",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        make_billing_account(
            condominium=condo,
            building=building,
            account_type=BillingAccountType.WATER,
            external_identifier="UC-12345",
        )


def test_soft_deleted_identity_allows_recreate() -> None:
    condo = make_condominium()
    building = make_building(street_number=836, condominium=condo)
    first = make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-12345",
    )
    first.delete()  # soft delete frees the partial-unique slot
    recreated = make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-12345",
    )
    assert recreated.pk != first.pk
    assert BillingAccount.objects.filter(external_identifier="UC-12345").count() == 1


def test_different_account_type_same_identifier_same_building_ok() -> None:
    """account_type composes the key — same identifier under a different type coexists."""
    condo = make_condominium()
    building = make_building(street_number=836, condominium=condo)
    make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="SHARED-1",
    )
    make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.ELECTRICITY,
        external_identifier="SHARED-1",
    )
    assert BillingAccount.objects.filter(external_identifier="SHARED-1").count() == 2


def test_blank_external_identifier_rejected_for_water() -> None:
    account = make_billing_account(account_type=BillingAccountType.WATER, external_identifier="")
    with pytest.raises(ValidationError) as exc_info:
        account.clean()
    assert "external_identifier" in exc_info.value.message_dict
    assert "Informe a inscrição/UC" in exc_info.value.message_dict["external_identifier"][0]


@pytest.mark.parametrize("account_type", [BillingAccountType.ELECTRICITY, BillingAccountType.IPTU])
def test_blank_external_identifier_rejected_for_electricity_and_iptu(
    account_type: BillingAccountType,
) -> None:
    account = make_billing_account(account_type=account_type, external_identifier="   ")
    with pytest.raises(ValidationError) as exc_info:
        account.clean()
    assert "external_identifier" in exc_info.value.message_dict


@pytest.mark.parametrize("account_type", [BillingAccountType.GENERIC, BillingAccountType.INTERNET])
def test_blank_external_identifier_allowed_for_generic_and_internet(
    account_type: BillingAccountType,
) -> None:
    account = make_billing_account(account_type=account_type, external_identifier="")
    account.clean()  # must not raise


def test_clean_still_normalizes_tracking_start_month_and_rejects_negative_amount() -> None:
    account = make_billing_account(
        account_type=BillingAccountType.GENERIC, tracking_start_month=date(2026, 6, 17)
    )
    account.clean()
    assert account.tracking_start_month == date(2026, 6, 1)

    negative = make_billing_account(account_type=BillingAccountType.GENERIC)
    negative.expected_amount = Decimal("-1.00")
    with pytest.raises(ValidationError) as exc_info:
        negative.clean()
    assert "expected_amount" in exc_info.value.message_dict
