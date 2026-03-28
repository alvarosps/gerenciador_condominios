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

import re
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

# Import validators (note: we don't enforce these on existing data)
from core.validators import (
    validate_brazilian_phone,
    validate_cnpj,
    validate_cpf,
    validate_due_day,
    validate_lease_dates,
    validate_tenant_count,
)

# =============================================================================
# BASE MIXINS
# =============================================================================


class SoftDeleteManager(models.Manager):
    """
    Custom manager that excludes soft-deleted objects by default.

    Provides additional methods to access deleted and all objects.
    """

    def get_queryset(self) -> QuerySet[Any]:
        """Return queryset excluding soft-deleted objects."""
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self) -> QuerySet[Any]:
        """Return queryset including soft-deleted objects."""
        return super().get_queryset()

    def deleted_only(self) -> QuerySet[Any]:
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

    def save(self, *args: Any, **kwargs: Any) -> None:
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

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
        hard_delete: bool = False,
        deleted_by: Any = None,
    ) -> tuple[int, dict[str, int]]:
        """
        Soft delete the record or perform hard delete if explicitly requested.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent model instances
            hard_delete: If True, permanently delete the record
            deleted_by: User performing the deletion (for audit)
        """
        if hard_delete:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if deleted_by:
            self.deleted_by = deleted_by
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
        return 0, {}

    def restore(self, restored_by: Any = None) -> None:
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

    street_number = models.PositiveIntegerField(
        unique=True, help_text="Número da rua (ex.: 836 ou 850)"
    )
    name = models.CharField(max_length=100, help_text="Nome do prédio")
    address = models.CharField(max_length=200, help_text="Endereço completo do prédio")

    # Custom manager that excludes soft-deleted objects
    all_objects = models.Manager()  # Access all objects including deleted
    objects = SoftDeleteManager()

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

    name = models.CharField(
        max_length=100, unique=True, help_text="Nome do móvel (ex.: Fogão, Geladeira, etc.)"
    )
    description = models.TextField(blank=True, default="")

    # Custom manager that excludes soft-deleted objects
    all_objects = models.Manager()  # Access all objects including deleted
    objects = SoftDeleteManager()

    def __str__(self) -> str:
        """Return string representation of furniture."""
        return self.name


