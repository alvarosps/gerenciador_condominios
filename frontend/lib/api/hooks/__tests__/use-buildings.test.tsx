/**
 * Tests for useBuildings hooks
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBuildings, useBuilding, useCreateBuilding, useUpdateBuilding, useDeleteBuilding } from '../use-buildings';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockBuildings } from '@/tests/mocks/data';

describe('useBuildings', () => {
  describe('useBuildings (list)', () => {
    it('should fetch all buildings', async () => {
      const { result } = renderHook(() => useBuildings(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for data to load with increased timeout
      await waitFor(
        () => {
          expect(result.current.isSuccess).toBe(true);
        },
        { timeout: 5000 }
      );

      // Should have fetched buildings
      expect(result.current.data).toHaveLength(mockBuildings.length);
      expect(result.current.data?.[0].name).toBe(mockBuildings[0].name);
    });

    it('should validate building data with Zod schema', async () => {
      const { result } = renderHook(() => useBuildings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // All buildings should have required fields
      result.current.data?.forEach((building) => {
        expect(building).toHaveProperty('id');
        expect(building).toHaveProperty('street_number');
        expect(building).toHaveProperty('name');
      });
    });
  });

  describe('useBuilding (single)', () => {
    it('should fetch a single building by ID', async () => {
      const { result } = renderHook(() => useBuilding(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.name).toBe(mockBuildings[0].name);
    });

    it('should not fetch when ID is null', async () => {
      const { result } = renderHook(() => useBuilding(null), {
        wrapper: createWrapper(),
      });

      // Query should be disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle 404 for non-existent building', async () => {
      const { result } = renderHook(() => useBuilding(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useCreateBuilding', () => {
    it('should create a new building', async () => {
      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useCreateBuilding(), {
        wrapper: createWrapper(queryClient),
      });

      const newBuilding = {
        street_number: 9999,
        name: 'New Building',
        address: 'New Street, 9999 - New Neighborhood, São Paulo - SP, 01310-100',
      };

      result.current.mutate(newBuilding);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe('New Building');
    });

    it('should invalidate buildings query after creation', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateBuilding(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        street_number: 9999,
        name: 'New Building',
        address: 'New Street, 9999 - New Neighborhood, São Paulo - SP, 01310-100',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['buildings'] });
    });
  });

  describe('useUpdateBuilding', () => {
    it('should update an existing building', async () => {
      const { result } = renderHook(() => useUpdateBuilding(), {
        wrapper: createWrapper(),
      });

      const updatedBuilding = {
        ...mockBuildings[0],
        name: 'Updated Building Name',
      };

      result.current.mutate(updatedBuilding);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe('Updated Building Name');
    });
  });

  describe('useDeleteBuilding', () => {
    it('should delete a building', async () => {
      const { result } = renderHook(() => useDeleteBuilding(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it('should handle 404 for non-existent building', async () => {
      const { result } = renderHook(() => useDeleteBuilding(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });
});
