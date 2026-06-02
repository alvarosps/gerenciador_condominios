import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

export function GET(req: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL ?? 'http://localhost:8008/api';
  const baseUrl = backendUrl.replace(/\/api\/?$/, '');
  
  const path = req.nextUrl.searchParams.get('path');
  if (!path) {
    return new Response('Missing path', { status: 400 });
  }

  // Ensure path doesn't start with a slash if baseUrl ends without one
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  const targetUrl = `${baseUrl}/${cleanPath}`;
  
  return NextResponse.redirect(targetUrl);
}
