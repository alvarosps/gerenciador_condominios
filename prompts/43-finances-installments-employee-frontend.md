# Sessão 43 — Frontend: Parcelas + Folha (schemas/hooks/páginas)

> **Feature**: Condomínio Finance (módulo financeiro do condomínio — saídas/saldo/reserva/distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da Fase 3 (Parcelas + Folha)**: 41 → 42 → **43** (esta é a **43**, **camada de UI** do frontend da Fase 3).
> A Sessão 41 entregou models+serviços (`InstallmentPlan`/`Installment`/`Employee`, `InstallmentPlanService.convert_deferred`, extensão de `ensure_month_bills`, abatimento §4.6). A Sessão 42 expôs a **API** (serializers dual, viewsets CRUD + filtros, ação `installment-plans/{id}/convert_deferred`, `installments` GET/PATCH, `employees` CRUD). Esta sessão constrói **somente a UI da Fase 3**: (1) **camada de dados FE nova** (schemas Zod + hooks TanStack + query-keys + MSW para parcelas/folha — a S39 NÃO os criou); (2) **página de Planos de Parcelas** (CRUD avulso **e** embutido + UI de **conversão de IPTU deferido**); (3) **página de Folha** (`Employee` CRUD, incl. **variável-only**). **Sem projeção, sem distribuição** (Fases 5/6).

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.3 dois eixos de tipo, §4.6 abatimento Rosa, §5.2 «App finances» [`InstallmentPlan`/`Installment`/`Employee`], §7 mapeamento [embutido/avulso/IPTU deferido/Rosa/Raymel/Adriana], §8 [`convert_deferred`/sync realizado], §9 API, §10 Frontend, §11 cache lado consumidor, §18 «Parcelas» + «Folha»)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md` — **confirmar S42 concluída** (esta sessão consome as rotas/shapes que ela expôs) **e S40 concluída** (consome o padrão de página de Contas + grupo de menu "Condomínio" + `StatusChip`/`computeLineTotal`). **Se S42 ou S40 não estiverem concluídas, PARE** (DEPENDENCY ORDER: 42 → 43; 40 precede 43 no padrão de UI).
- **Contrato cross-session consumido (verbatim, NÃO derivar)**:
  - **da S42** (final de `@prompts/42-finances-installments-employee-api.md`, seção "Contratos cross-session expostos"): rotas `/api/finances/{installment-plans,installments,employees}/` (+ `installment-plans/{id}/convert_deferred/`); shapes dual `InstallmentPlanSerializer` (read nested `category`/`building`/`linked_billing_account` + `installments`; write `category_id`/`building_id`/`linked_billing_account_id`), `EmployeeSerializer` (read `person`/`lease`; write `person_id`/`lease_id`), `InstallmentSerializer` (`amount` schedule editável + `is_overdue`); `lifecycle_state`/`payment_type` strings do model.
  - **da S40** (final de `@prompts/40-finances-frontend-calendar-bills-ui.md`, "Contratos cross-session definidos por esta sessão"): padrão `useCrudPage<T>` + form modal + grupo de menu "Condomínio" (`sidebar.tsx`); helpers `StatusChip`/`computeLineTotal` extraídos (reusar, **não** duplicar); `ROUTES.FINANCES_BILLS`.
  - **da S39** (final de `@prompts/39-finances-frontend-data-layer.md`): `useFinanceCategories` (+ tipo `FinanceCategory`), `useBillingAccounts` (+ `BillingAccount`), grupo `queryKeys.finances.*`, padrão de schema com Decimal string→Number no boundary, `tests/mocks/data/finances.ts` + `financeHandlers`. Esta sessão **estende** esses artefatos (novos sub-grupos/handlers), **não** os recria.
  - **Se algum nome de tipo/hook/campo/rota divergir deste prompt, o export/handoff real da S39/S40/S42 prevalece** — importar/consumir o nome real, nunca recriar/duplicar.
- **Regras do projeto**: `frontend/CLAUDE.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`.

### Exemplares (arquivo:linha — abrir e seguir; exemplar > descrição)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Schema Zod com Decimal string→Number no boundary + FK dual (nested-read + `_id`-write nulável) + nested list** | `frontend/lib/schemas/income.schema.ts:6-30` (`amount` `.string().or(z.number()).transform(Number)`; `person`/`person_id` `nullable().optional()`; `building`/`building_id`; `category`/`category_id`) | **Exemplar canônico** de `installment-plan.schema.ts` (`total_amount` transform; `category`/`category_id`, `building`/`building_id` nulável, `linked_billing_account`/`_id` nulável; `installments` nested) e `employee.schema.ts` (`base_salary` nulável; `person`/`person_id`, `lease`/`lease_id` nulável) |
| **Schema com nested array de filhos + `superRefine` (regras condicionais PT) + quantização 2-casas** | `frontend/lib/schemas/expense.schema.ts:12-60,93` (`total_amount` `Math.round(Number(val)*100)/100`; `installments: z.array(...).default([])`; `is_offset`; `.superRefine(validateExpenseRules)`) | Forma do `total_amount`/`installment_count`/`installments` do plano + validação `embedded ⇒ linked_billing_account_id` obrigatório (PT) via `superRefine` |
| **Hook CRUD TanStack v5 (list paginada + detail + create/update/delete; invalida no `onSuccess`)** | `frontend/lib/api/hooks/use-expenses.ts:18-106` (`useExpenses(filters)` com `extractResults`+`schema.parse`; `useCreate/Update/DeleteExpense` invalidando `expenses.all`+`financialDashboard.all`+`cashFlow.all`) | **Exemplar canônico** dos hooks `use-installment-plans.ts` e `use-employees.ts` (CRUD + filtros + parse Zod; invalidar `queryKeys.finances.*`) |
| **Hook de ação POST que retorna resultado serializado + invalida** | `frontend/lib/api/hooks/use-expenses.ts:108-141` (`useMarkExpensePaid` → `POST /expenses/{id}/mark_paid/` retorna `Expense`; `useGenerateInstallments` → POST + invalida `expenses`+`expenseInstallments`) | **Exemplar canônico** do `useConvertDeferred` (POST `installment-plans/{id}/convert_deferred/` → retorna `InstallmentPlan`; invalida `finances.installmentPlans` + `finances.bills` + `finances.billingAccounts`) |
| **Hook PATCH parcial que retorna o objeto (`Partial<T> & {id}`)** | `frontend/lib/api/hooks/use-leases.ts:77-87` (update via `PATCH` retornando `response.data`) e `use-leases.ts:188-211` (`useChangeDueDate` — ação POST com params nomeados + retorno tipado) | Modelo do `useUpdateInstallment` (PATCH `amount`/`due_date` do **schedule**) e do shape de params de `useConvertDeferred` |
| **Sub-grupos de query-keys (`all`/`list(filters)`/`detail(id)`, objeto `as const`)** | `frontend/lib/api/query-keys.ts:22-31` (`expenses`/`expenseInstallments`) | Adicionar sub-grupos a `queryKeys.finances.*`: `installmentPlans`, `installments`, `employees` (espelhar `all`/`list`/`detail`; objeto `as const`; grupos existentes intactos) |
| **Página CRUD canônica (`useCrudPage` + DataTable + form modal + AlertDialog delete + export + gating)** | `frontend/app/(dashboard)/buildings/page.tsx:42-242` (hook `useCrudPage<Building>` :47-55; colunas+ações :57-106; header+botões :114-150; `<DataTable>` :183-189; `<FormModal>` :191-195; `<AlertDialog>` de delete :197-216) | **Exemplar canônico** de `installment-plans/page.tsx` e `employees/page.tsx` |
| **`useCrudPage` (estado CRUD: modal/edit/delete/bulk/export)** | `frontend/lib/hooks/use-crud-page.ts:156-311` (genérico `<T extends {id?: number}>`; `openCreateModal`/`openEditModal`/`closeModal`/`handleDeleteClick`/`handleDelete`/`isDeleting`/`handleExport`) | Reusar **verbatim**; passar `deleteMutation = useDeleteInstallmentPlan()` / `useDeleteEmployee()` |
| **Form modal financeiro (Dialog shadcn + RHF + `zodResolver` + create/update + selects + `watch()` condicional + `superRefine`)** | `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx:4-5,99-150,208-214` (`useForm`+`zodResolver`; `useCreate/UpdateExpense`; `usePersons`/`useBuildings`/`useExpenseCategories`; `form.watch(...)`; flags `show*` por tipo) | **Exemplar canônico** de `installment-plan-form-modal.tsx` (campo condicional `embedded` → mostra `linked_billing_account_id` via `watch`) e `employee-form-modal.tsx` (`payment_type` → mostra/oculta `base_salary` via `watch`) |
| **Lista dinâmica `useFieldArray` (append/remove + empty state)** | `frontend/app/(dashboard)/tenants/_components/dependent-form-list.tsx:39-72,133` (`useFieldArray({control, name})`; `fields.map` com `field.id`; `append({...})`; `remove(index)`) | Modelo do **schedule editável** das parcelas (`installment-schedule-field.tsx`): listar/editar `amount`/`due_date` por parcela materializada (read+PATCH; **não** criar/remover parcela — nascem do serviço S41) |
| **Erro/toast** | `frontend/lib/utils/error-handler.ts` (`getErrorMessage`/`handleError`) + `sonner` `toast` (uso em `expense-form-modal.tsx:37`) | Sucesso → `toast.success` (PT); erro → `handleError(err, 'mensagem PT')` |
| **`is_staff` gating (fonte do usuário)** | `frontend/store/auth-store.ts` (`user.is_staff`) lido via `useAuthStore()` (ex.: `financial/daily/page.tsx:29` `isAdmin = user?.is_staff ?? false`) ou `useCurrentUser()` (`use-auth.ts:107`) | Esconder toda UI de escrita (criar/editar/excluir/converter) quando `!is_staff`; backend `FinancialReadOnly` é a autoridade |
| **Formatadores (moeda + mês + data ISO)** | `frontend/lib/utils/formatters.ts:5` (`formatCurrency`), `:89` (`formatMonthYear` → `"Junho/2026"` **com barra**), `:98` (`formatDateISO`), `:104` (`MONTH_ABBR`) | Moeda/datas. **Datas puras `YYYY-MM-DD` exibidas por split**, nunca `new Date(iso)` (ver `late-payments-alert.tsx:17-21`) |
| **`ROUTES` + sidebar grupo "Condomínio" (criado na S40)** | `frontend/lib/utils/constants.ts:48-71` (`ROUTES`); `frontend/components/layouts/sidebar.tsx:44-57` (`financialChildren` formato) + o **grupo "Condomínio"** que a S40 adicionou com `ROUTES.FINANCES_BILLS` | Adicionar `ROUTES.FINANCES_INSTALLMENT_PLANS`/`ROUTES.FINANCES_EMPLOYEES` e os itens no **mesmo** grupo "Condomínio" (não no "Financeiro" legado) |
| **Teste de hook (MSW, sem mock de internals; `renderHook`+`createWrapper`)** | `frontend/lib/api/hooks/__tests__/` (padrão geral; `server.use` por teste, mock data de `tests/mocks/data/*`) e `tests/test-utils.tsx:15-44` (`createTestQueryClient`/`renderWithProviders`/wrapper) | Estrutura dos testes de `use-installment-plans.test.tsx`/`use-employees.test.tsx` |
| **Teste de componente (MSW + `renderWithProviders`, mock só do boundary de rede)** | `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx:1-75` (`API_BASE` :9; `server.use(http.get(...))` :33-35; `renderWithProviders(<X/>, {queryClient: createTestQueryClient()})` :36; `userEvent`) | **Padrão a copiar** nos testes de página/modal: MSW por teste (preferir) **ou** `vi.spyOn` no módulo de hooks; nunca mockar TanStack/`apiClient`/ORM |
| **MSW data + handlers de `finances` (estender — já existem da S39)** | `frontend/tests/mocks/data/finances.ts` (factories `Partial<T>`-override) + `financeHandlers` em `frontend/tests/mocks/handlers.ts` (`API_BASE = 'http://localhost:8008/api'` :30) | **Estender** com `createMockInstallmentPlan`/`createMockInstallment`/`createMockEmployee` + handlers das 3 rotas novas; **não** recriar os existentes (DRY) |

### Artefatos da S42/S40/S39 que esta sessão CONSOME (não recriar)

- **Rotas (S42)**: `/api/finances/installment-plans/` (+ `{id}/convert_deferred/`), `/api/finances/installments/` (GET/PATCH; **sem** POST/DELETE → 405), `/api/finances/employees/`.
- **Shapes dual (S42)**: conforme tabela de exemplares (read nested + `_id` write; `installments` nested read-only no plano; `amount` schedule editável; `is_overdue`). `lifecycle_state ∈ {active, paid, deferred, canceled}`; `payment_type ∈ {fixed, variable, mixed}`; Decimal = string na API.
- **UI/helpers (S40)**: padrão de página de Contas, grupo de menu "Condomínio", `StatusChip`, `computeLineTotal` — reusar quando aplicável.
- **Camada de dados (S39)**: `useFinanceCategories`/`useBillingAccounts` (selects do form), `queryKeys.finances` (estender), padrão de schema/transform, MSW finances (estender).

> Os nomes/caminhos/campos acima são o **contrato cross-session** da Fase 3 FE. **Verbatim** — não derivar nem renomear. Se algum diferir do `SESSION_STATE.md` real, **o `SESSION_STATE.md` prevalece** (parar e alinhar antes de codar).

---

## Escopo

### Arquivos a criar

**Camada de dados (schemas Zod)** — `frontend/lib/schemas/finances/`
- `installment-plan.schema.ts` — `installmentPlanSchema` (+ `type InstallmentPlan`), `installmentSchema` (+ `type Installment`), enum `InstallmentPlanState` (`'active'|'paid'|'deferred'|'canceled'`). Decimal string→Number no boundary; FK dual; `installments` nested read-only; `superRefine` (`embedded ⇒ linked_billing_account_id` obrigatório, PT).
- `employee.schema.ts` — `employeeSchema` (+ `type Employee`), enum `EmployeePaymentType` (`'fixed'|'variable'|'mixed'`). `base_salary` nulável (variável-only); `person`/`person_id`, `lease`/`lease_id` nuláveis; `superRefine` (`payment_type==='fixed' ⇒ base_salary` obrigatório; `'variable' ⇒ base_salary` ausente/null — PT).

**Camada de dados (hooks)** — `frontend/lib/api/hooks/`
- `use-installment-plans.ts` — `useInstallmentPlans(filters?)`/`useInstallmentPlan(id)`/`useCreate|Update|DeleteInstallmentPlan`; `useInstallments(filters?)`/`useUpdateInstallment` (PATCH schedule); `useConvertDeferred` (ação POST → retorna `InstallmentPlan`).
- `use-employees.ts` — `useEmployees(filters?)`/`useEmployee(id)`/`useCreate|Update|DeleteEmployee`.

**Páginas (Planos de Parcelas)** — `frontend/app/(dashboard)/finances/installment-plans/`
- `page.tsx` — `useCrudPage<InstallmentPlan>` + `DataTable` + header (criar/exportar) + AlertDialog delete + montagem do form modal e do diálogo de conversão de deferido.
- `_components/installment-plan-columns.tsx` — colunas (descrição, prédio|"Condomínio", categoria, total, nº parcelas, `embedded`, `lifecycle_state` via `StatusChip`/badge, ações: editar/converter-deferido/excluir, gated por `is_staff`).
- `_components/installment-plan-form-modal.tsx` — Dialog + RHF + Zod; create via `useCreateInstallmentPlan`, edit via `useUpdateInstallmentPlan`; `embedded` (`Switch`) → mostra `linked_billing_account_id` via `watch`.
- `_components/installment-schedule-field.tsx` — lista das parcelas materializadas (read + PATCH `amount`/`due_date` via `useUpdateInstallment`); **sem** criar/remover parcela (nascem do serviço S41).
- `_components/convert-deferred-dialog.tsx` — diálogo da **conversão de IPTU deferido** (params reais da assinatura S41/S42: ex. `installment_count`/`start_due_date`/`default_due_day`); chama `useConvertDeferred`.
- `__tests__/installment-plan-form-modal.test.tsx`, `__tests__/installment-schedule-field.test.tsx`, `__tests__/convert-deferred-dialog.test.tsx`, `__tests__/installment-plans-page.test.tsx`.

**Páginas (Folha)** — `frontend/app/(dashboard)/finances/employees/`
- `page.tsx` — `useCrudPage<Employee>` + `DataTable` + header + AlertDialog delete + montagem do form modal.
- `_components/employee-columns.tsx` — colunas (nome, cargo/`role`, `payment_type`, `base_salary`, vínculo `person`/`lease`, `is_active`, ações gated).
- `_components/employee-form-modal.tsx` — Dialog + RHF + Zod; create/update; `payment_type` (`Select`) → `watch` controla visibilidade/obrigatoriedade de `base_salary`; selects de `usePersons`/`useLeases` (nuláveis).
- `__tests__/employee-form-modal.test.tsx`, `__tests__/employees-page.test.tsx`.

**Hook tests** — `frontend/lib/api/hooks/__tests__/`
- `use-installment-plans.test.tsx`, `use-employees.test.tsx`.

### Arquivos a modificar
- `frontend/lib/api/query-keys.ts` — estender `queryKeys.finances` com `installmentPlans`/`installments`/`employees` (sub-grupos `all`/`list(filters)`/`detail(id)`, `as const`). Grupos existentes (incl. `finances.*` da S39) **intactos**.
- `frontend/lib/utils/constants.ts` — adicionar a `ROUTES`: `FINANCES_INSTALLMENT_PLANS: '/finances/installment-plans'`, `FINANCES_EMPLOYEES: '/finances/employees'`. **Não** alterar rotas existentes (legado `/financial/...` intacto).
- `frontend/components/layouts/sidebar.tsx` — adicionar os itens "Parcelas" e "Folha" no **grupo "Condomínio"** criado pela S40 (espelhar o formato de `financialChildren:44-57`). Não tocar nos itens existentes.
- `frontend/tests/mocks/data/finances.ts` — estender com `createMockInstallmentPlan`/`createMockInstallment`/`createMockEmployee` (`Partial<T>`-override, importando os tipos dos novos schemas; fora de barrel).
- `frontend/tests/mocks/handlers.ts` — estender `financeHandlers` com as rotas `installment-plans` (GET/POST/PATCH/DELETE + `:id/convert_deferred`), `installments` (GET/PATCH), `employees` (GET/POST/PATCH/DELETE). Handlers existentes **intactos**.

### NÃO fazer (pertence a outras sessões)
- **Sem projeção/simulação** (tabela 12 meses, `ComposedChart`, simulador) — **Fase 5** (S47–S48). As parcelas futuras aparecem na **projeção** lá; aqui só CRUD do plano e edição do schedule.
- **Sem distribuição por proprietário** (cards "por proprietário", externos Tiago/Alvaro) — **Fase 6** (S49–S50).
- **Sem KPIs de saldo/caixa/reserva** nem `StatCard` de saldo — **Fase 4** (S44–S46). A coluna de status do plano usa `lifecycle_state`/`StatusChip`, **não** saldo.
- **Sem UI de pagamento de parcela**: pagamento é via `bills/{id}/pay` (Fase 2 / `usePayBill` — página de Contas da S40). **Não** expor `pay`/`bulk_pay` em parcelas/folha. A folha vira `Bill` via `ensure_month_bills` (S41) e é paga na tela de Contas.
- **Sem criar/remover `Installment` avulsa** na UI — parcelas nascem da materialização do plano (serviço S41); o `installment-schedule-field` só **edita** `amount`/`due_date` (PATCH; backend retorna 405 em POST/DELETE — não chamar).
- **Sem lógica de negócio no FE**: dedup de embutido, sync realizado×schedule, abatimento §4.6, conversão de deferido — **tudo no backend** (S41). A UI só dispara `useConvertDeferred`/PATCH e **exibe** o que o servidor retorna (nunca recalcula `amount_total`/abatimento no FE).
- **Sem alterar** a camada de dados da S39 (`use-bills`/`use-billing-accounts`/`use-combined-calendar`/`use-payments`/`use-finance-categories`/`use-bill-skips`/schemas de bill), a UI da S40 (`finance-calendar/*`, `finances/bills/*`), nem o módulo legado (`financial/expenses`/`employees`/`daily`). Estender, não recriar.
- **Sem deps novas** (RHF/Zod 4/TanStack v5/Shadcn/lucide/sonner/date-fns/MSW já no repo).
- **Sem mexer** em `client.ts`, `test-utils.tsx`, `query-client.ts`, `server.ts`.

---

## Especificação

Direção de dados (`frontend/CLAUDE.md` + `.claude/rules/architecture.md` Frontend Layers): **só os containers** (`*/page.tsx` e os modais/diálogos que disparam mutations) consomem hooks; os demais componentes são **puros** (props in, callbacks out). **Nenhum componente chama `apiClient`/axios** — só os hooks. Forms = React Hook Form + Zod (nunca Ant Design Form). Moeda via `formatCurrency`; datas puras por **split** (nunca `new Date(iso)`). Mensagens ao usuário em **PT**; identificadores/tipos em **EN**. Decimal: CRUD = `number` (transformado no schema, design §39/S39); o front **nunca** recalcula `amount_total`/abatimento de dados do backend.

### 43.1 `installment-plan.schema.ts` (Decimal boundary + FK dual + nested + `superRefine`)
```ts
export const installmentSchema = z.object({
  id: z.number().optional(),
  plan: z.number().optional(),                 // PK (read-only no backend)
  number: z.number().optional(),               // read-only (fixado na materialização)
  due_date: z.string(),                        // YYYY-MM-DD (schedule editável)
  amount: z.string().or(z.number()).transform((v) => Math.round(Number(v) * 100) / 100),
  is_overdue: z.boolean().optional(),          // annotation read-only (S42)
});
export type Installment = z.infer<typeof installmentSchema>;

