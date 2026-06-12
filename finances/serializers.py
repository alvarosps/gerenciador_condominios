"""DRF serializers for the finances API (Session 38).

Dual pattern: FK read nested, write via ``<fk>_id`` (PrimaryKeyRelatedField,
write_only, allow_null for nullable FKs). Bill amount_* are read-only string Decimals
read from the Bill.objects.with_amounts(today) annotations via getattr (3-arg, so the
value is defensive and mypy/ruff stay clean) — never recomputed in Python (design §4.4).
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from rest_framework import serializers

from core.models import Building, Condominium, Lease, Person
from core.serializers import BuildingSerializer, LeaseSerializer, PersonSimpleSerializer
from core.services.timezone import today_sp
from finances.models import (
    _CONSUMPTION_TYPES,
    _EMBEDDED_NEEDS_CONSUMPTION_MSG,
    _ERR_BASE_SALARY_NEGATIVE,
    _ERR_FIXED_NEEDS_BASE,
    _ERR_IDENTIFIER_REQUIRED,
    _ERR_VARIABLE_NO_BASE,
    _TYPED_IDENTITY_ACCOUNT_TYPES,
    Bill,
    BillingAccount,
    BillingAccountType,
    BillLineItem,
    BillSkip,
    Category,
    CondoMonthClose,
    ElectricityBillStatement,
    Employee,
    EmployeePaymentType,
    IncomeEntry,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
    Payment,
    PaymentAllocation,
    Reserve,
    ReserveMovement,
    ReserveMovementKind,
    WaterBillStatement,
)
from finances.money import money_str

_ERR_DUPLICATE_BILLING_ACCOUNT = "Já existe uma conta ativa com este prédio, tipo e inscrição/UC."


def _apply_default_condominium(instance: object, attrs: dict[str, object]) -> None:
    """Inject the singleton condominium on create when ``condominium_id`` is omitted.

    The condominium is an invisible singleton with no client-side selector (design §15),
    so condo-scoped resources (reserve, income) default to ``Condominium.get_default()``
    exactly as ``Building.save`` does. On update the existing condominium is kept.
    """
    if instance is None and attrs.get("condominium") is None:
        default = Condominium.get_default()
        if default is None:
            raise serializers.ValidationError(
                {"condominium_id": Condominium.NOT_CONFIGURED_MESSAGE}
            )
        attrs["condominium"] = default


class CondominiumSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominium
        fields = ["id", "name"]
        read_only_fields = fields


class CategorySimpleSerializer(serializers.ModelSerializer):
    """Non-recursive read representation of a Category (used for parent)."""

    class Meta:
        model = Category
        fields = ["id", "name"]
        read_only_fields = fields


class CategorySerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(),
        source="condominium",
        write_only=True,
        required=False,
        allow_null=True,
    )
    parent = CategorySimpleSerializer(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="parent",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Category
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "parent",
            "parent_id",
            "name",
            "color",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # The (condominium, parent, name) uniqueness is a partial DB constraint; DRF's
        # auto UniqueTogetherValidator would wrongly force parent_id to always be present.
        validators: list[object] = []

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        # The condominium is an invisible singleton with no client-side selector (design §15);
        # the Categorias management UI never sends condominium_id, so default it on create exactly
        # as Bill/Reserve/IncomeEntry do (DRY).
        _apply_default_condominium(self.instance, attrs)
        return attrs


class BillingAccountSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(), source="condominium", write_only=True
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(),
        source="building",
        write_only=True,
        required=False,
        allow_null=True,
    )
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = BillingAccount
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "building",
            "building_id",
            "category",
            "category_id",
            "name",
            "external_identifier",
            "account_type",
            "holder_name",
            "registered_address",
            "secondary_identifier",
            "supply_status",
            "description",
            "default_due_day",
            "expected_amount",
            "lifecycle_state",
            "tracking_start_month",
            "end_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # The (building, account_type, external_identifier) uniqueness is a partial DB
        # constraint (is_deleted=False); DRF's auto UniqueTogetherValidator would wrongly
        # force building_id to always be present (a condo-level account has building=null).
        validators: list[object] = []

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Mirror BillingAccount.clean(): a typed account (water/power/IPTU) needs an
        inscrição/UC. Resolve account_type/external_identifier from the payload with a fallback
        to the existing instance (so a PATCH that only sets account_type is also caught)."""
        account_type = attrs.get("account_type")
        if account_type is None and self.instance is not None:
            account_type = self.instance.account_type
        external_identifier = attrs.get("external_identifier")
        if external_identifier is None and self.instance is not None:
            external_identifier = self.instance.external_identifier
        if (
            account_type in _TYPED_IDENTITY_ACCOUNT_TYPES
            and not str(external_identifier or "").strip()
        ):
            raise serializers.ValidationError({"external_identifier": _ERR_IDENTIFIER_REQUIRED})
        self._validate_identity_available(attrs)
        return attrs

    def _validate_identity_available(self, attrs: dict[str, object]) -> None:
        """Reject a duplicate active (building, account_type, external_identifier) identity.

        Mirrors the partial DB UniqueConstraint (is_deleted=False) so a clash returns a clean PT 400
        instead of an uncaught IntegrityError 500 (like LeaseSerializer._validate_apartment_available).
        Each component falls back to the existing instance on PATCH; the row being edited is excluded.
        """
        instance = self.instance

        def resolved(field: str, sentinel: object = None) -> object:
            if field in attrs:
                return attrs[field]
            return getattr(instance, field) if instance is not None else sentinel

        resolved_building = resolved("building")
        building = resolved_building if isinstance(resolved_building, Building) else None
        account_type = str(resolved("account_type") or "")
        external_identifier = str(resolved("external_identifier", "") or "")
        qs = BillingAccount.objects.filter(  # default manager excludes soft-deleted rows
            building=building,  # None matches the condominium-level (building IS NULL) slot
            account_type=account_type,
            external_identifier=external_identifier,
        )
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"external_identifier": _ERR_DUPLICATE_BILLING_ACCOUNT}
            )


class BillLineItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = BillLineItem
        fields = ["id", "category", "description", "amount", "is_offset"]
        read_only_fields = fields


class WaterBillStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterBillStatement
        fields = [
            "id",
            "consumo_m3",
            "leitura_anterior",
            "leitura_atual",
            "leitura_dias",
            "data_leitura",
            "agua_status",
            "esgoto_status",
        ]
        read_only_fields = fields


class ElectricityBillStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectricityBillStatement
        fields = [
            "id",
            "consumo_kwh",
            "energia_injetada_kwh",
            "leitura_anterior",
            "leitura_atual",
            "leitura_dias",
            "classe",
            "bandeira",
        ]
        read_only_fields = fields


class BillSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(),
        source="condominium",
        write_only=True,
        required=False,
        allow_null=True,
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(),
        source="building",
        write_only=True,
        required=False,
        allow_null=True,
    )
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    billing_account = BillingAccountSerializer(read_only=True)
    billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(),
        source="billing_account",
        write_only=True,
        required=False,
        allow_null=True,
    )
    line_items = BillLineItemSerializer(many=True, read_only=True)
    water_statement = serializers.SerializerMethodField()
    electricity_statement = serializers.SerializerMethodField()
    amount_total = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    account_type = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "building",
            "building_id",
            "category",
            "category_id",
            "competence_month",
            "due_date",
            "issue_date",
            "description",
            "external_identifier",
            "behavior",
            "billing_account",
            "billing_account_id",
            "lifecycle_state",
            "notes",
            "line_items",
            "water_statement",
            "electricity_statement",
            "amount_total",
            "amount_paid",
            "amount_remaining",
            "payment_status",
            "is_overdue",
            "account_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # The (billing_account, competence_month) uniqueness is a partial DB constraint;
        # DRF's auto UniqueTogetherValidator would wrongly force billing_account_id to be
        # present on every write (avulsa bills have billing_account=None).
        validators: list[object] = []

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        # The condominium is an invisible singleton with no client-side selector (design §15);
        # the parse-invoice draft + the bill modal never send condominium_id, so default it on
        # create exactly as ReserveSerializer/IncomeEntrySerializer do (DRY).
        _apply_default_condominium(self.instance, attrs)
        return attrs

    def validate_competence_month(self, value: date) -> date:
        # DRF.create() does not call Model.clean(); normalize to the 1st here too.
        return value.replace(day=1)

    def get_water_statement(self, obj: Bill) -> dict[str, object] | None:
        # The reverse OneToOne is loaded via _base_manager (select_related), so a soft-deleted
        # statement is still attached — exclude it explicitly so a hidden bill never exposes one.
        try:
            statement = obj.water_statement
        except ObjectDoesNotExist:
            return None
        if statement.is_deleted:
            return None
        return WaterBillStatementSerializer(statement).data

    def get_electricity_statement(self, obj: Bill) -> dict[str, object] | None:
        try:
            statement = obj.electricity_statement
        except ObjectDoesNotExist:
            return None
        if statement.is_deleted:
            return None
        return ElectricityBillStatementSerializer(statement).data

    def get_amount_total(self, obj: Bill) -> str:
        return money_str(getattr(obj, "amount_total", Decimal(0)))

    def get_amount_paid(self, obj: Bill) -> str:
        return money_str(getattr(obj, "amount_paid", Decimal(0)))

    def get_amount_remaining(self, obj: Bill) -> str:
        return money_str(getattr(obj, "amount_remaining", Decimal(0)))

    def get_payment_status(self, obj: Bill) -> str:
        return str(getattr(obj, "payment_status", "open"))

    def get_is_overdue(self, obj: Bill) -> bool:
        return bool(getattr(obj, "is_overdue", False))

    def get_account_type(self, obj: Bill) -> str:
        # Structural type for the "Tipo" column. A recurring água/luz Bill links the account
        # directly; a standalone IPTU parcela Bill has billing_account=None and reaches the IPTU
        # account via installment→plan; an avulsa one_time Bill has neither → generic.
        if obj.billing_account is not None:
            return obj.billing_account.account_type
        if obj.installment is not None and obj.installment.plan.billing_account is not None:
            return obj.installment.plan.billing_account.account_type
        return BillingAccountType.GENERIC.value


