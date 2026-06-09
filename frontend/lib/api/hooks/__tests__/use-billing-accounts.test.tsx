import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useBillingAccount,
  useBillingAccounts,
  useCreateBillingAccount,
  useDeleteBillingAccount,
  useUpdateBillingAccount,
} from '../use-billing-accounts';
import { createTestQueryClient, createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBillingAccount } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

describe('useBillingAccounts', () => {
  it('fetches the list and parses expected_amount (string Decimal) to number', async () => {
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/`, () =>
        // Raw API shape: expected_amount is a string Decimal that the schema transforms to number.
        HttpResponse.json([
          { ...createMockBillingAccount(), expected_amount: '120.50', lifecycle_state: 'suspended' },
        ]),
      ),
    );

    const { result } = renderHook(() => useBillingAccounts(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.length).toBeGreaterThan(0);
    expect(result.current.data?.[0]?.name).toBeDefined();
    expect(typeof result.current.data?.[0]?.expected_amount).toBe('number');
    expect(result.current.data?.[0]?.expected_amount).toBe(120.5);
    expect(result.current.data?.[0]?.lifecycle_state).toBe('suspended');
  });

  it('forwards filters as query params', async () => {
    let captured: Record<string, string> = {};
    server.use(
      http.get(`${API_BASE}/finances/billing-accounts/`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        captured = {
          building_id: params.get('building_id') ?? '',
          lifecycle_state: params.get('lifecycle_state') ?? '',
        };
        return HttpResponse.json([]);
      }),
    );

    const { result } = renderHook(
      () => useBillingAccounts({ building_id: 7, lifecycle_state: 'active' }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(captured.building_id).toBe('7');
    expect(captured.lifecycle_state).toBe('active');
  });

  it('fetches a single billing account when an id is provided', async () => {
    const { result } = renderHook(() => useBillingAccount(1), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.id).toBe(1);
  });

  it('stays idle when id is null', () => {
    const { result } = renderHook(() => useBillingAccount(null), { wrapper: createWrapper() });
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('surfaces server errors', async () => {
    server.use(
      http.get(
        `${API_BASE}/finances/billing-accounts/`,
        () => new HttpResponse(null, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useBillingAccounts(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('billing-account mutations', () => {
  it('creates a billing account and invalidates the dependent caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useCreateBillingAccount(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      name: 'Água - Prédio 836',
      external_identifier: '',
      account_type: 'water',
      holder_name: '',
      registered_address: '',
      secondary_identifier: '',
      supply_status: 'active',
      description: '',
      default_due_day: 10,
      expected_amount: 120,
      lifecycle_state: 'active',
      notes: '',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
  });

  it('updates a billing account, stripping nested read-only objects and invalidating caches', async () => {
    let sentBody: Record<string, unknown> | null = null;
    server.use(
      http.put(`${API_BASE}/finances/billing-accounts/:id/`, async ({ request }) => {
        sentBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: 1, ...sentBody });
      }),
    );

    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateBillingAccount(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate({
      id: 1,
      name: 'Atualizado',
      expected_amount: 999,
      condominium: { id: 1, name: 'Condomínio' },
      building: null,
      category: null,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(result.current.data?.name).toBe('Atualizado');
    expect(sentBody).not.toBeNull();
    expect(sentBody).not.toHaveProperty('condominium');
    expect(sentBody).not.toHaveProperty('building');
    expect(sentBody).not.toHaveProperty('category');
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
  });

  it('deletes a billing account and invalidates caches', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteBillingAccount(), {
      wrapper: createWrapper(queryClient),
    });

    result.current.mutate(1);
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'billing-accounts'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'combined-calendar'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overdue-bills'] });
  });
});