export const installmentPlanSchema = z.object({
  id: z.number().optional(),
  description: z.string().min(1, 'Descrição é obrigatória'),
  total_amount: z.string().or(z.number()).transform((v) => Math.round(Number(v) * 100) / 100),
  installment_count: z.number().int().positive('Número de parcelas inválido'),
  start_due_date: z.string(),                  // YYYY-MM-DD
  default_due_day: z.number().int().min(1).max(31),
  lifecycle_state: z.enum(['active', 'paid', 'deferred', 'canceled']),
  embedded: z.boolean().default(false),
  category: financeCategorySchema.nullable().optional(),   // nested read (S39)
  category_id: z.number(),                                 // write
  building: buildingSchema.nullable().optional(),
  building_id: z.number().nullable().optional(),           // null = nível-condomínio
  linked_billing_account: billingAccountSchema.nullable().optional(),
  linked_billing_account_id: z.number().nullable().optional(), // só p/ embutido
  installments: z.array(installmentSchema).default([]),    // nested read-only
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.embedded && (data.linked_billing_account_id === null || data.linked_billing_account_id === undefined)) {
    ctx.addIssue({ code: 'custom', path: ['linked_billing_account_id'],
      message: 'Conta recorrente vinculada é obrigatória para parcela embutida' });
  }
});
```
- `InstallmentPlanState` exportado como o enum acima. **Não** criar `Installment`s via nested write — nascem do serviço (S41). O form escreve só o plano.
- `total_amount`/`amount` Decimal→Number (CRUD). `lifecycle_state` string do model.

### 43.2 `employee.schema.ts` (variável-only + nuláveis + `superRefine`)
```ts
export const employeeSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, 'Nome é obrigatório'),
  role: z.string().optional().default(''),
  payment_type: z.enum(['fixed', 'variable', 'mixed']),
  base_salary: z.string().or(z.number()).nullable().optional()
    .transform((v) => (v !== null && v !== undefined && v !== '' ? Math.round(Number(v) * 100) / 100 : null)),
  default_due_day: z.number().int().min(1).max(31),
  is_active: z.boolean().default(true),
  notes: z.string().optional().default(''),
  person: personSimpleSchema.nullable().optional(),
  person_id: z.number().nullable().optional(),
  lease: leaseSchema.nullable().optional(),     // ou um summary, conforme o serializer real S42
  lease_id: z.number().nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.payment_type === 'fixed' && (data.base_salary === null || data.base_salary === undefined)) {
    ctx.addIssue({ code: 'custom', path: ['base_salary'], message: 'Salário base é obrigatório para tipo fixo' });
  }
});
```
- **Variável-only (Raymel, §18)**: `payment_type='variable'` + `base_salary=null`. O abatimento §4.6 (Rosa) é **backend** (S41) — o FE só expõe `person_id`/`lease_id`; **não** validar/computar abatimento aqui.

### 43.3 Hooks (`use-installment-plans.ts`, `use-employees.ts`)
- CRUD espelha `use-expenses.ts:18-106`: `useInstallmentPlans(filters?)` (`page_size` grande + `extractResults` + `schema.parse`), `useInstallmentPlan(id)`, `useCreate/Update/DeleteInstallmentPlan`. Filtros: `building_id`/`category_id`/`lifecycle_state`/`embedded`.
- `useInstallments(filters?)` (filtro `plan_id`/`due_date_from`/`due_date_to`) + `useUpdateInstallment` (PATCH `amount`/`due_date` — schedule). **Não** criar `useCreate/DeleteInstallment` (405 no backend).
- **`useConvertDeferred`** (espelha `useMarkExpensePaid`/`useGenerateInstallments` `use-expenses.ts:108-141`): `POST /finances/installment-plans/{id}/convert_deferred/` com os params reais da S41/S42 → retorna `InstallmentPlan` (parse Zod). **Invalida**: `queryKeys.finances.installmentPlans.all` **+** `queryKeys.finances.bills.all` **+** `queryKeys.finances.billingAccounts.all` (o item deferido pode ser `Bill`/`BillingAccount` — design §7/§8; invalidar os 3 garante consistência). Nenhuma lógica de conversão no FE — só dispara e parseia.
- `use-employees.ts`: CRUD espelhando `use-expenses.ts` (filtros `is_active`/`payment_type`/`person_id`/`lease_id`). Invalidar `queryKeys.finances.employees.all` (e `finance-*` é responsabilidade do backend/signals — o FE invalida só suas queries).
- **Todas as mutations** invalidam as keys relevantes no `onSuccess` (`void queryClient.invalidateQueries(...)`); HTTP só via `apiClient`.

### 43.4 `installment-plan-form-modal.tsx` (embutido via `watch`)
- Dialog (shadcn) + `useForm` + `zodResolver(installmentPlanFormSchema)` (schema local espelha `expense-form-modal.tsx:99-150`). Campos: `description`, `category_id` (`Select` de `useFinanceCategories`), `building_id` (`Select` nulável — null = "Condomínio"), `total_amount`, `installment_count`, `start_due_date`, `default_due_day`, `embedded` (`Switch`), `linked_billing_account_id` (`Select` de `useBillingAccounts`, **condicional** a `embedded` via `form.watch('embedded')`).
- **Embutido vs avulso** (§7): `embedded=true` → mostra e exige `linked_billing_account_id` (a parcela vira **linha** no `Bill` da conta recorrente — design §3.2; a UI só seta o vínculo, o dedup é backend). `embedded=false` → esconde o campo; cada parcela vira 1 `Bill` (S41).
- Create → `useCreateInstallmentPlan().mutate(payload)`; edit → `useUpdateInstallmentPlan()` (campos do plano; **não** edita parcelas aqui — schedule é o `installment-schedule-field`). Sucesso → `toast.success` (PT) + `onClose`; erro → `handleError(err, 'Erro ao salvar plano de parcelas')`.

### 43.5 `installment-schedule-field.tsx` (schedule read + PATCH)
- Lista as `installments` (nested do plano, ordenadas por `number`): por parcela exibe `number`, `due_date` (split), `amount` (`formatCurrency` em leitura; `Input` numérico em edição), badge `is_overdue` (§18 — vencida não-paga → "Vencida"). Editar `amount`/`due_date` → `useUpdateInstallment().mutate({ id, amount?, due_date? })` (PATCH; backend é a autoridade do sync realizado×schedule — S41; o FE **não** sincroniza).
- **Sem** append/remove (parcelas nascem do serviço; POST/DELETE → 405). Empty state PT ("Nenhuma parcela materializada ainda — gere as contas do mês"). `amount < 0` barrado por Zod (PT).

### 43.6 `convert-deferred-dialog.tsx` (UI de conversão de IPTU deferido — design §7/§8)
- Diálogo disparado por uma ação na linha de um plano/item **deferido** (`lifecycle_state==='deferred'`). Campos (params reais da assinatura `InstallmentPlanService.convert_deferred` — **ler S41/S42**): tipicamente `installment_count`, `start_due_date` (`YYYY-MM-DD`, default próximo mês via `formatDateISO`), `default_due_day`. Nota PT: "O IPTU anual deferido será reparcelado; o valor total é preservado."
- Submit → `useConvertDeferred().mutate({ id, ...params })`; sucesso → `toast.success(result.message ?? 'Plano de parcelas criado a partir do item deferido')` + fechar; erro → `handleError(err, 'Erro ao converter item deferido')`. **§18 «`convert_deferred` sem duplicar/perder»**: o FE não soma/valida o total — exibe o `InstallmentPlan` retornado (cujo `total_amount == valor deferido`, garantido pelo backend).

### 43.7 `employee-form-modal.tsx` (`payment_type` condicional)
- Dialog + RHF + Zod. Campos: `name`, `role`, `payment_type` (`Select` fixed/variable/mixed), `base_salary` (`Input` numérico — **condicional**: visível/obrigatório quando `payment_type ∈ {fixed, mixed}` via `form.watch('payment_type')`; oculto/null quando `'variable'`), `default_due_day`, `is_active` (`Switch`), `person_id` (`Select` de `usePersons`, nulável), `lease_id` (`Select` de `useLeases`, nulável — vínculo Rosa-like), `notes`.
- **Variável-only (Raymel, §18)**: `payment_type='variable'` → `base_salary` escondido e enviado `null`; o form ainda é válido. **Rosa-like**: `payment_type='mixed'` + `person_id`+`lease_id` setados (o abatimento §4.6 é backend — a UI só vincula). Create/update via hooks; toast/erro como acima.

### 43.8 Páginas CRUD (`installment-plans/page.tsx`, `employees/page.tsx`)
- `useCrudPage<InstallmentPlan>` / `useCrudPage<Employee>` (espelha `buildings/page.tsx:47-55`); `deleteMutation = useDeleteInstallmentPlan()` / `useDeleteEmployee()`; `useAuthStore()` → `isAdmin`.
- **Colunas** (gated): plano = Descrição · Prédio|"Condomínio" · Categoria · Total (`formatCurrency`) · Nº parcelas · Embutido (badge sim/não) · Estado (`lifecycle_state` via `StatusChip`/badge PT) · Ações (Editar / **Converter** [só se `deferred`] / Excluir). Folha = Nome · Cargo · Tipo (`payment_type` rótulo PT) · Salário base (`formatCurrency` ou "—" se null) · Vínculo (`person`/`lease` ou "—") · Ativo · Ações (Editar / Excluir).
- **Ações gated por `isAdmin`** (esconder quando `!isAdmin`). Header: título PT ("Planos de Parcelas" / "Folha de Pagamento"), botão "Novo …" (gated) + export (`crud.handleExport`). Loading → skeleton; empty → estado vazio PT. Delete = soft (AlertDialog → `useDelete*`).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md` + memória do projeto): mockar **APENAS fronteiras externas**. Aqui = a **rede via MSW** (`server.use(...)` por teste, estendendo `tests/mocks/data/finances.ts` + `financeHandlers`) — padrão de `late-payments-alert.test.tsx:33-36`. Para testes de página, é aceitável **`vi.spyOn` no módulo de hooks** desta sessão + `useAuthStore`/`usePersons`/`useLeases`/`useFinanceCategories`/`useBillingAccounts` (carve-out de fixture com `as` **só** no shape de retorno do hook, exatamente como S40/`late-payments-alert.test.tsx`). **NUNCA** mockar TanStack Query, `apiClient`, componentes internos, ou os schemas Zod. Usar `renderWithProviders`/`createTestQueryClient` (`test-utils.tsx:15-44`).

