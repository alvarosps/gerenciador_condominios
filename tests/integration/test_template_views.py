"""Integration tests for ContractTemplateViewSet — template API endpoints."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework import status

from core.models import Apartment, Building, Lease, Tenant


@pytest.fixture
def template_dir(tmp_path, monkeypatch):
    """Create a temporary template directory and patch BASE_DIR."""
    template_path = tmp_path / "core" / "templates"
    template_path.mkdir(parents=True)
    template_file = template_path / "contract_template.html"
    template_file.write_text(
        "<html><body>Test Contract Template</body></html>", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))
    return template_path


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=8801,
        name="Template View Building",
        address="Rua TemplateView, 8801",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=301,
        rental_value=Decimal("1400.00"),
        cleaning_fee=Decimal("180.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="TemplateView Tenant",
        cpf_cnpj="12345678909",  # Valid CPF
        phone="11955550003",
        marital_status="Solteiro(a)",
        profession="Jornalista",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    l = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date="2026-02-01",
        validity_months=12,
        tag_fee=Decimal("50.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    l.tenants.add(tenant)
    return l


@pytest.mark.integration
class TestGetTemplateEndpoint:
    url = "/api/templates/current/"

    def test_returns_200_with_template_content(self, authenticated_api_client, template_dir):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert "content" in response.data
        assert "Test Contract Template" in response.data["content"]

    def test_unauthenticated_returns_401(self, api_client, template_dir):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, template_dir):
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_when_template_missing(self, authenticated_api_client, tmp_path, monkeypatch):
        empty = tmp_path / "notemplate"
        (empty / "core" / "templates").mkdir(parents=True)
        monkeypatch.setattr(settings, "BASE_DIR", str(empty))
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data


@pytest.mark.integration
class TestSaveTemplateEndpoint:
    url = "/api/templates/save/"

    def test_saves_template_and_returns_200(self, authenticated_api_client, template_dir):
        new_content = "<html><body>Updated Template</body></html>"
        response = authenticated_api_client.post(
            self.url, {"content": new_content}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert "backup_filename" in response.data

    def test_missing_content_returns_400(self, authenticated_api_client, template_dir):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_empty_content_returns_400(self, authenticated_api_client, template_dir):
        response = authenticated_api_client.post(
            self.url, {"content": "   "}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client, template_dir):
        response = api_client.post(self.url, {"content": "<html></html>"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, template_dir):
        response = regular_authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_updates_template_file_on_disk(self, authenticated_api_client, template_dir):
        new_content = "<html><body>Disk Updated</body></html>"
        authenticated_api_client.post(self.url, {"content": new_content}, format="json")
        template_file = template_dir / "contract_template.html"
        assert template_file.read_text(encoding="utf-8") == new_content


@pytest.mark.integration
class TestPreviewTemplateEndpoint:
    url = "/api/templates/preview/"

    def test_returns_200_with_rendered_html(
        self, authenticated_api_client, template_dir, lease
    ):
        response = authenticated_api_client.post(
            self.url,
            {"content": "<html><body>Preview {{ lease.id }}</body></html>"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "html" in response.data
        assert str(lease.id) in response.data["html"]

    def test_renders_with_specific_lease_id(
        self, authenticated_api_client, template_dir, lease
    ):
        response = authenticated_api_client.post(
            self.url,
            {
                "content": "<html>{{ lease.id }}</html>",
                "lease_id": lease.id,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert str(lease.id) in response.data["html"]

    def test_missing_content_returns_400(self, authenticated_api_client, template_dir, lease):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_invalid_lease_id_returns_400(
        self, authenticated_api_client, template_dir, lease
    ):
        response = authenticated_api_client.post(
            self.url,
            {"content": "<html></html>", "lease_id": 999999},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_no_leases_returns_400(self, authenticated_api_client, template_dir):
        Lease.objects.all().delete()
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client, template_dir, lease):
        response = api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestListBackupsEndpoint:
    url = "/api/templates/backups/"

    def test_returns_empty_list_when_no_backups(self, authenticated_api_client, template_dir):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_returns_backup_list_after_save(self, authenticated_api_client, template_dir):
        # Create a backup by saving
        authenticated_api_client.post(
            "/api/templates/save/",
            {"content": "<html>v1</html>"},
            format="json",
        )
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 1

    def test_backup_contains_required_fields(self, authenticated_api_client, template_dir):
        authenticated_api_client.post(
            "/api/templates/save/",
            {"content": "<html>v2</html>"},
            format="json",
        )
        response = authenticated_api_client.get(self.url)
        if response.data:
            backup = response.data[0]
            assert "filename" in backup
            assert "size" in backup
            assert "created_at" in backup
            assert "is_default" in backup

    def test_unauthenticated_returns_401(self, api_client, template_dir):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, template_dir):
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestRestoreBackupEndpoint:
    url = "/api/templates/restore/"

    def test_restores_backup_successfully(self, authenticated_api_client, template_dir, tmp_path):
        # Create a backup by saving
        save_response = authenticated_api_client.post(
            "/api/templates/save/",
            {"content": "<html>before restore</html>"},
            format="json",
        )
        backup_filename = save_response.data["backup_filename"]

        response = authenticated_api_client.post(
            self.url, {"backup_filename": backup_filename}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert "safety_backup" in response.data

    def test_missing_backup_filename_returns_400(self, authenticated_api_client, template_dir):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_nonexistent_backup_returns_404(self, authenticated_api_client, template_dir):
        response = authenticated_api_client.post(
            self.url,
            {"backup_filename": "does_not_exist.html"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data

    def test_unauthenticated_returns_401(self, api_client, template_dir):
        response = api_client.post(
            self.url, {"backup_filename": "some_backup.html"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, template_dir):
        response = regular_authenticated_api_client.post(
            self.url, {"backup_filename": "some_backup.html"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Additional error-branch coverage — missing lines 62-70, 110-124, 163-170,
# 199-210, 253-267
# =============================================================================


@pytest.mark.integration
class TestGetTemplatePermissionError:
    url = "/api/templates/current/"

    def test_permission_error_returns_403(self, authenticated_api_client, monkeypatch):
        """Covers lines 62-70: PermissionError branch in get_template."""
        from core.services import TemplateManagementService

        def raise_permission(*args, **kwargs):
            raise PermissionError("no read access")

        monkeypatch.setattr(TemplateManagementService, "get_template", staticmethod(raise_permission))
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permissão" in response.data["error"]

    def test_unexpected_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 68-73: generic Exception branch in get_template."""
        from core.services import TemplateManagementService

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("unexpected")

        monkeypatch.setattr(TemplateManagementService, "get_template", staticmethod(raise_unexpected))
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Erro interno" in response.data["error"]


