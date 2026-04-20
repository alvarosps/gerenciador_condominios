import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface TenantRentPayment {
  id: number;
  reference_month: string;
  amount_paid: string;
  payment_date: string;
  notes: string;
}

export interface TenantRentAdjustment {
  id: number;
  adjustment_date: string;
  percentage: string;
  previous_value: string;
  new_value: string;
}

export interface PixResponse {
  pix_payload: string;
  amount: string;
  recipient: string;
}

export const tenantPaymentKeys = {
  all: ['tenant', 'payments'] as const,
  adjustments: ['tenant', 'rent-adjustments'] as const,
} as const;

export function useTenantPayments() {
  return useQuery({
    queryKey: tenantPaymentKeys.all,
    queryFn: async () => {
      const { data } = await apiClient.get<{ results: TenantRentPayment[] }>('/tenant/payments/');
      return data.results;
    },
  });
}

export function useTenantRentAdjustments() {
  return useQuery({
    queryKey: tenantPaymentKeys.adjustments,
    queryFn: async () => {
      const { data } = await apiClient.get<TenantRentAdjustment[]>('/tenant/rent-adjustments/');
      return data;
    },
  });
}

export function useGeneratePix() {
  return useMutation({
    mutationFn: async (params?: { amount?: string; description?: string }) => {
      const { data } = await apiClient.post<PixResponse>('/tenant/payments/pix/', params ?? {});
      return data;
    },
  });
}

export function useUploadProof() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await apiClient.post<PaymentProof>('/tenant/payments/proof/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: tenantPaymentKeys.all });
    },
  });
}

export interface PaymentProof {
  id: number;
  reference_month: string;
  file: string;
  pix_code: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewed_at: string | null;
  rejection_reason: string;
  created_at: string;
}
