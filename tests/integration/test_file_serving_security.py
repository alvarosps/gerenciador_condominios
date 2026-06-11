"""Security regression tests: no filesystem path leakage and no anonymous static serving in prod.

- generate_contract / task_status responses must never expose the on-disk PDF path.
- The ^contracts/ and ^media/ static routes must only exist in DEBUG (removed in production).
"""

import importlib
from datetime import date
from decimal import Decimal

import pytest
from django.test import override_settings
from django.urls import Resolver404, clear_url_caches, resolve
from rest_framework import status

from core.models import Landlord
from tests.factories import make_apartment, make_building, make_lease, make_tenant


@pytest.fixture
def building(admin_user):
    return make_building(
        street_number=6100,
        user=admin_user,
        name="Edifício Segurança",
        address="Rua Segurança, 6100",
    )


@pytest.fixture
def apartment(building, admin_user):
    return make_apartment(
        building=building,
        number=101,
        user=admin_user,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
    )


@pytest.fixture
def tenant(admin_user):
    return make_tenant(
        cpf_cnpj="52998224725",
        user=admin_user,
        name="Inquilino Segurança",
        phone="11999990001",
        due_day=10,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    created = make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
    )
    created.tenants.add(tenant)
    return created


@pytest.fixture
def landlord(admin_user):
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


@pytest.mark.integration
@pytest.mark.django_db
class TestNoPathLeakage:
    def test_generate_contract_response_nao_contem_pdf_path(
        self, authenticated_api_client, lease, landlord, mock_pdf_generation
    ):
        url = f"/api/leases/{lease.pk}/generate_contract/"
        response = authenticated_api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert "pdf_path" not in response.data
        assert response.data["lease_id"] == lease.pk
        assert "message" in response.data

    def test_task_status_nao_expoe_caminho_filesystem(self, authenticated_api_client, mocker):
        """A SUCCESSFUL contract task returns the on-disk PDF path; task_status must not surface it.

        Celery's result backend is an external system (Redis in prod, disabled in tests), so it is
        the one boundary stubbed here — the view's payload-shaping logic runs unmocked.
        """

        class _FakeResult:
            status = "SUCCESS"
            result = "/opt/render/project/contracts/836/contract_apto_101_1.pdf"

            def ready(self) -> bool:
                return True

            def successful(self) -> bool:
                return True

        mocker.patch("celery.result.AsyncResult", return_value=_FakeResult())

        response = authenticated_api_client.get("/api/tasks/some-task-id/status/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "SUCCESS"
        body = str(response.data)
        assert "contracts/" not in body
        assert "/opt/" not in body
        assert "contract_apto" not in body
        assert "result" not in response.data
        assert "pdf_path" not in response.data


def _reload_root_urlconf():
    """Reload the root URLConf so module-level ``if settings.DEBUG`` branches re-evaluate."""
    import condominios_manager.urls as root_urls

    clear_url_caches()
    importlib.reload(root_urls)


@pytest.mark.integration
class TestStaticRoutesDebugGated:
    def test_contracts_static_route_ausente_quando_debug_false(self):
        with override_settings(DEBUG=False):
            _reload_root_urlconf()
            try:
                with pytest.raises(Resolver404):
                    resolve("/contracts/836/contract_apto_101_1.pdf")
                with pytest.raises(Resolver404):
                    resolve("/media/payment_proofs/2026/03/p.png")
            finally:
                _reload_root_urlconf()

    def test_contracts_static_route_presente_em_debug(self):
        with override_settings(DEBUG=True):
            _reload_root_urlconf()
            try:
                match = resolve("/contracts/836/contract_apto_101_1.pdf")
                assert match is not None
            finally:
                _reload_root_urlconf()
