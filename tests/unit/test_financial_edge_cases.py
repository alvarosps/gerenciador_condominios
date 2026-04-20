"""Financial edge case tests — boundary values, constraint violations, cash flow exclusions."""

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import IntegrityError

from core.models import (
    Apartment,
    Building,
    Lease,
    RentPayment,
    Tenant,
)
from core.services.cash_flow_service import CashFlowService
from core.services.fee_calculator import FeeCalculatorService

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# =============================================================================
# TestFeeCalculatorEdgeCases
# =============================================================================


class TestFeeCalculatorEdgeCases:
    def test_late_fee_zero_days(self) -> None:
        """On the due day itself — not late, fee is zero."""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_day=15,
            current_date=date(2026, 3, 15),
        )
        assert result["is_late"] is False
        assert result["late_days"] == 0
        assert result["late_fee"] == Decimal("0.00")

    def test_late_fee_one_day(self) -> None:
        """1 day late: fee = daily_rate × 1 × LATE_FEE_PERCENTAGE."""
        rental_value = Decimal("1500.00")
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=rental_value,
            due_day=10,
            current_date=date(2026, 3, 11),
        )
        daily_rate = rental_value / Decimal(str(settings.DAYS_PER_MONTH))
        expected = daily_rate * 1 * Decimal(str(settings.LATE_FEE_PERCENTAGE))
        assert result["is_late"] is True
        assert result["late_days"] == 1
        assert result["late_fee"] == expected

    def test_late_fee_30_days(self) -> None:
        """30 days late (due day 1, current day 31 same month)."""
        rental_value = Decimal("900.00")
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=rental_value,
            due_day=1,
            current_date=date(2026, 3, 31),
        )
        daily_rate = rental_value / Decimal(str(settings.DAYS_PER_MONTH))
        expected = daily_rate * 30 * Decimal(str(settings.LATE_FEE_PERCENTAGE))
        assert result["late_days"] == 30
        assert result["late_fee"] == expected

    def test_daily_rate_large_value(self) -> None:
        """R$999,999.99 should not raise and produce a positive rate."""
        rate = FeeCalculatorService.calculate_daily_rate(Decimal("999999.99"))
        assert rate > Decimal(0)
        assert isinstance(rate, Decimal)

    def test_daily_rate_one_cent(self) -> None:
        """R$0.01 should return a positive (but tiny) daily rate."""
        rate = FeeCalculatorService.calculate_daily_rate(Decimal("0.01"))
        assert rate > Decimal(0)

    def test_tag_fee_one_tenant(self) -> None:
        """Single tenant returns DEFAULT_TAG_FEE_SINGLE (R$50)."""
        fee = FeeCalculatorService.calculate_tag_fee(1)
        assert fee == Decimal(str(settings.DEFAULT_TAG_FEE_SINGLE))

    def test_tag_fee_two_tenants(self) -> None:
        """Two tenants returns DEFAULT_TAG_FEE_MULTIPLE (R$80)."""
        fee = FeeCalculatorService.calculate_tag_fee(2)
        assert fee == Decimal(str(settings.DEFAULT_TAG_FEE_MULTIPLE))

    def test_tag_fee_many_tenants(self) -> None:
        """10 tenants still returns DEFAULT_TAG_FEE_MULTIPLE (R$80)."""
        fee = FeeCalculatorService.calculate_tag_fee(10)
        assert fee == Decimal(str(settings.DEFAULT_TAG_FEE_MULTIPLE))

    def test_tag_fee_zero_raises(self) -> None:
        """Zero tenants raises ValueError."""
        with pytest.raises(ValueError, match="at least 1"):
            FeeCalculatorService.calculate_tag_fee(0)

    def test_total_value_sum(self) -> None:
        """Total = rental + cleaning + tag."""
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("80.00"),
        )
        assert total == Decimal("1780.00")

    def test_due_date_change_forward(self) -> None:
        """Changing due date from day 10 to day 20 within same month."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1500.00"),
            current_due_day=10,
            new_due_day=20,
            reference_date=date(2026, 3, 1),
        )
        assert result["old_due_date"] == date(2026, 3, 10)
        assert result["new_due_date"] == date(2026, 3, 20)
        # inclusive count: 20 - 10 + 1 = 11 days
        assert result["days_difference"] == 11
        assert result["total_due"] == Decimal("1500.00") + result["fee"]

    def test_due_date_change_backward_wraps(self) -> None:
        """Changing from day 22 to day 5 wraps to next month."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1250.00"),
            current_due_day=22,
            new_due_day=5,
            reference_date=date(2026, 3, 1),
        )
        assert result["old_due_date"] == date(2026, 3, 22)
        assert result["new_due_date"] == date(2026, 4, 5)
        # (Apr 5 - Mar 22) + 1 = 14 + 1 = 15 days
        assert result["days_difference"] == 15

    def test_due_date_clamped_short_month(self) -> None:
        """Day 31 clamped to Feb 28 (non-leap year 2026)."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1000.00"),
            current_due_day=10,
            new_due_day=31,
            reference_date=date(2026, 2, 1),
        )
        # Feb 2026 has 28 days — day 31 clamped to 28
        assert result["new_due_date"] == date(2026, 2, 28)


# =============================================================================
# TestCashFlowEdgeCases
# =============================================================================


class TestCashFlowEdgeCases:
    def test_monthly_income_empty_db(self) -> None:
        """With no leases or income records, returns zero totals."""
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["rent_income"] == Decimal("0.00")
        assert result["extra_income"] == Decimal("0.00")
        assert result["total"] == Decimal("0.00")
        assert result["rent_details"] == []

    def test_excludes_owner_apartments(self) -> None:
        """Apartments with an owner are excluded from condominium income."""
        owner = _make_person("Owner")
        building = Building.objects.create(
            street_number=701, name="Owner Building", address="Rua Owner, 701"
        )
        apt = Apartment.objects.create(
            building=building,
            number=10,
            rental_value=Decimal("2000.00"),
            max_tenants=2,
            is_rented=True,
            owner=owner,
        )
        tenant = _make_tenant("Owner Tenant", "11122233396")
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("2000.00"),
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["rent_income"] == Decimal("0.00")

    def test_excludes_salary_offset(self) -> None:
        """Leases with is_salary_offset=True are excluded from condominium income."""
        building = Building.objects.create(
            street_number=702, name="Salary Building", address="Rua Salary, 702"
        )
        apt = Apartment.objects.create(
            building=building,
            number=20,
            rental_value=Decimal("1800.00"),
            max_tenants=2,
            is_rented=True,
        )
        tenant = _make_tenant("Salary Tenant", "98765432100")
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1800.00"),
            is_salary_offset=True,
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["rent_income"] == Decimal("0.00")


# =============================================================================
# TestRentPaymentConstraints
# =============================================================================


class TestRentPaymentConstraints:
    def test_duplicate_raises_integrity_error(self) -> None:
        """Same lease + reference_month combination violates unique constraint."""
        building = Building.objects.create(
            street_number=801, name="Constraint Building", address="Rua C, 801"
        )
        apt = Apartment.objects.create(
            building=building, number=101, rental_value=Decimal("1200.00"), max_tenants=2
        )
        tenant = _make_tenant("Dup Tenant", "11144477735")
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1200.00"),
        )
        RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1200.00"),
            payment_date=date(2026, 3, 10),
        )
        with pytest.raises(IntegrityError):
            RentPayment.objects.create(
                lease=lease,
                reference_month=date(2026, 3, 1),
                amount_paid=Decimal("1200.00"),
                payment_date=date(2026, 3, 11),
            )

    def test_different_months_allowed(self) -> None:
        """Same lease with different reference_months is valid."""
        building = Building.objects.create(
            street_number=802, name="Multi Month Building", address="Rua M, 802"
        )
        apt = Apartment.objects.create(
            building=building, number=201, rental_value=Decimal("1300.00"), max_tenants=2
        )
        tenant = _make_tenant("Multi Tenant", "44455566619")
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=24,
            rental_value=Decimal("1300.00"),
        )
        rp1 = RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1300.00"),
            payment_date=date(2026, 3, 10),
        )
        rp2 = RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 4, 1),
            amount_paid=Decimal("1300.00"),
            payment_date=date(2026, 4, 10),
        )
        assert rp1.pk != rp2.pk


# =============================================================================
# Helpers
# =============================================================================


def _make_person(name: str):
    from core.models import Person

    return Person.objects.create(name=name, relationship="Familiar")


def _make_tenant(name: str, cpf: str) -> Tenant:
    return Tenant.objects.create(
        name=name,
        cpf_cnpj=cpf,
        phone="11987654321",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=10,
    )
