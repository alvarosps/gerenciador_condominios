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

from core.models import FinancialSettings, RentPayment
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

    def test_returns_pending_value_for_mid_month_pending_date(self, lease) -> None:
        """A mid-month pending date activates the increase for that whole month
        (month-granular), matching RentAdjustmentService.activate_pending_adjustments."""
        lease.pending_rental_value = Decimal("1400.00")
        lease.pending_rental_value_date = date(2026, 7, 15)
        lease.save(update_fields=["pending_rental_value", "pending_rental_value_date"])
        # reference_month is the first of July — before the day-15 pending date, but
        # the increase must already be in effect for July.
        value = RentScheduleService.effective_rental_value(lease, date(2026, 7, 1))
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

    def test_prepaid_boundary_keeps_month_whose_due_equals_prepaid_until(self, building) -> None:
        """Pay-to-live: prepaid_until is the end of the last paid period. The installment
        due exactly on prepaid_until is the NEXT one due and must stay collectible — the
        month whose clamped due date equals prepaid_until is NOT prepaid (regression for
        the month-start off-by-one). Kitnet 113: prepaid_until=2026-09-29, due_day=29."""
        apt = make_apartment(
            building=building,
            number=113,
            rental_value=Decimal("1300.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="52998224725", name="Kitnet 113", due_day=29)
        prepaid_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=24,
            rental_value=Decimal("1300.00"),
            prepaid_until=date(2026, 9, 29),
        )
        # Aug: due 29/08 < prepaid_until 29/09 -> already paid -> excluded.
        assert prepaid_lease not in list(RentScheduleService.collectible_leases(date(2026, 8, 1)))
        # Sep: due 29/09 == prepaid_until -> NEXT one due -> COLLECTIBLE.
        assert prepaid_lease in list(RentScheduleService.collectible_leases(date(2026, 9, 1)))
        # Oct: due 29/10 > prepaid_until -> collectible.
        assert prepaid_lease in list(RentScheduleService.collectible_leases(date(2026, 10, 1)))

    def test_prepaid_excludes_month_whose_due_precedes_prepaid_until(self, building) -> None:
        """A month whose clamped due date falls strictly before prepaid_until is already
        covered and excluded — compared against the clamped due date, not the month start."""
        apt = make_apartment(
            building=building,
            number=114,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="12345678909", name="Dia 10", due_day=10)
        prepaid_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=24,
            rental_value=Decimal("1000.00"),
            prepaid_until=date(2026, 9, 20),
        )
        # Sep: due 10/09 < prepaid_until 20/09 -> covered -> excluded.
        assert prepaid_lease not in list(RentScheduleService.collectible_leases(date(2026, 9, 1)))
        # Oct: due 10/10 > prepaid_until -> collectible.
        assert prepaid_lease in list(RentScheduleService.collectible_leases(date(2026, 10, 1)))

    def test_includes_auto_renewing_lease_past_calculated_end_date(self, building) -> None:
        """Brazilian residential leases auto-renew (Lei 8.245/91): a lease whose original
        term elapsed long ago is still active (move-out = soft-delete, not term expiry), so
        it stays collectible. Regression guard for the dropped-auto-renewed-leases bug."""
        apt = make_apartment(
            building=building,
            number=204,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="10000000019", name="Contrato Antigo", due_day=8)
        # Original term 2024-01-01 + 12 months elapsed before March 2026, but the lease
        # auto-renewed and was never soft-deleted -> still collectible.
        auto_renewed_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2024, 1, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 3, 1)))
        assert auto_renewed_lease in result

    def test_collectible_includes_lease_well_past_validity(self, building) -> None:
        """A lease started 2022 with a 12-month term is still collectible in 2026 — no
        upper date bound exists; only soft-delete deactivates a lease."""
        apt = make_apartment(
            building=building,
            number=206,
            rental_value=Decimal("1000.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="20000000108", name="Veterano", due_day=8)
        old_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2022, 1, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        result = list(RentScheduleService.collectible_leases(date(2026, 6, 1)))
        assert old_lease in result

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
# displayable_leases
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestDisplayableLeases:
    def test_includes_owner_repass_lease_flagged(self, building) -> None:
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=250,
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
        result = RentScheduleService.displayable_leases(date(2026, 3, 1))
        assert (owned_lease, False, "owner_repass") in result
        assert owned_lease not in list(RentScheduleService.collectible_leases(date(2026, 3, 1)))

    def test_includes_salary_offset_lease_flagged(self, building) -> None:
        apt = make_apartment(
            building=building,
            number=251,
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
        result = RentScheduleService.displayable_leases(date(2026, 3, 1))
        assert (offset_lease, False, "salary_offset") in result
        assert offset_lease not in list(RentScheduleService.collectible_leases(date(2026, 3, 1)))

    def test_collectible_lease_flagged_true_none(self, lease) -> None:
        result = RentScheduleService.displayable_leases(date(2026, 3, 1))
        assert (lease, True, None) in result

    def test_prepaid_lease_is_hidden(self, building) -> None:
        apt = make_apartment(
            building=building,
            number=252,
            rental_value=Decimal("1300.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="52998224725", name="Pré-pago", due_day=15)
        # due 15/03 < prepaid_until 2026-09-01 -> prepaid for March -> hidden.
        prepaid_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1300.00"),
            prepaid_until=date(2026, 9, 1),
        )
        displayed = [item[0] for item in RentScheduleService.displayable_leases(date(2026, 3, 1))]
        assert prepaid_lease not in displayed
        assert prepaid_lease not in list(RentScheduleService.collectible_leases(date(2026, 3, 1)))

    def test_soft_deleted_lease_excluded(self, lease) -> None:
        lease.delete()
        displayed = [item[0] for item in RentScheduleService.displayable_leases(date(2026, 3, 1))]
        assert lease not in displayed


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

    @freeze_time("2026-03-20")
    def test_next_due_date_none_when_no_future_unpaid_due(self, lease) -> None:
        """When every due date in the month is in the past, next_due_date is None
        (drives the disabled 'Próximo vencimento' button in the UI)."""
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        assert schedule["next_due_date"] is None

    @freeze_time("2026-03-03")
    def test_owner_repass_item_has_is_collectible_false_and_no_toggle(self, building) -> None:
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=260,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=True,
            owner=owner,
        )
        tenant = make_tenant(cpf_cnpj="11144477735", name="Repasse", due_day=10)
        owner_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        item = _find_item(schedule, owner_lease.id)
        assert item["is_collectible"] is False
        assert item["non_collectible_reason"] == "owner_repass"
        assert item["can_toggle"] is False

    @freeze_time("2026-03-03")
    def test_salary_offset_item_flagged(self, building) -> None:
        apt = make_apartment(
            building=building,
            number=261,
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
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        item = _find_item(schedule, offset_lease.id)
        assert item["is_collectible"] is False
        assert item["non_collectible_reason"] == "salary_offset"
        assert item["can_toggle"] is False

    @freeze_time("2026-03-03")
    def test_collectible_item_has_is_collectible_true(self, lease) -> None:
        schedule = RentScheduleService.get_month_schedule(2026, 3)
        item = _find_item(schedule, lease.id)
        assert item["is_collectible"] is True
        assert item["non_collectible_reason"] is None

    @freeze_time("2026-03-03")
    def test_next_due_date_ignores_non_collectible_items(self, building) -> None:
        """A month with only a non-collectible (owner-repass) item has no next_due_date."""
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=262,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=True,
            owner=owner,
        )
        tenant = make_tenant(cpf_cnpj="11144477735", name="Repasse", due_day=20)
        make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        schedule = RentScheduleService.get_month_schedule(2026, 3, building_id=building.id)
        assert schedule["next_due_date"] is None


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
    def test_received_and_expected_totals_scoped_by_building(self, building, lease) -> None:
        """received_total/expected_total honor the building_id filter so the
        building-scoped view stays coherent with to_receive_total."""
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 2),
        )
        other_building = make_building(
            street_number=840, name="Edifício 840", address="Rua Teste, 840"
        )
        other_apt = make_apartment(
            building=other_building,
            number=10,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=True,
        )
        other_tenant = make_tenant(cpf_cnpj="70000000663", name="Outro Prédio", due_day=5)
        other_lease = make_lease(
            apartment=other_apt,
            tenant=other_tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        make_rent_payment(
            lease=other_lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("900.00"),
            payment_date=date(2026, 3, 2),
        )
        all_stats = RentScheduleService.get_month_stats(2026, 3)
        assert all_stats["received_total"] == "2100.00"
        scoped = RentScheduleService.get_month_stats(2026, 3, building_id=building.id)
        assert scoped["received_total"] == "1200.00"
        assert scoped["expected_total"] == "1200.00"

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
    def test_overdue_count_accrued_but_fee_zero_for_past_month(self, lease) -> None:
        # Past month (April viewed from June): the item is overdue (counted) but the fee is
        # only computed for the current month.
        stats = RentScheduleService.get_month_stats(2026, 4)
        assert stats["overdue_count"] == 1
        assert stats["overdue_total_fee"] == "0.00"

    @freeze_time("2026-03-20")
    def test_no_overdue_for_future_month(self, lease) -> None:
        # Future month (May viewed from March): nothing is overdue yet.
        stats = RentScheduleService.get_month_stats(2026, 5)
        assert stats["overdue_count"] == 0
        assert stats["overdue_total_fee"] == "0.00"

    @freeze_time("2026-03-03")
    def test_due_count_excludes_non_collectible_leases(self, building, lease) -> None:
        """Stats are computed over collectible leases only: an owner-repass lease is
        surfaced in the calendar but never counted as due."""
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=270,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=True,
            owner=owner,
        )
        tenant = make_tenant(cpf_cnpj="11144477735", name="Repasse", due_day=10)
        make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        stats = RentScheduleService.get_month_stats(2026, 3)
        assert stats["due_count"] == 1


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

    @freeze_time("2026-03-03")
    def test_unmark_records_deleted_by(self, lease, admin_user) -> None:
        """Soft-delete on unmark records the acting user in the audit column."""
        make_rent_payment(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 2),
        )
        RentScheduleService.toggle_payment(lease.id, date(2026, 3, 1), admin_user)
        deleted = RentPayment.all_objects.get(
            lease=lease, reference_month=date(2026, 3, 1), is_deleted=True
        )
        assert deleted.deleted_by_id == admin_user.id

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

    @freeze_time("2026-03-03")
    def test_refuses_owner_repass_lease(self, building, admin_user) -> None:
        """An owner-repass lease is surfaced but not collectible — toggling is refused."""
        owner = make_person(name="Proprietário")
        apt = make_apartment(
            building=building,
            number=241,
            rental_value=Decimal("900.00"),
            max_tenants=1,
            is_rented=True,
            owner=owner,
        )
        tenant = make_tenant(cpf_cnpj="11144477735", name="Repasse", due_day=10)
        owner_lease = make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        result = RentScheduleService.toggle_payment(owner_lease.id, date(2026, 3, 1), admin_user)
        assert result["status"] == "error"


