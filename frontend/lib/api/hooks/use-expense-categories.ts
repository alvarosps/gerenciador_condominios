import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type ExpenseCategory, expenseCategorySchema } from '@/lib/schemas/expense-category.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export function useExpenseCategories() {
  return useQuery({
    queryKey: ['expense-categories'],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<ExpenseCategory> | ExpenseCategory[]>(
        '/expense-categories/',
        { params: { page_size: 10000 } },
      );
      const categories = extractResults(data);
      return categories.map((cat) => expenseCategorySchema.parse(cat));
    },
  });
}

export function useExpenseCategory(id: number | null) {
  return useQuery({
    queryKey: ['expense-categories', id],
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
      void queryClient.invalidateQueries({ queryKey: ['expense-categories'] });
    },
  });
}

export function useUpdateExpenseCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<ExpenseCategory> & { id: number }) => {
      if (!data.id) throw new Error('ExpenseCategory ID is required for update');
      const { parent: _parent, subcategories: _subcategories, ...updateData } = data;
      const response = await apiClient.put<ExpenseCategory>(`/expense-categories/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['expense-categories'] });
      void queryClient.invalidateQueries({ queryKey: ['expense-categories', data.id] });
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
      void queryClient.invalidateQueries({ queryKey: ['expense-categories'] });
    },
  });
}
