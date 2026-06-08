"""Finances app models — bill core (Phase 2, Session 36).

Models: Category, BillingAccount, Bill, BillLineItem, BillSkip, Payment,
PaymentAllocation. Reuses core's AuditMixin / SoftDeleteMixin / SoftDeleteManager
(unidirectional dependency finances -> core).

Bill amount figures (amount_total / amount_paid / amount_remaining /
payment_status / is_overdue) are ORM annotations via Bill.objects.with_amounts(today)
— never Python @property (design §4.4). Installment/Employee source FKs on Bill,
and the installment FK on BillLineItem, are added in Session 41 (the models don't
exist yet); only Bill.billing_account is created here.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from core.models import (
    AuditMixin,
    Building,
    Condominium,
    Lease,
    Person,
    SoftDeleteManager,
    SoftDeleteMixin,
)

_MONEY: DecimalField = DecimalField(max_digits=12, decimal_places=2)
_ZERO_MONEY = Value(Decimal(0), output_field=_MONEY)


class BillBehavior(models.TextChoices):
    ONE_TIME = "one_time", "Avulsa"
    RECURRING = "recurring", "Recorrente"
    INSTALLMENT = "installment", "Parcelada"


class BillLifecycleState(models.TextChoices):
    ACTIVE = "active", "Ativa"
    SUSPENDED = "suspended", "Suspensa"
    DEFERRED = "deferred", "Adiada"
    CANCELED = "canceled", "Cancelada"


class BillingAccountState(models.TextChoices):
    ACTIVE = "active", "Ativa"
    SUSPENDED = "suspended", "Suspensa"
    DEFERRED = "deferred", "Adiada"
    ENDED = "ended", "Encerrada"


class BillingAccountType(models.TextChoices):
    WATER = "water", "Água"
    ELECTRICITY = "electricity", "Luz"
    IPTU = "iptu", "IPTU"
    INTERNET = "internet", "Internet"
    GENERIC = "generic", "Genérica"


class SupplyStatus(models.TextChoices):
    """Physical supply line state (water/power) — distinct from BillingAccountState (the
    account's lifecycle). A cut supply still has an active registry account (design §3.1)."""

    ACTIVE = "active", "Ligada"
    CUT = "cut", "Cortada"


class FundedFrom(models.TextChoices):
    CAIXA = "caixa", "Caixa"
    RESERVE = "reserve", "Reserva"


class Category(AuditMixin, SoftDeleteMixin, models.Model):
    """Classification tree (self-FK), condominium-scoped. No treebeard (YAGNI)."""

    condominium = models.ForeignKey(
        Condominium, on_delete=models.PROTECT, related_name="categories"
    )
    name = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    color = models.CharField(max_length=20, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "parent", "name"],
                condition=Q(is_deleted=False),
                # Treat NULL parent (root categories) as equal so duplicate roots collide.
                nulls_distinct=False,
                name="unique_active_finance_category",
            ),
        ]

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


_TYPED_IDENTITY_ACCOUNT_TYPES = frozenset(
    {BillingAccountType.WATER, BillingAccountType.ELECTRICITY, BillingAccountType.IPTU}
)
_ERR_IDENTIFIER_REQUIRED = "Informe a inscrição/UC para contas de água, luz ou IPTU."


class BillingAccountQuerySet(models.QuerySet["BillingAccount"]):
    def recurring_for_generation(self) -> "BillingAccountQuerySet":
        """Active accounts that generate a recurring Bill — IPTU is registry-only (design §10.3).

        Single shared predicate used by BillGenerationService.ensure_month_bills,
        CondoProjectionService._projected_expenses, and (transitively, via materialized
        bills) CondoCalendarService — so generation, projection and calendar never diverge.
        IPTU installments live on STANDALONE plans (own Bill) and are NOT excluded here.
        """
        return self.filter(lifecycle_state=BillingAccountState.ACTIVE).exclude(
            account_type=BillingAccountType.IPTU
        )


