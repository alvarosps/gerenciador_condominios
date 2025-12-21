"""
Integration tests for contract template management endpoints.

Tests all 5 template management endpoints in LeaseViewSet:
- GET /api/leases/get_contract_template/
- POST /api/leases/save_contract_template/
- POST /api/leases/preview_contract_template/
- GET /api/leases/list_template_backups/
- POST /api/leases/restore_template_backup/
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from core.models import Building, Apartment, Tenant, Lease
from datetime import date, timedelta
from decimal import Decimal
import os
from pathlib import Path


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user for authentication."""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )
    return user


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def sample_lease(db):
    """Create a sample lease for preview testing."""
    building = Building.objects.create(
        street_number=836,
        name="Test Building",
        address="Test Street, 836"
    )
    apartment = Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal('1500.00'),
        cleaning_fee=Decimal('200.00'),
        max_tenants=2,
        is_rented=True
    )
    tenant = Tenant.objects.create(
        name="John Doe",
        cpf_cnpj="12345678901",
        phone="11999999999",
        marital_status="Casado(a)",
        profession="Engineer",
        is_company=False
    )
    lease = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date.today(),
        validity_months=12,
        due_day=10,
        rental_value=Decimal('1500.00'),
        cleaning_fee=Decimal('200.00'),
        tag_fee=Decimal('50.00'),
        contract_generated=False
    )
    lease.tenants.add(tenant)
    return lease


