# Sessão 39 — Frontend data layer: schemas Zod + hooks TanStack + MSW (contas/pagamentos/calendário)

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → **39** → 40 → 41 → … → 50 (Fase 2, camada de dados do frontend)
> Esta sessão cria a **camada de dados do frontend** da Fase 2: schemas Zod (`lib/schemas/finances/`), o grupo `finances` em **query-keys central**, e os **hooks TanStack Query v5** para `billing-accounts`, `bills`, `payments`, `finance-categories`, `bill-skips`, o **calendário combinado** (`finance-dashboard/combined_calendar`) e os **atrasados** (`finance-dashboard/overdue`), incluindo o **toggle otimista de pagamento de conta** (espelhando `use-rent-calendar`). Mais **MSW handlers** + **mock data factories** + **testes de hook (Vitest)**. **Sem páginas, sem componentes de UI, sem CRUD page** — isso é a **Sessão 40**.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.1, §4.2, §4.4, §9 (API), §10 (Frontend/Dashboard), §11 (cache, lado do consumidor), §18 edge-cases das fases 2/4)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md` (verificar S36/S37/S38 **concluídas** — esta sessão consome o que elas entregaram)
- **Contrato de modelos (campos/enums)**: `@prompts/36-finances-models-bills.md` (seção "Contratos cross-session" no fim — `BillBehavior`, `BillLifecycleState`, `BillingAccountState`, `FundedFrom`, `with_amounts` annotations)
- **Regras do projeto**: `frontend/CLAUDE.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Hook calendário + toggle OTIMISTA v5 (a copiar quase verbatim)** | `frontend/lib/api/hooks/use-rent-calendar.ts:1-165` (tipos `RentCalendar*` :8-62; `flipPaidByLease` puro/imutável :70-80; `ToggleRentPaymentContext` :82-84; `useRentCalendar` `useQuery`+`staleTime` :90-105; `useToggleRentPayment` `onMutate`/`getQueriesData`/`setQueryData`/`onError`/`onSettled` :112-156; `export type` no fim :158-165) | **Exemplar canônico** do `useCombinedCalendar` + `useToggleBillPayment`. O toggle de conta segue **exatamente** o mesmo formato otimista (cancel→snapshot→flip imutável→rollback→invalidate). |
| **Testes do hook calendário + toggle (MSW, sem mock de internals)** | `frontend/lib/api/hooks/__tests__/use-rent-calendar.test.tsx:1-390` (fetch/shape :13-45; `building_id` na querystring :47-73; erro 500 :75-87; flip otimista observável via `getQueryData` :153-189; rollback discriminante (1º GET=false, refetch=true delayed) :191-256; invalidação no settle (3 keys) :258-275; flip across ALL cached queries :277-318) | **Espelhar** a estrutura dos testes do toggle (flip/rollback/invalidate), inclusive a técnica do GET discriminante para provar rollback sem mock de internals. |
| **Mock data factory (fonte de tipos do hook; fora do barrel)** | `frontend/tests/mocks/data/rent-calendar.ts:1-52` (`createMockRentCalendarItem` :3-23 + `createMockRentCalendar` :25-52, importam os tipos do próprio hook) | Forma de `tests/mocks/data/finances.ts` — factories `Partial<T>`-override que importam os tipos dos hooks de `finances`; **não** entram em `data/index.ts`. |
| **Schema Zod simples (mixins de auditoria)** | `frontend/lib/schemas/building.schema.ts:1-17` | Forma-base de campos `id?`/`created_at?`/`updated_at?`/`is_deleted?`/`deleted_*?`. |
| **Schema com Decimal-como-string→Number na fronteira** | `frontend/lib/schemas/income.schema.ts:6-32` (`amount` `.string().or(z.number()).transform(Number)` :9-12; **dual** nested-read `building`/`category` + write `building_id`/`category_id` :14-19) | **Padrão canônico**: Decimal vem como **string** do backend; transformar para `Number` no boundary. FK nested read + `_id` write. |
| **Schema com quantização de centavos (ROUND_HALF_UP no boundary)** | `frontend/lib/schemas/expense.schema.ts:17-20` (`total_amount` → `Math.round(Number(val) * 100) / 100`) | Para os campos monetários **string** que precisam ser quantizados a 2 casas no boundary (§4 quantização — sem off-by-cent). |
| **Schema com `superRefine` (validação condicional)** | `frontend/lib/schemas/expense.schema.ts:78-108` (`validateExpenseRules` + `expenseSchema = base.superRefine(...)`) | Se algum schema de `finances` precisar de regra condicional (ex.: `funded_from='reserve'` exige guarda no form da S40 — **aqui** só o schema, sem UI). KISS: não adicionar regras especulativas. |
| **Hook CRUD (list/detail/create/update/delete + invalidate)** | `frontend/lib/api/hooks/use-expenses.ts:1-141` (filtros limpos `Object.fromEntries(...v!==undefined)` :19-21; `useQuery` list `extractResults`+`.parse` :23-33; `useQuery` detail `enabled` :35-45; `useCreate/Update/Delete` com `invalidateQueries` :47-106; action `useMark*Paid` POST :108-122) | **Exemplar canônico** dos hooks CRUD de `billing-accounts`/`bills`/`payments`/`finance-categories`/`bill-skips`. Reusar `extractResults` + `schema.parse`. |
| **Hook de dashboard read-only (staleTime, params year/month)** | `frontend/lib/api/hooks/use-daily-control.ts:66-92` (`useDailyBreakdown`/`useDailySummary` `useQuery` + `params:{year,month}` + `staleTime`) | Forma do `useCombinedCalendar`/`useOverdueBills` (read-only com `{year,month}` na key). **Mas** o `combined_calendar` é **sem cache no backend** (§11) → no front usar `staleTime` curto (30s, como o rent-calendar) **e** `placeholderData: keepPreviousData` (ver Especificação). |
| **query-keys central (grupo `rentCalendar` a espelhar)** | `frontend/lib/api/query-keys.ts:131-135` (`rentCalendar.all` + `month(year, month, buildingId?)` com `buildingId ?? null`); grupo `cashFlow` :98-106; grupo `financialDashboard` :107-122 | **Espelhar** para o grupo `finances` (sub-grupos `billingAccounts`/`bills`/`payments`/`financeCategories`/`billSkips`/`combinedCalendar`/`overdueBills`). |
| **Helpers de paginação DRF** | `frontend/lib/types/api.ts:4-31` (`PaginatedResponse<T>`, `extractResults`) | Reusar `extractResults` nas listas (o interceptor já desembrulha `results`, mas os hooks tipam `PaginatedResponse<T> | T[]` por robustez — ver `use-expenses.ts:26`). |
| **apiClient (Axios; desembrulha `results`; nunca chamar axios cru)** | `frontend/lib/api/client.ts:7-14` (instance), `:19-38` (desembrulho de paginação) | **Toda** chamada HTTP via `apiClient` (regra `frontend/CLAUDE.md` "Comunicação com API"). |
| **MSW handlers (estrutura + reset + array final)** | `frontend/tests/mocks/handlers.ts:30` (`API_BASE`), `:43-52` (`resetMockData`), `:57-60` (forma `http.get` + `await delay(50)`), `:28` (import de `./data/rent-calendar` direto, fora do barrel) | Adicionar `financeHandlers` no array `handlers` e **espalhar** `...financeHandlers`; mock data importado **direto** de `./data/finances`. |
| **test-utils (wrapper/queryClient; gcTime:0)** | `frontend/tests/test-utils.tsx:15-28` (`createTestQueryClient` `gcTime:0`/`staleTime:0`/`retry:false`), `:69-74` (`createWrapper`) | Reusar **verbatim** nos testes; lembrar do `gcTime:0` ao asserir flip otimista (manter um hook montado, como `use-rent-calendar.test.tsx:153-189`). |

