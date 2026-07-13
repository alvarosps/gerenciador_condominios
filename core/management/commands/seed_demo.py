"""Management command: seed_demo (fable-audit Fase 5 — modo demo).

Seeds an exhaustive, self-consistent demo dataset (3 buildings, 34 kitnets, 30 tenants,
30 leases, 18 months of rent history, and the full condo-finance module) from
``scripts/data/demo_seed_data.json`` into a DEDICATED demo database — never the real one.

Safety (CRITICAL, non-negotiable): refuses to run unless the configured database name
contains "demo" or starts with "test_" (the pytest database), AND ``DEBUG`` is True. There
is no bypass flag; a production-shaped environment can never reach this command's writes.

Idempotent: without ``--reset`` the command aborts if any domain data already exists;
``--reset`` deletes every domain row (FK-safe order, hard delete) and reseeds from scratch.

Correctness: rows are created through the ORM (model ``clean()``/``full_clean()`` runs,
so an invalid seed row is a bug, not a silently accepted record) and, wherever a service
owns a money invariant, that service is used instead of a raw ``objects.create`` — condo
bill payments via ``BillPaymentService.pay``, monthly closes via
``CondoMonthCloseService.close``, reserve movements via ``ReserveService``. Bulk writes are
used only for pure historical facts with no service/signal side effect (``RentPayment``,
``IPCAIndex``), each instance still ``full_clean()``-ed first.

``--verify`` runs a battery of PASS/FAIL invariant checks after seeding (counts vs. the
JSON, CPF validity, cash continuity across closed months, login of the 3 tenant personas).
"""

import json
from argparse import ArgumentParser
from datetime import date
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Protocol, TypedDict, cast

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from core.models import (
    Apartment,
    Building,
    Condominium,
    Dependent,
    FinancialSettings,
    Furniture,
    IPCAIndex,
    Lease,
    PaymentProof,
    RentAdjustment,
    RentPayment,
    Tenant,
)
from core.services.rent_schedule_service import RentScheduleService
from core.services.timezone import today_sp
from core.validators.brazilian import CNPJValidator, CPFValidator
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLineItem,
    Category,
    CondoMonthClose,
    CondoMonthCloseStatus,
    Employee,
    Payment,
    PaymentAllocation,
    Reserve,
    ReserveMovement,
)
from finances.services.bill_payment_service import BillPaymentService
from finances.services.bill_service import (
    BillDraft,
    BillLineInput,
    BillService,
    ElectricityStatementInput,
    StatementInput,
    WaterStatementInput,
)
from finances.services.condo_balance_service import CondoBalanceService, _next_month
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.reserve_service import ReserveService

_DEFAULT_FILE = "scripts/data/demo_seed_data.json"
_DEMO_PASSWORD = "Demo@2026"

_ERR_NOT_DEMO_DB = (
    "seed_demo recusa rodar: o banco configurado ('{name}') não é um banco de demo/teste "
    "(precisa conter 'demo' ou começar com 'test_'). NUNCA rode este comando contra o banco "
    "real — configure DB_NAME=condominio_demo (ou equivalente) antes de continuar."
)
_ERR_NOT_DEBUG = "seed_demo recusa rodar com DEBUG=False — configure DEBUG=True no ambiente demo."
_ERR_FILE_MISSING = "Arquivo de seed não encontrado: {path}"
_ERR_DATA_EXISTS = (
    "Já existem dados de domínio neste banco. Use --reset para limpar e repovoar, "
    "ou aponte para um banco vazio."
)
_ERR_BUILDING_MISSING = "Prédio com street_number={number} não encontrado no dataset."
_ERR_TENANT_MISSING = "Inquilino com id_ref={ref} não encontrado no dataset."
_ERR_LEASE_MISSING = "Locação com id_ref={ref} não encontrada no dataset."


class _HardDeletable(Protocol):
    """A model class exposing ``all_objects`` (every model in _SOFT_DELETE_RESET_MODELS defines
    it) — the shape needed by ``_reset`` (django-stubs cannot unify a heterogeneous tuple of
    model classes' manager attributes, hence this narrow structural type read via cast)."""

    __name__: str
    all_objects: models.Manager[models.Model]


class _PlainDeletable(Protocol):
    """A model class with only the default ``objects`` manager (no SoftDeleteMixin) — the shape
    needed for _PLAIN_RESET_MODELS (IPCAIndex, CondoMonthClose)."""

    __name__: str
    objects: models.Manager[models.Model]


# SoftDeleteMixin models cleared by --reset, in FK-safe (child -> parent) order. Hard delete (the
# demo database is disposable; soft-delete would leave rows the uniqueness constraints still see).
# PaymentAllocation/Payment first: PaymentAllocation.bill is PROTECT, so a live allocation blocks
# deleting its Bill (ReserveMovement.payment is SET_NULL — no such ordering constraint there).
_SOFT_DELETE_RESET_MODELS: tuple[type[models.Model], ...] = (
    PaymentAllocation,
    Payment,
    ReserveMovement,
    Reserve,
    Bill,  # cascades BillLineItem/statements via CASCADE FKs.
    Employee,
    BillingAccount,
    Category,
    PaymentProof,
    RentAdjustment,
    RentPayment,
    Dependent,
    Lease,
    Tenant,
    Apartment,
    Building,
)

