import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useEmployeePayments,
  useEmployeePayment,
  useCreateEmployeePayment,
  useUpdateEmployeePayment,
  useDeleteEmployeePayment,
  useMarkEmployeePaymentPaid,
} from '../use-employee-payments';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

describe('useEmployeePayments', () => {
  describe('useEmployeePayments (list)', () => {
    it('should fetch all employee payments', async () => {
      const { result } = renderHook(() => useEmployeePayments(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(1);
      expect(result.current.data?.[0]?.base_salary).toBe(1320);
    });

    it('should fetch with filters', async () => {
      const { result } = renderHook(() => useEmployeePayments({ person_id: 2, is_paid: false }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toBeDefined();
    });

    it('should handle empty list', async () => {
      server.use(
        http.get(`${API_BASE}/employee-payments/`, () => {
          return HttpResponse.json([]);
        }),
      );

      const { result } = renderHook(() => useEmployeePayments({ is_paid: true }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(0);
    });
  });

  describe('useEmployeePayment (single)', () => {
    it('should fetch a single employee payment by ID', async () => {
      const { result } = renderHook(() => useEmployeePayment(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.is_paid).toBe(false);
    });

    it('should not fetch when ID is null', () => {
      const { result } = renderHook(() => useEmployeePayment(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });
  });

  describe('useCreateEmployeePayment', () => {
    it('should create a payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateEmployeePayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        person_id: 2,
        reference_month: '2026-04-01',
        base_salary: 1320,
        variable_amount: 0,
        rent_offset: 0,
        cleaning_count: 8,
        is_paid: false,
        notes: '',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['employee-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useUpdateEmployeePayment', () => {
    it('should update a payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateEmployeePayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ id: 1, cleaning_count: 15, notes: 'Atualizado' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['employee-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useDeleteEmployeePayment', () => {
    it('should delete a payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteEmployeePayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['employee-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useMarkEmployeePaymentPaid', () => {
    it('should mark payment as paid and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useMarkEmployeePaymentPaid(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['employee-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });
});
