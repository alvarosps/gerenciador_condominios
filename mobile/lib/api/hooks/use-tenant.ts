import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { TenantMe, RentPayment, RentAdjustment } from "@/lib/schemas/tenant";

export function useTenantMe() {
  return useQuery<TenantMe>({
    queryKey: ["tenant", "me"],
    queryFn: async () => {
      const response = await apiClient.get<TenantMe>("/tenant/me/");
      return response.data;
    },
  });
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export function useTenantPayments() {
  return useQuery<RentPayment[]>({
    queryKey: ["tenant", "payments"],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<RentPayment>>("/tenant/payments/");
      return response.data.results;
    },
  });
}

export function useTenantAdjustments() {
  return useQuery<RentAdjustment[]>({
    queryKey: ["tenant", "adjustments"],
    queryFn: async () => {
      const response = await apiClient.get<RentAdjustment[]>("/tenant/rent-adjustments/");
      return response.data;
    },
  });
}
