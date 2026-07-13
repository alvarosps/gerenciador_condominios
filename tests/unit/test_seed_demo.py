"""seed_demo management command tests (fable-audit Fase 5 — modo demo).

Mock policy (tests/CLAUDE.md): nothing internal is mocked. The command, the ORM, and every
service it calls (BillService, BillPaymentService, CondoMonthCloseService, ReserveService)
are exercised for real via ``django.core.management.call_command`` against the pytest
database (``test_condominio`` — pytest.ini pins ``DEBUG=False`` for the whole suite, so tests
that need the guard to PASS explicitly opt into ``DEBUG=True`` via ``settings_override``; a
dedicated guard test confirms ``DEBUG=False`` is rejected even on a ``test_``-prefixed name).

A small, self-contained fixture subset (1 building, 2 apartments, 2 tenants, 2 leases, a
handful of rent payments/condo-finance rows, 1 user) covers the default/fast test path;
the full real dataset (30 leases, 475 rent payments, 18 months of condo finance) is exercised
by one @pytest.mark.slow smoke test (mirrors test_seed_condo_utilities.py's real-inventory
smoke test).
"""

import copy
import json
from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from core.management.commands.seed_demo import Command, _is_demo_or_test_db_name
from core.models import Apartment, Building, IPCAIndex, Lease, RentPayment, Tenant
from finances.models import (
    Bill,
    BillingAccount,
    Category,
    CondoMonthClose,
    CondoMonthCloseStatus,
    Employee,
    Reserve,
)

pytestmark = pytest.mark.django_db

_DEMO_PASSWORD = "Demo@2026"

