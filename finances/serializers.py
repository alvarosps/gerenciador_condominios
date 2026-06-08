"""DRF serializers for the finances API (Session 38).

Dual pattern: FK read nested, write via ``<fk>_id`` (PrimaryKeyRelatedField,
write_only, allow_null for nullable FKs). Bill amount_* are read-only string Decimals
read from the Bill.objects.with_amounts(today) annotations via getattr (3-arg, so the
value is defensive and mypy/ruff stay clean) — never recomputed in Python (design §4.4).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from core.models import Building, Condominium, Lease, Person
from core.serializers import BuildingSerializer, LeaseSerializer, PersonSimpleSerializer
from finances.models import (
    Bill,
    BillingAccount,
    BillLineItem,
    BillSkip,
    Category,
    CondoMonthClose,
    Employee,
    IncomeEntry,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
    Payment,
    PaymentAllocation,
    Reserve,
    ReserveMovement,
    ReserveMovementKind,
)
from finances.money import money_str
from finances.services.timezone import today_sp


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
        queryset=Condominium.objects.all(), source="condominium", write_only=True
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


class BillLineItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = BillLineItem
        fields = ["id", "category", "description", "amount", "is_offset"]
        read_only_fields = fields


class BillSerializer(serializers.ModelSerializer):
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
    billing_account = BillingAccountSerializer(read_only=True)
    billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(),
        source="billing_account",
        write_only=True,
        required=False,
        allow_null=True,
    )
    line_items = BillLineItemSerializer(many=True, read_only=True)
    amount_total = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

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
            "amount_total",
            "amount_paid",
            "amount_remaining",
            "payment_status",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # The (billing_account, competence_month) uniqueness is a partial DB constraint;
        # DRF's auto UniqueTogetherValidator would wrongly force billing_account_id to be
        # present on every write (avulsa bills have billing_account=None).
        validators: list[object] = []

    def validate_competence_month(self, value: date) -> date:
        # DRF.create() does not call Model.clean(); normalize to the 1st here too.
        return value.replace(day=1)

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


class BillSkipSerializer(serializers.ModelSerializer):
    billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(), source="billing_account", write_only=True
    )

    class Meta:
        model = BillSkip
        fields = ["id", "billing_account", "billing_account_id", "reference_month"]
        read_only_fields = ["id", "billing_account"]


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
        read_only_fields = ["id", "created_at", "updated_at"]


class InstallmentSerializer(serializers.ModelSerializer):
    """Installment schedule row. amount is the schedule (editable); is_overdue is computed."""

    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Installment
        fields = ["id", "plan", "number", "due_date", "amount", "is_overdue"]
        read_only_fields = ["id", "plan", "number"]

    def get_is_overdue(self, obj: Installment) -> bool:
        # No "paid" semantics on Installment (the realized side lives on BillLineItem, S41);
        # overdue = past due AND the plan is still active.
        return obj.due_date < today_sp() and obj.plan.lifecycle_state == InstallmentPlanState.ACTIVE


class InstallmentPlanSerializer(serializers.ModelSerializer):
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
    linked_billing_account = BillingAccountSerializer(read_only=True)
    linked_billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(),
        source="linked_billing_account",
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
            "linked_billing_account",
            "linked_billing_account_id",
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
        # DRF does not call Model.clean(); mirror the embedded <-> linked invariant (design §7)
        # so the API cannot create an inconsistent plan.
        embedded = attrs.get("embedded", getattr(self.instance, "embedded", False))
        linked = attrs.get(
            "linked_billing_account", getattr(self.instance, "linked_billing_account", None)
        )
        if embedded and linked is None:
            raise serializers.ValidationError(
                {
                    "linked_billing_account_id": "Plano embutido exige uma conta recorrente vinculada."
                }
            )
        if not embedded and linked is not None:
            raise serializers.ValidationError(
                {
                    "linked_billing_account_id": "Plano avulso não pode ter conta recorrente vinculada."
                }
            )
        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    condominium = CondominiumSimpleSerializer(read_only=True)
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(), source="condominium", write_only=True
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
    reserve_id = serializers.PrimaryKeyRelatedField(
        queryset=Reserve.objects.all(), source="reserve", write_only=True
    )
    bill_id = serializers.PrimaryKeyRelatedField(
        queryset=Bill.objects.all(),
        source="bill",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ReserveMovement
        fields = [
            "id",
            "reserve",
            "reserve_id",
            "kind",
            "amount",
            "movement_date",
            "bill",
            "bill_id",
            "reference",
            "notes",
            "created_at",
            "updated_at",
        ]
        # bill is exposed as a PK on read (set = withdrawal to pay a bill, null = cash transfer).
        # The canonical write path is reserves/{id}/deposit|withdraw (the balance guard lives in
        # the service); direct create is admin-only and unguarded by design.
        read_only_fields = ["id", "bill", "created_at", "updated_at"]


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
    condominium_id = serializers.PrimaryKeyRelatedField(
        queryset=Condominium.objects.all(), source="condominium", write_only=True
    )

    class Meta:
        model = CondoMonthClose
        fields = [
            "id",
            "condominium",
            "condominium_id",
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
        # The canonical write path is condo-month-closes/{close,reopen}; the frozen figures are
        # computed by the service, never set directly through the serializer.
        read_only_fields = [
            "id",
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
