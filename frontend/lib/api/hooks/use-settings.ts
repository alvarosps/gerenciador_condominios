import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { User } from '@/store/auth-store';

interface UpdateProfilePayload {
  first_name: string;
  last_name: string;
}

interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
}

export function useUpdateProfile() {
  return useMutation({
    mutationFn: async (data: UpdateProfilePayload) => {
      const response = await apiClient.patch<User>('/auth/me/update/', data);
      return response.data;
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (data: ChangePasswordPayload) => {
      const response = await apiClient.post<{ detail: string }>('/auth/change-password/', data);
      return response.data;
    },
  });
}
