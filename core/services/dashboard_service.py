"""
Dashboard service for financial metrics and operational statistics.

Phase 7: Advanced Features - Dashboard Service Foundation

Provides:
- Financial summary (revenue, occupancy, late payments)
- Lease metrics (active, expiring, contract status)
- Building and apartment statistics
- Tenant analytics
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from core.models import Apartment, Building, Lease, Tenant

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
    def get_financial_summary() -> Dict[str, Any]:
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
            total_cleaning_fees=Coalesce(Sum("cleaning_fee"), Decimal("0.00")),
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
        revenue_per_apartment = (total_revenue / rented_apartments) if rented_apartments > 0 else Decimal("0.00")

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
    def get_lease_metrics() -> Dict[str, Any]:
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

        today = date.today()
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

        # Calculate expiring and expired leases using database-level filtering
        # Instead of looping, we filter by start_date ranges
        # A lease is expired if start_date + validity_months * 30 days < today
        # A lease is expiring soon if start_date + validity_months * 30 days <= today + 30
        #
        # We use values() to calculate in Python but with minimal data transfer
        lease_dates = Lease.objects.values("start_date", "validity_months")

        expiring_soon = 0
        expired_leases = 0

        for lease_data in lease_dates:
            final_date = lease_data["start_date"] + timedelta(days=lease_data["validity_months"] * 30)
            if final_date < today:
                expired_leases += 1
            elif final_date <= expiry_threshold:
                expiring_soon += 1

        metrics = {
            "total_leases": total_leases,
            "active_leases": active_leases,
            "inactive_leases": inactive_leases,
            "contracts_generated": contracts_generated,
            "contracts_pending": contracts_pending,
            "expiring_soon": expiring_soon,
            "expired_leases": expired_leases,
        }

        logger.info(f"Lease metrics: Total={total_leases}, Active={active_leases}, " f"Expiring soon={expiring_soon}")
        return metrics

    @staticmethod
    def get_building_statistics() -> List[Dict[str, Any]]:
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
            >>> stats = DashboardService.get_building_statistics()
            >>> for building_stat in stats:
            ...     print(f"Building {building_stat['building_number']}: "
            ...           f"{building_stat['occupancy_rate']}% occupied")
        """
        logger.info("Calculating building statistics")

        # Use annotations for efficient aggregation - single query instead of N+1
        buildings = Building.objects.annotate(
            total_apartments=Count("apartments"),
            rented_apartments=Count("apartments", filter=Q(apartments__is_rented=True)),
            total_revenue=Coalesce(
                Sum("apartments__lease__rental_value", filter=Q(apartments__is_rented=True)),
                Decimal("0.00"),
            ),
        ).values("id", "street_number", "total_apartments", "rented_apartments", "total_revenue")

        building_stats = []

        for building in buildings:
            total_apartments = building["total_apartments"]
            rented_apartments = building["rented_apartments"]
            vacant_apartments = total_apartments - rented_apartments

            occupancy_rate = (rented_apartments / total_apartments * 100) if total_apartments > 0 else 0
            total_revenue = building["total_revenue"] or Decimal("0.00")

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
    def get_late_payment_summary() -> Dict[str, Any]:
        """
        Calculate late payment statistics across all active leases.

        Returns:
            Dictionary containing:
            - total_late_leases: Number of leases with late payments
            - total_late_fees: Sum of all late fees
            - average_late_days: Average number of late days
            - late_leases: List of dictionaries with lease details

        Example:
            >>> summary = DashboardService.get_late_payment_summary()
            >>> print(f"{summary['total_late_leases']} leases are late")
            >>> print(f"Total late fees: R$ {summary['total_late_fees']}")
        """
        logger.info("Calculating late payment summary")

        today = date.today()

        late_leases = []
        total_late_fees = Decimal("0.00")
        total_late_days = 0

        # Check all active leases - use select_related to avoid N+1 queries
        active_leases = Lease.objects.filter(apartment__is_rented=True).select_related(
            "apartment", "apartment__building", "responsible_tenant"
        )

        for lease in active_leases:
            # Calculate if payment is late
            result = FeeCalculatorService.calculate_late_fee(
                rental_value=lease.rental_value, due_day=lease.due_day, current_date=today
            )

            if result["is_late"]:
                late_days = result["late_days"]
                late_fee = result["late_fee"]
                total_late_fees += late_fee
                total_late_days += late_days

                late_leases.append(
                    {
                        "lease_id": lease.id,
                        "apartment_number": lease.apartment.number,
                        "building_number": lease.apartment.building.street_number,
                        "tenant_name": lease.responsible_tenant.name,
                        "rental_value": lease.rental_value,
                        "due_day": lease.due_day,
                        "late_days": late_days,
                        "late_fee": late_fee,
                    }
                )

        average_late_days = total_late_days / len(late_leases) if late_leases else 0

        summary = {
            "total_late_leases": len(late_leases),
            "total_late_fees": total_late_fees.quantize(Decimal("0.01")),
            "average_late_days": round(average_late_days, 1),
            "late_leases": late_leases,
        }

        logger.info(f"Late payment summary: {len(late_leases)} leases late, " f"total fees=R$ {total_late_fees}")
        return summary

    @staticmethod
    def get_tenant_statistics() -> Dict[str, Any]:
        """
        Calculate tenant statistics and demographics.

        Returns:
            Dictionary containing:
            - total_tenants: Total number of tenants
            - individual_tenants: Number of individual (non-company) tenants
            - company_tenants: Number of company tenants
            - tenants_with_dependents: Number of tenants with dependents
            - total_dependents: Total number of dependents
            - marital_status_distribution: Distribution of marital statuses

        Example:
            >>> stats = DashboardService.get_tenant_statistics()
            >>> print(f"Total tenants: {stats['total_tenants']}")
            >>> print(f"Individuals: {stats['individual_tenants']}, "
            ...       f"Companies: {stats['company_tenants']}")
        """
        logger.info("Calculating tenant statistics")

        # Aggregate tenant counts
        tenant_stats = Tenant.objects.aggregate(
            total_tenants=Count("id"),
            individual_tenants=Count("id", filter=Q(is_company=False)),
            company_tenants=Count("id", filter=Q(is_company=True)),
        )

        # Count tenants with dependents
        tenants_with_dependents = Tenant.objects.filter(dependents__isnull=False).distinct().count()

        # Count total dependents
        from core.models import Dependent

        total_dependents = Dependent.objects.count()

        # Get marital status distribution using values().annotate() - single query
        marital_status_qs = Tenant.objects.filter(is_company=False).values("marital_status").annotate(count=Count("id"))
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
