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
from django.db import transaction

from core.models import Building, Condominium
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    Category,
    ElectricityBillStatement,
    Installment,
    WaterBillStatement,
)
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.timezone import today_sp

logger = logging.getLogger(__name__)

_ERR_STATEMENT_TYPE = "Statement só é permitida para contas de água ou luz."
_ERR_BILL_PAID = "Não é possível alterar uma conta com pagamento. Desfaça o pagamento primeiro."

_STATEMENT_MODEL_BY_TYPE: dict[str, type[WaterBillStatement | ElectricityBillStatement]] = {
    BillingAccountType.WATER: WaterBillStatement,
    BillingAccountType.ELECTRICITY: ElectricityBillStatement,
}


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
        """
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
        return bill

    @staticmethod
    def update_with_lines(
        bill: Bill,
        lines: list[BillLineInput],
        statement: StatementInput | None = None,
        user: User | None = None,
    ) -> Bill:
        """Replace the bill's lines + upsert the statement on the SAME Bill (pk/payments kept).

        Allowed only while the bill is UNPAID (payment_status == 'open', read from
        with_amounts — never summed in Python) and its competence month is OPEN
        (CondoMonthCloseService.assert_open). Old lines are soft-deleted (audit history kept);
        with_amounts ignores soft-deleted lines. Raises (PT) when paid or month closed.
        """
        annotated = Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)
        if str(getattr(annotated, "payment_status", "open")) != "open":
            raise ValidationError(_ERR_BILL_PAID)
        CondoMonthCloseService.assert_open(bill.competence_month)
        with transaction.atomic():
            for line in BillLineItem.objects.filter(bill=bill):
                line.delete(deleted_by=user)
            BillService._write_lines(bill, lines, user)
            BillService._upsert_statement(bill, bill.billing_account, statement, user)
        return bill

    @staticmethod
    def delete(bill: Bill, user: User | None = None) -> None:
        """Soft-delete the bill and cascade the soft-delete to its live statement.

        SoftDeleteMixin.delete() only touches the record itself (it does not walk the reverse
        OneToOne), so the statement is soft-deleted explicitly here (design §7.3).
        """
        with transaction.atomic():
            for live_model in (WaterBillStatement, ElectricityBillStatement):
                for statement in live_model.objects.filter(bill=bill):
                    statement.delete(deleted_by=user)
            bill.delete(deleted_by=user)
