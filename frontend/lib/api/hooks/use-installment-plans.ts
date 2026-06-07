import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  type Installment,
  type InstallmentPlan,
  installmentPlanSchema,
  installmentSchema,
} from '@/lib/schemas/finances/installment-plan.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const PLANS_ENDPOINT = '/finances/installment-plans/';
const INSTALLMENTS_ENDPOINT = '/finances/installments/';

export interface InstallmentPlanFilters {
  building_id?: number;
  category_id?: number;
  lifecycle_state?: string;
  embedded?: boolean;
}

export interface InstallmentFilters {
  plan_id?: number;
  due_date_from?: string;
  due_date_to?: string;
}

/** Params for the convert_deferred action (detail=false; operates on a deferred Bill). */
export interface ConvertDeferredParams {
  bill_id: number;
  installment_count: number;
  start_due_date: string;
  default_due_day: number;
  category_id?: number;
}

type InstallmentPlanWrite = Omit<
  InstallmentPlan,
  | 'id'
  | 'condominium'
  | 'category'
  | 'building'
  | 'linked_billing_account'
  | 'installments'
  | 'created_at'
  | 'updated_at'
>;

function cleanFilters(filters?: object): Record<string, unknown> {
  return filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};
}

export function useInstallmentPlans(filters?: InstallmentPlanFilters) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: queryKeys.finances.installmentPlans.list(params),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<InstallmentPlan> | InstallmentPlan[]>(
        PLANS_ENDPOINT,
        { params: { page_size: 10000, ...params } },
      );
      return extractResults(data).map((plan) => installmentPlanSchema.parse(plan));
    },
  });
}

export function useInstallmentPlan(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.installmentPlans.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Installment plan ID is required');
      const { data } = await apiClient.get<InstallmentPlan>(`${PLANS_ENDPOINT}${id}/`);
      return installmentPlanSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

function invalidatePlanCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installmentPlans.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installments.all });
}

export function useCreateInstallmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: InstallmentPlanWrite) => {
      const response = await apiClient.post<InstallmentPlan>(PLANS_ENDPOINT, data);
      return response.data;
    },
    onSuccess: () => invalidatePlanCaches(queryClient),
  });
}

export function useUpdateInstallmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<InstallmentPlan> & { id: number }) => {
      const {
        condominium: _condominium,
        category: _category,
        building: _building,
        linked_billing_account: _linked_billing_account,
        installments: _installments,
        ...updateData
      } = data;
      const response = await apiClient.patch<InstallmentPlan>(
        `${PLANS_ENDPOINT}${data.id}/`,
        updateData,
      );
      return response.data;
    },
    onSuccess: () => invalidatePlanCaches(queryClient),
  });
}

export function useDeleteInstallmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${PLANS_ENDPOINT}${id}/`);
    },
    onSuccess: () => invalidatePlanCaches(queryClient),
  });
}

export function useInstallments(filters?: InstallmentFilters) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: queryKeys.finances.installments.list(params),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Installment> | Installment[]>(
        INSTALLMENTS_ENDPOINT,
        { params: { page_size: 10000, ...params } },
      );
      return extractResults(data).map((installment) => installmentSchema.parse(installment));
    },
  });
}

/** PATCH the schedule (amount/due_date). Installments are never created/deleted in the FE (405). */
export function useUpdateInstallment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { id: number; amount?: number; due_date?: string }) => {
      const { id, ...updateData } = data;
      const response = await apiClient.patch<Installment>(
        `${INSTALLMENTS_ENDPOINT}${id}/`,
        updateData,
      );
      return installmentSchema.parse(response.data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installmentPlans.all });
    },
  });
}

/**
 * Convert a deferred Bill into a standalone InstallmentPlan (design §7/§8). The action is
 * detail=false on the backend and operates on the deferred Bill via `bill_id` in the body.
 * The FE never sums/validates the total — it returns the InstallmentPlan the server creates
 * (total preserved, §18). Invalidates plans + bills + billing-accounts for consistency.
 */
export function useConvertDeferred() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: ConvertDeferredParams) => {
      const { data } = await apiClient.post<InstallmentPlan>(
        `${PLANS_ENDPOINT}convert_deferred/`,
        params,
      );
      return installmentPlanSchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installmentPlans.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.billingAccounts.all });
    },
  });
}
