"""
Unit tests for Brazilian validators.

Tests CPF, CNPJ, and phone number validation with comprehensive coverage
including valid cases, invalid cases, edge cases, and formatting.
"""
import pytest
from django.core.exceptions import ValidationError

from core.validators.brazilian import (
    CPFValidator,
    CNPJValidator,
    BrazilianPhoneValidator,
    validate_cpf,
    validate_cnpj,
    validate_brazilian_phone,
)


class TestCPFValidator:
    """Test CPF validation logic."""

    def test_valid_cpf_formatted(self):
        """Test validation of properly formatted valid CPF."""
        validator = CPFValidator()
        # Valid CPF: 111.444.777-35
        result = validator('111.444.777-35')
        assert result == '11144477735'

    def test_valid_cpf_raw(self):
        """Test validation of raw (unformatted) valid CPF."""
        validator = CPFValidator()
        result = validator('11144477735')
        assert result == '11144477735'

    def test_valid_cpf_various_formats(self):
        """Test validation with various formatting styles."""
        validator = CPFValidator()
        # All these should be valid for the same CPF
        assert validator('111.444.777-35') == '11144477735'
        assert validator('111444777-35') == '11144477735'
        assert validator('111.44477735') == '11144477735'

    def test_invalid_cpf_wrong_checksum(self):
        """Test rejection of CPF with invalid checksum."""
        validator = CPFValidator()
        with pytest.raises(ValidationError) as exc:
            validator('111.444.777-00')
        assert 'CPF inválido' in str(exc.value)

    def test_invalid_cpf_all_same_digits(self):
        """Test rejection of CPF with all same digits."""
        validator = CPFValidator()
        invalid_cpfs = [
            '000.000.000-00',
            '111.111.111-11',
            '222.222.222-22',
            '999.999.999-99',
        ]
        for cpf in invalid_cpfs:
            with pytest.raises(ValidationError):
                validator(cpf)

    def test_invalid_cpf_wrong_length(self):
        """Test rejection of CPF with wrong length."""
        validator = CPFValidator()
        with pytest.raises(ValidationError):
            validator('111.444.777')  # Too short

        with pytest.raises(ValidationError):
            validator('111.444.777-355')  # Too long

    def test_cpf_clean_method(self):
        """Test CPF cleaning (removing formatting)."""
        assert CPFValidator.clean('111.444.777-35') == '11144477735'
        assert CPFValidator.clean('111444777-35') == '11144477735'
        assert CPFValidator.clean('11144477735') == '11144477735'

    def test_cpf_checksum_calculation(self):
        """Test CPF checksum digit calculation."""
        # First digit of 111.444.777-35
        first_digit = CPFValidator.calculate_checksum_digit('111444777', 10)
        assert first_digit == 3

        # Second digit of 111.444.777-35
        second_digit = CPFValidator.calculate_checksum_digit('1114447773', 11)
        assert second_digit == 5

    def test_cpf_validate_method(self):
        """Test CPF validation method directly."""
        validator = CPFValidator()
        assert validator.validate('11144477735') is True
        assert validator.validate('11144477700') is False
        assert validator.validate('00000000000') is False
        assert validator.validate('123') is False

    def test_cpf_none_value(self):
        """Test CPF validator with None value."""
        validator = CPFValidator()
        assert validator(None) is None

    def test_cpf_empty_string(self):
        """Test CPF validator with empty string."""
        validator = CPFValidator()
        assert validator('') == ''

    def test_validate_cpf_function(self):
        """Test standalone validate_cpf function."""
        # Valid CPF should not raise
        validate_cpf('111.444.777-35')

        # Invalid CPF should raise
        with pytest.raises(ValidationError):
            validate_cpf('111.444.777-00')


class TestCNPJValidator:
    """Test CNPJ validation logic."""

    def test_valid_cnpj_formatted(self):
        """Test validation of properly formatted valid CNPJ."""
        validator = CNPJValidator()
        # Valid CNPJ: 11.222.333/0001-81
        result = validator('11.222.333/0001-81')
        assert result == '11222333000181'

    def test_valid_cnpj_raw(self):
        """Test validation of raw (unformatted) valid CNPJ."""
        validator = CNPJValidator()
        result = validator('11222333000181')
        assert result == '11222333000181'

    def test_invalid_cnpj_wrong_checksum(self):
        """Test rejection of CNPJ with invalid checksum."""
        validator = CNPJValidator()
        with pytest.raises(ValidationError) as exc:
            validator('11.222.333/0001-00')
        assert 'CNPJ inválido' in str(exc.value)

    def test_invalid_cnpj_all_same_digits(self):
        """Test rejection of CNPJ with all same digits."""
        validator = CNPJValidator()
        invalid_cnpjs = [
            '00.000.000/0000-00',
            '11.111.111/1111-11',
            '22.222.222/2222-22',
        ]
        for cnpj in invalid_cnpjs:
            with pytest.raises(ValidationError):
                validator(cnpj)

    def test_invalid_cnpj_wrong_length(self):
        """Test rejection of CNPJ with wrong length."""
        validator = CNPJValidator()
        with pytest.raises(ValidationError):
            validator('11.222.333/0001')  # Too short

        with pytest.raises(ValidationError):
            validator('11.222.333/0001-811')  # Too long

    def test_cnpj_clean_method(self):
        """Test CNPJ cleaning (removing formatting)."""
        assert CNPJValidator.clean('11.222.333/0001-81') == '11222333000181'
        assert CNPJValidator.clean('11222333/0001-81') == '11222333000181'
        assert CNPJValidator.clean('11222333000181') == '11222333000181'

    def test_cnpj_checksum_calculation(self):
        """Test CNPJ checksum digit calculation."""
        # First digit of 11.222.333/0001-81
        first_weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        first_digit = CNPJValidator.calculate_checksum_digit('112223330001', first_weights)
        assert first_digit == 8

        # Second digit of 11.222.333/0001-81
        second_weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        second_digit = CNPJValidator.calculate_checksum_digit('1122233300018', second_weights)
        assert second_digit == 1

    def test_cnpj_validate_method(self):
        """Test CNPJ validation method directly."""
        validator = CNPJValidator()
        assert validator.validate('11222333000181') is True
        assert validator.validate('11222333000100') is False
        assert validator.validate('00000000000000') is False
        assert validator.validate('123') is False

    def test_cnpj_none_value(self):
        """Test CNPJ validator with None value."""
        validator = CNPJValidator()
        assert validator(None) is None

    def test_cnpj_empty_string(self):
        """Test CNPJ validator with empty string."""
        validator = CNPJValidator()
        assert validator('') == ''

    def test_validate_cnpj_function(self):
        """Test standalone validate_cnpj function."""
        # Valid CNPJ should not raise
        validate_cnpj('11.222.333/0001-81')

        # Invalid CNPJ should raise
        with pytest.raises(ValidationError):
            validate_cnpj('11.222.333/0001-00')


