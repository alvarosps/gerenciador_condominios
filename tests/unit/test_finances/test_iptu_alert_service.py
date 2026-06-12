"""Session 61 — IptuAlertService unit tests (design §9.1, Apêndice B Fase 5).

Read-only risk evaluation for standalone IPTU installment plans:
- 1 overdue parcela-bill  -> WARNING
- >=2 overdue parcela-bills -> CRITICAL
- 0 overdue                -> no row

overdue/deadline are read from Bill.objects.with_amounts(today).is_overdue
(no N+1, no Python recompute of due_date < today). Only freezegun is mocked
(today / is_overdue); ORM and the service are real.
"""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill, BillingAccountType, InstallmentPlanState
from finances.services.bill_payment_service import BillPaymentService
from finances.services.iptu_alert_service import IptuAlertService, IptuRiskRow
from freezegun import freeze_time

from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_building,
    make_installment,
    make_installment_plan,
)

pytestmark = pytest.mark.django_db

FROZEN = "2026-07-15 12:00:00"


def _iptu_account(building=None, external_identifier: str = "516481", condominium=None):
    return make_billing_account(
        condominium=condominium,
        building=building,
        account_type=BillingAccountType.IPTU,
        external_identifier=external_identifier,
        name=f"IPTU {external_identifier}",
    )


def _iptu_plan(account, *, lifecycle_state=InstallmentPlanState.ACTIVE, embedded=False):
    return make_installment_plan(
        condominium=account.condominium,
        building=account.building,
        billing_account=account,
        embedded=embedded,
        lifecycle_state=lifecycle_state,
        installment_count=10,
    )


def _parcela_bill(plan, *, number: int, due_date: date, amount: str = "100.00") -> Bill:
    """A standalone parcela: an Installment + the Bill that materializes it (line item)."""
    installment = make_installment(
        plan=plan, number=number, due_date=due_date, amount=Decimal(amount)
    )
    bill = make_bill(
        condominium=plan.condominium,
        building=plan.building,
        installment=installment,
        due_date=due_date,
        competence_month=due_date.replace(day=1),
        description=f"IPTU parcela {number}",
        behavior="installment",
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time(FROZEN)
def test_evaluate_returns_empty_when_no_iptu_plans() -> None:
    """Sem InstallmentPlan de IPTU ativo/avulso → evaluate retorna []."""
    assert IptuAlertService.evaluate(date(2026, 7, 15)) == []


@freeze_time(FROZEN)
def test_evaluate_ignores_embedded_plans() -> None:
    """Plano embedded=True (água/luz) com parcela vencida NÃO gera linha (só avulso de IPTU)."""
    water = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="WUC-1", name="Água"
    )
    plan = make_installment_plan(
        condominium=water.condominium,
        building=water.building,
        billing_account=water,
        embedded=True,
        lifecycle_state=InstallmentPlanState.ACTIVE,
    )
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    assert IptuAlertService.evaluate(date(2026, 7, 15)) == []


@freeze_time(FROZEN)
def test_evaluate_ignores_non_iptu_account_type() -> None:
    """Plano avulso ligado a conta WATER/ELECTRICITY com parcela vencida NÃO gera linha."""
    power = make_billing_account(
        account_type=BillingAccountType.ELECTRICITY, external_identifier="EUC-1", name="Luz"
    )
    plan = make_installment_plan(
        condominium=power.condominium,
        building=power.building,
        billing_account=power,
        embedded=False,
        lifecycle_state=InstallmentPlanState.ACTIVE,
    )
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    assert IptuAlertService.evaluate(date(2026, 7, 15)) == []


@freeze_time(FROZEN)
def test_evaluate_ignores_inactive_plan() -> None:
    """Plano IPTU avulso com lifecycle_state != ACTIVE/MATERIALIZED (deferred/paid/canceled) é excluído."""
    account = _iptu_account()
    for state in (
        InstallmentPlanState.DEFERRED,
        InstallmentPlanState.PAID,
        InstallmentPlanState.CANCELED,
    ):
        plan = _iptu_plan(account, lifecycle_state=state)
        _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    assert IptuAlertService.evaluate(date(2026, 7, 15)) == []


