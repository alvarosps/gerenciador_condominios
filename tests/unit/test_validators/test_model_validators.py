"""
Unit tests for model validators.

Tests validation logic for model fields and cross-field validation.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

import pytest

from core.validators.model_validators import (
    validate_date_range,
    validate_due_day,
    validate_lease_dates,
    validate_rental_value,
    validate_tenant_count,
)


class TestValidateDueDay:
    """Test due day validation."""

    def test_valid_due_day_start_of_month(self):
        """Test validation of day 1."""
        validate_due_day(1)  # Should not raise

    def test_valid_due_day_middle_of_month(self):
        """Test validation of middle days."""
        validate_due_day(15)  # Should not raise
        validate_due_day(20)  # Should not raise

    def test_valid_due_day_end_of_month(self):
        """Test validation of day 31."""
        validate_due_day(31)  # Should not raise

    def test_invalid_due_day_zero(self):
        """Test rejection of day 0."""
        with pytest.raises(ValidationError) as exc:
            validate_due_day(0)
        assert "between 1 and 31" in str(exc.value)

    def test_invalid_due_day_negative(self):
        """Test rejection of negative days."""
        with pytest.raises(ValidationError):
            validate_due_day(-1)

    def test_invalid_due_day_too_high(self):
        """Test rejection of day > 31."""
        with pytest.raises(ValidationError) as exc:
            validate_due_day(32)
        assert "between 1 and 31" in str(exc.value)

    def test_invalid_due_day_not_integer(self):
        """Test rejection of non-integer values."""
        with pytest.raises(ValidationError) as exc:
            validate_due_day("15")
        assert "must be an integer" in str(exc.value)

        with pytest.raises(ValidationError):
            validate_due_day(15.5)


class TestValidateDateRange:
    """Test date range validation."""

    def test_valid_date_range(self):
        """Test validation of valid date range."""
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        validate_date_range(start, end)  # Should not raise

    def test_valid_date_range_one_day_apart(self):
        """Test validation when dates are one day apart."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 2)
        validate_date_range(start, end)  # Should not raise

    def test_invalid_date_range_same_date(self):
        """Test rejection when start and end are the same."""
        same_date = date(2025, 1, 1)
        with pytest.raises(ValidationError) as exc:
            validate_date_range(same_date, same_date)
        assert "must be after start date" in str(exc.value)

    def test_invalid_date_range_end_before_start(self):
        """Test rejection when end is before start."""
        start = date(2025, 12, 31)
        end = date(2025, 1, 1)
        with pytest.raises(ValidationError) as exc:
            validate_date_range(start, end)
        assert "must be after start date" in str(exc.value)

    def test_custom_field_name_in_error(self):
        """Test that custom field name appears in error message."""
        start = date(2025, 12, 31)
        end = date(2025, 1, 1)
        with pytest.raises(ValidationError) as exc:
            validate_date_range(start, end, field_name="final_date")
        assert "final_date" in str(exc.value)


class TestValidateRentalValue:
    """Test rental value validation."""

    def test_valid_rental_value_typical(self):
        """Test validation of typical rental values."""
        validate_rental_value(1500.00)  # Should not raise
        validate_rental_value(2000.00)  # Should not raise
        validate_rental_value(500.00)  # Should not raise

    def test_valid_rental_value_minimum(self):
        """Test validation at minimum threshold."""
        validate_rental_value(100.00)  # Should not raise

    def test_valid_rental_value_maximum(self):
        """Test validation at maximum threshold."""
        validate_rental_value(100000.00)  # Should not raise

    def test_invalid_rental_value_negative(self):
        """Test rejection of negative values."""
        with pytest.raises(ValidationError) as exc:
            validate_rental_value(-100.00)
        assert "cannot be negative" in str(exc.value)

    def test_invalid_rental_value_too_low(self):
        """Test rejection of unreasonably low values."""
        with pytest.raises(ValidationError) as exc:
            validate_rental_value(50.00)
        assert "too low" in str(exc.value)

    def test_invalid_rental_value_too_high(self):
        """Test rejection of unreasonably high values."""
        with pytest.raises(ValidationError) as exc:
            validate_rental_value(200000.00)
        assert "too high" in str(exc.value)


