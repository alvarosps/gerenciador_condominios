"""Bill creation/replacement with line items + reading statements, in the service (S37/S58).

Bill + BillLineItem(s) (+ an optional 1:1 reading statement) are created/replaced
atomically here, not in a writable nested serializer (design §8 / architecture: business
logic in services). The Bill fields are grouped into the cohesive BillDraft value object so
the service signature stays small; the viewset builds a BillDraft from validated data and
passes the lines + statement.

Statements (S58) hold only readings (consumo/leituras) — money is always BillLineItem
(single source, design §3.2). The statement type is decided by the billing account's
account_type (WATER -> WaterBillStatement, ELECTRICITY -> ElectricityBillStatement); any
other type (or no account) with a statement is rejected. update_with_lines replaces the
lines + upserts the statement on the SAME Bill, but only while the Bill is UNPAID and its
competence month is OPEN. delete cascades the soft-delete to the statement (SoftDeleteMixin
does not walk the reverse relation — design §7.3).
"""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NotRequired, TypedDict

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import Building, Condominium
from core.services.timezone import today_sp
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    Category,
    ElectricityBillStatement,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
    WaterBillStatement,
)
from finances.services.condo_month_close_service import CondoMonthCloseService

logger = logging.getLogger(__name__)

_ERR_STATEMENT_TYPE = "Statement só é permitida para contas de água ou luz."
_ERR_BILL_PAID = "Não é possível alterar uma conta com pagamento. Desfaça o pagamento primeiro."
_ERR_BILL_ALREADY_EXISTS = (
    "Já existe uma conta para esta conta recorrente neste mês de competência. "
    "Atualize a conta existente em vez de criar uma nova."
)
# The Bill partial unique (is_deleted=False, NOT lifecycle-filtered): full_clean() reports its
# violation under this constraint name, so the raw message is mapped to the PT one below.
_ACCOUNT_MONTH_CONSTRAINT = "unique_active_bill_per_account_month"

_STATEMENT_MODEL_BY_TYPE: dict[str, type[WaterBillStatement | ElectricityBillStatement]] = {
    BillingAccountType.WATER: WaterBillStatement,
    BillingAccountType.ELECTRICITY: ElectricityBillStatement,
}


def assert_not_paid(bill: Bill) -> None:
    """Reject (PT) when the bill has a live payment (total OR partial).

    payment_status is read from with_amounts (never summed in Python) — 'open' is the only
    state with no live PaymentAllocation. Shared by update_with_lines, delete (B4) and
    BillLifecycleService.set_state (B4): a paid Bill mutated/deleted/suspended/canceled would
    leave its Payment/allocation/ReserveMovement live in the cash flow with no expense behind
    them — unpay is required first (design §4.4).
    """
    annotated = Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)
    if str(getattr(annotated, "payment_status", "open")) != "open":
        raise ValidationError(_ERR_BILL_PAID)


class BillLineInput(TypedDict):
    description: str
    amount: Decimal
    is_offset: NotRequired[bool]
    category: NotRequired[Category | None]
    installment: NotRequired[Installment | None]


class WaterStatementInput(TypedDict):
    consumo_m3: int
    leitura_anterior: NotRequired[int | None]
    leitura_atual: NotRequired[int | None]
    leitura_dias: NotRequired[int | None]
    data_leitura: NotRequired[date | None]
    agua_status: NotRequired[str]
    esgoto_status: NotRequired[str]


class ElectricityStatementInput(TypedDict):
    consumo_kwh: int
    energia_injetada_kwh: NotRequired[int | None]
    leitura_anterior: NotRequired[int | None]
    leitura_atual: NotRequired[int | None]
    leitura_dias: NotRequired[int | None]
    classe: NotRequired[str]
    bandeira: NotRequired[str]


StatementInput = WaterStatementInput | ElectricityStatementInput


@dataclass(frozen=True, kw_only=True)
class BillDraft:
    """The Bill fields for BillService.create_with_lines (cohesive value object)."""

    condominium: Condominium
    competence_month: date
    due_date: date
    description: str
    behavior: str
    building: Building | None = None
    category: Category | None = None
    billing_account: BillingAccount | None = None
    external_identifier: str = ""
    lifecycle_state: str = BillLifecycleState.ACTIVE
    notes: str = ""


