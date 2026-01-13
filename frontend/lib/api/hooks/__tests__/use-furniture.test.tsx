/**
 * Tests for useFurniture hooks
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useFurniture, useCreateFurniture, useUpdateFurniture, useDeleteFurniture } from '../use-furniture';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockFurniture } from '@/tests/mocks/data';

describe('useFurniture', () => {
  describe('useFurniture (list)', () => {
    it('should fetch all furniture items', async () => {
      const { result } = renderHook(() => useFurniture(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for data to load
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should have fetched furniture
      expect(result.current.data).toHaveLength(mockFurniture.length);
      expect(result.current.data?.[0].name).toBe(mockFurniture[0].name);
    });

    it('should validate furniture data with Zod schema', async () => {
      const { result } = renderHook(() => useFurniture(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // All furniture items should have required fields
      result.current.data?.forEach((item) => {
        expect(item).toHaveProperty('id');
        expect(item).toHaveProperty('name');
      });
    });
  });

  describe('useCreateFurniture', () => {
    it('should create a new furniture item', async () => {
      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useCreateFurniture(), {
        wrapper: createWrapper(queryClient),
      });

      const newFurniture = {
        name: 'New Chair',
        description: 'A comfortable office chair',
      };

      result.current.mutate(newFurniture);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe('New Chair');
    });

    it('should invalidate furniture query after creation', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateFurniture(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        name: 'New Desk',
        description: 'A standing desk',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['furniture'] });
    });
  });

  describe('useUpdateFurniture', () => {
    it('should update an existing furniture item', async () => {
      const { result } = renderHook(() => useUpdateFurniture(), {
        wrapper: createWrapper(),
      });

      const updatedFurniture = {
        ...mockFurniture[0],
        name: 'Updated Furniture Name',
      };

      result.current.mutate(updatedFurniture);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe('Updated Furniture Name');
    });
  });

  describe('useDeleteFurniture', () => {
    it('should delete a furniture item', async () => {
      const { result } = renderHook(() => useDeleteFurniture(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it('should handle 404 for non-existent furniture', async () => {
      const { result } = renderHook(() => useDeleteFurniture(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });
});
