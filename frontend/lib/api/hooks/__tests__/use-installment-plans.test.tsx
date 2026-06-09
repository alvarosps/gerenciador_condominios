import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useConvertDeferred,
  useCreateInstallmentPlan,
  useDeleteInstallmentPlan,
  useInstallmentPlans,
  useInstallments,
  useUpdateInstallment,
  useUpdateInstallmentPlan,
} from '../use-installment-plans';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockInstallment, createMockInstallmentPlan } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useInstallmentPlans', () => {
  it('lists plans and parses total_amount to a number', async () => {
    server.use(
      http.get(`${API_BASE}/finances/installment-plans/`, () =>
        // Raw API shape: total_amount is a string Decimal the schema transforms to number.
        HttpResponse.json([{ ...createMockInstallmentPlan(), total_amount: '1500.00' }]),
      ),
    );

    const { result } = renderHook(() => useInstallmentPlans(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const plan = result.current.data?.[0];
    expect(typeof plan?.total_amount).toBe('number');
    expect(plan?.total_amount).toBe(1500);
    expect(typeof plan?.installments?.[0]?.amount).toBe('number');
  });

  it('forwards building_id / lifecycle_state / embedded as query params', async () => {
    let captured: Record<string, string> = {};
    server.use(
      http.get(`${API_BASE}/finances/installment-plans/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        captured = {
          building_id: params.get('building_id') ?? '',
          lifecycle_state: params.get('lifecycle_state') ?? '',
          embedded: params.get('embedded') ?? '',
        };
        return HttpResponse.json([]);
      }),
    );

    const { result } = renderHook(
      () => useInstallmentPlans({ building_id: 4, lifecycle_state: 'deferred', embedded: true }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(captured.building_id).toBe('4');
    expect(captured.lifecycle_state).toBe('deferred');
    expect(captured.embedded).toBe('true');
  });

  it('surfaces server errors', async () => {
    server.use(
      http.get(
        `${API_BASE}/finances/installment-plans/`,
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useInstallmentPlans(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('installment plan mutations', () => {
  it('creates a plan with _id write fields and receives nested read; invalidates caches', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/finances/installment-plans/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockInstallmentPlan({ id: 9, category: null, building: null }), {
          status: 201,
        });
      }),
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useCreateInstallmentPlan(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      condominium_id: 1,
      description: 'IPTU 2026',
      total_amount: 1500,
      installment_count: 3,
      start_due_date: '2026-07-10',
      default_due_day: 10,
      lifecycle_state: 'active',
      embedded: false,
      category_id: 5,
      building_id: 4,
      billing_account_id: null,
      notes: '',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(sentBody).toHaveProperty('category_id', 5);
    expect(sentBody).toHaveProperty('building_id', 4);
    expect(result.current.data?.category).toBeNull();
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'installment-plans'] });
  });

  it('updates a plan via PATCH stripping nested read-only objects', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(`${API_BASE}/finances/installment-plans/:id/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createMockInstallmentPlan({ id: 1 }));
      }),
    );

    const { result } = renderHook(() => useUpdateInstallmentPlan(), { wrapper: createWrapper() });
    result.current.mutate({
      id: 1,
      description: 'IPTU revisado',
      condominium: { id: 1, name: 'Condominio' },
      category: null,
      building: null,
      billing_account: null,
      installments: [],
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(sentBody).toHaveProperty('description', 'IPTU revisado');
    expect(sentBody).not.toHaveProperty('condominium');
    expect(sentBody).not.toHaveProperty('category');
    expect(sentBody).not.toHaveProperty('building');
    expect(sentBody).not.toHaveProperty('billing_account');
    expect(sentBody).not.toHaveProperty('installments');
  });

  it('deletes a plan and invalidates caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteInstallmentPlan(), {
      wrapper: createWrapper(queryClient),
    });
    result.current.mutate(1);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'installment-plans'] });
  });

  it('surfaces a 500 error from a mutation without swallowing it', async () => {
    server.use(
      http.delete(
        `${API_BASE}/finances/installment-plans/:id/`,
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useDeleteInstallmentPlan(), { wrapper: createWrapper() });
    result.current.mutate(1);
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useUpdateInstallment (schedule PATCH)', () => {
  it('PATCHes amount/due_date and parses the new amount to a number', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(`${API_BASE}/finances/installments/:id/`, async ({ params, request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...createMockInstallment({ id: Number(params.id) }), amount: '620.50' });
      }),
    );

    const { result } = renderHook(() => useUpdateInstallment(), { wrapper: createWrapper() });
    result.current.mutate({ id: 2, amount: 620.5, due_date: '2026-08-15' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(sentBody).toHaveProperty('amount', 620.5);
    expect(sentBody).toHaveProperty('due_date', '2026-08-15');
    expect(typeof result.current.data?.amount).toBe('number');
    expect(result.current.data?.amount).toBe(620.5);
  });
});

describe('useInstallments', () => {
  it('forwards plan_id as a query param', async () => {
    let captured = '';
    server.use(
      http.get(`${API_BASE}/finances/installments/`, ({ request }) => {
        captured = new URL(request.url).searchParams.get('plan_id') ?? '';
        return HttpResponse.json([createMockInstallment()]);
      }),
    );
    const { result } = renderHook(() => useInstallments({ plan_id: 1 }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(captured).toBe('1');
    expect(typeof result.current.data?.[0]?.amount).toBe('number');
  });
});

describe('useConvertDeferred', () => {
  it('POSTs convert_deferred (detail=false) and invalidates plans + bills + billing-accounts', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/finances/installment-plans/convert_deferred/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          { ...createMockInstallmentPlan({ id: 7, lifecycle_state: 'active' }), total_amount: '1500.00' },
          { status: 201 },
        );
      }),
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useConvertDeferred(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      bill_id: 42,
      installment_count: 3,
      start_due_date: '2026-07-10',
      default_due_day: 10,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(sentBody).toHaveProperty('bill_id', 42);
    expect(result.current.data?.total_amount).toBe(1500);

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'installment-plans'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'bills'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
  });
});
