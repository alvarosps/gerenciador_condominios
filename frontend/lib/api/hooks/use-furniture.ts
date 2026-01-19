import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { Furniture, furnitureSchema } from '@/lib/schemas/furniture.schema';
import { PaginatedResponse, extractResults } from '@/lib/types/api';

/**
 * Hook to fetch all furniture items
 */
export function useFurniture() {
  return useQuery({
    queryKey: ['furniture'],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Furniture> | Furniture[]>('/furnitures/', {
        params: { page_size: 10000 },
      });
      // Handle both paginated and non-paginated responses
      const furnitures = extractResults(data);
      // Validate each furniture item with Zod schema
      return furnitures.map((furniture) => furnitureSchema.parse(furniture));
    },
  });
}

/**
 * Hook to fetch a single furniture item by ID
 */
export function useFurnitureItem(id: number | null) {
  return useQuery({
    queryKey: ['furniture', id],
    queryFn: async () => {
      if (!id) throw new Error('Furniture ID is required');
      const { data } = await apiClient.get<Furniture>(`/furnitures/${id}/`);
      return furnitureSchema.parse(data);
    },
    enabled: !!id,
  });
}

/**
 * Hook to create a new furniture item
 */
export function useCreateFurniture() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Furniture, 'id'>) => {
      // Validate data before sending
      const validated = furnitureSchema.omit({ id: true }).parse(data);
      const response = await apiClient.post<Furniture>('/furnitures/', validated);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate furniture list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['furniture'] });
    },
  });
}

/**
 * Hook to update an existing furniture item
 */
export function useUpdateFurniture() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Furniture) => {
      if (!data.id) throw new Error('Furniture ID is required for update');
      // Validate complete furniture data
      const validated = furnitureSchema.parse(data);
      const response = await apiClient.put<Furniture>(
        `/furnitures/${data.id}/`,
        validated
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate both list and specific furniture item cache
      queryClient.invalidateQueries({ queryKey: ['furniture'] });
      queryClient.invalidateQueries({ queryKey: ['furniture', data.id] });
    },
  });
}

/**
 * Hook to delete a furniture item
 */
export function useDeleteFurniture() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/furnitures/${id}/`);
    },
    onSuccess: () => {
      // Invalidate furniture list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['furniture'] });
    },
  });
}
