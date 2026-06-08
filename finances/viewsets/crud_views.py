"""CRUD viewsets + Bill actions for the finances API (Session 38).

ModelViewSet + FinancialReadOnly + CustomPageNumberPagination. Bill amount_* read from
the with_amounts(today) annotation (TZ-SP today). Actions are thin: they parse/validate
request data (400 PT) and delegate to the S37/S38 services.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.http import QueryDict
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.pagination import CustomPageNumberPagination
from core.permissions import FinancialReadOnly
from finances.models import (
    Bill,
    BillingAccount,
    BillLifecycleState,
    BillSkip,
    Category,
    CondoMonthClose,
    FundedFrom,
    IncomeEntry,
    Installment,
    Payment,
    Reserve,
    ReserveMovement,
)
from finances.serializers import (
    BillingAccountSerializer,
    BillSerializer,
    BillSkipSerializer,
    CategorySerializer,
    CondoMonthCloseSerializer,
    IncomeEntrySerializer,
    PaymentSerializer,
    ReserveMovementSerializer,
    ReserveSerializer,
)
from finances.services.bill_generation_service import BillGenerationService
from finances.services.bill_lifecycle_service import BillLifecycleService
from finances.services.bill_payment_service import BillPaymentService
from finances.services.bill_service import (
    BillDraft,
    BillLineInput,
    BillService,
    StatementInput,
)
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.reserve_service import ReserveService
from finances.services.timezone import today_sp
from finances.viewsets.query_params import int_param

MONTHS_IN_YEAR = 12


def _parse_year_month(data: dict[str, object]) -> tuple[int, int]:
    """Parse year/month from request data; raise ValueError (-> 400) when invalid."""
    year = int(cast(str, data["year"]))
    month = int(cast(str, data["month"]))
    if not (1 <= month <= MONTHS_IN_YEAR):
        raise ValueError  # caller maps this to a 400 with a user-facing message
    return year, month


def _validated_funded_from(raw: object) -> str:
    """funded_from coerced to a known FundedFrom value; raise ValueError (-> 400) otherwise.

    Without this an arbitrary string is persisted verbatim (CharField choices are not DB-enforced
    and .create() skips full_clean), silently behaving as 'caixa' while polluting the funded_from
    filter — so validate it at the action boundary for both pay and bulk_pay (DRY).
    """
    value = str(raw)
    if value not in FundedFrom.values:
        raise ValueError
    return value


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[Category]:
        queryset = Category.objects.select_related("parent", "condominium")
        params = self.request.query_params
        parent_id = int_param(params, "parent_id")
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)
        condominium_id = int_param(params, "condominium_id")
        if condominium_id is not None:
            queryset = queryset.filter(condominium_id=condominium_id)
        return queryset


class BillingAccountViewSet(viewsets.ModelViewSet):
    serializer_class = BillingAccountSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[BillingAccount]:
        queryset = BillingAccount.objects.select_related("building", "category", "condominium")
        params = self.request.query_params
        building_id = int_param(params, "building_id")
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        category_id = int_param(params, "category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        lifecycle_state = params.get("lifecycle_state")
        if lifecycle_state is not None:
            queryset = queryset.filter(lifecycle_state=lifecycle_state)
        account_type = params.get("account_type")
        if account_type is not None:
            queryset = queryset.filter(account_type=account_type)
        return queryset


class BillSkipViewSet(viewsets.ModelViewSet):
    serializer_class = BillSkipSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[BillSkip]:
        queryset = BillSkip.objects.select_related("billing_account")
        params = self.request.query_params
        billing_account_id = int_param(params, "billing_account_id")
        if billing_account_id is not None:
            queryset = queryset.filter(billing_account_id=billing_account_id)
        reference_month = params.get("reference_month")
        if reference_month is not None:
            queryset = queryset.filter(reference_month=reference_month)
        return queryset.order_by("-reference_month")


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[Payment]:
        queryset = Payment.objects.select_related("condominium").prefetch_related(
            "allocations", "allocations__bill"
        )
        params = self.request.query_params
        funded_from = params.get("funded_from")
        if funded_from is not None:
            queryset = queryset.filter(funded_from=funded_from)
        date_from = params.get("date_from")
        if date_from is not None:
            queryset = queryset.filter(payment_date__gte=date_from)
        date_to = params.get("date_to")
        if date_to is not None:
            queryset = queryset.filter(payment_date__lte=date_to)
        return queryset

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Reverse a payment through the single reversal path (BillPaymentService.unpay).

        The default destroy would SoftDeleteMixin.delete() only the Payment row, orphaning its
        live PaymentAllocation rows (the bill stays falsely 'paid', amount_remaining unchanged) and
        never reversing a reserve withdrawal. unpay soft-deletes the allocations, reverses the
        reserve movement, and enforces the closed-month guard (assert_open -> 400 PT).
        """
        payment = self.get_object()
        try:
            BillPaymentService.unpay(payment, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


_INT_STATEMENT_FIELDS = frozenset(
    {
        "consumo_m3",
        "consumo_kwh",
        "energia_injetada_kwh",
        "leitura_anterior",
        "leitura_atual",
        "leitura_dias",
    }
)
_DATE_STATEMENT_FIELDS = frozenset({"data_leitura"})

_ERR_STATEMENT_OBJECT = "statement deve ser um objeto."
_ERR_LINE_OBJECT = "Cada linha deve ser um objeto."


def _coerce_statement_value(field: str, raw: object) -> object:
    """Coerce a single raw statement field (int / date / str) — raises on a bad value."""
    if raw is None:
        return None
    if field in _INT_STATEMENT_FIELDS:
        return int(str(raw))  # bad value -> ValueError -> 400 PT in the action
    if field in _DATE_STATEMENT_FIELDS:
        return date.fromisoformat(str(raw))
    return str(raw)


def _parse_statement(raw: object) -> StatementInput | None:
    """Build a typed statement dict from the raw request payload (None passes through).

    The statement TYPE (water vs electricity) is decided by the billing account in the
    service; here we only coerce values (int/date/str) and surface a 400 PT on a bad one.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValidationError(_ERR_STATEMENT_OBJECT)
    coerced = {field: _coerce_statement_value(field, value) for field, value in raw.items()}
    return cast(StatementInput, coerced)


def _parse_lines(line_items: list[object]) -> list[BillLineInput]:
    """Build BillLineInput list from the raw line_items payload (resolves category/installment)."""
    lines: list[BillLineInput] = []
    for raw in line_items:
        if not isinstance(raw, dict):
            raise ValidationError(_ERR_LINE_OBJECT)
        category_id = raw.get("category_id")
        installment_id = raw.get("installment_id")
        lines.append(
            BillLineInput(
                description=str(raw["description"]),
                amount=Decimal(str(raw["amount"])),
                is_offset=bool(raw.get("is_offset", False)),
                category=(Category.objects.filter(pk=category_id).first() if category_id else None),
                installment=(
                    Installment.objects.filter(pk=installment_id).first()
                    if installment_id
                    else None
                ),
            )
        )
    return lines


class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[Bill]:
        queryset = (
            Bill.objects.with_amounts(today_sp())
            .select_related(
                "building",
                "category",
                "billing_account",
                "condominium",
                "water_statement",
                "electricity_statement",
            )
            .prefetch_related("line_items", "allocations")
        )
        return self._apply_filters(queryset, self.request.query_params)

    def _apply_filters(self, queryset: QuerySet[Bill], params: QueryDict) -> QuerySet[Bill]:
        building_id = int_param(params, "building_id")
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        category_id = int_param(params, "category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
        competence_month = params.get("competence_month")
        if competence_month is not None:
            queryset = queryset.filter(competence_month=competence_month)
        lifecycle_state = params.get("lifecycle_state")
        if lifecycle_state is not None:
            queryset = queryset.filter(lifecycle_state=lifecycle_state)
        behavior = params.get("behavior")
        if behavior is not None:
            queryset = queryset.filter(behavior=behavior)
        # payment_status / is_overdue are with_amounts annotations — pass the lookup through a
        # dict variable so the django-stubs plugin does not reject the annotation names as
        # unknown fields (an inline ** literal would be rewritten by ruff PIE804).
        payment_status = params.get("payment_status")
        if payment_status is not None:
            status_lookup: dict[str, object] = {"payment_status": payment_status}
            queryset = queryset.filter(**status_lookup)
        is_overdue = params.get("is_overdue")
        if is_overdue is not None:
            overdue_lookup: dict[str, object] = {"is_overdue": is_overdue.lower() == "true"}
            queryset = queryset.filter(**overdue_lookup)
        return queryset

    def _serialized_bill(self, bill: Bill) -> dict[str, object]:
        annotated = self.get_queryset().get(pk=bill.pk)
        return BillSerializer(annotated, context={"request": self.request}).data

    @action(detail=True, methods=["post"])
    def pay(self, request: Request, pk: str | None = None) -> Response:
        bill = self.get_object()
        payment_date_raw = request.data.get("payment_date")
        if not payment_date_raw:
            return Response(
                {"error": "Campo payment_date é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payment_date = date.fromisoformat(str(payment_date_raw))
            amount_raw = request.data.get("amount")
            amount = Decimal(str(amount_raw)) if amount_raw is not None else None
            funded_from = _validated_funded_from(request.data.get("funded_from", "caixa"))
            BillPaymentService.pay(
                bill, payment_date, amount, funded_from, user=cast(User, request.user)
            )
        except (ValueError, InvalidOperation):
            return Response(
                {"error": "Valor, data ou forma de pagamento inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def bulk_pay(self, request: Request) -> Response:
        bill_ids = request.data.get("bill_ids")
        payment_date_raw = request.data.get("payment_date")
        if not bill_ids or not isinstance(bill_ids, list) or not payment_date_raw:
            return Response(
                {"error": "Campos bill_ids (lista não vazia) e payment_date são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            funded_from = _validated_funded_from(request.data.get("funded_from", "caixa"))
            payment_date = date.fromisoformat(str(payment_date_raw))
        except (ValueError, InvalidOperation):
            return Response(
                {"error": "Data ou forma de pagamento inválida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bills = list(Bill.objects.filter(pk__in=bill_ids))
        if len(bills) != len(bill_ids):
            return Response(
                {"error": "Uma ou mais contas não foram encontradas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                for bill in bills:
                    BillPaymentService.pay(
                        bill, payment_date, None, funded_from, user=cast(User, request.user)
                    )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response([self._serialized_bill(bill) for bill in bills], status=status.HTTP_200_OK)

    def _transition(self, state: str) -> Response:
        bill = self.get_object()
        BillLifecycleService.set_state(bill, state, user=cast(User, self.request.user))
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def suspend(self, request: Request, pk: str | None = None) -> Response:
        return self._transition(BillLifecycleState.SUSPENDED)

    @action(detail=True, methods=["post"])
    def defer(self, request: Request, pk: str | None = None) -> Response:
        return self._transition(BillLifecycleState.DEFERRED)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        return self._transition(BillLifecycleState.CANCELED)

    @action(detail=True, methods=["post"])
    def reactivate(self, request: Request, pk: str | None = None) -> Response:
        bill = self.get_object()
        try:
            BillLifecycleService.reactivate(bill, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def generate_month(self, request: Request) -> Response:
        try:
            year, month = _parse_year_month(request.data)
        except (KeyError, ValueError, TypeError):
            return Response(
                {"error": "Parâmetros year/month inválidos (mês entre 1 e 12)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bills = BillGenerationService.ensure_month_bills(year, month, user=cast(User, request.user))
        return Response(
            {
                "created": len(bills),
                "bills": [self._serialized_bill(bill) for bill in bills],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def create_with_lines(self, request: Request) -> Response:
        bill_data = request.data.get("bill")
        line_items = request.data.get("line_items", [])
        if not isinstance(bill_data, dict) or not isinstance(line_items, list):
            return Response(
                {
                    "error": "Payload inválido: 'bill' (objeto) e 'line_items' (lista) são obrigatórios."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        bill_serializer = BillSerializer(data=bill_data)
        if not bill_serializer.is_valid():
            return Response(bill_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated = bill_serializer.validated_data
        try:
            draft = BillDraft(
                condominium=validated["condominium"],
                competence_month=validated["competence_month"],
                due_date=validated["due_date"],
                description=validated["description"],
                behavior=validated["behavior"],
                building=validated.get("building"),
                category=validated.get("category"),
                billing_account=validated.get("billing_account"),
                external_identifier=validated.get("external_identifier", ""),
                lifecycle_state=validated.get("lifecycle_state", BillLifecycleState.ACTIVE),
                notes=validated.get("notes", ""),
            )
            lines = _parse_lines(line_items)
            statement = _parse_statement(request.data.get("statement"))
            bill = BillService.create_with_lines(
                draft, lines, statement=statement, user=cast(User, request.user)
            )
        except (KeyError, ValueError, InvalidOperation, ValidationError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) else str(exc)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def update_with_lines(self, request: Request, pk: str | None = None) -> Response:
        """Replace a bill's lines + upsert its statement on the SAME Bill (UNPAID + OPEN only)."""
        bill = self.get_object()
        line_items = request.data.get("line_items", [])
        if not isinstance(line_items, list):
            return Response(
                {"error": "Payload inválido: 'line_items' (lista) é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            lines = _parse_lines(line_items)
            statement = _parse_statement(request.data.get("statement"))
            BillService.update_with_lines(
                bill, lines, statement=statement, user=cast(User, request.user)
            )
        except (KeyError, ValueError, InvalidOperation, ValidationError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) else str(exc)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Soft-delete the bill through BillService.delete, which cascades to its statement.

        The default destroy would SoftDeleteMixin.delete() only the Bill row, leaving a live
        water/electricity statement orphaned (it would still surface via the reverse accessor on
        a re-fetched soft-deleted bill — design §7.3). delete soft-deletes the statement first.
        """
        bill = self.get_object()
        BillService.delete(bill, user=cast(User, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReserveViewSet(viewsets.ModelViewSet):
    serializer_class = ReserveSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[Reserve]:
        queryset = Reserve.objects.select_related("condominium").prefetch_related("movements")
        condominium_id = int_param(self.request.query_params, "condominium_id")
        if condominium_id is not None:
            queryset = queryset.filter(condominium_id=condominium_id)
        return queryset

    def _serialized(self, reserve: Reserve) -> dict[str, object]:
        return ReserveSerializer(reserve, context={"request": self.request}).data

    @action(detail=True, methods=["post"])
    def deposit(self, request: Request, pk: str | None = None) -> Response:
        return self._movement(request, ReserveService.deposit)

    @action(detail=True, methods=["post"])
    def withdraw(self, request: Request, pk: str | None = None) -> Response:
        return self._movement(request, ReserveService.withdraw)

    def _movement(self, request: Request, operation: Callable[..., ReserveMovement]) -> Response:
        reserve = self.get_object()
        amount_raw = request.data.get("amount")
        if amount_raw is None:
            return Response(
                {"error": "Campo amount é obrigatório."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            amount = Decimal(str(amount_raw))
            movement_date_raw = request.data.get("movement_date")
            movement_date = (
                date.fromisoformat(str(movement_date_raw)) if movement_date_raw else today_sp()
            )
            operation(
                reserve,
                amount,
                movement_date,
                reference=str(request.data.get("reference", "")),
                notes=str(request.data.get("notes", "")),
                user=cast(User, request.user),
            )
        except (ValueError, InvalidOperation):
            return Response(
                {"error": "Valor ou data inválido."}, status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized(reserve), status=status.HTTP_200_OK)


class ReserveMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ledger. The ONLY write path is reserves/{id}/deposit|withdraw, where
    ReserveService enforces the never-negative guard (design §4.3/§18). A direct create/update
    here would bypass that guard and could drive the reserve negative, so writes are not exposed."""

    serializer_class = ReserveMovementSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[ReserveMovement]:
        queryset = ReserveMovement.objects.select_related("reserve", "bill")
        params = self.request.query_params
        reserve_id = int_param(params, "reserve_id")
        if reserve_id is not None:
            queryset = queryset.filter(reserve_id=reserve_id)
        kind = params.get("kind")
        if kind is not None:
            queryset = queryset.filter(kind=kind)
        date_from = params.get("date_from")
        if date_from is not None:
            queryset = queryset.filter(movement_date__gte=date_from)
        date_to = params.get("date_to")
        if date_to is not None:
            queryset = queryset.filter(movement_date__lte=date_to)
        return queryset


class IncomeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeEntrySerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[IncomeEntry]:
        queryset = IncomeEntry.objects.select_related("building", "category", "condominium")
        params = self.request.query_params
        building_id = int_param(params, "building_id")
        if building_id is not None:
            queryset = queryset.filter(building_id=building_id)
        category_id = int_param(params, "category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)
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


class CondoMonthCloseViewSet(viewsets.ModelViewSet):
    serializer_class = CondoMonthCloseSerializer
    permission_classes = [FinancialReadOnly]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[CondoMonthClose]:
        queryset = CondoMonthClose.objects.select_related("condominium")
        params = self.request.query_params
        status_param = params.get("status")
        if status_param is not None:
            queryset = queryset.filter(status=status_param)
        reference_month = params.get("reference_month")
        if reference_month is not None:
            queryset = queryset.filter(reference_month=reference_month)
        return queryset

    def _close_action(
        self, request: Request, operation: Callable[[int, int, User], CondoMonthClose]
    ) -> Response:
        try:
            year, month = _parse_year_month(request.data)
        except (KeyError, ValueError, TypeError):
            return Response(
                {"error": "Parâmetros year/month inválidos (mês entre 1 e 12)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            close = operation(year, month, cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            CondoMonthCloseSerializer(close, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def close(self, request: Request) -> Response:
        return self._close_action(request, CondoMonthCloseService.close)

    @action(detail=False, methods=["post"])
    def reopen(self, request: Request) -> Response:
        return self._close_action(request, CondoMonthCloseService.reopen)
