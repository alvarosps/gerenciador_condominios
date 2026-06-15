"""Session 56 — BillingAccount.objects.recurring_for_generation() + service wiring.

recurring_for_generation() is the single shared predicate (ACTIVE + exclude IPTU)
used by BillGenerationService.ensure_month_bills, CondoProjectionService._projected_expenses,
and (transitively, via materialized bills) CondoCalendarService — so an IPTU account
generates ZERO recurring bills while its STANDALONE installments stay intact, and
generation == projection to the cent. Real ORM/services; freezegun only where a
service reads "today / this month".
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountState,
    BillingAccountType,
)
from finances.money import money_str
from finances.services.bill_generation_service import BillGenerationService
from finances.services.condo_calendar_service import CondoCalendarService
from finances.services.condo_projection_service import CondoProjectionService
from tests.factories import (
    make_billing_account,
    make_condominium,
    make_installment,
    make_installment_plan,
)

pytestmark = pytest.mark.django_db


def test_recurring_for_generation_excludes_iptu() -> None:
    condo = make_condominium()
    water = make_billing_account(
        condominium=condo,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-WATER",
        lifecycle_state=BillingAccountState.ACTIVE,
    )
    make_billing_account(
        condominium=condo,
        account_type=BillingAccountType.IPTU,
        external_identifier="IPTU-1",
        lifecycle_state=BillingAccountState.ACTIVE,
    )
    recurring = list(BillingAccount.objects.recurring_for_generation())
    assert recurring == [water]


def test_recurring_for_generation_excludes_non_active() -> None:
    condo = make_condominium()
    make_billing_account(
        condominium=condo,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-SUSP",
        lifecycle_state=BillingAccountState.SUSPENDED,
    )
    make_billing_account(
        condominium=condo,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-ENDED",
        lifecycle_state=BillingAccountState.ENDED,
    )
    assert BillingAccount.objects.recurring_for_generation().count() == 0


def test_recurring_for_generation_excludes_soft_deleted() -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier="UC-DELETED",
        lifecycle_state=BillingAccountState.ACTIVE,
    )
    account.delete()  # soft delete — inherited is_deleted=False filter must drop it
    assert BillingAccount.objects.recurring_for_generation().count() == 0


@freeze_time("2026-06-15 12:00:00")
def test_iptu_account_generates_zero_recurring_bills() -> None:
    account = make_billing_account(
        account_type=BillingAccountType.IPTU,
        external_identifier="IPTU-ZERO",
        lifecycle_state=BillingAccountState.ACTIVE,
        expected_amount=Decimal("300.00"),
        default_due_day=10,
    )
    BillGenerationService.ensure_month_bills(2026, 6)
    assert Bill.all_objects.filter(billing_account=account).count() == 0


@freeze_time("2026-06-15 12:00:00")
def test_standalone_iptu_installment_bill_untouched() -> None:
    """A standalone (embedded=False) IPTU installment plan still materializes its own Bill."""
    condo = make_condominium()
    plan = make_installment_plan(
        condominium=condo,
        embedded=False,
        installment_count=1,
        description="IPTU 2026 avulso",
    )
    inst = make_installment(
        plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("250.00")
    )
    BillGenerationService.ensure_month_bills(2026, 6)
    bills = Bill.all_objects.filter(installment=inst)
    assert bills.count() == 1


@freeze_time("2026-06-15 12:00:00")
def test_generation_equals_projection_to_the_cent() -> None:
    """WATER recurring (expected_amount) + standalone IPTU installment due this month:
    Σ amount_total of generated bills == CondoProjectionService._projected_expenses(year, month).

    A 2x plan with only the June installment due keeps the plan ACTIVE after generation (it is
    not fully materialized), so generation and projection read the SAME state — the shared
    recurring predicate guarantees they match to the cent.
    """
    condo = make_condominium()
    make_billing_account(
        condominium=condo,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-WATER-GP",
        lifecycle_state=BillingAccountState.ACTIVE,
        expected_amount=Decimal("600.00"),
        default_due_day=10,
    )
    plan = make_installment_plan(
        condominium=condo,
        embedded=False,
        installment_count=2,
        description="IPTU avulso 2x",
    )
    make_installment(plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("250.00"))
    make_installment(plan=plan, number=2, due_date=date(2026, 7, 10), amount=Decimal("250.00"))

    bills = BillGenerationService.ensure_month_bills(2026, 6)
    today = date(2026, 6, 15)
    generated_total = sum(
        (Bill.objects.with_amounts(today).get(pk=bill.pk).amount_total for bill in bills),
        Decimal(0),
    )
    projected = CondoProjectionService._projected_expenses(2026, 6)
    assert money_str(generated_total) == money_str(projected)
    assert money_str(projected) == "850.00"  # 600 consumo + 250 parcela avulsa de junho


@freeze_time("2026-06-15 12:00:00")
def test_calendar_excludes_iptu_recurring_transitively() -> None:
    """After generation, the IPTU recurring bill is absent (0 generated) while its standalone
    installment (due this month) appears — the calendar reads materialized bills only."""
    condo = make_condominium()
    iptu = make_billing_account(
        condominium=condo,
        account_type=BillingAccountType.IPTU,
        external_identifier="IPTU-CAL",
        lifecycle_state=BillingAccountState.ACTIVE,
        expected_amount=Decimal("300.00"),
        default_due_day=10,
    )
    plan = make_installment_plan(
        condominium=condo,
        embedded=False,
        installment_count=1,
        description="IPTU avulso calendário",
    )
    make_installment(plan=plan, number=1, due_date=date(2026, 6, 20), amount=Decimal("250.00"))

    BillGenerationService.ensure_month_bills(2026, 6)
    result = CondoCalendarService.combined_month(2026, 6)
    all_exits = [exit_ for day in result["days"] for exit_ in day["bill_exits"]]
    iptu_recurring_bills = Bill.all_objects.filter(
        billing_account=iptu, competence_month=date(2026, 6, 1)
    )
    assert iptu_recurring_bills.count() == 0  # no recurring IPTU bill exists
    assert any(e["description"] == "IPTU avulso calendário" for e in all_exits)  # standalone shows


@freeze_time("2026-06-15 12:00:00")
def test_projection_recurring_loop_skips_iptu() -> None:
    """_projected_expenses with only one ACTIVE IPTU account (no installments) sums 0."""
    make_billing_account(
        account_type=BillingAccountType.IPTU,
        external_identifier="IPTU-PROJ",
        lifecycle_state=BillingAccountState.ACTIVE,
        expected_amount=Decimal("300.00"),
        default_due_day=10,
    )
    projected = CondoProjectionService._projected_expenses(2026, 6)
    assert projected == Decimal(0)
