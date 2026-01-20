import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';

/**
 * Contract Rule type from the API
 */
export interface ContractRule {
  id: number;
  content: string;
  order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Input type for creating/updating a rule
 */
export interface ContractRuleInput {
  content: string;
  order?: number;
  is_active?: boolean;
}

/**
 * Paginated response from DRF
 */
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Get all contract rules
 */
export function useContractRules(activeOnly: boolean = false) {
  return useQuery({
    queryKey: ['contract-rules', { activeOnly }],
    queryFn: async () => {
      const params = activeOnly ? { is_active: 'true' } : {};
      const { data } = await apiClient.get<PaginatedResponse<ContractRule> | ContractRule[]>('/rules/', { params });
      // Handle both paginated and non-paginated responses
      if (Array.isArray(data)) {
        return data;
      }
      return data.results;
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}

/**
 * Get a single contract rule by ID
 */
export function useContractRule(id: number) {
  return useQuery({
    queryKey: ['contract-rules', id],
    queryFn: async () => {
      const { data } = await apiClient.get<ContractRule>(`/rules/${id}/`);
      return data;
    },
    enabled: !!id,
  });
}

/**
 * Create a new contract rule
 */
export function useCreateContractRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: ContractRuleInput) => {
      const { data } = await apiClient.post<ContractRule>('/rules/', input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-rules'] });
    },
  });
}

/**
 * Update an existing contract rule
 */
export function useUpdateContractRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, ...input }: ContractRuleInput & { id: number }) => {
      const { data } = await apiClient.patch<ContractRule>(`/rules/${id}/`, input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-rules'] });
    },
  });
}

/**
 * Delete a contract rule (soft delete)
 */
export function useDeleteContractRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/rules/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-rules'] });
    },
  });
}

/**
 * Reorder contract rules
 */
export function useReorderContractRules() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (ruleIds: number[]) => {
      const { data } = await apiClient.post<{ message: string }>('/rules/reorder/', {
        rule_ids: ruleIds,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-rules'] });
    },
  });
}

/**
 * Toggle rule active status
 */
export function useToggleContractRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      const { data } = await apiClient.patch<ContractRule>(`/rules/${id}/`, { is_active });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-rules'] });
    },
  });
}
