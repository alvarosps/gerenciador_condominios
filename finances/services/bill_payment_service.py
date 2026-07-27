"""Bill payment (partial / total) with over-allocation guard (Phase 2, Session 37;
reserve funding + closed-month guard added in Session 45).

pay() creates a Payment + one PaymentAllocation; unpay() reverses via soft-delete.
amount_remaining is read from Bill.objects.with_amounts (never summed in Python).

Session 45 extensions:
- CondoMonthCloseService.assert_open(bill.competence_month) rejects pay/unpay on a closed month.
- funded_from='reserve' also records a ReserveMovement(withdrawal, bill=...) on the condominium's
  reserve, guarded so the reserve never goes negative; unpay reverses that movement too. A
  reserve-funded payment debits only the reserve, never the cash (design §4.3).

B3: pay/unpay/bulk_pay (bulk_pay delegates to pay per bill) also guard the CASH month
(payment_date) via the same CondoMonthCloseService.assert_open, not just competence_month — a
payment dated into a closed cash month would silently change that month's frozen
cash_balance_end even though the bill's own competence month is still open.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Protocol, cast

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Person
from core.services.timezone import today_sp
from finances.models import (
    ERR_PERSON_ONLY_THIRD_PARTY,
    ERR_THIRD_PARTY_NEEDS_PERSON,
    Bill,
    BillLifecycleState,
    BillLineItem,
    FundedFrom,
    Payment,
    PaymentAllocation,
    Reserve,
    ReserveMovement,
)
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.reserve_service import ReserveService

logger = logging.getLogger(__name__)


class _BillRemaining(Protocol):
    # Bill.objects.with_amounts(today) annotates amount_remaining/amount_total; django-stubs
    # does not propagate dynamic annotations onto the model instance, so we read them via cast.
    amount_remaining: Decimal
    amount_total: Decimal


_AMOUNT_NON_POSITIVE = "O valor do pagamento deve ser positivo."
_OVER_ALLOCATION = "O valor do pagamento excede o saldo devedor da conta."
_NO_RESERVE = "Nenhuma reserva configurada para o condomínio."
_BILL_NOT_ACTIVE = "Só é possível pagar uma conta ativa."
_ESTIMATED_MULTIPLE_LINES = "A conta estimada tem mais de uma linha — edite a conta pelas linhas."
_NEW_TOTAL_BELOW_INSTALLMENTS = "O novo total é menor que a soma das parcelas embutidas da conta."
_NEW_TOTAL_BELOW_TOTAL = "Edite a conta para reduzir o valor."
_SURCHARGE_DESCRIPTION = "Juros/multa"
# S80 §4b: a third-party purchase is born paid, so reversing its payment would leave the Bill
# ACTIVE and unpaid — a "conta a pagar do caixa" in the cockpit while the person's statement
# still charges the debt. The same money twice. delete_purchase is the only correction path.
ERR_UNPAY_THIRD_PARTY_PURCHASE = (
    "Uma compra de terceiro não pode ter o pagamento desfeito — exclua a compra."
)


class BillPaymentService:
    """Stateless bill payment / reversal."""

    @staticmethod
    def pay(
        bill: Bill,
        payment_date: date,
        amount: Decimal | None = None,
        funded_from: str = FundedFrom.CAIXA,
        new_total: Decimal | None = None,
        paid_by: Person | None = None,
        user: User | None = None,
    ) -> Payment:
        """Pay a Bill (partial or total). Σ(allocation) == payment.amount; over-allocation rejected.

        funded_from='reserve' additionally debits the condominium reserve via a
        ReserveMovement(withdrawal, bill=..., payment=...) with a balance guard (design §4.3).
        Only an ACTIVE bill is payable — a CANCELED/SUSPENDED/DEFERRED one would be a double
        charge (its expense is already excluded from the result), so it is rejected (PT 400).
        A payment (total OR partial) means the real value is now known, so a still-estimated
        bill has its amount_is_estimated flag cleared in the SAME transaction (S65) — bulk_pay
        covers this by delegating to pay() per bill.

        new_total (S68, design §3.3/§9): when the real value differs from the current total
        (estimated bill) or a late invoice adds interest (confirmed bill), adjusts amount_total
        to exactly new_total BEFORE allocating, in the SAME transaction, via _apply_new_total —
        never by summing amount_remaining + delta in Python. The over-allocation/positive-amount
        guards below therefore run AFTER the adjustment (remaining is re-read post-adjustment),
        so amount=None defaults to the adjusted remaining and a bad amount rolls the adjustment
        back with everything else (atomic). Installment-linked lines (BillLineItem.installment
        set) are never touched by the adjustment, in any branch.

        paid_by (S80) is the person who funded the payment out of her own pocket. Its position in
        the signature (after new_total, before user) is load-bearing: the production callers pass
        bill/payment_date/amount/funded_from positionally. Payment.objects.create() skips
        full_clean(), so the S77 invariant (THIRD_PARTY needs a person, any other funding forbids
        one) is enforced HERE, before the row is written. funded_from=THIRD_PARTY debits neither
        the reserve nor the cash — the money came from the person, and only the settlement that
        repays her leaves the condominium (design §5).
        """
        BillPaymentService._assert_paid_by_matches_funding(funded_from, paid_by)
        CondoMonthCloseService.assert_open(bill.competence_month)
        CondoMonthCloseService.assert_open(payment_date.replace(day=1))
        if bill.lifecycle_state != BillLifecycleState.ACTIVE:
            raise ValidationError(_BILL_NOT_ACTIVE)
        today = today_sp()
        with transaction.atomic():
            locked = Bill.objects.select_for_update().get(pk=bill.pk)
            if new_total is not None:
                BillPaymentService._apply_new_total(locked, new_total, user)
            # amount_remaining is the with_amounts annotation (never sum in Python, design §4.4).
            annotated = cast(_BillRemaining, Bill.objects.with_amounts(today).get(pk=locked.pk))
            remaining: Decimal = annotated.amount_remaining
            if amount is None:
                amount = remaining
            if amount <= 0:
                raise ValidationError(_AMOUNT_NON_POSITIVE)
            if amount > remaining:
                raise ValidationError(_OVER_ALLOCATION)
            payment = Payment.objects.create(
                condominium=locked.condominium,
                payment_date=payment_date,
                amount=amount,
                funded_from=funded_from,
                paid_by=paid_by,
                created_by=user,
                updated_by=user,
            )
            PaymentAllocation.objects.create(
                payment=payment,
                bill=locked,
                amount=amount,
                created_by=user,
                updated_by=user,
            )
            if payment.funded_from == FundedFrom.RESERVE:
                BillPaymentService._withdraw_reserve_for_bill(
                    locked, payment, amount, payment_date, user
                )
            if locked.amount_is_estimated:
                locked.amount_is_estimated = False
                locked.updated_by = user
                # AuditMixin.save appends updated_at to update_fields automatically.
                locked.save(update_fields=["amount_is_estimated", "updated_by"])
            logger.info("Bill %s paid %s (funded_from=%s)", locked.pk, amount, funded_from)
        return payment

    @staticmethod
    def unpay(payment: Payment, user: User | None = None) -> None:
        """Reverse a payment by soft-deleting it and its allocations (recomposes amount_remaining).

        A reserve-funded payment also reverses every ReserveMovement(withdrawal) linked to it by
        the deterministic ``payment`` FK (never the old bill+kind+amount heuristic, which could
        reverse a sibling payment's movement). Rejected on a closed competence month OR a closed
        cash month (payment_date) — B3: reversing a payment made in a now-closed cash month would
        change that month's frozen cash_balance_end (assert_open).

        Also rejected (S80 §4b) when any allocated bill is a third-party purchase: the purchase is
        born paid, so reversing the payment would leave the Bill active-and-unpaid in the cockpit
        while the person's statement keeps charging the debt. Use
        ThirdPartyPurchaseService.delete_purchase, which removes both sides atomically.
        """
        BillPaymentService._assert_reversible(payment)
        with transaction.atomic():
            CondoMonthCloseService.assert_open(payment.payment_date.replace(day=1))
            for allocation in payment.allocations.all():
                CondoMonthCloseService.assert_open(allocation.bill.competence_month)
                allocation.delete(deleted_by=user)
            for movement in ReserveMovement.objects.filter(payment=payment):
                movement.delete(deleted_by=user)
            payment.delete(deleted_by=user)
            logger.info("Payment %s reversed", payment.pk)

    @staticmethod
    def reverse_purchase_payment(payment: Payment, user: User | None = None) -> None:
        """Internal reversal used ONLY by ThirdPartyPurchaseService.delete_purchase (S80 §4b).

        Same mechanics as unpay (soft-delete allocations + payment) minus the third-party
        rejection, because here the Bill is being deleted in the SAME transaction — the "active
        and unpaid" state unpay() protects against never materializes. The closed-month guards
        still apply; the caller runs them first so nothing is written on a frozen month.
        """
        CondoMonthCloseService.assert_open(payment.payment_date.replace(day=1))
        for allocation in payment.allocations.all():
            CondoMonthCloseService.assert_open(allocation.bill.competence_month)
            allocation.delete(deleted_by=user)
        payment.delete(deleted_by=user)

    @staticmethod
    def _assert_reversible(payment: Payment) -> None:
        """Reject reversing a payment that settles a third-party purchase (S80 §4b)."""
        is_purchase_payment = payment.allocations.filter(
            bill__paid_by_person__isnull=False
        ).exists()
        if is_purchase_payment:
            raise ValidationError(ERR_UNPAY_THIRD_PARTY_PURCHASE)

    @staticmethod
    def _assert_paid_by_matches_funding(funded_from: str, paid_by: Person | None) -> None:
        """Mirror Payment.clean()'s third-party invariant before Payment.objects.create().

        create() skips full_clean(), so without this the model rule would not protect this path
        at all. The messages are imported from finances.models (single source, S77).
        """
        is_third_party = funded_from == FundedFrom.THIRD_PARTY.value
        if is_third_party and paid_by is None:
            raise ValidationError(ERR_THIRD_PARTY_NEEDS_PERSON)
        if not is_third_party and paid_by is not None:
            raise ValidationError(ERR_PERSON_ONLY_THIRD_PARTY)

    @staticmethod
    def _apply_new_total(bill: Bill, new_total: Decimal, user: User | None) -> None:
        """Adjust bill's amount_total to exactly new_total, before allocation (S68).

        Dispatches on the S65 amount_is_estimated flag: an estimated bill adjusts (or creates)
        its single seed line by delta; a confirmed bill (any number of lines — an imported
        multi-line invoice paid late is exactly the Juros/multa case) only ever grows via a
        surcharge line, never shrinks (that is an edit, not a payment).
        """
        if bill.amount_is_estimated:
            BillPaymentService._adjust_estimated_seed(bill, new_total, user)
        else:
            BillPaymentService._append_surcharge_line(bill, new_total, user)

    @staticmethod
    def _adjust_estimated_seed(bill: Bill, new_total: Decimal, user: User | None) -> None:
        """Adjust (or create) the single non-installment seed line of an estimated bill by delta.

        Installment-linked lines are never seeds (they are the embedded parcela, S41) and are
        excluded from both the count and the adjustment. Exactly one seed -> shift its amount by
        (new_total - current total); zero seeds ("aguardando fatura", expected_amount=0 at
        generation) -> create one in the shape BillGenerationService._ensure_account_bill uses;
        more than one is an ambiguous edit, rejected (PT). full_clean() enforces amount >= 0 —
        the seed CAN land on exactly 0 (new_total == the embedded installments' sum) but never
        negative.
        """
        seeds = list(BillLineItem.objects.filter(bill=bill, installment__isnull=True))
        current_total = cast(
            _BillRemaining, Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)
        ).amount_total
        delta = new_total - current_total
        if len(seeds) == 0:
            seed = BillLineItem(
                bill=bill,
                description=bill.description,
                amount=delta,
                is_offset=False,
                category=bill.category,
                created_by=user,
                updated_by=user,
            )
        elif len(seeds) == 1:
            seed = seeds[0]
            seed.amount += delta
            seed.updated_by = user
        else:
            raise ValidationError(_ESTIMATED_MULTIPLE_LINES)
        if seed.amount < 0:
            raise ValidationError(_NEW_TOTAL_BELOW_INSTALLMENTS)
        seed.full_clean(exclude=["bill"])
        seed.save()

    @staticmethod
    def _append_surcharge_line(bill: Bill, new_total: Decimal, user: User | None) -> None:
        """Grow a confirmed bill's total to new_total via a 'Juros/multa' line; never shrink it.

        Applies regardless of how many lines the bill already has (an imported CEEE/DMAE
        multi-line invoice paid late is exactly this case). Equal totals are a no-op; a lower
        new_total is rejected (PT) — reducing a confirmed total is an edit (update_with_lines),
        not a payment.
        """
        current_total = cast(
            _BillRemaining, Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)
        ).amount_total
        if new_total < current_total:
            raise ValidationError(_NEW_TOTAL_BELOW_TOTAL)
        if new_total == current_total:
            return
        surcharge = BillLineItem(
            bill=bill,
            description=_SURCHARGE_DESCRIPTION,
            amount=new_total - current_total,
            is_offset=False,
            category=None,
            created_by=user,
            updated_by=user,
        )
        surcharge.full_clean(exclude=["bill"])
        surcharge.save()

    @staticmethod
    def _withdraw_reserve_for_bill(
        bill: Bill, payment: Payment, amount: Decimal, movement_date: date, user: User | None
    ) -> None:
        """Debit the condominium reserve for a bill payment (guard lives in ReserveService.withdraw).

        The withdrawal carries the driving ``payment`` so unpay can reverse it deterministically.
        """
        reserve = Reserve.objects.filter(condominium=bill.condominium).order_by("id").first()
        if reserve is None:
            raise ValidationError(_NO_RESERVE)
        ReserveService.withdraw(
            reserve, amount, movement_date, bill=bill, payment=payment, user=user
        )
