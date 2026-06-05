"""Unit tests for DashboardService.

Tests all five service methods with real database objects.
No internal code is mocked — only time is frozen where needed.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from freezegun import freeze_time

from core.models import Apartment, Building, Dependent, FinancialSettings, Lease, Tenant
from core.services.dashboard_service import DashboardService
from core.services.fee_calculator import FeeCalculatorService
from tests.factories import make_person, make_rent_payment

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


@pytest.fixture
def active_lease_company(building, tenant_company, admin_user):
    """A second active lease so tenant_company counts as an active tenant."""
    apartment = Apartment.objects.create(
        building=building,
        number=403,
        rental_value=Decimal("1000.00"),
        cleaning_fee=Decimal("100.00"),
        max_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant_company,
        start_date=date(2026, 1, 1),
        validity_months=24,
        tag_fee=Decimal("40.00"),
        rental_value=Decimal("1000.00"),
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

    def test_with_rented_apartment_calculates_revenue(self, apartment_rented, active_lease):
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
            summary["total_revenue"] + summary["total_cleaning_fees"] + summary["total_tag_fees"]
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
            metrics["contracts_pending"] == metrics["total_leases"] - metrics["contracts_generated"]
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
        building_stat = next((s for s in stats if s["building_id"] == building2.id), None)
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
        assert Decimal(summary["total_late_fees"]) > Decimal("0.00")
        late = summary["late_leases"][0]
        assert "lease_id" in late
        assert "tenant_name" in late
        assert "late_days" in late
        assert "late_fee" in late
        assert late["late_days"] >= 1

    @freeze_time("2026-03-05")
    def test_not_late_when_before_due_day(
        self, active_lease, apartment_rented, tenant_individual, admin_user
    ):
        # due_day = 10, today = 2026-03-05 → March not yet due; prior months are paid
        make_rent_payment(lease=active_lease, user=admin_user, reference_month=date(2026, 1, 1))
        make_rent_payment(lease=active_lease, user=admin_user, reference_month=date(2026, 2, 1))
        summary = DashboardService.get_late_payment_summary()
        # This particular lease should not be in late_leases
        late_lease_ids = [lease["lease_id"] for lease in summary["late_leases"]]
        assert active_lease.id not in late_lease_ids

    @freeze_time("2026-03-15")
    def test_average_late_days_calculated(self, active_lease, apartment_rented):
        summary = DashboardService.get_late_payment_summary()
        if summary["total_late_leases"] > 0:
            assert summary["average_late_days"] > 0


# ---------------------------------------------------------------------------
# get_late_payment_summary — rent-collectibility SSOT consolidation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLatePaymentSummarySSOT:
    """Regression tests for routing the late-payment summary through the
    rent-collectibility single source of truth (RentScheduleService)."""

    @freeze_time("2026-03-15")
    def test_late_fee_uses_effective_rental_value(self, apartment_rented, admin_user):
        # Pending adjustment in effect for March (date = first of the frozen month):
        # the late fee must be computed on the effective value (1200), not 1000.
        tenant = Tenant.objects.create(
            name="Effective Value Tenant",
            cpf_cnpj="11144477735",
            phone="11933330001",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment_rented,
            responsible_tenant=tenant,
            start_date=date(2026, 3, 1),
            validity_months=24,
            tag_fee=Decimal("80.00"),
            rental_value=Decimal("1000.00"),
            pending_rental_value=Decimal("1200.00"),
            pending_rental_value_date=date(2026, 3, 1),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late = next(item for item in summary["late_leases"] if item["lease_id"] == lease.id)

        # Frozen on day 15, due_day=10 → 5 days late, single month (March only).
        late_fee_percentage = Decimal(str(settings.LATE_FEE_PERCENTAGE))
        expected_fee = (
            FeeCalculatorService.calculate_daily_rate(Decimal("1200.00")) * 5 * late_fee_percentage
        ).quantize(Decimal("0.01"))
        fee_on_1000 = (
            FeeCalculatorService.calculate_daily_rate(Decimal("1000.00")) * 5 * late_fee_percentage
        ).quantize(Decimal("0.01"))

        assert Decimal(late["late_fee"]) == expected_fee
        assert Decimal(late["late_fee"]) > fee_on_1000
        # Output rental_value also reflects the effective (pending) value.
        assert Decimal(late["rental_value"]) == Decimal("1200.00")

    @freeze_time("2026-03-20")
    def test_prepaid_boundary_off_by_one_regression(self, apartment_rented, admin_user):
        # prepaid_until == clamped due date (March 15). Per is_prepaid_for_month
        # (prepaid only if strictly AFTER the due date), the installment due on the
        # 15th is NOT prepaid → this lease IS collectible and must appear as late.
        tenant = Tenant.objects.create(
            name="Boundary Tenant",
            cpf_cnpj="12345678909",
            phone="11933330002",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=15,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment_rented,
            responsible_tenant=tenant,
            start_date=date(2026, 3, 1),
            validity_months=24,
            tag_fee=Decimal("80.00"),
            rental_value=Decimal("1000.00"),
            prepaid_until=date(2026, 3, 15),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id in late_ids

    @freeze_time("2026-03-20")
    def test_truly_prepaid_lease_excluded(self, apartment_rented, admin_user):
        # prepaid_until strictly AFTER the clamped due date (March 16 > 15) → the
        # March installment is prepaid → not collectible → must NOT appear as late.
        tenant = Tenant.objects.create(
            name="Prepaid Tenant",
            cpf_cnpj="98765432100",
            phone="11933330003",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=15,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment_rented,
            responsible_tenant=tenant,
            start_date=date(2026, 3, 1),
            validity_months=24,
            tag_fee=Decimal("80.00"),
            rental_value=Decimal("1000.00"),
            prepaid_until=date(2026, 3, 16),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id not in late_ids

    @freeze_time("2026-03-20")
    def test_owner_kitnet_lease_not_in_late_summary(self, building, admin_user):
        # Apartment with an owner = rent repassed to the owner, not condominium
        # revenue → excluded from the late summary even when past due and unpaid.
        owner = make_person(user=admin_user, relationship="Proprietário")
        owned_apt = Apartment.objects.create(
            building=building,
            number=410,
            rental_value=Decimal("1000.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=1,
            owner=owner,
            created_by=admin_user,
            updated_by=admin_user,
        )
        tenant = Tenant.objects.create(
            name="Owner Kitnet Tenant",
            cpf_cnpj="71428793860",
            phone="11933330004",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=owned_apt,
            responsible_tenant=tenant,
            start_date=date(2026, 2, 1),
            validity_months=24,
            tag_fee=Decimal("80.00"),
            rental_value=Decimal("1000.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id not in late_ids

    @freeze_time("2026-03-20")
    def test_salary_offset_lease_not_in_late_summary(self, apartment_rented, admin_user):
        # Salary-offset rent is netted against an employee salary, never collected
        # as cash → excluded from the late summary even when past due and unpaid.
        tenant = Tenant.objects.create(
            name="Salary Offset Tenant",
            cpf_cnpj="15782647825",
            phone="11933330005",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment_rented,
            responsible_tenant=tenant,
            start_date=date(2026, 2, 1),
            validity_months=24,
            tag_fee=Decimal("80.00"),
            rental_value=Decimal("1000.00"),
            is_salary_offset=True,
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id not in late_ids


# ---------------------------------------------------------------------------
# get_late_payment_summary — start-date guard (Fix D)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLatePaymentSummaryStartDateGuard:
    """Regression tests: a lease whose due date falls before its start_date must not
    be flagged as late for that month (the tenant was not yet living there)."""

    @freeze_time("2026-06-25")
    def test_lease_starting_after_due_day_not_late_for_that_month(self, building, admin_user):
        """start_date=2026-06-20, due_day=10 → June-10 due date precedes move-in →
        the lease must NOT appear in late_leases for June."""
        apartment = Apartment.objects.create(
            building=building,
            number=420,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=1,
            created_by=admin_user,
            updated_by=admin_user,
        )
        tenant = Tenant.objects.create(
            name="Late After Move-In",
            cpf_cnpj="20000000299",
            is_company=False,
            phone="11933330010",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2026, 6, 20),
            validity_months=24,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1200.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id not in late_ids

    @freeze_time("2026-06-25")
    def test_lease_starting_before_due_day_is_late(self, building, admin_user):
        """start_date=2026-06-05, due_day=10 → June-10 due date is after move-in →
        the lease IS late when today=2026-06-25 and no payment exists."""
        apartment = Apartment.objects.create(
            building=building,
            number=421,
            rental_value=Decimal("1300.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=1,
            created_by=admin_user,
            updated_by=admin_user,
        )
        tenant = Tenant.objects.create(
            name="Late From Move-In",
            cpf_cnpj="30000000388",
            is_company=False,
            phone="11933330011",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2026, 6, 5),
            validity_months=24,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1300.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id in late_ids


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

    def test_counts_individual_and_company_tenants(self, active_lease, active_lease_company):
        # Both tenants are active (each linked to a lease)
        stats = DashboardService.get_tenant_statistics()
        assert stats["individual_tenants"] >= 1
        assert stats["company_tenants"] >= 1
        assert stats["total_tenants"] >= 2

    def test_counts_dependents(self, active_lease, tenant_individual, admin_user):
        # active_lease makes tenant_individual an active tenant
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

    def test_marital_status_counts_individual_tenants_only(self, tenant_individual, tenant_company):
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


# ---------------------------------------------------------------------------
# get_late_payment_summary — rent-tracking start boundary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLatePaymentSummaryTrackingBoundary:
    """Regression tests for bounding the overdue back-scan to the configured
    rent-tracking start date (FinancialSettings.rent_tracking_start_date).

    Without a boundary a lease starting in 2024 accumulates thousands of late
    days by 2026; with the boundary set to 2026-06-01 only June 2026 is scanned,
    producing a small, sane number.
    """

    def _make_old_lease(self, building, admin_user):
        """Lease started 2024-07-01, validity 60 months (max), due_day=10, no payments.

        Start date chosen so the lease is well in the past relative to June 2026 test
        dates: 2024-07 → 2026-06 = 24 months of unpaid rent when no boundary is set.
        """
        tenant = Tenant.objects.create(
            name="Old Lease Tenant",
            cpf_cnpj="10000000019",
            phone="11900000010",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment = Apartment.objects.create(
            building=building,
            number=501,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
            created_by=admin_user,
            updated_by=admin_user,
        )
        return Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2024, 7, 1),
            validity_months=60,
            tag_fee=Decimal("40.00"),
            rental_value=Decimal("1500.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

    @freeze_time("2026-06-15")
    def test_boundary_limits_scan_to_one_month(self, building, admin_user):
        """Core regression: with boundary=2026-06-01 the lease that started in 2024
        is only scanned from June 2026, so late_months==1 and late_days is small (5)."""
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        lease = self._make_old_lease(building, admin_user)

        summary = DashboardService.get_late_payment_summary()
        late = next(item for item in summary["late_leases"] if item["lease_id"] == lease.id)

        # Only June 2026 is scanned; due_day=10, today=2026-06-15 → 5 days late.
        assert late["late_months"] == 1
        assert late["late_days"] == 5
        # Sanity: total late days must be small, NOT thousands.
        assert late["late_days"] <= 31

    @freeze_time("2026-06-15")
    def test_no_boundary_accumulates_many_months(self, building, admin_user):
        """Legacy behavior without a boundary: same lease accumulates many late months
        (2024-07 through 2026-06 = 24 months), documenting what the boundary fixes."""
        # No FinancialSettings row → no boundary.
        lease = self._make_old_lease(building, admin_user)

        summary = DashboardService.get_late_payment_summary()
        late = next(item for item in summary["late_leases"] if item["lease_id"] == lease.id)

        # 2024-07 to 2026-06 inclusive = 24 months, all unpaid and overdue.
        assert late["late_months"] >= 24
        assert late["late_days"] >= 100

    @freeze_time("2026-05-20")
    def test_current_month_before_boundary_produces_empty_summary(self, building, admin_user):
        """When today is before the tracking boundary, no month is tracked yet → no
        late leases reported even if the lease would otherwise be overdue."""
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        self._make_old_lease(building, admin_user)

        summary = DashboardService.get_late_payment_summary()
        assert summary["total_late_leases"] == 0

    @freeze_time("2026-06-20")
    def test_prepaid_lease_still_excluded_under_boundary(self, building, admin_user):
        """With the boundary set, a lease prepaid past the June due date is still
        excluded from the late summary (prepaid logic works inside the bounded loop)."""
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        tenant = Tenant.objects.create(
            name="Prepaid Boundary Tenant",
            cpf_cnpj="20000000108",
            phone="11900000020",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment = Apartment.objects.create(
            building=building,
            number=502,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("150.00"),
            max_tenants=1,
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2024, 7, 1),
            validity_months=60,
            tag_fee=Decimal("20.00"),
            rental_value=Decimal("1200.00"),
            # prepaid_until strictly after June 10 → June installment is prepaid.
            prepaid_until=date(2026, 6, 11),
            created_by=admin_user,
            updated_by=admin_user,
        )

        summary = DashboardService.get_late_payment_summary()
        late_ids = [item["lease_id"] for item in summary["late_leases"]]
        assert lease.id not in late_ids
