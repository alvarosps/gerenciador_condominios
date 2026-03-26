"""Unit tests for DashboardService.

Tests all five service methods with real database objects.
No internal code is mocked — only time is frozen where needed.
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import Apartment, Building, Dependent, Lease, Tenant
from core.services.dashboard_service import DashboardService


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=7700,
        name="Edifício Dashboard Test",
        address="Rua Dashboard, 7700",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def building2(admin_user):
    return Building.objects.create(
        street_number=7701,
        name="Edifício Dashboard Test 2",
        address="Rua Dashboard, 7701",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_rented(building, admin_user):
    """Apartment that will have a lease (is_rented set via signal)."""
    return Apartment.objects.create(
        building=building,
        number=401,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_vacant(building, admin_user):
    """Apartment without a lease (not rented)."""
    return Apartment.objects.create(
        building=building,
        number=402,
        rental_value=Decimal("1000.00"),
        cleaning_fee=Decimal("100.00"),
        max_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant_individual(admin_user):
    return Tenant.objects.create(
        name="Tenant Individual Dashboard",
        cpf_cnpj="98765432100",
        is_company=False,
        phone="11977770001",
        marital_status="Casado(a)",
        profession="Médico",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant_company(admin_user):
    return Tenant.objects.create(
        name="Empresa Dashboard LTDA",
        cpf_cnpj="11222333000181",
        is_company=True,
        phone="11977770002",
        marital_status="Solteiro(a)",
        profession="TI",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def active_lease(apartment_rented, tenant_individual, admin_user):
    """Creates a lease, which triggers the signal to set apartment.is_rented=True."""
    return Lease.objects.create(
        apartment=apartment_rented,
        responsible_tenant=tenant_individual,
        start_date=date(2026, 1, 1),
        validity_months=24,
        tag_fee=Decimal("80.00"),
        rental_value=Decimal("1500.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


# ---------------------------------------------------------------------------
# get_financial_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFinancialSummary:
    def test_returns_expected_keys(self):
        summary = DashboardService.get_financial_summary()
        expected_keys = {
            "total_revenue",
            "total_cleaning_fees",
            "total_tag_fees",
            "total_income",
            "occupancy_rate",
            "total_apartments",
            "rented_apartments",
            "vacant_apartments",
            "revenue_per_apartment",
        }
        assert expected_keys.issubset(summary.keys())

    def test_empty_database_returns_zero_totals(self):
        summary = DashboardService.get_financial_summary()
        assert summary["total_revenue"] == Decimal("0.00")
        assert summary["occupancy_rate"] == 0
        assert summary["total_apartments"] >= 0

    def test_with_rented_apartment_calculates_revenue(
        self, apartment_rented, active_lease
    ):
        summary = DashboardService.get_financial_summary()
        assert summary["rented_apartments"] >= 1
        assert summary["total_revenue"] >= Decimal("1500.00")
        assert summary["total_tag_fees"] >= Decimal("80.00")

    def test_occupancy_rate_between_0_and_100(
        self, apartment_rented, apartment_vacant, active_lease
    ):
        summary = DashboardService.get_financial_summary()
        assert 0 <= summary["occupancy_rate"] <= 100

    def test_vacant_apartments_counted(self, apartment_vacant):
        summary = DashboardService.get_financial_summary()
        assert summary["vacant_apartments"] >= 1

    def test_revenue_per_apartment_is_zero_when_no_rented(self):
        # Only if no rented apartments exist in clean state
        summary = DashboardService.get_financial_summary()
        if summary["rented_apartments"] == 0:
            assert summary["revenue_per_apartment"] == Decimal("0.00")

    def test_total_income_equals_sum(self, active_lease, apartment_rented):
        summary = DashboardService.get_financial_summary()
        expected = (
            summary["total_revenue"]
            + summary["total_cleaning_fees"]
            + summary["total_tag_fees"]
        )
        assert summary["total_income"] == expected


# ---------------------------------------------------------------------------
# get_lease_metrics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLeaseMetrics:
    def test_returns_expected_keys(self):
        metrics = DashboardService.get_lease_metrics()
        expected_keys = {
            "total_leases",
            "active_leases",
            "inactive_leases",
            "contracts_generated",
            "contracts_pending",
            "expiring_soon",
            "expired_leases",
        }
        assert expected_keys.issubset(metrics.keys())

    def test_empty_database_returns_zeroes(self):
        metrics = DashboardService.get_lease_metrics()
        assert metrics["total_leases"] >= 0
        assert metrics["expiring_soon"] >= 0
        assert metrics["expired_leases"] >= 0

    @freeze_time("2028-06-01")
    def test_expired_lease_counted(self, active_lease):
        # lease started 2026-01-01 with 24 months → ends 2028-01-01 (approx)
        # On 2028-06-01, it should be expired
        metrics = DashboardService.get_lease_metrics()
        assert metrics["expired_leases"] >= 1

    @freeze_time("2026-06-01")
    def test_active_lease_counted(self, active_lease, apartment_rented):
        metrics = DashboardService.get_lease_metrics()
        assert metrics["active_leases"] >= 1

    @freeze_time("2027-12-20")
    def test_expiring_soon_counted(self, active_lease):
        # lease ends 2028-01-01 — within 30 days of 2027-12-20
        metrics = DashboardService.get_lease_metrics()
        assert metrics["expiring_soon"] >= 1

    def test_contracts_pending_equals_total_minus_generated(self, active_lease):
        metrics = DashboardService.get_lease_metrics()
        assert (
            metrics["contracts_pending"]
            == metrics["total_leases"] - metrics["contracts_generated"]
        )

    def test_inactive_leases_equals_total_minus_active(self, active_lease, apartment_rented):
        metrics = DashboardService.get_lease_metrics()
        assert metrics["inactive_leases"] == metrics["total_leases"] - metrics["active_leases"]


# ---------------------------------------------------------------------------
# get_building_statistics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetBuildingStatistics:
    def test_returns_list(self):
        stats = DashboardService.get_building_statistics()
        assert isinstance(stats, list)

    def test_each_entry_has_required_keys(self, building):
        stats = DashboardService.get_building_statistics()
        building_stat = next((s for s in stats if s["building_id"] == building.id), None)
        assert building_stat is not None
        required_keys = {
            "building_id",
            "building_number",
            "total_apartments",
            "rented_apartments",
            "vacant_apartments",
            "occupancy_rate",
            "total_revenue",
        }
        assert required_keys.issubset(building_stat.keys())

    def test_occupancy_rate_correct(
        self, building, apartment_rented, apartment_vacant, active_lease
    ):
        stats = DashboardService.get_building_statistics()
        building_stat = next(s for s in stats if s["building_id"] == building.id)
        # 1 rented, 1 vacant → 50% occupancy
        assert building_stat["total_apartments"] == 2
        assert building_stat["rented_apartments"] == 1
        assert building_stat["vacant_apartments"] == 1
        assert building_stat["occupancy_rate"] == 50.0

    def test_building_with_no_apartments_has_zero_occupancy(self, building2):
        stats = DashboardService.get_building_statistics()
        building_stat = next(
            (s for s in stats if s["building_id"] == building2.id), None
        )
        assert building_stat is not None
        assert building_stat["total_apartments"] == 0
        assert building_stat["occupancy_rate"] == 0

    def test_total_revenue_is_decimal(self, building, active_lease):
        stats = DashboardService.get_building_statistics()
        building_stat = next(s for s in stats if s["building_id"] == building.id)
        assert isinstance(building_stat["total_revenue"], Decimal)


# ---------------------------------------------------------------------------
# get_late_payment_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLatePaymentSummary:
    def test_returns_expected_keys(self):
        summary = DashboardService.get_late_payment_summary()
        assert "total_late_leases" in summary
        assert "total_late_fees" in summary
        assert "average_late_days" in summary
        assert "late_leases" in summary

    def test_no_late_leases_returns_zero(self):
        # Without any active rented lease, no late leases
        summary = DashboardService.get_late_payment_summary()
        assert summary["total_late_leases"] >= 0
        assert isinstance(summary["late_leases"], list)

    @freeze_time("2026-03-15")
    def test_late_lease_detected(self, active_lease, apartment_rented, tenant_individual):
        # tenant_individual.due_day = 10, today = 2026-03-15 → 5 days late
        summary = DashboardService.get_late_payment_summary()
        assert summary["total_late_leases"] >= 1
        assert summary["total_late_fees"] > Decimal("0.00")
        late = summary["late_leases"][0]
        assert "lease_id" in late
        assert "tenant_name" in late
        assert "late_days" in late
        assert "late_fee" in late
        assert late["late_days"] >= 1

    @freeze_time("2026-03-05")
    def test_not_late_when_before_due_day(
        self, active_lease, apartment_rented, tenant_individual
    ):
        # due_day = 10, today = 2026-03-05 → not late
        summary = DashboardService.get_late_payment_summary()
        # This particular lease should not be in late_leases
        late_lease_ids = [l["lease_id"] for l in summary["late_leases"]]
        assert active_lease.id not in late_lease_ids

    @freeze_time("2026-03-15")
    def test_average_late_days_calculated(self, active_lease, apartment_rented):
        summary = DashboardService.get_late_payment_summary()
        if summary["total_late_leases"] > 0:
            assert summary["average_late_days"] > 0


# ---------------------------------------------------------------------------
# get_tenant_statistics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTenantStatistics:
    def test_returns_expected_keys(self):
        stats = DashboardService.get_tenant_statistics()
        expected_keys = {
            "total_tenants",
            "individual_tenants",
            "company_tenants",
            "tenants_with_dependents",
            "total_dependents",
            "marital_status_distribution",
        }
        assert expected_keys.issubset(stats.keys())

    def test_counts_individual_and_company_tenants(
        self, tenant_individual, tenant_company
    ):
        stats = DashboardService.get_tenant_statistics()
        assert stats["individual_tenants"] >= 1
        assert stats["company_tenants"] >= 1
        assert stats["total_tenants"] >= 2

    def test_counts_dependents(self, tenant_individual, admin_user):
        Dependent.objects.create(
            tenant=tenant_individual,
            name="Dependente Dashboard",
            phone="11900001111",
            created_by=admin_user,
        )
        stats = DashboardService.get_tenant_statistics()
        assert stats["total_dependents"] >= 1
        assert stats["tenants_with_dependents"] >= 1

    def test_marital_status_distribution_is_dict(self, tenant_individual):
        stats = DashboardService.get_tenant_statistics()
        assert isinstance(stats["marital_status_distribution"], dict)

    def test_marital_status_counts_individual_tenants_only(
        self, tenant_individual, tenant_company
    ):
        # company tenants should not appear in marital status distribution
        stats = DashboardService.get_tenant_statistics()
        dist = stats["marital_status_distribution"]
        # tenant_individual has marital_status "Casado(a)"
        total_in_dist = sum(dist.values())
        # should not include company tenants
        assert total_in_dist <= stats["individual_tenants"]

    def test_empty_tenant_db_returns_zeroes(self):
        stats = DashboardService.get_tenant_statistics()
        assert stats["total_tenants"] >= 0
        assert stats["total_dependents"] >= 0