class TestBrazilianPhoneValidator:
    """Test Brazilian phone number validation."""

    def test_valid_mobile_formatted(self):
        """Test validation of formatted mobile number."""
        validator = BrazilianPhoneValidator()
        validator('(11) 98765-4321')  # Should not raise

    def test_valid_mobile_raw(self):
        """Test validation of raw mobile number."""
        validator = BrazilianPhoneValidator()
        validator('11987654321')  # Should not raise

    def test_valid_landline_formatted(self):
        """Test validation of formatted landline number."""
        validator = BrazilianPhoneValidator()
        validator('(11) 3456-7890')  # Should not raise

    def test_valid_landline_raw(self):
        """Test validation of raw landline number."""
        validator = BrazilianPhoneValidator()
        validator('1134567890')  # Should not raise

    def test_valid_phone_various_area_codes(self):
        """Test validation with various Brazilian area codes."""
        validator = BrazilianPhoneValidator()
        area_codes = ['11', '21', '27', '31', '47', '85', '91']
        for code in area_codes:
            validator(f'({code}) 98765-4321')  # Should not raise
            validator(f'{code}987654321')  # Should not raise

    def test_invalid_phone_wrong_format(self):
        """Test rejection of incorrectly formatted phone."""
        validator = BrazilianPhoneValidator()
        with pytest.raises(ValidationError):
            validator('123')  # Too short

        with pytest.raises(ValidationError):
            validator('98765-4321')  # Missing area code

    def test_invalid_phone_wrong_length(self):
        """Test rejection of phone with wrong digit count."""
        validator = BrazilianPhoneValidator()
        with pytest.raises(ValidationError):
            validator('119876543')  # 9 digits (too short)

        with pytest.raises(ValidationError):
            validator('119876543210')  # 12 digits (too long)

    def test_invalid_area_code(self):
        """Test rejection of invalid area codes."""
        validator = BrazilianPhoneValidator()
        with pytest.raises(ValidationError):
            validator('(01) 98765-4321')  # Area code < 11

        with pytest.raises(ValidationError):
            validator('(00) 98765-4321')  # Invalid area code

    def test_phone_clean_method(self):
        """Test phone cleaning (removing formatting)."""
        assert BrazilianPhoneValidator.clean('(11) 98765-4321') == '11987654321'
        assert BrazilianPhoneValidator.clean('11 98765-4321') == '11987654321'
        assert BrazilianPhoneValidator.clean('11987654321') == '11987654321'

    def test_phone_none_value(self):
        """Test phone validator with None value."""
        validator = BrazilianPhoneValidator()
        assert validator(None) is None

    def test_phone_empty_string(self):
        """Test phone validator with empty string."""
        validator = BrazilianPhoneValidator()
        assert validator('') == ''

    def test_validate_brazilian_phone_function(self):
        """Test standalone validate_brazilian_phone function."""
        # Valid phone should not raise
        validate_brazilian_phone('(11) 98765-4321')

        # Invalid phone should raise
        with pytest.raises(ValidationError):
            validate_brazilian_phone('123')


class TestBrazilianValidatorsIntegration:
    """Integration tests for Brazilian validators."""

    def test_cpf_cnpj_distinction(self):
        """Test that CPF and CNPJ validators are distinct."""
        cpf_validator = CPFValidator()
        cnpj_validator = CNPJValidator()

        valid_cpf = '111.444.777-35'
        valid_cnpj = '11.222.333/0001-81'

        # CPF validator should accept CPF
        cpf_validator(valid_cpf)

        # CNPJ validator should accept CNPJ
        cnpj_validator(valid_cnpj)

        # CPF validator should reject CNPJ format
        with pytest.raises(ValidationError):
            cpf_validator(valid_cnpj)

        # CNPJ validator should reject CPF format
        with pytest.raises(ValidationError):
            cnpj_validator(valid_cpf)

    def test_all_validators_handle_none(self):
        """Test that all validators handle None gracefully."""
        assert CPFValidator()(None) is None
        assert CNPJValidator()(None) is None
        assert BrazilianPhoneValidator()(None) is None

    def test_all_validators_handle_empty_string(self):
        """Test that all validators handle empty strings."""
        assert CPFValidator()('') == ''
        assert CNPJValidator()('') == ''
        assert BrazilianPhoneValidator()('') == ''
