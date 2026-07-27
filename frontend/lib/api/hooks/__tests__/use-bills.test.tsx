import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useQuery } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import {
  useCancelBill,
  useCreateBillWithLines,
  useDeferBill,
  useDeleteBill,
  useGenerateMonthBills,
  usePayBill,
  useReactivateBill,
  useSuspendBill,
  useUpdateBill,
} from '../use-bills';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { queryKeys } from '@/lib/api/query-keys';
import { createMockBill } from '@/tests/mocks/data/finances';

/** Minimal probe query kept under the bills prefix so `gcTime: 0` (test QueryClient) doesn't
 *  purge the seeded cache entry between `setQueryData` and the assertion — mirrors having a real
 *  list subscriber mounted, without depending on the removed `useBills` hook. Never refetches on
 *  its own (`enabled: false`): the test controls exactly when the cache value changes. */
function useBillsProbe(queryKey: readonly unknown[]) {
  return useQuery<{ payment_status: string }[]>({
    queryKey,
    queryFn: () => Promise.resolve([]),
    enabled: false,
  });
}

const API_BASE = 'http://localhost:8008/api';

describe('bill mutations', () => {
  it('creates a bill with line items and invalidates caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateBillWithLines(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      bill: {
        competence_month: '2026-06-01',
        due_date: '2026-06-10',
        description: 'Conta de Luz',
        behavior: 'one_time',
        lifecycle_state: 'active',
      },
      line_items: [{ description: 'Energia', amount: 350 }],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
  });

  it('updates a bill via PATCH, stripping nested read-only objects', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(`${API_BASE}/finances/bills/:id/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: 1, ...sentBody });
      })
    );

    const { result } = renderHook(() => useUpdateBill(), { wrapper: createWrapper() });

    result.current.mutate({
      id: 1,
      description: 'Conta revisada',
      condominium: { id: 1, name: 'Condomínio' },
      building: null,
      category: null,
      billing_account: null,
      line_items: [],
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(sentBody).not.toBeNull();
    expect(sentBody).toHaveProperty('description', 'Conta revisada');
    expect(sentBody).not.toHaveProperty('condominium');
    expect(sentBody).not.toHaveProperty('building');
    expect(sentBody).not.toHaveProperty('category');
    expect(sentBody).not.toHaveProperty('billing_account');
    expect(sentBody).not.toHaveProperty('line_items');
  });

  it('deletes a bill', async () => {
    const { result } = renderHook(() => useDeleteBill(), { wrapper: createWrapper() });
    result.current.mutate(1);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
  });

  it('generates the bills for a month and invalidates caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useGenerateMonthBills(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ year: 2026, month: 7 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.created).toBe(1);
    expect(result.current.data?.bills?.[0]?.competence_month).toBe('2026-07-01');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
  });
});

describe('bill lifecycle actions', () => {
  it('suspends a bill and invalidates caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useSuspendBill(), { wrapper: createWrapper(queryClient) });

    result.current.mutate(1);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.lifecycle_state).toBe('suspended');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
  });

  it('defers, cancels and reactivates a bill', async () => {
    const { result: defer } = renderHook(() => useDeferBill(), { wrapper: createWrapper() });
    defer.current.mutate(1);
    await waitFor(() => expect(defer.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(defer.current.data?.lifecycle_state).toBe('deferred');

    const { result: cancel } = renderHook(() => useCancelBill(), { wrapper: createWrapper() });
    cancel.current.mutate(1);
    await waitFor(() => expect(cancel.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(cancel.current.data?.lifecycle_state).toBe('canceled');

    const { result: reactivate } = renderHook(() => useReactivateBill(), {
      wrapper: createWrapper(),
    });
    reactivate.current.mutate(1);
    await waitFor(() => expect(reactivate.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(reactivate.current.data?.lifecycle_state).toBe('active');
  });
});

describe('usePayBill (no optimistic update)', () => {
  it('does not touch the cached bill list while the mutation is in flight (any path)', async () => {
    const queryClient = createTestQueryClient();
    // Seed the cache directly under the bills prefix — invalidateBillCaches invalidates
    // queryKeys.finances.bills.all, so any query keyed under that prefix is a valid probe.
    const billsQueryKey = [...queryKeys.finances.bills.all, 'probe'];

    let respond: (() => void) | undefined;
    const serverReady = new Promise<void>((resolve) => {
      respond = resolve;
    });
    server.use(
      http.post(`${API_BASE}/finances/bills/1/pay/`, async () => {
        await serverReady;
        return HttpResponse.json(
          createMockBill({ id: 1, payment_status: 'paid', amount_remaining: 0 })
        );
      })
    );

    const { result } = renderHook(
      () => ({ probe: useBillsProbe(billsQueryKey), pay: usePayBill() }),
      { wrapper: createWrapper(queryClient) }
    );
    // enabled:false never fetches — populate the cache the probe observes directly.
    queryClient.setQueryData(billsQueryKey, [
      { ...createMockBill({ id: 1, payment_status: 'open', amount_remaining: 350 }) },
    ]);

    result.current.pay.mutate({ bill_id: 1, payment_date: '2026-06-10' });

    // Pre-populated cache stays intact throughout the in-flight window — onMutate was removed.
    await waitFor(() => expect(result.current.pay.isPending).toBe(true), { timeout: 5000 });
    const inFlightBills = queryClient.getQueryData<{ payment_status: string }[]>(billsQueryKey);
    expect(inFlightBills?.[0]?.payment_status).toBe('open');
    respond?.();

    await waitFor(() => expect(result.current.pay.isSuccess).toBe(true), { timeout: 5000 });

    // The mutation invalidates the bills prefix — no manual write ever touches the probe entry,
    // it only gets marked stale (an `enabled: false` observer never auto-refetches, so the
    // pre-populated value itself stays untouched — same assertion the removed useBills made).
    expect(queryClient.getQueryState(billsQueryKey)?.isInvalidated).toBe(true);
  });

  it('does not roll back anything on error (there is nothing to restore — same asserto as the partial-amount path)', async () => {
    const queryClient = createTestQueryClient();
    const billsQueryKey = [...queryKeys.finances.bills.all, 'probe'];

    const { result } = renderHook(
      () => ({ probe: useBillsProbe(billsQueryKey), pay: usePayBill() }),
      { wrapper: createWrapper(queryClient) }
    );
    queryClient.setQueryData(billsQueryKey, [
      { ...createMockBill({ id: 1, payment_status: 'open', amount_remaining: 350 }) },
    ]);

    server.use(
      http.post(`${API_BASE}/finances/bills/1/pay/`, () => new HttpResponse(null, { status: 500 }))
    );

    result.current.pay.mutate({ bill_id: 1, payment_date: '2026-06-10' });

    await waitFor(() => expect(result.current.pay.isError).toBe(true), { timeout: 5000 });

    const bills = queryClient.getQueryData<{ payment_status: string }[]>(billsQueryKey);
    expect(bills?.[0]?.payment_status).toBe('open');
  });

  it('sends new_total as a decimal string in the body when informed', async () => {
    let captured: Record<string, unknown> = {};
    server.use(
      http.post(`${API_BASE}/finances/bills/1/pay/`, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockBill({ id: 1, payment_status: 'paid' }));
      })
    );

    const { result } = renderHook(() => usePayBill(), { wrapper: createWrapper() });

    result.current.mutate({
      bill_id: 1,
      payment_date: '2026-06-10',
      funded_from: 'caixa',
      new_total: '230.00',
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(captured).toEqual({
      payment_date: '2026-06-10',
      funded_from: 'caixa',
      new_total: '230.00',
    });
  });

  it('omits new_total from the body when not informed (current payload untouched)', async () => {
    let captured: Record<string, unknown> = {};
    server.use(
      http.post(`${API_BASE}/finances/bills/1/pay/`, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockBill({ id: 1, payment_status: 'paid' }));
      })
    );

    const { result } = renderHook(() => usePayBill(), { wrapper: createWrapper() });

    result.current.mutate({ bill_id: 1, payment_date: '2026-06-10', funded_from: 'reserve' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(captured).not.toHaveProperty('new_total');
    expect(captured.funded_from).toBe('reserve');
    expect(captured.payment_date).toBe('2026-06-10');
  });

  it('invalidates bills, combined-calendar, overdue, monthBoard and billingAccounts caches on success', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => usePayBill(), { wrapper: createWrapper(queryClient) });

    result.current.mutate({ bill_id: 1, payment_date: '2026-06-10' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'month-board'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
  });
});
