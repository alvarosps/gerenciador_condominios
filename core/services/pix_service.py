"""PIX EMV payload generation service.

Implements the BCB (Banco Central do Brasil) specification for static PIX QR codes.
Generates both the EMV copia e cola string and the payload metadata dict.
"""

from decimal import Decimal


def _crc16_ccitt(data: str) -> str:
    """Calculate CRC16-CCITT for EMV PIX payload."""
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _emv_field(tag: str, value: str) -> str:
    """Format an EMV TLV field: tag + length (2 digits) + value."""
    return f"{tag}{len(value):02d}{value}"


def generate_pix_emv(
    pix_key: str,
    merchant_name: str,
    city: str,
    amount: Decimal,
    txid: str = "***",
) -> str:
    """Generate PIX EMV (copia e cola) payload string.

    Follows BCB specification for static PIX QR codes.
    """
    gui = _emv_field("00", "br.gov.bcb.pix")
    key = _emv_field("01", pix_key)
    merchant_account = _emv_field("26", gui + key)

    payload = (
        _emv_field("00", "01")  # Payload Format Indicator
        + merchant_account
        + _emv_field("52", "0000")  # Merchant Category Code
        + _emv_field("53", "986")  # Transaction Currency (BRL)
        + _emv_field("54", f"{amount:.2f}")  # Transaction Amount
        + _emv_field("58", "BR")  # Country Code
        + _emv_field("59", merchant_name[:25])  # Merchant Name (max 25)
        + _emv_field("60", city[:15])  # Merchant City (max 15)
        + _emv_field("62", _emv_field("05", txid))  # Additional Data (txid)
    )

    payload += "6304"
    crc = _crc16_ccitt(payload)
    return payload + crc


def generate_pix_payload(
    pix_key: str,
    pix_key_type: str,
    amount: Decimal,
    merchant_name: str,
    city: str,
) -> dict[str, str]:
    """Generate full PIX payload for mobile app.

    Returns dict with pix_copy_paste, qr_data, and metadata.
    Raises ValueError if pix_key is empty.
    """
    if not pix_key:
        msg = "Chave PIX não cadastrada. Entre em contato com o administrador."
        raise ValueError(msg)

    emv = generate_pix_emv(
        pix_key=pix_key,
        merchant_name=merchant_name,
        city=city,
        amount=amount,
    )

    return {
        "pix_copy_paste": emv,
        "qr_data": emv,
        "pix_key": pix_key,
        "pix_key_type": pix_key_type,
        "amount": f"{amount:.2f}",
        "merchant_name": merchant_name,
    }
