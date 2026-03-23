import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface DailyEntry {
  type: string;
  id?: number;
  description: string;
  amount: number;
  expected: boolean;
  paid: boolean;
  payment_date?: string;
}

export interface DailyExit {
  type: string;
  id: number;
  description: string;
  amount: number;
  due: boolean;
  paid: boolean;
  person?: string;
  card?: string;
  building?: string;
  payment_date?: string;
}

export interface DailyBreakdownDay {
  date: string;
  day_of_week: string;
  entries: DailyEntry[];
  exits: DailyExit[];
  total_entries: number;
  total_exits: number;
  day_balance: number;
  cumulative_balance: number;
}

export interface DailySummary {
  total_expected_income: number;
  total_received_income: number;
  total_expected_expenses: number;
  total_paid_expenses: number;
  overdue_count: number;
  overdue_total: number;
  upcoming_7_days_count: number;
  upcoming_7_days_total: number;
  current_balance: number;
  projected_balance: number;
}

export interface MarkPaidRequest {
  item_type: 'installment' | 'expense' | 'income';
  item_id: number;
  payment_date: string;
}

const STALE_TIME = 1000 * 60 * 5;

export function useDailyBreakdown(year: number, month: number) {
  return useQuery({
    queryKey: ['daily-control', 'breakdown', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<DailyBreakdownDay[]>('/daily-control/breakdown/', {
        params: { year, month },
      });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useDailySummary(year: number, month: number) {
  return useQuery({
    queryKey: ['daily-control', 'summary', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<DailySummary>('/daily-control/summary/', {
        params: { year, month },
      });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

export function useMarkItemPaid() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: MarkPaidRequest) => {
      const { data } = await apiClient.post<{ success: boolean }>('/daily-control/mark_paid/', request);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['daily-control'] });
      void queryClient.invalidateQueries({ queryKey: ['expenses'] });
      void queryClient.invalidateQueries({ queryKey: ['financial-dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}
