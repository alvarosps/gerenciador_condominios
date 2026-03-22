"""
Template management service for contract template CRUD operations.

Handles all business logic related to contract template management including:
- Reading current template from filesystem
- Saving template with automatic backup
- Rendering template preview with sample data
"""

from __future__ import annotations

import datetime as dt
import logging
import shutil
from pathlib import Path

from django.conf import settings
from jinja2 import BaseLoader, Environment, select_autoescape

from core.models import Lease
from core.utils import format_currency, number_to_words

from .contract_service import ContractService

logger = logging.getLogger(__name__)


class TemplateManagementService:
    """
    Service for contract template management.

    Provides enterprise-level template CRUD operations with backup functionality
    and preview rendering using sample lease data.

    Methods:
        get_template: Read current template content from filesystem
        save_template: Save template with automatic versioned backup
        preview_template: Render template with sample data for preview
        list_backups: List all template backups
        restore_backup: Restore a specific backup
    """

    @staticmethod
    def get_template_path() -> Path:
        """
        Get the absolute path to the contract template file.

        Returns:
            Path to contract_template.html

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = Path(settings.BASE_DIR) / "core" / "templates" / "contract_template.html"

        if not template_path.exists():
            msg = f"Template file not found at {template_path}"
            raise FileNotFoundError(msg)

        return template_path

    @staticmethod
    def get_backup_directory() -> Path:
        """
        Get the directory for template backups.

        Returns:
            Path to backups directory

        Creates the directory if it doesn't exist.
        """
        backup_dir = Path(settings.BASE_DIR) / "core" / "templates" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @classmethod
    def ensure_default_backup(cls) -> str | None:
        """
        Ensure a default backup exists.

        Creates a backup named 'contract_template_DEFAULT.html' from the current
        template if it doesn't already exist. This serves as the original template
        that can always be restored.

        Returns:
            str: Path to default backup file, or None if already exists
        """
        try:
            backup_dir = cls.get_backup_directory()
            default_backup_path = backup_dir / "contract_template_DEFAULT.html"

            if not default_backup_path.exists():
                template_path = cls.get_template_path()
                shutil.copy2(template_path, default_backup_path)
                logger.info(f"Default backup created: {default_backup_path}")
                return str(default_backup_path)

        except OSError:
            logger.exception("Error creating default backup")
            return None
        else:
            return None

    @classmethod
    def get_template(cls) -> str:
        """
        Read current contract template content.

        Ensures a default backup exists before returning the template.

        Returns:
            str: Template HTML content

        Raises:
            FileNotFoundError: If template file doesn't exist
            IOError: If file cannot be read
        """
        template_path = cls.get_template_path()

        # Ensure default backup exists on first access
        cls.ensure_default_backup()

        content = template_path.read_text(encoding="utf-8")
        logger.info("Template content retrieved successfully")
        return content

    @classmethod
    def save_template(cls, content: str) -> dict[str, str]:
        """
        Save contract template with automatic backup.

        Creates a timestamped backup of the current template before saving
        the new content. Backups are stored in core/templates/backups/

        Args:
            content: New template HTML content

        Returns:
            dict: {
                "message": Success message,
                "backup_path": Path to backup file
            }

        Raises:
            ValueError: If content is empty
            IOError: If file operations fail
        """
        if not content or not content.strip():
            msg = "Template content cannot be empty"
            raise ValueError(msg)

        template_path = cls.get_template_path()
        backup_dir = cls.get_backup_directory()

        # Generate timestamped backup filename
        timestamp = dt.datetime.now(tz=dt.UTC).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"contract_template_backup_{timestamp}.html"
        backup_path = backup_dir / backup_filename

        # Create backup of current template
        if template_path.exists():
            shutil.copy2(template_path, backup_path)
            logger.info(f"Backup created: {backup_path}")

        # Save new template
        template_path.write_text(content, encoding="utf-8")
        logger.info("Template saved successfully")

        return {
            "message": "Template salvo com sucesso! Backup criado.",
            "backup_path": str(backup_path),
            "backup_filename": backup_filename,
        }

    @classmethod
    def preview_template(cls, content: str, lease_id: int | None = None) -> str:
        """
        Render template with sample data for preview.

        Uses either a specific lease or the first available lease as sample data.
        Renders the template using Jinja2 with the same context as contract generation.

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

        # Render template with Jinja2
        env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(["html"]),
        )
        env.filters["currency"] = format_currency
        env.filters["extenso"] = number_to_words

        template = env.from_string(content)
        html_content = template.render(context)

        logger.info("Template preview rendered successfully")
        return html_content

    @classmethod
    def list_backups(cls) -> list[dict[str, str]]:
        """
        List all template backups.

        Returns the DEFAULT backup first (if exists), followed by timestamped
        backups sorted by creation date (newest first).

        Returns:
            list: List of backup info dicts with filename, path, timestamp, and is_default flag
        """
        backup_dir = cls.get_backup_directory()
        backups = []
        default_backup = None

        for filename in sorted(backup_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if filename.suffix != ".html":
                continue

            stat_info = filename.stat()

            backup_info = {
                "filename": filename.name,
                "path": str(filename),
                "size": stat_info.st_size,
                "created_at": dt.datetime.fromtimestamp(stat_info.st_ctime, tz=dt.UTC).isoformat(),
                "is_default": filename.name == "contract_template_DEFAULT.html",
            }

            # Separate default backup to show first
            if filename.name == "contract_template_DEFAULT.html":
                default_backup = backup_info
            elif filename.name.startswith(
                ("contract_template_backup_", "contract_template_before_restore_")
            ):
                backups.append(backup_info)

        # Put default backup at the beginning if it exists
        if default_backup:
            backups.insert(0, default_backup)

        return backups

    @classmethod
    def restore_backup(cls, backup_filename: str) -> dict[str, str]:
        """
        Restore a template from backup.

        Args:
            backup_filename: Name of the backup file to restore

        Returns:
            dict: {"message": Success message}

        Raises:
            FileNotFoundError: If backup file doesn't exist
            IOError: If file operations fail
        """
        backup_dir = cls.get_backup_directory()
        backup_path = backup_dir / backup_filename

        if not backup_path.exists():
            msg = f"Backup file not found: {backup_filename}"
            raise FileNotFoundError(msg)

        template_path = cls.get_template_path()

        # Create a backup of current template before restoring
        timestamp = dt.datetime.now(tz=dt.UTC).strftime("%Y%m%d_%H%M%S")
        safety_backup = f"contract_template_before_restore_{timestamp}.html"
        safety_backup_path = backup_dir / safety_backup
        shutil.copy2(template_path, safety_backup_path)

        # Restore the backup
        shutil.copy2(backup_path, template_path)

        logger.info(f"Template restored from backup: {backup_filename}")

        return {
            "message": f"Template restaurado com sucesso de {backup_filename}",
            "safety_backup": safety_backup,
        }
