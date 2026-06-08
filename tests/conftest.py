"""
Global pytest configuration and fixtures

This module provides shared fixtures and configuration for all tests.
"""

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from freezegun import freeze_time as _freeze_time
from model_bakery import baker
from rest_framework.test import APIClient

from tests.constants import TEST_PASSWORD
from tests.factories import make_apartment, make_building, make_person

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


@pytest.fixture(scope="session", autouse=True)
def _pin_throttle_timer_to_real_clock():
    """Keep DRF throttling's clock immune to freezegun.

    ``SimpleRateThrottle.timer = time.time`` is captured when ``rest_framework.throttling`` is first
    imported. If that first import happens inside a ``freeze_time`` test, ``timer`` captures
    freezegun's ``fake_time`` — a plain function, so accessing ``self.timer`` binds ``self`` and
    ``allow_request`` raises ``TypeError: fake_time() takes 0 positional arguments but 1 was given``.
    Pinning ``timer`` to a ``staticmethod`` wrapping the real ``time.time`` once at session start
    (before any freeze) makes throttling use the real wall clock regardless of import order.
    """
    import time

    from rest_framework.throttling import SimpleRateThrottle

    SimpleRateThrottle.timer = staticmethod(time.time)


@pytest.fixture(autouse=True)
def _clear_caches_between_tests():
    """Clear all in-memory (locmem) caches before each test to prevent cross-test pollution.

    LocMemCache keeps a per-LOCATION global store that is NOT rolled back like the database,
    so cached values (e.g. @cache_result results, or @override_settings(CACHES=...) backends)
    leak between tests unless explicitly cleared. Each LocMemCache instance captures a
    reference to its inner store dict at init, so we must clear those dicts in place (clearing
    the outer registry would orphan but not empty them).
    """
    from django.core.cache.backends import locmem

    for store in locmem._caches.values():
        store.clear()
    for store in locmem._expire_info.values():
        store.clear()


@pytest.fixture(autouse=True)
def _isolate_media_root(tmp_path, settings):
    """Redirect MEDIA_ROOT to a per-test temp dir so file uploads never pollute the repo.

    ``settings.MEDIA_ROOT`` defaults to ``BASE_DIR / "contracts"`` and ``PaymentProof.file`` (plus
    any other ``FileField``) uploads under it. Without this, every test that saves an uploaded file
    writes a real artifact into the repo's ``contracts/payment_proofs/`` directory (which is not
    git-ignored). A tmp dir keeps the working tree clean and the upload auto-cleaned. The ``settings``
    param is pytest-django's wrapper, so the assignment fires ``setting_changed`` (the file storage
    picks up the new location) and is reverted after the test.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture(autouse=True)
def _restore_signal_receivers():
    """Restore the process-global Django signal registry after every test.

    Signal connect/disconnect mutates a PROCESS-GLOBAL receiver list that the per-test DB rollback
    does NOT undo. A test that disconnects a receiver and fails to fully reconnect (e.g.
    core.signals.disconnect_all_signals, whose paired connect must restore the Lease ->
    Apartment.is_rented sync) would silently break EVERY later test in the same xdist worker —
    order-dependent flakiness that only surfaces under `-n` parallel scheduling. Snapshotting and
    restoring the receiver lists here makes that whole class of cross-test pollution impossible.
    """
    from django.db.models.signals import (
        m2m_changed,
        post_delete,
        post_save,
        pre_delete,
        pre_save,
    )

    tracked = (pre_save, post_save, pre_delete, post_delete, m2m_changed)
    saved = {signal: list(signal.receivers) for signal in tracked}
    yield
    for signal in tracked:
        if list(signal.receivers) != saved[signal]:
            with signal.lock:
                signal.receivers = saved[signal]
                signal.sender_receivers_cache.clear()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for test session.
    Runs migrations and prepares test database.
    """
    with django_db_blocker.unblock():
        # Run migrations
        call_command("migrate", "--noinput")
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
        password=TEST_PASSWORD,
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )


