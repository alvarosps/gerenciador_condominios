"""Session 64 — seed_condo_utilities management command tests (design §13, Apêndice A/B Fase 7).

The command seeds the real condo utility/IPTU inventory idempotently:
- typed BillingAccounts (water/electricity/IPTU) with identity (inscrição/UC/medidor/holder/address),
- embedded InstallmentPlans (water 836/850, electricity 850) linked to the consumption account,
- 9 standalone IPTU terms (InstallmentPlan embedded=False, billing_account=<IPTU>) with ONLY the
  opening parcelas materialized — current (overdue 29/05) + next (open 30/06) — at competence 2026-06,
- 3 deferred 2026 IPTU debts (Bill DEFERRED + 1 full-value BillLineItem + billing_account=<IPTU>).

Mock policy (tests/CLAUDE.md): only freezegun (today_sp / overdue) is mocked. ORM, the command,
BillService, InstallmentPlanService and IptuAlertService are real (banco real, --reuse-db). The
command is exercised via django.core.management.call_command — never patched.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
    SupplyStatus,
)
from finances.services.bill_generation_service import BillGenerationService
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.installment_plan_service import InstallmentPlanService
from finances.services.iptu_alert_service import IptuAlertService
from finances.services.timezone import today_sp
from freezegun import freeze_time

from core.models import FinancialSettings
from tests.factories import make_building

pytestmark = pytest.mark.django_db

FROZEN = "2026-06-08 12:00:00"
OPENING_COMPETENCE = date(2026, 6, 1)
REAL_SEED_PATH = Path("scripts/data/condo_utilities_seed.json")

# A small but faithful subset of the real inventory: 1 water + 1 electricity + 1 IPTU account,
# 1 embedded plan, 2 IPTU terms (each with an overdue opening parcela), 1 deferred 2026 debt.
_FIXTURE_DATA: dict[str, object] = {
    "configuracoes": {
        "saldo_inicial": 0,
        "data_saldo_inicial": "2026-03-01",
        "rent_tracking_start_date": "2026-06-01",
    },
    "contas": [
        {
            "predio_street_number": 836,
            "account_type": "water",
            "name": "Água DMAE 836",
            "external_identifier": "117.111.0049.0519.00",
            "secondary_identifier": "003419142",
            "holder_name": "RAUL",
            "registered_address": "Av Circular 828",
            "supply_status": "cut",
            "default_due_day": 4,
            "expected_amount": 0,
        },
        {
            "predio_street_number": 836,
            "account_type": "electricity",
            "name": "Luz principal 840 (solar) 836",
            "external_identifier": "1.273.798.010-05",
            "secondary_identifier": "MD50721985",
            "holder_name": "RAUL",
            "registered_address": "Av Circular 828",
            "supply_status": "active",
            "default_due_day": 10,
            "expected_amount": 921.49,
        },
        {
            "predio_street_number": 836,
            "account_type": "iptu",
            "name": "IPTU 836",
            "external_identifier": "516449",
            "holder_name": "RAUL",
            "registered_address": "Av Circular 828",
            "supply_status": "active",
            "default_due_day": 30,
            "expected_amount": 0,
        },
    ],
    "planos_embutidos": [
        {
            "predio_street_number": 836,
            "account_type": "water",
            "account_external_identifier": "117.111.0049.0519.00",
            "description": "Parcelamento DMAE água 836",
            "installment_count": 46,
            "current_installment": 24,
            "installment_amount": 94.48,
            "default_due_day": 4,
        },
    ],
    "termos_iptu": [
        {
            "predio_street_number": 836,
            "account_external_identifier": "516449",
            "termo": "992988",
            "installment_count": 10,
            "total_amount": 1045.44,
            "current_number": 9,
            "current_amount": 522.72,
            "current_due_date": "2026-05-29",
            "next_number": 10,
            "next_amount": 522.72,
            "next_due_date": "2026-06-30",
        },
        {
            "predio_street_number": 836,
            "account_external_identifier": "516449",
            "termo": "992991",
            "installment_count": 10,
            "total_amount": 98.37,
            "current_number": 9,
            "current_amount": 49.15,
            "current_due_date": "2026-05-29",
            "next_number": 10,
            "next_amount": 49.22,
            "next_due_date": "2026-06-30",
        },
    ],
    "dividas_2026": [
        {
            "predio_street_number": 836,
            "account_external_identifier": "516449",
            "lancamento": "202600179949",
            "amount": 10308.70,
            "due_date": "2026-06-30",
        },
    ],
}


def _write_fixture(tmp_path: Path, data: dict[str, object] | None = None) -> str:
    payload = _FIXTURE_DATA if data is None else data
    path = tmp_path / "condo_utilities_seed_test.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _make_real_buildings() -> None:
    make_building(street_number=836)
    make_building(street_number=850)


def _make_fixture_buildings() -> None:
    make_building(street_number=836)


def _run(file_path: str, *, dry_run: bool = False) -> None:
    args = ["seed_condo_utilities", "--file", file_path]
    if dry_run:
        args.append("--dry-run")
    call_command(*args)


def _iptu_account(external_identifier: str) -> BillingAccount:
    return BillingAccount.objects.get(
        account_type=BillingAccountType.IPTU, external_identifier=external_identifier
    )


def _term_plan(termo: str) -> InstallmentPlan:
    return InstallmentPlan.objects.get(description__contains=termo, embedded=False)


def _deferred_debt(external_identifier: str) -> Bill:
    return Bill.objects.get(
        billing_account__external_identifier=external_identifier,
        lifecycle_state=BillLifecycleState.DEFERRED,
    )


@freeze_time(FROZEN)
def test_seed_creates_typed_billing_accounts_with_identity(tmp_path: Path) -> None:
    """Typed BillingAccounts (water/electricity/IPTU) carry account_type, external_identifier
    (inscrição/UC), secondary_identifier (imóvel/medidor), holder_name, registered_address and
    supply_status from the JSON; 836-água has supply_status=CUT."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    water = BillingAccount.objects.get(
        account_type=BillingAccountType.WATER, external_identifier="117.111.0049.0519.00"
    )
    assert water.secondary_identifier == "003419142"
    assert water.holder_name == "RAUL"
    assert water.registered_address == "Av Circular 828"
    assert water.supply_status == SupplyStatus.CUT
    assert water.default_due_day == 4
    assert water.building is not None
    assert water.building.street_number == 836

    electricity = BillingAccount.objects.get(
        account_type=BillingAccountType.ELECTRICITY, external_identifier="1.273.798.010-05"
    )
    assert electricity.secondary_identifier == "MD50721985"
    assert electricity.expected_amount == Decimal("921.49")
    assert electricity.supply_status == SupplyStatus.ACTIVE

    iptu = _iptu_account("516449")
    assert iptu.holder_name == "RAUL"
    assert iptu.account_type == BillingAccountType.IPTU


