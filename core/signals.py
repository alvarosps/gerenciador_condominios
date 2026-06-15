"""
Django signals for automatic cache invalidation.

Phase 4 Infrastructure: Automatic cache invalidation on model changes.

Signals are connected to post_save and post_delete for all models to ensure
cache consistency. When a model is created, updated, or deleted, related
caches are automatically invalidated.

Models and their cache invalidation relationships:
- Building: Invalidates Building, Apartment, Lease caches
- Apartment: Invalidates Apartment, Lease caches
- Tenant: Invalidates Tenant, Lease caches
- Lease: Invalidates Lease, Apartment, Tenant caches
- Furniture: Invalidates Furniture, Apartment, Tenant caches
- Dependent: Invalidates Dependent, Tenant caches
"""

import logging
from typing import Any

from django.db.models import Exists, OuterRef
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .cache import (
    FINANCE_MODULE_CACHE_PREFIXES,
    CacheManager,
    invalidate_legacy_financial_caches,
)
from .models import (
    Apartment,
    Building,
    CreditCard,
    Dependent,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    ExpenseMonthSkip,
    FinancialSettings,
    Furniture,
    Income,
    IPCAIndex,
    Landlord,
    Lease,
    MonthSnapshot,
    Person,
    PersonIncome,
    PersonPayment,
    PersonPaymentSchedule,
    RentAdjustment,
    RentPayment,
    Tenant,
)

logger = logging.getLogger(__name__)

# The condominium-finance module (app `finances`) owns these prefixes in
# finances/cache.py (FINANCE_*_PREFIX). core must NOT import finances (that would invert
# the finances -> core dependency), so the literals are duplicated here and the match is
# locked by tests/unit/test_finances/test_finance_cache_signals.py. Writes to
# Apartment / Lease / RentAdjustment / MonthSnapshot / RentPayment / FinancialSettings
# change condominium revenue, projection or close state, so they invalidate finance-*.
_FINANCE_CACHE_PREFIXES = FINANCE_MODULE_CACHE_PREFIXES


def _invalidate_finance_module_caches() -> None:
    """Invalidate the condominium-finance dashboard / cash-flow / projection caches."""
    for prefix in _FINANCE_CACHE_PREFIXES:
        CacheManager.invalidate_pattern(f"{prefix}*")


# Real @cache_result key prefixes that a core-model write must invalidate. The old
# CacheManager.invalidate_model("Model") produced "*Model*" globs that never matched these
# hyphenated prefixes, so core invalidation only worked by TTL expiry (120-300s). The keys are
# hyphenated, so the glob is "<prefix>*" ("<prefix>:*" never matches — same trap as the
# financial caches). finance-* stays handled by _invalidate_finance_module_caches() at the
# Apartment/Lease receivers, so it is intentionally not duplicated here.
_PROPERTY_CACHE_PREFIXES = (
    "dashboard-financial-summary",
    "dashboard-lease-metrics",
    "dashboard-building-stats",
    "dashboard-tenant-stats",
    "dashboard-late-payment",
    "dashboard-rent-adjustment-alerts",
    "cash-flow-projection",
    # The legacy financial-dashboard overview/summary derive rent income from Lease via
    # CashFlowService, so a property/rent write (Building/Apartment/Lease) must drop it too.
    "financial-dashboard",
)
# The rent-adjustment alert payload depends on Lease, RentAdjustment, the Landlord fallback
# percentage, and the latest IPCAIndex, so each of those writes must drop
# "dashboard-rent-adjustment-alerts".
_RENT_ADJUSTMENT_ALERTS_PREFIXES = ("dashboard-rent-adjustment-alerts",)
_CORE_MODEL_CACHE_PREFIXES: dict[str, tuple[str, ...]] = {
    "Building": _PROPERTY_CACHE_PREFIXES,
    "Apartment": _PROPERTY_CACHE_PREFIXES,
    "Lease": _PROPERTY_CACHE_PREFIXES,
    "Tenant": (
        "dashboard-financial-summary",
        "dashboard-lease-metrics",
        "dashboard-tenant-stats",
        "dashboard-late-payment",
        # The rent-adjustment alert card embeds lease.responsible_tenant.name, so a tenant
        # rename must drop it.
        "dashboard-rent-adjustment-alerts",
    ),
    "Furniture": ("dashboard-financial-summary", "dashboard-lease-metrics"),
    "Dependent": ("dashboard-tenant-stats",),
    "RentAdjustment": _RENT_ADJUSTMENT_ALERTS_PREFIXES,
    "Landlord": _RENT_ADJUSTMENT_ALERTS_PREFIXES,
    "IPCAIndex": _RENT_ADJUSTMENT_ALERTS_PREFIXES,
}


