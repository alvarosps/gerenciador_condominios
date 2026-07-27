import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useAccountStatement } from '../use-account-statement';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockAccountStatement } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useAccountStatement', () => {
  it('fetches billing-accounts/{id}/statement/ and returns account+stats+months+plans parsed', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/7/statement/`, () =>
        HttpResponse.json(createMockAccountStatement())
      )
    );

    const { result } = renderHook(() => useAccountStatement(7), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.account).toBeDefined();
    expect(result.current.data?.stats.open_balance).toBe('350.00');
    expect(result.current.data?.stats.open_bills_count).toBe(1);
    expect(result.current.data?.months.length).toBeGreaterThan(0);
    expect(result.current.data?.plans).toBeDefined();
    const month = result.current.data?.months[0];
    expect(typeof month?.amount_total).toBe('number');
  });

  it('does not fire with id null (enabled=false)', () => {
    const { result } = renderHook(() => useAccountStatement(null), { wrapper: createWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('accepts stats.avg_delay_days null (account without a paid-off bill)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/7/statement/`, () =>
        HttpResponse.json(
          createMockAccountStatement({
            stats: { open_balance: '0.00', open_bills_count: 0, avg_delay_days: null },
          })
        )
      )
    );

    const { result } = renderHook(() => useAccountStatement(7), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.stats.avg_delay_days).toBeNull();
  });

  it('propagates a 404 for a non-existent account', async () => {
    server.use(
      http.get(
        `${API_BASE}/finances/billing-accounts/999/statement/`,
        () => new HttpResponse(null, { status: 404 })
      )
    );

    const { result } = renderHook(() => useAccountStatement(999), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });

  it('is configured uncached (staleTime 0)', async () => {
    const queryClient = createTestQueryClient();
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/7/statement/`, () =>
        HttpResponse.json(createMockAccountStatement())
      )
    );

    const { result } = renderHook(() => useAccountStatement(7), {
      wrapper: createWrapper(queryClient),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const query = queryClient
      .getQueryCache()
      .find({ queryKey: ['finances', 'billing-accounts', 7, 'statement'] });
    const observerOptions = query?.observers[0]?.options;
    expect(observerOptions?.staleTime).toBe(0);
  });
});
