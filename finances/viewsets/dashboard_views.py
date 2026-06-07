"""Finance dashboard endpoints (Session 38): combined_calendar (uncached) + overdue."""

from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import FinancialReadOnly
from core.services.rent_schedule_service import RentScheduleService
from finances.models import Bill
from finances.money import money_str
from finances.serializers import BillSerializer
from finances.services.condo_calendar_service import CondoCalendarService
from finances.services.timezone import current_month_sp, today_sp

MONTHS_IN_YEAR = 12
ZERO = Decimal(0)


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
        building_id_raw = request.query_params.get("building_id")
        building_id = int(building_id_raw) if building_id_raw is not None else None
        data = CondoCalendarService.combined_month(year, month, building_id)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def overdue(self, request: Request) -> Response:
        building_id_raw = request.query_params.get("building_id")
        building_id = int(building_id_raw) if building_id_raw is not None else None
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

        # Rent overdue is a SEPARATE sub-total (not summed with bills) — design §4.4.
        current = current_month_sp()
        rent_stats = RentScheduleService.get_month_stats(current.year, current.month, building_id)
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
