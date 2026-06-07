import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { type Employee, employeeSchema } from '@/lib/schemas/finances/employee.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

const ENDPOINT = '/finances/employees/';

export interface EmployeeFilters {
  is_active?: boolean;
  payment_type?: string;
  person_id?: number;
  lease_id?: number;
}

type EmployeeWrite = Omit<
  Employee,
  'id' | 'condominium' | 'person' | 'lease' | 'created_at' | 'updated_at'
>;

export function useEmployees(filters?: EmployeeFilters) {
  const params = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};
  return useQuery({
    queryKey: queryKeys.finances.employees.list(params),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Employee> | Employee[]>(ENDPOINT, {
        params: { page_size: 10000, ...params },
      });
      return extractResults(data).map((employee) => employeeSchema.parse(employee));
    },
  });
}

export function useEmployee(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.employees.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Employee ID is required');
      const { data } = await apiClient.get<Employee>(`${ENDPOINT}${id}/`);
      return employeeSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

function invalidateEmployeeCaches(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.finances.employees.all });
}

export function useCreateEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: EmployeeWrite) => {
      const response = await apiClient.post<Employee>(ENDPOINT, data);
      return response.data;
    },
    onSuccess: () => invalidateEmployeeCaches(queryClient),
  });
}

export function useUpdateEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Employee> & { id: number }) => {
      const {
        condominium: _condominium,
        person: _person,
        lease: _lease,
        ...updateData
      } = data;
      const response = await apiClient.patch<Employee>(`${ENDPOINT}${data.id}/`, updateData);
      return response.data;
    },
    onSuccess: () => invalidateEmployeeCaches(queryClient),
  });
}

export function useDeleteEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${ENDPOINT}${id}/`);
    },
    onSuccess: () => invalidateEmployeeCaches(queryClient),
  });
}
