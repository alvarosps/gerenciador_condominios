import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type Income, incomeSchema } from '@/lib/schemas/income.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export interface IncomeFilters {
  person_id?: number;
  building_id?: number;
  is_received?: boolean;
  is_recurring?: boolean;
}

export function useIncomes(filters?: IncomeFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: ['incomes', cleanFilters],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Income> | Income[]>('/incomes/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const incomes = extractResults(data);
      return incomes.map((income) => incomeSchema.parse(income));
    },
  });
}

export function useIncome(id: number | null) {
  return useQuery({
    queryKey: ['incomes', id],
    queryFn: async () => {
      if (!id) throw new Error('Income ID is required');
      const { data } = await apiClient.get<Income>(`/incomes/${id}/`);
      return incomeSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateIncome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Income, 'id' | 'person' | 'building' | 'category'>) => {
      const response = await apiClient.post<Income>('/incomes/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['incomes'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useUpdateIncome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Income> & { id: number }) => {
      if (!data.id) throw new Error('Income ID is required for update');
      const { person: _person, building: _building, category: _category, ...updateData } = data;
      const response = await apiClient.put<Income>(`/incomes/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['incomes'] });
      void queryClient.invalidateQueries({ queryKey: ['incomes', data.id] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useDeleteIncome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/incomes/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['incomes'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useMarkIncomeReceived() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await apiClient.post<Income>(`/incomes/${id}/mark_received/`);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['incomes'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}
