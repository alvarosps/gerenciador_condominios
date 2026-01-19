import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { Tenant, tenantSchema } from '@/lib/schemas/tenant.schema';
import { PaginatedResponse, extractResults } from '@/lib/types/api';

/**
 * Hook to fetch all tenants with optional filters
 */
export function useTenants(filters?: {
  is_company?: boolean;
  has_dependents?: boolean;
  has_furniture?: boolean;
  search?: string;
}) {
  return useQuery({
    queryKey: ['tenants', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Tenant> | Tenant[]>('/tenants/', {
        params: { ...filters, page_size: 10000 },
      });
      // Handle both paginated and non-paginated responses
      const tenants = extractResults(data);
      // Validate each tenant with Zod schema
      return tenants.map((tenant) => tenantSchema.parse(tenant));
    },
  });
}

/**
 * Hook to fetch a single tenant by ID
 */
export function useTenant(id: number | null) {
  return useQuery({
    queryKey: ['tenants', id],
    queryFn: async () => {
      if (!id) throw new Error('Tenant ID is required');
      const { data } = await apiClient.get<Tenant>(`/tenants/${id}/`);
      return tenantSchema.parse(data);
    },
    enabled: !!id,
  });
}

/**
 * Hook to create a new tenant
 * Supports creating tenant with dependents in a single request
 */
export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Tenant, 'id' | 'furnitures'>) => {
      const response = await apiClient.post<Tenant>('/tenants/', data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate tenants list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

/**
 * Hook to update an existing tenant
 */
export function useUpdateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Tenant> & { id: number }) => {
      if (!data.id) throw new Error('Tenant ID is required for update');

      // Remove nested objects for API call
      const { furnitures: _furnitures, dependents: _dependents, ...updateData } = data;

      const response = await apiClient.put<Tenant>(
        `/tenants/${data.id}/`,
        updateData
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate both list and specific tenant cache
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenants', data.id] });
    },
  });
}

/**
 * Hook to delete a tenant
 */
export function useDeleteTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/tenants/${id}/`);
    },
    onSuccess: () => {
      // Invalidate tenants list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

/**
 * Hook to get tenants with furniture
 */
export function useTenantsWithFurniture() {
  return useTenants({ has_furniture: true });
}

/**
 * Hook to get company tenants
 */
export function useCompanyTenants() {
  return useTenants({ is_company: true });
}

/**
 * Hook to get person tenants
 */
export function usePersonTenants() {
  return useTenants({ is_company: false });
}

/**
 * Hook to search tenants by name or CPF/CNPJ
 */
export function useSearchTenants(searchTerm: string) {
  return useTenants({ search: searchTerm });
}
