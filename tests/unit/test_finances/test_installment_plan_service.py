"""Session 41 — InstallmentPlanService.convert_deferred tests (atomic, no dup/loss, terminal).

Session 70 extends this module with TestConsolidateOpenBills (consolidate_open_bills: N open
bills of an account -> 1 InstallmentPlan, atomic origin cancellation).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
    PaymentAllocation,
)
from finances.services.bill_lifecycle_service import BillLifecycleService
from finances.services.bill_payment_service import BillPaymentService
from finances.services.installment_plan_service import InstallmentPlanService, _split_amount
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condo_month_close,
    make_installment,
    make_installment_plan,
)

pytestmark = pytest.mark.django_db


# --- B5: materialize_schedule (used by the create-via-API path, InstallmentPlanViewSet) ---


def test_materialize_schedule_creates_installments_summing_to_total() -> None:
    plan = make_installment_plan(
        total_amount=Decimal("1200.00"),
        installment_count=12,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    InstallmentPlanService.materialize_schedule(plan)
    installments = list(plan.installments.order_by("number"))
    assert len(installments) == 12
    assert sum(i.amount for i in installments) == Decimal("1200.00")
    assert installments[0].due_date == date(2026, 7, 10)
    assert installments[1].due_date == date(2026, 8, 10)


def test_materialize_schedule_is_idempotent_when_already_materialized() -> None:
    plan = make_installment_plan(installment_count=1)
    make_installment(plan=plan, number=1)
    before = list(plan.installments.values_list("id", flat=True))
    InstallmentPlanService.materialize_schedule(plan)
    after = list(plan.installments.values_list("id", flat=True))
    assert before == after  # no duplicate materialization


def _iptu_account(condominium=None) -> BillingAccount:
    return make_billing_account(
        condominium=condominium,
        account_type=BillingAccountType.IPTU,
        external_identifier="IPTU-1",
    )


def _deferred_bill(amount: str) -> Bill:
    account = _iptu_account()
    bill = make_bill(
        condominium=account.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.DEFERRED,
        billing_account=account,
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time("2026-06-15")
def test_convert_deferred_creates_plan_and_installments() -> None:
    bill = _deferred_bill("1200.00")
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=12,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    assert plan.embedded is False
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE
    assert plan.total_amount == Decimal("1200.00")
    installments = list(plan.installments.order_by("number"))
    assert len(installments) == 12
    assert sum(i.amount for i in installments) == Decimal("1200.00")
    assert installments[0].due_date == date(2026, 7, 10)
    assert installments[1].due_date == date(2026, 8, 10)
    assert installments[11].due_date == date(2027, 6, 10)


@freeze_time("2026-06-15")
def test_convert_deferred_remainder_on_last_installment() -> None:
    bill = _deferred_bill("100.00")
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=3,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    amounts = [i.amount for i in plan.installments.order_by("number")]
    assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(amounts) == Decimal("100.00")


@pytest.mark.parametrize(
    ("total", "count"),
    [("0.05", 9), ("0.54", 12), ("0.01", 3), ("100.00", 3), ("1200.00", 12), ("7.00", 24)],
)
def test_split_amount_parts_are_non_negative_and_sum_exact(total: str, count: int) -> None:
    parts = _split_amount(Decimal(total), count)
    assert len(parts) == count
    assert all(part >= Decimal("0.00") for part in parts), (total, count, parts)
    assert sum(parts) == Decimal(total)


@freeze_time("2026-06-15")
def test_convert_deferred_rejects_negative_total() -> None:
    account = _iptu_account()
    bill = make_bill(
        condominium=account.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.DEFERRED,
        billing_account=account,
    )
    make_bill_line_item(bill=bill, amount=Decimal("10.00"), is_offset=False)
    make_bill_line_item(bill=bill, amount=Decimal("50.00"), is_offset=True)  # net total -40
    with pytest.raises(ValidationError):
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=3,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert InstallmentPlan.objects.count() == 0  # atomic: nothing created


@freeze_time("2026-08-15")
def test_deferred_bill_becomes_terminal_outside_all_sums() -> None:
    account = _iptu_account()
    bill = make_bill(
        condominium=account.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.DEFERRED,
        due_date=date(2026, 1, 10),
        billing_account=account,
    )
    make_bill_line_item(bill=bill, amount=Decimal("1200.00"))
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=12,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.CANCELED
    # Canceled -> not overdue and not counted; the value migrated whole, never duplicated.
    annotated = Bill.objects.with_amounts(date(2026, 8, 15)).get(pk=bill.pk)
    assert annotated.is_overdue is False
    assert plan.total_amount == Decimal("1200.00")


@freeze_time("2026-06-15")
def test_convert_deferred_count_zero_is_rejected_atomically() -> None:
    bill = _deferred_bill("100.00")
    with pytest.raises(ValidationError):
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=0,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert InstallmentPlan.objects.count() == 0
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.DEFERRED


@freeze_time("2026-06-15")
def test_convert_deferred_requires_deferred_state() -> None:
    bill = make_bill(behavior="one_time", lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    with pytest.raises(ValidationError):
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=3,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert InstallmentPlan.objects.count() == 0


@freeze_time("2026-06-15")
def test_convert_deferred_inherits_iptu_billing_account() -> None:
    """convert_deferred de um Bill(deferred) com billing_account IPTU → plan.billing_account == conta."""
    account = _iptu_account()
    bill = make_bill(
        condominium=account.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.DEFERRED,
        billing_account=account,
    )
    make_bill_line_item(bill=bill, amount=Decimal("1500.00"))
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=3,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    assert plan.embedded is False
    assert plan.billing_account_id == account.id
    assert plan.billing_account.account_type == BillingAccountType.IPTU


@freeze_time("2026-06-15")
def test_convert_deferred_rejects_non_iptu_billing_account() -> None:
    """convert_deferred de um Bill(deferred) sem conta / conta não-IPTU → ValidationError PT."""
    water = make_billing_account(account_type=BillingAccountType.WATER, external_identifier="UC-9")
    bill_water = make_bill(
        condominium=water.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.DEFERRED,
        billing_account=water,
    )
    make_bill_line_item(bill=bill_water, amount=Decimal("100.00"))
    with pytest.raises(ValidationError) as exc:
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill_water,
            installment_count=3,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert "billing_account" in exc.value.message_dict
    assert InstallmentPlan.objects.count() == 0

    bill_none = make_bill(behavior="one_time", lifecycle_state=BillLifecycleState.DEFERRED)
    make_bill_line_item(bill=bill_none, amount=Decimal("100.00"))
    with pytest.raises(ValidationError) as exc:
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill_none,
            installment_count=3,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert "billing_account" in exc.value.message_dict
    assert InstallmentPlan.objects.count() == 0


# --- B9: convert_deferred must parcel amount_remaining (total - already paid), not amount_total ---


@freeze_time("2026-06-15")
def test_convert_deferred_parcels_only_remaining_after_partial_payment() -> None:
    account = _iptu_account()
    bill = make_bill(
        condominium=account.condominium,
        behavior="one_time",
        lifecycle_state=BillLifecycleState.ACTIVE,  # pay requires ACTIVE
        billing_account=account,
    )
    make_bill_line_item(bill=bill, amount=Decimal("1200.00"))
    BillPaymentService.pay(bill, date(2026, 6, 1), amount=Decimal("200.00"))  # partial payment
    BillLifecycleService.set_state(
        bill, BillLifecycleState.DEFERRED
    )  # allowed: defer, not paid-blocked

    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=10,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    # remaining = 1200 - 200 = 1000, NOT the full 1200 (would double-charge the paid part)
    assert plan.total_amount == Decimal("1000.00")
    installments = list(plan.installments.order_by("number"))
    assert sum(i.amount for i in installments) == Decimal("1000.00")


# --- Session 70: consolidate_open_bills (N open bills of an account -> 1 InstallmentPlan) ---


def _open_bill(account: BillingAccount, amount: str, **kwargs) -> Bill:
    bill = make_bill(condominium=account.condominium, billing_account=account, **kwargs)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


class TestConsolidateOpenBills:
    @freeze_time("2026-07-15")
    def test_consolidates_two_open_bills_into_one_plan(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER, name="Água 850")
        bill1 = _open_bill(account, "300.00", competence_month=date(2026, 5, 1))
        bill2 = _open_bill(account, "200.00", competence_month=date(2026, 6, 1))

        plan = InstallmentPlanService.consolidate_open_bills(
            account=account,
            bill_ids=[bill1.id, bill2.id],
            embedded=False,
            installment_count=5,
            start_due_date=date(2026, 8, 10),
            default_due_day=10,
        )

        assert plan.total_amount == Decimal("500.00")
        assert plan.billing_account_id == account.id
        installments = list(plan.installments.order_by("number"))
        assert len(installments) == 5
        assert sum(i.amount for i in installments) == Decimal("500.00")

        bill1.refresh_from_db()
        bill2.refresh_from_db()
        assert bill1.lifecycle_state == BillLifecycleState.CANCELED
        assert bill2.lifecycle_state == BillLifecycleState.CANCELED

    @freeze_time("2026-07-15")
    def test_partial_payment_counts_remaining_not_total(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        bill = _open_bill(account, "300.00", lifecycle_state=BillLifecycleState.ACTIVE)
        BillPaymentService.pay(bill, date(2026, 6, 1), amount=Decimal("100.00"))
        allocation = PaymentAllocation.objects.get(bill=bill)

        plan = InstallmentPlanService.consolidate_open_bills(
            account=account,
            bill_ids=[bill.id],
            embedded=False,
            installment_count=2,
            start_due_date=date(2026, 8, 10),
            default_due_day=10,
        )

        assert plan.total_amount == Decimal("200.00")
        allocation.refresh_from_db()
        assert allocation.is_deleted is False  # the paid part stays live history (B9 precedent)

    @freeze_time("2026-07-15")
    def test_bill_with_installment_fk_rejected(self) -> None:
        host_account = make_billing_account(
            account_type=BillingAccountType.WATER, external_identifier="UC-1"
        )
        embedded_plan = make_installment_plan(
            condominium=host_account.condominium,
            embedded=True,
            billing_account=host_account,
            installment_count=1,
            total_amount=Decimal("50.00"),
        )
        installment = make_installment(plan=embedded_plan, number=1, amount=Decimal("50.00"))
        standalone_parcela_bill = make_bill(
            condominium=host_account.condominium, installment=installment
        )
        make_bill_line_item(bill=standalone_parcela_bill, amount=Decimal("50.00"))

        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=host_account,
                bill_ids=[standalone_parcela_bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.filter(pk=embedded_plan.pk).exists()
        assert InstallmentPlan.objects.count() == 1  # nothing new persisted

    @freeze_time("2026-07-15")
    def test_bill_with_embedded_line_of_active_plan_rejected(self) -> None:
        account = make_billing_account(
            account_type=BillingAccountType.WATER, external_identifier="UC-2"
        )
        embedded_plan = make_installment_plan(
            condominium=account.condominium,
            embedded=True,
            billing_account=account,
            installment_count=1,
            total_amount=Decimal("40.00"),
            lifecycle_state=InstallmentPlanState.ACTIVE,
        )
        installment = make_installment(plan=embedded_plan, number=1, amount=Decimal("40.00"))
        bill = _open_bill(account, "100.00")
        BillLineItem.objects.create(bill=bill, installment=installment, amount=Decimal("40.00"))

        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 1  # nothing new persisted
        bill.refresh_from_db()
        assert bill.lifecycle_state != BillLifecycleState.CANCELED

    @freeze_time("2026-07-15")
    def test_bill_of_other_account_rejected(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        other_account = make_billing_account(
            condominium=account.condominium,
            account_type=BillingAccountType.ELECTRICITY,
            external_identifier="UC-OTHER",
        )
        foreign_bill = _open_bill(other_account, "150.00")

        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[foreign_bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0
        foreign_bill.refresh_from_db()
        assert foreign_bill.lifecycle_state == BillLifecycleState.ACTIVE

    @freeze_time("2026-07-15")
    def test_canceled_and_deleted_bills_rejected(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        canceled_bill = _open_bill(
            account,
            "100.00",
            lifecycle_state=BillLifecycleState.CANCELED,
            competence_month=date(2026, 5, 1),
        )
        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[canceled_bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0

        deleted_bill = _open_bill(account, "100.00", competence_month=date(2026, 6, 1))
        deleted_bill.is_deleted = True
        deleted_bill.save(update_fields=["is_deleted"])
        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[deleted_bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0

    @freeze_time("2026-07-15")
    def test_suspended_and_deferred_bills_accepted(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        suspended_bill = _open_bill(
            account,
            "80.00",
            lifecycle_state=BillLifecycleState.SUSPENDED,
            competence_month=date(2026, 5, 1),
        )
        deferred_bill = _open_bill(
            account,
            "120.00",
            lifecycle_state=BillLifecycleState.DEFERRED,
            competence_month=date(2026, 6, 1),
        )

        plan = InstallmentPlanService.consolidate_open_bills(
            account=account,
            bill_ids=[suspended_bill.id, deferred_bill.id],
            embedded=False,
            installment_count=2,
            start_due_date=date(2026, 8, 10),
            default_due_day=10,
        )

        assert plan.total_amount == Decimal("200.00")
        suspended_bill.refresh_from_db()
        deferred_bill.refresh_from_db()
        assert suspended_bill.lifecycle_state == BillLifecycleState.CANCELED
        assert deferred_bill.lifecycle_state == BillLifecycleState.CANCELED

    @freeze_time("2026-07-15")
    def test_fully_paid_bill_rejected(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        bill = _open_bill(account, "300.00")
        BillPaymentService.pay(bill, date(2026, 6, 1))  # full payment -> amount_remaining == 0

        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0

    @freeze_time("2026-07-15")
    def test_closed_competence_rejected_before_any_write(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        open_bill = _open_bill(account, "100.00", competence_month=date(2026, 7, 1))
        closed_bill = _open_bill(account, "200.00", competence_month=date(2026, 6, 1))
        make_condo_month_close(
            condominium=account.condominium, reference_month=date(2026, 6, 1), status="closed"
        )

        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[open_bill.id, closed_bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0
        open_bill.refresh_from_db()
        assert open_bill.lifecycle_state == BillLifecycleState.ACTIVE  # nothing canceled either

    @freeze_time("2026-07-15")
    def test_embedded_requires_consumption_account(self) -> None:
        iptu_account = make_billing_account(
            account_type=BillingAccountType.IPTU, external_identifier="IPTU-70"
        )
        iptu_bill = _open_bill(iptu_account, "100.00")
        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=iptu_account,
                bill_ids=[iptu_bill.id],
                embedded=True,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0

        water_account = make_billing_account(
            account_type=BillingAccountType.WATER, external_identifier="UC-EMB"
        )
        water_bill = _open_bill(water_account, "100.00")
        plan = InstallmentPlanService.consolidate_open_bills(
            account=water_account,
            bill_ids=[water_bill.id],
            embedded=True,
            installment_count=1,
            start_due_date=date(2026, 8, 10),
            default_due_day=10,
        )
        assert plan.embedded is True

    @freeze_time("2026-07-15")
    def test_duplicate_or_empty_bill_ids_rejected(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        bill = _open_bill(account, "100.00")

        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[bill.id, bill.id],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[],
                embedded=False,
                installment_count=1,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0

    @freeze_time("2026-07-15")
    def test_installment_count_non_positive_rejected(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        bill = _open_bill(account, "100.00")
        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[bill.id],
                embedded=False,
                installment_count=0,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )
        assert InstallmentPlan.objects.count() == 0

    @freeze_time("2026-07-15")
    def test_origin_notes_receive_plan_reference(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        bill = _open_bill(account, "100.00", notes="Cliente ligou reclamando.")

        plan = InstallmentPlanService.consolidate_open_bills(
            account=account,
            bill_ids=[bill.id],
            embedded=False,
            installment_count=1,
            start_due_date=date(2026, 8, 10),
            default_due_day=10,
        )

        bill.refresh_from_db()
        assert bill.notes.startswith("Cliente ligou reclamando.")
        assert bill.notes.endswith(f"Consolidada no plano #{plan.pk}")

    @freeze_time("2026-07-15")
    def test_installments_sum_equals_total_with_cents(self) -> None:
        account = make_billing_account(account_type=BillingAccountType.WATER)
        bills = [
            _open_bill(account, "33.34", competence_month=date(2026, 4, 1)),
            _open_bill(account, "33.34", competence_month=date(2026, 5, 1)),
            _open_bill(account, "33.33", competence_month=date(2026, 6, 1)),
        ]

        plan = InstallmentPlanService.consolidate_open_bills(
            account=account,
            bill_ids=[b.id for b in bills],
            embedded=False,
            installment_count=3,
            start_due_date=date(2026, 8, 10),
            default_due_day=10,
        )

        assert plan.total_amount == Decimal("100.01")
        amounts = [i.amount for i in plan.installments.order_by("number")]
        assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.35")]
        assert sum(amounts) == Decimal("100.01")

    @freeze_time("2026-06-15")
    def test_convert_deferred_untouched(self) -> None:
        """Regression: convert_deferred keeps working unmodified alongside consolidate_open_bills."""
        bill = _deferred_bill("1200.00")
        plan = InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=12,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
        assert plan.total_amount == Decimal("1200.00")
        bill.refresh_from_db()
        assert bill.lifecycle_state == BillLifecycleState.CANCELED

    @freeze_time("2026-07-15")
    def test_atomic_failure_leaves_nothing_persisted(self) -> None:
        """A validation failure discovered mid-loop (2nd bill fails) must roll back everything,
        including the 1st bill's cancellation — the whole call is one transaction."""
        account = make_billing_account(account_type=BillingAccountType.WATER)
        good_bill = _open_bill(account, "100.00", competence_month=date(2026, 7, 1))
        closed_bill = _open_bill(account, "200.00", competence_month=date(2026, 6, 1))
        make_condo_month_close(
            condominium=account.condominium, reference_month=date(2026, 6, 1), status="closed"
        )

        installments_before = Installment.objects.count()
        with pytest.raises(ValidationError):
            InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=[good_bill.id, closed_bill.id],
                embedded=False,
                installment_count=2,
                start_due_date=date(2026, 8, 10),
                default_due_day=10,
            )

        assert InstallmentPlan.objects.count() == 0
        assert Installment.objects.count() == installments_before
        good_bill.refresh_from_db()
        closed_bill.refresh_from_db()
        assert good_bill.lifecycle_state == BillLifecycleState.ACTIVE
        assert closed_bill.lifecycle_state == BillLifecycleState.ACTIVE
