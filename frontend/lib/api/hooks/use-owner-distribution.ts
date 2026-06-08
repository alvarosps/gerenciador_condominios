import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

// Dashboard endpoint → Decimals are strings (hand-written types, no Zod transform). The household
// fold (available/carried_out) is computed by the backend (§4.7) and NEVER recomputed on the front.

export interface OwnerHousehold {
  name: string; // "Raul & Célia" — a label (the household IS the condominium, §13)
  result_of_month: string; // competence result (= CondoBalanceService.result_of_month, §8)
  carried_in: string; // carregado_in[M], <= 0 (§4.7)
  available: string; // max(0, net + carried_in) — distributable (§4.7)
  carried_out: string; // min(0, net + carried_in), <= 0 — carried to the next month (§4.7)
}

export interface ExternalOwnerEntry {
  owner_id: number;
  owner_name: string; // Tiago / Alvaro (§17)
  leases_count: number;
  rent_total: string; // Σ effective_rental_value of the owner's displayable leases — display only (§6)
}

export interface OwnerDistribution {
  year: number;
  month: number;
  household: OwnerHousehold;
  external_owners: ExternalOwnerEntry[];
  external_total: string; // Σ rent_total — display only, never part of the household result
}

const STALE_TIME = 1000 * 60 * 5;

export function useOwnerDistribution(year: number, month: number, buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.finances.ownerDistribution.month(year, month, buildingId),
    queryFn: async () => {
      const { data } = await apiClient.get<OwnerDistribution>(
        '/finances/finance-dashboard/by_owner/',
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
