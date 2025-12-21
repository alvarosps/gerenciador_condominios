"""
Unit tests for TemplateManagementService.

Tests all template management operations including:
- Reading template from filesystem
- Saving template with automatic backup
- Preview rendering with sample data
- Listing and restoring backups
"""
import pytest
import os
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from freezegun import freeze_time

from core.services.template_management_service import TemplateManagementService
from core.models import Building, Apartment, Tenant, Lease, Furniture


@pytest.fixture
def mock_template_path(tmp_path, monkeypatch):
    """Mock the template file path to use temporary directory."""
    template_dir = tmp_path / "core" / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_file = template_dir / "contract_template.html"

    # Create a sample template file
    template_content = """<!DOCTYPE html>
<html>
<head><title>Contrato</title></head>
<body>
    <h1>Contrato de Locação</h1>
    <p>Inquilino: {{ tenant.name }}</p>
    <p>Apartamento: {{ apartment_number }}</p>
    <p>Valor: {{ rental_value | currency }}</p>
</body>
</html>"""
    template_file.write_text(template_content, encoding='utf-8')

    # Mock get_template_path to return our temp file
    monkeypatch.setattr(
        'core.services.template_management_service.TemplateManagementService.get_template_path',
        lambda: str(template_file)
    )

    # Mock get_backup_directory
    backup_dir = template_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(
        'core.services.template_management_service.TemplateManagementService.get_backup_directory',
        lambda: str(backup_dir)
    )

    return {
        'template_file': template_file,
        'backup_dir': backup_dir,
        'content': template_content
    }


@pytest.fixture
def sample_lease_for_preview():
    """Create a complete lease with all related objects for preview testing."""
    # Create building
    building = Building.objects.create(
        street_number=836,
        name="Test Building",
        address="Test Street, 836"
    )

    # Create apartment
    apartment = Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal('1500.00'),
        cleaning_fee=Decimal('200.00'),
        max_tenants=2
    )

    # Create furniture
    bed = Furniture.objects.create(name="Bed")
    table = Furniture.objects.create(name="Table")
    apartment.furnitures.add(bed, table)

    # Create tenant
    tenant = Tenant.objects.create(
        name="John Doe",
        cpf_cnpj="12345678901",
        phone="11999999999",
        marital_status="Single",
        profession="Engineer"
    )

    # Create lease
    lease = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=datetime(2025, 1, 15).date(),
        validity_months=12,
        due_day=10,
        rental_value=Decimal('1500.00'),
        cleaning_fee=Decimal('200.00'),
        tag_fee=Decimal('50.00'),
        contract_generated=False
    )
    lease.tenants.add(tenant)

    return lease


class TestGetTemplatePath:
    """Test template path resolution."""

    def test_get_template_path_returns_absolute_path(self, settings, tmp_path):
        """Test that get_template_path returns an absolute path."""
        settings.BASE_DIR = str(tmp_path)

        # Create the template file
        template_dir = tmp_path / "core" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        template_file = template_dir / "contract_template.html"
        template_file.write_text("test", encoding='utf-8')

        path = TemplateManagementService.get_template_path()

        assert os.path.isabs(path)
        assert "contract_template.html" in path

    def test_get_template_path_raises_if_not_found(self, settings, tmp_path):
        """Test that FileNotFoundError is raised if template doesn't exist."""
        settings.BASE_DIR = str(tmp_path)

        with pytest.raises(FileNotFoundError):
            TemplateManagementService.get_template_path()


class TestGetBackupDirectory:
    """Test backup directory management."""

    def test_get_backup_directory_creates_if_not_exists(self, settings, tmp_path):
        """Test that backup directory is created if it doesn't exist."""
        settings.BASE_DIR = str(tmp_path)

        backup_dir = TemplateManagementService.get_backup_directory()

        assert os.path.exists(backup_dir)
        assert os.path.isdir(backup_dir)
        assert "backups" in backup_dir

    def test_get_backup_directory_returns_existing(self, settings, tmp_path):
        """Test that existing backup directory is returned."""
        settings.BASE_DIR = str(tmp_path)

        # Create backup directory
        backup_path = tmp_path / "core" / "templates" / "backups"
        backup_path.mkdir(parents=True, exist_ok=True)

        # Create a file in it to verify it's not recreated
        test_file = backup_path / "test.txt"
        test_file.write_text("test")

        backup_dir = TemplateManagementService.get_backup_directory()

        assert os.path.exists(backup_dir)
        assert (Path(backup_dir) / "test.txt").exists()


