import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useBill,
  useBills,
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
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { queryKeys } from '@/lib/api/query-keys';
import { createMockBill } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useBills', () => {
  it('fetches the bill list and parses money annotations to numbers', async () => {
    const { result } = renderHook(() => useBills(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.length).toBeGreaterThan(0);
    const bill = result.current.data?.[0];
    expect(bill?.amount_total).toBe(350);
    expect(bill?.amount_remaining).toBe(350);
    expect(bill?.payment_status).toBe('open');
  });

  it('parses string Decimal annotations to number without recalculating amount_total (§4.1)', async () => {
    // amount_total is an annotation the front must READ verbatim, never recompute from lines.
    // The lines deliberately do not sum to amount_total, proving the value comes from the field.
    server.use(
      http.get(`${API_BASE}/finances/bills/`, () =>
        // Raw API shape: money fields are string Decimals the schema transforms to number.
        HttpResponse.json([
          {
            ...createMockBill({ id: 1 }),
            amount_total: '123.45',
            amount_paid: '0.00',
            amount_remaining: '123.45',
            line_items: [
              { id: 1, description: 'A', amount: '600.00', is_offset: false },
              { id: 2, description: 'B', amount: '400.00', is_offset: false },
              { id: 3, description: 'Desconto', amount: '100.00', is_offset: true },
            ],
          },
        ])
      )
    );

    const { result } = renderHook(() => useBills(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const bill = result.current.data?.[0];
    expect(typeof bill?.amount_total).toBe('number');
    expect(typeof bill?.amount_remaining).toBe('number');
    expect(bill?.amount_total).toBe(123.45); // the annotation, not 600 + 400 - 100
    expect(typeof bill?.line_items?.[0]?.amount).toBe('number');
    expect(bill?.line_items?.[2]?.is_offset).toBe(true);
  });

  it('forwards filters as query params', async () => {
    let captured: Record<string, string> = {};
    server.use(
      http.get(`${API_BASE}/finances/bills/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        captured = {
          building_id: params.get('building_id') ?? '',
          competence_month: params.get('competence_month') ?? '',
          lifecycle_state: params.get('lifecycle_state') ?? '',
        };
        return HttpResponse.json([]);
      })
    );

    const { result } = renderHook(
      () => useBills({ building_id: 4, competence_month: '2026-06-01', lifecycle_state: 'active' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(captured.building_id).toBe('4');
    expect(captured.competence_month).toBe('2026-06-01');
    expect(captured.lifecycle_state).toBe('active');
  });

  it('surfaces server errors', async () => {
    server.use(
      http.get(`${API_BASE}/finances/bills/`, () => new HttpResponse(null, { status: 500 }))
    );

    const { result } = renderHook(() => useBills(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });

  it('defaults amount_is_estimated to false on an old payload without the field (S65/S71)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/bills/`, () => {
        const { amount_is_estimated: _amount_is_estimated, ...rest } = createMockBill();
        return HttpResponse.json([rest]);
      })
    );

    const { result } = renderHook(() => useBills(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.[0]?.amount_is_estimated).toBe(false);
  });

  it('fetches a single bill with nested line_items / stays idle when id is null', async () => {
    const { result } = renderHook(() => useBill(1), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.id).toBe(1);
    expect(result.current.data?.line_items?.length).toBeGreaterThan(0);
    expect(result.current.data?.line_items?.[0]?.is_offset).toBe(false);
    expect(typeof result.current.data?.line_items?.[0]?.amount).toBe('number');

    const { result: idle } = renderHook(() => useBill(null), { wrapper: createWrapper() });
    expect(idle.current.fetchStatus).toBe('idle');
  });
});

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

  it('updates a bill, stripping nested read-only objects', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.put(`${API_BASE}/finances/bills/:id/`, async ({ request }) => {
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

    let getCount = 0;
    server.use(
      http.get(`${API_BASE}/finances/bills/`, () => {
        getCount += 1;
        // 2nd GET is the post-invalidate refetch — reflects the payment server-side.
        const paid = getCount > 1;
        return HttpResponse.json([
          createMockBill({
            id: 1,
            payment_status: paid ? 'paid' : 'open',
            amount_remaining: paid ? 0 : 350,
          }),
        ]);
      })
    );

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

    const { result } = renderHook(() => ({ bills: useBills(), pay: usePayBill() }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.bills.isSuccess).toBe(true), { timeout: 5000 });

    result.current.pay.mutate({ bill_id: 1, payment_date: '2026-06-10' });

    // Pre-populated cache stays intact throughout the in-flight window — onMutate was removed.
    await waitFor(() => expect(result.current.pay.isPending).toBe(true), { timeout: 5000 });
    const inFlightBills = queryClient.getQueryData<Bill[]>(queryKeys.finances.bills.list({}));
    expect(inFlightBills?.[0]?.payment_status).toBe('open');
    respond?.();

    await waitFor(() => expect(result.current.pay.isSuccess).toBe(true), { timeout: 5000 });

    // Only AFTER the response + invalidate→refetch does the cache reflect the paid status.
    await waitFor(() => {
      const bills = queryClient.getQueryData<Bill[]>(queryKeys.finances.bills.list({}));
      expect(bills?.[0]?.payment_status).toBe('paid');
    });
  });

  it('does not roll back anything on error (there is nothing to restore — same asserto as the partial-amount path)', async () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => ({ bills: useBills(), pay: usePayBill() }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.bills.isSuccess).toBe(true), { timeout: 5000 });

    server.use(
      http.post(`${API_BASE}/finances/bills/1/pay/`, () => new HttpResponse(null, { status: 500 }))
    );

    result.current.pay.mutate({ bill_id: 1, payment_date: '2026-06-10' });

    await waitFor(() => expect(result.current.pay.isError).toBe(true), { timeout: 5000 });

    const bills = queryClient.getQueryData<Bill[]>(queryKeys.finances.bills.list({}));
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
