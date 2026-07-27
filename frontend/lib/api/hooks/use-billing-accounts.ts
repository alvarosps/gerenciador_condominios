import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { parseList } from '../parse-list';
import { invalidateFinanceMoneyCaches } from './use-bills';
import {
  type BillingAccount,
  billingAccountSchema,
} from '@/lib/schemas/finances/billing-account.schema';
import { installmentPlanSchema } from '@/lib/schemas/finances/installment-plan.schema';

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
      const { data } = await apiClient.get<unknown>(ENDPOINT, {
        params: { page_size: 10000, ...cleanFilters },
      });
      return parseList(data, billingAccountSchema).items;
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
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.monthBoard.all });
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

export interface ConsolidateDebtRequest {
  account_id: number;
  bill_ids: number[];
  embedded: boolean;
  installment_count: number;
  start_due_date: string; // YYYY-MM-DD
  default_due_day: number;
}

/**
 * Consolidate the account's open bills into a single installment plan (S70) — cancels the
 * source bills in the same backend transaction. Both sides need a refetch on success.
 */
export function useConsolidateDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ account_id, ...body }: ConsolidateDebtRequest) => {
      const { data } = await apiClient.post<unknown>(
        `${ENDPOINT}${account_id}/consolidate_debt/`,
        body
      );
      return installmentPlanSchema.parse(data); // 201 with the plan serialized (S70)
    },
    onSuccess: () => {
      invalidateBillingAccountCaches(queryClient);
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installmentPlans.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
      invalidateFinanceMoneyCaches(queryClient);
    },
  });
}
