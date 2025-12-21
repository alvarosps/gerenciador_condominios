import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { Lease, leaseSchema } from '@/lib/schemas/lease.schema';

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
  return useQuery({
    queryKey: ['leases', filters],
    queryFn: async () => {
      const { data } = await apiClient.get<Lease[]>('/leases/', {
        params: filters,
      });
      // Validate each lease with Zod schema
      return data.map((lease) => leaseSchema.parse(lease));
    },
  });
}

/**
 * Hook to fetch a single lease by ID
 */
export function useLease(id: number | null) {
  return useQuery({
    queryKey: ['leases', id],
    queryFn: async () => {
      if (!id) throw new Error('Lease ID is required');
      const { data } = await apiClient.get<Lease>(`/leases/${id}/`);
      return leaseSchema.parse(data);
    },
    enabled: !!id,
  });
}

/**
 * Hook to create a new lease
 */
export function useCreateLease() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<Lease, 'id' | 'apartment' | 'responsible_tenant' | 'tenants' | 'final_date'>) => {
      const response = await apiClient.post<Lease>('/leases/', data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate leases list and related caches
      queryClient.invalidateQueries({ queryKey: ['leases'] });
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      // Invalidate both list and specific lease cache
      queryClient.invalidateQueries({ queryKey: ['leases'] });
      queryClient.invalidateQueries({ queryKey: ['leases', data.id] });
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      // Invalidate leases list and related caches
      queryClient.invalidateQueries({ queryKey: ['leases'] });
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
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
      // Invalidate lease to refresh contract_generated status
      queryClient.invalidateQueries({ queryKey: ['leases', leaseId] });
      queryClient.invalidateQueries({ queryKey: ['leases'] });
      queryClient.invalidateQueries({ queryKey: ['apartments'] });
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
        change_fee: number;
        days_difference: number;
        daily_rate: number;
        message: string;
      }>(`/leases/${params.leaseId}/change_due_date/`, {
        new_due_day: params.new_due_day,
      });
      return data;
    },
    onSuccess: (_, params) => {
      // Invalidate lease to refresh due_day
      queryClient.invalidateQueries({ queryKey: ['leases', params.leaseId] });
      queryClient.invalidateQueries({ queryKey: ['leases'] });
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
