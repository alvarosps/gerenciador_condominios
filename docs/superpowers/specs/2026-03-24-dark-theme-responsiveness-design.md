# Dark/Light Theme + Responsiveness Design

**Date:** 2026-03-24
**Status:** Approved
**Scope:** Frontend (Next.js 14 + shadcn/ui + Tailwind CSS v4)

## Summary

Implement system-aware dark/light theme with teal/emerald brand palette across the entire frontend, combined with responsiveness fixes for mobile/tablet viewports. The project already has `next-themes` installed, CSS variables for light/dark defined, and Tailwind `darkMode: 'class'` configured — but none of it is wired together, colors are mostly neutral gray, and ~342 hardcoded color values bypass the token system.

## Goals

1. **System-aware theming**: Detect OS preference (Windows dark mode), allow manual override (light/dark/system)
2. **Teal/emerald brand palette**: Replace neutral gray palette with a property-management-appropriate color scheme
3. **Token consistency**: Replace all hardcoded Tailwind colors (`bg-white`, `text-gray-*`, etc.) with semantic design tokens
4. **Mobile-first responsiveness**: Fix dialogs, tables, filters, grids, and typography for mobile/tablet

## Non-Goals

- Redesigning page layouts or component structure
- Adding new features or pages
- Changing backend behavior
- Making the WYSIWYG contract editor dark (it simulates paper — stays light)
- Theming Ant Design components — Ant Design has its own theming system (`ConfigProvider` + `theme.darkAlgorithm`); this is a separate effort if needed. For now, any Ant Design components will remain visually light. If this creates jarring inconsistency, a follow-up task will address Ant Design theming via `ConfigProvider`.

---

## Part 1: Theme Infrastructure

### 1.1 — ThemeProvider Setup

**File:** `app/providers.tsx`

Wrap the app with `next-themes` ThemeProvider:

