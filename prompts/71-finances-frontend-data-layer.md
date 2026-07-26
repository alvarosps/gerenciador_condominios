# Sessão 71 — Frontend: data layer do cockpit (schemas Zod + query-keys + hooks + MSW para `month_board`/`statement`/`apply_invoice`/`consolidate_debt`/`new_total`)

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida — `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (rev. 2)
> **Sessões da feature**: 65 → 66 → 67 → 68 → 69 → 70 → **71** → 72 ∥ 73 → 74 → 75 → 76
> Esta sessão é a **fundação FE**: entrega TODO o data layer que as S72–S76 consomem — schemas Zod raw-shape (`month-board.schema.ts`, `account-statement.schema.ts`, `open_balance` e `amount_is_estimated` nos schemas existentes), blocos novos em `query-keys.ts` (`monthBoard`, `billingAccounts.statement`), hooks (`useMonthBoard`, `useAccountStatement`, `useApplyInvoice`, `useConsolidateDebt`, `usePayBill` + `new_total`), factories e handlers MSW. **Nenhuma página/componente** — UI é S72–S75.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.3 month_board/flag estimada, §3.4 extrato, §3.5 consolidação, §4 API, §8 erros, §9 testes-FE)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Contratos AUTORITATIVOS S66–S70** (payloads da API — copiar verbatim, NUNCA inventar campo): `@prompts/SESSION_STATE.md` seção "Cockpit operacional de contas", bullets S66/S67/S68/S69/S70. Se este prompt divergir deles, **eles prevalecem**.
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Bloco de query-keys por mês** | `frontend/lib/api/query-keys.ts:165-175` (`combinedCalendar` `{all, month(y,m,building?)}`) + `billingAccounts` `:138-143` (só `all`/`list`/`detail` hoje) | `monthBoard` copia o formato de `combinedCalendar` (sem `buildingId`); `billingAccounts` ganha `statement(id)` |
| **Hook de dashboard mensal** | `frontend/lib/api/hooks/use-combined-calendar.ts:47-66` (`useCombinedCalendar` — params year/month, `keepPreviousData` :63) | Base do `useMonthBoard`; **mas** `staleTime: 0` (contrato S71), não 30s |
| **Invalidação de caches de dinheiro** | `frontend/lib/api/hooks/use-bills.ts:120-126` (`invalidateFinanceMoneyCaches`) + `:128-133` (`invalidateBillCaches` privado) | `invalidateBillCaches` é a fonte única — esta sessão o ESTENDE com `monthBoard.all` + `billingAccounts.all` (pagar/editar bill muda `open_balance`) |
| **Hook multipart (FormData)** | `frontend/lib/api/hooks/use-bills.ts:151-162` (`useParseInvoice` — `FormData` + `headers {'Content-Type': undefined}`) | Exemplar do `useApplyInvoice` (mesmo header; mas invalida, pois `apply_invoice` GRAVA) |
| **`usePayBill` (optimistic conservador)** | `frontend/lib/api/hooks/use-bills.ts:256-304` (`onMutate` flip otimista para "paid" :267-291) | Ganha `new_total?: string` e **PERDE o optimistic update por completo** (remover `onMutate`/rollback — design §8: sem optimistic em mutação de dinheiro; atualizar os testes existentes que travam o flip) |
| **Invalidações de billing-accounts** | `frontend/lib/api/hooks/use-billing-accounts.ts:50-54` + detail `:38-48` | `useConsolidateDebt` vive aqui; `useAccountStatement` espelha o guard `enabled: Boolean(id)` do detail |
| **Schemas raw-shape (estilo atual)** | `frontend/lib/schemas/finances/bill.schema.ts:44-75` (money via `moneyField`, nested `nullable().optional()`), `billing-account.schema.ts:20-44`, `money.ts:4` (`moneyField` string→number) | Novos schemas seguem ESTE estilo: dinheiro `moneyField`, datas string, `z.input` compatível com o JSON cru do DRF |
| **Factories `z.input` (raw DRF)** | `frontend/tests/mocks/data/finances.ts:31-50` (racional raw-shape) + `createMockBillingAccount` :68, `createMockBill` :107, `createMockCombinedCalendar` :229, `createMockOverdueResponse` :256 | `createMockMonthBoard`/`createMockAccountStatement` seguem o padrão (strings de dinheiro, sem `*_id` write-only) |
| **Regra de ordenação MSW** | `frontend/tests/mocks/handlers.ts:2245-2248` (actions de collection ANTES das rotas `:id`) + billing-accounts :2251-2285, bills :2288-2378 (`pay` :2307, `update_with_lines` :2321), finance-dashboard :2469-2480 | `apply_invoice` entra junto de `pay`; `statement` registrado ANTES de `billing-accounts/:id/`; `month_board` junto de `combined_calendar` |
| **Testes de hook (MSW, sem mock interno)** | `frontend/lib/api/hooks/__tests__/use-parse-invoice.test.tsx` (FormData/multipart/invalidação) e `use-combined-calendar.test.tsx` | Espelho dos testes desta sessão; `renderWithProviders`/`createTestQueryClient` de `@/tests/test-utils` |

### O que as S65–S70 já entregaram (PRÉ-REQUISITO — se faltar, PARE)

- **S65**: `Bill.amount_is_estimated` (default `False`), exposto read-only no `BillSerializer`.
- **S66**: `GET finance-dashboard/month_board?year&month` (uncached, 400 em year/month inválidos).
- **S67**: `open_balance` (string decimal) no `BillingAccountSerializer` + `GET billing-accounts/{id}/statement` (404 se inexistente).
- **S68**: action `pay` aceita `new_total` opcional (decimal string); `bulk_pay` NÃO aceita.
- **S69**: `POST bills/{id}/apply_invoice` (MultiPartParser) → bill serializada; 400 com mensagens PT.
- **S70**: `POST billing-accounts/{id}/consolidate_debt` → 201 com o plano serializado.

---

## Escopo

### Arquivos a criar
- `frontend/lib/schemas/finances/month-board.schema.ts` — `monthBoardSchema` + tipos.
- `frontend/lib/schemas/finances/account-statement.schema.ts` — `accountStatementSchema` + tipos.
- `frontend/lib/api/hooks/use-month-board.ts` — `useMonthBoard(year, month)`.
- `frontend/lib/api/hooks/use-account-statement.ts` — `useAccountStatement(id)`.
- `frontend/lib/api/hooks/__tests__/use-month-board.test.tsx`
- `frontend/lib/api/hooks/__tests__/use-account-statement.test.tsx`
- `frontend/lib/api/hooks/__tests__/use-apply-invoice.test.tsx`
- `frontend/lib/api/hooks/__tests__/use-consolidate-debt.test.tsx`

### Arquivos a modificar
- `frontend/lib/schemas/finances/bill.schema.ts` — `amount_is_estimated: z.boolean().default(false)` no `billSchema` (raw antigo sem o campo continua parseando).
- `frontend/lib/schemas/finances/billing-account.schema.ts` — `open_balance: moneyField.optional()` — **OPCIONAL**: payload antigo sem o campo NÃO pode quebrar `parseList`.
- `frontend/lib/api/query-keys.ts` — bloco `monthBoard: {all, month(y,m)}` (formato de `combinedCalendar:165-175`, sem buildingId) + `statement(id)` dentro de `billingAccounts`.
- `frontend/lib/api/hooks/use-bills.ts` — `useApplyInvoice()`; `PayBillRequest.new_total?: string` + envio condicional; **remoção completa do optimistic update do `usePayBill`** (`onMutate`/`onError` rollback saem; mutação → invalidate → refetch); `invalidateBillCaches` ganha `monthBoard.all` + `billingAccounts.all`.
- `frontend/lib/api/hooks/use-billing-accounts.ts` — `useConsolidateDebt()`; `invalidateBillingAccountCaches` ganha `monthBoard.all`.
- `frontend/tests/mocks/data/finances.ts` — `createMockMonthBoard`/`createMockAccountStatement` (tipadas via `z.input` dos schemas novos); `createMockBill` ganha `amount_is_estimated: false` e `createMockBillingAccount` ganha `open_balance: '0.00'` nos defaults.
- `frontend/tests/mocks/handlers.ts` — handlers `month_board`, `billing-accounts/:id/statement/` (ANTES de `billing-accounts/:id/`), `bills/:id/apply_invoice/` (junto de `pay`), `billing-accounts/:id/consolidate_debt/`.
- `frontend/lib/api/hooks/__tests__/use-bills.test.tsx` — cenários novos do `usePayBill` com `new_total` (arquivo existente; não regredir os cenários NÃO-otimistas; os testes que travam o flip otimista DEVEM ser reescritos para assertar a AUSÊNCIA de optimistic — nenhum teste morto/skipped).

### NÃO fazer (pertence a outras sessões)
- **Nenhuma página/componente/rota** — `/finances/accounts` é S72, `[id]` é S73, cockpit é S74/S75.
- **Não remover** `useBills`/`page_size=10000`/agrupamento client-side da página de contas — a troca pelo `month_board` é S74.
- **Não tocar** no fluxo avulso `useParseInvoice`/draft/modal (S63) — `useApplyInvoice` é um hook NOVO, irmão.
- **Nada da Fase 2** (terceiros/`paid_by`) e nenhum backend.

---

## Especificação

> Camadas FE: hooks em `lib/api/hooks/` via `apiClient`; schemas Zod em `lib/schemas/finances/`. `import type`; named exports; sem `as`/`!` em produção; sem suppressions. Payloads abaixo são os **contratos S66–S70 verbatim**.

### `month-board.schema.ts` (payload S66)

O payload é um objeto plano (NÃO `{results,count}` — o interceptor não o desempacota). `bills` são serializadas pelo `BillSerializer` ⇒ **reusar `billSchema`** (que após esta sessão já tem `amount_is_estimated`):

```ts
import { z } from 'zod';
import { billSchema } from './bill.schema';

