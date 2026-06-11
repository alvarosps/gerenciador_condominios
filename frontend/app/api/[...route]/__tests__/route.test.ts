import { NextRequest } from 'next/server';
import { describe, it, expect, vi, afterEach } from 'vitest';

import { POST } from '../route';

describe('API proxy route', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns 502 Bad Gateway when the backend connection fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('fetch failed'));
    vi.spyOn(console, 'error').mockImplementation(() => undefined);

    const request = new NextRequest('http://localhost:4000/api/leases/65/generate_contract/', {
      method: 'POST',
    });

    const response = await POST(request);

    expect(response.status).toBe(502);
    const body: unknown = await response.json();
    expect(body).toEqual({ error: 'Bad Gateway', details: 'fetch failed' });
  });

  it('does not forward hop-by-hop headers to the backend', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{}', { status: 200 }));

    const request = new NextRequest('http://localhost:4000/api/leases/65/generate_contract/', {
      method: 'POST',
      headers: {
        'transfer-encoding': 'chunked',
        connection: 'keep-alive',
        'keep-alive': 'timeout=5',
        authorization: 'Bearer token-123',
      },
    });

    await POST(request);

    const init = fetchSpy.mock.calls[0]?.[1];
    // The route forwards a Headers instance; assert against it directly.
    // Do NOT re-wrap with `new Headers(init.headers)` — happy-dom's Headers
    // copy-constructor drops headers that were themselves copied in, which
    // would spuriously strip `authorization` here.
    const forwardedHeaders = init?.headers;
    expect(forwardedHeaders).toBeInstanceOf(Headers);
    if (!(forwardedHeaders instanceof Headers)) {
      throw new Error('expected forwarded headers to be a Headers instance');
    }
    expect(forwardedHeaders.has('transfer-encoding')).toBe(false);
    expect(forwardedHeaders.has('connection')).toBe(false);
    expect(forwardedHeaders.has('keep-alive')).toBe(false);
    expect(forwardedHeaders.get('authorization')).toBe('Bearer token-123');
  });

  it('forwards backend responses with their original status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Não encontrado.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const request = new NextRequest('http://localhost:4000/api/leases/999/', {
      method: 'GET',
    });

    const response = await POST(request);

    expect(response.status).toBe(404);
    const body: unknown = await response.json();
    expect(body).toEqual({ detail: 'Não encontrado.' });
  });
});