### Contratos do backend que esta sessão CONSOME (S36/S37/S38 — verbatim, NÃO derivar)

> **Pré-requisito**: S38 expõe `/api/finances/...` (ModelViewSet + `FinancialReadOnly` + `CustomPageNumberPagination`, serializers dual nested-read/`_id`-write, **Decimal como string**, `competence_month`/`reference_month` = 1º dia). **Se S38 não estiver concluída, PARE** (DEPENDENCY ORDER 38→39). Confirmar no `SESSION_STATE.md` os **shapes reais** dos serializers antes de fixar os schemas — se divergirem deste prompt, o **serializer real prevalece** (ajustar o schema, anotando a divergência no handoff; nunca inventar campo).

- **Enums** (de `finances.models`, S36): `BillBehavior` = `'one_time' | 'recurring' | 'installment'`; `BillLifecycleState` = `'active' | 'suspended' | 'deferred' | 'canceled'`; `BillingAccountState` = `'active' | 'suspended' | 'deferred' | 'ended'`; `FundedFrom` = `'caixa' | 'reserve'`. **Os valores TS devem casar 1:1** com os `TextChoices` (lado esquerdo) do backend.
- **`Bill` (read)**: `id`, `condominium` (id), `building`/`building_id`, `category`/`category_id`, `competence_month` (`YYYY-MM-01`), `due_date` (`YYYY-MM-DD`), `issue_date` (nullable), `description`, `external_identifier`, `behavior` (`BillBehavior`), `billing_account`/`billing_account_id` (nullable), `lifecycle_state` (`BillLifecycleState`), `notes`, `line_items` (nested `BillLineItem[]`), **+ annotations** `amount_total`/`amount_paid`/`amount_remaining` (**string Decimal**), `payment_status` (`'open' | 'partial' | 'paid'`), `is_overdue` (bool). (Annotations vêm de `Bill.objects.with_amounts(today)` — S36 contrato, serializadas como string Decimal por S38.)
- **`BillLineItem` (read)**: `id`, `bill`/`bill_id`, `category`/`category_id`, `description`, `amount` (**string Decimal**, sempre `>= 0`), `is_offset` (bool). (Sinal: positivo + subtraído — §4.1; o front **não** recalcula `amount_total`, lê a annotation.)
- **`BillingAccount` (read)**: `id`, `condominium`, `building`/`building_id` (nullable=nível-condomínio), `category`/`category_id`, `name`, `external_identifier`, `description`, `default_due_day` (1–31), `expected_amount` (**string Decimal**), `lifecycle_state` (`BillingAccountState`), `tracking_start_month` (`YYYY-MM-01` nullable), `end_date` (nullable), `notes`.
- **`Payment` (read)**: `id`, `condominium`, `payment_date` (`YYYY-MM-DD`), `amount` (**string Decimal**), `method`, `funded_from` (`FundedFrom`), `reference`, `notes`, `allocations` (nested `PaymentAllocation[]`).
- **`PaymentAllocation` (read)**: `id`, `payment`/`payment_id`, `bill`/`bill_id`, `amount` (**string Decimal**).
- **`Category` (finance, read)**: `id`, `condominium`, `name`, `parent`/`parent_id` (nullable), `color`, `sort_order`. (Árvore self-FK; **não** confundir com `ExpenseCategory` do legado.)
- **`BillSkip` (read)**: `id`, `billing_account`/`billing_account_id`, `reference_month` (`YYYY-MM-01`). (Sem soft-delete — S36.)
- **Ações (S38)**: `POST /finances/bills/{id}/pay/` body `{ payment_date, amount?, funded_from? }` (default `funded_from='caixa'`; `amount` omitido = total) → retorna `{ status, payment_status, amount_remaining, message }` (PT). `POST /finances/bills/{id}/suspend|defer|cancel|reactivate/`. `POST /finances/bills/create_with_lines/`. `POST /finances/bills/generate_month/` body `{ year, month }`.
- **Dashboard (bare ViewSet, S38)**: `GET /finances/finance-dashboard/combined_calendar/?year=&month=&building_id=` → por dia: seção entradas (aluguéis) + seção saídas (bills) + stats; `GET /finances/finance-dashboard/overdue/?building_id=` → lista de bills atrasados + KPI `Σ amount_remaining`.

