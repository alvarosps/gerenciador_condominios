"""Regression tests for the fix_iptu_parcela_amounts management command.

The original seed materialized IPTU opening parcelas from ``saldo ÷ nº-parcelas`` instead of the
real per-parcela "Atualizado" value. This command re-applies the corrected values (from the seed
JSON) to the ALREADY-materialized ``Installment.amount`` + the standalone parcela ``Bill``'s single
``BillLineItem.amount`` + ``InstallmentPlan.total_amount``. The displayed value is the line amount,
so correcting only the schedule would not fix the screen — both must change.

Mock policy (tests/CLAUDE.md): only freezegun is mocked; the ORM, the seed command, and the fix
command are real (banco real, --reuse-db), exercised via call_command.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from freezegun import freeze_time

from finances.models import (
    Bill,
    Installment,
    InstallmentPlan,
    Payment,
    PaymentAllocation,
)
from tests.factories import make_building

pytestmark = pytest.mark.django_db

FROZEN = "2026-06-08 12:00:00"


def _term_fixture(*, total: float, current: float, nxt: float) -> dict[str, object]:
    """A minimal seed fixture: 1 IPTU account + term 992988 (parcelas 9 overdue + 10 open)."""
    return {
        "configuracoes": {
            "saldo_inicial": 0,
            "data_saldo_inicial": "2026-03-01",
            "rent_tracking_start_date": "2026-06-01",
        },
        "contas": [
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
        "termos_iptu": [
            {
                "predio_street_number": 836,
                "account_external_identifier": "516449",
                "termo": "992988",
                "installment_count": 10,
                "total_amount": total,
                "current_number": 9,
                "current_amount": current,
                "current_due_date": "2026-05-29",
                "next_number": 10,
                "next_amount": nxt,
                "next_due_date": "2026-06-30",
            },
        ],
    }


def _write(tmp_path: Path, data: dict[str, object], name: str) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _seed_wrong(tmp_path: Path) -> None:
    """Reproduce the WRONG (saldo÷count) state the original seed produced for term 992988."""
    make_building(street_number=836)
    wrong = _term_fixture(total=27181.69, current=2718.16, nxt=2718.25)
    call_command("seed_condo_utilities", "--file", _write(tmp_path, wrong, "wrong.json"))


def _corrected_file(tmp_path: Path) -> str:
    return _write(tmp_path, _term_fixture(total=1045.44, current=522.72, nxt=522.72), "fixed.json")


def _plan() -> InstallmentPlan:
    return InstallmentPlan.objects.get(description="IPTU termo 992988", embedded=False)


def _installment(number: int) -> Installment:
    return Installment.objects.get(plan=_plan(), number=number)


def _line_amount(number: int) -> Decimal:
    bill = Bill.objects.get(installment=_installment(number))
    return bill.line_items.get(is_deleted=False).amount


@freeze_time(FROZEN)
def test_fix_corrects_installment_line_and_total(tmp_path: Path) -> None:
    _seed_wrong(tmp_path)
    # Precondition: the seeded (wrong) state.
    assert _installment(9).amount == Decimal("2718.16")
    assert _line_amount(9) == Decimal("2718.16")
    assert _plan().total_amount == Decimal("27181.69")

    call_command("fix_iptu_parcela_amounts", "--file", _corrected_file(tmp_path))

    # Both the schedule (Installment) AND the realized line are corrected, plus the plan total.
    assert _installment(9).amount == Decimal("522.72")
    assert _installment(10).amount == Decimal("522.72")
    assert _line_amount(9) == Decimal("522.72")
    assert _line_amount(10) == Decimal("522.72")
    assert _plan().total_amount == Decimal("1045.44")


@freeze_time(FROZEN)
def test_fix_is_idempotent(tmp_path: Path) -> None:
    _seed_wrong(tmp_path)
    fixed = _corrected_file(tmp_path)
    call_command("fix_iptu_parcela_amounts", "--file", fixed)
    call_command("fix_iptu_parcela_amounts", "--file", fixed)  # second run = no-op
    assert _line_amount(9) == Decimal("522.72")
    assert _plan().total_amount == Decimal("1045.44")


@freeze_time(FROZEN)
def test_fix_dry_run_changes_nothing(tmp_path: Path) -> None:
    _seed_wrong(tmp_path)
    call_command("fix_iptu_parcela_amounts", "--file", _corrected_file(tmp_path), "--dry-run")
    assert _installment(9).amount == Decimal("2718.16")
    assert _line_amount(9) == Decimal("2718.16")
    assert _plan().total_amount == Decimal("27181.69")


@freeze_time(FROZEN)
def test_fix_skips_a_paid_bill(tmp_path: Path) -> None:
    """Defensive: a parcela whose Bill already has a PaymentAllocation is NOT mutated."""
    _seed_wrong(tmp_path)
    bill9 = Bill.objects.get(installment=_installment(9))
    payment = Payment.objects.create(
        condominium=bill9.condominium, payment_date=date(2026, 6, 8), amount=Decimal("2718.16")
    )
    PaymentAllocation.objects.create(payment=payment, bill=bill9, amount=Decimal("2718.16"))

    call_command("fix_iptu_parcela_amounts", "--file", _corrected_file(tmp_path))

    # Parcela 9 (paid) is left untouched; parcela 10 (unpaid) is still corrected.
    assert _installment(9).amount == Decimal("2718.16")
    assert _line_amount(9) == Decimal("2718.16")
    assert _line_amount(10) == Decimal("522.72")
