"""
Admin payment proof review endpoints.

Provides admin-only endpoints for listing pending payment proofs
and approving or rejecting them.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import PaymentProof
from core.pagination import CustomPageNumberPagination
from core.permissions import IsAdminUser
from core.serializers import PaymentProofSerializer

_VALID_REVIEW_ACTIONS = ("approve", "reject")


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
    def review(self, request: Request, pk: int | None = None) -> Response:
        """
        POST /api/admin/proofs/{pk}/review/

        Approve or reject a payment proof.
        Body: {"action": "approve"|"reject", "reason": "..."}
        """
        try:
            proof = PaymentProof.objects.get(pk=pk)
        except PaymentProof.DoesNotExist:
            return Response(
                {"error": "Comprovante não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        action_type = request.data.get("action")
        if action_type not in _VALID_REVIEW_ACTIONS:
            return Response(
                {"error": "action deve ser 'approve' ou 'reject'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()

        if action_type == "approve":
            proof.status = "approved"
        else:
            proof.status = "rejected"
            proof.rejection_reason = request.data.get("reason", "")

        proof.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"])
        return Response(PaymentProofSerializer(proof).data)