class Apartment(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents an individual apartment unit within a building.

    Attributes:
        building: Parent building containing this apartment
        number: Apartment number within the building
        rental_value: Monthly rental amount
        cleaning_fee: One-time cleaning fee
        max_tenants: Maximum allowed tenants
        is_rented: Current rental status — updated automatically via Lease signal
        last_rent_increase_date: Date of most recent rent increase
        furnitures: Furniture items included with apartment

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="apartments")
    number = models.PositiveIntegerField(help_text="Número único do apartamento no prédio")

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
    rental_value_double = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Valor do aluguel para 2 pessoas",
    )

    is_rented = models.BooleanField(
        default=False, help_text="Atualizado automaticamente via signal de Lease"
    )
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

    # Proprietário do apartamento
    owner = models.ForeignKey(
        "Person",
        null=True,
        blank=True,
        related_name="owned_apartments",
        on_delete=models.SET_NULL,
    )

    # Custom manager that excludes soft-deleted objects
    all_objects = models.Manager()  # Access all objects including deleted
    objects = SoftDeleteManager()

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
        due_day: Day of month when rent is due
        warning_count: Number of rule violation warnings issued to this tenant
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

    # Brazilian marital status choices (includes legacy values without "(a)" for backward compatibility)
    MARITAL_STATUS_CHOICES = [
        ("Solteiro(a)", "Solteiro(a)"),
        ("Casado(a)", "Casado(a)"),
        ("Divorciado(a)", "Divorciado(a)"),
        ("Viúvo(a)", "Viúvo(a)"),
        ("União Estável", "União Estável"),
        # Legacy values (backward compatibility)
        ("Solteiro", "Solteiro"),
        ("Casado", "Casado"),
        ("Divorciado", "Divorciado"),
        ("Viúvo", "Viúvo"),
        ("Separado", "Separado"),
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
        max_length=20, blank=True, default="", help_text="RG (não obrigatório para empresas)"
    )
    phone = models.CharField(
        max_length=20,
        help_text="Telefone de contato",
        validators=[validate_brazilian_phone],
    )
    marital_status = models.CharField(
        max_length=50, choices=MARITAL_STATUS_CHOICES, help_text="Estado civil"
    )
    profession = models.CharField(max_length=100, help_text="Profissão")

    # Dados financeiros e administrativos
    due_day = models.PositiveIntegerField(
        help_text="Dia do vencimento do aluguel",
        default=1,
        validators=[validate_due_day],
    )
    warning_count = models.PositiveIntegerField(
        default=0, help_text="Quantidade de avisos do inquilino"
    )

    # Relação com móveis próprios do inquilino
    furnitures = models.ManyToManyField(
        Furniture, blank=True, related_name="tenants", help_text="Móveis próprios do inquilino"
    )

    # Custom manager that excludes soft-deleted objects
    all_objects = models.Manager()  # Access all objects including deleted
    objects = SoftDeleteManager()

    class Meta:
        indexes = [
            # Composite indexes (Phase 5) for common query patterns
            models.Index(fields=["is_company", "name"], name="tenant_type_name_idx"),
            models.Index(fields=["marital_status", "is_company"], name="tenant_status_type_idx"),
        ]

    def __str__(self) -> str:
        """Return string representation of tenant."""
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to enforce validation before persisting."""
        self.full_clean()
        super().save(*args, **kwargs)

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
                raise ValidationError({"cpf_cnpj": e.message}) from e


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
    cpf_cnpj = models.CharField(
        max_length=14,
        blank=True,
        default="",
        help_text="CPF ou CNPJ do dependente",
    )

    # Custom manager that excludes soft-deleted objects
    all_objects = models.Manager()  # Access all objects including deleted
    objects = SoftDeleteManager()

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
        number_of_tenants: Number of occupants (1 or 2). Determines pricing tier.
                          Must be <= apartment.max_tenants.
        start_date: Lease start date
        validity_months: Duration of lease in months
        tag_fee: Tag/key deposit amount
        deposit_amount: Security deposit amount paid by tenant
        cleaning_fee_paid: Whether the cleaning fee has been paid
        tag_deposit_paid: Whether the tag deposit has been paid
        contract_generated: Whether contract PDF has been generated
        contract_signed: Whether contract has been signed
        interfone_configured: Whether intercom has been configured
    """

    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name="leases")
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
        help_text="Número de ocupantes (1 ou 2). Determina tier de preço. Deve ser <= apartment.max_tenants.",
        default=1,
    )
    resident_dependent = models.ForeignKey(
        "Dependent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leases_as_resident",
        help_text="Dependente que reside no apartamento neste contrato",
    )

    start_date = models.DateField(
        help_text="Data de início da locação",
        db_index=True,  # Add index for date range queries
    )
    validity_months = models.PositiveIntegerField(help_text="Validade do contrato em meses")

    tag_fee = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Valor da caução da tag", default=0
    )
    rental_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Valor do aluguel acordado no contrato",
    )

    # Campos do contrato (caução/pagamentos)
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Valor da caução"
    )
    cleaning_fee_paid = models.BooleanField(default=False, help_text="Taxa de limpeza paga")
    tag_deposit_paid = models.BooleanField(default=False, help_text="Caução de tags paga")

    contract_generated = models.BooleanField(
        default=False, help_text="Indica se o contrato foi gerado"
    )
    contract_signed = models.BooleanField(
        default=False, help_text="Indica se o contrato foi assinado"
    )
    interfone_configured = models.BooleanField(
        default=False, help_text="Indica se o interfone foi configurado"
    )

    # Financial fields
    prepaid_until = models.DateField(
        null=True, blank=True, help_text="Aluguel pré-pago até esta data."
    )
    is_salary_offset = models.BooleanField(
        default=False, help_text="Aluguel compensado como salário."
    )
    last_rent_increase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Data do último reajuste. Referência para o próximo reajuste anual.",
    )
    pending_rental_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Novo valor de aluguel pendente (reajuste com data futura).",
    )
    pending_rental_value_date = models.DateField(
        null=True,
        blank=True,
        help_text="Data a partir da qual o pending_rental_value entra em vigor.",
    )

    # Managers
    all_objects = models.Manager()  # Access all objects including deleted
    objects = SoftDeleteManager()

    class Meta:
        indexes = [
            # Single-column indexes (Phase 3)
            models.Index(fields=["start_date"], name="lease_start_date_idx"),
            models.Index(fields=["contract_generated"], name="lease_contract_gen_idx"),
            # Composite indexes (Phase 5) for common query patterns
            models.Index(fields=["apartment", "start_date"], name="lease_apt_date_idx"),
            models.Index(fields=["responsible_tenant", "start_date"], name="lease_tenant_date_idx"),
            models.Index(fields=["contract_generated", "start_date"], name="lease_status_date_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["apartment"],
                condition=models.Q(is_deleted=False),
                name="unique_active_lease_per_apartment",
            )
        ]

    def __str__(self) -> str:
        """Return string representation of lease."""
        return f"Locação do Apto {self.apartment.number} - {self.apartment.building.street_number}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to enforce validation before persisting."""
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """
        Perform model-level validation.

        Validates:
        - Lease date consistency
        - Tenant count (1 or 2, must not exceed apartment.max_tenants)
        """
        super().clean()

        # Validate lease dates
        validate_lease_dates(self)

        # Validate tenant count
        validate_tenant_count(self)


