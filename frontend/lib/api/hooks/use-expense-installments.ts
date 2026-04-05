import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type ExpenseInstallment, expenseInstallmentSchema } from '@/lib/schemas/expense-installment.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface ExpenseInstallmentFilters {
  expense_id?: number;
  is_paid?: boolean;
}

export function useExpenseInstallments(filters?: ExpenseInstallmentFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.expenseInstallments.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<ExpenseInstallment> | ExpenseInstallment[]>(
        '/expense-installments/',
        { params: { page_size: 10000, ...cleanFilters } },
      );
      const installments = extractResults(data);
      return installments.map((inst) => expenseInstallmentSchema.parse(inst));
    },
  });
}

export function useMarkInstallmentPaid() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await apiClient.post<ExpenseInstallment>(`/expense-installments/${id}/mark_paid/`);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseInstallments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenses.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useBulkMarkInstallmentsPaid() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ids: number[]) => {
      const { data } = await apiClient.post<{ message: string; updated_count: number }>(
        '/expense-installments/bulk_mark_paid/',
        { ids },
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseInstallments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenses.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}
