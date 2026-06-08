"""Finances app signal handlers — finance-* cache invalidation (Session 37).

Every write (create / update / soft-delete via post_save / hard-delete via post_delete)
to a finances model invalidates the finance-* dashboard / cash-flow / projection caches
through the single source finances.cache.invalidate_finance_caches.
"""

import logging
from typing import Any

from django.db import models
from django.db.models.signals import post_delete, post_save

from finances.cache import invalidate_finance_caches
from finances.models import (
    Bill,
    BillingAccount,
    BillLineItem,
    BillSkip,
    Category,
    CondoMonthClose,
    ElectricityBillStatement,
    Employee,
    IncomeEntry,
    Installment,
    InstallmentPlan,
    Payment,
    PaymentAllocation,
    Reserve,
    ReserveMovement,
    WaterBillStatement,
)

logger = logging.getLogger(__name__)

_FINANCE_MODELS = (
    Category,
    BillingAccount,
    Bill,
    BillLineItem,
    BillSkip,
    Payment,
    PaymentAllocation,
    InstallmentPlan,
    Installment,
    Employee,
    Reserve,
    ReserveMovement,
    IncomeEntry,
    CondoMonthClose,
    WaterBillStatement,
    ElectricityBillStatement,
)


def _invalidate_finance_cache(
    sender: type[models.Model], instance: models.Model, **kwargs: Any
) -> None:
    """Invalidate finance-* caches on any finances-model write (soft-delete is a post_save)."""
    invalidate_finance_caches()


for _model in _FINANCE_MODELS:
    post_save.connect(
        _invalidate_finance_cache,
        sender=_model,
        dispatch_uid=f"finance_cache_save_{_model.__name__}",
    )
    post_delete.connect(
        _invalidate_finance_cache,
        sender=_model,
        dispatch_uid=f"finance_cache_delete_{_model.__name__}",
    )
