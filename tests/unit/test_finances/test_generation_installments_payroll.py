"""Session 41 — ensure_month_bills extension: installments (standalone/embedded) + payroll."""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill, BillBehavior, BillingAccountState, InstallmentPlanState
from finances.services.bill_generation_service import BillGenerationService
from freezegun import freeze_time

from core.services.rent_schedule_service import RentScheduleService
from tests.factories import (
    make_bill_skip,
    make_billing_account,
    make_employee,
    make_installment,
    make_installment_plan,
    make_lease,
)

pytestmark = pytest.mark.django_db

_NEXT_MONTH = date(2026, 7, 1)


# --- standalone installments ---


def test_standalone_installment_generates_own_bill_idempotent() -> None:
    plan = make_installment_plan(embedded=False, installment_count=1, description="Notebook")
    inst = make_installment(
        plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00")
    )
    BillGenerationService.ensure_month_bills(2026, 6)
    BillGenerationService.ensure_month_bills(2026, 6)  # idempotent re-run

    bills = Bill.all_objects.filter(installment=inst)
    assert bills.count() == 1
    bill = bills.get()
    assert bill.behavior == BillBehavior.INSTALLMENT
    assert bill.line_items.count() == 1
    annotated = Bill.objects.with_amounts(_NEXT_MONTH).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("400.00")


def test_installment_outside_month_is_not_generated() -> None:
    plan = make_installment_plan(embedded=False, installment_count=1)
    inst = make_installment(
        plan=plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("400.00")
    )
    BillGenerationService.ensure_month_bills(2026, 6)
    assert Bill.all_objects.filter(installment=inst).count() == 0


# --- embedded installments + dedup ---


def test_embedded_installment_becomes_line_no_own_bill() -> None:
    account = make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
    plan = make_installment_plan(
        condominium=account.condominium,
        embedded=True,
        billing_account=account,
        installment_count=1,
        description="TV parcelada",
    )
    inst = make_installment(
        plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00")
    )

    BillGenerationService.ensure_month_bills(2026, 6)  # single pass: recurring before embedded

    account_bills = Bill.all_objects.filter(
        billing_account=account, competence_month=date(2026, 6, 1)
    )
    assert account_bills.count() == 1
    bill = account_bills.get()
    assert bill.line_items.count() == 2  # consumo 600 + parcela 400
    assert Bill.all_objects.filter(installment=inst).count() == 0  # never its own bill
    annotated = Bill.objects.with_amounts(_NEXT_MONTH).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("1000.00")  # 600 + 400


