"""
Integration tests for tenant WhatsApp OTP authentication endpoints.

Tests cover:
- POST /api/auth/whatsapp/request/  — request a verification code
- POST /api/auth/whatsapp/verify/   — verify the code and receive JWT tokens

Mock policy: only the EXTERNAL Twilio boundary is mocked — ``core.services.whatsapp_service.Client``
(the Twilio SDK). The real ``send_verification_code`` / ``send_whatsapp_message`` run end-to-end
(exercising the ``content_variables=json.dumps(...)`` contract), and an autouse ``settings``
fixture supplies the TWILIO_* credentials the guard requires. Django ORM and all internal services run against the
real test DB — never patched.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Apartment, Building, Lease, Tenant, WhatsAppVerification
from tests.factories import CPF_VALID_PRIMARY

REQUEST_URL = "/api/auth/whatsapp/request/"
VERIFY_URL = "/api/auth/whatsapp/verify/"

# Tenant.cpf_cnpj is normalized to digits on save and the auth view normalizes the request
# input, so verifications are persisted/looked-up by the digits-only form.
_CPF_DIGITS = CPF_VALID_PRIMARY
_CPF = "529.982.247-25"  # CPF_VALID_PRIMARY in the formatted form the API accepts
_PHONE = "(11) 98765-4321"

# Generic, identical responses that must not reveal whether a CPF/CNPJ is a tenant.
_GENERIC_REQUEST_DETAIL = "Se o CPF/CNPJ estiver cadastrado, um código foi enviado via WhatsApp."
_GENERIC_VERIFY_ERROR = "Código inválido."


@pytest.fixture(autouse=True)
def _twilio_credentials(settings):
    """send_whatsapp_message raises RuntimeError when TWILIO_ACCOUNT_SID is empty (the test env
    leaves it unset), so the real send path needs these credentials present. The Twilio Client
    itself is mocked per-test, so the values are inert."""
    settings.TWILIO_ACCOUNT_SID = "ACtest00000000000000000000000000"
    settings.TWILIO_AUTH_TOKEN = "test-auth-token"
    settings.TWILIO_TEMPLATE_VERIFICATION = "HXtest00000000000000000000000000"
    settings.TWILIO_WHATSAPP_FROM = "+15551230000"


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

    def test_request_code_known_cpf_returns_generic_200(self, admin_user):
        """Known CPF creates a WhatsAppVerification, sends the code and returns a generic 200."""
        _make_tenant(admin_user)
        client = APIClient()

        with patch("core.services.whatsapp_service.Client") as mock_client:
            response = client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == _GENERIC_REQUEST_DETAIL
        # The real send_verification_code ran end-to-end and hit the Twilio Client once.
        mock_client.return_value.messages.create.assert_called_once()
        assert WhatsAppVerification.objects.filter(cpf_cnpj=_CPF_DIGITS).count() == 1

    def test_request_code_unknown_cpf_returns_same_generic_200(self):
        """Unknown CPF must NOT enumerate: same generic 200, no verification, no send."""
        client = APIClient()

        with patch("core.services.whatsapp_service.Client") as mock_client:
            response = client.post(REQUEST_URL, {"cpf_cnpj": "000.000.000-00"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == _GENERIC_REQUEST_DETAIL
        # Unknown CPF must not send — the Twilio Client is never even constructed.
        mock_client.assert_not_called()
        assert WhatsAppVerification.objects.filter(cpf_cnpj="000.000.000-00").count() == 0

    def test_request_code_missing_cpf(self):
        """Missing cpf_cnpj returns 400."""
        client = APIClient()
        response = client.post(REQUEST_URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rate_limiting(self, admin_user):
        """4th request within 15 minutes is rejected with 429."""
        _make_tenant(admin_user)
        client = APIClient()

        with patch("core.services.whatsapp_service.Client"):
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

        with patch("core.services.whatsapp_service.Client"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF_DIGITS).latest(
            "created_at"
        )
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

        with patch("core.services.whatsapp_service.Client"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF_DIGITS).latest(
            "created_at"
        )
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

    def test_verify_unknown_cpf_returns_400_generic(self):
        """Unknown CPF must NOT enumerate: same generic 400 as a wrong code (never 404)."""
        client = APIClient()
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": "000.000.000-00", "code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == _GENERIC_VERIFY_ERROR

    def test_verify_no_pending_verification_returns_400_generic(self, admin_user):
        """Known CPF without a pending verification returns the same generic 400 (never 404)."""
        _make_tenant(admin_user)
        client = APIClient()
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": _CPF, "code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == _GENERIC_VERIFY_ERROR

    def test_verify_missing_fields(self):
        """Missing required fields returns 400."""
        client = APIClient()
        response = client.post(VERIFY_URL, {"cpf_cnpj": _CPF}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_lockout_after_three_wrong_attempts(self, admin_user):
        """After 3 wrong attempts the verification is locked and returns 429."""
        _make_tenant(admin_user)
        client = APIClient()

        with patch("core.services.whatsapp_service.Client"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")

        # Three wrong attempts exhaust the counter
        for _ in range(3):
            response = client.post(
                VERIFY_URL,
                {"cpf_cnpj": _CPF, "code": "000000"},
                format="json",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Fourth attempt (even with the right code) is blocked with 429
        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF_DIGITS).latest(
            "created_at"
        )
        response = client.post(
            VERIFY_URL,
            {"cpf_cnpj": _CPF, "code": verification.code},
            format="json",
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_verify_second_login_reuses_existing_user(self, admin_user, django_user_model):
        """Second successful login reuses the existing linked user."""
        tenant = _make_tenant(admin_user)
        client = APIClient()

        # First login — creates the user
        with patch("core.services.whatsapp_service.Client"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")
        verification = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF_DIGITS).latest(
            "created_at"
        )
        client.post(VERIFY_URL, {"cpf_cnpj": _CPF, "code": verification.code}, format="json")

        tenant.refresh_from_db()
        first_user_pk = tenant.user.pk

        # Second login — must reuse the same user
        with patch("core.services.whatsapp_service.Client"):
            client.post(REQUEST_URL, {"cpf_cnpj": _CPF}, format="json")
        verification2 = WhatsAppVerification.objects.filter(cpf_cnpj=_CPF_DIGITS).latest(
            "created_at"
        )
        response = client.post(
            VERIFY_URL, {"cpf_cnpj": _CPF, "code": verification2.code}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        tenant.refresh_from_db()
        assert tenant.user.pk == first_user_pk
        assert django_user_model.objects.filter(username=f"tenant_{tenant.pk}").count() == 1
