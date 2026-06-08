import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

// Dashboard endpoints return Decimal as string (like the other finances dashboards); converted to
// number only at the display/reduction boundary in the UI (never recomputed — the fold is backend,
// design §4.7/§8). These types are hand-written (not Zod) — there is no `.transform(Number)`.

export interface CondoProjectionMonth {
  year: number;
  month: number;
  income_total: string; // Decimal string (§4.5 collectibility-filtered revenue)
  expenses_total: string; // Decimal string
  net: string; // Decimal string (competence result of the month)
  cumulative_cash: string; // Decimal string (fold anchored on the last CondoMonthClose, §4.7)
  is_actual: boolean; // closed or the current open month = Real; future = Projetado (§8)
  is_closed: boolean; // a CondoMonthClose froze this month
}

// The scenario `type` values match CondoSimulationService.VALID_SCENARIO_TYPES (S47) 1:1.
// change_rent carries `delta` (can be negative); the rest carry `amount`. `months` is an optional
// window limiting how many future months the delta touches.
export type CondoScenarioType = 'add_expense' | 'remove_expense' | 'change_rent' | 'add_income';

export interface CondoSimulationScenario {
  type: CondoScenarioType;
  amount?: string;
  delta?: string;
  months?: number;
}

export interface CondoComparisonMonth {
  year: number;
  month: number;
  base_net: string;
  simulated_net: string;
  net_delta: string;
  base_cumulative_cash: string;
  simulated_cumulative_cash: string;
  cumulative_delta: string;
}

export interface CondoSimulationComparison {
  months: CondoComparisonMonth[];
  final_cumulative_delta: string;
  total_net_delta: string;
}

export interface CondoSimulationResult {
  base: CondoProjectionMonth[];
  simulated: CondoProjectionMonth[];
  comparison: CondoSimulationComparison;
}

export interface CondoSimulationInput {
  scenarios: CondoSimulationScenario[];
  months?: number;
}

const STALE_TIME = 1000 * 60 * 5;

export function useCondoProjection(months = 12) {
  return useQuery({
    queryKey: queryKeys.finances.projection.list(months),
    queryFn: async () => {
      const { data } = await apiClient.get<CondoProjectionMonth[]>(
        '/finances/finance-cash-flow/projection/',
        { params: { months } },
      );
      return data;
    },
    placeholderData: keepPreviousData, // §10: month-horizon changes without a flash (not useSuspenseQuery)
    staleTime: STALE_TIME,
  });
}

// Ephemeral what-if: useMutation (no query cache — deltas live in memory, design §8). The page keeps
// the result in useState.
export function useCondoSimulation() {
  return useMutation<CondoSimulationResult, Error, CondoSimulationInput>({
    mutationFn: async ({ scenarios, months }) => {
      const { data } = await apiClient.post<CondoSimulationResult>(
        '/finances/finance-cash-flow/simulate/',
        { scenarios, ...(months !== undefined ? { months } : {}) },
      );
      return data;
    },
  });
}
