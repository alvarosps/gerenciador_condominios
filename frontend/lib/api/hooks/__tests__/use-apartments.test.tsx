/**
 * Tests for useApartments hooks
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import {
  useApartments,
  useApartment,
  useCreateApartment,
  useUpdateApartment,
  useDeleteApartment,
} from '../use-apartments';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockApartments } from '@/tests/mocks/data';

describe('useApartments', () => {
  describe('useApartments (list)', () => {
    it('should fetch all apartments', async () => {
      const { result } = renderHook(() => useApartments(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // Should have fetched apartments
      expect(result.current.data).toHaveLength(mockApartments.length);
    });

    it('should validate apartment data with Zod schema', async () => {
      const { result } = renderHook(() => useApartments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      // All apartments should have required fields
      result.current.data?.forEach((apartment) => {
        expect(apartment).toHaveProperty('id');
        expect(apartment).toHaveProperty('number');
        expect(apartment).toHaveProperty('building_id');
      });
    });
  });

  describe('useApartment (single)', () => {
    it('should fetch a single apartment by ID', async () => {
      const { result } = renderHook(() => useApartment(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.id).toBe(1);
    });

    it('should not fetch when ID is null', async () => {
      const { result } = renderHook(() => useApartment(null), {
        wrapper: createWrapper(),
      });

      // Query should be disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle 404 for non-existent apartment', async () => {
      const { result } = renderHook(() => useApartment(9999), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCreateApartment', () => {
    it('should create a new apartment', async () => {
      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useCreateApartment(), {
        wrapper: createWrapper(queryClient),
      });

      const newApartment = {
        number: 999,
        building_id: 1,
        rental_value: 1500,
        cleaning_fee: 150,
        max_tenants: 2,
        interfone_configured: false,
        contract_generated: false,
        contract_signed: false,
        is_rented: false,
        furniture_ids: [],
      };

      result.current.mutate(newApartment);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.number).toBe(999);
    });

    it('should invalidate apartments query after creation', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateApartment(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        number: 999,
        building_id: 1,
        rental_value: 1500,
        cleaning_fee: 150,
        max_tenants: 2,
        interfone_configured: false,
        contract_generated: false,
        contract_signed: false,
        is_rented: false,
        furniture_ids: [],
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['apartments'] });
    });
  });

  describe('useUpdateApartment', () => {
    it('should update an existing apartment', async () => {
      const { result } = renderHook(() => useUpdateApartment(), {
        wrapper: createWrapper(),
      });

      const updatedApartment = {
        id: 1,
        number: mockApartments[0].number,
        has_furniture: false,
      };

      result.current.mutate(updatedApartment);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    });
  });

  describe('useDeleteApartment', () => {
    it('should delete an apartment', async () => {
      const { result } = renderHook(() => useDeleteApartment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    });

    it('should handle 404 for non-existent apartment', async () => {
      const { result } = renderHook(() => useDeleteApartment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(9999);

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
