# Sprint 4 — Frontend Polish & Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the frontend against common failure modes — session expiry races, open redirect vulnerabilities, inadequate retry strategy, and stale UI from Zustand hydration mismatches — while improving accessibility, SEO, and backend password/admin security.

**Architecture:** 12 tasks, all independent of each other. Frontend tasks target Next.js 14 App Router with cookie-based JWT auth (HttpOnly cookies), Zustand for auth profile, TanStack Query for server state. Backend tasks target Django 5.2 settings and `core/` app.

**Tech Stack:** Next.js 14, React 18, TypeScript strict, TanStack Query v5, Zustand, Axios, Zod, Django 5.2, DRF, pytest, Ruff, mypy

**Dependency Graph:**
```
All 12 tasks are independent and can be implemented in any order.

Task 1 (Token refresh soft redirect)   → independent
Task 2 (Login error handling)          → independent
Task 3 (Exponential backoff)           → independent
Task 4 (Middleware redirect validation) → independent
Task 5 (React.memo list components)    → independent
Task 6 (Console cleanup)               → independent
Task 7 (Accessibility icon labels)     → independent
Task 8 (SEO metadata)                  → independent
Task 9 (Hydration guard for Zustand)   → independent
Task 10 (Password complexity validator) → independent
Task 11 (Admin URL obfuscation)        → independent
Task 12 (Bare exception cleanup)       → independent
```

---

## Task 1: Token Refresh Soft Redirect

**Context:** `frontend/lib/api/client.ts:57` — when the token refresh request fails (network error or server-side refresh rejection), the interceptor calls `window.location.href = '/login'`. This causes a hard browser reload, destroying all in-flight TanStack Query state and React component trees. Additionally, if multiple concurrent API requests all fail with 401 simultaneously while the deduplication promise is resolving, multiple interceptor catch-blocks can race and all attempt to set `window.location.href`, causing multiple history entries (the user cannot press Back to escape the loop). The fix adds a module-level `isRedirecting` flag and uses `window.location.replace('/login')` (which replaces the current history entry rather than pushing a new one, preventing the back-button loop).

**Files:**
- Modify: `frontend/lib/api/client.ts`

- [ ] **Step 1: Add `isRedirecting` flag and replace hard redirect**

Read `frontend/lib/api/client.ts` (already done) then apply the following changes.

The current catch block at line 50–63:
```typescript
} catch (refreshError) {
  // Refresh failed - clear auth state and redirect to login
  if (typeof window !== 'undefined') {
    // Also clear Zustand store (imported dynamically to avoid circular dependency)
    const { useAuthStore } = await import('@/store/auth-store');
    useAuthStore.getState().clearAuth();

    window.location.href = '/login';
  }
  ...
}
```

Replace with a version that:
1. Guards against multiple concurrent redirects with a module-level flag
2. Imports `toast` from `sonner` (already in the project) for user feedback
3. Uses `window.location.replace` instead of `href` assignment

