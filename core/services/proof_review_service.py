"""Payment-proof review state machine, extracted from the viewset.

The viewset only resolves the proof and the request payload; the approve/reject
state transition and the tenant notification live here (architecture: business
logic in services, not views).
"""

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.exceptions import Conflict
from core.models import PaymentProof
from core.services.notification_service import notify_proof_reviewed

VALID_REVIEW_ACTIONS = ("approve", "reject")
_NOT_PENDING_ERROR = "Apenas comprovantes pendentes podem ser revisados."
_INVALID_ACTION_ERROR = "action deve ser 'approve' ou 'reject'."


class ProofReviewService:
    """Stateless service for reviewing tenant payment proofs."""

    @staticmethod
    def review(*, proof: PaymentProof, action: str, reason: str, user: User) -> PaymentProof:
        """Approve or reject a pending payment proof, then notify the tenant.

        Raises ``Conflict`` (409) when the proof is not pending and ``ValidationError``
        (400) for an unknown action. The tenant's rejection_reason is only set on reject.
        """
        if proof.status != "pending":
            raise Conflict(_NOT_PENDING_ERROR)
        if action not in VALID_REVIEW_ACTIONS:
            raise ValidationError({"action": _INVALID_ACTION_ERROR})

        proof.reviewed_by = user
        proof.reviewed_at = timezone.now()
        if action == "approve":
            proof.status = "approved"
        else:
            proof.status = "rejected"
            proof.rejection_reason = reason

        # AuditMixin.save appends updated_at to update_fields automatically.
        proof.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"])
        notify_proof_reviewed(proof)
        return proof
