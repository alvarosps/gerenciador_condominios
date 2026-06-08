import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { useCombinedCalendar, useOverdueBills } from '../use-combined-calendar';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import {
  createMockBill,
  createMockCombinedCalendar,
  createMockOverdueResponse,
} from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useCombinedCalendar', () => {
  it('fetches the combined calendar for a given year/month', async () => {
    const { result } = renderHook(() => useCombinedCalendar(2026, 6), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.year).toBe(2026);
    expect(result.current.data?.month).toBe(6);
    expect(result.current.data?.today).toBeDefined();
    const exit = result.current.data?.days?.[0]?.bill_exits?.[0];
    expect(exit?.bill_id).toBeDefined();
    // Dashboard money stays a string (no client transform on calendar reads).
    expect(exit?.amount_remaining).toBe('350.00');
    expect(result.current.data?.days?.[0]?.rent_entries).toBeDefined();
  });

  it('forwards building_id to the query string when provided', async () => {
    let captured: string | null = null;
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/combined_calendar/`, ({ request }) => {
        captured = new URL(request.url).searchParams.get('building_id');
        return HttpResponse.json(createMockCombinedCalendar());
      }),
    );

    const { result } = renderHook(() => useCombinedCalendar(2026, 6, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(captured).toBe('3');
  });

  it('keeps the previous month data while the next month loads (placeholderData)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/combined_calendar/`, async ({ request }) => {
        const month = Number(new URL(request.url).searchParams.get('month') ?? '6');
        await delay(50);
        return HttpResponse.json(createMockCombinedCalendar({ month }));
      }),
    );

    const { result, rerender } = renderHook(
      ({ month }: { month: number }) => useCombinedCalendar(2026, month),
      { wrapper: createWrapper(), initialProps: { month: 6 } },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.month).toBe(6);

    // Navigating to July must not drop back to undefined — June stays as placeholder.
    rerender({ month: 7 });
    expect(result.current.data?.month).toBe(6);
    expect(result.current.isPlaceholderData).toBe(true);

    await waitFor(() => expect(result.current.data?.month).toBe(7), { timeout: 5000 });
    expect(result.current.isPlaceholderData).toBe(false);
  });

  it('surfaces server errors', async () => {
    server.use(
      http.get(
        `${API_BASE}/finances/finance-dashboard/combined_calendar/`,
        () => new HttpResponse(null, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useCombinedCalendar(2026, 6), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useOverdueBills', () => {
  it('fetches overdue bills with the KPI totals', async () => {
    const { result } = renderHook(() => useOverdueBills(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.overdue_bills_count).toBe(1);
    expect(result.current.data?.overdue_bills_total).toBe('350.00');
    expect(result.current.data?.rent_overdue).toBeDefined();
    expect(result.current.data?.bills?.[0]?.is_overdue).toBe(true);
    // §4.4: only active+overdue bills appear — deferred/suspended are filtered out by the backend.
    expect(result.current.data?.bills?.every((bill) => bill.lifecycle_state === 'active')).toBe(true);
  });

  it('KPI total reconciles with the sum of amount_remaining of returned bills', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/overdue/`, () =>
        HttpResponse.json(
          createMockOverdueResponse({
            bills: [
              createMockBill({ id: 1, amount_remaining: 100, is_overdue: true }),
              createMockBill({ id: 2, amount_remaining: 250, is_overdue: true }),
            ],
            overdue_bills_total: '350.00',
            overdue_bills_count: 2,
          }),
        ),
      ),
    );

    const { result } = renderHook(() => useOverdueBills(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const sum = (result.current.data?.bills ?? []).reduce(
      (acc, bill) => acc + (bill.amount_remaining ?? 0),
      0,
    );
    expect(sum).toBe(Number(result.current.data?.overdue_bills_total));
  });

  it('forwards building_id when provided', async () => {
    let captured: string | null = null;
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/overdue/`, ({ request }) => {
        captured = new URL(request.url).searchParams.get('building_id');
        return HttpResponse.json(createMockOverdueResponse());
      }),
    );

    const { result } = renderHook(() => useOverdueBills(5), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(captured).toBe('5');
  });
});
