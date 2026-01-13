import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * List of public paths that don't require authentication
 */
const PUBLIC_PATHS = ['/login', '/register'];

/**
 * Middleware to protect routes that require authentication
 *
 * This runs before rendering any page, checking if the user is authenticated.
 * Redirects to /login if accessing protected pages without authentication.
 * Redirects to / (dashboard) if accessing /login while already authenticated.
 *
 * Protected routes (under (dashboard) route group):
 * - / (root/dashboard)
 * - /buildings
 * - /apartments
 * - /tenants
 * - /leases
 * - /furniture
 * - /contract-template
 */
export function middleware(request: NextRequest) {
  // Check for access token in cookies (synced from localStorage on login)
  const hasToken = request.cookies.has('access_token');

  // Get current path
  const path = request.nextUrl.pathname;

  // Check if this is a public path
  const isPublicPath = PUBLIC_PATHS.some((publicPath) => path === publicPath || path.startsWith(`${publicPath}/`));

  // If accessing protected page without token, redirect to login
  if (!isPublicPath && !hasToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', path); // Save redirect path for after login
    return NextResponse.redirect(loginUrl);
  }

  // If accessing login/register while authenticated, redirect to dashboard
  if (isPublicPath && hasToken) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Allow the request to proceed
  return NextResponse.next();
}

/**
 * Matcher configuration - specify which routes this middleware applies to
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (images, etc.)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.svg$).*)',
  ],
};
