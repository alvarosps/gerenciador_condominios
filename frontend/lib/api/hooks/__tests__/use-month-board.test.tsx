import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useMonthBoard } from '../use-month-board';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill, createMockMonthBoard } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useMonthBoard', () => {
  it('fetches month_board with year/month in the params and returns the parsed plain object', async () => {
    let captured: { year: string | null; month: string | null } = { year: null, month: null };
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        captured = { year: params.get('year'), month: params.get('month') };
        return HttpResponse.json(createMockMonthBoard());
      })
    );

    const { result } = renderHook(() => useMonthBoard(2026, 7), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(captured.year).toBe('2026');
    expect(captured.month).toBe('7');
    expect(result.current.data?.overdue).toBeDefined();
    expect(result.current.data?.groups).toBeDefined();
    expect(result.current.data?.totals).toBeDefined();
    expect(result.current.data?.generation).toBeDefined();
  });

  it('parses bills in every section via billSchema (amount_is_estimated present, money coerced)', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () =>
        HttpResponse.json(
          createMockMonthBoard({
            groups: [
              {
                building_id: 1,
                building_label: 'Prédio 836',
                bills: [
                  createMockBill({ id: 42, amount_is_estimated: true, amount_total: '350.00' }),
                ],
              },
            ],
          })
        )
      )
    );

    const { result } = renderHook(() => useMonthBoard(2026, 7), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const bill = result.current.data?.groups?.[0]?.bills?.[0];
    expect(bill?.amount_is_estimated).toBe(true);
    expect(typeof bill?.amount_total).toBe('number');
    expect(bill?.amount_total).toBe(350);
  });

  it('is configured uncached (staleTime 0) with keepPreviousData', async () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useMonthBoard(2026, 7), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const query = queryClient
      .getQueryCache()
      .find({ queryKey: ['finances', 'month-board', 'month', 2026, 7] });
    const observerOptions = query?.observers[0]?.options;
    expect(observerOptions?.staleTime).toBe(0);
    expect(observerOptions?.placeholderData).toBeDefined();
  });

  it('propagates a 400 error for invalid year/month', async () => {
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/month_board/`, () =>
        HttpResponse.json({ detail: 'Mês inválido.' }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useMonthBoard(2026, 13), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
