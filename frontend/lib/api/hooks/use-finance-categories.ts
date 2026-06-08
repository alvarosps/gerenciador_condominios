import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  type FinanceCategory,
  financeCategorySchema,
} from '@/lib/schemas/finances/category.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const ENDPOINT = '/finances/finance-categories/';

type FinanceCategoryWrite = Omit<
  FinanceCategory,
  'id' | 'condominium' | 'parent' | 'created_at' | 'updated_at'
>;

export function useFinanceCategories() {
  return useQuery({
    queryKey: queryKeys.finances.financeCategories.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<FinanceCategory> | FinanceCategory[]>(
        ENDPOINT,
        { params: { page_size: 10000 } },
      );
      return extractResults(data).map((category) => financeCategorySchema.parse(category));
    },
  });
}

export function useCreateFinanceCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: FinanceCategoryWrite) => {
      const response = await apiClient.post<FinanceCategory>(ENDPOINT, data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.financeCategories.all });
    },
  });
}

export function useUpdateFinanceCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<FinanceCategory> & { id: number }) => {
      const { condominium: _condominium, parent: _parent, ...updateData } = data;
      const response = await apiClient.put<FinanceCategory>(`${ENDPOINT}${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.financeCategories.all });
    },
  });
}

export function useDeleteFinanceCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${ENDPOINT}${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.financeCategories.all });
    },
  });
}
