import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface FinancialOverview {
  total_expenses: number;
  total_income: number;
  net_balance: number;
  pending_expenses: number;
  pending_income: number;
  overdue_installments: number;
}

export interface DebtByPerson {
  person_id: number;
  person_name: string;
  total_debt: number;
}

export interface DebtByType {
  expense_type: string;
  total: number;
}

export interface UpcomingInstallment {
  id: number;
  expense_description: string;
  installment_number: number;
  total_installments: number;
  amount: string;
  due_date: string;
}

export interface CategoryBreakdown {
  category_name: string;
  total: number;
  percentage: number;
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
