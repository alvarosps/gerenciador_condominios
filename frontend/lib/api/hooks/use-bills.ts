import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import type { CombinedCalendar } from './use-combined-calendar';
import { type Bill, type BillLineItem, billSchema } from '@/lib/schemas/finances/bill.schema';
import {
  type ParsedInvoice,
  parsedInvoiceSchema,
} from '@/lib/schemas/finances/invoice-parse.schema';
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
  installment_id?: number; // binds the line to the embedded Installment (§7.1)
}

/**
 * Readings-only statement payload (§3.2/§3.3): NO money fields. `kind` discriminates the
 * water/electricity shape on the front; the backend `_parse_statement` only coerces the reading
 * fields (the statement TYPE is decided by the billing account), so the extra `kind` is inert.
 */
export type BillStatementInput =
  | {
      kind: 'water';
      consumo_m3: number;
      leitura_anterior?: number | null;
      leitura_atual?: number | null;
      leitura_dias?: number | null;
      data_leitura?: string | null;
      agua_status?: string;
      esgoto_status?: string;
    }
  | {
      kind: 'electricity';
      consumo_kwh: number;
      energia_injetada_kwh?: number | null;
      leitura_anterior?: number | null;
      leitura_atual?: number | null;
      leitura_dias?: number | null;
      classe?: string;
      bandeira?: string;
    };

export interface CreateBillWithLines {
  bill: Record<string, unknown>;
  line_items: BillLineInput[];
  statement?: BillStatementInput | null;
}

export interface UpdateBillWithLines {
  bill_id: number;
  bill?: Record<string, unknown>;
  line_items: BillLineInput[];
  statement?: BillStatementInput | null;
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

/** Invalidate the condominium money dashboards (overview, balance, projection, …) that any
 *  bill/payment mutation affects. Shared by bill and payment hooks so they stay consistent. */
export function invalidateFinanceMoneyCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.monthlyBalance.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.byCategory.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.projection.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.ownerDistribution.all });
}

function invalidateBillCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.combinedCalendar.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overdueBills.all });
  invalidateFinanceMoneyCaches(queryClient);
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

/**
 * Parse a utility invoice PDF into a serialized DRAFT (S60). Multipart: send FormData with
 * `Content-Type: undefined` so the browser sets the boundary. Writes NOTHING — no cache
 * invalidation; the modal persists the draft later via create/update_with_lines (§5.2).
 */
export function useParseInvoice() {
  return useMutation({
    mutationFn: async (file: File): Promise<ParsedInvoice> => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await apiClient.post<unknown>(`${ENDPOINT}parse_invoice/`, formData, {
        headers: { 'Content-Type': undefined },
      });
      return parsedInvoiceSchema.parse(data); // single draft object — returned raw
    },
  });
}

/**
 * Replace a bill's lines + upsert its statement on the SAME Bill (UNPAID + OPEN only — the
 * backend rejects paid/closed with a 400 PT). Routes here when the parse draft carries an
 * `existing_bill_id` (idempotency, §5.5). Invalidates the bill caches on success.
 */
export function useUpdateBillWithLines() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateBillWithLines) => {
      const { data } = await apiClient.post<Bill>(
        `${ENDPOINT}${payload.bill_id}/update_with_lines/`,
        { bill: payload.bill, line_items: payload.line_items, statement: payload.statement ?? null }
      );
      return billSchema.parse(data);
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
        params
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
          : exit
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
    onSettled: (_data, _error, request) => {
      invalidateBillCaches(queryClient);
      if (request.funded_from === 'reserve') {
        void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserves.all });
        void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserveMovements.all });
      }
    },
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