export const monthBoardGroupSchema = z.object({
  building_id: z.number().nullable(), // null = bucket "Condomínio" (por último)
  building_label: z.string(),
  bills: z.array(billSchema),
});

export const monthBoardSchema = z.object({
  overdue: z.array(billSchema),            // ACTIVE, resto>0, due_date<hoje, QUALQUER competência
  deferred_suspended: z.array(billSchema), // SUSPENDED/DEFERRED resto>0, fora dos totais
  groups: z.array(monthBoardGroupSchema),  // ACTIVE do mês (pagas incluídas)
  totals: z.object({
    due: z.string(),       // strings decimais — exibição converte na borda (formatCurrency aceita)
    paid: z.string(),
    remaining: z.string(),
    overdue: z.string(),   // Σ resto da seção overdue (não entra em due/paid/remaining)
  }),
  generation: z.object({ missing_count: z.number().int() }),
});

export type MonthBoard = z.infer<typeof monthBoardSchema>;
export type MonthBoardGroup = z.infer<typeof monthBoardGroupSchema>;
```

### `account-statement.schema.ts` (payload S67)

```ts
import { z } from 'zod';
import { billingAccountSchema } from './billing-account.schema';
import { moneyField } from './money';

export const statementMonthRowSchema = z.object({
  bill_id: z.number(),
  competence_month: z.string(),
  due_date: z.string(),
  description: z.string(),
  amount_total: moneyField,
  amount_paid: moneyField,
  amount_remaining: moneyField,
  payment_status: z.string(),
  lifecycle_state: z.string(),
  amount_is_estimated: z.boolean(),
  paid_date: z.string().nullable(), // MAX(payment_date) das alocações vivas; null se não pago
});

