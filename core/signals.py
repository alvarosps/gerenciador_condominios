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

from __future__ import annotations

import logging

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .cache import invalidate_related_caches
from .models import Apartment, Building, Dependent, Furniture, Lease, Tenant

logger = logging.getLogger(__name__)


# =============================================================================
# Building Signals
# =============================================================================


@receiver(post_save, sender=Building)
def invalidate_building_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate Building caches when a Building is created or updated.

    Also invalidates Apartment and Lease caches since they depend on Building.
    """
    action = "created" if created else "updated"
    logger.info(f"Building {instance.pk} {action}, invalidating caches")

    invalidate_related_caches(instance, related_models=["Apartment", "Lease"])


@receiver(post_delete, sender=Building)
def invalidate_building_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate Building caches when a Building is deleted.
    """
    logger.info(f"Building {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Apartment", "Lease"])


# =============================================================================
# Apartment Signals
# =============================================================================


@receiver(post_save, sender=Apartment)
def invalidate_apartment_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate Apartment caches when an Apartment is created or updated.

    Also invalidates Building and Lease caches.
    """
    action = "created" if created else "updated"
    logger.info(f"Apartment {instance.pk} {action}, invalidating caches")

    invalidate_related_caches(instance, related_models=["Building", "Lease"])


@receiver(post_delete, sender=Apartment)
def invalidate_apartment_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate Apartment caches when an Apartment is deleted.
    """
    logger.info(f"Apartment {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Building", "Lease"])


@receiver(m2m_changed, sender=Apartment.furnitures.through)
def invalidate_apartment_furniture_cache(sender, instance, action, **kwargs):
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
def invalidate_tenant_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate Tenant caches when a Tenant is created or updated.

    Also invalidates Lease and Dependent caches.
    """
    action = "created" if created else "updated"
    logger.info(f"Tenant {instance.pk} {action}, invalidating caches")

    invalidate_related_caches(instance, related_models=["Lease", "Dependent"])


@receiver(post_delete, sender=Tenant)
def invalidate_tenant_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate Tenant caches when a Tenant is deleted.
    """
    logger.info(f"Tenant {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Lease", "Dependent"])


@receiver(m2m_changed, sender=Tenant.furnitures.through)
def invalidate_tenant_furniture_cache(sender, instance, action, **kwargs):
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
def invalidate_lease_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate Lease caches when a Lease is created or updated.

    Also invalidates Apartment and Tenant caches since lease status affects them.
    """
    action = "created" if created else "updated"
    logger.info(f"Lease {instance.pk} {action}, invalidating caches")

    invalidate_related_caches(instance, related_models=["Apartment", "Tenant"])


@receiver(post_delete, sender=Lease)
def invalidate_lease_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate Lease caches when a Lease is deleted.
    """
    logger.info(f"Lease {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Apartment", "Tenant"])


@receiver(m2m_changed, sender=Lease.tenants.through)
def invalidate_lease_tenants_cache(sender, instance, action, **kwargs):
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
def invalidate_furniture_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate Furniture caches when Furniture is created or updated.

    Also invalidates Apartment, Tenant, and Lease caches since they reference furniture.
    """
    action = "created" if created else "updated"
    logger.info(f"Furniture {instance.pk} {action}, invalidating caches")

    invalidate_related_caches(instance, related_models=["Apartment", "Tenant", "Lease"])


@receiver(post_delete, sender=Furniture)
def invalidate_furniture_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate Furniture caches when Furniture is deleted.
    """
    logger.info(f"Furniture {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Apartment", "Tenant", "Lease"])


# =============================================================================
# Dependent Signals
# =============================================================================


@receiver(post_save, sender=Dependent)
def invalidate_dependent_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate Dependent caches when a Dependent is created or updated.

    Also invalidates Tenant caches since dependents are part of tenant data.
    """
    action = "created" if created else "updated"
    logger.info(f"Dependent {instance.pk} {action}, invalidating caches")

    invalidate_related_caches(instance, related_models=["Tenant"])


@receiver(post_delete, sender=Dependent)
def invalidate_dependent_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate Dependent caches when a Dependent is deleted.
    """
    logger.info(f"Dependent {instance.pk} deleted, invalidating caches")
    invalidate_related_caches(instance, related_models=["Tenant"])


# =============================================================================
# Utility Functions
# =============================================================================


def connect_all_signals():
    """
    Explicitly connect all signals.

    This function is called in apps.py ready() method to ensure all signals
    are connected when the application starts.

    Note: Django automatically connects signals with @receiver decorator,
    but this function provides explicit control and logging.
    """
    logger.info("All cache invalidation signals connected successfully")


def disconnect_all_signals():
    """
    Disconnect all cache invalidation signals.

    Useful for testing or temporary suspension of cache invalidation.

    Warning: Use with caution! Disabling signals can lead to stale caches.
    """
    from django.db.models.signals import m2m_changed, post_delete, post_save

    # Disconnect all post_save signals
    post_save.disconnect(sender=Building)
    post_save.disconnect(sender=Apartment)
    post_save.disconnect(sender=Tenant)
    post_save.disconnect(sender=Lease)
    post_save.disconnect(sender=Furniture)
    post_save.disconnect(sender=Dependent)

    # Disconnect all post_delete signals
    post_delete.disconnect(sender=Building)
    post_delete.disconnect(sender=Apartment)
    post_delete.disconnect(sender=Tenant)
    post_delete.disconnect(sender=Lease)
    post_delete.disconnect(sender=Furniture)
    post_delete.disconnect(sender=Dependent)

    # Disconnect m2m_changed signals
    m2m_changed.disconnect(sender=Apartment.furnitures.through)
    m2m_changed.disconnect(sender=Tenant.furnitures.through)
    m2m_changed.disconnect(sender=Lease.tenants.through)

    logger.warning("All cache invalidation signals disconnected")
