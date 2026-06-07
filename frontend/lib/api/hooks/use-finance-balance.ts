import { useQuery } from '@tanstack/react-query';
import { keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

// Dashboard types — money stays as STRING from server, converted at display only
export interface RentOverdue {
  count: number;
  total_fee: string;
}

export interface FinanceOverview {
  year: number;
  month: number;
  result_of_month: string;
  cash_change_of_month: string;
  cash_balance: string;
  reserve_balance: string;
  total_balance: string;
  overdue_bills_total: string;
  overdue_bills_count: number;
  rent_overdue: RentOverdue;
  wedge_ok: boolean;
}

export interface MonthlyBalanceEntry {
  month: number;
  result_of_month: string;
  cash_change_of_month: string;
  cash_balance_end: string;
  reserve_balance_end: string;
  total_balance: string;
  is_closed: boolean;
}

export interface MonthlyBalance {
  year: number;
  months: MonthlyBalanceEntry[];
}

export interface ByCategoryEntry {
  category_id: number | null;
  name: string;
  color: string;
  total: string;
}

export interface ByCategory {
  year: number;
  month: number;
  categories: ByCategoryEntry[];
}

export function useFinanceOverview(
  year: number,
  month: number,
  buildingId?: number,
) {
  return useQuery({
    queryKey: queryKeys.finances.overview.month(year, month, buildingId),
    queryFn: async () => {
      const params: Record<string, string | number> = { year, month };
      if (buildingId !== undefined) {
        params.building_id = buildingId;
      }
      const { data } = await apiClient.get<FinanceOverview>(
        '/finances/finance-dashboard/overview/',
        { params },
      );
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useMonthlyBalance(year: number) {
  return useQuery({
    queryKey: queryKeys.finances.monthlyBalance.year(year),
    queryFn: async () => {
      const { data } = await apiClient.get<MonthlyBalance>(
        '/finances/finance-dashboard/monthly_balance/',
        { params: { year } },
      );
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useByCategory(year: number, month: number, buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.finances.byCategory.month(year, month, buildingId),
    queryFn: async () => {
      const params: Record<string, string | number> = { year, month };
      if (buildingId !== undefined) {
        params.building_id = buildingId;
      }
      const { data } = await apiClient.get<ByCategory>(
        '/finances/finance-dashboard/by_category/',
        { params },
      );
      return data;
    },
    placeholderData: keepPreviousData,
  });
}
