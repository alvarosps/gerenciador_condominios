import { describe, it, expect } from 'vitest';
import { NextRequest } from 'next/server';
import { middleware } from '@/middleware';

interface Cookie {
  name: string;
  value: string;
}

function makeRequest(path: string, cookies: Cookie[] = []): NextRequest {
  const request = new NextRequest(new URL(`https://app.example.com${path}`));
  for (const { name, value } of cookies) {
    request.cookies.set(name, value);
  }
  return request;
}

const AUTH = { name: 'is_authenticated', value: '1' };
const STAFF = { name: 'role', value: 'staff' };
const TENANT = { name: 'role', value: 'tenant' };

describe('middleware role-based routing', () => {
  it('redirects a tenant from an admin route to /tenant', () => {
    const response = middleware(makeRequest('/buildings', [AUTH, TENANT]));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example.com/tenant');
  });

  it('redirects a tenant from the dashboard root to /tenant', () => {
    const response = middleware(makeRequest('/', [AUTH, TENANT]));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example.com/tenant');
  });

  it('treats a missing role as tenant (fail-safe) on an admin route', () => {
    const response = middleware(makeRequest('/finances/bills', [AUTH]));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example.com/tenant');
  });

  it('allows a staff user on /finances/bills', () => {
    const response = middleware(makeRequest('/finances/bills', [AUTH, STAFF]));
    // NextResponse.next() carries the rewrite header, not a redirect Location.
    expect(response.headers.get('location')).toBeNull();
  });

  it('allows a tenant on the tenant portal', () => {
    const response = middleware(makeRequest('/tenant', [AUTH, TENANT]));
    expect(response.headers.get('location')).toBeNull();
  });

  it('redirects a staff user away from the tenant portal to /', () => {
    const response = middleware(makeRequest('/tenant/payments', [AUTH, STAFF]));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example.com/');
  });

  it('redirects an unauthenticated user on /tenant to /tenant/login (not /login)', () => {
    const response = middleware(makeRequest('/tenant/payments'));
    expect(response.status).toBe(307);
    const location = response.headers.get('location') ?? '';
    expect(location).toContain('/tenant/login');
    expect(location).toContain('redirect=%2Ftenant%2Fpayments');
  });

  it('redirects an unauthenticated user on an admin route to /login', () => {
    const response = middleware(makeRequest('/buildings'));
    expect(response.status).toBe(307);
    const location = response.headers.get('location') ?? '';
    expect(location).toContain('/login');
    expect(location).not.toContain('/tenant/login');
  });

  it('sends an authenticated tenant on /login to /tenant', () => {
    const response = middleware(makeRequest('/login', [AUTH, TENANT]));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example.com/tenant');
  });

  it('sends an authenticated staff user on /login to /', () => {
    const response = middleware(makeRequest('/login', [AUTH, STAFF]));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://app.example.com/');
  });
});
