"""Session 49 — OwnerDistributionService tests (Phase 6 backend).

Household (Raul & Célia = the condominium) result via the anchored carry-forward fold consuming
CondoBalanceService.result_of_month (DRY); external owners (Tiago/Alvaro) aggregated from
displayable_leases as DISPLAY ONLY — strictly outside net/cash/fold. Pre-tracking months are
isolated (net shown, not accumulated). Money is quantized only at the boundary.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from finances.models import BillLifecycleState
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.owner_distribution_service import OwnerDistributionService
from freezegun import freeze_time

from core.models import FinancialSettings
from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_building,
    make_condo_month_close,
    make_lease,
    make_person,
    make_rent_payment,
    make_reserve_movement,
)

pytestmark = pytest.mark.django_db

JUNE = date(2026, 6, 1)
JULY = date(2026, 7, 1)


def _active_bill(amount: str, *, competence=JULY):
    bill = make_bill(competence_month=competence, lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


# --------------------------------------------------------------------------- household = condo


@freeze_time("2026-07-15 12:00:00")
def test_household_result_of_month_consumes_result_of_month() -> None:
    lease = make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_rent_payment(lease=lease, reference_month=JULY, amount_paid=Decimal("1000.00"))
    _active_bill("400.00")
    result = OwnerDistributionService.compute(2026, 7)
    assert result["household"]["result_of_month"] == str(
        CondoBalanceService.result_of_month(2026, 7)
    )
    assert result["household"]["result_of_month"] == "600.00"  # 1000 received - 400 expense


@freeze_time("2026-07-15 12:00:00")
def test_household_name_is_label_not_person() -> None:
    assert OwnerDistributionService.compute(2026, 7)["household"]["name"] == "Raul & Célia"


# --------------------------------------------------------------------------- fold


@freeze_time("2026-07-15 12:00:00")
def test_fold_anchored_on_previous_closed_month() -> None:
    make_condo_month_close(
        reference_month=JUNE,
        status="closed",
        closed_at=timezone.now(),
        carry_forward_out=Decimal("-50.00"),
    )
    _active_bill("100.00")  # July net = -100
    result = OwnerDistributionService.compute(2026, 7)["household"]
    assert result["result_of_month"] == "-100.00"
    assert result["carried_in"] == "-50.00"
    assert result["available"] == "0.00"  # max(0, -100 + -50)
    assert result["carried_out"] == "-150.00"  # min(0, -100 + -50)


@freeze_time("2026-07-15 12:00:00")
def test_no_prior_close_carries_in_zero_positive_net() -> None:
    make_lease(rental_value=Decimal("900.00"), start_date=date(2026, 1, 1))
    result = OwnerDistributionService.compute(2026, 7)["household"]
    assert result["carried_in"] == "0.00"
    assert result["available"] == "900.00"  # expected (unpaid) rent of a collectible lease
    assert result["carried_out"] == "0.00"


@freeze_time("2026-07-15 12:00:00")
def test_sequential_carry_chains_from_close() -> None:
    _active_bill("200.00", competence=JUNE)  # June net = -200
    CondoMonthCloseService.close(2026, 6)
    june_carry = CondoMonthCloseService.carried_in_for(JULY)
    result = OwnerDistributionService.compute(2026, 7)["household"]
    assert result["carried_in"] == str(june_carry)
    assert june_carry == Decimal("-200.00")


@freeze_time("2026-07-15 12:00:00")
def test_reserve_deposit_does_not_change_distribution() -> None:
    make_lease(rental_value=Decimal("500.00"), start_date=date(2026, 1, 1))
    before = OwnerDistributionService.compute(2026, 7)["household"]
    make_reserve_movement(kind="deposit", amount=Decimal("300.00"), movement_date=date(2026, 7, 5))
    after = OwnerDistributionService.compute(2026, 7)["household"]
    assert before == after  # reserve transfer never reduces the household distribution (§4.7)


@freeze_time("2026-07-15 12:00:00")
def test_pre_tracking_month_is_isolated() -> None:
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 1, 1),
        rent_tracking_start_date=JUNE,
    )
    _active_bill("100.00", competence=date(2026, 5, 1))  # a May bill
    result = OwnerDistributionService.compute(2026, 5)["household"]
    assert result["result_of_month"] == "-100.00"  # shown
    assert result["carried_in"] == "0.00"
    assert result["carried_out"] == "0.00"  # isolated — NOT a spurious -100 carry


# --------------------------------------------------------------------------- external owners


@freeze_time("2026-07-15 12:00:00")
def test_external_owners_aggregated_per_owner() -> None:
    building = make_building(street_number=836)
    tiago = make_person(name="Tiago", is_owner=True)
    alvaro = make_person(name="Alvaro", is_owner=True)
    make_lease(
        apartment=make_apartment(building=building, number=101, owner=tiago),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
    )
    make_lease(
        apartment=make_apartment(building=building, number=103, owner=tiago),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
    )
    make_lease(
        apartment=make_apartment(building=building, number=200, owner=alvaro),
        rental_value=Decimal("750.00"),
        start_date=date(2026, 1, 1),
    )
    result = OwnerDistributionService.compute(2026, 7)
    by_name = {owner["owner_name"]: owner for owner in result["external_owners"]}
    assert by_name["Tiago"]["leases_count"] == 2
    assert by_name["Tiago"]["rent_total"] == "1600.00"
    assert by_name["Alvaro"]["leases_count"] == 1
    assert by_name["Alvaro"]["rent_total"] == "750.00"
    assert result["external_total"] == "2350.00"


@freeze_time("2026-07-15 12:00:00")
def test_external_owner_rent_excluded_from_household_net() -> None:
    owner_lease = make_lease(
        apartment=make_apartment(owner=make_person(name="Tiago", is_owner=True)),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
    )
    make_rent_payment(lease=owner_lease, reference_month=JULY, amount_paid=Decimal("800.00"))
    result = OwnerDistributionService.compute(2026, 7)
    # The owner-repass rent is neither in the household net nor folded into available.
    assert result["household"]["result_of_month"] == "0.00"
    assert result["household"]["available"] == "0.00"
    assert result["external_total"] == "800.00"


@freeze_time("2026-07-15 12:00:00")
def test_external_owner_uses_effective_rental_value_with_pending() -> None:
    make_lease(
        apartment=make_apartment(owner=make_person(name="Tiago", is_owner=True)),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
        pending_rental_value=Decimal("900.00"),
        pending_rental_value_date=JULY,
    )
    result = OwnerDistributionService.compute(2026, 7)
    assert result["external_owners"][0]["rent_total"] == "900.00"


@freeze_time("2026-07-15 12:00:00")
def test_salary_offset_lease_is_not_an_external_owner() -> None:
    make_lease(is_salary_offset=True, rental_value=Decimal("850.00"), start_date=date(2026, 1, 1))
    result = OwnerDistributionService.compute(2026, 7)
    assert result["external_owners"] == []
    assert result["external_total"] == "0.00"


@freeze_time("2026-07-15 12:00:00")
def test_soft_deleted_owner_lease_excluded_from_externals() -> None:
    """§18: a soft-deleted owner-repass Lease drops out of the external aggregation — confirming
    the exclusion via displayable_leases' default manager, not merely assuming it."""
    apartment = make_apartment(owner=make_person(name="Tiago", is_owner=True))
    lease = make_lease(
        apartment=apartment, rental_value=Decimal("800.00"), start_date=date(2026, 1, 1)
    )
    assert OwnerDistributionService.compute(2026, 7)["external_total"] == "800.00"

    lease.delete()  # soft delete
    after = OwnerDistributionService.compute(2026, 7)
    assert after["external_owners"] == []
    assert after["external_total"] == "0.00"