def _invalidate_core_model_caches(model_name: str) -> None:
    """Invalidate the real cache prefixes a core-model write affects (no-op if none)."""
    for prefix in _CORE_MODEL_CACHE_PREFIXES.get(model_name, ()):
        CacheManager.invalidate_pattern(f"{prefix}*")


# =============================================================================
# Building Signals
# =============================================================================


@receiver(post_save, sender=Building)
def invalidate_building_cache_on_save(
    sender: type[Building], instance: Building, created: bool, **kwargs: Any
) -> None:
    """
    Invalidate Building caches when a Building is created or updated.

    Also invalidates Apartment and Lease caches since they depend on Building.
    """
    action = "created" if created else "updated"
    logger.info(f"Building {instance.pk} {action}, invalidating caches")

    _invalidate_core_model_caches("Building")


@receiver(post_delete, sender=Building)
def invalidate_building_cache_on_delete(
    sender: type[Building], instance: Building, **kwargs: Any
) -> None:
    """
    Invalidate Building caches when a Building is deleted.
    """
    logger.info(f"Building {instance.pk} deleted, invalidating caches")
    _invalidate_core_model_caches("Building")


# =============================================================================
# Apartment Signals
# =============================================================================


@receiver(post_save, sender=Apartment)
def invalidate_apartment_cache_on_save(
    sender: type[Apartment], instance: Apartment, created: bool, **kwargs: Any
) -> None:
    """
    Invalidate Apartment caches when an Apartment is created or updated.

    Also invalidates Building and Lease caches.
    """
    action = "created" if created else "updated"
    logger.info(f"Apartment {instance.pk} {action}, invalidating caches")

    _invalidate_core_model_caches("Apartment")
    # owner / rental value changes condominium revenue + projection (design §11, NET-NEW)
    _invalidate_finance_module_caches()


@receiver(post_delete, sender=Apartment)
def invalidate_apartment_cache_on_delete(
    sender: type[Apartment], instance: Apartment, **kwargs: Any
) -> None:
    """
    Invalidate Apartment caches when an Apartment is deleted.
    """
    logger.info(f"Apartment {instance.pk} deleted, invalidating caches")
    _invalidate_core_model_caches("Apartment")
    _invalidate_finance_module_caches()


@receiver(m2m_changed, sender=Apartment.furnitures.through)
def invalidate_apartment_furniture_cache(
    sender: Any, instance: Apartment, action: str, **kwargs: Any
) -> None:
    """
    Invalidate caches when Apartment-Furniture relationship changes.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(f"Apartment {instance.pk} furniture changed, invalidating caches")
        _invalidate_core_model_caches("Apartment")


# =============================================================================
# Tenant Signals
# =============================================================================


@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache_on_save(
    sender: type[Tenant], instance: Tenant, created: bool, **kwargs: Any
) -> None:
    """
    Invalidate Tenant caches when a Tenant is created or updated.

    Also invalidates Lease and Dependent caches.
    """
    action = "created" if created else "updated"
    logger.info(f"Tenant {instance.pk} {action}, invalidating caches")

    _invalidate_core_model_caches("Tenant")


@receiver(post_delete, sender=Tenant)
def invalidate_tenant_cache_on_delete(
    sender: type[Tenant], instance: Tenant, **kwargs: Any
) -> None:
    """
    Invalidate Tenant caches when a Tenant is deleted.
    """
    logger.info(f"Tenant {instance.pk} deleted, invalidating caches")
    _invalidate_core_model_caches("Tenant")


@receiver(m2m_changed, sender=Tenant.furnitures.through)
def invalidate_tenant_furniture_cache(
    sender: Any, instance: Tenant, action: str, **kwargs: Any
) -> None:
    """
    Invalidate caches when Tenant-Furniture relationship changes.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(f"Tenant {instance.pk} furniture changed, invalidating caches")
        _invalidate_core_model_caches("Tenant")


