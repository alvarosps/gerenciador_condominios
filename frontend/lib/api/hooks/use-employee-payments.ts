import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { type EmployeePayment, employeePaymentSchema } from '@/lib/schemas/employee-payment.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface EmployeePaymentFilters {
  person_id?: number;
  reference_month?: string;
  is_paid?: boolean;
}

export function useEmployeePayments(filters?: EmployeePaymentFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.employeePayments.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<EmployeePayment> | EmployeePayment[]>(
        '/employee-payments/',
        { params: { page_size: 10000, ...cleanFilters } },
      );
      const payments = extractResults(data);
      return payments.map((payment) => employeePaymentSchema.parse(payment));
    },
  });
}

export function useEmployeePayment(id: number | null) {
  return useQuery({
    queryKey: queryKeys.employeePayments.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('EmployeePayment ID is required');
      const { data } = await apiClient.get<EmployeePayment>(`/employee-payments/${id}/`);
      return employeePaymentSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateEmployeePayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Omit<EmployeePayment, 'id' | 'person' | 'total_paid'>) => {
      const response = await apiClient.post<EmployeePayment>('/employee-payments/', data);
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.employeePayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useUpdateEmployeePayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<EmployeePayment> & { id: number }) => {
      if (!data.id) throw new Error('EmployeePayment ID is required for update');
      const { person: _person, ...updateData } = data;
      const response = await apiClient.put<EmployeePayment>(`/employee-payments/${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.employeePayments.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({ queryKey: queryKeys.employeePayments.detail(data.id) });
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useDeleteEmployeePayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/employee-payments/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.employeePayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}

export function useMarkEmployeePaymentPaid() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await apiClient.post<EmployeePayment>(`/employee-payments/${id}/mark_paid/`);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.employeePayments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.financialDashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.cashFlow.all });
    },
  });
}