_FIXTURE_DATA: dict[str, object] = {
    "_meta": {
        "scale_inventory": {
            "buildings": 1,
            "apartments": 2,
            "tenants": 2,
            "leases_active": 2,
            "rent_payments": 4,
        }
    },
    "buildings": [
        {
            "street_number": 1247,
            "name": "Residencial Riachuelo",
            "address": "Rua Riachuelo, 1247 - Centro Histórico, Porto Alegre - RS",
        }
    ],
    "apartments": [
        {
            "building_street_number": 1247,
            "number": 101,
            "rental_value": "950.00",
            "rental_value_double": "1215.00",
            "cleaning_fee": "120.00",
            "max_tenants": 2,
            "furnitures": ["Cama de solteiro", "Geladeira"],
        },
        {
            "building_street_number": 1247,
            "number": 102,
            "rental_value": "995.00",
            "rental_value_double": "1275.00",
            "cleaning_fee": "120.00",
            "max_tenants": 2,
            "furnitures": ["Cama de solteiro", "Geladeira"],
        },
    ],
    "tenants": [
        {
            "id_ref": "tenant_01",
            "name": "Marcelo Souza Martins",
            "cpf_cnpj": "160.260.650-16",
            "is_company": False,
            "phone": "(51) 91000-1000",
            "marital_status": "Solteiro(a)",
            "profession": "Analista de Sistemas",
            "due_day": 5,
        },
        {
            "id_ref": "tenant_02",
            "name": "Camila Oliveira Rocha",
            "cpf_cnpj": "348.621.595-75",
            "is_company": False,
            "phone": "(51) 91037-1073",
            "marital_status": "Casado(a)",
            "profession": "Professor(a)",
            "due_day": 10,
        },
    ],
    "dependents": [
        {
            "tenant_ref": "tenant_01",
            "name": "Dependente de Marcelo",
            "phone": "(51) 91000-1000",
            "cpf_cnpj": "",
        }
    ],
    "leases": [
        {
            "id_ref": "lease_01",
            "apartment_building": 1247,
            "apartment_number": 101,
            "responsible_tenant_ref": "tenant_01",
            "tenant_refs": ["tenant_01"],
            "number_of_tenants": 1,
            "start_date": "2024-03-01",
            "validity_months": 30,
            "tag_fee": "20.00",
            "rental_value": "950.00",
            "deposit_amount": "950.00",
            "cleaning_fee_paid": True,
            "tag_deposit_paid": True,
            "contract_generated": True,
            "contract_signed": True,
            "interfone_configured": True,
            "prepaid_until": None,
            "is_salary_offset": False,
            "last_rent_increase_date": None,
            "is_ended": False,
            "end_date": None,
        },
        {
            "id_ref": "lease_02",
            "apartment_building": 1247,
            "apartment_number": 102,
            "responsible_tenant_ref": "tenant_02",
            "tenant_refs": ["tenant_02"],
            "number_of_tenants": 1,
            "start_date": "2024-06-01",
            "validity_months": 30,
            "tag_fee": "20.00",
            "rental_value": "995.00",
            "deposit_amount": "995.00",
            "cleaning_fee_paid": True,
            "tag_deposit_paid": True,
            "contract_generated": True,
            "contract_signed": True,
            "interfone_configured": True,
            "prepaid_until": None,
            "is_salary_offset": True,
            "last_rent_increase_date": None,
            "is_ended": False,
            "end_date": None,
        },
    ],
    "ipca_index": [
        {"reference_month": "2025-01-01", "value": "6900.0000000000000"},
        {"reference_month": "2025-02-01", "value": "6928.9000000000000"},
    ],
    "rent_adjustments": [],
    "rent_payments": [
        {
            "lease_ref": "lease_01",
            "reference_month": "2025-01-01",
            "amount_paid": "950.00",
            "payment_date": "2025-01-05",
            "notes": "",
        },
        {
            "lease_ref": "lease_01",
            "reference_month": "2025-02-01",
            "amount_paid": "950.00",
            "payment_date": "2025-02-05",
            "notes": "",
        },
        {
            "lease_ref": "lease_02",
            "reference_month": "2025-01-01",
            "amount_paid": "995.00",
            "payment_date": "2025-01-10",
            "notes": "",
        },
        {
            "lease_ref": "lease_02",
            "reference_month": "2025-02-01",
            "amount_paid": "995.00",
            "payment_date": "2025-02-10",
            "notes": "",
        },
    ],
    "payment_proofs": [
        {
            "lease_ref": "lease_01",
            "reference_month": "2025-02-01",
            "pix_code": "00020126...DEMO",
            "status": "approved",
            "rejection_reason": "",
        }
    ],
    "condo_finance": {
        "categories": [
            {"name": "Água", "color": "#3B82F6", "parent": None, "sort_order": 1},
            {"name": "Folha de Pagamento", "color": "#EC4899", "parent": None, "sort_order": 2},
        ],
        "water_bills": [
            {
                "building_street_number": 1247,
                "competence_month": "2025-01-01",
                "due_date": "2025-01-10",
                "consumo_m3": 21,
                "amount": "108.78",
            }
        ],
        "electricity_bills": [],
        "internet_bills": [],
        "iptu_terms": [],
        "employee": {
            "name": "Raimundo Nonato da Silveira",
            "role": "Zelador",
            "payment_type": "mixed",
            "base_salary": "2100.00",
            "default_due_day": 5,
            "lease_ref_salary_offset": "lease_02",
            "payments": [
                {
                    "reference_month": "2025-01-01",
                    "base_salary": "2100.00",
                    "variable_amount": "45.00",
                    "rent_offset": "995.00",
                    "cleaning_count": 1,
                    "payment_date": "2025-01-05",
                    "is_paid": True,
                },
                {
                    "reference_month": "2025-02-01",
                    "base_salary": "2100.00",
                    "variable_amount": "0.00",
                    "rent_offset": "995.00",
                    "cleaning_count": 0,
                    "payment_date": "2025-02-05",
                    "is_paid": True,
                },
            ],
        },
        "reserve": {
            "name": "Reserva Teste",
            "movements": [
                {
                    "kind": "deposit",
                    "amount": "200.00",
                    "movement_date": "2025-01-15",
                    "reference": "Aporte inicial",
                    "notes": "",
                }
            ],
        },
    },
    "users": [
        {
            "id_ref": "user_admin",
            "username": "gestor.demo",
            "email": "gestor.demo@demo.local",
            "first_name": "Gestor",
            "last_name": "Demo",
            "is_staff": True,
            "is_superuser": True,
            "role": "admin",
        },
        {
            "id_ref": "user_tenant_pontual",
            "username": "inquilino.pontual",
            "email": "inquilino.pontual@demo.local",
            "first_name": "Juliana",
            "last_name": "Ribeiro Correia",
            "is_staff": False,
            "is_superuser": False,
            "role": "tenant",
            "tenant_ref": "tenant_01",
        },
        {
            "id_ref": "user_tenant_onboarding",
            "username": "inquilino.onboarding",
            "email": "inquilino.onboarding@demo.local",
            "first_name": "Onboarding",
            "last_name": "Sem Locação",
            "is_staff": False,
            "is_superuser": False,
            "role": "tenant",
            "tenant_ref": None,
        },
    ],
}

