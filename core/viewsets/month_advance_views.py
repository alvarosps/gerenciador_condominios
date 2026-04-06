"""ViewSet for month advancement operations."""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import MonthSnapshot
from core.services.month_advance_service import MonthAdvanceService


class MonthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthSnapshot
        fields = [
            "id",
            "reference_month",
            "total_income",
            "total_expenses",
            "net_balance",
            "cumulative_ending_balance",
            "total_rent_income",
            "total_extra_income",
            "total_person_payments_received",
            "total_card_installments",
            "total_loan_installments",
            "total_utility_bills",
            "total_fixed_expenses",
            "total_one_time_expenses",
            "total_employee_salary",
            "total_owner_repayments",
            "total_person_stipends",
            "total_debt_installments",
            "total_property_tax",
            "is_finalized",
            "finalized_at",
            "detailed_breakdown",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class MonthAdvanceViewSet(viewsets.ViewSet):
    """
    Endpoints for month advancement pipeline.

    POST /advance/     — Advance (close) a month
    POST /rollback/    — Rollback the last finalized month
    GET  /status/      — Check month status and validation
    GET  /snapshots/   — List all snapshots
    GET  /snapshots/{year}/{month}/ — Get specific snapshot
    GET  /preview/     — Preview next month without advancing
    """

    permission_classes = [IsAdminUser]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.service = MonthAdvanceService()

    @action(detail=False, methods=["post"])
    def advance(self, request: Request) -> Response:
        """Advance (close) a month."""
        year = request.data.get("year")
        month = request.data.get("month")
        force = request.data.get("force", False)
        notes = request.data.get("notes", "")

        if not year or not month:
            return Response(
                {"error": "year and month are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self.service.advance_month(
                int(year), int(month), force=bool(force), notes=str(notes)
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def rollback(self, request: Request) -> Response:
        """Rollback the last finalized month."""
        year = request.data.get("year")
        month = request.data.get("month")
        confirm = request.data.get("confirm", False)

        if not year or not month:
            return Response(
                {"error": "year and month are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self.service.rollback_month(int(year), int(month), confirm=bool(confirm))
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def get_status(self, request: Request) -> Response:
        """Check month status and validation."""
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response(
                {"error": "year and month query params are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.service.get_status(int(year), int(month))
        return Response(result)

    @action(detail=False, methods=["get"])
    def snapshots(self, request: Request) -> Response:
        """List all snapshots, optionally filtered by year."""
        year = request.query_params.get("year")
        qs = MonthSnapshot.objects.all()
        if year:
            qs = qs.filter(reference_month__year=int(year))
        serializer = MonthSnapshotSerializer(qs, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="snapshots/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})",
    )
    def snapshot_detail(self, request: Request, year: str = "", month: str = "") -> Response:
        """Get specific month snapshot."""
        reference_month = f"{year}-{int(month):02d}-01"
        try:
            snapshot = MonthSnapshot.objects.get(reference_month=reference_month)
        except MonthSnapshot.DoesNotExist:
            return Response(
                {"error": "Snapshot not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MonthSnapshotSerializer(snapshot)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def preview(self, request: Request) -> Response:
        """Preview next month without advancing."""
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response(
                {"error": "year and month query params are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.service.get_next_month_preview(int(year), int(month))
        return Response(result)