@freeze_time(FROZEN)
def test_evaluate_monitors_materialized_plan_with_overdue_parcela() -> None:
    """REGRESSÃO (P2.3 step 9): um plano IPTU totalmente MATERIALIZED (todas as parcelas viraram
    bills) com 1 parcela vencida não paga AINDA é monitorado — antes virava PAID e o alerta sumia."""
    account = _iptu_account()
    plan = _iptu_plan(account, lifecycle_state=InstallmentPlanState.MATERIALIZED)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert len(rows) == 1
    assert rows[0].level == IptuAlertService.LEVEL_WARNING
    assert rows[0].overdue_count == 1
    assert rows[0].plan_id == plan.pk


@freeze_time(FROZEN)
def test_one_overdue_installment_is_warning() -> None:
    """1 parcela-bill vencida não paga → level=WARNING, overdue_count=1."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert len(rows) == 1
    row = rows[0]
    assert row.level == IptuAlertService.LEVEL_WARNING
    assert row.overdue_count == 1
    assert row.plan_id == plan.pk
    assert row.external_identifier == "516481"


@freeze_time(FROZEN)
def test_two_overdue_installments_is_critical() -> None:
    """>=2 parcela-bills vencidas → level=CRITICAL, overdue_count=2, deadline pode ser None."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 5, 10))
    _parcela_bill(plan, number=2, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert len(rows) == 1
    row = rows[0]
    assert row.level == IptuAlertService.LEVEL_CRITICAL
    assert row.overdue_count == 2
    assert row.deadline is None  # no not-yet-due parcela remaining


@freeze_time(FROZEN)
def test_paid_overdue_installment_not_counted() -> None:
    """Parcela com due_date passado mas amount_remaining==0 (paga) NÃO é overdue (annotation)."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    bill = _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))
    BillPaymentService.pay(bill, payment_date=date(2026, 6, 12))

    assert IptuAlertService.evaluate(date(2026, 7, 15)) == []


@freeze_time(FROZEN)
def test_deadline_is_earliest_not_yet_overdue_installment() -> None:
    """deadline = menor due_date >= today entre as parcelas não pagas (1ª ainda não vencida)."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))  # overdue
    _parcela_bill(plan, number=2, due_date=date(2026, 8, 10))  # future (later)
    _parcela_bill(plan, number=3, due_date=date(2026, 7, 20))  # future (earliest >= today)

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert len(rows) == 1
    assert rows[0].level == IptuAlertService.LEVEL_WARNING
    assert rows[0].deadline == date(2026, 7, 20)


@freeze_time("2026-06-30 12:00:00")
def test_boundary_30_06_is_warning() -> None:
    """today=2026-06-30: parcela 9 venc 2026-05-29 (overdue) + parcela 10 venc 2026-06-30
    (due_date < today FALSO no próprio dia → não overdue) → WARNING (1 vencida), deadline=30/06."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=9, due_date=date(2026, 5, 29))
    _parcela_bill(plan, number=10, due_date=date(2026, 6, 30))

    rows = IptuAlertService.evaluate(date(2026, 6, 30))

    assert len(rows) == 1
    assert rows[0].level == IptuAlertService.LEVEL_WARNING
    assert rows[0].overdue_count == 1
    assert rows[0].deadline == date(2026, 6, 30)


@freeze_time("2026-07-01 12:00:00")
def test_boundary_01_07_is_critical() -> None:
    """today=2026-07-01: parcela 10 (venc 30/06) passa a overdue → 2 vencidas → CRITICAL."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=9, due_date=date(2026, 5, 29))
    _parcela_bill(plan, number=10, due_date=date(2026, 6, 30))

    rows = IptuAlertService.evaluate(date(2026, 7, 1))

    assert len(rows) == 1
    assert rows[0].level == IptuAlertService.LEVEL_CRITICAL
    assert rows[0].overdue_count == 2


@freeze_time(FROZEN)
def test_warning_message_pt_includes_inscricao_and_deadline() -> None:
    """Mensagem WARNING contém a inscrição, o venc. da atrasada e o venc. do deadline (DD/MM)."""
    account = _iptu_account(external_identifier="516503")
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))  # overdue
    _parcela_bill(plan, number=2, due_date=date(2026, 7, 20))  # deadline

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    message = rows[0].message
    assert "516503" in message
    assert "10/06" in message  # overdue parcela due date
    assert "20/07" in message  # deadline
    assert "parcelamento" in message.lower()


