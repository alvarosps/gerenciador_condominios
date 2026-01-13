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
    # Validator classes
    "CPFValidator",
    "CNPJValidator",
    "BrazilianPhoneValidator",
    # Brazilian field validators
    "validate_cpf",
    "validate_cnpj",
    "validate_brazilian_phone",
    # Model validators
    "validate_due_day",
    "validate_date_range",
    "validate_lease_dates",
    "validate_tenant_count",
    "validate_rental_value",
]
