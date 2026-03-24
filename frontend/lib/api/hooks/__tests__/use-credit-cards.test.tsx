import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useCreditCards,
  useCreditCard,
  useCreateCreditCard,
  useUpdateCreditCard,
  useDeleteCreditCard,
} from '../use-credit-cards';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

describe('useCreditCards', () => {
  describe('useCreditCards (list)', () => {
    it('should fetch all credit cards', async () => {
      const { result } = renderHook(() => useCreditCards(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0]?.nickname).toBe('Nubank Rodrigo');
    });

    it('should validate credit card data with Zod schema', async () => {
      const { result } = renderHook(() => useCreditCards(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      result.current.data?.forEach((card) => {
        expect(card).toHaveProperty('nickname');
        expect(card).toHaveProperty('closing_day');
        expect(card).toHaveProperty('due_day');
        expect(card).toHaveProperty('is_active');
      });
    });

    it('should handle error when server fails', async () => {
      server.use(
        http.get(`${API_BASE}/credit-cards/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useCreditCards(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreditCard (single)', () => {
    it('should fetch a single credit card by ID', async () => {
      const { result } = renderHook(() => useCreditCard(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.nickname).toBe('Nubank Rodrigo');
    });

    it('should not fetch when ID is null', () => {
      const { result } = renderHook(() => useCreditCard(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle 404 for non-existent card', async () => {
      const { result } = renderHook(() => useCreditCard(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreateCreditCard', () => {
    it('should create a new credit card and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateCreditCard(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        person_id: 1,
        nickname: 'C6 Bank',
        last_four_digits: '9012',
        closing_day: 15,
        due_day: 22,
        is_active: true,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.nickname).toBe('C6 Bank');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['credit-cards'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['persons'] });
    });
  });

  describe('useUpdateCreditCard', () => {
    it('should update an existing credit card', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateCreditCard(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ id: 1, nickname: 'Nubank Atualizado', closing_day: 12, due_day: 19, is_active: true });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.nickname).toBe('Nubank Atualizado');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['credit-cards'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['persons'] });
    });
  });

  describe('useDeleteCreditCard', () => {
    it('should delete a credit card and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteCreditCard(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(2);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['credit-cards'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['persons'] });
    });

    it('should handle 404 when deleting non-existent card', async () => {
      const { result } = renderHook(() => useDeleteCreditCard(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
