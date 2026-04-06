import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useContractRules,
  useContractRule,
  useCreateContractRule,
  useUpdateContractRule,
  useDeleteContractRule,
  useReorderContractRules,
  useToggleContractRule,
} from '../use-contract-rules';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useContractRules', () => {
  describe('useContractRules (list)', () => {
    it('should fetch all rules', async () => {
      const { result } = renderHook(() => useContractRules(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(3);
      expect(result.current.data?.[0]?.content).toBe('O inquilino deve pagar até o dia 5.');
    });

    it('should fetch only active rules when activeOnly is true', async () => {
      const { result } = renderHook(() => useContractRules(true), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.every((r) => r.is_active)).toBe(true);
      expect(result.current.data?.length).toBeLessThan(3);
    });

    it('should handle paginated response', async () => {
      server.use(
        http.get(`${API_BASE}/rules/`, () => {
          return HttpResponse.json({
            count: 2,
            next: null,
            previous: null,
            results: [
              { id: 1, content: 'Regra 1', order: 1, is_active: true, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
              { id: 2, content: 'Regra 2', order: 2, is_active: true, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
            ],
          });
        }),
      );

      const { result } = renderHook(() => useContractRules(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveLength(2);
    });
  });

  describe('useContractRule (single)', () => {
    it('should fetch a single rule by ID', async () => {
      const { result } = renderHook(() => useContractRule(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.content).toBe('O inquilino deve pagar até o dia 5.');
    });

    it('should handle 404 for non-existent rule', async () => {
      const { result } = renderHook(() => useContractRule(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreateContractRule', () => {
    it('should create a new rule', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateContractRule(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ content: 'Nova regra', order: 10, is_active: true });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBeDefined();
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['contract-rules'] });
    });
  });

  describe('useUpdateContractRule', () => {
    it('should update a rule via PATCH', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateContractRule(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ id: 1, content: 'Regra atualizada', is_active: false });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.content).toBe('Regra atualizada');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['contract-rules'] });
    });
  });

  describe('useDeleteContractRule', () => {
    it('should delete a rule', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useDeleteContractRule(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['contract-rules'] });
    });

    it('should handle 404 for non-existent rule', async () => {
      const { result } = renderHook(() => useDeleteContractRule(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useReorderContractRules', () => {
    it('should reorder rules and invalidate cache', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useReorderContractRules(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate([3, 1, 2]);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.message).toBeDefined();
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['contract-rules'] });
    });
  });

  describe('useToggleContractRule', () => {
    it('should toggle rule active status', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useToggleContractRule(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({ id: 1, is_active: false });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.is_active).toBe(false);
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['contract-rules'] });
    });
  });
});
