import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import { parseList } from '../parse-list';
import {
  type ThirdPartySettlement,
  thirdPartyPersonSchema,
  thirdPartySettlementSchema,
  thirdPartyStatementSchema,
} from '@/lib/schemas/finances/third-party.schema';

const SETTLEMENTS_ENDPOINT = '/finances/third-party-settlements/';
const PEOPLE_ENDPOINT = '/finances/third-party/people/';
const STATEMENT_ENDPOINT = '/finances/third-party/statement/';

/** Fields the API accepts on write — `person_id` (write-only) never the nested `person`. */
export interface ThirdPartySettlementWrite {
  person_id: number;
  settlement_date: string;
  amount: string;
  method?: string;
  notes?: string;
}

/**
 * Índice de terceiros: uma linha por pessoa com dívida viva (quem não deve nada é omitido pelo
 * backend). Plain array, not a DRF envelope. Uncached on the backend — it depends on `today_sp()`,
 * so `staleTime: 0` mirrors `useAccountStatement`/`useMonthBoard`.
 */
export function useThirdPartyPeople() {
  return useQuery({
    queryKey: queryKeys.finances.thirdParty.people(),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>(PEOPLE_ENDPOINT);
      return parseList(data, thirdPartyPersonSchema).items;
    },
    staleTime: 0,
  });
}

/**
 * Extrato mês a mês de uma pessoa. Plain object (not `{results,count}`) — parsed whole, so a
 * malformed payload surfaces as an error instead of a silently empty screen.
 */
export function useThirdPartyStatement(personId: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.thirdParty.statement(personId ?? 0),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>(STATEMENT_ENDPOINT, {
        params: { person_id: personId },
      });
      return thirdPartyStatementSchema.parse(data);
    },
    enabled: Boolean(personId),
    staleTime: 0,
  });
}

export function useThirdPartySettlements(personId?: number) {
  const filters = personId === undefined ? undefined : { person_id: personId };
  return useQuery({
    queryKey: queryKeys.finances.thirdParty.settlements(filters),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>(SETTLEMENTS_ENDPOINT, {
        params: { ...filters, page_size: 10000 },
      });
      return parseList(data, thirdPartySettlementSchema).items;
    },
  });
}

/**
 * A settlement changes BOTH the person's live debt (índice) and her month-by-month allocation
 * (extrato) — the FIFO allocation is recomputed at every read and never persisted, so failing to
 * invalidate `statement` alongside `people` leaves the extrato showing pre-acerto numbers.
 * Invalidating the shared `thirdParty.all` prefix would also work, but naming both keys keeps the
 * requirement explicit and survives a future key reshuffle.
 */
function useInvalidateThirdParty() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.finances.thirdParty.people() });
    void queryClient.invalidateQueries({
      queryKey: [...queryKeys.finances.thirdParty.all, 'statement'],
    });
    void queryClient.invalidateQueries({
      queryKey: [...queryKeys.finances.thirdParty.all, 'settlements'],
    });
  };
}

export function useCreateThirdPartySettlement() {
  const invalidate = useInvalidateThirdParty();
  return useMutation({
    mutationFn: async (data: ThirdPartySettlementWrite) => {
      const { data: created } = await apiClient.post<unknown>(SETTLEMENTS_ENDPOINT, data);
      return thirdPartySettlementSchema.parse(created);
    },
    onSuccess: invalidate,
  });
}

export function useUpdateThirdPartySettlement() {
  const invalidate = useInvalidateThirdParty();
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: Partial<ThirdPartySettlementWrite> & { id: number }): Promise<ThirdPartySettlement> => {
      const { data: updated } = await apiClient.patch<unknown>(
        `${SETTLEMENTS_ENDPOINT}${String(id)}/`,
        data
      );
      return thirdPartySettlementSchema.parse(updated);
    },
    onSuccess: invalidate,
  });
}

export function useDeleteThirdPartySettlement() {
  const invalidate = useInvalidateThirdParty();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`${SETTLEMENTS_ENDPOINT}${String(id)}/`);
    },
    onSuccess: invalidate,
  });
}
