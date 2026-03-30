import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { PixPayload } from "@/lib/schemas/tenant";

export function useGeneratePix() {
  return useMutation<PixPayload, Error, void>({
    mutationFn: async () => {
      const response = await apiClient.post<PixPayload>("/tenant/payments/pix/");
      return response.data;
    },
  });
}
