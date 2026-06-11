"""Integration tests for ContractTemplateViewSet — DB-backed template API endpoints."""

from decimal import Decimal

import pytest
from rest_framework import status

from core.models import Apartment, Building, ContractTemplate, Lease, Tenant


@pytest.fixture
def active_template(admin_user):
    """Replace the migration-seeded DEFAULT with a small, known active template."""
    ContractTemplate.objects.all().delete()
    return ContractTemplate.objects.create(
        content="<html><body>Test Contract Template {{ lease.id }}</body></html>",
        label="Padrão",
        is_default=True,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


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
    lease_obj = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date="2026-02-01",
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1400.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    lease_obj.tenants.add(tenant)
    return lease_obj


@pytest.mark.integration
class TestGetTemplateEndpoint:
    url = "/api/templates/current/"

    def test_returns_200_with_template_content(self, authenticated_api_client, active_template):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert "content" in response.data
        assert "Test Contract Template" in response.data["content"]

    def test_unauthenticated_returns_401(self, api_client, active_template):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, active_template):
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_when_no_active_template(self, authenticated_api_client):
        ContractTemplate.objects.all().delete()
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data


@pytest.mark.integration
class TestSaveTemplateEndpoint:
    url = "/api/templates/save/"

    def test_saves_template_and_returns_200(self, authenticated_api_client, active_template):
        new_content = "<html><body>Updated Template {{ lease.id }}</body></html>"
        response = authenticated_api_client.post(self.url, {"content": new_content}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert "version_id" in response.data

    def test_missing_content_returns_400(self, authenticated_api_client, active_template):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_empty_content_returns_400(self, authenticated_api_client, active_template):
        response = authenticated_api_client.post(self.url, {"content": "   "}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client, active_template):
        response = api_client.post(self.url, {"content": "<html></html>"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, active_template):
        response = regular_authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_creates_new_active_version_in_db(self, authenticated_api_client, active_template):
        new_content = "<html><body>DB Updated {{ lease.id }}</body></html>"
        authenticated_api_client.post(self.url, {"content": new_content}, format="json")
        assert ContractTemplate.get_active_content() == new_content
        # The previous default version is deactivated but still present (backup).
        active_template.refresh_from_db()
        assert active_template.is_active is False
        assert ContractTemplate.objects.filter(is_active=True).count() == 1


@pytest.mark.integration
class TestPreviewTemplateEndpoint:
    url = "/api/templates/preview/"

    def test_returns_200_with_rendered_html(
        self, authenticated_api_client, active_template, lease, active_landlord
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
        self, authenticated_api_client, active_template, lease, active_landlord
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

    def test_missing_content_returns_400(self, authenticated_api_client, active_template, lease):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_invalid_lease_id_returns_400(self, authenticated_api_client, active_template, lease):
        response = authenticated_api_client.post(
            self.url,
            {"content": "<html></html>", "lease_id": 999999},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_no_leases_returns_400(self, authenticated_api_client, active_template):
        Lease.objects.all().delete()
        response = authenticated_api_client.post(
            self.url, {"content": "<html></html>"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client, active_template, lease):
        response = api_client.post(self.url, {"content": "<html></html>"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestListBackupsEndpoint:
    url = "/api/templates/backups/"

    def test_returns_default_version(self, authenticated_api_client, active_template):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 1
        assert response.data[0]["is_default"] is True

    def test_returns_version_list_after_save(self, authenticated_api_client, active_template):
        authenticated_api_client.post(
            "/api/templates/save/",
            {"content": "<html>v1 {{ lease.id }}</html>"},
            format="json",
        )
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        # default + saved version
        assert len(response.data) == 2

    def test_version_contains_required_fields(self, authenticated_api_client, active_template):
        authenticated_api_client.post(
            "/api/templates/save/",
            {"content": "<html>v2 {{ lease.id }}</html>"},
            format="json",
        )
        response = authenticated_api_client.get(self.url)
        backup = response.data[0]
        assert "id" in backup
        assert "label" in backup
        assert "created_at" in backup
        assert "is_default" in backup
        assert "is_active" in backup
        # The filesystem shape must be gone.
        assert "filename" not in backup
        assert "path" not in backup
        assert "size" not in backup

    def test_unauthenticated_returns_401(self, api_client, active_template):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, active_template):
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestRestoreBackupEndpoint:
    url = "/api/templates/restore/"

    def test_restores_version_by_id(self, authenticated_api_client, active_template):
        original_content = active_template.content
        # Save a new active version, then restore the default by its id.
        authenticated_api_client.post(
            "/api/templates/save/",
            {"content": "<html>after change {{ lease.id }}</html>"},
            format="json",
        )

        response = authenticated_api_client.post(
            self.url, {"version_id": active_template.pk}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        assert response.data["version_id"] == active_template.pk
        assert ContractTemplate.get_active_content() == original_content

    def test_missing_version_id_returns_400(self, authenticated_api_client, active_template):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_non_integer_version_id_returns_400(self, authenticated_api_client, active_template):
        response = authenticated_api_client.post(
            self.url, {"version_id": "not-a-number"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_nonexistent_version_returns_404(self, authenticated_api_client, active_template):
        response = authenticated_api_client.post(self.url, {"version_id": 999999}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data

    def test_unauthenticated_returns_401(self, api_client, active_template):
        response = api_client.post(self.url, {"version_id": 1}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, active_template):
        response = regular_authenticated_api_client.post(self.url, {"version_id": 1}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Security regressions — SSTI sandbox, save validation, restore by integer id
# =============================================================================


@pytest.mark.integration
class TestRestoreNoPathTraversal:
    """restore takes an integer version_id; no filesystem path can be supplied."""

    url = "/api/templates/restore/"

    def test_traversal_string_rejected_as_non_integer(
        self, authenticated_api_client, active_template
    ):
        """A path-traversal style string is rejected as a non-integer (400), and the active
        template is unchanged — there is no filesystem restore surface anymore."""
        original = ContractTemplate.get_active_content()
        response = authenticated_api_client.post(
            self.url, {"version_id": "../../.env"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert ContractTemplate.get_active_content() == original


@pytest.mark.integration
class TestSaveInvalidTemplate:
    url = "/api/templates/save/"

    def test_save_invalid_template_returns_400_and_keeps_current(
        self, authenticated_api_client, active_template
    ):
        """Invalid Jinja returns 400 and leaves the active template intact (so PDF
        generation stays available)."""
        original = ContractTemplate.get_active_content()

        response = authenticated_api_client.post(
            self.url, {"content": "<html>{% if %}</html>"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert ContractTemplate.get_active_content() == original


@pytest.mark.integration
class TestPreviewSSTI:
    url = "/api/templates/preview/"

    def test_preview_ssti_payload_does_not_execute(
        self, authenticated_api_client, active_template, lease, active_landlord
    ):
        """An SSTI payload is blocked by the sandbox: the view returns a 5xx error envelope
        without leaking subclass internals (the gadget never executes)."""
        payload = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
        response = authenticated_api_client.post(
            self.url, {"content": payload, "lease_id": lease.id}, format="json"
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "html" not in response.data
        assert "subclasses" not in str(response.data)
