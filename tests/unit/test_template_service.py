"""Unit tests for core/services/template_management_service.py (DB-backed)."""

from decimal import Decimal

import pytest

from core.models import Apartment, Building, ContractTemplate, Lease, Tenant
from core.services.template_management_service import TemplateManagementService


@pytest.fixture
def default_template(admin_user):
    """Replace the migration-seeded DEFAULT with a small, known active template."""
    ContractTemplate.objects.all().delete()
    return ContractTemplate.objects.create(
        content="<html><body>Test template {{ tenant }}</body></html>",
        label="Padrão",
        is_default=True,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


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
    lease_obj = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date="2026-01-01",
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1200.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    lease_obj.tenants.add(tenant)
    return lease_obj


@pytest.mark.unit
class TestGetTemplate:
    def test_returns_active_template_content(self, default_template):
        content = TemplateManagementService.get_template()
        assert "Test template" in content

    def test_raises_when_no_active_template(self, default_template):
        ContractTemplate.objects.all().delete()
        with pytest.raises(ContractTemplate.DoesNotExist):
            TemplateManagementService.get_template()


@pytest.mark.unit
class TestSaveTemplate:
    def test_saves_new_active_version(self, default_template, admin_user):
        new_content = "<html><body>New Template {{ tenant }}</body></html>"
        result = TemplateManagementService.save_template(new_content, user=admin_user)

        assert "message" in result
        assert "version_id" in result
        assert "label" in result
        assert TemplateManagementService.get_template() == new_content

    def test_previous_version_deactivated(self, default_template, admin_user):
        TemplateManagementService.save_template("<html>{{ tenant }}</html>", user=admin_user)
        default_template.refresh_from_db()
        assert default_template.is_active is False

    def test_raises_value_error_on_empty_content(self, default_template, admin_user):
        with pytest.raises(ValueError, match="vazio"):
            TemplateManagementService.save_template("", user=admin_user)

    def test_raises_value_error_on_whitespace_only(self, default_template, admin_user):
        with pytest.raises(ValueError, match="vazio"):
            TemplateManagementService.save_template("   \n\t  ", user=admin_user)

    def test_invalid_jinja_rejected_and_active_unchanged(self, default_template, admin_user):
        original = TemplateManagementService.get_template()

        with pytest.raises(ValueError, match="Template inválido"):
            TemplateManagementService.save_template("<html>{% if %}</html>", user=admin_user)

        assert TemplateManagementService.get_template() == original

    def test_invalid_jinja_creates_no_version(self, default_template, admin_user):
        before = ContractTemplate.objects.count()
        with pytest.raises(ValueError, match="Template inválido"):
            TemplateManagementService.save_template("<html>{% for x %}</html>", user=admin_user)
        assert ContractTemplate.objects.count() == before


@pytest.mark.unit
class TestListBackups:
    def test_returns_version_info_dicts(self, default_template, admin_user):
        TemplateManagementService.save_template("<html>v1 {{ tenant }}</html>", user=admin_user)
        backups = TemplateManagementService.list_backups()

        assert len(backups) >= 1
        backup = backups[0]
        assert "id" in backup
        assert "label" in backup
        assert "created_at" in backup
        assert "is_default" in backup
        assert "is_active" in backup
        # New shape no longer leaks filesystem details.
        assert "filename" not in backup
        assert "path" not in backup
        assert "size" not in backup

    def test_default_listed_first(self, default_template, admin_user):
        TemplateManagementService.save_template("<html>new {{ tenant }}</html>", user=admin_user)
        backups = TemplateManagementService.list_backups()
        assert backups[0]["is_default"] is True

    def test_includes_default_and_saved_versions(self, default_template, admin_user):
        TemplateManagementService.save_template("<html>v1 {{ tenant }}</html>", user=admin_user)
        TemplateManagementService.save_template("<html>v2 {{ tenant }}</html>", user=admin_user)
        backups = TemplateManagementService.list_backups()
        # default + 2 saved versions
        assert len(backups) == 3


@pytest.mark.unit
class TestRestoreBackup:
    def test_restores_version_by_id(self, default_template, admin_user):
        original_content = default_template.content
        TemplateManagementService.save_template(
            "<html>Modified {{ tenant }}</html>", user=admin_user
        )

        result = TemplateManagementService.restore_backup(default_template.pk, user=admin_user)

        assert "message" in result
        assert result["version_id"] == default_template.pk
        assert TemplateManagementService.get_template() == original_content

    def test_raises_when_version_not_found(self, default_template, admin_user):
        with pytest.raises(ContractTemplate.DoesNotExist):
            TemplateManagementService.restore_backup(999999, user=admin_user)


@pytest.mark.unit
class TestPreviewTemplate:
    def test_raises_when_no_leases_exist(self, default_template):
        Lease.objects.all().delete()
        with pytest.raises(ValueError, match="Nenhuma locação"):
            TemplateManagementService.preview_template("<html>{{ tenant }}</html>")

    def test_raises_when_lease_id_not_found(self, default_template, lease):
        with pytest.raises(ValueError, match="não encontrada"):
            TemplateManagementService.preview_template("<html>{{ tenant }}</html>", lease_id=999999)

    def test_renders_template_with_lease_data(self, default_template, lease, active_landlord):
        html_content = TemplateManagementService.preview_template(
            "<html><body>Contract for lease {{ lease.id }}</body></html>"
        )
        assert isinstance(html_content, str)
        assert str(lease.id) in html_content

    def test_renders_template_with_specific_lease_id(
        self, default_template, lease, active_landlord
    ):
        html_content = TemplateManagementService.preview_template(
            "<html><body>{{ lease.id }}</body></html>",
            lease_id=lease.id,
        )
        assert str(lease.id) in html_content


@pytest.mark.unit
class TestPreviewTemplateSecurity:
    """preview_template runs inside the SandboxedEnvironment with StrictUndefined."""

    def test_preview_rejects_ssti_payload(self, default_template, lease, active_landlord):
        """The classic SSTI/RCE gadget must be blocked by the sandbox (not executed)."""
        from jinja2.exceptions import SecurityError

        payload = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
        with pytest.raises(SecurityError):
            TemplateManagementService.preview_template(payload, lease_id=lease.id)

    def test_preview_rejects_dunder_access(self, default_template, lease, active_landlord):
        from jinja2.exceptions import SecurityError

        with pytest.raises(SecurityError):
            TemplateManagementService.preview_template("{{ ''.__class__ }}", lease_id=lease.id)

    def test_preview_renders_valid_template(self, default_template, lease, active_landlord):
        html_content = TemplateManagementService.preview_template(
            "<html>{{ tenant.name }}</html>", lease_id=lease.id
        )
        assert lease.responsible_tenant.name in html_content

    def test_preview_strict_undefined_raises_on_unknown_var(
        self, default_template, lease, active_landlord
    ):
        from jinja2.exceptions import UndefinedError

        with pytest.raises(UndefinedError):
            TemplateManagementService.preview_template(
                "<html>{{ variavel_que_nao_existe }}</html>", lease_id=lease.id
            )
