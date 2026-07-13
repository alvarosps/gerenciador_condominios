import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { parseList } from '../parse-list';
import { type CreditCard, creditCardSchema } from '@/lib/schemas/credit-card.schema';
import { queryKeys } from '@/lib/api/query-keys';

export function useCreditCards() {
  return useQuery({
    queryKey: queryKeys.creditCards.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>('/credit-cards/', {
        params: { page_size: 10000 },
      });
      return parseList(data, creditCardSchema).items;
    },
  });
}

export function useCreditCard(id: number | null) {
  return useQuery({
    queryKey: queryKeys.creditCards.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('CreditCard ID is required');
      const { data } = await apiClient.get<CreditCard>(`/credit-cards/${id}/`);
      return creditCardSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateCreditCard() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<CreditCard, 'id' | 'person'>) => {
      const response = await apiClient.post<CreditCard>('/credit-cards/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.creditCards.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.persons.all });
    },
  });
}

export function useUpdateCreditCard() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<CreditCard> & { id: number }) => {
      if (!data.id) throw new Error('CreditCard ID is required for update');
      const { person: _person, ...updateData } = data;
      const response = await apiClient.put<CreditCard>(`/credit-cards/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.creditCards.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.creditCards.detail(data.id) });
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.persons.all });
    },
  });
}

export function useDeleteCreditCard() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/credit-cards/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.creditCards.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.persons.all });
    },
  });
}