class TestGetTemplate:
    """Test template content retrieval."""

    def test_get_template_returns_content(self, mock_template_path):
        """Test that get_template returns the template content."""
        content = TemplateManagementService.get_template()

        assert content == mock_template_path['content']
        assert "<!DOCTYPE html>" in content
        assert "{{ tenant.name }}" in content

    def test_get_template_handles_utf8(self, mock_template_path):
        """Test that get_template handles UTF-8 encoding correctly."""
        # Add some Portuguese characters
        template_file = Path(TemplateManagementService.get_template_path())
        template_content = "<!DOCTYPE html>\n<html><body>Locação: R$ 1.500,00</body></html>"
        template_file.write_text(template_content, encoding='utf-8')

        content = TemplateManagementService.get_template()

        assert "Locação" in content
        assert "R$ 1.500,00" in content

    def test_get_template_raises_on_read_error(self, monkeypatch):
        """Test that IOError is raised if template cannot be read."""
        # Mock get_template_path to return non-existent file
        monkeypatch.setattr(
            'core.services.template_management_service.TemplateManagementService.get_template_path',
            lambda: '/nonexistent/path/template.html'
        )

        with pytest.raises(Exception):
            TemplateManagementService.get_template()


@freeze_time("2025-01-15 14:30:00")
class TestSaveTemplate:
    """Test template saving with backup."""

    def test_save_template_creates_backup(self, mock_template_path):
        """Test that save_template creates a timestamped backup."""
        new_content = "<html><body>New Template</body></html>"

        result = TemplateManagementService.save_template(new_content)

        # Verify backup was created
        backup_dir = Path(mock_template_path['backup_dir'])
        backup_files = list(backup_dir.glob("contract_template_backup_*.html"))

        assert len(backup_files) == 1
        assert "contract_template_backup_20250115_143000.html" in str(backup_files[0])

        # Verify backup contains old content
        backup_content = backup_files[0].read_text(encoding='utf-8')
        assert backup_content == mock_template_path['content']

    def test_save_template_updates_file(self, mock_template_path):
        """Test that save_template updates the template file."""
        new_content = "<html><body>New Template</body></html>"

        TemplateManagementService.save_template(new_content)

        # Verify template was updated
        template_file = Path(TemplateManagementService.get_template_path())
        current_content = template_file.read_text(encoding='utf-8')

        assert current_content == new_content

    def test_save_template_returns_result(self, mock_template_path):
        """Test that save_template returns success message and paths."""
        new_content = "<html><body>New Template</body></html>"

        result = TemplateManagementService.save_template(new_content)

        assert 'message' in result
        assert 'backup_path' in result
        assert 'backup_filename' in result
        assert "sucesso" in result['message'].lower()
        assert "20250115_143000" in result['backup_filename']

    def test_save_template_rejects_empty_content(self, mock_template_path):
        """Test that save_template rejects empty content."""
        with pytest.raises(ValueError, match="cannot be empty"):
            TemplateManagementService.save_template("")

        with pytest.raises(ValueError, match="cannot be empty"):
            TemplateManagementService.save_template("   ")

    def test_save_template_handles_utf8(self, mock_template_path):
        """Test that save_template handles UTF-8 correctly."""
        new_content = "<html><body>Locação: R$ 1.500,00 - São Paulo</body></html>"

        TemplateManagementService.save_template(new_content)

        # Verify content was saved correctly
        template_file = Path(TemplateManagementService.get_template_path())
        saved_content = template_file.read_text(encoding='utf-8')

        assert saved_content == new_content
        assert "Locação" in saved_content
        assert "São Paulo" in saved_content


