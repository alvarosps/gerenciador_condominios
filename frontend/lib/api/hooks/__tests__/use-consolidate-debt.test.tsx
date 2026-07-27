import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useConsolidateDebt } from '../use-billing-accounts';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockInstallmentPlan } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useConsolidateDebt', () => {
  it('posts the {bill_ids, embedded, installment_count, start_due_date, default_due_day} body', async () => {
    let capturedBody: Record<string, unknown> = {};
    server.use(
      http.post(
        `${API_BASE}/finances/billing-accounts/7/consolidate_debt/`,
        async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json(createMockInstallmentPlan(), { status: 201 });
        }
      )
    );

    const { result } = renderHook(() => useConsolidateDebt(), { wrapper: createWrapper() });
    result.current.mutate({
      account_id: 7,
      bill_ids: [1, 2, 3],
      embedded: false,
      installment_count: 3,
      start_due_date: '2026-08-10',
      default_due_day: 10,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(capturedBody).toEqual({
      bill_ids: [1, 2, 3],
      embedded: false,
      installment_count: 3,
      start_due_date: '2026-08-10',
      default_due_day: 10,
    });
  });

  it('returns the parsed plan via installmentPlanSchema', async () => {
    server.use(
      http.post(`${API_BASE}/finances/billing-accounts/7/consolidate_debt/`, () =>
        HttpResponse.json(createMockInstallmentPlan({ id: 55 }), { status: 201 })
      )
    );

    const { result } = renderHook(() => useConsolidateDebt(), { wrapper: createWrapper() });
    result.current.mutate({
      account_id: 7,
      bill_ids: [1],
      embedded: false,
      installment_count: 1,
      start_due_date: '2026-08-10',
      default_due_day: 10,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.id).toBe(55);
    expect(typeof result.current.data?.total_amount).toBe('number');
  });

  it('invalidates billingAccounts + monthBoard + installmentPlans + installments + bills on success', async () => {
    server.use(
      http.post(`${API_BASE}/finances/billing-accounts/7/consolidate_debt/`, () =>
        HttpResponse.json(createMockInstallmentPlan(), { status: 201 })
      )
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useConsolidateDebt(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      account_id: 7,
      bill_ids: [1],
      embedded: false,
      installment_count: 1,
      start_due_date: '2026-08-10',
      default_due_day: 10,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'month-board'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'installment-plans'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'installments'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
  });

  it('propagates a 400 error (closed competence / bill from another account)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/billing-accounts/7/consolidate_debt/`, () =>
        HttpResponse.json({ detail: 'Competência fechada.' }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useConsolidateDebt(), { wrapper: createWrapper() });
    result.current.mutate({
      account_id: 7,
      bill_ids: [1],
      embedded: false,
      installment_count: 1,
      start_due_date: '2026-08-10',
      default_due_day: 10,
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
