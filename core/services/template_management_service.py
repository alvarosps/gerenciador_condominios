"""
Template management service for contract template CRUD operations.

Handles all business logic related to contract template management including:
- Reading current template from filesystem
- Saving template with automatic backup
- Rendering template preview with sample data
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from typing import Dict, Optional

from django.conf import settings

from jinja2 import BaseLoader, Environment

from core.models import Lease
from core.utils import format_currency, number_to_words

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
    def get_template_path() -> str:
        """
        Get the absolute path to the contract template file.

        Returns:
            str: Absolute path to contract_template.html

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = os.path.join(settings.BASE_DIR, "core", "templates", "contract_template.html")

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found at {template_path}")

        return template_path

    @staticmethod
    def get_backup_directory() -> str:
        """
        Get the directory for template backups.

        Returns:
            str: Absolute path to backups directory

        Creates the directory if it doesn't exist.
        """
        backup_dir = os.path.join(settings.BASE_DIR, "core", "templates", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @classmethod
    def get_template(cls) -> str:
        """
        Read current contract template content.

        Returns:
            str: Template HTML content

        Raises:
            FileNotFoundError: If template file doesn't exist
            IOError: If file cannot be read
        """
        try:
            template_path = cls.get_template_path()

            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info("Template content retrieved successfully")
            return content

        except Exception as e:
            logger.error(f"Error reading template: {str(e)}")
            raise

    @classmethod
    def save_template(cls, content: str) -> Dict[str, str]:
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
            raise ValueError("Template content cannot be empty")

        try:
            template_path = cls.get_template_path()
            backup_dir = cls.get_backup_directory()

            # Generate timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"contract_template_backup_{timestamp}.html"
            backup_path = os.path.join(backup_dir, backup_filename)

            # Create backup of current template
            if os.path.exists(template_path):
                shutil.copy2(template_path, backup_path)
                logger.info(f"Backup created: {backup_path}")

            # Save new template
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("Template saved successfully")

            return {
                "message": "Template salvo com sucesso! Backup criado.",
                "backup_path": backup_path,
                "backup_filename": backup_filename,
            }

        except Exception as e:
            logger.error(f"Error saving template: {str(e)}")
            raise

    @classmethod
    def preview_template(cls, content: str, lease_id: Optional[int] = None) -> str:
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
        try:
            # Get sample lease
            if lease_id:
                sample_lease = (
                    Lease.objects.select_related(
                        "apartment",
                        "apartment__building",
                        "responsible_tenant",
                    )
                    .prefetch_related(
                        "tenants",
                        "tenants__dependents",
                        "tenants__furnitures",
                        "apartment__furnitures",
                    )
                    .get(pk=lease_id)
                )
            else:
                sample_lease = (
                    Lease.objects.select_related(
                        "apartment",
                        "apartment__building",
                        "responsible_tenant",
                    )
                    .prefetch_related(
                        "tenants",
                        "tenants__dependents",
                        "tenants__furnitures",
                        "apartment__furnitures",
                    )
                    .first()
                )

            if not sample_lease:
                raise ValueError(
                    "Nenhuma locação encontrada no sistema. " "Crie uma locação para visualizar o preview."
                )

            # Import ContractService to reuse context preparation
            from .contract_service import ContractService

            # Prepare context using the same logic as contract generation
            context = ContractService.prepare_contract_context(sample_lease)

            # Render template with Jinja2
            env = Environment(loader=BaseLoader())
            env.filters["currency"] = format_currency
            env.filters["extenso"] = number_to_words

            template = env.from_string(content)
            html_content = template.render(context)

            logger.info("Template preview rendered successfully")
            return html_content

        except Lease.DoesNotExist:
            raise ValueError(f"Locação com ID {lease_id} não encontrada")
        except Exception as e:
            logger.error(f"Error rendering template preview: {str(e)}")
            raise

    @classmethod
    def list_backups(cls) -> list[Dict[str, str]]:
        """
        List all template backups.

        Returns:
            list: List of backup info dicts with filename, path, and timestamp
        """
        try:
            backup_dir = cls.get_backup_directory()
            backups = []

            for filename in sorted(os.listdir(backup_dir), reverse=True):
                if filename.startswith("contract_template_backup_") and filename.endswith(".html"):
                    file_path = os.path.join(backup_dir, filename)
                    stat_info = os.stat(file_path)

                    backups.append(
                        {
                            "filename": filename,
                            "path": file_path,
                            "size": stat_info.st_size,
                            "created_at": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                        }
                    )

            return backups

        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            raise

    @classmethod
    def restore_backup(cls, backup_filename: str) -> Dict[str, str]:
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
        try:
            backup_dir = cls.get_backup_directory()
            backup_path = os.path.join(backup_dir, backup_filename)

            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_filename}")

            template_path = cls.get_template_path()

            # Create a backup of current template before restoring
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_backup = f"contract_template_before_restore_{timestamp}.html"
            safety_backup_path = os.path.join(backup_dir, safety_backup)
            shutil.copy2(template_path, safety_backup_path)

            # Restore the backup
            shutil.copy2(backup_path, template_path)

            logger.info(f"Template restored from backup: {backup_filename}")

            return {
                "message": f"Template restaurado com sucesso de {backup_filename}",
                "safety_backup": safety_backup,
            }

        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            raise