```typescript
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

let refreshPromise: Promise<void> | null = null;
let isRedirecting = false;

const REQUEST_TIMEOUT_MS = 30_000;

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api',
  timeout: REQUEST_TIMEOUT_MS,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Response interceptor - Handle 401 errors by refreshing the HttpOnly cookie token
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError & { config?: InternalAxiosRequestConfig & { _retry?: boolean } }) => {
    const originalRequest = error.config;

    // If 401 Unauthorized and we haven't retried yet
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        if (typeof window === 'undefined') {
          return await Promise.reject(error instanceof Error ? error : new Error(String(error)));
        }

        // Deduplicate concurrent refresh calls — only one request goes out
        // Cookies are sent automatically via withCredentials
        refreshPromise ??= axios
          .post(
            `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api'}/auth/token/refresh/`,
            {},
            { withCredentials: true }
          )
          .then(() => undefined)
          .finally(() => {
            refreshPromise = null;
          });

        await refreshPromise;

        // Retry the original request — new access cookie is now set
        return await apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear auth state and redirect to login
        // Guard against multiple concurrent 401s all racing to redirect
        if (typeof window !== 'undefined' && !isRedirecting) {
          isRedirecting = true;

          const { useAuthStore } = await import('@/store/auth-store');
          useAuthStore.getState().clearAuth();

          // Inline import to avoid bundling sonner into the interceptor module path
          const { toast } = await import('sonner');
          toast.error('Sessão expirada. Faça login novamente.');

          // replace() prevents a back-button loop (no new history entry)
          window.location.replace('/login');
        }

        return Promise.reject(
          refreshError instanceof Error ? refreshError : new Error(String(refreshError))
        );
      }
    }

    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }
);
```

- [ ] **Step 2: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 2: Login Error Handling

**Context:** `frontend/app/login/page.tsx:69-74` — the catch block tests for `z.ZodError` and falls through to a generic `setError('Credenciais inválidas...')` for every other error type. This means a network failure (server is down), a 500 Internal Server Error, or a timeout all display the same misleading message as an actual wrong-password 401. The project already has `getErrorMessage()` in `frontend/lib/utils/error-handler.ts` which handles network errors, HTTP status codes, and DRF response shapes. Using it here with a 401-specific fallback produces correct messages for all error types.

**Files:**
- Modify: `frontend/app/login/page.tsx`

- [ ] **Step 1: Import `getErrorMessage` and update the catch block**

Current catch at line 69–75:
```typescript
} catch (err) {
  if (err instanceof z.ZodError) {
    toast.error('Por favor, preencha todos os campos corretamente');
  } else {
    setError('Credenciais inválidas. Verifique seu usuário e senha.');
  }
}
```

Replace with:
```typescript
import { getErrorMessage } from '@/lib/utils/error-handler';
```

And the catch block becomes:
```typescript
} catch (err) {
  if (err instanceof z.ZodError) {
    toast.error('Por favor, preencha todos os campos corretamente');
  } else {
    setError(getErrorMessage(err, 'Credenciais inválidas. Verifique seu usuário e senha.'));
  }
}
```

Note: `getErrorMessage` already maps 401 responses to `'Sessão expirada. Faça login novamente.'` (line 122 of `error-handler.ts`). For the login page this is semantically wrong — a 401 during login means wrong credentials, not an expired session. The correct approach is to pass the fallback default `'Credenciais inválidas. Verifique seu usuário e senha.'` as the second argument, which `getErrorMessage` uses when the Axios error response contains no structured message. This keeps the correct user-facing text for 401 while surfacing real network errors distinctly.

- [ ] **Step 2: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 3: Exponential Backoff for TanStack Query Retries

**Context:** `frontend/lib/config/query-client.ts:7-18` — the `retry` callback correctly skips retries on 401/403, and limits to 3 attempts. However, there is no `retryDelay` configured. Without it, TanStack Query uses its built-in default of a fixed 1000ms delay between all retry attempts. Exponential backoff (1s, 2s, 4s, capped at 30s) is the correct strategy for transient failures: it avoids hammering a temporarily overloaded server while still recovering quickly on the first retry.

**Files:**
- Modify: `frontend/lib/config/query-client.ts`

- [ ] **Step 1: Add `retryDelay` to `defaultOptions.queries`**

Current file:
```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error) => {
        if (
          error instanceof Error &&
          'response' in error &&
          [401, 403].includes(
            (error as { response?: { status?: number } }).response?.status ?? 0
          )
        ) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: true,
    },
  },
});
```

Updated file:
```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error) => {
        if (
          error instanceof Error &&
          'response' in error &&
          [401, 403].includes(
            (error as { response?: { status?: number } }).response?.status ?? 0
          )
        ) {
          return false;
        }
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30_000),
      refetchOnWindowFocus: true,
    },
  },
});
```

- [ ] **Step 2: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 4: Middleware Redirect Validation (Open Redirect Prevention)

**Context:** `frontend/middleware.ts:38` — when an unauthenticated user accesses a protected page, the middleware sets `?redirect=<pathname>` so the login page can send the user to their original destination after authentication. The pathname is taken directly from `request.nextUrl.pathname` without validation. A malicious link like `/login?redirect=//evil.example.com` would not work because Next.js URL parsing normalizes the path, but a relative path to a crafted page under a legitimate prefix could behave unexpectedly. The correct defence is allowlisting: only set the redirect param when the path starts with a known app route prefix.

