import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { parseList } from '../parse-list';
import { type ExpenseCategory, expenseCategorySchema } from '@/lib/schemas/expense-category.schema';
import { queryKeys } from '@/lib/api/query-keys';

export function useExpenseCategories() {
  return useQuery({
    queryKey: queryKeys.expenseCategories.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>('/expense-categories/', {
        params: { page_size: 10000 },
      });
      return parseList(data, expenseCategorySchema).items;
    },
  });
}

export function useExpenseCategory(id: number | null) {
  return useQuery({
    queryKey: queryKeys.expenseCategories.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('ExpenseCategory ID is required');
      const { data } = await apiClient.get<ExpenseCategory>(`/expense-categories/${id}/`);
      return expenseCategorySchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateExpenseCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<ExpenseCategory, 'id' | 'parent' | 'subcategories'>) => {
      const response = await apiClient.post<ExpenseCategory>('/expense-categories/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories.all });
    },
  });
}

export function useUpdateExpenseCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<ExpenseCategory> & { id: number }) => {
      if (!data.id) throw new Error('ExpenseCategory ID is required for update');
      const { parent: _parent, subcategories: _subcategories, ...updateData } = data;
      const response = await apiClient.put<ExpenseCategory>(
        `/expense-categories/${data.id}/`,
        updateData
      );
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.expenseCategories.detail(data.id),
        });
      }
    },
  });
}

export function useDeleteExpenseCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/expense-categories/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories.all });
    },
  });
}