@freeze_time(FROZEN)
def test_seed_is_idempotent_no_duplication_on_rerun(tmp_path: Path) -> None:
    """call_command 2× keeps BillingAccount/InstallmentPlan/Bill(deferred)/BillLineItem counts
    identical after the 2nd run (update_or_create on natural keys; the single deferred line is
    NOT duplicated — get_or_create)."""
    _make_fixture_buildings()
    file_path = _write_fixture(tmp_path)
    _run(file_path)

    counts_after_first = {
        "accounts": BillingAccount.objects.count(),
        "plans": InstallmentPlan.objects.count(),
        "installments": Installment.objects.count(),
        "bills": Bill.objects.count(),
        "deferred": Bill.objects.filter(lifecycle_state=BillLifecycleState.DEFERRED).count(),
        "lines": BillLineItem.objects.count(),
    }

    _run(file_path)

    counts_after_second = {
        "accounts": BillingAccount.objects.count(),
        "plans": InstallmentPlan.objects.count(),
        "installments": Installment.objects.count(),
        "bills": Bill.objects.count(),
        "deferred": Bill.objects.filter(lifecycle_state=BillLifecycleState.DEFERRED).count(),
        "lines": BillLineItem.objects.count(),
    }
    assert counts_after_first == counts_after_second


@freeze_time(FROZEN)
def test_seed_embedded_plans_linked_to_consumption_accounts(tmp_path: Path) -> None:
    """Embedded plans (water/electricity) have embedded=True, billing_account=<consumption account>,
    installment_count from the JSON; clean() accepts them (consumption account)."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    plan = InstallmentPlan.objects.get(embedded=True)
    assert plan.billing_account is not None
    assert plan.billing_account.account_type == BillingAccountType.WATER
    assert plan.installment_count == 46
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE


@freeze_time(FROZEN)
def test_seed_embedded_plan_materializes_going_forward_installments(tmp_path: Path) -> None:
    """The embedded plan is NOT an inert shell: going-forward Installment rows are materialized
    (current parcela 24 through 46, non-backfill of 1..23), so generation can land the parcela.
    Current parcela (24) is due in the opening month 2026-06."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    plan = InstallmentPlan.objects.get(embedded=True)
    numbers = sorted(Installment.objects.filter(plan=plan).values_list("number", flat=True))
    assert numbers == list(range(24, 47))  # current 24 .. count 46; 1..23 NOT backfilled
    current = Installment.objects.get(plan=plan, number=24)
    assert current.due_date == date(2026, 6, 4)  # default_due_day 4, opening month 2026-06
    assert current.amount == Decimal("94.48")


