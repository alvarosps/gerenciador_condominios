"""mark_credit_card respects the displayed month, not the server month (P2.5).

_mark_credit_card_paid used the UTC server month to pick which installments to settle,
so paying a card while navigating an earlier month wrongly hit the current server month.
The service now accepts year/month (the displayed month) and falls back to the
payment_date's month, never the raw server clock.
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import CreditCard, Expense, ExpenseInstallment, ExpenseType, Person
from core.services.daily_control_service import DailyControlService

pytestmark = pytest.mark.django_db


@pytest.fixture
def card() -> CreditCard:
    person = Person.objects.create(name="DC Person", relationship="Filho")
    return CreditCard.objects.create(
        person=person, nickname="Card DC", closing_day=15, due_day=22, is_active=True
    )


def _installment(card: CreditCard, due: date, amount: Decimal) -> ExpenseInstallment:
    expense = Expense.objects.create(
        description="Card purchase",
        expense_type=ExpenseType.CARD_PURCHASE,
        total_amount=amount,
        expense_date=due,
        credit_card=card,
        is_installment=True,
        is_offset=False,
    )
    return ExpenseInstallment.objects.create(
        expense=expense,
        installment_number=1,
        total_installments=1,
        amount=amount,
        due_date=due,
        is_paid=False,
    )


@freeze_time("2026-06-02 12:00:00")
def test_mark_credit_card_uses_displayed_month(card: CreditCard) -> None:
    """User navigated to May (year=2026, month=5) and pays the card on 02/06: the MAY
    installments are settled and June stays untouched (the server month is June)."""
    may_inst = _installment(card, date(2026, 5, 22), Decimal("100.00"))
    june_inst = _installment(card, date(2026, 6, 22), Decimal("200.00"))

    result = DailyControlService.mark_item_paid(
        "credit_card", card.id, date(2026, 6, 2), year=2026, month=5
    )
    assert result["status"] == "ok"

    may_inst.refresh_from_db()
    june_inst.refresh_from_db()
    assert may_inst.is_paid is True
    assert june_inst.is_paid is False


@freeze_time("2026-06-02 12:00:00")
def test_mark_credit_card_falls_back_to_payment_date(card: CreditCard) -> None:
    """Without year/month, the month of payment_date drives the selection (not the raw
    server clock). Paying with payment_date 2026-05-30 settles May installments."""
    may_inst = _installment(card, date(2026, 5, 22), Decimal("100.00"))
    june_inst = _installment(card, date(2026, 6, 22), Decimal("200.00"))

    result = DailyControlService.mark_item_paid("credit_card", card.id, date(2026, 5, 30))
    assert result["status"] == "ok"

    may_inst.refresh_from_db()
    june_inst.refresh_from_db()
    assert may_inst.is_paid is True
    assert june_inst.is_paid is False


@freeze_time("2026-06-02 12:00:00")
def test_mark_credit_card_already_paid(card: CreditCard) -> None:
    """No installments in the target month → already_paid (non-regression)."""
    _installment(card, date(2026, 6, 22), Decimal("200.00"))
    result = DailyControlService.mark_item_paid(
        "credit_card", card.id, date(2026, 5, 30), year=2026, month=5
    )
    assert result["status"] == "already_paid"
