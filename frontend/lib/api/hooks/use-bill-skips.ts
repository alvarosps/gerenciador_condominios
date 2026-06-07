import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { type BillSkip, billSkipSchema } from '@/lib/schemas/finances/bill-skip.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const ENDPOINT = '/finances/bill-skips/';

export interface BillSkipFilters {
  billing_account_id?: number;
  reference_month?: string;
}

type BillSkipWrite = Omit<BillSkip, 'id' | 'billing_account'>;

export function useBillSkips(filters?: BillSkipFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};
  return useQuery({
    queryKey: queryKeys.finances.billSkips.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<BillSkip> | BillSkip[]>(ENDPOINT, {
        params: { page_size: 10000, ...cleanFilters },
      });
      return extractResults(data).map((skip) => billSkipSchema.parse(skip));
    },
  });
}

function invalidateBillSkipCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.billSkips.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.combinedCalendar.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overdueBills.all });
}

export function useCreateBillSkip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: BillSkipWrite) => {
      const response = await apiClient.post<BillSkip>(ENDPOINT, data);
      return response.data;
    },
    onSuccess: () => invalidateBillSkipCaches(queryClient),
  });
}

export function useDeleteBillSkip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${ENDPOINT}${id}/`);
    },
    onSuccess: () => invalidateBillSkipCaches(queryClient),
  });
}
