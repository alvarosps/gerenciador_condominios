"""Finance dashboard endpoints: combined_calendar (uncached) + overdue (Session 38);
overview / monthly_balance / by_category (Session 45, cached on finance-dashboard)."""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from core.cache import cache_result
from core.permissions import FinancialReadOnly
from core.services.rent_schedule_service import RentScheduleService
from finances.cache import FINANCE_DASHBOARD_PREFIX, FINANCE_PROJECTION_PREFIX
from finances.models import (
    Bill,
    BillLifecycleState,
    BillLineItem,
    CondoMonthClose,
    CondoMonthCloseStatus,
)
from finances.money import money_str, quantize_money
from finances.serializers import BillSerializer
from finances.services.condo_balance_service import CondoBalanceService, _next_month
from finances.services.condo_calendar_service import CondoCalendarService
from finances.services.condo_projection_service import CondoProjectionService
from finances.services.condo_simulation_service import CondoSimulationService
from finances.services.iptu_alert_service import IptuAlertService
from finances.services.owner_distribution_service import OwnerDistributionService
from finances.services.timezone import current_month_sp, today_sp

MONTHS_IN_YEAR = 12
DEFAULT_PROJECTION_MONTHS = 12
MAX_PROJECTION_MONTHS = 36  # cap the fold loop (a what-if horizon, not an absurd 100-month run)
ZERO = Decimal(0)
ZERO_MONEY = Decimal("0.00")


def _parse_year_month_query(request: Request, current: date) -> tuple[int, int]:
    """Parse year/month query params (default to the current SP month); raise ValueError if bad."""
    year = int(request.query_params.get("year", current.year))
    month = int(request.query_params.get("month", current.month))
    if not (1 <= month <= MONTHS_IN_YEAR):
        raise ValueError
    return year, month


def _coerce_building_id(raw: str | int | None) -> int | None:
    """Coerce a raw building_id (query param or body) to int; 400 (PT) on a non-numeric value.

    Raises a DRF ValidationError so every caller fails closed with a 400 uniformly (no per-action
    try/except), instead of an unguarded int() ValueError escaping the action as a 500.
    """
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise DRFValidationError({"building_id": "Deve ser um número inteiro."}) from exc


def _building_id_param(request: Request) -> int | None:
    return _coerce_building_id(request.query_params.get("building_id"))


def _validated_months(raw: str | int | None) -> int:
    """Parse a projection-months value (default 12) clamped to [1, MAX]; raise ValueError if bad."""
    months = int(raw) if raw is not None else DEFAULT_PROJECTION_MONTHS
    if not (1 <= months <= MAX_PROJECTION_MONTHS):
        raise ValueError
    return months


# Distinct sub-prefixes per endpoint: cache_result keys on (prefix, *args) and ignores the
# function name when a prefix is set (core/cache.py), so overview and by_category — which share
# the (year, month, building_id) arg tuple — would otherwise collide on one key and serve each
# other's payload. All three still start with FINANCE_DASHBOARD_PREFIX, so
# invalidate_pattern("finance-dashboard*") (finances/cache.py) keeps clearing all of them.
_OVERVIEW_PREFIX = f"{FINANCE_DASHBOARD_PREFIX}-overview"
_MONTHLY_PREFIX = f"{FINANCE_DASHBOARD_PREFIX}-monthly"
_CATEGORY_PREFIX = f"{FINANCE_DASHBOARD_PREFIX}-category"


@cache_result(key_prefix=_OVERVIEW_PREFIX)
def _cached_overview(year: int, month: int, building_id: int | None) -> dict[str, Any]:
    return CondoBalanceService.overview(year, month, building_id)


@cache_result(key_prefix=_MONTHLY_PREFIX)
def _cached_monthly_balance(year: int, building_id: int | None) -> list[dict[str, Any]]:
    return _monthly_balance(year, building_id)


@cache_result(key_prefix=_CATEGORY_PREFIX)
def _cached_by_category(year: int, month: int, building_id: int | None) -> list[dict[str, Any]]:
    return _by_category(year, month, building_id)


_BY_OWNER_PREFIX = f"{FINANCE_DASHBOARD_PREFIX}-by-owner"


@cache_result(key_prefix=_BY_OWNER_PREFIX)
def _cached_by_owner(year: int, month: int, building_id: int | None) -> dict[str, Any]:
    return OwnerDistributionService.compute(year, month, building_id)


# Own sub-prefix under FINANCE_PROJECTION_PREFIX: cache_result keys on (prefix, *args) and ignores
# the function name (core/cache.py), so a distinct sub-prefix avoids colliding with any other
# finance-projection consumer while still matching invalidate_pattern("finance-projection*").
_PROJECTION_PREFIX = f"{FINANCE_PROJECTION_PREFIX}-cashflow"


