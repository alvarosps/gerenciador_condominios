import type { NextRequest } from 'next/server';

async function handleProxy(req: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://localhost:8008/api';
  
  // Extract path and search params
  const path = req.nextUrl.pathname.replace('/api/', '');
  const searchParams = req.nextUrl.search;
  
  // Construct destination URL, ensuring trailing slash for Django
  let targetPath = path;
  if (!targetPath.endsWith('/')) {
    targetPath += '/';
  }
  const targetUrl = `${backendUrl}/${targetPath}${searchParams}`;
  
  // Prepare body
  let body: ArrayBuffer | null = null;
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    body = await req.arrayBuffer();
  }
  
  // Prepare headers
  const headers = new Headers(req.headers);
  headers.delete('host'); // Let fetch set the correct host for Render
  headers.delete('connection');
  headers.delete('content-length'); // We will set it precisely
  
  if (body) {
    headers.set('content-length', body.byteLength.toString());
  }

  try {
    const response = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      redirect: 'manual',
    });

    const responseHeaders = new Headers(response.headers);
    // Remove headers that might confuse the client/proxy
    responseHeaders.delete('content-encoding');
    responseHeaders.delete('transfer-encoding');
    responseHeaders.delete('content-length'); // fetch decompresses automatically, so original length is wrong

    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    console.error('API Proxy Error:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return new Response(JSON.stringify({ error: 'Proxy Error', details: errorMessage }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const PATCH = handleProxy;
export const DELETE = handleProxy;
export const OPTIONS = handleProxy;
