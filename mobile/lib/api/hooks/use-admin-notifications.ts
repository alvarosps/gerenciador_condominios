import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { TenantNotification } from "@/lib/schemas/tenant";

// Backend endpoints: GET/PATCH/POST /admin/notifications/ (IsAdminUser permission)

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export function useAdminNotifications() {
  return useQuery<TenantNotification[]>({
    queryKey: ["admin", "notifications"],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<TenantNotification>>(
        "/admin/notifications/",
        { params: { page_size: 50 } },
      );
      return response.data.results;
    },
  });
}

export function useMarkAdminNotificationRead() {
  const qc = useQueryClient();
  return useMutation<TenantNotification, Error, number>({
    mutationFn: async (notificationId) => {
      const response = await apiClient.patch<TenantNotification>(
        `/admin/notifications/${notificationId}/read/`,
      );
      return response.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "notifications"] });
    },
  });
}

export function useMarkAllAdminNotificationsRead() {
  const qc = useQueryClient();
  return useMutation<{ marked_read: number }, Error, void>({
    mutationFn: async () => {
      const response = await apiClient.post<{ marked_read: number }>(
        "/notifications/read-all/",
      );
      return response.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "notifications"] });
    },
  });
}