@cache_result(key_prefix=_PROJECTION_PREFIX)
def _cached_projection(months: int, building_id: int | None) -> list[dict[str, Any]]:
    return CondoProjectionService.project(months, building_id)


def _monthly_balance(year: int, building_id: int | None) -> list[dict[str, Any]]:
    """12-month series: closed months read the frozen CondoMonthClose, open months compute on-read.

    Reserve and total_balance are CONDO-LEVEL (one Reserve per condominium); a per-building request
    reports them as None rather than mixing one building's cash with the whole-condo reserve.
    """
    condo_wide = building_id is None
    closes = {
        close.reference_month.month: close
        for close in CondoMonthClose.objects.filter(
            reference_month__year=year, status=CondoMonthCloseStatus.CLOSED
        )
    }
    rows: list[dict[str, Any]] = []
    for month in range(1, MONTHS_IN_YEAR + 1):
        close = closes.get(month)
        if close is not None:
            result = close.net_result
            cash_end = close.cash_balance_end
            reserve_end = close.reserve_balance_end if condo_wide else None
            cash_change = Decimal(str(close.breakdown.get("cash_change_of_month", "0.00")))
            is_closed = True
        else:
            result = CondoBalanceService.result_of_month(year, month, building_id)
            cash_change = CondoBalanceService.cash_change_of_month(year, month, building_id)
            cash_end = CondoBalanceService.cash_balance(
                _next_month(date(year, month, 1)), building_id
            )
            reserve_end = CondoBalanceService.reserve_balance() if condo_wide else None
            is_closed = False
        total = quantize_money(cash_end + reserve_end) if reserve_end is not None else None
        rows.append(
            {
                "month": month,
                "result_of_month": money_str(result),
                "cash_change_of_month": money_str(cash_change),
                "cash_balance_end": money_str(cash_end),
                "reserve_balance_end": money_str(reserve_end) if reserve_end is not None else None,
                "total_balance": money_str(total) if total is not None else None,
                "is_closed": is_closed,
            }
        )
    return rows


def _by_category(year: int, month: int, building_id: int | None) -> list[dict[str, Any]]:
    """Expense donut: Σ active-bill line net (non-offset - offset) grouped by the bill's category."""
    lines = BillLineItem.objects.filter(
        bill__competence_month=date(year, month, 1),
        bill__lifecycle_state=BillLifecycleState.ACTIVE,
        bill__is_deleted=False,
    )
    if building_id is not None:
        lines = lines.filter(bill__building_id=building_id)
    grouped = (
        lines.values("bill__category", "bill__category__name", "bill__category__color")
        .annotate(
            positive=Coalesce(Sum("amount", filter=Q(is_offset=False)), ZERO_MONEY),
            negative=Coalesce(Sum("amount", filter=Q(is_offset=True)), ZERO_MONEY),
        )
        .order_by("bill__category__name")
    )
    return [
        {
            "category_id": row["bill__category"],
            "name": row["bill__category__name"] or "Sem categoria",
            "color": row["bill__category__color"] or "",
            "total": money_str(row["positive"] - row["negative"]),
        }
        for row in grouped
    ]


