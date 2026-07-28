"""Session 80 — third-party purchase lifecycle (design §4.3.1 / §4.5).

A third-party purchase is a ``Bill(paid_by_person=P)`` that is **born paid**: the person already
put the money in (her own card), so the Bill and the ``Payment(THIRD_PARTY, paid_by=P)`` that
settles it are created in the SAME transaction. It never moves the condominium's cash — only the
``ThirdPartySettlement`` that repays her does (design §5).

Being born paid has a consequence the adversarial review caught: ``BillService.assert_not_paid``
blocks suspend/cancel/delete/update_with_lines on any bill with a live payment, so a mistyped
purchase would be uncorrectable from the UI. Hence the two correction paths that live here:

- ``delete_purchase`` — removes Bill + Payment + allocation atomically (the ONLY way to undo a
  purchase; ``BillPaymentService.unpay`` deliberately rejects them);
- ``reassign_payer`` — fixes a wrong payer on BOTH sides (``Bill.paid_by_person`` and
  ``Payment.paid_by``) in one transaction, since ``paid_by_person`` is not an editable header
  field and ``update_with_lines`` would hit ``assert_not_paid``.

**Instalments deliberately do NOT use ``InstallmentPlan``** (design §4.5): that mechanism
materializes Bills later, in a monthly batch job, from a hardcoded defaults dict with no
``paid_by_person`` and born UNPAID — the exact opposite of a purchase. ``create_purchase`` builds
the N Bills + N Payments itself, in one transaction, with the cents remainder on the FIRST parcela
so Σ(parcelas) == the exact total.
"""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Building, Condominium, Person
from finances.models import (
    Bill,
    BillBehavior,
    BillLineItem,
    Category,
    FundedFrom,
    Payment,
)
from finances.money import quantize_money
from finances.services.bill_payment_service import BillPaymentService
from finances.services.condo_month_close_service import CondoMonthCloseService

logger = logging.getLogger(__name__)

ERR_AMOUNT_NON_POSITIVE = "O valor da compra deve ser positivo."
ERR_INSTALLMENT_COUNT = "O número de parcelas deve ser no mínimo 1."
ERR_INSTALLMENT_COUNT_MAX = "O número de parcelas deve ser no máximo 60."
ERR_NOT_A_PURCHASE = "Esta conta não é uma compra de terceiro."
ERR_NO_PURCHASE_PAYMENT = "Esta compra não tem pagamento de terceiro para corrigir."
MAX_INSTALLMENT_COUNT = 60


def _assert_month_open(month: date) -> None:
    """Closed-month guard that names WHICH month — a purchase spans competence AND cash.

    Delegates to the canonical ``CondoMonthCloseService.assert_open``: a second copy of a
    safety-critical predicate is exactly the duplication the project rules forbid.
    """
    CondoMonthCloseService.assert_open(month, name_month=True)


