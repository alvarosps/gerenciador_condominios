"""Unit tests for core/services/pix_service.py — PIX EMV payload generation."""

from decimal import Decimal

import pytest

from core.services.pix_service import (
    _crc16_ccitt,
    _emv_field,
    generate_pix_emv,
    generate_pix_payload,
)


@pytest.mark.unit
class TestPixPayload:
    def test_generate_payload_with_cpf_key(self):
        result = generate_pix_payload(
            pix_key="12345678901",
            pix_key_type="cpf",
            amount=Decimal("1200.00"),
            merchant_name="Maria Silva",
            city="Sao Paulo",
        )
        assert "pix_copy_paste" in result
        assert "qr_data" in result
        assert result["amount"] == "1200.00"
        assert result["pix_key"] == "12345678901"

    def test_generate_emv_format(self):
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="Maria Silva",
            city="Sao Paulo",
            amount=Decimal("1200.00"),
        )
        assert emv.startswith("00")  # EMV payload indicator
        assert "12345678901" in emv
        assert "1200.00" in emv

    def test_no_pix_key_raises(self):
        with pytest.raises(ValueError, match="Chave PIX não cadastrada"):
            generate_pix_payload(
                pix_key="",
                pix_key_type="cpf",
                amount=Decimal("1200.00"),
                merchant_name="Test",
                city="Test",
            )


@pytest.mark.unit
class TestPixAccents:
    def test_merchant_name_with_accents_does_not_raise(self):
        # RED: today merchant_name="João" → UnicodeEncodeError in _crc16_ccitt.
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="João",
            city="São Paulo",
            amount=Decimal("1200.00"),
        )
        assert isinstance(emv, str)
        assert emv  # non-empty

    def test_accented_name_sanitized_to_ascii_upper(self):
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="João André",
            city="São Paulo",
            amount=Decimal("1200.00"),
        )
        assert "JOAO ANDRE" in emv
        assert "João" not in emv
        assert "André" not in emv

    def test_default_condominio_name_works(self):
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="Condomínio",
            city="Porto Alegre",
            amount=Decimal("1200.00"),
        )
        assert "CONDOMINIO" in emv
        assert "Condomínio" not in emv

    def test_city_sanitized(self):
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="Maria Silva",
            city="São Paulo",
            amount=Decimal("1200.00"),
        )
        assert "SAO PAULO" in emv
        assert "São Paulo" not in emv


@pytest.mark.unit
class TestEmvFieldLength:
    def test_emv_field_length_is_bytes(self):
        # ASCII value: length == number of chars == number of bytes.
        ascii_field = _emv_field("01", "andre@apto.com")
        assert ascii_field == "0114andre@apto.com"

    def test_emv_field_length_counts_bytes_for_multibyte(self):
        # "é" is 2 bytes in UTF-8; the TLV length must be byte count, not char count.
        field = _emv_field("01", "é")
        # tag "01" + length "02" (2 bytes) + value "é"
        assert field == "0102é"
        # length prefix must reflect bytes, never the single char.
        assert field[2:4] == "02"


@pytest.mark.unit
class TestCrc16:
    def test_crc16_valid_for_accented_payload(self):
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="João André",
            city="São Paulo",
            amount=Decimal("1200.00"),
        )
        # The last 4 chars are the CRC; recompute over everything before them.
        body = emv[:-4]
        crc = emv[-4:]
        assert _crc16_ccitt(body) == crc

    def test_crc16_known_value(self):
        # Sanity check against a fixed input (deterministic CRC16-CCITT).
        assert _crc16_ccitt("123456789") == "29B1"
