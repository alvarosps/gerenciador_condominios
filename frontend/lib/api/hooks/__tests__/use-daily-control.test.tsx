import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useDailyBreakdown, useDailySummary, useMarkItemPaid } from '../use-daily-control';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useDailyControl', () => {
  describe('useDailyBreakdown', () => {
    it('should fetch daily breakdown for a given year and month', async () => {
      const { result } = renderHook(() => useDailyBreakdown(2026, 3), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(1);
      expect(result.current.data?.[0]?.date).toBe('2026-03-01');
      expect(result.current.data?.[0]?.total_entries).toBe(1300);
      expect(result.current.data?.[0]?.entries).toHaveLength(1);
      expect(result.current.data?.[0]?.exits).toHaveLength(1);
    });

    it('should handle empty breakdown', async () => {
      server.use(
        http.get(`${API_BASE}/daily-control/breakdown/`, () => {
          return HttpResponse.json([]);
        }),
      );

      const { result } = renderHook(() => useDailyBreakdown(2026, 1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(0);
    });

    it('should handle error from server', async () => {
      server.use(
        http.get(`${API_BASE}/daily-control/breakdown/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useDailyBreakdown(2026, 3), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useDailySummary', () => {
    it('should fetch daily summary for a given year and month', async () => {
      const { result } = renderHook(() => useDailySummary(2026, 3), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.total_expected_income).toBe(12000);
      expect(result.current.data?.total_received_income).toBe(10000);
      expect(result.current.data?.overdue_count).toBe(2);
      expect(result.current.data?.current_balance).toBe(7000);
    });

    it('should handle error from server', async () => {
      server.use(
        http.get(`${API_BASE}/daily-control/summary/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useDailySummary(2026, 3), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useMarkItemPaid', () => {
    it('should mark an installment as paid and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useMarkItemPaid(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ item_type: 'installment', item_id: 1, payment_date: '2026-03-24' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.success).toBe(true);
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['daily-control'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expenses'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });

    it('should mark an expense as paid', async () => {
      const { result } = renderHook(() => useMarkItemPaid(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ item_type: 'expense', item_id: 5, payment_date: '2026-03-24' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.success).toBe(true);
    });

    it('should mark an income as paid', async () => {
      const { result } = renderHook(() => useMarkItemPaid(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ item_type: 'income', item_id: 3, payment_date: '2026-03-24' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.success).toBe(true);
    });
  });
});
