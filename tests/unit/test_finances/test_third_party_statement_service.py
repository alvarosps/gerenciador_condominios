"""Session 79 — ThirdPartyStatementService.build (design §6).

The rule in one sentence: chronological FIFO allocation of the person's settlement pool over
the month-by-month "devido", computed at every read and NEVER persisted.

Every expected figure is computed BY HAND in the test (never re-derived from the service's own
formula), all Decimal, no floats. Nothing is mocked: real ORM, real service.
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Condominium, Person
from finances.models import (
    Bill,
    BillLifecycleState,
    FundedFrom,
    ThirdPartySettlement,
)
from finances.services.third_party_statement_service import (
    MonthCharge,
    Settlement,
    ThirdPartyStatementService,
    allocate_fifo,
)
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_condominium,
    make_payment,
    make_payment_allocation,
    make_person,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

# "Today" for every DB-backed test: 15/07/2026 -> current month is 2026-07.
TODAY = date(2026, 7, 15)
MAY = date(2026, 5, 1)
JUNE = date(2026, 6, 1)
JULY = date(2026, 7, 1)
AUGUST = date(2026, 8, 1)


@pytest.fixture
def condominium() -> Condominium:
    """The DEFAULT condominium — what ``build`` resolves when no ``condominium_id`` is given.

    A factory-made condominium would NOT be the default (``get_default`` takes the lowest id,
    and the migration-created "Condomínio Principal" already occupies it), so the statement would
    come back empty and every assertion would silently test nothing.
    """
    default = Condominium.get_default()
    assert default is not None
    return default


@pytest.fixture
def person() -> Person:
    return make_person(name="Raul Terceiro")


def purchase(
    condominium: Condominium,
    person: Person | None,
    amount: str,
    competence_month: date,
    *,
    lifecycle_state: str = BillLifecycleState.ACTIVE,
    description: str = "Compra",
    is_offset: bool = False,
) -> Bill:
    """A third-party purchase: a Bill attributed to ``person`` with one line item."""
    bill = make_bill(
        condominium=condominium,
        paid_by_person=person,
        competence_month=competence_month,
        due_date=competence_month.replace(day=10),
        description=description,
        lifecycle_state=lifecycle_state,
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount), is_offset=is_offset)
    return bill


def third_party_payment(
    condominium: Condominium,
    person: Person,
    amount: str,
    payment_date: date,
    *,
    reference: str = "",
) -> Any:
    """A bill paid by the person: Payment(THIRD_PARTY, paid_by=person) allocated to a bill."""
    bill = make_bill(
        condominium=condominium,
        competence_month=payment_date.replace(day=1),
        due_date=payment_date,
        description="Conta do condomínio",
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    payment = make_payment(
        condominium=condominium,
        payment_date=payment_date,
        amount=Decimal(amount),
        funded_from=FundedFrom.THIRD_PARTY,
        paid_by=person,
        reference=reference,
    )
    make_payment_allocation(payment=payment, bill=bill, amount=Decimal(amount))
    return payment


def settle(
    condominium: Condominium, person: Person, amount: str, settlement_date: date
) -> ThirdPartySettlement:
    return ThirdPartySettlement.objects.create(
        condominium=condominium,
        person=person,
        settlement_date=settlement_date,
        amount=Decimal(amount),
    )


def month_row(result: Any, month: date) -> Any:
    return next(row for row in result["months"] if row["month"] == month)


# --- 1. allocate_fifo as a pure function (no I/O) -----------------------------------


class TestAllocateFifoPure:
    def test_empty_input_returns_zero_totals(self) -> None:
        rows, totals = allocate_fifo([], [], current_month=JULY)

        assert rows == []
        assert totals == {
            "total_devido": Decimal(0),
            "total_pago": Decimal(0),
            "total_em_aberto": Decimal(0),
            "total_atrasado": Decimal(0),
            "saldo_credor": Decimal(0),
        }

    def test_earlier_settlement_is_already_in_the_pool_when_the_charge_arrives(self) -> None:
        """A May settlement DOES clear a June charge: the cut is "settlements up to M"."""
        charges = [
            MonthCharge(month=MAY, devido=Decimal(0)),
            MonthCharge(month=JUNE, devido=Decimal("1000.00")),
        ]
        settlements = [Settlement(month=MAY, amount=Decimal("1000.00"))]

        rows, totals = allocate_fifo(charges, settlements, current_month=JULY)

        assert rows[1].month == JUNE
        assert rows[1].aplicado == Decimal("1000.00")
        assert rows[1].status == "paid"
        assert totals["saldo_credor"] == Decimal(0)

    def test_pool_only_receives_settlements_up_to_the_month(self) -> None:
        """Availability is min(settlement month, first month) once the money has been handed over.

        With current_month=AUGUST a JULY settlement is already made, so it clears the JUNE
        charge — the routine "settle the previous month" case (design §6.2, rev. 3).
        """
        charges = [MonthCharge(month=JUNE, devido=Decimal("300.00"))]
        settlements = [Settlement(month=JULY, amount=Decimal("300.00"))]

        rows, totals = allocate_fifo(charges, settlements, current_month=AUGUST)

        june = next(row for row in rows if row.month == JUNE)
        assert june.aplicado == Decimal("300.00")
        assert june.resto == Decimal(0)
        assert june.status == "paid"
        assert totals["total_atrasado"] == Decimal(0)
        assert totals["saldo_credor"] == Decimal(0)

    def test_pool_withholds_a_settlement_dated_in_the_future(self) -> None:
        """The other half of the cut: money not yet handed over cannot clear anything."""
        charges = [MonthCharge(month=JUNE, devido=Decimal("300.00"))]
        settlements = [Settlement(month=AUGUST, amount=Decimal("300.00"))]

        rows, totals = allocate_fifo(charges, settlements, current_month=JULY)

        june = next(row for row in rows if row.month == JUNE)
        assert june.aplicado == Decimal(0)
        assert june.status == "overdue"
        assert totals["saldo_credor"] == Decimal("300.00")

    def test_negative_devido_credit_propagates_forward(self) -> None:
        charges = [
            MonthCharge(month=MAY, devido=Decimal("-200.00")),
            MonthCharge(month=JUNE, devido=Decimal("500.00")),
        ]

        rows, totals = allocate_fifo(charges, [], current_month=JULY)

        may, june = rows
        assert may.status == "credit"
        assert may.aplicado == Decimal(0)
        assert may.resto == Decimal(0)
        # 200 credit absorbed 200 of June's 500 -> 300 left, June is in the past -> overdue.
        assert june.aplicado == Decimal("200.00")
        assert june.resto == Decimal("300.00")
        assert june.status == "overdue"
        # total_devido is the GROSS charge: the credit month contributes 0, not -200.
        assert totals["total_devido"] == Decimal("500.00")
        assert totals["total_pago"] == Decimal("200.00")
        assert totals["total_em_aberto"] == Decimal("300.00")
        assert totals["total_atrasado"] == Decimal("300.00")
        assert totals["saldo_credor"] == Decimal(0)

    def test_overpayment_becomes_next_month_credit(self) -> None:
        charges = [
            MonthCharge(month=JUNE, devido=Decimal("1000.00")),
            MonthCharge(month=JULY, devido=Decimal("800.00")),
        ]
        settlements = [Settlement(month=JUNE, amount=Decimal("1500.00"))]

        rows, totals = allocate_fifo(charges, settlements, current_month=JULY)

        june, july = rows
        assert june.status == "paid"
        assert june.aplicado == Decimal("1000.00")
        assert june.resto == Decimal(0)
        # 500 left over -> July's 800 gets 500 applied, 300 remaining, current month.
        assert july.aplicado == Decimal("500.00")
        assert july.resto == Decimal("300.00")
        assert july.status == "partially_paid"
        assert totals["total_devido"] == Decimal("1800.00")
        assert totals["total_pago"] == Decimal("1500.00")
        assert totals["total_em_aberto"] == Decimal("300.00")
        assert totals["total_atrasado"] == Decimal(0)

    def test_future_month_remainder_counts_in_neither_total(self) -> None:
        charges = [MonthCharge(month=AUGUST, devido=Decimal("400.00"))]

        rows, totals = allocate_fifo(charges, [], current_month=JULY)

        assert rows[0].status == "open"
        assert rows[0].resto == Decimal("400.00")
        assert totals["total_em_aberto"] == Decimal(0)
        assert totals["total_atrasado"] == Decimal(0)
        assert totals["total_devido"] == Decimal("400.00")

    def test_current_month_remainder_counts_open_but_not_overdue(self) -> None:
        charges = [MonthCharge(month=JULY, devido=Decimal("400.00"))]

        rows, totals = allocate_fifo(charges, [], current_month=JULY)

        assert rows[0].status == "open"
        assert totals["total_em_aberto"] == Decimal("400.00")
        assert totals["total_atrasado"] == Decimal(0)

    def test_leftover_pool_becomes_saldo_credor(self) -> None:
        charges = [MonthCharge(month=JUNE, devido=Decimal("100.00"))]
        settlements = [Settlement(month=JUNE, amount=Decimal("250.00"))]

        rows, totals = allocate_fifo(charges, settlements, current_month=JULY)

        assert rows[0].status == "paid"
        assert totals["saldo_credor"] == Decimal("150.00")
        assert totals["total_pago"] == Decimal("100.00")

    def test_cents_precision_three_installments_of_3333_over_10000(self) -> None:
        charges = [
            MonthCharge(month=MAY, devido=Decimal("33.33")),
            MonthCharge(month=JUNE, devido=Decimal("33.33")),
            MonthCharge(month=JULY, devido=Decimal("33.34")),
        ]
        settlements = [Settlement(month=MAY, amount=Decimal("100.00"))]

        rows, totals = allocate_fifo(charges, settlements, current_month=JULY)

        assert [row.aplicado for row in rows] == [
            Decimal("33.33"),
            Decimal("33.33"),
            Decimal("33.34"),
        ]
        assert all(row.resto == Decimal(0) for row in rows)
        assert totals["total_devido"] == Decimal("100.00")
        assert totals["total_pago"] == Decimal("100.00")
        assert totals["saldo_credor"] == Decimal(0)


# --- 2. build(): the five statuses through the ORM ----------------------------------


class TestStatuses:
    def test_paid_status(self, condominium: Condominium, person: Person) -> None:
        purchase(condominium, person, "500.00", JUNE)
        settle(condominium, person, "500.00", date(2026, 6, 20))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        row = month_row(result, JUNE)
        assert row["status"] == "paid"
        assert row["devido"] == "500.00"
        assert row["aplicado"] == "500.00"
        assert row["resto"] == "0.00"

    def test_overdue_status(self, condominium: Condominium, person: Person) -> None:
        purchase(condominium, person, "500.00", JUNE)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        row = month_row(result, JUNE)
        assert row["status"] == "overdue"
        assert row["resto"] == "500.00"
        assert result["totals"]["total_atrasado"] == "500.00"

    def test_partially_paid_status_current_month(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "500.00", JULY)
        settle(condominium, person, "200.00", date(2026, 7, 5))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        row = month_row(result, JULY)
        assert row["status"] == "partially_paid"
        assert row["aplicado"] == "200.00"
        assert row["resto"] == "300.00"

    def test_open_status_future_month(self, condominium: Condominium, person: Person) -> None:
        purchase(condominium, person, "500.00", AUGUST)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        row = month_row(result, AUGUST)
        assert row["status"] == "open"
        assert row["aplicado"] == "0.00"
        assert result["totals"]["total_em_aberto"] == "0.00"

    def test_credit_status(self, condominium: Condominium, person: Person) -> None:
        purchase(condominium, person, "150.00", JUNE, is_offset=True, description="Estorno")

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        row = month_row(result, JUNE)
        assert row["status"] == "credit"
        assert row["devido"] == "-150.00"
        assert result["totals"]["total_devido"] == "0.00"
        assert result["totals"]["saldo_credor"] == "150.00"


# --- 3. build(): devido composition ------------------------------------------------


class TestDevidoComposition:
    def test_payment_and_purchase_in_the_same_month_add_up(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "300.00", JUNE)
        third_party_payment(condominium, person, "200.00", date(2026, 6, 12))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["devido"] == "500.00"

    def test_canceled_bill_is_excluded_suspended_and_deferred_are_included(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", JUNE, lifecycle_state=BillLifecycleState.CANCELED)
        purchase(condominium, person, "70.00", JUNE, lifecycle_state=BillLifecycleState.SUSPENDED)
        purchase(condominium, person, "30.00", JUNE, lifecycle_state=BillLifecycleState.DEFERRED)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["devido"] == "100.00"

    def test_installment_purchase_of_ten_lands_one_per_month(
        self, condominium: Condominium, person: Person
    ) -> None:
        # 10 monthly Bills of 50.00 starting in 2026-01.
        for offset in range(10):
            month = date(2026, 1 + offset, 1)
            purchase(condominium, person, "50.00", month, description=f"Parcela {offset + 1}/10")

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert len(result["months"]) == 10
        assert {row["month"] for row in result["months"]} == {
            date(2026, 1 + offset, 1) for offset in range(10)
        }
        assert all(row["devido"] == "50.00" for row in result["months"])
        assert result["totals"]["total_devido"] == "500.00"

    def test_other_persons_movements_do_not_leak(
        self, condominium: Condominium, person: Person
    ) -> None:
        other = make_person(name="Outra Pessoa")
        purchase(condominium, person, "100.00", JUNE)
        purchase(condominium, other, "999.00", JUNE)
        third_party_payment(condominium, other, "777.00", date(2026, 6, 3))
        settle(condominium, other, "500.00", date(2026, 6, 4))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["devido"] == "100.00"
        assert result["totals"]["saldo_credor"] == "0.00"

    def test_bill_without_paid_by_person_does_not_count(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", JUNE)
        purchase(condominium, None, "888.00", JUNE)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["devido"] == "100.00"

    def test_caixa_payment_does_not_count_as_third_party(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", JUNE)
        bill = make_bill(condominium=condominium, competence_month=JUNE)
        make_bill_line_item(bill=bill, amount=Decimal("400.00"))
        payment = make_payment(
            condominium=condominium,
            payment_date=date(2026, 6, 8),
            amount=Decimal("400.00"),
            funded_from=FundedFrom.CAIXA,
        )
        make_payment_allocation(payment=payment, bill=bill, amount=Decimal("400.00"))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["devido"] == "100.00"

    def test_soft_deleted_payment_and_bill_leave_the_statement(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", JUNE)
        deleted_bill = purchase(condominium, person, "60.00", JUNE)
        deleted_bill.delete()
        deleted_payment = third_party_payment(condominium, person, "40.00", date(2026, 6, 9))
        deleted_payment.delete()

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["devido"] == "100.00"

    def test_other_condominium_movements_are_scoped_out(self, person: Person) -> None:
        first = make_condominium()
        second = make_condominium()
        purchase(first, person, "100.00", JUNE)
        purchase(second, person, "555.00", JUNE)
        settle(second, person, "555.00", date(2026, 6, 15))

        result = ThirdPartyStatementService.build(person.pk, TODAY, condominium_id=first.pk)

        assert month_row(result, JUNE)["devido"] == "100.00"
        assert result["totals"]["total_atrasado"] == "100.00"


# --- 4. build(): settlements ---------------------------------------------------------


class TestSettlements:
    def test_soft_deleted_settlement_leaves_the_pool(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "500.00", JUNE)
        settlement = settle(condominium, person, "500.00", date(2026, 6, 20))
        settlement.delete()

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert month_row(result, JUNE)["status"] == "overdue"
        assert result["totals"]["total_atrasado"] == "500.00"

    def test_settlement_after_the_charge_month_does_not_backfill_it(
        self, condominium: Condominium, person: Person
    ) -> None:
        """An ALREADY-MADE settlement DOES clear an earlier month (design §6.2, rev. 3).

        The owners settle the previous month as a matter of routine — June paid on 10 July is
        normal, not late. Refusing it would report "atrasado R$500" to someone who already paid
        and leave the money dangling in saldo_credor. What stays blocked is the future-dated
        settlement (see test_future_dated_settlement_cannot_green_an_earlier_month).
        """
        purchase(condominium, person, "500.00", JUNE)
        settle(condominium, person, "500.00", date(2026, 7, 10))  # <= TODAY (2026-07-15)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        june = month_row(result, JUNE)
        assert june["aplicado"] == "500.00"
        assert june["resto"] == "0.00"
        assert june["status"] == "paid"
        assert result["totals"]["total_atrasado"] == "0.00"
        assert result["totals"]["saldo_credor"] == "0.00"

    def test_future_dated_settlement_cannot_green_an_earlier_month(
        self, condominium: Condominium, person: Person
    ) -> None:
        """The hazard the temporal cut still blocks: money that has NOT been handed over yet."""
        purchase(condominium, person, "500.00", JUNE)
        settle(condominium, person, "500.00", date(2026, 9, 10))  # > TODAY (2026-07-15)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        june = month_row(result, JUNE)
        assert june["status"] == "overdue"
        assert june["aplicado"] == "0.00"
        assert result["totals"]["total_atrasado"] == "500.00"
        assert result["totals"]["saldo_credor"] == "500.00"

    def test_settlement_only_month_appears_in_the_window(
        self, condominium: Condominium, person: Person
    ) -> None:
        settle(condominium, person, "300.00", date(2026, 5, 4))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert [row["month"] for row in result["months"]] == [MAY, JUNE, JULY]
        assert month_row(result, MAY)["devido"] == "0.00"
        assert result["totals"]["saldo_credor"] == "300.00"

    def test_realistic_sequence_ends_at_zero(
        self, condominium: Condominium, person: Person
    ) -> None:
        # Cobrado 600 (maio 400 + junho 200); acertado 600 (150 em maio + 450 em junho).
        # Hoje é 15/07, então os DOIS acertos já foram feitos e ficam disponíveis desde o
        # início da janela (design §6.2, rev. 3) — FIFO quita maio (400) e depois junho (200),
        # e a pessoa fica zerada. Antes da rev. 3 este mesmo cenário deixava maio "atrasado
        # 250" com 250 pendurados em saldo_credor, apesar de tudo ter sido pago.
        purchase(condominium, person, "400.00", MAY)
        settle(condominium, person, "150.00", date(2026, 5, 20))
        purchase(condominium, person, "200.00", JUNE)
        settle(condominium, person, "450.00", date(2026, 6, 25))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        may = month_row(result, MAY)
        assert may["devido"] == "400.00"
        assert may["aplicado"] == "400.00"
        assert may["resto"] == "0.00"
        assert may["status"] == "paid"
        june = month_row(result, JUNE)
        assert june["devido"] == "200.00"
        assert june["aplicado"] == "200.00"
        assert june["resto"] == "0.00"
        assert june["status"] == "paid"
        totals = result["totals"]
        assert totals["total_devido"] == "600.00"
        assert totals["total_pago"] == "600.00"
        assert totals["total_em_aberto"] == "0.00"
        assert totals["total_atrasado"] == "0.00"
        assert totals["saldo_credor"] == "0.00"  # cobrado == acertado, ninguém fica devendo


# --- 5. build(): window, shape and items --------------------------------------------


class TestWindowAndShape:
    def test_person_without_movement_returns_empty_statement(self, person: Person) -> None:
        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert result["person_id"] == person.pk
        assert result["person_name"] == "Raul Terceiro"
        assert result["months"] == []
        assert result["totals"] == {
            "total_devido": "0.00",
            "total_pago": "0.00",
            "total_em_aberto": "0.00",
            "total_atrasado": "0.00",
            "saldo_credor": "0.00",
        }

    def test_gap_months_inside_the_window_appear_with_zero(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", date(2026, 3, 1))
        purchase(condominium, person, "100.00", JUNE)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert [row["month"] for row in result["months"]] == [
            date(2026, 3, 1),
            date(2026, 4, 1),
            MAY,
            JUNE,
            JULY,
        ]
        assert month_row(result, date(2026, 4, 1))["devido"] == "0.00"
        # NOT "paid": design §6.3 requires devido > 0 for paid. A gap month rendered "Quitado"
        # between two overdue months would read as "that month was settled" — it had no movement.
        assert month_row(result, date(2026, 4, 1))["status"] == "empty"
        assert month_row(result, MAY)["status"] == "empty"
        # A month that really WAS charged and settled still reads "paid".
        assert month_row(result, date(2026, 3, 1))["status"] == "overdue"

    def test_window_extends_to_the_last_movement_beyond_current_month(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", JUNE)
        purchase(condominium, person, "100.00", date(2026, 9, 1))

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert [row["month"] for row in result["months"]] == [
            JUNE,
            JULY,
            AUGUST,
            date(2026, 9, 1),
        ]

    def test_items_carry_both_kinds_with_id_description_amount_and_date(
        self, condominium: Condominium, person: Person
    ) -> None:
        bill = purchase(condominium, person, "300.00", JUNE, description="Material de obra")
        payment = third_party_payment(
            condominium, person, "200.00", date(2026, 6, 12), reference="Luz junho"
        )

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        items = month_row(result, JUNE)["items"]
        assert len(items) == 2
        by_kind = {item["kind"]: item for item in items}
        assert by_kind["purchase"] == {
            "kind": "purchase",
            "id": bill.pk,
            "description": "Material de obra",
            "amount": "300.00",
            "date": JUNE,
        }
        assert by_kind["payment"]["id"] == payment.pk
        assert by_kind["payment"]["amount"] == "200.00"
        assert by_kind["payment"]["date"] == date(2026, 6, 12)
        assert by_kind["payment"]["description"] == "Luz junho"

    def test_month_row_shape(self, condominium: Condominium, person: Person) -> None:
        purchase(condominium, person, "100.00", JUNE)

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert set(result.keys()) == {"person_id", "person_name", "months", "totals"}
        assert set(result["months"][0].keys()) == {
            "month",
            "devido",
            "aplicado",
            "resto",
            "status",
            "items",
        }

    def test_soft_deleted_person_still_resolves_its_name(
        self, condominium: Condominium, person: Person
    ) -> None:
        purchase(condominium, person, "100.00", JUNE)
        person.delete()

        result = ThirdPartyStatementService.build(person.pk, TODAY)

        assert result["person_name"] == "Raul Terceiro"
        assert month_row(result, JUNE)["devido"] == "100.00"


# --- 6. Performance ------------------------------------------------------------------


class TestQueryCount:
    def test_query_count_is_constant_for_2_and_for_12_months(
        self, condominium: Condominium, person: Person
    ) -> None:
        for offset in range(2):
            purchase(condominium, person, "10.00", date(2026, 6 + offset, 1))
        with CaptureQueriesContext(connection) as short:
            ThirdPartyStatementService.build(person.pk, TODAY)

        wide = make_person(name="Doze Meses")
        # 2025-08 .. 2026-07 — twelve consecutive months, each with a purchase and a settlement.
        wide_months = [date(2025, 8 + offset, 1) for offset in range(5)] + [
            date(2026, 1 + offset, 1) for offset in range(7)
        ]
        assert len(wide_months) == 12
        for month in wide_months:
            purchase(condominium, wide, "10.00", month)
            settle(condominium, wide, "5.00", month.replace(day=15))
        with CaptureQueriesContext(connection) as long:
            statement = ThirdPartyStatementService.build(wide.pk, TODAY)

        assert len(statement["months"]) == 12
        assert len(long.captured_queries) == len(short.captured_queries)
