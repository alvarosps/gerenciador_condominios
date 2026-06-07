import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import type { RentCalendarItem } from './use-rent-calendar';
import { type Bill, billSchema } from '@/lib/schemas/finances/bill.schema';
import type { PaymentStatus } from '@/lib/schemas/finances/category.schema';

// Dashboard endpoints return Decimal as string (like the other dashboards); converted to
// number only at the display boundary (S40). rent_entries reuse the rent-calendar item type.
interface CombinedCalendarBillExit {
  bill_id: number;
  description: string;
  building_number: number | null;
  category: string | null;
  amount_total: string;
  amount_remaining: string;
  payment_status: PaymentStatus;
  due_date: string;
  is_overdue: boolean;
  lifecycle_state: string;
}

interface CombinedCalendarDay {
  day: number;
  date: string;
  weekday: string;
  rent_entries: RentCalendarItem[];
  bill_exits: CombinedCalendarBillExit[];
}

interface CombinedCalendar {
  year: number;
  month: number;
  today: string;
  days: CombinedCalendarDay[];
}

interface OverdueBillsResponse {
  bills: Bill[];
  overdue_bills_total: string;
  overdue_bills_count: number;
  rent_overdue: { count: number; total_fee: string };
}

const STALE_TIME = 1000 * 30; // combined_calendar is uncached on the backend (§11)

export function useCombinedCalendar(year: number, month: number, buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.finances.combinedCalendar.month(year, month, buildingId),
    queryFn: async () => {
      const { data } = await apiClient.get<CombinedCalendar>(
        '/finances/finance-dashboard/combined_calendar/',
        {
          params: {
            year,
            month,
            ...(buildingId !== undefined ? { building_id: buildingId } : {}),
          },
        },
      );
      return data;
    },
    placeholderData: keepPreviousData, // §10: month navigation without a flash (not useSuspenseQuery)
    staleTime: STALE_TIME,
  });
}

interface OverdueBillsRaw {
  bills: unknown[];
  overdue_bills_total: string;
  overdue_bills_count: number;
  rent_overdue: { count: number; total_fee: string };
}

export function useOverdueBills(buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.finances.overdueBills.list(buildingId),
    queryFn: async (): Promise<OverdueBillsResponse> => {
      const { data } = await apiClient.get<OverdueBillsRaw>(
        '/finances/finance-dashboard/overdue/',
        { params: { ...(buildingId !== undefined ? { building_id: buildingId } : {}) } },
      );
      return {
        bills: data.bills.map((bill) => billSchema.parse(bill)),
        overdue_bills_total: data.overdue_bills_total,
        overdue_bills_count: data.overdue_bills_count,
        rent_overdue: data.rent_overdue,
      };
    },
    staleTime: STALE_TIME,
  });
}

export type { CombinedCalendar, CombinedCalendarBillExit, CombinedCalendarDay, OverdueBillsResponse };
