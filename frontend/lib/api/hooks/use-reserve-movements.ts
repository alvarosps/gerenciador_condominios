import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  reserveMovementSchema,
  type ReserveMovement,
  type ReserveMovementFilters,
} from '@/lib/schemas/finances/reserve-movement.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export function useReserveMovements(filters?: ReserveMovementFilters) {
  const cleanFilters = filters
    ? Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined))
    : {};

  return useQuery({
    queryKey: queryKeys.finances.reserveMovements.list(cleanFilters),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<ReserveMovement> | ReserveMovement[]>(
        '/finances/reserve-movements/',
        { params: { page_size: 10000, ...cleanFilters } },
      );
      const items = extractResults(data);
      return items.map((item) => reserveMovementSchema.parse(item));
    },
  });
}
