import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type RentPayment, rentPaymentSchema } from '@/lib/schemas/rent-payment.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface RentPaymentFilters {
  lease_id?: number;
  reference_month?: string;
}

export function useRentPayments(filters?: RentPaymentFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.rentPayments.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<RentPayment> | RentPayment[]>('/rent-payments/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const payments = extractResults(data);
      return payments.map((payment) => rentPaymentSchema.parse(payment));
    },
  });
}

export function useRentPayment(id: number | null) {
  return useQuery({
    queryKey: queryKeys.rentPayments.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('RentPayment ID is required');
      const { data } = await apiClient.get<RentPayment>(`/rent-payments/${id}/`);
      return rentPaymentSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateRentPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<RentPayment, 'id' | 'lease'>) => {
      const response = await apiClient.post<RentPayment>('/rent-payments/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rentPayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useUpdateRentPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<RentPayment> & { id: number }) => {
      if (!data.id) throw new Error('RentPayment ID is required for update');
      const { lease: _lease, ...updateData } = data;
      const response = await apiClient.put<RentPayment>(`/rent-payments/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rentPayments.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.rentPayments.detail(data.id) });
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useDeleteRentPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/rent-payments/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rentPayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}
