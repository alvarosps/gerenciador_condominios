"""Condominium owner-distribution service (Phase 6, Session 49, design §4.7/§6/§8).

OwnerDistributionService.compute distributes the month's result:
- the household (Raul & Célia = the condominium itself) gets the competence result via the anchored
  carry-forward fold — consuming CondoBalanceService.result_of_month (DRY, never re-derived) and the
  shared fold_step (single source with CondoMonthCloseService.close);
- external owners (Tiago / Alvaro) are DISPLAY ONLY — owner→Σ effective_rental_value of the
  owner-repass leases from RentScheduleService.displayable_leases — strictly outside net/cash/fold.

Pre-tracking months (before rent_tracking_start_date) are isolated: their net is shown but NOT
accumulated into the fold (design §4.7). Internal sums are raw Decimals; quantize_money is applied
once at the output boundary so the household figure never differs from result_of_month by a cent.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from core.models import Person
from core.services.rent_schedule_service import RentScheduleService
from finances.money import money_str
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService

ZERO = Decimal(0)

# Raul & Célia are NOT a Person (§17) — the household IS the condominium (locked decision #13).
_HOUSEHOLD_NAME = "Raul & Célia"
_OWNER_REPASS = "owner_repass"


class OwnerDistributionService:
    """Stateless per-owner distribution: household fold + display-only external owners."""

    @staticmethod
    def compute(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Distribute the month's result by owner (design §4.7/§6).

        household = the condominium (Raul & Célia): result_of_month (consumed, not re-derived) folded
        with the anchored carry-forward; external_owners = display-only Σ rent per external owner
        (never part of net/cash/fold). Money is a quantized string at the boundary.
        """
        reference_month = date(year, month, 1)
        net = CondoBalanceService.result_of_month(year, month, building_id)

        # Single source of the fold + pre-tracking isolation, shared with CondoMonthCloseService.close
        # so the displayed distribution can never contradict the frozen CondoMonthClose (design §4.7).
        carried_in, available, carried_out = CondoMonthCloseService.folded_distribution(
            reference_month, net
        )

        external_owners = OwnerDistributionService._external_owners(reference_month, building_id)
        external_total = sum((Decimal(owner["rent_total"]) for owner in external_owners), ZERO)

        return {
            "year": year,
            "month": month,
            "household": {
                "name": _HOUSEHOLD_NAME,
                "result_of_month": money_str(net),
                "carried_in": money_str(carried_in),
                "available": money_str(available),
                "carried_out": money_str(carried_out),
            },
            "external_owners": external_owners,
            "external_total": money_str(external_total),
        }

    @staticmethod
    def _external_owners(reference_month: date, building_id: int | None) -> list[dict[str, Any]]:
        """Aggregate owner-repass leases (Tiago/Alvaro) by Apartment.owner — display only (§6).

        Σ effective_rental_value per owner (never raw rental_value); salary-offset leases have no
        owner and never appear. Ordered by owner_id for a deterministic payload.
        """
        totals: dict[int, Decimal] = {}
        counts: dict[int, int] = {}
        for lease, _is_collectible, reason in RentScheduleService.displayable_leases(
            reference_month, building_id
        ):
            if reason != _OWNER_REPASS:
                continue
            # owner_repass is emitted only when apartment.owner_id is set; owner_id is the already
            # select_related'd FK column (no per-lease Person query). The None guard is the type
            # narrowing + a defense against an SSOT change in displayable_leases — never hit today.
            owner_id = lease.apartment.owner_id
            if owner_id is None:
                continue
            totals[owner_id] = totals.get(
                owner_id, ZERO
            ) + RentScheduleService.effective_rental_value(lease, reference_month)
            counts[owner_id] = counts.get(owner_id, 0) + 1
        if not totals:
            return []
        # Resolve owner names in ONE query (all_objects mirrors FK access — a soft-deleted owner
        # still shows its name, as the prior lease.apartment.owner dereference did).
        names = dict(Person.all_objects.filter(pk__in=totals).values_list("pk", "name"))
        return [
            {
                "owner_id": owner_id,
                "owner_name": names.get(owner_id, ""),
                "leases_count": counts[owner_id],
                "rent_total": money_str(totals[owner_id]),
            }
            for owner_id in sorted(totals)
        ]
