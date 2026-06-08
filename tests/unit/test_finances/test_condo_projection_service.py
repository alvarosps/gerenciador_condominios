"""Session 47 — CondoProjectionService tests (Phase 5 backend).

Projected income (collectibility-filtered rent with prepaid evaluated PER MONTH + IncomeEntry),
projected expenses (expected_amount of eligible accounts + ALL active installments due — embedded
and standalone — + payroll, with embedded dedup matching the real generated bills), and the
forward fold anchored on the last CondoMonthClose (frozen months win, current month delegates to
CondoBalanceService.result_of_month). Money is quantized only at the output boundary (string).

Embedded-installment dedup (design §7/§8/§18): the recurring account's expected_amount is the
CONSUMO only; the embedded parcela is the Installment, ADDED on top — exactly as
ensure_month_bills materializes it (600 consumo + 400 parcela = 1000). The projection therefore
counts expected_amount once + each installment once; a parity test pins it to the generated bills.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from finances.models import (
    Bill,
    BillingAccountState,
    BillLifecycleState,
    InstallmentPlanState,
)
from finances.services.bill_generation_service import BillGenerationService
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.condo_projection_service import CondoProjectionService
from freezegun import freeze_time

from core.models import FinancialSettings
from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_bill_skip,
    make_billing_account,
    make_building,
    make_condo_month_close,
    make_employee,
    make_income_entry,
    make_installment,
    make_installment_plan,
    make_lease,
    make_person,
    make_rent_payment,
    make_tenant,
)

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- income


def test_projected_income_rent_plus_income_entry() -> None:
    make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_income_entry(amount=Decimal("300.00"), income_date=date(2026, 7, 15))
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("1300.00")


def test_projected_income_prepaid_evaluated_per_month() -> None:
    # Adriana-style (836/113 prepaid): June is prepaid, July is the next installment due.
    tenant = make_tenant(due_day=10)
    make_lease(
        tenant=tenant,
        rental_value=Decimal("836.00"),
        start_date=date(2026, 1, 1),
        prepaid_until=date(2026, 7, 1),
    )
    assert CondoProjectionService._projected_income(2026, 6) == Decimal(
        "0.00"
    )  # prepaid -> excluded
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("836.00")  # collectible


def test_projected_income_excludes_owner_and_salary_offset() -> None:
    owner = make_person(name="Tiago")
    owner_apartment = make_apartment(building=make_building(street_number=9301), owner=owner)
    make_lease(
        apartment=owner_apartment, rental_value=Decimal("900.00"), start_date=date(2026, 1, 1)
    )
    offset_apartment = make_apartment(building=make_building(street_number=9302))
    make_lease(
        apartment=offset_apartment,
        is_salary_offset=True,
        rental_value=Decimal("850.00"),
        start_date=date(2026, 1, 1),
    )
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("0.00")


def test_projected_income_uses_effective_rental_value_with_pending() -> None:
    make_lease(
        rental_value=Decimal("1000.00"),
        start_date=date(2026, 1, 1),
        pending_rental_value=Decimal("1100.00"),
        pending_rental_value_date=date(2026, 7, 1),
    )
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("1100.00")  # pending active
    assert CondoProjectionService._projected_income(2026, 6) == Decimal("1000.00")  # before pending


def test_projected_income_zero_before_tracking_start() -> None:
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 1, 1),
        rent_tracking_start_date=date(2026, 6, 1),
    )
    make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    assert CondoProjectionService._projected_income(2026, 5) == Decimal("0.00")  # pre-tracking
    assert CondoProjectionService._projected_income(2026, 6) == Decimal("1000.00")  # tracked


def test_projected_income_building_id_filter() -> None:
    building = make_building(street_number=9100)
    apartment = make_apartment(building=building)
    make_lease(apartment=apartment, rental_value=Decimal("700.00"), start_date=date(2026, 1, 1))
    make_lease(rental_value=Decimal("500.00"), start_date=date(2026, 1, 1))  # other building
    assert CondoProjectionService._projected_income(2026, 7, None) == Decimal("1200.00")
    assert CondoProjectionService._projected_income(2026, 7, building.id) == Decimal("700.00")


# --------------------------------------------------------------------------- expenses


def test_projected_expenses_accounts_installments_dedup() -> None:
    account = make_billing_account(expected_amount=Decimal("600.00"), default_due_day=10)
    embedded_plan = make_installment_plan(
        condominium=account.condominium,
        embedded=True,
        linked_billing_account=account,
        installment_count=1,
    )
    make_installment(
        plan=embedded_plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("400.00")
    )
    standalone_plan = make_installment_plan(embedded=False, installment_count=1)
    make_installment(
        plan=standalone_plan, number=1, due_date=date(2026, 7, 15), amount=Decimal("250.00")
    )
    # 600 consumo (expected_amount) + 400 embedded parcela + 250 standalone parcela; nothing doubled.
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("1250.00")


def test_projected_expenses_matches_generated_bill_totals() -> None:
    # The projection must equal what ensure_month_bills actually materializes (no off-by-parcela).
    account = make_billing_account(expected_amount=Decimal("600.00"), default_due_day=10)
    embedded_plan = make_installment_plan(
        condominium=account.condominium,
        embedded=True,
        linked_billing_account=account,
        installment_count=2,
    )
    make_installment(
        plan=embedded_plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("400.00")
    )
    make_installment(
        plan=embedded_plan, number=2, due_date=date(2026, 8, 10), amount=Decimal("400.00")
    )
    standalone_plan = make_installment_plan(embedded=False, installment_count=2)
    make_installment(
        plan=standalone_plan, number=1, due_date=date(2026, 7, 15), amount=Decimal("250.00")
    )
    make_installment(
        plan=standalone_plan, number=2, due_date=date(2026, 8, 15), amount=Decimal("250.00")
    )

    projected = CondoProjectionService._projected_expenses(
        2026, 7
    )  # BEFORE generation mutates plans
    bills = BillGenerationService.ensure_month_bills(2026, 7)
    generated = sum(
        (
            Bill.objects.with_amounts(date(2026, 8, 1)).get(pk=bill.pk).amount_total
            for bill in bills
        ),
        Decimal("0.00"),
    )
    assert projected == generated == Decimal("1250.00")


def test_projected_expenses_respects_end_date() -> None:
    make_billing_account(expected_amount=Decimal("100.00"), end_date=date(2026, 6, 30))  # ended
    make_billing_account(
        expected_amount=Decimal("200.00"), end_date=date(2026, 7, 31)
    )  # still active
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("200.00")


def test_projected_expenses_excludes_suspended_account() -> None:
    account = make_billing_account(
        expected_amount=Decimal("100.00"), lifecycle_state=BillingAccountState.SUSPENDED
    )
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("0.00")
    account.lifecycle_state = BillingAccountState.ACTIVE
    account.save()
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("100.00")


def test_projected_expenses_respects_bill_skip() -> None:
    account = make_billing_account(expected_amount=Decimal("100.00"))
    skip = make_bill_skip(billing_account=account, reference_month=date(2026, 7, 1))
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("0.00")
    skip.delete()  # hard delete (no soft-delete) un-skips
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("100.00")


def test_projected_expenses_respects_tracking_start_month() -> None:
    make_billing_account(expected_amount=Decimal("100.00"), tracking_start_month=date(2026, 8, 1))
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("0.00")  # before start
    assert CondoProjectionService._projected_expenses(2026, 8) == Decimal("100.00")  # at start


def test_projected_expenses_payroll_with_salary_offset() -> None:
    lease = make_lease(
        is_salary_offset=True, rental_value=Decimal("850.00"), start_date=date(2026, 1, 1)
    )
    make_employee(payment_type="mixed", base_salary=Decimal("2000.00"), lease=lease)
    # base 2000 - abatimento 850; Rosa's rent is neither income nor a separate expense line.
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("1150.00")
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("0.00")


def test_projected_expenses_payroll_excluded_when_building_scoped() -> None:
    make_employee(payment_type="fixed", base_salary=Decimal("1500.00"))
    building = make_building(street_number=9200)
    make_billing_account(building=building, expected_amount=Decimal("100.00"))
    # Condo-level payroll is excluded from a building-scoped projection.
    assert CondoProjectionService._projected_expenses(2026, 7, building.id) == Decimal("100.00")
    assert CondoProjectionService._projected_expenses(2026, 7, None) == Decimal("1600.00")


def test_projected_expenses_building_id_filter() -> None:
    building = make_building(street_number=8800)
    make_billing_account(building=building, expected_amount=Decimal("100.00"))
    make_billing_account(expected_amount=Decimal("200.00"))  # condo-level (building=null)
    assert CondoProjectionService._projected_expenses(2026, 7, None) == Decimal("300.00")
    assert CondoProjectionService._projected_expenses(2026, 7, building.id) == Decimal("100.00")


def test_projected_expenses_excludes_soft_deleted() -> None:
    account = make_billing_account(expected_amount=Decimal("100.00"))
    account.delete()  # soft delete
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("0.00")


def test_projected_excludes_soft_deleted_installment_and_income() -> None:
    plan = make_installment_plan(embedded=False, installment_count=1)
    installment = make_installment(
        plan=plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("300.00")
    )
    income = make_income_entry(amount=Decimal("150.00"), income_date=date(2026, 7, 5))
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("300.00")
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("150.00")
    installment.delete()  # soft delete
    income.delete()  # soft delete
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("0.00")
    assert CondoProjectionService._projected_income(2026, 7) == Decimal("0.00")


def test_projected_expenses_skips_inactive_plan_installments() -> None:
    plan = make_installment_plan(embedded=False, lifecycle_state=InstallmentPlanState.DEFERRED)
    make_installment(plan=plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("400.00"))
    assert CondoProjectionService._projected_expenses(2026, 7) == Decimal("0.00")


# --------------------------------------------------------------------------- project / fold


@freeze_time("2026-07-15 12:00:00")
def test_project_returns_chronological_months_with_flags() -> None:
    rows = CondoProjectionService.project(months=3)
    assert len(rows) == 3
    assert [(row["year"], row["month"]) for row in rows] == [(2026, 7), (2026, 8), (2026, 9)]
    assert rows[0]["is_actual"] is True  # current month is real (delegates to result_of_month)
    assert rows[1]["is_actual"] is False  # future projected
    assert rows[2]["is_actual"] is False
    assert all(row["is_closed"] is False for row in rows)
    for row in rows:
        for key in ("income_total", "expenses_total", "net", "cumulative_cash"):
            assert isinstance(row[key], str)


@freeze_time("2026-07-15 12:00:00")
def test_project_baseline_anchored_on_last_closed_month() -> None:
    make_condo_month_close(
        reference_month=date(2026, 6, 1),
        status="closed",
        closed_at=timezone.now(),
        cash_balance_end=Decimal("5000.00"),
    )
    rows = CondoProjectionService.project(months=1)
    # July (current) has no data → net 0; cumulative = anchored baseline (June close) + 0.
    assert rows[0]["net"] == "0.00"
    assert rows[0]["cumulative_cash"] == "5000.00"


@freeze_time("2026-07-15 12:00:00")
def test_project_empty_state_all_zero() -> None:
    rows = CondoProjectionService.project(months=2)
    for row in rows:
        assert row["income_total"] == "0.00"
        assert row["expenses_total"] == "0.00"
        assert row["net"] == "0.00"
        assert row["cumulative_cash"] == "0.00"


@freeze_time("2026-07-15 12:00:00")
def test_project_closed_month_reads_frozen_and_wins() -> None:
    make_condo_month_close(
        reference_month=date(2026, 7, 1),
        status="closed",
        closed_at=timezone.now(),
        net_result=Decimal("1234.00"),
        cash_balance_end=Decimal("9999.00"),
    )
    rows = CondoProjectionService.project(months=1)
    assert rows[0]["is_closed"] is True
    assert rows[0]["is_actual"] is True
    assert rows[0]["net"] == "1234.00"
    assert rows[0]["cumulative_cash"] == "9999.00"

    # Mutating a bill of the closed month must NOT change the frozen net/cumulative.
    bill = make_bill(competence_month=date(2026, 7, 1), lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("500.00"))
    refreshed = CondoProjectionService.project(months=1)
    assert refreshed[0]["net"] == "1234.00"
    assert refreshed[0]["cumulative_cash"] == "9999.00"


@freeze_time("2026-07-15 12:00:00")
def test_project_closed_month_pontas_frozen_and_consistent() -> None:
    # Close July via the real service so the breakdown carries the frozen income/expense pontas.
    bill = make_bill(competence_month=date(2026, 7, 1), lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("400.00"))
    CondoMonthCloseService.close(2026, 7)
    row = CondoProjectionService.project(months=1)[0]
    assert row["is_closed"] is True
    assert row["expenses_total"] == "400.00"
    assert Decimal(row["income_total"]) - Decimal(row["expenses_total"]) == Decimal(row["net"])

    # Editing the closed month's bills must leave the frozen pontas (not just net) unchanged.
    extra = make_bill(competence_month=date(2026, 7, 1), lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=extra, amount=Decimal("999.00"))
    refreshed = CondoProjectionService.project(months=1)[0]
    assert refreshed["expenses_total"] == "400.00"  # frozen, not 1399
    assert Decimal(refreshed["income_total"]) - Decimal(refreshed["expenses_total"]) == Decimal(
        refreshed["net"]
    )


@freeze_time("2026-07-15 12:00:00")
def test_project_current_month_delegates_to_result_of_month() -> None:
    lease = make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_rent_payment(lease=lease, reference_month=date(2026, 7, 1), amount_paid=Decimal("1000.00"))
    bill = make_bill(competence_month=date(2026, 7, 1), lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("400.00"))
    rows = CondoProjectionService.project(months=1)
    expected_net = CondoBalanceService.result_of_month(2026, 7)
    assert rows[0]["net"] == str(expected_net)
    # No off-by-cent: the displayed pontas reconcile to the canonical net.
    assert Decimal(rows[0]["income_total"]) - Decimal(rows[0]["expenses_total"]) == expected_net


@freeze_time("2026-07-15 12:00:00")
def test_project_future_month_uses_projection_and_folds() -> None:
    make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_billing_account(expected_amount=Decimal("400.00"))
    rows = CondoProjectionService.project(months=2)
    august = rows[1]
    assert august["is_actual"] is False
    assert august["income_total"] == "1000.00"
    assert august["expenses_total"] == "400.00"
    assert august["net"] == "600.00"
    # cumulative folds July (current) net into August.
    july_cumulative = Decimal(rows[0]["cumulative_cash"])
    assert Decimal(august["cumulative_cash"]) == july_cumulative + Decimal("600.00")


@freeze_time("2026-07-01 02:00:00")
def test_project_uses_sao_paulo_month_boundary() -> None:
    # UTC is already July 1 (02:00); in São Paulo it is still June 30 23:00 → current month = June.
    rows = CondoProjectionService.project(months=1)
    assert (rows[0]["year"], rows[0]["month"]) == (2026, 6)
