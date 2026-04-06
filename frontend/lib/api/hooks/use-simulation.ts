import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { CashFlowProjectionMonth } from './use-cash-flow';

export type SimulationScenarioType =
  | 'pay_off_early'
  | 'change_rent'
  | 'new_loan'
  | 'remove_tenant'
  | 'add_fixed_expense'
  | 'remove_fixed_expense';

export interface SimulationScenario {
  type: SimulationScenarioType;
  expense_id?: number;
  apartment_id?: number;
  new_value?: number;
  amount?: number;
  installments?: number;
  start_month?: string;
  description?: string;
}

export interface ComparisonMonth {
  year: number;
  month: number;
  base_balance: number;
  simulated_balance: number;
  delta: number;
  base_cumulative: number;
  simulated_cumulative: number;
}

export interface SimulationComparison {
  month_by_month: ComparisonMonth[];
  total_impact_12m: number;
  break_even_month: string | null;
}

export interface SimulationResult {
  base: CashFlowProjectionMonth[];
  simulated: CashFlowProjectionMonth[];
  comparison: SimulationComparison;
}

export function useSimulation() {
  return useMutation({
    mutationFn: async (scenarios: SimulationScenario[]) => {
      const { data } = await apiClient.post<SimulationResult>('/cash-flow/simulate/', {
        scenarios,
      });
      return data;
    },
  });
}
