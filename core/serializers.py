from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import serializers

from core.validators import BrazilianPhoneValidator, CNPJValidator, CPFValidator

from .models import (
    Apartment,
    Building,
    ContractRule,
    CreditCard,
    Dependent,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    FinancialSettings,
    Furniture,
    Income,
    Landlord,
    Lease,
    Person,
    PersonIncome,
    PersonPayment,
    RentPayment,
    Tenant,
)

User = get_user_model()

_DOUBLE_OCCUPANCY = 2  # number_of_tenants tier that uses rental_value_double


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"


class FurnitureSerializer(serializers.ModelSerializer):
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

        if max_tenants == _DOUBLE_OCCUPANCY and rental_value_double is None:
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

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Apartment:
        """Create apartment with furniture relationships."""
        furniture_ids = validated_data.pop("furniture_ids", [])
        apartment = Apartment.objects.create(**validated_data)
        if furniture_ids:
            apartment.furnitures.set(furniture_ids)
        return apartment

    def update(self, instance: Apartment, validated_data: dict[str, Any]) -> Apartment:
        """Update apartment with furniture relationships."""
        furniture_ids = validated_data.pop("furniture_ids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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
            try:
                if is_company:
                    CNPJValidator()(cpf_cnpj)
                else:
                    CPFValidator()(cpf_cnpj)
            except serializers.ValidationError as e:
                raise serializers.ValidationError({"cpf_cnpj": str(e)}) from e

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Tenant:
        dependents_data = validated_data.pop("dependents", [])
        furniture_ids = validated_data.pop("furniture_ids", [])
        tenant = Tenant.objects.create(**validated_data)
        if furniture_ids:
            tenant.furnitures.set(furniture_ids)
        for dep_data in dependents_data:
            Dependent.objects.create(tenant=tenant, **dep_data)
        return tenant

    def update(self, instance: Tenant, validated_data: dict[str, Any]) -> Tenant:
        dependents_data = validated_data.pop("dependents", None)
        furniture_ids = validated_data.pop("furniture_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if furniture_ids is not None:
            instance.furnitures.set(furniture_ids)

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
                    # Create new dependent
                    Dependent.objects.create(tenant=instance, **dep_data)

        return instance


class LeaseSerializer(serializers.ModelSerializer):
    apartment = ApartmentSerializer(read_only=True)
    apartment_id = serializers.PrimaryKeyRelatedField(
        queryset=Apartment.objects.all(), source="apartment", write_only=True
    )
    responsible_tenant = TenantSerializer(read_only=True)
    responsible_tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), source="responsible_tenant", write_only=True
    )
    tenants = TenantSerializer(many=True, read_only=True)
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

        if number_of_tenants not in (1, _DOUBLE_OCCUPANCY):
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

        if number_of_tenants == _DOUBLE_OCCUPANCY:
            resident_dependent = attrs.get("resident_dependent")

            # For update: if number_of_tenants is not changing, resident_dependent
            # is already set on the instance — no need to re-supply it.
            already_set = (
                self.instance is not None
                and self.instance.number_of_tenants == _DOUBLE_OCCUPANCY
                and "number_of_tenants" not in attrs
            )

            if resident_dependent is None and not already_set:
                raise serializers.ValidationError(
                    {"resident_dependent_id": "Obrigatório quando number_of_tenants é 2."}
                )

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

        return attrs

    def create(self, validated_data: dict[str, Any]) -> Lease:
        """Create lease with tenant relationships.

        If rental_value is not provided, derives it from the apartment based on
        number_of_tenants: uses apartment.rental_value_double for 2 tenants when
        available, otherwise falls back to apartment.rental_value.
        """
        tenants = validated_data.pop("tenants", [])
        if "rental_value" not in validated_data:
            apartment: Apartment = validated_data["apartment"]
            number_of_tenants: int = validated_data.get("number_of_tenants", 1)
            if number_of_tenants == _DOUBLE_OCCUPANCY and apartment.rental_value_double is not None:
                validated_data["rental_value"] = apartment.rental_value_double
            else:
                validated_data["rental_value"] = apartment.rental_value
        lease = Lease.objects.create(**validated_data)
        if tenants:
            lease.tenants.set(tenants)
        return lease

    def update(self, instance: Lease, validated_data: dict[str, Any]) -> Lease:
        """Update lease with tenant relationships."""
        tenants = validated_data.pop("tenants", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tenants is not None:
            instance.tenants.set(tenants)

        return instance


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


# =============================================================================
# FINANCIAL MODULE SERIALIZERS
# =============================================================================


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


class ExpenseInstallmentSerializer(serializers.ModelSerializer):
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
        return not obj.is_paid and obj.due_date < date.today()


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
        return obj.installments.filter(is_paid=False).count()

    def get_total_paid(self, obj: Expense) -> str:
        result = obj.installments.filter(is_paid=True).aggregate(total=Sum("amount"))
        return str(result["total"] or Decimal(0))

    def get_total_remaining(self, obj: Expense) -> str:
        result = obj.installments.filter(is_paid=False).aggregate(total=Sum("amount"))
        return str(result["total"] or Decimal(0))

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        expense_type = attrs.get("expense_type", "")

        if expense_type == "card_purchase" and not attrs.get("credit_card"):
            raise serializers.ValidationError(
                {"credit_card_id": "Compra no cartão requer um cartão de crédito."}
            )

        if expense_type == "bank_loan" and not attrs.get("person"):
            raise serializers.ValidationError(
                {"person_id": "Empréstimo bancário requer uma pessoa."}
            )

        if expense_type in ("water_bill", "electricity_bill", "property_tax") and not attrs.get(
            "building"
        ):
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

    def get_current_value(self, obj: PersonIncome) -> str:
        if obj.income_type == "apartment_rent" and obj.apartment:
            lease = obj.apartment.leases.filter(is_deleted=False).first()
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


class RentPaymentSerializer(serializers.ModelSerializer):
    lease = LeaseSerializer(read_only=True)
    lease_id = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.all(), source="lease", write_only=True
    )

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

    def validate_reference_month(self, value: date) -> date:
        if value.day != 1:
            msg = "O mês de referência deve ser o primeiro dia do mês."
            raise serializers.ValidationError(msg)
        return value


class EmployeePaymentSerializer(serializers.ModelSerializer):
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
        if value.day != 1:
            msg = "O mês de referência deve ser o primeiro dia do mês."
            raise serializers.ValidationError(msg)
        return value


class PersonPaymentSerializer(serializers.ModelSerializer):
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
        if value.day != 1:
            msg = "O mês de referência deve ser o primeiro dia do mês."
            raise serializers.ValidationError(msg)
        return value


class FinancialSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialSettings
        fields = [
            "id",
            "initial_balance",
            "initial_balance_date",
            "notes",
            "updated_at",
            "updated_by",
        ]
        read_only_fields = ["id", "updated_at"]
