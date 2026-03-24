# Frontend — Next.js 14 + React 18

## Arquitetura

```
app/(dashboard)/              # Rotas protegidas (Dashboard, Buildings, Apartments, Tenants, Leases, Furniture, Contract Template)
app/login/                    # Auth page
components/layouts/           # MainLayout, Sidebar, Header, MobileNav
components/shared/            # ConfirmDialog, DeleteConfirmDialog, Loading
components/tables/            # DataTable (Ant Design)
components/ui/                # Shadcn/ui (sheet, skeleton, etc.)
components/search/            # GlobalSearch
lib/api/client.ts             # Axios instance com interceptors
lib/api/hooks/                # TanStack Query hooks (useBuildings, useLeases, etc.)
lib/schemas/                  # Zod validation schemas
lib/hooks/use-crud-page.ts    # Hook padrão para páginas CRUD
lib/utils/                    # validators (CPF/CNPJ), formatters, error-handler
store/auth-store.ts           # Zustand auth state
```

## Git Hooks

- `husky` + `lint-staged`: ESLint --fix + Prettier --write rodam automaticamente em `*.{ts,tsx}` no pre-commit

## Padrões Obrigatórios

- IMPORTANT: Todas as páginas CRUD usam `useCrudPage` hook — seguir o padrão existente
- State: Zustand (client), TanStack Query v5 (server) — NÃO usar useState para server state
- Forms: React Hook Form + Zod — NÃO usar Ant Design Form
- Tenant form usa wizard de 6 steps em `tenants/_components/wizard/`
- Error handling: usar `getErrorMessage()` e `handleError()` de `lib/utils/error-handler.ts`
- Auth: JWT + refresh token via Axios interceptors em `lib/api/client.ts`

## Testes

```bash
npm run test:unit     # Vitest
npm run test:watch    # Watch mode
```

- MSW para mock de API: `tests/mocks/` (handlers, server, data generators)
- Test utils com providers: `tests/test-utils.tsx`
- Testes em `lib/api/hooks/__tests__/`
