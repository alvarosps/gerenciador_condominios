import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface CashFlowMonth {
  year: number;
  month: number;
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  opening_balance: number;
  closing_balance: number;
  income_items: unknown[];
  expense_items: unknown[];
}

export interface CashFlowProjectionMonth {
  year: number;
  month: number;
  projected_income: number;
  projected_expenses: number;
  projected_balance: number;
}

export interface PersonSummary {
  person_id: number;
  person_name: string;
  year: number;
  month: number;
  total_income: number;
  total_expenses: number;
  net: number;
}

const STALE_TIME = 1000 * 60 * 5;
const REFETCH_INTERVAL = 1000 * 60 * 5;

export function useMonthlyCashFlow(year: number, month: number) {
  return useQuery({
    queryKey: ['cash-flow', 'monthly', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<CashFlowMonth>('/cash-flow/monthly/', {
        params: { year, month },
      });
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useCashFlowProjection(months?: number) {
  return useQuery({
    queryKey: ['cash-flow', 'projection', months],
    queryFn: async () => {
      const { data } = await apiClient.get<CashFlowProjectionMonth[]>('/cash-flow/projection/', {
        params: months ? { months } : undefined,
      });
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function usePersonSummary(personId: number, year: number, month: number) {
  return useQuery({
    queryKey: ['cash-flow', 'person_summary', personId, year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<PersonSummary>('/cash-flow/person_summary/', {
        params: { person_id: personId, year, month },
      });
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
    enabled: Boolean(personId),
  });
}
