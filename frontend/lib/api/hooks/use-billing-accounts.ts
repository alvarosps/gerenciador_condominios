import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  type BillingAccount,
  billingAccountSchema,
} from '@/lib/schemas/finances/billing-account.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const ENDPOINT = '/finances/billing-accounts/';

export interface BillingAccountFilters {
  building_id?: number;
  category_id?: number;
  lifecycle_state?: string;
}

type BillingAccountWrite = Omit<
  BillingAccount,
  'id' | 'condominium' | 'building' | 'category' | 'created_at' | 'updated_at'
>;

export function useBillingAccounts(filters?: BillingAccountFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};
  return useQuery({
    queryKey: queryKeys.finances.billingAccounts.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<BillingAccount> | BillingAccount[]>(
        ENDPOINT,
        { params: { page_size: 10000, ...cleanFilters } },
      );
      return extractResults(data).map((account) => billingAccountSchema.parse(account));
    },
  });
}

export function useBillingAccount(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.billingAccounts.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Billing account ID is required');
      const { data } = await apiClient.get<BillingAccount>(`${ENDPOINT}${id}/`);
      return billingAccountSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

function invalidateBillingAccountCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.billingAccounts.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.combinedCalendar.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overdueBills.all });
}

export function useCreateBillingAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: BillingAccountWrite) => {
      const response = await apiClient.post<BillingAccount>(ENDPOINT, data);
      return response.data;
    },
    onSuccess: () => invalidateBillingAccountCaches(queryClient),
  });
}

export function useUpdateBillingAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<BillingAccount> & { id: number }) => {
      const {
        condominium: _condominium,
        building: _building,
        category: _category,
        ...updateData
      } = data;
      const response = await apiClient.put<BillingAccount>(`${ENDPOINT}${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => invalidateBillingAccountCaches(queryClient),
  });
}

export function useDeleteBillingAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${ENDPOINT}${id}/`);
    },
    onSuccess: () => invalidateBillingAccountCaches(queryClient),
  });
}
