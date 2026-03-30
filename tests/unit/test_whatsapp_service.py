import pytest

from core.services.whatsapp_service import generate_verification_code, normalize_phone_to_e164


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
