import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { parseList } from '../parse-list';
import {
  reserveMovementSchema,
  type ReserveMovementFilters,
} from '@/lib/schemas/finances/reserve-movement.schema';

export function useReserveMovements(filters?: ReserveMovementFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.finances.reserveMovements.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>('/finances/reserve-movements/', {
        params: { page_size: 10000, ...cleanFilters },
      });
      return parseList(data, reserveMovementSchema).items;
    },
  });
}
