"""DRF serializers for the finances API (Session 38).

Dual pattern: FK read nested, write via ``<fk>_id`` (PrimaryKeyRelatedField,
write_only, allow_null for nullable FKs). Bill amount_* are read-only string Decimals
read from the Bill.objects.with_amounts(today) annotations via getattr (3-arg, so the
value is defensive and mypy/ruff stay clean) — never recomputed in Python (design §4.4).
"""

from datetime import date
from decimal import Decimal

from rest_framework import serializers

from core.models import Building, Condominium, Lease, Person
from core.serializers import BuildingSerializer, LeaseSerializer, PersonSimpleSerializer
from finances.models import (
    Bill,
    BillingAccount,
    BillLineItem,
    BillSkip,
    Category,
    Employee,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
    Payment,
    PaymentAllocation,
)
from finances.money import money_str
from finances.services.timezone import today_sp


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
