"""Single money-quantization helper for the finances output boundary (design §4).

Services/annotations sum raw Decimals; the quantization to 2 places (ROUND_HALF_UP)
happens once here, at the serializer/service output boundary — identical everywhere so
the dashboard and projection can never differ by a cent.
"""

from decimal import ROUND_HALF_UP, Decimal


def money_str(value: object) -> str:
    """Quantize a money value to 2 decimal places and render it as a string."""
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
