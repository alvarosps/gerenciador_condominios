"""Integration tests for the RentAdjustment feature.

Covers:
- RentAdjustmentService.apply_adjustment (calculation, validation, side effects)
- RentAdjustmentService.get_eligible_leases (filtering, reference date logic)
- POST /api/leases/{id}/adjust_rent/ endpoint
- GET /api/leases/{id}/rent_adjustments/ endpoint
- GET /api/dashboard/rent_adjustment_alerts/ endpoint
"""

from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Lease, RentAdjustment
from core.services.rent_adjustment_service import RentAdjustmentService

# Valid CPFs (checksum verified) — one per test to avoid unique constraint collisions
_CPF_1 = "52998224725"
_CPF_2 = "29375235017"
_CPF_3 = "71428793860"
_CPF_4 = "11144477735"
_CPF_5 = "71286955084"
_CPF_6 = "15350946056"
_CPF_7 = "78912345664"
_CPF_8 = "29765710070"
_CPF_9 = "12345678909"
_CPF_10 = "46959416000"
_CPF_11 = "23456789173"
_CPF_12 = "34567891228"
_CPF_13 = "45678912364"
_CPF_14 = "56789123482"
_CPF_15 = "67891234582"


def _make_building(street_number: int) -> object:
    return baker.make(
        "core.Building",
        street_number=street_number,
        name="Test Building",
        address="Test Address",
    )


def _make_apartment(
    building: object,
    number: int = 101,
    rental_value: str = "1400.00",
    rental_value_double: str = "1500.00",
) -> object:
    return baker.make(
        "core.Apartment",
        building=building,
        number=number,
        rental_value=Decimal(rental_value),
        rental_value_double=Decimal(rental_value_double),
        max_tenants=2,
        cleaning_fee=Decimal("100.00"),
    )


def _make_tenant(cpf: str, name: str = "Test Tenant") -> object:
    return baker.make(
        "core.Tenant",
        name=name,
        cpf_cnpj=cpf,
        phone="11999990000",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=10,
    )


def _make_lease(
    apartment: object,
    tenant: object,
    rental_value: str = "1400.00",
    start_date: date | None = None,
    validity_months: int = 24,
    number_of_tenants: int = 1,
    is_salary_offset: bool = False,
) -> object:
    if start_date is None:
        start_date = date.today() - relativedelta(months=11)
    return baker.make(
        "core.Lease",
        apartment=apartment,
        responsible_tenant=tenant,
        rental_value=Decimal(rental_value),
        start_date=start_date,
        validity_months=validity_months,
        number_of_tenants=number_of_tenants,
        is_salary_offset=is_salary_offset,
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestRentAdjustmentService:
    def test_apply_adjustment_calculates_correct_value(self) -> None:
        apartment = _make_apartment(_make_building(9901))
        lease = _make_lease(apartment, _make_tenant(_CPF_1))

        adjustment, warning = RentAdjustmentService.apply_adjustment(
            lease=lease,
            percentage=Decimal("5.23"),
            update_apartment_prices=False,
        )

        # 1400.00 * 1.0523 = 1473.22
        assert adjustment.previous_value == Decimal("1400.00")
        assert adjustment.new_value == Decimal("1473.22")
        assert adjustment.percentage == Decimal("5.23")
        lease.refresh_from_db()
        assert lease.rental_value == Decimal("1473.22")
        assert warning is None

    def test_apply_adjustment_negative_percentage(self) -> None:
        apartment = _make_apartment(_make_building(9902))
        lease = _make_lease(apartment, _make_tenant(_CPF_2))

        adjustment, warning = RentAdjustmentService.apply_adjustment(
            lease=lease,
            percentage=Decimal("-0.64"),
            update_apartment_prices=False,
        )

        # 1400.00 * 0.9936 = 1391.04
        assert adjustment.new_value == Decimal("1391.04")
        lease.refresh_from_db()
        assert lease.rental_value == Decimal("1391.04")
        assert warning is None

    def test_apply_adjustment_updates_apartment_prices(self) -> None:
        apartment = _make_apartment(_make_building(9903))
        lease = _make_lease(apartment, _make_tenant(_CPF_3))

        RentAdjustmentService.apply_adjustment(
            lease=lease,
            percentage=Decimal("5.23"),
            update_apartment_prices=True,
        )

        apartment.refresh_from_db()
        # 1400.00 * 1.0523 = 1473.22
        assert apartment.rental_value == Decimal("1473.22")
        # 1500.00 * 1.0523 = 1578.45
        assert apartment.rental_value_double == Decimal("1578.45")
        assert apartment.last_rent_increase_date == date.today()

    def test_apply_adjustment_does_not_update_apartment_when_false(self) -> None:
        apartment = _make_apartment(_make_building(9904))
        original_rental_value = apartment.rental_value
        original_double = apartment.rental_value_double
        lease = _make_lease(apartment, _make_tenant(_CPF_4))

        RentAdjustmentService.apply_adjustment(
            lease=lease,
            percentage=Decimal("5.00"),
            update_apartment_prices=False,
        )

        apartment.refresh_from_db()
        assert apartment.rental_value == original_rental_value
        assert apartment.rental_value_double == original_double
        assert apartment.last_rent_increase_date is None

    def test_apply_adjustment_zero_percentage_raises(self) -> None:
        apartment = _make_apartment(_make_building(9905))
        lease = _make_lease(apartment, _make_tenant(_CPF_5))

        with pytest.raises(ValidationError) as exc_info:
            RentAdjustmentService.apply_adjustment(
                lease=lease,
                percentage=Decimal(0),
                update_apartment_prices=False,
            )

        assert "zero" in str(exc_info.value).lower()

    def test_apply_adjustment_expired_lease_raises(self) -> None:
        apartment = _make_apartment(_make_building(9906))
        # Lease started 3 years ago, valid for 12 months → expired
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_6),
            start_date=date.today() - relativedelta(months=36),
            validity_months=12,
        )

        with pytest.raises(ValidationError) as exc_info:
            RentAdjustmentService.apply_adjustment(
                lease=lease,
                percentage=Decimal("5.00"),
                update_apartment_prices=False,
            )

        assert "encerrada" in str(exc_info.value).lower()

    def test_apply_adjustment_recent_adjustment_returns_warning(self) -> None:
        apartment = _make_apartment(_make_building(9907))
        # Lease started 23 months ago so two adjustments stay within lease period
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_7),
            start_date=date.today() - relativedelta(months=23),
            validity_months=36,
        )

        # Apply first adjustment
        RentAdjustmentService.apply_adjustment(
            lease=lease,
            percentage=Decimal("3.00"),
            update_apartment_prices=False,
        )

        # Apply second adjustment within 10 months of the first
        lease.refresh_from_db()
        _adjustment2, warning = RentAdjustmentService.apply_adjustment(
            lease=lease,
            percentage=Decimal("2.00"),
            update_apartment_prices=False,
        )

        assert warning is not None
        assert warning["type"] == "recent_adjustment"
        assert "last_date" in warning