# =============================================================================
# Lease Signals
# =============================================================================


@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """Sync apartment.is_rented based on whether any active lease exists."""
    Apartment.objects.filter(pk=instance.apartment_id).update(
        is_rented=Exists(Lease.objects.filter(apartment_id=OuterRef("pk")))
    )


@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """Sync apartment.is_rented when lease is hard-deleted."""
    Apartment.objects.filter(pk=instance.apartment_id).update(
        is_rented=Exists(Lease.objects.filter(apartment_id=OuterRef("pk")))
    )


@receiver(post_save, sender=Lease)
def invalidate_lease_cache_on_save(
    sender: type[Lease], instance: Lease, created: bool, **kwargs: Any
) -> None:
    """
    Invalidate Lease caches when a Lease is created or updated.

    Also invalidates Apartment and Tenant caches since lease status affects them.
    """
    action = "created" if created else "updated"
    logger.info(f"Lease {instance.pk} {action}, invalidating caches")

    _invalidate_core_model_caches("Lease")
    # collectibility / salary-offset / prepaid changes condominium revenue (design §11)
    _invalidate_finance_module_caches()


@receiver(post_delete, sender=Lease)
def invalidate_lease_cache_on_delete(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """
    Invalidate Lease caches when a Lease is deleted.
    """
    logger.info(f"Lease {instance.pk} deleted, invalidating caches")
    _invalidate_core_model_caches("Lease")
    _invalidate_finance_module_caches()


@receiver(m2m_changed, sender=Lease.tenants.through)
def invalidate_lease_tenants_cache(
    sender: Any, instance: Lease, action: str, **kwargs: Any
) -> None:
    """
    Invalidate caches when Lease-Tenant relationship changes.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(f"Lease {instance.pk} tenants changed, invalidating caches")
        _invalidate_core_model_caches("Lease")


# =============================================================================
# Furniture Signals
# =============================================================================


@receiver(post_save, sender=Furniture)
def invalidate_furniture_cache_on_save(
    sender: type[Furniture], instance: Furniture, created: bool, **kwargs: Any
) -> None:
    """
    Invalidate Furniture caches when Furniture is created or updated.

    Also invalidates Apartment, Tenant, and Lease caches since they reference furniture.
    """
    action = "created" if created else "updated"
    logger.info(f"Furniture {instance.pk} {action}, invalidating caches")

    _invalidate_core_model_caches("Furniture")


@receiver(post_delete, sender=Furniture)
def invalidate_furniture_cache_on_delete(
    sender: type[Furniture], instance: Furniture, **kwargs: Any
) -> None:
    """
    Invalidate Furniture caches when Furniture is deleted.
    """
    logger.info(f"Furniture {instance.pk} deleted, invalidating caches")
    _invalidate_core_model_caches("Furniture")


# =============================================================================
# Dependent Signals
# =============================================================================


@receiver(post_save, sender=Dependent)
def invalidate_dependent_cache_on_save(
    sender: type[Dependent], instance: Dependent, created: bool, **kwargs: Any
) -> None:
    """
    Invalidate Dependent caches when a Dependent is created or updated.

    Also invalidates Tenant caches since dependents are part of tenant data.
    """
    action = "created" if created else "updated"
    logger.info(f"Dependent {instance.pk} {action}, invalidating caches")

    _invalidate_core_model_caches("Dependent")


@receiver(post_delete, sender=Dependent)
def invalidate_dependent_cache_on_delete(
    sender: type[Dependent], instance: Dependent, **kwargs: Any
) -> None:
    """
    Invalidate Dependent caches when a Dependent is deleted.
    """
    logger.info(f"Dependent {instance.pk} deleted, invalidating caches")
    _invalidate_core_model_caches("Dependent")


# =============================================================================
# Financial Model Signals
# =============================================================================


def _invalidate_financial_caches(model_name: str, pk: int) -> None:
    """Invalidate all financial dashboard caches affected by financial model changes."""
    logger.info(f"{model_name} {pk} changed, invalidating financial caches")
    # cash-flow* / financial-dashboard* + the condominium-finance caches (RentPayment /
    # FinancialSettings route through here, so finance-* is invalidated for them too).
    invalidate_legacy_financial_caches()


@receiver(post_save, sender=Person)
def invalidate_person_cache_on_save(
    sender: type[Person], instance: Person, created: bool, **kwargs: Any
) -> None:
    # Person.name is surfaced in the condominium-finance by_owner card (external owners) and in the
    # legacy financial dashboards, so a rename must invalidate both, not just leave a stale name.
    action = "created" if created else "updated"
    logger.info(f"Person {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("Person", instance.pk)


@receiver(post_delete, sender=Person)
def invalidate_person_cache_on_delete(
    sender: type[Person], instance: Person, **kwargs: Any
) -> None:
    _invalidate_financial_caches("Person", instance.pk)


@receiver(post_save, sender=PersonPayment)
def invalidate_person_payment_cache_on_save(
    sender: type[PersonPayment], instance: PersonPayment, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"PersonPayment {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("PersonPayment", instance.pk)


@receiver(post_delete, sender=PersonPayment)
def invalidate_person_payment_cache_on_delete(
    sender: type[PersonPayment], instance: PersonPayment, **kwargs: Any
) -> None:
    _invalidate_financial_caches("PersonPayment", instance.pk)


@receiver(post_save, sender=PersonPaymentSchedule)
def invalidate_person_payment_schedule_cache_on_save(
    sender: type[PersonPaymentSchedule],
    instance: PersonPaymentSchedule,
    created: bool,
    **kwargs: Any,
) -> None:
    action = "created" if created else "updated"
    logger.info(f"PersonPaymentSchedule {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("PersonPaymentSchedule", instance.pk)


@receiver(post_delete, sender=PersonPaymentSchedule)
def invalidate_person_payment_schedule_cache_on_delete(
    sender: type[PersonPaymentSchedule], instance: PersonPaymentSchedule, **kwargs: Any
) -> None:
    _invalidate_financial_caches("PersonPaymentSchedule", instance.pk)


@receiver(post_save, sender=ExpenseMonthSkip)
def invalidate_expense_month_skip_cache_on_save(
    sender: type[ExpenseMonthSkip],
    instance: ExpenseMonthSkip,
    created: bool,
    **kwargs: Any,
) -> None:
    action = "created" if created else "updated"
    logger.info(f"ExpenseMonthSkip {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("ExpenseMonthSkip", instance.pk)


@receiver(post_delete, sender=ExpenseMonthSkip)
def invalidate_expense_month_skip_cache_on_delete(
    sender: type[ExpenseMonthSkip], instance: ExpenseMonthSkip, **kwargs: Any
) -> None:
    _invalidate_financial_caches("ExpenseMonthSkip", instance.pk)


def _invalidate_rent_payment_caches(pk: int) -> None:
    """A RentPayment create / soft-delete (rent toggle) changes received rent, overdue
    status and the late-payment summary — invalidate the financial AND dashboard caches.

    Soft-delete goes through SoftDeleteMixin.delete() -> save(), so post_save covers both
    create and unmark; post_delete covers the rare hard delete.
    """
    _invalidate_financial_caches("RentPayment", pk)
    # Only the late-payment summary depends on RentPayment; get_financial_summary derives
    # revenue from leases (not payments), so it is intentionally NOT invalidated here.
    CacheManager.invalidate_pattern("dashboard-late-payment*")


@receiver(post_save, sender=RentPayment)
def invalidate_rent_payment_cache_on_save(
    sender: type[RentPayment], instance: RentPayment, **kwargs: Any
) -> None:
    _invalidate_rent_payment_caches(instance.pk)


@receiver(post_delete, sender=RentPayment)
def invalidate_rent_payment_cache_on_delete(
    sender: type[RentPayment], instance: RentPayment, **kwargs: Any
) -> None:
    _invalidate_rent_payment_caches(instance.pk)


@receiver(post_save, sender=FinancialSettings)
def invalidate_financial_settings_cache_on_save(
    sender: type[FinancialSettings], instance: FinancialSettings, **kwargs: Any
) -> None:
    """FinancialSettings drives the rent-tracking boundary and other financial config,
    which changes collectibility, overdue and cash-flow results — invalidate the
    financial AND late-payment dashboard caches."""
    _invalidate_financial_caches("FinancialSettings", instance.pk)
    CacheManager.invalidate_pattern("dashboard-late-payment*")


@receiver(post_save, sender=RentAdjustment)
def invalidate_rent_adjustment_finance_cache_on_save(
    sender: type[RentAdjustment], instance: RentAdjustment, **kwargs: Any
) -> None:
    """A rent adjustment changes effective_rental_value, hence the condominium
    projection — invalidate finance-* (design §11) and the rent-adjustment alerts."""
    _invalidate_finance_module_caches()
    _invalidate_core_model_caches("RentAdjustment")


@receiver(post_delete, sender=RentAdjustment)
def invalidate_rent_adjustment_finance_cache_on_delete(
    sender: type[RentAdjustment], instance: RentAdjustment, **kwargs: Any
) -> None:
    _invalidate_finance_module_caches()
    _invalidate_core_model_caches("RentAdjustment")


@receiver(post_save, sender=Landlord)
def invalidate_landlord_cache_on_save(
    sender: type[Landlord], instance: Landlord, **kwargs: Any
) -> None:
    """The active Landlord's rent_adjustment_percentage feeds the alert fallback, so a
    Landlord write must drop the rent-adjustment alerts cache."""
    _invalidate_core_model_caches("Landlord")


@receiver(post_delete, sender=Landlord)
def invalidate_landlord_cache_on_delete(
    sender: type[Landlord], instance: Landlord, **kwargs: Any
) -> None:
    _invalidate_core_model_caches("Landlord")


@receiver(post_save, sender=IPCAIndex)
def invalidate_ipca_index_cache_on_save(
    sender: type[IPCAIndex], instance: IPCAIndex, **kwargs: Any
) -> None:
    """The rent-adjustment alert payload derives ipca_12m / suggested values from the latest
    IPCAIndex, so the daily cron persisting a new index month must drop the alerts cache (it is
    otherwise stale until the 300s TTL or an unrelated Lease/RentAdjustment/Landlord write)."""
    _invalidate_core_model_caches("IPCAIndex")


@receiver(post_delete, sender=IPCAIndex)
def invalidate_ipca_index_cache_on_delete(
    sender: type[IPCAIndex], instance: IPCAIndex, **kwargs: Any
) -> None:
    _invalidate_core_model_caches("IPCAIndex")


@receiver(post_save, sender=MonthSnapshot)
def invalidate_month_snapshot_finance_cache_on_save(
    sender: type[MonthSnapshot], instance: MonthSnapshot, **kwargs: Any
) -> None:
    """Finalizing / rolling back a month snapshot changes settled state used by the
    condominium balance/projection — invalidate finance-* (design §11)."""
    _invalidate_finance_module_caches()


@receiver(post_delete, sender=MonthSnapshot)
def invalidate_month_snapshot_finance_cache_on_delete(
    sender: type[MonthSnapshot], instance: MonthSnapshot, **kwargs: Any
) -> None:
    _invalidate_finance_module_caches()


@receiver(post_save, sender=Expense)
def invalidate_expense_cache_on_save(
    sender: type[Expense], instance: Expense, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"Expense {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("Expense", instance.pk)


@receiver(post_delete, sender=Expense)
def invalidate_expense_cache_on_delete(
    sender: type[Expense], instance: Expense, **kwargs: Any
) -> None:
    _invalidate_financial_caches("Expense", instance.pk)


@receiver(post_save, sender=ExpenseInstallment)
def invalidate_expense_installment_cache_on_save(
    sender: type[ExpenseInstallment],
    instance: ExpenseInstallment,
    created: bool,
    **kwargs: Any,
) -> None:
    action = "created" if created else "updated"
    logger.info(f"ExpenseInstallment {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("ExpenseInstallment", instance.pk)


@receiver(post_delete, sender=ExpenseInstallment)
def invalidate_expense_installment_cache_on_delete(
    sender: type[ExpenseInstallment], instance: ExpenseInstallment, **kwargs: Any
) -> None:
    _invalidate_financial_caches("ExpenseInstallment", instance.pk)


@receiver(post_save, sender=Income)
def invalidate_income_cache_on_save(
    sender: type[Income], instance: Income, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"Income {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("Income", instance.pk)


@receiver(post_delete, sender=Income)
def invalidate_income_cache_on_delete(
    sender: type[Income], instance: Income, **kwargs: Any
) -> None:
    _invalidate_financial_caches("Income", instance.pk)


@receiver(post_save, sender=EmployeePayment)
def invalidate_employee_payment_cache_on_save(
    sender: type[EmployeePayment], instance: EmployeePayment, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"EmployeePayment {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("EmployeePayment", instance.pk)


@receiver(post_delete, sender=EmployeePayment)
def invalidate_employee_payment_cache_on_delete(
    sender: type[EmployeePayment], instance: EmployeePayment, **kwargs: Any
) -> None:
    _invalidate_financial_caches("EmployeePayment", instance.pk)


@receiver(post_save, sender=PersonIncome)
def invalidate_person_income_cache_on_save(
    sender: type[PersonIncome], instance: PersonIncome, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"PersonIncome {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("PersonIncome", instance.pk)


@receiver(post_delete, sender=PersonIncome)
def invalidate_person_income_cache_on_delete(
    sender: type[PersonIncome], instance: PersonIncome, **kwargs: Any
) -> None:
    _invalidate_financial_caches("PersonIncome", instance.pk)


@receiver(post_save, sender=CreditCard)
def invalidate_credit_card_cache_on_save(
    sender: type[CreditCard], instance: CreditCard, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"CreditCard {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("CreditCard", instance.pk)


@receiver(post_delete, sender=CreditCard)
def invalidate_credit_card_cache_on_delete(
    sender: type[CreditCard], instance: CreditCard, **kwargs: Any
) -> None:
    _invalidate_financial_caches("CreditCard", instance.pk)


@receiver(post_save, sender=ExpenseCategory)
def invalidate_expense_category_cache_on_save(
    sender: type[ExpenseCategory], instance: ExpenseCategory, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"ExpenseCategory {instance.pk} {action}, invalidating financial caches")
    _invalidate_financial_caches("ExpenseCategory", instance.pk)


@receiver(post_delete, sender=ExpenseCategory)
def invalidate_expense_category_cache_on_delete(
    sender: type[ExpenseCategory], instance: ExpenseCategory, **kwargs: Any
) -> None:
    _invalidate_financial_caches("ExpenseCategory", instance.pk)


# =============================================================================
# Utility Functions
# =============================================================================


# The receivers disconnect_all_signals()/connect_all_signals() toggle as a round-trip pair. The
# @receiver decorators wire every signal once at import; only receivers disconnected with an
# EXPLICIT receiver (these two) are actually removed by disconnect_all_signals — Django keys on
# (receiver, sender), so the other sender-only disconnect() calls are silent no-ops. So these are
# the only ones connect_all_signals must restore.
_TOGGLEABLE_RECEIVERS: tuple[tuple[Any, Any, type], ...] = (
    (post_save, sync_apartment_is_rented, Lease),
    (post_delete, sync_apartment_is_rented_on_delete, Lease),
)


def connect_all_signals() -> None:
    """(Re)connect the toggleable signals — idempotent, so disconnect_all_signals() + this is a
    true round-trip.

    The @receiver decorators connect every signal at import; this restores the receivers that
    disconnect_all_signals() removes (the Lease -> Apartment.is_rented sync). It is idempotent
    (disconnect-then-connect guarantees exactly one connection), so it is safe whether or not a
    disconnect happened — without a working reconnect, disconnect_all_signals() would leave the
    is_rented sync permanently off (a real bug, and a source of cross-test pollution).
    """
    for signal, handler, sender in _TOGGLEABLE_RECEIVERS:
        signal.disconnect(handler, sender=sender)
        signal.connect(handler, sender=sender)
    logger.info("All cache invalidation signals connected successfully")


def disconnect_all_signals() -> None:
    """Disconnect the toggleable signals (the Lease -> Apartment.is_rented sync).

    Useful for testing or temporary suspension. Only the receivers in
    _TOGGLEABLE_RECEIVERS are disconnectable here — Django keys on (receiver, sender),
    so the historical sender-only disconnect() calls were silent no-ops. connect_all_signals
    restores exactly these. Use with caution: disabling can lead to stale caches.
    """
    for signal, handler, sender in _TOGGLEABLE_RECEIVERS:
        signal.disconnect(handler, sender=sender)
    logger.warning("is_rented sync signals disconnected")
