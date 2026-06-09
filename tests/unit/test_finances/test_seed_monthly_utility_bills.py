"""Fase 5 — fix_agua_embedded_installments (off-by-one) + the monthly água/luz fatura seed.

Mock policy (tests/CLAUDE.md): only freezegun; the ORM, the seed command, the fix command and
BillService are real (banco real, --reuse-db), exercised via call_command.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from finances.models import Bill, Installment, InstallmentPlan, WaterBillStatement
from freezegun import freeze_time

from tests.factories import make_building

pytestmark = pytest.mark.django_db

FROZEN = "2026-06-08 12:00:00"
WATER_836 = "117.111.0049.0519.00"


def _write(tmp_path: Path, data: dict[str, object], name: str) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _account_fixture(current_installment: int) -> dict[str, object]:
    return {
        "contas": [
            {
                "predio_street_number": 836,
                "account_type": "water",
                "name": "Água DMAE 836",
                "external_identifier": WATER_836,
                "secondary_identifier": "003419142",
                "supply_status": "active",
                "default_due_day": 4,
                "expected_amount": 0,
            }
        ],
        "planos_embutidos": [
            {
                "predio_street_number": 836,
                "account_type": "water",
                "account_external_identifier": WATER_836,
                "description": "Parcelamento DMAE água 836",
                "installment_count": 46,
                "current_installment": current_installment,
                "installment_amount": 94.48,
                "default_due_day": 4,
            }
        ],
    }


def _plan() -> InstallmentPlan:
    return InstallmentPlan.objects.get(description="Parcelamento DMAE água 836", embedded=True)


def _live_numbers() -> list[int]:
    return sorted(Installment.objects.filter(plan=_plan()).values_list("number", flat=True))


@freeze_time(FROZEN)
def test_fix_agua_rematerializes_off_by_one(tmp_path: Path) -> None:
    make_building(street_number=836)
    # Seed the WRONG state (current 24 → installments 24..46, parcela 24 dated 04/06).
    call_command(
        "seed_condo_utilities", "--file", _write(tmp_path, _account_fixture(24), "wrong.json")
    )
    assert _live_numbers()[0] == 24
    assert Installment.objects.get(plan=_plan(), number=24).due_date == date(2026, 6, 4)

    # Fix from the corrected current (23).
    call_command(
        "fix_agua_embedded_installments",
        "--file",
        _write(tmp_path, _account_fixture(23), "fix.json"),
    )

    assert _live_numbers() == list(range(23, 47))  # 23..46, parcela 23 now exists
    assert Installment.objects.get(plan=_plan(), number=23).due_date == date(2026, 6, 4)
    assert Installment.objects.get(plan=_plan(), number=24).due_date == date(2026, 7, 4)  # shifted


@freeze_time(FROZEN)
def test_fix_agua_idempotent_when_already_correct(tmp_path: Path) -> None:
    make_building(street_number=836)
    call_command(
        "seed_condo_utilities", "--file", _write(tmp_path, _account_fixture(23), "ok.json")
    )
    before = _live_numbers()
    call_command(
        "fix_agua_embedded_installments",
        "--file",
        _write(tmp_path, _account_fixture(23), "ok.json"),
    )
    assert before == _live_numbers() == list(range(23, 47))


@freeze_time(FROZEN)
def test_seed_monthly_fatura_creates_bill_statement_lines_and_bound_parcela(tmp_path: Path) -> None:
    make_building(street_number=836)
    fixture = _account_fixture(23)
    fixture["faturas_mensais"] = [
        {
            "account_type": "water",
            "account_external_identifier": WATER_836,
            "competence_month": "2026-05-01",
            "due_date": "2026-06-04",
            "description": "Água DMAE 836 — 05/2026",
            "statement": {
                "consumo_m3": 51,
                "leitura_anterior": 619,
                "leitura_atual": 670,
                "leitura_dias": 29,
                "agua_status": "active",
                "esgoto_status": "active",
            },
            "lines": [
                {"description": "Água", "amount": 660.00},
                {"description": "Esgoto", "amount": 528.00},
                {
                    "description": "Parcelamento de débitos 23/46",
                    "amount": 94.48,
                    "installment_number": 23,
                },
                {"description": "Multa", "amount": 2.31},
                {"description": "Juros de mora", "amount": 1.88},
                {"description": "Atualização monetária", "amount": 0.28},
            ],
        }
    ]
    call_command("seed_condo_utilities", "--file", _write(tmp_path, fixture, "fatura.json"))

    bill = Bill.objects.get(
        competence_month=date(2026, 5, 1), billing_account__external_identifier=WATER_836
    )
    annotated = Bill.objects.with_amounts(date(2026, 6, 8)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("1286.95")  # Σ lines = printed total

    statement = WaterBillStatement.objects.get(bill=bill)
    assert statement.consumo_m3 == 51
    assert statement.agua_status == "active"

    parcela_line = bill.line_items.get(is_deleted=False, installment__isnull=False)
    assert parcela_line.installment is not None
    assert parcela_line.installment.number == 23
    assert parcela_line.amount == Decimal("94.48")

    # Idempotent: re-run detects the existing bill and does not duplicate.
    call_command("seed_condo_utilities", "--file", _write(tmp_path, fixture, "fatura.json"))
    assert (
        Bill.objects.filter(
            competence_month=date(2026, 5, 1), billing_account__external_identifier=WATER_836
        ).count()
        == 1
    )
