"""
Unit tests for BaseService generic CRUD operations.

Tests all standard CRUD methods provided by the base service class
using a concrete implementation with the Tenant model.
"""

import logging

import pytest

from core.models import Tenant
from core.services.base import BaseService


# Create a concrete service for testing
class TenantTestService(BaseService[Tenant]):
    """Concrete service implementation for testing BaseService."""

    model = Tenant


@pytest.fixture
def service():
    """Create a TenantTestService instance."""
    return TenantTestService()


@pytest.fixture
def sample_tenant(db):
    """Create a sample tenant for testing."""
    return Tenant.objects.create(
        name="John Doe",
        cpf_cnpj="529.982.247-25",  # Valid CPF with proper format
        phone="11999999999",
        marital_status="Casado(a)",
        profession="Engineer",
        is_company=False,
    )


# Valid CPFs for testing (pass Receita Federal checksum validation)
VALID_CPFS = [
    "529.982.247-25",  # Verified valid checksum
    "987.654.321-00",  # Verified valid checksum
    "111.222.333-96",  # Verified valid checksum
]


@pytest.fixture
def multiple_tenants(db):
    """Create multiple tenants for testing list operations."""
    tenants = []
    for i in range(3):
        tenant = Tenant.objects.create(
            name=f"Tenant {i+1}",
            cpf_cnpj=VALID_CPFS[i],  # Use valid CPFs
            phone=f"1199999999{i}",
            marital_status="Solteiro(a)",
            profession=f"Profession {i+1}",
            is_company=False,
        )
        tenants.append(tenant)
    return tenants


@pytest.mark.django_db
class TestBaseServiceInit:
    """Test BaseService initialization."""

    def test_init_creates_logger(self, service):
        """Test that initialization creates a logger with correct name."""
        assert hasattr(service, "logger")
        assert isinstance(service.logger, logging.Logger)
        assert service.logger.name == "TenantTestService"


@pytest.mark.django_db
class TestGetQueryset:
    """Test get_queryset method."""

    def test_get_queryset_returns_all_objects(self, service, multiple_tenants):
        """Test that get_queryset returns all objects."""
        queryset = service.get_queryset()

        assert queryset.count() == 3
        assert queryset.model == Tenant


@pytest.mark.django_db
class TestGetById:
    """Test get_by_id method."""

    def test_get_by_id_existing(self, service, sample_tenant):
        """Test retrieving an existing object by ID."""
        result = service.get_by_id(sample_tenant.id)

        assert result is not None
        assert result.id == sample_tenant.id
        assert result.name == "John Doe"

    def test_get_by_id_non_existing(self, service, sample_tenant):
        """Test retrieving a non-existent object returns None."""
        result = service.get_by_id(99999)

        assert result is None

    def test_get_by_id_logs_success(self, service, sample_tenant, caplog):
        """Test that successful retrieval logs debug message."""
        with caplog.at_level(logging.DEBUG):
            service.get_by_id(sample_tenant.id)

        assert f"Retrieved Tenant with id {sample_tenant.id}" in caplog.text

    def test_get_by_id_logs_failure(self, service, caplog):
        """Test that failed retrieval logs warning message."""
        with caplog.at_level(logging.WARNING):
            service.get_by_id(99999)

        assert "Tenant with id 99999 not found" in caplog.text


@pytest.mark.django_db
class TestGetAll:
    """Test get_all method."""

    def test_get_all_multiple_objects(self, service, multiple_tenants):
        """Test retrieving all objects."""
        result = service.get_all()

        assert len(result) == 3
        assert all(isinstance(obj, Tenant) for obj in result)

    def test_get_all_empty(self, service):
        """Test retrieving all objects when none exist."""
        result = service.get_all()

        assert result == []

    def test_get_all_logs_debug(self, service, multiple_tenants, caplog):
        """Test that get_all logs debug message with count."""
        with caplog.at_level(logging.DEBUG):
            service.get_all()

        assert "Retrieved 3 Tenant instances" in caplog.text


@pytest.mark.django_db
class TestCreate:
    """Test create method."""

    def test_create_new_object(self, service):
        """Test creating a new object."""
        result = service.create(
            name="New Tenant",
            cpf_cnpj="123.456.780-62",  # Valid CPF with checksum
            phone="11888888888",
            marital_status="Solteiro(a)",
            profession="Doctor",
            is_company=False,
        )

        assert result.id is not None
        assert result.name == "New Tenant"
        assert result.cpf_cnpj == "123.456.780-62"

        # Verify it was saved to database
        assert Tenant.objects.filter(id=result.id).exists()

    def test_create_logs_info(self, service, caplog):
        """Test that create logs info message."""
        with caplog.at_level(logging.INFO):
            result = service.create(
                name="Test",
                cpf_cnpj="111.444.777-35",  # Valid CPF (from docs example)
                phone="11999999999",
                marital_status="Solteiro(a)",
                profession="Test",
                is_company=False,
            )

        assert f"Created Tenant with id {result.id}" in caplog.text


