# core/viewsets/template_views.py
"""
Contract template management views.

This module handles all contract template CRUD operations:
- Get current template
- Save template with backup
- Preview template with sample data
- List and restore backups

Separated from LeaseViewSet to follow Single Responsibility Principle.
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..permissions import IsAdminUser
from ..services import TemplateManagementService

logger = logging.getLogger(__name__)


class ContractTemplateViewSet(viewsets.ViewSet):
    """
    ViewSet for contract template management.

    Permissions: Admin only

    Provides endpoints for managing the contract template used for
    PDF generation. All changes are backed up automatically.
    """

    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["get"], url_path="current")
    def get_template(self, request):
        """
        Get current contract template HTML.

        GET /api/templates/current/

        Returns the HTML content of the current contract template used for
        PDF generation. Used by the template editor frontend.

        Returns:
            Response: {"content": "<html>...</html>"}
        """
        try:
            content = TemplateManagementService.get_template()
            return Response({"content": content}, status=status.HTTP_200_OK)
        except FileNotFoundError as e:
            logger.warning(f"Template file not found: {e}")
            return Response(
                {"error": "Template de contrato não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionError as e:
            logger.error(f"Permission denied reading template: {e}")
            return Response(
                {"error": "Sem permissão para ler o template"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception:
            logger.exception("Unexpected error getting template")
            return Response(
                {"error": "Erro interno ao obter template"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="save")
    def save_template(self, request):
        """
        Save contract template HTML with automatic backup.

        POST /api/templates/save/

        Creates a timestamped backup of the current template before saving
        the new content. Backups are stored in core/templates/backups/

        Request Body:
            {
                "content": "<html>...</html>"
            }

        Returns:
            Response: {
                "message": "Template salvo com sucesso!",
                "backup_path": "path/to/backup",
                "backup_filename": "backup_filename.html"
            }
        """
        content = request.data.get("content")

        if not content:
            return Response(
                {"error": "O campo 'content' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = TemplateManagementService.save_template(content)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            logger.error(f"Permission denied saving template: {e}")
            return Response(
                {"error": "Sem permissão para salvar o template"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except OSError as e:
            logger.error(f"OS error saving template: {e}")
            return Response(
                {"error": "Erro ao salvar arquivo do template"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception("Unexpected error saving template")
            return Response(
                {"error": "Erro interno ao salvar template"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="preview")
    def preview_template(self, request):
        """
        Render template with sample data for preview.

        POST /api/templates/preview/

        Renders the provided template content with sample lease data to
        generate a preview. Uses the first available lease or a specific
        lease if lease_id is provided.

        Request Body:
            {
                "content": "<html>...</html>",
                "lease_id": 123  // Optional
            }

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
    def list_backups(self, request):
        """
        List all template backups.

        GET /api/templates/backups/

        Returns a list of all template backups with metadata including
        filename, size, and creation timestamp.

        Returns:
            Response: [
                {
                    "filename": "backup_filename.html",
                    "path": "absolute/path",
                    "size": 12345,
                    "created_at": "2025-01-19T14:30:00"
                },
                ...
            ]
        """
        try:
            backups = TemplateManagementService.list_backups()
            return Response(backups, status=status.HTTP_200_OK)
        except FileNotFoundError as e:
            logger.warning(f"Backup directory not found: {e}")
            return Response([], status=status.HTTP_200_OK)  # Return empty list if no backups
        except PermissionError as e:
            logger.error(f"Permission denied listing backups: {e}")
            return Response(
                {"error": "Sem permissão para listar backups"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception:
            logger.exception("Unexpected error listing backups")
            return Response(
                {"error": "Erro interno ao listar backups"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="restore")
    def restore_backup(self, request):
        """
        Restore a template from backup.

        POST /api/templates/restore/

        Restores a specific backup file. Creates a safety backup of the
        current template before restoring.

        Request Body:
            {
                "backup_filename": "contract_template_backup_20250119_143000.html"
            }

        Returns:
            Response: {
                "message": "Template restaurado com sucesso",
                "safety_backup": "safety_backup_filename.html"
            }
        """
        backup_filename = request.data.get("backup_filename")

        if not backup_filename:
            return Response(
                {"error": "O campo 'backup_filename' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = TemplateManagementService.restore_backup(backup_filename)
            return Response(result, status=status.HTTP_200_OK)
        except FileNotFoundError as e:
            logger.warning(f"Backup file not found: {e}")
            return Response(
                {"error": "Arquivo de backup não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionError as e:
            logger.error(f"Permission denied restoring backup: {e}")
            return Response(
                {"error": "Sem permissão para restaurar backup"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except OSError as e:
            logger.error(f"OS error restoring backup: {e}")
            return Response(
                {"error": "Erro ao restaurar arquivo de backup"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception("Unexpected error restoring backup")
            return Response(
                {"error": "Erro interno ao restaurar backup"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
