"""
Dashboard service for financial metrics and operational statistics.

Phase 7: Advanced Features - Dashboard Service Foundation

Provides:
- Financial summary (revenue, occupancy, late payments)
- Lease metrics (active, expiring, contract status)
- Building and apartment statistics
- Tenant analytics
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Count, DateField, Q, Sum
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.cache import cache_result
from core.models import Apartment, Building, Dependent, Lease, RentPayment, Tenant
from core.services.rent_schedule_service import RentScheduleService

from .fee_calculator import FeeCalculatorService

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service for dashboard metrics and financial summaries.

    Provides business intelligence metrics for property management:
    - Total revenue and occupancy rates
    - Active/inactive lease counts
    - Contract generation status
    - Late payment calculations
    - Building/apartment utilization

    Example usage:
        >>> summary = DashboardService.get_financial_summary()
        >>> print(f"Total revenue: R$ {summary['total_revenue']}")
        >>> print(f"Occupancy rate: {summary['occupancy_rate']}%")

        >>> lease_metrics = DashboardService.get_lease_metrics()
        >>> print(f"Active leases: {lease_metrics['active_leases']}")
    """

    @staticmethod
    @cache_result(timeout=120, key_prefix="dashboard-financial-summary")
    def get_financial_summary() -> dict[str, Any]:
        """
        Calculate financial summary across all properties.

        Returns:
            Dictionary containing:
            - total_revenue: Total monthly rental revenue
            - total_cleaning_fees: Total cleaning fees
            - total_tag_fees: Total tag fees
            - total_income: Total monthly income (sum of all fees)
            - occupancy_rate: Percentage of rented apartments
            - total_apartments: Total number of apartments
            - rented_apartments: Number of rented apartments
            - vacant_apartments: Number of vacant apartments
            - revenue_per_apartment: Average revenue per rented apartment

        Example:
            >>> summary = DashboardService.get_financial_summary()
            >>> print(summary)
            {
                'total_revenue': Decimal('15000.00'),
                'total_cleaning_fees': Decimal('2000.00'),
                'total_tag_fees': Decimal('800.00'),
                'total_income': Decimal('17800.00'),
                'occupancy_rate': 75.0,
                'total_apartments': 20,
                'rented_apartments': 15,
                'vacant_apartments': 5,
                'revenue_per_apartment': Decimal('1000.00')
            }
        """
        logger.info("Calculating financial summary")

        # Get active leases (apartments with contracts)
        active_leases = Lease.objects.filter(apartment__is_rented=True)

        # Calculate revenue totals
        revenue_aggregates = active_leases.aggregate(
            total_revenue=Coalesce(Sum("rental_value"), Decimal("0.00")),
            total_cleaning_fees=Coalesce(Sum("apartment__cleaning_fee"), Decimal("0.00")),
            total_tag_fees=Coalesce(Sum("tag_fee"), Decimal("0.00")),
        )

        total_revenue = revenue_aggregates["total_revenue"]
        total_cleaning_fees = revenue_aggregates["total_cleaning_fees"]
        total_tag_fees = revenue_aggregates["total_tag_fees"]
        total_income = total_revenue + total_cleaning_fees + total_tag_fees

        # Calculate occupancy metrics
        apartment_stats = Apartment.objects.aggregate(
            total_apartments=Count("id"),
            rented_apartments=Count("id", filter=Q(is_rented=True)),
        )

        total_apartments = apartment_stats["total_apartments"]
        rented_apartments = apartment_stats["rented_apartments"]
        vacant_apartments = total_apartments - rented_apartments

        # Calculate occupancy rate and revenue per apartment
        occupancy_rate = (rented_apartments / total_apartments * 100) if total_apartments > 0 else 0
        revenue_per_apartment = (
            (total_income / rented_apartments) if rented_apartments > 0 else Decimal("0.00")
        )

        summary = {
            "total_revenue": total_revenue,
            "total_cleaning_fees": total_cleaning_fees,
            "total_tag_fees": total_tag_fees,
            "total_income": total_income,
            "occupancy_rate": round(occupancy_rate, 2),
            "total_apartments": total_apartments,
            "rented_apartments": rented_apartments,
            "vacant_apartments": vacant_apartments,
            "revenue_per_apartment": revenue_per_apartment.quantize(Decimal("0.01")),
        }

        logger.info(f"Financial summary: Revenue={total_revenue}, Occupancy={occupancy_rate:.1f}%")
        return summary

    @staticmethod
    @cache_result(timeout=120, key_prefix="dashboard-lease-metrics")
    def get_lease_metrics() -> dict[str, Any]:
        """
        Calculate lease statistics and metrics.

        Returns:
            Dictionary containing:
            - total_leases: Total number of leases
            - active_leases: Number of active (rented) leases
            - inactive_leases: Number of inactive leases
            - contracts_generated: Number of leases with contracts
            - contracts_pending: Number of leases without contracts
            - expiring_soon: Number of leases expiring in next 30 days
            - expired_leases: Number of leases that have expired

        Example:
            >>> metrics = DashboardService.get_lease_metrics()
            >>> print(metrics)
            {
                'total_leases': 15,
                'active_leases': 12,
                'inactive_leases': 3,
                'contracts_generated': 10,
                'contracts_pending': 5,
                'expiring_soon': 2,
                'expired_leases': 3
            }
        """
        logger.info("Calculating lease metrics")

        today = timezone.now().date()
        expiry_threshold = today + timedelta(days=30)

        # Count leases by various statuses
        lease_stats = Lease.objects.aggregate(
            total_leases=Count("id"),
            active_leases=Count("id", filter=Q(apartment__is_rented=True)),
            contracts_generated=Count("id", filter=Q(contract_generated=True)),
        )

        total_leases = lease_stats["total_leases"]
        active_leases = lease_stats["active_leases"]
        contracts_generated = lease_stats["contracts_generated"]

        inactive_leases = total_leases - active_leases
        contracts_pending = total_leases - contracts_generated

        # Calculate expiring and expired leases using database-level annotation

        annotated = Lease.objects.annotate(
            end_date=RawSQL(
                "(start_date + (validity_months || ' months')::interval)::date",
                [],
                output_field=DateField(),
            ),
        )
        counts = annotated.aggregate(
            expiring_soon=Count(
                "id", filter=Q(end_date__gte=today, end_date__lte=expiry_threshold)
            ),
            expired_leases=Count("id", filter=Q(end_date__lt=today)),
        )
        expiring_soon = counts["expiring_soon"]
        expired_leases = counts["expired_leases"]

        metrics = {
            "total_leases": total_leases,
            "active_leases": active_leases,
            "inactive_leases": inactive_leases,
            "contracts_generated": contracts_generated,
            "contracts_pending": contracts_pending,
            "expiring_soon": expiring_soon,
            "expired_leases": expired_leases,
        }

        logger.info(
            f"Lease metrics: Total={total_leases}, Active={active_leases}, Expiring soon={expiring_soon}"
        )
        return metrics

    @staticmethod
    @cache_result(timeout=300, key_prefix="dashboard-building-stats")
    def get_building_statistics() -> list[dict[str, Any]]:
        """
        Get per-building statistics and occupancy.

        Returns:
            List of dictionaries, one per building, containing:
            - building_id: Building primary key
            - building_number: Street number of the building
            - total_apartments: Total apartments in building
            - rented_apartments: Number of rented apartments
            - vacant_apartments: Number of vacant apartments
            - occupancy_rate: Percentage of rented apartments
            - total_revenue: Total monthly revenue from building

        Example:
        Get aggregated statistics per building.
        Returns total/rented/vacant apartments and revenue per building.
        Cached for 5 minutes as it requires complex aggregation.
        """
        logger.info("Calculating building statistics")

        # Get building counts
        buildings = Building.objects.annotate(
            total_apartments=Count("apartments", distinct=True),
            rented_apartments=Count(
                "apartments", filter=Q(apartments__is_rented=True), distinct=True
            ),
        ).values("id", "street_number", "total_apartments", "rented_apartments")

        # Get revenue per building including fees
        revenue_per_building = (
            Lease.objects.filter(apartment__is_rented=True, is_deleted=False)
            .values("apartment__building_id")
            .annotate(
                sum_rental=Coalesce(Sum("rental_value"), Decimal("0.00")),
                sum_cleaning=Coalesce(Sum("apartment__cleaning_fee"), Decimal("0.00")),
                sum_tag=Coalesce(Sum("tag_fee"), Decimal("0.00")),
            )
        )

        revenue_map = {
            item["apartment__building_id"]: item["sum_rental"]
            + item["sum_cleaning"]
            + item["sum_tag"]
            for item in revenue_per_building
        }

        building_stats = []

        for building in buildings:
            total_apartments = building["total_apartments"]
            rented_apartments = building["rented_apartments"]
            vacant_apartments = total_apartments - rented_apartments

            occupancy_rate = (
                (rented_apartments / total_apartments * 100) if total_apartments > 0 else 0
            )
            total_revenue = revenue_map.get(building["id"], Decimal("0.00"))

            building_stats.append(
                {
                    "building_id": building["id"],
                    "building_number": building["street_number"],
                    "total_apartments": total_apartments,
                    "rented_apartments": rented_apartments,
                    "vacant_apartments": vacant_apartments,
                    "occupancy_rate": round(occupancy_rate, 2),
                    "total_revenue": (
                        total_revenue.quantize(Decimal("0.01"))
                        if isinstance(total_revenue, Decimal)
                        else Decimal(str(total_revenue)).quantize(Decimal("0.01"))
                    ),
                }
            )

        logger.info(f"Calculated statistics for {len(building_stats)} buildings")
        return building_stats

    @staticmethod
    @cache_result(timeout=120, key_prefix="dashboard-late-payment")
    def get_late_payment_summary() -> dict[str, Any]:
        """
        Calculate late payment statistics across all active leases.

        Only considers leases where the current month's rent has NOT been paid
        (checked via RentPayment records). Excludes prepaid, salary-offset,
        and owner-occupied leases.

        Returns:
            Dictionary containing:
            - total_late_leases: Number of leases with late payments
            - total_late_fees: Sum of all late fees
            - average_late_days: Average number of late days
            - late_leases: List of dictionaries with lease details
        """
        logger.info("Calculating late payment summary")

        today = timezone.now().date()
        month_start = today.replace(day=1)

        late_leases = []
        total_late_fees = Decimal("0.00")
        total_late_days = 0

        # Collectible leases for the current month (single source of truth): excludes
        # soft-deleted, owner-repass, salary-offset and prepaid-for-month leases.
        collectible_leases = list(RentScheduleService.collectible_leases(month_start))

        # Fetch all rent payments to build a ledger up to the current month
        all_payments = RentPayment.objects.filter(
            lease__in=collectible_leases, reference_month__lte=month_start
        ).values("lease_id", "reference_month", "payment_date")

        payments_by_lease: dict[int, set[date]] = {}
        last_payments: dict[int, date] = {}
        for p in all_payments:
            lid = p["lease_id"]
            payments_by_lease.setdefault(lid, set()).add(p["reference_month"])

            existing_last = last_payments.get(lid)
            if not existing_last or p["payment_date"] > existing_last:
                last_payments[lid] = p["payment_date"]

        for lease in collectible_leases:
            lease_payments = payments_by_lease.get(lease.id, set())
            start_month = lease.start_date.replace(day=1)

            curr_month_iter = start_month
            lease_late_months_count = 0
            lease_total_late_fee = Decimal("0.00")
            lease_total_late_days = 0

            while curr_month_iter <= month_start:
                if not RentScheduleService.is_collectible_for_month(
                    lease, curr_month_iter.year, curr_month_iter.month
                ):
                    curr_month_iter = curr_month_iter + relativedelta(months=1)
                    continue

                if curr_month_iter not in lease_payments:
                    due_day = RentScheduleService.clamp_due_day(
                        lease.responsible_tenant.due_day,
                        curr_month_iter.year,
                        curr_month_iter.month,
                    )
                    due_date = curr_month_iter.replace(day=due_day)

                    if today > due_date:
                        late_days = (today - due_date).days
                        daily_rate = FeeCalculatorService.calculate_daily_rate(
                            RentScheduleService.effective_rental_value(lease, curr_month_iter)
                        )
                        late_fee_percentage = Decimal(str(settings.LATE_FEE_PERCENTAGE))
                        late_fee = daily_rate * late_days * late_fee_percentage

                        lease_late_months_count += 1
                        lease_total_late_fee += late_fee
                        lease_total_late_days += late_days

                curr_month_iter = curr_month_iter + relativedelta(months=1)

            if lease_late_months_count > 0:
                total_late_fees += lease_total_late_fee
                total_late_days += lease_total_late_days
                last_payment_date = last_payments.get(lease.id)

                late_leases.append(
                    {
                        "lease_id": lease.id,
                        "apartment_number": lease.apartment.number,
                        "building_number": lease.apartment.building.street_number,
                        "tenant_name": lease.responsible_tenant.name,
                        "rental_value": str(
                            RentScheduleService.effective_rental_value(lease, month_start)
                        ),
                        "due_day": lease.responsible_tenant.due_day,
                        "late_days": lease_total_late_days,
                        "late_fee": str(lease_total_late_fee.quantize(Decimal("0.01"))),
                        "late_months": lease_late_months_count,
                        "last_payment_date": (
                            last_payment_date.isoformat() if last_payment_date else None
                        ),
                    }
                )

        average_late_days = (total_late_days / len(late_leases)) if late_leases else 0

        summary = {
            "total_late_leases": len(late_leases),
            "total_late_fees": str(total_late_fees.quantize(Decimal("0.01"))),
            "average_late_days": round(float(average_late_days), 1),
            "late_leases": late_leases,
        }

        logger.info(
            f"Late payment summary: {len(late_leases)} leases late, total fees=R$ {total_late_fees}"
        )
        return summary

    @staticmethod
    @cache_result(timeout=300, key_prefix="dashboard-tenant-stats")
    def get_tenant_statistics() -> dict[str, Any]:
        """
        Calculate tenant statistics and demographics.

        Only ACTIVE tenants — those linked to a non-deleted lease — are counted;
        registered tenants without a current lease are excluded.

        Returns:
            Dictionary containing:
            - total_tenants: Total number of active tenants
            - individual_tenants: Number of individual (non-company) tenants
            - company_tenants: Number of company tenants
            - tenants_with_dependents: Number of tenants with dependents
            - total_dependents: Total number of dependents
            - marital_status_distribution: Distribution of marital statuses

        Example:
            >>> stats = DashboardService.get_tenant_statistics()
            >>> print(f"Total tenants: {stats['total_tenants']}")
            >>> print(
            ...     f"Individuals: {stats['individual_tenants']}, "
            ...     f"Companies: {stats['company_tenants']}"
            ... )
        """
        logger.info("Calculating tenant statistics")

        # Aggregate tenant counts — only ACTIVE tenants (those with a non-deleted lease)
        tenant_stats = (
            Tenant.objects.filter(
                Q(leases_responsible__is_deleted=False) | Q(leases__is_deleted=False)
            )
            .distinct()
            .aggregate(
                total_tenants=Count("id"),
                individual_tenants=Count("id", filter=Q(is_company=False)),
                company_tenants=Count("id", filter=Q(is_company=True)),
            )
        )

        # Count tenants with dependents
        tenants_with_dependents = (
            Tenant.objects.filter(
                Q(leases_responsible__is_deleted=False) | Q(leases__is_deleted=False),
                dependents__isnull=False,
            )
            .distinct()
            .count()
        )

        # Count total dependents of active tenants
        total_dependents = Dependent.objects.filter(
            tenant__in=Tenant.objects.filter(
                Q(leases_responsible__is_deleted=False) | Q(leases__is_deleted=False)
            )
        ).count()

        # Get marital status distribution using values().annotate() - single query
        marital_status_qs = (
            Tenant.objects.filter(
                Q(leases_responsible__is_deleted=False) | Q(leases__is_deleted=False),
                is_company=False,
            )
            .values("marital_status")
            .annotate(count=Count("id"))
        )
        marital_status_distribution = {}
        for item in marital_status_qs:
            status = item["marital_status"] or "Not specified"
            marital_status_distribution[status] = item["count"]

        statistics = {
            "total_tenants": tenant_stats["total_tenants"],
            "individual_tenants": tenant_stats["individual_tenants"],
            "company_tenants": tenant_stats["company_tenants"],
            "tenants_with_dependents": tenants_with_dependents,
            "total_dependents": total_dependents,
            "marital_status_distribution": marital_status_distribution,
        }

        logger.info(
            f"Tenant statistics: Total={statistics['total_tenants']}, "
            f"Individuals={statistics['individual_tenants']}"
        )
        return statistics
