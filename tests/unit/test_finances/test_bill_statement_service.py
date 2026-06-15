"""Session 58 — BillService statement extension tests.

create_with_lines (statement + per-line installment), update_with_lines (replace lines +
upsert statement, guard UNPAID + month OPEN), delete (cascade soft-delete of the statement),
and the nested read-only statement in BillSerializer. ORM/services are real (mock policy);
freezegun fixes today_sp() where UNPAID/overdue matters.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time

from finances.models import (
    Bill,
    BillBehavior,
    BillingAccountType,
    BillLineItem,
    ElectricityBillStatement,
    SupplyStatus,
    WaterBillStatement,
)
from finances.serializers import BillSerializer
from finances.services.bill_payment_service import BillPaymentService
from finances.services.bill_service import BillDraft, BillService
from tests.factories import (
    make_billing_account,
    make_condo_month_close,
    make_condominium,
    make_installment,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

FROZEN = "2026-06-05 12:00:00"


def _draft(cond, account=None, **kwargs):
    defaults = {
        "condominium": cond,
        "competence_month": date(2026, 6, 1),
        "due_date": date(2026, 6, 10),
        "description": "Conta de consumo",
        "behavior": BillBehavior.RECURRING,
        "billing_account": account,
    }
    defaults.update(kwargs)
    return BillDraft(**defaults)


def _water_account(cond):
    return make_billing_account(
        condominium=cond, account_type=BillingAccountType.WATER, external_identifier="UC-1"
    )


def _power_account(cond):
    return make_billing_account(
        condominium=cond, account_type=BillingAccountType.ELECTRICITY, external_identifier="UC-2"
    )


def test_create_with_lines_creates_water_statement() -> None:
    cond = make_condominium()
    account = _water_account(cond)
    bill = BillService.create_with_lines(
        _draft(cond, account),
        [{"description": "Consumo", "amount": Decimal("120.00")}],
        statement={"consumo_m3": 158, "leitura_anterior": 1000, "leitura_atual": 1158},
    )
    statement = WaterBillStatement.objects.get(bill=bill)
    assert statement.consumo_m3 == 158
    annotated = Bill.objects.with_amounts(date(2026, 6, 30)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("120.00")


def test_create_with_lines_creates_electricity_statement() -> None:
    cond = make_condominium()
    account = _power_account(cond)
    bill = BillService.create_with_lines(
        _draft(cond, account),
        [{"description": "Energia", "amount": Decimal("300.00")}],
        statement={"consumo_kwh": 1752, "bandeira": "Verde"},
    )
    statement = ElectricityBillStatement.objects.get(bill=bill)
    assert statement.consumo_kwh == 1752
    assert statement.bandeira == "Verde"


def test_create_with_lines_sets_line_installment() -> None:
    cond = make_condominium()
    installment = make_installment()
    bill = BillService.create_with_lines(
        _draft(cond),
        [{"description": "Parcela", "amount": Decimal("100.00"), "installment": installment}],
    )
    line = bill.line_items.get()
    assert line.installment_id == installment.pk


def test_create_with_lines_statement_none_creates_no_statement() -> None:
    cond = make_condominium()
    account = _water_account(cond)
    bill = BillService.create_with_lines(
        _draft(cond, account),
        [{"description": "Consumo", "amount": Decimal("120.00")}],
        statement=None,
    )
    assert WaterBillStatement.objects.filter(bill=bill).exists() is False
    assert ElectricityBillStatement.objects.filter(bill=bill).exists() is False


def test_create_with_lines_rejects_statement_for_generic_account() -> None:
    cond = make_condominium()
    before = Bill.all_objects.count()
    with pytest.raises(ValidationError):
        BillService.create_with_lines(
            _draft(cond, account=None, behavior=BillBehavior.ONE_TIME),
            [{"description": "X", "amount": Decimal("10.00")}],
            statement={"consumo_m3": 10},
        )
    assert Bill.all_objects.count() == before


def test_create_with_lines_atomic_rollback_on_bad_statement() -> None:
    cond = make_condominium()
    account = _water_account(cond)
    bill_before = Bill.all_objects.count()
    line_before = BillLineItem.all_objects.count()
    statement_before = WaterBillStatement.all_objects.count()
    with pytest.raises(ValidationError):
        BillService.create_with_lines(
            _draft(cond, account),
            [{"description": "Consumo", "amount": Decimal("120.00")}],
            statement={"leitura_anterior": 1000},  # missing consumo_m3
        )
    assert Bill.all_objects.count() == bill_before
    assert BillLineItem.all_objects.count() == line_before
    assert WaterBillStatement.all_objects.count() == statement_before


@freeze_time(FROZEN)
def test_update_with_lines_replaces_lines_keeps_bill_pk() -> None:
    cond = make_condominium()
    account = _water_account(cond)
    bill = BillService.create_with_lines(
        _draft(cond, account),
        [{"description": "Antiga", "amount": Decimal("100.00")}],
    )
    old_line = bill.line_items.get()
    updated = BillService.update_with_lines(
        bill,
        [
            {"description": "Nova A", "amount": Decimal("70.00")},
            {"description": "Nova B", "amount": Decimal("80.00")},
        ],
    )
    assert updated.pk == bill.pk
    assert BillLineItem.objects.filter(bill=bill).count() == 2
    assert BillLineItem.objects.with_deleted().get(pk=old_line.pk).is_deleted is True
    annotated = Bill.objects.with_amounts(date(2026, 6, 30)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("150.00")


@freeze_time(FROZEN)
def test_update_with_lines_upserts_statement() -> None:
    cond = make_condominium()
    account = _water_account(cond)
    bill = BillService.create_with_lines(
        _draft(cond, account),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
        statement={"consumo_m3": 100},
    )
    BillService.update_with_lines(
        bill,
        [{"description": "Consumo", "amount": Decimal("110.00")}],
        statement={"consumo_m3": 158},
    )
    assert WaterBillStatement.objects.filter(bill=bill).count() == 1
    assert WaterBillStatement.objects.get(bill=bill).consumo_m3 == 158


@freeze_time(FROZEN)
def test_update_with_lines_rejects_when_paid() -> None:
    cond = make_condominium()
    user = get_user_model().objects.create(username="payer")
    bill = BillService.create_with_lines(
        _draft(cond, _water_account(cond)),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
    )
    BillPaymentService.pay(bill, date(2026, 6, 5), None, user=user)
    with pytest.raises(ValidationError):
        BillService.update_with_lines(bill, [{"description": "X", "amount": Decimal("50.00")}])
    assert BillLineItem.objects.get(bill=bill).description == "Consumo"


@freeze_time(FROZEN)
def test_update_with_lines_rejects_when_month_closed() -> None:
    cond = make_condominium()
    bill = BillService.create_with_lines(
        _draft(cond, _water_account(cond)),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
    )
    make_condo_month_close(
        condominium=cond,
        reference_month=date(2026, 6, 1),
        status="closed",
        closed_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        BillService.update_with_lines(bill, [{"description": "X", "amount": Decimal("50.00")}])


def test_delete_cascades_statement_soft() -> None:
    cond = make_condominium()
    bill = BillService.create_with_lines(
        _draft(cond, _water_account(cond)),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
        statement={"consumo_m3": 100},
    )
    BillService.delete(bill)
    assert Bill.objects.filter(pk=bill.pk).exists() is False
    assert WaterBillStatement.objects.filter(bill=bill).exists() is False
    assert Bill.objects.with_deleted().get(pk=bill.pk).is_deleted is True
    statement = WaterBillStatement.objects.with_deleted().filter(bill=bill).first()
    assert statement is not None
    assert statement.is_deleted is True


@freeze_time(FROZEN)
def test_serializer_nests_live_water_statement() -> None:
    cond = make_condominium()
    bill = BillService.create_with_lines(
        _draft(cond, _water_account(cond)),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
        statement={"consumo_m3": 158, "agua_status": SupplyStatus.CUT},
    )
    annotated = Bill.objects.with_amounts(date(2026, 6, 30)).get(pk=bill.pk)
    data = BillSerializer(annotated).data
    assert data["water_statement"]["consumo_m3"] == 158
    assert data["water_statement"]["agua_status"] == SupplyStatus.CUT
    assert data["electricity_statement"] is None


def test_serializer_hidden_bill_does_not_expose_statement() -> None:
    cond = make_condominium()
    bill = BillService.create_with_lines(
        _draft(cond, _water_account(cond)),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
        statement={"consumo_m3": 158},
    )
    BillService.delete(bill)
    reloaded = Bill.objects.with_deleted().get(pk=bill.pk)
    data = BillSerializer(reloaded).data
    assert data["water_statement"] is None


def test_serializer_hidden_bill_does_not_expose_electricity_statement() -> None:
    cond = make_condominium()
    bill = BillService.create_with_lines(
        _draft(cond, _power_account(cond)),
        [{"description": "Energia", "amount": Decimal("300.00")}],
        statement={"consumo_kwh": 1752},
    )
    BillService.delete(bill)
    reloaded = Bill.objects.with_deleted().get(pk=bill.pk)
    data = BillSerializer(reloaded).data
    assert data["electricity_statement"] is None


@freeze_time(FROZEN)
def test_serializer_nests_live_electricity_statement() -> None:
    cond = make_condominium()
    bill = BillService.create_with_lines(
        _draft(cond, _power_account(cond)),
        [{"description": "Energia", "amount": Decimal("300.00")}],
        statement={"consumo_kwh": 1752, "bandeira": "Verde"},
    )
    annotated = Bill.objects.with_amounts(date(2026, 6, 30)).get(pk=bill.pk)
    data = BillSerializer(annotated).data
    assert data["electricity_statement"]["consumo_kwh"] == 1752
    assert data["electricity_statement"]["bandeira"] == "Verde"
    assert data["water_statement"] is None


@freeze_time(FROZEN)
def test_update_with_lines_swaps_statement_type() -> None:
    """A water bill re-typed as electricity: the old water statement is soft-deleted and a single
    live electricity statement replaces it (a bill carries at most one reading statement)."""
    cond = make_condominium()
    water_account = _water_account(cond)
    bill = BillService.create_with_lines(
        _draft(cond, water_account),
        [{"description": "Consumo", "amount": Decimal("100.00")}],
        statement={"consumo_m3": 158},
    )
    bill.billing_account = _power_account(cond)
    bill.save(update_fields=["billing_account"])
    BillService.update_with_lines(
        bill,
        [{"description": "Energia", "amount": Decimal("120.00")}],
        statement={"consumo_kwh": 999},
    )
    assert WaterBillStatement.objects.filter(bill=bill).exists() is False
    assert WaterBillStatement.objects.with_deleted().get(bill=bill).is_deleted is True
    assert ElectricityBillStatement.objects.get(bill=bill).consumo_kwh == 999
