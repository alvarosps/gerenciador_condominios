"""Tests for ProofReviewService — approve/reject state machine."""

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from core.exceptions import Conflict
from core.models import PaymentProof, RentPayment
from core.services.proof_review_service import ProofReviewService
from tests.factories import make_lease


def _make_proof(status: str = "pending", lease=None) -> PaymentProof:
    lease = lease or make_lease()
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


@pytest.mark.unit
@pytest.mark.django_db
class TestProofReviewServiceRentPayment:
    """Approving a proof registers the rent payment for its reference month (P6)."""

    def test_approve_creates_paid_rent_payment(self, admin_user) -> None:
        proof = _make_proof()
        ProofReviewService.review(proof=proof, action="approve", reason="", user=admin_user)

        payment = RentPayment.objects.get(lease=proof.lease, reference_month=proof.reference_month)
        assert payment.amount_paid == proof.lease.rental_value

    def test_approve_twice_same_month_does_not_duplicate(self, admin_user) -> None:
        # Two proofs for the SAME lease/month — approving both must yield one RentPayment.
        lease = make_lease()
        first_proof = _make_proof(lease=lease)
        second_proof = _make_proof(lease=lease)

        ProofReviewService.review(proof=first_proof, action="approve", reason="", user=admin_user)
        ProofReviewService.review(proof=second_proof, action="approve", reason="", user=admin_user)

        assert (
            RentPayment.objects.filter(
                lease=lease, reference_month=first_proof.reference_month
            ).count()
            == 1
        )

    def test_approve_when_month_already_paid_keeps_existing_payment(self, admin_user) -> None:
        lease = make_lease()
        RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1000.00"),
            payment_date=date(2026, 3, 5),
            created_by=admin_user,
            updated_by=admin_user,
        )
        proof = _make_proof(lease=lease)

        ProofReviewService.review(proof=proof, action="approve", reason="", user=admin_user)

        payment = RentPayment.objects.get(lease=lease, reference_month=date(2026, 3, 1))
        assert payment.payment_date == date(2026, 3, 5)

    def test_reject_does_not_create_rent_payment(self, admin_user) -> None:
        proof = _make_proof()
        ProofReviewService.review(proof=proof, action="reject", reason="ilegível", user=admin_user)

        assert not RentPayment.objects.filter(
            lease=proof.lease, reference_month=proof.reference_month
        ).exists()
