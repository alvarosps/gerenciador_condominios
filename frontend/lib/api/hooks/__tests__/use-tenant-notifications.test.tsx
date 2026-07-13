/**
 * Tests for tenant notification hooks and the contract-download blob error parsing (P11).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useTenantNotifications,
  useMarkNotificationRead,
  useDownloadContract,
} from '../use-tenant-notifications';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useTenantNotifications', () => {
  it('should fetch the notification list from the paginated envelope', async () => {
    server.use(
      http.get(`${API_BASE}/tenant/notifications/`, () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 1,
              type: 'rent_due',
              title: 'Aluguel vence em breve',
              body: 'Seu aluguel vence em 3 dias.',
              is_read: false,
              sent_at: '2026-03-01T10:00:00Z',
            },
          ],
        })
      )
    );

    const { result } = renderHook(() => useTenantNotifications(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0]?.title).toBe('Aluguel vence em breve');
  });
});

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
