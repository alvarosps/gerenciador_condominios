"""CRUD viewsets + Bill actions for the finances API (Session 38).

ModelViewSet + IsAdminUser + CustomPageNumberPagination. Bill amount_* read from
the with_amounts(today) annotation (TZ-SP today). Actions are thin: they parse/validate
request data (400 PT) and delegate to the S37/S38 services.
"""

import io
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast

import pdfplumber
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.http import QueryDict
from pdfplumber.utils.exceptions import PdfminerException
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from core.models import Building, Condominium, Person
from core.pagination import CustomPageNumberPagination
from core.permissions import IsAdminUser
from core.services.timezone import today_sp
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
    InstallmentPlanState,
    Payment,
    Reserve,
    ReserveMovement,
    ThirdPartySettlement,
)
from finances.serializers import (
    BillingAccountSerializer,
    BillSerializer,
    BillSkipSerializer,
    CategorySerializer,
    CondoMonthCloseSerializer,
    IncomeEntrySerializer,
    InstallmentPlanSerializer,
    PaymentSerializer,
    ReserveMovementSerializer,
    ReserveSerializer,
    ThirdPartySettlementSerializer,
)
from finances.services.account_statement_service import AccountStatementService
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
from finances.services.installment_plan_service import InstallmentPlanService
from finances.services.invoice_apply_service import InvoiceApplyService
from finances.services.invoice_draft_service import InvoiceDraftService
from finances.services.invoice_parsing.base import ParsedInvoice
from finances.services.invoice_parsing.registry import detect_and_parse
from finances.services.reserve_service import ReserveService
from finances.services.third_party_purchase_service import (
    PurchaseDraft,
    ThirdPartyPurchaseService,
)
from finances.services.third_party_settlement_service import ThirdPartySettlementService
from finances.services.third_party_statement_service import ThirdPartyStatementService
from finances.viewsets.query_params import int_param

MONTHS_IN_YEAR = 12

# The default DRF CRUD write routes bypass the rich-path guards; these messages (PT) explain the
# 405 the closed routes return and point the client at the canonical action (P2.3 steps 3/4).
_PAYMENT_WRITE_BLOCKED = (
    "Pagamentos são criados e editados apenas via contas/{id}/pay e contas/{id}/unpay."
)
_BILL_CREATE_BLOCKED = "Contas são criadas via contas/create_with_lines (com as linhas)."


def _parse_year_month(data: dict[str, object]) -> tuple[int, int]:
    """Parse year/month from request data; raise ValueError (-> 400) when invalid."""
    year = int(cast(str, data["year"]))
    month = int(cast(str, data["month"]))
    if not (1 <= month <= MONTHS_IN_YEAR):
        raise ValueError  # caller maps this to a 400 with a user-facing message
    return year, month


_THIRD_PARTY_NEEDS_PERSON = "Pagamento de terceiro exige a pessoa que pagou (paid_by_person_id)."
_UNKNOWN_PERSON = "Pessoa não encontrada."
_UNKNOWN_CATEGORY = "Categoria não encontrada."
_UNKNOWN_BUILDING = "Prédio não encontrado."


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


def _validated_funding(data: dict[str, object] | QueryDict) -> tuple[str, Person | None]:
    """Resolve (funded_from, paid_by) together — the single validation point for BOTH pay and
    bulk_pay (S80 §4).

    bulk_pay must go through here too: skipping it would leave an escape hatch for creating a
    third-party payment with no person attached, and the debt would belong to nobody. One
    paid_by_person_id applies to EVERY bill in a bulk_pay — assigning a whole month's bills to
    the same card is the desired behavior (design §7).
    """
    funded_from = _validated_funded_from(data.get("funded_from", "caixa"))
    raw_person = data.get("paid_by_person_id")
    if funded_from == FundedFrom.THIRD_PARTY.value and raw_person is None:
        raise ValidationError(_THIRD_PARTY_NEEDS_PERSON)
    if raw_person is None:
        return funded_from, None
    return funded_from, _person_or_400(raw_person)


def _person_or_400(raw: object) -> Person:
    """Resolve a Person by pk; a missing/non-numeric id is a PT 400, never a 500."""
    try:
        person_id = int(cast(str, raw))
    except (TypeError, ValueError) as exc:
        raise ValidationError(_UNKNOWN_PERSON) from exc
    person = Person.objects.filter(pk=person_id).first()
    if person is None:
        raise ValidationError(_UNKNOWN_PERSON)
    return person


