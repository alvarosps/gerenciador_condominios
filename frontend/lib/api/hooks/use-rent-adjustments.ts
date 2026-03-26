import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import {
  type RentAdjustment,
  rentAdjustmentSchema,
  type RentAdjustmentAlert,
  rentAdjustmentAlertSchema,
} from '@/lib/schemas/rent-adjustment.schema';

export function useApplyRentAdjustment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      leaseId: number;
      percentage: number;
      update_apartment_prices: boolean;
    }) => {
      const { data } = await apiClient.post<
        RentAdjustment & { warning: { type: string; last_date: string } | null }
      >(`/leases/${String(params.leaseId)}/adjust_rent/`, {
        percentage: params.percentage,
        update_apartment_prices: params.update_apartment_prices,
      });
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['leases'] });
      void queryClient.invalidateQueries({ queryKey: ['apartments'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['rent-adjustment-alerts'] });
    },
  });
}

export function useRentAdjustments(leaseId: number | null) {
  return useQuery({
    queryKey: ['rent-adjustments', leaseId],
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

export function useRentAdjustmentAlerts() {
  return useQuery({
    queryKey: ['rent-adjustment-alerts'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ alerts: RentAdjustmentAlert[] }>(
        '/dashboard/rent_adjustment_alerts/',
      );
      return data.alerts.map((alert) => rentAdjustmentAlertSchema.parse(alert));
    },
  });
}
