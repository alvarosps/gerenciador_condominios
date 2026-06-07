import { describe, it, expect } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useCondoMonthCloses,
  useCloseMonth,
  useReopenMonth,
} from '../use-condo-month-closes';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useCondoMonthCloses', () => {
  it('fetches list of month closes', async () => {
    const { result } = renderHook(() => useCondoMonthCloses(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
  });

  it('parses money fields as numbers', async () => {
    server.use(
      http.get(`${API_BASE}/finances/condo-month-closes/`, () =>
        HttpResponse.json([
          {
            id: 1,
            condominium: { id: 1, name: 'C' },
            reference_month: '2026-05-01',
            status: 'closed',
            closed_at: '2026-06-01T00:00:00Z',
            net_result: '2000.00',
            cash_balance_end: '15000.00',
            reserve_balance_end: '5000.00',
            carry_forward_out: '0.00',
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useCondoMonthCloses(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    const close = result.current.data?.[0];
    expect(typeof close?.net_result).toBe('number');
    expect(close?.net_result).toBe(2000);
    expect(close?.cash_balance_end).toBe(15000);
  });

  it('handles server error', async () => {
    server.use(
      http.get(`${API_BASE}/finances/condo-month-closes/`, () =>
        new HttpResponse(null, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useCondoMonthCloses(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useCloseMonth', () => {
  it('closes a month successfully', async () => {
    const { result } = renderHook(() => useCloseMonth(), { wrapper: createWrapper() });
    let closed: unknown;
    await act(async () => {
      closed = await result.current.mutateAsync({ year: 2026, month: 5 });
    });
    expect(closed).toBeDefined();
  });

  it('handles already-closed error (400)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/condo-month-closes/close/`, () =>
        HttpResponse.json({ error: 'Mês já foi fechado' }, { status: 400 }),
      ),
    );
    const { result } = renderHook(() => useCloseMonth(), { wrapper: createWrapper() });
    await act(async () => {
      try {
        await result.current.mutateAsync({ year: 2026, month: 5 });
      } catch {
        // expected
      }
    });
    expect(result.current.isError).toBe(true);
  });
});

describe('useReopenMonth', () => {
  it('reopens a closed month', async () => {
    const { result } = renderHook(() => useReopenMonth(), { wrapper: createWrapper() });
    let reopened: unknown;
    await act(async () => {
      reopened = await result.current.mutateAsync({ year: 2026, month: 5 });
    });
    expect(reopened).toBeDefined();
  });
});