def _add_months(month: date, offset: int) -> date:
    total = month.month - 1 + offset
    return date(month.year + total // 12, total % 12 + 1, 1)


def _split_amount(total: Decimal, count: int) -> list[Decimal]:
    """Split ``total`` into ``count`` parcelas with the cents remainder on the FIRST one.

    Σ(result) == total exactly — never create or lose a cent (design §4.5).
    """
    base = quantize_money(total / count)
    parcels = [base] * count
    parcels[0] = quantize_money(total) - base * (count - 1)
    return parcels


@dataclass(frozen=True, kw_only=True)
class PurchaseDraft:
    """What the client submits for a third-party purchase (cohesive value object).

    Mirrors ``BillService.BillDraft``: the service signature stays small and the viewset builds
    the draft from the validated payload.
    """

    condominium: Condominium
    person: Person
    description: str
    amount: Decimal
    competence_month: date
    due_date: date
    category: Category | None = None
    building: Building | None = None
    installment_count: int = 1


class ThirdPartyPurchaseService:
    """Stateless third-party purchase creation / correction (design §4.3.1, §4.5)."""

    @staticmethod
    def create_purchase(draft: PurchaseDraft, user: User | None = None) -> list[Bill]:
        """Create the purchase — N Bills each born paid by ``person``, in ONE transaction.

        ``installment_count=1`` (the default) is the plain purchase: one Bill with one line and
        one Payment. With N > 1, parcela *i* lands on ``competence_month + i`` with the
        description suffixed "(i/N)"; ``Bill.installment`` stays empty (it is not a condominium
        plan) and the cents remainder sits on the first parcela.

        Every competence month AND the cash month (``due_date``) are checked for closure BEFORE
        anything is written, and the messages name the month — one closed month rejects the whole
        operation. A failure at any point rolls the entire purchase back: no orphan Bill.
        """
        count = draft.installment_count
        if draft.amount <= 0:
            raise ValidationError(ERR_AMOUNT_NON_POSITIVE)
        if count < 1:
            raise ValidationError(ERR_INSTALLMENT_COUNT)
        if count > MAX_INSTALLMENT_COUNT:
            raise ValidationError(ERR_INSTALLMENT_COUNT_MAX)

        months = [_add_months(draft.competence_month, index) for index in range(count)]
        for month in months:
            _assert_month_open(month)
        _assert_month_open(draft.due_date)

        parcels = _split_amount(draft.amount, count)
        with transaction.atomic():
            return [
                ThirdPartyPurchaseService._create_one(
                    draft=draft,
                    description=(
                        draft.description
                        if count == 1
                        else f"{draft.description} ({index + 1}/{count})"
                    ),
                    amount=parcels[index],
                    competence_month=month,
                    user=user,
                )
                for index, month in enumerate(months)
            ]

    @staticmethod
    def _create_one(
        *,
        draft: PurchaseDraft,
        description: str,
        amount: Decimal,
        competence_month: date,
        user: User | None,
    ) -> Bill:
        """One purchase Bill + its single line + the Payment that settles it.

        The Bill is created directly (not through ``BillService.create_with_lines``) because a
        purchase carries ``paid_by_person``, which ``BillDraft`` deliberately does not model —
        BillDraft describes the condominium's own payables, and adding an attribution field to it
        would leak the third-party concern into every ordinary bill creation path.
        """
        bill = Bill(
            condominium=draft.condominium,
            building=draft.building,
            category=draft.category,
            paid_by_person=draft.person,
            competence_month=competence_month,
            due_date=draft.due_date,
            description=description,
            behavior=BillBehavior.ONE_TIME,
            created_by=user,
            updated_by=user,
        )
        bill.full_clean()
        bill.save()
        line = BillLineItem(
            bill=bill,
            description=description,
            amount=amount,
            is_offset=False,
            category=draft.category,
            created_by=user,
            updated_by=user,
        )
        line.full_clean(exclude=["bill"])
        line.save()
        BillPaymentService.pay(
            bill,
            draft.due_date,
            None,
            FundedFrom.THIRD_PARTY,
            paid_by=draft.person,
            user=user,
        )
        logger.info("Third-party purchase %s created for person %s", bill.pk, draft.person.pk)
        return bill

    @staticmethod
    def delete_purchase(bill: Bill, user: User | None = None) -> None:
        """Remove a purchase entirely — Bill + Payment + allocation — atomically (design §4.3.1).

        The ONLY correction path for a mistyped purchase: ``BillService.delete`` hits
        ``assert_not_paid`` (the purchase is born paid) and ``BillPaymentService.unpay`` rejects
        purchase payments outright. Both months (competence and cash) must be open, since removing
        the pair changes what those months report.
        """
        if bill.paid_by_person_id is None:
            raise ValidationError(ERR_NOT_A_PURCHASE)
        _assert_month_open(bill.competence_month)
        payments = ThirdPartyPurchaseService._purchase_payments(bill)
        for payment in payments:
            _assert_month_open(payment.payment_date)
        with transaction.atomic():
            for payment in payments:
                BillPaymentService.reverse_purchase_payment(payment, user=user)
            bill.delete(deleted_by=user)
            logger.info("Third-party purchase %s deleted", bill.pk)

    @staticmethod
    def reassign_payer(bill: Bill, person: Person, user: User | None = None) -> Bill:
        """Move a purchase to another payer — BOTH sides in one transaction (design §4.3.1).

        ``Bill.paid_by_person`` alone would leave ``Payment.paid_by`` pointing at the old person,
        so her statement would keep the payment while the purchase moved: the debt would be split
        across two people and neither total would be true.

        Both months (competence and cash) must be OPEN, exactly as in ``delete_purchase``: this
        rewrites WHO is owed money in those months, so doing it inside a frozen month would leave
        the ledger disagreeing with that month's snapshot — the B3 bug class this codebase already
        fixed for payments.
        """
        if bill.paid_by_person_id is None:
            raise ValidationError(ERR_NOT_A_PURCHASE)
        _assert_month_open(bill.competence_month)
        payments = ThirdPartyPurchaseService._purchase_payments(bill)
        if not payments:
            raise ValidationError(ERR_NO_PURCHASE_PAYMENT)
        for payment in payments:
            _assert_month_open(payment.payment_date)
        with transaction.atomic():
            bill.paid_by_person = person
            bill.updated_by = user
            # AuditMixin.save appends updated_at to update_fields automatically.
            bill.save(update_fields=["paid_by_person", "updated_by"])
            for payment in payments:
                payment.paid_by = person
                payment.updated_by = user
                payment.save(update_fields=["paid_by", "updated_by"])
            logger.info("Third-party purchase %s reassigned to person %s", bill.pk, person.pk)
        return bill

    @staticmethod
    def _purchase_payments(bill: Bill) -> list[Payment]:
        """The live third-party Payments allocated to this bill (usually exactly one)."""
        return list(
            Payment.objects.filter(
                allocations__bill=bill,
                allocations__is_deleted=False,
                funded_from=FundedFrom.THIRD_PARTY,
            ).distinct()
        )
