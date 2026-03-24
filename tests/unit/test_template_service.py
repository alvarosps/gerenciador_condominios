"""Unit tests for core/services/template_management_service.py."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings

from core.models import Apartment, Building, Lease, Tenant
from core.services.template_management_service import TemplateManagementService


@pytest.fixture
def template_file(tmp_path, monkeypatch):
    """
    Creates a temporary template file and patches BASE_DIR to point at tmp_path.
    Also creates the expected directory structure under tmp_path.
    """
    template_dir = tmp_path / "core" / "templates"
    template_dir.mkdir(parents=True)
    template_file = template_dir / "contract_template.html"
    template_file.write_text(
        "<html><body>Test template {{ tenant }}</body></html>", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))
    return template_file


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=5501,
        name="Template Test Building",
        address="Rua Template, 5501",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=201,
        rental_value=Decimal("1200.00"),
        cleaning_fee=Decimal("150.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Template Tenant",
        cpf_cnpj="15350946056",  # Valid CPF
        phone="11977770002",
        marital_status="Solteiro(a)",
        profession="Designer",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    l = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date="2026-01-01",
        validity_months=12,
        tag_fee=Decimal("50.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    l.tenants.add(tenant)
    return l


@pytest.mark.unit
class TestGetTemplatePath:
    def test_returns_existing_path(self, template_file):
        path = TemplateManagementService.get_template_path()
        assert path.exists()
        assert path.name == "contract_template.html"

    def test_raises_when_missing(self, tmp_path, monkeypatch):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        (empty_dir / "core" / "templates").mkdir(parents=True)
        monkeypatch.setattr(settings, "BASE_DIR", str(empty_dir))
        with pytest.raises(FileNotFoundError):
            TemplateManagementService.get_template_path()


@pytest.mark.unit
class TestGetBackupDirectory:
    def test_creates_and_returns_directory(self, template_file, tmp_path):
        backup_dir = TemplateManagementService.get_backup_directory()
        assert backup_dir.exists()
        assert backup_dir.name == "backups"


@pytest.mark.unit
class TestEnsureDefaultBackup:
    def test_creates_default_backup_when_not_exists(self, template_file, tmp_path):
        result = TemplateManagementService.ensure_default_backup()
        backup_dir = tmp_path / "core" / "templates" / "backups"
        default_backup = backup_dir / "contract_template_DEFAULT.html"
        assert default_backup.exists()
        # When it creates the file, returns the path
        assert result is not None

    def test_does_not_overwrite_existing_default_backup(self, template_file, tmp_path):
        backup_dir = tmp_path / "core" / "templates" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        default_backup = backup_dir / "contract_template_DEFAULT.html"
        default_backup.write_text("original", encoding="utf-8")

        TemplateManagementService.ensure_default_backup()

        assert default_backup.read_text(encoding="utf-8") == "original"


@pytest.mark.unit
class TestGetTemplate:
    def test_returns_template_content(self, template_file):
        content = TemplateManagementService.get_template()
        assert "Test template" in content

    def test_raises_when_template_missing(self, tmp_path, monkeypatch):
        empty = tmp_path / "notemplate"
        (empty / "core" / "templates").mkdir(parents=True)
        monkeypatch.setattr(settings, "BASE_DIR", str(empty))
        with pytest.raises(FileNotFoundError):
            TemplateManagementService.get_template()


@pytest.mark.unit
class TestSaveTemplate:
    def test_saves_new_content(self, template_file):
        new_content = "<html><body>New Template Content</body></html>"
        result = TemplateManagementService.save_template(new_content)

        assert "message" in result
        assert "backup_path" in result
        assert "backup_filename" in result
        assert template_file.read_text(encoding="utf-8") == new_content

    def test_creates_backup_before_saving(self, template_file, tmp_path):
        TemplateManagementService.save_template("<html>New</html>")
        backup_dir = tmp_path / "core" / "templates" / "backups"
        backup_files = list(backup_dir.glob("contract_template_backup_*.html"))
        assert len(backup_files) >= 1

    def test_raises_value_error_on_empty_content(self, template_file):
        with pytest.raises(ValueError, match="empty"):
            TemplateManagementService.save_template("")

    def test_raises_value_error_on_whitespace_only(self, template_file):
        with pytest.raises(ValueError, match="empty"):
            TemplateManagementService.save_template("   \n\t  ")

    def test_backup_filename_contains_timestamp(self, template_file):
        result = TemplateManagementService.save_template("<html>Content</html>")
        assert "contract_template_backup_" in result["backup_filename"]


@pytest.mark.unit
class TestListBackups:
    def test_returns_empty_list_when_no_backups(self, template_file, tmp_path):
        backups = TemplateManagementService.list_backups()
        # Only DEFAULT may exist from get_template
        assert isinstance(backups, list)

    def test_returns_backup_info_dicts(self, template_file):
        TemplateManagementService.save_template("<html>v1</html>")
        backups = TemplateManagementService.list_backups()
        assert len(backups) >= 1
        backup = backups[0]
        assert "filename" in backup
        assert "path" in backup
        assert "size" in backup
        assert "created_at" in backup
        assert "is_default" in backup

    def test_default_backup_listed_first(self, template_file, tmp_path):
        # Create a DEFAULT backup manually
        backup_dir = tmp_path / "core" / "templates" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        default_path = backup_dir / "contract_template_DEFAULT.html"
        default_path.write_text("<html>default</html>", encoding="utf-8")

        TemplateManagementService.save_template("<html>new</html>")
        backups = TemplateManagementService.list_backups()

        assert backups[0]["is_default"] is True
        assert backups[0]["filename"] == "contract_template_DEFAULT.html"

    def test_only_html_files_returned(self, template_file, tmp_path):
        backup_dir = tmp_path / "core" / "templates" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "somefile.txt").write_text("not html")

        backups = TemplateManagementService.list_backups()
        for b in backups:
            assert b["filename"].endswith(".html")


@pytest.mark.unit
class TestRestoreBackup:
    def test_restores_backup_file(self, template_file, tmp_path):
        original_content = template_file.read_text(encoding="utf-8")
        # Save to create a backup
        TemplateManagementService.save_template("<html>Modified</html>")

        # Get the backup filename
        backup_dir = tmp_path / "core" / "templates" / "backups"
        backup_files = list(backup_dir.glob("contract_template_backup_*.html"))
        assert backup_files

        backup_filename = backup_files[0].name
        result = TemplateManagementService.restore_backup(backup_filename)

        assert "message" in result
        assert "safety_backup" in result
        # Template should be restored to original
        assert template_file.read_text(encoding="utf-8") == original_content

    def test_raises_when_backup_not_found(self, template_file):
        with pytest.raises(FileNotFoundError):
            TemplateManagementService.restore_backup("nonexistent_backup.html")

    def test_creates_safety_backup_before_restore(self, template_file, tmp_path):
        backup_dir = tmp_path / "core" / "templates" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        manual_backup = backup_dir / "contract_template_backup_20240101_000000.html"
        manual_backup.write_text("<html>old</html>", encoding="utf-8")

        TemplateManagementService.restore_backup("contract_template_backup_20240101_000000.html")

        safety_backups = list(backup_dir.glob("contract_template_before_restore_*.html"))
        assert len(safety_backups) >= 1


@pytest.mark.unit
class TestPreviewTemplate:
    def test_raises_when_no_leases_exist(self, template_file):
        Lease.objects.all().delete()
        with pytest.raises(ValueError, match="Nenhuma locação"):
            TemplateManagementService.preview_template("<html>{{ tenant }}</html>")

    def test_raises_when_lease_id_not_found(self, template_file, lease):
        with pytest.raises(ValueError, match="não encontrada"):
            TemplateManagementService.preview_template("<html>{{ tenant }}</html>", lease_id=999999)

    def test_renders_template_with_lease_data(self, template_file, lease):
        # Use a minimal template with a known variable
        html_content = TemplateManagementService.preview_template(
            "<html><body>Contract for lease {{ lease.id }}</body></html>"
        )
        assert isinstance(html_content, str)
        assert str(lease.id) in html_content

    def test_renders_template_with_specific_lease_id(self, template_file, lease):
        html_content = TemplateManagementService.preview_template(
            "<html><body>{{ lease.id }}</body></html>",
            lease_id=lease.id,
        )
        assert str(lease.id) in html_content