**Files:**
- Modify: `frontend/middleware.ts`

- [ ] **Step 1: Add allowed redirect prefixes and validate before setting param**

Current code at line 36–39:
```typescript
if (!isPublicPath && !hasToken) {
  const loginUrl = new URL('/login', request.url);
  loginUrl.searchParams.set('redirect', path); // Save redirect path for after login
  return NextResponse.redirect(loginUrl);
}
```

Updated file:
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * List of public paths that don't require authentication
 */
const PUBLIC_PATHS = ['/login', '/register', '/tenant/login'];

/**
 * Allowed redirect prefixes after login — only app-internal routes.
 * Prevents open redirect attacks by rejecting arbitrary paths.
 */
const ALLOWED_REDIRECT_PREFIXES = [
  '/',
  '/buildings',
  '/apartments',
  '/tenants',
  '/leases',
  '/furniture',
  '/contract-template',
  '/finances',
  '/settings',
  '/admin',
];

function isSafeRedirectPath(path: string): boolean {
  return ALLOWED_REDIRECT_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`)
  );
}

// ... rest of middleware unchanged, but replace the redirect block:

if (!isPublicPath && !hasToken) {
  const loginUrl = new URL('/login', request.url);
  if (isSafeRedirectPath(path)) {
    loginUrl.searchParams.set('redirect', path);
  }
  return NextResponse.redirect(loginUrl);
}
```

Write the full updated `middleware.ts` — do not truncate the matcher config at the bottom.

- [ ] **Step 2: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 5: React.memo for High-Frequency List Components

**Context:** Only 4 components in the project use `React.memo` (EditorToolbar, ToolbarButton, VariableInserter, WysiwygEditor — all in the contract template editor). The sidebar navigation items and any repeated row-level components in the financial pages re-render on every parent state change even when their own props are unchanged. `React.memo` is most valuable on components that: (a) render in a list/loop, (b) receive stable props that rarely change, and (c) have non-trivial render cost.

**Files:**
- Read: `frontend/components/layouts/sidebar.tsx`
- Possibly modify based on what is found

- [ ] **Step 1: Read the Sidebar component to identify nav item rendering**

```bash
cat frontend/components/layouts/sidebar.tsx
```

Look for:
- A navigation item component rendered in a loop (`.map(...)`)
- Whether the component is defined inline or as a named component
- What props it receives (href, label, icon, isActive)

- [ ] **Step 2: Extract nav item into a memoized named component if rendered inline**

If sidebar nav items are rendered via an inline JSX expression inside `.map()`, extract them into a `NavItem` component and wrap with `React.memo`. Example pattern:

```typescript
import { memo } from 'react';

interface NavItemProps {
  href: string;
  label: string;
  icon: React.ReactNode;
  isActive: boolean;
  onClick?: () => void;
}

const NavItem = memo(function NavItem({ href, label, icon, isActive, onClick }: NavItemProps) {
  return (
    <Link href={href} onClick={onClick} className={isActive ? 'bg-accent' : ''}>
      {icon}
      <span>{label}</span>
    </Link>
  );
});
```

Only apply `memo` if the props (especially `isActive`) are derived from stable values. Do not memo if `isActive` recalculates on every render from `usePathname()` — in that case the memo wrapper adds overhead with no benefit.

- [ ] **Step 3: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 6: Console Statement Cleanup

**Context:** There are 237 `console.error`/`console.warn` calls across the frontend. In production builds these add noise to error reporting tools and can leak implementation details. The project's `error-handler.ts` already has a `handleError()` function with a comment indicating Sentry integration is planned. The ESLint config may or may not have `no-console` enabled — check first before adding a rule.

**Files:**
- Read: `frontend/.eslintrc.json` or `frontend/eslint.config.mjs`
- Modify: `frontend/lib/utils/error-handler.ts` and affected files

- [ ] **Step 1: Check current ESLint console configuration**

```bash
cat /c/Users/alvar/git/personal/gerenciador_condominios/frontend/.eslintrc.json 2>/dev/null || cat /c/Users/alvar/git/personal/gerenciador_condominios/frontend/eslint.config.mjs
```

- [ ] **Step 2: If `no-console` is not set to `error`, add it**

In the ESLint config, add or update:
```json
"no-console": ["error", { "allow": [] }]
```

This enforces that no `console.*` calls remain in production code. All existing usages must be resolved before this rule is active (otherwise CI breaks).

- [ ] **Step 3: Audit and fix `console.error` calls in production code paths**

Run:
```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && grep -rn "console\." --include="*.ts" --include="*.tsx" --exclude-dir=__tests__ --exclude-dir=tests src/ app/ lib/ components/ store/ 2>/dev/null | grep -v "\.test\." | grep -v "\.spec\."
```

For each occurrence, apply one of these fixes based on context:

a) **Developer-only debugging logs** — wrap in environment guard:
```typescript
if (process.env.NODE_ENV === 'development') {
  console.warn('[ComponentName] debug info:', value);
}
```

