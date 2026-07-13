/**
 * Tests for the tenant profile hook — including the "no active lease" shape (P8) and
 * the phone-update mutation (P10).
 */

import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useTenantProfile, useUpdateTenantPhone } from '../use-tenant-portal';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useTenantProfile', () => {
  it('should fetch the tenant profile with lease and apartment present', async () => {
    const { result } = renderHook(() => useTenantProfile(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.lease).toBeDefined();
    expect(result.current.data?.apartment).toBeDefined();
  });

  it('should handle a profile with no active lease (backend omits the keys)', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/me/`, () =>
        HttpResponse.json({
          id: 2,
          name: 'Sem Locação',
          cpf_cnpj: '11144477735',
          phone: '(11) 90000-0000',
          marital_status: 'Solteiro(a)',
          profession: 'Autônomo',
          due_day: 10,
          dependents: [],
          // lease/apartment intentionally absent — mirrors the real backend response.
        })
      )
    );

    const { result } = renderHook(() => useTenantProfile(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.lease).toBeUndefined();
    expect(result.current.data?.apartment).toBeUndefined();
  });
});

describe('useUpdateTenantPhone', () => {
  it('should update the phone via the shared profile endpoint', async () => {
    const { result } = renderHook(() => useUpdateTenantPhone(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('11988887777');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('should surface an error when the phone is invalid', async () => {
    server.use(
      http.patch(`${API_BASE}/auth/me/update/`, () =>
        HttpResponse.json({ error: 'Telefone inválido.' }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useUpdateTenantPhone(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('');

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