@pytest.mark.integration
@pytest.mark.django_db
class TestRentAdjustmentAPI:
    def setup_method(self) -> None:
        self.client = APIClient()
        self.admin = baker.make("auth.User", is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=self.admin)

    def test_adjust_rent_endpoint_creates_record(self) -> None:
        apartment = _make_apartment(_make_building(9801))
        lease = _make_lease(apartment, _make_tenant(_CPF_8))

        url = f"/api/leases/{lease.pk}/adjust_rent/"
        response = self.client.post(url, {"percentage": "5.23"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["percentage"] == "5.23"
        assert response.data["previous_value"] == "1400.00"
        assert response.data["new_value"] == "1473.22"
        lease.refresh_from_db()
        assert lease.rental_value == Decimal("1473.22")

    def test_adjust_rent_endpoint_with_apartment_update(self) -> None:
        apartment = _make_apartment(_make_building(9802))
        lease = _make_lease(apartment, _make_tenant(_CPF_9))

        url = f"/api/leases/{lease.pk}/adjust_rent/"
        response = self.client.post(
            url,
            {"percentage": "5.23", "update_apartment_prices": True},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["apartment_updated"] is True
        apartment.refresh_from_db()
        assert apartment.rental_value == Decimal("1473.22")

    def test_adjust_rent_endpoint_invalid_percentage(self) -> None:
        apartment = _make_apartment(_make_building(9803))
        lease = _make_lease(apartment, _make_tenant(_CPF_10))

        url = f"/api/leases/{lease.pk}/adjust_rent/"
        response = self.client.post(url, {"percentage": "0"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_rent_adjustments_endpoint_returns_history(self) -> None:
        apartment = _make_apartment(_make_building(9804))
        # Lease started 23 months ago to allow two adjustments within the period
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_11),
            start_date=date.today() - relativedelta(months=23),
            validity_months=36,
        )

        RentAdjustmentService.apply_adjustment(
            lease=lease, percentage=Decimal("3.00"), update_apartment_prices=False
        )
        lease.refresh_from_db()
        RentAdjustmentService.apply_adjustment(
            lease=lease, percentage=Decimal("2.00"), update_apartment_prices=False
        )

        url = f"/api/leases/{lease.pk}/rent_adjustments/"
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        percentages = [item["percentage"] for item in response.data]
        assert "2.00" in percentages
        assert "3.00" in percentages

    def test_rent_adjustment_alerts_endpoint(self) -> None:
        apartment = _make_apartment(_make_building(9805))
        # Start date 11 months ago — eligible within the 2-month alert window
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_12),
            start_date=date.today() - relativedelta(months=11),
            validity_months=24,
        )

        url = "/api/dashboard/rent_adjustment_alerts/"
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "alerts" in response.data
        lease_ids = [alert["lease_id"] for alert in response.data["alerts"]]
        assert lease.pk in lease_ids


@pytest.mark.integration
@pytest.mark.django_db
class TestGetEligibleLeases:
    def test_get_eligible_leases_excludes_salary_offset(self) -> None:
        apartment = _make_apartment(_make_building(9701))
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_13),
            start_date=date.today() - relativedelta(months=11),
            validity_months=24,
            is_salary_offset=True,
        )

        result = RentAdjustmentService.get_eligible_leases()

        lease_ids_returned = [item["lease_id"] for item in result]
        assert lease.pk not in lease_ids_returned

    def test_get_eligible_leases_excludes_expired(self) -> None:
        apartment = _make_apartment(_make_building(9702))
        # Lease expired 2 years ago (started 3yr ago, valid 12 months)
        expired_lease = _make_lease(
            apartment,
            _make_tenant(_CPF_14),
            start_date=date.today() - relativedelta(months=36),
            validity_months=12,
        )

        result = RentAdjustmentService.get_eligible_leases()

        lease_ids_returned = [item["lease_id"] for item in result]
        assert expired_lease.pk not in lease_ids_returned

    def test_get_eligible_leases_uses_last_adjustment_date(self) -> None:
        apartment = _make_apartment(_make_building(9703))
        # Lease started 23 months ago — overdue for adjustment based on start_date
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_15),
            start_date=date.today() - relativedelta(months=23),
            validity_months=36,
        )

        # Apply an adjustment today — next eligible date becomes today + 12 months,
        # which is outside the 2-month alert window → lease should NOT appear
        RentAdjustmentService.apply_adjustment(
            lease=lease, percentage=Decimal("3.00"), update_apartment_prices=False
        )

        result = RentAdjustmentService.get_eligible_leases()

        lease_ids_returned = [item["lease_id"] for item in result]
        assert lease.pk not in lease_ids_returned