b) **Error logging in catch blocks** — replace with `handleError()`:
```typescript
// Before
console.error('Failed to load data:', error);

// After
import { handleError } from '@/lib/utils/error-handler';
handleError(error, 'ComponentName.functionName');
```

c) **Logs that serve no purpose** — delete entirely.

- [ ] **Step 4: Verify linting and type-check pass with zero console violations**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 7: Accessibility — Icon Aria Labels

**Context:** 27 Lucide React icon usages lack accessibility attributes. Screen readers encounter icon-only buttons without labels, leaving keyboard-only and assistive technology users unable to determine button purpose. The fix depends on context: decorative icons (next to descriptive text) get `aria-hidden="true"`, icon-only interactive elements get `aria-label` on the button/link wrapping them.

**Files:**
- Search and modify: components containing `<Button size="icon">` or similar icon-only interactive elements

- [ ] **Step 1: Find all icon-only button patterns**

```bash
grep -rn 'size="icon"' /c/Users/alvar/git/personal/gerenciador_condominios/frontend/components /c/Users/alvar/git/personal/gerenciador_condominios/frontend/app --include="*.tsx" | grep -v "__tests__"
```

Also search for icons inside buttons without adjacent text:
```bash
grep -rn 'Button.*icon\|IconButton' /c/Users/alvar/git/personal/gerenciador_condominios/frontend --include="*.tsx" | grep -v "__tests__"
```

- [ ] **Step 2: Add `aria-label` to icon-only interactive elements**

Common patterns to fix:

For CRUD action icon buttons (edit, delete, view):
```tsx
// Before
<Button variant="ghost" size="icon" onClick={onEdit}>
  <Pencil className="h-4 w-4" />
</Button>

// After
<Button variant="ghost" size="icon" onClick={onEdit} aria-label="Editar">
  <Pencil className="h-4 w-4" aria-hidden="true" />
</Button>
```

For navigation/menu icon buttons:
```tsx
// Excluir
<Button variant="ghost" size="icon" onClick={onDelete} aria-label="Excluir">
  <Trash2 className="h-4 w-4" aria-hidden="true" />
</Button>

// Visualizar
<Button variant="ghost" size="icon" onClick={onView} aria-label="Visualizar detalhes">
  <Eye className="h-4 w-4" aria-hidden="true" />
</Button>
```

