"""Financial ViewSets for simple CRUD endpoints."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import CreditCard, ExpenseCategory, FinancialSettings, Person
from core.permissions import IsAdminUser, ReadOnlyForNonAdmin
from core.serializers import (
    CreditCardSerializer,
    ExpenseCategorySerializer,
    FinancialSettingsSerializer,
    PersonSerializer,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request

logger = logging.getLogger(__name__)


class PersonViewSet(viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    permission_classes = [ReadOnlyForNonAdmin]

    def get_queryset(self) -> QuerySet[Person]:
        queryset = Person.objects.prefetch_related("credit_cards").all()
        is_owner = self.request.query_params.get("is_owner")
        is_employee = self.request.query_params.get("is_employee")
        search = self.request.query_params.get("search")

        if is_owner is not None:
            queryset = queryset.filter(is_owner=is_owner.lower() == "true")
        if is_employee is not None:
            queryset = queryset.filter(is_employee=is_employee.lower() == "true")
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset


class CreditCardViewSet(viewsets.ModelViewSet):
    serializer_class = CreditCardSerializer
    permission_classes = [ReadOnlyForNonAdmin]

    def get_queryset(self) -> QuerySet[CreditCard]:
        queryset = CreditCard.objects.select_related("person").all()
        person_id = self.request.query_params.get("person_id")
        is_active = self.request.query_params.get("is_active")

        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [ReadOnlyForNonAdmin]


class FinancialSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["get", "put", "patch"], url_path="current")
    def current(self, request: Request) -> Response:
        if request.method == "GET":
            settings_obj, created = FinancialSettings.objects.get_or_create(
                pk=1,
                defaults={
                    "initial_balance": 0,
                    "initial_balance_date": date.today(),
                },
            )
            if created:
                logger.info("FinancialSettings created with defaults")

            serializer = FinancialSettingsSerializer(settings_obj)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # PUT or PATCH
        try:
            settings_obj = FinancialSettings.objects.get(pk=1)
        except FinancialSettings.DoesNotExist:
            settings_obj = FinancialSettings(pk=1, initial_balance_date=date.today())

        serializer = FinancialSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=(request.method == "PATCH"),
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            logger.info("FinancialSettings updated")
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
