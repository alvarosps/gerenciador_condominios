"""Landlord activation service.

The landlord is a singleton: at most one active landlord exists at a time, enforced at the DB
level by the ``unique_active_landlord`` partial constraint. Activation must therefore deactivate
the others and activate the target inside a single transaction — done here instead of in
``Landlord.save`` so business logic lives in the service layer (architecture rules).
"""

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.models import Landlord


class LandlordService:
    """Stateless operations for the singleton landlord."""

    @staticmethod
    def activate(landlord: Landlord, *, updated_by: Any = None) -> Landlord:
        """Make ``landlord`` the single active landlord.

        Deactivates every other active landlord and activates the target, all within one
        transaction so the ``unique_active_landlord`` partial constraint is never transiently
        violated (deactivation happens before activation). The deactivated rows keep a proper
        audit trail (``updated_at``/``updated_by``) instead of bypassing it via a bare bulk update.

        Args:
            landlord: The landlord to activate (already persisted).
            updated_by: User performing the change, recorded on the deactivated rows.

        Returns:
            The now-active landlord.
        """
        with transaction.atomic():
            Landlord.objects.filter(is_active=True).exclude(pk=landlord.pk).update(
                is_active=False, updated_at=timezone.now(), updated_by=updated_by
            )
            if not landlord.is_active:
                landlord.is_active = True
                if updated_by is not None:
                    landlord.updated_by = updated_by
                landlord.save(update_fields=["is_active", "updated_by"])
        return landlord
