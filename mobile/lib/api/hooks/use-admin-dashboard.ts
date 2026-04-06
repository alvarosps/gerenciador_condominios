import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type {
  FinancialSummary,
  LatePaymentItem,
  LeaseMetrics,
  RentAdjustmentAlert,
} from "@/lib/schemas/admin";

export function useFinancialSummary() {
  return useQuery<FinancialSummary>({
    queryKey: ["admin", "dashboard", "financial_summary"],
    queryFn: async () => {
      const response = await apiClient.get<FinancialSummary>("/dashboard/financial_summary/");
      return response.data;
    },
  });
}

interface LatePaymentSummary {
  late_payments: LatePaymentItem[];
  total_late: number;
  total_amount_due: string;
}

export function useLatePayments() {
  return useQuery<LatePaymentSummary>({
    queryKey: ["admin", "dashboard", "late_payment_summary"],
    queryFn: async () => {
      const response = await apiClient.get<LatePaymentSummary>("/dashboard/late_payment_summary/");
      return response.data;
    },
  });
}

export function useLeaseMetrics() {
  return useQuery<LeaseMetrics>({
    queryKey: ["admin", "dashboard", "lease_metrics"],
    queryFn: async () => {
      const response = await apiClient.get<LeaseMetrics>("/dashboard/lease_metrics/");
      return response.data;
    },
  });
}

export function useRentAdjustmentAlerts() {
  return useQuery<RentAdjustmentAlert[]>({
    queryKey: ["admin", "dashboard", "rent_adjustment_alerts"],
    queryFn: async () => {
      const response = await apiClient.get<RentAdjustmentAlert[]>(
        "/dashboard/rent_adjustment_alerts/",
      );
      return response.data;
    },
  });
}
