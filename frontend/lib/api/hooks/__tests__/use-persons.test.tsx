import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { usePersons, useCreatePerson, useUpdatePerson, useDeletePerson } from '../use-persons';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockPersons } from '@/tests/mocks/data';

describe('usePersons', () => {
  describe('usePersons (list)', () => {
    it('should fetch persons list', async () => {
      const { result } = renderHook(() => usePersons(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(
        () => {
          expect(result.current.isSuccess).toBe(true);
        },
        { timeout: 5000 },
      );

      expect(result.current.data).toHaveLength(mockPersons.length);
      expect(result.current.data?.[0]?.name).toBe(mockPersons[0]?.name);
    });
  });

  describe('useCreatePerson', () => {
    it('should create a person', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useCreatePerson(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        name: 'Nova Pessoa',
        relationship: 'Amigo',
        phone: '11999990000',
        email: 'nova@example.com',
        is_owner: false,
        is_employee: false,
        user: null,
        notes: '',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['persons'] });
    });
  });

  describe('useUpdatePerson', () => {
    it('should update a person', async () => {
      const { result } = renderHook(() => useUpdatePerson(), {
        wrapper: createWrapper(),
      });

      const basePerson = mockPersons[0];
      if (!basePerson?.id) throw new Error('Test data missing');

      result.current.mutate({
        ...basePerson,
        id: basePerson.id,
        name: 'Nome Atualizado',
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useDeletePerson', () => {
    it('should delete a person', async () => {
      const { result } = renderHook(() => useDeletePerson(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });
});