@pytest.mark.integration
class TestSaveTemplateErrorBranches:
    url = "/api/templates/save/"

    def test_permission_error_returns_403(self, authenticated_api_client, monkeypatch):
        """Covers lines 110-115: PermissionError branch in save_template."""
        from core.services import TemplateManagementService

        def raise_permission(*args, **kwargs):
            raise PermissionError("no write")

        monkeypatch.setattr(TemplateManagementService, "save_template", staticmethod(raise_permission))
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permissão" in response.data["error"]

    def test_os_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 116-120: OSError branch in save_template."""
        from core.services import TemplateManagementService

        def raise_os_error(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(TemplateManagementService, "save_template", staticmethod(raise_os_error))
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "salvar" in response.data["error"]

    def test_unexpected_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 122-127: generic Exception branch in save_template."""
        from core.services import TemplateManagementService

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(TemplateManagementService, "save_template", staticmethod(raise_unexpected))
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_value_error_returns_400(self, authenticated_api_client, monkeypatch):
        """Covers lines 108-109: ValueError branch in save_template."""
        from core.services import TemplateManagementService

        def raise_value_error(*args, **kwargs):
            raise ValueError("invalid content")

        monkeypatch.setattr(TemplateManagementService, "save_template", staticmethod(raise_value_error))
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid content" in response.data["error"]


