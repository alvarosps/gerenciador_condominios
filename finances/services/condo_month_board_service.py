"""Session 66 — single data source for the monthly bills cockpit (design §3.3).

CondoMonthBoardService.build assembles the whole board from Bill.objects.with_amounts(today)
.with_list_relations(): the "Atrasadas" section (cross-competence, own overdue criterion), the
"Dívida adiada/suspensa" sub-section (also cross-competence, kept out of the month totals), the
selected month grouped by building, the month totals, and the count of billing accounts still
missing a bill for the month. Read-only; ``today`` always comes from the caller (today_sp()).
"""

from datetime import date
from decimal import Decimal
from typing import TypedDict

from django.db.models import QuerySet

from finances.models import Bill, BillingAccount, BillLifecycleState, BillSkip
from finances.money import money_str
from finances.serializers import BillSerializer
from finances.services.bill_generation_service import BillGenerationService

_ZERO: Decimal = Decimal("0.00")
_CONDOMINIO_LABEL = "Condomínio"
_DEFERRED_SUSPENDED_STATES = (BillLifecycleState.SUSPENDED, BillLifecycleState.DEFERRED)


class MonthBoardTotals(TypedDict):
    due: str
    paid: str
    remaining: str
    overdue: str


class MonthBoardGeneration(TypedDict):
    missing_count: int


class MonthBoardGroup(TypedDict):
    building_id: int | None
    building_label: str
    bills: list[dict[str, object]]


class MonthBoard(TypedDict):
    """Payload shape returned by ``build`` (S66 authoritative contract — SESSION_STATE)."""

    overdue: list[dict[str, object]]
    deferred_suspended: list[dict[str, object]]
    groups: list[MonthBoardGroup]
    totals: MonthBoardTotals
    generation: MonthBoardGeneration


def _serialize_bills(bills: list[Bill]) -> list[dict[str, object]]:
    """BillSerializer(many=True).data as a plain list[dict] (DRF's ReturnList/ReturnDict are
    dict/list subclasses at runtime; materializing them here keeps the board's TypedDict
    honest without a suppression at every call site)."""
    return [dict(item) for item in BillSerializer(bills, many=True).data]


