"""
Landlord management views.

Provides endpoints for managing the landlord/owner configuration:
- Get current (active) landlord
- Update landlord information

This is a singleton-like resource - there's only one active landlord.
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Landlord
from ..permissions import IsAdminUser
from ..serializers import LandlordSerializer

logger = logging.getLogger(__name__)


class LandlordViewSet(viewsets.ViewSet):
    """
    ViewSet for landlord (LOCADOR) management.

    Permissions: Admin only

    This is a singleton-like resource - there's only one active landlord
    that is used for all contract generation.

    Endpoints:
        GET /api/landlords/current/ - Get the active landlord
        PUT /api/landlords/current/ - Update or create landlord
        PATCH /api/landlords/current/ - Partial update landlord
    """

    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["get", "put", "patch"], url_path="current")
    def current(self, request):
        """
        Get or update the currently active landlord.

        GET /api/landlords/current/ - Returns the active landlord's data
        PUT /api/landlords/current/ - Full update or create landlord
        PATCH /api/landlords/current/ - Partial update landlord

        Returns:
            Response: Landlord data or error message
        """
        if request.method == "GET":
            landlord = Landlord.get_active()

            if not landlord:
                return Response(
                    {"error": "Nenhum locador configurado"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = LandlordSerializer(landlord)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # PUT or PATCH
        landlord = Landlord.get_active()

        if landlord:
            serializer = LandlordSerializer(
                landlord,
                data=request.data,
                partial=(request.method == "PATCH"),
            )
        else:
            serializer = LandlordSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(is_active=True)
            logger.info(f"Landlord updated: {serializer.data.get('name')}")
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