For icons adjacent to text labels (decorative):
```tsx
// Before
<Settings className="mr-2 h-4 w-4" />
<span>Configurações</span>

// After — icon is decorative, text provides the label
<Settings className="mr-2 h-4 w-4" aria-hidden="true" />
<span>Configurações</span>
```

Note: `header.tsx` already has `aria-label="Notificações"` on the Bell button — this is the correct pattern to follow.

- [ ] **Step 3: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 8: SEO Metadata and Viewport

**Context:** `frontend/app/layout.tsx:5-8` exports only `title` and `description`. Next.js 14 supports a structured `Metadata` object and a separate `Viewport` export (required since Next.js 14.0 — the `viewport` key inside `metadata` is deprecated and produces a warning). Missing `robots` metadata means search engines can index the login page and internal pages, which is undesirable for a private property management system. Missing `viewport` meta leaves mobile rendering to browser defaults.

**Files:**
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Expand metadata and add Viewport export**

Current file:
```typescript
import type { Metadata } from 'next';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'Condomínios Manager',
  description: 'Sistema de gerenciamento de locações',
};
```

Updated file:
```typescript
import type { Metadata, Viewport } from 'next';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Condomínios Manager',
    template: '%s | Condomínios Manager',
  },
  description: 'Sistema de gestão de imóveis para locação no Brasil.',
  // Private app — do not index any pages
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: 'Condomínios Manager',
    description: 'Sistema de gestão de imóveis para locação no Brasil.',
    type: 'website',
    locale: 'pt_BR',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Verify linting, type-check, and build pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check && npm run build
```

Expected: zero errors, no Next.js metadata deprecation warnings

---

## Task 9: Hydration Guard for Zustand Auth Consumers

**Context:** `useHydration` hook exists at `frontend/lib/hooks/use-hydration.ts` and is already used correctly in `header.tsx` (shows `HeaderSkeleton` until hydration). However, multiple other components call `useAuthStore()` directly without a hydration guard. In Next.js SSR, Zustand's `persist` middleware initialises from `localStorage`, which is unavailable during server rendering. On first paint, the store returns its initial state (user = null, isAuthenticated = false) before hydrating from localStorage, causing a flash of unauthenticated UI.

Components that read `useAuthStore` without guarding: `main-layout.tsx` (reads `isAuthenticated` and `user` in a `useEffect`), `sidebar.tsx` (likely reads user role for conditional nav), and various financial page components.

**Files:**
- Read and potentially modify: `frontend/components/layouts/main-layout.tsx`, `frontend/components/layouts/sidebar.tsx`, and any page component that conditionally renders based on `user.is_staff`

- [ ] **Step 1: Audit all `useAuthStore` consumers for SSR-unsafe patterns**

```bash
grep -rn "useAuthStore" /c/Users/alvar/git/personal/gerenciador_condominios/frontend/components /c/Users/alvar/git/personal/gerenciador_condominios/frontend/app --include="*.tsx" | grep -v "__tests__"
```

For each file, check:
- Does it render different UI based on `user`, `isAuthenticated`, or `user.is_staff`?
- Is the component server-rendered or client-rendered (`'use client'` directive)?
- Would a mismatch between SSR output and client hydration cause a React error?

- [ ] **Step 2: Apply hydration guard to components with auth-conditional rendering**

The `header.tsx` pattern is the reference implementation — follow it exactly:

```typescript
'use client';

import { useHydration } from '@/lib/hooks/use-hydration';
import { useAuthStore } from '@/store/auth-store';
import { Skeleton } from '@/components/ui/skeleton';

export function SomeComponent() {
  const isHydrated = useHydration();
  const user = useAuthStore((state) => state.user);

  // Prevent hydration mismatch — auth state is unavailable during SSR
  if (!isHydrated) {
    return <Skeleton className="h-10 w-full" />;
  }

  // Safe to use user here — localStorage has been read
  return user?.is_staff ? <AdminSection /> : <UserSection />;
}
```

