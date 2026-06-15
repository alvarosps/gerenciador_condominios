"""Enrich a parsed invoice (S59) into a persistable DRAFT — account match + installment
reconciliation + idempotency. WRITES NOTHING (past-immutable, design §6 / Apêndice B).

The S59 parser produces a pure ``ParsedInvoice`` (no ORM). This service is the ONLY place that
touches the database: it reads the matching ``BillingAccount`` (by ``account_type`` + inscrição/UC),
reads the embedded-installment plan to resolve ``installment_id`` per line, and reads whether an
active ``Bill`` already exists for (account, competence) to flag a replacement. It never creates,
updates or deletes a record — the draft is persisted later by ``create_with_lines`` /
``update_with_lines`` (S58), from the modal (S63). Direction: ``finances.models`` +
``finances.services.invoice_parsing.base`` only — never views/serializers reach back here.
"""

from typing import TypedDict

from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    Installment,
    InstallmentPlanState,
)
from finances.money import money_str
from finances.serializers import BillingAccountSerializer
from finances.services.invoice_parsing.base import ParsedInvoice, ParsedLine


class InvoiceDraft(TypedDict):
    """Serialized draft shape returned by ``build_draft`` (persists nothing)."""

    bill: dict[str, object]
    line_items: list[dict[str, object]]
    statement: object
    matched_account: object
    existing_bill_id: int | None
    warnings: list[str]


# PT labels per account type for the draft's user-facing text (warning + fallback description).
# Literal here (not BillingAccountType.label, whose lazy-promise type the checkers disagree on);
# GENERIC is the fallback for any unmapped/unknown type.
_ACCOUNT_TYPE_LABELS: dict[str, str] = {
    BillingAccountType.WATER: "Água",
    BillingAccountType.ELECTRICITY: "Luz",
    BillingAccountType.IPTU: "IPTU",
    BillingAccountType.INTERNET: "Internet",
    BillingAccountType.GENERIC: "Genérica",
}

_WARN_NO_MATCH = (
    "Nenhuma conta de {label} encontrada para a inscrição/UC {identifier}. "
    "Selecione ou crie a conta."
)
_WARN_REPLACEMENT = (
    "Já existe uma conta para {name} em {month} — salvar substituirá as linhas dela "
    "(use Atualizar)."
)
_WARN_INSTALLMENT_NO_PLAN = (
    "Parcela {number} sem plano de parcelamento cadastrado — crie o plano em "
    "Planos de Parcelamento."
)


class InvoiceDraftService:
    @staticmethod
    def build_draft(parsed: ParsedInvoice) -> InvoiceDraft:
        """Enriquece um ParsedInvoice (S59) com casamento de conta + reconciliação de parcela +
        idempotência, e devolve o RASCUNHO serializado (grava NADA)."""
        warnings = list(parsed.warnings)
        account = InvoiceDraftService._match_account(parsed)
        if account is None:
            warnings.append(
                _WARN_NO_MATCH.format(
                    label=InvoiceDraftService._type_label(parsed.account_type),
                    identifier=parsed.external_identifier,
                )
            )

        line_items = [
            InvoiceDraftService._reconcile_line(line, account, warnings)
            for line in parsed.line_items
        ]

        existing_bill_id = InvoiceDraftService._existing_bill_id(parsed, account)
        if existing_bill_id is not None and account is not None:
            warnings.append(
                _WARN_REPLACEMENT.format(
                    name=account.name,
                    month=parsed.competence_month.strftime("%m/%Y"),
                )
            )

        return {
            "bill": InvoiceDraftService._bill_dict(parsed, account),
            "line_items": line_items,
            "statement": parsed.statement,
            "matched_account": (BillingAccountSerializer(account).data if account else None),
            "existing_bill_id": existing_bill_id,
            "warnings": warnings,
        }

    @staticmethod
    def _type_label(account_type: str) -> str:
        return _ACCOUNT_TYPE_LABELS.get(
            account_type, _ACCOUNT_TYPE_LABELS[BillingAccountType.GENERIC]
        )

    @staticmethod
    def _match_account(parsed: ParsedInvoice) -> BillingAccount | None:
        """The active account for this invoice's type + inscrição/UC (objects excludes deleted)."""
        return BillingAccount.objects.filter(
            account_type=parsed.account_type, external_identifier=parsed.external_identifier
        ).first()

    @staticmethod
    def _bill_dict(parsed: ParsedInvoice, account: BillingAccount | None) -> dict[str, object]:
        """The bill header in the BillSerializer write shape (building_id/category_id), with a
        description from the matched account name, falling back to '{tipo} {MM/AAAA}'."""
        if account is not None:
            description: str = account.name
        else:
            description = (
                f"{InvoiceDraftService._type_label(parsed.account_type)} "
                f"{parsed.competence_month.strftime('%m/%Y')}"
            )
        return {
            "competence_month": parsed.competence_month.isoformat(),
            "due_date": parsed.due_date.isoformat(),
            "external_identifier": parsed.external_identifier,
            "behavior": parsed.behavior,
            "account_type": parsed.account_type,
            "description": description,
            "building_id": account.building_id if account else None,
            "category_id": account.category_id if account else None,
        }

    @staticmethod
    def _reconcile_line(
        line: ParsedLine, account: BillingAccount | None, warnings: list[str]
    ) -> dict[str, object]:
        """Serialize one parsed line; resolve installment_id from the account's embedded plan.

        installment_number is INTERNAL to ParsedLine (S59) and never leaks into the draft — the
        draft exposes only installment_id. A parcela line whose plan is missing stays generic
        (installment_id=None) and appends a PT warning; no plan/installment is ever created.
        """
        installment_id: int | None = None
        if line.installment_number is not None and account is not None:
            installment = Installment.objects.filter(
                plan__billing_account=account,
                plan__embedded=True,
                plan__lifecycle_state=InstallmentPlanState.ACTIVE,
                plan__is_deleted=False,
                number=line.installment_number,
            ).first()
            installment_id = installment.pk if installment is not None else None
        if line.installment_number is not None and installment_id is None:
            warnings.append(_WARN_INSTALLMENT_NO_PLAN.format(number=line.installment_number))
        return {
            "description": line.description,
            "amount": money_str(line.amount),
            "is_offset": line.is_offset,
            "category_id": None,
            "installment_id": installment_id,
        }

    @staticmethod
    def _existing_bill_id(parsed: ParsedInvoice, account: BillingAccount | None) -> int | None:
        """The pk of ANY non-deleted Bill already covering (account, competence), or None.

        The Bill partial unique is ``WHERE is_deleted=False`` (NOT lifecycle-filtered): a non-deleted
        SUSPENDED/CANCELED/DEFERRED bill for (account, competence) still occupies the slot, so a
        create_with_lines would raise IntegrityError. Matching any non-deleted bill routes the modal
        to update_with_lines (S58) instead. This only READS; ``objects`` already excludes soft-deleted
        bills, mirroring the constraint's condition exactly.
        """
        if account is None:
            return None
        bill = Bill.objects.filter(
            billing_account=account,
            competence_month=parsed.competence_month,
        ).first()
        return bill.pk if bill is not None else None
