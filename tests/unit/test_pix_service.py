"""Unit tests for core/services/pix_service.py — PIX EMV payload generation."""

from decimal import Decimal

import pytest

from core.services.pix_service import generate_pix_emv, generate_pix_payload


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
