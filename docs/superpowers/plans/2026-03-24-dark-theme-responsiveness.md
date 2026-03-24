# Dark/Light Theme + Responsiveness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement system-aware dark/light theme with teal/emerald palette and fix mobile responsiveness across the entire frontend.

**Architecture:** Replace neutral CSS variable palette with teal/emerald brand colors (OKLch), wire up `next-themes` ThemeProvider for system detection + manual toggle, replace ~342 hardcoded Tailwind color classes with semantic tokens, and fix responsive breakpoints on dialogs, tables, filters, and grids.

**Tech Stack:** Next.js 14, Tailwind CSS v4, next-themes, shadcn/ui, OKLch color space

**Spec:** `docs/superpowers/specs/2026-03-24-dark-theme-responsiveness-design.md`

---

## Task 1: Theme Infrastructure — globals.css palette + tailwind config cleanup

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`

This is the highest-risk task. It replaces the entire color system. Must be verified with `npm run build` before proceeding.

- [ ] **Step 1: Delete the HSL `@layer base` block AND the old base styles block from globals.css**

The file has THREE `@layer base` blocks. Delete TWO of them:

1. **Delete lines 7-53** (including trailing blank line): The HSL `:root`/`.dark` variable block (`@layer base { :root { --background: 0 0% 100%; ...`). This is duplicated by OKLch blocks below.

2. **Delete lines 54-62**: The OLD base styles block (`@layer base { * { @apply border-border; } body { @apply bg-background text-foreground; font-feature-settings: ... } }`). This is duplicated by the NEWER block at lines 171-178 which also includes `outline-ring/50`.

**Keep lines 171-178** (`@layer base { * { @apply border-border outline-ring/50; } body { @apply bg-background text-foreground; } }`) — this is the Tailwind v4 version. If `font-feature-settings` is still needed, merge it into the body rule at line 176.

After this step, only ONE `@layer base` block should remain (the one near line 171).

- [ ] **Step 2: Replace `:root` OKLch variables (lines 102-135) with teal/emerald palette**

Replace the current `:root` block with:

```css
:root {
  --radius: 0.625rem;
  --background: oklch(0.985 0.002 240);
  --foreground: oklch(0.15 0.01 260);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.15 0.01 260);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.15 0.01 260);
  --primary: oklch(0.55 0.15 175);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.965 0.015 175);
  --secondary-foreground: oklch(0.25 0.05 175);
  --muted: oklch(0.96 0.005 260);
  --muted-foreground: oklch(0.55 0.01 260);
  --accent: oklch(0.94 0.03 175);
  --accent-foreground: oklch(0.25 0.05 175);
  --destructive: oklch(0.577 0.245 27.325);
  --destructive-foreground: oklch(0.985 0 0);
  --border: oklch(0.91 0.005 260);
  --input: oklch(0.91 0.005 260);
  --ring: oklch(0.55 0.15 175);
  --success: oklch(0.60 0.17 155);
  --success-foreground: oklch(0.985 0 0);
  --warning: oklch(0.75 0.17 80);
  --warning-foreground: oklch(0.25 0.05 80);
  --info: oklch(0.60 0.15 240);
  --info-foreground: oklch(0.985 0 0);
  --chart-1: oklch(0.55 0.15 175);
  --chart-2: oklch(0.60 0.17 155);
  --chart-3: oklch(0.75 0.17 80);
  --chart-4: oklch(0.60 0.15 240);
  --chart-5: oklch(0.577 0.245 27.325);
  --sidebar: oklch(0.98 0.005 175);
  --sidebar-foreground: oklch(0.15 0.01 260);
  --sidebar-primary: oklch(0.45 0.15 175);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.94 0.03 175);
  --sidebar-accent-foreground: oklch(0.25 0.05 175);
  --sidebar-border: oklch(0.91 0.005 260);
  --sidebar-ring: oklch(0.55 0.15 175);
}
```

- [ ] **Step 3: Replace `.dark` OKLch variables (lines 137-169) with dark palette**

Replace the current `.dark` block with:

```css
.dark {
  --background: oklch(0.13 0.01 260);
  --foreground: oklch(0.93 0.005 260);
  --card: oklch(0.18 0.01 260);
  --card-foreground: oklch(0.93 0.005 260);
  --popover: oklch(0.18 0.01 260);
  --popover-foreground: oklch(0.93 0.005 260);
  --primary: oklch(0.70 0.15 175);
  --primary-foreground: oklch(0.15 0.02 175);
  --secondary: oklch(0.22 0.02 260);
  --secondary-foreground: oklch(0.90 0.005 260);
  --muted: oklch(0.22 0.01 260);
  --muted-foreground: oklch(0.65 0.01 260);
  --accent: oklch(0.25 0.03 175);
  --accent-foreground: oklch(0.90 0.01 175);
  --destructive: oklch(0.65 0.2 25);
  --destructive-foreground: oklch(0.985 0 0);
  --border: oklch(1 0 0 / 12%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.70 0.15 175);
  --success: oklch(0.70 0.17 155);
  --success-foreground: oklch(0.15 0.03 155);
  --warning: oklch(0.80 0.15 80);
  --warning-foreground: oklch(0.20 0.05 80);
  --info: oklch(0.70 0.15 240);
  --info-foreground: oklch(0.15 0.03 240);
  --chart-1: oklch(0.70 0.15 175);
  --chart-2: oklch(0.70 0.17 155);
  --chart-3: oklch(0.80 0.15 80);
  --chart-4: oklch(0.70 0.15 240);
  --chart-5: oklch(0.65 0.2 25);
  --sidebar: oklch(0.16 0.01 260);
  --sidebar-foreground: oklch(0.93 0.005 260);
  --sidebar-primary: oklch(0.70 0.15 175);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.25 0.03 175);
  --sidebar-accent-foreground: oklch(0.90 0.01 175);
  --sidebar-border: oklch(1 0 0 / 12%);
  --sidebar-ring: oklch(0.70 0.15 175);
}
```

- [ ] **Step 4: Add new tokens to `@theme inline` block**

Add these lines to the existing `@theme inline` block in `globals.css`:

```css
--color-success: var(--success);
--color-success-foreground: var(--success-foreground);
--color-warning: var(--warning);
--color-warning-foreground: var(--warning-foreground);
--color-info: var(--info);
--color-info-foreground: var(--info-foreground);
--color-destructive-foreground: var(--destructive-foreground);
```

- [ ] **Step 5: Fix `hsl(var(...))` wrappers in WYSIWYG CSS**

In `globals.css`, replace all `hsl(var(--token))` with bare `var(--token)` in WYSIWYG rules:

- Line ~208: `color: hsl(var(--muted-foreground))` → `color: var(--muted-foreground)`
- Line ~276: `border: 1px solid hsl(var(--border))` → `border: 1px solid var(--border)`
- Line ~281: `background: hsl(var(--muted))` → `background: var(--muted)`
- Line ~287: `border-top: 1px solid hsl(var(--border))` → `border-top: 1px solid var(--border)`

- [ ] **Step 6: Make WYSIWYG desk area dark-aware**

In `globals.css`, change the desk area background:
- `.wysiwyg-editor-content { background-color: #f3f4f6; }` → `.wysiwyg-editor-content { background-color: var(--muted); }`

The paper area (`.ProseMirror`) keeps `background-color: #fff; color: #000` — this is intentional.

- [ ] **Step 7: Clean up tailwind.config.ts**

Delete the entire `theme.extend.colors` block (lines 19-53) and `theme.extend.borderRadius` block (lines 54-58) from `tailwind.config.ts`. The `@theme inline` block in `globals.css` is the sole source of truth for Tailwind v4.

Keep: `content`, `container`, `keyframes`, `animation`, and `plugins`.

Result should be:

Remove `darkMode: 'class'` as well — it's a no-op in Tailwind v4 (dark mode is handled by `@custom-variant dark` in `globals.css`).

```ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

- [ ] **Step 8: Verify `@custom-variant dark` compatibility**

Check that `@custom-variant dark (&:is(.dark *))` in `globals.css` (line 5) works with next-themes. The `.dark` class is on `<html>`, so `&:is(.dark *)` matches all descendants. The `body` base styles use `@apply bg-background text-foreground` which reads CSS variables directly (not via `dark:` variant), so body theming works regardless. If any issue is found, update to `@custom-variant dark (&:where(.dark, .dark *))`.

- [ ] **Step 9: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors. Colors render correctly.

- [ ] **Step 10: Commit**

```bash
git add frontend/app/globals.css frontend/tailwind.config.ts
git commit -m "style(frontend): replace color palette with teal/emerald OKLch tokens"
```

---

## Task 2: ThemeProvider + ThemeToggle + Layout

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/providers.tsx`
- Create: `frontend/components/theme-toggle.tsx`
- Modify: `frontend/components/layouts/header.tsx`
- Modify: `frontend/components/layouts/main-layout.tsx`
- Modify: `frontend/components/layouts/sidebar.tsx`

- [ ] **Step 1: Add suppressHydrationWarning to layout.tsx**

In `frontend/app/layout.tsx`, change:
```tsx
<html lang="pt-BR">
```
to:
```tsx
<html lang="pt-BR" suppressHydrationWarning>
```

- [ ] **Step 2: Wrap with ThemeProvider in providers.tsx**

In `frontend/app/providers.tsx`, add `ThemeProvider` as the outermost wrapper (must be outside `QueryClientProvider` for SSR correctness):

```tsx
'use client';

import { ThemeProvider } from 'next-themes';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/sonner';
import { queryClient } from '@/lib/config/query-client';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
```

- [ ] **Step 3: Create ThemeToggle component**

Create `frontend/components/theme-toggle.tsx`:

```tsx
'use client';

import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function ThemeToggle() {
  const { setTheme, theme } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Alternar tema</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')} className={theme === 'light' ? 'bg-accent' : ''}>
          <Sun className="mr-2 h-4 w-4" />
          <span>Claro</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')} className={theme === 'dark' ? 'bg-accent' : ''}>
          <Moon className="mr-2 h-4 w-4" />
          <span>Escuro</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')} className={theme === 'system' ? 'bg-accent' : ''}>
          <Monitor className="mr-2 h-4 w-4" />
          <span>Sistema</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 4: Add ThemeToggle to header.tsx and fix hardcoded colors**

In `frontend/components/layouts/header.tsx`:
1. Import `ThemeToggle`: `import { ThemeToggle } from '@/components/theme-toggle';`
2. Replace all `bg-white` with `bg-card` (lines 26, 58)
3. Add `<ThemeToggle />` before the notifications bell button

- [ ] **Step 5: Fix hardcoded colors in main-layout.tsx**

In `frontend/components/layouts/main-layout.tsx`:
- Line 30: `bg-white border-r` → `bg-card border-r`

- [ ] **Step 6: Fix hardcoded colors in sidebar.tsx**

In `frontend/components/layouts/sidebar.tsx`:
- Line 122: `bg-white` → `bg-card`

- [ ] **Step 7: Verify build + visual test**

Run: `cd frontend && npm run build`
Expected: Build succeeds. Theme toggle should work. Light/dark should switch properly.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/providers.tsx frontend/components/theme-toggle.tsx frontend/components/layouts/header.tsx frontend/components/layouts/main-layout.tsx frontend/components/layouts/sidebar.tsx
git commit -m "feat(frontend): add dark/light theme toggle with system detection"
```

---

## Task 3: Shared UI Components — Dialog + DataTable responsiveness

**Files:**
- Modify: `frontend/components/ui/dialog.tsx`
- Modify: `frontend/components/tables/data-table.tsx`

- [ ] **Step 1: Update DialogContent for mobile responsiveness**

In `frontend/components/ui/dialog.tsx` line 41, update the className string:
1. Add `max-h-[85vh] overflow-y-auto` for scroll on tall modals
2. Add responsive width: `mx-4 sm:mx-auto` with `max-w-[calc(100vw-2rem)] sm:max-w-lg` to prevent overflow on very narrow screens while keeping the existing `max-w-lg` on desktop

Updated line 41:
```
"fixed left-[50%] top-[50%] z-50 grid w-full max-w-[calc(100vw-2rem)] sm:max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 max-h-[85vh] overflow-y-auto data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg",
```

Note: Individual modals that override `max-w-lg` (e.g., `max-w-3xl`) should use the same responsive pattern: `max-w-[calc(100vw-2rem)] sm:max-w-2xl md:max-w-3xl`.

- [ ] **Step 2: Add horizontal scroll to DataTable**

In `frontend/components/tables/data-table.tsx`, wrap the `<Table>` in an overflow container. Change line 194:

From:
```tsx
<div className="rounded-md border">
  <Table>
```
To:
```tsx
<div className="rounded-md border overflow-x-auto">
  <Table>
```

- [ ] **Step 3: Fix DataTable pagination for mobile**

In `frontend/components/tables/data-table.tsx`, line 260 change:
```tsx
<div className="flex items-center justify-between">
```
to:
```tsx
<div className="flex flex-col sm:flex-row items-center justify-between gap-2">
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 5: Commit**

```bash
git add frontend/components/ui/dialog.tsx frontend/components/tables/data-table.tsx
git commit -m "style(frontend): improve dialog and data table mobile responsiveness"
```

---

## Task 4: Core Pages — Login, Error, Dashboard

**Files:**
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/app/global-error.tsx`
- Modify: `frontend/app/(dashboard)/page.tsx`

- [ ] **Step 1: Fix login page colors**

In `frontend/app/login/page.tsx`:
- Replace `bg-gradient-to-br from-blue-50 to-indigo-100` → `bg-gradient-to-br from-secondary to-accent`
- Replace `text-gray-800` → `text-foreground`

- [ ] **Step 2: Fix global-error page colors**

In `frontend/app/global-error.tsx`:
- Replace `text-gray-600` → `text-muted-foreground`
- Replace `bg-blue-500 hover:bg-blue-600` → `bg-primary hover:bg-primary/90`
- Ensure `text-white` on the button becomes `text-primary-foreground`

- [ ] **Step 3: Fix dashboard page colors**

In `frontend/app/(dashboard)/page.tsx`:
- Replace `text-gray-600` → `text-muted-foreground`

- [ ] **Step 4: Commit**

```bash
git add frontend/app/login/page.tsx frontend/app/global-error.tsx frontend/app/(dashboard)/page.tsx
git commit -m "style(frontend): apply theme tokens to login, error, and dashboard pages"
```

---

## Task 5: Dashboard Widgets — theme + responsive grids

**Files:**
- Modify: `frontend/app/(dashboard)/_components/late-payments-alert.tsx`
- Modify: `frontend/app/(dashboard)/_components/financial-summary-widget.tsx`
- Modify: `frontend/app/(dashboard)/_components/lease-metrics-widget.tsx`
- Modify: `frontend/app/(dashboard)/_components/tenant-statistics-widget.tsx`
- Modify: `frontend/app/(dashboard)/_components/building-statistics-chart.tsx`

- [ ] **Step 1: Fix late-payments-alert.tsx**

Replace hardcoded colors with semantic tokens:
- `border-green-200 bg-green-50` → `border-success/20 bg-success/5`
- `text-green-600` → `text-success`
- `text-green-800` → `text-success`
- `border-red-200` → `border-destructive/20`
- `text-red-500`, `text-red-600` → `text-destructive`

Fix flex layouts for mobile:
- Headers with `flex items-center justify-between` → `flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2`

- [ ] **Step 2: Fix financial-summary-widget.tsx**

Replace hardcoded colors:
- `text-green-600` → `text-success`
- `text-blue-600` → `text-primary`
- `text-orange-500` → `text-warning`
- `text-red-600` → `text-destructive`

Fix grid: ensure `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` pattern.
Fix title: `text-3xl` → `text-xl sm:text-2xl md:text-3xl`

- [ ] **Step 3: Fix lease-metrics-widget.tsx**

Replace all hardcoded colors following the same pattern.
Fix grid breakpoints: add `sm:` where missing.

- [ ] **Step 4: Fix tenant-statistics-widget.tsx**

Replace all hardcoded colors following the same pattern.

- [ ] **Step 5: Fix building-statistics-chart.tsx**

Replace all hardcoded colors following the same pattern.
Fix grid: `grid-cols-2 md:grid-cols-4` → `grid-cols-2 sm:grid-cols-3 md:grid-cols-4`

- [ ] **Step 6: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 7: Commit**

```bash
git add frontend/app/\(dashboard\)/_components/
git commit -m "style(frontend): apply theme tokens and responsive grids to dashboard widgets"
```

---

## Task 6: CRUD Pages — Buildings, Apartments, Tenants, Furniture

**Files:**
- Modify: `frontend/app/(dashboard)/buildings/page.tsx`
- Modify: `frontend/app/(dashboard)/apartments/page.tsx`
- Modify: `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx`
- Modify: `frontend/app/(dashboard)/tenants/page.tsx`
- Modify: `frontend/app/(dashboard)/furniture/page.tsx`
- Modify: `frontend/app/(dashboard)/settings/page.tsx`

- [ ] **Step 1: Fix buildings/page.tsx**

Replace hardcoded colors:
- `text-gray-600` → `text-muted-foreground`
- `bg-blue-50 border-blue-200` → `bg-primary/5 border-primary/20`
- `text-blue-700` → `text-primary`

Fix filter layout: replace `flex gap-4 flex-wrap` + `min-w-[...]` with `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`. Remove `min-w-` constraints.

- [ ] **Step 2: Fix apartments/page.tsx**

Replace hardcoded colors (5 occurrences).
Fix filter layout same as buildings.

- [ ] **Step 3: Fix apartment-form-modal.tsx**

Replace hardcoded color (1 occurrence).

- [ ] **Step 4: Fix tenants/page.tsx**

Replace hardcoded colors (10 occurrences).
Fix filter layout: remove `min-w-[250px]`, use grid.

- [ ] **Step 5: Fix furniture/page.tsx**

Replace hardcoded colors (3 occurrences).
Fix filter layout.

- [ ] **Step 6: Fix settings/page.tsx**

Replace hardcoded colors (2 occurrences).

- [ ] **Step 7: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 8: Commit**

```bash
git add frontend/app/\(dashboard\)/buildings/ frontend/app/\(dashboard\)/apartments/ frontend/app/\(dashboard\)/tenants/ frontend/app/\(dashboard\)/furniture/ frontend/app/\(dashboard\)/settings/
git commit -m "style(frontend): apply theme tokens and responsive filters to CRUD pages"
```

---

## Task 7: Lease Pages — theme + responsive

**Files:**
- Modify: `frontend/app/(dashboard)/leases/page.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/lease-table-columns.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/late-fee-modal.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/due-date-modal.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx`

- [ ] **Step 1: Fix leases/page.tsx**

Replace hardcoded colors (3 occurrences).
Fix filter layout.

- [ ] **Step 2: Fix lease-table-columns.tsx**

Replace hardcoded colors (12 occurrences — mostly status badges).
Use pattern: `bg-success/10 text-success`, `bg-destructive/10 text-destructive`, `bg-warning/10 text-warning`, `bg-info/10 text-info`.

- [ ] **Step 3: Fix late-fee-modal.tsx**

Replace hardcoded colors (19 occurrences).
Fix flex layouts for mobile.

- [ ] **Step 4: Fix due-date-modal.tsx**

Replace hardcoded colors (23 occurrences).
Fix flex layouts for mobile.

- [ ] **Step 5: Fix contract-generate-modal.tsx**

Replace hardcoded colors (23 occurrences).
Fix flex layouts for mobile.

- [ ] **Step 6: Fix lease-form-modal.tsx**

Replace hardcoded color (1 occurrence).

- [ ] **Step 7: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 8: Commit**

```bash
git add frontend/app/\(dashboard\)/leases/
git commit -m "style(frontend): apply theme tokens and responsiveness to lease pages"
```

---

## Task 8: Financial Dashboard + Cash Flow

**Files:**
- Modify: `frontend/app/(dashboard)/financial/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/balance-cards.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/expense-summary-card.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/income-summary-card.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/overdue-section.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/upcoming-installments.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx`
- Modify: `frontend/app/(dashboard)/financial/_components/person-month-summary.tsx`

- [ ] **Step 1: Fix financial/page.tsx**

Replace hardcoded colors (1 occurrence).

- [ ] **Step 2: Fix balance-cards.tsx**

Replace hardcoded colors:
- `text-blue-600` → `text-info`
- `text-amber-500` → `text-warning`
- `text-green-600` → `text-success`
- `text-orange-500` → `text-warning`
- `text-red-600` → `text-destructive`

Fix grid: ensure `sm:` breakpoints.

- [ ] **Step 3: Fix expense-summary-card.tsx**

This file has the most hardcoded colors (~18 occurrences). Replace ALL:
- `text-red-600` → `text-destructive`
- `text-green-600` → `text-success`
- `text-orange-600` → `text-warning`
- `bg-gray-200` → `bg-muted`
- `bg-green-500`, `bg-blue-500`, `bg-amber-500` → `bg-success`, `bg-primary`, `bg-warning`
- `text-gray-600` → `text-muted-foreground`
- `text-blue-600` → `text-info`
- `text-purple-600` → `text-primary`

- [ ] **Step 4: Fix income-summary-card.tsx**

Replace hardcoded colors (3 occurrences).

- [ ] **Step 5: Fix cash-flow-chart.tsx**

Replace Tailwind classes:
- `text-green-600` → `text-success`
- `text-red-600` → `text-destructive`
- `text-blue-600` → `text-info`

Replace inline Recharts colors with CSS variable references:
- `fill="#22c55e"` → `fill="var(--success)"`
- `fill="#ef4444"` → `fill="var(--destructive)"`
- `stroke="#3b82f6"` → `stroke="var(--info)"`

- [ ] **Step 6: Fix overdue-alerts.tsx and overdue-section.tsx**

Replace hardcoded colors (7 + 5 occurrences):
- `border-amber-200 bg-amber-50/50` → `border-warning/20 bg-warning/5`
- `text-amber-800` → `text-warning`
- `text-red-600` → `text-destructive`
- `text-green-600` → `text-success`
- `text-blue-600` → `text-info`

- [ ] **Step 7: Fix upcoming-installments.tsx, person-summary-cards.tsx, person-month-summary.tsx**

Replace all hardcoded colors following the same semantic token pattern.

- [ ] **Step 8: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 9: Commit**

```bash
git add frontend/app/\(dashboard\)/financial/_components/ frontend/app/\(dashboard\)/financial/page.tsx
git commit -m "style(frontend): apply theme tokens to financial dashboard components"
```

---

## Task 9: Financial Subpages — Daily, Expenses, Persons, etc.

**Files:**
- Modify: All files in `frontend/app/(dashboard)/financial/daily/_components/`
- Modify: All files in `frontend/app/(dashboard)/financial/expenses/` (page + _components/ + details/)
- Modify: `frontend/app/(dashboard)/financial/incomes/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/rent-payments/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/persons/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/person-payments/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/person-incomes/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/categories/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/employees/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/settings/page.tsx`
- Modify: `frontend/app/(dashboard)/financial/simulator/_components/` (all files)

- [ ] **Step 1: Fix daily control components**

Files: `daily-summary-cards.tsx`, `daily-timeline.tsx`, `daily-balance-chart.tsx`, `day-detail-drawer.tsx`

Replace all hardcoded colors (~36 occurrences total):
- Green → `text-success` / `bg-success/10`
- Red → `text-destructive` / `bg-destructive/10`
- Blue → `text-info` / `bg-info/10`
- Orange/Amber → `text-warning` / `bg-warning/10`
- Gray → `text-muted-foreground` / `bg-muted`

Fix grids: add `sm:` breakpoints where missing.

- [ ] **Step 2: Fix expenses pages and components**

Files: `expenses/page.tsx`, `expense-columns.tsx`, `expense-list-table.tsx`, `installments-drawer.tsx`, `expenses/details/page.tsx`, `detail-header.tsx`, `expense-detail-table.tsx`, `expense-accordion.tsx`, `expense-edit-modal.tsx`

Replace all hardcoded colors.
Fix filter layouts.

- [ ] **Step 3: Fix remaining financial subpages**

Files: `incomes/page.tsx`, `rent-payments/page.tsx`, `persons/page.tsx`, `person-payments/page.tsx`, `person-incomes/page.tsx` (+ form modals), `categories/page.tsx`, `employees/page.tsx`, `settings/page.tsx`

Replace all hardcoded colors.

- [ ] **Step 4: Fix simulator components**

Files: `scenario-card.tsx`, `comparison-table.tsx`, `comparison-chart.tsx`, `impact-summary.tsx`

Replace all hardcoded colors.

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/app/\(dashboard\)/financial/
git commit -m "style(frontend): apply theme tokens to all financial subpages"
```

---

## Task 10: Contract Template + Editor Extensions + Search

**Files:**
- Modify: `frontend/app/(dashboard)/contract-template/page.tsx`
- Modify: `frontend/components/contract-editor/extensions/page-break.tsx`
- Modify: `frontend/components/contract-editor/extensions/template-variable.tsx`
- Modify: `frontend/components/search/global-search.tsx`

- [ ] **Step 1: Fix contract-template/page.tsx**

This file has ~49 hardcoded color occurrences — mostly toolbar buttons and formatting controls. Replace:
- `bg-white` → `bg-card`
- `text-gray-*` → `text-muted-foreground` or `text-foreground`
- `bg-gray-*` → `bg-muted`
- `border-gray-*` → `border-border`
- Status/action colors → semantic tokens

**Note:** The WYSIWYG paper area (`ProseMirror`) stays white. Only toolbar and surrounding UI get dark mode.

- [ ] **Step 2: Fix page-break.tsx extension**

Replace:
- `border-gray-400` → `border-border`
- `text-gray-500` → `text-muted-foreground`
- `bg-gray-100` → `bg-muted`

- [ ] **Step 3: Fix template-variable.tsx extension**

Replace:
- `bg-blue-100 text-blue-800 border-blue-200` → `bg-info/10 text-info border-info/20`

- [ ] **Step 4: Fix global-search.tsx**

Replace icon colors — these are entity-type indicators that need to remain visually distinct. Use semantic tokens with opacity:
- `text-blue-500` (building) → `text-info`
- `text-green-500` (apartment) → `text-success`
- `text-orange-500` (tenant) → `text-warning`
- `text-purple-500` (lease) → `text-primary`
- `text-pink-500` (furniture) → `text-destructive`

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/app/\(dashboard\)/contract-template/ frontend/components/contract-editor/ frontend/components/search/
git commit -m "style(frontend): apply theme tokens to contract template, editor, and search"
```

---

## Task 11: Final Verification + Lint + Type Check

**Files:** None (verification only)

- [ ] **Step 1: Run full build**

Run: `cd frontend && npm run build`
Expected: Clean build, zero errors.

- [ ] **Step 2: Run linter**

Run: `cd frontend && npm run lint`
Expected: No errors.

- [ ] **Step 3: Run type check**

Run: `cd frontend && npm run type-check`
Expected: No errors.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "style(frontend): fix remaining theme and responsiveness issues"
```
