import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { type Lease, leaseSchema } from '@/lib/schemas/lease.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

/**
 * Hook to fetch all leases with optional filters
 */
export function useLeases(filters?: {
  apartment_id?: number;
  responsible_tenant_id?: number;
  is_active?: boolean;
  is_expired?: boolean;
  expiring_soon?: boolean;
}) {
  // Clean filters: remove undefined values for proper query key comparison
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.leases.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Lease> | Lease[]>('/leases/', {
        params: { ...cleanFilters, page_size: 10000 },
      });
      // Handle both paginated and non-paginated responses
      const leases = extractResults(data);
      // Validate each lease with Zod schema
      return leases.map((lease) => leaseSchema.parse(lease));
    },
  });
}

/**
 * Hook to fetch a single lease by ID
 */
export function useLease(id: number | null) {
  return useQuery({
    queryKey: queryKeys.leases.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Lease ID is required');
      const { data } = await apiClient.get<Lease>(`/leases/${id}/`);
      return leaseSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

/**
 * Hook to create a new lease
 */
export function useCreateLease() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Lease, 'id' | 'apartment' | 'responsible_tenant' | 'tenants' | 'final_date' | 'rental_value' | 'resident_dependent'>) => {
      const response = await apiClient.post<Lease>('/leases/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

/**
 * Hook to update an existing lease
 */
export function useUpdateLease() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Lease> & { id: number }) => {
      if (!data.id) throw new Error('Lease ID is required for update');

      // Remove nested objects for API call
      const { apartment: _apartment, responsible_tenant: _responsible_tenant, tenants: _tenants, ...updateData } = data;

      const response = await apiClient.put<Lease>(
        `/leases/${data.id}/`,
        updateData
      );
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.leases.detail(data.id) });
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

/**
 * Hook to delete a lease
 */
export function useDeleteLease() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/leases/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

/**
 * Hook to partially update a lease (PATCH)
 */
export function usePatchLease() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...fields }: { id: number } & Record<string, unknown>) => {
      const response = await apiClient.patch<Lease>(`/leases/${String(id)}/`, fields);
      return leaseSchema.parse(response.data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
    },
  });
}

/**
 * Hook to generate a contract PDF for a lease
 * This calls the backend to generate the PDF using pyppeteer
 */
export function useGenerateContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (leaseId: number) => {
      const { data } = await apiClient.post<{
        pdf_path: string;
        message: string;
      }>(`/leases/${leaseId}/generate_contract/`);
      return data;
    },
    onSuccess: (_, leaseId) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.detail(leaseId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
    },
  });
}

/**
 * Hook to calculate late fee for a lease
 * Returns the calculated late fee based on days overdue
 */
export function useCalculateLateFee() {
  return useMutation({
    mutationFn: async (params: {
      leaseId: number;
      payment_date: string; // Format: YYYY-MM-DD
    }) => {
      const { data } = await apiClient.get<{
        late_fee: number;
        days_late: number;
        daily_rate: number;
        message: string;
      }>(`/leases/${params.leaseId}/calculate_late_fee/`, {
        params: {
          payment_date: params.payment_date,
        },
      });
      return data;
    },
  });
}

/**
 * Hook to change the due date of a lease
 * Calculates and applies a fee for changing the due date
 */
export function useChangeDueDate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: {
      leaseId: number;
      new_due_day: number; // 1-31
    }) => {
      const { data } = await apiClient.post<{
        old_due_day: number;
        new_due_day: number;
        old_due_date: string;
        new_due_date: string;
        change_fee: number;
        days_difference: number;
        daily_rate: number;
        total_due: number;
        message: string;
      }>(`/leases/${params.leaseId}/change_due_date/`, {
        new_due_day: params.new_due_day,
      });
      return data;
    },
    onSuccess: (_, params) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.detail(params.leaseId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.tenants.all });
    },
  });
}

/**
 * Hook to get active leases
 */
export function useActiveLeases() {
  return useLeases({ is_active: true });
}

/**
 * Hook to get expired leases
 */
export function useExpiredLeases() {
  return useLeases({ is_expired: true });
}

/**
 * Hook to get leases expiring soon (within 30 days)
 */
export function useExpiringSoonLeases() {
  return useLeases({ expiring_soon: true });
}

/**
 * Hook to get leases for a specific apartment
 */
export function useApartmentLeases(apartmentId: number | null) {
  return useLeases(apartmentId ? { apartment_id: apartmentId } : undefined);
}

/**
 * Hook to get leases for a specific tenant
 */
export function useTenantLeases(tenantId: number | null) {
  return useLeases(tenantId ? { responsible_tenant_id: tenantId } : undefined);
}

/**
 * Hook to transfer a tenant to a different apartment (creates a new lease)
 * Calls POST /leases/{id}/transfer/ which terminates the old lease and creates a new one
 */
export function useTransferLease() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leaseId, ...payload }: { leaseId: number } & Record<string, unknown>) => {
      const response = await apiClient.post<Lease>(`/leases/${String(leaseId)}/transfer/`, payload);
      return leaseSchema.parse(response.data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
    },
  });
}

/**
 * Hook to terminate a lease contract
 * Calls POST /leases/{id}/terminate/ which marks the apartment as available
 */
export function useTerminateLease() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leaseId: number) => {
      const response = await apiClient.post<{ detail: string }>(`/leases/${String(leaseId)}/terminate/`);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leases.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.apartments.all });
    },
  });
}
