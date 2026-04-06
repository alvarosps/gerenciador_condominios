"""Celery tasks for async operations."""

from typing import Any

from celery import shared_task


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generate_contract_pdf(self: Any, lease_id: int) -> str:
    """Generate contract PDF asynchronously. Returns the file path."""
    from core.models import Lease
    from core.services.contract_service import ContractService

    lease = Lease.objects.select_related("apartment", "apartment__building").get(id=lease_id)
    path = ContractService.generate_contract(lease)
    return str(path)
