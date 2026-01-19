import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { Apartment, apartmentSchema } from '@/lib/schemas/apartment.schema';
import { PaginatedResponse, extractResults } from '@/lib/types/api';

/**
 * Hook to fetch all apartments
 */
export function useApartments(filters?: {
  building_id?: number;
  is_rented?: boolean;
  min_price?: number;
  max_price?: number;
}) {
  return useQuery({
    queryKey: ['apartments', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Apartment> | Apartment[]>('/apartments/', {
        params: { ...filters, page_size: 10000 },
      });
      // Handle both paginated and non-paginated responses
      const apartments = extractResults(data);
      // Validate each apartment with Zod schema
      return apartments.map((apartment) => apartmentSchema.parse(apartment));
    },
  });
}

/**
 * Hook to fetch a single apartment by ID
 */
export function useApartment(id: number | null) {
  return useQuery({
    queryKey: ['apartments', id],
    queryFn: async () => {
      if (!id) throw new Error('Apartment ID is required');
      const { data} = await apiClient.get<Apartment>(`/apartments/${id}/`);
      return apartmentSchema.parse(data);
    },
    enabled: !!id,
  });
}

/**
 * Hook to create a new apartment
 */
export function useCreateApartment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Apartment, 'id' | 'building' | 'furnitures'>) => {
      // Validate data before sending
      const validated = apartmentSchema.omit({ id: true, building: true, furnitures: true }).parse(data);
      const response = await apiClient.post<Apartment>('/apartments/', validated);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate apartments list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
    },
  });
}

/**
 * Hook to update an existing apartment
 */
export function useUpdateApartment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Apartment> & { id: number }) => {
      if (!data.id) throw new Error('Apartment ID is required for update');

      // Remove nested objects for API call
      const { building: _building, furnitures: _furnitures, ...updateData } = data;

      const response = await apiClient.put<Apartment>(
        `/apartments/${data.id}/`,
        updateData
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate both list and specific apartment cache
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
      queryClient.invalidateQueries({ queryKey: ['apartments', data.id] });
    },
  });
}

/**
 * Hook to delete an apartment
 */
export function useDeleteApartment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/apartments/${id}/`);
    },
    onSuccess: () => {
      // Invalidate apartments list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
    },
  });
}

/**
 * Hook to get available apartments (not rented)
 */
export function useAvailableApartments() {
  return useApartments({ is_rented: false });
}
