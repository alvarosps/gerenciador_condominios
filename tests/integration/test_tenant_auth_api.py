"""
Integration tests for tenant WhatsApp OTP authentication endpoints.

Tests cover:
- POST /api/auth/whatsapp/request/  — request a verification code
- POST /api/auth/whatsapp/verify/   — verify the code and receive JWT tokens

Mock policy: send_verification_code is mocked because it is an external boundary
(Twilio HTTP API). Django ORM and all internal services run against the real test DB.
"""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from core.models import Apartment, Building, Lease, Tenant, WhatsAppVerification

REQUEST_URL = "/api/auth/whatsapp/request/"
VERIFY_URL = "/api/auth/whatsapp/verify/"

_CPF = "529.982.247-25"
_PHONE = "(11) 98765-4321"


def _make_tenant(admin_user, cpf_cnpj=_CPF, phone=_PHONE):
    building = Building.objects.create(
        street_number=8360,
        name="Edifício Teste Auth",
        address="Rua Teste, 8360",
        created_by=admin_user,
        updated_by=admin_user,
    )
    apartment = Apartment.objects.create(
        building=building,
        number=101,
        rental_value="1500.00",
        cleaning_fee="200.00",
        max_tenants=2,
        is_rented=True,
        created_by=admin_user,
        updated_by=admin_user,
    )
    tenant = Tenant.objects.create(
        name="João da Silva",
        cpf_cnpj=cpf_cnpj,
        phone=phone,
        marital_status="Casado(a)",
        profession="Engenheiro",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )
    Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=timezone.now().date(),
        validity_months=12,
        rental_value="1500.00",
        number_of_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )
    return tenant


@pytest.mark.integration
class TestRequestCode:
    """Tests for POST /api/auth/whatsapp/request/"""

    def test_request_code_success(self, admin_user):
        """Successful code request creates a WhatsAppVerification and returns 200."""
        _make_tenant(admin_user)
        client = APIClient()

        with patch("core.viewsets.auth_views.send_verification_code") as mock_send:
            response = client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "Código enviado" in response.data["detail"]
        mock_send.assert_called_once()
        assert WhatsAppVerification.objects.filter(cpf_cnpj=_CPF).count() == 1

    def test_request_code_unknown_cpf(self):
        """Unknown CPF returns 404."""
        client = APIClient()
        response = client.post(REQUEST_URL, {"cpf_cnpj": "000.000.000-00"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_request_code_missing_cpf(self):
        """Missing cpf_cnpj returns 400."""
        client = APIClient()
        response = client.post(REQUEST_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rate_limiting(self, admin_user):
        """4th request within 15 minutes is rejected with 429."""
        _make_tenant(admin_user)
        client = APIClient()

        with patch("core.viewsets.auth_views.send_verification_code"):
            for _ in range(3):
                response = client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")
                assert response.status_code == status.HTTP_200_OK

            response = client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.integration
class TestVerifyCode:
    """Tests for POST /api/auth/whatsapp/verify/"""

    def test_verify_code_success(self, admin_user, django_user_model):
        """Correct code returns JWT tokens and links tenant.user."""
        tenant = _make_tenant(admin_user)
        client = APIClient()

        with patch("core.viewsets.auth_views.send_verification_code"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF).latest("created_at")
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": _CPF, "code": verification.code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

        tenant.refresh_from_db()
        assert tenant.user is not None
        assert tenant.user.username == f"tenant_{tenant.pk}"
        assert tenant.user.is_staff is False

    def test_verify_wrong_code_increments_attempts(self, admin_user):
        """Wrong code returns 400 and increments the attempts counter."""
        _make_tenant(admin_user)
        client = APIClient()

        with patch("core.viewsets.auth_views.send_verification_code"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF).latest("created_at")
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": _CPF, "code": "000000"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        verification.refresh_from_db()
        assert verification.attempts == 1

    def test_verify_expired_code(self, admin_user):
        """Expired code returns 400."""
        tenant = _make_tenant(admin_user)
        expired = WhatsAppVerification.objects.create(
            cpf_cnpj=tenant.cpf_cnpj,
            code="123456",
            phone="+5511987654321",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        client = APIClient()
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": _CPF, "code": expired.code},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_unknown_cpf(self):
        """Unknown CPF returns 404."""
        client = APIClient()
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": "000.000.000-00", "code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_no_pending_verification(self, admin_user):
        """No pending verification returns 404."""
        _make_tenant(admin_user)
        client = APIClient()
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": _CPF, "code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_missing_fields(self):
        """Missing required fields returns 400."""
        client = APIClient()
        response = client.post(VERIFY_URL, {"cpf_cnpj": _CPF}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_second_login_reuses_existing_user(self, admin_user, django_user_model):
        """Second successful login reuses the existing linked user."""
        tenant = _make_tenant(admin_user)
        client = APIClient()

        # First login — creates the user
        with patch("core.viewsets.auth_views.send_verification_code"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")
        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF).latest("created_at")
        client.post(VERIFY_URL, {"cpf_cnpj": _CPF, "code": verification.code}, format="json")

        tenant.refresh_from_db()
        first_user_pk = tenant.user.pk

        # Second login — must reuse the same user
        with patch("core.viewsets.auth_views.send_verification_code"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")
        verification2 = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF).latest("created_at")
        response = client.post(
            VERIFY_URL, {"cpf_cnpj": _CPF, "code": verification2.code}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        tenant.refresh_from_db()
        assert tenant.user.pk == first_user_pk
        assert django_user_model.objects.filter(username=f"tenant_{tenant.pk}").count() == 1