# SoftDeleteManager.get_queryset already filters is_deleted=False; from_queryset keeps that and
# exposes recurring_for_generation()/with_deleted() on BillingAccount.objects (django-stubs friendly).
BillingAccountManager = SoftDeleteManager.from_queryset(BillingAccountQuerySet)


class BillingAccount(AuditMixin, SoftDeleteMixin, models.Model):
    """Recurring template (water/power/IPTU/internet). Generates a real Bill (S37)."""

    condominium = models.ForeignKey(
        Condominium, on_delete=models.PROTECT, related_name="billing_accounts"
    )
    building = models.ForeignKey(
        Building, null=True, blank=True, on_delete=models.PROTECT, related_name="billing_accounts"
    )  # null = condominium level
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="billing_accounts"
    )
    name = models.CharField(max_length=200)
    account_type = models.CharField(
        max_length=20, choices=BillingAccountType.choices, default=BillingAccountType.GENERIC
    )
    external_identifier = models.CharField(max_length=100, blank=True)  # inscrição/UC principal
    holder_name = models.CharField(max_length=200, blank=True)
    registered_address = models.CharField(max_length=255, blank=True)
    secondary_identifier = models.CharField(max_length=100, blank=True)  # imóvel/medidor/lançamento
    supply_status = models.CharField(
        max_length=10, choices=SupplyStatus.choices, default=SupplyStatus.ACTIVE
    )
    description = models.TextField(blank=True)
    default_due_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    lifecycle_state = models.CharField(
        max_length=20, choices=BillingAccountState.choices, default=BillingAccountState.ACTIVE
    )
    tracking_start_month = models.DateField(null=True, blank=True)  # seed; 1st day of month
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = BillingAccountManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(expected_amount__gte=0),
                name="billing_account_expected_amount_non_negative",
            ),
            models.UniqueConstraint(
                fields=["building", "account_type", "external_identifier"],
                condition=Q(is_deleted=False),
                name="unique_active_billing_account_identity",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.expected_amount is not None and self.expected_amount < 0:
            raise ValidationError({"expected_amount": "O valor esperado não pode ser negativo."})
        if self.tracking_start_month is not None:
            self.tracking_start_month = self.tracking_start_month.replace(day=1)
        # Typed accounts (water/power/IPTU) must carry their inscrição/UC: '' = '' collides on the
        # identity unique in Postgres, so this is the functional guard, not a structural one.
        if (
            self.account_type in _TYPED_IDENTITY_ACCOUNT_TYPES
            and not (self.external_identifier or "").strip()
        ):
            raise ValidationError({"external_identifier": _ERR_IDENTIFIER_REQUIRED})


class BillQuerySet(models.QuerySet["Bill"]):
    def with_amounts(self, today: date) -> "BillQuerySet":
        """Annotate amount_total / amount_paid / amount_remaining / payment_status / is_overdue.

        Each figure is a scalar correlated Subquery (no cartesian join between line
        items and allocations). Soft-deleted line items / allocations are excluded
        (their managers filter is_deleted=False). Quantization happens at the output
        boundary (service/serializer), not here (design §4).
        """
        line_items = BillLineItem.objects.filter(bill=OuterRef("pk")).values("bill")
        total_subquery = Subquery(
            line_items.annotate(
                total=Coalesce(Sum("amount", filter=Q(is_offset=False)), _ZERO_MONEY)
                - Coalesce(Sum("amount", filter=Q(is_offset=True)), _ZERO_MONEY)
            ).values("total"),
            output_field=_MONEY,
        )
        paid_subquery = Subquery(
            PaymentAllocation.objects.filter(bill=OuterRef("pk"))
            .values("bill")
            .annotate(paid=Coalesce(Sum("amount"), _ZERO_MONEY))
            .values("paid"),
            output_field=_MONEY,
        )
        return (
            self.annotate(
                amount_total=Coalesce(total_subquery, _ZERO_MONEY),
                amount_paid=Coalesce(paid_subquery, _ZERO_MONEY),
            )
            .annotate(amount_remaining=F("amount_total") - F("amount_paid"))
            .annotate(
                payment_status=Case(
                    When(amount_paid__lte=0, then=Value("open")),
                    When(amount_paid__gte=F("amount_total"), then=Value("paid")),
                    default=Value("partial"),
                    output_field=CharField(),
                ),
                is_overdue=Case(
                    When(
                        Q(due_date__lt=today)
                        & Q(amount_remaining__gt=0)
                        & Q(lifecycle_state=BillLifecycleState.ACTIVE),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
        )


# SoftDeleteManager.get_queryset already filters is_deleted=False; from_queryset keeps
# that and exposes with_amounts()/with_deleted() on Bill.objects (django-stubs friendly).
BillManager = SoftDeleteManager.from_queryset(BillQuerySet)


class Bill(AuditMixin, SoftDeleteMixin, models.Model):
    """A payable (real). amount_* via Bill.objects.with_amounts(today) — never a Python property.

    Source FKs: billing_account (S36, recurring), installment (S41, non-embedded plan),
    employee (S41, payroll). on_delete=SET_NULL so deleting a plan/employee never erases
    the real Bill history (past = real lines, design §3.2). behavior includes INSTALLMENT.
    """

    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="bills")
    building = models.ForeignKey(
        Building, null=True, blank=True, on_delete=models.PROTECT, related_name="bills"
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="bills"
    )
    competence_month = models.DateField()  # 1st day
    due_date = models.DateField()
    issue_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=500)
    external_identifier = models.CharField(max_length=100, blank=True)
    behavior = models.CharField(max_length=20, choices=BillBehavior.choices)
    billing_account = models.ForeignKey(
        BillingAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="bills"
    )
    installment = models.ForeignKey(
        "Installment", null=True, blank=True, on_delete=models.SET_NULL, related_name="bills"
    )
    employee = models.ForeignKey(
        "Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="bills"
    )
    lifecycle_state = models.CharField(
        max_length=20, choices=BillLifecycleState.choices, default=BillLifecycleState.ACTIVE
    )
    attachment = models.FileField(null=True, blank=True, upload_to="finances/bills/")
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = BillManager()

    class Meta:
        ordering = ["-competence_month", "due_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["billing_account", "competence_month"],
                condition=Q(is_deleted=False, billing_account__isnull=False),
                name="unique_active_bill_per_account_month",
            ),
            models.UniqueConstraint(
                fields=["installment"],
                condition=Q(is_deleted=False, installment__isnull=False),
                name="unique_active_bill_per_installment",
            ),
            models.UniqueConstraint(
                fields=["employee", "competence_month"],
                condition=Q(is_deleted=False, employee__isnull=False),
                name="unique_active_bill_per_employee_month",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} ({self.competence_month:%m/%Y})"

    def clean(self) -> None:
        super().clean()
        if self.competence_month is not None:
            self.competence_month = self.competence_month.replace(day=1)


class BillLineItem(AuditMixin, SoftDeleteMixin, models.Model):
    """A line of a Bill. is_offset: stored POSITIVE, subtracted (design §4.1).

    installment marks an embedded-installment line (the parcela on a recurring
    account's Bill); dedup on (bill, installment) keeps generation idempotent (S41).
    """

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="line_items")
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="line_items"
    )
    installment = models.ForeignKey(
        "Installment", null=True, blank=True, on_delete=models.SET_NULL, related_name="line_items"
    )
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # >= 0
    is_offset = models.BooleanField(default=False)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="bill_line_item_amount_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} - R${self.amount}"

    def clean(self) -> None:
        super().clean()
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "O valor da linha não pode ser negativo."})


