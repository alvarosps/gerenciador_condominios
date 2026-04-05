import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '../client';
import { getErrorMessage } from '@/lib/utils/error-handler';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ValidationItem {
  lease_id?: number;
  apartment?: string;
  tenant?: string;
  rental_value?: number;
  installment_id?: number;
  description?: string;
  person?: string | null;
  amount?: number;
  due_date?: string;
  installment?: string;
  person_id?: number;
  name?: string;
  status?: string;
  type?: string;
  label?: string;
  person_name?: string;
  expected?: number;
  paid?: number;
  remaining?: number;
}

export interface MonthValidation {
  unpaid_rent: ValidationItem[];
  unpaid_installments: ValidationItem[];
  unpaid_employees: ValidationItem[];
  missing_utility_bills: ValidationItem[];
  unpaid_person_schedules: ValidationItem[];
  has_warnings: boolean;
  warning_count: number;
}

export interface MonthStatus {
  year: number;
  month: number;
  is_finalized: boolean;
  snapshot_id: number | null;
  validation: MonthValidation;
}

export interface MonthSnapshotSummary {
  id: number;
  reference_month: string;
  total_income: string;
  total_expenses: string;
  net_balance: string;
  cumulative_ending_balance: string;
  is_finalized: boolean;
  finalized_at: string | null;
  notes: string;
  created_at: string;
}

export interface MonthSnapshotDetail extends MonthSnapshotSummary {
  total_rent_income: string;
  total_extra_income: string;
  total_person_payments_received: string;
  total_card_installments: string;
  total_loan_installments: string;
  total_utility_bills: string;
  total_fixed_expenses: string;
  total_one_time_expenses: string;
  total_employee_salary: string;
  total_owner_repayments: string;
  total_person_stipends: string;
  total_debt_installments: string;
  total_property_tax: string;
  detailed_breakdown: Record<string, unknown>;
}

export interface NextMonthPreviewInstallment {
  description: string;
  person: string | null;
  amount: number;
  due_date: string;
  installment: string;
}

export interface NextMonthPreview {
  year: number;
  month: number;
  upcoming_installments_count: number;
  upcoming_installments_total: number;
  upcoming_installments: NextMonthPreviewInstallment[];
  expected_rent_total: number;
  active_leases_count: number;
  manual_reminders: string[];
  auto_created?: {
    employee_payments_created: number;
    payment_schedules_created: number;
  };
}

export interface AdvanceMonthRequest {
  year: number;
  month: number;
  force?: boolean;
  notes?: string;
}

export interface AdvanceMonthResponse {
  snapshot: MonthSnapshotDetail;
  warnings: string[];
  next_month_preview: NextMonthPreview;
}

export interface RollbackMonthRequest {
  year: number;
  month: number;
  confirm: boolean;
}

export interface RollbackMonthResponse {
  success: boolean;
  message: string;
  deleted_records: Record<string, number>;
}

const STALE_TIME = 1000 * 60 * 2;

// ── Queries ────────────────────────────────────────────────────────────────────

export function useMonthStatus(year: number, month: number) {
  return useQuery({
    queryKey: ['month-advance', 'status', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<MonthStatus>('/month-advance/get_status/', {
        params: { year, month },
      });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useMonthSnapshots(year?: number) {
  return useQuery({
    queryKey: ['month-advance', 'snapshots', year],
    queryFn: async () => {
      const { data } = await apiClient.get<MonthSnapshotSummary[]>('/month-advance/snapshots/', {
        params: year !== undefined ? { year } : undefined,
      });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useMonthSnapshotDetail(year: number, month: number) {
  return useQuery({
    queryKey: ['month-advance', 'snapshot-detail', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<MonthSnapshotDetail>(
        `/month-advance/snapshots/${String(year)}/${String(month)}/`,
      );
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useMonthPreview(year: number, month: number) {
  return useQuery({
    queryKey: ['month-advance', 'preview', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<NextMonthPreview>('/month-advance/preview/', {
        params: { year, month },
      });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

// ── Mutations ──────────────────────────────────────────────────────────────────

export function useAdvanceMonth() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: AdvanceMonthRequest) => {
      const { data } = await apiClient.post<AdvanceMonthResponse>(
        '/month-advance/advance/',
        request,
      );
      return data;
    },
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['month-advance'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
      const monthLabel = `${String(variables.month).padStart(2, '0')}/${String(variables.year)}`;
      toast.success(`Mês ${monthLabel} finalizado com sucesso!`);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao finalizar mês'));
    },
  });
}

export function useRollbackMonth() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: RollbackMonthRequest) => {
      const { data } = await apiClient.post<RollbackMonthResponse>(
        '/month-advance/rollback/',
        request,
      );
      return data;
    },
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['month-advance'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
      const monthLabel = `${String(variables.month).padStart(2, '0')}/${String(variables.year)}`;
      toast.success(`Mês ${monthLabel} revertido com sucesso.`);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao reverter mês'));
    },
  });
}
