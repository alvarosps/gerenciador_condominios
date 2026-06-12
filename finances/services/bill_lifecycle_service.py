"""Bill lifecycle-state transitions (Session 38).

Kept in the service layer (never the view) — S37 did not expose a transition helper,
so the suspend/defer/cancel/reactivate actions delegate here.
"""

import logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from finances.models import Bill, BillLifecycleState
from finances.services.condo_month_close_service import CondoMonthCloseService

logger = logging.getLogger(__name__)

_REACTIVATABLE = {BillLifecycleState.SUSPENDED, BillLifecycleState.DEFERRED}


class BillLifecycleService:
    """Stateless lifecycle-state transitions for a Bill."""

    @staticmethod
    def set_state(bill: Bill, state: str, user: User | None = None) -> Bill:
        # Suspend/defer/cancel/reactivate all funnel through here; a transition in a closed month
        # would change that month's frozen expense_competence, so it is rejected (PT 400 — §4.7).
        CondoMonthCloseService.assert_open(bill.competence_month)
        bill.lifecycle_state = state
        if user is not None:
            bill.updated_by = user
        bill.save(update_fields=["lifecycle_state", "updated_by", "updated_at"])
        return bill

    @staticmethod
    def reactivate(bill: Bill, user: User | None = None) -> Bill:
        if bill.lifecycle_state not in _REACTIVATABLE:
            raise ValidationError(
                {"lifecycle_state": "Só é possível reativar uma conta suspensa ou adiada."}
            )
        return BillLifecycleService.set_state(bill, BillLifecycleState.ACTIVE, user)
