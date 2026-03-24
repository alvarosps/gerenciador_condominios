"""Integration tests for Tenant CRUD — validation, soft delete, filters."""

import pytest
from rest_framework import status

from core.models import Tenant


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Ana Tenant CRUD",
        cpf_cnpj="29375235017",
        phone="11999990011",
        marital_status="Solteiro(a)",
        profession="Médica",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def company_tenant(admin_user):
    return Tenant.objects.create(
        name="Empresa CRUD Ltda",
        cpf_cnpj="11222333000181",
        is_company=True,
        phone="11888880011",
        marital_status="Solteiro(a)",
        profession="TI",
        due_day=15,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
class TestTenantCreate:
    url = "/api/tenants/"

    def test_create_tenant_with_valid_cpf(self, authenticated_api_client):
        payload = {
            "name": "João CPF Válido",
            "cpf_cnpj": "529.982.247-25",
            "is_company": False,
            "phone": "(11) 98765-4321",
            "marital_status": "Casado(a)",
            "profession": "Arquiteto",
            "due_day": 10,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "João CPF Válido"
        assert response.data["is_company"] is False

    def test_create_tenant_with_valid_cnpj(self, authenticated_api_client):
        payload = {
            "name": "CNPJ Empresa SA",
            "cpf_cnpj": "11.222.333/0001-81",
            "is_company": True,
            "phone": "(11) 3333-4444",
            "marital_status": "Solteiro(a)",
            "profession": "Empresa",
            "due_day": 20,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_company"] is True

    def test_create_tenant_duplicate_cpf_returns_400(
        self, authenticated_api_client, tenant
    ):
        # Use the same exact stored format as the fixture (raw digits, no formatting)
        payload = {
            "name": "Outro Com Mesmo CPF",
            "cpf_cnpj": "29375235017",
            "phone": "(11) 91111-2222",
            "marital_status": "Solteiro(a)",
            "profession": "Dev",
            "due_day": 5,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_tenant_missing_required_fields(self, authenticated_api_client):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_tenant_invalid_due_day_returns_400(self, authenticated_api_client):
        payload = {
            "name": "Dia Inválido",
            "cpf_cnpj": "529.982.247-25",
            "phone": "(11) 99999-8888",
            "marital_status": "Solteiro(a)",
            "profession": "Dev",
            "due_day": 32,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestTenantUpdate:
    def test_full_update_tenant(self, authenticated_api_client, tenant):
        payload = {
            "name": "Ana Atualizada",
            "cpf_cnpj": "29375235017",
            "is_company": False,
            "phone": "(11) 99999-1111",
            "marital_status": "Divorciado(a)",
            "profession": "Empresária",
            "due_day": 20,
        }
        response = authenticated_api_client.put(
            f"/api/tenants/{tenant.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Ana Atualizada"
        assert response.data["marital_status"] == "Divorciado(a)"
        assert response.data["due_day"] == 20

    def test_partial_update_tenant(self, authenticated_api_client, tenant):
        response = authenticated_api_client.patch(
            f"/api/tenants/{tenant.id}/",
            {"name": "Ana Parcial", "due_day": 15},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Ana Parcial"
        assert response.data["due_day"] == 15

    def test_update_tenant_regular_user_forbidden(
        self, regular_authenticated_api_client, tenant
    ):
        response = regular_authenticated_api_client.patch(
            f"/api/tenants/{tenant.id}/",
            {"name": "Não Permitido"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestTenantSoftDelete:
    def test_delete_tenant_soft_deletes(self, authenticated_api_client, tenant):
        response = authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Should not appear in default queryset (soft delete)
        assert not Tenant.objects.filter(id=tenant.id).exists()
        # But exists in all_objects
        assert Tenant.all_objects.filter(id=tenant.id).exists()

    def test_deleted_tenant_excluded_from_list(self, authenticated_api_client, tenant):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        response = authenticated_api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert tenant.id not in ids


@pytest.mark.integration
class TestTenantFilters:
    def test_filter_is_company_true(
        self, authenticated_api_client, tenant, company_tenant
    ):
        response = authenticated_api_client.get("/api/tenants/?is_company=true")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert company_tenant.id in ids
        assert tenant.id not in ids

    def test_search_by_name(self, authenticated_api_client, tenant, company_tenant):
        response = authenticated_api_client.get("/api/tenants/?search=Ana Tenant CRUD")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert tenant.id in ids
        assert company_tenant.id not in ids
