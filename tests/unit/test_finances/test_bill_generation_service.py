"""Session 37 — BillGenerationService tests (date generator, eligibility, idempotency, seed)."""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill, BillBehavior, BillingAccountState
from finances.services.bill_generation_service import BillGenerationService
from finances.services.timezone import today_sp
from freezegun import freeze_time

from tests.factories import make_bill_skip, make_billing_account, make_condominium

pytestmark = pytest.mark.django_db


def test_due_date_for_clamps() -> None:
    feb = make_billing_account(default_due_day=31)
    assert BillGenerationService._due_date_for(feb, 2026, 2) == date(2026, 2, 28)
    assert BillGenerationService._due_date_for(feb, 2024, 2) == date(2024, 2, 29)
    assert BillGenerationService._due_date_for(feb, 2026, 4) == date(2026, 4, 30)
    ten = make_billing_account(default_due_day=10)
    assert BillGenerationService._due_date_for(ten, 2026, 3) == date(2026, 3, 10)


def test_generates_recurring_bill_with_seed_line() -> None:
    account = make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
    bills = BillGenerationService.ensure_month_bills(2026, 6)
    assert len(bills) == 1
    bill = bills[0]
    assert bill.billing_account_id == account.id
    assert bill.competence_month == date(2026, 6, 1)
    assert bill.behavior == BillBehavior.RECURRING
    assert bill.due_date == date(2026, 6, 10)
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("600.00")


def test_generation_is_idempotent() -> None:
    account = make_billing_account(expected_amount=Decimal("600.00"))
    BillGenerationService.ensure_month_bills(2026, 6)
    BillGenerationService.ensure_month_bills(2026, 6)
    bills = Bill.all_objects.filter(billing_account=account, competence_month=date(2026, 6, 1))
    assert bills.count() == 1
    assert bills.get().line_items.count() == 1


def test_suspended_account_does_not_generate() -> None:
    make_billing_account(lifecycle_state=BillingAccountState.SUSPENDED)
    assert BillGenerationService.ensure_month_bills(2026, 6) == []


def test_bill_skip_blocks_then_hard_delete_unskips() -> None:
    account = make_billing_account(expected_amount=Decimal("100.00"))
    skip = make_bill_skip(billing_account=account, reference_month=date(2026, 6, 1))
    assert BillGenerationService.ensure_month_bills(2026, 6) == []
    skip.delete()  # hard delete (no soft-delete) un-skips
    bills = BillGenerationService.ensure_month_bills(2026, 6)
    assert len(bills) == 1


def test_end_date_cutoff() -> None:
    before = make_billing_account(end_date=date(2026, 5, 31))
    on = make_billing_account(end_date=date(2026, 6, 1))
    after = make_billing_account(end_date=date(2026, 7, 31))
    ids = {b.billing_account_id for b in BillGenerationService.ensure_month_bills(2026, 6)}
    assert before.id not in ids
    assert on.id in ids
    assert after.id in ids


def test_tracking_start_month_seed_and_cross_year() -> None:
    make_billing_account(tracking_start_month=date(2026, 7, 1))  # future start: not eligible
    assert BillGenerationService.ensure_month_bills(2026, 6) == []
    past = make_billing_account(tracking_start_month=date(2025, 11, 1))
    bills = BillGenerationService.ensure_month_bills(2026, 1)
    assert {b.billing_account_id for b in bills} == {past.id}


@freeze_time("2026-07-15 12:00:00")
def test_seed_bill_is_overdue_after_due_date() -> None:
    make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
    bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
    annotated = Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)
    assert annotated.is_overdue is True
    assert annotated.amount_remaining == Decimal("600.00")


def test_expected_amount_zero_generates_bill_without_line() -> None:
    make_billing_account(expected_amount=Decimal("0.00"))
    bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert bill.line_items.count() == 0
    assert annotated.amount_total == Decimal("0.00")
    assert annotated.payment_status == "open"
    assert annotated.is_overdue is False


def test_no_billing_accounts_returns_empty() -> None:
    make_condominium()  # a condominium without any billing account
    assert BillGenerationService.ensure_month_bills(2026, 6) == []


@freeze_time("2026-07-01 02:00:00")
def test_overdue_uses_sao_paulo_month_boundary() -> None:
    # UTC is already July 1; in São Paulo it is still June 30 23:00 — seed bill due June 10
    # is overdue under SP today as well, but today_sp() must be the SP date (June 30).
    make_billing_account(default_due_day=10, expected_amount=Decimal("100.00"))
    bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
    assert today_sp() == date(2026, 6, 30)
    annotated = Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)
    assert annotated.is_overdue is True
