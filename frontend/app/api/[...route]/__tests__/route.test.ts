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

  it('forwards backend responses with their original status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Não encontrado.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
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