REAL_SEED_PATH = Path("scripts/data/demo_seed_data.json")


def _write_fixture(tmp_path: Path, data: dict[str, object] | None = None) -> str:
    payload = _FIXTURE_DATA if data is None else data
    path = tmp_path / "demo_seed_data_test.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _run(file_path: str, *, reset: bool = False, verify: bool = False) -> None:
    args = ["seed_demo", "--file", file_path]
    if reset:
        args.append("--reset")
    if verify:
        args.append("--verify")
    call_command(*args)


# ------------------------------------------------------------------ guard


def test_guard_db_name_predicate_rejects_non_demo_non_test_names() -> None:
    """The pure predicate behind the guard's name check (extracted so it is testable without
    mutating settings.DATABASES, which Django's override_settings warns about) rejects a real
    production-shaped name like 'condominio' but accepts 'condominio_demo' / 'test_condominio'."""
    assert _is_demo_or_test_db_name("condominio") is False
    assert _is_demo_or_test_db_name("condominio_demo") is True
    assert _is_demo_or_test_db_name("test_condominio") is True
    assert _is_demo_or_test_db_name("test_condominio_gw0") is True


def test_guard_blocks_when_debug_false(tmp_path: Path) -> None:
    """The pytest database is 'test_condominio' (accepted by the name check) but pytest.ini
    pins DEBUG=False — the guard must still reject, proving the DEBUG check is enforced even
    when the name check alone would pass."""
    file_path = _write_fixture(tmp_path)
    with pytest.raises(CommandError) as exc_info:
        _run(file_path)
    assert "DEBUG" in str(exc_info.value)


def test_guard_passes_with_test_prefixed_db_and_debug_true(tmp_path: Path) -> None:
    """Both conditions satisfied (test_condominio + DEBUG=True) — the guard is a no-op and the
    seed proceeds."""
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)
    assert Building.objects.count() == 1


# ------------------------------------------------------------------ seeding


def test_seed_creates_expected_counts_from_fixture_subset(tmp_path: Path) -> None:
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)

    assert Building.objects.count() == 1
    assert Apartment.objects.count() == 2
    assert Tenant.objects.count() == 2
    assert Lease.objects.count() == 2
    assert RentPayment.objects.count() == 4
    assert IPCAIndex.objects.count() == 2
    assert Category.objects.count() == 2
    assert BillingAccount.objects.count() == 1  # 1 water account (1247)
    assert Bill.objects.count() == 3  # 1 water bill + 2 payroll bills
    assert Employee.objects.count() == 1
    assert Reserve.objects.count() == 1


def test_seed_pays_condo_bills_via_bill_payment_service(tmp_path: Path) -> None:
    """The water bill and both payroll bills are PAID (not just created) — the seed routes
    through BillPaymentService.pay, not a raw Payment.objects.create."""
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)

    for bill in Bill.objects.all():
        annotated = Bill.objects.with_amounts(date(2025, 6, 1)).get(pk=bill.pk)
        assert annotated.payment_status == "paid"


def test_seed_closes_historical_months_leaving_last_month_open(tmp_path: Path) -> None:
    """CondoMonthCloseService.close is used (not a raw CondoMonthClose.objects.create) — the
    fixture's rent_tracking_start_date (2025-01-01, set by the command) allows a chronological
    close of every month through the one before the dataset's implicit 'current' boundary."""
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)

    closed = CondoMonthClose.objects.filter(status=CondoMonthCloseStatus.CLOSED)
    assert closed.exists()


def test_seed_creates_lease_tenants_with_password_and_login(tmp_path: Path) -> None:
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)

    assert authenticate(username="inquilino.pontual", password=_DEMO_PASSWORD) is not None
    tenant = Tenant.objects.get(cpf_cnpj="16026065016")
    assert tenant.user is not None
    assert tenant.user.username == "inquilino.pontual"