> **NOTA crítica de URL**: os endpoints de `finances` são **namespaced** sob `/api/finances/...` (design §9), diferente do legado (`/api/expenses/`, `/api/dashboard/...`). Os hooks chamam `apiClient.get('/finances/bills/', …)` etc. (o `baseURL` do `apiClient` já é `/api`). Nos testes MSW, `API_BASE = 'http://localhost:8008/api'` + caminho `/finances/...`.

---

## Escopo

### Arquivos a criar
- `frontend/lib/schemas/finances/category.schema.ts` — `financeCategorySchema` (self-FK `parent`/`parent_id`; `sort_order`) + `type FinanceCategory`.
- `frontend/lib/schemas/finances/billing-account.schema.ts` — `billingAccountSchema` (`expected_amount` string→Number; `lifecycle_state` enum; `tracking_start_month`/`end_date` nullable; dual `building`/`building_id`, `category`/`category_id`) + `type BillingAccount` + enum `BillingAccountState` (Zod `z.enum`).
- `frontend/lib/schemas/finances/bill.schema.ts` — `billLineItemSchema` (`amount` string→Number, `is_offset`) + `billSchema` (dual FKs; `behavior`/`lifecycle_state` enums; `line_items` nested; **annotations** `amount_total`/`amount_paid`/`amount_remaining` string→Number, `payment_status` enum, `is_overdue` bool) + `type Bill`/`BillLineItem` + enums `BillBehavior`/`BillLifecycleState`/`PaymentStatus`.
- `frontend/lib/schemas/finances/payment.schema.ts` — `paymentAllocationSchema` + `paymentSchema` (`amount` string→Number; `funded_from` enum `FundedFrom`; `allocations` nested) + `type Payment`/`PaymentAllocation` + enum `FundedFrom`.
- `frontend/lib/schemas/finances/bill-skip.schema.ts` — `billSkipSchema` + `type BillSkip`.
- `frontend/lib/api/hooks/use-billing-accounts.ts` — `useBillingAccounts(filters?)` + `useBillingAccount(id)` + `useCreate/Update/DeleteBillingAccount`.
- `frontend/lib/api/hooks/use-bills.ts` — `useBills(filters?)` + `useBill(id)` + `useCreateBillWithLines` + `useUpdate/DeleteBill` + `usePayBill` (otimista, padrão `useToggleRentPayment`) + `useGenerateMonthBills` + `useSuspend/Defer/Cancel/ReactivateBill`.
- `frontend/lib/api/hooks/use-payments.ts` — `usePayments(filters?)` + `usePayment(id)` + `useCreate/Update/DeletePayment`.
- `frontend/lib/api/hooks/use-finance-categories.ts` — `useFinanceCategories()` + CRUD.
- `frontend/lib/api/hooks/use-bill-skips.ts` — `useBillSkips(filters?)` + `useCreate/DeleteBillSkip` (sem update — hard create/delete des-pula).
- `frontend/lib/api/hooks/use-combined-calendar.ts` — `useCombinedCalendar(year, month, buildingId?)` (`placeholderData: keepPreviousData`, `staleTime` 30s) + tipos `CombinedCalendar*` + `useOverdueBills(buildingId?)`.
- `frontend/tests/mocks/data/finances.ts` — factories `createMockBill`/`createMockBillLineItem`/`createMockBillingAccount`/`createMockPayment`/`createMockPaymentAllocation`/`createMockFinanceCategory`/`createMockBillSkip`/`createMockCombinedCalendar`/`createMockOverdueBills` (importam os tipos dos hooks/schemas; **fora** do barrel `data/index.ts`).
- `frontend/lib/api/hooks/__tests__/use-bills.test.tsx` — fetch/shape, `parse` Decimal→Number, filtros na querystring, `usePayBill` otimista (flip `payment_status`/`amount_remaining`) + rollback + invalidate.
- `frontend/lib/api/hooks/__tests__/use-combined-calendar.test.tsx` — fetch/shape combinado, `building_id` na querystring, `placeholderData` preservado entre meses, `useOverdueBills` (KPI Σ remaining), erro 500.
- `frontend/lib/api/hooks/__tests__/use-billing-accounts.test.tsx` — fetch/shape, create invalida `billingAccounts`+`combinedCalendar`.

### Arquivos a modificar
- `frontend/lib/api/query-keys.ts` — adicionar o grupo `finances` (sub-grupos `billingAccounts`/`bills`/`payments`/`financeCategories`/`billSkips`/`combinedCalendar`/`overdueBills`), espelhando `rentCalendar` (`:131-135`) e `cashFlow` (`:98-106`). **Não** alterar grupos existentes.
- `frontend/tests/mocks/handlers.ts` — adicionar `financeHandlers` (GET list/detail + POST/PUT/DELETE + `pay`/`generate_month`/`combined_calendar`/`overdue`) e incluir `...financeHandlers` no array `handlers`; importar mock data **direto** de `./data/finances` (como `:28`). **Não** mexer em handlers existentes.

