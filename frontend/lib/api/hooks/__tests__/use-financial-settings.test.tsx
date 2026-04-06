import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useFinancialSettings, useUpdateFinancialSettings } from '../use-financial-settings';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useFinancialSettings', () => {
  describe('useFinancialSettings (query)', () => {
    it('should fetch financial settings', async () => {
      const { result } = renderHook(() => useFinancialSettings(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.initial_balance).toBe(10000);
      expect(result.current.data?.initial_balance_date).toBe('2026-01-01');
      expect(result.current.data?.notes).toBe('Saldo inicial do sistema');
    });

    it('should validate settings with Zod schema', async () => {
      const { result } = renderHook(() => useFinancialSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveProperty('initial_balance');
      expect(result.current.data).toHaveProperty('initial_balance_date');
      expect(typeof result.current.data?.initial_balance).toBe('number');
    });

    it('should handle error from server', async () => {
      server.use(
        http.get(`${API_BASE}/financial-settings/current/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useFinancialSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useUpdateFinancialSettings', () => {
    it('should update settings and invalidate cache', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateFinancialSettings(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        initial_balance: 15000,
        initial_balance_date: '2026-03-01',
        notes: 'Saldo ajustado',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.notes).toBe('Saldo ajustado');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-settings'] });
    });

    it('should handle update failure gracefully', async () => {
      server.use(
        http.put(`${API_BASE}/financial-settings/current/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useUpdateFinancialSettings(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        initial_balance: 15000,
        initial_balance_date: '2026-03-01',
        notes: '',
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
