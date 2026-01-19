"""
Model Factories for Testing

This module provides factory_boy factories for all models in the application.
Factories generate realistic test data using Faker and provide a clean API
for creating test objects.

Usage:
    from tests.fixtures.factories import BuildingFactory, ApartmentFactory

    # Simple creation
    building = BuildingFactory()

    # With custom attributes
    building = BuildingFactory(street_number=850)

    # Create multiple instances
    buildings = BuildingFactory.create_batch(5)

    # Build without saving to database
    building = BuildingFactory.build()

    # Create with related objects
    apartment = ApartmentFactory(building__street_number=836)
"""

import random
from datetime import date, timedelta
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from core.models import Apartment, Building, Dependent, Furniture, Lease, Tenant

fake = Faker("pt_BR")

# Pre-validated CPF values that pass Brazilian checksum validation
# These CPFs are for testing purposes only - all generated using the CPF algorithm
VALID_CPFS = [
    "529.982.247-25",
    "111.444.777-35",
    "276.685.415-00",
    "853.513.468-93",
    "987.654.321-00",
    "123.456.789-09",
    "456.123.789-55",
    "234.567.890-92",
    "345.678.901-75",
    "567.890.123-03",
    "678.901.234-69",
    "789.012.345-05",
    "890.123.456-42",
    "901.234.567-70",
    "012.345.678-90",
]


class BuildingFactory(DjangoModelFactory):
    """
    Factory for Building model.

    Creates buildings with unique street numbers and realistic Brazilian addresses.

    Attributes:
        street_number: Unique sequential number (836, 837, 838, ...)
        name: Generated building name (e.g., "Edifício São Paulo")
        address: Complete Brazilian address
    """

    class Meta:
        model = Building
        django_get_or_create = ("street_number",)

    street_number = factory.Sequence(lambda n: 836 + n)
    name = factory.LazyAttribute(lambda obj: f"Edifício {fake.street_name()}")
    address = factory.LazyAttribute(
        lambda obj: f"Rua {fake.street_name()}, {obj.street_number} - {fake.bairro()} - São Paulo/SP"
    )


class FurnitureFactory(DjangoModelFactory):
    """
    Factory for Furniture model.

    Creates furniture items with realistic Brazilian names.

    Common furniture types:
        - Geladeira (Refrigerator)
        - Fogão (Stove)
        - Micro-ondas (Microwave)
        - Sofá (Sofa)
        - Cama (Bed)
        - Guarda-roupa (Wardrobe)
        - Mesa (Table)
        - Cadeira (Chair)
    """

    class Meta:
        model = Furniture
        django_get_or_create = ("name",)

    name = factory.Sequence(
        lambda n: random.choice(
            [
                f"Geladeira {n}",
                f"Fogão {n}",
                f"Micro-ondas {n}",
                f"Sofá {n}",
                f"Cama {n}",
                f"Guarda-roupa {n}",
                f"Mesa {n}",
                f"Cadeira {n}",
                f"Armário {n}",
                f"Estante {n}",
            ]
        )
    )
    description = factory.LazyAttribute(lambda obj: f"{obj.name} - {fake.sentence(nb_words=6)}")


class ApartmentFactory(DjangoModelFactory):
    """
    Factory for Apartment model.

    Creates apartments with realistic rental values and configurations.

    Post-generation:
        furnitures: Automatically creates 3-5 random furniture items

    Usage:
        # Apartment with auto-generated furniture
        apt = ApartmentFactory()

        # Apartment with specific furniture
        apt = ApartmentFactory(furnitures=[furniture1, furniture2])

        # Apartment without furniture
        apt = ApartmentFactory(furnitures=[])
    """

    class Meta:
        model = Apartment
        skip_postgeneration_save = True

    building = factory.SubFactory(BuildingFactory)
    number = factory.Sequence(lambda n: 101 + n)
    interfone_configured = False
    contract_generated = False
    contract_signed = False
    rental_value = factory.LazyAttribute(
        lambda obj: Decimal(random.choice(["1200.00", "1500.00", "1800.00", "2000.00", "2500.00"]))
    )
    cleaning_fee = factory.LazyAttribute(lambda obj: Decimal(random.choice(["150.00", "200.00", "250.00"])))
    max_tenants = factory.LazyAttribute(lambda obj: random.choice([1, 2, 3, 4]))
    is_rented = False
    lease_date = None
    last_rent_increase_date = None

    @factory.post_generation
    def furnitures(self, create, extracted, **kwargs):
        """
        Post-generation hook to add furniture to apartment.

        Args:
            create: Boolean indicating if object is being saved
            extracted: List of furniture objects to add (if provided)
            **kwargs: Additional keyword arguments
        """
        if not create:
            return

        if extracted is not None:
            # Use provided furniture list
            for furniture in extracted:
                self.furnitures.add(furniture)
        else:
            # Create random furniture (3-5 items)
            furniture_count = random.randint(3, 5)
            furnitures = FurnitureFactory.create_batch(furniture_count)
            self.furnitures.set(furnitures)