export const statementPlanRowSchema = z.object({
  id: z.number(),
  description: z.string(),
  installment_count: z.number().int(),
  materialized_count: z.number().int(),
  lifecycle_state: z.string(),
  embedded: z.boolean(),
});

export const accountStatementSchema = z.object({
  account: billingAccountSchema, // já com open_balance opcional
  stats: z.object({
    open_balance: z.string(),           // string decimal (contrato S67)
    open_bills_count: z.number().int(),
    avg_delay_days: z.number().int().nullable(), // null = sem bill quitada elegível
  }),
  months: z.array(statementMonthRowSchema),
  plans: z.array(statementPlanRowSchema),
});

export type AccountStatement = z.infer<typeof accountStatementSchema>;
export type StatementMonthRow = z.infer<typeof statementMonthRowSchema>;
export type StatementPlanRow = z.infer<typeof statementPlanRowSchema>;
```

### `query-keys.ts`

Dentro de `finances`: `monthBoard: { all: ['finances', 'month-board'] as const, month: (year, month) => [...all, 'month', year, month] as const }` (formato `combinedCalendar:165-175`, sem `buildingId`). Em `billingAccounts`, adicionar `statement: (id: number) => [...queryKeys.finances.billingAccounts.all, id, 'statement'] as const`.

### Hooks novos

```ts
// use-month-board.ts
export function useMonthBoard(year: number, month: number) {
  return useQuery({
    queryKey: queryKeys.finances.monthBoard.month(year, month),
    queryFn: async () => {
      const { data } = await apiClient.get<unknown>('/finances/finance-dashboard/month_board/', {
        params: { year, month },
      });
      return monthBoardSchema.parse(data); // objeto plano — interceptor não desempacota
    },
    staleTime: 0,                       // uncached no backend (contrato S71) — NUNCA staleTime longo
    placeholderData: keepPreviousData,  // navegação de mês sem flash (use-combined-calendar.ts:63)
  });
}

