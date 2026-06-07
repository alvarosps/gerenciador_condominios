import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useBillSkips, useCreateBillSkip, useDeleteBillSkip } from '../use-bill-skips';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useBillSkips', () => {
  it('fetches the bill-skip list', async () => {
    const { result } = renderHook(() => useBillSkips(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.length).toBeGreaterThan(0);
    expect(result.current.data?.[0]?.reference_month).toBeDefined();
  });

  it('forwards filters as query params', async () => {
    let captured: Record<string, string> = {};
    server.use(
      http.get(`${API_BASE}/finances/bill-skips/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        captured = {
          billing_account_id: params.get('billing_account_id') ?? '',
          reference_month: params.get('reference_month') ?? '',
        };
        return HttpResponse.json([]);
      }),
    );

    const { result } = renderHook(
      () => useBillSkips({ billing_account_id: 3, reference_month: '2026-06-01' }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(captured.billing_account_id).toBe('3');
    expect(captured.reference_month).toBe('2026-06-01');
  });
});

describe('bill-skip mutations', () => {
  it('creates a bill skip and invalidates the combined calendar (§18)', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateBillSkip(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({ billing_account_id: 1, reference_month: '2026-07-01' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bill-skips'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
  });

  it('deletes a bill skip (un-skips) and invalidates the combined calendar', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useDeleteBillSkip(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bill-skips'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
  });
});
