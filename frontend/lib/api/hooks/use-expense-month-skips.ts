import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import {
  type ExpenseMonthSkip,
  expenseMonthSkipSchema,
} from '@/lib/schemas/expense-month-skip.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface ExpenseMonthSkipFilters {
  expense_id?: number;
  reference_month?: string;
}

export function useExpenseMonthSkips(filters?: ExpenseMonthSkipFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.expenseMonthSkips.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<
        PaginatedResponse<ExpenseMonthSkip> | ExpenseMonthSkip[]
      >('/expense-month-skips/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const skips = extractResults(data);
      return skips.map((skip) => expenseMonthSkipSchema.parse(skip));
    },
  });
}

export function useCreateExpenseMonthSkip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<ExpenseMonthSkip, 'id' | 'expense_description' | 'created_at' | 'updated_at'>) => {
      const response = await apiClient.post<ExpenseMonthSkip>('/expense-month-skips/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseMonthSkips.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dailyControl.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useDeleteExpenseMonthSkip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/expense-month-skips/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseMonthSkips.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dailyControl.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}
