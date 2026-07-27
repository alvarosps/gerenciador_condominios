"""Session 37 — BillPaymentService tests (partial/total, over-allocation, funded_from, reversal).

Session 45 wired funded_from='reserve' to a guarded ReserveMovement(withdrawal, bill=...) and
added the closed-month guard, so the reserve tests assert that behavior (a reserve must exist
with sufficient balance; the reserve — not the cash — is debited; unpay restores it).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from finances.models import (
    Bill,
    BillLifecycleState,
    BillLineItem,
    Payment,
    ReserveMovement,
    ReserveMovementKind,
)
from finances.services.bill_payment_service import BillPaymentService
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_installment,
    make_reserve,
    make_reserve_movement,
)

pytestmark = pytest.mark.django_db

PAY_DATE = date(2026, 6, 5)


def _bill_with_total(amount: str) -> Bill:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


def _amounts(bill: Bill) -> Bill:
    return Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)


def test_total_payment() -> None:
    bill = _bill_with_total("900.00")
    payment = BillPaymentService.pay(bill, PAY_DATE)
    assert payment.amount == Decimal("900.00")
    assert payment.allocations.count() == 1
    assert payment.allocations.first().amount == payment.amount
    annotated = _amounts(bill)
    assert annotated.amount_paid == Decimal("900.00")
    assert annotated.amount_remaining == Decimal("0.00")
    assert annotated.payment_status == "paid"


def test_partial_then_total() -> None:
    bill = _bill_with_total("900.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("300.00"))
    mid = _amounts(bill)
    assert mid.payment_status == "partial"
    assert mid.amount_remaining == Decimal("600.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"))
    final = _amounts(bill)
    assert final.payment_status == "paid"
    assert final.amount_paid == Decimal("900.00")


def test_over_allocation_rejected() -> None:
    bill = _bill_with_total("900.00")
    before = Payment.objects.count()
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("1000.00"))
    assert Payment.objects.count() == before
    BillPaymentService.pay(bill, PAY_DATE)  # pay it off
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("1.00"))


def test_non_positive_amount_rejected() -> None:
    bill = _bill_with_total("900.00")
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("0.00"))


def _reserve_with_balance(bill: Bill, balance: str):
    reserve = make_reserve(condominium=bill.condominium)
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal(balance), movement_date=PAY_DATE
    )
    return reserve


def test_funded_from_reserve_creates_withdrawal_and_debits_only_reserve() -> None:
    bill = _bill_with_total("300.00")
    reserve = _reserve_with_balance(bill, "500.00")
    payment = BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")
    assert payment.funded_from == "reserve"
    # amount_paid derives ONLY from PaymentAllocation, never from ReserveMovement.bill (design §4.3)
    assert _amounts(bill).payment_status == "paid"
    assert reserve.movements.filter(kind="withdrawal", bill=bill, amount=Decimal("300.00")).exists()
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("200.00")


def test_funded_from_reserve_requires_a_reserve() -> None:
    bill = _bill_with_total("300.00")
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")


def test_funded_from_reserve_guards_insufficient_balance() -> None:
    bill = _bill_with_total("300.00")
    _reserve_with_balance(bill, "100.00")
    before = Payment.objects.count()
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")
    assert Payment.objects.count() == before  # atomic: nothing persisted


def test_unpay_reserve_payment_restores_reserve_balance() -> None:
    bill = _bill_with_total("300.00")
    _reserve_with_balance(bill, "500.00")
    payment = BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("200.00")
    BillPaymentService.unpay(payment)
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("500.00")
    assert _amounts(bill).payment_status == "open"


def test_reversal_recomposes_remaining() -> None:
    bill = _bill_with_total("900.00")
    payment = BillPaymentService.pay(bill, PAY_DATE)
    BillPaymentService.unpay(payment)
    assert not Payment.objects.filter(pk=payment.pk).exists()
    assert Payment.objects.with_deleted().filter(pk=payment.pk).exists()
    annotated = _amounts(bill)
    assert annotated.amount_remaining == Decimal("900.00")
    assert annotated.payment_status == "open"
    # paying again after reversal works
    BillPaymentService.pay(bill, PAY_DATE)
    assert _amounts(bill).payment_status == "paid"


def test_split_cash_and_reserve_two_payments() -> None:
    bill = _bill_with_total("900.00")
    _reserve_with_balance(bill, "600.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("300.00"), funded_from="caixa")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"), funded_from="reserve")
    annotated = _amounts(bill)
    assert annotated.amount_paid == Decimal("900.00")  # from PaymentAllocation only
    assert annotated.payment_status == "paid"
    assert Payment.objects.filter(allocations__bill=bill).distinct().count() == 2
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("0.00")


def test_sequential_over_allocation_rejected() -> None:
    bill = _bill_with_total("900.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"))
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"))
    assert _amounts(bill).amount_paid == Decimal("600.00")


# --- lifecycle guard: paying a non-ACTIVE bill is a double-charge bug (P2.3 step 1) ---


@pytest.mark.parametrize(
    "state",
    [
        BillLifecycleState.CANCELED,
        BillLifecycleState.SUSPENDED,
        BillLifecycleState.DEFERRED,
    ],
)
def test_pay_rejects_non_active_bill(state: str) -> None:
    bill = _bill_with_total("300.00")
    bill.lifecycle_state = state
    bill.save(update_fields=["lifecycle_state"])
    before = Payment.objects.count()
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE)
    assert Payment.objects.count() == before  # nothing persisted (no double charge)
    assert _amounts(bill).payment_status == "open"


def test_pay_accepts_active_bill() -> None:
    bill = _bill_with_total("300.00")
    payment = BillPaymentService.pay(bill, PAY_DATE)
    assert payment.amount == Decimal("300.00")
    assert _amounts(bill).payment_status == "paid"


# --- B3: the CASH month (payment_date) must also be open, not just competence_month ---


def test_pay_rejects_closed_cash_month_even_when_competence_open() -> None:
    """Bill.competence_month=2026-06 (open); payment_date=2026-05 (closed) must still be rejected."""
    bill = _bill_with_total("300.00")  # competence_month defaults to 2026-06-01, open
    CondoMonthCloseService.close(2026, 5)
    before = Payment.objects.count()
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, date(2026, 5, 20))
    assert Payment.objects.count() == before


def test_unpay_rejects_closed_cash_month_even_when_competence_open() -> None:
    """A payment made in an open cash month, later closed, cannot be reversed anymore."""
    bill = _bill_with_total("300.00")
    payment = BillPaymentService.pay(bill, date(2026, 5, 20))
    CondoMonthCloseService.close(2026, 5)
    with pytest.raises(ValidationError):
        BillPaymentService.unpay(payment)
    assert Payment.objects.filter(pk=payment.pk).exists()


def test_bulk_pay_rejects_closed_cash_month() -> None:
    bill = _bill_with_total("300.00")
    CondoMonthCloseService.close(2026, 5)
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, date(2026, 5, 20))


# --- ReserveMovement.payment FK: deterministic link (P2.3 step 10) ---


def test_reserve_payment_records_movement_with_payment_fk() -> None:
    bill = _bill_with_total("300.00")
    reserve = _reserve_with_balance(bill, "500.00")
    payment = BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")
    movement = reserve.movements.get(kind=ReserveMovementKind.WITHDRAWAL)
    assert movement.payment_id == payment.pk
    assert movement.bill_id == bill.pk


def test_unpay_reverses_via_payment_fk() -> None:
    bill = _bill_with_total("300.00")
    _reserve_with_balance(bill, "500.00")
    payment = BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")
    BillPaymentService.unpay(payment)
    # The withdrawal resolved by the FK is soft-deleted; the reserve balance is restored.
    assert not ReserveMovement.objects.filter(payment=payment).exists()
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("500.00")


def test_unpay_reverses_only_its_own_movement_when_two_share_bill_and_amount() -> None:
    """Two distinct reserve payments of the SAME bill+amount: unpay of one reverses ONLY its
    own movement (the old bill+kind+amount heuristic would reverse the wrong one)."""
    bill = _bill_with_total("600.00")
    _reserve_with_balance(bill, "1000.00")
    pay_a = BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("300.00"), funded_from="reserve")
    pay_b = BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("300.00"), funded_from="reserve")
    move_a = ReserveMovement.objects.get(payment=pay_a)
    move_b = ReserveMovement.objects.get(payment=pay_b)
    assert move_a.pk != move_b.pk

    BillPaymentService.unpay(pay_a)

    assert not ReserveMovement.objects.filter(pk=move_a.pk).exists()  # only pay_a's reversed
    assert ReserveMovement.objects.filter(pk=move_b.pk).exists()
    assert ReserveMovement.objects.get(pk=move_b.pk).payment_id == pay_b.pk
    # 600 deposited - 300 (pay_b still standing) = 700 after restoring pay_a's 300.
    assert CondoBalanceService.reserve_balance(bill.condominium_id) == Decimal("700.00")


# --- Session 68: pay(new_total=...) — adjust the TOTAL before allocating, same transaction ---


def _estimated_bill(seed_amount: str | None, condominium=None) -> Bill:
    """An estimated bill (S65 flag) with 0 or 1 seed line (installment=None)."""
    bill = make_bill(amount_is_estimated=True, condominium=condominium)
    if seed_amount is not None:
        make_bill_line_item(bill=bill, amount=Decimal(seed_amount), description=bill.description)
    return bill


def _confirmed_bill(total_amount: str, condominium=None) -> Bill:
    bill = make_bill(amount_is_estimated=False, condominium=condominium)
    make_bill_line_item(bill=bill, amount=Decimal(total_amount))
    return bill


class TestPayWithNewTotal:
    def test_new_total_none_keeps_current_behavior(self) -> None:
        """new_total ausente: pagamento total idêntico ao comportamento atual."""
        bill = _bill_with_total("900.00")
        payment = BillPaymentService.pay(bill, PAY_DATE)
        assert payment.amount == Decimal("900.00")
        assert _amounts(bill).payment_status == "paid"

    def test_estimated_seed_adjusted_up_and_fully_paid(self) -> None:
        """Fatura real maior que a estimativa: semente ajustada e paga sem over-allocation."""
        bill = _estimated_bill("200.00")
        payment = BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("230.00"), new_total=Decimal("230.00")
        )
        assert payment.amount == Decimal("230.00")
        annotated = _amounts(bill)
        assert annotated.amount_total == Decimal("230.00")
        assert annotated.amount_remaining == Decimal("0.00")
        assert annotated.payment_status == "paid"

    def test_estimated_seed_adjusted_down_no_ghost_remainder(self) -> None:
        """Fatura real menor: sem resto-fantasma de R$20."""
        bill = _estimated_bill("200.00")
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("180.00"), new_total=Decimal("180.00")
        )
        annotated = _amounts(bill)
        assert annotated.amount_total == Decimal("180.00")
        assert annotated.amount_remaining == Decimal("0.00")

    def test_estimated_with_embedded_installment_adjusts_only_seed(self) -> None:
        """Delta aplicado só na semente; linha de parcela intocável."""
        bill = _estimated_bill("200.00")
        installment_line = make_bill_line_item(
            bill=bill,
            amount=Decimal("530.00"),
            description="Parcela 3/12",
            installment=make_installment(),
        )
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("750.00"), new_total=Decimal("750.00")
        )
        seed = BillLineItem.objects.get(bill=bill, installment__isnull=True)
        assert seed.amount == Decimal("220.00")
        installment_line.refresh_from_db()
        assert installment_line.amount == Decimal("530.00")
        assert _amounts(bill).amount_total == Decimal("750.00")

    def test_estimated_zero_lines_creates_seed(self) -> None:
        """Bill 'aguardando fatura' paga em 1 clique cria a semente."""
        bill = _estimated_bill(None)
        assert BillLineItem.objects.filter(bill=bill).count() == 0
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("150.00"), new_total=Decimal("150.00")
        )
        seed = BillLineItem.objects.get(bill=bill, installment__isnull=True)
        assert seed.description == bill.description
        assert seed.is_offset is False
        assert seed.amount == Decimal("150.00")
        annotated = _amounts(bill)
        assert annotated.amount_total == Decimal("150.00")
        assert annotated.payment_status == "paid"

    def test_estimated_multiple_non_installment_lines_rejected(self) -> None:
        """Semente ambígua: rejeita e não altera nada."""
        bill = _estimated_bill("100.00")
        make_bill_line_item(bill=bill, amount=Decimal("100.00"), description="Outra linha")
        before_amounts = [item.amount for item in BillLineItem.objects.filter(bill=bill)]
        with pytest.raises(ValidationError):
            BillPaymentService.pay(bill, PAY_DATE, new_total=Decimal("300.00"))
        after_amounts = [item.amount for item in BillLineItem.objects.filter(bill=bill)]
        assert after_amounts == before_amounts
        assert Payment.objects.count() == 0

    def test_new_total_below_embedded_installments_rejected(self) -> None:
        """new_total abaixo da soma das parcelas: semente negativa é impossível."""
        bill = _estimated_bill("200.00")
        make_bill_line_item(
            bill=bill,
            amount=Decimal("530.00"),
            description="Parcela 3/12",
            installment=make_installment(),
        )
        with pytest.raises(ValidationError):
            BillPaymentService.pay(bill, PAY_DATE, new_total=Decimal("500.00"))
        seed = BillLineItem.objects.get(bill=bill, installment__isnull=True)
        assert seed.amount == Decimal("200.00")
        assert Payment.objects.count() == 0

    def test_estimated_new_total_equal_to_installments_zeroes_seed(self) -> None:
        """Fronteira: new_total == soma das parcelas embutidas zera a semente (permitido)."""
        bill = _estimated_bill("200.00")
        make_bill_line_item(
            bill=bill,
            amount=Decimal("530.00"),
            description="Parcela 3/12",
            installment=make_installment(),
        )
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("530.00"), new_total=Decimal("530.00")
        )
        seed = BillLineItem.objects.get(bill=bill, installment__isnull=True)
        assert seed.amount == Decimal("0.00")
        assert _amounts(bill).amount_total == Decimal("530.00")

    def test_over_allocation_still_guarded_after_adjustment(self) -> None:
        """Guard de over-allocation vale APÓS o ajuste, e o rollback desfaz o ajuste."""
        bill = _estimated_bill("200.00")
        with pytest.raises(ValidationError):
            BillPaymentService.pay(
                bill, PAY_DATE, amount=Decimal("250.00"), new_total=Decimal("230.00")
            )
        seed = BillLineItem.objects.get(bill=bill, installment__isnull=True)
        assert seed.amount == Decimal("200.00")  # rolled back
        assert Payment.objects.count() == 0
        bill.refresh_from_db()
        assert bill.amount_is_estimated is True

    def test_confirmed_new_total_above_adds_juros_multa_line(self) -> None:
        """Juros/multa CEEE/DMAE em bill confirmada de linha única."""
        bill = _confirmed_bill("300.00")
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("315.00"), new_total=Decimal("315.00")
        )
        juros = BillLineItem.objects.get(bill=bill, description="Juros/multa")
        assert juros.amount == Decimal("15.00")
        assert juros.is_offset is False
        assert juros.category_id is None
        annotated = _amounts(bill)
        assert annotated.amount_total == Decimal("315.00")
        assert annotated.payment_status == "paid"

    def test_confirmed_new_total_below_rejected(self) -> None:
        """Reduzir total em confirmada é edição, não pagamento."""
        bill = _confirmed_bill("300.00")
        with pytest.raises(ValidationError) as exc_info:
            BillPaymentService.pay(bill, PAY_DATE, new_total=Decimal("280.00"))
        assert "Edite a conta para reduzir o valor." in str(exc_info.value)
        assert Payment.objects.count() == 0

    def test_confirmed_multiple_lines_new_total_adds_juros_multa(self) -> None:
        """Juros/multa em confirmada multi-linha (fatura importada CEEE/DMAE paga com atraso)."""
        bill = make_bill(amount_is_estimated=False)
        line_1 = make_bill_line_item(bill=bill, amount=Decimal("200.00"), description="Consumo")
        line_2 = make_bill_line_item(bill=bill, amount=Decimal("150.00"), description="Taxa")
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("400.00"), new_total=Decimal("400.00")
        )
        line_1.refresh_from_db()
        line_2.refresh_from_db()
        assert line_1.amount == Decimal("200.00")
        assert line_2.amount == Decimal("150.00")
        juros = BillLineItem.objects.get(bill=bill, description="Juros/multa")
        assert juros.amount == Decimal("50.00")
        annotated = _amounts(bill)
        assert annotated.amount_total == Decimal("400.00")
        assert annotated.payment_status == "paid"

    def test_confirmed_partially_paid_new_total_adds_juros_on_top(self) -> None:
        """Juros sobre o resto: caso real de atraso em bill parcialmente paga."""
        bill = _confirmed_bill("300.00")
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("100.00"))
        BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("215.00"), new_total=Decimal("315.00")
        )
        juros = BillLineItem.objects.get(bill=bill, description="Juros/multa")
        assert juros.amount == Decimal("15.00")
        annotated = _amounts(bill)
        assert annotated.amount_total == Decimal("315.00")
        assert annotated.amount_remaining == Decimal("0.00")

    def test_confirmed_new_total_equal_is_noop(self) -> None:
        """new_total igual ao total: no-op."""
        bill = _confirmed_bill("300.00")
        lines_before = BillLineItem.objects.filter(bill=bill).count()
        BillPaymentService.pay(bill, PAY_DATE, new_total=Decimal("300.00"))
        assert BillLineItem.objects.filter(bill=bill).count() == lines_before
        assert _amounts(bill).payment_status == "paid"

    def test_amount_default_is_adjusted_remaining(self) -> None:
        """amount=None defaulta para o resto PÓS-ajuste."""
        bill = _estimated_bill("200.00")
        payment = BillPaymentService.pay(bill, PAY_DATE, new_total=Decimal("230.00"))
        assert payment.amount == Decimal("230.00")

    def test_new_total_respects_active_and_closed_month_guards(self) -> None:
        """Guards ACTIVE/mês fechado inalterados com new_total."""
        suspended = _estimated_bill("200.00")
        suspended.lifecycle_state = BillLifecycleState.SUSPENDED
        suspended.save(update_fields=["lifecycle_state"])
        with pytest.raises(ValidationError):
            BillPaymentService.pay(suspended, PAY_DATE, new_total=Decimal("230.00"))

        closed_month_bill = _estimated_bill("200.00")
        closed_month_bill.competence_month = date(2026, 5, 1)
        closed_month_bill.save(update_fields=["competence_month"])
        CondoMonthCloseService.close(2026, 5)
        with pytest.raises(ValidationError):
            BillPaymentService.pay(
                closed_month_bill, date(2026, 5, 20), new_total=Decimal("230.00")
            )

    def test_estimated_flag_cleared_after_pay_with_new_total(self) -> None:
        """Pagar com ajuste também confirma a bill (regressão do contrato S65)."""
        bill = _estimated_bill("200.00")
        BillPaymentService.pay(bill, PAY_DATE, new_total=Decimal("230.00"))
        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

    def test_unpay_keeps_adjustment_and_flag(self) -> None:
        """unpay reverte só o pagamento, nunca o ajuste de linhas/flag."""
        bill = _confirmed_bill("300.00")
        payment = BillPaymentService.pay(
            bill, PAY_DATE, amount=Decimal("315.00"), new_total=Decimal("315.00")
        )
        BillPaymentService.unpay(payment)
        assert BillLineItem.objects.filter(bill=bill, description="Juros/multa").exists()
        bill.refresh_from_db()
        assert bill.amount_is_estimated is False
        assert _amounts(bill).payment_status == "open"
