import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import type { CombinedCalendar } from './use-combined-calendar';
import { type Bill, type BillLineItem, billSchema } from '@/lib/schemas/finances/bill.schema';
import type { FundedFrom, PaymentStatus } from '@/lib/schemas/finances/category.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const ENDPOINT = '/finances/bills/';

export interface BillFilters {
  building_id?: number;
  category_id?: number;
  competence_month?: string;
  lifecycle_state?: string;
  behavior?: string;
  payment_status?: string;
  is_overdue?: boolean;
}

export interface BillLineInput {
  description: string;
  amount: number;
  is_offset?: boolean;
  category_id?: number;
}

export interface CreateBillWithLines {
  bill: Record<string, unknown>;
  line_items: BillLineInput[];
}

export interface PayBillRequest {
  bill_id: number;
  payment_date: string;
  amount?: number;
  funded_from?: FundedFrom;
}

interface PayBillResponse {
  id?: number;
  payment_status?: PaymentStatus;
  amount_remaining?: number;
}

interface PayBillContext {
  previousBills: [readonly unknown[], Bill[] | Bill | undefined][];
  previousCalendar: [readonly unknown[], CombinedCalendar | undefined][];
}

export function useBills(filters?: BillFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};
  return useQuery({
    queryKey: queryKeys.finances.bills.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Bill> | Bill[]>(ENDPOINT, {
        params: { page_size: 10000, ...cleanFilters },
      });
      return extractResults(data).map((bill) => billSchema.parse(bill));
    },
  });
}

export function useBill(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.bills.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Bill ID is required');
      const { data } = await apiClient.get<Bill>(`${ENDPOINT}${id}/`);
      return billSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

function invalidateBillCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.combinedCalendar.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overdueBills.all });
}

export function useCreateBillWithLines() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateBillWithLines) => {
      const { data } = await apiClient.post<Bill>(`${ENDPOINT}create_with_lines/`, payload);
      return data;
    },
    onSuccess: () => invalidateBillCaches(queryClient),
  });
}

export function useUpdateBill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Bill> & { id: number }) => {
      const {
        condominium: _condominium,
        building: _building,
        category: _category,
        billing_account: _billing_account,
        line_items: _line_items,
        ...updateData
      } = data;
      const response = await apiClient.put<Bill>(`${ENDPOINT}${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => invalidateBillCaches(queryClient),
  });
}

export function useDeleteBill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${ENDPOINT}${id}/`);
    },
    onSuccess: () => invalidateBillCaches(queryClient),
  });
}

export function useGenerateMonthBills() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { year: number; month: number }) => {
      const { data } = await apiClient.post<{ created: number; bills: Bill[] }>(
        `${ENDPOINT}generate_month/`,
        params,
      );
      return data;
    },
    onSuccess: () => invalidateBillCaches(queryClient),
  });
}

/** Pure, immutable: flip a single Bill to fully paid (conservative optimistic update). */
function flipBillPaid(bill: Bill, billId: number): Bill {
  return bill.id === billId ? { ...bill, payment_status: 'paid', amount_remaining: 0 } : bill;
}

function markBillPaid(data: Bill[] | Bill | undefined, billId: number): Bill[] | Bill | undefined {
  if (!data) return data;
  if (Array.isArray(data)) return data.map((bill) => flipBillPaid(bill, billId));
  return flipBillPaid(data, billId);
}

function markBillPaidInCalendar(calendar: CombinedCalendar, billId: number): CombinedCalendar {
  return {
    ...calendar,
    days: calendar.days.map((day) => ({
      ...day,
      bill_exits: day.bill_exits.map((exit) =>
        exit.bill_id === billId
          ? { ...exit, payment_status: 'paid', amount_remaining: '0.00', is_overdue: false }
          : exit,
      ),
    })),
  };
}

/**
 * Pay a bill (partial/total) with a conservative optimistic update: only a full payment
 * (amount omitted) is reflected optimistically as 'paid'; partial payments wait for the
 * server (onSettled) to reconcile, since simulating partial arithmetic client-side is fragile.
 */
export function usePayBill() {
  const queryClient = useQueryClient();
  return useMutation<PayBillResponse, Error, PayBillRequest, PayBillContext>({
    mutationFn: async (request) => {
      const { data } = await apiClient.post<PayBillResponse>(`${ENDPOINT}${request.bill_id}/pay/`, {
        payment_date: request.payment_date,
        ...(request.amount !== undefined ? { amount: request.amount } : {}),
        funded_from: request.funded_from ?? 'caixa',
      });
      return data;
    },
    onMutate: async (request) => {
      if (request.amount !== undefined) {
        return { previousBills: [], previousCalendar: [] };
      }
      await queryClient.cancelQueries({ queryKey: queryKeys.finances.bills.all });
      await queryClient.cancelQueries({ queryKey: queryKeys.finances.combinedCalendar.all });

      const previousBills = queryClient.getQueriesData<Bill[] | Bill>({
        queryKey: queryKeys.finances.bills.all,
      });
      for (const [key, data] of previousBills) {
        if (data) {
          queryClient.setQueryData(key, markBillPaid(data, request.bill_id));
        }
      }
      const previousCalendar = queryClient.getQueriesData<CombinedCalendar>({
        queryKey: queryKeys.finances.combinedCalendar.all,
      });
      for (const [key, data] of previousCalendar) {
        if (data) {
          queryClient.setQueryData(key, markBillPaidInCalendar(data, request.bill_id));
        }
      }
      return { previousBills, previousCalendar };
    },
    onError: (_error, _request, context) => {
      context?.previousBills.forEach(([key, data]) => queryClient.setQueryData(key, data));
      context?.previousCalendar.forEach(([key, data]) => queryClient.setQueryData(key, data));
    },
    onSettled: () => invalidateBillCaches(queryClient),
  });
}

function useBillLifecycleAction(action: 'suspend' | 'defer' | 'cancel' | 'reactivate') {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (billId: number) => {
      const { data } = await apiClient.post<Bill>(`${ENDPOINT}${billId}/${action}/`);
      return data;
    },
    onSuccess: () => invalidateBillCaches(queryClient),
  });
}

export const useSuspendBill = () => useBillLifecycleAction('suspend');
export const useDeferBill = () => useBillLifecycleAction('defer');
export const useCancelBill = () => useBillLifecycleAction('cancel');
export const useReactivateBill = () => useBillLifecycleAction('reactivate');

export type { Bill, BillLineItem };
