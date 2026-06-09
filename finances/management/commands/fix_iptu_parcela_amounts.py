"""Management command: fix_iptu_parcela_amounts (one-off, idempotent).

The original ``seed_condo_utilities`` materialized the IPTU opening parcelas from
``saldo ÷ nº-parcelas`` instead of the real per-parcela "Atualizado" value of the prefeitura
extract — 8 of the 9 termos ended up wrong (e.g. termo 992988 parcela 9 = R$2.718,16 instead of
R$522,72). This command re-applies the CORRECTED values from ``scripts/data/condo_utilities_seed.json``
to the ALREADY-materialized rows.

The displayed amount on Contas/calendar is ``Σ BillLineItem.amount`` (not ``Installment.amount``),
and the standalone parcela ``Bill`` carries ONE line copied from the schedule at materialization —
so a correction must touch BOTH the ``Installment.amount`` (schedule) AND that ``BillLineItem.amount``
(realized/displayed), plus ``InstallmentPlan.total_amount`` (the 2-parcela remaining balance). The
seed's ``get_or_create`` on ``(plan, number)`` never updates an existing row, so re-running the seed
does NOT repair the data — hence this dedicated command.

Idempotent: re-running once the values already match is a no-op. ``--dry-run`` rolls everything back.
Defensive: any parcela whose Bill already has a (non-deleted) ``PaymentAllocation`` is SKIPPED —
editing a paid bill's line would desync ``amount_paid``/``payment_status``.
"""

import json
from argparse import ArgumentParser
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from finances.models import Bill, BillingAccountType, Installment, InstallmentPlan

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
        "Corrige os valores das parcelas de IPTU (Installment + BillLineItem + total do plano) "
        "para o valor real 'Atualizado' do extrato (corrige o bug saldo÷nº-parcelas do seed)."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--file", default=_DEFAULT_FILE)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        file_path = str(options["file"])
        dry_run = bool(options["dry_run"])
        data = self._load(file_path)
        terms = self._section(data, "termos_iptu")

        self.stats: dict[str, int] = {
            "plans_updated": 0,
            "installments_updated": 0,
            "lines_updated": 0,
            "skipped_paid": 0,
            "missing": 0,
        }
        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            f"{prefix}Corrigindo valores das parcelas de IPTU ({len(terms)} termos)..."
        )
        with transaction.atomic():
            for term in terms:
                self._fix_term(term)
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(self._summary(prefix)))

    # ------------------------------------------------------------------ per-term

    def _fix_term(self, term: dict[str, object]) -> None:
        termo = _as_str(term["termo"])
        external = _as_str(term["account_external_identifier"])
        description = f"IPTU termo {termo}"
        plan = InstallmentPlan.objects.filter(
            embedded=False,
            description=description,
            billing_account__account_type=BillingAccountType.IPTU,
            billing_account__external_identifier=external,
        ).first()
        if plan is None:
            self.stats["missing"] += 1
            self.stdout.write(
                self.style.WARNING(f"  ! {description}: plano não encontrado — pulando")
            )
            return

        new_total = _money(term["total_amount"])
        if plan.total_amount != new_total:
            plan.total_amount = new_total
            plan.full_clean()
            plan.save()
            self.stats["plans_updated"] += 1

        self._fix_parcela(
            plan, description, _as_int(term["current_number"]), _money(term["current_amount"])
        )
        self._fix_parcela(
            plan, description, _as_int(term["next_number"]), _money(term["next_amount"])
        )
        self.stdout.write(
            f"  + {description}: total {new_total}; "
            f"parcelas {term['current_number']}+{term['next_number']}"
        )

    def _fix_parcela(
        self, plan: InstallmentPlan, description: str, number: int, amount: Decimal
    ) -> None:
        installment = Installment.objects.filter(plan=plan, number=number).first()
        if installment is None:
            self.stats["missing"] += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ! {description} parcela {number}: installment não encontrada — pulando"
                )
            )
            return

        bill = Bill.objects.filter(installment=installment).first()
        if bill is not None and bill.allocations.exists():
            self.stats["skipped_paid"] += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ! {description} parcela {number}: bill com pagamento alocado — "
                    "pulando (defensivo)"
                )
            )
            return

        if installment.amount != amount:
            installment.amount = amount
            installment.full_clean()
            installment.save()
            self.stats["installments_updated"] += 1

        if bill is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  ! {description} parcela {number}: bill não encontrada — "
                    "apenas a installment foi corrigida"
                )
            )
            return

        lines = list(bill.line_items.filter(is_deleted=False))
        if len(lines) != 1:
            self.stats["missing"] += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  ! {description} parcela {number}: esperava 1 linha na bill, "
                    f"encontrei {len(lines)} — pulando a linha"
                )
            )
            return
        line = lines[0]
        if line.amount != amount:
            line.amount = amount
            line.full_clean(exclude=["bill"])
            line.save()
            self.stats["lines_updated"] += 1

    # ------------------------------------------------------------------ helpers

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
