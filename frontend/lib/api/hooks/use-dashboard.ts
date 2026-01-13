import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

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
  tenants_with_dependents: number;
  total_dependents: number;
  marital_status_distribution: MaritalStatusDistribution[];
}

/**
 * Hook to fetch financial summary
 * Returns revenue, average values, and occupancy rate
 */
export function useDashboardFinancialSummary() {
  return useQuery({
    queryKey: ['dashboard', 'financial_summary'],
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
    queryKey: ['dashboard', 'lease_metrics'],
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
    queryKey: ['dashboard', 'building_statistics'],
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
 * Returns summary and list of late payments
 */
export function useDashboardLatePayments() {
  return useQuery({
    queryKey: ['dashboard', 'late_payment_summary'],
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
 * Hook to fetch tenant statistics
 * Returns statistics about tenants (dependents, type, marital status)
 */
export function useDashboardTenantStatistics() {
  return useQuery({
    queryKey: ['dashboard', 'tenant_statistics'],
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
