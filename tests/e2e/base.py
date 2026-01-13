"""
Base E2E Test Class

Provides common setup, utilities, and helpers for all E2E tests.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

User = get_user_model()


class BaseE2ETest:
    """Base class for all E2E tests with common setup and utilities."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup run before each test."""
        # Clear cache before each test
        cache.clear()

        # Create API client
        self.client = APIClient()

        # Create admin user for authenticated tests
        self.admin_user = User.objects.create_superuser(
            username="admin_e2e", email="admin@e2e.test", password="AdminPass123!"
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            username="user_e2e", email="user@e2e.test", password="UserPass123!"
        )

        # Storage for test data created during workflow
        self.test_data = {}

    def authenticate_as_admin(self):
        """Authenticate client as admin user."""
        self.client.force_authenticate(user=self.admin_user)
        return self.admin_user

    def authenticate_as_user(self):
        """Authenticate client as regular user."""
        self.client.force_authenticate(user=self.regular_user)
        return self.regular_user

    def logout(self):
        """Logout current user."""
        self.client.force_authenticate(user=None)

    def login_with_credentials(self, username, password):
        """
        Login using JWT authentication.
        Returns access and refresh tokens.
        """
        response = self.client.post("/api/auth/token/", {"username": username, "password": password})
        assert (
            response.status_code == 200
        ), f"Login failed: {response.content if hasattr(response, 'content') else 'Unknown error'}"

        tokens = response.json()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        return tokens

    def refresh_token(self, refresh_token):
        """Refresh JWT access token."""
        response = self.client.post("/api/auth/token/refresh/", {"refresh": refresh_token})
        assert (
            response.status_code == 200
        ), f"Token refresh failed: {response.content if hasattr(response, 'content') else 'Unknown error'}"

        new_tokens = response.json()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_tokens["access"]}')
        return new_tokens

    def assert_response_success(self, response, expected_status=200):
        """Assert response is successful with expected status."""
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}: {response.data}"

    def assert_response_error(self, response, expected_status=400):
        """Assert response is an error with expected status."""
        assert response.status_code == expected_status, f"Expected error {expected_status}, got {response.status_code}"

    def assert_has_keys(self, data, *keys):
        """Assert dictionary has required keys."""
        for key in keys:
            assert key in data, f"Missing required key: {key}"

    def create_building(self, street_number=836, name="Test Building", **kwargs):
        """Helper to create a building."""
        data = {
            "street_number": street_number,
            "name": name,
            "address": kwargs.get("address", f"Test Street, {street_number}"),
            **kwargs,
        }
        response = self.client.post("/api/buildings/", data, format="json")
        self.assert_response_success(response, 201)
        return response.json()

    def create_apartment(self, building_id, number=101, **kwargs):
        """Helper to create an apartment."""
        data = {
            "building_id": building_id,
            "number": number,
            "rental_value": kwargs.get("rental_value", "1500.00"),
            "cleaning_fee": kwargs.get("cleaning_fee", "200.00"),
            "max_tenants": kwargs.get("max_tenants", 2),
            "is_rented": kwargs.get("is_rented", False),
            **kwargs,
        }
        response = self.client.post("/api/apartments/", data, format="json")
        self.assert_response_success(response, 201)
        return response.json()

    def create_tenant(self, name="Test Tenant", **kwargs):
        """Helper to create a tenant."""
        import uuid

        # Use UUID to ensure uniqueness - take 11 digits
        unique_id = str(uuid.uuid4().int)[:11]
        cpf = unique_id

        data = {
            "name": name,
            "cpf_cnpj": kwargs.get("cpf_cnpj", cpf),
            "phone": kwargs.get("phone", "11999999999"),
            "marital_status": kwargs.get("marital_status", "Solteiro(a)"),
            "profession": kwargs.get("profession", "Engineer"),
            "is_company": kwargs.get("is_company", False),
            **kwargs,
        }
        response = self.client.post("/api/tenants/", data, format="json")
        self.assert_response_success(response, 201)
        return response.json()

    def create_furniture(self, name=None, description="Test Furniture", **kwargs):
        """Helper to create furniture."""
        import random

        if name is None:
            name = f"Furniture_{random.randint(1000, 9999)}"

        data = {"name": name, "description": description, **kwargs}
        response = self.client.post("/api/furnitures/", data, format="json")
        self.assert_response_success(response, 201)
        return response.json()

    def create_lease(self, apartment_id, responsible_tenant_id, tenant_ids, **kwargs):
        """Helper to create a lease."""
        data = {
            "apartment_id": apartment_id,
            "responsible_tenant_id": responsible_tenant_id,
            "tenant_ids": tenant_ids,
            "start_date": kwargs.get("start_date", str(date.today())),
            "validity_months": kwargs.get("validity_months", 12),
            "due_day": kwargs.get("due_day", 10),
            "rental_value": kwargs.get("rental_value", "1500.00"),
            "cleaning_fee": kwargs.get("cleaning_fee", "200.00"),
            "tag_fee": kwargs.get("tag_fee", "50.00"),
            **kwargs,
        }
        response = self.client.post("/api/leases/", data, format="json")
        self.assert_response_success(response, 201)
        return response.json()

    def wait_for_condition(self, condition_func, timeout=5, interval=0.1):
        """Wait for a condition to become true."""
        import time

        start = time.time()
        while time.time() - start < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
