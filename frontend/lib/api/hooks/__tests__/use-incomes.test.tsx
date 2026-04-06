import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import {
  useIncomes,
  useIncome,
  useCreateIncome,
  useUpdateIncome,
  useDeleteIncome,
  useMarkIncomeReceived,
} from '../use-incomes';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';

describe('useIncomes', () => {
  describe('useIncomes (list)', () => {
    it('should fetch all incomes', async () => {
      const { result } = renderHook(() => useIncomes(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(1);
      expect(result.current.data?.[0]?.description).toBe('Aluguel extra escritório');
    });

    it('should fetch with filters', async () => {
      const { result } = renderHook(() => useIncomes({ person_id: 3, is_received: false }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toBeDefined();
    });

    it('should validate income data with Zod schema', async () => {
      const { result } = renderHook(() => useIncomes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      result.current.data?.forEach((income) => {
        expect(income).toHaveProperty('description');
        expect(income).toHaveProperty('amount');
        expect(income).toHaveProperty('income_date');
        expect(income).toHaveProperty('is_received');
      });
    });
  });

  describe('useIncome (single)', () => {
    it('should fetch a single income by ID', async () => {
      const { result } = renderHook(() => useIncome(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.amount).toBe(2000);
    });

    it('should not fetch when ID is null', () => {
      const { result } = renderHook(() => useIncome(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle 404 for non-existent income', async () => {
      const { result } = renderHook(() => useIncome(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreateIncome', () => {
    it('should create an income and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateIncome(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        description: 'Nova receita',
        amount: 1500,
        income_date: '2026-04-01',
        person_id: null,
        building_id: null,
        category_id: null,
        is_recurring: false,
        expected_monthly_amount: null,
        is_received: false,
        received_date: null,
        notes: '',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useUpdateIncome', () => {
    it('should update an income and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateIncome(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ id: 1, description: 'Receita atualizada', amount: 2500 });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.description).toBe('Receita atualizada');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['incomes', 1] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useDeleteIncome', () => {
    it('should delete an income and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteIncome(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useMarkIncomeReceived', () => {
    it('should mark income as received and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useMarkIncomeReceived(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['incomes'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });
});