Apply this pattern to every component where auth state affects the initial render. Do NOT apply to components that only use auth state inside event handlers or effects (those are safe — they run client-side only).

- [ ] **Step 3: Verify no new hydration warnings in build output**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run build 2>&1 | grep -i "hydrat"
```

Expected: no hydration warnings

- [ ] **Step 4: Verify linting and type-check pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend && npm run lint && npm run type-check
```

Expected: zero errors

---

## Task 10: Password Complexity Validator

**Context:** `condominios_manager/settings.py:166-179` configures four Django password validators: `UserAttributeSimilarityValidator`, `MinimumLengthValidator` (default: 8 chars), `CommonPasswordValidator`, and `NumericPasswordValidator`. For a financial property management system accessible via the web, the Django defaults are insufficient — they do not require mixed case or digits. A custom validator enforcing uppercase + lowercase + digit requirements addresses this without third-party dependencies.

**Files:**
- Create: `core/validators/password_validator.py`
- Modify: `condominios_manager/settings.py`
- Create: `tests/unit/test_password_validator.py`

- [ ] **Step 1: Write failing tests for the validator**

Create `tests/unit/test_password_validator.py`:

```python
import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


pytestmark = [pytest.mark.unit]


class TestPasswordComplexityValidator:
    """Unit tests for PasswordComplexityValidator."""

    def test_accepts_password_with_upper_lower_digit(self) -> None:
        # Should not raise
        validate_password("Secur3Pass")

    def test_rejects_password_without_uppercase(self) -> None:
        with pytest.raises(ValidationError, match="maiúscula"):
            validate_password("secur3pass")

    def test_rejects_password_without_lowercase(self) -> None:
        with pytest.raises(ValidationError, match="minúscula"):
            validate_password("SECUR3PASS")

    def test_rejects_password_without_digit(self) -> None:
        with pytest.raises(ValidationError, match="número"):
            validate_password("SecurePass")

    def test_accepts_password_with_special_chars(self) -> None:
        # Special chars are allowed but not required
        validate_password("Secur3P@ss!")

    def test_get_help_text_returns_string(self) -> None:
        from core.validators.password_validator import PasswordComplexityValidator

        validator = PasswordComplexityValidator()
        help_text = validator.get_help_text()
        assert isinstance(help_text, str)
        assert len(help_text) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios && python -m pytest tests/unit/test_password_validator.py -v
```

Expected: FAIL — `PasswordComplexityValidator` does not exist yet

- [ ] **Step 3: Implement the validator**

Create `core/validators/password_validator.py`:

```python
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    """
    Validates that the password contains at least one uppercase letter,
    one lowercase letter, and one digit.
    """

    def validate(self, password: str, user: object = None) -> None:
        errors: list[ValidationError] = []

        if not re.search(r"[A-Z]", password):
            errors.append(
                ValidationError(
                    _("A senha deve conter pelo menos uma letra maiúscula."),
                    code="password_no_upper",
                )
            )

        if not re.search(r"[a-z]", password):
            errors.append(
                ValidationError(
                    _("A senha deve conter pelo menos uma letra minúscula."),
                    code="password_no_lower",
                )
            )

        if not re.search(r"\d", password):
            errors.append(
                ValidationError(
                    _("A senha deve conter pelo menos um número."),
                    code="password_no_digit",
                )
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self) -> str:
        return _(
            "A senha deve conter pelo menos uma letra maiúscula, "
            "uma letra minúscula e um número."
        )
```

- [ ] **Step 4: Register the validator in settings**

In `condominios_manager/settings.py`, add to `AUTH_PASSWORD_VALIDATORS`:

```python
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "core.validators.password_validator.PasswordComplexityValidator",
    },
]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios && python -m pytest tests/unit/test_password_validator.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Run ruff and mypy**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios && ruff check core/validators/password_validator.py && ruff format --check core/validators/password_validator.py && mypy core/validators/password_validator.py
```

Expected: zero errors

---

## Task 11: Admin URL Obfuscation