### 1. RED — escrever os testes primeiro (devem falhar por arquivo/símbolo inexistente)

Cobrir, no mínimo:

**`use-installment-plans.test.tsx`** (MSW; `renderHook`+`createWrapper`)
- [ ] `useInstallmentPlans` lista paginada → `results` extraídos + `total_amount` parseado para **Number**; filtros (`building_id`/`lifecycle_state`/`embedded`) vão na querystring.
- [ ] `useCreateInstallmentPlan` envia `category_id`/`building_id`/`linked_billing_account_id` (write) e o retorno tem `category`/`building` **nested** (read); invalida `finances.installmentPlans`.
- [ ] `useUpdateInstallment` faz **PATCH** `installments/{id}/` com `amount`/`due_date`; retorno reflete novo `amount` (Number).
- [ ] **`useConvertDeferred`** faz POST `installment-plans/{id}/convert_deferred/` → retorna `InstallmentPlan` parseado; invalida `installmentPlans` **+** `bills` **+** `billingAccounts` (§18 «convert_deferred sem duplicar/perder» — o teste assere o `total_amount` retornado pelo MSW = valor deferido).
- [ ] erro 500 numa mutation → estado de erro propagado (sem swallow).

**`use-employees.test.tsx`**
- [ ] `useEmployees` lista + filtros (`is_active`/`payment_type`/`person_id`).
- [ ] `useCreateEmployee` `payment_type='variable'`, `base_salary=null` (Raymel) → enviado sem `base_salary`/com null; retorno parseado. **§18 «variável-only»**.
- [ ] `useCreateEmployee` `payment_type='mixed'` + `person_id`+`lease_id` (Rosa-like) → write com `_id`; retorno nested `person`/`lease`.
- [ ] `useDeleteEmployee` invalida `finances.employees`.