class BillSkipSerializer(serializers.ModelSerializer):
    billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(), source="billing_account", write_only=True
    )

    class Meta:
        model = BillSkip
        fields = ["id", "billing_account", "billing_account_id", "reference_month"]
        read_only_fields = ["id", "billing_account"]

    def validate_reference_month(self, value: date) -> date:
        # DRF.create() does not call Model.clean(); normalize to the 1st here too (mirrors
        # BillSkip.clean + BillSerializer.validate_competence_month) so the (account, month)
        # uniqueness and the generation lookup match regardless of the day sent.
        return value.replace(day=1)


class PaymentAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAllocation
        fields = ["id", "bill", "amount"]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(), source="condominium", write_only=True
    )
    allocations = PaymentAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "payment_date",
            "amount",
            "method",
            "funded_from",
            "reference",
            "notes",
            "allocations",
            "created_at",
            "updated_at",
        ]
        # amount and funded_from are set EXCLUSIVELY by BillPaymentService.pay (which also writes the
        # matching PaymentAllocation rows and any reserve withdrawal). Editing them here would desync
        # Σ(allocation) from amount and create a reserve ghost (§4.8), so they are read-only — a
        # payment's value/funding only changes via unpay() + pay().
        read_only_fields = ["id", "amount", "funded_from", "created_at", "updated_at"]


class InstallmentSerializer(serializers.ModelSerializer):
    """Installment schedule row. amount is the schedule (editable); is_overdue is computed."""

    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Installment
        fields = ["id", "plan", "number", "due_date", "amount", "is_overdue"]
        read_only_fields = ["id", "plan", "number"]

    def get_is_overdue(self, obj: Installment) -> bool:
        # No "paid" semantics on Installment (the realized side lives on BillLineItem, S41);
        # overdue = past due AND the plan is still ACTIVE or MATERIALIZED (a fully materialized
        # plan whose parcela bill is unpaid is still overdue — MATERIALIZED ≠ pago, P2.3 step 9).
        return obj.due_date < today_sp() and obj.plan.lifecycle_state in (
            InstallmentPlanState.ACTIVE,
            InstallmentPlanState.MATERIALIZED,
        )


class InstallmentPlanSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(),
        source="condominium",
        write_only=True,
        required=False,
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(),
        source="building",
        write_only=True,
        required=False,
        allow_null=True,
    )
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    billing_account = BillingAccountSerializer(read_only=True)
    billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(),
        source="billing_account",
        write_only=True,
        required=False,
        allow_null=True,
    )
    installments = InstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = InstallmentPlan
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "building",
            "building_id",
            "category",
            "category_id",
            "billing_account",
            "billing_account_id",
            "description",
            "total_amount",
            "installment_count",
            "start_due_date",
            "default_due_day",
            "lifecycle_state",
            "embedded",
            "notes",
            "installments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        # The InstallmentPlan form never sends condominium_id (singleton), so default it on create.
        _apply_default_condominium(self.instance, attrs)
        # DRF does not call Model.clean(); mirror the embedded->consumption-account invariant
        # (design §4) so the API cannot create an inconsistent plan. Single source of the rule
        # is the model (_CONSUMPTION_TYPES / message), re-expressed here only because DRF skips clean().
        embedded = attrs.get("embedded", getattr(self.instance, "embedded", False))
        account = attrs.get("billing_account", getattr(self.instance, "billing_account", None))
        if embedded and (
            not isinstance(account, BillingAccount)
            or account.account_type not in _CONSUMPTION_TYPES
        ):
            raise serializers.ValidationError(
                {"billing_account_id": _EMBEDDED_NEEDS_CONSUMPTION_MSG}
            )
        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(),
        source="condominium",
        write_only=True,
        required=False,
    )
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="person",
        write_only=True,
        required=False,
        allow_null=True,
    )
    lease = LeaseSerializer(read_only=True)
    lease_id = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.all(),
        source="lease",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "person",
            "person_id",
            "lease",
            "lease_id",
            "name",
            "role",
            "payment_type",
            "base_salary",
            "default_due_day",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        # The Employee form never sends condominium_id (singleton), so default it on create.
        _apply_default_condominium(self.instance, attrs)
        # DRF skips Model.clean(); mirror Employee.clean()'s payroll invariants so the API
        # returns a clean 400 instead of accepting an invalid record (or a 500 on the
        # negative-salary CheckConstraint). Single source of the rules is the model.
        payment_type = attrs.get("payment_type", getattr(self.instance, "payment_type", None))
        raw_salary = attrs.get("base_salary", getattr(self.instance, "base_salary", None))
        base_salary = raw_salary if isinstance(raw_salary, Decimal) else None
        if base_salary is not None and base_salary < 0:
            raise serializers.ValidationError({"base_salary": _ERR_BASE_SALARY_NEGATIVE})
        needs_base = payment_type in (EmployeePaymentType.FIXED, EmployeePaymentType.MIXED)
        if needs_base and (base_salary is None or base_salary <= 0):
            raise serializers.ValidationError({"base_salary": _ERR_FIXED_NEEDS_BASE})
        if (
            payment_type == EmployeePaymentType.VARIABLE
            and base_salary is not None
            and base_salary > 0
        ):
            raise serializers.ValidationError({"base_salary": _ERR_VARIABLE_NO_BASE})
        return attrs


