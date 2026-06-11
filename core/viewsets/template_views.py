# core/viewsets/template_views.py
"""
Contract template management views.

This module handles all contract template CRUD operations:
- Get the active template
- Save a new active version (with backup rotation)
- Preview a template with sample data
- List versions and restore one by id

Persistence is database-backed (``ContractTemplate``); restore takes an integer version
id, so there is no filesystem path traversal surface.

Separated from LeaseViewSet to follow Single Responsibility Principle.
"""

import logging
from typing import cast

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import ContractTemplate
from ..permissions import IsAdminUser
from ..services import TemplateManagementService

logger = logging.getLogger(__name__)


class ContractTemplateViewSet(viewsets.ViewSet):
    """
    ViewSet for contract template management.

    Permissions: Admin only

    Provides endpoints for managing the contract template used for PDF generation.
    Every save creates a new versioned backup in the database.
    """

    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["get"], url_path="current")
    def get_template(self, request: Request) -> Response:
        """
        Get the active contract template HTML.

        GET /api/templates/current/

        Returns:
            Response: {"content": "<html>...</html>"}
        """
        try:
            content = TemplateManagementService.get_template()
            return Response({"content": content}, status=status.HTTP_200_OK)
        except ContractTemplate.DoesNotExist:
            logger.warning("No active contract template configured")
            return Response(
                {"error": "Template de contrato não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception("Unexpected error getting template")
            return Response(
                {"error": "Erro interno ao obter template"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="save")
    def save_template(self, request: Request) -> Response:
        """
        Save the contract template as a new active version.

        POST /api/templates/save/

        Validates the Jinja syntax, deactivates the previous version, creates the new
        active version, and rotates old backups.

        Request Body:
            {"content": "<html>...</html>"}

        Returns:
            Response: {"message", "version_id", "label"}
        """
        content = request.data.get("content")

        if not content:
            return Response(
                {"error": "O campo 'content' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = TemplateManagementService.save_template(content, user=cast(User, request.user))
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error saving template")
            return Response(
                {"error": "Erro interno ao salvar template"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="preview")
    def preview_template(self, request: Request) -> Response:
        """
        Render a template with sample data for preview.

        POST /api/templates/preview/

        Request Body:
            {"content": "<html>...</html>", "lease_id": 123}  # lease_id optional

        Returns:
            Response: {"html": "<rendered html>"}
        """
        content = request.data.get("content")
        lease_id = request.data.get("lease_id")

        if not content:
            return Response(
                {"error": "O campo 'content' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            html_content = TemplateManagementService.preview_template(content, lease_id)
            return Response({"html": html_content}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return Response(
                {"error": "Locação não encontrada para preview"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception("Unexpected error previewing template")
            return Response(
                {"error": "Erro interno ao gerar preview"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="backups")
    def list_backups(self, request: Request) -> Response:
        """
        List all template versions.

        GET /api/templates/backups/

        Returns:
            Response: [
                {"id": 1, "label": "Padrão", "created_at": "...",
                 "is_default": true, "is_active": true},
                ...
            ]
        """
        try:
            backups = TemplateManagementService.list_backups()
            return Response(backups, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Unexpected error listing backups")
            return Response(
                {"error": "Erro interno ao listar backups"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="restore")
    def restore_backup(self, request: Request) -> Response:
        """
        Restore (activate) a specific template version by id.

        POST /api/templates/restore/

        Request Body:
            {"version_id": 12}

        Returns:
            Response: {"message", "version_id", "label"}
        """
        version_id = request.data.get("version_id")

        if version_id is None:
            return Response(
                {"error": "O campo 'version_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            version_id = int(version_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "O campo 'version_id' deve ser um número inteiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = TemplateManagementService.restore_backup(
                version_id, user=cast(User, request.user)
            )
            return Response(result, status=status.HTTP_200_OK)
        except ContractTemplate.DoesNotExist:
            logger.warning("Template version not found: %s", version_id)
            return Response(
                {"error": "Versão de template não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception("Unexpected error restoring backup")
            return Response(
                {"error": "Erro interno ao restaurar backup"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
