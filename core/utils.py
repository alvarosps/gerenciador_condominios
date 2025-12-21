"""
Utility functions for Condomínios Manager.

This module provides helper functions for:
- Currency formatting (Brazilian Real)
- Number to words conversion (Portuguese)
"""
from decimal import Decimal
from typing import Union

from num2words import num2words


def number_to_words(value: Union[int, float, Decimal]) -> str:
    """
    Convert a number to its word representation in Portuguese (BR).

    Args:
        value: Numeric value to convert to words

    Returns:
        Word representation of the number in Portuguese

    Examples:
        >>> number_to_words(1500)
        'mil e quinhentos'
        >>> number_to_words(1500.50)
        'mil e quinhentos vírgula cinquenta'
    """
    try:
        return str(num2words(float(value), lang="pt_BR"))
    except Exception as e:
        print(f"Erro ao converter número para extenso: {e}")
        return str(value)


def format_currency(value: Union[int, float, Decimal]) -> str:
    """
    Format a numeric value as Brazilian currency (R$).

    Args:
        value: Numeric value to format (int, float, or Decimal)

    Returns:
        Formatted currency string in Brazilian format (e.g., "R$1.500,00")

    Examples:
        >>> format_currency(1500)
        'R$1.500,00'
        >>> format_currency(1500.50)
        'R$1.500,50'
        >>> format_currency(Decimal('1500.00'))
        'R$1.500,00'
    """
    return f"R${value:,.2f}"