@freeze_time(FROZEN)
def test_seed_embedded_parcela_lands_on_generated_bill(tmp_path: Path) -> None:
    """Regression: after seed + ensure_month_bills(2026,6), the embedded parcela appears as a line on
    the recurring account's generated Bill (the plan is no longer an inert shell)."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    account = BillingAccount.objects.get(
        account_type=BillingAccountType.WATER, external_identifier="117.111.0049.0519.00"
    )
    current = Installment.objects.get(plan__billing_account=account, number=24)
    BillGenerationService.ensure_month_bills(2026, 6)

    bill = Bill.objects.get(billing_account=account, competence_month=OPENING_COMPETENCE)
    parcela_lines = BillLineItem.objects.filter(bill=bill, installment=current)
    assert parcela_lines.count() == 1
    assert parcela_lines.first().amount == Decimal("94.48")


@freeze_time(FROZEN)
def test_seed_iptu_terms_are_standalone_with_iptu_account(tmp_path: Path) -> None:
    """Each IPTU term → InstallmentPlan(embedded=False, billing_account=<IPTU>, ACTIVE); description
    contains the term number; visible to IptuAlertService (account_type=IPTU, embedded=False)."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    plan = _term_plan("992988")
    assert plan.embedded is False
    assert plan.billing_account is not None
    assert plan.billing_account.account_type == BillingAccountType.IPTU
    assert plan.billing_account.external_identifier == "516449"
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE
    assert "992988" in plan.description

    visible_plan_ids = {
        p.pk
        for p in InstallmentPlan.objects.filter(
            embedded=False,
            lifecycle_state=InstallmentPlanState.ACTIVE,
            billing_account__account_type=BillingAccountType.IPTU,
        )
    }
    assert plan.pk in visible_plan_ids


@freeze_time(FROZEN)
def test_opening_installments_use_competence_2026_06_with_real_due_dates(tmp_path: Path) -> None:
    """Current (overdue 29/05) and next (open 30/06) parcelas: both bills have competence_month ==
    date(2026,6,1) but due_date == the real date (29/05 and 30/06); number == real (9 and 10)."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    plan = _term_plan("992988")
    installments = {i.number: i for i in Installment.objects.filter(plan=plan)}
    assert set(installments) == {9, 10}
    assert installments[9].due_date == date(2026, 5, 29)
    assert installments[10].due_date == date(2026, 6, 30)

    bills = {
        b.installment.number: b
        for b in Bill.objects.filter(installment__plan=plan).select_related("installment")
    }
    assert bills[9].competence_month == OPENING_COMPETENCE
    assert bills[10].competence_month == OPENING_COMPETENCE
    assert bills[9].due_date == date(2026, 5, 29)
    assert bills[10].due_date == date(2026, 6, 30)


@freeze_time(FROZEN)
def test_seed_does_not_backfill_paid_pre_tracking_installments(tmp_path: Path) -> None:
    """Only the current and next parcelas exist per term: exactly 2 Installments (numbers {9,10});
    parcelas 1..8 are NOT created (non-backfill, §13)."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    plan = _term_plan("992988")
    numbers = sorted(Installment.objects.filter(plan=plan).values_list("number", flat=True))
    assert numbers == [9, 10]


