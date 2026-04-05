import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useMonthlyCashFlow, useCashFlowProjection, usePersonSummary } from '../use-cash-flow';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useMonthlyCashFlow', () => {
  it('should fetch monthly data', async () => {
    const { result } = renderHook(() => useMonthlyCashFlow(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(result.current.data?.year).toBe(2026);
    expect(result.current.data?.month).toBe(3);
    expect(result.current.data?.income.total).toBe(12000.0);
    expect(result.current.data?.expenses.total).toBe(5200.0);
    expect(result.current.data?.balance).toBe(6800.0);
  });

  it('should include rent details in income', async () => {
    const { result } = renderHook(() => useMonthlyCashFlow(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.income.rent_details).toHaveLength(1);
    expect(result.current.data?.income.rent_income).toBe(10000);
  });

  it('should handle error from server', async () => {
    server.use(
      http.get(`${API_BASE}/cash-flow/monthly/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useMonthlyCashFlow(2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useCashFlowProjection', () => {
  it('should fetch projection', async () => {
    const { result } = renderHook(() => useCashFlowProjection({ months: 3 }), {
      wrapper: createWrapper(),
    });

    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true);
      },
      { timeout: 5000 },
    );

    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
    const firstMonth = result.current.data?.[0];
    expect(firstMonth?.income_total).toBeDefined();
    expect(firstMonth?.expenses_total).toBeDefined();
  });

  it('should fetch projection without months parameter', async () => {
    const { result } = renderHook(() => useCashFlowProjection(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('should include is_projected flag in each month', async () => {
    const { result } = renderHook(() => useCashFlowProjection({ months: 3 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    result.current.data?.forEach((month) => {
      expect(month).toHaveProperty('is_projected');
      expect(month).toHaveProperty('cumulative_balance');
    });
  });
});

describe('usePersonSummary', () => {
  it('should fetch person summary for given person and month', async () => {
    const { result } = renderHook(() => usePersonSummary(1, 2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.person_name).toBeDefined();
    expect(result.current.data?.net_amount).toBeDefined();
    expect(result.current.data?.pending_balance).toBeDefined();
  });

  it('should not fetch when personId is 0', () => {
    const { result } = renderHook(() => usePersonSummary(0, 2026, 3), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it('should handle error from server', async () => {
    server.use(
      http.get(`${API_BASE}/cash-flow/person_summary/`, () => {
        return new HttpResponse(null, { status: 500 });
      }),
    );

    const { result } = renderHook(() => usePersonSummary(1, 2026, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
