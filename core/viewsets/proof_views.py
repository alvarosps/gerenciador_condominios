"""
Admin payment proof review endpoints.

Provides admin-only endpoints for listing pending payment proofs
and approving or rejecting them.
"""

from typing import cast

from django.contrib.auth.models import User
from django.http import HttpResponseBase
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import PaymentProof
from core.pagination import CustomPageNumberPagination
from core.permissions import IsAdminUser
from core.serializers import PaymentProofSerializer
from core.services.file_response_service import proof_file_response
from core.services.proof_review_service import ProofReviewService


class AdminProofViewSet(ViewSet):
    """ViewSet for admin review of tenant payment proofs."""

    permission_classes = [IsAdminUser]

    def list(self, request: Request) -> Response:
        """
        GET /api/admin/proofs/?status=pending

        Returns a paginated list of payment proofs filtered by status.
        Defaults to 'pending' proofs.
        """
        status_filter = request.query_params.get("status", "pending")
        proofs = (
            PaymentProof.objects.filter(status=status_filter)
            .select_related(
                "lease",
                "lease__apartment",
                "lease__apartment__building",
                "lease__responsible_tenant",
            )
            .order_by("-created_at")
        )
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(proofs, request)
        serializer = PaymentProofSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request: Request, pk: str | None = None) -> Response:
        """
        POST /api/admin/proofs/{pk}/review/

        Approve or reject a payment proof.
        Body: {"action": "approve"|"reject", "reason": "..."}
        """
        proof = get_object_or_404(PaymentProof, pk=pk)
        proof = ProofReviewService.review(
            proof=proof,
            action=request.data.get("action", ""),
            reason=request.data.get("reason", ""),
            user=cast(User, request.user),
        )
        return Response(PaymentProofSerializer(proof).data)

    @action(detail=True, methods=["get"], url_path="file")
    def file(self, request: Request, pk: str | None = None) -> HttpResponseBase:
        """
        GET /api/admin/proofs/{pk}/file/

        Stream the proof's uploaded file for admin review.
        """
        if not pk:
            return Response(
                {"detail": "Comprovante não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            proof = PaymentProof.objects.select_related("lease").get(pk=pk)
        except PaymentProof.DoesNotExist:
            return Response(
                {"detail": "Comprovante não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not proof.file:
            return Response(
                {"detail": "Arquivo não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return proof_file_response(proof)