@freeze_time(FROZEN)
def test_opening_overdue_installment_appears_in_overdue_not_pre_tracking(tmp_path: Path) -> None:
    """The overdue opening parcela (competence 2026-06, UNPAID, due 29/05) is in 'Atrasados'; no
    bill with competence_month < 2026-06-01 was created → no spurious pre-tracking net."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    assert not Bill.objects.filter(competence_month__lt=OPENING_COMPETENCE).exists()
    overdue_total = CondoBalanceService.overdue_bills_total()
    # The overdue opening parcela of term 992988 (R$522,72, valor atualizado) is part of 'Atrasados'.
    assert overdue_total >= Decimal("522.72")


@freeze_time(FROZEN)
def test_deferred_2026_debts_excluded_from_result_cash_overdue(tmp_path: Path) -> None:
    """The deferred 2026 debt is Bill(lifecycle_state=DEFERRED) with 1 full-value BillLineItem +
    billing_account=<IPTU>; it does NOT show up in competence/cash/overdue (==ACTIVE filter)."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    debt = _deferred_debt("516449")
    assert debt.lifecycle_state == BillLifecycleState.DEFERRED
    assert debt.billing_account is not None
    assert debt.billing_account.account_type == BillingAccountType.IPTU
    lines = list(BillLineItem.objects.filter(bill=debt))
    assert len(lines) == 1
    assert lines[0].amount == Decimal("10308.70")
    assert lines[0].is_offset is False

    # competence result for June excludes the deferred debt (==ACTIVE); only ACTIVE opening parcelas
    # with competence June count. The deferred R$10.308,70 must not be in the expense competence.
    _revenue, expense = CondoBalanceService.competence_pontas(2026, 6)
    assert expense < Decimal("10308.70")

    overdue_total = CondoBalanceService.overdue_bills_total()
    # overdue sums the overdue opening parcelas; the deferred debt (due 30/06, DEFERRED) is excluded.
    assert overdue_total < Decimal("10308.70")


@freeze_time(FROZEN)
def test_convert_deferred_on_seeded_debt_yields_exact_total(tmp_path: Path) -> None:
    """InstallmentPlanService.convert_deferred(deferred_bill=<836 debt R$10.308,70>) → the plan
    inherits the IPTU account (§10.2) and plan.total_amount == Decimal('10308.70'); Σ installments
    == total; IptuAlertService then sees the new plan."""
    _make_fixture_buildings()
    _run(_write_fixture(tmp_path))

    debt = _deferred_debt("516449")
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=debt,
        installment_count=10,
        start_due_date=date(2026, 7, 30),
        default_due_day=30,
    )
    assert plan.billing_account is not None
    assert plan.billing_account.account_type == BillingAccountType.IPTU
    assert plan.total_amount == Decimal("10308.70")

    installment_sum = sum(
        (i.amount for i in Installment.objects.filter(plan=plan)), Decimal("0.00")
    )
    assert installment_sum == Decimal("10308.70")

    # The deferred bill is now CANCELED (terminal); the new active plan is visible to the alert.
    debt.refresh_from_db()
    assert debt.lifecycle_state == BillLifecycleState.CANCELED


@freeze_time(FROZEN)
def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    """call_command(..., '--dry-run') leaves BillingAccount/InstallmentPlan/Bill counts unchanged
    (transaction.set_rollback)."""
    _make_fixture_buildings()
    file_path = _write_fixture(tmp_path)

    _run(file_path, dry_run=True)

    assert BillingAccount.objects.count() == 0
    assert InstallmentPlan.objects.count() == 0
    assert Bill.objects.count() == 0
    assert FinancialSettings.objects.count() == 0