### NÃO fazer (pertence a outras sessões)
- **Nenhuma página/UI** (`app/(dashboard)/finances/...`, calendário combinado visual, CRUD page, form modals, KPIs cards, donut por categoria, toggle visual otimista) — é a **Sessão 40**. Esta sessão entrega **só** schemas + hooks + MSW + testes de hook. (DEPENDENCY ORDER 38→39→40.)
- **Nenhum componente** (`StatCard`/`AmountDisplay`/`ChartCard`/`useMonthNavigation`/Recharts) — S40.
- **Sem `is_staff` gating de UI** — não há UI aqui (o gating é da S40). Os hooks **não** decidem permissão (o backend `FinancialReadOnly` é a autoridade).
- **Sem hooks de Fase 4+**: `useReserves`/`useReserveMovements`/`useIncomeEntries`/`useCondoMonthClose`/`useCondoBalance`/`useProjection`/`useSimulation`/`useOwnerDistribution` — Fases 4/5/6 (S45+/S48+/S50). **Não** criar query-keys nem schemas para esses agora (YAGNI).
- **Sem `useInstallmentPlans`/`useInstallments`/`useEmployees`** — Fase 3 (S41–S44). O `billSchema` já tipa `behavior: 'installment'` (o valor existe), mas **sem** schema/hook de `InstallmentPlan` aqui.
- **Sem alterar** schemas/hooks do **módulo legado** (`expense.schema.ts`, `use-expenses.ts`, `use-daily-control.ts`, etc.) — coexistência (design §1). **Não** unir `combined_calendar` novo com `daily-control` legado (design §11/§15 — não wirar os dois).
- **Sem mexer** em `client.ts`, `test-utils.tsx`, `lib/types/api.ts`, `query-client.ts` — só **consumir**.

---

## Especificação

### Schemas Zod — Decimal como string no boundary

Convenções (design §10 + exemplares `income.schema.ts`/`expense.schema.ts`):

1. **Dinheiro vem do backend como `string` Decimal** (`'1500.00'`). Cada campo monetário usa `z.string().or(z.number()).transform((val) => Number(val))` (espelha `income.schema.ts:9-12`). Onde precisar quantizar a 2 casas (campos editáveis no form da S40, ex.: `expected_amount`), usar `Math.round(Number(val) * 100) / 100` (espelha `expense.schema.ts:17-20`). **DRY**: se o transform se repetir, extrair um helper local `moneyToNumber` num único módulo (`lib/schemas/finances/money.ts`) e reusar em todos os schemas de `finances` (uma fonte só — design-principles).
2. **FK dual**: nested read (`building: buildingSchema.nullable().optional()`) + write (`building_id: z.number().nullable().optional()`) — espelha `income.schema.ts:14-19`. O `category` de finances usa `financeCategorySchema` (self-FK via `parent`), **não** `expenseCategorySchema`.
3. **Enums** via `z.enum([...] as const)` com os valores **exatos** do backend (lado esquerdo dos `TextChoices`): `BillBehavior`, `BillLifecycleState`, `BillingAccountState`, `FundedFrom`, `payment_status` (`'open'|'partial'|'paid'`). Exportar tanto o schema quanto o `type` inferido (`export type Bill = z.infer<typeof billSchema>`).
4. **Datas** como `string` (`competence_month`/`reference_month` = `YYYY-MM-01`; `due_date`/`payment_date`/`income_date` = `YYYY-MM-DD`); **não** converter para `Date` no schema (TZ-safe é responsabilidade dos formatters/UI da S40 — design §10 "formatters TZ-safe"). Campos de auditoria opcionais (`id?`/`created_at?`/`updated_at?`/`is_deleted?`) como em `building.schema.ts:1-17`.
5. **Annotations do `Bill` são read-only**: `amount_total`/`amount_paid`/`amount_remaining` (string→Number), `payment_status` (enum), `is_overdue` (bool) — todos `.optional()` no schema (o backend sempre envia em read; mas o write — create/update — não os manda). **O front NUNCA recalcula `amount_total`** (lê a annotation; §4.4).

### `financeCategorySchema` (self-FK)

```ts
// lib/schemas/finances/category.schema.ts — z.lazy para subárvore (espelha expense-category.schema.ts)
export const financeCategorySchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  parent: z.lazy(() => financeCategorySchema).nullable().optional(),
  parent_id: z.number().nullable().optional(),
  color: z.string().default(''),
  sort_order: z.number().default(0),
  // auditoria opcional
});
export type FinanceCategory = z.infer<typeof financeCategorySchema>;
```