# Models with only a default ``objects`` manager (no SoftDeleteMixin) — cleared via the plain
# manager instead of ``all_objects``. CondoMonthClose first (references Condominium/no children).
_PLAIN_RESET_MODELS: tuple[type[models.Model], ...] = (CondoMonthClose, IPCAIndex)

_MINIMAL_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100feff0300000005fe02fea739e100000000"
    "49454e44ae426082"
)


class _Inventory(TypedDict, total=False):
    buildings: int
    apartments: int
    tenants: int
    dependents: int
    leases: int
    ipca_index: int
    rent_adjustments: int
    rent_payments: int
    payment_proofs: int
    finance_categories: int
    billing_accounts: int
    water_bills: int
    electricity_bills: int
    internet_bills: int
    iptu_installments: int
    employees: int
    employee_payroll_bills: int
    reserve_movements: int
    users: int


def _money(value: object) -> Decimal:
    """Money as Decimal from a JSON number/string — never via float (design / coding-standards)."""
    return Decimal(str(value))


def _as_date(value: object) -> date:
    return date.fromisoformat(str(value))


def _is_demo_or_test_db_name(db_name: str) -> bool:
    """Pure predicate behind the safety guard's name check — a database name is acceptable
    only if it contains "demo" or starts with "test_" (the pytest database). Extracted so the
    guard's logic is unit-testable without touching ``settings.DATABASES`` (which Django's
    ``override_settings`` warns about mutating mid-test-run)."""
    return "demo" in db_name or db_name.startswith("test_")


class _BillAmountPaid(Protocol):
    # Bill.objects.with_amounts(today) annotates amount_paid; django-stubs does not propagate
    # dynamic annotations onto the model instance, so it is read via this typed cast (mirrors
    # BillPaymentService._BillRemaining).
    amount_paid: Decimal


