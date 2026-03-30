import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { SimulateDueDate } from "@/lib/schemas/tenant";

interface SimulateDueDateInput {
  new_due_day: number;
}

export function useSimulateDueDate() {
  return useMutation<SimulateDueDate, Error, SimulateDueDateInput>({
    mutationFn: async (input) => {
      const response = await apiClient.post<SimulateDueDate>(
        "/tenant/due-date/simulate/",
        input,
      );
      return response.data;
    },
  });
}
