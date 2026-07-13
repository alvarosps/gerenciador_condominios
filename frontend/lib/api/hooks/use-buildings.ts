import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { parseList } from '../parse-list';
import { type Building, buildingSchema } from '@/lib/schemas/building.schema';

/**
 * Hook to fetch all buildings
 */
export function useBuildings() {
  return useQuery({
    queryKey: queryKeys.buildings.all,
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>('/buildings/', {
        params: { page_size: 10000 },
      });
      return parseList(data, buildingSchema).items;
    },
  });
}

/**
 * Hook to fetch a single building by ID
 */
export function useBuilding(id: number | null) {
  return useQuery({
    queryKey: queryKeys.buildings.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Building ID is required');
      const { data } = await apiClient.get<Building>(`/buildings/${id}/`);
      return buildingSchema.parse(data);
    },
    enabled: Boolean(id),
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
      void queryClient.invalidateQueries({ queryKey: queryKeys.buildings.all });
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
      const response = await apiClient.put<Building>(`/buildings/${data.id}/`, validated);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.buildings.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.buildings.detail(data.id) });
      }
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
      void queryClient.invalidateQueries({ queryKey: queryKeys.buildings.all });
    },
  });
}
