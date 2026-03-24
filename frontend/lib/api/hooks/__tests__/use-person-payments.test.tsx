import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  usePersonPayments,
  useCreatePersonPayment,
  useUpdatePersonPayment,
  useDeletePersonPayment,
} from '../use-person-payments';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockPersonPayments } from '@/tests/mocks/data';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

describe('usePersonPayments', () => {
  describe('usePersonPayments (list)', () => {
    it('should fetch all person payments', async () => {
      const { result } = renderHook(() => usePersonPayments(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(mockPersonPayments.length);
    });

    it('should fetch with filters', async () => {
      const { result } = renderHook(
        () => usePersonPayments({ person_id: 1, reference_month: '2026-03-01' }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toBeDefined();
    });

    it('should validate person payment data with Zod schema', async () => {
      const { result } = renderHook(() => usePersonPayments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      result.current.data?.forEach((payment) => {
        expect(payment).toHaveProperty('reference_month');
        expect(payment).toHaveProperty('amount');
        expect(payment).toHaveProperty('payment_date');
        expect(typeof payment.amount).toBe('number');
      });
    });

    it('should handle error from server', async () => {
      server.use(
        http.get(`${API_BASE}/person-payments/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => usePersonPayments({ month_from: '2026-01' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreatePersonPayment', () => {
    it('should create a person payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreatePersonPayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        person_id: 1,
        reference_month: '2026-04-01',
        amount: 800,
        payment_date: '2026-04-05',
        notes: 'Pagamento abril',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['person-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useUpdatePersonPayment', () => {
    it('should update a person payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const firstPayment = mockPersonPayments[0];
      if (!firstPayment?.id) throw new Error('Test data missing');

      const { result } = renderHook(() => useUpdatePersonPayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        id: firstPayment.id,
        person_id: firstPayment.person_id,
        reference_month: firstPayment.reference_month,
        amount: 600,
        payment_date: firstPayment.payment_date,
        notes: 'Atualizado',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['person-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });
  });

  describe('useDeletePersonPayment', () => {
    it('should delete a person payment and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeletePersonPayment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['person-payments'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['cash-flow'] });
    });

    it('should handle 404 when deleting non-existent payment', async () => {
      const { result } = renderHook(() => useDeletePersonPayment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