@pytest.mark.django_db
class TestValidateLeaseDates:
    """Test lease date validation (requires database for models)."""

    def test_valid_lease_dates(self):
        """Test validation of valid lease dates."""
        from core.models import Apartment, Building, Lease, Tenant

        # Create minimal test data
        building = Building.objects.create(street_number=999, name="Test Building", address="Test Address")
        apartment = Apartment.objects.create(
            building=building,
            number=101,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Test Tenant",
            cpf_cnpj="111.444.777-35",  # Valid CPF format
            phone="11987654321",
            marital_status="Solteiro(a)",
            profession="Engenheiro",
        )

        lease = Lease(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 15),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        validate_lease_dates(lease)  # Should not raise

    def test_invalid_lease_zero_validity(self):
        """Test rejection of zero validity months."""
        from core.models import Apartment, Building, Lease, Tenant

        building = Building.objects.create(street_number=998, name="Test Building 2", address="Test Address 2")
        apartment = Apartment.objects.create(
            building=building,
            number=102,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Test Tenant 2",
            cpf_cnpj="11.222.333/0001-81",  # Valid CNPJ format
            phone="11987654322",
            marital_status="Casado(a)",
            profession="Professor",
            is_company=True,  # CNPJ requires is_company=True
        )

        lease = Lease(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 15),
            validity_months=0,  # Invalid
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        with pytest.raises(ValidationError) as exc:
            validate_lease_dates(lease)
        assert "at least 1 month" in str(exc.value)

    def test_invalid_lease_excessive_validity(self):
        """Test rejection of excessive validity months."""
        from core.models import Apartment, Building, Lease, Tenant

        building = Building.objects.create(street_number=997, name="Test Building 3", address="Test Address 3")
        apartment = Apartment.objects.create(
            building=building,
            number=103,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Test Tenant 3",
            cpf_cnpj="222.555.888-46",  # Valid CPF format
            phone="11987654323",
            marital_status="Divorciado(a)",
            profession="Médico",
        )

        lease = Lease(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 15),
            validity_months=72,  # > 60 months
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        with pytest.raises(ValidationError) as exc:
            validate_lease_dates(lease)
        assert "cannot exceed 60 months" in str(exc.value)

    def test_invalid_lease_old_start_date(self):
        """Test rejection of very old start dates."""
        from core.models import Apartment, Building, Lease, Tenant

        building = Building.objects.create(street_number=996, name="Test Building 4", address="Test Address 4")
        apartment = Apartment.objects.create(
            building=building,
            number=104,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Test Tenant 4",
            cpf_cnpj="333.666.999-57",  # Valid CPF format
            phone="11987654324",
            marital_status="Viúvo(a)",
            profession="Arquiteto",
        )

        lease = Lease(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2000, 1, 1),  # More than 10 years ago
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
        )

        with pytest.raises(ValidationError) as exc:
            validate_lease_dates(lease)
        assert "10 years in the past" in str(exc.value)


@pytest.mark.django_db
class TestValidateTenantCount:
    """Test tenant count validation (requires database)."""

    def test_valid_tenant_count_match(self):
        """Test validation when count matches actual tenants."""
        from core.models import Apartment, Building, Lease, Tenant

        building = Building.objects.create(street_number=995, name="Test Building 5", address="Test Address 5")
        apartment = Apartment.objects.create(
            building=building,
            number=105,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=3,
        )
        tenant1 = Tenant.objects.create(
            name="Tenant 1",
            cpf_cnpj="444.777.000-83",  # Valid CPF format
            phone="11987654325",
            marital_status="Solteiro(a)",
            profession="Engenheiro",
        )
        tenant2 = Tenant.objects.create(
            name="Tenant 2",
            cpf_cnpj="555.888.111-94",  # Valid CPF format
            phone="11987654326",
            marital_status="Casado(a)",
            profession="Professor",
        )

        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant1,
            start_date=date(2025, 1, 15),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("80.00"),
            number_of_tenants=2,
        )
        lease.tenants.add(tenant1, tenant2)

        validate_tenant_count(lease)  # Should not raise

    def test_invalid_tenant_count_mismatch(self):
        """Test rejection when count doesn't match actual tenants."""
        from core.models import Apartment, Building, Lease, Tenant

        building = Building.objects.create(street_number=994, name="Test Building 6", address="Test Address 6")
        apartment = Apartment.objects.create(
            building=building,
            number=106,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=3,
        )
        tenant1 = Tenant.objects.create(
            name="Tenant 3",
            cpf_cnpj="666.999.222-03",
            phone="11987654327",
            marital_status="Solteiro(a)",
            profession="Médico",
        )
        tenant2 = Tenant.objects.create(
            name="Tenant 4",
            cpf_cnpj="777.000.333-40",
            phone="11987654328",
            marital_status="Casado(a)",
            profession="Advogado",
        )

        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant1,
            start_date=date(2025, 1, 15),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
            number_of_tenants=1,  # Says 1, but we'll add 2
        )
        lease.tenants.add(tenant1, tenant2)

        with pytest.raises(ValidationError) as exc:
            validate_tenant_count(lease)
        assert "cannot be less than actual registered tenant count" in str(exc.value)

    def test_tenant_count_validation_skipped_for_unsaved_lease(self):
        """Test that validation is skipped for unsaved leases."""
        from core.models import Apartment, Building, Lease, Tenant

        building = Building.objects.create(street_number=993, name="Test Building 7", address="Test Address 7")
        apartment = Apartment.objects.create(
            building=building,
            number=107,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Tenant 5",
            cpf_cnpj="888.111.444-50",  # Valid CPF format
            phone="11987654329",
            marital_status="Solteiro(a)",
            profession="Designer",
        )

        # Create lease without saving
        lease = Lease(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 15),
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("50.00"),
            number_of_tenants=99,  # Invalid, but should not be checked yet
        )

        # Should not raise because lease is not saved (no pk)
        validate_tenant_count(lease)