class ReserveSimpleSerializer(serializers.ModelSerializer):
    """Non-recursive read representation of a Reserve (used inside a movement)."""

    class Meta:
        model = Reserve
        fields = ["id", "name"]
        read_only_fields = fields


class ReserveSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(),
        source="condominium",
        write_only=True,
        required=False,
    )
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Reserve
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "name",
            "notes",
            "balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        _apply_default_condominium(self.instance, attrs)
        return attrs

    def get_balance(self, obj: Reserve) -> str:
        # Reserve-scoped ledger balance (deposits - withdrawals) via the model relation only
        # (architecture rule: serializers read models, never services). money_str at the boundary.
        deposits = obj.movements.filter(kind=ReserveMovementKind.DEPOSIT).aggregate(
            total=Sum("amount")
        )["total"] or Decimal(0)
        withdrawals = obj.movements.filter(kind=ReserveMovementKind.WITHDRAWAL).aggregate(
            total=Sum("amount")
        )["total"] or Decimal(0)
        return money_str(deposits - withdrawals)


class ReserveMovementSerializer(serializers.ModelSerializer):
    reserve = ReserveSimpleSerializer(read_only=True)

    class Meta:
        model = ReserveMovement
        fields = [
            "id",
            "reserve",
            "kind",
            "amount",
            "movement_date",
            "bill",
            "payment",
            "reference",
            "notes",
            "created_at",
            "updated_at",
        ]
        # Read-only ledger: movements are written ONLY via reserves/{id}/deposit|withdraw, where
        # ReserveService enforces the never-negative guard (design §4.3/§18). The viewset is a
        # ReadOnlyModelViewSet, so exposing a write path here (which would bypass that guard) is
        # neither offered nor needed — every field is read-only. bill is a PK on read (set =
        # withdrawal to pay a bill, null = cash transfer); payment is the deterministic link to
        # the driving Payment (null for a manual cash transfer — P2.3 step 10).
        read_only_fields = fields


class IncomeEntrySerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(),
        source="condominium",
        write_only=True,
        required=False,
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(),
        source="building",
        write_only=True,
        required=False,
        allow_null=True,
    )
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = IncomeEntry
        fields = [
            "id",
            "condominium",
            "condominium_id",
            "building",
            "building_id",
            "category",
            "category_id",
            "description",
            "amount",
            "income_date",
            "is_received",
            "received_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        # DRF does not call Model.clean(); mirror the is_received <-> received_date invariant.
        _apply_default_condominium(self.instance, attrs)
        is_received = attrs.get("is_received", getattr(self.instance, "is_received", False))
        received_date = attrs.get("received_date", getattr(self.instance, "received_date", None))
        if is_received and received_date is None:
            raise serializers.ValidationError(
                {"received_date": "Informe a data de recebimento quando a receita está recebida."}
            )
        if not is_received and received_date is not None:
            raise serializers.ValidationError(
                {"received_date": "A data de recebimento só se aplica a receitas recebidas."}
            )
        return attrs


class CondoMonthCloseSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)

    class Meta:
        model = CondoMonthClose
        # Fully read-only: the viewset is a ReadOnlyModelViewSet and the only write path is
        # condo-month-closes/{close,reopen} (the service computes every frozen figure). A
        # snapshot's identity (condominium, reference_month) is immutable once frozen, so neither
        # is writable here — the serializer serializes responses, it never persists (P2.3 step 5).
        fields = [
            "id",
            "condominium",
            "reference_month",
            "status",
            "closed_at",
            "net_result",
            "cash_balance_end",
            "reserve_balance_end",
            "carry_forward_out",
            "breakdown",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
