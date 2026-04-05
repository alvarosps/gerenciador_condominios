import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import {
  type RentAdjustment,
  rentAdjustmentSchema,
  type RentAdjustmentAlert,
  rentAdjustmentAlertSchema,
} from '@/lib/schemas/rent-adjustment.schema';
import { queryKeys } from '@/lib/api/query-keys';

export function useApplyRentAdjustment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      leaseId: number;
      percentage: number;
      update_apartment_prices: boolean;
      renewal_date?: string;
    }) => {
      const { data } = await apiClient.post<
        RentAdjustment & { warning: { type: string; last_date: string } | null }
      >(`/leases/${String(params.leaseId)}/adjust_rent/`, {
        percentage: params.percentage,
        update_apartment_prices: params.update_apartment_prices,
        renewal_date: params.renewal_date,
      });
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.rentAdjustmentAlerts.all });
    },
  });
}

export function useRentAdjustments(leaseId: number | null) {
  return useQuery({
    queryKey: queryKeys.rentAdjustments.byLease(leaseId),
    queryFn: async () => {
      if (!leaseId) throw new Error('Lease ID is required');
      const { data } = await apiClient.get<RentAdjustment[]>(
        `/leases/${String(leaseId)}/rent_adjustments/`,
      );
      return data.map((item) => rentAdjustmentSchema.parse(item));
    },
    enabled: Boolean(leaseId),
  });
}

interface RentAdjustmentAlertsResponse {
  alerts: RentAdjustmentAlert[];
  ipca_latest_month: string | null;
  fallback_percentage: string;
}

export function useRentAdjustmentAlerts() {
  return useQuery({
    queryKey: queryKeys.rentAdjustmentAlerts.all,
    queryFn: async () => {
      const { data } = await apiClient.get<RentAdjustmentAlertsResponse>(
        '/dashboard/rent_adjustment_alerts/',
      );
      return {
        alerts: data.alerts.map((alert) => rentAdjustmentAlertSchema.parse(alert)),
        ipcaLatestMonth: data.ipca_latest_month,
        fallbackPercentage: Number(data.fallback_percentage),
      };
    },
  });
}