class TestPreviewTemplate:
    """Test template preview rendering."""

    @patch('core.services.template_management_service.Environment')
    def test_preview_template_renders_with_sample_lease(
        self, mock_env_class, sample_lease_for_preview
    ):
        """Test that preview_template renders with sample lease data."""
        # Mock Jinja2 environment
        mock_env = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html>Rendered Contract</html>"
        mock_env.from_string.return_value = mock_template
        mock_env.filters = {}
        mock_env_class.return_value = mock_env

        content = "<html>{{ tenant.name }}</html>"

        html = TemplateManagementService.preview_template(content)

        # Verify template was rendered
        assert html == "<html>Rendered Contract</html>"
        mock_env.from_string.assert_called_once_with(content)
        mock_template.render.assert_called_once()

    @patch('core.services.template_management_service.Environment')
    def test_preview_template_uses_specific_lease(
        self, mock_env_class, sample_lease_for_preview
    ):
        """Test that preview_template can use a specific lease."""
        # Mock Jinja2 environment
        mock_env = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html>Test</html>"
        mock_env.from_string.return_value = mock_template
        mock_env.filters = {}
        mock_env_class.return_value = mock_env

        content = "<html>Test</html>"
        lease_id = sample_lease_for_preview.id

        html = TemplateManagementService.preview_template(content, lease_id)

        assert html == "<html>Test</html>"
        # Verify rendering happened
        mock_template.render.assert_called_once()

    @patch('core.services.template_management_service.Environment')
    def test_preview_template_registers_filters(self, mock_env_class):
        """Test that preview_template registers custom Jinja2 filters."""
        # Mock Jinja2 environment
        mock_env = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html>Test</html>"
        mock_env.from_string.return_value = mock_template
        mock_env.filters = {}
        mock_env_class.return_value = mock_env

        # Create minimal lease for testing
        building = Building.objects.create(
            street_number=100,
            name="Test",
            address="Test"
        )
        apartment = Apartment.objects.create(
            building=building,
            number=1,
            rental_value=Decimal('100.00'),
            cleaning_fee=Decimal('10.00'),
            max_tenants=1
        )
        tenant = Tenant.objects.create(
            name="Test",
            cpf_cnpj="123",
            phone="123",
            marital_status="Single",
            profession="Test"
        )
        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=datetime(2025, 1, 1).date(),
            validity_months=12,
            due_day=10,
            rental_value=Decimal('100.00'),
            cleaning_fee=Decimal('10.00'),
            tag_fee=Decimal('50.00')
        )
        lease.tenants.add(tenant)

        TemplateManagementService.preview_template("<html>Test</html>", lease.id)

        # Verify filters were registered
        assert 'currency' in mock_env.filters
        assert 'extenso' in mock_env.filters

    def test_preview_template_raises_if_no_lease(self):
        """Test that preview_template raises error if no lease exists."""
        content = "<html>Test</html>"

        with pytest.raises(ValueError, match="Nenhuma locação encontrada"):
            TemplateManagementService.preview_template(content)

    def test_preview_template_raises_if_lease_not_found(self):
        """Test that preview_template raises error if specific lease not found."""
        content = "<html>Test</html>"

        with pytest.raises(ValueError, match="não encontrada"):
            TemplateManagementService.preview_template(content, lease_id=99999)


