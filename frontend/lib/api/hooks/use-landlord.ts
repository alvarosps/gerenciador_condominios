import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { Landlord, LandlordFormData, landlordSchema } from '@/lib/schemas/landlord.schema';
import { AxiosError } from 'axios';

/**
 * Hook to fetch the current (active) landlord.
 *
 * Returns 404 if no landlord is configured yet.
 */
export function useLandlord() {
  return useQuery<Landlord, AxiosError>({
    queryKey: ['landlord', 'current'],
    queryFn: async () => {
      const { data } = await apiClient.get<Landlord>('/landlords/current/');
      return landlordSchema.parse(data);
    },
    retry: (failureCount, error) => {
      // Don't retry on 404 (no landlord configured)
      if (error.response?.status === 404) return false;
      return failureCount < 2;
    },
  });
}

/**
 * Hook to update the current landlord (or create if none exists).
 *
 * Uses PUT to fully replace the landlord data.
 */
export function useUpdateLandlord() {
  const queryClient = useQueryClient();

  return useMutation<Landlord, AxiosError, LandlordFormData>({
    mutationFn: async (formData: LandlordFormData) => {
      const { data } = await apiClient.put<Landlord>(
        '/landlords/current/',
        formData
      );
      return landlordSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['landlord'] });
    },
  });
}
