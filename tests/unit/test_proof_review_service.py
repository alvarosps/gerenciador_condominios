"""Tests for ProofReviewService — approve/reject state machine."""

from datetime import date
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from core.exceptions import Conflict
from core.models import PaymentProof
from core.services.proof_review_service import ProofReviewService
from tests.factories import make_lease


def _make_proof(status: str = "pending") -> PaymentProof:
    lease = make_lease()
    return PaymentProof.objects.create(
        lease=lease,
        reference_month=date(2026, 3, 1),
        file=SimpleUploadedFile("p.jpg", BytesIO(b"x").read(), content_type="image/jpeg"),
        status=status,
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestProofReviewService:
    def test_approve_sets_status_and_reviewer(self, admin_user) -> None:
        proof = _make_proof()
        result = ProofReviewService.review(
            proof=proof, action="approve", reason="", user=admin_user
        )
        assert result.status == "approved"
        assert result.reviewed_by == admin_user
        assert result.reviewed_at is not None

    def test_reject_sets_rejection_reason(self, admin_user) -> None:
        proof = _make_proof()
        result = ProofReviewService.review(
            proof=proof, action="reject", reason="ilegível", user=admin_user
        )
        assert result.status == "rejected"
        assert result.rejection_reason == "ilegível"

    def test_non_pending_raises_conflict(self, admin_user) -> None:
        proof = _make_proof(status="approved")
        with pytest.raises(Conflict):
            ProofReviewService.review(proof=proof, action="reject", reason="", user=admin_user)

    def test_invalid_action_raises_validation_error(self, admin_user) -> None:
        proof = _make_proof()
        with pytest.raises(ValidationError):
            ProofReviewService.review(proof=proof, action="bogus", reason="", user=admin_user)

    def test_sets_updated_at(self, admin_user) -> None:
        proof = _make_proof()
        before = proof.updated_at
        result = ProofReviewService.review(
            proof=proof, action="approve", reason="", user=admin_user
        )
        assert result.updated_at >= before
