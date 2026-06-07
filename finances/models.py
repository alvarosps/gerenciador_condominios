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

from core.models import AuditMixin, Building, Condominium, SoftDeleteManager, SoftDeleteMixin

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
    external_identifier = models.CharField(max_length=100, blank=True)
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
    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(expected_amount__gte=0),
                name="billing_account_expected_amount_non_negative",
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

    Source FKs: only billing_account now. Bill.installment and Bill.employee are added
    in Session 41 (the Installment/Employee models do not exist yet); behavior already
    includes INSTALLMENT.
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
        ]

    def __str__(self) -> str:
        return f"{self.description} ({self.competence_month:%m/%Y})"

    def clean(self) -> None:
        super().clean()
        if self.competence_month is not None:
            self.competence_month = self.competence_month.replace(day=1)


class BillLineItem(AuditMixin, SoftDeleteMixin, models.Model):
    """A line of a Bill. is_offset: stored POSITIVE, subtracted (design §4.1).

    The installment FK (embedded installment) is added in Session 41.
    """

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="line_items")
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="line_items"
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
