import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface MonthlyPurchaseItem {
  description: string;
  amount: number;
  total_amount: number | null;
  total_installments: number | null;
  person_name: string | null;
  card_name: string | null;
  category_name: string | null;
  category_color: string | null;
  date: string | null;
  expense_type: string;
}

export interface MonthlyPurchaseGroup {
  total: number;
  count: number;
  items: MonthlyPurchaseItem[];
}

export interface MonthlyPurchaseCategoryBreakdown {
  category_id: number | null;
  category_name: string;
  color: string;
  total: number;
  percentage: number;
  count: number;
}

export interface MonthlyPurchasesResponse {
  year: number;
  month: number;
  total: number;
  by_type: {
    card_purchases: MonthlyPurchaseGroup;
    loans: MonthlyPurchaseGroup;
    utility_bills: MonthlyPurchaseGroup;
    one_time_expenses: MonthlyPurchaseGroup;
    fixed_expenses: MonthlyPurchaseGroup;
  };
  by_category: MonthlyPurchaseCategoryBreakdown[];
}

export function useMonthlyPurchases(year: number, month: number) {
  return useQuery({
    queryKey: ['monthly-purchases', year, month],
    queryFn: async () => {
      const { data } = await apiClient.get<MonthlyPurchasesResponse>(
        '/financial-dashboard/monthly_purchases/',
        { params: { year, month } },
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
