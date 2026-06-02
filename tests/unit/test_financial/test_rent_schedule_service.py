"""Tests for RentScheduleService.

Single source of "rent due this month" logic: clamping, effective value,
collectible leases (date-aware), month schedule/stats, and payment toggle.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from freezegun import freeze_time
from model_bakery import baker

from core.models import RentPayment
from core.services.fee_calculator import FeeCalculatorService
from core.services.rent_schedule_service import RentScheduleService
from tests.factories import (
    make_apartment,
    make_building,
    make_lease,
    make_person,
    make_rent_payment,
    make_tenant,
)

User = get_user_model()


@pytest.fixture
def admin_user():
    return baker.make(User, username="admin", is_staff=True)


@pytest.fixture
def building():
    return make_building(street_number=836, name="Edifício 836", address="Rua Teste, 836")


@pytest.fixture
def apartment(building):
    return make_apartment(
        building=building,
        number=101,
        rental_value=Decimal("1200.00"),
        max_tenants=2,
        is_rented=True,
    )


@pytest.fixture
def tenant():
    return make_tenant(cpf_cnpj="98765432100", name="João Silva", due_day=7)


@pytest.fixture
def lease(apartment, tenant):
    """Active lease whose window (2025-06-01 .. 2026-06-01) covers March 2026."""
    return make_lease(
        apartment=apartment,
        tenant=tenant,
        start_date=date(2025, 6, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1200.00"),
    )


# ──────────────────────────────────────────
# clamp_due_day
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestClampDueDay:
    def test_clamps_31_to_february_non_leap(self) -> None:
        assert RentScheduleService.clamp_due_day(31, 2026, 2) == 28

    def test_clamps_31_to_february_leap(self) -> None:
        assert RentScheduleService.clamp_due_day(31, 2024, 2) == 29

    def test_clamps_31_to_april(self) -> None:
        assert RentScheduleService.clamp_due_day(31, 2026, 4) == 30

    def test_no_clamp_when_day_fits(self) -> None:
        assert RentScheduleService.clamp_due_day(10, 2026, 3) == 10


# ──────────────────────────────────────────
# effective_rental_value
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestEffectiveRentalValue:
    def test_returns_rental_value_without_pending(self, lease) -> None:
        value = RentScheduleService.effective_rental_value(lease, date(2026, 3, 1))
        assert value == Decimal("1200.00")

    def test_returns_current_value_before_pending_date(self, lease) -> None:
        lease.pending_rental_value = Decimal("1400.00")
        lease.pending_rental_value_date = date(2026, 5, 1)
        lease.save(update_fields=["pending_rental_value", "pending_rental_value_date"])
        value = RentScheduleService.effective_rental_value(lease, date(2026, 3, 1))
        assert value == Decimal("1200.00")

    def test_returns_pending_value_on_or_after_pending_date(self, lease) -> None:
        lease.pending_rental_value = Decimal("1400.00")
        lease.pending_rental_value_date = date(2026, 3, 1)
        lease.save(update_fields=["pending_rental_value", "pending_rental_value_date"])
        value = RentScheduleService.effective_rental_value(lease, date(2026, 3, 1))
        assert value == Decimal("1400.00")


# ──────────────────────────────────────────
# collectible_leases
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestCollectibleLeases:
    def test_includes_active_lease_covering_month(self, lease) -> None:
        result = RentScheduleService.collectible_leases(date(2026, 3, 1))
        assert lease in list(result)

    def test_excludes_lease_with_owner(self, building, lease) -> None:
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=201,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=True,
            owner=owner,
        )
        tenant = make_tenant(cpf_cnpj="11144477735", name="Inquilino Repasse", due_day=10)
        owned_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert owned_lease not in result
        assert lease in result

    def test_excludes_salary_offset_lease(self, building, lease) -> None:
        apt = make_apartment(
            building=building,
            number=202,
            rental_value=Decimal("800.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="12345678909", name="Funcionário", due_day=5)
        offset_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("800.00"),
            is_salary_offset=True,
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert offset_lease not in result

    def test_excludes_prepaid_lease(self, building, lease) -> None:
        apt = make_apartment(
            building=building,
            number=203,
            rental_value=Decimal("1300.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="52998224725", name="Pré-pago", due_day=15)
        prepaid_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1300.00"),
            prepaid_until=date(2026, 9, 1),
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert prepaid_lease not in result

    def test_excludes_lease_window_outside_month_even_if_rented(self, building) -> None:
        """Date-aware: a rented apartment whose lease window is before the month is excluded."""
        apt = make_apartment(
            building=building,
            number=204,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="10000000019", name="Contrato Antigo", due_day=8)
        # Window 2024-01-01 .. 2025-01-01 does NOT intersect March 2026.
        expired_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2024, 1, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert expired_lease not in result

    def test_includes_lease_covering_month_regardless_of_is_rented(self, building) -> None:
        """Date-aware: window covering the month is included even if is_rented=False."""
        apt = make_apartment(
            building=building,
            number=205,
            rental_value=Decimal("1100.00"),
            max_tenants=1,
            is_rented=False,
        )
        tenant = make_tenant(cpf_cnpj="20000000108", name="Janela Cobre", due_day=12)
        covering_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1100.00"),
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert covering_lease in result

    def test_building_id_filters_by_building(self, lease) -> None:
        other_building = make_building(
            street_number=900, name="Edifício 900", address="Rua Outra, 900"
        )
        other_apt = make_apartment(
            building=other_building,
            number=301,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        other_tenant = make_tenant(cpf_cnpj="30000000205", name="Outro Prédio", due_day=9)
        other_lease = make_lease(
            apartment=other_apt,
            tenant=other_tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        result = list(
            RentScheduleService.collectible_leases(
                date(2026, 3, 1), building_id=lease.apartment.building_id
            )
        )
        assert lease in result
        assert other_lease not in result

    def test_excludes_soft_deleted_lease(self, lease) -> None:
        lease.delete()
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert lease not in result


# ──────────────────────────────────────────
# get_month_schedule
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestGetMonthSchedule:
    @freeze_time("2026-03-03")
    def test_item_appears_on_clamped_day_with_details(self, lease) -> None:
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        days_with_items = {d["day"]: d for d in schedule["days"] if d["items"]}
        assert 7 in days_with_items  # due_day=7
        day_7 = days_with_items[7]
        assert day_7["date"] == "2026-03-07"
        item = day_7["items"][0]
        assert item["lease_id"] == lease.id
        assert item["tenant_name"] == "João Silva"
        assert item["apartment_number"] == 101
        assert item["building_number"] == "836"
        assert item["rental_value"] == "1200.00"

    @freeze_time("2026-03-10")
    def test_paid_item_marked(self, lease) -> None:
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 7),
        )
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        item = _find_item(schedule, lease.id)
        assert item["is_paid"] is True
        assert item["payment_date"] == "2026-03-07"

    @freeze_time("2026-03-20")
    def test_overdue_item_in_current_month_has_late_fee(self, lease) -> None:
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        item = _find_item(schedule, lease.id)
        assert item["is_overdue"] is True
        assert item["day_passed"] is True
        expected = FeeCalculatorService.calculate_late_fee(Decimal("1200.00"), 7, date(2026, 3, 20))
        assert item["late_days"] == expected["late_days"]
        assert item["late_fee"] == str(expected["late_fee"])
        assert item["late_days"] > 0
        assert Decimal(item["late_fee"]) > Decimal("0.00")

    @freeze_time("2026-06-15")
    def test_overdue_item_in_past_month_has_no_late_fee(self, lease) -> None:
        """Cross-month: viewing April 2026 from June reports no spurious late fee."""
        schedule = RentScheduleService.get_month_schedule(2026, 4)
        item = _find_item(schedule, lease.id)
        assert item["is_overdue"] is True
        assert item["late_fee"] == "0.00"
        assert item["late_days"] == 0

    @freeze_time("2026-03-20")
    def test_can_toggle_false_when_paid_and_day_passed(self, lease) -> None:
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 7),
        )
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        item = _find_item(schedule, lease.id)
        assert item["can_toggle"] is False

    @freeze_time("2026-03-03")
    def test_next_due_date_points_to_earliest_future_unpaid(self, building, lease) -> None:
        apt = make_apartment(
            building=building,
            number=210,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="40000000396", name="Vence Depois", due_day=20)
        make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        # due_day 7 (lease) is the earliest >= today (2026-03-03)
        assert schedule["next_due_date"] == "2026-03-07"


# ──────────────────────────────────────────
# get_month_stats
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestGetMonthStats:
    @freeze_time("2026-03-03")
    def test_received_total_not_filtered_by_collectibility(self, building, lease) -> None:
        """received_total sums ALL active RentPayments, including non-collectible leases."""
        # Collectible lease paid
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 2),
        )
        # Owned (non-collectible) lease with a payment — must still count in received_total
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=220,
            rental_value=Decimal("700.00"),
            max_tenants=1,
            is_rented=True,
            owner=owner,
        )
        owner_tenant = make_tenant(cpf_cnpj="50000000485", name="Repasse", due_day=5)
        owner_lease = make_lease(
            apartment=apt,
            tenant=owner_tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("700.00"),
        )
        make_rent_payment(
            lease=owner_lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("700.00"),
            payment_date=date(2026, 3, 2),
        )
        stats = RentScheduleService.get_month_stats(2026, 3)
        assert stats["received_total"] == "1900.00"

    @freeze_time("2026-03-03")
    def test_to_receive_and_expected_totals(self, building, lease) -> None:
        apt = make_apartment(
            building=building,
            number=221,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="60000000574", name="Não Pago", due_day=10)
        make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        # Pay the first lease only
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 2),
        )
        stats = RentScheduleService.get_month_stats(2026, 3)
        assert stats["received_total"] == "1200.00"
        assert stats["to_receive_total"] == "1000.00"
        assert stats["expected_total"] == "2200.00"
        assert stats["paid_count"] == 1
        assert stats["due_count"] == 2

    @freeze_time("2026-03-03")
    def test_vacant_kitnets_count_and_value(self, building, lease) -> None:
        make_apartment(
            building=building,
            number=230,
            rental_value=Decimal("800.00"),
            max_tenants=1,
            is_rented=False,
        )
        make_apartment(
            building=building,
            number=231,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=False,
        )
        stats = RentScheduleService.get_month_stats(2026, 3, building_id=building.id)
        assert stats["vacant_kitnets_count"] == 2
        assert stats["vacant_kitnets_value"] == "1700.00"

    @freeze_time("2026-03-20")
    def test_overdue_count_and_fee_current_month(self, lease) -> None:
        stats = RentScheduleService.get_month_stats(2026, 3)
        assert stats["overdue_count"] == 1
        expected = FeeCalculatorService.calculate_late_fee(Decimal("1200.00"), 7, date(2026, 3, 20))
        assert stats["overdue_total_fee"] == str(expected["late_fee"])
        assert Decimal(stats["overdue_total_fee"]) > Decimal("0.00")

    @freeze_time("2026-06-15")
    def test_overdue_fee_not_accrued_for_non_current_month(self, lease) -> None:
        stats = RentScheduleService.get_month_stats(2026, 4)
        assert stats["overdue_total_fee"] == "0.00"


# ──────────────────────────────────────────
# toggle_payment
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestTogglePayment:
    @freeze_time("2026-03-03")
    def test_creates_payment_when_unpaid_before_due(self, lease, admin_user) -> None:
        result = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "ok"
        assert result["is_paid"] is True
        payment = RentPayment.objects.get(lease=lease, reference_month=date(2026, 3, 1))
        assert payment.amount_paid == Decimal("1200.00")
        assert payment.payment_date == date(2026, 3, 3)

    @freeze_time("2026-03-20")
    def test_creates_payment_when_unpaid_overdue(self, lease, admin_user) -> None:
        result = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "ok"
        assert result["is_paid"] is True
        payment = RentPayment.objects.get(lease=lease, reference_month=date(2026, 3, 1))
        assert payment.payment_date == date(2026, 3, 20)

    @freeze_time("2026-03-03")
    def test_soft_deletes_payment_when_paid_before_due(self, lease, admin_user) -> None:
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 2),
        )
        result = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "ok"
        assert result["is_paid"] is False
        assert not RentPayment.objects.filter(
            lease=lease, reference_month=date(2026, 3, 1)
        ).exists()
        assert RentPayment.all_objects.filter(
            lease=lease, reference_month=date(2026, 3, 1), is_deleted=True
        ).exists()

    @freeze_time("2026-03-20")
    def test_refuses_unpay_when_paid_and_day_passed(self, lease, admin_user) -> None:
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 7),
        )
        result = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "error"
        assert RentPayment.objects.filter(lease=lease, reference_month=date(2026, 3, 1)).exists()

    @freeze_time("2026-03-03")
    def test_refuses_when_month_finalized(self, lease, admin_user) -> None:
        baker.make("core.MonthSnapshot", reference_month=date(2026, 3, 1), is_finalized=True)
        result = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "error"
        assert not RentPayment.objects.filter(
            lease=lease, reference_month=date(2026, 3, 1)
        ).exists()

    @freeze_time("2026-03-03")
    def test_refuses_when_lease_not_collectible(self, building, admin_user) -> None:
        apt = make_apartment(
            building=building,
            number=240,
            rental_value=Decimal("800.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="70000000663", name="Salário", due_day=5)
        offset_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("800.00"),
            is_salary_offset=True,
        )
        result = RentScheduleService.toggle_payment(offset_lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "error"

    @freeze_time("2026-03-03")
    def test_create_then_soft_delete_then_recreate(self, lease, admin_user) -> None:
        """UniqueConstraint is conditional on is_deleted=False — slot reusable."""
        first = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert first["is_paid"] is True
        second = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert second["is_paid"] is False
        third = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        assert third["status"] == "ok"
        assert third["is_paid"] is True
        assert (
            RentPayment.objects.filter(lease=lease, reference_month=date(2026, 3, 1)).count() == 1
        )

    @freeze_time("2026-03-03")
    def test_normalizes_reference_month_to_first_day(self, lease, admin_user) -> None:
        result = RentScheduleService.toggle_payment(lease.id, date(2026, 3, 15), admin_user)
        assert result["status"] == "ok"
        assert RentPayment.objects.filter(lease=lease, reference_month=date(2026, 3, 1)).exists()


def _find_item(schedule: dict, lease_id: int) -> dict:
    for day in schedule["days"]:
        for item in day["items"]:
            if item["lease_id"] == lease_id:
                return item
    msg = f"Item for lease {lease_id} not found in schedule"
    raise AssertionError(msg)