@freeze_time(FROZEN)
def test_critical_message_pt_no_pay_until() -> None:
    """Mensagem CRITICAL enumera N parcelas e NÃO contém 'pague até'/deadline."""
    account = _iptu_account(external_identifier="516449")
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 5, 10))
    _parcela_bill(plan, number=2, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    message = rows[0].message
    assert "516449" in message
    assert "2 parcelas" in message
    assert "pague até" not in message.lower()
    assert "reparcelar" in message.lower()


@freeze_time(FROZEN)
def test_warning_message_pt_omits_next_when_no_deadline() -> None:
    """WARNING sem parcela aberta restante (deadline None) omite o trecho 'junto com a próxima'."""
    account = _iptu_account(external_identifier="600001")
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=10, due_date=date(2026, 6, 10))  # only overdue, nothing future

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert rows[0].level == IptuAlertService.LEVEL_WARNING
    assert rows[0].deadline is None
    assert "junto com a próxima" not in rows[0].message.lower()


@freeze_time(FROZEN)
def test_building_label_falls_back_to_condominio_when_no_building() -> None:
    """Plano IPTU sem building → building_label == 'Condomínio'."""
    account = _iptu_account(building=None)
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert rows[0].building_label == "Condomínio"


@freeze_time(FROZEN)
def test_building_label_uses_street_number_when_building() -> None:
    """Plano IPTU com building → building_label == str(building.street_number)."""
    building = make_building(street_number=777)
    account = _iptu_account(building=building, condominium=building.condominium)
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert rows[0].building_label == "777"


@freeze_time(FROZEN)
def test_rows_ordered_critical_before_warning_then_external_identifier() -> None:
    """Ordenação determinística: CRITICAL antes de WARNING; depois por external_identifier."""
    # WARNING "516503" (1 overdue)
    warn_a = _iptu_account(external_identifier="516503")
    plan_warn_a = _iptu_plan(warn_a)
    _parcela_bill(plan_warn_a, number=1, due_date=date(2026, 6, 10))
    # WARNING "516449" (1 overdue) — earlier identifier, must come after CRITICAL but before 516503
    warn_b = _iptu_account(external_identifier="516449", condominium=warn_a.condominium)
    plan_warn_b = _iptu_plan(warn_b)
    _parcela_bill(plan_warn_b, number=1, due_date=date(2026, 6, 10))
    # CRITICAL "516999" (2 overdue)
    crit = _iptu_account(external_identifier="516999", condominium=warn_a.condominium)
    plan_crit = _iptu_plan(crit)
    _parcela_bill(plan_crit, number=1, due_date=date(2026, 5, 10))
    _parcela_bill(plan_crit, number=2, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert [(r.level, r.external_identifier) for r in rows] == [
        (IptuAlertService.LEVEL_CRITICAL, "516999"),
        (IptuAlertService.LEVEL_WARNING, "516449"),
        (IptuAlertService.LEVEL_WARNING, "516503"),
    ]


@freeze_time("2026-07-01 02:00:00")
def test_evaluate_uses_passed_today_not_utc() -> None:
    """is_overdue usa o `today` passado: parcela 10 venc 30/06. UTC já é 2026-07-01, mas o
    caller passa today_sp() = 2026-06-30 (SP, UTC-3) → ela NÃO é overdue → WARNING (1 vencida)."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=9, due_date=date(2026, 5, 29))
    _parcela_bill(plan, number=10, due_date=date(2026, 6, 30))

    # Caller passes the São Paulo date (still 2026-06-30 at 02:00 UTC = 23:00 of 06-29? no:
    # 02:00 UTC on 07-01 is 23:00 of 06-30 in SP). Pass today_sp() explicitly.
    sp_today = date(2026, 6, 30)
    rows = IptuAlertService.evaluate(sp_today)

    assert len(rows) == 1
    assert rows[0].level == IptuAlertService.LEVEL_WARNING
    assert rows[0].overdue_count == 1


@freeze_time(FROZEN)
def test_returns_iptu_risk_row_instances() -> None:
    """evaluate retorna instâncias de IptuRiskRow (dataclass frozen) com overdue_due_dates."""
    account = _iptu_account()
    plan = _iptu_plan(account)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    rows = IptuAlertService.evaluate(date(2026, 7, 15))

    assert isinstance(rows[0], IptuRiskRow)
    assert rows[0].overdue_due_dates == [date(2026, 6, 10)]