**`installment-plan-form-modal.test.tsx`**
- [ ] create: preencher campos → submit chama `useCreateInstallmentPlan().mutate` com `{ description, category_id, building_id, total_amount, installment_count, start_due_date, default_due_day, embedded, linked_billing_account_id? }`.
- [ ] `embedded=true` (via `watch`) → mostra `Select` de `billing_account` e **exige** `linked_billing_account_id` (sem ele → Zod barra, PT, `mutate` não chamado); `embedded=false` → campo escondido.
- [ ] edit: campos pré-preenchidos; submit chama `useUpdateInstallmentPlan`; **não** edita parcelas no modal (schedule é outro componente).
- [ ] validação: sem descrição/`installment_count` inválido → mensagem PT, `mutate` não chamado.

**`installment-schedule-field.test.tsx`** (montar dentro de host de teste; mock do boundary `useUpdateInstallment` via MSW ou spy)
- [ ] renderiza N parcelas ordenadas por `number` com `due_date` (split) + `amount` (`formatCurrency`).
- [ ] editar `amount` de uma parcela → `useUpdateInstallment().mutate({ id, amount })` (PATCH); `amount < 0` barrado por Zod (PT).
- [ ] **não** há botão de adicionar/remover parcela (POST/DELETE → 405; verificar ausência). Empty state PT quando 0 parcelas.
- [ ] `is_overdue` da parcela → badge "Vencida" (sob `@freeze_time`/fixture; §18 — futura não vira overdue espúrio).

