"""Session 67 — AccountStatementService.build (months / stats / plans)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from finances.models import BillingAccount
from finances.money import money_str
from finances.services.account_statement_service import AccountStatementService
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


class TestStatementMonths:
    def test_months_include_both_arms(self) -> None:
        account = make_billing_account(account_type="iptu", external_identifier="777")
        direct_bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=direct_bill, amount=Decimal("100.00"))

        plan = make_installment_plan(
            condominium=account.condominium, billing_account=account, embedded=False
        )
        installment = make_installment(plan=plan)
        standalone_bill = make_bill(
            condominium=account.condominium,
            billing_account=None,
            installment=installment,
            competence_month=date(2026, 8, 1),
        )
        make_bill_line_item(bill=standalone_bill, amount=Decimal("200.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        ids = {row["bill_id"] for row in result["months"]}
        assert direct_bill.id in ids
        assert standalone_bill.id in ids
        assert len(result["months"]) == 2

    def test_months_exclude_canceled_and_other_accounts(self) -> None:
        account = make_billing_account()
        other_account = make_billing_account(condominium=account.condominium, name="Outra conta")
        canceled = make_bill(
            condominium=account.condominium, billing_account=account, lifecycle_state="canceled"
        )
        make_bill_line_item(bill=canceled, amount=Decimal("50.00"))
        other = make_bill(condominium=account.condominium, billing_account=other_account)
        make_bill_line_item(bill=other, amount=Decimal("50.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        ids = {row["bill_id"] for row in result["months"]}
        assert canceled.id not in ids
        assert other.id not in ids

    def test_month_row_shape_and_money_strings(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("123.45"))

        result = AccountStatementService.build(account.pk, TODAY)

        row = result["months"][0]
        assert set(row.keys()) == {
            "bill_id",
            "competence_month",
            "due_date",
            "description",
            "amount_total",
            "amount_paid",
            "amount_remaining",
            "payment_status",
            "lifecycle_state",
            "amount_is_estimated",
            "paid_date",
        }
        assert row["amount_total"] == "123.45"
        assert row["amount_paid"] == "0.00"
        assert row["amount_remaining"] == "123.45"
        assert row["paid_date"] is None

    def test_months_ordered_most_recent_first(self) -> None:
        account = make_billing_account()
        earlier = make_bill(
            condominium=account.condominium,
            billing_account=account,
            competence_month=date(2026, 5, 1),
            due_date=date(2026, 5, 10),
        )
        make_bill_line_item(bill=earlier, amount=Decimal("10.00"))
        later = make_bill(
            condominium=account.condominium,
            billing_account=account,
            competence_month=date(2026, 6, 1),
            due_date=date(2026, 6, 10),
        )
        make_bill_line_item(bill=later, amount=Decimal("10.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        ids_in_order = [row["bill_id"] for row in result["months"]]
        assert ids_in_order.index(later.id) < ids_in_order.index(earlier.id)

    def test_paid_date_is_max_live_payment_date(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("300.00"))
        first_payment = make_payment(
            condominium=account.condominium, payment_date=date(2026, 6, 1), amount=Decimal(100)
        )
        make_payment_allocation(payment=first_payment, bill=bill, amount=Decimal(100))
        second_payment = make_payment(
            condominium=account.condominium, payment_date=date(2026, 6, 20), amount=Decimal(100)
        )
        make_payment_allocation(payment=second_payment, bill=bill, amount=Decimal(100))
        dead_payment = make_payment(
            condominium=account.condominium, payment_date=date(2026, 7, 1), amount=Decimal(100)
        )
        make_payment_allocation(payment=dead_payment, bill=bill, amount=Decimal(100))
        dead_payment.is_deleted = True
        dead_payment.save(update_fields=["is_deleted"])

        result = AccountStatementService.build(account.pk, TODAY)

        row = next(r for r in result["months"] if r["bill_id"] == bill.id)
        assert row["paid_date"] == date(2026, 6, 20)

    def test_paid_date_none_without_payment(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("10.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        row = next(r for r in result["months"] if r["bill_id"] == bill.id)
        assert row["paid_date"] is None


class TestStatementStats:
    def test_open_balance_matches_queryset_annotation(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("321.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        annotated = BillingAccount.objects.with_open_balance(TODAY).get(pk=account.pk)
        assert result["stats"]["open_balance"] == money_str(annotated.open_balance)
        assert result["stats"]["open_balance"] == "321.00"

    def test_open_bills_count(self) -> None:
        account = make_billing_account()
        open_bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=open_bill, amount=Decimal("50.00"))

        paid_bill = make_bill(
            condominium=account.condominium,
            billing_account=account,
            competence_month=date(2026, 8, 1),
        )
        make_bill_line_item(bill=paid_bill, amount=Decimal("50.00"))
        payment = make_payment(condominium=account.condominium, amount=Decimal("50.00"))
        make_payment_allocation(payment=payment, bill=paid_bill, amount=Decimal("50.00"))

        canceled_bill = make_bill(
            condominium=account.condominium,
            billing_account=account,
            lifecycle_state="canceled",
            competence_month=date(2026, 9, 1),
        )
        make_bill_line_item(bill=canceled_bill, amount=Decimal("50.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        assert result["stats"]["open_bills_count"] == 1

    def test_avg_delay_days_mean_of_last_12(self) -> None:
        """13 settled bills (due dates 30 days apart, most recent first): only the 12 most
        recent (due_date desc) enter the average. The oldest (excluded) is paid 100 days late —
        if wrongly included the average would spike far beyond the other 12 delays."""
        account = make_billing_account()
        for i in range(13):
            due_date = date(2026, 1, 10) + timedelta(days=30 * i)
            bill = make_bill(
                condominium=account.condominium,
                billing_account=account,
                competence_month=due_date.replace(day=1),
                due_date=due_date,
            )
            make_bill_line_item(bill=bill, amount=Decimal("100.00"))
            paid_date = date(2025, 10, 1) if i == 0 else due_date
            payment = make_payment(
                condominium=account.condominium, payment_date=paid_date, amount=Decimal("100.00")
            )
            make_payment_allocation(payment=payment, bill=bill, amount=Decimal("100.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        # The 12 most recent (i=1..12) are all paid exactly on time (delay=0); the excluded
        # oldest bill (i=0) was paid ~100 days EARLY — if wrongly included the average would be
        # sharply negative instead of 0.
        assert result["stats"]["avg_delay_days"] == 0

    def test_avg_delay_days_requires_fully_paid_and_positive_total(self) -> None:
        account = make_billing_account()
        partial_bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=partial_bill, amount=Decimal("100.00"))
        partial_payment = make_payment(condominium=account.condominium, amount=Decimal("50.00"))
        make_payment_allocation(payment=partial_payment, bill=partial_bill, amount=Decimal("50.00"))

        zero_total_bill = make_bill(
            condominium=account.condominium,
            billing_account=account,
            competence_month=date(2026, 8, 1),
        )
        make_bill_line_item(bill=zero_total_bill, amount=Decimal("50.00"), is_offset=False)
        make_bill_line_item(bill=zero_total_bill, amount=Decimal("50.00"), is_offset=True)

        result = AccountStatementService.build(account.pk, TODAY)

        assert result["stats"]["avg_delay_days"] is None

    def test_avg_delay_days_negative_when_paid_early(self) -> None:
        account = make_billing_account()
        bill = make_bill(
            condominium=account.condominium,
            billing_account=account,
            due_date=date(2026, 6, 20),
        )
        make_bill_line_item(bill=bill, amount=Decimal("100.00"))
        payment = make_payment(
            condominium=account.condominium,
            payment_date=date(2026, 6, 10),
            amount=Decimal("100.00"),
        )
        make_payment_allocation(payment=payment, bill=bill, amount=Decimal("100.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        assert result["stats"]["avg_delay_days"] == -10

    def test_avg_delay_days_null_without_settled_bills(self) -> None:
        account = make_billing_account()
        bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(bill=bill, amount=Decimal("100.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        assert result["stats"]["avg_delay_days"] is None


class TestStatementQueryCount:
    def test_months_section_query_count_stable_across_bill_count(self) -> None:
        """The months section is built from ONE annotated queryset (with_amounts +
        the paid_date subquery) — the query count of build() must NOT grow with the number of
        bills on the account (no per-bill query inside _month_row/_avg_delay_days)."""
        account = make_billing_account()
        for i in range(2):
            bill = make_bill(
                condominium=account.condominium,
                billing_account=account,
                competence_month=date(2026, i + 1, 1),
                due_date=date(2026, i + 1, 10),
            )
            make_bill_line_item(bill=bill, amount=Decimal("10.00"))
        with CaptureQueriesContext(connection) as ctx_two_bills:
            AccountStatementService.build(account.pk, TODAY)
        two_bill_queries = len(ctx_two_bills.captured_queries)

        for i in range(2, 8):
            bill = make_bill(
                condominium=account.condominium,
                billing_account=account,
                competence_month=date(2026, i + 1, 1),
                due_date=date(2026, i + 1, 10),
            )
            make_bill_line_item(bill=bill, amount=Decimal("10.00"))
        with CaptureQueriesContext(connection) as ctx_eight_bills:
            AccountStatementService.build(account.pk, TODAY)
        eight_bill_queries = len(ctx_eight_bills.captured_queries)

        assert eight_bill_queries == two_bill_queries


class TestStatementPlans:
    def test_plans_list_embedded_and_standalone_with_progress(self) -> None:
        account = make_billing_account(account_type="water", external_identifier="UC-1")
        embedded_plan = make_installment_plan(
            condominium=account.condominium,
            billing_account=account,
            embedded=True,
            installment_count=2,
        )
        embedded_inst_materialized = make_installment(plan=embedded_plan, number=1)
        make_installment(plan=embedded_plan, number=2)
        embedded_bill = make_bill(condominium=account.condominium, billing_account=account)
        make_bill_line_item(
            bill=embedded_bill, installment=embedded_inst_materialized, amount=Decimal("10.00")
        )

        standalone_plan = make_installment_plan(
            condominium=account.condominium,
            billing_account=account,
            embedded=False,
            installment_count=3,
        )
        standalone_inst_materialized = make_installment(plan=standalone_plan, number=1)
        make_installment(plan=standalone_plan, number=2)
        make_installment(plan=standalone_plan, number=3)
        make_bill(
            condominium=account.condominium,
            billing_account=None,
            installment=standalone_inst_materialized,
        )

        result = AccountStatementService.build(account.pk, TODAY)

        plans_by_id = {p["id"]: p for p in result["plans"]}
        assert plans_by_id[embedded_plan.id]["materialized_count"] == 1
        assert plans_by_id[embedded_plan.id]["installment_count"] == 2
        assert plans_by_id[embedded_plan.id]["embedded"] is True
        assert plans_by_id[standalone_plan.id]["materialized_count"] == 1
        assert plans_by_id[standalone_plan.id]["installment_count"] == 3
        assert plans_by_id[standalone_plan.id]["embedded"] is False

    def test_iptu_registry_account_statement_not_empty(self) -> None:
        account = make_billing_account(account_type="iptu", external_identifier="9988")
        plan = make_installment_plan(
            condominium=account.condominium,
            billing_account=account,
            embedded=False,
            installment_count=1,
        )
        installment = make_installment(plan=plan)
        bill = make_bill(
            condominium=account.condominium, billing_account=None, installment=installment
        )
        make_bill_line_item(bill=bill, amount=Decimal("999.00"))

        result = AccountStatementService.build(account.pk, TODAY)

        assert len(result["months"]) == 1
        assert result["stats"]["open_balance"] == "999.00"
        assert result["stats"]["open_bills_count"] == 1
        assert len(result["plans"]) == 1