> **NOTA**: `expense-category.schema.ts` usa `z.lazy()` para recursão (decisão arquitetural #8 do SESSION_STATE). Espelhar.

### `useCombinedCalendar` + `placeholderData: keepPreviousData` (design §10)

```ts
// lib/api/hooks/use-combined-calendar.ts
import { useQuery, keepPreviousData } from '@tanstack/react-query';

interface CombinedCalendarBillItem {
  bill_id: number;
  description: string;
  building_number: string | null;
  amount_remaining: string; // Decimal string (do backend; o hook NÃO transforma a resposta de dashboard — ver nota)
  due_date: string;
  payment_status: 'open' | 'partial' | 'paid';
  is_overdue: boolean;
  // …conforme serializer real S38
}
interface CombinedCalendarDay {
  day: number;
  date: string;
  weekday: string;
  rent_entries: RentCalendarItem[];   // entradas (aluguéis) — REUSAR o tipo de use-rent-calendar (import type)
  bill_exits: CombinedCalendarBillItem[]; // saídas (contas)
}
interface CombinedCalendar {
  year: number;
  month: number;
  today: string;
  days: CombinedCalendarDay[];
  stats: { /* received/to_pay/overdue_total/… conforme S38 */ };
}

export function useCombinedCalendar(year: number, month: number, buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.finances.combinedCalendar.month(year, month, buildingId),
    queryFn: async () => {
      const { data } = await apiClient.get<CombinedCalendar>(
        '/finances/finance-dashboard/combined_calendar/',
        { params: { year, month, ...(buildingId !== undefined ? { building_id: buildingId } : {}) } },
      );
      return data;
    },
    placeholderData: keepPreviousData, // §10: navegação de mês sem flash (NÃO useSuspenseQuery)
    staleTime: 1000 * 30,             // §11: combined_calendar é sem-cache no backend → 30s no front
  });
}
```

> **Tipo do item de aluguel (entradas)**: importar `RentCalendarItem` **direto** de `@/lib/api/hooks/use-rent-calendar` via `import type` (DRY — não redefinir; a metade de entradas do calendário combinado é a mesma estrutura de aluguel, design §11). **Sem re-export.**
> **Decimal no dashboard**: o `combined_calendar`/`overdue` retornam Decimals como **string** (como os demais endpoints de dashboard — `use-rent-calendar.ts` mantém `received_total: string`). Manter **string** nos tipos de dashboard (sem `.transform`), convertendo para `Number` **apenas** no boundary de exibição (S40, formatters). Os **schemas Zod** (com transform→Number) são para os recursos CRUD (`bill`/`billing-account`/`payment`), **não** para o read-only de dashboard (espelha a separação `use-rent-calendar` tipos hand-written × `expense.schema` parse).

### `usePayBill` — toggle/pagamento OTIMISTA (espelha `useToggleRentPayment`)

O pagamento de conta atualiza otimisticamente o `payment_status`/`amount_remaining` do bill nas queries em cache (lista de bills E calendário combinado) **antes** do request settlar — exatamente o formato de `use-rent-calendar.ts:112-156`:

```ts
interface PayBillRequest { bill_id: number; payment_date: string; amount?: number; funded_from?: 'caixa' | 'reserve'; }
interface PayBillResponse { status: string; payment_status: 'open' | 'partial' | 'paid'; amount_remaining: string; message: string; }

export function usePayBill() {
  const queryClient = useQueryClient();
  return useMutation<PayBillResponse, Error, PayBillRequest, PayBillContext>({
    mutationFn: async (req) => {
      const { data } = await apiClient.post<PayBillResponse>(`/finances/bills/${req.bill_id}/pay/`, {
        payment_date: req.payment_date,
        ...(req.amount !== undefined ? { amount: req.amount } : {}),
        funded_from: req.funded_from ?? 'caixa',
      });
      return data;
    },
    onMutate: async (req) => { /* cancel + snapshot + flip imutável em finances.bills.all E finances.combinedCalendar.all */ },
    onError:  (_e, _req, ctx) => { /* restaurar snapshot */ },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.bills.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.combinedCalendar.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.finances.overdueBills.all });
    },
  });
}
```

- **Flip otimista**: função pura imutável `markBillPaidOptimistic(bill, billId)` que seta `payment_status='paid'` e `amount_remaining='0.00'` (ou um flip mínimo coerente — o `onSettled` reconcilia com o servidor). Espelha `flipPaidByLease` (`use-rent-calendar.ts:70-80`) — **sem mutação in-place**. Como o pagamento parcial existe, o otimismo é **conservador**: refletir "pago" só quando `amount` omitido (total) ou ≥ remaining; senão deixar o `onSettled`/refetch reconciliar (documentar a escolha no código; KISS — não simular aritmética de parcial no cliente).
- **Sobre TODAS as queries em cache** (`getQueriesData`/`setQueryData` sobre `finances.bills.all` e `finances.combinedCalendar.all`) — a mutation não conhece os filtros/ mês.
- `usePayBill` é **a única mutation otimista** desta sessão. Os demais (`create`/`update`/`delete`/`generate_month`/`suspend`/etc.) seguem o padrão simples `use-expenses.ts` (`onSuccess` → invalidate).

### Invalidação (DRY com os grupos de query-keys)

Toda mutation de `finances` invalida: o próprio recurso + `finances.combinedCalendar.all` + `finances.overdueBills.all` (uma conta nova/paga muda calendário e atrasados). `generate_month` invalida `finances.bills.all` + `combinedCalendar` + `overdueBills`. **Não** invalidar grupos do legado (`expenses`/`financialDashboard`/`cashFlow`) — escopos distintos (design §1).

### query-keys — grupo `finances` (espelha `rentCalendar`/`cashFlow`)

```ts
finances: {
  all: ['finances'] as const,
  billingAccounts: {
    all: ['finances', 'billing-accounts'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.finances.billingAccounts.all, filters] as const,
    detail: (id: number) => [...queryKeys.finances.billingAccounts.all, id] as const,
  },
  bills: { all, list(filters?), detail(id) },
  payments: { all, list(filters?), detail(id) },
  financeCategories: { all, list() },
  billSkips: { all, list(filters?) },
  combinedCalendar: {
    all: ['finances', 'combined-calendar'] as const,
    month: (year: number, month: number, buildingId?: number) =>
      [...queryKeys.finances.combinedCalendar.all, 'month', year, month, buildingId ?? null] as const,
  },
  overdueBills: {
    all: ['finances', 'overdue-bills'] as const,
    list: (buildingId?: number) => [...queryKeys.finances.overdueBills.all, buildingId ?? null] as const,
  },
},
```

> `buildingId ?? null` para estabilizar a key (espelha `rentCalendar.month` :133-134).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md` + memória do projeto): mockar **APENAS fronteiras externas**. Aqui = **HTTP via MSW** (handlers em `tests/mocks/`). **NUNCA** mockar TanStack Query, o `queryClient`, hooks internos, `apiClient`, ou os schemas Zod. Banco/servidor reais não existem no front — o boundary é a rede (MSW). Testes em `lib/api/hooks/__tests__/` com `createWrapper`/`createTestQueryClient` (`test-utils.tsx:69-74`).

### 1. RED — escrever os testes primeiro

Criar os 3 arquivos de teste. Usar `renderHook`/`waitFor`, `createWrapper()`, `server.use(...)` para sobrescrever handlers por teste. Cobrir, no mínimo:

**`use-bills.test.tsx`**
- [ ] `useBills()` busca e retorna a lista; `billSchema.parse` converte `amount_total`/`amount_paid`/`amount_remaining` de **string** para **number** (asserir `typeof === 'number'`).
- [ ] `useBills(filters)` repassa `building_id`/`lifecycle_state`/`competence_month` na query string (verificar via `new URL(request.url).searchParams`).
- [ ] `useBill(id)` com `enabled` (id null → não dispara); shape com `line_items` nested + `is_offset` por linha.
- [ ] **§4.1 (boundary)**: bill com linhas `[600, 400 não-offset, 100 offset]` → o front **lê** `amount_total` da annotation (`'900.00'` → `900`), **não recalcula** das linhas (asserir que o valor vem do campo `amount_total`, não da soma das linhas).
- [ ] `useCreateBillWithLines` POST `/finances/bills/create_with_lines/` → invalida `bills`+`combinedCalendar`+`overdueBills` (spy em `invalidateQueries`).
- [ ] **`usePayBill` otimista** (espelha `use-rent-calendar.test.tsx:153-189`): seed do cache via GET montado; POST `pay` com `delay`; asserir `payment_status='paid'`/`amount_remaining` flipados **antes** do settle (via `queryClient.getQueryData`).
- [ ] **`usePayBill` rollback** (espelha `:191-256`, GET discriminante): POST 500 → snapshot restaurado (`payment_status` volta ao original); depois deixa o refetch settlar (sem request pendente no teardown).
- [ ] **`usePayBill` invalidate no settle**: as 3 keys (`finances.bills.all`, `finances.combinedCalendar.all`, `finances.overdueBills.all`).
- [ ] `usePayBill` com `funded_from='reserve'`: body POST inclui `funded_from:'reserve'` (capturado no handler). **§18 reserva**: o hook só envia o campo; a guarda de saldo é backend (não simular no front).
- [ ] `usePayBill` flip across ALL cached bill queries (lista + calendário) — espelha `:277-318`.
- [ ] `useGenerateMonthBills` POST `generate_month` body `{year,month}` → invalida `bills`+`combinedCalendar`+`overdueBills`.
- [ ] `useSuspendBill`/`useDeferBill`/`useCancelBill`/`useReactivateBill` POST nas rotas certas → invalidam (smoke de 1–2 representativos é suficiente; KISS).
- [ ] erro 500 em `useBills` → `isError`.

**`use-combined-calendar.test.tsx`**
- [ ] `useCombinedCalendar(2026, 6)` busca e expõe `days` com `rent_entries` (entradas) **e** `bill_exits` (saídas) separados + `stats`.
- [ ] `building_id` repassado na query string só quando definido (espelha `use-rent-calendar.test.tsx:47-73`).
- [ ] **`placeholderData: keepPreviousData`**: ao trocar `month` (re-render do hook com novo arg), `result.current.data` mantém os dados do mês anterior enquanto o novo carrega (`isPlaceholderData === true`), sem voltar a `undefined`. (Asserir `data` definido + `isPlaceholderData` durante a transição.)
- [ ] `useOverdueBills()` retorna a lista de atrasados + KPI `overdue_total` = `Σ amount_remaining` (string no dashboard) — **§4.4**: bills `deferred`/`suspended` **não** aparecem (o backend filtra; o teste verifica que o handler/serializer só devolve `lifecycle_state='active'`+overdue). Asserir que a soma do KPI bate com `Σ amount_remaining` dos itens devolvidos.
- [ ] `useOverdueBills(buildingId)` repassa `building_id`.
- [ ] erro 500 → `isError`.

**`use-billing-accounts.test.tsx`**
- [ ] `useBillingAccounts()` busca e `billingAccountSchema.parse` converte `expected_amount` string→number; `lifecycle_state` válido (`active`/`suspended`/`deferred`/`ended`).
- [ ] `useBillingAccounts(filters)` repassa `building_id`/`lifecycle_state`.
- [ ] `useCreateBillingAccount` POST → invalida `billingAccounts`+`combinedCalendar`.
- [ ] `useUpdateBillingAccount`/`useDeleteBillingAccount` invalidam corretamente.
- [ ] `useBillSkips`/`useCreateBillSkip`/`useDeleteBillSkip`: create POST `bill-skips/`, delete DELETE `bill-skips/{id}/`, ambos invalidam `combinedCalendar` (§18 — `BillSkip` num mês muda o calendário). (Pode ficar neste arquivo ou em `use-bill-skips.test.tsx` — escolher 1 e travar.)

> Rodar (devem **falhar** — schemas/hooks/handlers ainda não existem):
> ```bash
> cd frontend
> npx vitest run "lib/api/hooks/__tests__/use-bills.test.tsx" "lib/api/hooks/__tests__/use-combined-calendar.test.tsx" "lib/api/hooks/__tests__/use-billing-accounts.test.tsx"
> ```

### 2. GREEN — implementar schemas + query-keys + hooks + MSW

1. Criar os 5 schemas em `lib/schemas/finances/` (+ `money.ts` helper se houver duplicação de transform). Importar `buildingSchema` de `@/lib/schemas/building.schema`; **não** importar `expenseCategorySchema` (finances tem seu próprio `financeCategorySchema`).
2. Adicionar o grupo `finances` em `query-keys.ts` (após o grupo `financialSettings`, antes de `currentUser`, ou em ordem coerente — manter o objeto como `as const`).
3. Criar os 6 hooks. CRUD espelha `use-expenses.ts` (filtros limpos + `extractResults` + `.parse`); `usePayBill` espelha `useToggleRentPayment`; `useCombinedCalendar`/`useOverdueBills` espelham `useDailyBreakdown` + `placeholderData`. **Tipos de dashboard hand-written** (como `use-rent-calendar.ts:8-62`); **tipos de CRUD via `z.infer`** dos schemas.
4. Criar `tests/mocks/data/finances.ts` (factories `Partial<T>`-override) e `financeHandlers` em `handlers.ts` (incluir `...financeHandlers` no array `handlers`; importar mock data direto de `./data/finances`).

Rodar até verde:
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-bills.test.tsx" "lib/api/hooks/__tests__/use-combined-calendar.test.tsx" "lib/api/hooks/__tests__/use-billing-accounts.test.tsx"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Extrair `moneyToNumber`/`moneyToNumberRounded` num único módulo (`lib/schemas/finances/money.ts`) se o transform se repetir — **uma fonte só** (design-principles). Os schemas importam de lá (sem re-export, import direto).
- Extrair o flip otimista (`markBillPaidOptimistic`) e o tipo `*Context` como em `use-rent-calendar.ts:70-84` — funções puras, pequenas, intenção clara.
- Garantir que o tipo de item de aluguel no calendário combinado é **importado** (`import type { RentCalendarItem }`), não redefinido (DRY).
- Confirmar que **nenhum** schema/hook recalcula `amount_total` das linhas — lê a annotation (design §4.4).

### 4. VERIFY — gate frontend (escopo desta sessão)
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-bills.test.tsx" "lib/api/hooks/__tests__/use-combined-calendar.test.tsx" "lib/api/hooks/__tests__/use-billing-accounts.test.tsx"
npx tsc --noEmit
npx eslint "lib/schemas/finances" "lib/api/hooks/use-billing-accounts.ts" "lib/api/hooks/use-bills.ts" "lib/api/hooks/use-payments.ts" "lib/api/hooks/use-finance-categories.ts" "lib/api/hooks/use-bill-skips.ts" "lib/api/hooks/use-combined-calendar.ts" "lib/api/query-keys.ts" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "lib/api/hooks/__tests__/use-bills.test.tsx" "lib/api/hooks/__tests__/use-combined-calendar.test.tsx" "lib/api/hooks/__tests__/use-billing-accounts.test.tsx"
```
Zero erros e zero avisos em todos.

---

## Constraints

- **Camada de dados só** (`.claude/rules/architecture.md` Frontend Layers): hooks = TanStack Query para comunicação; schemas = Zod. **Zero UI/componentes/páginas** (S40). Hooks **não** renderizam nem decidem permissão.
- **Toda chamada HTTP via `apiClient`** (`frontend/CLAUDE.md`) — **nunca** `axios`/`fetch` cru em hook/teste de produção; testes mockam a rede via **MSW**.
- **TanStack Query v5**: `useQuery` + `placeholderData: keepPreviousData` para o calendário combinado — **NÃO** `useSuspenseQuery` (descarta `placeholderData`, design §10). Mutations invalidam as queries relevantes no settle/success (`void queryClient.invalidateQueries(...)`).
- **Decimal como string→Number no boundary**: schemas CRUD transformam string→Number (`income.schema.ts:9-12`); tipos de dashboard mantêm **string** (convertidos só na UI da S40). O front **nunca** recalcula `amount_total` (lê a annotation — §4.4).
- **DRY**: helper único de money-transform; tipo de item de aluguel **importado** de `use-rent-calendar` (sem redefinir); flip otimista extraído; query-keys central (sem keys inline). **Sem re-export / barrel files / shims.**
- **`as`/`!` proibidos em produção** (regra do projeto + memória): hooks/schemas sem `as`/non-null. Em testes, `as` só no carve-out de fixture de boundary (corpo MSW/`request.json()`), exatamente como `prompts/24`/`33` documentaram — **nunca** em produção.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o código de verdade. TypeScript strict + `noUncheckedIndexedAccess`.
- **Sem deps novas** — TanStack Query v5, Zod 4, MSW, axios já no repo (`frontend/package.json`). **Não** instalar nada.
- **Namespaced URLs** `/finances/...` (design §9) — **não** colidir com rotas legadas (`/expenses/`, `/dashboard/...`).
- **Escopo de fases**: sem Fase 3/4/5/6 (installments/employees/reserve/income/close/projection/distribution). `billSchema.behavior` inclui `'installment'` (valor existe) mas **sem** schema/hook de `InstallmentPlan`.
- Mensagens ao usuário em **Português** (não há UI aqui; mensagens de erro do servidor são exibidas pela S40); identificadores/tipos/logs em **Inglês**.

## Critérios de Aceite (binários)

- [ ] 5 schemas criados em `frontend/lib/schemas/finances/` (`category`, `billing-account`, `bill` incl. `bill-line-item`, `payment` incl. `payment-allocation`, `bill-skip`) com Decimal string→Number no boundary, FK dual nested-read/`_id`-write, enums casando 1:1 com os `TextChoices` do backend, e `type` inferido exportado. Annotations do `Bill` (`amount_*`/`payment_status`/`is_overdue`) tipadas read-only; o front **não** recalcula `amount_total`.
- [ ] 6 hooks criados: `use-billing-accounts`, `use-bills` (incl. `usePayBill` otimista + `useGenerateMonthBills` + suspend/defer/cancel/reactivate + `useCreateBillWithLines`), `use-payments`, `use-finance-categories`, `use-bill-skips`, `use-combined-calendar` (`useCombinedCalendar` com `placeholderData: keepPreviousData` + `useOverdueBills`). CRUD espelha `use-expenses.ts`; toggle espelha `useToggleRentPayment`.
- [ ] `query-keys.ts` ganha o grupo `finances` (sub-grupos `billingAccounts`/`bills`/`payments`/`financeCategories`/`billSkips`/`combinedCalendar`/`overdueBills`) espelhando `rentCalendar`/`cashFlow`; `buildingId ?? null` para estabilizar; objeto segue `as const`. Grupos existentes intactos.
- [ ] `usePayBill` é otimista (cancel→snapshot→flip imutável→rollback no erro→invalidate no settle das 3 keys), atua sobre **todas** as queries em cache de `bills` + `combinedCalendar`; flip conservador para pagamento parcial (documentado). Demais mutations = padrão simples (`onSuccess`→invalidate).
- [ ] `tests/mocks/data/finances.ts` com factories `Partial<T>`-override (importam os tipos dos hooks/schemas; fora do barrel); `financeHandlers` adicionado e espalhado em `handlers.ts` (mock data importado direto de `./data/finances`); handlers existentes intactos.
- [ ] 3 arquivos de teste cobrem todos os cenários listados (shape+parse Decimal→Number, filtros na querystring, `usePayBill` otimista+rollback+invalidate+funded_from+across-all-queries, `placeholderData` preservado entre meses, `useOverdueBills` KPI=Σ remaining com deferred/suspended fora, erro 500).
- [ ] `npx vitest run` (os 3 arquivos) passa 100%.
- [ ] `npx tsc --noEmit` limpo; `npx eslint` (todos os arquivos tocados) zero erros/zero avisos — **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção.
- [ ] Nenhuma página/componente/UI; nenhum hook/schema de Fase 3/4/5/6; schemas/hooks legados intactos; `client.ts`/`test-utils.tsx`/`lib/types/api.ts` não tocados.

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão):
   ```bash
   cd frontend
   npx vitest run "lib/api/hooks/__tests__/use-bills.test.tsx" "lib/api/hooks/__tests__/use-combined-calendar.test.tsx" "lib/api/hooks/__tests__/use-billing-accounts.test.tsx"
   npx tsc --noEmit
   npx eslint "lib/schemas/finances" "lib/api/hooks/use-bills.ts" "lib/api/hooks/use-billing-accounts.ts" "lib/api/hooks/use-payments.ts" "lib/api/hooks/use-finance-categories.ts" "lib/api/hooks/use-bill-skips.ts" "lib/api/hooks/use-combined-calendar.ts" "lib/api/query-keys.ts" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "lib/api/hooks/__tests__"
   ```
2. Atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 39 (status **concluída**) na tabela de progresso da feature Condomínio Finance.
   - Listar **Arquivos Criados** (5 schemas em `lib/schemas/finances/` [+ `money.ts` se extraído], 6 hooks `use-*.ts`, `tests/mocks/data/finances.ts`, 3 testes) e **Modificados** (`query-keys.ts` grupo `finances`, `handlers.ts` `financeHandlers`).
   - **Anotar os contratos cross-session (verbatim, ver abaixo)** para a S40 consumir sem derivar.
   - **Anotar divergências** se algum serializer real da S38 diferir do shape deste prompt (qual campo, como o schema foi ajustado).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch se necessário — ex.: `feat/condo-finance`):
   ```
   feat(finances): add frontend data layer — Zod schemas + TanStack hooks + MSW for bills/payments/combined-calendar

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **40 — Frontend páginas/UI de `finances`** (calendário combinado visual + toggle otimista, CRUD de contas, KPIs, donut por categoria) — **consome** os hooks/schemas/query-keys desta sessão. A S40 **adiciona** UI; **não** recria a camada de dados.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim na S40)

- **Schemas/tipos** (`@/lib/schemas/finances/*`): `FinanceCategory`, `BillingAccount` (+ `BillingAccountState`), `Bill`/`BillLineItem` (+ `BillBehavior`/`BillLifecycleState`/`PaymentStatus`), `Payment`/`PaymentAllocation` (+ `FundedFrom`), `BillSkip`. Dinheiro CRUD = `number` (já transformado); dinheiro de dashboard = `string` (converter na UI).
- **Hooks** (`@/lib/api/hooks/*`): `useBillingAccounts`/`useBillingAccount`/`useCreate|Update|DeleteBillingAccount`; `useBills`/`useBill`/`useCreateBillWithLines`/`useUpdate|DeleteBill`/`usePayBill`/`useGenerateMonthBills`/`useSuspend|Defer|Cancel|ReactivateBill`; `usePayments`/`usePayment`/`useCreate|Update|DeletePayment`; `useFinanceCategories`+CRUD; `useBillSkips`/`useCreate|DeleteBillSkip`; `useCombinedCalendar(year,month,buildingId?)` (placeholderData) + `useOverdueBills(buildingId?)`.
- **`usePayBill`** é otimista (mesmo contrato de `useToggleRentPayment`): a UI da S40 só chama `.mutate({ bill_id, payment_date, amount?, funded_from? })`; o flip/rollback/invalidate já estão no hook (S40 **não** duplica invalidação).
- **query-keys**: grupo `queryKeys.finances.*` — a S40 usa os mesmos sub-grupos; **não** criar keys inline.
- **`useCombinedCalendar`** retorna `days[].rent_entries` (entradas) + `days[].bill_exits` (saídas) separados (design §5/§10 — seções distintas no dia); `rent_entries` é o tipo `RentCalendarItem` reusado de `use-rent-calendar`.
- **`useOverdueBills`** KPI `overdue_total` = `Σ amount_remaining` (string Decimal); deferred/suspended fora (§4.4) — a S40 exibe o sub-total separado do atraso de aluguel.
- **MSW**: `tests/mocks/data/finances.ts` + `financeHandlers` disponíveis para os testes de componente da S40 (que mockam só o boundary de dados via MSW, **não** os hooks).
