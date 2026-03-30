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

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .cache import CacheManager, invalidate_related_caches
from .models import (
    Apartment,
    Building,
    Dependent,
    DeviceToken,
    ExpenseMonthSkip,
    Furniture,
    Lease,
    Notification,
    PaymentProof,
    PersonPayment,
    PersonPaymentSchedule,
    Tenant,
)

logger = logging.getLogger(__name__)


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

    invalidate_related_caches(instance, related_models=["Apartment", "Lease"])


@receiver(post_delete, sender=Building)
def invalidate_building_cache_on_delete(
    sender: type[Building], instance: Building, **kwargs: Any
) -> None:
    """
    Invalidate Building caches when a Building is deleted.
    """
    logger.info(f"Building {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Apartment", "Lease"])


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

    invalidate_related_caches(instance, related_models=["Building", "Lease"])


@receiver(post_delete, sender=Apartment)
def invalidate_apartment_cache_on_delete(
    sender: type[Apartment], instance: Apartment, **kwargs: Any
) -> None:
    """
    Invalidate Apartment caches when an Apartment is deleted.
    """
    logger.info(f"Apartment {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Building", "Lease"])


@receiver(m2m_changed, sender=Apartment.furnitures.through)
def invalidate_apartment_furniture_cache(
    sender: Any, instance: Apartment, action: str, **kwargs: Any
) -> None:
    """
    Invalidate caches when Apartment-Furniture relationship changes.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(f"Apartment {instance.pk} furniture changed, invalidating caches")
        invalidate_related_caches(instance, related_models=["Furniture", "Lease"])


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

    invalidate_related_caches(instance, related_models=["Lease", "Dependent"])


@receiver(post_delete, sender=Tenant)
def invalidate_tenant_cache_on_delete(
    sender: type[Tenant], instance: Tenant, **kwargs: Any
) -> None:
    """
    Invalidate Tenant caches when a Tenant is deleted.
    """
    logger.info(f"Tenant {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Lease", "Dependent"])


@receiver(m2m_changed, sender=Tenant.furnitures.through)
def invalidate_tenant_furniture_cache(
    sender: Any, instance: Tenant, action: str, **kwargs: Any
) -> None:
    """
    Invalidate caches when Tenant-Furniture relationship changes.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(f"Tenant {instance.pk} furniture changed, invalidating caches")
        invalidate_related_caches(instance, related_models=["Furniture", "Lease"])


# =============================================================================
# Lease Signals
# =============================================================================


@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """Sync apartment.is_rented based on whether any active lease exists."""
    has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)


@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """Sync apartment.is_rented when lease is hard-deleted."""
    has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)


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

    invalidate_related_caches(instance, related_models=["Apartment", "Tenant"])


@receiver(post_delete, sender=Lease)
def invalidate_lease_cache_on_delete(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """
    Invalidate Lease caches when a Lease is deleted.
    """
    logger.info(f"Lease {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Apartment", "Tenant"])


