import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { monthBoardSchema } from '@/lib/schemas/finances/month-board.schema';

/**
 * Cockpit month board (S66): overdue bills, deferred/suspended debt, per-building groups of the
 * competence, totals and the missing-bills banner count. Uncached on the backend — staleTime 0.
 */
export function useMonthBoard(year: number, month: number) {
  return useQuery({
    queryKey: queryKeys.finances.monthBoard.month(year, month),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>('/finances/finance-dashboard/month_board/', {
        params: { year, month },
      });
      return monthBoardSchema.parse(data); // plain object — the interceptor does not unwrap it
    },
    staleTime: 0, // uncached on the backend (S71 contract) — never a long staleTime
    placeholderData: keepPreviousData, // month navigation without a flash (use-combined-calendar.ts)
  });
}
