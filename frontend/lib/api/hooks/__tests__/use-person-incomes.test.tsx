import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  usePersonIncomes,
  useCreatePersonIncome,
  useUpdatePersonIncome,
  useDeletePersonIncome,
} from '../use-person-incomes';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

describe('usePersonIncomes', () => {
  describe('usePersonIncomes (list)', () => {
    it('should fetch all person incomes', async () => {
      const { result } = renderHook(() => usePersonIncomes(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toBeDefined();
      expect(Array.isArray(result.current.data)).toBe(true);
    });

    it('should fetch with filters', async () => {
      const { result } = renderHook(() => usePersonIncomes({ person_id: 1, is_active: true }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toBeDefined();
    });

    it('should validate person income data with Zod schema', async () => {
      const { result } = renderHook(() => usePersonIncomes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      result.current.data?.forEach((income) => {
        expect(income).toHaveProperty('income_type');
        expect(income).toHaveProperty('start_date');
        expect(income).toHaveProperty('is_active');
      });
    });

    it('should handle error from server', async () => {
      server.use(
        http.get(`${API_BASE}/person-incomes/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => usePersonIncomes({ income_type: 'test' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreatePersonIncome', () => {
    it('should create a person income and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreatePersonIncome(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        person_id: 1,
        income_type: 'fixed_stipend',
        apartment_id: null,
        fixed_amount: 1500,
        start_date: '2026-04-01',
        end_date: null,
        is_active: true,
        notes: 'Estipêndio novo',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['person-incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useUpdatePersonIncome', () => {
    it('should update a person income and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdatePersonIncome(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        id: 1,
        income_type: 'fixed_stipend',
        fixed_amount: 1200,
        start_date: '2026-01-01',
        is_active: true,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['person-incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useDeletePersonIncome', () => {
    it('should delete a person income and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeletePersonIncome(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['person-incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });

    it('should handle 404 when deleting non-existent income', async () => {
      server.use(
        http.delete(`${API_BASE}/person-incomes/:id/`, () => {
          return new HttpResponse(null, { status: 404 });
        }),
      );

      const { result } = renderHook(() => useDeletePersonIncome(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
