"""
Global pytest configuration and fixtures

This module provides shared fixtures and configuration for all tests.
"""

import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict

from django.conf import settings
from django.core.management import call_command
from rest_framework.test import APIClient

import pytest

# Ensure test settings are applied
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condominios_manager.settings")


@pytest.fixture(scope="session", autouse=True)
def configure_test_cache():
    """
    Use in-memory cache for tests instead of Redis.
    This eliminates Redis connection errors and makes tests faster.
    """
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "condominios-test-cache",
        }
    }


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for test session.
    Runs migrations and prepares test database.
    """
    with django_db_blocker.unblock():
        # Run migrations
        call_command("migrate", "--noinput")
    yield
    # Cleanup is handled automatically by pytest-django


@pytest.fixture
def api_client():
    """
    Provides a DRF API client for making requests in tests.

    Usage:
        def test_api_endpoint(api_client):
            response = api_client.get('/api/buildings/')
            assert response.status_code == 200
    """
    return APIClient()


@pytest.fixture
def admin_user(django_user_model):
    """
    Creates a test admin user with staff and superuser privileges.
    """
    return django_user_model.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )


@pytest.fixture
def regular_user(django_user_model):
    """
    Creates a test regular user without admin privileges.
    """
    return django_user_model.objects.create_user(
        username="user",
        email="user@test.com",
        password="testpass123",
        is_staff=False,
        is_superuser=False,
        is_active=True,
    )


@pytest.fixture
def authenticated_api_client(api_client, admin_user):
    """
    Provides an authenticated API client with admin user.
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def regular_authenticated_api_client(api_client, regular_user):
    """
    Provides an authenticated API client with regular user (non-admin).
    """
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    This removes the need to mark each test with @pytest.mark.django_db
    """
    pass


@pytest.fixture
def test_data_dir(tmp_path):
    """
    Provides a temporary directory for test data files.
    Automatically cleaned up after test completion.

    Returns:
        pathlib.Path: Temporary directory path
    """
    return tmp_path


@pytest.fixture
def mock_pdf_output_dir(tmp_path, monkeypatch):
    """
    Creates a temporary directory for PDF output during tests.
    Patches settings.PDF_OUTPUT_DIR to use temporary directory.

    Usage:
        def test_pdf_generation(mock_pdf_output_dir):
            # PDF will be saved to temporary directory
            lease.generate_contract()
    """
    pdf_dir = tmp_path / "test_contracts"
    pdf_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(settings, "PDF_OUTPUT_DIR", str(pdf_dir))
    return pdf_dir


@pytest.fixture
def mock_chrome_path(monkeypatch):
    """
    Mocks the Chrome executable path for tests that don't actually generate PDFs.

    Usage:
        def test_pdf_config(mock_chrome_path):
            assert settings.CHROME_EXECUTABLE_PATH == 'mock_chrome'
    """
    monkeypatch.setattr(settings, "CHROME_EXECUTABLE_PATH", "mock_chrome")


@pytest.fixture
def mock_pdf_generation(mocker, mock_pdf_output_dir):
    """
    Mocks the PDF generation process to avoid actually launching Chrome/pyppeteer.
    This allows the generate_contract code to execute without external dependencies.

    Usage:
        def test_generate_contract(mock_pdf_generation):
            response = client.post('/api/leases/1/generate_contract/')
            assert response.status_code == 200
    """
    # Mock asyncio.run to prevent actual pyppeteer execution
    # The mock will allow the code to run but skip the async PDF generation
    mock_run = mocker.patch("core.views.asyncio.run")
    mock_run.return_value = None  # Simulate successful PDF generation

    return mock_run


@pytest.fixture
def sample_building_data() -> Dict[str, Any]:
    """
    Provides sample building data for tests.

    Returns:
        Dict containing valid building data
    """
    return {"street_number": 836, "name": "Edifício Teste", "address": "Rua Teste, 836 - Bairro Teste"}


@pytest.fixture
def sample_apartment_data() -> Dict[str, Any]:
    """
    Provides sample apartment data for tests.
    Note: Requires a building_id to be added.

    Returns:
        Dict containing valid apartment data
    """
    return {
        "number": 101,
        "interfone_configured": False,
        "contract_generated": False,
        "contract_signed": False,
        "rental_value": Decimal("1500.00"),
        "cleaning_fee": Decimal("200.00"),
        "max_tenants": 2,
        "is_rented": False,
        "lease_date": None,
        "last_rent_increase_date": None,
    }


@pytest.fixture
def sample_furniture_data() -> Dict[str, Any]:
    """
    Provides sample furniture data for tests.

    Returns:
        Dict containing valid furniture data
    """
    return {"name": "Geladeira", "description": "Geladeira Frost Free 300L"}


@pytest.fixture
def sample_tenant_data() -> Dict[str, Any]:
    """
    Provides sample tenant data for tests.

    Returns:
        Dict containing valid tenant data
    """
    return {
        "name": "João da Silva",
        "cpf_cnpj": "529.982.247-25",  # Valid CPF that passes checksum validation
        "is_company": False,
        "rg": "12.345.678-9",
        "phone": "(11) 98765-4321",
        "marital_status": "Casado(a)",
        "profession": "Engenheiro",
        "deposit_amount": Decimal("1500.00"),
        "cleaning_fee_paid": False,
        "tag_deposit_paid": False,
        "rent_due_day": 10,
    }


@pytest.fixture
def sample_dependent_data() -> Dict[str, Any]:
    """
    Provides sample dependent data for tests.

    Returns:
        Dict containing valid dependent data
    """
    return {"name": "Maria da Silva", "phone": "(11) 91234-5678"}


@pytest.fixture
def sample_lease_data() -> Dict[str, Any]:
    """
    Provides sample lease data for tests.
    Note: Requires apartment_id, responsible_tenant_id, and tenant_ids.

    Returns:
        Dict containing valid lease data
    """
    return {
        "start_date": date.today(),
        "validity_months": 12,
        "due_day": 10,
        "rental_value": Decimal("1500.00"),
        "cleaning_fee": Decimal("200.00"),
        "tag_fee": Decimal("80.00"),
        "contract_generated": False,
        "contract_signed": False,
        "interfone_configured": False,
        "warning_count": 0,
        "number_of_tenants": 1,
    }


@pytest.fixture
def cleanup_test_contracts():
    """
    Cleans up any test contract files created during tests.
    Runs after test completion.
    """
    yield
    # Cleanup logic would go here if needed
    # Currently handled by tmp_path fixture


@pytest.fixture
def freeze_time():
    """
    Provides freezegun's freeze_time for time-dependent tests.

    Usage:
        def test_date_calculation(freeze_time):
            with freeze_time('2025-01-15'):
                # Test code here
                pass
    """
    from freezegun import freeze_time as _freeze_time

    return _freeze_time


@pytest.fixture
def settings_override():
    """
    Provides a context manager for temporarily overriding Django settings.

    Usage:
        def test_with_custom_setting(settings_override):
            with settings_override(DEBUG=False):
                # Test code with DEBUG=False
                pass
    """
    from django.test import override_settings

    return override_settings


# Performance fixtures
@pytest.fixture(scope="session")
def django_db_keepdb():
    """
    Keep database between test runs for faster execution.
    Only use for development, not in CI.
    """
    return True


# Marker registration (for better IDE support)
def pytest_configure(config):
    """
    Register custom markers to avoid warnings.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (API, database)")
    config.addinivalue_line("markers", "slow: Slow tests (PDF generation, external services)")
    config.addinivalue_line("markers", "pdf: PDF generation tests (require Chrome/Chromium)")
    config.addinivalue_line("markers", "model: Model layer tests")
    config.addinivalue_line("markers", "serializer: Serializer tests")
    config.addinivalue_line("markers", "view: View/API endpoint tests")
    config.addinivalue_line("markers", "util: Utility function tests")
    config.addinivalue_line("markers", "factory: Factory/fixture tests")
    config.addinivalue_line("markers", "infrastructure: Infrastructure abstraction tests (PDF generators, storage)")


def pytest_collection_modifyitems(config, items):
    """
    Automatically add markers based on test location and name.
    """
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add markers based on test name
        if "model" in item.nodeid.lower():
            item.add_marker(pytest.mark.model)
        if "serializer" in item.nodeid.lower():
            item.add_marker(pytest.mark.serializer)
        if "view" in item.nodeid.lower() or "api" in item.nodeid.lower():
            item.add_marker(pytest.mark.view)
        if "pdf" in item.nodeid.lower():
            item.add_marker(pytest.mark.pdf)
            item.add_marker(pytest.mark.slow)
