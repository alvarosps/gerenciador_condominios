from rest_framework import serializers
from .models import Building, Furniture, Apartment, Tenant, Dependent, Lease

class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = '__all__'

class FurnitureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Furniture
        fields = '__all__'

class ApartmentSerializer(serializers.ModelSerializer):
    furnitures = FurnitureSerializer(many=True, read_only=True)
    building = BuildingSerializer(read_only=True)
    building_id = serializers.PrimaryKeyRelatedField(queryset=Building.objects.all(), source='building', write_only=True)

    class Meta:
        model = Apartment
        fields = ['id', 'building', 'building_id', 'number', 'interfone_configured', 'contract_generated',
                  'contract_signed', 'rental_value', 'cleaning_fee', 'max_tenants', 'is_rented', 'lease_date',
                  'last_rent_increase_date', 'furnitures']

class DependentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependent
        fields = '__all__'

class TenantSerializer(serializers.ModelSerializer):
    dependents = DependentSerializer(many=True, required=False)
    furnitures = FurnitureSerializer(many=True, read_only=True)
    furniture_ids = serializers.PrimaryKeyRelatedField(queryset=Furniture.objects.all(), many=True, write_only=True, required=False)
    
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'cpf_cnpj', 'is_company', 'rg', 'phone', 'marital_status', 'profession',
                  'deposit_amount', 'cleaning_fee_paid', 'tag_deposit_paid', 'rent_due_day', 'dependents', 'furnitures', 'furniture_ids']

    def create(self, validated_data):
        dependents_data = validated_data.pop('dependents', [])
        furniture_ids = validated_data.pop('furniture_ids', [])
        tenant = Tenant.objects.create(**validated_data)
        if furniture_ids:
            tenant.furnitures.set(furniture_ids)
        for dep_data in dependents_data:
            Dependent.objects.create(tenant=tenant, **dep_data)
        return tenant

    def update(self, instance, validated_data):
        dependents_data = validated_data.pop('dependents', None)
        furniture_ids = validated_data.pop('furniture_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if furniture_ids is not None:
            instance.furnitures.set(furniture_ids)
        if dependents_data is not None:
            # Remover dependentes antigos e criar novos (pode ser aprimorado)
            instance.dependents.all().delete()
            for dep_data in dependents_data:
                Dependent.objects.create(tenant=instance, **dep_data)
        return instance

class LeaseSerializer(serializers.ModelSerializer):
    apartment = ApartmentSerializer(read_only=True)
    apartment_id = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all(), source='apartment', write_only=True)
    responsible_tenant = TenantSerializer(read_only=True)
    responsible_tenant_id = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), source='responsible_tenant', write_only=True)
    tenants = TenantSerializer(many=True, read_only=True)
    tenant_ids = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), many=True, source='tenants', write_only=True)

    class Meta:
        model = Lease
        fields = ['id', 'apartment', 'apartment_id', 'responsible_tenant', 'responsible_tenant_id', 'tenants', 'tenant_ids',
                  'start_date', 'validity_months', 'due_day', 'rental_value', 'cleaning_fee', 'tag_fee',
                  'contract_generated', 'contract_signed', 'interfone_configured', 'warning_count']