@receiver(m2m_changed, sender=Lease.tenants.through)
def invalidate_lease_tenants_cache(
    sender: Any, instance: Lease, action: str, **kwargs: Any
) -> None:
    """
    Invalidate caches when Lease-Tenant relationship changes.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(f"Lease {instance.pk} tenants changed, invalidating caches")
        invalidate_related_caches(instance, related_models=["Tenant"])


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

    invalidate_related_caches(instance, related_models=["Apartment", "Tenant", "Lease"])


@receiver(post_delete, sender=Furniture)
def invalidate_furniture_cache_on_delete(
    sender: type[Furniture], instance: Furniture, **kwargs: Any
) -> None:
    """
    Invalidate Furniture caches when Furniture is deleted.
    """
    logger.info(f"Furniture {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Apartment", "Tenant", "Lease"])


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

    invalidate_related_caches(instance, related_models=["Tenant"])


@receiver(post_delete, sender=Dependent)
def invalidate_dependent_cache_on_delete(
    sender: type[Dependent], instance: Dependent, **kwargs: Any
) -> None:
    """
    Invalidate Dependent caches when a Dependent is deleted.
    """
    logger.info(f"Dependent {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Tenant"])


# =============================================================================
# Financial Model Signals
# =============================================================================


def _invalidate_financial_caches(model_name: str, pk: int) -> None:
    """Invalidate all financial dashboard caches affected by financial model changes."""
    logger.info(f"{model_name} {pk} changed, invalidating financial caches")
    CacheManager.invalidate_pattern("daily-control:*")
    CacheManager.invalidate_pattern("cash-flow:*")
    CacheManager.invalidate_pattern("financial-dashboard:*")


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


# =============================================================================
# Mobile Model Signals
# =============================================================================


@receiver(post_save, sender=PaymentProof)
def invalidate_payment_proof_cache_on_save(
    sender: type[PaymentProof], instance: PaymentProof, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"PaymentProof {instance.pk} {action}, invalidating caches")
    invalidate_related_caches(instance, related_models=["Lease"])


@receiver(post_delete, sender=PaymentProof)
def invalidate_payment_proof_cache_on_delete(
    sender: type[PaymentProof], instance: PaymentProof, **kwargs: Any
) -> None:
    logger.info(f"PaymentProof {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Lease"])


@receiver(post_save, sender=Notification)
def invalidate_notification_cache_on_save(
    sender: type[Notification], instance: Notification, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"Notification {instance.pk} {action}, invalidating caches")
    CacheManager.invalidate_model("Notification", instance.pk)


@receiver(post_delete, sender=Notification)
def invalidate_notification_cache_on_delete(
    sender: type[Notification], instance: Notification, **kwargs: Any
) -> None:
    logger.info(f"Notification {instance.pk} deleted, invalidating caches")
    CacheManager.invalidate_model("Notification", instance.pk)


@receiver(post_save, sender=DeviceToken)
def invalidate_device_token_cache_on_save(
    sender: type[DeviceToken], instance: DeviceToken, created: bool, **kwargs: Any
) -> None:
    action = "created" if created else "updated"
    logger.info(f"DeviceToken {instance.pk} {action}, invalidating caches")
    CacheManager.invalidate_model("DeviceToken", instance.pk)


@receiver(post_delete, sender=DeviceToken)
def invalidate_device_token_cache_on_delete(
    sender: type[DeviceToken], instance: DeviceToken, **kwargs: Any
) -> None:
    logger.info(f"DeviceToken {instance.pk} deleted, invalidating caches")
    CacheManager.invalidate_model("DeviceToken", instance.pk)


# =============================================================================
# Utility Functions
# =============================================================================


def connect_all_signals() -> None:
    """
    Explicitly connect all signals.

    This function is called in apps.py ready() method to ensure all signals
    are connected when the application starts.

    Note: Django automatically connects signals with @receiver decorator,
    but this function provides explicit control and logging.
    """
    logger.info("All cache invalidation signals connected successfully")


def disconnect_all_signals() -> None:
    """
    Disconnect all cache invalidation signals.

    Useful for testing or temporary suspension of cache invalidation.

    Warning: Use with caution! Disabling signals can lead to stale caches.
    """
    # Disconnect all post_save signals
    post_save.disconnect(sender=Building)
    post_save.disconnect(sender=Apartment)
    post_save.disconnect(sender=Tenant)
    post_save.disconnect(sync_apartment_is_rented, sender=Lease)
    post_save.disconnect(sender=Lease)
    post_save.disconnect(sender=Furniture)
    post_save.disconnect(sender=Dependent)
    post_save.disconnect(sender=PaymentProof)
    post_save.disconnect(sender=Notification)
    post_save.disconnect(sender=DeviceToken)

    # Disconnect all post_delete signals
    post_delete.disconnect(sender=Building)
    post_delete.disconnect(sender=Apartment)
    post_delete.disconnect(sender=Tenant)
    post_delete.disconnect(sync_apartment_is_rented_on_delete, sender=Lease)
    post_delete.disconnect(sender=Lease)
    post_delete.disconnect(sender=Furniture)
    post_delete.disconnect(sender=Dependent)
    post_delete.disconnect(sender=PaymentProof)
    post_delete.disconnect(sender=Notification)
    post_delete.disconnect(sender=DeviceToken)

    # Disconnect m2m_changed signals
    m2m_changed.disconnect(sender=Apartment.furnitures.through)
    m2m_changed.disconnect(sender=Tenant.furnitures.through)
    m2m_changed.disconnect(sender=Lease.tenants.through)

    logger.warning("All cache invalidation signals disconnected")
