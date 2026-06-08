"""Single money-quantization helper for the finances output boundary (design §4).

Services/annotations sum raw Decimals; the quantization to 2 places (ROUND_HALF_UP)
happens once here, at the serializer/service output boundary — identical everywhere so
the dashboard and projection can never differ by a cent.
"""

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def quantize_money(value: object) -> Decimal:
    """Quantize a money value to 2 decimal places (ROUND_HALF_UP) — single output boundary.

    Internal sums stay raw; every figure exposed by a service or frozen on a
    CondoMonthClose passes through here, so the dashboard and the close can never differ
    by a cent (design §4).
    """
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def money_str(value: object) -> str:
    """Quantize a money value to 2 decimal places and render it as a string."""
    return str(quantize_money(value))