@freeze_time("2025-01-15 14:30:00")
class TestListBackups:
    """Test backup listing."""

    def test_list_backups_returns_empty_list(self, mock_template_path):
        """Test that list_backups returns empty list if no backups exist."""
        backups = TemplateManagementService.list_backups()

        assert backups == []

    def test_list_backups_returns_backup_info(self, mock_template_path):
        """Test that list_backups returns backup information."""
        # Create some backups
        backup_dir = Path(mock_template_path['backup_dir'])

        backup1 = backup_dir / "contract_template_backup_20250115_120000.html"
        backup1.write_text("backup 1", encoding='utf-8')

        backup2 = backup_dir / "contract_template_backup_20250115_130000.html"
        backup2.write_text("backup 2", encoding='utf-8')

        backups = TemplateManagementService.list_backups()

        assert len(backups) == 2

        # Verify backup info structure
        for backup in backups:
            assert 'filename' in backup
            assert 'path' in backup
            assert 'size' in backup
            assert 'created_at' in backup
            assert backup['filename'].startswith('contract_template_backup_')
            assert backup['filename'].endswith('.html')

    def test_list_backups_sorted_by_date_descending(self, mock_template_path):
        """Test that backups are sorted by date (newest first)."""
        # Create backups with different timestamps
        backup_dir = Path(mock_template_path['backup_dir'])

        backup1 = backup_dir / "contract_template_backup_20250115_100000.html"
        backup1.write_text("old", encoding='utf-8')

        backup2 = backup_dir / "contract_template_backup_20250115_140000.html"
        backup2.write_text("new", encoding='utf-8')

        backups = TemplateManagementService.list_backups()

        # Newest should be first
        assert backups[0]['filename'] == "contract_template_backup_20250115_140000.html"
        assert backups[1]['filename'] == "contract_template_backup_20250115_100000.html"

    def test_list_backups_includes_file_size(self, mock_template_path):
        """Test that backup info includes file size."""
        backup_dir = Path(mock_template_path['backup_dir'])

        backup = backup_dir / "contract_template_backup_20250115_120000.html"
        content = "A" * 1000  # 1000 bytes
        backup.write_text(content, encoding='utf-8')

        backups = TemplateManagementService.list_backups()

        assert len(backups) == 1
        assert backups[0]['size'] >= 1000  # Should be at least 1000 bytes

    def test_list_backups_ignores_non_backup_files(self, mock_template_path):
        """Test that list_backups ignores non-backup files."""
        backup_dir = Path(mock_template_path['backup_dir'])

        # Create valid backup
        valid_backup = backup_dir / "contract_template_backup_20250115_120000.html"
        valid_backup.write_text("valid", encoding='utf-8')

        # Create invalid files
        (backup_dir / "other_file.html").write_text("not a backup", encoding='utf-8')
        (backup_dir / "template.txt").write_text("wrong extension", encoding='utf-8')

        backups = TemplateManagementService.list_backups()

        # Should only return the valid backup
        assert len(backups) == 1
        assert backups[0]['filename'] == "contract_template_backup_20250115_120000.html"


@freeze_time("2025-01-15 16:00:00")
class TestRestoreBackup:
    """Test backup restoration."""

    def test_restore_backup_replaces_template(self, mock_template_path):
        """Test that restore_backup replaces current template."""
        # Create a backup
        backup_dir = Path(mock_template_path['backup_dir'])
        backup_file = backup_dir / "contract_template_backup_20250115_120000.html"
        backup_content = "<html><body>Old Template</body></html>"
        backup_file.write_text(backup_content, encoding='utf-8')

        # Modify current template
        template_file = Path(TemplateManagementService.get_template_path())
        template_file.write_text("<html><body>New Template</body></html>", encoding='utf-8')

        # Restore backup
        TemplateManagementService.restore_backup("contract_template_backup_20250115_120000.html")

        # Verify template was restored
        restored_content = template_file.read_text(encoding='utf-8')
        assert restored_content == backup_content

    def test_restore_backup_creates_safety_backup(self, mock_template_path):
        """Test that restore_backup creates a safety backup of current template."""
        # Create a backup
        backup_dir = Path(mock_template_path['backup_dir'])
        backup_file = backup_dir / "contract_template_backup_20250115_120000.html"
        backup_file.write_text("<html><body>Old Template</body></html>", encoding='utf-8')

        # Set current template
        template_file = Path(TemplateManagementService.get_template_path())
        current_content = "<html><body>Current Template</body></html>"
        template_file.write_text(current_content, encoding='utf-8')

        # Restore backup
        result = TemplateManagementService.restore_backup("contract_template_backup_20250115_120000.html")

        # Verify safety backup was created
        safety_backup = backup_dir / result['safety_backup']
        assert safety_backup.exists()
        assert "before_restore_20250115_160000" in result['safety_backup']

        # Verify safety backup contains current content
        safety_content = safety_backup.read_text(encoding='utf-8')
        assert safety_content == current_content

    def test_restore_backup_returns_result(self, mock_template_path):
        """Test that restore_backup returns success message."""
        # Create a backup
        backup_dir = Path(mock_template_path['backup_dir'])
        backup_file = backup_dir / "contract_template_backup_20250115_120000.html"
        backup_file.write_text("<html>Test</html>", encoding='utf-8')

        result = TemplateManagementService.restore_backup("contract_template_backup_20250115_120000.html")

        assert 'message' in result
        assert 'safety_backup' in result
        assert "restaurado com sucesso" in result['message'].lower()
        assert "contract_template_backup_20250115_120000.html" in result['message']

    def test_restore_backup_raises_if_not_found(self, mock_template_path):
        """Test that restore_backup raises error if backup not found."""
        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            TemplateManagementService.restore_backup("nonexistent_backup.html")

    def test_restore_backup_handles_utf8(self, mock_template_path):
        """Test that restore_backup handles UTF-8 correctly."""
        # Create backup with UTF-8 content
        backup_dir = Path(mock_template_path['backup_dir'])
        backup_file = backup_dir / "contract_template_backup_20250115_120000.html"
        backup_content = "<html><body>Locação em São Paulo - R$ 1.500,00</body></html>"
        backup_file.write_text(backup_content, encoding='utf-8')

        # Restore backup
        TemplateManagementService.restore_backup("contract_template_backup_20250115_120000.html")

        # Verify UTF-8 was preserved
        template_file = Path(TemplateManagementService.get_template_path())
        restored_content = template_file.read_text(encoding='utf-8')

        assert "Locação" in restored_content
        assert "São Paulo" in restored_content
        assert "R$ 1.500,00" in restored_content