```tsx
import { ThemeProvider } from 'next-themes';

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

**File:** `app/layout.tsx`

Add `suppressHydrationWarning` to `<html>` (required by next-themes to prevent SSR mismatch):

```tsx
<html lang="pt-BR" suppressHydrationWarning>
```

### 1.2 — Color Palette (OKLch)

**CRITICAL:** `globals.css` currently has THREE conflicting blocks defining the same variables:
1. Lines 7-52: `@layer base` with HSL values (`:root` and `.dark`) — **DELETE entirely**
2. Lines 102-135: bare `:root` with OKLch values — **REPLACE with new palette**
3. Lines 137-169: bare `.dark` with OKLch values — **REPLACE with new palette**

The `@layer base` HSL block (lines 7-52) MUST be deleted entirely. The new OKLch values go in the bare `:root`/`.dark` blocks (lines 102-169). If only one block is removed, residual HSL variables may win due to cascade specificity.

**Light Theme (`:root`):**

| Token | Value | Description |
|-------|-------|-------------|
| `--background` | `oklch(0.985 0.002 240)` | Warm off-white with slight blue tint |
| `--foreground` | `oklch(0.15 0.01 260)` | Near-black slate |
| `--card` | `oklch(1 0 0)` | Pure white for cards |
| `--card-foreground` | `oklch(0.15 0.01 260)` | Same as foreground |
| `--popover` | `oklch(1 0 0)` | White |
| `--popover-foreground` | `oklch(0.15 0.01 260)` | Same as foreground |
| `--primary` | `oklch(0.55 0.15 175)` | Teal-600 — main brand color |
| `--primary-foreground` | `oklch(0.985 0 0)` | White text on primary |
| `--secondary` | `oklch(0.965 0.015 175)` | Teal-50 — light teal tint |
| `--secondary-foreground` | `oklch(0.25 0.05 175)` | Dark teal text |
| `--muted` | `oklch(0.96 0.005 260)` | Light gray-blue |
| `--muted-foreground` | `oklch(0.55 0.01 260)` | Medium gray for secondary text |
| `--accent` | `oklch(0.94 0.03 175)` | Light teal for hover states |
| `--accent-foreground` | `oklch(0.25 0.05 175)` | Dark teal |
| `--destructive` | `oklch(0.577 0.245 27.325)` | Red (unchanged) |
| `--border` | `oklch(0.91 0.005 260)` | Light gray border |
| `--input` | `oklch(0.91 0.005 260)` | Same as border |
| `--ring` | `oklch(0.55 0.15 175)` | Teal — focus ring matches primary |
| `--success` | `oklch(0.60 0.17 155)` | Green for positive states |
| `--success-foreground` | `oklch(0.985 0 0)` | White |
| `--warning` | `oklch(0.75 0.17 80)` | Amber for alerts |
| `--warning-foreground` | `oklch(0.25 0.05 80)` | Dark amber |
| `--info` | `oklch(0.60 0.15 240)` | Blue for informational |
| `--info-foreground` | `oklch(0.985 0 0)` | White |

**Dark Theme (`.dark`):**

| Token | Value | Description |
|-------|-------|-------------|
| `--background` | `oklch(0.13 0.01 260)` | Slate-950 — slightly blue, not pure black |
| `--foreground` | `oklch(0.93 0.005 260)` | Off-white text |
| `--card` | `oklch(0.18 0.01 260)` | Slate-900 — elevated surface |
| `--card-foreground` | `oklch(0.93 0.005 260)` | Off-white |
| `--popover` | `oklch(0.18 0.01 260)` | Same as card |
| `--popover-foreground` | `oklch(0.93 0.005 260)` | Off-white |
| `--primary` | `oklch(0.70 0.15 175)` | Teal-400 — brighter for dark bg |
| `--primary-foreground` | `oklch(0.15 0.02 175)` | Dark teal on primary buttons |
| `--secondary` | `oklch(0.22 0.02 260)` | Dark slate |
| `--secondary-foreground` | `oklch(0.90 0.005 260)` | Light text |
| `--muted` | `oklch(0.22 0.01 260)` | Dark muted background |
| `--muted-foreground` | `oklch(0.65 0.01 260)` | Medium gray text |
| `--accent` | `oklch(0.25 0.03 175)` | Dark teal for hover |
| `--accent-foreground` | `oklch(0.90 0.01 175)` | Light teal |
| `--destructive` | `oklch(0.65 0.2 25)` | Lighter red for dark bg |
| `--border` | `oklch(1 0 0 / 12%)` | Subtle white border |
| `--input` | `oklch(1 0 0 / 15%)` | Slightly stronger for inputs |
| `--ring` | `oklch(0.70 0.15 175)` | Teal focus ring |
| `--success` | `oklch(0.70 0.17 155)` | Brighter green |
| `--success-foreground` | `oklch(0.15 0.03 155)` | Dark green |
| `--warning` | `oklch(0.80 0.15 80)` | Brighter amber |
| `--warning-foreground` | `oklch(0.20 0.05 80)` | Dark amber |
| `--info` | `oklch(0.70 0.15 240)` | Brighter blue |
| `--info-foreground` | `oklch(0.15 0.03 240)` | Dark blue |

**Sidebar tokens** follow the same pattern — `--sidebar-primary` uses a slightly darker/lighter teal variant.

**Chart tokens** get teal-based colors that work in both themes.

### 1.3 — Tailwind Config + @theme

The `@theme inline` block in `globals.css` already maps CSS vars to Tailwind colors. Add new tokens:

```css
--color-success: var(--success);
--color-success-foreground: var(--success-foreground);
--color-warning: var(--warning);
--color-warning-foreground: var(--warning-foreground);
--color-info: var(--info);
--color-info-foreground: var(--info-foreground);
--color-destructive-foreground: var(--destructive-foreground);
```

**CRITICAL:** `tailwind.config.ts` wraps CSS variables with `hsl()` (lines 20-53):
```ts
background: 'hsl(var(--background))',
```
Once CSS vars hold OKLch values, `hsl(oklch(...))` is INVALID CSS — all colors will break silently.

**Action:** Delete the entire `theme.extend.colors` block AND `theme.extend.borderRadius` block from `tailwind.config.ts`. The `@theme inline` block in `globals.css` is the sole source of truth for Tailwind v4 color and radius tokens. Keep only `content`, `container`, `keyframes`, `animation`, and `plugins`.

### 1.4 — Custom Dark Variant

**CRITICAL:** `globals.css` line 5 defines:
```css
@custom-variant dark (&:is(.dark *));
```

This selector requires elements to be **descendants** of `.dark`. Since `next-themes` places `.dark` on `<html>`, this works for all components inside `<body>`. However, verify that `<body>` itself can receive dark styles. If needed, update to:
```css
@custom-variant dark (&:where(.dark, .dark *));
```

### 1.5 — ThemeToggle Component

**File:** `components/theme-toggle.tsx`

Dropdown button with 3 options:
- **Light** (Sun icon) — forces light theme
- **Dark** (Moon icon) — forces dark theme
- **System** (Monitor icon) — follows OS preference

Uses `useTheme()` from next-themes. Placed in `header.tsx` next to the notifications bell.

### 1.6 — WYSIWYG Editor

The contract editor simulates paper — it stays light regardless of theme. The `.wysiwyg-editor-content .ProseMirror` already has hardcoded `background-color: #fff; color: #000` which is correct. The surrounding desk area (`#f3f4f6`) should use a dark-aware token for the outer wrapper, but the "paper" stays white.

