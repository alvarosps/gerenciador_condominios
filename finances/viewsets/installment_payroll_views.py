"""CRUD viewsets + convert_deferred action for installments/payroll (Session 42).

ModelViewSet + IsAdminUser + CustomPageNumberPagination. Thin actions: they
parse/validate request data (400 PT) and delegate to the Session 41 services
(InstallmentPlanService.convert_deferred). No business logic here.
"""

from datetime import date
from decimal import InvalidOperation
from typing import cast

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.pagination import CustomPageNumberPagination
from core.permissions import IsAdminUser
from finances.models import Bill, Category, Employee, Installment, InstallmentPlan
from finances.serializers import (
    EmployeeSerializer,
    InstallmentPlanSerializer,
    InstallmentSerializer,
)
from finances.services.installment_plan_service import InstallmentPlanService
from finances.viewsets.query_params import date_param, int_param


class InstallmentPlanViewSet(viewsets.ModelViewSet):
    serializer_class = InstallmentPlanSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[InstallmentPlan]:
        queryset = InstallmentPlan.objects.select_related(
            "category", "building", "billing_account", "condominium"
        ).prefetch_related("installments")
        params = self.request.query_params
        condominium_id = int_param(params, "condominium_id")
        if condominium_id is not None:
            queryset = queryset.filter(condominium_id=condominium_id)
        building_id = int_param(params, "building_id")
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        category_id = int_param(params, "category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        lifecycle_state = params.get("lifecycle_state")
        if lifecycle_state is not None:
            queryset = queryset.filter(lifecycle_state=lifecycle_state)
        embedded = params.get("embedded")
        if embedded is not None:
            queryset = queryset.filter(embedded=embedded.lower() == "true")
        return queryset

    @action(detail=False, methods=["post"])
    def convert_deferred(self, request: Request) -> Response:
        """Convert a deferred Bill into a standalone InstallmentPlan (delegates to S41)."""
        data = request.data
        bill_id = data.get("bill_id")
        installment_count_raw = data.get("installment_count")
        start_due_date_raw = data.get("start_due_date")
        default_due_day_raw = data.get("default_due_day")
        if (
            not bill_id
            or installment_count_raw is None
            or not start_due_date_raw
            or default_due_day_raw is None
        ):
            return Response(
                {
                    "error": "Campos bill_id, installment_count, start_due_date e "
                    "default_due_day são obrigatórios."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            installment_count = int(installment_count_raw)
            default_due_day = int(default_due_day_raw)
            start_due_date = date.fromisoformat(str(start_due_date_raw))
            deferred_bill = Bill.objects.get(pk=int(bill_id))
            category_id = data.get("category_id")
            category = (
                Category.objects.get(pk=int(category_id)) if category_id is not None else None
            )
            plan = InstallmentPlanService.convert_deferred(
                deferred_bill=deferred_bill,
                installment_count=installment_count,
                start_due_date=start_due_date,
                default_due_day=default_due_day,
                category=category,
                user=cast(User, request.user),
            )
        except (ValueError, InvalidOperation):
            return Response({"error": "Parâmetros inválidos."}, status=status.HTTP_400_BAD_REQUEST)
        except Bill.DoesNotExist:
            return Response(
                {"error": "Conta adiada não encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        except Category.DoesNotExist:
            return Response(
                {"error": "Categoria não encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InstallmentViewSet(viewsets.ModelViewSet):
    """Read + PATCH of the schedule (amount/due_date). Installments are materialized by the
    plan/generation (S41), so create/destroy are not exposed (only GET/PATCH)."""

    serializer_class = InstallmentSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomPageNumberPagination
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self) -> QuerySet[Installment]:
        queryset = Installment.objects.select_related("plan", "plan__category")
        params = self.request.query_params
        plan_id = int_param(params, "plan_id")
        if plan_id is not None:
            queryset = queryset.filter(plan_id=plan_id)
        due_date_from = date_param(params, "due_date_from")
        if due_date_from is not None:
            queryset = queryset.filter(due_date__gte=due_date_from)
        due_date_to = date_param(params, "due_date_to")
        if due_date_to is not None:
            queryset = queryset.filter(due_date__lte=due_date_to)
        return queryset


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[Employee]:
        queryset = Employee.objects.select_related(
            "person", "lease", "lease__apartment", "lease__apartment__building", "condominium"
        )
        params = self.request.query_params
        condominium_id = int_param(params, "condominium_id")
        if condominium_id is not None:
            queryset = queryset.filter(condominium_id=condominium_id)
        is_active = params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        payment_type = params.get("payment_type")
        if payment_type is not None:
            queryset = queryset.filter(payment_type=payment_type)
        person_id = int_param(params, "person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)
        lease_id = int_param(params, "lease_id")
        if lease_id is not None:
            queryset = queryset.filter(lease_id=lease_id)
        return queryset
