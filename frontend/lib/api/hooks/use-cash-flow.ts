import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface CashFlowRentDetail {
  apartment_id: number;
  apartment_number: string;
  building_name: string;
  tenant_name: string;
  rental_value: number;
  is_paid: boolean;
  payment_date: string | null;
}

export interface CashFlowIncome {
  rent_income: number;
  rent_details: CashFlowRentDetail[];
  extra_income: number;
  extra_income_details: Record<string, unknown>[];
  total: number;
}

export interface CashFlowExpenses {
  owner_repayments: number;
  person_stipends: number;
  card_installments: number;
  loan_installments: number;
  utility_bills: number;
  debt_installments: number;
  property_tax: number;
  employee_salary: number;
  fixed_expenses: number;
  one_time_expenses: number;
  total: number;
  [key: string]: unknown;
}

export interface CashFlowMonth {
  year: number;
  month: number;
  income: CashFlowIncome;
  expenses: CashFlowExpenses;
  balance: number;
}

export interface CashFlowProjectionMonth {
  year: number;
  month: number;
  income_total: number;
  expenses_total: number;
  balance: number;
  cumulative_balance: number;
  is_projected: boolean;
}

export interface PersonSummaryReceivesDetail {
  description?: string;
  apartment_number?: string;
  building_name?: string;
  rental_value?: number;
  amount?: number;
  source: string;
}

export interface PersonSummaryCardDetail {
  description: string;
  card_name: string | null;
  installment: string;
  amount: number;
  due_date: string;
}

export interface PersonSummaryLoanDetail {
  description: string;
  installment: string;
  amount: number;
  due_date: string;
}

export interface PersonSummaryOffsetDetail {
  description: string;
  installment: string | null;
  amount: number;
  due_date: string;
}

export interface PersonSummaryPaymentDetail {
  amount: number;
  payment_date: string;
  notes: string;
}

export interface PersonSummary {
  person_id: number;
  person_name: string;
  receives: number;
  receives_details: PersonSummaryReceivesDetail[];
  card_total: number;
  card_details: PersonSummaryCardDetail[];
  loan_total: number;
  loan_details: PersonSummaryLoanDetail[];
  offset_total: number;
  offset_details: PersonSummaryOffsetDetail[];
  fixed_total: number;
  fixed_details: { description: string; amount: number }[];
  net_amount: number;
  total_paid: number;
  payment_details: PersonSummaryPaymentDetail[];
  pending_balance: number;
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
