"""Session 58 — WaterBillStatement / ElectricityBillStatement model tests.

Reading-only 1:1 detail of a Bill (water / power). Zero money fields (money is on
BillLineItem). Mixins (AuditMixin + SoftDeleteMixin) + dual managers; OneToOne CASCADE
on hard-delete; soft-delete does NOT cascade through the relation (the service does).
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Manager

from finances.models import (
    ElectricityBillStatement,
    SoftDeleteManager,
    SupplyStatus,
    WaterBillStatement,
)
from tests.factories import make_bill, make_electricity_statement, make_water_statement

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_water_statement_inherits_audit_and_softdelete_mixins() -> None:
    statement = make_water_statement()
    assert statement.created_at is not None
    assert statement.updated_at is not None
    assert statement.is_deleted is False
    assert isinstance(WaterBillStatement.all_objects, Manager)
    assert isinstance(WaterBillStatement.objects, SoftDeleteManager)
    statement.delete()
    assert WaterBillStatement.objects.filter(pk=statement.pk).exists() is False
    assert WaterBillStatement.all_objects.filter(pk=statement.pk).exists() is True


def test_electricity_statement_inherits_audit_and_softdelete_mixins() -> None:
    statement = make_electricity_statement()
    assert statement.created_at is not None
    assert statement.updated_at is not None
    assert statement.is_deleted is False
    assert isinstance(ElectricityBillStatement.all_objects, Manager)
    assert isinstance(ElectricityBillStatement.objects, SoftDeleteManager)
    statement.delete()
    assert ElectricityBillStatement.objects.filter(pk=statement.pk).exists() is False
    assert ElectricityBillStatement.all_objects.filter(pk=statement.pk).exists() is True


def test_water_statement_is_one_to_one_with_bill() -> None:
    bill = make_bill()
    make_water_statement(bill=bill)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_water_statement(bill=bill)


def test_electricity_statement_is_one_to_one_with_bill() -> None:
    bill = make_bill()
    make_electricity_statement(bill=bill)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_electricity_statement(bill=bill)


def test_bill_hard_delete_cascades_statement() -> None:
    bill = make_bill()
    statement = make_water_statement(bill=bill)
    statement_pk = statement.pk
    bill.delete(hard_delete=True)
    assert WaterBillStatement.all_objects.filter(pk=statement_pk).exists() is False


def test_bill_soft_delete_does_not_remove_statement() -> None:
    bill = make_bill()
    statement = make_water_statement(bill=bill)
    bill.delete()  # soft (mixin) — does not walk the reverse relation
    statement.refresh_from_db()
    assert statement.is_deleted is False
    assert WaterBillStatement.objects.filter(pk=statement.pk).exists() is True


def test_reverse_accessor_water_statement() -> None:
    bill = make_bill()
    statement = make_water_statement(bill=bill)
    assert bill.water_statement == statement


def test_reverse_accessor_electricity_statement() -> None:
    bill = make_bill()
    statement = make_electricity_statement(bill=bill)
    assert bill.electricity_statement == statement


def test_supply_status_choices_default_active() -> None:
    statement = make_water_statement()
    assert statement.agua_status == SupplyStatus.ACTIVE
    assert statement.esgoto_status == SupplyStatus.ACTIVE
    statement.agua_status = SupplyStatus.CUT
    statement.esgoto_status = SupplyStatus.CUT
    statement.full_clean()
    statement.save()
    statement.refresh_from_db()
    assert statement.agua_status == SupplyStatus.CUT
    statement.agua_status = "frozen"
    with pytest.raises(ValidationError):
        statement.full_clean()


def test_nullable_reading_fields() -> None:
    water = make_water_statement(
        consumo_m3=10,
        leitura_anterior=None,
        leitura_atual=None,
        leitura_dias=None,
        data_leitura=None,
    )
    water.full_clean()
    assert water.leitura_anterior is None
    assert water.data_leitura is None
    power = make_electricity_statement(
        consumo_kwh=200,
        energia_injetada_kwh=None,
        leitura_anterior=None,
        leitura_atual=None,
        leitura_dias=None,
    )
    power.full_clean()
    assert power.energia_injetada_kwh is None
    assert power.leitura_anterior is None


def test_consumo_required() -> None:
    bill = make_bill()
    water = WaterBillStatement(bill=bill)
    with pytest.raises(ValidationError):
        water.full_clean()
    power = ElectricityBillStatement(bill=make_bill())
    with pytest.raises(ValidationError):
        power.full_clean()


def test_str_pt() -> None:
    water = make_water_statement(consumo_m3=158)
    power = make_electricity_statement(consumo_kwh=1752)
    assert "158" in str(water)
    assert "m³" in str(water)
    assert "1752" in str(power)
    assert "kWh" in str(power)


def test_reading_fields_persist() -> None:
    water = make_water_statement(
        consumo_m3=158,
        leitura_anterior=1000,
        leitura_atual=1158,
        leitura_dias=30,
        data_leitura=date(2026, 6, 1),
    )
    water.refresh_from_db()
    assert water.consumo_m3 == 158
    assert water.leitura_anterior == 1000
    assert water.leitura_atual == 1158
    assert water.leitura_dias == 30
    assert water.data_leitura == date(2026, 6, 1)
    power = make_electricity_statement(
        consumo_kwh=1752,
        energia_injetada_kwh=300,
        classe="Residencial",
        bandeira="Verde",
    )
    power.refresh_from_db()
    assert power.consumo_kwh == 1752
    assert power.energia_injetada_kwh == 300
    assert power.classe == "Residencial"
    assert power.bandeira == "Verde"
