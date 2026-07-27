import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { type Bill, type BillLineItem, billSchema } from '@/lib/schemas/finances/bill.schema';
import {
  type ParsedInvoice,
  parsedInvoiceSchema,
} from '@/lib/schemas/finances/invoice-parse.schema';
import type { FundedFrom, PaymentStatus } from '@/lib/schemas/finances/category.schema';
import { showFinanceMutationError } from '@/lib/utils/error-handler';
import { ROUTES } from '@/lib/utils/constants';

const ENDPOINT = '/finances/bills/';

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
  new_total?: string; // decimal string (contract S68) — adjusts the bill's total before allocating
}

interface PayBillResponse {
  id?: number;
  payment_status?: PaymentStatus;
  amount_remaining?: number;
}

export interface ApplyInvoiceRequest {
  bill_id: number;
  file: File;
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
  // Paying/editing a bill moves the cockpit board and the owning account's open_balance (S71).
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.monthBoard.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.billingAccounts.all });
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

/** Pure: wraps a PDF File in the single-field FormData both invoice endpoints expect. */
function pdfFormData(file: File): FormData {
  const formData = new FormData();
  formData.append('file', file);
  return formData;
}

/**
 * Parse a utility invoice PDF into a serialized DRAFT (S60). Multipart: send FormData with
 * `Content-Type: undefined` so the browser sets the boundary. Writes NOTHING — no cache
 * invalidation; the modal persists the draft later via create/update_with_lines (§5.2).
 */
export function useParseInvoice() {
  return useMutation({
    mutationFn: async (file: File): Promise<ParsedInvoice> => {
      const { data } = await apiClient.post<unknown>(
        `${ENDPOINT}parse_invoice/`,
        pdfFormData(file),
        {
          headers: { 'Content-Type': undefined },
        }
      );
      return parsedInvoiceSchema.parse(data); // single draft object — returned raw
    },
  });
}

/**
 * Apply a parsed invoice PDF directly to a TARGET bill (S69) — atomic write, replaces only the
 * lines without an `installment` FK and clears `amount_is_estimated`. Unlike `useParseInvoice`,
 * this endpoint WRITES: it invalidates the bill caches on success.
 */
export function useApplyInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ bill_id, file }: ApplyInvoiceRequest) => {
      const { data } = await apiClient.post<unknown>(
        `${ENDPOINT}${bill_id}/apply_invoice/`,
        pdfFormData(file),
        { headers: { 'Content-Type': undefined } } // browser sets the multipart boundary
      );
      return billSchema.parse(data); // response = the bill serialized with amounts (S69)
    },
    onSuccess: () => invalidateBillCaches(queryClient),
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

/**
 * Update a bill's HEADER fields via PATCH — routes to `BillService.update_header` (partial_update,
 * S65 contract). Money NEVER travels here: it lives in `BillLineItem`, written only through
 * `useCreateBillWithLines`/`useUpdateBillWithLines`. Callers pass only the header fields they mean
 * to change (e.g. `{ id, due_date }` for the inline due-date popover, S75).
 */
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
      const response = await apiClient.patch<Bill>(`${ENDPOINT}${data.id}/`, updateData);
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

/**
 * Generate the month's recurring bills. Both call sites (the always-available header action and
 * the "faltantes" banner shortcut, S74) share this single mutation instance's success/error
 * handling — mirrors `useAdvanceMonth`/`useRollbackMonth` (use-month-advance.ts), which also bake
 * the PT toast into the hook instead of duplicating it at each call site.
 */
export function useGenerateMonthBills() {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: async (params: { year: number; month: number }) => {
      const { data } = await apiClient.post<{ created: number; bills: Bill[] }>(
        `${ENDPOINT}generate_month/`,
        params
      );
      return data;
    },
    onSuccess: (result) => {
      invalidateBillCaches(queryClient);
      toast.success(`${String(result.created)} conta(s) gerada(s)`);
    },
    onError: (error) => {
      showFinanceMutationError(error, 'Erro ao gerar contas do mês', () =>
        router.push(ROUTES.FINANCES_MONTH_CLOSE)
      );
    },
  });
}

/**
 * Pay a bill (partial/total, optionally adjusting its total via `new_total`). NO optimistic
 * update on any path (design §8 — never simulate a money mutation client-side): the payment
 * status only changes once the server responds and the bill caches are invalidated/refetched.
 */
export function usePayBill() {
  const queryClient = useQueryClient();
  return useMutation<PayBillResponse, Error, PayBillRequest>({
    mutationFn: async (request) => {
      const { data } = await apiClient.post<PayBillResponse>(`${ENDPOINT}${request.bill_id}/pay/`, {
        payment_date: request.payment_date,
        ...(request.amount !== undefined ? { amount: request.amount } : {}),
        funded_from: request.funded_from ?? 'caixa',
        ...(request.new_total !== undefined ? { new_total: request.new_total } : {}),
      });
      return data;
    },
    onSuccess: (_data, request) => {
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
