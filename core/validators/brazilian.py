"""
Brazilian data format validators.

Provides validation for CPF, CNPJ, and Brazilian phone numbers.
These validators handle formatting, length checks, and checksum validation
according to Brazilian government standards.
"""
from __future__ import annotations

import re
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class CPFValidator:
    """
    Validator for Brazilian CPF (Cadastro de Pessoas Físicas).

    CPF is an 11-digit individual taxpayer ID with checksum validation.
    Format: XXX.XXX.XXX-XX (formatted) or XXXXXXXXXXX (raw)

    Example:
        >>> validator = CPFValidator()
        >>> validator('111.444.777-35')  # Valid
        >>> validator('11144477735')     # Valid (raw format)
        >>> validator('111.444.777-00')  # Raises ValidationError (invalid checksum)
    """

    message = "CPF inválido. Formato esperado: XXX.XXX.XXX-XX ou 11 dígitos."
    code = "invalid_cpf"

    @staticmethod
    def clean(value: str) -> str:
        """
        Remove formatting characters from CPF.

        Args:
            value: CPF string (formatted or raw)

        Returns:
            CPF with only digits

        Example:
            >>> CPFValidator.clean('111.444.777-35')
            '11144477735'
        """
        return re.sub(r"[^0-9]", "", value)

    @staticmethod
    def calculate_checksum_digit(cpf_digits: str, position: int) -> int:
        """
        Calculate a CPF checksum digit.

        Args:
            cpf_digits: First 9 (for first digit) or 10 (for second digit) digits
            position: Position of the digit to calculate (10 for first, 11 for second)

        Returns:
            Checksum digit (0-9)
        """
        total = sum(int(cpf_digits[i]) * (position - i) for i in range(len(cpf_digits)))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    def validate(self, value: str) -> bool:
        """
        Validate CPF checksum.

        Args:
            value: Clean CPF (11 digits, no formatting)

        Returns:
            True if valid, False otherwise
        """
        if len(value) != 11:
            return False

        # Check if all digits are the same (invalid CPFs like 111.111.111-11)
        if len(set(value)) == 1:
            return False

        # Validate first checksum digit
        first_digit = self.calculate_checksum_digit(value[:9], 10)
        if first_digit != int(value[9]):
            return False

        # Validate second checksum digit
        second_digit = self.calculate_checksum_digit(value[:10], 11)
        if second_digit != int(value[10]):
            return False

        return True

    def __call__(self, value: Optional[str]) -> str:
        """
        Validate and clean CPF.

        Args:
            value: CPF string to validate

        Returns:
            Cleaned CPF (digits only)

        Raises:
            ValidationError: If CPF is invalid
        """
        if not value:
            return value

        cleaned = self.clean(value)

        if not self.validate(cleaned):
            raise ValidationError(self.message, code=self.code)

        return cleaned


class CNPJValidator:
    """
    Validator for Brazilian CNPJ (Cadastro Nacional de Pessoa Jurídica).

    CNPJ is a 14-digit company taxpayer ID with checksum validation.
    Format: XX.XXX.XXX/XXXX-XX (formatted) or XXXXXXXXXXXXXX (raw)

    Example:
        >>> validator = CNPJValidator()
        >>> validator('11.222.333/0001-81')  # Valid
        >>> validator('11222333000181')      # Valid (raw format)
        >>> validator('11.222.333/0001-00')  # Raises ValidationError (invalid checksum)
    """

    message = "CNPJ inválido. Formato esperado: XX.XXX.XXX/XXXX-XX ou 14 dígitos."
    code = "invalid_cnpj"

    @staticmethod
    def clean(value: str) -> str:
        """
        Remove formatting characters from CNPJ.

        Args:
            value: CNPJ string (formatted or raw)

        Returns:
            CNPJ with only digits

        Example:
            >>> CNPJValidator.clean('11.222.333/0001-81')
            '11222333000181'
        """
        return re.sub(r"[^0-9]", "", value)

    @staticmethod
    def calculate_checksum_digit(cnpj_digits: str, weights: list[int]) -> int:
        """
        Calculate a CNPJ checksum digit.

        Args:
            cnpj_digits: First 12 (for first digit) or 13 (for second digit) digits
            weights: Weight sequence for calculation

        Returns:
            Checksum digit (0-9)
        """
        total = sum(int(cnpj_digits[i]) * weights[i] for i in range(len(cnpj_digits)))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    def validate(self, value: str) -> bool:
        """
        Validate CNPJ checksum.

        Args:
            value: Clean CNPJ (14 digits, no formatting)

        Returns:
            True if valid, False otherwise
        """
        if len(value) != 14:
            return False

        # Check if all digits are the same (invalid CNPJs)
        if len(set(value)) == 1:
            return False

        # Validate first checksum digit
        first_weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        first_digit = self.calculate_checksum_digit(value[:12], first_weights)
        if first_digit != int(value[12]):
            return False

        # Validate second checksum digit
        second_weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        second_digit = self.calculate_checksum_digit(value[:13], second_weights)
        if second_digit != int(value[13]):
            return False

        return True

    def __call__(self, value: Optional[str]) -> str:
        """
        Validate and clean CNPJ.

        Args:
            value: CNPJ string to validate

        Returns:
            Cleaned CNPJ (digits only)

        Raises:
            ValidationError: If CNPJ is invalid
        """
        if not value:
            return value

        cleaned = self.clean(value)

        if not self.validate(cleaned):
            raise ValidationError(self.message, code=self.code)

        return cleaned


