import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { useReserveMovements } from '../use-reserve-movements';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';

const API_BASE = 'http://localhost:8008/api';

describe('useReserveMovements', () => {
  it('fetches and parses the ledger — both kind enum members go through the schema', async () => {
    const { result } = renderHook(() => useReserveMovements(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    const [first, second] = result.current.data ?? [];
    expect(typeof first?.amount).toBe('number');
    expect(first?.kind).toBe('deposit');
    // The withdrawal row exercises the other half of the kind enum + amount string→number.
    expect(second?.kind).toBe('withdrawal');
    expect(typeof second?.amount).toBe('number');
  });

  it('forwards reserve_id and kind as query params (read-only — no balance simulation)', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/finances/reserve-movements/`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json([]);
      }),
    );
    const { result } = renderHook(() => useReserveMovements({ reserve_id: 7, kind: 'deposit' }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });
    expect(capturedUrl).toContain('reserve_id=7');
    expect(capturedUrl).toContain('kind=deposit');
  });

  it('surfaces server errors (isError) without throwing', async () => {
    server.use(
      http.get(`${API_BASE}/finances/reserve-movements/`, () => new HttpResponse(null, { status: 500 })),
    );
    const { result } = renderHook(() => useReserveMovements(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});
