import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from core.services.whatsapp_service import (
    generate_verification_code,
    normalize_phone_to_e164,
    send_verification_code,
    send_whatsapp_message,
)


@pytest.mark.unit
class TestNormalizePhone:
    def test_already_e164(self):
        assert normalize_phone_to_e164("+5511999998888") == "+5511999998888"

    def test_strips_formatting(self):
        assert normalize_phone_to_e164("(11) 99999-8888") == "+5511999998888"

    def test_adds_country_code(self):
        assert normalize_phone_to_e164("11999998888") == "+5511999998888"

    def test_handles_spaces_and_dashes(self):
        assert normalize_phone_to_e164("11 99999 8888") == "+5511999998888"

    def test_empty_phone_raises(self):
        with pytest.raises(ValueError, match="Telefone não cadastrado"):
            normalize_phone_to_e164("")

    def test_none_phone_raises(self):
        with pytest.raises(ValueError, match="Telefone não cadastrado"):
            normalize_phone_to_e164(None)


@pytest.mark.unit
class TestGenerateCode:
    def test_code_is_6_digits(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_codes_are_random(self):
        codes = {generate_verification_code() for _ in range(100)}
        assert len(codes) > 1


_TWILIO_SETTINGS = {
    "TWILIO_ACCOUNT_SID": "AC_test_sid",
    "TWILIO_AUTH_TOKEN": "test_token",
    "TWILIO_WHATSAPP_FROM": "+15550001111",
    "TWILIO_TEMPLATE_VERIFICATION": "HX_verification",
}


@pytest.mark.unit
class TestSendWhatsAppMessage:
    @override_settings(**_TWILIO_SETTINGS)
    def test_content_variables_sent_as_json_string(self):
        # RED: today content_variables is a dict; Twilio requires a JSON string.
        with patch("core.services.whatsapp_service.Client") as client_cls:
            message = MagicMock()
            message.sid = "SM_test"
            client_cls.return_value.messages.create.return_value = message

            result = send_whatsapp_message(
                to_phone="+5511999998888",
                template_sid="HX_template",
                template_variables={"1": "123456"},
            )

        assert result == "SM_test"
        _, kwargs = client_cls.return_value.messages.create.call_args
        content_variables = kwargs["content_variables"]
        assert isinstance(content_variables, str)
        assert json.loads(content_variables) == {"1": "123456"}

    @override_settings(TWILIO_ACCOUNT_SID="")
    def test_missing_credentials_raises_runtimeerror(self):
        with pytest.raises(RuntimeError, match="Twilio credentials not configured"):
            send_whatsapp_message(
                to_phone="+5511999998888",
                template_sid="HX_template",
                template_variables={"1": "123456"},
            )

    @override_settings(**_TWILIO_SETTINGS)
    def test_verification_code_uses_verification_template(self):
        with patch("core.services.whatsapp_service.Client") as client_cls:
            message = MagicMock()
            message.sid = "SM_verify"
            client_cls.return_value.messages.create.return_value = message

            send_verification_code(phone="+5511999998888", code="654321")

        _, kwargs = client_cls.return_value.messages.create.call_args
        assert kwargs["content_sid"] == "HX_verification"
        assert json.loads(kwargs["content_variables"]) == {"1": "654321"}
