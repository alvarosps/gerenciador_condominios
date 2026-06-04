import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

// Rent Calendar API Response Types - matching backend RentScheduleService.
// Monetary values are strings (as in the other dashboard endpoints); dates are ISO YYYY-MM-DD.

interface RentCalendarItem {
  lease_id: number;
  tenant_name: string;
  apartment_number: number;
  building_number: string;
  rental_value: string;
  is_paid: boolean;
  payment_date: string | null;
  is_overdue: boolean;
  day_passed: boolean;
  can_toggle: boolean;
  late_fee: string;
  late_days: number;
  is_collectible: boolean;
  non_collectible_reason: string | null;
}

interface RentCalendarDay {
  day: number;
  date: string;
  weekday: string;
  items: RentCalendarItem[];
}

interface RentCalendarStats {
  received_total: string;
  to_receive_total: string;
  expected_total: string;
  paid_count: number;
  due_count: number;
  overdue_count: number;
  overdue_total_fee: string;
  vacant_kitnets_count: number;
  vacant_kitnets_value: string;
}

interface RentCalendar {
  year: number;
  month: number;
  today: string;
  next_due_date: string | null;
  days: RentCalendarDay[];
  stats: RentCalendarStats;
}

interface ToggleRentPaymentRequest {
  lease_id: number;
  reference_month: string;
}

interface ToggleRentPaymentResponse {
  status: string;
  is_paid: boolean;
  message: string;
}

const STALE_TIME = 1000 * 30; // 30s — toggles need near-immediate reflection (endpoint is uncached)

/**
 * Returns a new RentCalendar with the matching lease item's `is_paid` flipped.
 * Pure and immutable — no in-place mutation, safe for optimistic flip and rollback.
 */
function flipPaidByLease(calendar: RentCalendar, leaseId: number): RentCalendar {
  return {
    ...calendar,
    days: calendar.days.map((day) => ({
      ...day,
      items: day.items.map((item) =>
        item.lease_id === leaseId ? { ...item, is_paid: !item.is_paid } : item,
      ),
    })),
  };
}

interface ToggleRentPaymentContext {
  previous: [readonly unknown[], RentCalendar | undefined][];
}

/**
 * Hook to fetch the monthly rent calendar (days + items + stats).
 * Forwards building_id only when defined.
 */
export function useRentCalendar(year: number, month: number, buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.rentCalendar.month(year, month, buildingId),
    queryFn: async () => {
      const { data } = await apiClient.get<RentCalendar>('/dashboard/rent_calendar/', {
        params: {
          year,
          month,
          ...(buildingId !== undefined ? { building_id: buildingId } : {}),
        },
      });
      return data;
    },
    staleTime: STALE_TIME,
  });
}

/**
 * Hook to toggle rent payment (mark/unmark paid) with an optimistic update.
 * The mutation does not know year/month/buildingId, so the optimistic flip acts on
 * every cached rent-calendar query via getQueriesData/setQueryData.
 */
export function useToggleRentPayment() {
  const queryClient = useQueryClient();

  return useMutation<
    ToggleRentPaymentResponse,
    Error,
    ToggleRentPaymentRequest,
    ToggleRentPaymentContext
  >({
    mutationFn: async (request) => {
      const { data } = await apiClient.post<ToggleRentPaymentResponse>(
        '/dashboard/toggle_rent_payment/',
        request,
      );
      return data;
    },
    onMutate: async (request) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.rentCalendar.all });

      const previous = queryClient.getQueriesData<RentCalendar>({
        queryKey: queryKeys.rentCalendar.all,
      });

      for (const [key, data] of previous) {
        if (data) {
          queryClient.setQueryData<RentCalendar>(key, flipPaidByLease(data, request.lease_id));
        }
      }

      return { previous };
    },
    onError: (_error, _request, context) => {
      if (context?.previous) {
        for (const [key, data] of context.previous) {
          queryClient.setQueryData(key, data);
        }
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rentCalendar.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.latePaymentSummary() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.financialSummary() });
    },
  });
}

export type {
  RentCalendar,
  RentCalendarDay,
  RentCalendarItem,
  RentCalendarStats,
  ToggleRentPaymentRequest,
  ToggleRentPaymentResponse,
};