class CondoMonthBoardService:
    """Stateless read-only board for the monthly bills cockpit."""

    @staticmethod
    def build(year: int, month: int, today: date) -> MonthBoard:
        """Assemble the board payload for (year, month) as of ``today``.

        Always called with today_sp(); bills are serialized via BillSerializer over
        Bill.objects.with_amounts(today).with_list_relations() (no N+1, money via annotations).
        """
        month_start = date(year, month, 1)
        base_qs = Bill.objects.with_amounts(today).with_list_relations()

        overdue_bills = CondoMonthBoardService._overdue_bills(base_qs, today)
        deferred_suspended_bills = CondoMonthBoardService._deferred_suspended_bills(base_qs)
        month_bills = CondoMonthBoardService._month_active_bills(base_qs, month_start)

        return {
            "overdue": _serialize_bills(overdue_bills),
            "deferred_suspended": _serialize_bills(deferred_suspended_bills),
            "groups": CondoMonthBoardService._grouped_by_building(month_bills),
            "totals": CondoMonthBoardService._totals(month_bills, overdue_bills),
            "generation": {"missing_count": CondoMonthBoardService._missing_count(month_start)},
        }

    @staticmethod
    def _overdue_bills(base_qs: QuerySet[Bill], today: date) -> list[Bill]:
        """The board's OWN overdue criterion: resto>0, due_date<today, ACTIVE, any competence.

        Deliberately built from explicit filters instead of the ``is_overdue`` with_amounts()
        annotation or the dashboard's legacy ``overdue`` action: the board owns this predicate
        (design §3.3) so it can never silently drift if either of those definitions changes for
        an unrelated reason. ``due_date == today`` is NOT overdue (strict less-than boundary).
        Filtered as a dict[str, object] lookup (idiom: dashboard_views.py:244) so the
        django-stubs plugin accepts the with_amounts() annotation field names.
        """
        overdue_lookup: dict[str, object] = {
            "amount_remaining__gt": 0,
            "due_date__lt": today,
            "lifecycle_state": BillLifecycleState.ACTIVE,
        }
        return list(base_qs.filter(**overdue_lookup).order_by("due_date"))

    @staticmethod
    def _deferred_suspended_bills(base_qs: QuerySet[Bill]) -> list[Bill]:
        """SUSPENDED/DEFERRED bills with resto>0, any competence — kept OUT of totals."""
        deferred_lookup: dict[str, object] = {
            "amount_remaining__gt": 0,
            "lifecycle_state__in": _DEFERRED_SUSPENDED_STATES,
        }
        return list(base_qs.filter(**deferred_lookup).order_by("due_date"))

    @staticmethod
    def _month_active_bills(base_qs: QuerySet[Bill], month_start: date) -> list[Bill]:
        """ACTIVE bills of the selected competence month (paid bills included; CANCELED never)."""
        return list(
            base_qs.filter(
                competence_month=month_start, lifecycle_state=BillLifecycleState.ACTIVE
            ).order_by("due_date")
        )

    @staticmethod
    def _grouped_by_building(month_bills: list[Bill]) -> list[MonthBoardGroup]:
        """Group the month's bills by building; buildingless bills bucket to "Condomínio", last.

        Grouped in Python (not the ORM) since the input is already a small, fully-loaded list —
        one pass builds ordered groups without an extra query. Groups ordered by street_number
        asc; bills within a group already arrive due_date-ordered from ``_month_active_bills``.
        """
        by_building_id: dict[int, list[Bill]] = {}
        street_number_by_building_id: dict[int, int] = {}
        building_label_by_id: dict[int, str] = {}
        condominio_bills: list[Bill] = []
        for bill in month_bills:
            building = bill.building
            if building is None:
                condominio_bills.append(bill)
                continue
            by_building_id.setdefault(building.id, []).append(bill)
            street_number_by_building_id[building.id] = building.street_number
            building_label_by_id[building.id] = str(building.street_number)

        ordered_building_ids = sorted(
            by_building_id, key=lambda bid: street_number_by_building_id[bid]
        )
        groups: list[MonthBoardGroup] = [
            {
                "building_id": building_id,
                "building_label": building_label_by_id[building_id],
                "bills": _serialize_bills(by_building_id[building_id]),
            }
            for building_id in ordered_building_ids
        ]
        if condominio_bills:
            groups.append(
                {
                    "building_id": None,
                    "building_label": _CONDOMINIO_LABEL,
                    "bills": _serialize_bills(condominio_bills),
                }
            )
        return groups

    @staticmethod
    def _totals(month_bills: list[Bill], overdue_bills: list[Bill]) -> MonthBoardTotals:
        """due/paid/remaining = Σ of the month's groups; overdue = Σ resto of the overdue section.

        Sums the annotations already loaded by with_amounts() — never re-derived from line items.
        """
        due = sum((getattr(bill, "amount_total", _ZERO) for bill in month_bills), _ZERO)
        paid = sum((getattr(bill, "amount_paid", _ZERO) for bill in month_bills), _ZERO)
        remaining = sum((getattr(bill, "amount_remaining", _ZERO) for bill in month_bills), _ZERO)
        overdue_total = sum(
            (getattr(bill, "amount_remaining", _ZERO) for bill in overdue_bills), _ZERO
        )
        return {
            "due": money_str(due),
            "paid": money_str(paid),
            "remaining": money_str(remaining),
            "overdue": money_str(overdue_total),
        }

    @staticmethod
    def _missing_count(month_start: date) -> int:
        """Eligible recurring accounts (is_account_eligible) with no non-deleted Bill this month.

        "Non-deleted, any lifecycle" mirrors the get_or_create lookup the generator itself uses
        (bill_generation_service.py:141): the partial unique on (billing_account, competence_month,
        is_deleted=False) does not filter by lifecycle_state, so a SUSPENDED/CANCELED bill in the
        month already occupies that slot — generate_month would not create another one, so it must
        NOT count as missing (otherwise the banner would never zero out after generation).

        Batched to avoid an N+1: the BillSkip check inside is_account_eligible and the occupied-slot
        check are each preloaded ONCE (a skip_index set + an occupied billing_account_id set) instead
        of one query per account — same pattern as CondoProjectionService.project's skip_index
        preload (condo_projection_service.py:74-79).
        """
        skip_index: set[tuple[int, date]] = {
            (ba_id, ref_month)
            for ba_id, ref_month in BillSkip.objects.filter(
                reference_month=month_start
            ).values_list("billing_account_id", "reference_month")
        }
        occupied_account_ids: set[int] = set(
            Bill.all_objects.filter(
                billing_account__isnull=False, competence_month=month_start, is_deleted=False
            ).values_list("billing_account_id", flat=True)
        )
        missing = 0
        for account in BillingAccount.objects.recurring_for_generation():
            if not BillGenerationService.is_account_eligible(
                account, month_start, skip_index=skip_index
            ):
                continue
            if account.pk not in occupied_account_ids:
                missing += 1
        return missing
