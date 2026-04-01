import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { PaymentProofAdmin } from "@/lib/schemas/admin";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface MarkRentPaidInput {
  lease_id: number;
  reference_month: string;
  amount_paid: string;
}

interface ReviewProofInput {
  id: number;
  action: "approve" | "reject";
  reason?: string;
}

interface ApplyRentAdjustmentInput {
  lease_id: number;
  percentage: string;
  adjustment_date: string;
  update_apartment_price: boolean;
}

interface LateFeeResult {
  days_late: number;
  daily_rate: string;
  late_fee: string;
  total_due: string;
}

export function useMarkRentPaid() {
  const qc = useQueryClient();
  return useMutation<void, Error, MarkRentPaidInput>({
    mutationFn: async (input) => {
      await apiClient.post("/dashboard/mark_rent_paid/", input);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
  });
}

export function useAdminProofs(status: string = "pending") {
  return useQuery<PaymentProofAdmin[]>({
    queryKey: ["admin", "proofs", status],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<PaymentProofAdmin>>(
        "/admin/proofs/",
        { params: { status } },
      );
      return response.data.results;
    },
  });
}

export function useReviewProof() {
  const qc = useQueryClient();
  return useMutation<void, Error, ReviewProofInput>({
    mutationFn: async ({ id, action, reason }) => {
      await apiClient.post(`/admin/proofs/${id}/review/`, { action, reason });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "proofs"] });
    },
  });
}

export function useApplyRentAdjustment() {
  const qc = useQueryClient();
  return useMutation<void, Error, ApplyRentAdjustmentInput>({
    mutationFn: async ({ lease_id, ...body }) => {
      await apiClient.post(`/leases/${lease_id}/adjust_rent/`, body);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "leases"] });
      void qc.invalidateQueries({ queryKey: ["admin", "dashboard", "rent_adjustment_alerts"] });
    },
  });
}

export function useCalculateLateFee(leaseId: number | null) {
  return useQuery<LateFeeResult>({
    queryKey: ["admin", "late_fee", leaseId],
    queryFn: async () => {
      const response = await apiClient.get<LateFeeResult>(
        `/leases/${leaseId}/calculate_late_fee/`,
      );
      return response.data;
    },
    enabled: leaseId !== null,
  });
}