class Payment(AuditMixin, SoftDeleteMixin, models.Model):
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    method = models.CharField(max_length=50, blank=True)
    funded_from = models.CharField(
        max_length=10, choices=FundedFrom.choices, default=FundedFrom.CAIXA
    )
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-payment_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Pagamento R${self.amount} ({self.payment_date:%d/%m/%Y})"

    def clean(self) -> None:
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "O valor do pagamento deve ser positivo."})


class PaymentAllocation(AuditMixin, SoftDeleteMixin, models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_allocation_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Alocação R${self.amount} -> conta {self.bill_id}"

    def clean(self) -> None:
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "O valor da alocação deve ser positivo."})


class BillSkip(AuditMixin, models.Model):
    """No SoftDelete (design §5.2): hard delete un-skips. Skips one month's generation."""

    billing_account = models.ForeignKey(
        BillingAccount, on_delete=models.CASCADE, related_name="skips"
    )
    reference_month = models.DateField()  # 1st day

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["billing_account", "reference_month"],
                name="unique_bill_skip_account_month",
            ),
        ]

    def __str__(self) -> str:
        return f"Skip {self.reference_month:%m/%Y} (conta {self.billing_account_id})"

    def clean(self) -> None:
        super().clean()
        if self.reference_month is not None:
            self.reference_month = self.reference_month.replace(day=1)


