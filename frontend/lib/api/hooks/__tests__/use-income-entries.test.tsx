import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useIncomeEntries,
  useCreateIncomeEntry,
  useUpdateIncomeEntry,
  useDeleteIncomeEntry,
} from '../use-income-entries';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useIncomeEntries', () => {
  it('fetches income entries list', async () => {
    const { result } = renderHook(() => useIncomeEntries(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(Array.isArray(result.current.data)).toBe(true);
  });

  it('parses amount as number from string', async () => {
    server.use(
      http.get(`${API_BASE}/finances/income-entries/`, () =>
        HttpResponse.json([
          {
            id: 1,
            description: 'Test',
            amount: '500.00',
            income_date: '2026-06-01',
            is_received: false,
            received_date: null,
            notes: '',
          },
        ]),
      ),
    );
    const { result } = renderHook(() => useIncomeEntries(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(typeof result.current.data?.[0]?.amount).toBe('number');
    expect(result.current.data?.[0]?.amount).toBe(500);
  });

  it('sends is_received as literal string in filters', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/finances/income-entries/`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json([]);
      }),
    );
    const { result } = renderHook(() => useIncomeEntries({ is_received: false }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(capturedUrl).toContain('is_received=false');
  });

  it('handles server error', async () => {
    server.use(
      http.get(`${API_BASE}/finances/income-entries/`, () =>
        new HttpResponse(null, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useIncomeEntries(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useCreateIncomeEntry', () => {
  it('creates an income entry and invalidates incomeEntries + overview (refreshes KPIs)', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useCreateIncomeEntry(), {
      wrapper: createWrapper(queryClient),
    });
    await act(async () => {
      await result.current.mutateAsync({
        description: 'Nova receita',
        amount: 500,
        income_date: '2026-06-05',
        is_received: false,
        received_date: null,
        notes: '',
      });
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'income-entries'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });
});

describe('useUpdateIncomeEntry', () => {
  it('updates an income entry and invalidates incomeEntries + overview', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateIncomeEntry(), {
      wrapper: createWrapper(queryClient),
    });
    await act(async () => {
      await result.current.mutateAsync({
        id: 1,
        description: 'Receita atualizada',
        amount: 600,
        income_date: '2026-06-05',
        is_received: true,
        received_date: '2026-06-05',
        notes: '',
      });
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'income-entries'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });
});

describe('useDeleteIncomeEntry', () => {
  it('deletes an income entry and invalidates incomeEntries + overview', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteIncomeEntry(), {
      wrapper: createWrapper(queryClient),
    });
    await act(async () => {
      await result.current.mutateAsync(1);
    });
    expect(result.current.isSuccess).toBe(true);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'income-entries'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });
});
