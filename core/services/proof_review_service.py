"""Payment-proof review state machine, extracted from the viewset.

The viewset only resolves the proof and the request payload; the approve/reject
state transition and the tenant notification live here (architecture: business
logic in services, not views).
"""

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.exceptions import Conflict
from core.models import PaymentProof, RentPayment
from core.services.notification_service import notify_proof_reviewed
from core.services.rent_schedule_service import RentScheduleService

VALID_REVIEW_ACTIONS = ("approve", "reject")
_NOT_PENDING_ERROR = "Apenas comprovantes pendentes podem ser revisados."
_INVALID_ACTION_ERROR = "action deve ser 'approve' ou 'reject'."


class ProofReviewService:
    """Stateless service for reviewing tenant payment proofs."""

    @staticmethod
    def review(*, proof: PaymentProof, action: str, reason: str, user: User) -> PaymentProof:
        """Approve or reject a pending payment proof, then notify the tenant.

        Approving registers the rent payment for the proof's reference month via
        ``RentScheduleService.toggle_payment`` (SSOT), unless a RentPayment already
        exists for that (lease, reference_month) — idempotent, never duplicates.
        Rejecting has no effect on RentPayment.

        Raises ``Conflict`` (409) when the proof is not pending, when the reference
        month's rent cannot be registered (finalized month / non-collectible lease),
        and ``ValidationError`` (400) for an unknown action. The tenant's
        rejection_reason is only set on reject.
        """
        if proof.status != "pending":
            raise Conflict(_NOT_PENDING_ERROR)
        if action not in VALID_REVIEW_ACTIONS:
            raise ValidationError({"action": _INVALID_ACTION_ERROR})

        proof.reviewed_by = user
        proof.reviewed_at = timezone.now()
        if action == "approve":
            proof.status = "approved"
            ProofReviewService._register_rent_payment(proof, user)
        else:
            proof.status = "rejected"
            proof.rejection_reason = reason

        # AuditMixin.save appends updated_at to update_fields automatically.
        proof.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"])
        notify_proof_reviewed(proof)
        return proof

    @staticmethod
    def _register_rent_payment(proof: PaymentProof, user: User) -> None:
        """Mark the proof's reference month as paid for its lease, idempotently."""
        already_paid = RentPayment.objects.filter(
            lease_id=proof.lease_id, reference_month=proof.reference_month
        ).exists()
        if already_paid:
            return

        result = RentScheduleService.toggle_payment(proof.lease_id, proof.reference_month, user)
        if result["status"] != "ok":
            raise Conflict(str(result["message"]))
