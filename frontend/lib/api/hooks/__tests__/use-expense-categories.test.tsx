import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useExpenseCategories,
  useExpenseCategory,
  useCreateExpenseCategory,
  useUpdateExpenseCategory,
  useDeleteExpenseCategory,
} from '../use-expense-categories';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useExpenseCategories', () => {
  describe('useExpenseCategories (list)', () => {
    it('should fetch all expense categories', async () => {
      const { result } = renderHook(() => useExpenseCategories(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0]?.name).toBe('Pessoal');
    });

    it('should include subcategories in response', async () => {
      const { result } = renderHook(() => useExpenseCategories(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      const firstCategory = result.current.data?.[0];
      expect(firstCategory?.subcategories).toHaveLength(1);
      expect(firstCategory?.subcategories?.[0]?.name).toBe('Cartão');
    });

    it('should handle error from server', async () => {
      server.use(
        http.get(`${API_BASE}/expense-categories/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useExpenseCategories(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useExpenseCategory (single)', () => {
    it('should fetch a single category by ID', async () => {
      const { result } = renderHook(() => useExpenseCategory(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.name).toBe('Pessoal');
    });

    it('should not fetch when ID is null', () => {
      const { result } = renderHook(() => useExpenseCategory(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle 404 for non-existent category', async () => {
      const { result } = renderHook(() => useExpenseCategory(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreateExpenseCategory', () => {
    it('should create a category and invalidate cache', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateExpenseCategory(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ name: 'Nova Categoria', description: 'Descrição', color: '#ff0000', parent_id: null });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.name).toBe('Nova Categoria');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-categories'] });
    });
  });

  describe('useUpdateExpenseCategory', () => {
    it('should update a category and invalidate caches', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateExpenseCategory(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ id: 1, name: 'Pessoal Atualizado', color: '#0000ff' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.name).toBe('Pessoal Atualizado');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-categories'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-categories', 1] });
    });
  });

  describe('useDeleteExpenseCategory', () => {
    it('should delete a category and invalidate cache', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteExpenseCategory(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(2);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['expense-categories'] });
    });

    it('should handle 404 when deleting non-existent category', async () => {
      const { result } = renderHook(() => useDeleteExpenseCategory(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
