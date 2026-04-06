import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

// Dashboard API Response Types - matching backend DashboardService

interface FinancialSummary {
  total_revenue: string;
  total_cleaning_fees: string;
  total_tag_fees: string;
  total_income: string;
  occupancy_rate: number;
  total_apartments: number;
  rented_apartments: number;
  vacant_apartments: number;
  revenue_per_apartment: string;
}

interface LeaseMetrics {
  total_leases: number;
  active_leases: number;
  inactive_leases: number;
  contracts_generated: number;
  contracts_pending: number;
  expiring_soon: number;
  expired_leases: number;
  avg_validity_months: number;
}

interface BuildingStatistic {
  building_id: number;
  building_number: string;
  total_apartments: number;
  rented_apartments: number;
  vacant_apartments: number;
  occupancy_rate: number;
  total_revenue: string;
}

interface LateLeaseInfo {
  lease_id: number;
  apartment_number: number;
  building_number: string;
  tenant_name: string;
  rental_value: string;
  due_day: number;
  late_days: number;
  late_fee: string;
  last_payment_date: string | null;
}

interface LatePaymentSummary {
  total_late_leases: number;
  total_late_fees: string;
  average_late_days: number;
  late_leases: LateLeaseInfo[];
}

interface MaritalStatusDistribution {
  marital_status: string;
  count: number;
}

interface TenantStatistics {
  total_tenants: number;
  individual_tenants: number;
  company_tenants: number;
  person_tenants: number;
  tenants_with_dependents: number;
  tenants_with_furniture: number;
  total_dependents: number;
  avg_dependents: number;
  marital_status_distribution: MaritalStatusDistribution[];
}

/**
 * Hook to fetch financial summary
 * Returns revenue, average values, and occupancy rate
 */
export function useDashboardFinancialSummary() {
  return useQuery({
    queryKey: queryKeys.dashboard.financialSummary(),
    queryFn: async () => {
      const { data } = await apiClient.get<FinancialSummary>(
        '/dashboard/financial_summary/'
      );
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes (backend caches this)
    refetchInterval: 1000 * 60 * 5, // Auto-refetch every 5 minutes
  });
}

/**
 * Hook to fetch lease metrics
 * Returns counts of leases by status
 */
export function useDashboardLeaseMetrics() {
  return useQuery({
    queryKey: queryKeys.dashboard.leaseMetrics(),
    queryFn: async () => {
      const { data } = await apiClient.get<LeaseMetrics>('/dashboard/lease_metrics/');
      return data;
    },
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  });
}

/**
 * Hook to fetch building statistics
 * Returns statistics for each building
 */
export function useDashboardBuildingStatistics() {
  return useQuery({
    queryKey: queryKeys.dashboard.buildingStatistics(),
    queryFn: async () => {
      const { data } = await apiClient.get<BuildingStatistic[]>(
        '/dashboard/building_statistics/'
      );
      return data;
    },
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  });
}

/**
 * Hook to fetch late payment summary
 * Returns list of late payment records
 */
export function useDashboardLatePayments() {
  return useQuery({
    queryKey: queryKeys.dashboard.latePaymentSummary(),
    queryFn: async () => {
      const { data } = await apiClient.get<LatePaymentSummary>(
        '/dashboard/late_payment_summary/'
      );
      return data;
    },
    refetchInterval: 1000 * 60 * 5, // Refetch every 5 minutes for real-time alerts
  });
}

/**
 * Hook to mark rent as paid for a lease in the current month
 */
export function useMarkRentPaid() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leaseId: number) => {
      const { data } = await apiClient.post<{ message: string }>(
        '/dashboard/mark_rent_paid/',
        { lease_id: leaseId }
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.latePaymentSummary() });
    },
  });
}

/**
 * Hook to fetch tenant statistics
 * Returns statistics about tenants (dependents, type, marital status)
 */
export function useDashboardTenantStatistics() {
  return useQuery({
    queryKey: queryKeys.dashboard.tenantStatistics(),
    queryFn: async () => {
      const { data } = await apiClient.get<TenantStatistics>(
        '/dashboard/tenant_statistics/'
      );
      return data;
    },
    staleTime: 1000 * 60 * 10, // 10 minutes (less frequently updated)
    refetchInterval: 1000 * 60 * 10,
  });
}

// Export types for use in components
export type {
  FinancialSummary,
  LeaseMetrics,
  BuildingStatistic,
  LateLeaseInfo,
  LatePaymentSummary,
  TenantStatistics,
  MaritalStatusDistribution,
};
