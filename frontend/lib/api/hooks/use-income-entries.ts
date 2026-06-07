import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  incomeEntrySchema,
  type IncomeEntry,
  type IncomeEntryWrite,
  type IncomeEntryFilters,
} from '@/lib/schemas/finances/income-entry.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export function useIncomeEntries(filters?: IncomeEntryFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v !== undefined).map(([k, v]) => {
          // Send booleans as literal strings so Django filters correctly
          if (typeof v === 'boolean') return [k, v ? 'true' : 'false'];
          return [k, v];
        }),
      )
    : {};

  return useQuery({
    queryKey: queryKeys.finances.incomeEntries.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<IncomeEntry> | IncomeEntry[]>(
        '/finances/income-entries/',
        { params: { page_size: 10000, ...cleanFilters } },
      );
      const items = extractResults(data);
      return items.map((item) => incomeEntrySchema.parse(item));
    },
  });
}

export function useIncomeEntry(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.incomeEntries.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('IncomeEntry ID is required');
      const { data } = await apiClient.get<IncomeEntry>(`/finances/income-entries/${id}/`);
      return incomeEntrySchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateIncomeEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncomeEntryWrite) => {
      const { data } = await apiClient.post<IncomeEntry>('/finances/income-entries/', payload);
      return incomeEntrySchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.incomeEntries.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}

export function useUpdateIncomeEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: IncomeEntryWrite & { id: number }) => {
      const { id, ...body } = payload;
      const { data } = await apiClient.put<IncomeEntry>(`/finances/income-entries/${id}/`, body);
      return incomeEntrySchema.parse(data);
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.incomeEntries.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.finances.incomeEntries.detail(data.id),
        });
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}

export function useDeleteIncomeEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/finances/income-entries/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.incomeEntries.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}
