"""Apply a parsed invoice (S59) DIRECTLY to a target Bill, in one transaction (S69, design §3.3).

Where the standalone ``parse_invoice`` flow (S60) only builds a read-only DRAFT that a human
later saves through the modal, ``apply_invoice`` skips the modal: it reconciles the parsed
invoice against the bill picked in the cockpit line (``target_bill``) and, if the reconciliation
passes the identity/state guards below, writes the lines + statement + editable header straight
through ``BillService.update_with_lines`` — the ONLY write path (design §6). This module never
touches the ORM itself for a write; it only reads (via ``InvoiceDraftService.build_draft``) and
delegates. ``InvoiceDraftService`` therefore stays 0-writes (S60 invariant), and the embedded-
parcela preservation/dedup rule lives in ONE place (``BillService.update_with_lines``, S69).
"""

from decimal import Decimal
from typing import cast

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from finances.models import Bill, BillLifecycleState, Installment, InstallmentPlanState
from finances.services.bill_service import BillLineInput, BillService, StatementInput
from finances.services.invoice_draft_service import InvoiceDraftService
from finances.services.invoice_parsing.base import ParsedInvoice

_ERR_ACCOUNT_MISMATCH = "A fatura não pertence à conta desta cobrança (inscrição/UC divergente)."
_ERR_COMPETENCE_MISMATCH = (
    "A competência da fatura ({parsed_month}) não bate com a desta cobrança ({bill_month})."
)
_ERR_BILL_NOT_ACTIVE = "Reative a conta antes de importar a fatura."


def _resolve_owned_installment(installment_id: int | None, bill: Bill) -> Installment | None:
    """Resolve installment_id -> Installment ONLY if it belongs to bill's embedded ACTIVE plan.

    Mirrors ``crud_views._resolve_owned_installment`` (the ownership guard the modal's
    ``update_with_lines`` action already enforces) — the apply path resolves the SAME
    ``installment_id`` the draft reconciler already matched against this exact billing_account,
    so this is a defensive re-check, never a foreign/standalone parcela binding here either.
    """
    if installment_id is None:
        return None
    return Installment.objects.filter(
        pk=installment_id,
        plan__billing_account=bill.billing_account,
        plan__embedded=True,
        plan__lifecycle_state=InstallmentPlanState.ACTIVE,
        plan__is_deleted=False,
    ).first()


def _matched_account_id(matched_account: object) -> int | None:
    """The matched account's pk from the draft's ``matched_account`` dict, or None (no match)."""
    if not isinstance(matched_account, dict):
        return None
    return cast(int, matched_account["id"])


class InvoiceApplyService:
    """Stateless: parse-and-apply-to-target-bill orchestration."""

    @staticmethod
    def apply(bill: Bill, parsed: ParsedInvoice, user: User | None = None) -> Bill:
        """Aplica uma fatura parseada À BILL ALVO via update_with_lines, na mesma transação.

        Reconcilia o parsed contra ``bill`` (via ``InvoiceDraftService.build_draft``, que também
        resolve ``installment_id`` por linha e produz warnings informativos — nunca bloqueantes
        aqui). Rejeita (PT 400) quando a conta casada diverge da conta da bill (ou é nula), a
        competência diverge, ou a bill não está ATIVA; bill paga/parcial e mês fechado são
        rejeitados por delegação a ``update_with_lines`` (guards não duplicados, design §6). O
        header aplicado é só ``due_date``/``external_identifier`` — ``ParsedInvoice`` não expõe
        ``issue_date`` (o parser, S59, não o extrai).
        """
        if bill.lifecycle_state != BillLifecycleState.ACTIVE:
            raise ValidationError(_ERR_BILL_NOT_ACTIVE)
        if parsed.competence_month != bill.competence_month:
            raise ValidationError(
                _ERR_COMPETENCE_MISMATCH.format(
                    parsed_month=parsed.competence_month.strftime("%m/%Y"),
                    bill_month=bill.competence_month.strftime("%m/%Y"),
                )
            )
        draft = InvoiceDraftService.build_draft(parsed, target_bill=bill)
        matched_account_id = _matched_account_id(draft["matched_account"])
        if (
            matched_account_id is None
            or bill.billing_account_id is None
            or matched_account_id != bill.billing_account_id
        ):
            raise ValidationError(_ERR_ACCOUNT_MISMATCH)

        lines: list[BillLineInput] = []
        for raw in draft["line_items"]:
            installment_id = cast("int | None", raw.get("installment_id"))
            lines.append(
                BillLineInput(
                    description=str(raw["description"]),
                    amount=Decimal(str(raw["amount"])),
                    is_offset=bool(raw.get("is_offset", False)),
                    installment=_resolve_owned_installment(installment_id, bill),
                )
            )
        header: dict[str, object] = {
            "due_date": parsed.due_date,
            "external_identifier": parsed.external_identifier,
        }
        with transaction.atomic():
            BillService.update_with_lines(
                bill,
                lines,
                statement=(
                    cast(StatementInput, parsed.statement) if parsed.statement is not None else None
                ),
                header=header,
                user=user,
            )
        return bill
