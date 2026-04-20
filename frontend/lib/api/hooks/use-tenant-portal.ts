import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface TenantProfile {
  id: number;
  name: string;
  cpf_cnpj: string;
  phone: string;
  marital_status: string;
  profession: string;
  due_day: number;
  dependents: { id: number; name: string; phone: string; cpf_cnpj: string }[];
  lease: {
    id: number;
    start_date: string;
    validity_months: number;
    rental_value: string;
    pending_rental_value: string | null;
    pending_rental_value_date: string | null;
    number_of_tenants: number;
    contract_generated: boolean;
  };
  apartment: {
    id: number;
    number: string;
    building_name: string;
    building_address: string;
  };
}

export function useTenantProfile() {
  return useQuery({
    queryKey: ['tenant', 'profile'],
    queryFn: async () => {
      const { data } = await apiClient.get<TenantProfile>('/tenant/me/');
      return data;
    },
  });
}
