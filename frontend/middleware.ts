import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Public paths that don't require authentication.
 */
const PUBLIC_PATHS = ['/login', '/register', '/tenant/login', '/auth/callback'];

/**
 * Admin dashboard route prefixes (everything under the (dashboard) route group).
 *
 * A non-staff tenant must never reach these — the backend already scopes/blocks the data,
 * this is the UX barrier so they land on their own portal instead of a broken admin shell.
 */
const ADMIN_ROUTE_PREFIXES = [
  '/buildings',
  '/apartments',
  '/tenants',
  '/leases',
  '/furniture',
  '/contract-template',
  '/finances',
  '/financial',
  '/admin',
  '/settings',
];

/**
 * Whether a path belongs to the admin dashboard (so a tenant must be redirected away).
 *
 * The dashboard root ("/") is admin-only too; the tenant portal lives under /tenant.
 */
function isAdminRoute(path: string): boolean {
  if (path === '/') {
    return true;
  }
  return ADMIN_ROUTE_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

/**
 * Middleware to protect routes that require authentication and to keep tenants out of the
 * admin dashboard.
 *
 * - Unauthenticated on a protected route → redirect to the matching login (/tenant/login for
 *   the portal, /login for the dashboard).
 * - Authenticated tenant (role !== 'staff', or role missing — fail-safe) on an admin route →
 *   redirect to /tenant.
 * - Authenticated staff on a /tenant route → redirect to / (the admin dashboard) to avoid a
 *   broken tenant UI.
 * - Authenticated on a public/login path → redirect to the role's home.
 *
 * The backend (queryset scope + IsAdminUser) is the real authorization barrier; the `role`
 * cookie is a non-HttpOnly hint the Edge middleware can read.
 */
export function middleware(request: NextRequest) {
  const hasToken = request.cookies.has('is_authenticated');
  // Missing role is treated as a tenant (non-admin) — fail-safe, never leak the dashboard.
  const isStaff = request.cookies.get('role')?.value === 'staff';

  const path = request.nextUrl.pathname;
  const isTenantPath = path === '/tenant' || path.startsWith('/tenant/');

  const isPublicPath = PUBLIC_PATHS.some(
    (publicPath) => path === publicPath || path.startsWith(`${publicPath}/`)
  );

  // Unauthenticated on a protected page → redirect to the matching login.
  if (!isPublicPath && !hasToken) {
    const loginPath = isTenantPath ? '/tenant/login' : '/login';
    const loginUrl = new URL(loginPath, request.url);
    loginUrl.searchParams.set('redirect', path);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated tenant trying to reach an admin route → send them to their portal.
  if (hasToken && !isStaff && isAdminRoute(path)) {
    return NextResponse.redirect(new URL('/tenant', request.url));
  }

  // Authenticated staff landing on the tenant portal (except its login) → back to dashboard.
  if (hasToken && isStaff && isTenantPath && path !== '/tenant/login') {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Authenticated on a login/register page → redirect to the role's home.
  if (isPublicPath && hasToken) {
    const home = isStaff ? '/' : '/tenant';
    return NextResponse.redirect(new URL(home, request.url));
  }

  return NextResponse.next();
}

/**
 * Matcher configuration - specify which routes this middleware applies to
 */
export const config = {
  matcher: [
    /*
     * Run the auth middleware on app routes only. Skip:
     * - api            — proxied to the backend (app/api/[...route])
     * - _next/static   — build assets
     * - _next/image    — image optimization
     * - offline        — the PWA offline fallback page (must load without auth)
     * - any path containing a dot — static/metadata assets served at the root
     *   (manifest.webmanifest, sw.js, favicon.ico, icons, robots.txt, …). These
     *   must NOT be auth-gated, or they 307 to /login and break the PWA/manifest.
     * Protected app routes (e.g. /buildings, /leases) have no dot, so they stay gated.
     */
    '/((?!api|_next/static|_next/image|offline|.*\\..*).*)',
  ],
};
