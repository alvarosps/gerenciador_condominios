"""Management command: fix_agua_embedded_installments (one-off, idempotent).

The seed pinned the água (water) embedded plans' ``current_installment`` one AHEAD of the real DMAE
invoice parcela for the first tracked cycle: água 836 used 24 at venc 04/06 (the real comp-05 fatura
is parcela 23/46), água 850 used 3 (real is 2/59). The vencimentos were right; only the parcela
NUMBERS were +1 and every materialized installment was dated one month too early (and parcela 23/2
was missing). Fixing the JSON ``current_installment`` is not enough — the seed's get_or_create on
``(plan, number)`` never repairs the already-materialized rows.

This re-materializes the embedded installments of the WATER plans from the CORRECTED
``current_installment`` in the seed JSON: the existing live installments are soft-deleted and the
full going-forward schedule (numbers + monthly due dates from 2026-06, via the same
``_schedule_due_dates`` the seed uses) is recreated. Safe: embedded installments are never referenced
by a Bill (the seed materializes Bills only for IPTU terms + deferred debts) — asserted before
touching anything. Idempotent: a plan already starting at the correct ``current`` is skipped.
``--dry-run`` rolls everything back.
"""

import json
from argparse import ArgumentParser
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Min

from finances.management.commands.seed_condo_utilities import _OPENING_COMPETENCE
from finances.models import Bill, BillingAccountType, Installment, InstallmentPlan
from finances.services.installment_plan_service import _schedule_due_dates

_DEFAULT_FILE = "scripts/data/condo_utilities_seed.json"

_ERR_FILE_MISSING = "Arquivo de seed não encontrado: {path}"


def _money(value: object) -> Decimal:
    return Decimal(str(value))


def _as_str(value: object) -> str:
    return str(value)


def _as_int(value: object) -> int:
    return int(str(value))


class Command(BaseCommand):
    help = (
        "Corrige o off-by-one das parcelas embutidas de água "
        "(re-materializa o cronograma a partir do current_installment correto do seed JSON)."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--file", default=_DEFAULT_FILE)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        file_path = str(options["file"])
        dry_run = bool(options["dry_run"])
        data = self._load(file_path)
        plans = self._section(data, "planos_embutidos")

        self.stats: dict[str, int] = {
            "plans_rematerialized": 0,
            "installments_created": 0,
            "installments_removed": 0,
            "skipped": 0,
            "missing": 0,
        }
        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(f"{prefix}Corrigindo parcelas embutidas de água (off-by-one)...")
        with transaction.atomic():
            for item in plans:
                if _as_str(item.get("account_type", "")) == BillingAccountType.WATER.value:
                    self._fix_plan(item)
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(self._summary(prefix)))

    def _fix_plan(self, item: dict[str, object]) -> None:
        external = _as_str(item["account_external_identifier"])
        description = _as_str(item["description"])
        current = _as_int(item["current_installment"])
        count = _as_int(item["installment_count"])
        amount = _money(item["installment_amount"])
        default_due_day = _as_int(item["default_due_day"])

        plan = InstallmentPlan.objects.filter(
            embedded=True,
            description=description,
            billing_account__account_type=BillingAccountType.WATER,
            billing_account__external_identifier=external,
        ).first()
        if plan is None:
            self.stats["missing"] += 1
            self.stdout.write(
                self.style.WARNING(f"  ! {description}: plano não encontrado — pulando")
            )
            return

        if Bill.all_objects.filter(installment__plan=plan).exists():
            self.stats["skipped"] += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ! {description}: há Bill referenciando as parcelas — pulando (não esperado)"
                )
            )
            return

        existing = Installment.objects.filter(plan=plan)
        existing_min = existing.aggregate(m=Min("number"))["m"]
        if existing_min == current:
            self.stats["skipped"] += 1
            self.stdout.write(f"  = {description}: já inicia em {current} — ok")
            return

        removed = existing.count()
        for installment in existing:
            installment.delete()
        self.stats["installments_removed"] += removed

        due_dates = _schedule_due_dates(_OPENING_COMPETENCE, count - current + 1, default_due_day)
        for offset, due_date in enumerate(due_dates):
            Installment.objects.get_or_create(
                plan=plan,
                number=current + offset,
                is_deleted=False,
                defaults={"due_date": due_date, "amount": amount},
            )
            self.stats["installments_created"] += 1
        self.stats["plans_rematerialized"] += 1
        self.stdout.write(
            f"  + {description}: re-materializado {current}..{count} "
            f"(removidas {removed}, criadas {count - current + 1})"
        )

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

    def _summary(self, prefix: str) -> str:
        lines = [f"{prefix}Correção concluída.", "Resumo:"]
        for key, count in self.stats.items():
            if count > 0:
                lines.append(f"  {key}: {count}")
        return "\n".join(lines)