class Command(BaseCommand):
    help = "Seed the exhaustive demo dataset (fable-audit Fase 5) into a demo-only database."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--file", default=_DEFAULT_FILE)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--verify", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        self._guard_demo_database()
        file_path = str(options["file"])
        reset = bool(options["reset"])
        verify = bool(options["verify"])
        data = self._load(file_path)

        self._refs: dict[str, object] = {}
        self._buildings: dict[int, Building] = {}
        self._accounts: dict[tuple[int, BillingAccountType], BillingAccount] = {}
        self._categories: dict[str, Category] = {}
        self.inventory: _Inventory = {}

        if reset:
            self._reset()
        else:
            self._guard_no_existing_data()

        with transaction.atomic():
            self._seed_financial_settings(data)
            self._seed_buildings(data)
            self._seed_apartments(data)
            self._seed_tenants(data)
            self._seed_dependents(data)
            self._seed_leases(data)
            self._seed_ipca_index(data)
            self._seed_rent_adjustments(data)
            self._seed_rent_payments(data)
            self._seed_payment_proofs(data)
            self._seed_condo_finance(data)
            self._seed_users(data)

        self.stdout.write(self.style.SUCCESS(self._render_inventory()))

        if verify:
            self.stdout.write("")
            self._run_verification(data)

    # ------------------------------------------------------------------ safety guard

    def _guard_demo_database(self) -> None:
        db_name = str(settings.DATABASES["default"]["NAME"])
        if not _is_demo_or_test_db_name(db_name):
            raise CommandError(_ERR_NOT_DEMO_DB.format(name=db_name))
        if not settings.DEBUG:
            raise CommandError(_ERR_NOT_DEBUG)

    def _guard_no_existing_data(self) -> None:
        if Building.objects.with_deleted().exists() or Tenant.objects.with_deleted().exists():
            raise CommandError(_ERR_DATA_EXISTS)

    # ------------------------------------------------------------------ loading

    def _load(self, file_path: str) -> dict[str, object]:
        path = Path(file_path)
        if not path.exists():
            raise CommandError(_ERR_FILE_MISSING.format(path=path))
        with path.open(encoding="utf-8") as handle:
            data: dict[str, object] = json.load(handle)
        return data

    def _section(self, data: dict[str, object], key: str) -> list[dict[str, object]]:
        section = data.get(key, [])
        if not isinstance(section, list):
            return []
        return [item for item in section if isinstance(item, dict)]

    # ------------------------------------------------------------------ reset

    def _reset(self) -> None:
        """Report the model's OWN row count (queried before delete), never Django's delete()
        total — that total includes cascaded rows of unrelated models (e.g. deleting Apartments
        cascades the furniture M2M through-table), which would misreport this model's count."""
        self.stdout.write("--reset: limpando dados de domínio existentes...")
        with transaction.atomic():
            for raw_plain_model in _PLAIN_RESET_MODELS:
                plain_model = cast(_PlainDeletable, raw_plain_model)
                count = plain_model.objects.count()
                plain_model.objects.all().delete()
                if count:
                    self.stdout.write(f"  - {plain_model.__name__}: {count} registros removidos")
            for raw_model in _SOFT_DELETE_RESET_MODELS:
                if raw_model is Category:
                    self._reset_categories()  # self-FK PROTECT: children before roots.
                    continue
                model = cast(_HardDeletable, raw_model)
                count = model.all_objects.count()
                model.all_objects.all().delete()
                if count:
                    self.stdout.write(f"  - {model.__name__}: {count} registros removidos")
            demo_users = User.objects.filter(email__endswith="@demo.local")
            count = demo_users.count()
            demo_users.delete()
            if count:
                self.stdout.write(f"  - User (demo): {count} registros removidos")

    def _reset_categories(self) -> None:
        """Delete children (non-null parent) before roots — Category.parent is self-FK PROTECT,
        so a single bulk delete() over the whole table can hit a live child and raise."""
        total = Category.all_objects.count()
        Category.all_objects.filter(parent__isnull=False).delete()
        Category.all_objects.filter(parent__isnull=True).delete()
        if total:
            self.stdout.write(f"  - Category: {total} registros removidos")

    # ------------------------------------------------------------------ core domain

    def _seed_financial_settings(self, data: dict[str, object]) -> None:
        """Tracking boundary anchored at the dataset's earliest month (jan/2025) so every
        historical month can be closed chronologically (CondoMonthCloseService._guard_no_gap)."""
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": Decimal("0.00"),
                "initial_balance_date": date(2025, 1, 1),
                "rent_tracking_start_date": date(2025, 1, 1),
            },
        )

    def _seed_buildings(self, data: dict[str, object]) -> None:
        items = self._section(data, "buildings")
        self.stdout.write(f"Prédios ({len(items)})...")
        for item in items:
            street_number = int(str(item["street_number"]))
            building = Building(
                street_number=street_number,
                name=str(item["name"]),
                address=str(item["address"]),
            )
            building.full_clean()
            building.save()
            self._buildings[street_number] = building
        self.inventory["buildings"] = len(items)

    def _get_building(self, street_number: int) -> Building:
        if street_number not in self._buildings:
            raise CommandError(_ERR_BUILDING_MISSING.format(number=street_number))
        return self._buildings[street_number]

    def _seed_apartments(self, data: dict[str, object]) -> None:
        items = self._section(data, "apartments")
        self.stdout.write(f"Apartamentos ({len(items)})...")
        for item in items:
            building = self._get_building(int(str(item["building_street_number"])))
            apartment = Apartment(
                building=building,
                number=int(str(item["number"])),
                rental_value=_money(item["rental_value"]),
                rental_value_double=_money(item["rental_value_double"]),
                cleaning_fee=_money(item["cleaning_fee"]),
                max_tenants=int(str(item["max_tenants"])),
            )
            apartment.full_clean()
            apartment.save()
            furniture_names = item.get("furnitures", [])
            if isinstance(furniture_names, list):
                for name in furniture_names:
                    furniture, _created = Furniture.objects.get_or_create(name=str(name))
                    apartment.furnitures.add(furniture)
            self._refs[f"apartment_{building.street_number}_{apartment.number}"] = apartment
        self.inventory["apartments"] = len(items)

    def _seed_tenants(self, data: dict[str, object]) -> None:
        items = self._section(data, "tenants")
        self.stdout.write(f"Inquilinos ({len(items)})...")
        for item in items:
            tenant = Tenant(
                name=str(item["name"]),
                cpf_cnpj=str(item["cpf_cnpj"]),
                is_company=bool(item["is_company"]),
                phone=str(item["phone"]),
                marital_status=str(item["marital_status"]),
                profession=str(item["profession"]),
                due_day=int(str(item["due_day"])),
            )
            tenant.full_clean()
            tenant.save()
            self._refs[str(item["id_ref"])] = tenant
        self.inventory["tenants"] = len(items)

    def _get_tenant(self, ref: str) -> Tenant:
        tenant = self._refs.get(ref)
        if not isinstance(tenant, Tenant):
            raise CommandError(_ERR_TENANT_MISSING.format(ref=ref))
        return tenant

    def _seed_dependents(self, data: dict[str, object]) -> None:
        items = self._section(data, "dependents")
        self.stdout.write(f"Dependentes ({len(items)})...")
        for item in items:
            tenant = self._get_tenant(str(item["tenant_ref"]))
            dependent = Dependent(
                tenant=tenant,
                name=str(item["name"]),
                phone=str(item["phone"]),
                cpf_cnpj=str(item.get("cpf_cnpj", "")),
            )
            dependent.full_clean()
            dependent.save()
        self.inventory["dependents"] = len(items)

    def _seed_leases(self, data: dict[str, object]) -> None:
        items = self._section(data, "leases")
        self.stdout.write(f"Locações ({len(items)})...")
        for item in items:
            building = self._get_building(int(str(item["apartment_building"])))
            apartment_number = int(str(item["apartment_number"]))
            apartment = self._refs[f"apartment_{building.street_number}_{apartment_number}"]
            if not isinstance(apartment, Apartment):
                raise CommandError(_ERR_BUILDING_MISSING.format(number=building.street_number))
            responsible = self._get_tenant(str(item["responsible_tenant_ref"]))
            lease = Lease(
                apartment=apartment,
                responsible_tenant=responsible,
                number_of_tenants=int(str(item["number_of_tenants"])),
                start_date=_as_date(item["start_date"]),
                validity_months=int(str(item["validity_months"])),
                tag_fee=_money(item["tag_fee"]),
                rental_value=_money(item["rental_value"]),
                deposit_amount=_money(item["deposit_amount"]),
                cleaning_fee_paid=bool(item["cleaning_fee_paid"]),
                tag_deposit_paid=bool(item["tag_deposit_paid"]),
                contract_generated=bool(item["contract_generated"]),
                contract_signed=bool(item["contract_signed"]),
                interfone_configured=bool(item["interfone_configured"]),
                prepaid_until=(
                    _as_date(item["prepaid_until"]) if item.get("prepaid_until") else None
                ),
                is_salary_offset=bool(item["is_salary_offset"]),
                last_rent_increase_date=(
                    _as_date(item["last_rent_increase_date"])
                    if item.get("last_rent_increase_date")
                    else None
                ),
            )
            lease.full_clean()
            lease.save()
            tenant_refs = item.get("tenant_refs", [])
            if isinstance(tenant_refs, list):
                for tenant_ref in tenant_refs:
                    lease.tenants.add(self._get_tenant(str(tenant_ref)))
            if bool(item["is_ended"]) and item.get("end_date"):
                lease.delete(deleted_by=None)
            self._refs[str(item["id_ref"])] = lease
        # is_rented is synced by LeaseService on the normal create path, not by the ORM —
        # reconcile explicitly so vacancy counts match reality.
        Apartment.objects.filter(leases__isnull=False, leases__is_deleted=False).update(
            is_rented=True
        )
        Apartment.objects.exclude(leases__is_deleted=False).update(is_rented=False)
        self.inventory["leases"] = len(items)

    def _get_lease(self, ref: str) -> Lease:
        lease = self._refs.get(ref)
        if not isinstance(lease, Lease):
            raise CommandError(_ERR_LEASE_MISSING.format(ref=ref))
        return lease

    def _seed_ipca_index(self, data: dict[str, object]) -> None:
        items = self._section(data, "ipca_index")
        self.stdout.write(f"Índice IPCA ({len(items)})...")
        rows: list[IPCAIndex] = []
        for item in items:
            row = IPCAIndex(
                reference_month=_as_date(item["reference_month"]),
                value=_money(item["value"]),
            )
            row.full_clean()
            rows.append(row)
        IPCAIndex.objects.bulk_create(rows)
        self.inventory["ipca_index"] = len(items)

    def _seed_rent_adjustments(self, data: dict[str, object]) -> None:
        """Applied directly from the dataset (percentages pre-validated against the real IPCA
        series) — updates lease.rental_value the same way RentAdjustmentService would."""
        items = self._section(data, "rent_adjustments")
        self.stdout.write(f"Reajustes de aluguel ({len(items)})...")
        for item in items:
            lease = self._get_lease(str(item["lease_ref"]))
            adjustment_date = _as_date(item["adjustment_date"])
            adjustment = RentAdjustment(
                lease=lease,
                adjustment_date=adjustment_date,
                percentage=_money(item["percentage"]),
                previous_value=_money(item["previous_value"]),
                new_value=_money(item["new_value"]),
                apartment_updated=bool(item["apartment_updated"]),
            )
            adjustment.full_clean()
            adjustment.save()
            lease.rental_value = adjustment.new_value
            lease.last_rent_increase_date = adjustment_date
            lease.save()
            if adjustment.apartment_updated:
                # update_fields: a full save() would write back the stale in-memory
                # is_rented captured before the reconciliation in _seed_leases.
                lease.apartment.rental_value = adjustment.new_value
                lease.apartment.save(update_fields=["rental_value", "updated_at"])
        self.inventory["rent_adjustments"] = len(items)

    def _seed_rent_payments(self, data: dict[str, object]) -> None:
        items = self._section(data, "rent_payments")
        self.stdout.write(f"Pagamentos de aluguel ({len(items)})...")
        rows: list[RentPayment] = []
        for item in items:
            lease = self._get_lease(str(item["lease_ref"]))
            row = RentPayment(
                lease=lease,
                reference_month=_as_date(item["reference_month"]),
                amount_paid=_money(item["amount_paid"]),
                payment_date=_as_date(item["payment_date"]),
                notes=str(item.get("notes", "")),
            )
            row.full_clean()
            rows.append(row)
        RentPayment.objects.bulk_create(rows)
        self.inventory["rent_payments"] = len(items)

    def _seed_payment_proofs(self, data: dict[str, object]) -> None:
        """No real file: a minimal in-memory PNG (ContentFile) stands in for the PIX receipt."""
        items = self._section(data, "payment_proofs")
        self.stdout.write(f"Comprovantes de pagamento ({len(items)})...")
        for index, item in enumerate(items, start=1):
            lease = self._get_lease(str(item["lease_ref"]))
            proof = PaymentProof(
                lease=lease,
                reference_month=_as_date(item["reference_month"]),
                pix_code=str(item.get("pix_code", "")),
                status=str(item["status"]),
                rejection_reason=str(item.get("rejection_reason", "")),
            )
            proof.file.save(f"demo_proof_{index}.png", ContentFile(_MINIMAL_PNG_BYTES), save=False)
            proof.full_clean()
            proof.save()
        self.inventory["payment_proofs"] = len(items)

    # ------------------------------------------------------------------ condo finance

    def _seed_condo_finance(self, data: dict[str, object]) -> None:
        condo_finance = data.get("condo_finance")
        if not isinstance(condo_finance, dict):
            return
        condominium = Condominium.get_default()
        if condominium is None:
            return
        self._seed_finance_categories(condominium, condo_finance)
        self._seed_billing_accounts(condominium, condo_finance)
        self._seed_utility_bills(condominium, condo_finance)
        self._seed_iptu_terms(condominium, condo_finance)
        self._seed_employee(condominium, condo_finance)
        self._seed_reserve(condominium, condo_finance)
        self._close_historical_months()

    def _seed_finance_categories(
        self, condominium: Condominium, condo_finance: dict[str, object]
    ) -> None:
        items = condo_finance.get("categories", [])
        if not isinstance(items, list):
            return
        self.stdout.write(f"Categorias financeiras ({len(items)})...")
        # Two passes: roots first (parent=None), then children (parent resolved by name) —
        # the dataset's `parent` field is a category NAME, not an id.
        pending: list[dict[str, object]] = [item for item in items if isinstance(item, dict)]
        roots = [item for item in pending if item.get("parent") is None]
        children = [item for item in pending if item.get("parent") is not None]
        for item in roots:
            self._create_finance_category(condominium, item, parent=None)
        for item in children:
            parent = self._categories[str(item["parent"])]
            self._create_finance_category(condominium, item, parent=parent)
        self.inventory["finance_categories"] = len(pending)

    def _create_finance_category(
        self, condominium: Condominium, item: dict[str, object], parent: Category | None
    ) -> None:
        category = Category(
            condominium=condominium,
            name=str(item["name"]),
            parent=parent,
            color=str(item.get("color", "")),
            sort_order=int(str(item.get("sort_order", 0))),
        )
        category.full_clean()
        category.save()
        self._categories[category.name] = category

    def _seed_billing_accounts(
        self, condominium: Condominium, condo_finance: dict[str, object]
    ) -> None:
        """One typed BillingAccount per (building, account_type) inferred from the utility
        bill sections — the dataset has no explicit accounts section (per-fatura only)."""
        specs: dict[tuple[int, BillingAccountType], str] = {}
        for section, account_type, name_prefix in (
            ("water_bills", BillingAccountType.WATER, "Água DMAE"),
            ("electricity_bills", BillingAccountType.ELECTRICITY, "Luz CEEE"),
            ("internet_bills", BillingAccountType.INTERNET, "Internet"),
        ):
            for item in self._section(condo_finance, section):
                street_number = int(str(item["building_street_number"]))
                specs[(street_number, account_type)] = name_prefix
        for item in self._section(condo_finance, "iptu_terms"):
            street_number = int(str(item["building_street_number"]))
            specs[(street_number, BillingAccountType.IPTU)] = "IPTU"

        self.stdout.write(f"Contas de serviço ({len(specs)})...")
        for (street_number, account_type), name_prefix in specs.items():
            building = self._get_building(street_number)
            account = BillingAccount(
                condominium=condominium,
                building=building,
                name=f"{name_prefix} {street_number}",
                account_type=account_type,
                external_identifier=f"DEMO-{account_type}-{street_number}",
                default_due_day=10,
                expected_amount=Decimal("0.00"),
            )
            account.full_clean()
            account.save()
            self._accounts[(street_number, account_type)] = account
        self.inventory["billing_accounts"] = len(specs)

    def _seed_utility_bills(
        self, condominium: Condominium, condo_finance: dict[str, object]
    ) -> None:
        self._seed_water_bills(condominium, condo_finance)
        self._seed_electricity_bills(condominium, condo_finance)
        self._seed_internet_bills(condominium, condo_finance)

    def _draft_for(
        self,
        condominium: Condominium,
        building: Building,
        account: BillingAccount,
        item: dict[str, object],
    ) -> BillDraft:
        return BillDraft(
            condominium=condominium,
            building=building,
            billing_account=account,
            category=self._category_for_account(account),
            competence_month=_as_date(item["competence_month"]),
            due_date=_as_date(item["due_date"]),
            description=account.name,
            behavior="recurring",
        )

    def _category_for_account(self, account: BillingAccount) -> Category | None:
        by_type: dict[str, str] = {
            BillingAccountType.WATER: "Água",
            BillingAccountType.ELECTRICITY: "Luz",
            BillingAccountType.INTERNET: "Internet",
            BillingAccountType.IPTU: "IPTU",
        }
        name = by_type.get(account.account_type)
        return self._categories.get(name) if name else None

    def _seed_water_bills(self, condominium: Condominium, condo_finance: dict[str, object]) -> None:
        items = self._section(condo_finance, "water_bills")
        self.stdout.write(f"Faturas de água ({len(items)})...")
        for item in items:
            building = self._get_building(int(str(item["building_street_number"])))
            account = self._accounts[(building.street_number, BillingAccountType.WATER)]
            amount = _money(item["amount"])
            lines: list[BillLineInput] = [
                {"description": "Consumo de água", "amount": amount, "is_offset": False}
            ]
            statement: StatementInput = WaterStatementInput(consumo_m3=int(str(item["consumo_m3"])))
            bill = BillService.create_with_lines(
                self._draft_for(condominium, building, account, item), lines, statement
            )
            BillPaymentService.pay(bill, bill.due_date)
        self.inventory["water_bills"] = len(items)

    def _seed_electricity_bills(
        self, condominium: Condominium, condo_finance: dict[str, object]
    ) -> None:
        items = self._section(condo_finance, "electricity_bills")
        self.stdout.write(f"Faturas de luz ({len(items)})...")
        for item in items:
            building = self._get_building(int(str(item["building_street_number"])))
            account = self._accounts[(building.street_number, BillingAccountType.ELECTRICITY)]
            amount = _money(item["amount"])
            lines: list[BillLineInput] = [
                {"description": "Consumo de energia", "amount": amount, "is_offset": False}
            ]
            statement: StatementInput = ElectricityStatementInput(
                consumo_kwh=int(str(item["consumo_kwh"]))
            )
            bill = BillService.create_with_lines(
                self._draft_for(condominium, building, account, item), lines, statement
            )
            BillPaymentService.pay(bill, bill.due_date)
        self.inventory["electricity_bills"] = len(items)

    def _seed_internet_bills(
        self, condominium: Condominium, condo_finance: dict[str, object]
    ) -> None:
        items = self._section(condo_finance, "internet_bills")
        self.stdout.write(f"Faturas de internet ({len(items)})...")
        for item in items:
            building = self._get_building(int(str(item["building_street_number"])))
            account = self._accounts[(building.street_number, BillingAccountType.INTERNET)]
            amount = _money(item["amount"])
            lines: list[BillLineInput] = [
                {"description": "Assinatura internet", "amount": amount, "is_offset": False}
            ]
            bill = BillService.create_with_lines(
                self._draft_for(condominium, building, account, item), lines, None
            )
            BillPaymentService.pay(bill, bill.due_date)
        self.inventory["internet_bills"] = len(items)

    def _installments_of(self, term: dict[str, object]) -> list[dict[str, object]]:
        raw = term.get("installments", [])
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    def _seed_iptu_terms(self, condominium: Condominium, condo_finance: dict[str, object]) -> None:
        """Each IPTU term's parcelas become standalone ONE_TIME bills (design mirrors
        seed_condo_utilities' opening-parcela pattern), paid at their own due_date."""
        terms = self._section(condo_finance, "iptu_terms")
        installment_count = sum(len(self._installments_of(term)) for term in terms)
        self.stdout.write(f"Termos IPTU ({len(terms)} termos, {installment_count} parcelas)...")
        category = self._categories.get("IPTU")
        for term in terms:
            building = self._get_building(int(str(term["building_street_number"])))
            account = self._accounts[(building.street_number, BillingAccountType.IPTU)]
            year = int(str(term["year"]))
            for raw in self._installments_of(term):
                number = int(str(raw["number"]))
                amount = _money(raw["amount"])
                due_date = _as_date(raw["due_date"])
                bill = Bill(
                    condominium=condominium,
                    building=building,
                    category=category,
                    billing_account=account,
                    competence_month=due_date,
                    due_date=due_date,
                    description=f"IPTU {year} parcela {number}/{term['installment_count']}",
                    behavior="one_time",
                )
                bill.full_clean()
                bill.save()
                line = BillLineItem(
                    bill=bill,
                    category=category,
                    description=bill.description,
                    amount=amount,
                    is_offset=False,
                )
                line.full_clean(exclude=["bill"])
                line.save()
                BillPaymentService.pay(bill, due_date)
        self.inventory["iptu_installments"] = installment_count

    def _seed_employee(self, condominium: Condominium, condo_finance: dict[str, object]) -> None:
        raw_employee = condo_finance.get("employee")
        if not isinstance(raw_employee, dict):
            return
        self.stdout.write("Funcionário + folha de pagamento...")
        lease_ref = raw_employee.get("lease_ref_salary_offset")
        lease = self._get_lease(str(lease_ref)) if lease_ref else None
        employee = Employee(
            condominium=condominium,
            name=str(raw_employee["name"]),
            role=str(raw_employee.get("role", "")),
            payment_type=str(raw_employee["payment_type"]),
            base_salary=_money(raw_employee["base_salary"]),
            default_due_day=int(str(raw_employee["default_due_day"])),
            lease=lease,
            is_active=True,
        )
        employee.full_clean()
        employee.save()
        category = self._categories.get("Folha de Pagamento")

        payments = raw_employee.get("payments", [])
        bills_created = 0
        if isinstance(payments, list):
            for payment in payments:
                if not isinstance(payment, dict):
                    continue
                self._seed_payroll_bill(condominium, employee, category, payment)
                bills_created += 1
        self.inventory["employees"] = 1
        self.inventory["employee_payroll_bills"] = bills_created

    def _seed_payroll_bill(
        self,
        condominium: Condominium,
        employee: Employee,
        category: Category | None,
        payment: dict[str, object],
    ) -> None:
        month_start = _as_date(payment["reference_month"])
        due_date = date(
            month_start.year,
            month_start.month,
            RentScheduleService.clamp_due_day(
                employee.default_due_day, month_start.year, month_start.month
            ),
        )
        bill = Bill(
            condominium=condominium,
            category=category,
            employee=employee,
            competence_month=month_start,
            due_date=due_date,
            description=f"Folha {employee.name}",
            behavior="recurring",
        )
        bill.full_clean()
        bill.save()

        base_salary = _money(payment["base_salary"])
        if base_salary > 0:
            base_line = BillLineItem(
                bill=bill, category=category, description="Salário base", amount=base_salary
            )
            base_line.full_clean(exclude=["bill"])
            base_line.save()

        variable_amount = _money(payment.get("variable_amount", 0))
        if variable_amount > 0:
            variable_line = BillLineItem(
                bill=bill,
                category=category,
                description="Variável (faxinas)",
                amount=variable_amount,
            )
            variable_line.full_clean(exclude=["bill"])
            variable_line.save()

        rent_offset = _money(payment.get("rent_offset", 0))
        if rent_offset > 0:
            offset_line = BillLineItem(
                bill=bill,
                category=category,
                description="Abatimento aluguel",
                amount=rent_offset,
                is_offset=True,
            )
            offset_line.full_clean(exclude=["bill"])
            offset_line.save()

        if bool(payment.get("is_paid")):
            payment_date = (
                _as_date(payment["payment_date"]) if payment.get("payment_date") else due_date
            )
            BillPaymentService.pay(bill, payment_date)

    def _seed_reserve(self, condominium: Condominium, condo_finance: dict[str, object]) -> None:
        raw_reserve = condo_finance.get("reserve")
        if not isinstance(raw_reserve, dict):
            return
        self.stdout.write("Reserva do condomínio...")
        reserve = Reserve(condominium=condominium, name=str(raw_reserve["name"]))
        reserve.full_clean()
        reserve.save()

        movements = raw_reserve.get("movements", [])
        count = 0
        if isinstance(movements, list):
            for movement in movements:
                if not isinstance(movement, dict):
                    continue
                kind = str(movement["kind"])
                amount = _money(movement["amount"])
                movement_date = _as_date(movement["movement_date"])
                reference = str(movement.get("reference", ""))
                notes = str(movement.get("notes", ""))
                if kind == "deposit":
                    ReserveService.deposit(
                        reserve, amount, movement_date, reference=reference, notes=notes
                    )
                else:
                    ReserveService.withdraw(
                        reserve, amount, movement_date, reference=reference, notes=notes
                    )
                count += 1
        self.inventory["reserve_movements"] = count

    def _close_historical_months(self) -> None:
        """Close every month from jan/2025 through mai/2026 (chronological, no gap); jun/2026
        stays open, as the demo's "current" month."""
        self.stdout.write("Fechando meses históricos (jan/2025 .. mai/2026)...")
        cursor = date(2025, 1, 1)
        last_open = date(2026, 6, 1)
        while cursor < last_open:
            CondoMonthCloseService.close(cursor.year, cursor.month)
            cursor += relativedelta(months=1)

    # ------------------------------------------------------------------ users

    def _seed_users(self, data: dict[str, object]) -> None:
        items = self._section(data, "users")
        self.stdout.write(f"Usuários/personas ({len(items)})...")
        for item in items:
            user = User(
                username=str(item["username"]),
                email=str(item["email"]),
                first_name=str(item.get("first_name", "")),
                last_name=str(item.get("last_name", "")),
                is_staff=bool(item.get("is_staff", False)),
                is_superuser=bool(item.get("is_superuser", False)),
            )
            user.set_password(_DEMO_PASSWORD)
            user.full_clean(exclude=["password"])
            user.save()
            tenant_ref = item.get("tenant_ref")
            if tenant_ref:
                tenant = self._get_tenant(str(tenant_ref))
                tenant.user = user
                tenant.save()
        self.inventory["users"] = len(items)

    # ------------------------------------------------------------------ output

    def _render_inventory(self) -> str:
        lines = ["Seed concluído. Inventário:"]
        for key, count in self.inventory.items():
            lines.append(f"  {key}: {count}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ verify

    def _check(self, label: str, ok: bool, detail: str = "") -> bool:
        status = "PASS" if ok else "FAIL"
        suffix = f" — {detail}" if detail else ""
        self.stdout.write(f"[{status}] {label}{suffix}")
        return ok

    def _tenant_persona_usernames(self, data: dict[str, object]) -> list[str]:
        """Usernames of every seeded tenant persona (role == 'tenant') — derived from the loaded
        dataset instead of hardcoded, so a reduced fixture (fewer personas) verifies correctly."""
        return [
            str(item["username"])
            for item in self._section(data, "users")
            if item.get("role") == "tenant"
        ]

    def _run_verification(self, data: dict[str, object]) -> None:
        self.stdout.write("Verificação (--verify):")
        all_ok = True

        meta = data.get("_meta", {})
        scale = meta.get("scale_inventory", {}) if isinstance(meta, dict) else {}

        all_ok &= self._check(
            "Contagem de prédios == JSON",
            Building.objects.count() == int(scale.get("buildings", -1)),
        )
        all_ok &= self._check(
            "Contagem de apartamentos == JSON",
            Apartment.objects.count() == int(scale.get("apartments", -1)),
        )
        all_ok &= self._check(
            "Contagem de inquilinos == JSON",
            Tenant.objects.count() == int(scale.get("tenants", -1)),
        )
        active_leases = Lease.objects.count()
        expected_active = int(scale.get("leases_active", -1))
        all_ok &= self._check(
            f"Locações ativas == {expected_active}",
            active_leases == expected_active,
            f"encontrado {active_leases}",
        )
        rented = Apartment.objects.filter(is_rented=True).count()
        all_ok &= self._check(
            f"Apartamentos is_rented == locações ativas ({expected_active})",
            rented == expected_active,
            f"encontrado {rented}",
        )
        expected_rent_payments = int(scale.get("rent_payments", -1))
        actual_rent_payments = RentPayment.objects.count()
        all_ok &= self._check(
            f"Contagem de pagamentos de aluguel == {expected_rent_payments}",
            actual_rent_payments == expected_rent_payments,
            f"encontrado {actual_rent_payments}",
        )

        invalid_cpfs = self._invalid_cpfs()
        all_ok &= self._check(
            "Nenhum CPF/CNPJ inválido entre os inquilinos",
            not invalid_cpfs,
            f"{len(invalid_cpfs)} inválido(s)" if invalid_cpfs else "",
        )

        all_ok &= self._check(
            "Bill.objects.with_amounts sem amount_paid negativo",
            not self._has_negative_amount_paid(),
        )

        all_ok &= self._check(
            "Continuidade de caixa entre meses fechados (cash_balance_end)",
            self._cash_continuity_ok(),
        )

        for username in self._tenant_persona_usernames(data):
            authenticated = authenticate(username=username, password=_DEMO_PASSWORD) is not None
            all_ok &= self._check(f"Login do persona '{username}'", authenticated)

        self.stdout.write("")
        if all_ok:
            self.stdout.write(self.style.SUCCESS("Verificação: TUDO PASS"))
        else:
            self.stdout.write(self.style.ERROR("Verificação: HÁ FALHAS (ver acima)"))

    def _invalid_cpfs(self) -> list[str]:
        invalid: list[str] = []
        for tenant in Tenant.objects.all():
            validator = CNPJValidator() if tenant.is_company else CPFValidator()
            try:
                validator(tenant.cpf_cnpj)
            except ValidationError:
                invalid.append(tenant.cpf_cnpj)
        return invalid

    def _has_negative_amount_paid(self) -> bool:
        annotated = cast(list[_BillAmountPaid], list(Bill.objects.with_amounts(today_sp())))
        return any(bill.amount_paid < 0 for bill in annotated)

    def _cash_continuity_ok(self) -> bool:
        """For every pair of consecutive closed months, month N's frozen cash_balance_end must
        equal the live cash_balance computed at the start of month N+1 (CondoBalanceService is
        the single source both close() and the dashboard read through)."""
        closes = list(
            CondoMonthClose.objects.filter(status=CondoMonthCloseStatus.CLOSED).order_by(
                "reference_month"
            )
        )
        for current, following in pairwise(closes):
            if _next_month(current.reference_month) != following.reference_month:
                continue  # a gap in closed months — not this check's concern.
            start_of_following = CondoBalanceService.cash_balance(following.reference_month)
            if current.cash_balance_end != start_of_following:
                return False
        return True