@pytest.fixture
def active_landlord(admin_user):
    """An active Landlord — required by ContractService.prepare_contract_context (and therefore by
    contract generation AND template preview). Tests that render a contract/preview need this."""
    from core.models import Landlord

    return Landlord.objects.create(
        name="Locador Teste",
        marital_status="Casado(a)",
        cpf_cnpj="12345678901",
        phone="11999990000",
        street="Rua Locador",
        street_number="100",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        zip_code="01310-100",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def regular_user(django_user_model):
    """
    Creates a test regular user without admin privileges.
    """
    return django_user_model.objects.create_user(
        username="user",
        email="user@test.com",
        password=TEST_PASSWORD,
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
    Mocks the external boundaries of contract PDF generation so tests never launch Chrome or
    write to the real contracts directory.

    The contract task runs ``ContractService().generate_contract_with_infrastructure``, which
    renders the PDF via ``PlaywrightPDFGenerator`` (headless Chrome — external) and persists it via
    ``FileSystemDocumentStorage`` (filesystem — external). Only those two boundaries are mocked, at
    the class level so the cached default singletons are covered too. The real orchestration —
    context preparation, template rendering and the lease status update — runs unmocked.

    Usage:
        def test_generate_contract(mock_pdf_generation):
            response = client.post(f'/api/leases/{lease.id}/generate_contract/')
            assert response.status_code == 200
    """

    def fake_render_pdf(output_path, **_kwargs):
        Path(output_path).write_bytes(b"%PDF-1.4\n%mock contract\n")

    def fake_save(file_path, **_kwargs):
        # Mirror FileSystemDocumentStorage.save: the returned path embeds the relative path
        # (building/apartment/lease ids), which some callers assert on.
        return f"contracts/{file_path}"

    mocker.patch(
        "core.infrastructure.pdf_generator.PlaywrightPDFGenerator.generate_pdf",
        side_effect=fake_render_pdf,
    )
    return mocker.patch(
        "core.infrastructure.storage.FileSystemDocumentStorage.save",
        side_effect=fake_save,
    )


@pytest.fixture
def sample_building_data() -> dict[str, Any]:
    """
    Provides sample building data for tests.

    Returns:
        Dict containing valid building data
    """
    return {
        "street_number": 836,
        "name": "Edifício Teste",
        "address": "Rua Teste, 836 - Bairro Teste",
    }


@pytest.fixture
def sample_apartment_data() -> dict[str, Any]:
    """
    Provides sample apartment data for tests.
    Note: Requires a building_id to be added.

    Returns:
        Dict containing valid apartment data
    """
    return {
        "number": 101,
        "rental_value": Decimal("1500.00"),
        "cleaning_fee": Decimal("200.00"),
        "max_tenants": 2,
        "is_rented": False,
        "last_rent_increase_date": None,
    }


@pytest.fixture
def sample_furniture_data() -> dict[str, Any]:
    """
    Provides sample furniture data for tests.

    Returns:
        Dict containing valid furniture data
    """
    return {"name": "Geladeira", "description": "Geladeira Frost Free 300L"}


@pytest.fixture
def sample_tenant_data() -> dict[str, Any]:
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
        "due_day": 10,
        "warning_count": 0,
    }


@pytest.fixture
def sample_dependent_data() -> dict[str, Any]:
    """
    Provides sample dependent data for tests.

    Returns:
        Dict containing valid dependent data
    """
    return {"name": "Maria da Silva", "phone": "(11) 91234-5678"}


@pytest.fixture
def sample_lease_data() -> dict[str, Any]:
    """
    Provides sample lease data for tests.
    Note: Requires apartment_id, responsible_tenant_id, and tenant_ids.

    Returns:
        Dict containing valid lease data
    """
    return {
        "start_date": date.today(),
        "validity_months": 12,
        "tag_fee": Decimal("80.00"),
        "rental_value": Decimal("1500.00"),
        "deposit_amount": None,
        "cleaning_fee_paid": False,
        "tag_deposit_paid": False,
        "contract_generated": False,
        "contract_signed": False,
        "interfone_configured": False,
        "number_of_tenants": 1,
    }


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
    config.addinivalue_line(
        "markers", "infrastructure: Infrastructure abstraction tests (PDF generators, storage)"
    )


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


@pytest.fixture
def building_with_apartment(admin_user, sample_building_data, sample_apartment_data):
    """Pre-built building + apartment for integration tests."""

    building = make_building(user=admin_user, **sample_building_data)
    apartment = make_apartment(
        building=building,
        number=sample_apartment_data["number"],
        user=admin_user,
        **{k: v for k, v in sample_apartment_data.items() if k != "number"},
    )
    return building, apartment


@pytest.fixture
def person_with_credit_card(admin_user):
    """Pre-built person + credit card for financial tests."""

    person = make_person(user=admin_user, relationship="Familiar")
    card = baker.make(
        "core.CreditCard",
        person=person,
        nickname="Test Card",
        closing_day=15,
        due_day=22,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )
    return person, card
