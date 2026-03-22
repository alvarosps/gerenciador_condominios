import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../client';

export interface SimulationScenario {
  name: string;
  [key: string]: unknown;
}

export interface SimulationResultMonth {
  year: number;
  month: number;
  projected_income: number;
  projected_expenses: number;
  projected_balance: number;
}

export interface SimulationScenarioResult {
  scenario_name: string;
  months: SimulationResultMonth[];
}

export interface SimulationResult {
  results: SimulationScenarioResult[];
}

export function useSimulation() {
  return useMutation({
    mutationFn: async (scenarios: SimulationScenario[]) => {
      const { data } = await apiClient.post<SimulationResult>('/cash-flow/simulate/', { scenarios });
      return data;
    },
  });
}
