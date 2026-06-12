from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from core.validators import BrazilianPhoneValidator, CNPJValidator, CPFValidator, validate_due_day
from core.validators.upload import validate_proof_file

from .models import (
    DOUBLE_OCCUPANCY,
    Apartment,
    Building,
    ContractRule,
    CreditCard,
    Dependent,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    ExpenseMonthSkip,
    FinancialSettings,
    Furniture,
    Income,
    Landlord,
    Lease,
    MonthSnapshot,
    Notification,
    PaymentProof,
    Person,
    PersonIncome,
    PersonPayment,
    PersonPaymentSchedule,
    RentAdjustment,
    RentPayment,
    Tenant,
)

User = get_user_model()

# Mirrors the DB UniqueConstraint (unique_active_lease_per_apartment, condition is_deleted=False):
# an apartment may have at most one active (non-soft-deleted) lease. Surfaced as a clean 400
# instead of letting the constraint raise IntegrityError 500. Reused by the onboarding service.
APARTMENT_ALREADY_LEASED_ERROR = "Este apartamento já possui um contrato ativo."

# Transient attribute set by TenantSerializer on the created/updated Tenant, holding the
# Dependent instances created during this save() in input order (the model has no Meta.ordering).
# Consumed by the onboarding service to resolve a newly-created resident dependent by index.
_CREATED_DEPENDENTS_ATTR = "_created_dependents"

REFERENCE_MONTH_FIRST_DAY_ERROR = "O mês de referência deve ser o primeiro dia do mês."
_POSITIVE_AMOUNT_ERROR = "O valor deve ser positivo."


def _validate_first_day_of_month(value: date) -> date:
    """Ensure a reference month is anchored to the first day of the month."""
    if value.day != 1:
        raise serializers.ValidationError(REFERENCE_MONTH_FIRST_DAY_ERROR)
    return value


class BuildingSerializer(serializers.ModelSerializer):
    # Uniqueness of street_number among active buildings is enforced by DRF's auto-generated
    # UniqueValidator, whose queryset already excludes soft-deleted rows (it mirrors the partial
    # unique_active_building_street_number constraint) — a clean 400, and a soft-deleted number is
    # reusable.
    class Meta:
        model = Building
        fields = "__all__"


class FurnitureSerializer(serializers.ModelSerializer):
    # Same as BuildingSerializer: the partial unique_active_furniture_name constraint yields a
    # soft-delete-aware UniqueValidator on name automatically.
    class Meta:
        model = Furniture
        fields = "__all__"


class PersonSimpleSerializer(serializers.ModelSerializer):
    """Simplified PersonSerializer without credit_cards to avoid recursion."""

    class Meta:
        model = Person
        fields = [
            "id",
            "name",
            "relationship",
            "phone",
            "email",
            "is_owner",
            "is_employee",
            "notes",
        ]


class TenantSimpleSerializer(serializers.ModelSerializer):
    """Simplified TenantSerializer with only id and name."""

    class Meta:
        model = Tenant
        fields = ["id", "name"]
        read_only_fields = fields


class TenantSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for tenant references in other serializers."""

    class Meta:
        model = Tenant
        fields = ["id", "name", "cpf_cnpj", "phone", "due_day"]
        read_only_fields = fields


class LeaseNestedForApartmentSerializer(serializers.ModelSerializer):
    """Lightweight lease info for embedding in ApartmentSerializer."""

    responsible_tenant = TenantSimpleSerializer(read_only=True)

    class Meta:
        model = Lease
        fields = [
            "id",
            "contract_generated",
            "contract_signed",
            "interfone_configured",
            "start_date",
            "validity_months",
            "rental_value",
            "pending_rental_value",
            "pending_rental_value_date",
            "responsible_tenant",
        ]
        read_only_fields = fields


class ApartmentSerializer(serializers.ModelSerializer):
    furnitures = FurnitureSerializer(many=True, read_only=True)
    furniture_ids = serializers.PrimaryKeyRelatedField(
        queryset=Furniture.objects.all(), many=True, write_only=True, required=False
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), source="building", write_only=True
    )
    owner = PersonSimpleSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="owner",
        write_only=True,
        required=False,
        allow_null=True,
    )
    active_lease = serializers.SerializerMethodField()

    class Meta:
        model = Apartment
        fields = [
            "id",
            "building",
            "building_id",
            "number",
            "rental_value",
            "rental_value_double",
            "cleaning_fee",
            "max_tenants",
            "is_rented",
            "last_rent_increase_date",
            "furnitures",
            "furniture_ids",
            "owner",
            "owner_id",
            "active_lease",
        ]
        read_only_fields = ["is_rented"]

    def get_active_lease(self, obj: Apartment) -> dict[str, Any] | None:
        """Return the active (non-deleted) lease for this apartment, if any."""
        # Use all() to leverage prefetch cache (first() bypasses it)
        lease = next(iter(obj.leases.all()), None)
        if lease is None:
            return None
        return LeaseNestedForApartmentSerializer(lease).data

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for rental_value_double when max_tenants == 2."""
        attrs = super().validate(attrs)

        max_tenants = attrs.get(
            "max_tenants",
            getattr(self.instance, "max_tenants", None) if self.instance else None,
        )
        rental_value_double = attrs.get(
            "rental_value_double",
            getattr(self.instance, "rental_value_double", None) if self.instance else None,
        )
        rental_value = attrs.get(
            "rental_value",
            getattr(self.instance, "rental_value", None) if self.instance else None,
        )

        if max_tenants == DOUBLE_OCCUPANCY and rental_value_double is None:
            raise serializers.ValidationError(
                {"rental_value_double": "Obrigatório quando max_tenants é 2."}
            )

        if (
            rental_value_double is not None
            and rental_value is not None
            and rental_value_double < rental_value
        ):
            raise serializers.ValidationError(
                {"rental_value_double": ("rental_value_double deve ser >= rental_value.")}
            )

        # (building, number) uniqueness is enforced by DRF's auto-generated
        # UniqueTogetherValidator, whose queryset already excludes soft-deleted rows (matching the
        # partial unique_active_apartment_per_building constraint) — so a soft-deleted number can
        # be reused and an active duplicate yields a clean 400 (non_field_errors), never a 500.

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Apartment:
        """Create apartment with furniture relationships."""
        furniture_ids = validated_data.pop("furniture_ids", [])
        apartment = Apartment(**validated_data)
        apartment.full_clean()
        apartment.save()
        if furniture_ids:
            apartment.furnitures.set(furniture_ids)
        return apartment

    def update(self, instance: Apartment, validated_data: dict[str, Any]) -> Apartment:
        """Update apartment with furniture relationships."""
        furniture_ids = validated_data.pop("furniture_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()

        if furniture_ids is not None:
            instance.furnitures.set(furniture_ids)

        return instance


class DependentSerializer(serializers.ModelSerializer):
    # Make id writable for update operations (allows identifying existing dependents)
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Dependent
        fields = ["id", "tenant", "name", "phone", "cpf_cnpj"]
        read_only_fields = ["tenant"]  # tenant is set by parent in nested creation

    def validate_phone(self, value: str) -> str:
        """Validate Brazilian phone number format."""
        if value:
            BrazilianPhoneValidator()(value)
        return value

    def validate_cpf_cnpj(self, value: str) -> str:
        """Validate CPF for dependent (individuals only)."""
        if value:
            try:
                CPFValidator()(value)
            except serializers.ValidationError as e:
                raise serializers.ValidationError(str(e)) from e
        return value


class TenantSerializer(serializers.ModelSerializer):
    dependents = DependentSerializer(many=True, required=False)
    furnitures = FurnitureSerializer(many=True, read_only=True)
    furniture_ids = serializers.PrimaryKeyRelatedField(
        queryset=Furniture.objects.all(), many=True, write_only=True, required=False
    )
    # Declared explicitly with no auto UniqueValidator: uniqueness must be checked against the
    # NORMALIZED (digits-only) value in validate() — DRF's auto validator would compare the raw
    # input ("529.982.247-25") against stored digits and miss the collision. max_length mirrors
    # the model field.
    cpf_cnpj = serializers.CharField(max_length=20)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "cpf_cnpj",
            "is_company",
            "rg",
            "phone",
            "marital_status",
            "profession",
            "due_day",
            "warning_count",
            "dependents",
            "furnitures",
            "furniture_ids",
        ]

    def validate_phone(self, value: str) -> str:
        """Validate Brazilian phone number format."""
        if value:
            BrazilianPhoneValidator()(value)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for CPF/CNPJ based on is_company flag."""
        attrs = super().validate(attrs)

        cpf_cnpj = attrs.get(
            "cpf_cnpj", getattr(self.instance, "cpf_cnpj", None) if self.instance else None
        )
        is_company = attrs.get(
            "is_company", getattr(self.instance, "is_company", False) if self.instance else False
        )

        if cpf_cnpj:
            validator = CNPJValidator() if is_company else CPFValidator()
            try:
                cleaned = validator(cpf_cnpj)
            except serializers.ValidationError as e:
                raise serializers.ValidationError({"cpf_cnpj": str(e)}) from e
            self._validate_unique_cpf_cnpj(cleaned)

        return attrs

    def _validate_unique_cpf_cnpj(self, cleaned: str | None) -> None:
        """Reject a CPF/CNPJ already held by another active tenant.

        Compares against the normalized (digits-only) form so a formatted value and its raw form
        are the same identity. The DB uniqueness is a partial constraint (active rows only), so
        this surfaces a clean 400 and lets a soft-deleted tenant's document be reused.
        """
        if not cleaned:
            return
        qs = Tenant.objects.filter(cpf_cnpj=cleaned)  # SoftDeleteManager excludes deleted
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"cpf_cnpj": "Já existe um inquilino com este CPF/CNPJ."}
            )

    @staticmethod
    def _create_dependent(
        tenant: Tenant, dep_data: dict[str, Any], validated_data: dict[str, Any]
    ) -> Dependent:
        """Create a Dependent, propagating audit fields from the parent save() kwargs.

        created_by/updated_by arrive in validated_data when the caller uses
        serializer.save(created_by=user, updated_by=user); they are None when omitted.
        """
        return Dependent.objects.create(
            tenant=tenant,
            created_by=validated_data.get("created_by"),
            updated_by=validated_data.get("updated_by"),
            **dep_data,
        )

    def create(self, validated_data: dict[str, Any]) -> Tenant:
        dependents_data = validated_data.pop("dependents", [])
        furniture_ids = validated_data.pop("furniture_ids", [])
        tenant = Tenant(**validated_data)
        tenant.full_clean()
        tenant.save()
        if furniture_ids:
            tenant.furnitures.set(furniture_ids)
        # Capture created dependents in input order so callers can resolve one by index
        # (the model has no Meta.ordering); also propagate created_by/updated_by.
        created = [
            self._create_dependent(tenant, dep_data, validated_data) for dep_data in dependents_data
        ]
        setattr(tenant, _CREATED_DEPENDENTS_ATTR, created)
        return tenant

    def update(self, instance: Tenant, validated_data: dict[str, Any]) -> Tenant:
        dependents_data = validated_data.pop("dependents", None)
        furniture_ids = validated_data.pop("furniture_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()

        if furniture_ids is not None:
            instance.furnitures.set(furniture_ids)

        created: list[Dependent] = []
        if dependents_data is not None:
            # Smart update: only delete removed dependents, update existing, create new
            existing_ids = {d.id for d in instance.dependents.all()}
            provided_ids = {d.get("id") for d in dependents_data if d.get("id")}

            # Delete only dependents that were removed (not in provided list)
            to_delete = existing_ids - provided_ids
            if to_delete:
                instance.dependents.filter(id__in=to_delete).delete()

            # Update existing or create new dependents
            for dep_data in dependents_data:
                dep_id = dep_data.pop("id", None)
                if dep_id and dep_id in existing_ids:
                    # Update existing dependent
                    instance.dependents.filter(id=dep_id).update(**dep_data)
                else:
                    # Create new dependent (audit propagated, captured in input order)
                    created.append(self._create_dependent(instance, dep_data, validated_data))

        setattr(instance, _CREATED_DEPENDENTS_ATTR, created)
        return instance


class LeaseSerializer(serializers.ModelSerializer):
    apartment = ApartmentSerializer(read_only=True)
    apartment_id = serializers.PrimaryKeyRelatedField(
        queryset=Apartment.objects.all(), source="apartment", write_only=True
    )
    responsible_tenant = TenantSummarySerializer(read_only=True)
    responsible_tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), source="responsible_tenant", write_only=True
    )
    tenants = TenantSummarySerializer(many=True, read_only=True)
    tenant_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), many=True, source="tenants", write_only=True
    )
    resident_dependent = DependentSerializer(read_only=True)
    resident_dependent_id = serializers.PrimaryKeyRelatedField(
        queryset=Dependent.objects.all(),
        source="resident_dependent",
        write_only=True,
        required=False,
        allow_null=True,
    )
    rental_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Valor do aluguel acordado. Se omitido, deriva do apartamento.",
    )

    class Meta:
        model = Lease
        fields = [
            "id",
            "apartment",
            "apartment_id",
            "responsible_tenant",
            "responsible_tenant_id",
            "tenants",
            "tenant_ids",
            "number_of_tenants",
            "resident_dependent",
            "resident_dependent_id",
            "start_date",
            "validity_months",
            "tag_fee",
            "rental_value",
            "last_rent_increase_date",
            "pending_rental_value",
            "pending_rental_value_date",
            "deposit_amount",
            "cleaning_fee_paid",
            "tag_deposit_paid",
            "contract_generated",
            "contract_signed",
            "interfone_configured",
            "prepaid_until",
            "is_salary_offset",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for number_of_tenants and resident_dependent."""
        attrs = super().validate(attrs)

        number_of_tenants = attrs.get(
            "number_of_tenants",
            getattr(self.instance, "number_of_tenants", 1) if self.instance else 1,
        )

        if number_of_tenants not in (1, DOUBLE_OCCUPANCY):
            raise serializers.ValidationError({"number_of_tenants": "Deve ser 1 ou 2."})

        apartment = attrs.get(
            "apartment",
            getattr(self.instance, "apartment", None) if self.instance else None,
        )
        if apartment is not None and number_of_tenants > apartment.max_tenants:
            raise serializers.ValidationError(
                {
                    "number_of_tenants": (
                        f"Número de ocupantes ({number_of_tenants}) excede o máximo "
                        f"permitido pelo apartamento ({apartment.max_tenants})."
                    )
                }
            )

        if number_of_tenants == DOUBLE_OCCUPANCY:
            resident_dependent = attrs.get("resident_dependent")

            if resident_dependent is not None:
                responsible_tenant = attrs.get(
                    "responsible_tenant",
                    getattr(self.instance, "responsible_tenant", None) if self.instance else None,
                )
                if (
                    responsible_tenant is not None
                    and resident_dependent.tenant_id != responsible_tenant.id
                ):
                    raise serializers.ValidationError(
                        {
                            "resident_dependent_id": (
                                "O dependente deve pertencer ao inquilino responsável."
                            )
                        }
                    )

        self._validate_apartment_available(apartment)

        return attrs

    def _validate_apartment_available(self, apartment: Apartment | None) -> None:
        """Reject an apartment that already has an active (non-soft-deleted) lease.

        Mirrors the DB UniqueConstraint condition (is_deleted=False) so callers get a clean,
        namespaced 400 instead of an IntegrityError 500. On edit, the lease being updated does
        not count against itself.
        """
        if apartment is None:
            return

        qs = Lease.objects.filter(apartment=apartment)  # SoftDeleteManager excludes deleted
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({"apartment": [APARTMENT_ALREADY_LEASED_ERROR]})

    def update(self, instance: Lease, validated_data: dict[str, Any]) -> Lease:
        """Update lease with tenant relationships.

        The apartment's last_rent_increase_date is synced by LeaseViewSet.perform_update
        (Views -> Services), keeping business logic out of the serializer.
        """
        tenants = validated_data.pop("tenants", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()

        if tenants is not None:
            instance.tenants.set(tenants)

        return instance


class TransferLeaseSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate the transfer payload so missing/invalid fields are a 400, not a KeyError 500.

    The transfer service (``transfer_lease``) reads these keys directly; this serializer
    guarantees their presence/types before that call. Business rules (tenant existence,
    target apartment already leased) stay in the service and surface as ValueError -> 400.
    """

    apartment_id = serializers.IntegerField()
    responsible_tenant_id = serializers.IntegerField()
    tenant_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    validity_months = serializers.IntegerField(required=False, min_value=1, default=12)
    start_date = serializers.DateField(required=False)
    rental_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    deposit_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    tag_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    cleaning_fee_paid = serializers.BooleanField(required=False, default=False)
    tag_deposit_paid = serializers.BooleanField(required=False, default=False)


class LandlordSerializer(serializers.ModelSerializer):
    """
    Serializer for Landlord model with full address property.

    Used for landlord (LOCADOR) configuration management.
    Provides validation for CPF/CNPJ fields.
    """

    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Landlord
        fields = [
            "id",
            "name",
            "nationality",
            "marital_status",
            "cpf_cnpj",
            "rg",
            "phone",
            "email",
            "street",
            "street_number",
            "complement",
            "neighborhood",
            "city",
            "state",
            "zip_code",
            "country",
            "rent_adjustment_percentage",
            "is_active",
            "full_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "full_address"]

    def validate_cpf_cnpj(self, value: str) -> str:
        """Validate CPF or CNPJ format."""
        if value:
            # Try CPF first, then CNPJ
            try:
                CPFValidator()(value)
            except serializers.ValidationError:
                try:
                    CNPJValidator()(value)
                except serializers.ValidationError as exc:
                    msg = "CPF ou CNPJ inválido"
                    raise serializers.ValidationError(msg) from exc
        return value

    def validate_phone(self, value: str) -> str:
        """Validate Brazilian phone number format."""
        if value:
            BrazilianPhoneValidator()(value)
        return value


class ContractRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for ContractRule model.

    Used for managing condominium rules that appear in rental contracts.
    """

    class Meta:
        model = ContractRule
        fields = [
            "id",
            "content",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContractRuleReorderSerializer(serializers.Serializer):
    """
    Serializer for bulk reordering of contract rules.
    """

    rule_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="Lista ordenada de IDs das regras"
    )


class RentAdjustmentSerializer(serializers.ModelSerializer):
    """Read-only serializer for rent adjustment history."""

    lease_summary = serializers.SerializerMethodField()

    class Meta:
        model = RentAdjustment
        fields = [
            "id",
            "lease",
            "lease_summary",
            "adjustment_date",
            "percentage",
            "previous_value",
            "new_value",
            "apartment_updated",
            "created_at",
            "created_by",
        ]
        read_only_fields = fields

    def get_lease_summary(self, obj: RentAdjustment) -> dict[str, Any]:
        return {
            "apartment_number": obj.lease.apartment.number,
            "building_name": obj.lease.apartment.building.name,
            "tenant_name": obj.lease.responsible_tenant.name,
        }


# =============================================================================
# FINANCIAL MODULE SERIALIZERS
# =============================================================================


class FinalizedMonthProtectionMixin(serializers.Serializer):
    """Prevents modification of financial data in finalized months."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)

        reference_month = self._get_reference_month(attrs)
        if reference_month is None:
            return attrs

        is_finalized = MonthSnapshot.objects.filter(
            reference_month=reference_month, is_finalized=True
        ).exists()

        if is_finalized:
            month_label = reference_month.strftime("%m/%Y")
            msg = f"O mês {month_label} está finalizado. Use rollback para reabrir antes de editar."
            raise serializers.ValidationError(msg)

        return attrs

    def _get_reference_month(self, attrs: dict[str, Any]) -> date | None:
        """Override in subclasses to extract the relevant month."""
        return None


class PersonSerializer(serializers.ModelSerializer):
    credit_cards = serializers.SerializerMethodField()
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Person
        fields = [
            "id",
            "name",
            "relationship",
            "phone",
            "email",
            "is_owner",
            "is_employee",
            "initial_balance",
            "initial_balance_date",
            "user",
            "user_id",
            "notes",
            "pix_key",
            "pix_key_type",
            "credit_cards",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_credit_cards(self, obj: Person) -> list[Any]:
        return list(CreditCardSerializer(obj.credit_cards.all(), many=True).data)


class CreditCardSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True
    )

    class Meta:
        model = CreditCard
        fields = [
            "id",
            "person",
            "person_id",
            "nickname",
            "last_four_digits",
            "closing_day",
            "due_day",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseCategory.objects.all(),
        source="parent",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ExpenseCategory
        fields = [
            "id",
            "name",
            "description",
            "color",
            "parent",
            "parent_id",
            "subcategories",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "parent", "subcategories", "created_at", "updated_at"]

    def get_subcategories(self, obj: ExpenseCategory) -> list[Any]:
        children = obj.subcategories.all()
        return list(ExpenseCategorySerializer(children, many=True).data)


class ExpenseInstallmentSerializer(FinalizedMonthProtectionMixin, serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseInstallment
        fields = [
            "id",
            "expense",
            "installment_number",
            "total_installments",
            "amount",
            "due_date",
            "is_paid",
            "paid_date",
            "notes",
            "is_overdue",
        ]
        read_only_fields = ["id"]

    def get_is_overdue(self, obj: ExpenseInstallment) -> bool:
        return not obj.is_paid and obj.due_date < timezone.now().date()

    def _get_reference_month(self, attrs: dict[str, Any]) -> date | None:
        due_date = attrs.get("due_date")
        if due_date is None and self.instance:
            due_date = self.instance.due_date
        if due_date:
            return date(due_date.year, due_date.month, 1)
        return None


class ExpenseSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="person",
        write_only=True,
        required=False,
        allow_null=True,
    )
    credit_card = CreditCardSerializer(read_only=True)
    credit_card_id = serializers.PrimaryKeyRelatedField(
        queryset=CreditCard.objects.all(),
        source="credit_card",
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
    category = ExpenseCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseCategory.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    installments = ExpenseInstallmentSerializer(many=True, read_only=True)
    remaining_installments = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "description",
            "expense_type",
            "total_amount",
            "expense_date",
            "person",
            "person_id",
            "credit_card",
            "credit_card_id",
            "building",
            "building_id",
            "category",
            "category_id",
            "is_installment",
            "total_installments",
            "is_debt_installment",
            "is_recurring",
            "expected_monthly_amount",
            "recurrence_day",
            "is_paid",
            "paid_date",
            "end_date",
            "is_offset",
            "bank_name",
            "interest_rate",
            "notes",
            "installments",
            "remaining_installments",
            "total_paid",
            "total_remaining",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_remaining_installments(self, obj: Expense) -> int:
        # Iterate the prefetched installments (ExpenseViewSet prefetches them) instead of a
        # per-row .count()/.aggregate() that would ignore the prefetch and N+1 (P5.1).
        return sum(1 for i in obj.installments.all() if not i.is_paid)

    def get_total_paid(self, obj: Expense) -> str:
        return str(sum((i.amount for i in obj.installments.all() if i.is_paid), Decimal(0)))

    def get_total_remaining(self, obj: Expense) -> str:
        return str(sum((i.amount for i in obj.installments.all() if not i.is_paid), Decimal(0)))

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)

        # For partial updates, fall back to instance values for cross-field validation
        expense_type = attrs.get("expense_type")
        if expense_type is None and self.instance:
            expense_type = self.instance.expense_type
        expense_type = expense_type or ""

        credit_card = attrs.get("credit_card")
        if credit_card is None and "credit_card" not in attrs and self.instance:
            credit_card = self.instance.credit_card

        person = attrs.get("person")
        if person is None and "person" not in attrs and self.instance:
            person = self.instance.person

        building = attrs.get("building")
        if building is None and "building" not in attrs and self.instance:
            building = self.instance.building

        if expense_type == "card_purchase" and not credit_card:
            raise serializers.ValidationError(
                {"credit_card_id": "Compra no cartão requer um cartão de crédito."}
            )

        if expense_type == "bank_loan" and not person:
            raise serializers.ValidationError(
                {"person_id": "Empréstimo bancário requer uma pessoa."}
            )

        if expense_type in ("water_bill", "electricity_bill", "property_tax") and not building:
            raise serializers.ValidationError(
                {"building_id": "Conta de utilidade requer um prédio."}
            )

        if attrs.get("is_installment") and not attrs.get("total_installments"):
            raise serializers.ValidationError(
                {"total_installments": "Despesa parcelada requer número total de parcelas."}
            )

        if attrs.get("is_recurring") and not attrs.get("expected_monthly_amount"):
            raise serializers.ValidationError(
                {"expected_monthly_amount": "Despesa recorrente requer valor mensal esperado."}
            )

        return attrs


class PersonIncomeSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True
    )
    apartment = ApartmentSerializer(read_only=True)
    apartment_id = serializers.PrimaryKeyRelatedField(
        queryset=Apartment.objects.all(),
        source="apartment",
        write_only=True,
        required=False,
        allow_null=True,
    )
    current_value = serializers.SerializerMethodField()

    class Meta:
        model = PersonIncome
        fields = [
            "id",
            "person",
            "person_id",
            "income_type",
            "apartment",
            "apartment_id",
            "fixed_amount",
            "start_date",
            "end_date",
            "is_active",
            "notes",
            "current_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "A data final não pode ser anterior à data inicial."}
            )
        return attrs

    def get_current_value(self, obj: PersonIncome) -> str:
        if obj.income_type == "apartment_rent" and obj.apartment:
            lease = obj.apartment.leases.first()
            if lease is not None:
                return str(lease.rental_value)
            return str(obj.apartment.rental_value)
        if obj.income_type == "fixed_stipend" and obj.fixed_amount:
            return str(obj.fixed_amount)
        return str(Decimal(0))


class IncomeSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="person",
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
    category = ExpenseCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseCategory.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Income
        fields = [
            "id",
            "description",
            "amount",
            "income_date",
            "person",
            "person_id",
            "building",
            "building_id",
            "category",
            "category_id",
            "is_recurring",
            "expected_monthly_amount",
            "is_received",
            "received_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= 0:
            raise serializers.ValidationError(_POSITIVE_AMOUNT_ERROR)
        return value


class RentPaymentValidationMixin(serializers.Serializer):
    """Shared rent-payment write path — ``lease_id`` write field, amount > 0 and reference month
    pinned to the 1st of the month. Lets the full-lease and slim-lease serializers share the
    write behaviour without one redeclaring the other's ``lease`` field type.
    """

    lease_id = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.all(), source="lease", write_only=True
    )

    def validate_amount_paid(self, value: Decimal) -> Decimal:
        # Mirrors the DB CheckConstraint rent_payment_amount_positive (a clean 400 vs a 500).
        if value <= 0:
            raise serializers.ValidationError(_POSITIVE_AMOUNT_ERROR)
        return value

    def validate_reference_month(self, value: date) -> date:
        return _validate_first_day_of_month(value)

    def _get_reference_month(self, attrs: dict[str, Any]) -> date | None:
        reference_month = attrs.get("reference_month")
        if reference_month is None and self.instance:
            reference_month = self.instance.reference_month
        if reference_month:
            return date(reference_month.year, reference_month.month, 1)
        return None


class RentPaymentSerializer(
    FinalizedMonthProtectionMixin, RentPaymentValidationMixin, serializers.ModelSerializer
):
    lease = LeaseSerializer(read_only=True)

    class Meta:
        model = RentPayment
        fields = [
            "id",
            "lease",
            "lease_id",
            "reference_month",
            "amount_paid",
            "payment_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RentPaymentBuildingSerializer(serializers.ModelSerializer):
    """id + name only — the building reference the rent-payments admin screen shows."""

    class Meta:
        model = Building
        fields = ["id", "name"]
        read_only_fields = fields


class RentPaymentApartmentSerializer(serializers.ModelSerializer):
    """Slim apartment for rent payments: no owner PII, no furnitures/active_lease."""

    building = RentPaymentBuildingSerializer(read_only=True)

    class Meta:
        model = Apartment
        fields = ["id", "number", "building"]
        read_only_fields = fields


class RentPaymentLeaseSerializer(serializers.ModelSerializer):
    """Lightweight lease reference for rent payments (no heavy LeaseSerializer nesting)."""

    apartment = RentPaymentApartmentSerializer(read_only=True)
    responsible_tenant = TenantSimpleSerializer(read_only=True)

    class Meta:
        model = Lease
        fields = ["id", "apartment", "responsible_tenant"]
        read_only_fields = fields


class RentPaymentSlimSerializer(
    FinalizedMonthProtectionMixin, RentPaymentValidationMixin, serializers.ModelSerializer
):
    """Read with a lightweight lease reference — used by the deprecated /api/rent-payments/
    list+detail to kill the per-row N+1 the full ``LeaseSerializer`` caused (apartment
    owner/furnitures/active_lease/tenants). The write path (``lease_id`` + amount/reference-month
    validation) matches :class:`RentPaymentSerializer` via the shared mixin.
    """

    lease = RentPaymentLeaseSerializer(read_only=True)

    class Meta(RentPaymentSerializer.Meta):
        pass


class EmployeePaymentSerializer(FinalizedMonthProtectionMixin, serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True
    )
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = EmployeePayment
        fields = [
            "id",
            "person",
            "person_id",
            "reference_month",
            "base_salary",
            "variable_amount",
            "rent_offset",
            "cleaning_count",
            "payment_date",
            "is_paid",
            "notes",
            "total_paid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_paid", "created_at", "updated_at"]

    def validate_reference_month(self, value: date) -> date:
        return _validate_first_day_of_month(value)

    def _get_reference_month(self, attrs: dict[str, Any]) -> date | None:
        reference_month = attrs.get("reference_month")
        if reference_month is None and self.instance:
            reference_month = self.instance.reference_month
        if reference_month:
            return date(reference_month.year, reference_month.month, 1)
        return None


class PersonPaymentSerializer(FinalizedMonthProtectionMixin, serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="person",
        write_only=True,
    )

    class Meta:
        model = PersonPayment
        fields = [
            "id",
            "person",
            "person_id",
            "reference_month",
            "amount",
            "payment_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_reference_month(self, value: date) -> date:
        return _validate_first_day_of_month(value)

    def _get_reference_month(self, attrs: dict[str, Any]) -> date | None:
        reference_month = attrs.get("reference_month")
        if reference_month is None and self.instance:
            reference_month = self.instance.reference_month
        if reference_month:
            return date(reference_month.year, reference_month.month, 1)
        return None


class PersonPaymentScheduleSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        source="person",
        write_only=True,
    )

    class Meta:
        model = PersonPaymentSchedule
        fields = [
            "id",
            "person",
            "person_id",
            "reference_month",
            "due_day",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_reference_month(self, value: date) -> date:
        return _validate_first_day_of_month(value)

    def validate_due_day(self, value: int) -> int:
        validate_due_day(value)
        return value


class ExpenseMonthSkipSerializer(serializers.ModelSerializer):
    expense_id = serializers.PrimaryKeyRelatedField(
        queryset=Expense.objects.all(),
        source="expense",
        write_only=True,
    )
    expense_description = serializers.CharField(source="expense.description", read_only=True)

    class Meta:
        model = ExpenseMonthSkip
        fields = [
            "id",
            "expense_id",
            "expense_description",
            "reference_month",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "expense_description", "created_at", "updated_at"]

    def validate_reference_month(self, value: date) -> date:
        return _validate_first_day_of_month(value)


class FinancialSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialSettings
        fields = [
            "id",
            "initial_balance",
            "initial_balance_date",
            "default_pix_key",
            "default_pix_key_type",
            "notes",
            "rent_tracking_start_date",
            "updated_at",
            "updated_by",
        ]
        read_only_fields = ["id", "updated_at", "updated_by"]


class PaymentProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = [
            "id",
            "lease",
            "reference_month",
            "file",
            "pix_code",
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "lease",
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "created_at",
        ]

    def validate_file(self, value: Any) -> Any:
        return validate_proof_file(value)

    def validate_reference_month(self, value: date) -> date:
        # The tenant types this as free text in the mobile app, so NORMALIZE to the first of the
        # month (reference_month is a competence month) rather than rejecting like the admin-entered
        # RentPayment — a tenant entering the day they paid must not be blocked with an opaque error.
        return value.replace(day=1)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "is_read",
            "read_at",
            "sent_at",
            "data",
        ]
        read_only_fields = ["id", "type", "title", "body", "sent_at", "data"]
