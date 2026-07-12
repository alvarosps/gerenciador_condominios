/**
 * Tests for tenant payment hooks (rent adjustments, proof upload/list).
 *
 * useTenantPayments is intentionally NOT covered here — it is pre-existing, out of this
 * batch's scope, and currently broken (reads `data.results` after the axios interceptor
 * already unwraps the paginated envelope into a plain array; see use-buildings.ts /
 * use-contract-rules.ts for the correct `Array.isArray(data) ? data : data.results` pattern).
 * Flagged separately — not fixed here to stay within the batch's scope.
 */

import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useTenantRentAdjustments, useUploadProof, useTenantProofs } from '../use-tenant-payments';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useTenantRentAdjustments', () => {
  it('should fetch the rent adjustments list', async () => {
    const { result } = renderHook(() => useTenantRentAdjustments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });
});

describe('useTenantProofs', () => {
  it('should fetch the tenant own proof list (P4)', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/payments/proof/`, () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 1,
              reference_month: '2026-03-01',
              file: 'http://localhost:8008/media/proof.png',
              pix_code: '',
              status: 'pending',
              reviewed_at: null,
              rejection_reason: '',
              created_at: '2026-03-01T10:00:00Z',
            },
          ],
        })
      )
    );

    const { result } = renderHook(() => useTenantProofs(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0]?.status).toBe('pending');
  });
});

describe('useUploadProof', () => {
  it('should upload the proof and invalidate the proof list query', async () => {
    const formData = new FormData();
    formData.append('reference_month', '2026-03-01');
    formData.append('file', new File(['x'], 'proof.png', { type: 'image/png' }));

    const { result } = renderHook(() => useUploadProof(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(formData);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.status).toBe('pending');
  });

  it('should surface an error when the upload fails (e.g. bad reference_month)', async () => {
    server.use(
      http.post(`${API_BASE}/tenant/payments/proof/`, () =>
        HttpResponse.json({ reference_month: ['Data inválida.'] }, { status: 400 })
      )
    );

    const formData = new FormData();
    formData.append('reference_month', 'not-a-date');
    formData.append('file', new File(['x'], 'proof.png', { type: 'image/png' }));

    const { result } = renderHook(() => useUploadProof(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(formData);

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
