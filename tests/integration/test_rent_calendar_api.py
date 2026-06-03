"""Integration tests for the rent calendar endpoints on DashboardViewSet.

Covers:
- GET  /api/dashboard/rent_calendar/        (RentScheduleService.get_month_schedule)
- POST /api/dashboard/toggle_rent_payment/  (RentScheduleService.toggle_payment)

Exercises the real path View -> RentScheduleService -> Model against the test
database (no mocking of internal services / ORM / serializers). Time is frozen
with freezegun (the only external boundary touched here).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.test import override_settings
from freezegun import freeze_time
from model_bakery import baker
from rest_framework import status

from core.models import MonthSnapshot, RentPayment

# DRF binds ``SimpleRateThrottle.timer = time.time`` as a class attribute, so under
# freezegun it is called as a bound method (``fake_time(self)``) and raises. Throttling
# is an external infrastructure boundary, not application logic — disable it here so the
# tests exercise the real View -> Service -> Model path. ``override_settings`` replaces
# the whole REST_FRAMEWORK dict, so the rest of the config is copied to keep auth intact.
_REST_FRAMEWORK_NO_THROTTLE = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}


@pytest.fixture(autouse=True)
def _disable_throttling():
    """Disable DRF throttling for every test in this module (see note above)."""
    with override_settings(REST_FRAMEWORK=_REST_FRAMEWORK_NO_THROTTLE):
        yield


# Valid CPFs (checksum verified) — one per tenant to avoid unique collisions.
_CPF_1 = "52998224725"
_CPF_2 = "29375235017"
_CPF_3 = "71428793860"

RENT_CALENDAR_URL = "/api/dashboard/rent_calendar/"
TOGGLE_URL = "/api/dashboard/toggle_rent_payment/"


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
    rental_value: str = "1500.00",
) -> object:
    return baker.make(
        "core.Apartment",
        building=building,
        number=number,
        rental_value=Decimal(rental_value),
        rental_value_double=Decimal("1600.00"),
        max_tenants=2,
        cleaning_fee=Decimal("100.00"),
        is_rented=False,
    )


def _make_tenant(cpf: str, name: str = "Test Tenant", due_day: int = 5) -> object:
    return baker.make(
        "core.Tenant",
        name=name,
        cpf_cnpj=cpf,
        phone="11999990000",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=due_day,
    )


def _make_lease(
    apartment: object,
    tenant: object,
    rental_value: str = "1500.00",
    start_date: date = date(2026, 1, 1),
    validity_months: int = 24,
) -> object:
    return baker.make(
        "core.Lease",
        apartment=apartment,
        responsible_tenant=tenant,
        rental_value=Decimal(rental_value),
        start_date=start_date,
        validity_months=validity_months,
        number_of_tenants=1,
        is_salary_offset=False,
    )


@pytest.fixture
def collectible_lease(admin_user) -> object:
    """A single collectible lease due on day 5, in building 100."""
    building = _make_building(100)
    apartment = _make_apartment(building, number=101)
    tenant = _make_tenant(_CPF_1, name="João Silva", due_day=5)
    return _make_lease(apartment, tenant)


@pytest.mark.integration
class TestRentCalendarRead:
    @freeze_time("2026-06-02")
    def test_returns_top_level_shape(self, authenticated_api_client, collectible_lease):
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": 2026, "month": 6})
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["year"] == 2026
        assert data["month"] == 6
        assert data["today"] == "2026-06-02"
        assert "next_due_date" in data
        assert isinstance(data["days"], list)
        assert isinstance(data["stats"], dict)

    @freeze_time("2026-06-02")
    def test_day_and_item_shape(self, authenticated_api_client, collectible_lease):
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": 2026, "month": 6})
        assert response.status_code == status.HTTP_200_OK

        first_day = response.data["days"][0]
        for key in ("day", "date", "weekday", "items"):
            assert key in first_day

        # Due day 5 -> item lives on the 5th (index 4).
        day_5 = response.data["days"][4]
        assert len(day_5["items"]) == 1
        item = day_5["items"][0]
        for key in (
            "lease_id",
            "tenant_name",
            "apartment_number",
            "building_number",
            "rental_value",
            "is_paid",
            "is_overdue",
            "day_passed",
            "can_toggle",
            "late_fee",
            "late_days",
        ):
            assert key in item
        assert item["lease_id"] == collectible_lease.pk
        assert item["tenant_name"] == "João Silva"

    @freeze_time("2026-06-02")
    def test_stats_shape(self, authenticated_api_client, collectible_lease):
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": 2026, "month": 6})
        assert response.status_code == status.HTTP_200_OK
        stats = response.data["stats"]
        for key in (
            "received_total",
            "to_receive_total",
            "expected_total",
            "paid_count",
            "due_count",
            "overdue_count",
            "overdue_total_fee",
            "vacant_kitnets_count",
            "vacant_kitnets_value",
        ):
            assert key in stats

    @freeze_time("2026-06-02")
    def test_building_id_filter_restricts_items(self, authenticated_api_client):
        building_a = _make_building(200)
        apartment_a = _make_apartment(building_a, number=201)
        tenant_a = _make_tenant(_CPF_2, name="Tenant A", due_day=5)
        lease_a = _make_lease(apartment_a, tenant_a)

        building_b = _make_building(300)
        apartment_b = _make_apartment(building_b, number=301)
        tenant_b = _make_tenant(_CPF_3, name="Tenant B", due_day=5)
        lease_b = _make_lease(apartment_b, tenant_b)

        response = authenticated_api_client.get(
            RENT_CALENDAR_URL,
            {"year": 2026, "month": 6, "building_id": building_a.pk},
        )
        assert response.status_code == status.HTTP_200_OK

        lease_ids = {item["lease_id"] for day in response.data["days"] for item in day["items"]}
        assert lease_a.pk in lease_ids
        assert lease_b.pk not in lease_ids

    @freeze_time("2026-06-02")
    def test_month_out_of_range_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": 2026, "month": 13})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_year_out_of_range_returns_400(self, authenticated_api_client):
        # Out-of-range year must be a clean 400, not a 500 from date(year, 1, 1).
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": 99999, "month": 6})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_non_integer_year_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": "abc", "month": 6})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_non_integer_month_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(RENT_CALENDAR_URL, {"year": 2026, "month": "xyz"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_missing_params_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(RENT_CALENDAR_URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_non_integer_building_id_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(
            RENT_CALENDAR_URL, {"year": 2026, "month": 6, "building_id": "abc"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(RENT_CALENDAR_URL, {"year": 2026, "month": 6})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.get(
            RENT_CALENDAR_URL, {"year": 2026, "month": 6}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
class TestToggleRentPayment:
    @freeze_time("2026-06-02")
    def test_toggle_creates_and_then_soft_deletes(
        self, authenticated_api_client, collectible_lease
    ):
        reference_month = date(2026, 6, 1)
        payload = {"lease_id": collectible_lease.pk, "reference_month": "2026-06-01"}

        # First toggle: due day (5) is in the future -> create active RentPayment.
        first = authenticated_api_client.post(TOGGLE_URL, payload, format="json")
        assert first.status_code == status.HTTP_200_OK
        assert first.data["is_paid"] is True
        assert RentPayment.objects.filter(
            lease=collectible_lease, reference_month=reference_month
        ).exists()

        # Second toggle: due day still in the future -> soft-delete it.
        second = authenticated_api_client.post(TOGGLE_URL, payload, format="json")
        assert second.status_code == status.HTTP_200_OK
        assert second.data["is_paid"] is False
        assert not RentPayment.objects.filter(
            lease=collectible_lease, reference_month=reference_month
        ).exists()
        deleted = RentPayment.all_objects.get(
            lease=collectible_lease, reference_month=reference_month
        )
        assert deleted.is_deleted is True

    @freeze_time("2026-06-10")
    def test_refuses_unmark_when_paid_and_day_passed(
        self, authenticated_api_client, admin_user, collectible_lease
    ):
        reference_month = date(2026, 6, 1)
        RentPayment.objects.create(
            lease=collectible_lease,
            reference_month=reference_month,
            amount_paid=Decimal("1500.00"),
            payment_date=date(2026, 6, 1),
            created_by=admin_user,
            updated_by=admin_user,
        )

        payload = {"lease_id": collectible_lease.pk, "reference_month": "2026-06-01"}
        response = authenticated_api_client.post(TOGGLE_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Payment is untouched.
        assert RentPayment.objects.filter(
            lease=collectible_lease, reference_month=reference_month
        ).exists()

    @freeze_time("2026-06-02")
    def test_finalized_month_blocks_toggle(
        self, authenticated_api_client, admin_user, collectible_lease
    ):
        reference_month = date(2026, 6, 1)
        MonthSnapshot.objects.create(
            reference_month=reference_month,
            is_finalized=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        payload = {"lease_id": collectible_lease.pk, "reference_month": "2026-06-01"}
        response = authenticated_api_client.post(TOGGLE_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not RentPayment.objects.filter(
            lease=collectible_lease, reference_month=reference_month
        ).exists()

    @freeze_time("2026-06-02")
    def test_missing_lease_id_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            TOGGLE_URL, {"reference_month": "2026-06-01"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_non_numeric_lease_id_returns_400(self, authenticated_api_client):
        # Non-numeric lease_id must be a clean 400, not a 500 from the ORM lookup.
        response = authenticated_api_client.post(
            TOGGLE_URL, {"lease_id": "abc", "reference_month": "2026-06-01"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_missing_reference_month_returns_400(self, authenticated_api_client, collectible_lease):
        response = authenticated_api_client.post(
            TOGGLE_URL, {"lease_id": collectible_lease.pk}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-06-02")
    def test_invalid_reference_month_returns_400(self, authenticated_api_client, collectible_lease):
        response = authenticated_api_client.post(
            TOGGLE_URL,
            {"lease_id": collectible_lease.pk, "reference_month": "2026-13-01"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(
            TOGGLE_URL, {"lease_id": 1, "reference_month": "2026-06-01"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, regular_authenticated_api_client, collectible_lease):
        response = regular_authenticated_api_client.post(
            TOGGLE_URL,
            {"lease_id": collectible_lease.pk, "reference_month": "2026-06-01"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
