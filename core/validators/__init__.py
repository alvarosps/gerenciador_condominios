"""
Validators package for Condomínios Manager.

This package provides validators for Brazilian-specific data formats
and model-level validation logic.
"""

from .brazilian import (
    BrazilianPhoneValidator,
    CNPJValidator,
    CPFValidator,
    validate_brazilian_phone,
    validate_cnpj,
    validate_cpf,
)
from .model_validators import (
    validate_date_range,
    validate_due_day,
    validate_lease_dates,
    validate_rental_value,
    validate_tenant_count,
)

__all__ = [
    "BrazilianPhoneValidator",
    "CNPJValidator",
    # Validator classes
    "CPFValidator",
    "validate_brazilian_phone",
    "validate_cnpj",
    # Brazilian field validators
    "validate_cpf",
    "validate_date_range",
    # Model validators
    "validate_due_day",
    "validate_lease_dates",
    "validate_rental_value",
    "validate_tenant_count",
]
