import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type PersonPayment, personPaymentSchema } from '@/lib/schemas/person-payment.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface PersonPaymentFilters {
  person_id?: number;
  reference_month?: string;
  month_from?: string;
  month_to?: string;
}

export function usePersonPayments(filters?: PersonPaymentFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.personPayments.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<PersonPayment> | PersonPayment[]>('/person-payments/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const payments = extractResults(data);
      return payments.map((payment) => personPaymentSchema.parse(payment));
    },
  });
}

export function useCreatePersonPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<PersonPayment, 'id' | 'person'>) => {
      const response = await apiClient.post<PersonPayment>('/person-payments/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personPayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useUpdatePersonPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<PersonPayment> & { id: number }) => {
      const { person: _person, ...updateData } = data;
      const response = await apiClient.put<PersonPayment>(`/person-payments/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personPayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useDeletePersonPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/person-payments/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personPayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}
