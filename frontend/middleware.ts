import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware to protect routes that require authentication
 *
 * This runs before rendering any page, checking if the user is authenticated.
 * Redirects to /login if accessing protected pages without authentication.
 * Redirects to /dashboard if accessing /login while already authenticated.
 */
export function middleware(request: NextRequest) {
  // Check for access token in cookies or check localStorage hint
  const hasToken = request.cookies.has('access_token');

  // Get current path
  const path = request.nextUrl.pathname;

  // Dashboard routes (protected)
  const isProtectedPage = path.startsWith('/dashboard');

  // If trying to access protected page without token, redirect to login
  if (isProtectedPage && !hasToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', path); // Save redirect path
    return NextResponse.redirect(loginUrl);
  }

  // If trying to access login/register while authenticated, redirect to dashboard
  if ((path === '/login' || path === '/register') && hasToken) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
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
