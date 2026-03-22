"""Financial ViewSets for CRUD endpoints."""

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import (
    CreditCard,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    FinancialSettings,
    Income,
    Person,
    PersonIncome,
    PersonPayment,
    RentPayment,
)
from core.permissions import FinancialReadOnly
from core.serializers import (
    CreditCardSerializer,
    EmployeePaymentSerializer,
    ExpenseCategorySerializer,
    ExpenseInstallmentSerializer,
    ExpenseSerializer,
    FinancialSettingsSerializer,
    IncomeSerializer,
    PersonIncomeSerializer,
    PersonPaymentSerializer,
    PersonSerializer,
    RentPaymentSerializer,
)

logger = logging.getLogger(__name__)


class PersonViewSet(viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    permission_classes = [FinancialReadOnly]

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
    permission_classes = [FinancialReadOnly]

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
    permission_classes = [FinancialReadOnly]


class FinancialSettingsViewSet(viewsets.ViewSet):
    permission_classes = [FinancialReadOnly]

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


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[Expense]:
        queryset = Expense.objects.select_related(
            "person", "credit_card", "building", "category"
        ).prefetch_related("installments")

        params = self.request.query_params

        person_id = params.get("person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)

        credit_card_id = params.get("credit_card_id")
        if credit_card_id is not None:
            queryset = queryset.filter(credit_card_id=credit_card_id)

        expense_type = params.get("expense_type")
        if expense_type is not None:
            queryset = queryset.filter(expense_type=expense_type)

        category_id = params.get("category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)

        building_id = params.get("building_id")
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)

        is_paid = params.get("is_paid")
        if is_paid is not None:
            queryset = queryset.filter(is_paid=is_paid.lower() == "true")

        is_installment = params.get("is_installment")
        if is_installment is not None:
            queryset = queryset.filter(is_installment=is_installment.lower() == "true")

        is_recurring = params.get("is_recurring")
        if is_recurring is not None:
            queryset = queryset.filter(is_recurring=is_recurring.lower() == "true")

        is_debt_installment = params.get("is_debt_installment")
        if is_debt_installment is not None:
            queryset = queryset.filter(is_debt_installment=is_debt_installment.lower() == "true")

        is_offset = params.get("is_offset")
        if is_offset is not None:
            queryset = queryset.filter(is_offset=is_offset.lower() == "true")

        date_from = params.get("date_from")
        if date_from is not None:
            queryset = queryset.filter(expense_date__gte=date_from)

        date_to = params.get("date_to")
        if date_to is not None:
            queryset = queryset.filter(expense_date__lte=date_to)

        return queryset

    @action(detail=True, methods=["post"])
    def mark_paid(self, request: Request, pk: str | None = None) -> Response:
        expense = self.get_object()
        paid_date = request.data.get("paid_date", date.today())
        expense.is_paid = True
        expense.paid_date = paid_date
        expense.save(update_fields=["is_paid", "paid_date", "updated_at"])
        serializer = self.get_serializer(expense)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def generate_installments(self, request: Request, pk: str | None = None) -> Response:
        expense = self.get_object()

        if not expense.is_installment or not expense.total_installments:
            return Response(
                {"error": "Despesa não é parcelada ou não tem total de parcelas definido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if expense.installments.exists():
            return Response(
                {"error": "Parcelas já foram geradas para esta despesa."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date_str = request.data.get("start_date")
        start_date = date.fromisoformat(start_date_str) if start_date_str else expense.expense_date

        installment_amount = (Decimal(expense.total_amount) / expense.total_installments).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        has_credit_card = expense.credit_card_id is not None

        installments = []
        for i in range(1, expense.total_installments + 1):
            if has_credit_card:
                due_date = (start_date + relativedelta(months=i - 1)).replace(
                    day=expense.credit_card.due_day
                )
            else:
                due_date = start_date + relativedelta(months=i - 1)

            installments.append(
                ExpenseInstallment(
                    expense=expense,
                    installment_number=i,
                    total_installments=expense.total_installments,
                    amount=installment_amount,
                    due_date=due_date,
                    created_by=request.user,
                    updated_by=request.user,
                )
            )

        ExpenseInstallment.objects.bulk_create(installments)
        expense = self.get_queryset().get(pk=expense.pk)
        serializer = self.get_serializer(expense)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExpenseInstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseInstallmentSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[ExpenseInstallment]:
        queryset = ExpenseInstallment.objects.select_related(
            "expense", "expense__person", "expense__credit_card"
        )

        params = self.request.query_params

        expense_id = params.get("expense_id")
        if expense_id is not None:
            queryset = queryset.filter(expense_id=expense_id)

        is_paid = params.get("is_paid")
        if is_paid is not None:
            queryset = queryset.filter(is_paid=is_paid.lower() == "true")

        is_overdue = params.get("is_overdue")
        if is_overdue is not None and is_overdue.lower() == "true":
            queryset = queryset.filter(is_paid=False, due_date__lt=date.today())

        due_date_from = params.get("due_date_from")
        if due_date_from is not None:
            queryset = queryset.filter(due_date__gte=due_date_from)

        due_date_to = params.get("due_date_to")
        if due_date_to is not None:
            queryset = queryset.filter(due_date__lte=due_date_to)

        person_id = params.get("person_id")
        if person_id is not None:
            queryset = queryset.filter(expense__person_id=person_id)

        credit_card_id = params.get("credit_card_id")
        if credit_card_id is not None:
            queryset = queryset.filter(expense__credit_card_id=credit_card_id)

        return queryset

    def _check_and_complete_expense(self, expense: Expense) -> None:
        """If all installments are paid, mark the expense as paid too."""
        if not expense.installments.filter(is_paid=False).exists():
            expense.is_paid = True
            expense.paid_date = date.today()
            expense.save(update_fields=["is_paid", "paid_date", "updated_at"])

    @action(detail=True, methods=["post"])
    def mark_paid(self, request: Request, pk: str | None = None) -> Response:
        installment = self.get_object()
        paid_date = request.data.get("paid_date", date.today())
        installment.is_paid = True
        installment.paid_date = paid_date
        installment.save(update_fields=["is_paid", "paid_date", "updated_at"])

        self._check_and_complete_expense(installment.expense)

        serializer = self.get_serializer(installment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def bulk_mark_paid(self, request: Request) -> Response:
        installment_ids = request.data.get("installment_ids", [])
        paid_date = request.data.get("paid_date", date.today())

        if not installment_ids:
            return Response(
                {"error": "Lista de parcelas vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        installments = ExpenseInstallment.objects.filter(pk__in=installment_ids)
        if installments.count() != len(installment_ids):
            return Response(
                {"error": "Uma ou mais parcelas não foram encontradas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        installments.update(is_paid=True, paid_date=paid_date)

        affected_expense_ids = set(installments.values_list("expense_id", flat=True))
        for expense in Expense.objects.filter(pk__in=affected_expense_ids):
            self._check_and_complete_expense(expense)

        updated_installments = ExpenseInstallment.objects.filter(pk__in=installment_ids)
        serializer = self.get_serializer(updated_installments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IncomeViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[Income]:
        queryset = Income.objects.select_related("person", "building", "category")

        params = self.request.query_params

        person_id = params.get("person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)

        building_id = params.get("building_id")
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)

        category_id = params.get("category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)

        is_recurring = params.get("is_recurring")
        if is_recurring is not None:
            queryset = queryset.filter(is_recurring=is_recurring.lower() == "true")

        is_received = params.get("is_received")
        if is_received is not None:
            queryset = queryset.filter(is_received=is_received.lower() == "true")

        date_from = params.get("date_from")
        if date_from is not None:
            queryset = queryset.filter(income_date__gte=date_from)

        date_to = params.get("date_to")
        if date_to is not None:
            queryset = queryset.filter(income_date__lte=date_to)

        return queryset

    @action(detail=True, methods=["post"])
    def mark_received(self, request: Request, pk: str | None = None) -> Response:
        income = self.get_object()
        received_date = request.data.get("received_date", date.today())
        income.is_received = True
        income.received_date = received_date
        income.save(update_fields=["is_received", "received_date", "updated_at"])
        serializer = self.get_serializer(income)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RentPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = RentPaymentSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[RentPayment]:
        queryset = RentPayment.objects.select_related(
            "lease", "lease__apartment", "lease__apartment__building", "lease__responsible_tenant"
        )

        params = self.request.query_params

        lease_id = params.get("lease_id")
        if lease_id is not None:
            queryset = queryset.filter(lease_id=lease_id)

        apartment_id = params.get("apartment_id")
        if apartment_id is not None:
            queryset = queryset.filter(lease__apartment_id=apartment_id)

        building_id = params.get("building_id")
        if building_id is not None:
            queryset = queryset.filter(lease__apartment__building_id=building_id)

        reference_month = params.get("reference_month")
        if reference_month is not None:
            queryset = queryset.filter(reference_month=reference_month)

        month_from = params.get("month_from")
        if month_from is not None:
            queryset = queryset.filter(reference_month__gte=month_from)

        month_to = params.get("month_to")
        if month_to is not None:
            queryset = queryset.filter(reference_month__lte=month_to)

        payment_date_from = params.get("payment_date_from")
        if payment_date_from is not None:
            queryset = queryset.filter(payment_date__gte=payment_date_from)

        payment_date_to = params.get("payment_date_to")
        if payment_date_to is not None:
            queryset = queryset.filter(payment_date__lte=payment_date_to)

        return queryset


class EmployeePaymentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeePaymentSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[EmployeePayment]:
        queryset = EmployeePayment.objects.select_related("person")

        params = self.request.query_params

        person_id = params.get("person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)

        reference_month = params.get("reference_month")
        if reference_month is not None:
            queryset = queryset.filter(reference_month=reference_month)

        is_paid = params.get("is_paid")
        if is_paid is not None:
            queryset = queryset.filter(is_paid=is_paid.lower() == "true")

        month_from = params.get("month_from")
        if month_from is not None:
            queryset = queryset.filter(reference_month__gte=month_from)

        month_to = params.get("month_to")
        if month_to is not None:
            queryset = queryset.filter(reference_month__lte=month_to)

        return queryset

    @action(detail=True, methods=["post"])
    def mark_paid(self, request: Request, pk: str | None = None) -> Response:
        payment = self.get_object()
        payment_date = request.data.get("payment_date", date.today())
        payment.is_paid = True
        payment.payment_date = payment_date
        payment.save(update_fields=["is_paid", "payment_date", "updated_at"])
        serializer = self.get_serializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PersonIncomeViewSet(viewsets.ModelViewSet):
    serializer_class = PersonIncomeSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[PersonIncome]:
        queryset = PersonIncome.objects.select_related("person", "apartment", "apartment__building")

        params = self.request.query_params

        person_id = params.get("person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)

        income_type = params.get("income_type")
        if income_type is not None:
            queryset = queryset.filter(income_type=income_type)

        is_active = params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        apartment_id = params.get("apartment_id")
        if apartment_id is not None:
            queryset = queryset.filter(apartment_id=apartment_id)

        return queryset


class PersonPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PersonPaymentSerializer
    permission_classes = [FinancialReadOnly]

    def get_queryset(self) -> QuerySet[PersonPayment]:
        queryset = PersonPayment.objects.select_related("person")

        params = self.request.query_params

        person_id = params.get("person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)

        reference_month = params.get("reference_month")
        if reference_month is not None:
            queryset = queryset.filter(reference_month=reference_month)

        month_from = params.get("month_from")
        if month_from is not None:
            queryset = queryset.filter(reference_month__gte=month_from)

        month_to = params.get("month_to")
        if month_to is not None:
            queryset = queryset.filter(reference_month__lte=month_to)

        return queryset
