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

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

# Import validators (note: we don't enforce these on existing data)
from core.validators import validate_brazilian_phone, validate_cnpj, validate_cpf, validate_due_day

# =============================================================================
# BASE MIXINS
# =============================================================================


class SoftDeleteManager(models.Manager):
    """
    Custom manager that excludes soft-deleted objects by default.

    Provides additional methods to access deleted and all objects.
    """

    def get_queryset(self):
        """Return queryset excluding soft-deleted objects."""
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        """Return queryset including soft-deleted objects."""
        return super().get_queryset()

    def deleted_only(self):
        """Return queryset with only soft-deleted objects."""
        return super().get_queryset().filter(is_deleted=True)


class AuditMixin(models.Model):
    """
    Abstract mixin providing audit trail fields for tracking creation and modification.

    Attributes:
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last modified
        created_by: User who created the record
        updated_by: User who last modified the record
    """

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Data/hora de criação do registro",
    )
    updated_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Data/hora da última modificação",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        editable=False,
        help_text="Usuário que criou o registro",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        editable=False,
        help_text="Usuário que modificou o registro",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Override save to automatically update updated_at timestamp."""
        if self.pk:  # If updating existing record
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class SoftDeleteMixin(models.Model):
    """
    Abstract mixin providing soft delete functionality.

    Instead of permanently deleting records, marks them as deleted
    and excludes them from default queries.

    Attributes:
        is_deleted: Flag indicating if the record is soft-deleted
        deleted_at: Timestamp when the record was soft-deleted
        deleted_by: User who soft-deleted the record
    """

    is_deleted = models.BooleanField(
        default=False,
        editable=False,
        db_index=True,
        help_text="Indica se o registro foi excluído",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="Data/hora da exclusão",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
        editable=False,
        help_text="Usuário que excluiu o registro",
    )

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard_delete=False, deleted_by=None):
        """
        Soft delete the record or perform hard delete if explicitly requested.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent model instances
            hard_delete: If True, permanently delete the record
            deleted_by: User performing the deletion (for audit)
        """
        if hard_delete:
            super().delete(using=using, keep_parents=keep_parents)
        else:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            if deleted_by:
                self.deleted_by = deleted_by
            self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def restore(self, restored_by=None):
        """
        Restore a soft-deleted record.

        Args:
            restored_by: User performing the restoration (for audit)
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        if restored_by:
            self.updated_by = restored_by
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_by"])


# =============================================================================
# DOMAIN MODELS
# =============================================================================


