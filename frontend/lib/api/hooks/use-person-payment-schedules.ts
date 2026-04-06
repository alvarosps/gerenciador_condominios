import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import {
  type PersonPaymentSchedule,
  type BulkConfigureRequest,
  type PersonMonthTotal,
  personPaymentScheduleSchema,
  personMonthTotalSchema,
} from '@/lib/schemas/person-payment-schedule.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';
import { queryKeys } from '@/lib/api/query-keys';

export interface PersonPaymentScheduleFilters {
  person_id?: number;
  reference_month?: string;
}

export function usePersonPaymentSchedules(filters?: PersonPaymentScheduleFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.personPaymentSchedules.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<
        PaginatedResponse<PersonPaymentSchedule> | PersonPaymentSchedule[]
      >('/person-payment-schedules/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      const schedules = extractResults(data);
      return schedules.map((schedule) => personPaymentScheduleSchema.parse(schedule));
    },
  });
}

export function usePersonMonthTotal(personId: number | undefined, referenceMonth: string | undefined) {
  return useQuery({
    queryKey: queryKeys.personPaymentSchedules.personMonthTotal(personId, referenceMonth),
    queryFn: async () => {
      const { data } = await apiClient.get<PersonMonthTotal>(
        '/person-payment-schedules/person_month_total/',
        { params: { person_id: personId, reference_month: referenceMonth } },
      );
      return personMonthTotalSchema.parse(data);
    },
    enabled: personId !== undefined && referenceMonth !== undefined,
  });
}

export function useBulkConfigureSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BulkConfigureRequest) => {
      const response = await apiClient.post<PersonPaymentSchedule[]>(
        '/person-payment-schedules/bulk_configure/',
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personPaymentSchedules.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dailyControl.all });
    },
  });
}

export function useDeletePersonPaymentSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/person-payment-schedules/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.personPaymentSchedules.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dailyControl.all });
    },
  });
}
