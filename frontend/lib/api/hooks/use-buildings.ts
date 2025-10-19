import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { Building, buildingSchema } from '@/lib/schemas/building.schema';

/**
 * Hook to fetch all buildings
 */
export function useBuildings() {
  return useQuery({
    queryKey: ['buildings'],
    queryFn: async () => {
      const { data } = await apiClient.get<Building[]>('/buildings/');
      // Validate each building with Zod schema
      return data.map((building) => buildingSchema.parse(building));
    },
  });
}

/**
 * Hook to fetch a single building by ID
 */
export function useBuilding(id: number | null) {
  return useQuery({
    queryKey: ['buildings', id],
    queryFn: async () => {
      if (!id) throw new Error('Building ID is required');
      const { data } = await apiClient.get<Building>(`/buildings/${id}/`);
      return buildingSchema.parse(data);
    },
    enabled: !!id,
  });
}

/**
 * Hook to create a new building
 */
export function useCreateBuilding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Building, 'id'>) => {
      // Validate data before sending
      const validated = buildingSchema.omit({ id: true }).parse(data);
      const response = await apiClient.post<Building>('/buildings/', validated);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate buildings list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
    },
  });
}

/**
 * Hook to update an existing building
 */
export function useUpdateBuilding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Building) => {
      if (!data.id) throw new Error('Building ID is required for update');
      // Validate complete building data
      const validated = buildingSchema.parse(data);
      const response = await apiClient.put<Building>(
        `/buildings/${data.id}/`,
        validated
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate both list and specific building cache
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
      queryClient.invalidateQueries({ queryKey: ['buildings', data.id] });
    },
  });
}

/**
 * Hook to delete a building
 */
export function useDeleteBuilding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/buildings/${id}/`);
    },
    onSuccess: () => {
      // Invalidate buildings list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
    },
  });
}
