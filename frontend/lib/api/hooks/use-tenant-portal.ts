import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export const tenantProfileKeys = {
  all: ['tenant', 'profile'] as const,
} as const;

export interface TenantProfile {
  id: number;
  name: string;
  cpf_cnpj: string;
  phone: string;
  marital_status: string;
  profession: string;
  due_day: number;
  dependents: { id: number; name: string; phone: string; cpf_cnpj: string }[];
  // Absent when the tenant has no active lease (e.g. moved out, awaiting a new lease) —
  // the backend only includes these keys when a lease exists.
  lease?: {
    id: number;
    start_date: string;
    validity_months: number;
    rental_value: string;
    pending_rental_value: string | null;
    pending_rental_value_date: string | null;
    number_of_tenants: number;
    contract_generated: boolean;
  };
  apartment?: {
    id: number;
    number: string;
    building_name: string;
    building_address: string;
  };
}

export function useTenantProfile() {
  return useQuery({
    queryKey: tenantProfileKeys.all,
    queryFn: async () => {
      const { data } = await apiClient.get<TenantProfile>('/tenant/me/');
      return data;
    },
  });
}

interface UpdateTenantPhoneResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

/**
 * Update the tenant's own phone (the OTP channel) via the shared profile-update endpoint.
 */
export function useUpdateTenantPhone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (phone: string) => {
      const { data } = await apiClient.patch<UpdateTenantPhoneResponse>('/auth/me/update/', {
        phone,
      });
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: tenantProfileKeys.all });
    },
  });
}
