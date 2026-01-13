/**
 * Tests for useLeases hooks
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useLeases, useLease, useCreateLease, useUpdateLease, useDeleteLease, useGenerateContract } from '../use-leases';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockLeases } from '@/tests/mocks/data';

describe('useLeases', () => {
  describe('useLeases (list)', () => {
    it('should fetch all leases', async () => {
      const { result } = renderHook(() => useLeases(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for data to load
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should have fetched leases
      expect(result.current.data).toHaveLength(mockLeases.length);
    });

    it('should include nested apartment and tenant data', async () => {
      const { result } = renderHook(() => useLeases(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const firstLease = result.current.data?.[0];
      expect(firstLease?.apartment).toBeDefined();
      expect(firstLease?.responsible_tenant).toBeDefined();
      expect(firstLease?.tenants).toBeInstanceOf(Array);
    });
  });

  describe('useLease (single)', () => {
    it('should fetch a single lease by ID', async () => {
      const { result } = renderHook(() => useLease(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.id).toBe(1);
    });

    it('should not fetch when ID is null', async () => {
      const { result } = renderHook(() => useLease(null), {
        wrapper: createWrapper(),
      });

      // Query should be disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });
  });

  describe('useCreateLease', () => {
    it('should create a new lease', async () => {
      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useCreateLease(), {
        wrapper: createWrapper(queryClient),
      });

      const newLease = {
        apartment_id: 4,
        responsible_tenant_id: 2,
        tenant_ids: [2],
        start_date: '2024-12-01',
        validity_months: 12,
        due_day: 5,
        rental_value: 2500,
        cleaning_fee: 300,
        tag_fee: 50,
      };

      result.current.mutate(newLease);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.rental_value).toBe(2500);
    });

    it('should invalidate leases query after creation', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreateLease(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        apartment_id: 4,
        responsible_tenant_id: 2,
        tenant_ids: [2],
        start_date: '2024-12-01',
        validity_months: 12,
        due_day: 5,
        rental_value: 2500,
        cleaning_fee: 300,
        tag_fee: 50,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['leases'] });
    });
  });

  describe('useUpdateLease', () => {
    it('should update an existing lease', async () => {
      const { result } = renderHook(() => useUpdateLease(), {
        wrapper: createWrapper(),
      });

      const updatedLease = {
        ...mockLeases[0],
        id: mockLeases[0].id ?? 1,
        rental_value: 1800,
      };

      result.current.mutate(updatedLease);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.rental_value).toBe(1800);
    });
  });

  describe('useDeleteLease', () => {
    it('should delete a lease', async () => {
      const { result } = renderHook(() => useDeleteLease(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useGenerateContract', () => {
    it('should generate a contract for a lease', async () => {
      const { result } = renderHook(() => useGenerateContract(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(3); // Lease 3 doesn't have contract generated

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveProperty('message');
      expect(result.current.data).toHaveProperty('pdf_path');
    });

    it('should invalidate lease query after contract generation', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useGenerateContract(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate(3);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalled();
    });
  });
});
