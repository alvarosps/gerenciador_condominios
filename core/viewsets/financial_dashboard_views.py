"""Financial dashboard, cash flow, and daily control ViewSets."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import Person, PersonPayment
from core.services.cash_flow_service import MONTHS_IN_YEAR, CashFlowService
from core.services.daily_control_service import DailyControlService
from core.services.financial_dashboard_service import FinancialDashboardService
from core.services.simulation_service import SimulationService

_DEFAULT_UPCOMING_DAYS = 30
_DEFAULT_PROJECTION_MONTHS = 12


class FinancialDashboardViewSet(viewsets.ViewSet):
    """Read-only ViewSet exposing FinancialDashboardService aggregations."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def overview(self, request: Request) -> Response:
        data = FinancialDashboardService.get_overview()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def debt_by_person(self, request: Request) -> Response:
        data = FinancialDashboardService.get_debt_by_person()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def debt_by_type(self, request: Request) -> Response:
        data = FinancialDashboardService.get_debt_by_type()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def upcoming_installments(self, request: Request) -> Response:
        try:
            days = int(request.query_params.get("days", _DEFAULT_UPCOMING_DAYS))
        except ValueError:
            return Response(
                {"error": "O parâmetro 'days' deve ser um inteiro válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = FinancialDashboardService.get_upcoming_installments(days=days)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def overdue_installments(self, request: Request) -> Response:
        data = FinancialDashboardService.get_overdue_installments()
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def category_breakdown(self, request: Request) -> Response:
        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' devem ser inteiros válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = FinancialDashboardService.get_expense_category_breakdown(year=year, month=month)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="dashboard_summary")
    def dashboard_summary(self, request: Request) -> Response:
        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' devem ser inteiros válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = FinancialDashboardService.get_dashboard_summary(year=year, month=month)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="expense_detail")
    def expense_detail(self, request: Request) -> Response:
        detail_type = request.query_params.get("type")
        if not detail_type:
            return Response(
                {"error": "O parâmetro 'type' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        detail_id_str = request.query_params.get("id")
        detail_id = int(detail_id_str) if detail_id_str else None

        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' devem ser inteiros válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = FinancialDashboardService.get_expense_detail(detail_type, detail_id, year, month)
        except (Person.DoesNotExist, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data, status=status.HTTP_200_OK)


class CashFlowViewSet(viewsets.ViewSet):
    """ViewSet for cash flow calculation and simulation endpoints."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def monthly(self, request: Request) -> Response:
        year_str = request.query_params.get("year")
        month_str = request.query_params.get("month")

        if year_str is None or month_str is None:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' devem ser inteiros."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= month <= MONTHS_IN_YEAR):
            return Response(
                {"error": "O parâmetro 'month' deve estar entre 1 e 12."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = CashFlowService.get_monthly_cash_flow(year, month)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def projection(self, request: Request) -> Response:
        months_str = request.query_params.get("months", str(_DEFAULT_PROJECTION_MONTHS))

        try:
            months = int(months_str)
        except ValueError:
            return Response(
                {"error": "O parâmetro 'months' deve ser um inteiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if months < 1:
            return Response(
                {"error": "O parâmetro 'months' deve ser maior que zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = CashFlowService.get_cash_flow_projection(months)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="person_summary")
    def person_summary(self, request: Request) -> Response:
        person_id_str = request.query_params.get("person_id")
        year_str = request.query_params.get("year")
        month_str = request.query_params.get("month")

        if person_id_str is None:
            return Response(
                {"error": "O parâmetro 'person_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if year_str is None or month_str is None:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            person_id = int(person_id_str)
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'person_id', 'year' e 'month' devem ser inteiros."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = CashFlowService.get_person_summary(person_id, year, month)
        except Person.DoesNotExist:
            return Response(
                {"error": "Pessoa não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def simulate(self, request: Request) -> Response:
        scenarios = request.data.get("scenarios")

        if not isinstance(scenarios, list) or len(scenarios) == 0:
            return Response(
                {"error": "O campo 'scenarios' é obrigatório e deve ser uma lista não vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = SimulationService.validate_scenarios(scenarios)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        base = CashFlowService.get_cash_flow_projection(_DEFAULT_PROJECTION_MONTHS)
        simulated = SimulationService.simulate_from_db(base, scenarios)
        comparison = SimulationService.compare(base, simulated)

        return Response(
            {"base": base, "simulated": simulated, "comparison": comparison},
            status=status.HTTP_200_OK,
        )


class DailyControlViewSet(viewsets.ViewSet):
    """ViewSet for daily financial control — breakdown, summary, and mark-paid."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def breakdown(self, request: Request) -> Response:
        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' devem ser inteiros válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= month <= MONTHS_IN_YEAR):
            return Response(
                {"error": "O parâmetro 'month' deve estar entre 1 e 12."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = DailyControlService.get_daily_breakdown(year, month)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
        except ValueError:
            return Response(
                {"error": "Os parâmetros 'year' e 'month' devem ser inteiros válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= month <= MONTHS_IN_YEAR):
            return Response(
                {"error": "O parâmetro 'month' deve estar entre 1 e 12."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = DailyControlService.get_month_summary(year, month)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def mark_paid(self, request: Request) -> Response:
        error = self._validate_mark_paid_base(request)
        if error:
            return error

        item_type = str(request.data.get("item_type"))
        payment_date = date.fromisoformat(str(request.data.get("payment_date")))

        if item_type == "person_schedule":
            return self._mark_person_schedule_paid(request, payment_date)

        return self._mark_standard_item_paid(request, item_type, payment_date)

    def _validate_mark_paid_base(self, request: Request) -> Response | None:
        """Validate common mark_paid fields. Returns an error Response or None."""
        item_type = request.data.get("item_type")
        payment_date_str = request.data.get("payment_date")

        if not item_type:
            return Response(
                {"error": "O campo 'item_type' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payment_date_str:
            return Response(
                {"error": "O campo 'payment_date' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            date.fromisoformat(str(payment_date_str))
        except ValueError:
            return Response(
                {"error": "O campo 'payment_date' deve estar no formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    def _mark_standard_item_paid(
        self, request: Request, item_type: str, payment_date: date
    ) -> Response:
        """Mark a standard item (installment, expense, income, credit_card) as paid."""
        item_id = request.data.get("item_id")
        if not item_id:
            return Response(
                {"error": "O campo 'item_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item_id_int = int(item_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "O campo 'item_id' deve ser um inteiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = DailyControlService.mark_item_paid(item_type, item_id_int, payment_date)
        except ObjectDoesNotExist as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)

    def _mark_person_schedule_paid(self, request: Request, payment_date: date) -> Response:
        person_id_val = request.data.get("person_id")
        amount_val = request.data.get("amount")
        year_val = request.data.get("year")
        month_val = request.data.get("month")

        if not person_id_val or amount_val is None or not year_val or not month_val:
            return Response(
                {
                    "error": "Os campos 'person_id', 'amount', 'year' e 'month' são obrigatórios para person_schedule."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            person_id = int(person_id_val)
            year = int(year_val)
            month = int(month_val)
            amount = Decimal(str(amount_val))
        except (ValueError, TypeError, InvalidOperation):
            return Response(
                {
                    "error": "Parâmetros inválidos: 'person_id', 'year' e 'month' devem ser inteiros e 'amount' decimal."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return Response({"error": "Pessoa não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        reference_month = date(year, month, 1)
        PersonPayment.objects.create(
            person=person,
            reference_month=reference_month,
            amount=amount,
            payment_date=payment_date,
        )
        return Response(
            {"status": "ok", "message": f"Pagamento de R${amount} registrado para {person.name}."},
            status=status.HTTP_200_OK,
        )