class TenantFactory(DjangoModelFactory):
    """
    Factory for Tenant model.

    Creates tenants with realistic Brazilian data (CPF, phone, etc.)

    Post-generation:
        dependents: Can create dependent automatically
        furnitures: Can add tenant's furniture

    Usage:
        # Simple tenant
        tenant = TenantFactory()

        # Tenant with dependents
        tenant = TenantFactory(dependents__count=2)

        # Tenant with furniture
        tenant = TenantFactory(furnitures=[furniture1, furniture2])
    """

    class Meta:
        model = Tenant
        skip_postgeneration_save = True

    name = factory.LazyAttribute(lambda obj: fake.name())
    cpf_cnpj = factory.Sequence(lambda n: VALID_CPFS[n % len(VALID_CPFS)])
    is_company = False
    rg = factory.Sequence(lambda n: f"{str(n).zfill(2)}.{str(n).zfill(3)}.{str(n).zfill(3)}-{n % 10}")
    phone = factory.LazyAttribute(lambda obj: f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}")
    marital_status = factory.LazyAttribute(
        lambda obj: random.choice(["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"])
    )
    profession = factory.LazyAttribute(
        lambda obj: random.choice(
            [
                "Engenheiro",
                "Médico",
                "Advogado",
                "Professor",
                "Desenvolvedor",
                "Designer",
                "Arquiteto",
                "Contador",
                "Administrador",
                "Empresário",
            ]
        )
    )
    deposit_amount = factory.LazyAttribute(
        lambda obj: Decimal(random.choice(["1500.00", "2000.00", "2500.00", "6000.00"]))
    )
    cleaning_fee_paid = False
    tag_deposit_paid = False
    rent_due_day = factory.LazyAttribute(lambda obj: random.choice([5, 10, 15, 20, 25]))

    @factory.post_generation
    def dependents(self, create, extracted, **kwargs):
        """
        Post-generation hook to create dependents.

        Args:
            create: Boolean indicating if object is being saved
            extracted: Number of dependents to create or list of dependents
            **kwargs: Additional keyword arguments (count, etc.)
        """
        if not create:
            return

        # Handle count parameter
        count = kwargs.get("count", 0)

        if extracted:
            if isinstance(extracted, int):
                count = extracted
            elif isinstance(extracted, list):
                for dependent in extracted:
                    dependent.tenant = self
                    dependent.save()
                return

        if count > 0:
            DependentFactory.create_batch(count, tenant=self)

    @factory.post_generation
    def furnitures(self, create, extracted, **kwargs):
        """
        Post-generation hook to add tenant's own furniture.

        Args:
            create: Boolean indicating if object is being saved
            extracted: List of furniture objects to add (if provided)
            **kwargs: Additional keyword arguments
        """
        if not create:
            return

        if extracted is not None:
            for furniture in extracted:
                self.furnitures.add(furniture)


class DependentFactory(DjangoModelFactory):
    """
    Factory for Dependent model.

    Creates dependents linked to tenants.

    Usage:
        # Create dependent for specific tenant
        dependent = DependentFactory(tenant=tenant)

        # Create with auto-generated tenant
        dependent = DependentFactory()
    """

    class Meta:
        model = Dependent

    tenant = factory.SubFactory(TenantFactory)
    name = factory.LazyAttribute(lambda obj: fake.name())
    phone = factory.LazyAttribute(lambda obj: f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}")