**Context:** `condominios_manager/urls.py:51` registers the Django admin at the predictable path `admin/`. This is a well-known target for automated brute-force attacks. While the admin requires authentication, moving it to a non-obvious URL reduces the attack surface area. The project already uses `python-decouple` for all configuration, so the admin URL path should come from an env var with a safe fallback for development.

**Files:**
- Modify: `condominios_manager/urls.py`
- Modify: `.env.example` (add `ADMIN_URL` variable)

- [ ] **Step 1: Update urls.py to read admin path from env**

Current line in `condominios_manager/urls.py`:
```python
path("admin/", admin.site.urls),
```

Updated:
```python
from decouple import config as env_config

# Admin URL is configurable to reduce brute-force attack surface.
# In production, set ADMIN_URL to a non-obvious path in .env
# (e.g., ADMIN_URL=secretpanel123/ — must end with /)
path(env_config("ADMIN_URL", default="admin/"), admin.site.urls),
```

Note: `decouple.config` is already imported at the top of `settings.py` under the alias `config`. In `urls.py`, check whether `config` is already imported. If not, add the import. Use `env_config` as the local alias to avoid shadowing any existing `config` name in the file.

- [ ] **Step 2: Add `ADMIN_URL` to `.env.example`**

Find and read the `.env.example` file, then add:
```bash
# Admin panel URL path — change in production to a non-obvious value (must end with /)
# Default: admin/ (development only)
ADMIN_URL=admin/
```

- [ ] **Step 3: Run ruff and mypy on urls.py**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios && ruff check condominios_manager/urls.py && ruff format --check condominios_manager/urls.py && mypy condominios_manager/urls.py
```

Expected: zero errors

---

## Task 12: Bare Exception Cleanup in Views and Auth

**Context:** `core/views.py:375` and `core/views.py:468` use `except Exception:` as catch-all handlers. `core/auth.py:111` also uses `except Exception:`. While broad exception handlers are sometimes appropriate for top-level safety nets, these three cases can be made more specific:

- `views.py:375` (contract generation task dispatch): catches any error from `generate_contract_pdf.delay()`. The only expected failures are Celery connection errors (`kombu.exceptions.OperationalError`) or import errors. A broad `except Exception` is acceptable here as a task dispatch safety net, but the log message should include the exception type.
- `views.py:468` (due date change fallthrough): This is the last `except` in a chain that already handles `ValueError`, `ValidationError`, `DatabaseError`, and `IntegrityError`. The only remaining cases are truly unexpected. Log the exception class for debugging but keep broad catch as a safety net.
- `auth.py:111` (OAuth token generation): catches errors from `get_tokens_for_user()` and `OAuthExchangeCode.objects.create()`. The specific exceptions are `django.db.utils.DatabaseError` for the ORM call and potentially `KeyError`/`AttributeError` for token generation. Since this is a redirect-based flow (not JSON API), a broad catch with logging is acceptable here too.

The goal is not to remove these handlers but to ensure they log enough information for debugging and to narrow the scope where the specific exception type is known.

**Files:**
- Modify: `core/views.py` (lines 375 and 468)
- Modify: `core/auth.py` (line 111)

- [ ] **Step 1: Read the three exception blocks in full context**

Read `core/views.py` lines 362–382 (contract dispatch block) and lines 426–473 (due date change block), then read `core/auth.py` lines 88–114 (OAuth callback).

- [ ] **Step 2: Narrow `views.py:375` — contract dispatch**

The contract dispatch `except Exception:` is catching errors from `generate_contract_pdf.delay()`. This is a Celery task dispatch. The failure modes are:

- `kombu.exceptions.OperationalError` — broker unreachable
- `celery.exceptions.CeleryError` — general Celery errors
- Any other unexpected error

Since Celery exceptions require importing `kombu` (a Celery dependency), use a two-stage catch:

```python
try:
    from core.tasks import generate_contract_pdf

    task = generate_contract_pdf.delay(lease.id)
    return Response(
        {"task_id": task.id, "status": "processing"},
        status=status.HTTP_202_ACCEPTED,
    )
