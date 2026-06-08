import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useReserves, useCreateReserve, useDeleteReserve, useDepositReserve, useWithdrawReserve } from '../use-reserves';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useReserves', () => {
  it('fetches the list of reserves', async () => {
    const { result } = renderHook(() => useReserves(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data?.length).toBeGreaterThan(0);
  });

  it('parses balance as number', async () => {
    server.use(
      http.get(`${API_BASE}/finances/reserves/`, () =>
        HttpResponse.json([{ id: 1, name: 'ER', notes: '', balance: '5000.00', condominium: { id: 1, name: 'Condo' } }]),
      ),
    );
    const { result } = renderHook(() => useReserves(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(typeof result.current.data?.[0]?.balance).toBe('number');
    expect(result.current.data?.[0]?.balance).toBe(5000);
  });

  it('handles server error gracefully', async () => {
    server.use(
      http.get(`${API_BASE}/finances/reserves/`, () => new HttpResponse(null, { status: 500 })),
    );
    const { result } = renderHook(() => useReserves(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useCreateReserve', () => {
  it('creates a reserve (schema-parsed, balance number) and invalidates reserves + overview', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useCreateReserve(), { wrapper: createWrapper(queryClient) });
    let created: unknown;
    await act(async () => {
      created = await result.current.mutateAsync({ name: 'Nova Reserva', notes: '' });
    });
    expect(created).toMatchObject({ name: 'Nova Reserva' });
    expect(created).toEqual(expect.objectContaining({ balance: expect.any(Number) }));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'reserves'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });
});

describe('useDeleteReserve', () => {
  it('deletes a reserve and invalidates reserves + overview', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteReserve(), { wrapper: createWrapper(queryClient) });
    await act(async () => {
      await result.current.mutateAsync(1);
    });
    expect(result.current.isSuccess).toBe(true);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'reserves'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });
});

describe('useDepositReserve', () => {
  it('deposits and invalidates reserves + reserve-movements + overview (contract lives in the hook)', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useDepositReserve(), {
      wrapper: createWrapper(queryClient),
    });
    let updated: unknown;
    await act(async () => {
      updated = await result.current.mutateAsync({ reserveId: 1, payload: { amount: 1000 } });
    });
    expect(updated).toEqual(expect.objectContaining({ balance: expect.any(Number) }));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'reserves'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'reserve-movements'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });

  it('handles withdraw guard error (400)', async () => {
    server.use(
      http.post(`${API_BASE}/finances/reserves/:id/withdraw/`, () =>
        HttpResponse.json({ error: 'Saldo insuficiente na reserva' }, { status: 400 }),
      ),
    );
    const { result } = renderHook(() => useWithdrawReserve(), { wrapper: createWrapper() });
    await act(async () => {
      try {
        await result.current.mutateAsync({ reserveId: 1, payload: { amount: 999999 } });
      } catch {
        // expected
      }
    });
    expect(result.current.isError).toBe(true);
  });
});

describe('useWithdrawReserve', () => {
  it('withdraws and invalidates reserves + reserve-movements + overview', async () => {
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useWithdrawReserve(), {
      wrapper: createWrapper(queryClient),
    });
    await act(async () => {
      await result.current.mutateAsync({ reserveId: 1, payload: { amount: 100 } });
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'reserves'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'reserve-movements'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['finances', 'overview'] });
  });
});
