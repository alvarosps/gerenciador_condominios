import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { DailySummaryData, FinancialOverview, MonthlyPurchaseGroup } from "@/lib/schemas/admin";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface InstallmentItem {
  id: number;
  description: string;
  amount: string;
  due_date: string;
  is_paid: boolean;
  person_name: string | null;
}

interface DailyItem {
  id: number;
  description: string;
  amount: string;
  type: string;
  is_paid: boolean;
  date: string;
}

interface MonthlyPurchases {
  card_purchases: MonthlyPurchaseGroup;
  loans: MonthlyPurchaseGroup;
  utility_bills: MonthlyPurchaseGroup;
  one_time_expenses: MonthlyPurchaseGroup;
  fixed_expenses: MonthlyPurchaseGroup;
}

interface MarkDailyPaidInput {
  item_id: number;
  item_type: string;
  amount_paid?: string;
}

export function useFinancialOverview() {
  return useQuery<FinancialOverview>({
    queryKey: ["admin", "financial", "overview"],
    queryFn: async () => {
      const response = await apiClient.get<FinancialOverview>("/financial-dashboard/overview/");
      return response.data;
    },
  });
}

export function useUpcomingInstallments(days: number = 30) {
  return useQuery<InstallmentItem[]>({
    queryKey: ["admin", "financial", "upcoming_installments", days],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<InstallmentItem>>(
        "/financial-dashboard/upcoming_installments/",
        { params: { days } },
      );
      return response.data.results;
    },
  });
}

export function useOverdueInstallments() {
  return useQuery<InstallmentItem[]>({
    queryKey: ["admin", "financial", "overdue_installments"],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<InstallmentItem>>(
        "/financial-dashboard/overdue_installments/",
      );
      return response.data.results;
    },
  });
}

export function useDailyBreakdown(year: number, month: number) {
  return useQuery<DailyItem[]>({
    queryKey: ["admin", "financial", "daily_breakdown", year, month],
    queryFn: async () => {
      const response = await apiClient.get<DailyItem[]>("/daily-control/breakdown/", {
        params: { year, month },
      });
      return response.data;
    },
  });
}

export function useDailySummary(year: number, month: number) {
  return useQuery<DailySummaryData>({
    queryKey: ["admin", "financial", "daily_summary", year, month],
    queryFn: async () => {
      const response = await apiClient.get<DailySummaryData>("/daily-control/summary/", {
        params: { year, month },
      });
      return response.data;
    },
  });
}

export function useMarkDailyPaid() {
  const qc = useQueryClient();
  return useMutation<void, Error, MarkDailyPaidInput>({
    mutationFn: async (input) => {
      await apiClient.post("/daily-control/mark_paid/", input);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "financial", "daily_breakdown"] });
      void qc.invalidateQueries({ queryKey: ["admin", "financial", "daily_summary"] });
    },
  });
}

export function useMonthlyPurchases(year: number, month: number) {
  return useQuery<MonthlyPurchases>({
    queryKey: ["admin", "financial", "monthly_purchases", year, month],
    queryFn: async () => {
      const response = await apiClient.get<MonthlyPurchases>(
        "/financial-dashboard/monthly_purchases/",
        { params: { year, month } },
      );
      return response.data;
    },
  });
}