// use-account-statement.ts
export function useAccountStatement(id: number | null) {
  return useQuery({
    queryKey: queryKeys.finances.billingAccounts.statement(id ?? 0),
    queryFn: async () => { /* GET `/finances/billing-accounts/${id}/statement/` → accountStatementSchema.parse */ },
    enabled: Boolean(id),
    staleTime: 0, // uncached no backend (S67)
  });
}
```

### `use-bills.ts`

- `invalidateBillCaches` (fonte única, `:128-133`) passa a invalidar TAMBÉM `queryKeys.finances.monthBoard.all` e `queryKeys.finances.billingAccounts.all` (pagar/editar muda o `open_balance` da conta e o board).
- `PayBillRequest` ganha `new_total?: string` (decimal string — contrato S68). No `mutationFn`, incluir `...(request.new_total !== undefined ? { new_total: request.new_total } : {})`. **Remover o optimistic update POR COMPLETO** (decisão do orquestrador, design §8 + refactor completo): sai o `onMutate` inteiro (flip para "paid") e o rollback correspondente em `onError`; nenhum caminho de `usePayBill` é otimista — o status só muda após resposta do servidor + invalidate. TODOS os consumidores atuais (bills page, combined calendar) passam a depender de invalidate→refetch.
- **Código morto resultante DEVE ser deletado** (design principles: refactor completo, zero dead code): `flipBillPaid`, `markBillPaid`, `markBillPaidInCalendar` (`use-bills.ts:226-249`), o 4º generic `PayBillContext` do `useMutation`, o import de `CombinedCalendar` se ficar órfão, e a docstring "conservative optimistic update" (`:251-255`).
- `useApplyInvoice()`:

```ts
export interface ApplyInvoiceRequest { bill_id: number; file: File; }
export function useApplyInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ bill_id, file }: ApplyInvoiceRequest) => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await apiClient.post<unknown>(`${ENDPOINT}${bill_id}/apply_invoice/`, formData, {
        headers: { 'Content-Type': undefined }, // browser seta o boundary
      });
      return billSchema.parse(data); // response = bill serializada com amounts (S69)
    },
    onSuccess: () => invalidateBillCaches(queryClient), // apply_invoice GRAVA (≠ parse_invoice)
  });
}
```

### `use-billing-accounts.ts`

- `invalidateBillingAccountCaches` (`:50-54`) passa a invalidar também `monthBoard.all`.
- `useConsolidateDebt()` — body é o contrato S70 verbatim:

```ts
export interface ConsolidateDebtRequest {
  account_id: number;
  bill_ids: number[];
  embedded: boolean;
  installment_count: number;
  start_due_date: string;  // YYYY-MM-DD
  default_due_day: number;
}
export function useConsolidateDebt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ account_id, ...body }: ConsolidateDebtRequest) => {
      const { data } = await apiClient.post<unknown>(`${ENDPOINT}${account_id}/consolidate_debt/`, body);
      return installmentPlanSchema.parse(data); // 201 com o plano serializado (S70)
    },
    onSuccess: () => {
      invalidateBillingAccountCaches(queryClient);
      // Cria plano + cancela bills de origem: os dois lados precisam refetch.
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installmentPlans.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.installments.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
      invalidateFinanceMoneyCaches(queryClient);
    },
  });
}
```

### MSW (factories + handlers)

- `createMockMonthBoard(overrides)` e `createMockAccountStatement(overrides)` tipadas `z.input<typeof …Schema>`; defaults mínimos coerentes (1 grupo com 1 bill via `createMockBill()`, totals `'350.00'/'0.00'/'350.00'/'0.00'`, `generation: {missing_count: 0}`; statement com 1 month row e `stats {open_balance: '350.00', open_bills_count: 1, avg_delay_days: null}`, `plans: []`).
- Handlers (respeitar `handlers.ts:2245-2248`): `GET finance-dashboard/month_board/` junto dos dashboards (`:2469-2480`); `GET billing-accounts/:id/statement/` **antes** de `GET billing-accounts/:id/` (`:2255`); `POST billing-accounts/:id/consolidate_debt/` (retorna `createMockInstallmentPlan()` com 201) antes das rotas `:id` genéricas; `POST bills/:id/apply_invoice/` junto de `pay` (`:2307`), retornando `createMockBill({ amount_is_estimated: false })`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> Mock policy: HTTP via **MSW** (`server.use` por teste quando precisar de resposta específica). **NUNCA** `vi.mock` de hooks internos, do `apiClient` ou de `query-keys`. `renderWithProviders`/`createTestQueryClient` de `@/tests/test-utils`.

### 1. RED — escrever os testes primeiro

#### `use-month-board.test.tsx`
```ts
describe('useMonthBoard', () => {
  it('busca month_board com year/month nos params e retorna o objeto plano parseado', async () => {});
  // handler captura searchParams (year=2026&month=7) e responde createMockMonthBoard(); hook devolve overdue/groups/totals/generation.
  it('parseia bills das seções via billSchema (amount_is_estimated presente, dinheiro coagido)', async () => {});
  // bill com amount_is_estimated: true no grupo → hook expõe boolean true e amount_total number.
  it('está configurado uncached (staleTime 0) com keepPreviousData', async () => {});
  // inspecionar options do observer via queryClient — sem mockar interno.
  it('propaga erro 400 de year/month inválidos', async () => {});
  // handler 400 → isError.
});
```

#### `use-account-statement.test.tsx`
```ts
describe('useAccountStatement', () => {
  it('busca billing-accounts/{id}/statement/ e retorna account+stats+months+plans parseados', async () => {});
  it('não dispara com id null (enabled=false)', async () => {});
  it('aceita stats.avg_delay_days null (conta sem bill quitada)', async () => {});
  it('propaga 404 de conta inexistente', async () => {});
});
```

#### `use-apply-invoice.test.tsx`
```ts
describe('useApplyInvoice', () => {
  it('posta FormData multipart em bills/{id}/apply_invoice/ e retorna a bill parseada', async () => {});
  // handler captura Content-Type multipart/form-data (boundary do browser) + body FormData com 'file'.
  it('invalida bills + monthBoard + billingAccounts + caches de dinheiro no sucesso (apply GRAVA)', async () => {});
  // spy em queryClient.invalidateQueries — inclui as chaves novas.
  it('propaga 400 de mismatch/mês fechado ao caller (mensagem PT do backend)', async () => {});
});
```

#### `use-consolidate-debt.test.tsx`
```ts
describe('useConsolidateDebt', () => {
  it('posta o body {bill_ids, embedded, installment_count, start_due_date, default_due_day} em billing-accounts/{id}/consolidate_debt/', async () => {});
  // handler captura o body exato (contrato S70) e responde 201 com createMockInstallmentPlan().
  it('retorna o plano parseado via installmentPlanSchema', async () => {});
  it('invalida billingAccounts + monthBoard + installmentPlans + installments + bills no sucesso', async () => {});
  it('propaga 400 (competência fechada / bill de outra conta) ao caller', async () => {});
});
```

#### `use-bills.test.tsx` (cenários NOVOS — não regredir os existentes)
```ts
describe('usePayBill new_total', () => {
  it('envia new_total como string decimal no body quando informado', async () => {});
  // handler captura body: { payment_date, funded_from, new_total: '230.00' }.
  it('não aplica optimistic update em nenhum caminho (onMutate removido — status só muda após refetch)', async () => {});
  // cache de bills pré-populado permanece intacto até o refetch (mesmo asserto do caminho amount parcial).
  it('omite new_total do body quando não informado (payload atual intacto)', async () => {});
});
describe('invalidateBillCaches estendido', () => {
  it('mutação de bill (pay) invalida também monthBoard.all e billingAccounts.all', async () => {});
});
```

#### Schemas (dentro dos arquivos de teste dos hooks — sem arquivo novo)
```ts
it('billingAccountSchema parseia payload SEM open_balance (compat parseList)', () => {});
it('billingAccountSchema coage open_balance string → number quando presente', () => {});
it('billSchema default amount_is_estimated=false em payload antigo', () => {});
```

> Rodar (devem **falhar**):
> ```bash
> cd frontend
> npx vitest run "lib/api/hooks/__tests__/use-month-board.test.tsx" "lib/api/hooks/__tests__/use-account-statement.test.tsx" \
>   "lib/api/hooks/__tests__/use-apply-invoice.test.tsx" "lib/api/hooks/__tests__/use-consolidate-debt.test.tsx" \
>   "lib/api/hooks/__tests__/use-bills.test.tsx"
> ```

### 2. GREEN — implementar na ordem
1. `bill.schema.ts` (`amount_is_estimated`) + `billing-account.schema.ts` (`open_balance` opcional).
2. `month-board.schema.ts` + `account-statement.schema.ts`.
3. `query-keys.ts` (`monthBoard` + `billingAccounts.statement`).
4. Factories + handlers MSW (ordem de registro!).
5. `use-month-board.ts` + `use-account-statement.ts`.
6. `use-bills.ts` (`useApplyInvoice`, `new_total`, `invalidateBillCaches` estendido).
7. `use-billing-accounts.ts` (`useConsolidateDebt`, invalidação estendida).

### 3. REFACTOR
- Invalidação: `invalidateBillCaches`/`invalidateBillingAccountCaches` continuam as fontes únicas — nenhum hook repete listas de `invalidateQueries` que elas já cobrem.
- `useApplyInvoice` e `useParseInvoice` compartilham o helper de FormData se a duplicação incomodar (função pura `pdfFormData(file)`).

### 4. VERIFY — gate
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__" "tests"        # hooks + infraestrutura MSW
npx vitest run "app/(dashboard)/finances"               # regressão: consumidores dos schemas/hooks tocados
npm run lint && npm run type-check && npm run test:unit
```