def test_embedded_installment_dedup_on_rerun() -> None:
    account = make_billing_account(expected_amount=Decimal("600.00"))
    plan = make_installment_plan(
        condominium=account.condominium,
        embedded=True,
        billing_account=account,
        installment_count=2,
    )
    make_installment(plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00"))
    make_installment(plan=plan, number=2, due_date=date(2026, 7, 10), amount=Decimal("400.00"))

    BillGenerationService.ensure_month_bills(2026, 6)
    BillGenerationService.ensure_month_bills(2026, 6)  # re-run does not duplicate the parcela line

    bill = Bill.all_objects.get(billing_account=account, competence_month=date(2026, 6, 1))
    assert bill.line_items.count() == 2  # consumo + 1 parcela (june only)


def _embedded_plan_on(account: object) -> object:
    plan = make_installment_plan(
        condominium=account.condominium,
        embedded=True,
        billing_account=account,
        installment_count=1,
        description="TV parcelada",
    )
    make_installment(plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00"))
    return plan


def test_embedded_installment_skipped_when_account_suspended() -> None:
    """A dormant host account materializes neither consumo nor the embedded parcela (§7/§8/§18)."""
    account = make_billing_account(
        expected_amount=Decimal("600.00"), lifecycle_state=BillingAccountState.SUSPENDED
    )
    _embedded_plan_on(account)

    BillGenerationService.ensure_month_bills(2026, 6)

    assert Bill.all_objects.filter(billing_account=account).count() == 0


def test_embedded_installment_skipped_when_account_skipped_for_month() -> None:
    account = make_billing_account(expected_amount=Decimal("600.00"))
    make_bill_skip(billing_account=account, reference_month=date(2026, 6, 1))
    _embedded_plan_on(account)

    BillGenerationService.ensure_month_bills(2026, 6)

    assert Bill.all_objects.filter(billing_account=account).count() == 0


def test_embedded_installment_skipped_when_account_ended() -> None:
    account = make_billing_account(expected_amount=Decimal("600.00"), end_date=date(2026, 5, 31))
    _embedded_plan_on(account)

    BillGenerationService.ensure_month_bills(2026, 6)

    assert Bill.all_objects.filter(billing_account=account).count() == 0


# --- sync schedule -> realized ---


def test_materialization_copies_schedule_and_realized_edit_keeps_schedule() -> None:
    plan = make_installment_plan(embedded=False, installment_count=1)
    inst = make_installment(
        plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00")
    )
    BillGenerationService.ensure_month_bills(2026, 6)

    bill = Bill.all_objects.get(installment=inst)
    line = bill.line_items.get()
    assert line.amount == Decimal("400.00")  # schedule -> realized copy

    line.amount = Decimal("420.00")
    line.save()
    inst.refresh_from_db()
    assert inst.amount == Decimal("400.00")  # schedule preserved (no realized -> schedule sync)


# --- last installment -> plan paid ---


def test_last_installment_materialized_marks_plan_paid() -> None:
    plan = make_installment_plan(embedded=False, installment_count=2)
    make_installment(plan=plan, number=1, due_date=date(2026, 1, 10), amount=Decimal("50.00"))
    make_installment(plan=plan, number=2, due_date=date(2026, 2, 10), amount=Decimal("50.00"))

    BillGenerationService.ensure_month_bills(2026, 1)  # intermediate month
    plan.refresh_from_db()
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE

    BillGenerationService.ensure_month_bills(2026, 2)  # last installment materialized
    plan.refresh_from_db()
    assert plan.lifecycle_state == InstallmentPlanState.PAID


# --- payroll ---


@freeze_time("2026-06-15")
def test_payroll_mixed_with_salary_offset_lease() -> None:
    lease = make_lease(is_salary_offset=True, rental_value=Decimal("1000.00"))
    emp = make_employee(
        payment_type="mixed", base_salary=Decimal("2000.00"), lease=lease, default_due_day=5
    )
    BillGenerationService.ensure_month_bills(2026, 6)

    bill = Bill.all_objects.get(employee=emp, competence_month=date(2026, 6, 1))
    assert bill.behavior == BillBehavior.RECURRING
    assert bill.due_date == date(2026, 6, 5)
    base = bill.line_items.filter(is_offset=False)
    offset = bill.line_items.filter(is_offset=True)
    assert base.count() == 1
    assert base.get().amount == Decimal("2000.00")
    assert offset.count() == 1
    assert offset.get().amount == Decimal("1000.00")
    annotated = Bill.objects.with_amounts(_NEXT_MONTH).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("1000.00")  # 2000 base - 1000 offset (paid to Rosa)

    # The salary-offset lease is counted once: it is NOT in collectible_leases (not income).
    collectible = RentScheduleService.collectible_leases(date(2026, 6, 1))
    assert lease.pk not in {lease_obj.pk for lease_obj in collectible}


@freeze_time("2026-06-15")
def test_payroll_offset_equals_effective_rental_value_with_pending() -> None:
    lease = make_lease(
        is_salary_offset=True,
        rental_value=Decimal("1000.00"),
        pending_rental_value=Decimal("1100.00"),
        pending_rental_value_date=date(2026, 6, 1),
    )
    emp = make_employee(payment_type="mixed", base_salary=Decimal("2000.00"), lease=lease)
    BillGenerationService.ensure_month_bills(2026, 6)

    bill = Bill.all_objects.get(employee=emp, competence_month=date(2026, 6, 1))
    offset = bill.line_items.get(is_offset=True)
    expected = RentScheduleService.effective_rental_value(lease, date(2026, 6, 1))
    assert offset.amount == expected == Decimal("1100.00")


@freeze_time("2026-06-15")
def test_payroll_variable_only_has_no_lines() -> None:
    emp = make_employee(payment_type="variable", base_salary=None, lease=None, default_due_day=5)
    BillGenerationService.ensure_month_bills(2026, 6)

    bill = Bill.all_objects.get(employee=emp, competence_month=date(2026, 6, 1))
    assert bill.line_items.count() == 0
    annotated = Bill.objects.with_amounts(_NEXT_MONTH).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("0.00")
    assert annotated.payment_status == "open"


@freeze_time("2026-07-15")
def test_payroll_offset_stops_when_lease_soft_deleted() -> None:
    lease = make_lease(is_salary_offset=True, rental_value=Decimal("1000.00"))
    emp = make_employee(payment_type="mixed", base_salary=Decimal("2000.00"), lease=lease)
    lease.delete()  # soft delete: FK stays, is_deleted=True ends the offset
    BillGenerationService.ensure_month_bills(2026, 7)

    bill = Bill.all_objects.get(employee=emp, competence_month=date(2026, 7, 1))
    assert bill.line_items.filter(is_offset=True).count() == 0  # offset stopped
    assert bill.line_items.filter(is_offset=False).count() == 1  # base still present


@freeze_time("2026-06-15")
def test_payroll_idempotent() -> None:
    emp = make_employee(payment_type="fixed", base_salary=Decimal("1500.00"))
    BillGenerationService.ensure_month_bills(2026, 6)
    BillGenerationService.ensure_month_bills(2026, 6)
    bills = Bill.all_objects.filter(employee=emp, competence_month=date(2026, 6, 1))
    assert bills.count() == 1
    assert bills.get().line_items.count() == 1


# --- structural / non-regression ---


def test_no_plans_or_employees_keeps_recurring_only() -> None:
    account = make_billing_account(expected_amount=Decimal("100.00"))
    bills = BillGenerationService.ensure_month_bills(2026, 6)
    assert len(bills) == 1
    assert bills[0].billing_account_id == account.id


def test_inactive_plan_and_employee_do_not_generate() -> None:
    plan = make_installment_plan(
        embedded=False, installment_count=1, lifecycle_state=InstallmentPlanState.DEFERRED
    )
    inst = make_installment(
        plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("100.00")
    )
    make_employee(is_active=False, payment_type="fixed", base_salary=Decimal("1000.00"))

    bills = BillGenerationService.ensure_month_bills(2026, 6)
    assert Bill.all_objects.filter(installment=inst).count() == 0
    assert all(b.employee_id is None for b in bills)
