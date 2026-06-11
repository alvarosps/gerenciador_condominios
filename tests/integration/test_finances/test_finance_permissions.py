"""IsAdminUser matrix for /api/finances/ endpoints (admin-only after P1.2)."""

import pytest
from rest_framework import status

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

WRITE_ENDPOINTS = [
    ("post", "/api/finances/finance-categories/"),
    ("post", "/api/finances/billing-accounts/"),
    ("post", "/api/finances/bills/"),
    ("post", "/api/finances/bill-skips/"),
    ("post", "/api/finances/payments/"),
    ("post", "/api/finances/bills/bulk_pay/"),
    ("post", "/api/finances/bills/generate_month/"),
    ("post", "/api/finances/bills/create_with_lines/"),
    ("post", "/api/finances/bills/1/pay/"),
    ("post", "/api/finances/bills/1/suspend/"),
]

READ_ENDPOINTS = [
    "/api/finances/finance-categories/",
    "/api/finances/billing-accounts/",
    "/api/finances/bills/",
    "/api/finances/bill-skips/",
    "/api/finances/payments/",
    "/api/finances/finance-dashboard/combined_calendar/",
    "/api/finances/finance-dashboard/overdue/",
]


@pytest.mark.parametrize(("method", "url"), WRITE_ENDPOINTS)
def test_non_admin_cannot_write(regular_authenticated_api_client, method, url):
    response = getattr(regular_authenticated_api_client, method)(url, {}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(("method", "url"), WRITE_ENDPOINTS)
def test_admin_write_passes_permission(authenticated_api_client, method, url):
    response = getattr(authenticated_api_client, method)(url, {}, format="json")
    assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("url", READ_ENDPOINTS)
def test_non_admin_cannot_read(regular_authenticated_api_client, url):
    assert regular_authenticated_api_client.get(url).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("url", READ_ENDPOINTS)
def test_admin_can_read(authenticated_api_client, url):
    assert authenticated_api_client.get(url).status_code == status.HTTP_200_OK


def test_unauthenticated_cannot_read(api_client):
    assert api_client.get("/api/finances/bills/").status_code == status.HTTP_401_UNAUTHORIZED
