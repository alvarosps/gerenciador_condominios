import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { PaymentProof } from "@/lib/schemas/tenant";

interface UploadProofInput {
  reference_month: string;
  file: {
    uri: string;
    name: string;
    type: string;
  };
  pix_code?: string;
}

export function useUploadProof() {
  return useMutation<PaymentProof, Error, UploadProofInput>({
    mutationFn: async (input) => {
      const formData = new FormData();
      formData.append("reference_month", input.reference_month);
      formData.append("file", {
        uri: input.file.uri,
        name: input.file.name,
        type: input.file.type,
      } as unknown as Blob);
      if (input.pix_code) {
        formData.append("pix_code", input.pix_code);
      }
      const response = await apiClient.post<PaymentProof>("/tenant/payments/proof/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data;
    },
  });
}

export function useProofStatus(proofId: number | null) {
  return useQuery<PaymentProof>({
    queryKey: ["tenant", "proof", proofId],
    queryFn: async () => {
      const response = await apiClient.get<PaymentProof>(`/tenant/payments/proof/${proofId}/`);
      return response.data;
    },
    enabled: proofId !== null,
  });
}