class FinanceDashboardViewSet(viewsets.ViewSet):
    """Read-only dashboard for the condominium-finance calendar and overdue list."""

    permission_classes = [FinancialReadOnly]

    @action(detail=False, methods=["get"])
    def combined_calendar(self, request: Request) -> Response:
        # NO cache (design §11): the calendar has two halves (rent via core, bills via
        # finances) invalidated by different triggers, so a rent toggle would only
        # invalidate the rent side — caching here would serve a stale calendar.
        current = current_month_sp()
        try:
            year = int(request.query_params.get("year", current.year))
            month = int(request.query_params.get("month", current.month))
        except ValueError:
            return Response(
                {"error": "Os parâmetros year/month devem ser inteiros."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= month <= MONTHS_IN_YEAR):
            return Response(
                {"error": "O mês deve estar entre 1 e 12."}, status=status.HTTP_400_BAD_REQUEST
            )
        building_id = _building_id_param(request)
        data = CondoCalendarService.combined_month(year, month, building_id)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def overdue(self, request: Request) -> Response:
        building_id = _building_id_param(request)
        # is_overdue is a with_amounts annotation — pass it through a dict variable so the
        # django-stubs plugin does not reject the annotation name as an unknown field.
        overdue_lookup: dict[str, object] = {"is_overdue": True}
        bills_qs = (
            Bill.objects.with_amounts(today_sp())
            .filter(**overdue_lookup)
            .select_related("building", "category", "billing_account", "condominium")
            .prefetch_related("line_items", "allocations")
            .order_by("due_date")
        )
        if building_id is not None:
            bills_qs = bills_qs.filter(building_id=building_id)
        bills = list(bills_qs)

        overdue_total: Decimal = ZERO
        for bill in bills:
            overdue_total += getattr(bill, "amount_remaining", ZERO)

        # Rent overdue is a SEPARATE sub-total (not summed with bills) — design §4.4. as_of=today_sp()
        # keeps the rent overdue sub-block on São Paulo's date, consistent with the bills half.
        current = current_month_sp()
        rent_stats = RentScheduleService.get_month_stats(
            current.year, current.month, building_id, as_of=today_sp()
        )
        serializer = BillSerializer(bills, many=True, context={"request": request})
        return Response(
            {
                "bills": serializer.data,
                "overdue_bills_total": money_str(overdue_total),
                "overdue_bills_count": len(bills),
                "rent_overdue": {
                    "count": rent_stats["overdue_count"],
                    "total_fee": rent_stats["overdue_total_fee"],
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def iptu_alerts(self, request: Request) -> Response:
        # NO cache (design §11): depends on today_sp() + payment state; midnight rollover is not a
        # write, so cache would never be invalidated — same rationale as combined_calendar/overdue.
        rows = IptuAlertService.evaluate(today_sp())
        return Response(
            {
                "alerts": [
                    {
                        "plan_id": r.plan_id,
                        "external_identifier": r.external_identifier,
                        "building_label": r.building_label,
                        "level": r.level,
                        "overdue_count": r.overdue_count,
                        "deadline": r.deadline,
                        "overdue_due_dates": r.overdue_due_dates,
                        "message": r.message,
                    }
                    for r in rows
                ],
                "warning_count": sum(1 for r in rows if r.level == IptuAlertService.LEVEL_WARNING),
                "critical_count": sum(
                    1 for r in rows if r.level == IptuAlertService.LEVEL_CRITICAL
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def overview(self, request: Request) -> Response:
        try:
            year, month = _parse_year_month_query(request, current_month_sp())
        except ValueError:
            return Response(
                {"error": "Parâmetros year/month inválidos (mês entre 1 e 12)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = _cached_overview(year, month, _building_id_param(request))
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def monthly_balance(self, request: Request) -> Response:
        try:
            year = int(request.query_params.get("year", current_month_sp().year))
        except ValueError:
            return Response(
                {"error": "Parâmetro year inválido."}, status=status.HTTP_400_BAD_REQUEST
            )
        data = _cached_monthly_balance(year, _building_id_param(request))
        return Response({"year": year, "months": data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def by_category(self, request: Request) -> Response:
        try:
            year, month = _parse_year_month_query(request, current_month_sp())
        except ValueError:
            return Response(
                {"error": "Parâmetros year/month inválidos (mês entre 1 e 12)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = _cached_by_category(year, month, _building_id_param(request))
        return Response(
            {"year": year, "month": month, "categories": data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"])
    def by_owner(self, request: Request) -> Response:
        try:
            year, month = _parse_year_month_query(request, current_month_sp())
            building_id = _building_id_param(request)
        except ValueError:
            return Response(
                {"error": "Parâmetros year/month/building_id inválidos (mês entre 1 e 12)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = _cached_by_owner(year, month, building_id)
        return Response(data, status=status.HTTP_200_OK)


class FinanceCashFlowViewSet(viewsets.ViewSet):
    """Read-only cash-flow projection + ephemeral what-if simulation (Session 47).

    GET projection is cached (finance-projection, invalidated by any finances write); POST simulate
    is never cached (depends on the body and is ephemeral). FinancialReadOnly: any authenticated
    user reads the projection; only is_staff may POST a simulation.
    """

    permission_classes = [FinancialReadOnly]

    @action(detail=False, methods=["get"])
    def projection(self, request: Request) -> Response:
        try:
            months = _validated_months(request.query_params.get("months"))
        except ValueError:
            return Response(
                {
                    "error": f"O parâmetro 'months' deve ser um inteiro entre 1 e {MAX_PROJECTION_MONTHS}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # _building_id_param raises a DRF ValidationError (-> 400) on a malformed value.
        data = _cached_projection(months, _building_id_param(request))
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def simulate(self, request: Request) -> Response:
        scenarios = request.data.get("scenarios")
        if not isinstance(scenarios, list) or len(scenarios) == 0:
            return Response(
                {"error": "O campo 'scenarios' é obrigatório e deve ser uma lista não vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        errors = CondoSimulationService.validate_scenarios(scenarios)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            months = _validated_months(request.data.get("months"))
            building_id = _coerce_building_id(request.data.get("building_id"))
        except (ValueError, TypeError):
            return Response(
                {
                    "error": f"Parâmetros 'months' (1 a {MAX_PROJECTION_MONTHS}) / 'building_id' inválidos."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        base = CondoProjectionService.project(months, building_id)
        simulated = CondoSimulationService.simulate(base, scenarios)
        comparison = CondoSimulationService.compare(base, simulated)
        return Response(
            {"base": base, "simulated": simulated, "comparison": comparison},
            status=status.HTTP_200_OK,
        )
