"""Lease lifecycle services: terminate and transfer."""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction

from core.models import Lease


@transaction.atomic
def terminate_lease(lease_id: int, user: Any) -> None:
    """Terminate a lease: reset contract fields, soft delete.

    The signal sync_apartment_is_rented handles setting apartment.is_rented = False.
    """
    lease = Lease.objects.get(pk=lease_id)
    Lease.objects.filter(pk=lease_id).update(
        contract_generated=False,
        contract_signed=False,
        interfone_configured=False,
    )
    lease.refresh_from_db()
    lease.delete(deleted_by=user)


@transaction.atomic
def transfer_lease(lease_id: int, payload: dict[str, Any], user: Any) -> Lease:
    """Transfer a lease to a new apartment.

    Soft-deletes the old lease and creates a new one on the target apartment.
    Signals handle apartment.is_rented sync automatically.
    """
    old_lease = Lease.objects.get(pk=lease_id)

    new_apartment_id: int = payload["apartment_id"]
    responsible_tenant_id: int = payload["responsible_tenant_id"]
    tenant_ids: list[int] = payload.get("tenant_ids", [])

    if Lease.objects.filter(apartment_id=new_apartment_id).exists():
        msg = "O apartamento destino já está alugado."
        raise ValueError(msg)

    Lease.objects.filter(pk=old_lease.pk).update(
        contract_generated=False,
        contract_signed=False,
        interfone_configured=False,
    )
    old_lease.refresh_from_db()
    old_lease.delete(deleted_by=user)

    raw_deposit = payload.get("deposit_amount")
    deposit_amount: Decimal | None = Decimal(str(raw_deposit)) if raw_deposit else None

    raw_rental_value = payload.get("rental_value")
    rental_value: Decimal = (
        Decimal(str(raw_rental_value)) if raw_rental_value else old_lease.rental_value
    )

    new_lease = Lease.objects.create(
        apartment_id=new_apartment_id,
        responsible_tenant_id=responsible_tenant_id,
        start_date=payload.get("start_date", date.today()),
        validity_months=payload.get("validity_months", 12),
        tag_fee=Decimal(str(payload.get("tag_fee", 0))),
        rental_value=rental_value,
        deposit_amount=deposit_amount,
        cleaning_fee_paid=payload.get("cleaning_fee_paid", False),
        tag_deposit_paid=payload.get("tag_deposit_paid", False),
        contract_generated=False,
        contract_signed=False,
        interfone_configured=False,
    )
    if tenant_ids:
        new_lease.tenants.set(tenant_ids)

    return new_lease