# ──────────────────────────────────────────
# is_collectible_for_month
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestIsCollectibleForMonth:
    def test_not_started(self, apartment) -> None:
        tenant = make_tenant(cpf_cnpj="52998224725", name="Futuro", due_day=10)
        lease = make_lease(
            apartment=apartment,
            tenant=tenant,
            start_date=date(2026, 5, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 4) is False

    def test_started(self, apartment) -> None:
        tenant = make_tenant(cpf_cnpj="11144477735", name="Ativo", due_day=10)
        lease = make_lease(
            apartment=apartment,
            tenant=tenant,
            start_date=date(2026, 3, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 3) is True
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 4) is True

    def test_prepaid(self, apartment) -> None:
        tenant = make_tenant(cpf_cnpj="12345678909", name="Pré-pago", due_day=10)
        # due 10/03 < prepaid_until 2026-03-11 -> March prepaid; due 10/04 > -> April collectible.
        lease = make_lease(
            apartment=apartment,
            tenant=tenant,
            start_date=date(2026, 1, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
            prepaid_until=date(2026, 3, 11),
        )
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 3) is False
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 4) is True


# ──────────────────────────────────────────
# rent_tracking_start_month / is_month_tracked / tracking boundary
# ──────────────────────────────────────────


@pytest.mark.django_db
class TestRentTrackingBoundary:
    """Gating collectibility by FinancialSettings.rent_tracking_start_date."""

    def _make_lease_for_boundary(self, building):
        """Helper: a lease started May 2026, otherwise collectible from May onwards."""
        apt = make_apartment(
            building=building,
            number=500,
            rental_value=Decimal("1100.00"),
            max_tenants=1,
            is_rented=True,
        )
        tenant = make_tenant(cpf_cnpj="40000000396", name="Boundary Tenant", due_day=10)
        return make_lease(
            apartment=apt,
            tenant=tenant,
            start_date=date(2026, 5, 1),
            validity_months=12,
            rental_value=Decimal("1100.00"),
        )

    # 1. collectible_leases gated by boundary
    def test_collectible_leases_empty_before_boundary(self, building) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        lease = self._make_lease_for_boundary(building)
        result = list(RentScheduleService.collectible_leases(date(2026, 5, 1)))
        assert lease not in result

    def test_collectible_leases_includes_lease_on_boundary_month(self, building) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        lease = self._make_lease_for_boundary(building)
        result = list(RentScheduleService.collectible_leases(date(2026, 6, 1)))
        assert lease in result

    # 2. is_collectible_for_month gated by boundary
    def test_is_collectible_false_before_boundary(self, building) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        lease = self._make_lease_for_boundary(building)
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 5) is False

    def test_is_collectible_true_on_boundary_month(self, building) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        lease = self._make_lease_for_boundary(building)
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 6) is True

    # 3. No boundary → gate is a no-op
    def test_no_boundary_collectible_leases_includes_lease(self, building) -> None:
        # No FinancialSettings row at all — legacy behavior must be preserved.
        lease = self._make_lease_for_boundary(building)
        result = list(RentScheduleService.collectible_leases(date(2026, 5, 1)))
        assert lease in result

    def test_no_boundary_is_collectible_true(self, building) -> None:
        lease = self._make_lease_for_boundary(building)
        assert RentScheduleService.is_collectible_for_month(lease, 2026, 5) is True

    # 4. rent_tracking_start_month() return values
    def test_rent_tracking_start_month_none_when_no_row(self) -> None:
        assert RentScheduleService.rent_tracking_start_month() is None

    def test_rent_tracking_start_month_none_when_field_is_null(self) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=None,
        )
        assert RentScheduleService.rent_tracking_start_month() is None

    def test_rent_tracking_start_month_returns_first_of_month(self) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        assert RentScheduleService.rent_tracking_start_month() == date(2026, 6, 1)

    def test_rent_tracking_start_month_normalizes_mid_month_value(self) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 15),
        )
        assert RentScheduleService.rent_tracking_start_month() == date(2026, 6, 1)

    # 5. Boundary respects month granularity
    def test_is_month_tracked_true_for_boundary_month(self) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        assert RentScheduleService.is_month_tracked(2026, 6) is True

    def test_is_month_tracked_false_for_month_before_boundary(self) -> None:
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        assert RentScheduleService.is_month_tracked(2026, 5) is False


def _find_item(schedule: dict, lease_id: int) -> dict:
    for day in schedule["days"]:
        for item in day["items"]:
            if item["lease_id"] == lease_id:
                return item
    msg = f"Item for lease {lease_id} not found in schedule"
    raise AssertionError(msg)