**`convert-deferred-dialog.test.tsx`** (boundary `useConvertDeferred` via spy)
- [ ] submit com os params reais → `mutate({ id, ...params })` chamado; sucesso → `toast.success` (mensagem do servidor) + `onClose`; erro → `handleError` (toast de erro).
- [ ] a UI **não** soma/valida o total (exibe o `InstallmentPlan` retornado); nota PT de "valor preservado" presente.
- [ ] o diálogo só é acionável para `lifecycle_state==='deferred'` (a ação na linha some/desabilita para outros estados — verificar na page test ou aqui).

**`employee-form-modal.test.tsx`**
- [ ] `payment_type='variable'` → `base_salary` **escondido**; submit válido sem `base_salary`. **§18 «variável-only»**.
- [ ] `payment_type='fixed'` → `base_salary` visível e **obrigatório** (vazio → Zod barra PT).
- [ ] `payment_type='mixed'` + `person_id`+`lease_id` (Rosa-like) → submit com `_id`s; o FE **não** valida abatimento (§4.6 é backend).
- [ ] edit: pré-preenche; submit chama `useUpdateEmployee`.

**`installment-plans-page.test.tsx`** (mock dos hooks desta sessão + `useAuthStore` via spy ou MSW)
- [ ] `isAdmin=false` → "Novo …"/Editar/Converter/Excluir **ausentes** (tabela renderiza p/ leitura); `isAdmin=true` → presentes.
- [ ] ação **Converter** aparece **só** para `lifecycle_state==='deferred'` (não para `active`/`paid`/`canceled`).
- [ ] coluna Total via `formatCurrency`; prédio null → "Condomínio"; Embutido → badge sim/não; Estado via `StatusChip`/badge (rótulo + ícone, não só cor).
- [ ] DELETE → soft (AlertDialog → `useDeleteInstallmentPlan`); loading → skeleton; empty → estado PT.

