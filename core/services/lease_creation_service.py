"""Lease creation business logic, extracted from the serializer.

Single source of truth for the rental-value derivation, the lease-creation defaults,
and mirroring the lease's ``last_rent_increase_date`` onto its apartment. The serializer
must not contain business logic (architecture rule: ``Serializers -> Models``), so
``LeaseViewSet.perform_create``/``perform_update`` delegate here.
"""

from decimal import Decimal
from typing import Any

from django.db import transaction

from core.models import DOUBLE_OCCUPANCY, Apartment, Lease, Tenant


class LeaseCreationService:
    """Stateless service for lease creation."""

    @staticmethod
    def resolve_rental_value(apartment: Apartment, number_of_tenants: int) -> Decimal:
        """Derive the rental value from the apartment for the given occupancy tier.

        Two occupants use the apartment's double rate when configured; otherwise the
        single-occupancy rate.
        """
        if number_of_tenants == DOUBLE_OCCUPANCY and apartment.rental_value_double is not None:
            return apartment.rental_value_double
        return apartment.rental_value

    @staticmethod
    def sync_apartment_last_rent_increase_date(lease: Lease) -> None:
        """Mirror the lease's ``last_rent_increase_date`` onto its apartment.

        No-op when the lease has no date or the apartment is already in sync. Unlike a
        rent adjustment (which only touches the apartment when its prices change), creating
        or editing a lease's rent-increase date always reflects onto the apartment.
        """
        if lease.last_rent_increase_date is None:
            return
        apartment = lease.apartment
        if apartment.last_rent_increase_date == lease.last_rent_increase_date:
            return
        apartment.last_rent_increase_date = lease.last_rent_increase_date
        # AuditMixin.save appends updated_at to update_fields automatically.
        apartment.save(update_fields=["last_rent_increase_date"])

    @staticmethod
    @transaction.atomic
    def create(*, validated_data: dict[str, Any], tenants: list[Tenant]) -> Lease:
        """Create a lease, applying the rental-value and rent-increase-date defaults.

        ``rental_value`` defaults to :meth:`resolve_rental_value`; ``last_rent_increase_date``
        defaults to ``start_date``; the apartment's date is then synced.
        """
        data = dict(validated_data)
        if "rental_value" not in data:
            apartment: Apartment = data["apartment"]
            number_of_tenants: int = data.get("number_of_tenants", 1)
            data["rental_value"] = LeaseCreationService.resolve_rental_value(
                apartment, number_of_tenants
            )
        if "last_rent_increase_date" not in data:
            data["last_rent_increase_date"] = data["start_date"]

        lease = Lease(**data)
        lease.full_clean()
        lease.save()
        if tenants:
            lease.tenants.set(tenants)
        LeaseCreationService.sync_apartment_last_rent_increase_date(lease)
        return lease