class InstallmentPlanState(models.TextChoices):
    ACTIVE = "active", "Ativo"
    PAID = "paid", "Quitado"
    DEFERRED = "deferred", "Adiado"
    CANCELED = "canceled", "Cancelado"


class EmployeePaymentType(models.TextChoices):
    FIXED = "fixed", "Fixo"
    VARIABLE = "variable", "Variável"
    MIXED = "mixed", "Misto"


class InstallmentPlan(AuditMixin, SoftDeleteMixin, models.Model):
    """Installment plan (embedded OR standalone). Materializes Installments (schedule)."""

    condominium = models.ForeignKey(
        Condominium, on_delete=models.PROTECT, related_name="installment_plans"
    )
    building = models.ForeignKey(
        Building, null=True, blank=True, on_delete=models.PROTECT, related_name="installment_plans"
    )  # null = condominium level
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="installment_plans"
    )
    description = models.CharField(max_length=500)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)  # >= 0
    installment_count = models.PositiveSmallIntegerField()  # > 0
    start_due_date = models.DateField()
    default_due_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    lifecycle_state = models.CharField(
        max_length=20,
        choices=InstallmentPlanState.choices,
        default=InstallmentPlanState.ACTIVE,
    )
    embedded = models.BooleanField(
        default=False
    )  # True = the parcela is a line on the account's Bill
    linked_billing_account = models.ForeignKey(
        BillingAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="installment_plans",
    )  # only for embedded plans
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["start_due_date", "description"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="installment_plan_total_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(installment_count__gt=0),
                name="installment_plan_count_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} ({self.installment_count}x)"

    def clean(self) -> None:
        super().clean()
        if self.total_amount is not None and self.total_amount < 0:
            raise ValidationError({"total_amount": "O valor total não pode ser negativo."})
        if self.installment_count is not None and self.installment_count <= 0:
            raise ValidationError({"installment_count": "O número de parcelas deve ser positivo."})
        # embedded ⇒ linked account required; standalone ⇒ no linked account (design §7).
        if self.embedded and self.linked_billing_account_id is None:
            raise ValidationError(
                {"linked_billing_account": "Plano embutido exige uma conta recorrente vinculada."}
            )
        if not self.embedded and self.linked_billing_account_id is not None:
            raise ValidationError(
                {"linked_billing_account": "Plano avulso não pode ter conta recorrente vinculada."}
            )


class Installment(AuditMixin, SoftDeleteMixin, models.Model):
    """A concrete installment (schedule). amount is the projection; copied to the
    BillLineItem.amount (realized) at materialization — schedule→realized only (S41)."""

    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name="installments")
    number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # >= 0; SCHEDULE

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["due_date", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "number"],
                condition=Q(is_deleted=False),
                name="unique_active_installment_per_plan_number",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="finance_installment_amount_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan.description} - Parcela {self.number}/{self.plan.installment_count}"

    def clean(self) -> None:
        super().clean()
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "O valor da parcela não pode ser negativo."})