class Building(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents a building/property managed by the system.

    Attributes:
        street_number: Unique identifier number for the building
        name: Display name of the building
        address: Full address of the building

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    street_number = models.PositiveIntegerField(unique=True, help_text="Número da rua (ex.: 836 ou 850)")
    name = models.CharField(max_length=100, help_text="Nome do prédio")
    address = models.CharField(max_length=200, help_text="Endereço completo do prédio")

    # Custom manager that excludes soft-deleted objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted

    def __str__(self) -> str:
        """Return string representation of building."""
        return f"{self.name} - {self.street_number}"


class Furniture(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents furniture items that can be associated with apartments or tenants.

    Attributes:
        name: Unique name of the furniture item
        description: Optional detailed description

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    name = models.CharField(max_length=100, unique=True, help_text="Nome do móvel (ex.: Fogão, Geladeira, etc.)")
    description = models.TextField(blank=True, null=True)

    # Custom manager that excludes soft-deleted objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted

    def __str__(self) -> str:
        """Return string representation of furniture."""
        return self.name


class Apartment(AuditMixin, SoftDeleteMixin, models.Model):
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

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="apartments")
    number = models.PositiveIntegerField(help_text="Número único do apartamento no prédio")
    interfone_configured = models.BooleanField(default=False, help_text="Indica se o interfone está configurado")
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
    last_rent_increase_date = models.DateField(blank=True, null=True, help_text="Data do último reajuste do aluguel")

    # Relação com móveis disponíveis no apartamento
    furnitures = models.ManyToManyField(
        Furniture,
        blank=True,
        related_name="apartments",
        help_text="Móveis presentes no apartamento",
    )

    # Custom manager that excludes soft-deleted objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted

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


class Tenant(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents a tenant (individual or company) renting an apartment.

    Attributes:
        user: Associated user account for tenant portal access (optional)
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

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    # Associated user account for tenant portal access
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_profile",
        help_text="Conta de usuário associada para acesso ao portal do inquilino",
    )

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
    rg = models.CharField(max_length=20, blank=True, null=True, help_text="RG (não obrigatório para empresas)")
    phone = models.CharField(
        max_length=20,
        help_text="Telefone de contato",
        validators=[validate_brazilian_phone],
    )
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS_CHOICES, help_text="Estado civil")
    profession = models.CharField(max_length=100, help_text="Profissão")

    # Dados financeiros e administrativos
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valor da caução, se houver",
    )
    cleaning_fee_paid = models.BooleanField(default=False, help_text="Indica se pagou a taxa de limpeza")
    tag_deposit_paid = models.BooleanField(default=False, help_text="Indica se o caução das tags já foi pago")
    rent_due_day = models.PositiveIntegerField(help_text="Dia do vencimento do aluguel", default=1)

    # Relação com móveis próprios do inquilino
    furnitures = models.ManyToManyField(
        Furniture, blank=True, related_name="tenants", help_text="Móveis próprios do inquilino"
    )

    # Custom manager that excludes soft-deleted objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted

    class Meta:
        indexes = [
            # Composite indexes (Phase 5) for common query patterns
            models.Index(fields=["is_company", "name"], name="tenant_type_name_idx"),
            models.Index(fields=["marital_status", "is_company"], name="tenant_status_type_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of tenant."""
        return self.name

    def clean(self) -> None:
        """
        Validate tenant data.

        Validates:
        - CPF format when is_company=False
        - CNPJ format when is_company=True

        Note: This is only called when full_clean() is explicitly invoked.
        """
        super().clean()

        if self.cpf_cnpj:
            try:
                if self.is_company:
                    validate_cnpj(self.cpf_cnpj)
                else:
                    validate_cpf(self.cpf_cnpj)
            except ValidationError as e:
                raise ValidationError({"cpf_cnpj": e.message})

    def save(self, *args, **kwargs):
        """Override save to enforce validation before persisting."""
        self.full_clean()
        super().save(*args, **kwargs)


class Dependent(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents a dependent of a tenant.

    Attributes:
        tenant: Parent tenant who has this dependent
        name: Full name of dependent
        phone: Contact phone number for dependent

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="dependents")
    name = models.CharField(max_length=150, help_text="Nome do dependente")
    phone = models.CharField(
        max_length=20,
        help_text="Telefone do dependente",
        validators=[validate_brazilian_phone],
    )

    # Custom manager that excludes soft-deleted objects
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted

    def __str__(self) -> str:
        """Return string representation of dependent."""
        return f"{self.name} (dependente de {self.tenant.name})"


class Lease(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents a rental lease/contract for an apartment.

    Inherits from AuditMixin (created_at, updated_at, created_by, updated_by)
    and SoftDeleteMixin (is_deleted, deleted_at, deleted_by, soft delete support).

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
    tenants = models.ManyToManyField(Tenant, related_name="leases", help_text="Inquilinos que residem no apartamento")
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

    rental_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor do aluguel")
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da taxa de limpeza")
    tag_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da caução da tag", default=0)

    contract_generated = models.BooleanField(default=False, help_text="Indica se o contrato foi gerado")
    contract_signed = models.BooleanField(default=False, help_text="Indica se o contrato foi assinado")
    interfone_configured = models.BooleanField(default=False, help_text="Indica se o interfone foi configurado")

    warning_count = models.PositiveIntegerField(
        default=0, help_text="Número de avisos do inquilino por descumprimento das regras"
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all objects including deleted

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

    def save(self, *args, **kwargs):
        """Override save to enforce validation before persisting."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return string representation of lease."""
        return f"Locação do Apto {self.apartment.number} - {self.apartment.building.street_number}"


class Landlord(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents the property owner/landlord (LOCADOR).

    Singleton pattern: Only one active landlord at a time.
    All contract generation uses the active landlord's data.

    Attributes:
        name: Full name or company name
        nationality: Nationality (default: Brasileira)
        marital_status: Marital status
        cpf_cnpj: Brazilian tax ID (CPF or CNPJ)
        rg: Brazilian national ID (optional)
        phone: Contact phone number
        email: Email address (optional)
        street: Street/Avenue name
        street_number: Street number
        complement: Address complement (optional)
        neighborhood: Neighborhood
        city: City
        state: State
        zip_code: ZIP/Postal code
        country: Country (default: Brasil)
        is_active: Active status (only one can be active)

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    # Personal Information
    name = models.CharField(max_length=200, help_text="Nome completo ou razão social")
    nationality = models.CharField(
        max_length=100, default="Brasileira", help_text="Nacionalidade"
    )
    marital_status = models.CharField(
        max_length=50,
        choices=Tenant.MARITAL_STATUS_CHOICES,
        help_text="Estado civil",
    )
    cpf_cnpj = models.CharField(max_length=20, help_text="CPF ou CNPJ")
    rg = models.CharField(
        max_length=20, blank=True, null=True, help_text="RG (opcional)"
    )

    # Contact Information
    phone = models.CharField(
        max_length=20,
        help_text="Telefone de contato",
        validators=[validate_brazilian_phone],
    )
    email = models.EmailField(blank=True, null=True, help_text="Email de contato")

    # Address
    street = models.CharField(max_length=200, help_text="Rua/Avenida")
    street_number = models.CharField(max_length=20, help_text="Número")
    complement = models.CharField(
        max_length=100, blank=True, null=True, help_text="Complemento"
    )
    neighborhood = models.CharField(max_length=100, help_text="Bairro")
    city = models.CharField(max_length=100, help_text="Cidade")
    state = models.CharField(max_length=50, help_text="Estado")
    zip_code = models.CharField(max_length=10, help_text="CEP")
    country = models.CharField(max_length=100, default="Brasil", help_text="País")

    # Status
    is_active = models.BooleanField(
        default=True, help_text="Locador ativo (apenas um pode estar ativo)"
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Locador"
        verbose_name_plural = "Locadores"

    def __str__(self) -> str:
        """Return string representation of landlord."""
        return self.name

    @property
    def full_address(self) -> str:
        """Return formatted full address."""
        parts = [f"{self.street} {self.street_number}"]
        if self.complement:
            parts.append(self.complement)
        parts.append(f"Bairro {self.neighborhood}")
        parts.append(f"{self.city}, {self.state}, {self.country}")
        parts.append(f"CEP {self.zip_code}")
        return ", ".join(parts)

    def save(self, *args, **kwargs):
        """Ensure only one active landlord exists."""
        if self.is_active:
            # Deactivate other landlords
            Landlord.objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls) -> "Landlord | None":
        """Get the currently active landlord."""
        return cls.objects.filter(is_active=True).first()
