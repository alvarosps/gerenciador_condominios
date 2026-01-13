from rest_framework import serializers

from core.validators import BrazilianPhoneValidator, CNPJValidator, CPFValidator

from .models import Apartment, Building, Dependent, Furniture, Lease, Tenant


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"


class FurnitureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Furniture
        fields = "__all__"


class ApartmentSerializer(serializers.ModelSerializer):
    furnitures = FurnitureSerializer(many=True, read_only=True)
    furniture_ids = serializers.PrimaryKeyRelatedField(
        queryset=Furniture.objects.all(), many=True, write_only=True, required=False
    )
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), source="building", write_only=True
    )

    class Meta:
        model = Apartment
        fields = [
            "id",
            "building",
            "building_id",
            "number",
            "interfone_configured",
            "contract_generated",
            "contract_signed",
            "rental_value",
            "cleaning_fee",
            "max_tenants",
            "is_rented",
            "lease_date",
            "last_rent_increase_date",
            "furnitures",
            "furniture_ids",
        ]

    def create(self, validated_data):
        """Create apartment with furniture relationships."""
        furniture_ids = validated_data.pop("furniture_ids", [])
        apartment = Apartment.objects.create(**validated_data)
        if furniture_ids:
            apartment.furnitures.set(furniture_ids)
        return apartment

    def update(self, instance, validated_data):
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
        fields = ["id", "tenant", "name", "phone"]
        read_only_fields = ["tenant"]  # tenant is set by parent in nested creation

    def validate_phone(self, value):
        """Validate Brazilian phone number format."""
        if value:
            BrazilianPhoneValidator()(value)
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
            "deposit_amount",
            "cleaning_fee_paid",
            "tag_deposit_paid",
            "rent_due_day",
            "dependents",
            "furnitures",
            "furniture_ids",
        ]

    def validate_phone(self, value):
        """Validate Brazilian phone number format."""
        if value:
            BrazilianPhoneValidator()(value)
        return value

    def validate(self, attrs):
        """Cross-field validation for CPF/CNPJ based on is_company flag."""
        attrs = super().validate(attrs)

        cpf_cnpj = attrs.get("cpf_cnpj", getattr(self.instance, "cpf_cnpj", None) if self.instance else None)
        is_company = attrs.get("is_company", getattr(self.instance, "is_company", False) if self.instance else False)

        if cpf_cnpj:
            try:
                if is_company:
                    CNPJValidator()(cpf_cnpj)
                else:
                    CPFValidator()(cpf_cnpj)
            except Exception as e:
                raise serializers.ValidationError({"cpf_cnpj": str(e)})

        return attrs

    def create(self, validated_data):
        dependents_data = validated_data.pop("dependents", [])
        furniture_ids = validated_data.pop("furniture_ids", [])
        tenant = Tenant.objects.create(**validated_data)
        if furniture_ids:
            tenant.furnitures.set(furniture_ids)
        for dep_data in dependents_data:
            Dependent.objects.create(tenant=tenant, **dep_data)
        return tenant

    def update(self, instance, validated_data):
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
            "start_date",
            "validity_months",
            "due_day",
            "rental_value",
            "cleaning_fee",
            "tag_fee",
            "contract_generated",
            "contract_signed",
            "interfone_configured",
            "warning_count",
        ]
