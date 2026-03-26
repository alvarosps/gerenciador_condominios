"""Integration tests for Lease action endpoints.

Tests behavioral correctness of:
- change_due_date: writes to Tenant.due_day (not Lease), reads rental_value from Apartment
- calculate_late_fee: reads rental_value from Apartment, due_day from Tenant
- generate_contract: all template context values come from new field locations
- Signal: creating a Lease sets apartment.is_rented=True, soft-deleting sets it to False
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from core.models import Apartment, Building, Lease, Tenant


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=4400,
        name="Edifício Lease Actions",
        address="Rua Lease, 4400",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Carlos Lease",
        cpf_cnpj="29375235017",
        phone="11999990044",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeDueDate:
    url_template = "/api/leases/{pk}/change_due_date/"

    @freeze_time("2026-03-15")
    def test_change_due_date_writes_to_tenant(self, authenticated_api_client, lease, tenant):
        """change_due_date must update Tenant.due_day, not any Lease field."""
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.post(url, {"new_due_day": 15}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["old_due_day"] == 10
        assert response.data["new_due_day"] == 15

        # Tenant.due_day should be updated
        tenant.refresh_from_db()
        assert tenant.due_day == 15

        # Lease should have no due_day field (it was removed in the refactor)
        from django.core.exceptions import FieldDoesNotExist

        with pytest.raises(FieldDoesNotExist):
            Lease._meta.get_field("due_day")

    @freeze_time("2026-03-15")
    def test_change_due_date_returns_complete_response(
        self, authenticated_api_client, lease, apartment, tenant
    ):
        """Response must include all fee details, dates, and total_due."""
        # tenant.due_day=10, rental_value=1500.00, new_due_day=20
        # reference=2026-03-15, old_date=2026-03-10, new_date=2026-03-20
        # inclusive days = (20-10)+1 = 11, daily_rate=50.00
        # fee=round(50*11)=550, total_due=1500+550=2050
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.post(url, {"new_due_day": 20}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["old_due_day"] == 10
        assert response.data["new_due_day"] == 20
        assert response.data["old_due_date"] == date(2026, 3, 10)
        assert response.data["new_due_date"] == date(2026, 3, 20)
        assert response.data["days_difference"] == 11
        assert Decimal(str(response.data["daily_rate"])) == Decimal("50.00")
        assert response.data["change_fee"] == 550
        assert Decimal(str(response.data["total_due"])) == Decimal("2050.00")

    @freeze_time("2026-03-15")
    def test_change_due_date_wraps_to_next_month(self, authenticated_api_client, admin_user):
        """When new_due_day < current_due_day, the new date falls in the next month.

        User's exact scenario: due_day=22 → 5, reference March 2026.
        old_date=2026-03-22, new_date=2026-04-05
        Inclusive days: 22,23,...,31,1,...,5 = 15 days
        daily_rate=1250/30=41.67, fee=round(41.67*15)=round(625.05)=625
        total_due=1250+625=1875
        """
        building = Building.objects.create(
            street_number=9900,
            name="Edifício Round Test",
            address="Rua Round, 9900",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apt = Apartment.objects.create(
            building=building,
            number=204,
            rental_value=Decimal("1250.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=2,
            created_by=admin_user,
            updated_by=admin_user,
        )
        tnt = Tenant.objects.create(
            name="Tenant Round Test",
            cpf_cnpj="52998224725",
            phone="11999990099",
            marital_status="Solteiro(a)",
            profession="Tester",
            due_day=22,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lse = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tnt,
            start_date=date(2026, 2, 22),
            validity_months=12,
            tag_fee=Decimal("50.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        url = self.url_template.format(pk=lse.pk)
        response = authenticated_api_client.post(url, {"new_due_day": 5}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["old_due_date"] == date(2026, 3, 22)
        assert response.data["new_due_date"] == date(2026, 4, 5)
        assert response.data["days_difference"] == 15
        assert Decimal(str(response.data["daily_rate"])) == Decimal("41.67")
        # 41.67 * 15 = 625.05 → rounds to 625
        assert response.data["change_fee"] == 625
        # total_due = 1250 + 625 = 1875
        assert Decimal(str(response.data["total_due"])) == Decimal("1875.00")

    def test_change_due_date_missing_param_returns_400(self, authenticated_api_client, lease):
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_change_due_date_invalid_value_returns_400(self, authenticated_api_client, lease):
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.post(
            url, {"new_due_day": "not_a_number"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_due_date_out_of_range_returns_400(self, authenticated_api_client, lease):
        """Due day must be between 1 and 31."""
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.post(url, {"new_due_day": 32}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
class TestCalculateLateFee:
    url_template = "/api/leases/{pk}/calculate_late_fee/"

    @freeze_time("2026-03-15")
    def test_calculates_fee_from_correct_sources(
        self, authenticated_api_client, lease, apartment, tenant
    ):
        """calculate_late_fee must use apartment.rental_value and tenant.due_day."""
        # Tenant.due_day=10, today=2026-03-15 → 5 days late
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "late_days" in response.data
        assert "late_fee" in response.data
        assert response.data["late_days"] == 5
        # Fee is 5% per day: 5 * 0.05 * (1500 / 30) = 5 * 0.05 * 50 = 12.50
        assert Decimal(str(response.data["late_fee"])) == Decimal("12.50")

    @freeze_time("2026-03-05")
    def test_not_late_returns_message(self, authenticated_api_client, lease, apartment, tenant):
        """When today < due_day, fee should be zero or return a not-late message."""
        # Tenant.due_day=10, today=2026-03-05 → not late yet
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Either a message or zero fee
        assert "message" in response.data or Decimal(
            str(response.data.get("late_fee", 0))
        ) == Decimal("0.00")


@pytest.mark.integration
@pytest.mark.django_db
class TestGenerateContract:
    url_template = "/api/leases/{pk}/generate_contract/"

    def test_generate_contract_succeeds(
        self, authenticated_api_client, lease, tenant, mock_pdf_generation
    ):
        """generate_contract should return 200 with pdf_path when PDF mock is active."""
        # Add tenant to M2M so calculate_tag_fee receives num_tenants >= 1
        lease.tenants.add(tenant)
        url = self.url_template.format(pk=lease.pk)
        response = authenticated_api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert "pdf_path" in response.data

    def test_generate_contract_marks_lease_contract_generated(
        self, authenticated_api_client, lease, tenant, mock_pdf_generation
    ):
        """After generating contract, lease.contract_generated should be True."""
        lease.tenants.add(tenant)
        url = self.url_template.format(pk=lease.pk)
        authenticated_api_client.post(url)

        lease.refresh_from_db()
        assert lease.contract_generated is True

    def test_generate_contract_unauthenticated_returns_401(self, api_client, lease):
        url = self.url_template.format(pk=lease.pk)
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestLeaseSignalIsRented:
    """Tests for the signal that syncs apartment.is_rented from Lease lifecycle."""

    def test_creating_lease_sets_apartment_is_rented_true(self, apartment, tenant, admin_user):
        """When a Lease is created, apartment.is_rented must become True."""
        assert not apartment.is_rented

        Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2026, 1, 1),
            validity_months=12,
            tag_fee=Decimal("0.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        apartment.refresh_from_db()
        assert apartment.is_rented is True

    def test_soft_deleting_lease_sets_apartment_is_rented_false(self, lease, apartment, admin_user):
        """When a Lease is soft-deleted, apartment.is_rented must become False."""
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        lease.delete(deleted_by=admin_user)

        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_apartment_is_rented_remains_false_without_lease(self, apartment):
        """An apartment without a lease should have is_rented=False."""
        assert apartment.is_rented is False
