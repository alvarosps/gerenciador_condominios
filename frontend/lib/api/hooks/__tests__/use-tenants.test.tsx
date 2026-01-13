/**
 * Tests for useTenants hooks
 */

import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useTenants, useTenant, useCreateTenant, useUpdateTenant, useDeleteTenant } from '../use-tenants';
import { createWrapper, createTestQueryClient } from '@/tests/test-utils';
import { mockTenants } from '@/tests/mocks/data';

describe('useTenants', () => {
  describe('useTenants (list)', () => {
    it('should fetch all tenants', async () => {
      const { result } = renderHook(() => useTenants(), {
        wrapper: createWrapper(),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for data to load
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should have fetched tenants
      expect(result.current.data).toHaveLength(mockTenants.length);
      expect(result.current.data?.[0].name).toBe(mockTenants[0].name);
    });

    it('should include individual and company tenants', async () => {
      const { result } = renderHook(() => useTenants(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const individuals = result.current.data?.filter((t) => !t.is_company) || [];
      const companies = result.current.data?.filter((t) => t.is_company) || [];

      expect(individuals.length).toBeGreaterThan(0);
      expect(companies.length).toBeGreaterThan(0);
    });
  });

  describe('useTenant (single)', () => {
    it('should fetch a single tenant by ID', async () => {
      const { result } = renderHook(() => useTenant(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.id).toBe(1);
      expect(result.current.data?.name).toBe(mockTenants[0].name);
    });

    it('should not fetch when ID is null', async () => {
      const { result } = renderHook(() => useTenant(null), {
        wrapper: createWrapper(),
      });

      // Query should be disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should include dependents data', async () => {
      const { result } = renderHook(() => useTenant(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Tenant 1 has dependents
      expect(result.current.data?.dependents).toBeInstanceOf(Array);
      expect(result.current.data?.dependents.length).toBeGreaterThan(0);
    });
  });

  describe('useCreateTenant', () => {
    it('should create a new tenant', async () => {
      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useCreateTenant(), {
        wrapper: createWrapper(queryClient),
      });

      const newTenant = {
        name: 'João Novo',
        cpf_cnpj: '11122233344',
        is_company: false,
        phone: '(11) 98888-7777',
        email: 'joao.novo@email.com',
        marital_status: 'Solteiro',
        profession: 'Desenvolvedor',
        deposit_amount: null,
        furnitures: [],
        dependents: [],
      };

      result.current.mutate(newTenant);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe('João Novo');
    });

    it('should create tenant with dependents', async () => {
      const { result } = renderHook(() => useCreateTenant(), {
        wrapper: createWrapper(),
      });

      const tenantWithDependents = {
        name: 'Família Silva',
        cpf_cnpj: '55566677788',
        is_company: false,
        phone: '(11) 98888-7777',
        email: 'familia.silva@email.com',
        marital_status: 'Casado',
        profession: 'Contador',
        deposit_amount: null,
        furnitures: [],
        dependents: [
          { name: 'Filho 1', phone: '(11) 91111-2222' },
          { name: 'Filho 2', phone: '(11) 93333-4444' },
        ],
      };

      result.current.mutate(tenantWithDependents);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useUpdateTenant', () => {
    it('should update an existing tenant', async () => {
      const { result } = renderHook(() => useUpdateTenant(), {
        wrapper: createWrapper(),
      });

      const updatedTenant = {
        ...mockTenants[0],
        id: mockTenants[0].id ?? 1,
        name: 'Updated Tenant Name',
      };

      result.current.mutate(updatedTenant);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe('Updated Tenant Name');
    });
  });

  describe('useDeleteTenant', () => {
    it('should delete a tenant', async () => {
      const { result } = renderHook(() => useDeleteTenant(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(1);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });
});