class RentAdjustment(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Records a rent adjustment applied to a lease.

    Attributes:
        lease: The lease this adjustment belongs to
        adjustment_date: Date the adjustment takes effect
        percentage: Adjustment percentage (positive = increase, negative = decrease)
        previous_value: Rental value before adjustment
        new_value: Rental value after adjustment
        apartment_updated: Whether the apartment's rental_value was updated

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    lease = models.ForeignKey(
        Lease,
        on_delete=models.CASCADE,
        related_name="rent_adjustments",
        help_text="Locação a qual o reajuste pertence",
    )
    adjustment_date = models.DateField(help_text="Data de aplicação do reajuste")
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentual aplicado (ex: 5.23 ou -0.64)",
    )
    previous_value = models.DecimalField(max_digits=10, decimal_places=2)
    new_value = models.DecimalField(max_digits=10, decimal_places=2)
    apartment_updated = models.BooleanField(default=False)

    # Managers
    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-adjustment_date"]

    def __str__(self) -> str:
        """Return string representation of rent adjustment."""
        return f"Reajuste {self.percentage}% - Locação Apto {self.lease.apartment.number}"


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
    nationality = models.CharField(max_length=100, default="Brasileira", help_text="Nacionalidade")
    marital_status = models.CharField(
        max_length=50,
        choices=Tenant.MARITAL_STATUS_CHOICES,
        help_text="Estado civil",
    )
    cpf_cnpj = models.CharField(max_length=20, help_text="CPF ou CNPJ")
    rg = models.CharField(max_length=20, blank=True, default="", help_text="RG (opcional)")

    # Contact Information
    phone = models.CharField(
        max_length=20,
        help_text="Telefone de contato",
        validators=[validate_brazilian_phone],
    )
    email = models.EmailField(blank=True, default="", help_text="Email de contato")

    # Address
    street = models.CharField(max_length=200, help_text="Rua/Avenida")
    street_number = models.CharField(max_length=20, help_text="Número")
    complement = models.CharField(max_length=100, blank=True, default="", help_text="Complemento")
    neighborhood = models.CharField(max_length=100, help_text="Bairro")
    city = models.CharField(max_length=100, help_text="Cidade")
    state = models.CharField(max_length=50, help_text="Estado")
    zip_code = models.CharField(max_length=10, help_text="CEP")
    country = models.CharField(max_length=100, default="Brasil", help_text="País")

    # Settings
    rent_adjustment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentual padrão de reajuste anual do aluguel (ex: 5.23)",
    )

    # Status
    is_active = models.BooleanField(
        default=True, help_text="Locador ativo (apenas um pode estar ativo)"
    )

    # Managers
    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        verbose_name = "Locador"
        verbose_name_plural = "Locadores"

    def __str__(self) -> str:
        """Return string representation of landlord."""
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Ensure only one active landlord exists."""
        if self.is_active:
            # Deactivate other landlords
            Landlord.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

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

    @classmethod
    def get_active(cls) -> "Landlord | None":
        """Get the currently active landlord."""
        return cls.objects.filter(is_active=True).first()


_RULE_TRUNCATE_LENGTH = 50


class ContractRule(AuditMixin, SoftDeleteMixin, models.Model):
    """
    Represents a condominium rule that appears in rental contracts.

    Rules are displayed in the contract's "Regras do prédio/Regras de Convivência"
    section and can be managed through the admin interface.

    Attributes:
        content: HTML content of the rule (supports <strong> for emphasis)
        order: Display order (lower numbers appear first)
        is_active: Whether the rule should be included in contracts

    Inherits audit fields (created_at, updated_at, created_by, updated_by)
    and soft delete capability (is_deleted, deleted_at, deleted_by).
    """

    content = models.TextField(help_text="Conteúdo HTML da regra (use <strong> para negrito)")
    order = models.PositiveIntegerField(
        default=0, db_index=True, help_text="Ordem de exibição (menores valores aparecem primeiro)"
    )
    is_active = models.BooleanField(
        default=True, db_index=True, help_text="Se a regra deve ser incluída nos contratos"
    )

    # Managers
    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Regra do Condomínio"
        verbose_name_plural = "Regras do Condomínio"
        indexes = [
            models.Index(fields=["is_active", "order"], name="rule_active_order_idx"),
        ]

    def __str__(self) -> str:
        """Return truncated rule content for display."""
        # Strip HTML and truncate
        clean_text = re.sub(r"<[^>]+>", "", self.content)
        if len(clean_text) > _RULE_TRUNCATE_LENGTH:
            return clean_text[:_RULE_TRUNCATE_LENGTH] + "..."
        return clean_text

    @classmethod
    def get_active_rules(cls) -> list[str]:
        """
        Get all active rules as a list of HTML strings.

        Returns list suitable for passing to contract template context.
        """
        return list(
            cls.objects.filter(is_active=True)
            .order_by("order", "id")
            .values_list("content", flat=True)
        )


# =============================================================================
# FINANCIAL MODULE MODELS
# =============================================================================


class Person(AuditMixin, SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_owner = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=False)
    initial_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Saldo devedor anterior ao sistema"
    )
    initial_balance_date = models.DateField(
        null=True, blank=True, help_text="Mês de referência do saldo devedor (dia 1 do mês)"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="person_profile",
    )
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CreditCard(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name="credit_cards", on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100)
    last_four_digits = models.CharField(max_length=4, blank=True)
    closing_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    due_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    is_active = models.BooleanField(default=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["person", "nickname"]
        unique_together = ["person", "nickname"]

    def __str__(self) -> str:
        return f"{self.nickname} ({self.person.name})"


class ExpenseCategory(AuditMixin, SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#6B7280")
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="subcategories", on_delete=models.CASCADE
    )

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Expense categories"

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class ExpenseType(models.TextChoices):
    CARD_PURCHASE = "card_purchase", "Compra no Cartão"
    BANK_LOAN = "bank_loan", "Empréstimo Bancário"
    PERSONAL_LOAN = "personal_loan", "Empréstimo Pessoal"
    WATER_BILL = "water_bill", "Conta de Água"
    ELECTRICITY_BILL = "electricity_bill", "Conta de Luz"
    PROPERTY_TAX = "property_tax", "IPTU"
    FIXED_EXPENSE = "fixed_expense", "Gasto Fixo Mensal"
    ONE_TIME_EXPENSE = "one_time_expense", "Gasto Único"
    EMPLOYEE_SALARY = "employee_salary", "Salário Funcionário"


class Expense(AuditMixin, SoftDeleteMixin, models.Model):
    description = models.CharField(max_length=500)
    expense_type = models.CharField(max_length=30, choices=ExpenseType.choices)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    person = models.ForeignKey(
        Person, null=True, blank=True, related_name="expenses", on_delete=models.SET_NULL
    )
    credit_card = models.ForeignKey(
        CreditCard, null=True, blank=True, related_name="expenses", on_delete=models.SET_NULL
    )
    building = models.ForeignKey(
        Building, null=True, blank=True, related_name="expenses", on_delete=models.SET_NULL
    )
    category = models.ForeignKey(
        ExpenseCategory, null=True, blank=True, related_name="expenses", on_delete=models.SET_NULL
    )
    is_installment = models.BooleanField(default=False)
    total_installments = models.PositiveIntegerField(null=True, blank=True)
    is_debt_installment = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    expected_monthly_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    recurrence_day = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Data fim para gastos fixos recorrentes. Projeção para após esta data.",
    )
    is_offset = models.BooleanField(
        default=False,
        help_text="Desconto: valor é subtraído do total da pessoa (compra feita no cartão dela, mas para os sogros/Camila).",
    )
    bank_name = models.CharField(max_length=100, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-expense_date"]
        indexes = [
            models.Index(fields=["-expense_date"], name="expense_date_idx"),
            models.Index(fields=["expense_type", "-expense_date"], name="expense_type_date_idx"),
            models.Index(fields=["is_paid", "-expense_date"], name="expense_paid_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.description} - R${self.total_amount}"


class ExpenseInstallment(AuditMixin, SoftDeleteMixin, models.Model):
    expense = models.ForeignKey(Expense, related_name="installments", on_delete=models.CASCADE)
    installment_number = models.PositiveIntegerField()
    total_installments = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        unique_together = ["expense", "installment_number"]
        ordering = ["due_date", "installment_number"]
        indexes = [
            models.Index(fields=["due_date"], name="installment_due_date_idx"),
            models.Index(fields=["is_paid", "due_date"], name="installment_paid_due_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.expense.description} - Parcela {self.installment_number}/{self.total_installments}"


class PersonIncomeType(models.TextChoices):
    APARTMENT_RENT = "apartment_rent", "Aluguel de Apartamento"
    FIXED_STIPEND = "fixed_stipend", "Estipêndio Fixo"


class PersonIncome(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name="incomes", on_delete=models.CASCADE)
    income_type = models.CharField(max_length=20, choices=PersonIncomeType.choices)
    apartment = models.ForeignKey(Apartment, null=True, blank=True, on_delete=models.SET_NULL)
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.person.name} - {self.get_income_type_display()}"


class Income(AuditMixin, SoftDeleteMixin, models.Model):
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    income_date = models.DateField()
    person = models.ForeignKey(
        Person, null=True, blank=True, related_name="extra_incomes", on_delete=models.SET_NULL
    )
    building = models.ForeignKey(
        Building, null=True, blank=True, related_name="extra_incomes", on_delete=models.SET_NULL
    )
    category = models.ForeignKey(ExpenseCategory, null=True, blank=True, on_delete=models.SET_NULL)
    is_recurring = models.BooleanField(default=False)
    expected_monthly_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    is_received = models.BooleanField(default=False)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-income_date"]

    def __str__(self) -> str:
        return f"{self.description} - R${self.amount}"


class RentPayment(AuditMixin, SoftDeleteMixin, models.Model):
    lease = models.ForeignKey(Lease, related_name="rent_payments", on_delete=models.CASCADE)
    reference_month = models.DateField()
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        unique_together = ["lease", "reference_month"]
        ordering = ["-reference_month"]
        indexes = [
            models.Index(fields=["-reference_month"], name="rent_payment_month_idx"),
            models.Index(fields=["lease", "-reference_month"], name="rent_payment_lease_month_idx"),
        ]

    def __str__(self) -> str:
        return f"Pagamento {self.reference_month.strftime('%m/%Y')} - Apto {self.lease.apartment.number}"


class EmployeePayment(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name="employee_payments", on_delete=models.CASCADE)
    reference_month = models.DateField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    variable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rent_offset = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cleaning_count = models.PositiveIntegerField(default=0)
    payment_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        unique_together = ["person", "reference_month"]
        ordering = ["-reference_month"]

    def __str__(self) -> str:
        return f"Pagamento {self.person.name} - {self.reference_month.strftime('%m/%Y')}"

    @property
    def total_paid(self) -> Decimal:
        return self.base_salary + self.variable_amount


class PersonPayment(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name="payments_received", on_delete=models.CASCADE)
    reference_month = models.DateField(
        help_text="Primeiro dia do mês de referência (ex: 2026-03-01)"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["person", "reference_month"], name="person_payment_month_idx"),
        ]

    def __str__(self) -> str:
        return f"Pagamento R${self.amount} a {self.person.name} - {self.reference_month.strftime('%m/%Y')}"


class PersonPaymentSchedule(AuditMixin, SoftDeleteMixin, models.Model):
    """Configurable payment schedule entry for a person in a specific month."""

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="payment_schedules",
    )
    reference_month = models.DateField(
        help_text="First day of the month (e.g., 2026-03-01)",
    )
    due_day = models.PositiveSmallIntegerField(
        help_text="Day of month for this payment (1-31, capped to last day)",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["reference_month", "due_day"]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "reference_month", "due_day"],
                condition=models.Q(is_deleted=False),
                name="unique_person_schedule_per_day",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.person.name} - {self.reference_month:%m/%Y} day {self.due_day}: R${self.amount}"
        )


class ExpenseMonthSkip(AuditMixin, models.Model):
    """Marks an expense as not charged in a specific month."""

    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="month_skips",
    )
    reference_month = models.DateField(
        help_text="First day of the month (e.g., 2026-03-01)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "reference_month"],
                name="unique_expense_skip_per_month",
            ),
        ]

    def __str__(self) -> str:
        return f"Skip: {self.expense.description} - {self.reference_month:%m/%Y}"


class FinancialSettings(models.Model):
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    initial_balance_date = models.DateField()
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = "Financial settings"

    def __str__(self) -> str:
        return f"Saldo inicial: R${self.initial_balance}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        if FinancialSettings.objects.filter(pk=1).exists():
            kwargs.pop("force_insert", None)
            kwargs["force_update"] = True
        super().save(*args, **kwargs)


class IPCAIndex(models.Model):
    """IPCA monthly index values from IBGE SIDRA API (table 1737, variable 2266).

    Base: December 1993 = 100. Used to calculate rent adjustment factors.
    """

    reference_month = models.DateField(
        unique=True,
        help_text="Primeiro dia do mês de referência (ex: 2026-03-01)",
    )
    value = models.DecimalField(
        max_digits=20,
        decimal_places=13,
        help_text="Número-índice IPCA (base dez/1993 = 100)",
    )
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reference_month"]
        indexes = [
            models.Index(fields=["reference_month"], name="ipca_index_month_idx"),
        ]

    def __str__(self) -> str:
        return f"IPCA {self.reference_month.strftime('%m/%Y')}: {self.value}"