class TestTemplateManagementServiceIntegration:
    """Integration tests for TemplateManagementService."""

    @freeze_time("2025-01-15 10:00:00")
    def test_complete_save_and_restore_flow(self, mock_template_path):
        """Test complete flow: save → modify → restore."""
        # 1. Get original content
        original_content = TemplateManagementService.get_template()

        # 2. Save new version (creates backup)
        new_content_v1 = "<html><body>Version 1</body></html>"
        result1 = TemplateManagementService.save_template(new_content_v1)
        backup_filename_v1 = result1['backup_filename']

        # 3. Save another version
        with freeze_time("2025-01-15 11:00:00"):
            new_content_v2 = "<html><body>Version 2</body></html>"
            result2 = TemplateManagementService.save_template(new_content_v2)
            backup_filename_v2 = result2['backup_filename']

        # 4. List backups (should have 2)
        backups = TemplateManagementService.list_backups()
        assert len(backups) == 2

        # 5. Restore first backup (contains original content)
        with freeze_time("2025-01-15 12:00:00"):
            restore_result = TemplateManagementService.restore_backup(backup_filename_v1)

        # 6. Verify content was restored to original (backup_v1 has original)
        current_content = TemplateManagementService.get_template()
        assert current_content == original_content

        # 7. Verify safety backup was created (but not listed in regular backups)
        # list_backups() only returns manual backups, not safety backups
        backups = TemplateManagementService.list_backups()
        assert len(backups) == 2  # 2 manual backups (safety backup uses different naming)

        # Verify safety backup file exists
        backup_dir = Path(mock_template_path['backup_dir'])
        safety_files = list(backup_dir.glob("contract_template_before_restore_*.html"))
        assert len(safety_files) == 1  # Safety backup was created

    @patch('core.services.contract_service.ContractService.prepare_contract_context')
    @patch('core.services.template_management_service.Environment')
    def test_preview_uses_contract_service_context(
        self, mock_env_class, mock_prepare_context, sample_lease_for_preview
    ):
        """Test that preview reuses ContractService.prepare_contract_context."""
        # Mock Jinja2
        mock_env = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html>Test</html>"
        mock_env.from_string.return_value = mock_template
        mock_env.filters = {}
        mock_env_class.return_value = mock_env

        # Mock context preparation
        mock_context = {
            'tenant': sample_lease_for_preview.responsible_tenant,
            'building_number': 836,
            'apartment_number': 101,
        }
        mock_prepare_context.return_value = mock_context

        content = "<html>{{ tenant.name }}</html>"
        TemplateManagementService.preview_template(content, sample_lease_for_preview.id)

        # Verify ContractService.prepare_contract_context was called
        mock_prepare_context.assert_called_once()

        # Verify template was rendered with that context
        mock_template.render.assert_called_once_with(mock_context)
