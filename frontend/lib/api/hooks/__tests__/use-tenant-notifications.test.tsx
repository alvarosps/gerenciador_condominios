/**
 * Tests for tenant notification hooks and the contract-download blob error parsing (P11).
 *
 * useTenantNotifications (list) is intentionally NOT covered here — it is pre-existing, out
 * of this batch's scope, and currently broken (reads `data.results` after the axios
 * interceptor already unwraps the paginated envelope into a plain array; see
 * use-buildings.ts / use-contract-rules.ts for the correct
 * `Array.isArray(data) ? data : data.results` pattern). Flagged separately — not fixed here.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useMarkNotificationRead, useDownloadContract } from '../use-tenant-notifications';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useMarkNotificationRead', () => {
  it('should mark a notification as read', async () => {
    server.use(
      http.patch(`${API_BASE}/tenant/notifications/1/read/`, () =>
        HttpResponse.json({}, { status: 200 })
      )
    );

    const { result } = renderHook(() => useMarkNotificationRead(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});

describe('useDownloadContract', () => {
  const originalCreateObjectURL = URL.createObjectURL.bind(URL);
  const originalRevokeObjectURL = URL.revokeObjectURL.bind(URL);
  let createObjectURLMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    createObjectURLMock = vi.fn(() => 'blob:mock-url');
    URL.createObjectURL = createObjectURLMock;
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it('should download the contract blob on success', async () => {
    const { result } = renderHook(() => useDownloadContract(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createObjectURLMock).toHaveBeenCalled();
  });

  it('should surface the real backend message on a failed download (not a generic status)', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/contract/`, () =>
        HttpResponse.json({ detail: 'Contrato ainda não foi gerado.' }, { status: 404 })
      )
    );

    const { result } = renderHook(() => useDownloadContract(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));

    const error = result.current.error as { response?: { data?: { detail?: string } } };
    expect(error.response?.data?.detail).toBe('Contrato ainda não foi gerado.');
  });
});