_NEW_TOTAL_INVALID = "Valor inválido: use no máximo 2 casas decimais."
_NEW_TOTAL_MAX_DECIMAL_PLACES = -2  # Decimal.as_tuple().exponent, money is always cents-scale.


def _parse_new_total(raw: object) -> Decimal | None:
    """new_total as a finite Decimal with at most 2 decimal places, or None (-> PT 400 otherwise).

    ``Decimal(str(raw))`` alone accepts "Infinity"/"NaN" (not caught by ValueError/
    InvalidOperation) and any decimal scale (e.g. "230.005"), both of which would otherwise
    reach BillLineItem.full_clean() and surface Django's default (English) validator message
    verbatim through the action's error shape. Rejected here instead, as a ValidationError (PT,
    caught by the same handler as every other business-rule rejection in this action) — no
    scientific/silent rounding: an out-of-range value is a 400, not a truncation.
    """
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except InvalidOperation as exc:
        raise ValidationError(_NEW_TOTAL_INVALID) from exc
    if not value.is_finite():
        raise ValidationError(_NEW_TOTAL_INVALID)
    # is_finite() guarantees a numeric (int) exponent here — Infinity/NaN ('F'/'n'/'N') are
    # already rejected above, so this comparison is type-safe (never the sign/payload literals).
    exponent = value.as_tuple().exponent
    if isinstance(exponent, str) or exponent < _NEW_TOTAL_MAX_DECIMAL_PLACES:
        raise ValidationError(_NEW_TOTAL_INVALID)
    return value


_CONSOLIDATE_DEBT_PAYLOAD_INVALID = (
    "Parâmetros inválidos: bill_ids (lista), embedded, installment_count, "
    "start_due_date, default_due_day."
)


class _ConsolidateDebtPayload:
    """Validated request.data for consolidate_debt (Session 70)."""

    __slots__ = ("bill_ids", "default_due_day", "embedded", "installment_count", "start_due_date")

    def __init__(
        self,
        bill_ids: list[int],
        embedded: bool,
        installment_count: int,
        start_due_date: date,
        default_due_day: int,
    ) -> None:
        self.bill_ids = bill_ids
        self.embedded = embedded
        self.installment_count = installment_count
        self.start_due_date = start_due_date
        self.default_due_day = default_due_day


def _strict_int(raw: object) -> int:
    """raw as an int, rejecting bool and float coercion; raise TypeError (-> 400 PT) otherwise.

    isinstance(True, int) is True in Python (bool is an int subclass) and int(3.7) silently
    truncates to 3, so a bare int(...) cast would accept a JSON bill id of `true` (-> 1) or `3.7`
    (-> 3) — the same laxness the strict embedded bool check below exists to avoid.
    """
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise TypeError
    return raw


