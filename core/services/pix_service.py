"""PIX EMV payload generation service.

Implements the BCB (Banco Central do Brasil) specification for static PIX QR codes.
Generates both the EMV copia e cola string and the payload metadata dict.
"""

import unicodedata
from decimal import Decimal

from core.models import FinancialSettings, Landlord, Lease

_MERCHANT_NAME_MAX = 25
_CITY_MAX = 15
_DEFAULT_MERCHANT_NAME = "Condomínio"
_DEFAULT_CITY = "Porto Alegre"


def _sanitize_ascii(value: str) -> str:
    """Reduce a string to uppercase ASCII per the BCB PIX spec.

    Strips diacritics via NFKD normalization, drops any remaining non-ASCII
    bytes, and uppercases the result. "João" -> "JOAO", "São Paulo" -> "SAO PAULO".
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_bytes = normalized.encode("ascii", "ignore")
    return ascii_bytes.decode("ascii").upper()


def _crc16_ccitt(data: str) -> str:
    """Calculate CRC16-CCITT for EMV PIX payload.

    The EMV payload is ASCII by specification; all dynamic fields are sanitized
    upstream, so encoding as ASCII here is the correct, strict behavior.
    """
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
    """Format an EMV TLV field: tag + length (2 digits) + value.

    The length is the number of BYTES of the value (UTF-8 encoded) per the EMV
    spec, not the number of characters.
    """
    return f"{tag}{len(value.encode('utf-8')):02d}{value}"


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
        + _emv_field("59", _sanitize_ascii(merchant_name)[:_MERCHANT_NAME_MAX])  # Merchant Name
        + _emv_field("60", _sanitize_ascii(city)[:_CITY_MAX])  # Merchant City
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


def _resolve_city(landlord: Landlord | None, settings_obj: FinancialSettings | None) -> str:
    """Resolve the PIX recipient city: active landlord, then settings, then default."""
    if landlord and landlord.city:
        return landlord.city
    if settings_obj and settings_obj.default_city:
        return settings_obj.default_city
    return _DEFAULT_CITY


def resolve_pix_recipient(lease: Lease) -> dict[str, str]:
    """Resolve the PIX recipient (key, type, merchant name, city) for a lease.

    Resolution rules:
      - PIX key/type/name: the apartment owner's key (kitnet) when present;
        otherwise the FinancialSettings default key/type with the active
        landlord's name (falling back to the "Condomínio" default name).
      - City: the active landlord's city, then FinancialSettings.default_city,
        then the module default (Porto Alegre).
    """
    apartment = lease.apartment
    owner = apartment.owner

    if owner and owner.pix_key:
        pix_key = owner.pix_key
        pix_key_type = owner.pix_key_type
        merchant_name = owner.name
    else:
        pix_key = ""
        pix_key_type = ""
        merchant_name = _DEFAULT_MERCHANT_NAME

    settings_obj = FinancialSettings.objects.filter(pk=1).first()
    landlord = Landlord.get_active()

    if not (owner and owner.pix_key):
        if settings_obj and settings_obj.default_pix_key:
            pix_key = settings_obj.default_pix_key
            pix_key_type = settings_obj.default_pix_key_type
        if landlord:
            merchant_name = landlord.name

    return {
        "pix_key": pix_key,
        "pix_key_type": pix_key_type,
        "merchant_name": merchant_name,
        "city": _resolve_city(landlord, settings_obj),
    }