class Employee(AuditMixin, SoftDeleteMixin, models.Model):
    """Payroll registry. The monthly payment is a Bill(employee=…) with lines (design §4.6)."""

    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="employees")
    person = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="finance_employees"
    )
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True)
    payment_type = models.CharField(max_length=10, choices=EmployeePaymentType.choices)
    base_salary = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # null/0 for variable-only
    default_due_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    lease = models.ForeignKey(
        Lease, null=True, blank=True, on_delete=models.SET_NULL, related_name="finance_employees"
    )  # salary-offset (Rosa, 850/205)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(base_salary__isnull=True) | Q(base_salary__gte=0),
                name="employee_base_salary_non_negative_or_null",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_payment_type_display()})"

    def clean(self) -> None:
        super().clean()
        if self.base_salary is not None and self.base_salary < 0:
            raise ValidationError({"base_salary": "O salário base não pode ser negativo."})
        needs_base = self.payment_type in (EmployeePaymentType.FIXED, EmployeePaymentType.MIXED)
        if needs_base and (self.base_salary is None or self.base_salary <= 0):
            raise ValidationError(
                {"base_salary": "Funcionário fixo/misto exige um salário base positivo."}
            )
        if (
            self.payment_type == EmployeePaymentType.VARIABLE
            and self.base_salary is not None
            and self.base_salary > 0
        ):
            raise ValidationError(
                {"base_salary": "Funcionário variável não pode ter salário base."}
            )


# =============================================================================
# PHASE 4 — Reserve / Income / Month close (Session 44)
# =============================================================================

_ERR_AMOUNT_POSITIVE = "O valor deve ser positivo."
_ERR_RECEIVED_DATE_REQUIRED = "Informe a data de recebimento quando a receita está recebida."
_ERR_RECEIVED_DATE_FORBIDDEN = "A data de recebimento só se aplica a receitas recebidas."
_ERR_CLOSED_NEEDS_DATE = "Um fechamento concluído exige a data de fechamento."
_ERR_CARRY_FORWARD_NON_POSITIVE = "O valor carregado para o próximo mês não pode ser positivo."


def _first_of_month(value: date) -> date:
    """Normalize a date to the first day of its month (single source — design §13)."""
    return value.replace(day=1)


class ReserveMovementKind(models.TextChoices):
    DEPOSIT = "deposit", "Depósito"
    WITHDRAWAL = "withdrawal", "Saque"


class CondoMonthCloseStatus(models.TextChoices):
    OPEN = "open", "Aberto"
    CLOSED = "closed", "Fechado"


class Reserve(AuditMixin, SoftDeleteMixin, models.Model):
    """Reserve (condominium savings). One per condominium in the UI; the model allows N
    (no selector now — YAGNI). Balance = Σ(ReserveMovement deposits − withdrawals) — DERIVED
    in the S45 service (never a @property/annotation here; design §4.3)."""

    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="reserves")
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"Reserva {self.name}"


