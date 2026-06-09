"""BillSerializer.account_type — the derived structural type used by the Contas "Tipo" column.

Resolution chain (serializers.py get_account_type): the bill's own billing_account, else the IPTU
account reached via installment→plan→billing_account (standalone parcela bills have
billing_account=None), else generic for an avulsa bill. ORM is real (no internal mocks).
"""

import pytest
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    Installment,
    InstallmentPlan,
)
from finances.serializers import BillSerializer
from model_bakery import baker

pytestmark = pytest.mark.django_db


def test_account_type_comes_from_the_bills_own_billing_account() -> None:
    account: BillingAccount = baker.make(
        BillingAccount, account_type=BillingAccountType.WATER, is_deleted=False
    )
    bill: Bill = baker.make(Bill, billing_account=account, installment=None, is_deleted=False)
    assert BillSerializer(bill).data["account_type"] == "water"


def test_account_type_falls_back_to_installment_plan_account_for_iptu_parcela() -> None:
    account: BillingAccount = baker.make(
        BillingAccount, account_type=BillingAccountType.IPTU, is_deleted=False
    )
    plan: InstallmentPlan = baker.make(
        InstallmentPlan, billing_account=account, embedded=False, is_deleted=False
    )
    installment: Installment = baker.make(Installment, plan=plan, is_deleted=False)
    bill: Bill = baker.make(Bill, billing_account=None, installment=installment, is_deleted=False)
    assert BillSerializer(bill).data["account_type"] == "iptu"


def test_account_type_is_generic_when_bill_has_neither_account_nor_installment() -> None:
    bill: Bill = baker.make(Bill, billing_account=None, installment=None, is_deleted=False)
    assert BillSerializer(bill).data["account_type"] == "generic"
