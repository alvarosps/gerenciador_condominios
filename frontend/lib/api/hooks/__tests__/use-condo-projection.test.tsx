import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useCondoProjection, useCondoSimulation } from '../use-condo-projection';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockCondoProjection, createMockCondoSimulation } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';
const PROJECTION_URL = `${API_BASE}/finances/finance-cash-flow/projection/`;
const SIMULATE_URL = `${API_BASE}/finances/finance-cash-flow/simulate/`;

describe('useCondoProjection', () => {
  it('fetches 12 months keeping money as string + is_actual bool', async () => {
    const { result } = renderHook(() => useCondoProjection(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data).toHaveLength(12);
    const first = result.current.data?.[0];
    expect(typeof first?.income_total).toBe('string');
    expect(typeof first?.expenses_total).toBe('string');
    expect(typeof first?.net).toBe('string');
    expect(typeof first?.cumulative_cash).toBe('string');
    expect(typeof first?.is_actual).toBe('boolean');
  });

  it('passes months as a query param', async () => {
    let capturedUrl = '';
    server.use(
      http.get(PROJECTION_URL, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(createMockCondoProjection(24));
      }),
    );
    const { result } = renderHook(() => useCondoProjection(24), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(new URL(capturedUrl).searchParams.get('months')).toBe('24');
  });

  it('keeps previous data while a new horizon loads (placeholderData)', async () => {
    const { result, rerender } = renderHook(({ m }) => useCondoProjection(m), {
      wrapper: createWrapper(),
      initialProps: { m: 12 },
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    const firstData = result.current.data;
    expect(firstData).toHaveLength(12);

    rerender({ m: 24 });
    // keepPreviousData: data is the previous result (not undefined) while the new one loads
    expect(result.current.data).toBe(firstData);
    expect(result.current.isPlaceholderData).toBe(true);

    await waitFor(() => expect(result.current.isPlaceholderData).toBe(false), { timeout: 5000 });
    expect(result.current.data).toHaveLength(24);
  });

  it('passes through a pre-tracking zero-revenue month untouched (fold is backend)', async () => {
    server.use(
      http.get(PROJECTION_URL, () =>
        HttpResponse.json([
          {
            year: 2026,
            month: 5,
            income_total: '0.00',
            expenses_total: '300.00',
            net: '-300.00',
            cumulative_cash: '-300.00',
            is_actual: false,
            is_closed: false,
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useCondoProjection(1), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.[0]?.income_total).toBe('0.00');
  });

  it('surfaces a 500 as isError', async () => {
    server.use(http.get(PROJECTION_URL, () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useCondoProjection(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useCondoSimulation', () => {
  it('POSTs scenarios in the body and returns base/simulated/comparison', async () => {
    let capturedBody: { scenarios?: unknown[] } = {};
    server.use(
      http.post(SIMULATE_URL, async ({ request }) => {
        capturedBody = (await request.json()) as { scenarios?: unknown[] };
        return HttpResponse.json(createMockCondoSimulation(12));
      }),
    );
    const { result } = renderHook(() => useCondoSimulation(), { wrapper: createWrapper() });
    result.current.mutate({ scenarios: [{ type: 'add_expense', amount: '100.00' }], months: 12 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(capturedBody.scenarios).toHaveLength(1);
    expect(result.current.data?.base).toBeDefined();
    expect(result.current.data?.simulated).toBeDefined();
    expect(result.current.data?.comparison.months).toBeDefined();
  });

  it('accepts an empty scenario list (base == simulated)', async () => {
    const { result } = renderHook(() => useCondoSimulation(), { wrapper: createWrapper() });
    result.current.mutate({ scenarios: [] });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.comparison.months.length).toBeGreaterThan(0);
  });

  it('surfaces a 500 as mutation.isError', async () => {
    server.use(http.post(SIMULATE_URL, () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useCondoSimulation(), { wrapper: createWrapper() });
    result.current.mutate({ scenarios: [{ type: 'add_income', amount: '50.00' }] });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
