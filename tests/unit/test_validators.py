"""Tests for Brazilian validators and model-level validators."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from core.validators.brazilian import (
    BrazilianPhoneValidator,
    CNPJValidator,
    CPFValidator,
    validate_brazilian_phone,
    validate_cnpj,
    validate_cpf,
)
from core.validators.model_validators import (
    validate_date_range,
    validate_due_day,
    validate_rental_value,
)


# =============================================================================
# CPFValidator
# =============================================================================


@pytest.mark.unit
class TestCPFValidator:
    def test_valid_cpf_formatted(self) -> None:
        validator = CPFValidator()
        result = validator("529.982.247-25")
        assert result == "52998224725"

    def test_valid_cpf_raw(self) -> None:
        validator = CPFValidator()
        result = validator("52998224725")
        assert result == "52998224725"

    def test_invalid_cpf_checksum(self) -> None:
        validator = CPFValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator("111.444.777-00")
        assert exc_info.value.code == "invalid_cpf"

    def test_all_same_digits_invalid(self) -> None:
        validator = CPFValidator()
        with pytest.raises(ValidationError):
            validator("111.111.111-11")

    def test_wrong_length_invalid(self) -> None:
        validator = CPFValidator()
        with pytest.raises(ValidationError):
            validator("123456789")  # only 9 digits

    def test_empty_value_returns_none(self) -> None:
        validator = CPFValidator()
        assert validator("") == ""

    def test_none_value_returns_none(self) -> None:
        validator = CPFValidator()
        assert validator(None) is None

    def test_clean_removes_formatting(self) -> None:
        assert CPFValidator.clean("529.982.247-25") == "52998224725"

    def test_calculate_checksum_digit(self) -> None:
        # Known good: first digit of 52998224725
        digit = CPFValidator.calculate_checksum_digit("529982247", 10)
        assert digit == 2

    def test_validate_function_convenience(self) -> None:
        """validate_cpf function wrapper should work."""
        validate_cpf("529.982.247-25")  # no exception

    def test_validate_function_raises_for_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_cpf("000.000.000-00")

    def test_valid_cpf_another_known_valid(self) -> None:
        """Known-valid CPF: 987.654.321-00."""
        validator = CPFValidator()
        result = validator("98765432100")
        assert result == "98765432100"


# =============================================================================
# CNPJValidator
# =============================================================================


@pytest.mark.unit
class TestCNPJValidator:
    def test_valid_cnpj_formatted(self) -> None:
        validator = CNPJValidator()
        result = validator("11.222.333/0001-81")
        assert result == "11222333000181"

    def test_valid_cnpj_raw(self) -> None:
        validator = CNPJValidator()
        result = validator("11222333000181")
        assert result == "11222333000181"

    def test_invalid_cnpj_checksum(self) -> None:
        validator = CNPJValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator("11.222.333/0001-00")
        assert exc_info.value.code == "invalid_cnpj"

    def test_all_same_digits_invalid(self) -> None:
        validator = CNPJValidator()
        with pytest.raises(ValidationError):
            validator("11.111.111/1111-11")

    def test_wrong_length_invalid(self) -> None:
        validator = CNPJValidator()
        with pytest.raises(ValidationError):
            validator("1122233300018")  # 13 digits

    def test_empty_value_returns_value(self) -> None:
        validator = CNPJValidator()
        assert validator("") == ""

    def test_none_value_returns_none(self) -> None:
        validator = CNPJValidator()
        assert validator(None) is None

    def test_clean_removes_formatting(self) -> None:
        assert CNPJValidator.clean("11.222.333/0001-81") == "11222333000181"

    def test_validate_function_convenience(self) -> None:
        validate_cnpj("11.222.333/0001-81")  # no exception

    def test_validate_function_raises_for_invalid(self) -> None:
        with pytest.raises(ValidationError):
            validate_cnpj("11.111.111/1111-11")


# =============================================================================
# BrazilianPhoneValidator
# =============================================================================


@pytest.mark.unit
class TestBrazilianPhoneValidator:
    def test_valid_mobile_formatted(self) -> None:
        validator = BrazilianPhoneValidator()
        validator("(11) 98765-4321")  # no exception

    def test_valid_landline_formatted(self) -> None:
        validator = BrazilianPhoneValidator()
        validator("(11) 3456-7890")  # no exception

    def test_valid_raw_11_digits(self) -> None:
        validator = BrazilianPhoneValidator()
        validator("11987654321")  # no exception

    def test_empty_value_no_exception(self) -> None:
        validator = BrazilianPhoneValidator()
        validator("")  # no exception — returns early

    def test_none_value_no_exception(self) -> None:
        validator = BrazilianPhoneValidator()
        validator(None)  # no exception

    def test_invalid_area_code_too_low(self) -> None:
        validator = BrazilianPhoneValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator("(10) 98765-4321")
        assert exc_info.value.code == "invalid_area_code"

    def test_invalid_format_raises(self) -> None:
        validator = BrazilianPhoneValidator()
        with pytest.raises(ValidationError):
            validator("not-a-phone")

    def test_clean_removes_formatting(self) -> None:
        assert BrazilianPhoneValidator.clean("(11) 98765-4321") == "11987654321"

    def test_convenience_function(self) -> None:
        validate_brazilian_phone("(11) 98765-4321")  # no exception

    def test_convenience_function_raises(self) -> None:
        with pytest.raises(ValidationError):
            validate_brazilian_phone("not-a-phone")


# =============================================================================
# Model-level validators
# =============================================================================


@pytest.mark.unit
class TestValidateDueDay:
    def test_valid_due_day(self) -> None:
        validate_due_day(1)
        validate_due_day(15)
        validate_due_day(31)

    def test_due_day_zero_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_due_day(0)
        assert exc_info.value.code == "invalid_due_day"

    def test_due_day_above_31_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_due_day(32)
        assert exc_info.value.code == "invalid_due_day"


@pytest.mark.unit
class TestValidateDateRange:
    def test_valid_date_range(self) -> None:
        validate_date_range(date(2025, 1, 1), date(2025, 12, 31))  # no exception

    def test_equal_dates_raises(self) -> None:
        with pytest.raises(ValidationError):
            validate_date_range(date(2025, 1, 1), date(2025, 1, 1))

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValidationError):
            validate_date_range(date(2025, 12, 31), date(2025, 1, 1))

    def test_custom_field_name_in_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range(date(2025, 1, 1), date(2024, 1, 1), field_name="custom_end")
        # Error dict key should be the field name
        assert "custom_end" in exc_info.value.message_dict


@pytest.mark.unit
class TestValidateRentalValue:
    def test_valid_value(self) -> None:
        validate_rental_value(1500.0)  # no exception

    def test_negative_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            validate_rental_value(-1.0)

    def test_too_low_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_rental_value(50.0)
        assert exc_info.value.code == "rental_value_too_low"

    def test_too_high_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_rental_value(200_000.0)
        assert exc_info.value.code == "rental_value_too_high"

    def test_boundary_min(self) -> None:
        validate_rental_value(100.0)  # exactly min, no exception

    def test_boundary_max(self) -> None:
        validate_rental_value(100_000.0)  # exactly max, no exception