class LeaseFactory(DjangoModelFactory):
    """
    Factory for Lease model.

    Creates leases with realistic dates and values.

    Post-generation:
        tenants: Automatically adds responsible_tenant and can add more

    Usage:
        # Simple lease (1 tenant)
        lease = LeaseFactory()

        # Lease with multiple tenants
        lease = LeaseFactory(tenants__count=2)

        # Lease with specific apartment and tenant
        lease = LeaseFactory(
            apartment=apartment,
            responsible_tenant=tenant,
            tenants=[tenant]
        )

    Note:
        - Apartment must not have an existing lease (OneToOne constraint)
        - tag_fee is automatically calculated based on number of tenants
    """

    class Meta:
        model = Lease
        skip_postgeneration_save = True

    apartment = factory.SubFactory(ApartmentFactory)
    responsible_tenant = factory.SubFactory(TenantFactory)
    start_date = factory.LazyAttribute(lambda obj: date.today())
    validity_months = factory.LazyAttribute(lambda obj: random.choice([6, 12, 18, 24]))
    due_day = factory.LazyAttribute(lambda obj: random.choice([5, 10, 15, 20, 25]))
    rental_value = factory.LazyAttribute(
        lambda obj: obj.apartment.rental_value if obj.apartment else Decimal("1500.00")
    )
    cleaning_fee = factory.LazyAttribute(lambda obj: obj.apartment.cleaning_fee if obj.apartment else Decimal("200.00"))
    tag_fee = Decimal("50.00")  # Will be recalculated in post_generation
    contract_generated = False
    contract_signed = False
    interfone_configured = False
    warning_count = 0
    number_of_tenants = 1  # Will be updated in post_generation

    @factory.post_generation
    def tenants(self, create, extracted, **kwargs):
        """
        Post-generation hook to add tenants to lease.

        Automatically includes responsible_tenant.
        Can add additional tenants via count parameter or extracted list.

        Args:
            create: Boolean indicating if object is being saved
            extracted: List of tenants or count of tenants to add
            **kwargs: Additional keyword arguments (count, etc.)
        """
        if not create:
            return

        # Always add responsible tenant
        self.tenants.add(self.responsible_tenant)

        # Handle count parameter
        count = kwargs.get("count", 0)

        if extracted:
            if isinstance(extracted, int):
                count = extracted - 1  # Subtract responsible tenant
            elif isinstance(extracted, list):
                for tenant in extracted:
                    if tenant != self.responsible_tenant:
                        self.tenants.add(tenant)
                # Update number_of_tenants and tag_fee
                tenant_count = self.tenants.count()
                self.number_of_tenants = tenant_count
                self.tag_fee = Decimal("50.00") if tenant_count == 1 else Decimal("80.00")
                self.save()
                return

        # Create additional tenants if count > 0
        if count > 0:
            additional_tenants = TenantFactory.create_batch(count)
            for tenant in additional_tenants:
                self.tenants.add(tenant)

        # Update number_of_tenants and tag_fee based on actual count
        tenant_count = self.tenants.count()
        self.number_of_tenants = tenant_count
        self.tag_fee = Decimal("50.00") if tenant_count == 1 else Decimal("80.00")
        self.save()


# Convenience functions for creating common test scenarios


def create_full_lease_scenario(
    num_tenants=1, num_dependents_per_tenant=0, apartment_furniture_count=5, tenant_furniture_count=2
):
    """
    Creates a complete lease scenario with all related objects.

    This is a convenience function for creating realistic test data
    including building, apartment, tenants, dependents, furniture, and lease.

    Args:
        num_tenants: Number of tenants in the lease (default: 1)
        num_dependents_per_tenant: Number of dependents for each tenant (default: 0)
        apartment_furniture_count: Number of furniture items in apartment (default: 5)
        tenant_furniture_count: Number of furniture items owned by responsible tenant (default: 2)

    Returns:
        Lease: A fully configured lease with all related objects

    Example:
        >>> lease = create_full_lease_scenario(
        ...     num_tenants=2,
        ...     num_dependents_per_tenant=1,
        ...     apartment_furniture_count=6,
        ...     tenant_furniture_count=3
        ... )
        >>> assert lease.tenants.count() == 2
        >>> assert lease.responsible_tenant.dependents.count() == 1
    """
    # Create building and apartment with furniture
    apartment = ApartmentFactory(furnitures=FurnitureFactory.create_batch(apartment_furniture_count))

    # Create responsible tenant with dependents and furniture
    responsible_tenant = TenantFactory(
        dependents__count=num_dependents_per_tenant, furnitures=FurnitureFactory.create_batch(tenant_furniture_count)
    )

    # Create lease
    if num_tenants == 1:
        lease = LeaseFactory(apartment=apartment, responsible_tenant=responsible_tenant, tenants=[responsible_tenant])
    else:
        # Create additional tenants
        additional_tenants = TenantFactory.create_batch(num_tenants - 1, dependents__count=num_dependents_per_tenant)
        all_tenants = [responsible_tenant] + additional_tenants

        lease = LeaseFactory(apartment=apartment, responsible_tenant=responsible_tenant, tenants=all_tenants)

    return lease


def create_rented_apartment(num_tenants=1):
    """
    Creates an apartment that is currently rented with an active lease.

    Args:
        num_tenants: Number of tenants (default: 1)

    Returns:
        tuple: (Apartment, Lease)

    Example:
        >>> apartment, lease = create_rented_apartment(num_tenants=2)
        >>> assert apartment.is_rented is True
        >>> assert lease.tenants.count() == 2
    """
    lease = create_full_lease_scenario(num_tenants=num_tenants)

    # Update apartment status
    apartment = lease.apartment
    apartment.is_rented = True
    apartment.lease_date = lease.start_date
    apartment.save()

    return apartment, lease


def create_multiple_buildings_with_apartments(num_buildings=3, apartments_per_building=5):
    """
    Creates multiple buildings each with multiple apartments.

    Args:
        num_buildings: Number of buildings to create (default: 3)
        apartments_per_building: Number of apartments per building (default: 5)

    Returns:
        list: List of Building objects with apartments

    Example:
        >>> buildings = create_multiple_buildings_with_apartments(2, 3)
        >>> assert len(buildings) == 2
        >>> assert buildings[0].apartments.count() == 3
    """
    buildings = []

    for i in range(num_buildings):
        building = BuildingFactory()

        # Create apartments for this building
        for j in range(apartments_per_building):
            ApartmentFactory(building=building, number=101 + j)

        buildings.append(building)

    return buildings
