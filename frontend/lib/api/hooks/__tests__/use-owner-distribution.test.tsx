import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useOwnerDistribution } from '../use-owner-distribution';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockOwnerDistribution } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';
const BY_OWNER_URL = `${API_BASE}/finances/finance-dashboard/by_owner/`;

describe('useOwnerDistribution', () => {
  it('fetches household + external_owners, money stays string', async () => {
    const { result } = renderHook(() => useOwnerDistribution(2026, 7), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    const household = result.current.data?.household;
    expect(typeof household?.result_of_month).toBe('string');
    expect(typeof household?.carried_in).toBe('string');
    expect(typeof household?.available).toBe('string');
    expect(typeof household?.carried_out).toBe('string');
    const owner = result.current.data?.external_owners[0];
    expect(typeof owner?.owner_name).toBe('string');
    expect(typeof owner?.rent_total).toBe('string');
  });

  it('passes year/month and building_id only when provided', async () => {
    const urls: string[] = [];
    server.use(
      http.get(BY_OWNER_URL, ({ request }) => {
        urls.push(request.url);
        return HttpResponse.json(createMockOwnerDistribution());
      }),
    );
    const withBuilding = renderHook(() => useOwnerDistribution(2026, 8, 42), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(withBuilding.result.current.isSuccess).toBe(true), { timeout: 5000 });
    const withoutBuilding = renderHook(() => useOwnerDistribution(2026, 9), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(withoutBuilding.result.current.isSuccess).toBe(true), {
      timeout: 5000,
    });
    const first = new URL(urls[0] ?? '');
    expect(first.searchParams.get('year')).toBe('2026');
    expect(first.searchParams.get('month')).toBe('8');
    expect(first.searchParams.get('building_id')).toBe('42');
    const second = new URL(urls[1] ?? '');
    expect(second.searchParams.get('building_id')).toBeNull();
  });

  it('keeps previous month while a new one loads (placeholderData)', async () => {
    const { result, rerender } = renderHook(({ m }) => useOwnerDistribution(2026, m), {
      wrapper: createWrapper(),
      initialProps: { m: 7 },
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    const firstData = result.current.data;
    rerender({ m: 8 });
    expect(result.current.data).toBe(firstData);
    expect(result.current.isPlaceholderData).toBe(true);
    await waitFor(() => expect(result.current.isPlaceholderData).toBe(false), { timeout: 5000 });
  });

  it('passes a pre-tracking zeroed month through untouched (fold is backend)', async () => {
    server.use(
      http.get(BY_OWNER_URL, () =>
        HttpResponse.json(
          createMockOwnerDistribution({
            month: 5,
            household: {
              name: 'Raul & Célia',
              result_of_month: '0.00',
              carried_in: '0.00',
              available: '0.00',
              carried_out: '0.00',
            },
            external_owners: [],
            external_total: '0.00',
          }),
        ),
      ),
    );
    const { result } = renderHook(() => useOwnerDistribution(2026, 5), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.household.available).toBe('0.00');
    expect(result.current.data?.external_owners).toEqual([]);
  });

  it('surfaces a 500 as isError', async () => {
    server.use(http.get(BY_OWNER_URL, () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useOwnerDistribution(2026, 7), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