@pytest.mark.django_db
class TestUpdate:
    """Test update method."""

    def test_update_object(self, service, sample_tenant):
        """Test updating an existing object."""
        result = service.update(sample_tenant, name="Updated Name", phone="11777777777")

        assert result.id == sample_tenant.id
        assert result.name == "Updated Name"
        assert result.phone == "11777777777"

        # Verify changes were saved
        sample_tenant.refresh_from_db()
        assert sample_tenant.name == "Updated Name"

    def test_update_single_field(self, service, sample_tenant):
        """Test updating only one field."""
        original_name = sample_tenant.name

        result = service.update(sample_tenant, phone="11666666666")

        assert result.name == original_name
        assert result.phone == "11666666666"

    def test_update_logs_info(self, service, sample_tenant, caplog):
        """Test that update logs info message."""
        with caplog.at_level(logging.INFO):
            service.update(sample_tenant, name="Changed")

        assert f"Updated Tenant with id {sample_tenant.id}" in caplog.text


@pytest.mark.django_db
class TestDelete:
    """Test delete method."""

    def test_delete_object(self, service, sample_tenant):
        """Test deleting an object."""
        tenant_id = sample_tenant.id

        service.delete(sample_tenant)

        # Verify object was deleted
        assert not Tenant.objects.filter(id=tenant_id).exists()

    def test_delete_logs_info(self, service, sample_tenant, caplog):
        """Test that delete logs info message."""
        tenant_id = sample_tenant.id

        with caplog.at_level(logging.INFO):
            service.delete(sample_tenant)

        assert f"Deleted Tenant with id {tenant_id}" in caplog.text


@pytest.mark.django_db
class TestExists:
    """Test exists method."""

    def test_exists_true(self, service, sample_tenant):
        """Test that exists returns True for existing object."""
        result = service.exists(sample_tenant.id)

        assert result is True

    def test_exists_false(self, service):
        """Test that exists returns False for non-existing object."""
        result = service.exists(99999)

        assert result is False

    def test_exists_logs_debug(self, service, sample_tenant, caplog):
        """Test that exists logs debug message."""
        with caplog.at_level(logging.DEBUG):
            service.exists(sample_tenant.id)

        assert f"Tenant with id {sample_tenant.id} exists: True" in caplog.text


@pytest.mark.django_db
class TestCount:
    """Test count method."""

    def test_count_multiple_objects(self, service, multiple_tenants):
        """Test counting multiple objects."""
        result = service.count()

        assert result == 3

    def test_count_zero(self, service):
        """Test counting when no objects exist."""
        result = service.count()

        assert result == 0

    def test_count_logs_debug(self, service, multiple_tenants, caplog):
        """Test that count logs debug message."""
        with caplog.at_level(logging.DEBUG):
            service.count()

        assert "Total Tenant count: 3" in caplog.text


@pytest.mark.django_db
class TestFilter:
    """Test filter method."""

    def test_filter_by_single_field(self, service, multiple_tenants):
        """Test filtering by a single field."""
        # Update one tenant to have different profession
        multiple_tenants[0].profession = "Unique Profession"
        multiple_tenants[0].save()

        result = service.filter(profession="Unique Profession")

        assert len(result) == 1
        assert result[0].profession == "Unique Profession"

    def test_filter_by_multiple_fields(self, service, multiple_tenants):
        """Test filtering by multiple fields."""
        result = service.filter(marital_status="Solteiro(a)", is_company=False)

        assert len(result) == 3
        assert all(t.marital_status == "Solteiro(a)" for t in result)

    def test_filter_no_matches(self, service, multiple_tenants):
        """Test filtering with no matching objects."""
        result = service.filter(profession="Non-existent")

        assert result == []

    def test_filter_logs_debug(self, service, multiple_tenants, caplog):
        """Test that filter logs debug message."""
        with caplog.at_level(logging.DEBUG):
            service.filter(is_company=False)

        assert "Filtered 3 Tenant instances" in caplog.text
        assert "is_company" in caplog.text


@pytest.mark.django_db
class TestBaseServiceIntegration:
    """Integration tests for BaseService complete workflows."""

    def test_full_crud_workflow(self, service):
        """Test complete create-read-update-delete workflow."""
        # Create
        tenant = service.create(
            name="Workflow Test",
            cpf_cnpj="222.333.444-05",  # Valid CPF with checksum
            phone="11555555555",
            marital_status="Casado(a)",
            profession="Tester",
            is_company=False,
        )
        assert tenant.id is not None

        # Read
        retrieved = service.get_by_id(tenant.id)
        assert retrieved is not None
        assert retrieved.name == "Workflow Test"

        # Update
        updated = service.update(retrieved, name="Updated Workflow")
        assert updated.name == "Updated Workflow"

        # Delete
        service.delete(updated)
        assert not service.exists(tenant.id)

    def test_filter_and_count_consistency(self, service, multiple_tenants):
        """Test that filter and count return consistent results."""
        filter_result = service.filter(is_company=False)
        count_result = service.count()

        assert len(filter_result) == count_result

    def test_get_all_and_filter_consistency(self, service, multiple_tenants):
        """Test that get_all and filter with no params are consistent."""
        all_objects = service.get_all()
        filtered_objects = service.filter()  # No filters = all objects

        assert len(all_objects) == len(filtered_objects)
