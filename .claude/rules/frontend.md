---
paths:
  - "frontend/**"
---

# Frontend Rules

## State Management
- Server state: TanStack Query v5 — never use useState/useEffect for API data
- Client state: Zustand (auth only) — don't expand Zustand for server state
- Form state: React Hook Form + Zod — never use Ant Design Form components

## Component Patterns
- CRUD pages: always use `useCrudPage` hook from `lib/hooks/use-crud-page.ts`
- Tables: use `DataTable` from `components/tables/`
- Dialogs: use `DeleteConfirmDialog` for delete confirmations
- Layout: all dashboard pages wrap in `MainLayout`

## Ant Design + Tailwind
- Use Ant Design for data-heavy components (Table, Select, DatePicker, Form layout)
- Use Tailwind for spacing, colors, custom layouts
- Use Shadcn/ui for dialogs, sheets, tooltips (Radix-based)
- Don't mix: pick one system per component type

## API Communication
- All API calls go through `lib/api/client.ts` Axios instance
- Create TanStack Query hooks in `lib/api/hooks/` — never call axios directly from components
- Error handling: use `getErrorMessage()` and `handleError()` from `lib/utils/error-handler.ts`

## Tenant Wizard
- 6-step wizard in `tenants/_components/wizard/`
- Each step is a separate component with its own validation
- Don't break this pattern — new tenant fields go in the appropriate step
