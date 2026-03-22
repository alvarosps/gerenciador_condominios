import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface FinancialOverview {
  current_month_balance: number;
  current_month_income: number;
  current_month_expenses: number;
  total_debt: number;
  total_monthly_obligations: number;
  total_monthly_income: number;
  months_until_break_even: number | null;
}

export interface DebtByPerson {
  person_id: number;
  person_name: string;
  card_debt: number;
  loan_debt: number;
  total_debt: number;
  monthly_card: number;
  monthly_loan: number;
  cards_count: number;
}

export interface DebtByType {
  expense_type: string;
  total: number;
}

export interface UpcomingInstallment {
  id: number;
  expense_description: string;
  expense_type: string;
  person_name: string | null;
  credit_card_nickname: string | null;
  installment_number: number;
  total_installments: number;
  amount: string;
  due_date: string;
  days_until_due?: number;
  days_overdue?: number;
}

export interface CategoryBreakdown {
  category_id: number | null;
  category_name: string;
  color: string;
  total: number;
  percentage: number;
  count: number;
}

const STALE_TIME = 1000 * 60 * 5;
const REFETCH_INTERVAL = 1000 * 60 * 5;

export function useFinancialOverview() {
  return useQuery({
    queryKey: ['financial-dashboard', 'overview'],
    queryFn: async () => {
      const { data } = await apiClient.get<FinancialOverview>('/financial-dashboard/overview/');
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useDebtByPerson() {
  return useQuery({
    queryKey: ['financial-dashboard', 'debt_by_person'],
    queryFn: async () => {
      const { data } = await apiClient.get<DebtByPerson[]>('/financial-dashboard/debt_by_person/');
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useDebtByType() {
  return useQuery({
    queryKey: ['financial-dashboard', 'debt_by_type'],
    queryFn: async () => {
      const { data } = await apiClient.get<DebtByType[]>('/financial-dashboard/debt_by_type/');
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useUpcomingInstallments(days?: number) {
  return useQuery({
    queryKey: ['financial-dashboard', 'upcoming_installments', days],
    queryFn: async () => {
      const { data } = await apiClient.get<UpcomingInstallment[]>(
        '/financial-dashboard/upcoming_installments/',
        { params: days ? { days } : undefined },
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useOverdueInstallments() {
  return useQuery({
    queryKey: ['financial-dashboard', 'overdue_installments'],
    queryFn: async () => {
      const { data } = await apiClient.get<UpcomingInstallment[]>(
        '/financial-dashboard/overdue_installments/',
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useCategoryBreakdown(year: number, month: number) {
  return useQuery({
    queryKey: ['financial-dashboard', 'category_breakdown', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<CategoryBreakdown[]>(
        '/financial-dashboard/category_breakdown/',
        { params: { year, month } },
      );
      return data;
    },
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_INTERVAL,
  });
}