---

## Constraints

- **Contratos S66–S70 verbatim**: nomes de campos/endpoints EXATOS dos bullets do SESSION_STATE — nunca renomear (`missing_count`, `deferred_suspended`, `avg_delay_days`, `paid_date`, `bill_ids`…).
- **`open_balance` OPCIONAL** no `billingAccountSchema` — payload antigo sem o campo não pode derrubar `parseList` (item deixaria a lista inteira mais pobre silenciosamente).
- **Objetos planos**: `month_board`/`statement` não são `{results,count}` — consumir cru, travar por teste.
- **`staleTime: 0`** em `useMonthBoard`/`useAccountStatement` (uncached no backend) — proibido staleTime longo.
- **`new_total` = string decimal** (S68); `usePayBill` **sem optimistic em nenhum caminho** (onMutate removido); `bulk_pay` NÃO ganha `new_total`.
- **MSW ordering**: actions registradas antes das rotas `:id` conforme `handlers.ts:2245-2248`.
- **Sem páginas/componentes/rotas** (S72–S75); sem remoção do `useBills` da página (S74); fluxo `parse_invoice` avulso intocado.
- Sem suppressions (`eslint-disable`/`@ts-ignore`/`as`/`!` em produção); `import type`; named exports; sem barrel/re-export; strings de dev em EN, mensagens de usuário (não há UI aqui) ficam para S72+.

