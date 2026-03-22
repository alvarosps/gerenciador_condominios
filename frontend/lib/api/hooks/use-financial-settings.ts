import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import {
  type FinancialSettings,
  financialSettingsSchema,
} from '@/lib/schemas/financial-settings.schema';

export function useFinancialSettings() {
  return useQuery({
    queryKey: ['financial-settings'],
    queryFn: async () => {
      const { data } = await apiClient.get<FinancialSettings>('/financial-settings/current/');
      return financialSettingsSchema.parse(data);
    },
  });
}

export function useUpdateFinancialSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<FinancialSettings, 'id' | 'updated_at' | 'updated_by'>) => {
      const response = await apiClient.put<FinancialSettings>('/financial-settings/current/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['financial-settings'] });
    },
  });
}
