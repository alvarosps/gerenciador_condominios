"""
Template management service for contract template CRUD operations.

Persistence lives in the database (``ContractTemplate``), not on the container
filesystem — the editor and its version history survive deploys/restarts on ephemeral
filesystems (Render), and restore takes an integer version id (no path traversal).

Handles all business logic related to contract template management including:
- Reading the active template
- Saving a new active version (with syntax validation + backup rotation)
- Rendering a template preview with sample data
- Listing template versions and restoring one by id
"""

import logging

from django.contrib.auth.models import User
from jinja2 import BaseLoader

from core.jinja_environment import build_contract_jinja_env
from core.models import ContractTemplate, Lease

from .contract_service import ContractService

logger = logging.getLogger(__name__)


class TemplateManagementService:
    """
    Service for contract template management.

    Provides template CRUD operations with versioned backups stored in the database
    and preview rendering using sample lease data.

    Methods:
        get_template: Read the active template content
        save_template: Persist a new active version (validates syntax, rotates backups)
        preview_template: Render template with sample data for preview
        list_backups: List all template versions (DEFAULT first, then newest-first)
        restore_backup: Activate a specific version by id
    """

    @classmethod
    def get_template(cls) -> str:
        """
        Read the active contract template content.

        Returns:
            str: Template HTML content

        Raises:
            ContractTemplate.DoesNotExist: If no active template exists
        """
        content = ContractTemplate.get_active_content()
        logger.info("Active contract template retrieved successfully")
        return content

    @classmethod
    def save_template(cls, content: str, user: User | None = None) -> dict[str, object]:
        """
        Persist a new active template version with backup rotation.

        Validates the Jinja syntax before persisting so a broken save never replaces the
        working active version (which would make ALL contract PDF generation fail).

        Args:
            content: New template HTML content
            user: User performing the change (audit)

        Returns:
            dict: {"message", "version_id", "label"}

        Raises:
            ValueError: If content is empty or has invalid Jinja syntax
        """
        version = ContractTemplate.save_version(content, user=user)
        logger.info("Contract template version %s saved successfully", version.pk)
        return {
            "message": "Template salvo com sucesso! Versão de backup criada.",
            "version_id": version.pk,
            "label": version.label,
        }

    @classmethod
    def preview_template(cls, content: str, lease_id: int | None = None) -> str:
        """
        Render template with sample data for preview.

        Uses either a specific lease or the first available lease as sample data.
        Renders the template using the shared sandboxed Jinja environment.

        Args:
            content: Template HTML content to render
            lease_id: Optional specific lease ID to use as sample data

        Returns:
            str: Rendered HTML content

        Raises:
            ValueError: If no sample lease is available
            Exception: If template rendering fails
        """
        lease_qs = Lease.objects.select_related(
            "apartment",
            "apartment__building",
            "responsible_tenant",
        ).prefetch_related(
            "tenants",
            "tenants__dependents",
            "tenants__furnitures",
            "apartment__furnitures",
        )

        try:
            sample_lease = lease_qs.get(pk=lease_id) if lease_id else lease_qs.first()
        except Lease.DoesNotExist:
            msg = f"Locação com ID {lease_id} não encontrada"
            raise ValueError(msg) from None

        if not sample_lease:
            msg = (
                "Nenhuma locação encontrada no sistema. Crie uma locação para visualizar o preview."
            )
            raise ValueError(msg)

        # Prepare context using the same logic as contract generation
        context = ContractService.prepare_contract_context(sample_lease)

        # Render template with the shared sandboxed Jinja environment
        env = build_contract_jinja_env(BaseLoader())
        template = env.from_string(content)
        html_content = template.render(context)

        logger.info("Template preview rendered successfully")
        return html_content

    @classmethod
    def list_backups(cls) -> list[dict[str, object]]:
        """
        List all template versions.

        Returns the DEFAULT version first, followed by the remaining versions sorted by
        creation date (newest first).

        Returns:
            list: Version info dicts with id, label, created_at, is_default, is_active
        """
        return [
            {
                "id": version.pk,
                "label": version.label,
                "created_at": version.created_at.isoformat(),
                "is_default": version.is_default,
                "is_active": version.is_active,
            }
            for version in ContractTemplate.list_versions()
        ]

    @classmethod
    def restore_backup(cls, version_id: int, user: User | None = None) -> dict[str, object]:
        """
        Activate a specific template version by id.

        Args:
            version_id: Primary key of the version to activate
            user: User performing the restore (audit)

        Returns:
            dict: {"message", "version_id", "label"}

        Raises:
            ContractTemplate.DoesNotExist: If the version id does not exist
        """
        version = ContractTemplate.restore_version(version_id, user=user)
        logger.info("Contract template restored to version %s", version.pk)
        return {
            "message": f"Template restaurado com sucesso para a versão '{version.label}'.",
            "version_id": version.pk,
            "label": version.label,
        }
