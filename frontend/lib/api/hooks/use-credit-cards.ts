import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type CreditCard, creditCardSchema } from '@/lib/schemas/credit-card.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export function useCreditCards() {
  return useQuery({
    queryKey: ['credit-cards'],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<CreditCard> | CreditCard[]>('/credit-cards/', {
        params: { page_size: 10000 },
      });
      const cards = extractResults(data);
      return cards.map((card) => creditCardSchema.parse(card));
    },
  });
}

export function useCreditCard(id: number | null) {
  return useQuery({
    queryKey: ['credit-cards', id],
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
      void queryClient.invalidateQueries({ queryKey: ['credit-cards'] });
      void queryClient.invalidateQueries({ queryKey: ['persons'] });
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
      void queryClient.invalidateQueries({ queryKey: ['credit-cards'] });
      void queryClient.invalidateQueries({ queryKey: ['credit-cards', data.id] });
      void queryClient.invalidateQueries({ queryKey: ['persons'] });
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
      void queryClient.invalidateQueries({ queryKey: ['credit-cards'] });
      void queryClient.invalidateQueries({ queryKey: ['persons'] });
    },
  });
}