**`employees-page.test.tsx`**
- [ ] gating `is_staff` (ações ausentes p/ não-admin); Salário base null → "—"; `payment_type` rótulo PT; Vínculo `person`/`lease` ou "—".
- [ ] DELETE soft; loading/empty PT.

> Rodar (devem **falhar**):
> ```bash
> cd frontend
> npx vitest run "lib/api/hooks/__tests__/use-installment-plans.test.tsx" "lib/api/hooks/__tests__/use-employees.test.tsx" "app/(dashboard)/finances/installment-plans" "app/(dashboard)/finances/employees"
> ```

### 2. GREEN — implementar schemas + hooks + query-keys/MSW + páginas/modais
1. Schemas: `installment-plan.schema.ts`, `employee.schema.ts` (espelhar `income.schema.ts`/`expense.schema.ts`).
2. Hooks: `use-installment-plans.ts`, `use-employees.ts` (espelhar `use-expenses.ts`); estender `query-keys.ts` (`finances.installmentPlans`/`installments`/`employees`).
3. MSW: estender `tests/mocks/data/finances.ts` + `financeHandlers` (3 grupos de rotas).
4. Páginas/modais: `installment-plans/` (page + 4 componentes) e `employees/` (page + 2 componentes); `ROUTES.*` em `constants.ts`; itens no grupo "Condomínio" do `sidebar.tsx`. Reusar `useCrudPage`, `StatusChip`/`computeLineTotal` (S40), `useFinanceCategories`/`useBillingAccounts` (S39) — **import direto da fonte, sem re-export**.

Rodar até verde:
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-installment-plans.test.tsx" "lib/api/hooks/__tests__/use-employees.test.tsx" "app/(dashboard)/finances/installment-plans" "app/(dashboard)/finances/employees"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Helper único de money-transform reusado pelos novos schemas (se a S39 já extraiu `money.ts`, **importar** dele — não duplicar a transform `string→Number`).
- Reusar `StatusChip` (S40) para `lifecycle_state`; se o mapeamento de `payment_type`→rótulo PT for usado em coluna **e** form, extrair **um** helper (`PAYMENT_TYPE_LABELS`). `useCrudPage` reusado verbatim nas 2 páginas.
- Sub-componentes pequenos (`ScheduleRow`, `EmployeeRow`) com responsabilidade única; sem comentários supérfluos; sem código especulativo (YAGNI).