except OSError:
    logger.exception("Broker connection error during contract task dispatch")
    return Response(
        {"error": "Falha ao iniciar geração do contrato."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
except Exception:
    logger.exception("Unexpected error during contract task dispatch")
    return Response(
        {"error": "Falha ao iniciar geração do contrato."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
```

- [ ] **Step 3: Narrow `views.py:468` — due date change fallthrough**

This `except Exception:` is already the last handler in a chain covering `ValueError`, `ValidationError`, `DatabaseError`, `IntegrityError`. It genuinely catches the unexpected. The only improvement needed is logging the exception class for easier debugging. The current code already calls `logger.exception(...)` which does this via the traceback. No change needed here — this handler is already correct. Mark as verified (no code change required).

- [ ] **Step 4: Narrow `auth.py:111` — OAuth token generation**

The `except Exception:` in `GoogleOAuthCallbackView.handle_callback()` wraps `get_tokens_for_user()` and `OAuthExchangeCode.objects.create()`. The `logger.exception()` call already logs the full traceback including exception type. The handler is a redirect-flow safety net — a broad catch here is appropriate and intentional. Verify the log call is present and no change is needed beyond confirming it logs correctly. Mark as verified.

- [ ] **Step 5: Run ruff and mypy**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios && ruff check core/views.py core/auth.py && ruff format --check core/views.py core/auth.py && mypy core/views.py core/auth.py
```

Expected: zero errors

- [ ] **Step 6: Run affected tests**

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios && python -m pytest tests/integration/test_lease_actions.py -v
```

Expected: all tests PASS

---

## Verification Checklist

After implementing all tasks, run the full verification suite:

### Frontend

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios/frontend

# Lint
npm run lint

# Type check
npm run type-check

# Build (catches SSR errors and metadata warnings)
npm run build

# Unit tests
npm run test:unit
```

Expected: zero lint errors, zero type errors, clean build with no hydration warnings, all unit tests passing.

### Backend

```bash
cd /c/Users/alvar/git/personal/gerenciador_condominios

# Lint and format check
ruff check core/ condominios_manager/
ruff format --check core/ condominios_manager/

# Type checking
mypy core/

# Unit tests (password validator + affected views)
python -m pytest tests/unit/test_password_validator.py -v
python -m pytest tests/integration/test_lease_actions.py -v
```

Expected: zero ruff errors, zero mypy errors, all tests PASS.

### Per-Task Summary

| Task | Files Changed | Verification Command |
|------|--------------|---------------------|
| 1 — Token refresh soft redirect | `frontend/lib/api/client.ts` | `npm run lint && npm run type-check` |
| 2 — Login error handling | `frontend/app/login/page.tsx` | `npm run lint && npm run type-check` |
| 3 — Exponential backoff | `frontend/lib/config/query-client.ts` | `npm run lint && npm run type-check` |
| 4 — Middleware redirect validation | `frontend/middleware.ts` | `npm run lint && npm run type-check` |
| 5 — React.memo list components | `frontend/components/layouts/sidebar.tsx` | `npm run lint && npm run type-check` |
| 6 — Console cleanup | Multiple frontend files, ESLint config | `npm run lint` |
| 7 — Accessibility icon labels | Multiple component files | `npm run lint && npm run type-check` |
| 8 — SEO metadata | `frontend/app/layout.tsx` | `npm run build` |
| 9 — Hydration guard | Layout and page components | `npm run build` (no hydration warnings) |
| 10 — Password validator | `core/validators/password_validator.py`, `settings.py` | `pytest tests/unit/test_password_validator.py` |
| 11 — Admin URL obfuscation | `condominios_manager/urls.py`, `.env.example` | `ruff check && mypy` |
| 12 — Bare exception cleanup | `core/views.py`, `core/auth.py` | `ruff check && mypy && pytest` |
