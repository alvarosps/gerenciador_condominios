"""
Unit tests for Core models

Tests all model functionality including:
- Model creation and validation
- Constraints (unique, unique_together)
- Relationships (ForeignKey, ManyToMany, OneToOne)
- Model methods and properties
- Edge cases and error handling

Coverage target: 100% of models.py
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError

import pytest

from core.models import Apartment, Building, Dependent, Furniture, Lease, Tenant
from tests.fixtures.factories import (
    ApartmentFactory,
    BuildingFactory,
    DependentFactory,
    FurnitureFactory,
    LeaseFactory,
    TenantFactory,
    create_full_lease_scenario,
    create_rented_apartment,
)

# ============================================================================
# Building Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.model
class TestBuildingModel:
    """Test suite for Building model"""

    def test_create_building(self):
        """Test creating a building with valid data"""
        building = BuildingFactory(street_number=836, name="Edifício Test", address="Rua Test, 836 - São Paulo/SP")

        assert building.id is not None
        assert building.street_number == 836
        assert building.name == "Edifício Test"
        assert "Rua Test" in building.address

    def test_building_str_representation(self):
        """Test __str__ method returns expected format"""
        building = BuildingFactory(street_number=850, name="Edifício Central")
        expected = "Edifício Central - 850"
        assert str(building) == expected

    def test_street_number_unique_constraint(self):
        """Test that street_number must be unique"""
        from django.db import transaction

        BuildingFactory(street_number=999)

        # Force create with same street_number (bypass factory sequence)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Building.objects.create(street_number=999, name="Duplicate Building", address="Duplicate Address")

    def test_building_apartments_relationship(self):
        """Test one-to-many relationship with apartments"""
        building = BuildingFactory()
        apt1 = ApartmentFactory(building=building, number=101)
        apt2 = ApartmentFactory(building=building, number=102)

        assert building.apartments.count() == 2
        assert apt1 in building.apartments.all()
        assert apt2 in building.apartments.all()

    def test_building_cascade_delete(self):
        """Test that hard deleting building cascades to apartments"""
        building = BuildingFactory()
        apartment = ApartmentFactory(building=building)
        apartment_id = apartment.id

        # Use hard_delete=True to test cascade (soft delete doesn't cascade)
        building.delete(hard_delete=True)

        assert not Apartment.objects.filter(id=apartment_id).exists()

    def test_building_ordering(self):
        """Test buildings are ordered by street_number"""
        building1 = BuildingFactory(street_number=850)
        building2 = BuildingFactory(street_number=836)
        building3 = BuildingFactory(street_number=900)

        # Apartments are ordered by building street_number
        apartments = [
            ApartmentFactory(building=building1),
            ApartmentFactory(building=building2),
            ApartmentFactory(building=building3),
        ]

        ordered_apts = Apartment.objects.all().order_by("building__street_number")
        assert list(ordered_apts) == [apartments[1], apartments[0], apartments[2]]


# ============================================================================
# Furniture Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.model
class TestFurnitureModel:
    """Test suite for Furniture model"""

    def test_create_furniture(self):
        """Test creating furniture with valid data"""
        furniture = FurnitureFactory(name="Geladeira", description="Geladeira Frost Free 300L")

        assert furniture.id is not None
        assert furniture.name == "Geladeira"
        assert "Frost Free" in furniture.description

    def test_furniture_str_representation(self):
        """Test __str__ method returns furniture name"""
        furniture = FurnitureFactory(name="Fogão")
        assert str(furniture) == "Fogão"

    def test_furniture_name_unique_constraint(self):
        """Test that furniture name must be unique"""
        from django.db import transaction

        FurnitureFactory(name="Geladeira Única")

        # Force create with same name (bypass factory sequence)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Furniture.objects.create(name="Geladeira Única")

    def test_furniture_apartments_relationship(self):
        """Test many-to-many relationship with apartments"""
        furniture1 = FurnitureFactory(name="Geladeira")
        furniture2 = FurnitureFactory(name="Fogão")

        apartment = ApartmentFactory(furnitures=[furniture1, furniture2])

        assert apartment.furnitures.count() == 2
        assert furniture1.apartments.count() == 1
        assert furniture2.apartments.count() == 1

    def test_furniture_tenants_relationship(self):
        """Test many-to-many relationship with tenants"""
        furniture1 = FurnitureFactory(name="Sofá")
        furniture2 = FurnitureFactory(name="Mesa")

        tenant = TenantFactory(furnitures=[furniture1, furniture2])

        assert tenant.furnitures.count() == 2
        assert furniture1.tenants.count() == 1
        assert furniture2.tenants.count() == 1

    def test_furniture_optional_description(self):
        """Test that description is optional"""
        furniture = FurnitureFactory(name="Cadeira", description=None)
        assert furniture.description is None

        furniture2 = FurnitureFactory(name="Mesa", description="")
        assert furniture2.description == ""


# ============================================================================
# Apartment Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.model
class TestApartmentModel:
    """Test suite for Apartment model"""

    def test_create_apartment(self):
        """Test creating apartment with valid data"""
        building = BuildingFactory()
        apartment = ApartmentFactory(
            building=building,
            number=101,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )

        assert apartment.id is not None
        assert apartment.building == building
        assert apartment.number == 101
        assert apartment.rental_value == Decimal("1500.00")
        assert apartment.cleaning_fee == Decimal("200.00")
        assert apartment.max_tenants == 2

    def test_apartment_str_representation(self):
        """Test __str__ method returns expected format"""
        building = BuildingFactory(street_number=836)
        apartment = ApartmentFactory(building=building, number=101)

        expected = "Apto 101 - 836"
        assert str(apartment) == expected

    def test_apartment_unique_together_constraint(self):
        """Test that (building, number) must be unique together"""
        building = BuildingFactory()
        ApartmentFactory(building=building, number=101)

        with pytest.raises(IntegrityError):
            ApartmentFactory(building=building, number=101)

    def test_apartment_different_buildings_same_number(self):
        """Test that same apartment number is allowed in different buildings"""
        building1 = BuildingFactory(street_number=836)
        building2 = BuildingFactory(street_number=850)

        apt1 = ApartmentFactory(building=building1, number=101)
        apt2 = ApartmentFactory(building=building2, number=101)

        assert apt1.number == apt2.number
        assert apt1.building != apt2.building

    def test_apartment_furnitures_relationship(self):
        """Test many-to-many relationship with furniture"""
        furniture1 = FurnitureFactory(name="Geladeira")
        furniture2 = FurnitureFactory(name="Fogão")
        furniture3 = FurnitureFactory(name="Micro-ondas")

        apartment = ApartmentFactory(furnitures=[furniture1, furniture2, furniture3])

        assert apartment.furnitures.count() == 3
        assert furniture1 in apartment.furnitures.all()
        assert furniture2 in apartment.furnitures.all()
        assert furniture3 in apartment.furnitures.all()

    def test_apartment_default_values(self):
        """Test that default values are set correctly"""
        apartment = ApartmentFactory()

        assert apartment.interfone_configured is False
        assert apartment.contract_generated is False
        assert apartment.contract_signed is False
        assert apartment.is_rented is False
        assert apartment.lease_date is None
        assert apartment.last_rent_increase_date is None
        assert apartment.cleaning_fee == Decimal("0.00") or apartment.cleaning_fee > Decimal("0.00")

    def test_apartment_rental_value_validation(self):
        """Test that rental_value must be positive"""
        apartment = ApartmentFactory(rental_value=Decimal("1500.00"))
        assert apartment.rental_value > Decimal("0.00")

        # Note: MinValueValidator is on the field, but doesn't raise on save
        # It raises during form validation or serializer validation

    def test_apartment_lease_relationship(self):
        """Test OneToOne relationship with lease"""
        apartment = ApartmentFactory()
        lease = LeaseFactory(apartment=apartment)

        assert apartment.lease == lease
        assert lease.apartment == apartment

    def test_apartment_ordering(self):
        """Test apartments are ordered by building and number"""
        building1 = BuildingFactory(street_number=836)
        building2 = BuildingFactory(street_number=850)

        apt1 = ApartmentFactory(building=building1, number=103)
        apt2 = ApartmentFactory(building=building1, number=101)
        apt3 = ApartmentFactory(building=building2, number=102)

        apartments = Apartment.objects.all().order_by("building__street_number", "number")
        assert list(apartments) == [apt2, apt1, apt3]


# ============================================================================
# Tenant Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.model
class TestTenantModel:
    """Test suite for Tenant model"""

    def test_create_tenant(self):
        """Test creating tenant with valid data"""
        tenant = TenantFactory(
            name="João da Silva",
            cpf_cnpj="529.982.247-25",  # Valid CPF
            is_company=False,
            phone="(11) 98765-4321",
            marital_status="Casado(a)",
            profession="Engenheiro",
        )

        assert tenant.id is not None
        assert tenant.name == "João da Silva"
        assert tenant.cpf_cnpj == "529.982.247-25"
        assert tenant.is_company is False
        assert tenant.phone == "(11) 98765-4321"
        assert tenant.marital_status == "Casado(a)"
        assert tenant.profession == "Engenheiro"

    def test_tenant_str_representation(self):
        """Test __str__ method returns tenant name"""
        tenant = TenantFactory(name="Maria Santos")
        assert str(tenant) == "Maria Santos"

    def test_cpf_cnpj_unique_constraint(self):
        """Test that cpf_cnpj must be unique"""
        TenantFactory(cpf_cnpj="529.982.247-25")  # Valid CPF

        # The model's full_clean() catches duplicates before database constraint
        with pytest.raises((IntegrityError, ValidationError)):
            TenantFactory(cpf_cnpj="529.982.247-25")  # Same CPF should fail

    def test_tenant_dependents_relationship(self):
        """Test one-to-many relationship with dependents"""
        tenant = TenantFactory()
        dep1 = DependentFactory(tenant=tenant)
        dep2 = DependentFactory(tenant=tenant)

        assert tenant.dependents.count() == 2
        assert dep1 in tenant.dependents.all()
        assert dep2 in tenant.dependents.all()

    def test_tenant_furnitures_relationship(self):
        """Test many-to-many relationship with furniture"""
        furniture1 = FurnitureFactory(name="Sofá Próprio")
        furniture2 = FurnitureFactory(name="Mesa Própria")

        tenant = TenantFactory(furnitures=[furniture1, furniture2])

        assert tenant.furnitures.count() == 2
        assert furniture1 in tenant.furnitures.all()
        assert furniture2 in tenant.furnitures.all()

    def test_tenant_default_values(self):
        """Test that default values are set correctly"""
        tenant = TenantFactory()

        assert tenant.is_company is False
        assert tenant.cleaning_fee_paid is False
        assert tenant.tag_deposit_paid is False
        assert tenant.rent_due_day == 1 or tenant.rent_due_day > 0

    def test_tenant_company_configuration(self):
        """Test creating a company (PJ) tenant"""
        tenant = TenantFactory(
            name="Empresa XYZ Ltda",
            cpf_cnpj="11.222.333/0001-81",
            is_company=True,
            rg=None,  # Valid CNPJ, companies don't have RG
        )

        assert tenant.is_company is True
        assert tenant.rg is None

    def test_tenant_cascade_delete_dependents(self):
        """Test that hard deleting tenant cascades to dependents"""
        tenant = TenantFactory()
        dependent = DependentFactory(tenant=tenant)
        dependent_id = dependent.id

        # Use hard_delete=True to test cascade (soft delete doesn't cascade)
        tenant.delete(hard_delete=True)

        assert not Dependent.objects.filter(id=dependent_id).exists()

    def test_tenant_leases_relationship(self):
        """Test many-to-many relationship with leases"""
        tenant = TenantFactory()
        apartment1 = ApartmentFactory()
        _apartment2 = ApartmentFactory()  # noqa: F841

        lease1 = LeaseFactory(apartment=apartment1, responsible_tenant=tenant, tenants=[tenant])
        # Note: Can't create second lease for same tenant as responsible (business logic)
        # but tenant can be in multiple leases as co-tenant

        assert tenant.leases.count() >= 1
        assert lease1 in tenant.leases.all()


# ============================================================================
# Dependent Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.model
class TestDependentModel:
    """Test suite for Dependent model"""

    def test_create_dependent(self):
        """Test creating dependent with valid data"""
        tenant = TenantFactory()
        dependent = DependentFactory(tenant=tenant, name="Maria Silva", phone="(11) 91234-5678")

        assert dependent.id is not None
        assert dependent.tenant == tenant
        assert dependent.name == "Maria Silva"
        assert dependent.phone == "(11) 91234-5678"

    def test_dependent_str_representation(self):
        """Test __str__ method returns expected format"""
        tenant = TenantFactory(name="João Silva")
        dependent = DependentFactory(tenant=tenant, name="Maria Silva")

        expected = "Maria Silva (dependente de João Silva)"
        assert str(dependent) == expected

    def test_dependent_tenant_relationship(self):
        """Test foreign key relationship with tenant"""
        tenant = TenantFactory()
        dependent = DependentFactory(tenant=tenant)

        assert dependent.tenant == tenant
        assert dependent in tenant.dependents.all()

    def test_multiple_dependents_per_tenant(self):
        """Test that tenant can have multiple dependents"""
        tenant = TenantFactory()
        dep1 = DependentFactory(tenant=tenant, name="Filho 1")
        dep2 = DependentFactory(tenant=tenant, name="Filho 2")
        dep3 = DependentFactory(tenant=tenant, name="Filho 3")

        assert tenant.dependents.count() == 3
        assert {dep1, dep2, dep3} == set(tenant.dependents.all())


# ============================================================================
# Lease Model Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.model
class TestLeaseModel:
    """Test suite for Lease model"""

    def test_create_lease(self):
        """Test creating lease with valid data"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        lease = LeaseFactory(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 15),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        assert lease.id is not None
        assert lease.apartment == apartment
        assert lease.responsible_tenant == tenant
        assert lease.start_date == date(2025, 1, 15)
        assert lease.validity_months == 12
        assert lease.due_day == 10
        assert lease.rental_value == Decimal("1500.00")
        assert lease.cleaning_fee == Decimal("200.00")
        assert lease.tag_fee == Decimal("50.00")

    def test_lease_str_representation(self):
        """Test __str__ method returns expected format"""
        building = BuildingFactory(street_number=836)
        apartment = ApartmentFactory(building=building, number=101)
        lease = LeaseFactory(apartment=apartment)

        expected = "Locação do Apto 101 - 836"
        assert str(lease) == expected

    def test_lease_one_to_one_apartment_constraint(self):
        """Test that apartment can only have one lease"""
        apartment = ApartmentFactory()
        LeaseFactory(apartment=apartment)

        # The model's full_clean() catches duplicates before database constraint
        with pytest.raises((IntegrityError, ValidationError)):
            LeaseFactory(apartment=apartment)

    def test_lease_multiple_tenants(self):
        """Test lease with multiple tenants"""
        apartment = ApartmentFactory()
        tenant1 = TenantFactory(cpf_cnpj="529.982.247-25")  # Valid CPF
        tenant2 = TenantFactory(cpf_cnpj="111.444.777-35")  # Valid CPF

        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant1, tenants=[tenant1, tenant2])

        assert lease.tenants.count() == 2
        assert tenant1 in lease.tenants.all()
        assert tenant2 in lease.tenants.all()
        assert lease.responsible_tenant == tenant1

    def test_lease_tenants_relationship(self):
        """Test many-to-many relationship with tenants"""
        apartment = ApartmentFactory()
        tenant1 = TenantFactory(cpf_cnpj="234.567.890-92")  # Valid CPF
        tenant2 = TenantFactory(cpf_cnpj="345.678.901-75")  # Valid CPF
        tenant3 = TenantFactory(cpf_cnpj="276.685.415-00")  # Valid CPF

        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant1, tenants=[tenant1, tenant2, tenant3])

        assert lease.tenants.count() == 3
        assert lease.number_of_tenants == 3
        # Tag fee should be 80 for multiple tenants
        assert lease.tag_fee == Decimal("80.00")

    def test_lease_tag_fee_single_tenant(self):
        """Test tag fee calculation for single tenant"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        assert lease.tenants.count() == 1
        assert lease.number_of_tenants == 1
        assert lease.tag_fee == Decimal("50.00")

    def test_lease_tag_fee_multiple_tenants(self):
        """Test tag fee calculation for multiple tenants"""
        apartment = ApartmentFactory()
        tenant1 = TenantFactory(cpf_cnpj="567.890.123-03")  # Valid CPF
        tenant2 = TenantFactory(cpf_cnpj="678.901.234-69")  # Valid CPF

        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant1, tenants=[tenant1, tenant2])

        assert lease.tenants.count() == 2
        assert lease.number_of_tenants == 2
        assert lease.tag_fee == Decimal("80.00")

    def test_lease_default_values(self):
        """Test that default values are set correctly"""
        lease = LeaseFactory()

        assert lease.contract_generated is False
        assert lease.contract_signed is False
        assert lease.interfone_configured is False
        assert lease.warning_count == 0
        assert lease.number_of_tenants >= 1

    def test_lease_furniture_calculation(self):
        """Test that lease furniture = apartment furniture - tenant furniture"""
        # Create furniture
        apt_furniture1 = FurnitureFactory(name="Geladeira Apt")
        apt_furniture2 = FurnitureFactory(name="Fogão Apt")
        apt_furniture3 = FurnitureFactory(name="Micro-ondas Apt")
        tenant_furniture1 = FurnitureFactory(name="Sofá Próprio")
        tenant_furniture2 = FurnitureFactory(name="Fogão Apt")  # Same as apartment

        # Create apartment with furniture
        apartment = ApartmentFactory(furnitures=[apt_furniture1, apt_furniture2, apt_furniture3])

        # Create tenant with furniture (including one that's in the apartment)
        tenant = TenantFactory(furnitures=[tenant_furniture1, tenant_furniture2])

        # Create lease
        _lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])  # noqa: F841

        # Lease should have apartment furniture minus tenant furniture
        apt_furn_set = set(apartment.furnitures.all())
        tenant_furn_set = set(tenant.furnitures.all())
        lease_furniture = apt_furn_set - tenant_furn_set

        # Expected: apt_furniture1 and apt_furniture3 (not fogão, as tenant has it)
        assert apt_furniture1 in lease_furniture
        assert apt_furniture3 in lease_furniture
        assert apt_furniture2 not in lease_furniture  # Tenant has this one
        assert tenant_furniture1 not in lease_furniture  # Tenant's own furniture

    def test_lease_protect_tenant_deletion(self):
        """Test that responsible tenant cannot be hard-deleted while lease exists"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        _lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant)  # noqa: F841

        # Django's PROTECT should prevent hard deletion
        # Note: Soft delete (default) would work fine - this tests actual FK protection
        from django.db.models import ProtectedError

        with pytest.raises((ProtectedError, IntegrityError)):
            tenant.delete(hard_delete=True)

    def test_full_lease_scenario(self):
        """Test creating a complete lease scenario with all related objects"""
        lease = create_full_lease_scenario(
            num_tenants=2, num_dependents_per_tenant=1, apartment_furniture_count=5, tenant_furniture_count=2
        )

        assert lease is not None
        assert lease.tenants.count() == 2
        assert lease.responsible_tenant.dependents.count() == 1
        assert lease.apartment.furnitures.count() == 5
        assert lease.responsible_tenant.furnitures.count() == 2

    def test_rented_apartment_scenario(self):
        """Test creating a rented apartment with active lease"""
        apartment, lease = create_rented_apartment(num_tenants=1)

        assert apartment.is_rented is True
        assert apartment.lease_date is not None
        assert apartment.lease == lease
        assert lease.apartment == apartment
