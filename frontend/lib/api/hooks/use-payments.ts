import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { type Payment, paymentSchema } from '@/lib/schemas/finances/payment.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const ENDPOINT = '/finances/payments/';

export interface PaymentFilters {
  funded_from?: string;
  date_from?: string;
  date_to?: string;
}

type PaymentWrite = Omit<
  Payment,
  'id' | 'condominium' | 'allocations' | 'created_at' | 'updated_at'
>;

export function usePayments(filters?: PaymentFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};
  return useQuery({
    queryKey: queryKeys.finances.payments.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Payment> | Payment[]>(ENDPOINT, {
        params: { page_size: 10000, ...cleanFilters },
      });
      return extractResults(data).map((payment) => paymentSchema.parse(payment));
    },
  });
}

export function usePayment(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.payments.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Payment ID is required');
      const { data } = await apiClient.get<Payment>(`${ENDPOINT}${id}/`);
      return paymentSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

function invalidatePaymentCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.payments.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.combinedCalendar.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overdueBills.all });
}

export function useCreatePayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PaymentWrite) => {
      const response = await apiClient.post<Payment>(ENDPOINT, data);
      return response.data;
    },
    onSuccess: () => invalidatePaymentCaches(queryClient),
  });
}

export function useUpdatePayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Payment> & { id: number }) => {
      const { condominium: _condominium, allocations: _allocations, ...updateData } = data;
      const response = await apiClient.put<Payment>(`${ENDPOINT}${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => invalidatePaymentCaches(queryClient),
  });
}

export function useDeletePayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${ENDPOINT}${id}/`);
    },
    onSuccess: () => invalidatePaymentCaches(queryClient),
  });
}