**CRITICAL:** `globals.css` uses `hsl(var(--...))` inside WYSIWYG CSS rules — these will break after OKLch migration:
- Line 208: `color: hsl(var(--muted-foreground))` — placeholder text
- Line 276: `border: 1px solid hsl(var(--border))` — table cells
- Line 281: `background: hsl(var(--muted))` — table headers
- Line 287: `border-top: 1px solid hsl(var(--border))` — hr rule

**Action:** Replace all `hsl(var(--token))` with bare `var(--token)` — OKLch values are used directly without a color function wrapper.

---

## Part 2: Hardcoded Color Replacement

### 2.1 — Substitution Map

| Hardcoded Class | Semantic Replacement |
|----------------|---------------------|
| `bg-white` | `bg-background` or `bg-card` (cards/panels use `bg-card`) |
| `bg-gray-50`, `bg-gray-100`, `bg-slate-50` | `bg-muted` |
| `bg-gray-200`, `bg-slate-200` | `bg-muted` or `bg-accent` |
| `text-gray-400`, `text-gray-500`, `text-slate-500` | `text-muted-foreground` |
| `text-gray-600`, `text-gray-700` | `text-foreground` or `text-muted-foreground` |
| `text-gray-900`, `text-slate-900` | `text-foreground` |
| `text-white` (on primary bg) | `text-primary-foreground` |
| `text-white` (on destructive bg) | `text-destructive-foreground` |
| `text-white` (on success bg) | `text-success-foreground` |
| `text-white` (on other colored bg) | appropriate `-foreground` token |
| `border-gray-*`, `border-slate-*` | `border-border` |
| `bg-green-*` | `bg-success` or `bg-success/10` (for light bg) |
| `text-green-*` | `text-success` |
| `bg-red-*` | `bg-destructive/10` |
| `text-red-*` | `text-destructive` |
| `bg-blue-*` | `bg-primary/10` or `bg-info/10` |
| `text-blue-*` | `text-primary` or `text-info` |
| `bg-yellow-*`, `bg-amber-*` | `bg-warning/10` |
| `text-yellow-*`, `text-amber-*` | `text-warning` |

### 2.2 — Files Affected