### 4. VERIFY — gate frontend (escopo desta sessão)
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-installment-plans.test.tsx" "lib/api/hooks/__tests__/use-employees.test.tsx" "app/(dashboard)/finances/installment-plans" "app/(dashboard)/finances/employees"
npx tsc --noEmit
npx eslint "lib/schemas/finances/installment-plan.schema.ts" "lib/schemas/finances/employee.schema.ts" "lib/api/hooks/use-installment-plans.ts" "lib/api/hooks/use-employees.ts" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "app/(dashboard)/finances/installment-plans" "app/(dashboard)/finances/employees"
```
Zero erros e zero avisos em todos (ESLint strict-type-checked, TypeScript strict + `noUncheckedIndexedAccess`).

---

## Constraints

- **Camada por responsabilidade** (`.claude/rules/architecture.md` Frontend Layers): páginas/modais/diálogos consomem hooks; demais componentes **puros**. **Nenhum** componente chama `apiClient`/axios. Hooks **não** renderizam nem decidem permissão (o gating é na UI; a autoridade é o backend `FinancialReadOnly`).
- **TanStack Query v5**: `useQuery` para listas; mutations invalidam no `onSuccess` (`void queryClient.invalidateQueries(...)`). **Não** usar `useSuspenseQuery`. **Não** reimplementar optimismo aqui (não há toggle de pagamento nesta sessão).
- **Decimal**: CRUD = `number` (transformado no schema); o front **nunca** recalcula `amount_total`/abatimento de dados do backend (lê o que a API devolve — design §4.4/§4.6).
- **Datas puras** `YYYY-MM-DD` por **split** (`late-payments-alert.tsx:17-21`), **nunca** `new Date(iso)`. `formatDateISO`/`formatCurrency`/`formatMonthYear` de `formatters.ts`.
- **`is_staff` gating**: esconder toda UI de escrita (criar/editar/excluir/converter/PATCH schedule) quando `!user.is_staff` (`useAuthStore`/`useCurrentUser`). O backend é a autoridade — o front só esconde (`.claude/rules/security.md`).
- **Status nunca só por cor** — sempre rótulo + ícone (acessibilidade). Reusar `StatusChip` (S40).
- **`installments`**: só **read + PATCH** (schedule). **Não** expor criar/remover parcela (405 backend). **Sem** UI de pagamento de parcela (pagamento é `bills/{id}/pay`, Fase 2).
- **`as`/`!` proibidos em produção** (regra do projeto + memória): schemas/hooks/componentes sem `as`/non-null — corrigir o tipo na raiz (`import type`, `??`, null guards, `noUncheckedIndexedAccess`). **CARVE-OUT (só fixtures de teste)**: `as <Tipo>`/`as unknown as <Mutation>` permitido **apenas** no shape de retorno de hooks de query/mutation do TanStack e no corpo MSW (`request.json()`), **exatamente** como S40/`late-payments-alert.test.tsx`. Em produção, proibido.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o código.
- **Sem re-export / barrel files / shims**: importar tipos/hooks **direto da fonte** (`@/lib/schemas/finances/*`, `@/lib/api/hooks/*`). Reusar `FinanceCategory`/`BillingAccount`/`StatusChip`/`computeLineTotal` (importar de S39/S40, **não** redefinir).
- **Sem deps novas**; sem `from __future__`/`TYPE_CHECKING` (irrelevante no FE).
- **Escopo de fases**: **sem** projeção/simulação (Fase 5), **sem** distribuição/owner (Fase 6), **sem** KPIs de saldo (Fase 4), **sem** UI de pagamento de parcela, **sem** criar/remover `Installment`.
- **Coexistência**: **não** alterar/remover a camada S39, a UI S40 (`finance-calendar/*`, `finances/bills/*`), nem o legado (`financial/*`). Estender, não recriar.
- **SOLID/DRY/KISS/YAGNI/Clean Code** (`.claude/rules/design-principles.md`) — componentes pequenos, helpers extraídos uma vez, sem workarounds, sem TODO/FIXME, todos os consumidores atualizados.
- **Não rodar a suíte completa** — só os arquivos desta sessão.

---

## Critérios de Aceite (binários)

- [ ] `frontend/lib/schemas/finances/installment-plan.schema.ts` com `installmentPlanSchema`/`installmentSchema` (+ tipos) + enum `InstallmentPlanState`: Decimal string→Number; FK dual (`category`/`category_id`, `building`/`building_id` nulável, `linked_billing_account`/`_id` nulável); `installments` nested read-only; `superRefine` `embedded ⇒ linked_billing_account_id` (PT). O front **não** recalcula `amount_total`.
- [ ] `frontend/lib/schemas/finances/employee.schema.ts` com `employeeSchema` (+ tipo) + enum `EmployeePaymentType`: `base_salary` nulável (variável-only); `person`/`person_id`, `lease`/`lease_id` nuláveis; `superRefine` `fixed ⇒ base_salary` (PT).
- [ ] `use-installment-plans.ts`: `useInstallmentPlans`/`useInstallmentPlan`/`useCreate|Update|DeleteInstallmentPlan`, `useInstallments`/`useUpdateInstallment` (PATCH schedule — **sem** create/delete), `useConvertDeferred` (POST → retorna `InstallmentPlan`, invalida `installmentPlans`+`bills`+`billingAccounts`). `use-employees.ts`: CRUD completo. Todos via `apiClient`, parse Zod, invalidando `queryKeys.finances.*`.
- [ ] `query-keys.ts` ganha `finances.installmentPlans`/`installments`/`employees` (`all`/`list`/`detail`, `as const`); grupos existentes (incl. `finances.*` da S39) intactos.
- [ ] Página `finances/installment-plans/`: `page.tsx` (`useCrudPage<InstallmentPlan>` + `DataTable` + AlertDialog delete) + `installment-plan-columns`/`installment-plan-form-modal` (embutido via `watch`) /`installment-schedule-field` (read+PATCH, sem add/remove) /`convert-deferred-dialog` (UI de conversão de IPTU deferido).
- [ ] Página `finances/employees/`: `page.tsx` (`useCrudPage<Employee>`) + `employee-columns`/`employee-form-modal` (`payment_type` condicional via `watch`; variável-only sem `base_salary`).
- [ ] Conversão de deferido: ação visível **só** para `lifecycle_state==='deferred'`; `useConvertDeferred` dispara e a UI exibe o `InstallmentPlan` retornado (valor preservado — backend; o FE não soma).
- [ ] Toda UI de escrita **gated por `is_staff`**; leitura sempre visível.
- [ ] `ROUTES.FINANCES_INSTALLMENT_PLANS`/`FINANCES_EMPLOYEES` em `constants.ts`; itens "Parcelas"/"Folha" no grupo "Condomínio" do `sidebar.tsx` (S40); rotas/menu legados intactos.
- [ ] `tests/mocks/data/finances.ts` estendido (`createMockInstallmentPlan`/`createMockInstallment`/`createMockEmployee`) + `financeHandlers` com as 3 rotas (incl. `convert_deferred` e `installments` GET/PATCH); handlers existentes intactos.
- [ ] Testes cobrem: hooks (CRUD+filtros+parse Number, `useConvertDeferred` invalidação tripla + total preservado, variável-only); modais (embutido `watch`+`superRefine`, `payment_type` condicional, schedule PATCH sem add/remove, convert dialog); páginas (gating `is_staff`, "Converter" só p/ `deferred`, soft-delete, formatação moeda/data por split, prédio null → "Condomínio"). Edge-cases §18 (variável-only; convert sem duplicar/perder; parcela overdue) presentes.
- [ ] `npx vitest run` (os arquivos desta sessão) 100% verde.
- [ ] `npx tsc --noEmit` limpo; `npx eslint` (todos os arquivos tocados) zero erros/zero avisos — **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção (único `as` = carve-out de fixture de teste).
- [ ] Sem re-exports/barrel; sem dependência nova; `FinanceCategory`/`BillingAccount`/`StatusChip`/`computeLineTotal` importados (não redefinidos); camada S39/UI S40/legado intactos; sem projeção/distribuição/KPI/pagamento-de-parcela.

---

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão — colar saída como evidência):
   ```bash
   cd frontend
   npx vitest run "lib/api/hooks/__tests__/use-installment-plans.test.tsx" "lib/api/hooks/__tests__/use-employees.test.tsx" "app/(dashboard)/finances/installment-plans" "app/(dashboard)/finances/employees"
   npx tsc --noEmit
   npx eslint "lib/schemas/finances/installment-plan.schema.ts" "lib/schemas/finances/employee.schema.ts" "lib/api/hooks/use-installment-plans.ts" "lib/api/hooks/use-employees.ts" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "app/(dashboard)/finances/installment-plans" "app/(dashboard)/finances/employees"
   ```
2. Atualizar `prompts/SESSION_STATE.md` (somente a tabela de progresso/notas da feature Condomínio Finance — **NÃO** editar `ROADMAP.md` nem o que o orquestrador gerencia):
   - Marcar a Sessão 43 como **concluída**.
   - **Arquivos Criados**: 2 schemas (`installment-plan.schema.ts`, `employee.schema.ts`), 2 hooks (`use-installment-plans.ts`, `use-employees.ts`), `installment-plans/page.tsx` + 4 componentes, `employees/page.tsx` + 2 componentes, e os 8 arquivos de teste.
   - **Arquivos Modificados**: `query-keys.ts` (`finances.installmentPlans`/`installments`/`employees`), `constants.ts` (`ROUTES.FINANCES_INSTALLMENT_PLANS`/`FINANCES_EMPLOYEES`), `sidebar.tsx` (itens "Parcelas"/"Folha" no grupo "Condomínio"), `tests/mocks/data/finances.ts` + `tests/mocks/handlers.ts` (estendidos).
   - **Documentar decisões**: params reais de `useConvertDeferred` (conforme assinatura S41/S42); shape do `lease` no `employeeSchema` (full `leaseSchema` vs summary, conforme serializer real S42); comportamento de edição de parcela (PATCH-only, sem add/remove).
   - **Anotar divergências** se algum nome de rota/tipo/campo da S42/S40/S39 diferir deste prompt (qual, como foi consumido).
   - **Anotar contratos cross-session** (verbatim, ver abaixo) para as Fases 5/6 consumirem sem derivar.
3. Rodar `/audit` (skill `audit`) contra esta seção de **Critérios de Aceite** e corrigir gaps antes de fechar a sessão.
4. Commitar (a partir de `master`, criar branch da feature se necessário — ex.: `feat/condo-finance`):
   ```
   feat(finances): add installment-plans + employees frontend (schemas, hooks, pages, deferred-IPTU conversion UI)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **44 — Backend Fase 4 (Saldo + Reserva + Receita avulsa + Fechamento)** (lê o `SESSION_STATE.md` atualizado). A Fase 4 **adiciona** KPIs/saldo/reserva; quando a UI de Fase 4 vier, ela **adiciona** colunas/cards — **não** recria as páginas de Parcelas/Folha desta sessão.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim nas fases seguintes)

- **Schemas/tipos** (`@/lib/schemas/finances/*`): `InstallmentPlan`/`Installment` (+ `InstallmentPlanState` `'active'|'paid'|'deferred'|'canceled'`), `Employee` (+ `EmployeePaymentType` `'fixed'|'variable'|'mixed'`). Dinheiro CRUD = `number` (transformado); `installments` nested read-only no plano.
- **Hooks** (`@/lib/api/hooks/*`): `useInstallmentPlans`/`useInstallmentPlan`/`useCreate|Update|DeleteInstallmentPlan`; `useInstallments`/`useUpdateInstallment` (PATCH schedule); `useConvertDeferred` (POST → `InstallmentPlan`); `useEmployees`/`useEmployee`/`useCreate|Update|DeleteEmployee`. A Fase 5 (projeção) **lê** parcelas futuras via seu próprio hook de projeção (backend) — **não** recalcula a partir destes; a UI de parcelas/folha desta sessão é o único CRUD desses recursos.
- **query-keys**: `queryKeys.finances.installmentPlans`/`installments`/`employees` — as próximas telas usam os mesmos sub-grupos; **não** criar keys inline.
- **Rotas/menu**: `ROUTES.FINANCES_INSTALLMENT_PLANS = '/finances/installment-plans'`, `ROUTES.FINANCES_EMPLOYEES = '/finances/employees'`, itens no grupo "Condomínio" do `sidebar.tsx` (as próximas telas de `finances` registram aí).
- **MSW**: `createMockInstallmentPlan`/`createMockInstallment`/`createMockEmployee` + os handlers de `installment-plans`/`installments`/`employees` disponíveis para os testes das fases seguintes (estender, não recriar).
- **Padrão de UI**: páginas de Parcelas/Folha seguem o mesmo `useCrudPage<T>` + form modal + `StatusChip` (S40); a conversão de deferido é um diálogo que dispara `useConvertDeferred` e exibe o `InstallmentPlan` retornado (valor preservado — backend, o FE nunca soma/valida o total).
