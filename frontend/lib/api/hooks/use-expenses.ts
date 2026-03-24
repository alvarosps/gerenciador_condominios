import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type Expense, expenseSchema } from '@/lib/schemas/expense.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export interface ExpenseFilters {
  expense_type?: string;
  person_id?: number;
  credit_card_id?: number;
  building_id?: number;
  category_id?: number;
  is_paid?: boolean;
  is_recurring?: boolean;
  is_offset?: boolean;
}

export function useExpenses(filters?: ExpenseFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: ['expenses', cleanFilters],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Expense> | Expense[]>('/expenses/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const expenses = extractResults(data);
      return expenses.map((expense) => expenseSchema.parse(expense));
    },
  });
}

export function useExpense(id: number | null) {
  return useQuery({
    queryKey: ['expenses', id],
    queryFn: async () => {
      if (!id) throw new Error('Expense ID is required');
      const { data } = await apiClient.get<Expense>(`/expenses/${id}/`);
      return expenseSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      data: Omit<Expense, 'id' | 'person' | 'credit_card' | 'building' | 'category' | 'installments' | 'remaining_installments' | 'total_paid' | 'total_remaining'>,
    ) => {
      const response = await apiClient.post<Expense>('/expenses/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['expenses'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useUpdateExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Expense> & { id: number }) => {
      if (!data.id) throw new Error('Expense ID is required for update');
      const {
        person: _person,
        credit_card: _credit_card,
        building: _building,
        category: _category,
        installments: _installments,
        ...updateData
      } = data;
      const response = await apiClient.put<Expense>(`/expenses/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['expenses'] });
      void queryClient.invalidateQueries({ queryKey: ['expenses', data.id] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useDeleteExpense() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/expenses/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['expenses'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useMarkExpensePaid() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await apiClient.post<Expense>(`/expenses/${id}/mark_paid/`);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['expenses'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}

export function useGenerateInstallments() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (expenseId: number) => {
      const { data } = await apiClient.post<{ message: string; installments_created: number }>(
        `/expenses/${expenseId}/generate_installments/`,
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['expenses'] });
      void queryClient.invalidateQueries({ queryKey: ['expense-installments'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}
