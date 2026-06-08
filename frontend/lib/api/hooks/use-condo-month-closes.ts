import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  condoMonthCloseSchema,
  type CondoMonthClose,
  type CondoMonthCloseFilters,
} from '@/lib/schemas/finances/condo-month-close.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export function useCondoMonthCloses(filters?: CondoMonthCloseFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.finances.condoMonthCloses.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<
        PaginatedResponse<CondoMonthClose> | CondoMonthClose[]
      >('/finances/condo-month-closes/', { params: { page_size: 10000, ...cleanFilters } });
      const items = extractResults(data);
      return items.map((item) => condoMonthCloseSchema.parse(item));
    },
  });
}

export function useCondoMonthClose(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.condoMonthCloses.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('CondoMonthClose ID is required');
      const { data } = await apiClient.get<CondoMonthClose>(`/finances/condo-month-closes/${id}/`);
      return condoMonthCloseSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCloseMonth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { year: number; month: number }) => {
      const { data } = await apiClient.post<CondoMonthClose>(
        '/finances/condo-month-closes/close/',
        params,
      );
      return condoMonthCloseSchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.condoMonthCloses.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.monthlyBalance.all });
    },
  });
}

export function useReopenMonth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { year: number; month: number }) => {
      const { data } = await apiClient.post<CondoMonthClose>(
        '/finances/condo-month-closes/reopen/',
        params,
      );
      return condoMonthCloseSchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.condoMonthCloses.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.monthlyBalance.all });
    },
  });
}
