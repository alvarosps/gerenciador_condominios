"""Bill creation with line items, orchestrated in the service (Phase 2, Session 37).

Bill + BillLineItem(s) are created atomically here, not in a writable nested
serializer (design §8 / architecture: business logic in services). The Bill fields
are grouped into the cohesive BillDraft value object so the service signature stays
small; the S38 viewset builds a BillDraft from validated data and passes the lines.
"""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NotRequired, TypedDict

from django.contrib.auth.models import User
from django.db import transaction

from core.models import Building, Condominium
from finances.models import Bill, BillingAccount, BillLifecycleState, BillLineItem, Category

logger = logging.getLogger(__name__)


class BillLineInput(TypedDict):
    description: str
    amount: Decimal
    is_offset: NotRequired[bool]
    category: NotRequired[Category | None]


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
    def create_with_lines(
        draft: BillDraft, lines: list[BillLineInput], user: User | None = None
    ) -> Bill:
        """Create a Bill plus its BillLineItem(s) atomically.

        amount_total derives from the lines via Bill.objects.with_amounts(today).
        Any line failing validation (e.g. amount < 0) rolls the whole Bill back.
        An empty lines list is accepted (amount_total == 0; lines can be added later).
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
            for line in lines:
                item = BillLineItem(
                    bill=bill,
                    description=line["description"],
                    amount=line["amount"],
                    is_offset=line.get("is_offset", False),
                    category=line.get("category"),
                    created_by=user,
                    updated_by=user,
                )
                item.full_clean(exclude=["bill"])  # PT amount >= 0
                item.save()
        return bill