def test_seed_onboarding_user_has_no_tenant_link(tmp_path: Path) -> None:
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)

    onboarding = User.objects.get(username="inquilino.onboarding")
    assert not hasattr(onboarding, "tenant_profile") or onboarding.tenant_profile is None


# ------------------------------------------------------------------ idempotency / reset


def test_seed_without_reset_aborts_when_data_exists(tmp_path: Path) -> None:
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path)
        with pytest.raises(CommandError) as exc_info:
            _run(file_path)
    assert "--reset" in str(exc_info.value)


def test_reset_reseeds_cleanly_without_duplication(tmp_path: Path) -> None:
    """--reset run twice in a row leaves identical counts (hard delete + full repopulate,
    not an accumulation)."""
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path, reset=True)
        first_counts = (
            Building.objects.count(),
            Apartment.objects.count(),
            Tenant.objects.count(),
            Lease.objects.count(),
            RentPayment.objects.count(),
            Bill.objects.count(),
        )
        _run(file_path, reset=True)
        second_counts = (
            Building.objects.count(),
            Apartment.objects.count(),
            Tenant.objects.count(),
            Lease.objects.count(),
            RentPayment.objects.count(),
            Bill.objects.count(),
        )
    assert first_counts == second_counts
    assert first_counts == (1, 2, 2, 2, 4, 3)


def test_reset_without_prior_data_is_a_no_op_then_seeds(tmp_path: Path) -> None:
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path, reset=True)
    assert Building.objects.count() == 1


# ------------------------------------------------------------------ --verify


def test_verify_passes_on_the_fixture_subset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path, reset=True, verify=True)
    output = capsys.readouterr().out
    assert "TUDO PASS" in output
    assert "FAIL" not in output


def test_verify_detects_invalid_cpf(tmp_path: Path) -> None:
    """The _invalid_cpfs check (the CPF-validity item --verify reports as PASS/FAIL) runs the
    real CPFValidator, not a rubber-stamp: it is exercised directly against a DB row corrupted
    via bulk_update (bypasses Tenant.full_clean(), the only path seed_demo itself writes through
    — the seed pipeline never lets an invalid CPF in, so this is the only way to reach the FAIL
    branch and prove the check is real)."""
    file_path = _write_fixture(tmp_path)
    with override_settings(DEBUG=True):
        _run(file_path, reset=True)
        tenant = Tenant.objects.first()
        assert tenant is not None
        tenant.cpf_cnpj = "11111111111"  # structurally invalid (all digits repeated)
        Tenant.objects.bulk_update([tenant], ["cpf_cnpj"])

        invalid = Command()._invalid_cpfs()
    assert invalid == ["11111111111"]


# ------------------------------------------------------------------ file / error handling


def test_missing_file_raises_command_error(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    with override_settings(DEBUG=True), pytest.raises(CommandError) as exc_info:
        _run(str(missing))
    assert "does_not_exist.json" in str(exc_info.value)


def test_missing_building_reference_raises_command_error(tmp_path: Path) -> None:
    data = copy.deepcopy(_FIXTURE_DATA)
    apartments = data["apartments"]
    assert isinstance(apartments, list)
    first_apartment = apartments[0]
    assert isinstance(first_apartment, dict)
    first_apartment["building_street_number"] = 9999  # no such building in the dataset
    file_path = _write_fixture(tmp_path, data)
    with override_settings(DEBUG=True), pytest.raises(CommandError) as exc_info:
        _run(file_path)
    assert "9999" in str(exc_info.value)


# ------------------------------------------------------------------ real dataset (slow)


@pytest.mark.slow
def test_real_dataset_seed_and_verify_end_to_end() -> None:
    """SMOKE: the full real scripts/data/demo_seed_data.json seeds and --verify PASSes
    end-to-end (30 leases / 28 active, 475 rent payments, 18 months of condo finance)."""
    with override_settings(DEBUG=True):
        call_command("seed_demo", "--file", str(REAL_SEED_PATH), "--reset", "--verify")

    assert Building.objects.count() == 3
    assert Apartment.objects.count() == 34
    assert Tenant.objects.count() == 30
    assert Lease.objects.count() == 28  # ended leases (2) are soft-deleted
    assert RentPayment.objects.count() == 475