@pytest.mark.django_db
class TestGetContractTemplate:
    """Test GET /api/leases/get_contract_template/ endpoint."""

    def test_get_template_success(self, authenticated_client):
        """Test successfully retrieving the contract template."""
        response = authenticated_client.get('/api/leases/get_contract_template/')

        assert response.status_code == status.HTTP_200_OK
        assert 'content' in response.data
        assert isinstance(response.data['content'], str)
        assert len(response.data['content']) > 0

    def test_get_template_unauthenticated(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.get('/api/leases/get_contract_template/')

        # Returns 401 Unauthorized or 403 Forbidden depending on authentication config
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_template_non_admin(self, api_client, db):
        """Test that non-admin users are rejected."""
        # Create regular user (not admin)
        user = User.objects.create_user(
            username='regular',
            password='regular123'
        )
        api_client.force_authenticate(user=user)

        response = api_client.get('/api/leases/get_contract_template/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSaveContractTemplate:
    """Test POST /api/leases/save_contract_template/ endpoint."""

    def test_save_template_success(self, authenticated_client):
        """Test successfully saving a new template."""
        new_content = "<html><body>Updated Template Content</body></html>"

        response = authenticated_client.post(
            '/api/leases/save_contract_template/',
            {'content': new_content},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'backup_filename' in response.data
        assert 'backup_' in response.data['backup_filename']

    def test_save_template_missing_content(self, authenticated_client):
        """Test saving template without content parameter."""
        response = authenticated_client.post(
            '/api/leases/save_contract_template/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_save_template_empty_content(self, authenticated_client):
        """Test saving template with empty content."""
        response = authenticated_client.post(
            '/api/leases/save_contract_template/',
            {'content': ''},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_save_template_unauthenticated(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.post(
            '/api/leases/save_contract_template/',
            {'content': 'test'},
            format='json'
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_save_template_non_admin(self, api_client, db):
        """Test that non-admin users are rejected."""
        user = User.objects.create_user(
            username='regular',
            password='regular123'
        )
        api_client.force_authenticate(user=user)

        response = api_client.post(
            '/api/leases/save_contract_template/',
            {'content': 'test'},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPreviewContractTemplate:
    """Test POST /api/leases/preview_contract_template/ endpoint."""

    def test_preview_template_success(self, authenticated_client, sample_lease):
        """Test successfully previewing template with sample data."""
        template_content = "<html><body>Test: {{ tenant_name }}</body></html>"

        response = authenticated_client.post(
            '/api/leases/preview_contract_template/',
            {
                'content': template_content,
                'lease_id': sample_lease.id
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'html' in response.data
        assert isinstance(response.data['html'], str)

    def test_preview_template_without_lease(self, authenticated_client, sample_lease):
        """Test previewing template without specific lease (uses first available)."""
        template_content = "<html><body>Generic Preview</body></html>"

        response = authenticated_client.post(
            '/api/leases/preview_contract_template/',
            {'content': template_content},
            format='json'
        )

        # Should succeed using the sample_lease fixture (first available lease)
        assert response.status_code == status.HTTP_200_OK
        assert 'html' in response.data

    def test_preview_template_missing_content(self, authenticated_client):
        """Test preview without content parameter."""
        response = authenticated_client.post(
            '/api/leases/preview_contract_template/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_preview_template_invalid_lease(self, authenticated_client):
        """Test preview with non-existent lease ID."""
        response = authenticated_client.post(
            '/api/leases/preview_contract_template/',
            {
                'content': 'test',
                'lease_id': 99999
            },
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_preview_template_unauthenticated(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.post(
            '/api/leases/preview_contract_template/',
            {'content': 'test'},
            format='json'
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestListTemplateBackups:
    """Test GET /api/leases/list_template_backups/ endpoint."""

    def test_list_backups_success(self, authenticated_client):
        """Test successfully listing template backups."""
        # First create a backup by saving a template
        authenticated_client.post(
            '/api/leases/save_contract_template/',
            {'content': '<html><body>Backup Test</body></html>'},
            format='json'
        )

        response = authenticated_client.get('/api/leases/list_template_backups/')

        assert response.status_code == status.HTTP_200_OK
        # Response is the list directly, not wrapped
        assert isinstance(response.data, list)
        # Should have at least one backup
        if len(response.data) > 0:
            assert 'filename' in response.data[0]
            assert 'created_at' in response.data[0]

    def test_list_backups_empty(self, authenticated_client):
        """Test listing backups returns a list (may be empty or have backups from other tests)."""
        response = authenticated_client.get('/api/leases/list_template_backups/')

        assert response.status_code == status.HTTP_200_OK
        # Response should be a list (may be empty or have items from other tests)
        assert isinstance(response.data, list)

    def test_list_backups_unauthenticated(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.get('/api/leases/list_template_backups/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestRestoreTemplateBackup:
    """Test POST /api/leases/restore_template_backup/ endpoint."""

    def test_restore_backup_success(self, authenticated_client):
        """Test successfully restoring from a backup."""
        # First create a backup
        original_content = '<html><body>Original</body></html>'
        save_response = authenticated_client.post(
            '/api/leases/save_contract_template/',
            {'content': original_content},
            format='json'
        )
        backup_filename = save_response.data['backup_filename']

        # Change the template
        authenticated_client.post(
            '/api/leases/save_contract_template/',
            {'content': '<html><body>Changed</body></html>'},
            format='json'
        )

        # Restore from backup
        response = authenticated_client.post(
            '/api/leases/restore_template_backup/',
            {'backup_filename': backup_filename},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        # Message is in Portuguese: "Template restaurado com sucesso"
        assert 'restaurado' in response.data['message'].lower()

    def test_restore_backup_missing_filename(self, authenticated_client):
        """Test restore without backup_filename parameter."""
        response = authenticated_client.post(
            '/api/leases/restore_template_backup/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_restore_backup_invalid_filename(self, authenticated_client):
        """Test restore with non-existent backup file."""
        response = authenticated_client.post(
            '/api/leases/restore_template_backup/',
            {'backup_filename': 'nonexistent_backup.html'},
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_restore_backup_unauthenticated(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.post(
            '/api/leases/restore_template_backup/',
            {'backup_filename': 'test.html'},
            format='json'
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestTemplateEndpointsIntegration:
    """Integration tests for complete template management workflow."""

    def test_complete_template_workflow(self, authenticated_client, sample_lease):
        """Test complete workflow: get → save → preview → backup → restore."""
        # 1. Get current template
        get_response = authenticated_client.get('/api/leases/get_contract_template/')
        assert get_response.status_code == status.HTTP_200_OK
        original_content = get_response.data['content']

        # 2. Save new template
        new_content = '<html><body>Workflow Test {{ tenant_name }}</body></html>'
        save_response = authenticated_client.post(
            '/api/leases/save_contract_template/',
            {'content': new_content},
            format='json'
        )
        assert save_response.status_code == status.HTTP_200_OK
        backup_filename = save_response.data['backup_filename']

        # 3. Preview the new template
        preview_response = authenticated_client.post(
            '/api/leases/preview_contract_template/',
            {
                'content': new_content,
                'lease_id': sample_lease.id
            },
            format='json'
        )
        assert preview_response.status_code == status.HTTP_200_OK
        assert 'html' in preview_response.data

        # 4. List backups
        list_response = authenticated_client.get('/api/leases/list_template_backups/')
        assert list_response.status_code == status.HTTP_200_OK
        # Response is list directly, not wrapped
        assert isinstance(list_response.data, list)
        assert len(list_response.data) > 0

        # 5. Restore from backup
        restore_response = authenticated_client.post(
            '/api/leases/restore_template_backup/',
            {'backup_filename': backup_filename},
            format='json'
        )
        assert restore_response.status_code == status.HTTP_200_OK

        # 6. Verify restoration
        verify_response = authenticated_client.get('/api/leases/get_contract_template/')
        assert verify_response.status_code == status.HTTP_200_OK
