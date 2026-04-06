"""Integration tests for FinancialReadOnly permission on financial API endpoints.

Verifies that the FinancialReadOnly permission class is wired correctly on all
financial viewsets — non-admin authenticated users can read but not write,
and admin users can write.

Unit-level permission logic is tested in tests/unit/test_permissions.py.
These tests cover the HTTP layer (view → permission → response).
"""

import pytest
from rest_framework import status

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FINANCIAL_WRITE_ENDPOINTS = [
    ("post", "/api/persons/"),
    ("post", "/api/expenses/"),
    ("post", "/api/incomes/"),
    ("post", "/api/rent-payments/"),
    ("post", "/api/employee-payments/"),
    ("post", "/api/credit-cards/"),
    ("post", "/api/expense-categories/"),
    ("post", "/api/person-incomes/"),
    ("post", "/api/person-payments/"),
]

FINANCIAL_READ_ENDPOINTS = [
    "/api/persons/",
    "/api/expenses/",
    "/api/expense-categories/",
    "/api/incomes/",
    "/api/rent-payments/",
]


class TestFinancialWritePermissions:
    """Non-admin authenticated users cannot write to financial endpoints."""

    @pytest.mark.parametrize(("method", "url"), FINANCIAL_WRITE_ENDPOINTS)
    def test_non_admin_cannot_write(self, regular_authenticated_api_client, method, url):
        response = getattr(regular_authenticated_api_client, method)(url, {}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(("method", "url"), FINANCIAL_WRITE_ENDPOINTS)
    def test_admin_write_passes_permission_check(self, authenticated_api_client, method, url):
        """Admin gets past the permission gate (400 validation is acceptable — not 403)."""
        response = getattr(authenticated_api_client, method)(url, {}, format="json")
        assert response.status_code != status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("url", FINANCIAL_READ_ENDPOINTS)
    def test_non_admin_can_read(self, regular_authenticated_api_client, url):
        response = regular_authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_read_financial(self, api_client):
        response = api_client.get("/api/persons/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