@pytest.mark.integration
@pytest.mark.django_db
class TestGetEligibleLeasesExtra:
    """Additional eligible leases tests that reuse CPFs already used above
    but run in separate transaction scopes."""

    def test_eligible_lease_appears_in_results(self) -> None:
        apartment = _make_apartment(_make_building(9704))
        # Start date 11 months ago — anniversary in 1 month, within 2-month window
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_1),
            start_date=date.today() - relativedelta(months=11),
            validity_months=24,
        )

        result = RentAdjustmentService.get_eligible_leases()

        lease_ids_returned = [item["lease_id"] for item in result]
        assert lease.pk in lease_ids_returned
        matching = next(item for item in result if item["lease_id"] == lease.pk)
        assert matching["status"] in ("upcoming", "overdue")
        assert "eligible_date" in matching
        assert "rental_value" in matching

    def test_eligible_lease_status_overdue_when_past_anniversary(self) -> None:
        apartment = _make_apartment(_make_building(9705))
        # Start date 13 months ago — anniversary already passed → overdue
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_2),
            start_date=date.today() - relativedelta(months=13),
            validity_months=36,
        )

        result = RentAdjustmentService.get_eligible_leases()

        lease_ids_returned = [item["lease_id"] for item in result]
        assert lease.pk in lease_ids_returned
        matching = next(item for item in result if item["lease_id"] == lease.pk)
        assert matching["status"] == "overdue"
        assert matching["days_until"] < 0

    def test_eligible_leases_returns_last_adjustment_info(self) -> None:
        apartment = _make_apartment(_make_building(9706))
        # Lease started 25 months ago
        lease = _make_lease(
            apartment,
            _make_tenant(_CPF_3),
            start_date=date.today() - relativedelta(months=25),
            validity_months=36,
        )

        # Apply adjustment 13 months ago so the next window opens now
        RentAdjustment.objects.create(
            lease=Lease.objects.get(pk=lease.pk),
            adjustment_date=date.today() - relativedelta(months=13),
            percentage=Decimal("5.00"),
            previous_value=Decimal("1400.00"),
            new_value=Decimal("1470.00"),
            apartment_updated=False,
        )

        result = RentAdjustmentService.get_eligible_leases()

        lease_ids_returned = [item["lease_id"] for item in result]
        assert lease.pk in lease_ids_returned
        matching = next(item for item in result if item["lease_id"] == lease.pk)
        assert matching["last_adjustment"] is not None
        assert matching["last_adjustment"]["percentage"] == "5.00"
