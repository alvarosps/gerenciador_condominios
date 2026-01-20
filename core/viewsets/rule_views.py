# core/viewsets/rule_views.py
"""
Contract rule management views.

This module handles all contract rule CRUD operations:
- List all rules
- Create new rule
- Update existing rule
- Delete rule
- Reorder rules

Separated from main views to follow Single Responsibility Principle.
"""
import logging

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import ContractRule
from ..permissions import IsAdminUser
from ..serializers import ContractRuleReorderSerializer, ContractRuleSerializer

logger = logging.getLogger(__name__)


class ContractRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for contract rule management.

    Permissions: Admin only

    Provides full CRUD operations for managing condominium rules
    that appear in rental contracts.

    Endpoints:
        GET    /api/rules/           - List all active rules
        POST   /api/rules/           - Create new rule
        GET    /api/rules/{id}/      - Get single rule
        PUT    /api/rules/{id}/      - Update rule
        PATCH  /api/rules/{id}/      - Partial update rule
        DELETE /api/rules/{id}/      - Soft delete rule
        POST   /api/rules/reorder/   - Bulk reorder rules
    """

    queryset = ContractRule.objects.all()
    serializer_class = ContractRuleSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Return rules ordered by order field.

        Optionally filter by is_active query parameter.
        """
        queryset = super().get_queryset().order_by("order", "id")

        # Optional filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset

    def perform_create(self, serializer):
        """Set created_by and auto-assign order if not provided."""
        instance = serializer.save(created_by=self.request.user)

        # If order not specified, set to last position
        if instance.order == 0:
            max_order = (
                ContractRule.objects.exclude(pk=instance.pk)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
            ) or 0
            instance.order = max_order + 1
            instance.save(update_fields=["order"])

    def perform_update(self, serializer):
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete the rule."""
        instance.delete(deleted_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        """
        Bulk reorder rules by providing ordered list of IDs.

        POST /api/rules/reorder/

        Request Body:
            {
                "rule_ids": [3, 1, 2, 5, 4]  // IDs in desired order
            }

        Returns:
            Response: {"message": "Regras reordenadas com sucesso"}
        """
        serializer = ContractRuleReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rule_ids = serializer.validated_data["rule_ids"]

        try:
            with transaction.atomic():
                # Verify all IDs exist
                existing_ids = set(
                    ContractRule.objects.filter(id__in=rule_ids).values_list(
                        "id", flat=True
                    )
                )
                missing_ids = set(rule_ids) - existing_ids
                if missing_ids:
                    return Response(
                        {"error": f"Regras não encontradas: {list(missing_ids)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Update order for each rule
                for index, rule_id in enumerate(rule_ids):
                    ContractRule.objects.filter(id=rule_id).update(
                        order=index,
                        updated_by=request.user,
                    )

            return Response(
                {"message": "Regras reordenadas com sucesso"},
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Error reordering rules")
            return Response(
                {"error": "Erro ao reordenar regras"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="active")
    def active_rules(self, request):
        """
        Get only active rules (for contract generation).

        GET /api/rules/active/

        Returns:
            Response: List of active rules in order
        """
        rules = ContractRule.objects.filter(is_active=True).order_by("order", "id")
        serializer = self.get_serializer(rules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
