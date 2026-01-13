"""
Unit tests for DashboardService.

Tests all dashboard metrics and financial summaries:
- Financial summary (revenue, occupancy, fees)
- Lease metrics (active, expiring, contracts)
- Building statistics per building
- Late payment calculations
- Tenant demographics and statistics
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from core.models import Apartment, Building, Dependent, Furniture, Lease, Tenant
from core.services.dashboard_service import DashboardService


@pytest.fixture
def sample_buildings():
    """Create sample buildings for testing."""
    building1 = Building.objects.create(street_number=836, name="Building A", address="Street A, 836")
    building2 = Building.objects.create(street_number=850, name="Building B", address="Street B, 850")
    return {"building1": building1, "building2": building2}


@pytest.fixture
def sample_apartments(sample_buildings):
    """Create sample apartments in both buildings."""
    apartments = []

    # Building 1: 3 apartments (2 rented, 1 vacant)
    for i in range(1, 4):
        apt = Apartment.objects.create(
            building=sample_buildings["building1"],
            number=100 + i,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
            is_rented=(i <= 2),  # First 2 are rented
        )
        apartments.append(apt)

    # Building 2: 2 apartments (1 rented, 1 vacant)
    for i in range(1, 3):
        apt = Apartment.objects.create(
            building=sample_buildings["building2"],
            number=200 + i,
            rental_value=Decimal("1800.00"),
            cleaning_fee=Decimal("250.00"),
            max_tenants=2,
            is_rented=(i == 1),  # Only first is rented
        )
        apartments.append(apt)

    return apartments


@pytest.fixture
def sample_tenants():
    """Create sample tenants."""
    tenant1 = Tenant.objects.create(
        name="John Doe",
        cpf_cnpj="529.982.247-25",  # Valid CPF
        phone="11999999999",
        marital_status="Casado(a)",
        profession="Engineer",
        is_company=False,
    )
    tenant2 = Tenant.objects.create(
        name="Jane Smith",
        cpf_cnpj="191.503.098-62",  # Valid CPF
        phone="11988888888",
        marital_status="Solteiro(a)",
        profession="Doctor",
        is_company=False,
    )
    tenant3 = Tenant.objects.create(
        name="Company XYZ",
        cpf_cnpj="11.222.333/0001-81",  # Valid CNPJ
        phone="1133333333",
        marital_status="Solteiro(a)",  # Required field, use default for companies
        profession="Corporate",
        is_company=True,
    )
    return [tenant1, tenant2, tenant3]


@pytest.fixture
def sample_leases(sample_apartments, sample_tenants):
    """Create sample leases for testing."""
    leases = []
    today = date.today()

    # Lease 1: Active, on Building 1, Apartment 101
    lease1 = Lease.objects.create(
        apartment=sample_apartments[0],
        responsible_tenant=sample_tenants[0],
        start_date=today - timedelta(days=30),
        validity_months=12,
        due_day=10,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        tag_fee=Decimal("50.00"),
        contract_generated=True,
    )
    lease1.tenants.add(sample_tenants[0])
    leases.append(lease1)

    # Lease 2: Active, on Building 1, Apartment 102
    lease2 = Lease.objects.create(
        apartment=sample_apartments[1],
        responsible_tenant=sample_tenants[1],
        start_date=today - timedelta(days=60),
        validity_months=6,
        due_day=15,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        tag_fee=Decimal("50.00"),
        contract_generated=False,
    )
    lease2.tenants.add(sample_tenants[1])
    leases.append(lease2)

    # Lease 3: Active, on Building 2, Apartment 201
    lease3 = Lease.objects.create(
        apartment=sample_apartments[3],
        responsible_tenant=sample_tenants[2],
        start_date=today - timedelta(days=400),  # Expired
        validity_months=12,
        due_day=5,
        rental_value=Decimal("1800.00"),
        cleaning_fee=Decimal("250.00"),
        tag_fee=Decimal("80.00"),
        contract_generated=True,
    )
    lease3.tenants.add(sample_tenants[2])
    leases.append(lease3)

    return leases


@pytest.fixture
def sample_dependents(sample_tenants):
    """Create sample dependents."""
    dep1 = Dependent.objects.create(tenant=sample_tenants[0], name="John Doe Jr", phone="11977777777")
    dep2 = Dependent.objects.create(tenant=sample_tenants[0], name="Jane Doe", phone="11966666666")
    return [dep1, dep2]


class TestGetFinancialSummary:
    """Test financial summary calculations."""

    def test_financial_summary_with_active_leases(self, sample_leases):
        """Test financial summary with active leases."""
        summary = DashboardService.get_financial_summary()

        # Verify structure
        assert "total_revenue" in summary
        assert "total_cleaning_fees" in summary
        assert "total_tag_fees" in summary
        assert "total_income" in summary
        assert "occupancy_rate" in summary
        assert "total_apartments" in summary
        assert "rented_apartments" in summary
        assert "vacant_apartments" in summary
        assert "revenue_per_apartment" in summary

        # Verify calculations
        # 3 active leases: 1500 + 1500 + 1800 = 4800
        assert summary["total_revenue"] == Decimal("4800.00")

        # 3 active leases: 200 + 200 + 250 = 650
        assert summary["total_cleaning_fees"] == Decimal("650.00")

        # 3 active leases: 50 + 50 + 80 = 180
        assert summary["total_tag_fees"] == Decimal("180.00")

        # Total income: 4800 + 650 + 180 = 5630
        assert summary["total_income"] == Decimal("5630.00")

        # 5 total apartments, 3 rented
        assert summary["total_apartments"] == 5
        assert summary["rented_apartments"] == 3
        assert summary["vacant_apartments"] == 2

        # Occupancy: 3/5 = 60%
        assert summary["occupancy_rate"] == 60.0

        # Revenue per apartment: 4800 / 3 = 1600
        assert summary["revenue_per_apartment"] == Decimal("1600.00")

    def test_financial_summary_no_leases(self):
        """Test financial summary with no leases."""
        summary = DashboardService.get_financial_summary()

        assert summary["total_revenue"] == Decimal("0.00")
        assert summary["total_cleaning_fees"] == Decimal("0.00")
        assert summary["total_tag_fees"] == Decimal("0.00")
        assert summary["total_income"] == Decimal("0.00")
        assert summary["occupancy_rate"] == 0.0
        assert summary["revenue_per_apartment"] == Decimal("0.00")

    def test_financial_summary_no_apartments(self):
        """Test financial summary when no apartments exist."""
        # Remove all apartments
        Apartment.objects.all().delete()

        summary = DashboardService.get_financial_summary()

        assert summary["total_apartments"] == 0
        assert summary["rented_apartments"] == 0
        assert summary["vacant_apartments"] == 0
        assert summary["occupancy_rate"] == 0.0


class TestGetLeaseMetrics:
    """Test lease metrics calculations."""

    def test_lease_metrics_standard(self, sample_leases):
        """Test lease metrics with standard leases."""
        metrics = DashboardService.get_lease_metrics()

        # Verify structure
        assert "total_leases" in metrics
        assert "active_leases" in metrics
        assert "inactive_leases" in metrics
        assert "contracts_generated" in metrics
        assert "contracts_pending" in metrics
        assert "expiring_soon" in metrics
        assert "expired_leases" in metrics

        # Verify counts
        assert metrics["total_leases"] == 3
        assert metrics["active_leases"] == 3  # All 3 have is_rented=True
        assert metrics["inactive_leases"] == 0

        # 2 have contract_generated=True
        assert metrics["contracts_generated"] == 2
        assert metrics["contracts_pending"] == 1

        # One lease is expired (started 400 days ago, 12 months = ~360 days)
        assert metrics["expired_leases"] >= 1

    def test_lease_metrics_expiring_soon(self, sample_apartments, sample_tenants):
        """Test detection of leases expiring soon."""
        today = date.today()

        # Create a lease expiring in 15 days
        lease = Lease.objects.create(
            apartment=sample_apartments[0],
            responsible_tenant=sample_tenants[0],
            start_date=today - timedelta(days=345),  # 345 days ago, 12 months = ~360 days
            validity_months=12,
            due_day=10,
            rental_value=Decimal("1000.00"),
            cleaning_fee=Decimal("100.00"),
            tag_fee=Decimal("50.00"),
            contract_generated=True,
        )
        lease.tenants.add(sample_tenants[0])
        sample_apartments[0].is_rented = True
        sample_apartments[0].save()

        metrics = DashboardService.get_lease_metrics()

        # Should detect this lease as expiring soon
        assert metrics["expiring_soon"] >= 1

    def test_lease_metrics_no_leases(self):
        """Test lease metrics with no leases."""
        metrics = DashboardService.get_lease_metrics()

        assert metrics["total_leases"] == 0
        assert metrics["active_leases"] == 0
        assert metrics["inactive_leases"] == 0
        assert metrics["contracts_generated"] == 0
        assert metrics["contracts_pending"] == 0
        assert metrics["expiring_soon"] == 0
        assert metrics["expired_leases"] == 0


class TestGetBuildingStatistics:
    """Test building statistics calculations."""

    def test_building_statistics_multiple_buildings(self, sample_leases):
        """Test building statistics with multiple buildings."""
        stats = DashboardService.get_building_statistics()

        # Should have 2 buildings
        assert len(stats) == 2

        # Verify structure
        for building_stat in stats:
            assert "building_id" in building_stat
            assert "building_number" in building_stat
            assert "total_apartments" in building_stat
            assert "rented_apartments" in building_stat
            assert "vacant_apartments" in building_stat
            assert "occupancy_rate" in building_stat
            assert "total_revenue" in building_stat

        # Find Building 836 stats
        building_836 = next(s for s in stats if s["building_number"] == 836)

        # Building 836 has 3 apartments, 2 rented
        assert building_836["total_apartments"] == 3
        assert building_836["rented_apartments"] == 2
        assert building_836["vacant_apartments"] == 1
        assert building_836["occupancy_rate"] == round(2 / 3 * 100, 2)

        # Total revenue: 1500 + 1500 = 3000
        assert building_836["total_revenue"] == Decimal("3000.00")

        # Find Building 850 stats
        building_850 = next(s for s in stats if s["building_number"] == 850)

        # Building 850 has 2 apartments, 1 rented
        assert building_850["total_apartments"] == 2
        assert building_850["rented_apartments"] == 1
        assert building_850["vacant_apartments"] == 1
        assert building_850["occupancy_rate"] == 50.0

        # Total revenue: 1800
        assert building_850["total_revenue"] == Decimal("1800.00")

    def test_building_statistics_no_buildings(self):
        """Test building statistics with no buildings."""
        Building.objects.all().delete()

        stats = DashboardService.get_building_statistics()

        assert stats == []

    def test_building_statistics_empty_building(self, sample_buildings):
        """Test building statistics with a building that has no apartments."""
        # Building 1 and 2 exist but let's remove all apartments
        Apartment.objects.all().delete()

        stats = DashboardService.get_building_statistics()

        # Should still have 2 buildings
        assert len(stats) == 2

        # All should have 0 apartments
        for building_stat in stats:
            assert building_stat["total_apartments"] == 0
            assert building_stat["rented_apartments"] == 0
            assert building_stat["vacant_apartments"] == 0
            assert building_stat["occupancy_rate"] == 0.0
            assert building_stat["total_revenue"] == Decimal("0.00")


class TestGetLatePaymentSummary:
    """Test late payment summary calculations."""

    @patch("core.services.dashboard_service.FeeCalculatorService.calculate_late_fee")
    def test_late_payment_summary_with_late_leases(self, mock_calculate_late_fee, sample_leases):
        """Test late payment summary with late leases."""

        # Mock some leases as late
        def late_fee_side_effect(*args, **kwargs):
            late_fee_side_effect.call_count += 1
            lease_count = late_fee_side_effect.call_count
            if lease_count == 1:
                # First lease is late
                return {"is_late": True, "late_days": 5, "late_fee": Decimal("250.00")}
            elif lease_count == 2:
                # Second lease is not late
                return {"is_late": False, "late_days": 0, "late_fee": Decimal("0.00")}
            else:
                # Third lease is late
                return {"is_late": True, "late_days": 10, "late_fee": Decimal("600.00")}

        late_fee_side_effect.call_count = 0
        mock_calculate_late_fee.side_effect = late_fee_side_effect

        summary = DashboardService.get_late_payment_summary()

        # Verify structure
        assert "total_late_leases" in summary
        assert "total_late_fees" in summary
        assert "average_late_days" in summary
        assert "late_leases" in summary

        # Should have 2 late leases
        assert summary["total_late_leases"] == 2

        # Total late fees: 250 + 600 = 850
        assert summary["total_late_fees"] == Decimal("850.00")

        # Average late days: (5 + 10) / 2 = 7.5
        assert summary["average_late_days"] == 7.5

        # Verify late_leases list
        assert len(summary["late_leases"]) == 2
        for late_lease in summary["late_leases"]:
            assert "lease_id" in late_lease
            assert "apartment_number" in late_lease
            assert "building_number" in late_lease
            assert "tenant_name" in late_lease
            assert "rental_value" in late_lease
            assert "due_day" in late_lease
            assert "late_days" in late_lease
            assert "late_fee" in late_lease

    @patch("core.services.dashboard_service.FeeCalculatorService.calculate_late_fee")
    def test_late_payment_summary_no_late_leases(self, mock_calculate_late_fee, sample_leases):
        """Test late payment summary when no leases are late."""
        # Mock all leases as not late
        mock_calculate_late_fee.return_value = {"is_late": False, "late_days": 0, "late_fee": Decimal("0.00")}

        summary = DashboardService.get_late_payment_summary()

        assert summary["total_late_leases"] == 0
        assert summary["total_late_fees"] == Decimal("0.00")
        assert summary["average_late_days"] == 0.0
        assert summary["late_leases"] == []

    @patch("core.services.dashboard_service.FeeCalculatorService.calculate_late_fee")
    def test_late_payment_summary_no_active_leases(self, mock_calculate_late_fee):
        """Test late payment summary with no active leases."""
        summary = DashboardService.get_late_payment_summary()

        assert summary["total_late_leases"] == 0
        assert summary["total_late_fees"] == Decimal("0.00")
        assert summary["average_late_days"] == 0.0
        assert summary["late_leases"] == []

        # FeeCalculatorService should not be called
        mock_calculate_late_fee.assert_not_called()


class TestGetTenantStatistics:
    """Test tenant statistics calculations."""

    def test_tenant_statistics_standard(self, sample_tenants, sample_dependents):
        """Test tenant statistics with standard data."""
        stats = DashboardService.get_tenant_statistics()

        # Verify structure
        assert "total_tenants" in stats
        assert "individual_tenants" in stats
        assert "company_tenants" in stats
        assert "tenants_with_dependents" in stats
        assert "total_dependents" in stats
        assert "marital_status_distribution" in stats

        # Verify counts
        assert stats["total_tenants"] == 3
        assert stats["individual_tenants"] == 2  # John and Jane
        assert stats["company_tenants"] == 1  # Company XYZ

        # John has 2 dependents
        assert stats["tenants_with_dependents"] == 1
        assert stats["total_dependents"] == 2

        # Marital status distribution (companies are excluded from this distribution)
        assert "Casado(a)" in stats["marital_status_distribution"]
        assert "Solteiro(a)" in stats["marital_status_distribution"]
        assert stats["marital_status_distribution"]["Casado(a)"] == 1
        # Note: Only 1 Solteiro(a) because Company XYZ is excluded (is_company=True)
        assert stats["marital_status_distribution"]["Solteiro(a)"] == 1

    def test_tenant_statistics_no_tenants(self):
        """Test tenant statistics with no tenants."""
        stats = DashboardService.get_tenant_statistics()

        assert stats["total_tenants"] == 0
        assert stats["individual_tenants"] == 0
        assert stats["company_tenants"] == 0
        assert stats["tenants_with_dependents"] == 0
        assert stats["total_dependents"] == 0
        assert stats["marital_status_distribution"] == {}

    def test_tenant_statistics_marital_status_variety(self, sample_tenants):
        """Test tenant statistics with various marital statuses."""
        # Create additional tenants with different marital statuses
        Tenant.objects.create(
            name="Divorced Tenant",
            cpf_cnpj="520.998.780-99",  # Valid CPF
            phone="11911111111",
            marital_status="Divorciado(a)",
            profession="Worker",
            is_company=False,
        )

        stats = DashboardService.get_tenant_statistics()

        # Should have multiple marital status entries
        # sample_tenants has: "Casado(a)", "Solteiro(a)", "Solteiro(a)"
        # Plus we added "Divorciado(a)"
        assert len(stats["marital_status_distribution"]) >= 3
        assert "Divorciado(a)" in stats["marital_status_distribution"]
        assert stats["marital_status_distribution"]["Divorciado(a)"] == 1

    def test_tenant_statistics_multiple_dependents(self, sample_tenants):
        """Test tenant statistics with multiple tenants having dependents."""
        # Add dependents to multiple tenants
        Dependent.objects.create(tenant=sample_tenants[0], name="Dependent 1", phone="11911111111")
        Dependent.objects.create(tenant=sample_tenants[1], name="Dependent 2", phone="11922222222")
        Dependent.objects.create(tenant=sample_tenants[1], name="Dependent 3", phone="11933333333")

        stats = DashboardService.get_tenant_statistics()

        # 2 tenants have dependents
        assert stats["tenants_with_dependents"] == 2

        # Total of 3 dependents
        assert stats["total_dependents"] == 3


class TestDashboardServiceIntegration:
    """Integration tests for DashboardService."""

    def test_complete_dashboard_workflow(self, sample_leases, sample_dependents):
        """Test complete dashboard data retrieval workflow."""
        # Get all metrics
        financial = DashboardService.get_financial_summary()
        lease_metrics = DashboardService.get_lease_metrics()
        building_stats = DashboardService.get_building_statistics()
        tenant_stats = DashboardService.get_tenant_statistics()

        # Verify all return proper data structures
        assert isinstance(financial, dict)
        assert isinstance(lease_metrics, dict)
        assert isinstance(building_stats, list)
        assert isinstance(tenant_stats, dict)

        # Verify consistency across metrics
        assert financial["rented_apartments"] == lease_metrics["active_leases"]
        assert sum(bs["total_apartments"] for bs in building_stats) == financial["total_apartments"]

    @patch("core.services.dashboard_service.FeeCalculatorService.calculate_late_fee")
    def test_all_metrics_with_late_payments(self, mock_calculate_late_fee, sample_leases):
        """Test all metrics together with late payment calculations."""
        # Mock late payments
        mock_calculate_late_fee.return_value = {"is_late": True, "late_days": 3, "late_fee": Decimal("150.00")}

        # Get all metrics
        financial = DashboardService.get_financial_summary()
        late_payments = DashboardService.get_late_payment_summary()

        # All active leases should be late
        assert late_payments["total_late_leases"] == financial["rented_apartments"]
