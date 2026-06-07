import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import {
  reserveSchema,
  type Reserve,
  type ReserveWrite,
  type DepositPayload,
  type WithdrawPayload,
} from '@/lib/schemas/finances/reserve.schema';
import { type PaginatedResponse, extractResults } from '@/lib/types/api';

export function useReserves() {
  return useQuery({
    queryKey: queryKeys.finances.reserves.list(),
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<Reserve> | Reserve[]>(
        '/finances/reserves/',
        { params: { page_size: 10000 } },
      );
      const items = extractResults(data);
      return items.map((item) => reserveSchema.parse(item));
    },
  });
}

export function useReserve(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.reserves.detail(id ?? 0),
    queryFn: async () => {
      if (!id) throw new Error('Reserve ID is required');
      const { data } = await apiClient.get<Reserve>(`/finances/reserves/${id}/`);
      return reserveSchema.parse(data);
    },
    enabled: Boolean(id),
  });
}

export function useCreateReserve() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReserveWrite) => {
      const { data } = await apiClient.post<Reserve>('/finances/reserves/', payload);
      return reserveSchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserves.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}

export function useUpdateReserve() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReserveWrite & { id: number }) => {
      const { id, ...body } = payload;
      const { data } = await apiClient.put<Reserve>(`/finances/reserves/${id}/`, body);
      return reserveSchema.parse(data);
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserves.all });
      if (data.id !== undefined) {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.finances.reserves.detail(data.id),
        });
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}

export function useDeleteReserve() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/finances/reserves/${id}/`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserves.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}

export function useDepositReserve() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { reserveId: number; payload: DepositPayload }) => {
      const { data } = await apiClient.post<Reserve>(
        `/finances/reserves/${params.reserveId}/deposit/`,
        params.payload,
      );
      return reserveSchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserves.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserveMovements.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}

export function useWithdrawReserve() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: { reserveId: number; payload: WithdrawPayload }) => {
      const { data } = await apiClient.post<Reserve>(
        `/finances/reserves/${params.reserveId}/withdraw/`,
        params.payload,
      );
      return reserveSchema.parse(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserves.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.reserveMovements.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overview.all });
    },
  });
}
