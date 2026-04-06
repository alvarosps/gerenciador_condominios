import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type PersonIncome, personIncomeSchema } from '@/lib/schemas/person-income.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface PersonIncomeFilters {
  person_id?: number;
  income_type?: string;
  is_active?: boolean;
  apartment_id?: number;
}

export function usePersonIncomes(filters?: PersonIncomeFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.personIncomes.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<PersonIncome> | PersonIncome[]>('/person-incomes/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const incomes = extractResults(data);
      return incomes.map((income) => personIncomeSchema.parse(income));
    },
  });
}

export function useCreatePersonIncome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<PersonIncome, 'id' | 'person' | 'apartment' | 'current_value'>) => {
      const response = await apiClient.post<PersonIncome>('/person-incomes/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personIncomes.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useUpdatePersonIncome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<PersonIncome> & { id: number }) => {
      const { person: _person, apartment: _apartment, current_value: _cv, ...updateData } = data;
      const response = await apiClient.put<PersonIncome>(`/person-incomes/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personIncomes.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useDeletePersonIncome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/person-incomes/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personIncomes.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}
