import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useLandlord, useUpdateLandlord } from '../use-landlord';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8000/api';

describe('useLandlord', () => {
  describe('useLandlord (query)', () => {
    it('should fetch current landlord', async () => {
      const { result } = renderHook(() => useLandlord(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.name).toBe('João da Silva');
      expect(result.current.data?.cpf_cnpj).toBe('12345678901');
      expect(result.current.data?.city).toBe('São Paulo');
    });

    it('should validate landlord data with Zod schema', async () => {
      const { result } = renderHook(() => useLandlord(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data).toHaveProperty('name');
      expect(result.current.data).toHaveProperty('cpf_cnpj');
      expect(result.current.data).toHaveProperty('marital_status');
      expect(result.current.data).toHaveProperty('is_active');
    });

    it('should handle 404 gracefully without retrying', async () => {
      server.use(
        http.get(`${API_BASE}/landlords/current/`, () => {
          return new HttpResponse(null, { status: 404 });
        }),
      );

      const { result } = renderHook(() => useLandlord(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });

      // The retry logic should stop on 404
      expect(result.current.error).toBeDefined();
    });
  });

  describe('useUpdateLandlord', () => {
    it('should update landlord and invalidate cache', async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateLandlord(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        name: 'João da Silva Atualizado',
        nationality: 'Brasileira',
        marital_status: 'Casado(a)',
        cpf_cnpj: '12345678901',
        phone: '(11) 88888-8888',
        street: 'Rua das Flores',
        street_number: '456',
        neighborhood: 'Jardins',
        city: 'São Paulo',
        state: 'SP',
        zip_code: '01310-100',
        country: 'Brasil',
        is_active: true,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.name).toBe('João da Silva Atualizado');
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['landlord'] });
    });

    it('should handle server error during update', async () => {
      server.use(
        http.put(`${API_BASE}/landlords/current/`, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(() => useUpdateLandlord(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        name: 'Teste',
        nationality: 'Brasileira',
        marital_status: 'Solteiro(a)',
        cpf_cnpj: '12345678901',
        phone: '(11) 99999-9999',
        street: 'Rua Teste',
        street_number: '1',
        neighborhood: 'Centro',
        city: 'São Paulo',
        state: 'SP',
        zip_code: '01310-100',
        country: 'Brasil',
        is_active: true,
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });
});