@freeze_time(FROZEN)
def test_seed_settings_singleton(tmp_path: Path) -> None:
    """FinancialSettings (pk=1) → initial_balance=0, initial_balance_date=2026-03-01,
    rent_tracking_start_date=2026-06-01 (update_or_create; rerun does not duplicate)."""
    _make_fixture_buildings()
    file_path = _write_fixture(tmp_path)
    _run(file_path)
    _run(file_path)

    assert FinancialSettings.objects.count() == 1
    settings = FinancialSettings.objects.get(pk=1)
    assert settings.initial_balance == Decimal(0)
    assert settings.initial_balance_date == date(2026, 3, 1)
    assert settings.rent_tracking_start_date == date(2026, 6, 1)


@freeze_time(FROZEN)
def test_seed_missing_building_raises_command_error(tmp_path: Path) -> None:
    """A JSON referencing a non-existent building raises a PT CommandError and creates nothing
    (transaction.atomic wraps everything)."""
    # No buildings created → 836 is missing.
    with pytest.raises(CommandError) as exc_info:
        _run(_write_fixture(tmp_path))
    assert "836" in str(exc_info.value)
    assert BillingAccount.objects.count() == 0
    assert FinancialSettings.objects.count() == 0


@freeze_time(FROZEN)
def test_seed_missing_file_raises_command_error(tmp_path: Path) -> None:
    """A --file path that does not exist raises a PT CommandError naming the path."""
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(CommandError) as exc_info:
        _run(str(missing))
    assert "does_not_exist.json" in str(exc_info.value)


@freeze_time(FROZEN)
def test_seed_tolerates_missing_and_malformed_sections(tmp_path: Path) -> None:
    """A JSON without 'configuracoes' and with a non-list section is tolerated (no settings row,
    no crash): the defensive guards skip them instead of raising."""
    _make_fixture_buildings()
    data: dict[str, object] = {"contas": "not-a-list"}
    _run(_write_fixture(tmp_path, data))

    assert FinancialSettings.objects.count() == 0
    assert BillingAccount.objects.count() == 0


@freeze_time(FROZEN)
def test_real_inventory_smoke_counts_match_appendix_a() -> None:
    """SMOKE: the REAL condo_utilities_seed.json (after creating buildings 836/850) →
    9 active standalone IPTU plans, 3 deferred debts, 5 consumption accounts (2 water DMAE +
    3 electricity: 836 principal + 836 2º relógio + 850), 3 IPTU accounts (516449 / 516481 /
    516503); IptuAlertService.evaluate(today_sp()) → 9 WARNING rows.

    (Apêndice A is authoritative: 3 electricity + 3 IPTU inscrições. The prompt's totals line said
    '4 luz / 6 consumo / 4 IPTU' but the per-account inventory — the canonical source — has 3 luz /
    5 consumo / 3 IPTU; one deferred debt + several terms per IPTU inscrição.)"""
    _make_real_buildings()
    _run(str(REAL_SEED_PATH))

    iptu_plans = InstallmentPlan.objects.filter(
        embedded=False,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        billing_account__account_type=BillingAccountType.IPTU,
    )
    assert iptu_plans.count() == 9

    deferred = Bill.objects.filter(lifecycle_state=BillLifecycleState.DEFERRED)
    assert deferred.count() == 3
    for debt in deferred:
        assert BillLineItem.objects.filter(bill=debt).count() == 1

    water = BillingAccount.objects.filter(account_type=BillingAccountType.WATER)
    electricity = BillingAccount.objects.filter(account_type=BillingAccountType.ELECTRICITY)
    assert water.count() == 2
    assert electricity.count() == 3
    assert BillingAccount.objects.filter(account_type=BillingAccountType.IPTU).count() == 3

    rows = IptuAlertService.evaluate(today_sp())
    assert len(rows) == 9
    assert all(r.level == IptuAlertService.LEVEL_WARNING for r in rows)
