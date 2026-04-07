import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useAuthStore } from '@/store/auth-store';
import type { User } from '@/store/auth-store';

interface RequestOtpData {
  cpf_cnpj: string;
}

interface RequestOtpResponse {
  detail: string;
}

interface VerifyOtpData {
  cpf_cnpj: string;
  code: string;
}

interface VerifyOtpResponse {
  user: User;
}

export function useRequestOtp() {
  return useMutation({
    mutationFn: async (data: RequestOtpData) => {
      const response = await apiClient.post<RequestOtpResponse>('/auth/whatsapp/request/', data);
      return response.data;
    },
  });
}

export function useVerifyOtp() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (data: VerifyOtpData) => {
      const { data: responseData } = await apiClient.post<VerifyOtpResponse>(
        '/auth/whatsapp/verify/',
        data,
      );
      return responseData.user;
    },
    onSuccess: (user) => {
      setAuth(user);
    },
  });
}
