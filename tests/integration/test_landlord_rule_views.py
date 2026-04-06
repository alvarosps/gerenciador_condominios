"""Integration tests for LandlordViewSet and ContractRuleViewSet.

Covers:
- GET/PUT/PATCH /api/landlords/current/
- Full CRUD /api/rules/ + reorder + active_rules actions

Note: List endpoints return paginated responses: {"count", "next", "previous", "results"}.
The active_rules and reorder are custom actions that return plain lists/dicts.
"""

import pytest
from rest_framework import status

from core.models import ContractRule, Landlord


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

LANDLORD_PAYLOAD = {
    "name": "José da Silva",
    "nationality": "Brasileira",
    "marital_status": "Casado(a)",
    "cpf_cnpj": "529.982.247-25",
    "rg": "12.345.678-9",
    "phone": "(11) 98765-4321",
    "email": "jose@example.com",
    "street": "Rua das Flores",
    "street_number": "100",
    "complement": "Apto 1",
    "neighborhood": "Centro",
    "city": "São Paulo",
    "state": "SP",
    "zip_code": "01310-100",
    "country": "Brasil",
    "is_active": True,
}


@pytest.fixture
def landlord(admin_user):
    return Landlord.objects.create(
        name="Maria Locadora",
        nationality="Brasileira",
        marital_status="Solteiro(a)",
        cpf_cnpj="29375235017",
        phone="11999990001",
        street="Rua Teste",
        street_number="50",
        neighborhood="Bairro Teste",
        city="São Paulo",
        state="SP",
        zip_code="01310-000",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def rule(admin_user):
    return ContractRule.objects.create(
        content="É proibido animais de grande porte.",
        order=1,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def rule2(admin_user):
    return ContractRule.objects.create(
        content="O condomínio fecha às 22h.",
        order=2,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def inactive_rule(admin_user):
    return ContractRule.objects.create(
        content="Regra inativa de teste.",
        order=99,
        is_active=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


# ---------------------------------------------------------------------------
# LandlordViewSet
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLandlordViewSet:
    url = "/api/landlords/current/"

    def test_get_current_landlord_admin(self, authenticated_api_client, landlord):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == landlord.name

    def test_get_current_landlord_when_none_returns_404(self, authenticated_api_client):
        # Ensure no landlord exists
        Landlord.objects.all().update(is_active=False)
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data

    def test_get_current_landlord_regular_user_forbidden(
        self, regular_authenticated_api_client, landlord
    ):
        response = regular_authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_landlord_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_put_creates_landlord_when_none_exists(self, authenticated_api_client):
        Landlord.objects.all().update(is_active=False)
        response = authenticated_api_client.put(self.url, LANDLORD_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "José da Silva"
        assert response.data["is_active"] is True

    def test_put_updates_existing_landlord(self, authenticated_api_client, landlord):
        updated = {**LANDLORD_PAYLOAD, "name": "José Atualizado"}
        response = authenticated_api_client.put(self.url, updated, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "José Atualizado"
        landlord.refresh_from_db()
        assert landlord.name == "José Atualizado"

    def test_patch_partial_update(self, authenticated_api_client, landlord):
        response = authenticated_api_client.patch(
            self.url, {"name": "Nome via PATCH"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Nome via PATCH"

    def test_put_invalid_data_returns_400(self, authenticated_api_client, landlord):
        bad_payload = {**LANDLORD_PAYLOAD, "cpf_cnpj": "000.000.000-00"}
        response = authenticated_api_client.put(self.url, bad_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_put_regular_user_forbidden(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.put(
            self.url, LANDLORD_PAYLOAD, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# ContractRuleViewSet — CRUD
# ---------------------------------------------------------------------------


def get_ids(response):
    """Extract IDs from a paginated list response."""
    return [item["id"] for item in response.data["results"]]


@pytest.mark.integration
class TestContractRuleViewSet:
    list_url = "/api/rules/"

    def test_list_rules_admin(self, authenticated_api_client, rule, rule2):
        response = authenticated_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert rule.id in ids
        assert rule2.id in ids

    def test_list_rules_regular_user_forbidden(self, regular_authenticated_api_client, rule):
        response = regular_authenticated_api_client.get(self.list_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_rules_unauthenticated(self, api_client):
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_is_active_true(
        self, authenticated_api_client, rule, inactive_rule
    ):
        response = authenticated_api_client.get(f"{self.list_url}?is_active=true")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert rule.id in ids
        assert inactive_rule.id not in ids

    def test_filter_by_is_active_false(
        self, authenticated_api_client, rule, inactive_rule
    ):
        response = authenticated_api_client.get(f"{self.list_url}?is_active=false")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert inactive_rule.id in ids
        assert rule.id not in ids

    def test_retrieve_rule(self, authenticated_api_client, rule):
        response = authenticated_api_client.get(f"{self.list_url}{rule.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["content"] == rule.content

    def test_create_rule_admin(self, authenticated_api_client):
        payload = {"content": "Nova regra criada no teste.", "order": 5, "is_active": True}
        response = authenticated_api_client.post(self.list_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == "Nova regra criada no teste."

    def test_create_rule_without_order_auto_assigns(self, authenticated_api_client):
        payload = {"content": "Regra sem order explícito.", "order": 0, "is_active": True}
        response = authenticated_api_client.post(self.list_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_rule_regular_user_forbidden(self, regular_authenticated_api_client):
        payload = {"content": "Bloqueado.", "order": 1, "is_active": True}
        response = regular_authenticated_api_client.post(
            self.list_url, payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_rule_admin(self, authenticated_api_client, rule):
        payload = {"content": "Conteúdo atualizado.", "order": 1, "is_active": True}
        response = authenticated_api_client.put(
            f"{self.list_url}{rule.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["content"] == "Conteúdo atualizado."

    def test_partial_update_rule_admin(self, authenticated_api_client, rule):
        response = authenticated_api_client.patch(
            f"{self.list_url}{rule.id}/", {"is_active": False}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        rule.refresh_from_db()
        assert rule.is_active is False

    def test_soft_delete_rule_admin(self, authenticated_api_client, rule):
        response = authenticated_api_client.delete(f"{self.list_url}{rule.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        rule.refresh_from_db()
        assert rule.is_deleted is True

    def test_delete_rule_regular_user_forbidden(
        self, regular_authenticated_api_client, rule
    ):
        response = regular_authenticated_api_client.delete(f"{self.list_url}{rule.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# ContractRuleViewSet — reorder action
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestContractRuleReorder:
    reorder_url = "/api/rules/reorder/"

    def test_reorder_rules_success(self, authenticated_api_client, rule, rule2):
        payload = {"rule_ids": [rule2.id, rule.id]}
        response = authenticated_api_client.post(self.reorder_url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        rule2.refresh_from_db()
        rule.refresh_from_db()
        assert rule2.order == 0
        assert rule.order == 1

    def test_reorder_with_nonexistent_id_returns_400(
        self, authenticated_api_client, rule
    ):
        payload = {"rule_ids": [rule.id, 999999]}
        response = authenticated_api_client.post(self.reorder_url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_reorder_regular_user_forbidden(
        self, regular_authenticated_api_client, rule, rule2
    ):
        payload = {"rule_ids": [rule.id, rule2.id]}
        response = regular_authenticated_api_client.post(
            self.reorder_url, payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reorder_missing_rule_ids_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(self.reorder_url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# ContractRuleViewSet — active_rules action
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestContractRuleActiveRules:
    active_url = "/api/rules/active/"

    def test_active_rules_returns_only_active(
        self, authenticated_api_client, rule, inactive_rule
    ):
        response = authenticated_api_client.get(self.active_url)
        assert response.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in response.data]
        assert rule.id in ids
        assert inactive_rule.id not in ids

    def test_active_rules_ordered_by_order_field(
        self, authenticated_api_client, rule, rule2
    ):
        response = authenticated_api_client.get(self.active_url)
        assert response.status_code == status.HTTP_200_OK
        orders = [r["order"] for r in response.data]
        assert orders == sorted(orders)

    def test_active_rules_regular_user_forbidden(
        self, regular_authenticated_api_client, rule
    ):
        response = regular_authenticated_api_client.get(self.active_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