class BrazilianPhoneValidator(RegexValidator):
    """
    Validator for Brazilian phone numbers.

    Accepts both landline and mobile formats:
    - Mobile: (XX) 9XXXX-XXXX (11 digits with area code)
    - Landline: (XX) XXXX-XXXX (10 digits with area code)

    Example:
        >>> validator = BrazilianPhoneValidator()
        >>> validator('(11) 98765-4321')  # Valid mobile
        >>> validator('(11) 3456-7890')   # Valid landline
        >>> validator('11987654321')      # Valid (raw format)
    """

    regex = r"^(\(?\d{2}\)?\s?)?(\d{4,5})-?(\d{4})$"
    message = "Telefone inválido. Formato esperado: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX"
    code = "invalid_phone"

    def __init__(self, *args, **kwargs):
        """Initialize phone validator with Brazilian format regex."""
        super().__init__(regex=self.regex, message=self.message, code=self.code)

    @staticmethod
    def clean(value: str) -> str:
        """
        Remove formatting characters from phone number.

        Args:
            value: Phone string (formatted or raw)

        Returns:
            Phone with only digits

        Example:
            >>> BrazilianPhoneValidator.clean('(11) 98765-4321')
            '11987654321'
        """
        return re.sub(r"[^0-9]", "", value)

    def __call__(self, value: Optional[str]) -> str:
        """
        Validate Brazilian phone number.

        Args:
            value: Phone string to validate

        Returns:
            Original value if valid

        Raises:
            ValidationError: If phone format is invalid
        """
        if not value:
            return value

        # Use parent regex validation
        super().__call__(value)

        # Additional validation: check digit count
        cleaned = self.clean(value)
        if len(cleaned) not in (10, 11):
            raise ValidationError(self.message, code=self.code)

        # Check area code (11-99)
        if len(cleaned) >= 2:
            area_code = int(cleaned[:2])
            if area_code < 11 or area_code > 99:
                raise ValidationError(
                    "Código de área inválido. Deve estar entre 11 e 99.", code="invalid_area_code"
                )

        return value


# Convenience functions for use in model validators parameter
def validate_cpf(value: str) -> None:
    """
    Django model field validator for CPF.

    Usage:
        cpf_cnpj = models.CharField(
            max_length=20,
            validators=[validate_cpf]
        )
    """
    CPFValidator()(value)


def validate_cnpj(value: str) -> None:
    """
    Django model field validator for CNPJ.

    Usage:
        cpf_cnpj = models.CharField(
            max_length=20,
            validators=[validate_cnpj]
        )
    """
    CNPJValidator()(value)


def validate_brazilian_phone(value: str) -> None:
    """
    Django model field validator for Brazilian phone numbers.

    Usage:
        phone = models.CharField(
            max_length=20,
            validators=[validate_brazilian_phone]
        )
    """
    BrazilianPhoneValidator()(value)