@freeze_time("2026-07-15 12:00:00")
def test_pre_tracking_hides_external_owners() -> None:
    FinancialSettings.objects.create(
        pk=1,
        initial_balance=Decimal("0.00"),
        initial_balance_date=date(2026, 1, 1),
        rent_tracking_start_date=JUNE,
    )
    make_lease(
        apartment=make_apartment(owner=make_person(name="Tiago", is_owner=True)),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
    )
    result = OwnerDistributionService.compute(2026, 5)  # before tracking
    assert result["external_owners"] == []
    assert result["external_total"] == "0.00"


# --------------------------------------------------------------------------- structural


@freeze_time("2026-07-15 12:00:00")
def test_building_id_scopes_household_and_externals() -> None:
    building = make_building(street_number=8360)
    make_lease(
        apartment=make_apartment(
            building=building, number=101, owner=make_person(name="Tiago", is_owner=True)
        ),
        rental_value=Decimal("800.00"),
        start_date=date(2026, 1, 1),
    )
    # An owner lease in another building must be excluded by the building filter.
    make_lease(
        apartment=make_apartment(
            building=make_building(street_number=9990),
            number=1,
            owner=make_person(name="Outro", is_owner=True),
        ),
        rental_value=Decimal("500.00"),
        start_date=date(2026, 1, 1),
    )
    result = OwnerDistributionService.compute(2026, 7, building.id)
    assert [owner["owner_name"] for owner in result["external_owners"]] == ["Tiago"]
    assert result["external_total"] == "800.00"


@freeze_time("2026-07-15 12:00:00")
def test_empty_state_is_coherent() -> None:
    result = OwnerDistributionService.compute(2026, 7)
    assert result["household"]["result_of_month"] == "0.00"
    assert result["household"]["available"] == "0.00"
    assert result["household"]["carried_out"] == "0.00"
    assert result["external_owners"] == []
    assert result["external_total"] == "0.00"
