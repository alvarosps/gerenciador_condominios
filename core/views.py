# core/views.py
import logging
from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Apartment, Building, Furniture, Lease, Tenant
from .permissions import CanGenerateContract, CanModifyLease, IsAdminUser, IsTenantOrAdmin, ReadOnlyForNonAdmin
from .serializers import ApartmentSerializer, BuildingSerializer, FurnitureSerializer, LeaseSerializer, TenantSerializer
from .services import ContractService, DashboardService, FeeCalculatorService

logger = logging.getLogger(__name__)


class BuildingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Building model.

    Permissions:
    - Read: All authenticated users
    - Write: Admin only

    Buildings are reference data managed by administrators.
    """

    queryset = Building.objects.all().order_by("id")
    serializer_class = BuildingSerializer
    permission_classes = [ReadOnlyForNonAdmin]

    def get_queryset(self):
        """
        Optimize queryset with prefetch_related for apartments.

        Phase 5 Query Optimization:
        - prefetch_related: For apartments (reverse FK)
        """
        queryset = super().get_queryset()

        if self.action in ["list", "retrieve"]:
            queryset = queryset.prefetch_related("apartments")  # Reverse FK: Building -> Apartments

        return queryset


class FurnitureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Furniture model.

    Permissions:
    - Read: All authenticated users
    - Write: Admin only

    Furniture catalog is reference data managed by administrators.
    """

    queryset = Furniture.objects.all().order_by("id")
    serializer_class = FurnitureSerializer
    permission_classes = [ReadOnlyForNonAdmin]


class ApartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Apartment model.

    Permissions:
    - Read: All authenticated users
    - Write: Admin only

    Apartment data (units, rental values, etc.) is managed by administrators.
    """

    queryset = Apartment.objects.all().order_by("id")
    serializer_class = ApartmentSerializer
    permission_classes = [ReadOnlyForNonAdmin]

    def get_queryset(self):
        """
        Optimize queryset with select_related and prefetch_related.

        Phase 5 Query Optimization:
        - select_related: For building (ForeignKey)
        - prefetch_related: For furnitures (ManyToMany) and lease (reverse OneToOne)
        """
        queryset = super().get_queryset()

        if self.action in ["list", "retrieve"]:
            queryset = queryset.select_related("building").prefetch_related(  # ForeignKey: Apartment -> Building
                "furnitures"  # ManyToMany: Apartment -> Furnitures
            )

        return queryset


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tenant model.

    Permissions:
    - Read: All authenticated users
    - Write: Admin only

    Tenant personal data should be protected and only manageable by administrators.
    """

    queryset = Tenant.objects.all().order_by("id")
    serializer_class = TenantSerializer
    permission_classes = [ReadOnlyForNonAdmin]

    def get_queryset(self):
        """
        Optimize queryset with prefetch_related.

        Phase 5 Query Optimization:
        - prefetch_related: For dependents (reverse FK) and furnitures (ManyToMany)
        """
        queryset = super().get_queryset()

        if self.action in ["list", "retrieve"]:
            queryset = queryset.prefetch_related(
                "dependents",  # Reverse FK: Tenant -> Dependents
                "furnitures",  # ManyToMany: Tenant -> Furnitures
            )

        return queryset


class LeaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lease model.

    Permissions:
    - Read: Tenants (only their leases) and Admins (all leases)
    - Write: Admin only

    Lease terms are managed by administrators. Tenants can view their leases
    and perform specific actions like viewing late fees.
    """

    queryset = Lease.objects.all().order_by("id")
    serializer_class = LeaseSerializer
    permission_classes = [CanModifyLease]

    def get_queryset(self):
        """
        Optimize queryset with select_related and prefetch_related to eliminate N+1 queries.

        Phase 5 Query Optimization:
        - select_related: For ForeignKey and OneToOne (apartment, building, responsible_tenant)
        - prefetch_related: For ManyToMany (tenants, dependents) and reverse relations

        This reduces queries from ~301 to ~4 for the list endpoint.
        """
        queryset = super().get_queryset()

        if self.action == "list":
            # Optimize for list view: load all related data in minimal queries
            queryset = queryset.select_related(
                "apartment",  # OneToOne: Lease -> Apartment
                "apartment__building",  # ForeignKey: Apartment -> Building
                "responsible_tenant",  # ForeignKey: Lease -> Tenant (responsible)
            ).prefetch_related(
                "tenants",  # ManyToMany: Lease -> Tenants (all tenants)
                "tenants__dependents",  # Reverse FK: Tenant -> Dependents
                "tenants__furnitures",  # ManyToMany: Tenant -> Furnitures (tenant's own)
                "apartment__furnitures",  # ManyToMany: Apartment -> Furnitures (apartment's)
            )
        elif self.action == "retrieve":
            # Optimize for detail view: same as list but for single object
            queryset = queryset.select_related(
                "apartment", "apartment__building", "responsible_tenant"
            ).prefetch_related("tenants", "tenants__dependents", "tenants__furnitures", "apartment__furnitures")

        return queryset

    # Endpoint para gerar contrato em PDF
    @action(detail=True, methods=["post"], permission_classes=[CanGenerateContract])
    def generate_contract(self, request, pk=None):
        """
        Generate PDF contract for a lease.

        Permissions: Admin or responsible tenant

        Delegates all business logic to ContractService which handles:
        - Context preparation (dates, fees, furniture)
        - Template rendering
        - PDF generation
        - Lease status update
        """
        lease = self.get_object()

        try:
            # Delegate all business logic to ContractService
            pdf_path = ContractService.generate_contract(lease)

            return Response(
                {"message": "Contrato gerado com sucesso!", "pdf_path": pdf_path},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except FileNotFoundError as e:
            logger.error(f"Template not found during contract generation: {e}")
            return Response(
                {"error": "Template de contrato não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (DatabaseError, IntegrityError) as e:
            logger.error(f"Database error during contract generation: {e}")
            return Response(
                {"error": "Erro ao salvar dados do contrato"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception("Unexpected error during contract generation")
            return Response(
                {"error": "Erro interno ao gerar contrato"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Endpoint para cálculo de multa de atraso
    @action(detail=True, methods=["get"], permission_classes=[IsTenantOrAdmin])
    def calculate_late_fee(self, request, pk=None):
        """
        Calculate late payment fee for a lease.

        Permissions: Tenant (only their lease) or Admin

        Uses FeeCalculatorService for business logic.
        """
        lease = self.get_object()

        # Delegate to service layer
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=lease.rental_value, due_day=lease.due_day, current_date=date.today()
        )

        # Return appropriate response
        if result["is_late"]:
            return Response(
                {"late_days": result["late_days"], "late_fee": result["late_fee"]},
                status=status.HTTP_200_OK,
            )
        else:
            return Response({"message": result["message"]}, status=status.HTTP_200_OK)

    # Endpoint para alteração do dia de vencimento com cálculo da taxa
    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def change_due_date(self, request, pk=None):
        """
        Change the due date for rent payments.

        Permissions: Admin only (lease terms modification)

        Uses FeeCalculatorService to calculate the fee for changing due date.
        """
        lease = self.get_object()
        new_due_day = request.data.get("new_due_day")

        if not new_due_day:
            return Response({"error": "Campo new_due_day é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_due_day = int(new_due_day)

            # Delegate fee calculation to service layer
            fee_result = FeeCalculatorService.calculate_due_date_change_fee(
                rental_value=lease.rental_value,
                current_due_day=lease.due_day,
                new_due_day=new_due_day,
            )

            # Update the due date
            lease.due_day = new_due_day
            lease.save()

            return Response(
                {"message": "Dia de vencimento alterado.", "fee": fee_result["fee"]},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"error": f"Valor inválido para new_due_day: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (DatabaseError, IntegrityError) as e:
            logger.error(f"Database error during due date change: {e}")
            return Response(
                {"error": "Erro ao salvar alteração de vencimento"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception("Unexpected error during due date change")
            return Response(
                {"error": "Erro interno ao alterar vencimento"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for dashboard metrics and statistics.

    Phase 7: Advanced Features - Dashboard API Endpoints

    Provides read-only endpoints for business intelligence and reporting:
    - Financial summary (revenue, occupancy, fees)
    - Lease metrics (active, expired, expiring soon)
    - Building statistics (per-building occupancy and revenue)
    - Late payment summary (late fees, late leases)
    - Tenant statistics (demographics, dependents)

    All endpoints require authentication. Admin users have full access.

    Permissions:
    - Read: All authenticated users (limited data for tenants)
    - Admin gets complete data access
    """

    permission_classes = [IsAdminUser]  # Only admins can access dashboard

    @action(detail=False, methods=["get"])
    def financial_summary(self, request):
        """
        Get financial summary across all properties.

        GET /api/dashboard/financial_summary/

        Returns:
            {
                "total_revenue": "15000.00",
                "total_cleaning_fees": "2000.00",
                "total_tag_fees": "800.00",
                "total_income": "17800.00",
                "occupancy_rate": 75.0,
                "total_apartments": 20,
                "rented_apartments": 15,
                "vacant_apartments": 5,
                "revenue_per_apartment": "1000.00"
            }
        """
        summary = DashboardService.get_financial_summary()
        return Response(summary, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def lease_metrics(self, request):
        """
        Get lease statistics and metrics.

        GET /api/dashboard/lease_metrics/

        Returns:
            {
                "total_leases": 15,
                "active_leases": 12,
                "inactive_leases": 3,
                "contracts_generated": 10,
                "contracts_pending": 5,
                "expiring_soon": 2,
                "expired_leases": 3
            }
        """
        metrics = DashboardService.get_lease_metrics()
        return Response(metrics, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def building_statistics(self, request):
        """
        Get per-building statistics and occupancy.

        GET /api/dashboard/building_statistics/

        Returns:
            [
                {
                    "building_id": 1,
                    "building_number": 836,
                    "total_apartments": 10,
                    "rented_apartments": 8,
                    "vacant_apartments": 2,
                    "occupancy_rate": 80.0,
                    "total_revenue": "8000.00"
                },
                ...
            ]
        """
        statistics = DashboardService.get_building_statistics()
        return Response(statistics, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def late_payment_summary(self, request):
        """
        Get late payment statistics.

        GET /api/dashboard/late_payment_summary/

        Returns:
            {
                "total_late_leases": 5,
                "total_late_fees": "250.00",
                "average_late_days": 3.4,
                "late_leases": [
                    {
                        "lease_id": 1,
                        "apartment_number": 101,
                        "building_number": 836,
                        "tenant_name": "João Silva",
                        "rental_value": "1500.00",
                        "due_day": 10,
                        "late_days": 5,
                        "late_fee": "50.00"
                    },
                    ...
                ]
            }
        """
        summary = DashboardService.get_late_payment_summary()
        return Response(summary, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def tenant_statistics(self, request):
        """
        Get tenant statistics and demographics.

        GET /api/dashboard/tenant_statistics/

        Returns:
            {
                "total_tenants": 25,
                "individual_tenants": 20,
                "company_tenants": 5,
                "tenants_with_dependents": 8,
                "total_dependents": 12,
                "marital_status_distribution": {
                    "Casado": 10,
                    "Solteiro": 8,
                    "Divorciado": 2
                }
            }
        """
        statistics = DashboardService.get_tenant_statistics()
        return Response(statistics, status=status.HTTP_200_OK)
