"""Management command: seed_condo_utilities (design §13, Apêndice A — Fase 7, última).

Seeds the REAL condo utility/IPTU inventory of buildings 836/850 idempotently from
``scripts/data/condo_utilities_seed.json``: typed BillingAccounts (water/electricity/IPTU)
with identity, embedded InstallmentPlans (water 836/850, electricity 850), the 9 standalone
IPTU terms (``embedded=False`` plans pointing at the IPTU account) with ONLY the opening
parcelas materialized — current (overdue 29/05) + next (open 30/06) — at ``competence_month``
2026-06-01, and the 3 deferred 2026 IPTU debts (``Bill`` DEFERRED + 1 full-value
``BillLineItem`` + ``billing_account``). It does NOT generate recurring bills (the monthly
BillGenerationService does, on demand) and does NOT backfill pre-tracking paid parcelas.

Idempotent: every write is ``update_or_create``/``get_or_create`` on a natural key
(account = (building, account_type, external_identifier); plan = (billing_account, embedded,
description); deferred debt = (billing_account, competence_month); installment = (plan,
number)), so re-running never duplicates. ``--dry-run`` rolls everything back. ``--file``
overrides the JSON path. The buildings 836/850 must already exist (looked up by street_number).
"""

import json
from argparse import ArgumentParser
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Building, FinancialSettings
from finances.models import (
    Bill,
    BillBehavior,
    BillingAccount,
    BillLifecycleState,
    BillLineItem,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
)

# Opening parcelas are pinned to the first tracked month so an overdue parcela (due 29/05) does
# not create a pre-tracking month with a spurious negative net; the real due_date is preserved on
# the Bill/Installment (design §10.1). Single source.
_OPENING_COMPETENCE = date(2026, 6, 1)

_DEFAULT_FILE = "scripts/data/condo_utilities_seed.json"

_ERR_BUILDING_MISSING = "Prédio com street_number={number} não encontrado no banco."
_ERR_FILE_MISSING = "Arquivo de seed não encontrado: {path}"


def _money(value: object) -> Decimal:
    """Money as Decimal from a JSON number/string — never via float (design / coding-standards)."""
    return Decimal(str(value))


def _as_str(value: object) -> str:
    """Coerce a JSON value (typed ``object``) to ``str`` — single typed accessor (mypy strict)."""
    return str(value)


def _as_int(value: object) -> int:
    """Coerce a JSON value (typed ``object``) to ``int`` via its ``str`` form (mypy strict)."""
    return int(str(value))


def _as_date(value: object) -> date:
    """Parse an ISO ``YYYY-MM-DD`` JSON value (typed ``object``) into a ``date`` (mypy strict)."""
    return date.fromisoformat(str(value))