## Critérios de Aceite (binários)

- [ ] `billSchema` com `amount_is_estimated` (default `false`); `billingAccountSchema` com `open_balance` **opcional** via `moneyField`; payload antigo parseia (teste travado).
- [ ] `month-board.schema.ts` e `account-statement.schema.ts` casam os contratos S66/S67 campo a campo (bills via `billSchema`; `avg_delay_days: int|null`; `plans` com `materialized_count`/`embedded`).
- [ ] `query-keys.ts`: `finances.monthBoard.{all,month(y,m)}` no formato de `combinedCalendar`; `finances.billingAccounts.statement(id)`.
- [ ] `useMonthBoard`/`useAccountStatement` com `staleTime: 0`, parse via schema, `enabled` no statement; erros 400/404 propagados.
- [ ] `useApplyInvoice` multipart (`Content-Type: undefined`), retorna `billSchema.parse`, invalida via `invalidateBillCaches`.
- [ ] `useConsolidateDebt` posta o body S70 exato, parseia `installmentPlanSchema`, invalida billingAccounts+monthBoard+installmentPlans+installments+bills+dinheiro.
- [ ] `usePayBill` envia `new_total` (string) só quando presente; `onMutate`/rollback removidos por completo (zero optimistic); testes antigos do flip atualizados, nenhum teste morto.
- [ ] `invalidateBillCaches` inclui `monthBoard.all` + `billingAccounts.all`; `invalidateBillingAccountCaches` inclui `monthBoard.all`.
- [ ] Factories `createMockMonthBoard`/`createMockAccountStatement` (`z.input`); handlers novos registrados na ordem documentada.
- [ ] Todos os cenários de teste da seção TDD implementados e verdes; **nenhuma página criada**.
- [ ] `cd frontend && npm run lint && npm run type-check && npm run test:unit` — zero erros, zero warnings, zero suppressions.

## Handoff

1. Rodar e confirmar o gate acima verde.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (linha S71 → **concluída**; listar criados/modificados; nota: "data layer completo — S72/S73/S74/S75 consomem `useMonthBoard`/`useAccountStatement`/`useApplyInvoice`/`useConsolidateDebt`/`usePayBill(new_total)` e os schemas novos SEM criar hook/schema próprio").
3. Rodar `/audit` contra os Critérios de Aceite e corrigir gaps.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 71 — FE data layer do cockpit (schemas, query-keys, hooks, MSW)

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. Próximas sessões: **72** (`/finances/accounts`) e **73** (`/finances/accounts/[id]`) — podem rodar em paralelo após esta.
