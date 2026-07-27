"""Session 66 — CondoMonthBoardService.build (Atrasadas/adiada-suspensa/groups/totals/missing_count)."""

from datetime import date
from decimal import Decimal

import pytest

from finances.services.bill_generation_service import BillGenerationService
from finances.services.condo_month_board_service import CondoMonthBoardService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_bill_skip,
    make_billing_account,
    make_building,
    make_condominium,
    make_payment,
    make_payment_allocation,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

TODAY = date(2026, 7, 15)


class TestMonthBoardOverdueSection:
    def test_overdue_includes_previous_competence(self) -> None:
        bill = make_bill(competence_month=date(2026, 6, 1), due_date=date(2026, 6, 10))
        make_bill_line_item(bill=bill, amount=Decimal("500.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        ids = {b["id"] for b in board["overdue"]}
        assert bill.id in ids

    def test_overdue_excludes_due_today(self) -> None:
        bill = make_bill(competence_month=date(2026, 7, 1), due_date=TODAY)
        make_bill_line_item(bill=bill, amount=Decimal("500.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        ids = {b["id"] for b in board["overdue"]}
        assert bill.id not in ids

    def test_overdue_only_active(self) -> None:
        bill = make_bill(
            competence_month=date(2026, 6, 1),
            due_date=date(2026, 6, 10),
            lifecycle_state="suspended",
        )
        make_bill_line_item(bill=bill, amount=Decimal("500.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        overdue_ids = {b["id"] for b in board["overdue"]}
        deferred_ids = {b["id"] for b in board["deferred_suspended"]}
        assert bill.id not in overdue_ids
        assert bill.id in deferred_ids

    def test_overdue_excludes_paid(self) -> None:
        bill = make_bill(competence_month=date(2026, 6, 1), due_date=date(2026, 6, 10))
        make_bill_line_item(bill=bill, amount=Decimal("500.00"))
        payment = make_payment(payment_date=date(2026, 6, 5), amount=Decimal("500.00"))
        make_payment_allocation(payment=payment, bill=bill, amount=Decimal("500.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        ids = {b["id"] for b in board["overdue"]}
        assert bill.id not in ids

    def test_overdue_sorted_by_due_date(self) -> None:
        later = make_bill(competence_month=date(2026, 6, 1), due_date=date(2026, 6, 20))
        make_bill_line_item(bill=later, amount=Decimal("100.00"))
        earlier = make_bill(competence_month=date(2026, 6, 1), due_date=date(2026, 6, 5))
        make_bill_line_item(bill=earlier, amount=Decimal("100.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        ids_in_order = [b["id"] for b in board["overdue"]]
        assert ids_in_order.index(earlier.id) < ids_in_order.index(later.id)


class TestMonthBoardDeferredSuspended:
    def test_deferred_suspended_any_competence_with_rest(self) -> None:
        suspended = make_bill(competence_month=date(2026, 5, 1), lifecycle_state="suspended")
        make_bill_line_item(bill=suspended, amount=Decimal("200.00"))
        deferred = make_bill(competence_month=date(2026, 7, 1), lifecycle_state="deferred")
        make_bill_line_item(bill=deferred, amount=Decimal("300.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        ids = {b["id"] for b in board["deferred_suspended"]}
        assert suspended.id in ids
        assert deferred.id in ids

    def test_deferred_suspended_excludes_settled(self) -> None:
        bill = make_bill(competence_month=date(2026, 6, 1), lifecycle_state="suspended")
        make_bill_line_item(bill=bill, amount=Decimal("200.00"))
        payment = make_payment(payment_date=date(2026, 6, 5), amount=Decimal("200.00"))
        make_payment_allocation(payment=payment, bill=bill, amount=Decimal("200.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        ids = {b["id"] for b in board["deferred_suspended"]}
        assert bill.id not in ids

    def test_deferred_suspended_out_of_totals(self) -> None:
        bill = make_bill(competence_month=date(2026, 7, 1), lifecycle_state="suspended")
        make_bill_line_item(bill=bill, amount=Decimal("999.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["totals"]["due"] == "0.00"
        assert board["totals"]["paid"] == "0.00"
        assert board["totals"]["remaining"] == "0.00"
        assert board["totals"]["overdue"] == "0.00"


class TestMonthBoardGroupsAndTotals:
    def test_canceled_invisible_everywhere(self) -> None:
        canceled = make_bill(
            competence_month=date(2026, 6, 1),
            due_date=date(2026, 6, 10),
            lifecycle_state="canceled",
        )
        make_bill_line_item(bill=canceled, amount=Decimal("400.00"))
        canceled_this_month = make_bill(
            competence_month=date(2026, 7, 1), lifecycle_state="canceled"
        )
        make_bill_line_item(bill=canceled_this_month, amount=Decimal("400.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        all_ids = {b["id"] for b in board["overdue"]}
        all_ids |= {b["id"] for b in board["deferred_suspended"]}
        for group in board["groups"]:
            all_ids |= {b["id"] for b in group["bills"]}
        assert canceled.id not in all_ids
        assert canceled_this_month.id not in all_ids

    def test_groups_only_selected_month_active_including_paid(self) -> None:
        building = make_building()
        this_month = make_bill(building=building, competence_month=date(2026, 7, 1))
        make_bill_line_item(bill=this_month, amount=Decimal("100.00"))
        payment = make_payment(payment_date=date(2026, 7, 5), amount=Decimal("100.00"))
        make_payment_allocation(payment=payment, bill=this_month, amount=Decimal("100.00"))
        other_month = make_bill(building=building, competence_month=date(2026, 6, 1))
        make_bill_line_item(bill=other_month, amount=Decimal("100.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        group_ids: set[object] = set()
        for group in board["groups"]:
            group_ids |= {b["id"] for b in group["bills"]}
        assert this_month.id in group_ids
        assert other_month.id not in group_ids

    def test_group_without_building_is_condominio_last(self) -> None:
        condominium = make_condominium()
        building = make_building(condominium=condominium, street_number=200)
        with_building = make_bill(
            condominium=condominium, building=building, competence_month=date(2026, 7, 1)
        )
        make_bill_line_item(bill=with_building, amount=Decimal("10.00"))
        without_building = make_bill(
            condominium=condominium, building=None, competence_month=date(2026, 7, 1)
        )
        make_bill_line_item(bill=without_building, amount=Decimal("10.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        labels = [g["building_label"] for g in board["groups"]]
        assert labels[-1] == "Condomínio"
        condominio_group = next(g for g in board["groups"] if g["building_label"] == "Condomínio")
        assert condominio_group["building_id"] is None
        assert any(b["id"] == without_building.id for b in condominio_group["bills"])

    def test_groups_ordered_by_street_number(self) -> None:
        condominium = make_condominium()
        building_high = make_building(condominium=condominium, street_number=300)
        building_low = make_building(condominium=condominium, street_number=50)
        bill_high = make_bill(
            condominium=condominium, building=building_high, competence_month=date(2026, 7, 1)
        )
        make_bill_line_item(bill=bill_high, amount=Decimal("10.00"))
        bill_low = make_bill(
            condominium=condominium, building=building_low, competence_month=date(2026, 7, 1)
        )
        make_bill_line_item(bill=bill_low, amount=Decimal("10.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        labels = [g["building_label"] for g in board["groups"]]
        assert labels.index("50") < labels.index("300")

    def test_totals_due_paid_remaining_of_month(self) -> None:
        bill = make_bill(competence_month=date(2026, 7, 1))
        make_bill_line_item(bill=bill, amount=Decimal("1000.00"))
        payment = make_payment(payment_date=date(2026, 7, 5), amount=Decimal("400.00"))
        make_payment_allocation(payment=payment, bill=bill, amount=Decimal("400.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["totals"]["due"] == "1000.00"
        assert board["totals"]["paid"] == "400.00"
        assert board["totals"]["remaining"] == "600.00"

    def test_totals_overdue_sums_overdue_section(self) -> None:
        overdue1 = make_bill(competence_month=date(2026, 5, 1), due_date=date(2026, 5, 10))
        make_bill_line_item(bill=overdue1, amount=Decimal("300.00"))
        overdue2 = make_bill(competence_month=date(2026, 6, 1), due_date=date(2026, 6, 10))
        make_bill_line_item(bill=overdue2, amount=Decimal("200.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["totals"]["overdue"] == "500.00"

    def test_bills_serialized_with_amounts_and_estimated_flag(self) -> None:
        bill = make_bill(competence_month=date(2026, 7, 1))
        make_bill_line_item(bill=bill, amount=Decimal("50.00"))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        serialized = next(b for g in board["groups"] for b in g["bills"] if b["id"] == bill.id)
        assert serialized["amount_total"] == "50.00"
        assert serialized["amount_paid"] == "0.00"
        assert serialized["amount_remaining"] == "50.00"
        assert serialized["payment_status"] == "open"
        assert "amount_is_estimated" in serialized


class TestMonthBoardGeneration:
    def test_missing_count_eligible_account_without_bill(self) -> None:
        make_billing_account(name="Água", default_due_day=10)

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["generation"]["missing_count"] == 1

    def test_missing_count_zero_after_generation(self) -> None:
        make_billing_account(name="Água", default_due_day=10)

        BillGenerationService.ensure_month_bills(2026, 7)
        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["generation"]["missing_count"] == 0

    def test_missing_count_respects_bill_skip(self) -> None:
        account = make_billing_account(name="Água", default_due_day=10)
        make_bill_skip(billing_account=account, reference_month=date(2026, 7, 1))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["generation"]["missing_count"] == 0

    def test_missing_count_respects_tracking_start_and_end_date(self) -> None:
        make_billing_account(
            name="Futura", default_due_day=10, tracking_start_month=date(2026, 8, 1)
        )
        make_billing_account(name="Encerrada", default_due_day=10, end_date=date(2026, 6, 30))

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["generation"]["missing_count"] == 0

    def test_missing_count_ignores_iptu_registry_account(self) -> None:
        make_billing_account(name="IPTU", default_due_day=10, account_type="iptu")

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["generation"]["missing_count"] == 0

    def test_missing_count_bill_any_lifecycle_occupies_slot(self) -> None:
        account = make_billing_account(name="Água", default_due_day=10)
        BillGenerationService.ensure_month_bills(2026, 7)
        bill = account.bills.get(competence_month=date(2026, 7, 1))
        bill.lifecycle_state = "suspended"
        bill.save(update_fields=["lifecycle_state"])

        board = CondoMonthBoardService.build(2026, 7, TODAY)

        assert board["generation"]["missing_count"] == 0