class ReserveMovement(AuditMixin, SoftDeleteMixin, models.Model):
    """A movement on the reserve's single ledger. bill set = withdrawal to pay a bill;
    bill=null = cash <-> reserve transfer. amount is stored POSITIVE; the SIGN comes from
    `kind` (deposit adds, withdrawal subtracts).

    The "withdrawal <= reserve balance" guard is a SERVICE concern (S45 — CondoBalanceService
    + ReserveService.withdraw / BillPaymentService.pay), NOT this model: clean() must not query
    aggregates of other rows (design §4.3 + pinned decision). Here we only enforce sign/positivity.
    amount_paid of a Bill derives ONLY from PaymentAllocation (S36 with_amounts) — NEVER from
    ReserveMovement.bill (the bill link is just the withdrawal target, not a payment)."""

    reserve = models.ForeignKey(Reserve, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=10, choices=ReserveMovementKind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    movement_date = models.DateField()
    bill = models.ForeignKey(
        Bill, null=True, blank=True, on_delete=models.SET_NULL, related_name="reserve_movements"
    )
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        # Deterministic ledger (design §4.3): same movement_date ties broken by insertion id.
        ordering = ["movement_date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="reserve_movement_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} R${self.amount} ({self.movement_date:%d/%m/%Y})"

    def clean(self) -> None:
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": _ERR_AMOUNT_POSITIVE})


class IncomeEntry(AuditMixin, SoftDeleteMixin, models.Model):
    """One-off condominium income (loan proceeds, etc. — design §7). is_received=True (with
    received_date) is what counts in the cash balance (entradas_caixa, S45). Not recurring
    (YAGNI — design §15)."""

    condominium = models.ForeignKey(
        Condominium, on_delete=models.PROTECT, related_name="income_entries"
    )
    building = models.ForeignKey(
        Building, null=True, blank=True, on_delete=models.SET_NULL, related_name="income_entries"
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="income_entries"
    )
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    income_date = models.DateField()
    is_received = models.BooleanField(default=False)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-income_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="income_entry_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} - R${self.amount}"

    def clean(self) -> None:
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": _ERR_AMOUNT_POSITIVE})
        if self.is_received and self.received_date is None:
            raise ValidationError({"received_date": _ERR_RECEIVED_DATE_REQUIRED})
        if not self.is_received and self.received_date is not None:
            raise ValidationError({"received_date": _ERR_RECEIVED_DATE_FORBIDDEN})


class CondoMonthClose(AuditMixin, models.Model):
    """Lightweight, condominium-scoped anchor of the cash/fold + audit (design §3.2/§5.2).
    NO SoftDelete (only AuditMixin). Freezes net/cash/reserve/carry_forward_out of the CLOSED
    month and seeds the next month's cash/fold (S45). Does NOT lock rent (rent-lock = legacy
    MonthSnapshot). reference_month = 1st day of the month.

    net_result/cash_balance_end/reserve_balance_end may be negative (cash can go negative — an
    informational warning, not a block; design §4.2/§4.3) so they carry no CheckConstraint.
    carry_forward_out is structurally <= 0 (design §4.7: carregado_out = min(0, ...))."""

    condominium = models.ForeignKey(
        Condominium, on_delete=models.PROTECT, related_name="month_closes"
    )
    reference_month = models.DateField(
        help_text="Primeiro dia do mês de referência (ex: 2026-06-01)"
    )
    status = models.CharField(
        max_length=10, choices=CondoMonthCloseStatus.choices, default=CondoMonthCloseStatus.OPEN
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    net_result = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    cash_balance_end = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    reserve_balance_end = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    carry_forward_out = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal(0)
    )  # <= 0 (design §4.7)
    breakdown = models.JSONField(default=dict, blank=True)  # minimal display payload (S45/S46)

    objects = models.Manager()  # no SoftDeleteManager (there is no is_deleted)

    class Meta:
        ordering = ["-reference_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "reference_month"],
                name="unique_condo_month_close",
            ),
            models.CheckConstraint(
                condition=Q(carry_forward_out__lte=0),
                name="condo_month_close_carry_forward_non_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Fechamento {self.reference_month:%m/%Y} ({self.get_status_display()})"

    def clean(self) -> None:
        super().clean()
        if self.reference_month is not None:
            self.reference_month = _first_of_month(self.reference_month)
        if self.status == CondoMonthCloseStatus.CLOSED and self.closed_at is None:
            raise ValidationError({"closed_at": _ERR_CLOSED_NEEDS_DATE})
        if self.carry_forward_out is not None and self.carry_forward_out > 0:
            raise ValidationError({"carry_forward_out": _ERR_CARRY_FORWARD_NON_POSITIVE})