# The mutable header fields a re-imported (corrected) invoice may carry into update_with_lines.
# competence_month is INTENTIONALLY absent — the (billing_account, competence_month) identity is
# immutable once a bill exists; only the editable header is replaced alongside the lines (design §6).
_EDITABLE_HEADER_FIELDS = frozenset(
    {
        "due_date",
        "issue_date",
        "description",
        "behavior",
        "external_identifier",
        "building",
        "category",
        "billing_account",
        "notes",
    }
)


class BillService:
    """Stateless Bill orchestration."""

    @staticmethod
    def _statement_model_for(
        billing_account: BillingAccount | None,
    ) -> type[WaterBillStatement | ElectricityBillStatement]:
        """Resolve the statement model from the account type, or reject (PT) — single source."""
        account_type = billing_account.account_type if billing_account is not None else None
        model = _STATEMENT_MODEL_BY_TYPE.get(account_type) if account_type is not None else None
        if model is None:
            raise ValidationError(_ERR_STATEMENT_TYPE)
        return model

    @staticmethod
    def _write_lines(bill: Bill, lines: list[BillLineInput], user: User | None) -> None:
        for line in lines:
            item = BillLineItem(
                bill=bill,
                description=line["description"],
                amount=line["amount"],
                is_offset=line.get("is_offset", False),
                category=line.get("category"),
                installment=line.get("installment"),
                created_by=user,
                updated_by=user,
            )
            item.full_clean(exclude=["bill"])  # PT amount >= 0
            item.save()

    @staticmethod
    def _upsert_statement(
        bill: Bill,
        billing_account: BillingAccount | None,
        statement: StatementInput | None,
        user: User | None,
    ) -> None:
        """Upsert the 1:1 reading statement on the bill (type decided by the account).

        No statement payload is a pure no-op (any existing statement stays live). The bill_id
        is a hard OneToOne unique (per table), so the target-type row is reused in place rather
        than soft-deleted + recreated. A live statement of the OTHER type (different table) is
        soft-deleted (a bill carries at most one reading statement, design §3.2).
        """
        if statement is None:
            return
        model = BillService._statement_model_for(billing_account)
        other_model = (
            ElectricityBillStatement if model is WaterBillStatement else WaterBillStatement
        )
        for stale in other_model.objects.filter(bill=bill):
            stale.delete(deleted_by=user)
        instance = model.all_objects.filter(bill=bill).first() or model(bill=bill, created_by=user)
        values: dict[str, object] = dict(statement)
        for field_name, value in values.items():
            setattr(instance, field_name, value)
        instance.is_deleted = False
        instance.deleted_at = None
        instance.deleted_by = None
        instance.updated_by = user
        instance.full_clean(exclude=["bill"])
        instance.save()

    @staticmethod
    def create_with_lines(
        draft: BillDraft,
        lines: list[BillLineInput],
        statement: StatementInput | None = None,
        user: User | None = None,
    ) -> Bill:
        """Create a Bill plus its BillLineItem(s) and an optional 1:1 reading statement, atomically.

        amount_total derives from the lines via Bill.objects.with_amounts(today). The statement
        type is decided by draft.billing_account.account_type (WATER/ELECTRICITY); any other
        type or no account with a statement raises (PT). Any line/statement failing validation
        rolls the whole Bill back. An empty lines list is accepted (amount_total == 0).

        A non-deleted bill already occupying (billing_account, competence_month) — the partial
        unique is WHERE is_deleted=False, NOT lifecycle-filtered, so a SUSPENDED/CANCELED bill also
        collides — raises IntegrityError; it is caught here and surfaced as a PT ValidationError
        (400) instead of a 500. The idempotency match (InvoiceDraftService) routes the modal to
        update_with_lines first; this is the defensive backstop.

        Rejected (PT 400) when the competence month is closed — a new bill there would change that
        month's frozen result (mirrors update_with_lines / delete — design §4.7).
        """
        CondoMonthCloseService.assert_open(draft.competence_month)
        try:
            with transaction.atomic():
                bill = Bill(
                    condominium=draft.condominium,
                    building=draft.building,
                    category=draft.category,
                    billing_account=draft.billing_account,
                    competence_month=draft.competence_month,
                    due_date=draft.due_date,
                    description=draft.description,
                    external_identifier=draft.external_identifier,
                    behavior=draft.behavior,
                    lifecycle_state=draft.lifecycle_state,
                    notes=draft.notes,
                    created_by=user,
                    updated_by=user,
                )
                bill.full_clean()  # PT validation + competence_month -> day 1
                bill.save()
                BillService._write_lines(bill, lines, user)
                BillService._upsert_statement(bill, draft.billing_account, statement, user)
        except ValidationError as exc:
            # full_clean()'s validate_constraints() reports the partial unique under its constraint
            # name; map that one violation to the PT message and re-raise everything else verbatim.
            if _ACCOUNT_MONTH_CONSTRAINT in str(exc):
                raise ValidationError(_ERR_BILL_ALREADY_EXISTS) from exc
            raise
        except IntegrityError as exc:
            # Defensive backstop if full_clean() is ever bypassed (race / direct save path).
            raise ValidationError(_ERR_BILL_ALREADY_EXISTS) from exc
        return bill

    @staticmethod
    def _apply_header(bill: Bill, header: dict[str, object], user: User | None) -> None:
        """Apply the editable header fields of a re-imported (corrected) invoice, in place.

        competence_month is immutable (the (billing_account, competence_month) identity is fixed
        once a bill exists), so it is never written here — only the _EDITABLE_HEADER_FIELDS the
        serializer validated. full_clean() re-runs the model invariants before the save.
        """
        changed = [field for field in header if field in _EDITABLE_HEADER_FIELDS]
        if not changed:
            return
        for field in changed:
            setattr(bill, field, header[field])
        bill.updated_by = user
        bill.full_clean()
        # AuditMixin.save appends updated_at to update_fields automatically.
        bill.save(update_fields=[*changed, "updated_by"])

    @staticmethod
    def _write_lines_preserving_installments(
        bill: Bill, lines: list[BillLineInput], user: User | None
    ) -> None:
        """Replace the bill's non-parcela lines; an embedded-installment line is NEVER replaced.

        Only ``BillLineItem.objects.filter(bill=bill, installment__isnull=True)`` is soft-deleted
        — a line carrying the ``installment`` FK (the embedded parcela materialized by
        generation/S41) survives with its original pk, untouched. An incoming line whose
        ``installment`` already has a LIVE line on this bill (either pre-existing OR already
        queued earlier in THIS same payload — ``live_installment_ids`` is updated as each
        incoming line is accepted, so a payload that repeats the same installment twice dedupes
        the second occurrence too) is a re-send (the modal resubmits the locked parcela line,
        S63; the parser re-emits the reconciled 'PARCELA X/N' line, S69) and is skipped — dedup
        on (bill, installment), mirroring BillGenerationService._generate_embedded_lines
        (bill_generation_service.py:207), so the parcela's money is never doubled. An incoming
        line with an ``installment`` that has no live line yet is created normally (a new
        parcela entering this bill for the first time).
        """
        for existing_line in BillLineItem.objects.filter(bill=bill, installment__isnull=True):
            existing_line.delete(deleted_by=user)
        live_installment_ids = set(
            BillLineItem.objects.filter(bill=bill, installment__isnull=False).values_list(
                "installment_id", flat=True
            )
        )
        to_write: list[BillLineInput] = []
        for incoming_line in lines:
            installment = incoming_line.get("installment")
            if installment is not None:
                if installment.pk in live_installment_ids:
                    continue  # dedup: this parcela already has a live line on the bill
                live_installment_ids.add(installment.pk)
            to_write.append(incoming_line)
        BillService._write_lines(bill, to_write, user)

    @staticmethod
    def update_with_lines(
        bill: Bill,
        lines: list[BillLineInput],
        statement: StatementInput | None = None,
        header: dict[str, object] | None = None,
        user: User | None = None,
    ) -> Bill:
        """Replace the bill's lines + upsert the statement (+ editable header) on the SAME Bill.

        Allowed only while the bill is UNPAID (payment_status == 'open', read from
        with_amounts — never summed in Python) and its competence month is OPEN
        (CondoMonthCloseService.assert_open). When ``header`` is given (a re-imported corrected
        invoice), its editable fields (due_date/external_identifier/issue_date/building/category/…)
        are persisted in the SAME atomic transaction; competence_month stays immutable. Only lines
        WITHOUT the ``installment`` FK are replaced — an embedded-parcela line is untouchable, and
        an incoming line whose parcela already has a live line is deduped, never doubled (S69, see
        ``_write_lines_preserving_installments``); with_amounts ignores soft-deleted lines. The
        lines replaced here are a confirmed real value, so a still-estimated bill has its
        amount_is_estimated flag cleared in the SAME transaction (S65 — a bill already confirmed
        stays False, no-op). Raises (PT) when paid or month closed.
        """
        assert_not_paid(bill)
        CondoMonthCloseService.assert_open(bill.competence_month)
        with transaction.atomic():
            if header is not None:
                BillService._apply_header(bill, header, user)
            BillService._write_lines_preserving_installments(bill, lines, user)
            BillService._upsert_statement(bill, bill.billing_account, statement, user)
            if bill.amount_is_estimated:
                bill.amount_is_estimated = False
                bill.updated_by = user
                # AuditMixin.save appends updated_at to update_fields automatically.
                bill.save(update_fields=["amount_is_estimated", "updated_by"])
        return bill

    @staticmethod
    def update_header(bill: Bill, header: dict[str, object], user: User | None = None) -> Bill:
        """Update ONLY a bill's editable header fields (the Contas modal's edit mode, P2.3 step 1).

        The default DRF update used to write any field (including competence_month) with no guard;
        this is the guarded replacement the viewset delegates to. competence_month is immutable
        (only _EDITABLE_HEADER_FIELDS are applied) and a closed competence month is rejected
        (assert_open). Lines/payments are NOT touched — that is update_with_lines' job (design §6).
        """
        CondoMonthCloseService.assert_open(bill.competence_month)
        with transaction.atomic():
            BillService._apply_header(bill, header, user)
        return bill

    @staticmethod
    def delete(bill: Bill, user: User | None = None) -> None:
        """Soft-delete the bill and cascade the soft-delete to its live statement.

        SoftDeleteMixin.delete() only touches the record itself (it does not walk the reverse
        OneToOne), so the statement is soft-deleted explicitly here (design §7.3). Rejected
        (PT 400) when the bill has a live payment (B4 — unpay first) or the competence month is
        closed — deleting a frozen-month bill would change that month's frozen result (design §4.7).

        B8d: a Bill materialized from an Installment (standalone: bill.installment; embedded: a
        BillLineItem.installment on this bill) orphans that parcela forever otherwise — generation
        never revisits an installment whose plan is MATERIALIZED. Deleting the bill therefore also
        soft-deletes the embedded line(s) and reverts the plan to ACTIVE, so ensure_month_bills can
        materialize the parcela again.
        """
        assert_not_paid(bill)
        CondoMonthCloseService.assert_open(bill.competence_month)
        with transaction.atomic():
            for live_model in (WaterBillStatement, ElectricityBillStatement):
                for statement in live_model.objects.filter(bill=bill):
                    statement.delete(deleted_by=user)
            BillService._revert_installment_materialization(bill, user)
            bill.delete(deleted_by=user)

    @staticmethod
    def _revert_installment_materialization(bill: Bill, user: User | None) -> None:
        """Soft-delete embedded parcela line(s) + revert their plan(s) MATERIALIZED -> ACTIVE."""
        plan_ids: set[int] = set()
        if bill.installment is not None:
            plan_ids.add(bill.installment.plan_id)
        embedded_lines = BillLineItem.objects.filter(bill=bill, installment__isnull=False)
        for line in embedded_lines:
            installment = line.installment
            if installment is not None:
                plan_ids.add(installment.plan_id)
            line.delete(deleted_by=user)
        for plan in InstallmentPlan.objects.filter(
            pk__in=plan_ids, lifecycle_state=InstallmentPlanState.MATERIALIZED
        ):
            plan.lifecycle_state = InstallmentPlanState.ACTIVE
            plan.updated_by = user
            # AuditMixin.save appends updated_at to update_fields automatically.
            plan.save(update_fields=["lifecycle_state", "updated_by"])
