import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { AdminUser, UserFormValues } from '@/lib/schemas/user';
import { queryKeys } from '@/lib/api/query-keys';

export function useAdminUsers() {
  return useQuery({
    queryKey: queryKeys.adminUsers.all,
    queryFn: async () => {
      const { data } = await apiClient.get<AdminUser[]>('/admin/users/');
      return data;
    },
  });
}

export function useCreateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UserFormValues) => {
      const { data } = await apiClient.post<AdminUser>('/admin/users/', payload);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers.all });
    },
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: UserFormValues & { id: number }) => {
      const { data } = await apiClient.patch<AdminUser>(`/admin/users/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers.all });
    },
  });
}

export function useDeleteAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/admin/users/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers.all });
    },
  });
}
