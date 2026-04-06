"""Integration tests for the /api/health/ endpoint."""

import pytest
from rest_framework import status


@pytest.mark.integration
class TestHealthCheck:
    def test_health_returns_200(self, api_client):
        response = api_client.get("/api/health/")
        assert response.status_code == status.HTTP_200_OK

    def test_health_response_has_status_field(self, api_client):
        response = api_client.get("/api/health/")
        assert "status" in response.data

    def test_health_status_is_healthy(self, api_client):
        response = api_client.get("/api/health/")
        assert response.data["status"] == "healthy"

    def test_health_response_has_database_field(self, api_client):
        response = api_client.get("/api/health/")
        assert "database" in response.data

    def test_health_database_is_true(self, api_client):
        response = api_client.get("/api/health/")
        assert response.data["database"] is True

    def test_health_no_auth_required(self, api_client):
        # Unauthenticated client must still get 200
        response = api_client.get("/api/health/")
        assert response.status_code == status.HTTP_200_OK

    def test_health_only_accepts_get(self, api_client):
        response = api_client.post("/api/health/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
