import re
import secrets

from django.conf import settings
from twilio.rest import Client

_MSG_PHONE_MISSING = "Telefone não cadastrado"
# Minimum digit count for a Brazilian number that already includes country code (55)
_BRAZIL_COUNTRY_CODE_PREFIX = "55"
_MIN_DIGITS_WITH_COUNTRY_CODE = 12


def normalize_phone_to_e164(phone: str | None) -> str:
    """Normalize Brazilian phone to E.164 format (+5511999998888).

    Strips formatting (parens, spaces, dashes) and adds +55 if needed.
    Raises ValueError if phone is empty or None.
    """
    if not phone:
        raise ValueError(_MSG_PHONE_MISSING)

    digits = re.sub(r"\D", "", phone)

    if not digits:
        raise ValueError(_MSG_PHONE_MISSING)

    if (
        digits.startswith(_BRAZIL_COUNTRY_CODE_PREFIX)
        and len(digits) >= _MIN_DIGITS_WITH_COUNTRY_CODE
    ):
        return f"+{digits}"
    return f"+55{digits}"


def generate_verification_code() -> str:
    """Generate a cryptographically secure 6-digit verification code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def send_whatsapp_message(
    to_phone: str,
    template_sid: str,
    template_variables: dict[str, str],
) -> str:
    """Send a WhatsApp message via Twilio.

    Args:
        to_phone: E.164 formatted phone number
        template_sid: Twilio content template SID
        template_variables: Template variable substitutions

    Returns:
        Twilio message SID

    Raises:
        RuntimeError: If Twilio credentials are not configured
    """
    if not settings.TWILIO_ACCOUNT_SID:
        msg = "Twilio credentials not configured"
        raise RuntimeError(msg)

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
        to=f"whatsapp:{to_phone}",
        content_sid=template_sid,
        content_variables=template_variables,
    )
    return str(message.sid)


def send_verification_code(phone: str, code: str) -> str:
    """Send a verification code via WhatsApp."""
    return send_whatsapp_message(
        to_phone=phone,
        template_sid=settings.TWILIO_TEMPLATE_VERIFICATION,
        template_variables={"1": code},
    )


def send_rent_adjustment_notice(
    phone: str,
    property_address: str,
    old_value: str,
    new_value: str,
    percentage: str,
    effective_date: str,
) -> str:
    """Send rent adjustment notification via WhatsApp."""
    return send_whatsapp_message(
        to_phone=phone,
        template_sid=settings.TWILIO_TEMPLATE_RENT_ADJUSTMENT,
        template_variables={
            "1": property_address,
            "2": old_value,
            "3": new_value,
            "4": percentage,
            "5": effective_date,
        },
    )
