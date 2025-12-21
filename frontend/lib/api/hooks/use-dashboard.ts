import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

// Dashboard API Response Types
interface FinancialSummary {
  total_revenue: number;
  avg_rental_value: number;
  total_cleaning_fees: number;
  total_late_fees: number;
  occupancy_rate: number;
}

interface LeaseMetrics {
  total_leases: number;
  active_leases: number;
  expired_leases: number;
  expiring_soon: number;
  avg_validity_months: number;
}

interface BuildingStatistic {
  building_id: number;
  building_name: string;
  total_apartments: number;
  rented_apartments: number;
  occupancy_rate: number;
  total_revenue: number;
}

interface LatePayment {
  lease_id: number;
  tenant_name: string;
  building: string;
  apartment_number: number;
  days_late: number;
  late_fee: number;
}

interface TenantStatistics {
  total_tenants: number;
  tenants_with_dependents: number;
  avg_dependents: number;
  tenants_with_furniture: number;
  company_tenants: number;
  person_tenants: number;
}

/**
 * Hook to fetch financial summary
 * Returns revenue, average values, and occupancy rate
 */
export function useDashboardFinancialSummary() {
  return useQuery({
    queryKey: ['dashboard', 'financial-summary'],
    queryFn: async () => {
      const { data } = await apiClient.get<FinancialSummary>(
        '/dashboard/financial-summary/'
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
    queryKey: ['dashboard', 'lease-metrics'],
    queryFn: async () => {
      const { data } = await apiClient.get<LeaseMetrics>('/dashboard/lease-metrics/');
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
    queryKey: ['dashboard', 'building-statistics'],
    queryFn: async () => {
      const { data } = await apiClient.get<BuildingStatistic[]>(
        '/dashboard/building-statistics/'
      );
      return data;
    },
    staleTime: 1000 * 60 * 5,
    refetchInterval: 1000 * 60 * 5,
  });
}

/**
 * Hook to fetch late payments
 * Returns list of tenants with late payments
 */
export function useDashboardLatePayments() {
  return useQuery({
    queryKey: ['dashboard', 'late-payments'],
    queryFn: async () => {
      const { data } = await apiClient.get<LatePayment[]>('/dashboard/late-payments/');
      return data;
    },
    refetchInterval: 1000 * 60 * 5, // Refetch every 5 minutes for real-time alerts
  });
}

/**
 * Hook to fetch tenant statistics
 * Returns statistics about tenants (dependents, furniture, type)
 */
export function useDashboardTenantStatistics() {
  return useQuery({
    queryKey: ['dashboard', 'tenant-statistics'],
    queryFn: async () => {
      const { data } = await apiClient.get<TenantStatistics>(
        '/dashboard/tenant-statistics/'
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
  LatePayment,
  TenantStatistics,
};