~64 files with ~342 occurrences. Largest concentrations:
- `contract-template/page.tsx` (49 occurrences) — WYSIWYG toolbar buttons
- `leases/_components/` (multiple modals with status badges)
- `financial/` (dashboard cards, expense tables, daily timeline)
- Layout components (header, sidebar, main-layout)

### 2.3 — Status Badge Pattern

Many components use colored badges to convey meaning (paid/overdue/pending). These MUST remain visually distinct in both themes. Pattern:

```tsx
// Light: tinted background + strong text
// Dark: same tokens auto-adjust via CSS variables
<Badge className="bg-success/10 text-success">Pago</Badge>
<Badge className="bg-destructive/10 text-destructive">Vencido</Badge>
<Badge className="bg-warning/10 text-warning">Pendente</Badge>
```

---

## Part 3: Responsiveness Fixes

### 3.1 — Dialog/Modal Components

**File:** `components/ui/dialog.tsx`

Update `DialogContent` base classes:
- Add `w-[calc(100vw-2rem)] sm:w-auto` to prevent overflow on mobile
- Keep existing `max-w-*` variants that individual modals set
- Add `max-h-[85vh] overflow-y-auto` as defaults

### 3.2 — Data Tables

**File:** `components/tables/data-table.tsx`

Wrap the `<table>` element in an `overflow-x-auto` container. This lets tables scroll horizontally on mobile while maintaining the full column layout.

### 3.3 — Filter Cards

**All CRUD pages with filters**

Replace `flex gap-4 flex-wrap` + `min-w-[200px]` pattern with responsive grid:

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
```

Remove all `min-w-[*]` constraints from filter inputs.

### 3.4 — Dashboard Grids

Add `sm:` breakpoints to all metric card grids:

| Current | Fixed |
|---------|-------|
| `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` |
| `grid-cols-1 md:grid-cols-2` | `grid-cols-1 sm:grid-cols-2` |
| `grid-cols-2 md:grid-cols-4` | `grid-cols-2 sm:grid-cols-3 md:grid-cols-4` |

### 3.5 — Typography Scaling

Page titles and large numbers get responsive sizing:

```tsx
// Titles
className="text-xl sm:text-2xl md:text-3xl font-bold"

// Metric numbers
className="text-lg sm:text-xl md:text-2xl font-bold"
```

### 3.6 — Flex Layout Wrapping

Components that use `flex justify-between` and break on mobile get `flex-col sm:flex-row`:

```tsx
<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
```

Applies to: page headers, list item rows, late payment alerts.

---

## Implementation Strategy

### Session Order

1. **Infrastructure** — ThemeProvider, palette, globals.css cleanup, tailwind config, ThemeToggle component
2. **Layout components** — main-layout, header, sidebar, mobile-nav (theme + responsive)
3. **Shared/UI components** — dialog, data-table, badges (theme + responsive)
4. **Dashboard pages** — main dashboard widgets (theme + responsive)
5. **CRUD pages** — buildings, apartments, tenants, leases, furniture (theme + responsive)
6. **Financial module** — dashboard, daily control, expenses, all subpages (theme + responsive)
7. **Contract template page** — WYSIWYG toolbar (theme only, editor stays light)
8. **Login page + global-error** — theme
9. **Verification** — build, lint, type-check, visual review both themes

### Risk Mitigation

- Each session ends with `npm run build && npm run lint && npm run type-check`
- Visual verification in both themes after each session
- WYSIWYG editor isolated — dark mode doesn't touch the paper area
- Hardcoded colors in `globals.css` for template badges already have `.dark` variants — no changes needed
- Session 1 (infrastructure) is the highest-risk — must verify `tailwind.config.ts` cleanup + OKLch migration don't break existing styles before proceeding

### What NOT to Change

- Backend code — zero changes
- Component logic/behavior — only styling classes
- File structure — no new directories, no moving files
- Test files — no test changes needed (styling-only changes)
- WYSIWYG paper area — stays white in both themes
- Ant Design components — separate theming system, out of scope (see Non-Goals)
