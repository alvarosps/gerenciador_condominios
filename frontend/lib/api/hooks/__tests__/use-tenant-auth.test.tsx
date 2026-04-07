/**
 * Tests for tenant auth hooks (OTP flow)
 *
 * Tests verify that hooks make correct API calls and handle success/error
 * responses. Uses MSW to intercept HTTP requests at the network boundary.
 * Uses the real Zustand auth store — reset between tests with clearAuth().
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useRequestOtp, useVerifyOtp } from '../use-tenant-auth';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';

const API_BASE = 'http://localhost:8008/api';

describe('useRequestOtp', () => {
  it('should return success detail on valid CPF/CNPJ', async () => {
    const { result } = renderHook(() => useRequestOtp(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ cpf_cnpj: '12345678901' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.detail).toBe('Código enviado via WhatsApp');
  });

  it('should error on invalid request', async () => {
    server.use(
      http.post(`${API_BASE}/auth/whatsapp/request/`, () => {
        return HttpResponse.json({ detail: 'CPF/CNPJ não encontrado' }, { status: 400 });
      }),
    );

    const { result } = renderHook(() => useRequestOtp(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ cpf_cnpj: '00000000000' });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('useVerifyOtp', () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth();
  });

  it('should set auth state on successful OTP verification', async () => {
    const { result } = renderHook(() => useVerifyOtp(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ cpf_cnpj: '12345678901', code: '123456' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    const storeState = useAuthStore.getState();
    expect(storeState.isAuthenticated).toBe(true);
    expect(storeState.user?.first_name).toBe('João');
  });

  it('should error on invalid OTP code', async () => {
    server.use(
      http.post(`${API_BASE}/auth/whatsapp/verify/`, () => {
        return HttpResponse.json({ detail: 'Código inválido ou expirado' }, { status: 400 });
      }),
    );

    const { result } = renderHook(() => useVerifyOtp(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ cpf_cnpj: '12345678901', code: '000000' });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });

    const storeState = useAuthStore.getState();
    expect(storeState.isAuthenticated).toBe(false);
  });
});
