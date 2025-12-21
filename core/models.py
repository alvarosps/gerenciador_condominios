"""
Django models for Condomínios Manager.

This module defines the core domain models for property management:
- Building: Property buildings
- Apartment: Individual units within buildings
- Furniture: Furniture items in apartments
- Tenant: People renting apartments
- Dependent: Tenant dependents
- Lease: Rental contracts
"""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# Import validators (note: we don't enforce these on existing data)
from core.validators import validate_due_day


class Building(models.Model):
    """
    Represents a building/property managed by the system.

    Attributes:
        street_number: Unique identifier number for the building
        name: Display name of the building
        address: Full address of the building
    """

    street_number = models.PositiveIntegerField(
        unique=True, help_text="Número da rua (ex.: 836 ou 850)"
    )
    name = models.CharField(max_length=100, help_text="Nome do prédio")
    address = models.CharField(max_length=200, help_text="Endereço completo do prédio")

    def __str__(self) -> str:
        """Return string representation of building."""
        return f"{self.name} - {self.street_number}"


class Furniture(models.Model):
    """
    Represents furniture items that can be associated with apartments or tenants.

    Attributes:
        name: Unique name of the furniture item
        description: Optional detailed description
    """

    name = models.CharField(
        max_length=100, unique=True, help_text="Nome do móvel (ex.: Fogão, Geladeira, etc.)"
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        """Return string representation of furniture."""
        return self.name


class Apartment(models.Model):
    """
    Represents an individual apartment unit within a building.

    Attributes:
        building: Parent building containing this apartment
        number: Apartment number within the building
        interfone_configured: Whether intercom is configured
        contract_generated: Whether rental contract has been generated
        contract_signed: Whether contract has been signed
        rental_value: Monthly rental amount
        cleaning_fee: One-time cleaning fee
        max_tenants: Maximum allowed tenants
        is_rented: Current rental status
        lease_date: Date when current lease started
        last_rent_increase_date: Date of most recent rent increase
        furnitures: Furniture items included with apartment
    """

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="apartments")
    number = models.PositiveIntegerField(help_text="Número único do apartamento no prédio")
    interfone_configured = models.BooleanField(
        default=False, help_text="Indica se o interfone está configurado"
    )
    contract_generated = models.BooleanField(default=False, help_text="Contrato foi gerado?")
    contract_signed = models.BooleanField(default=False, help_text="Contrato foi assinado?")

    rental_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Valor do aluguel",
    )
    cleaning_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), help_text="Taxa de limpeza"
    )
    max_tenants = models.PositiveIntegerField(help_text="Número máximo de inquilinos permitidos")

    is_rented = models.BooleanField(default=False, help_text="Apartamento alugado ou não")
    lease_date = models.DateField(blank=True, null=True, help_text="Data da locação (caso alugado)")
    last_rent_increase_date = models.DateField(
        blank=True, null=True, help_text="Data do último reajuste do aluguel"
    )

    # Relação com móveis disponíveis no apartamento
    furnitures = models.ManyToManyField(
        Furniture,
        blank=True,
        related_name="apartments",
        help_text="Móveis presentes no apartamento",
    )

    class Meta:
        unique_together = ("building", "number")
        ordering = ["building__street_number", "number"]
        indexes = [
            # Composite indexes (Phase 5) for common query patterns
            models.Index(fields=["building", "is_rented"], name="apt_building_rented_idx"),
            models.Index(fields=["is_rented", "rental_value"], name="apt_rented_value_idx"),
            models.Index(fields=["building", "number"], name="apt_building_number_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of apartment."""
        return f"Apto {self.number} - {self.building.street_number}"


class Tenant(models.Model):
    """
    Represents a tenant (individual or company) renting an apartment.

    Attributes:
        name: Full name or company name
        cpf_cnpj: Brazilian tax ID (CPF for individuals, CNPJ for companies)
        is_company: Whether tenant is a company (PJ) or individual (PF)
        rg: Brazilian national ID (optional for companies)
        phone: Contact phone number
        marital_status: Marital status (for individuals)
        profession: Occupation or business type
        deposit_amount: Security deposit amount
        cleaning_fee_paid: Whether cleaning fee has been paid
        tag_deposit_paid: Whether tag deposit has been paid
        rent_due_day: Day of month when rent is due
        furnitures: Furniture items owned by tenant
    """

    # Brazilian marital status choices
    MARITAL_STATUS_CHOICES = [
        ("Solteiro(a)", "Solteiro(a)"),
        ("Casado(a)", "Casado(a)"),
        ("Divorciado(a)", "Divorciado(a)"),
        ("Viúvo(a)", "Viúvo(a)"),
        ("União Estável", "União Estável"),
    ]

    # Dados básicos
    name = models.CharField(max_length=150, help_text="Nome completo ou razão social")
    cpf_cnpj = models.CharField(
        max_length=20,
        unique=True,
        help_text="CPF (ou CNPJ em caso de empresa)",
        db_index=True,  # Add index for faster lookups
    )
    is_company = models.BooleanField(default=False, help_text="Indica se é Pessoa Jurídica")
    rg = models.CharField(
        max_length=20, blank=True, null=True, help_text="RG (não obrigatório para empresas)"
    )
    phone = models.CharField(max_length=20, help_text="Telefone de contato")
    marital_status = models.CharField(
        max_length=50, choices=MARITAL_STATUS_CHOICES, help_text="Estado civil"
    )
    profession = models.CharField(max_length=100, help_text="Profissão")

    # Dados financeiros e administrativos
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valor da caução, se houver",
    )
    cleaning_fee_paid = models.BooleanField(
        default=False, help_text="Indica se pagou a taxa de limpeza"
    )
    tag_deposit_paid = models.BooleanField(
        default=False, help_text="Indica se o caução das tags já foi pago"
    )
    rent_due_day = models.PositiveIntegerField(help_text="Dia do vencimento do aluguel", default=1)

    # Relação com móveis próprios do inquilino
    furnitures = models.ManyToManyField(
        Furniture, blank=True, related_name="tenants", help_text="Móveis próprios do inquilino"
    )

    class Meta:
        indexes = [
            # Composite indexes (Phase 5) for common query patterns
            models.Index(fields=["is_company", "name"], name="tenant_type_name_idx"),
            models.Index(fields=["marital_status", "is_company"], name="tenant_status_type_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of tenant."""
        return self.name


class Dependent(models.Model):
    """
    Represents a dependent of a tenant.

    Attributes:
        tenant: Parent tenant who has this dependent
        name: Full name of dependent
        phone: Contact phone number for dependent
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="dependents")
    name = models.CharField(max_length=150, help_text="Nome do dependente")
    phone = models.CharField(max_length=20, help_text="Telefone do dependente")

    def __str__(self) -> str:
        """Return string representation of dependent."""
        return f"{self.name} (dependente de {self.tenant.name})"


class Lease(models.Model):
    """
    Represents a rental lease/contract for an apartment.

    Attributes:
        apartment: Apartment being rented
        responsible_tenant: Primary tenant responsible for the lease
        tenants: All tenants living in the apartment
        number_of_tenants: Declared number of occupants (used for tag fee calculation).
                          Can be >= actual tenant count to account for additional occupants
                          not formally registered as tenants.
        start_date: Lease start date
        validity_months: Duration of lease in months
        due_day: Day of month when rent is due
        rental_value: Monthly rent amount
        cleaning_fee: One-time cleaning fee
        tag_fee: Tag/key deposit amount
        contract_generated: Whether contract PDF has been generated
        contract_signed: Whether contract has been signed
        interfone_configured: Whether intercom has been configured
        warning_count: Number of rule violation warnings
    """

    apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE, related_name="lease")
    responsible_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="leases_responsible",
        help_text="Inquilino responsável pela locação",
    )
    tenants = models.ManyToManyField(
        Tenant, related_name="leases", help_text="Inquilinos que residem no apartamento"
    )
    number_of_tenants = models.PositiveIntegerField(
        help_text="Número de ocupantes (para cálculo de taxa de tag). "
        "Pode ser maior que o número de inquilinos registrados.",
        default=1,
    )

    start_date = models.DateField(
        help_text="Data de início da locação", db_index=True  # Add index for date range queries
    )
    validity_months = models.PositiveIntegerField(help_text="Validade do contrato em meses")
    due_day = models.PositiveIntegerField(
        help_text="Dia do vencimento do aluguel",
        validators=[validate_due_day],  # Validate 1-31 range
    )

    rental_value = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Valor do aluguel"
    )
    cleaning_fee = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Valor da taxa de limpeza"
    )
    tag_fee = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Valor da caução da tag", default=0
    )

    contract_generated = models.BooleanField(
        default=False, help_text="Indica se o contrato foi gerado"
    )
    contract_signed = models.BooleanField(
        default=False, help_text="Indica se o contrato foi assinado"
    )
    interfone_configured = models.BooleanField(
        default=False, help_text="Indica se o interfone foi configurado"
    )

    warning_count = models.PositiveIntegerField(
        default=0, help_text="Número de avisos do inquilino por descumprimento das regras"
    )

    class Meta:
        indexes = [
            # Single-column indexes (Phase 3)
            models.Index(fields=["start_date"], name="lease_start_date_idx"),
            models.Index(fields=["contract_generated"], name="lease_contract_gen_idx"),
            # Composite indexes (Phase 5) for common query patterns
            models.Index(fields=["apartment", "start_date"], name="lease_apt_date_idx"),
            models.Index(fields=["responsible_tenant", "start_date"], name="lease_tenant_date_idx"),
            models.Index(fields=["contract_generated", "start_date"], name="lease_status_date_idx"),
            models.Index(fields=["due_day", "start_date"], name="lease_due_date_idx"),
        ]

    def clean(self) -> None:
        """
        Perform model-level validation.

        Validates:
        - Due day is in valid range (1-31)
        - Lease date consistency
        - Tenant count consistency (if saved)

        Note: This is only called when full_clean() is explicitly invoked,
        not automatically on save(). This maintains backward compatibility
        with existing data.
        """
        super().clean()

        from core.validators import validate_lease_dates, validate_tenant_count

        # Validate lease dates
        try:
            validate_lease_dates(self)
        except ValidationError:
            # Re-raise to preserve error structure
            raise

        # Validate tenant count (only if lease is saved)
        if self.pk:
            try:
                validate_tenant_count(self)
            except ValidationError:
                # Re-raise to preserve error structure
                raise

    def __str__(self) -> str:
        """Return string representation of lease."""
        return f"Locação do Apto {self.apartment.number} - {self.apartment.building.street_number}"