class Command(BaseCommand):
    help = "Seed real condo utility accounts/plans/IPTU debts (prédios 836 e 850)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--file", default=_DEFAULT_FILE)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        file_path = str(options["file"])
        dry_run = bool(options["dry_run"])
        data = self._load(file_path)

        self._buildings: dict[int, Building] = {}
        self._accounts: dict[str, BillingAccount] = {}
        self.stats: dict[str, int] = {
            "settings": 0,
            "accounts_created": 0,
            "accounts_updated": 0,
            "embedded_plans_created": 0,
            "embedded_plans_updated": 0,
            "iptu_terms_created": 0,
            "iptu_terms_updated": 0,
            "opening_installments_created": 0,
            "opening_bills_created": 0,
            "deferred_debts_created": 0,
            "deferred_debts_updated": 0,
        }

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(f"{prefix}Semeando contas de serviço (prédios 836/850)...")
        with transaction.atomic():
            self._seed_settings(data)
            self._seed_billing_accounts(data)
            self._seed_embedded_plans(data)
            self._seed_iptu_terms(data)
            self._seed_deferred_2026_debts(data)
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(self._summary(prefix)))

    # ------------------------------------------------------------------ loading

    def _load(self, file_path: str) -> dict[str, object]:
        path = Path(file_path)
        if not path.exists():
            raise CommandError(_ERR_FILE_MISSING.format(path=path))
        with path.open(encoding="utf-8") as handle:
            data: dict[str, object] = json.load(handle)
        return data

    def _get_building(self, street_number: int) -> Building:
        """Look up a building by street_number (do NOT create — buildings pre-exist), PT error."""
        if street_number not in self._buildings:
            try:
                self._buildings[street_number] = Building.objects.get(street_number=street_number)
            except Building.DoesNotExist as exc:
                raise CommandError(_ERR_BUILDING_MISSING.format(number=street_number)) from exc
        return self._buildings[street_number]

    def _account_key(self, account_type: str, external_identifier: str) -> str:
        return f"{account_type}|{external_identifier}"

    def _get_account(self, account_type: str, external_identifier: str) -> BillingAccount:
        return self._accounts[self._account_key(account_type, external_identifier)]

    # ------------------------------------------------------------------ sections

    def _seed_settings(self, data: dict[str, object]) -> None:
        """FinancialSettings singleton (pk=1) — update_or_create, rerun does not duplicate."""
        config = data.get("configuracoes")
        if not isinstance(config, dict):
            return
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": _money(config["saldo_inicial"]),
                "initial_balance_date": _as_date(config["data_saldo_inicial"]),
                "rent_tracking_start_date": _as_date(config["rent_tracking_start_date"]),
            },
        )
        self.stats["settings"] = 1
        self.stdout.write("  + FinancialSettings (saldo 0 / 2026-03-01 / tracking 2026-06-01)")

    def _seed_billing_accounts(self, data: dict[str, object]) -> None:
        """Typed BillingAccounts — key (building, account_type, external_identifier)."""
        items = self._section(data, "contas")
        self.stdout.write(f"  Contas de serviço ({len(items)})...")
        for index, item in enumerate(items, start=1):
            building = self._get_building(_as_int(item["predio_street_number"]))
            account_type = _as_str(item["account_type"])
            external_identifier = _as_str(item["external_identifier"])
            account, created = BillingAccount.objects.update_or_create(
                building=building,
                account_type=account_type,
                external_identifier=external_identifier,
                defaults={
                    "condominium": building.condominium,
                    "name": _as_str(item["name"]),
                    "secondary_identifier": _as_str(item.get("secondary_identifier", "")),
                    "holder_name": _as_str(item.get("holder_name", "")),
                    "registered_address": _as_str(item.get("registered_address", "")),
                    "supply_status": _as_str(item["supply_status"]),
                    "default_due_day": _as_int(item["default_due_day"]),
                    "expected_amount": _money(item.get("expected_amount", 0)),
                },
            )
            self._accounts[self._account_key(account_type, external_identifier)] = account
            self._tally("accounts", created)
            self.stdout.write(
                f"  [{index}/{len(items)}] + {account.name} ({account_type} {external_identifier})"
            )

    def _seed_embedded_plans(self, data: dict[str, object]) -> None:
        """Embedded plans (water/electricity) — key (billing_account, embedded=True, description)."""
        items = self._section(data, "planos_embutidos")
        self.stdout.write(f"  Planos embutidos ({len(items)})...")
        for index, item in enumerate(items, start=1):
            building = self._get_building(_as_int(item["predio_street_number"]))
            account = self._get_account(
                _as_str(item["account_type"]), _as_str(item["account_external_identifier"])
            )
            description = _as_str(item["description"])
            count = _as_int(item["installment_count"])
            total_amount = _money(item["installment_amount"]) * count
            _plan, created = InstallmentPlan.objects.update_or_create(
                billing_account=account,
                embedded=True,
                description=description,
                defaults={
                    "condominium": building.condominium,
                    "building": building,
                    "total_amount": total_amount,
                    "installment_count": count,
                    "start_due_date": _OPENING_COMPETENCE,
                    "default_due_day": _as_int(item["default_due_day"]),
                    "lifecycle_state": InstallmentPlanState.ACTIVE,
                },
            )
            self._tally("embedded_plans", created)
            self.stdout.write(
                f"  [{index}/{len(items)}] + {description} "
                f"({item['installment_count']}x, atual {item['current_installment']})"
            )

    def _seed_iptu_terms(self, data: dict[str, object]) -> None:
        """IPTU terms — standalone plan (embedded=False, billing_account=<IPTU>) + opening parcelas.

        Key: plan (billing_account, embedded=False, description="IPTU termo <num>"); installment
        (plan, number). Only the current (overdue) + next (open) parcelas are materialized — no
        backfill of paid pre-tracking parcelas (§13). Each opening parcela also gets its Bill (the
        S41 standalone path) at competence 2026-06 with the real due_date preserved.
        """
        items = self._section(data, "termos_iptu")
        self.stdout.write(f"  Termos IPTU ({len(items)})...")
        for index, item in enumerate(items, start=1):
            building = self._get_building(_as_int(item["predio_street_number"]))
            account = self._get_account("iptu", _as_str(item["account_external_identifier"]))
            description = f"IPTU termo {item['termo']}"
            plan, created = InstallmentPlan.objects.update_or_create(
                billing_account=account,
                embedded=False,
                description=description,
                defaults={
                    "condominium": building.condominium,
                    "building": building,
                    "total_amount": _money(item["total_amount"]),
                    "installment_count": _as_int(item["installment_count"]),
                    "start_due_date": _as_date(item["current_due_date"]),
                    "default_due_day": 30,
                    "lifecycle_state": InstallmentPlanState.ACTIVE,
                },
            )
            self._tally("iptu_terms", created)
            self._seed_opening_parcela(
                plan=plan,
                building=building,
                number=_as_int(item["current_number"]),
                amount=_money(item["current_amount"]),
                due_date=_as_date(item["current_due_date"]),
                description=f"{description} parcela {item['current_number']}",
            )
            self._seed_opening_parcela(
                plan=plan,
                building=building,
                number=_as_int(item["next_number"]),
                amount=_money(item["next_amount"]),
                due_date=_as_date(item["next_due_date"]),
                description=f"{description} parcela {item['next_number']}",
            )
            self.stdout.write(
                f"  [{index}/{len(items)}] + {description} "
                f"(parcelas {item['current_number']}+{item['next_number']})"
            )

    def _seed_opening_parcela(
        self,
        *,
        plan: InstallmentPlan,
        building: Building,
        number: int,
        amount: Decimal,
        due_date: date,
        description: str,
    ) -> None:
        """Materialize one opening parcela: an Installment (schedule) + its Bill (realized).

        Idempotent: get_or_create on (plan, number) for the schedule; the Bill is created only when
        no active Bill references the installment yet (unique_active_bill_per_installment is the
        natural key). The standalone parcela Bill is built exactly like the S41 production path
        (BillGenerationService._generate_installment_bills): Bill(installment=…, behavior=INSTALLMENT)
        + one BillLineItem copying the schedule amount. The installment FK on the Bill is what links
        it to the IPTU plan for IptuAlertService (filter installment__plan=plan) — BillService /
        BillDraft cannot set it, so it is materialized here, the same way generation does. The only
        deviation from generation is competence_month=2026-06 (the real due_date 29/05 or 30/06 is
        preserved): pinning the competence keeps the overdue parcela out of a pre-tracking month
        with a spurious negative net (§10.1), while the calendar still groups by due_date.
        """
        installment, created = Installment.objects.get_or_create(
            plan=plan,
            number=number,
            is_deleted=False,
            defaults={"due_date": due_date, "amount": amount},
        )
        if created:
            self.stats["opening_installments_created"] += 1
        if Bill.objects.filter(installment=installment).exists():
            return
        bill = Bill(
            condominium=building.condominium,
            building=building,
            installment=installment,
            competence_month=_OPENING_COMPETENCE,
            due_date=due_date,
            description=description,
            behavior=BillBehavior.INSTALLMENT,
            lifecycle_state=BillLifecycleState.ACTIVE,
        )
        bill.full_clean()
        bill.save()
        line = BillLineItem(bill=bill, description=description, amount=amount, is_offset=False)
        line.full_clean(exclude=["bill"])
        line.save()
        self.stats["opening_bills_created"] += 1

    def _seed_deferred_2026_debts(self, data: dict[str, object]) -> None:
        """3 deferred 2026 debts — Bill(DEFERRED, billing_account=<IPTU>) + 1 full-value line.

        Key: Bill (billing_account, competence_month=2026-06-01) via the partial unique; the single
        BillLineItem (the full debt amount, is_offset=False — mandatory or convert_deferred yields a
        R$0 plan, §10.4) is get_or_create on (bill, description) so a rerun never accumulates lines.
        """
        items = self._section(data, "dividas_2026")
        self.stdout.write(f"  Dívidas 2026 diferidas ({len(items)})...")
        for index, item in enumerate(items, start=1):
            building = self._get_building(_as_int(item["predio_street_number"]))
            account = self._get_account("iptu", _as_str(item["account_external_identifier"]))
            description = f"IPTU dívida 2026 lançamento {item['lancamento']}"
            amount = _money(item["amount"])
            bill, created = Bill.objects.get_or_create(
                billing_account=account,
                competence_month=_OPENING_COMPETENCE,
                is_deleted=False,
                defaults={
                    "condominium": building.condominium,
                    "building": building,
                    "due_date": _as_date(item["due_date"]),
                    "description": description,
                    "external_identifier": _as_str(item["lancamento"]),
                    "behavior": BillBehavior.ONE_TIME,
                    "lifecycle_state": BillLifecycleState.DEFERRED,
                },
            )
            BillLineItem.objects.get_or_create(
                bill=bill,
                description=description,
                is_deleted=False,
                defaults={"amount": amount, "is_offset": False},
            )
            self._tally("deferred_debts", created)
            self.stdout.write(f"  [{index}/{len(items)}] + {description} (R$ {amount})")

    # ------------------------------------------------------------------ helpers

    def _section(self, data: dict[str, object], key: str) -> list[dict[str, object]]:
        section = data.get(key, [])
        if not isinstance(section, list):
            return []
        return [item for item in section if isinstance(item, dict)]

    def _tally(self, entity: str, created: bool) -> None:
        suffix = "created" if created else "updated"
        self.stats[f"{entity}_{suffix}"] += 1

    def _summary(self, prefix: str) -> str:
        lines = [f"{prefix}Seed concluído.", "Resumo:"]
        for key, count in self.stats.items():
            if count > 0:
                lines.append(f"  {key}: {count}")
        return "\n".join(lines)
