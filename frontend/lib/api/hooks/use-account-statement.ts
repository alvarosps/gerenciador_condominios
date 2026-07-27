import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { accountStatementSchema } from '@/lib/schemas/finances/account-statement.schema';

/**
 * Per-account statement (S67): account + open-balance stats + month rows + installment plans.
 * Uncached on the backend — staleTime 0. Mirrors the `enabled: Boolean(id)` guard of
 * `useBillingAccount` (use-billing-accounts.ts).
 */
export function useAccountStatement(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.billingAccounts.statement(id ?? 0),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>(`/finances/billing-accounts/${id}/statement/`);
      return accountStatementSchema.parse(data); // plain object — the interceptor does not unwrap it
    },
    enabled: Boolean(id),
    staleTime: 0, // uncached on the backend (S67)
  });
}
