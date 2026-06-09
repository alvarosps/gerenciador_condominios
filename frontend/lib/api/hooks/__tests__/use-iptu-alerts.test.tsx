import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useIptuAlerts } from '../use-iptu-alerts';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { queryKeys } from '@/lib/api/query-keys';
import { createMockIptuAlertRow } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useIptuAlerts', () => {
  it('fetches iptu_alerts and returns the flat {alerts, warning_count, critical_count} object', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
        HttpResponse.json({
          alerts: [createMockIptuAlertRow({ level: 'warning' })],
          warning_count: 1,
          critical_count: 0,
        }),
      ),
    );

    const { result } = renderHook(() => useIptuAlerts(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    // Flat object — NOT unwrapped to a bare array (it is not {results,count}).
    expect(Array.isArray(result.current.data)).toBe(false);
    expect(result.current.data?.alerts.length).toBe(1);
    expect(result.current.data?.warning_count).toBe(1);
    expect(result.current.data?.critical_count).toBe(0);
    expect(result.current.data?.alerts[0]?.level).toBe('warning');
  });

  it('is configured uncached (staleTime 0, refetchOnWindowFocus true)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
        HttpResponse.json({ alerts: [], warning_count: 0, critical_count: 0 }),
      ),
    );

    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useIptuAlerts(), {
      wrapper: createWrapper(queryClient),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const query = queryClient
      .getQueryCache()
      .find({ queryKey: queryKeys.finances.iptuAlerts.list() });
    const observerOptions = query?.observers[0]?.options;
    expect(observerOptions?.staleTime).toBe(0);
    expect(observerOptions?.refetchOnWindowFocus).toBe(true);
  });

  it('surfaces backend errors', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/iptu_alerts/`, () =>
        new HttpResponse(null, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useIptuAlerts(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
