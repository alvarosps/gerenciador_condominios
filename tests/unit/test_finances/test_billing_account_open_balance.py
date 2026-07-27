"""Session 67 — BillingAccountQuerySet.with_open_balance (two-arm FK sum)."""

from datetime import date
from decimal import Decimal

import pytest

from finances.models import BillingAccount
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_installment,
    make_installment_plan,
    make_payment,
    make_payment_allocation,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

TODAY = date(2026, 7, 15)


def _open_balance(account: BillingAccount) -> Decimal:
    return BillingAccount.objects.with_open_balance(TODAY).get(pk=account.pk).open_balance


class TestWithOpenBalance:
    def test_open_balance_sums_direct_bills(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("150.00"))

        assert _open_balance(account) == Decimal("150.00")

    def test_open_balance_includes_installment_arm(self) -> None:
        """Standalone parcelas (installment->plan->billing_account, billing_account=None on the
        Bill itself) still count — the IPTU registry-only account must not zero out."""
        account = make_billing_account(account_type="iptu", external_identifier="123")
        plan = make_installment_plan(
            condominium=account.condominium, billing_account=account, embedded=False
        )
        installment = make_installment(plan=plan)
        bill = make_bill(
            condominium=account.condominium, billing_account=None, installment=installment
        )
        make_bill_line_item(bill=bill, amount=Decimal("200.00"))

        assert _open_balance(account) == Decimal("200.00")

    def test_open_balance_no_double_count_across_arms(self) -> None:
        """A bill that would match both arms (billing_account set AND installment->plan->same
        account) counts once — arm B excludes rows already covered by arm A."""
        account = make_billing_account()
        plan = make_installment_plan(condominium=account.condominium, billing_account=account)
        installment = make_installment(plan=plan)
        bill = make_bill(
            condominium=account.condominium, billing_account=account, installment=installment
        )
        make_bill_line_item(bill=bill, amount=Decimal("300.00"))

        assert _open_balance(account) == Decimal("300.00")

    def test_open_balance_partial_payment_counts_rest(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("500.00"))
        payment = make_payment(condominium=account.condominium, amount=Decimal("200.00"))
        make_payment_allocation(payment=payment, bill=bill, amount=Decimal("200.00"))

        assert _open_balance(account) == Decimal("300.00")

    def test_open_balance_excludes_canceled(self) -> None:
        account = make_billing_account()
        canceled = make_bill(
            condominium=account.condominium, billing_account=account, lifecycle_state="canceled"
        )
        make_bill_line_item(bill=canceled, amount=Decimal("400.00"))
        suspended = make_bill(
            condominium=account.condominium,
            billing_account=account,
            lifecycle_state="suspended",
            competence_month=date(2026, 8, 1),
        )
        make_bill_line_item(bill=suspended, amount=Decimal("100.00"))
        deferred = make_bill(
            condominium=account.condominium,
            billing_account=account,
            lifecycle_state="deferred",
            competence_month=date(2026, 9, 1),
        )
        make_bill_line_item(bill=deferred, amount=Decimal("50.00"))

        assert _open_balance(account) == Decimal("150.00")

    def test_open_balance_excludes_soft_deleted_bills(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("400.00"))
        bill.is_deleted = True
        bill.save(update_fields=["is_deleted"])

        assert _open_balance(account) == Decimal("0.00")

    def test_open_balance_ignores_dead_allocations_and_payments(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("500.00"))
        live_payment = make_payment(condominium=account.condominium, amount=Decimal("100.00"))
        make_payment_allocation(payment=live_payment, bill=bill, amount=Decimal("100.00"))

        dead_allocation_payment = make_payment(
            condominium=account.condominium, amount=Decimal("50.00")
        )
        dead_allocation = make_payment_allocation(
            payment=dead_allocation_payment, bill=bill, amount=Decimal("50.00")
        )
        dead_allocation.is_deleted = True
        dead_allocation.save(update_fields=["is_deleted"])

        dead_payment = make_payment(condominium=account.condominium, amount=Decimal("75.00"))
        make_payment_allocation(payment=dead_payment, bill=bill, amount=Decimal("75.00"))
        dead_payment.is_deleted = True
        dead_payment.save(update_fields=["is_deleted"])

        assert _open_balance(account) == Decimal("400.00")

    def test_open_balance_zero_without_bills(self) -> None:
        account = make_billing_account()

        assert _open_balance(account) == Decimal("0.00")

    def test_open_balance_scoped_per_account(self) -> None:
        account_a = make_billing_account(name="Conta A")
        account_b = make_billing_account(condominium=account_a.condominium, name="Conta B")
        bill_a = make_bill(condominium=account_a.condominium, billing_account=account_a)
        make_bill_line_item(bill=bill_a, amount=Decimal("111.00"))
        bill_b = make_bill(condominium=account_a.condominium, billing_account=account_b)
        make_bill_line_item(bill=bill_b, amount=Decimal("222.00"))

        assert _open_balance(account_a) == Decimal("111.00")
        assert _open_balance(account_b) == Decimal("222.00")
