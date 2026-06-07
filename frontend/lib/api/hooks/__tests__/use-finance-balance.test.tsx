import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useFinanceOverview, useMonthlyBalance, useByCategory } from '../use-finance-balance';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useFinanceOverview', () => {
  it('fetches overview and keeps money as string', async () => {
    const { result } = renderHook(() => useFinanceOverview(2026, 6), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    // money stays STRING — FE never recomputes KPIs
    expect(typeof result.current.data?.cash_balance).toBe('string');
    expect(typeof result.current.data?.total_balance).toBe('string');
    expect(typeof result.current.data?.reserve_balance).toBe('string');
  });

  it('passes year and month as query params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/overview/`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          year: 2026, month: 3, result_of_month: '0', cash_change_of_month: '0',
          cash_balance: '0', reserve_balance: '0', total_balance: '0',
          overdue_bills_total: '0', overdue_bills_count: 0,
          rent_overdue: { count: 0, total_fee: '0' }, wedge_ok: true,
        });
      }),
    );
    const { result } = renderHook(() => useFinanceOverview(2026, 3), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(capturedUrl).toContain('year=2026');
    expect(capturedUrl).toContain('month=3');
  });

  it('passes building_id when provided', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/finances/finance-dashboard/overview/`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          year: 2026, month: 6, result_of_month: '0', cash_change_of_month: '0',
          cash_balance: '0', reserve_balance: '0', total_balance: '0',
          overdue_bills_total: '0', overdue_bills_count: 0,
          rent_overdue: { count: 0, total_fee: '0' }, wedge_ok: true,
        });
      }),
    );
    const { result } = renderHook(() => useFinanceOverview(2026, 6, 42), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(capturedUrl).toContain('building_id=42');
  });
});

describe('useMonthlyBalance', () => {
  it('fetches monthly balance with 12 months', async () => {
    const { result } = renderHook(() => useMonthlyBalance(2026), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.months).toHaveLength(12);
    // money stays STRING
    expect(typeof result.current.data?.months[0]?.total_balance).toBe('string');
  });
});

describe('useByCategory', () => {
  it('fetches by_category data — field is `total` not `amount`', async () => {
    const { result } = renderHook(() => useByCategory(2026, 6), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    const cat = result.current.data?.categories[0];
    expect(cat).toBeDefined();
    // The money field from the API is `total` — not `amount`
    expect('total' in (cat ?? {})).toBe(true);
    expect(typeof cat?.total).toBe('string');
  });
});
