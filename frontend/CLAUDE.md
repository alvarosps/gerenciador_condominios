# Frontend — Next.js 14 + React 18

## Arquitetura

```
app/(dashboard)/              # Rotas protegidas (Dashboard, Buildings, Apartments, Tenants, Leases, Furniture, Contract Template)
app/(dashboard)/finances/     # CONDOMÍNIO (sidebar "Condomínio"): bills (cockpit sobre month_board), categories,
                              #   distribution, employees, income-entries, installment-plans, month-close, projection,
                              #   reserve — consome /api/finances/
app/(dashboard)/finances/accounts/          # Contas cadastradas (CRUD BillingAccount + saldo devedor via célula-link)
app/(dashboard)/finances/accounts/[id]/     # Extrato da conta — PRIMEIRA rota dinâmica [id] do dashboard
                                            #   (useParams + guard de id inválido + StatCards + consolidação de dívida)
app/(dashboard)/financial/    # Financeiro PESSOAL — DEPRECATED (sidebar "Finanças"; remoção em P7)
app/(dashboard)/admin/        # Admin (proofs/notifications/users)
app/(tenant)/                 # Portal do inquilino (login OTP, payments, contract, notifications)
app/api/[...route]/route.ts   # Proxy same-origin para o backend (prod: NEXT_PUBLIC_API_URL=/api)
app/sw.ts, app/manifest.*     # PWA: service worker (Serwist) + manifest + offline
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

- `lint-staged` (ESLint --fix + Prettier --write em `*.{ts,tsx}`) roda via o hook `frontend-lint-staged` do **pre-commit da raiz** (não mais husky). Enforcement exige `pre-commit install` após clonar.

## Padrões Obrigatórios

- IMPORTANT: Todas as páginas CRUD usam `useCrudPage` hook — seguir o padrão existente
- State: Zustand (client), TanStack Query v5 (server) — NÃO usar useState para server state
- Forms: React Hook Form + Zod — NÃO usar Ant Design Form
- Tenant form usa wizard de 6 steps em `tenants/_components/wizard/`
- Error handling: usar `getErrorMessage()` e `handleError()` de `lib/utils/error-handler.ts`
- Auth: JWT + refresh token via Axios interceptors em `lib/api/client.ts`

## UI: Ant Design + Tailwind + Shadcn
- Ant Design para componentes data-heavy (Table, Select, DatePicker, layout); Tailwind para spacing/cores/layouts custom; Shadcn/ui (Radix) para dialogs, sheets, tooltips. NÃO misturar — um sistema por tipo de componente.
- Tabelas: `DataTable` de `components/tables/`. Delete: `DeleteConfirmDialog`. Páginas do dashboard envolvem em `MainLayout`.
- Charts: Recharts (`ComposedChart` para bar+line, `PieChart` para breakdowns). Cada widget do dashboard é um componente independente com seu próprio hook.

## Comunicação com API
- Todas as chamadas via instância Axios `lib/api/client.ts` — nunca chamar axios direto de componentes; criar hooks TanStack Query em `lib/api/hooks/`.
- Mutations DEVEM invalidar as queries relevantes no sucesso: `void queryClient.invalidateQueries(...)`.

## Módulo Financeiro (frontend)
- Form de despesa adapta campos conforme `expense_type` — conditional rendering com `watch()`.
- Filtros em cascata: person → credit card (opções de cartão filtram pela pessoa selecionada).
- Installments: visualizar em Sheet/Drawer, `mark_paid` via ação PATCH.
- Moeda: `formatCurrency()` de `lib/utils/formatters.ts` (R$ 1.500,00); data DD/MM/YYYY via date-fns (locale pt-BR).

### Cockpit operacional de contas (`finances/bills`, `finances/accounts`)
- Fonte de dados única: `useMonthBoard(year, month)` (`lib/api/hooks/use-month-board.ts`, `staleTime: 0`) — sem cache no backend, sem agrupamento client-side de página inteira.
- Popover-em-célula para edição inline: reusa `components/ui/popover.tsx` dentro do `render` da coluna do `DataTable` (não criar célula editável genérica) — exemplares em `bills/_components/bill-inline-edit.tsx` (`DueDatePopover`/`AmountPopover`) e `bill-pay-popover.tsx`.
- Vencimento edita via PATCH (`useUpdateBill` → `update_header`); valor SEMPRE via `useUpdateBillWithLines` (dinheiro vive em `BillLineItem`, nunca no header).
- Toast acionável de mês fechado: `showFinanceMutationError(error, fallback, goToMonthClose)` em `lib/utils/error-handler.ts` — 400 cuja mensagem casa `/fechad/i` ganha `action: { label: 'Abrir fechamento', onClick }` (sonner) navegando para `ROUTES.FINANCES_MONTH_CLOSE`; todo `onError` de mutação do cockpit usa este helper (nunca reimplementar a detecção por call-site).
- `/finances/accounts/[id]` é o primeiro precedente de rota dinâmica no dashboard: `'use client'` + `useParams<{id:string}>()` + guard de id inválido (empty state PT, sem redirect) + `PageHeader` + `StatCard`×3 + `DataTable` mês a mês.
- `CondoMonthBoardService`/`AccountStatementService` (backend) alimentam `useMonthBoard`/`useAccountStatement` — ver `docs/FINANCES.md` para o contrato completo dos payloads.

## Testes

```bash
npm run test:unit     # Vitest
npm run test:watch    # Watch mode
```

- MSW para mock de API: `tests/mocks/` (handlers, server, data generators)
- Test utils com providers: `tests/test-utils.tsx`
- Testes em `lib/api/hooks/__tests__/`