@pytest.mark.integration
class TestPreviewTemplateErrorBranches:
    url = "/api/templates/preview/"

    def test_object_does_not_exist_returns_404(self, authenticated_api_client, monkeypatch):
        """Covers lines 163-167: ObjectDoesNotExist branch in preview_template."""
        from django.core.exceptions import ObjectDoesNotExist

        from core.services import TemplateManagementService

        def raise_does_not_exist(*args, **kwargs):
            raise ObjectDoesNotExist("lease not found")

        monkeypatch.setattr(
            TemplateManagementService, "preview_template", staticmethod(raise_does_not_exist)
        )
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Locação não encontrada" in response.data["error"]

    def test_unexpected_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 168-173: generic Exception branch in preview_template."""
        from core.services import TemplateManagementService

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("render failure")

        monkeypatch.setattr(
            TemplateManagementService, "preview_template", staticmethod(raise_unexpected)
        )
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.integration
class TestListBackupsErrorBranches:
    url = "/api/templates/backups/"

    def test_file_not_found_returns_empty_list(self, authenticated_api_client, monkeypatch):
        """Covers lines 199-201: FileNotFoundError → returns empty list with 200."""
        from core.services import TemplateManagementService

        def raise_fnf(*args, **kwargs):
            raise FileNotFoundError("backup dir missing")

        monkeypatch.setattr(TemplateManagementService, "list_backups", staticmethod(raise_fnf))
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_permission_error_returns_403(self, authenticated_api_client, monkeypatch):
        """Covers lines 202-207: PermissionError branch in list_backups."""
        from core.services import TemplateManagementService

        def raise_permission(*args, **kwargs):
            raise PermissionError("no list access")

        monkeypatch.setattr(TemplateManagementService, "list_backups", staticmethod(raise_permission))
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permissão" in response.data["error"]

    def test_unexpected_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 208-213: generic Exception branch in list_backups."""
        from core.services import TemplateManagementService

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("unexpected list failure")

        monkeypatch.setattr(TemplateManagementService, "list_backups", staticmethod(raise_unexpected))
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.integration
class TestRestoreBackupErrorBranches:
    url = "/api/templates/restore/"

    def test_permission_error_returns_403(self, authenticated_api_client, monkeypatch):
        """Covers lines 253-257: PermissionError branch in restore_backup."""
        from core.services import TemplateManagementService

        def raise_permission(*args, **kwargs):
            raise PermissionError("no restore access")

        monkeypatch.setattr(
            TemplateManagementService, "restore_backup", staticmethod(raise_permission)
        )
        response = authenticated_api_client.post(
            self.url, {"backup_filename": "backup.html"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permissão" in response.data["error"]

    def test_os_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 258-263: OSError branch in restore_backup."""
        from core.services import TemplateManagementService

        def raise_os_error(*args, **kwargs):
            raise OSError("restore disk error")

        monkeypatch.setattr(
            TemplateManagementService, "restore_backup", staticmethod(raise_os_error)
        )
        response = authenticated_api_client.post(
            self.url, {"backup_filename": "backup.html"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "restaurar" in response.data["error"]

    def test_unexpected_error_returns_500(self, authenticated_api_client, monkeypatch):
        """Covers lines 264-269: generic Exception branch in restore_backup."""
        from core.services import TemplateManagementService

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("unexpected restore failure")

        monkeypatch.setattr(
            TemplateManagementService, "restore_backup", staticmethod(raise_unexpected)
        )
        response = authenticated_api_client.post(
            self.url, {"backup_filename": "backup.html"}, format="json"
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