def _parse_consolidate_debt_payload(data: dict[str, object]) -> _ConsolidateDebtPayload:
    """Parse consolidate_debt's body; raise KeyError/ValueError/TypeError (-> 400 PT) otherwise.

    embedded must be a strict JSON bool (isinstance check) — bool("false") is True in Python, so
    coercing via bool(...) would silently accept the string "false" as True. bill_ids items and
    installment_count/default_due_day are strict JSON ints for the same reason (_strict_int).
    """
    bill_ids_raw = data["bill_ids"]
    if not isinstance(bill_ids_raw, list) or not bill_ids_raw:
        raise TypeError
    bill_ids = [_strict_int(item) for item in bill_ids_raw]
    embedded = data["embedded"]
    if not isinstance(embedded, bool):
        raise TypeError
    installment_count = _strict_int(data["installment_count"])
    start_due_date = date.fromisoformat(str(data["start_due_date"]))
    default_due_day = _strict_int(data["default_due_day"])
    return _ConsolidateDebtPayload(
        bill_ids, embedded, installment_count, start_due_date, default_due_day
    )


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[BillingAccount]:
        # with_open_balance(today_sp()) exposes the S67 open_balance annotation on every read
        # (list + retrieve) — no cache here, same as before (design §4).
        queryset = BillingAccount.objects.with_open_balance(today_sp()).select_related(
            "building", "category", "condominium"
        )
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

    @action(detail=True, methods=["get"])
    def statement(self, request: Request, pk: str | None = None) -> Response:
        # NO cache (design §4/§10): depends on payment state + today_sp(); midnight rollover is
        # not a write, so cache would never be invalidated — same rationale as
        # month_board/iptu_alerts/overdue.
        account = self.get_object()  # 404 for unknown/soft-deleted account (live manager)
        return Response(
            AccountStatementService.build(account.pk, today_sp()), status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def consolidate_debt(self, request: Request, pk: str | None = None) -> Response:
        """Consolida N contas em aberto desta conta em 1 plano (cancela as origens)."""
        account = self.get_object()  # 404 for unknown/soft-deleted account (live manager)
        try:
            payload = _parse_consolidate_debt_payload(request.data)
        except KeyError, ValueError, TypeError:
            return Response(
                {"error": _CONSOLIDATE_DEBT_PAYLOAD_INVALID}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            plan = InstallmentPlanService.consolidate_open_bills(
                account=account,
                bill_ids=payload.bill_ids,
                embedded=payload.embedded,
                installment_count=payload.installment_count,
                start_due_date=payload.start_due_date,
                default_due_day=payload.default_due_day,
                user=cast(User, request.user),
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            InstallmentPlanSerializer(plan, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class BillSkipViewSet(viewsets.ModelViewSet):
    serializer_class = BillSkipSerializer
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
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

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        # A Payment (amount/funded_from read-only) created via the default route would either 500
        # (amount missing) or desync Σ(allocation) from amount and orphan any reserve withdrawal.
        # The only write path is contas/{id}/pay (P2.3 step 3).
        return Response(
            {"detail": _PAYMENT_WRITE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        # Editing a payment in place would desync its allocations / reserve ghost (§4.8); change
        # a payment only via unpay() + pay().
        return Response(
            {"detail": _PAYMENT_WRITE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request: Request, *args: object, **kwargs: object) -> Response:
        return self.update(request, *args, **kwargs)

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
_ERR_NO_FILE = "Envie o arquivo da fatura no campo 'file'."
_ERR_NOT_PDF = "O arquivo enviado não é um PDF válido."
_ERR_INSTALLMENT_NOT_OWNED = (
    "A parcela informada não pertence ao plano embutido ativo desta conta recorrente."
)


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


def _resolve_owned_installment(
    installment_id: object, billing_account: BillingAccount | None
) -> Installment | None:
    """Resolve an installment_id to an Installment ONLY if it belongs to this bill's embedded ACTIVE
    plan; otherwise reject (400 PT). Without this an attacker could bind ANY installment id to a
    line (cross-account leakage / a parcela that is not the account's). Mirrors the embedded-plan
    invariant the draft reconciler (InvoiceDraftService._reconcile_line) already enforces."""
    if not installment_id:
        return None
    pk = int(str(installment_id))  # bad id -> ValueError -> 400 PT in the action
    installment = Installment.objects.filter(
        pk=pk,
        plan__billing_account=billing_account,
        plan__embedded=True,
        plan__lifecycle_state=InstallmentPlanState.ACTIVE,
        plan__is_deleted=False,
    ).first()
    if installment is None:
        raise ValidationError(_ERR_INSTALLMENT_NOT_OWNED)
    return installment


def _parse_lines(
    line_items: list[object], billing_account: BillingAccount | None
) -> list[BillLineInput]:
    """Build BillLineInput list from the raw line_items payload (resolves category/installment).

    An installment_id is bound ONLY when it belongs to the bill's embedded ACTIVE plan (ownership
    guard); a foreign/standalone/inactive installment is rejected 400 PT.
    """
    lines: list[BillLineInput] = []
    for raw in line_items:
        if not isinstance(raw, dict):
            raise ValidationError(_ERR_LINE_OBJECT)
        category_id = raw.get("category_id")
        lines.append(
            BillLineInput(
                description=str(raw["description"]),
                amount=Decimal(str(raw["amount"])),
                is_offset=bool(raw.get("is_offset", False)),
                category=(Category.objects.filter(pk=category_id).first() if category_id else None),
                installment=_resolve_owned_installment(raw.get("installment_id"), billing_account),
            )
        )
    return lines


class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [IsAdminUser]
    # The Contas UI groups ALL bills per building (no page slicing) and relies on
    # page_size=10000 returning every bill in one page — CustomPageNumberPagination's
    # max_page_size is 10000 (A3), so no dedicated "large" pagination class is needed here.
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[Bill]:
        queryset = Bill.objects.with_amounts(today_sp()).with_list_relations()
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
            new_total = _parse_new_total(request.data.get("new_total"))
            funded_from, paid_by = _validated_funding(request.data)
            BillPaymentService.pay(
                bill,
                payment_date,
                amount,
                funded_from,
                new_total=new_total,
                paid_by=paid_by,
                user=cast(User, request.user),
            )
        except ValueError, InvalidOperation:
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
            funded_from, paid_by = _validated_funding(request.data)
            payment_date = date.fromisoformat(str(payment_date_raw))
        except ValueError, InvalidOperation:
            return Response(
                {"error": "Data ou forma de pagamento inválida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
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
                        bill,
                        payment_date,
                        None,
                        funded_from,
                        paid_by=paid_by,
                        user=cast(User, request.user),
                    )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response([self._serialized_bill(bill) for bill in bills], status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def create_purchase(self, request: Request) -> Response:
        """Third-party purchase: N Bills + N Payments, born paid, in ONE transaction (§4.5).

        Returns the list of created bills (one element for a plain purchase, N for a parcelada) so
        the client never has to guess how many rows a submission produced.
        """
        try:
            person = _person_or_400(request.data.get("person_id"))
            amount = Decimal(str(request.data.get("amount")))
            competence_month = date.fromisoformat(str(request.data.get("competence_month")))
            due_date = date.fromisoformat(str(request.data.get("due_date")))
            installment_count = int(request.data.get("installment_count", 1))
            category = self._optional_category(request.data.get("category_id"))
            building = self._optional_building(request.data.get("building_id"))
        except ValueError, InvalidOperation, TypeError:
            return Response(
                {"error": "Payload inválido: verifique pessoa, valor, competência e vencimento."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        description = str(request.data.get("description", "")).strip()
        if not description:
            return Response(
                {"error": "Campo description é obrigatório."}, status=status.HTTP_400_BAD_REQUEST
            )
        condominium = Condominium.get_default()
        if condominium is None:
            return Response(
                {"error": Condominium.NOT_CONFIGURED_MESSAGE}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            bills = ThirdPartyPurchaseService.create_purchase(
                PurchaseDraft(
                    condominium=condominium,
                    person=person,
                    description=description,
                    amount=amount,
                    competence_month=competence_month,
                    due_date=due_date,
                    category=category,
                    building=building,
                    installment_count=installment_count,
                ),
                user=cast(User, request.user),
            )
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            [self._serialized_bill(bill) for bill in bills], status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["delete"])
    def delete_purchase(self, request: Request, pk: str | None = None) -> Response:
        """The ONLY way to undo a third-party purchase (§4.3.1) — Bill + Payment, atomically.

        The ordinary delete/cancel routes reject a purchase (assert_not_paid: it is born paid) and
        unpay rejects its payment, so without this action a mistyped purchase would be permanent.
        """
        bill = self.get_object()
        try:
            ThirdPartyPurchaseService.delete_purchase(bill, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def reassign_payer(self, request: Request, pk: str | None = None) -> Response:
        """Fix a wrong payer on BOTH sides — Bill.paid_by_person and Payment.paid_by (§4.3.1)."""
        bill = self.get_object()
        try:
            person = _person_or_400(request.data.get("paid_by_person_id"))
            ThirdPartyPurchaseService.reassign_payer(bill, person, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    @staticmethod
    def _optional_category(raw: object) -> Category | None:
        """Resolve an optional category id; an unknown id is a PT 400, never a silent None."""
        if raw is None:
            return None
        category = Category.objects.filter(pk=int(cast(str, raw))).first()
        if category is None:
            raise ValidationError(_UNKNOWN_CATEGORY)
        return category

    @staticmethod
    def _optional_building(raw: object) -> Building | None:
        if raw is None:
            return None
        building = Building.objects.filter(pk=int(cast(str, raw))).first()
        if building is None:
            raise ValidationError(_UNKNOWN_BUILDING)
        return building

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
        except KeyError, ValueError, TypeError:
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
            lines = _parse_lines(line_items, validated.get("billing_account"))
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
        """Replace a bill's lines + upsert its statement (+ corrected header) on the SAME Bill.

        UNPAID + OPEN only. A re-imported (corrected) invoice carries a 'bill' header; its editable
        fields (due_date/external_identifier/issue_date/building/category/…) are validated here via
        the partial BillSerializer and persisted in the SAME atomic transaction as the line/statement
        replace. competence_month stays IMMUTABLE — it is never forwarded to the service.
        """
        bill = self.get_object()
        line_items = request.data.get("line_items", [])
        if not isinstance(line_items, list):
            return Response(
                {"error": "Payload inválido: 'line_items' (lista) é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bill_data = request.data.get("bill")
        header: dict[str, object] | None = None
        if bill_data is not None:
            if not isinstance(bill_data, dict):
                return Response(
                    {"error": "Payload inválido: 'bill' deve ser um objeto."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            header_serializer = BillSerializer(instance=bill, data=bill_data, partial=True)
            if not header_serializer.is_valid():
                return Response(header_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            # competence_month is immutable; drop it (+ condominium, never reassigned) so the
            # service only sees the editable header fields it accepts.
            header = {
                field: value
                for field, value in header_serializer.validated_data.items()
                if field not in ("competence_month", "condominium")
            }
        try:
            lines = _parse_lines(line_items, bill.billing_account)
            statement = _parse_statement(request.data.get("statement"))
            BillService.update_with_lines(
                bill, lines, statement=statement, header=header, user=cast(User, request.user)
            )
        except (KeyError, ValueError, InvalidOperation, ValidationError) as exc:
            message = exc.messages[0] if isinstance(exc, ValidationError) else str(exc)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    def _read_parsed_invoice(self, request: Request) -> ParsedInvoice | Response:
        """Read+validate the uploaded invoice PDF and parse it in MEMORY (shared by
        parse_invoice/apply_invoice — DRY, identical 400/422 PT on both).

        Returns the parsed invoice on success or the PT error Response on failure (the caller
        checks ``isinstance(result, ParsedInvoice)`` and returns the Response verbatim otherwise).
        The PDF is validated and discarded — never stored (decisão #4). The only external I/O
        boundary is pdfplumber.open; the positional parsing lives in the S59 registry.
        """
        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response({"error": _ERR_NO_FILE}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes = uploaded.read()
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                has_pages = bool(pdf.pages)
        except PdfminerException, ValueError, OSError:
            return Response({"error": _ERR_NOT_PDF}, status=status.HTTP_400_BAD_REQUEST)
        if not has_pages:
            return Response({"error": _ERR_NOT_PDF}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return detect_and_parse(pdf_bytes)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def parse_invoice(self, request: Request) -> Response:
        """Receive a utility invoice PDF (multipart), parse it in MEMORY and return a DRAFT.

        Writes NOTHING (past-immutable, design §6): the draft is persisted later via
        create_with_lines/update_with_lines (S58), from the modal (S63). is_staff is enforced by
        IsAdminUser (admin-only viewset). The PDF is validated and discarded — never stored
        (decisão #4). The only external I/O boundary is pdfplumber.open; the positional parsing
        lives in the S59 registry.
        """
        parsed = self._read_parsed_invoice(request)
        if not isinstance(parsed, ParsedInvoice):
            return parsed
        draft = InvoiceDraftService.build_draft(parsed)
        return Response(draft, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def apply_invoice(self, request: Request, pk: str | None = None) -> Response:
        """Receive a utility invoice PDF (multipart), parse it in MEMORY and APPLY it to THIS bill.

        Unlike parse_invoice (a read-only draft for the modal), this writes: lines + statement +
        editable header (due_date/external_identifier) are replaced on the SAME transaction via
        InvoiceApplyService.apply -> BillService.update_with_lines (S69, design §3.3). 400 PT on
        account/competence mismatch, a non-ACTIVE bill, a paid bill or a closed month (the last
        two rejected by update_with_lines' own guards, delegated). 422 PT on an unknown issuer
        (same status as parse_invoice). The PDF is validated and discarded — never stored.
        """
        bill = self.get_object()
        parsed = self._read_parsed_invoice(request)
        if not isinstance(parsed, ParsedInvoice):
            return parsed
        try:
            InvoiceApplyService.apply(bill, parsed, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        # The default create cannot write line items (amount_total derives from them), so a bill
        # created here would always be empty AND would bypass the closed-month / identity guards.
        # The only creation path is create_with_lines (P2.3 step 4).
        return Response({"detail": _BILL_CREATE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Edit ONLY a bill's header fields (the Contas modal's edit mode), through the guard.

        The default DRF update wrote any field (competence_month included) with no guard. Here the
        validated header is delegated to BillService.update_header, which keeps competence_month
        immutable, rejects a closed competence month (assert_open), and never touches lines/payments
        (those go through update_with_lines / pay). Lines stay editable only via update_with_lines.
        """
        partial = bool(kwargs.get("partial", False))
        bill = self.get_object()
        serializer = self.get_serializer(bill, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # competence_month is immutable; drop it (+ condominium, never reassigned) so only the
        # editable header reaches the service (mirrors update_with_lines).
        header = {
            field: value
            for field, value in serializer.validated_data.items()
            if field not in ("competence_month", "condominium")
        }
        try:
            BillService.update_header(bill, header, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._serialized_bill(bill), status=status.HTTP_200_OK)

    def partial_update(self, request: Request, *args: object, **kwargs: object) -> Response:
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        """Soft-delete the bill through BillService.delete, which cascades to its statement.

        The default destroy would SoftDeleteMixin.delete() only the Bill row, leaving a live
        water/electricity statement orphaned (it would still surface via the reverse accessor on
        a re-fetched soft-deleted bill — design §7.3). delete soft-deletes the statement first
        and rejects (PT 400) a closed competence month (assert_open).
        """
        bill = self.get_object()
        try:
            BillService.delete(bill, user=cast(User, request.user))
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReserveViewSet(viewsets.ModelViewSet):
    serializer_class = ReserveSerializer
    permission_classes = [IsAdminUser]
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
        except ValueError, InvalidOperation:
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
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
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

    def perform_create(self, serializer: BaseSerializer[IncomeEntry]) -> None:
        # An income in a closed month changes that month's frozen cash/competence; reject it here
        # (the architecture rule keeps assert_open out of the serializer — P2.3 step 2).
        self._assert_income_month_open(serializer)
        serializer.save()

    def perform_update(self, serializer: BaseSerializer[IncomeEntry]) -> None:
        # B8b: guard BOTH the new AND the old dates — moving an income OUT of a closed month
        # (competence or cash) corrupts that month's frozen close exactly like moving one in.
        self._assert_income_month_open(serializer, instance=serializer.instance)
        self._assert_income_month_open(serializer)
        serializer.save()

    def perform_destroy(self, instance: IncomeEntry) -> None:
        # B8a: deleting an income in a closed competence OR cash month changes that month's
        # frozen income_competence/income_cash — the default ModelViewSet.destroy had no guard.
        CondoMonthCloseService.assert_open(instance.income_date.replace(day=1))
        if instance.is_received and instance.received_date is not None:
            CondoMonthCloseService.assert_open(instance.received_date.replace(day=1))
        instance.delete()

    @staticmethod
    def _assert_income_month_open(
        serializer: BaseSerializer[IncomeEntry], *, instance: IncomeEntry | None = None
    ) -> None:
        """Reject the write when the income's competence (income_date) OR cash (received_date,
        when is_received) month is closed.

        ``instance=None`` (the default) reads the NEW values (validated_data, falling back to the
        existing instance for an omitted PATCH field) — the create/update-in path. Passing the
        existing instance explicitly (B8b) reads the OLD values instead, so perform_update can
        guard the record's current dates too, before they are overwritten.
        """
        existing = instance if instance is not None else serializer.instance
        existing_income_date = existing.income_date if isinstance(existing, IncomeEntry) else None
        existing_is_received = existing.is_received if isinstance(existing, IncomeEntry) else False
        existing_received_date = (
            existing.received_date if isinstance(existing, IncomeEntry) else None
        )
        if instance is not None:
            income_date = existing_income_date
            is_received = existing_is_received
            received_date = existing_received_date
        else:
            income_date = cast(
                "date | None", serializer.validated_data.get("income_date", existing_income_date)
            )
            is_received = cast(
                bool, serializer.validated_data.get("is_received", existing_is_received)
            )
            received_date = cast(
                "date | None",
                serializer.validated_data.get("received_date", existing_received_date),
            )
        if income_date is not None:
            CondoMonthCloseService.assert_open(income_date.replace(day=1))
        if is_received and received_date is not None:
            CondoMonthCloseService.assert_open(received_date.replace(day=1))


class CondoMonthCloseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CondoMonthCloseSerializer
    permission_classes = [IsAdminUser]
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
        except KeyError, ValueError, TypeError:
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


class ThirdPartySettlementViewSet(viewsets.ModelViewSet):
    """Acertos com terceiros — NEVER a bare ModelViewSet write path (design §4.4 / S80 §4c).

    A settlement is real cash leaving the condominium, and CondoMonthClose.cash_balance_end is
    frozen, so create/update/DELETE all route through ThirdPartySettlementService, which asserts
    the settlement month is open (an update guards the OLD month too). Skipping any of the three
    would silently corrupt a closed month's snapshot — the same bug class already fixed for
    payments (B3).
    """

    serializer_class = ThirdPartySettlementSerializer
    permission_classes = [IsAdminUser]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self) -> QuerySet[ThirdPartySettlement]:
        queryset = ThirdPartySettlement.objects.select_related("condominium", "person")
        params = self.request.query_params
        person_id = int_param(params, "person_id")
        if person_id is not None:
            queryset = queryset.filter(person_id=person_id)
        date_from = params.get("date_from")
        if date_from is not None:
            queryset = queryset.filter(settlement_date__gte=date_from)
        date_to = params.get("date_to")
        if date_to is not None:
            queryset = queryset.filter(settlement_date__lte=date_to)
        return queryset

    def perform_create(self, serializer: BaseSerializer[ThirdPartySettlement]) -> None:
        settlement = ThirdPartySettlement(**serializer.validated_data)
        ThirdPartySettlementService.create(settlement, user=cast(User, self.request.user))
        serializer.instance = settlement

    def perform_update(self, serializer: BaseSerializer[ThirdPartySettlement]) -> None:
        settlement = cast(ThirdPartySettlement, serializer.instance)
        previous_date = settlement.settlement_date
        for field, value in serializer.validated_data.items():
            setattr(settlement, field, value)
        ThirdPartySettlementService.update(
            settlement, previous_date, user=cast(User, self.request.user)
        )

    def perform_destroy(self, instance: ThirdPartySettlement) -> None:
        ThirdPartySettlementService.delete(instance, user=cast(User, self.request.user))


class ThirdPartyViewSet(viewsets.ViewSet):
    """Read-only third-party index + per-person statement (design §7).

    NOT cached, deliberately: both actions depend on today_sp() (which month counts as overdue),
    and a midnight rollover is not a write, so a cache would never invalidate — same reasoning as
    month_board and AccountStatementService.
    """

    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["get"])
    def people(self, request: Request) -> Response:
        today = today_sp()
        rows = [
            row
            for person_id, person_name in Person.objects.order_by("id").values_list("id", "name")
            if (row := _third_party_row(person_id, person_name, today)) is not None
        ]
        rows.sort(key=lambda row: Decimal(cast(str, row["total_em_aberto"])), reverse=True)
        return Response(rows, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def statement(self, request: Request) -> Response:
        raw_person_id = request.query_params.get("person_id")
        try:
            person = _person_or_400(raw_person_id)
        except ValidationError as exc:
            return Response({"error": str(exc.messages[0])}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ThirdPartyStatementService.build(person.pk, today_sp()), status=status.HTTP_200_OK
        )


def _third_party_row(person_id: int, person_name: str, today: date) -> dict[str, object] | None:
    """One index row, or None when the person owes nothing live (design §7).

    Built on ThirdPartyStatementService so the index and the statement can never disagree — the
    open/overdue totals shown on the card are literally the ones the extrato computes.
    """
    statement = ThirdPartyStatementService.build(person_id, today)
    totals = statement["totals"]
    if Decimal(totals["total_em_aberto"]) <= 0:
        return None
    last_settlement = (
        ThirdPartySettlement.objects.filter(person_id=person_id)
        .order_by("-settlement_date")
        .values_list("settlement_date", flat=True)
        .first()
    )
    return {
        "person_id": person_id,
        "person_name": person_name,
        "total_em_aberto": totals["total_em_aberto"],
        "total_atrasado": totals["total_atrasado"],
        "last_settlement_date": last_settlement,
    }
