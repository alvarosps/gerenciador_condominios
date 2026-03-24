import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import {
  useRentPayments,
  useRentPayment,
  useCreateRentPayment,
  useUpdateRentPayment,
  useDeleteRentPayment,
} from '../use-rent-payments';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';

describe('useRentPayments', () => {
  describe('useRentPayments (list)', () => {
    it('should fetch all rent payments', async () => {
      const { result } = renderHook(() => useRentPayments(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(1);
      expect(result.current.data?.[0]?.amount_paid).toBe(1300);
    });

    it('should fetch with filters', async () => {
      const { result } = renderHook(
        () => useRentPayments({ lease_id: 1, reference_month: '2026-03-01' }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toBeDefined();
    });

    it('should validate rent payment data with Zod schema', async () => {
      const { result } = renderHook(() => useRentPayments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      result.current.data?.forEach((payment) => {
        expect(payment).toHaveProperty('reference_month');
        expect(payment).toHaveProperty('amount_paid');
        expect(payment).toHaveProperty('payment_date');
        expect(typeof payment.amount_paid).toBe('number');
      });
    });
  });

  describe('useRentPayment (single)', () => {
    it('should fetch a single rent payment by ID', async () => {
      const { result } = renderHook(() => useRentPayment(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.amount_paid).toBe(1300);
    });

    it('should not fetch when ID is null', () => {
      const { result } = renderHook(() => useRentPayment(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle 404 for non-existent rent payment', async () => {
      const { result } = renderHook(() => useRentPayment(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreateRentPayment', () => {
    it('should create a rent payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateRentPayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        lease_id: 1,
        reference_month: '2026-04-01',
        amount_paid: 1300,
        payment_date: '2026-04-05',
        notes: '',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['rent-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useUpdateRentPayment', () => {
    it('should update a rent payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateRentPayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        id: 1,
        lease_id: 1,
        reference_month: '2026-03-01',
        amount_paid: 1400,
        payment_date: '2026-03-10',
        notes: 'Pagamento com atraso',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['rent-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['rent-payments', 1] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useDeleteRentPayment', () => {
    it('should delete a rent payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteRentPayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['rent-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['financial-dashboard'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });

    it('should handle 404 when deleting non-existent payment', async () => {
      const { result } = renderHook(() => useDeleteRentPayment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
