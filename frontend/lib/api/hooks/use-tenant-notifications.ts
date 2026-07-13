import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { apiClient } from '@/lib/api/client';

/**
 * Parse a failed blob-responseType request's error body (itself a Blob, since axios still
 * honors responseType on error responses) into a plain object so getErrorMessage() can read
 * the real backend message (e.g. {"detail": "..."}) instead of falling back to a generic
 * HTTP-status message.
 */
async function rethrowWithParsedBlobError(error: unknown): Promise<never> {
  if (isAxiosError(error) && error.response?.data instanceof Blob) {
    try {
      const text = await error.response.data.text();
      error.response.data = JSON.parse(text) as unknown;
    } catch {
      // Not JSON (or empty) — leave the original Blob, getErrorMessage falls back to status.
    }
  }
  throw error;
}

export interface TenantNotification {
  id: number;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  sent_at: string;
}

export const tenantNotificationKeys = {
  all: ['tenant', 'notifications'] as const,
} as const;

export function useTenantNotifications() {
  return useQuery({
    queryKey: tenantNotificationKeys.all,
    queryFn: async () => {
      const { data } = await apiClient.get<{ results: TenantNotification[] }>(
        '/tenant/notifications/'
      );
      return data.results;
    },
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.patch(`/tenant/notifications/${String(id)}/read/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: tenantNotificationKeys.all });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/tenant/notifications/read-all/');
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: tenantNotificationKeys.all });
    },
  });
}

export function useDownloadContract() {
  return useMutation({
    mutationFn: async () => {
      try {
        const response = await apiClient.get('/tenant/contract/', {
          responseType: 'blob',
        });
        const url = URL.createObjectURL(response.data as Blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'contrato.pdf';
        link.click();
        URL.revokeObjectURL(url);
      } catch (error) {
        await rethrowWithParsedBlobError(error);
      }
    },
  });
}
