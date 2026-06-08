# Sessão 46 — Frontend Fase 4: KPIs de saldo + Reserva (movimentos) + Receita avulsa + Fechamento mensal

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → **46** → 47 → 48 → 49 → 50 (esta **fecha a Fase 4 — frontend de saldo/reserva/income/fechamento**)
> Esta sessão entrega a **UI da Fase 4** (consumindo a API da S45) + a **camada de dados de frontend que falta** para a Fase 4 (schemas Zod + hooks TanStack + query-keys + MSW dos novos recursos `reserves`/`reserve-movements`/`income-entries`/`condo-month-closes` + dashboard `overview`/`monthly_balance`/`by_category`): (1) **fileira de KPIs** no dashboard — Caixa / Reserva / Resultado do mês / Atrasados / Saldo total — via `StatCard`+`AmountDisplay` (primitivos novos espelhando `controle-financeiro`); (2) **página de Reserva** (saldo + ledger de movimentos + diálogos depósito/saque); (3) **página de Receita avulsa** (CRUD de `IncomeEntry` via `useCrudPage`); (4) **página de Fechamento mensal** (lista de `CondoMonthClose` open/closed + ações fechar/reabrir, gating cronológico exibido pelo erro do backend). **Sem projeção/simulação (Fase 5 — S47/S48); sem distribuição por proprietário/donos externos (Fase 6 — S49/S50); sem gráficos blocking no gate.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.2 caixa/competência/reserva/saldo total, §4.3 reserva sem dupla-contagem, §4.4 atrasado, §4.5 receita filtrada, §4.7 fold/âncora, §6 receita não-invasiva, §9 API, §10 Frontend/Dashboard, §11 cache lado consumidor, §15 fora de escopo, §18 edge-cases das fases 2/4)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md` — **confirmar S45 (API Fase 4) e S40 (UI Fase 2) concluídas**. Se a **S45 não estiver concluída, PARE** (DEPENDENCY ORDER 45 → 46): esta sessão consome os endpoints e shapes que ela entregou. Se a **S40 não estiver concluída, PARE** (DEPENDENCY ORDER 40 → 46): esta sessão monta os KPIs **acima** do `CombinedCalendarSection` da S40, reusa o grupo de menu "Condomínio" e o `ROUTES.FINANCES_BILLS` que a S40 criou, e segue o padrão de página/teste estabelecido lá.
- **Contrato da API Fase 4 (verbatim, NÃO derivar)**: a seção "Contratos cross-session definidos por esta sessão (consumir verbatim)" no fim de `@prompts/45-finances-balance-close-services-api.md` (shapes de `overview`/`monthly_balance`/`by_category`, ações `deposit`/`withdraw`/`close`/`reopen`, serializers `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose`). **Se algum nome de campo do serializer real da S45 divergir deste prompt, o serializer real prevalece** (ajustar o schema, anotar a divergência no handoff; nunca inventar campo).
- **Contrato da camada de dados Fase 2 (a estender, NÃO recriar)**: a seção de contratos no fim de `@prompts/39-finances-frontend-data-layer.md` (grupo `queryKeys.finances.*`, `lib/schemas/finances/*`, `lib/schemas/finances/money.ts`, `tests/mocks/data/finances.ts`, `financeHandlers`).
- **Regras do projeto**: `frontend/CLAUDE.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`.

### Exemplares (arquivo:linha — abrir e seguir; exemplar > descrição)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`StatCard` (primitivo de KPI a portar — design reference do `controle-financeiro`)** | `c:/Users/alvar/git/personal/controle-financeiro/financial-control-v2/apps/web/src/components/shared/StatCard.tsx:1-74` (props `label`/`value`/`icon`/`tone`/`delta`; `valueTone`/`iconTone` por tom; `CardContent flex flex-col gap-2`) | **Fonte do design** do `StatCard` desta sessão. **ADAPTAR**: o `Card` deste repo (`components/ui/card.tsx:5-17`) **NÃO** tem a prop `surface` — remover `surface`; usar `Card`/`CardContent` daqui; tons mapeados para tokens deste repo (`text-success`/`text-destructive`/`text-warning`/`text-info`/`text-foreground`/`text-muted-foreground`). |
| **`AmountDisplay` (primitivo de valor monetário a portar)** | `c:/Users/alvar/git/personal/controle-financeiro/financial-control-v2/apps/web/src/components/shared/AmountDisplay.tsx:1-49` (props `amount`/`showSign`/`size`/`variant`; `tabular-nums`; cor por sinal) | **Fonte do design** do `AmountDisplay`. **ADAPTAR**: usar `formatCurrency` de `@/lib/utils/formatters` (não `formatCurrencyValue`); variantes mapeadas para os tokens deste repo (`text-success`/`text-destructive`/`text-foreground`). |
| **KPI cards reais DESTE repo (grid + Card/CardHeader/CardContent + tokens + skeleton)** | `frontend/app/(dashboard)/financial/_components/balance-cards.tsx:25-119` (`BalanceCardsSkeleton` :25-34; grid `grid gap-4 md:grid-cols-2 lg:grid-cols-4` :48; Card por KPI com `CardTitle`+ícone lucide+valor `text-3xl font-bold`+tom condicional `balance>=0 ? text-success : text-destructive` :88-99) | **Exemplar canônico** da fileira de KPIs do condomínio. A nova `FinanceKpiRow` usa **`StatCard`** (extraído) em vez de repetir `Card` 5×, mas a **estrutura/skeleton/grid/tokens** espelham este arquivo. 5 KPIs → grid `md:grid-cols-2 lg:grid-cols-5` ou `xl:grid-cols-5`. |
| **Dashboard financeiro (montagem de KPIs + loading/erro + `{year,month}` por `new Date`)** | `frontend/app/(dashboard)/financial/page.tsx:16-77` (`year`/`month` :17-19; `useDashboardSummary` :20; `isLoading` → skeleton :30; erro → Card :32-38; `data && <BalanceCards …>` :40-42; charts montados **fora** do bloco de dados :54-67) | Modelo de montagem da `FinanceKpiRow` no dashboard do condomínio (**acima** do `CombinedCalendarSection` da S40). |
| **Calendário combinado (S40 — onde os KPIs entram ACIMA)** | `frontend/app/(dashboard)/_components/finance-calendar/combined-calendar-section.tsx` (container `'use client'`, `useState {year,month}`, `useBuildings`+`Select`, grid 3 colunas) | A `FinanceKpiRow` consome o **mesmo** `{year,month,buildingId}` do calendário. **Decisão (anotar no handoff)**: montar a `FinanceKpiRow` no `app/(dashboard)/page.tsx` **acima** do `<CombinedCalendarSection />` (S40) — **não** recriar o calendário; os dois compartilham nav de mês via estado local de cada um (KISS — não acoplar via contexto agora). |
| **CRUD page canônica (`useCrudPage` + DataTable + form modal + AlertDialog delete + export)** | `frontend/app/(dashboard)/buildings/page.tsx:42-242` (`useCrudPage<Building>` :47-55; colunas + ações :57-106; header :114-150; `<DataTable>` :183-189; modal :191-195; delete dialogs :197-239) | **Exemplar canônico** da página de **Receita avulsa** (`finances/income-entries/page.tsx`). |
| **CRUD page financeira com filtros/`dynamic`/`useCrudPage`/`useAuthStore`** | `frontend/app/(dashboard)/financial/incomes/page.tsx:1-60` (imports `useCrudPage`/`DataTable`/`DeleteConfirmDialog`/`useExport`/`formatCurrency`/`formatDate` :24-37; `dynamic(() => import(...form-modal))` :52-55) | Forma da página de Receita avulsa (filtros `is_received`/`building_id`/date range; modal lazy; export). |
| **Form modal financeiro (Dialog + RHF + Zod + create/update + selects + `toast`)** | `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx:1-120` (Dialog :7-13; `useForm({resolver: zodResolver, defaultValues})` :108-120; create/update :99-101; selects `useBuildings`/categorias :103-106) | **Exemplar canônico** do `income-entry-form-modal.tsx`: Dialog + RHF + Zod; campos `description`/`amount`/`income_date`/`is_received`/`received_date`/`building_id`/`category_id`/`notes`; selects de `useBuildings`/`useFinanceCategories`. |
| **Form de singleton/ação simples (RHF+Zod+`useAuthStore` gating+`mutateAsync`+`toast`)** | `frontend/app/(dashboard)/financial/settings/page.tsx:35-162` (`isAdmin = user?.is_staff ?? false` :37; `useForm` :41-48; `reset` no `useEffect` quando data chega :50-58; submit `mutateAsync` + `toast` + `handleError` :60-72; botão só se `isAdmin` :152-156) | **Exemplar canônico** dos diálogos de **depósito/saque** (form pequeno `amount`/`movement_date`) e da ação de **fechar/reabrir mês** (`{year,month}` + submit + toast do erro PT do backend). |
| **`is_staff` gating (fonte do usuário)** | `frontend/store/auth-store.ts` (`user.is_staff: boolean`) via `useAuthStore()` (`financial/settings/page.tsx:36-37`) **ou** `useCurrentUser()` em `frontend/lib/api/hooks/use-auth.ts:107` | Esconder toda UI de escrita (depósito/saque/criar income/excluir/fechar/reabrir) quando `!is_staff`. O backend `FinancialReadOnly` é a autoridade; o front só esconde. |
| **Hook CRUD (list/detail/create/update/delete + invalidate; filtros limpos + `extractResults` + `.parse`)** | `frontend/lib/api/hooks/use-expenses.ts:1-141` (`Object.fromEntries(...v!==undefined)` :19-21; `useQuery` list `extractResults`+`.parse` :23-33; `useCreate/Update/Delete` invalidate :47-106; action POST :108-122) | **Exemplar canônico** de `use-income-entries`/`use-reserves`/`use-condo-month-closes`. Reusar `extractResults` + `schema.parse`. |
| **Hook de dashboard read-only (`staleTime`, params `year`/`month`)** | `frontend/lib/api/hooks/use-daily-control.ts:66-92` (`useDailyBreakdown`/`useDailySummary` `useQuery`+`params:{year,month}`+`staleTime`) | Forma de `useFinanceOverview(year,month,buildingId?)`/`useMonthlyBalance(year)`/`useByCategory(year,month,buildingId?)` — **`useQuery` + `placeholderData: keepPreviousData`** (nav de mês sem flash; design §10), `staleTime` curto. **NÃO** `useSuspenseQuery`. |
| **Hook calendário/`placeholderData` (espelhar para overview)** | `frontend/lib/api/hooks/use-combined-calendar.ts` (S39: `useQuery` + `keepPreviousData` + `staleTime`, `building_id` só quando definido) | Forma exata de `useFinanceOverview` (mesmos params `{year,month,building_id?}`, `placeholderData: keepPreviousData`). Dashboard = **string Decimal** (não transformar a resposta; converter na UI). |
| **query-keys central (grupo `finances` a estender)** | `frontend/lib/api/query-keys.ts` (grupo `finances.*` da S39: `bills`/`payments`/`combinedCalendar`/`overdueBills`); `rentCalendar.month` (`buildingId ?? null`) | **Estender** `finances` com sub-grupos `reserves`/`reserveMovements`/`incomeEntries`/`condoMonthCloses`/`overview`/`monthlyBalance`/`byCategory` (espelhar a forma `all`/`list(filters?)`/`detail(id)` e `month(year,month,buildingId?)`). **Não** alterar sub-grupos existentes. |
| **Schema Zod (Decimal string→Number no boundary + FK dual + auditoria)** | `frontend/lib/schemas/income.schema.ts:6-32` (`amount` `.string().or(z.number()).transform(Number)` :9-12; dual `building`/`building_id`/`category`/`category_id` :14-19) + `frontend/lib/schemas/finances/money.ts` (S39: helper `moneyToNumber`) | **Exemplar canônico** de `income-entry.schema.ts`/`reserve.schema.ts`/`reserve-movement.schema.ts`/`condo-month-close.schema.ts`. Reusar `moneyToNumber` da S39 (import direto; **sem** duplicar transform). |
| **`formatCurrency` / `formatMonthYear` / `formatDate`** | `frontend/lib/utils/formatters.ts:5` (`formatCurrency` → "R$ 1.500,00"), `:89` (`formatMonthYear` → "Junho de 2026" **com " de "**), `:79` (`formatDate`) | Moeda/rótulo de mês/data. **NOTA**: `formatMonthYear` produz "Junho de 2026" (com " de ") — asserir exatamente isso. Datas puras `YYYY-MM-DD`/`YYYY-MM-01` por **split** (não `new Date(iso)`). |
| **Parsing ISO puro por split (NUNCA `new Date(iso)`)** | `frontend/app/(dashboard)/_components/late-payments-alert.tsx:17-21` (`dateStr.split('-')`) | Datas das colunas/ledger por split (bug de timezone). |
| **`ROUTES` + grupo de menu "Condomínio" (criado na S40)** | `frontend/lib/utils/constants.ts:48-71` (`ROUTES`, S40 adicionou `FINANCES_BILLS`); `frontend/components/layouts/sidebar.tsx:44-58` (`financialChildren`) + `:96-101` (item pai com `children`) | Adicionar `ROUTES.FINANCES_RESERVE`/`FINANCES_INCOME`/`FINANCES_MONTH_CLOSE` e registrá-las no grupo **"Condomínio"** que a S40 criou (não no "Financeiro" legado). |
| **Teste de componente do dashboard (`vi.spyOn` no módulo de hooks; `renderWithProviders`)** | `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx:1-154` (`makeQueryResult` :10-36 + `idleMutation` :38-55 com `as`-carve-out; `vi.spyOn(hooksModule,'useX')` :67-70; `renderWithProviders`) | **Padrão a copiar** para os testes de componente (`FinanceKpiRow`, páginas) — mockar **só** os hooks de dados + `useAuthStore`, nunca componentes internos/TanStack/`apiClient`/ORM. |
| **Teste de hook (MSW, sem mock de internals)** | `frontend/lib/api/hooks/__tests__/use-combined-calendar.test.tsx` (S39) + `frontend/tests/test-utils.tsx:55-78` (`renderWithProviders`/`createWrapper`) + `:15-28` (`createTestQueryClient` `gcTime:0`) | **Padrão a copiar** para `use-reserves.test.tsx`/`use-income-entries.test.tsx`/`use-finance-balance.test.tsx` — MSW por teste (`server.use`), `createWrapper`. |
| **MSW data + handlers de `finances` (S39 — a estender)** | `frontend/tests/mocks/data/finances.ts` + `financeHandlers` em `frontend/tests/mocks/handlers.ts` | **Estender** com `createMockReserve`/`createMockReserveMovement`/`createMockIncomeEntry`/`createMockCondoMonthClose`/`createMockFinanceOverview`/`createMockMonthlyBalance`/`createMockByCategory` + handlers das novas rotas. **Não** recriar os existentes (DRY). |

### Contrato de dados consumido (definido pela S45 — NÃO derivar; serializer real prevalece)

Os endpoints abaixo são **namespaced** sob `/api/finances/...` (o `baseURL` do `apiClient` já é `/api`; chamar `apiClient.get('/finances/...')`). Decimais vêm como **string** (dashboard e serializers). `reference_month`/`competence_month` = 1º dia (`YYYY-MM-01`).

- **`finance-dashboard/overview?year=&month=&building_id=`** → `{ year, month, result_of_month, cash_change_of_month, cash_balance, reserve_balance, total_balance, overdue_bills_total, overdue_bills_count, rent_overdue: { count, total_fee }, wedge_ok }` (todos os valores monetários **string**; counts/`wedge_ok` não-string). **Os 5 KPIs**: Caixa = `cash_balance`, Reserva = `reserve_balance`, Resultado do mês = `result_of_month`, Atrasados = `overdue_bills_total` (+ sub-total `rent_overdue.total_fee` de aluguel, separado — §4.4), Saldo total = `total_balance`.
- **`finance-dashboard/monthly_balance?year=`** → `[{ month, result_of_month, cash_change_of_month, cash_balance_end, reserve_balance_end, total_balance, is_closed }]` (12 meses; `is_closed` distingue mês fechado/aberto). *(Esta sessão pode exibir uma tabela simples; o gráfico de série é da Fase 5 — não obrigatório aqui.)*
- **`finance-dashboard/by_category?year=&month=&building_id=`** → breakdown de despesa por categoria (`name`/`color`/`amount` string). *(Donut = gráfico, **não-blocking** no gate — opcional; a tabela/JSON é o load-bearing. **Não** instalar Recharts aqui.)*
- **`reserves`** (CRUD; serializer com `balance` read-only string) + **`reserves/{id}/deposit`** `{ amount, movement_date?, reference?, notes? }` (transferência caixa→reserva; saldo total inalterado) + **`reserves/{id}/withdraw`** `{ amount, movement_date? }` (reserva→caixa; **guarda**: `amount > reserve_balance` → 400 PT "Saldo da reserva insuficiente.").
- **`reserve-movements`** (read list/retrieve; `kind` `deposit|withdrawal`, `amount` string, `movement_date`, `bill`/`bill_id` nullable, `reference`/`notes`). Ledger ordenado `(movement_date, id)`.
- **`income-entries`** (CRUD; `description`, `amount` string >0, `income_date`, `is_received`, `received_date` nullable, `building`/`building_id` nullable, `category`/`category_id` nullable, `notes`). Filtros `is_received`/`building_id`/date range.
- **`condo-month-closes`** (list/retrieve; `reference_month`, `status` `open|closed`, `closed_at`, `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out` string read-only, `breakdown`) + **`condo-month-closes/close`** `{ year, month }` (cronológico/sem gap → 400 PT; já fechado → 400 PT) + **`condo-month-closes/reopen`** `{ year, month }` (mês inexistente → 400 PT; recomputa cascata no backend).

> **NOTA crítica**: a guarda de saldo da reserva e a validação cronológica do fechamento **são do backend** (S45). O front **não** simula saldo nem ordem — só envia a ação e **exibe o erro PT do servidor** via `handleError`/`toast.error`. (design §4.3/§18 "a guarda de saldo é backend".)

---

## Escopo

### Arquivos a criar

**Primitivos de KPI** — `frontend/components/ui/`
- `stat-card.tsx` — `StatCard` (porta `controle-financeiro` adaptado ao `Card` deste repo; props `label`/`value`/`icon?`/`tone?`; tons → tokens deste repo; **sem** prop `surface`).
- `amount-display.tsx` — `AmountDisplay` (porta adaptado; usa `formatCurrency` daqui; props `amount`/`showSign?`/`size?`/`variant?`).
- `__tests__/stat-card.test.tsx`, `__tests__/amount-display.test.tsx`.

**Camada de dados Fase 4 (schemas + hooks + MSW)**
- `frontend/lib/schemas/finances/reserve.schema.ts` — `reserveSchema` (`name`/`notes`/`balance` string→Number) + `type Reserve`.
- `frontend/lib/schemas/finances/reserve-movement.schema.ts` — `reserveMovementSchema` (`kind` enum `'deposit'|'withdrawal'`, `amount` string→Number, `movement_date`, dual `bill`/`bill_id` nullable, `reference`/`notes`) + `type ReserveMovement` + enum `ReserveMovementKind`.
- `frontend/lib/schemas/finances/income-entry.schema.ts` — `incomeEntrySchema` (`amount` string→Number, `income_date`, `is_received`, `received_date` nullable, dual `building`/`building_id` + `category`/`category_id` nullable, `notes`) + `type IncomeEntry`.
- `frontend/lib/schemas/finances/condo-month-close.schema.ts` — `condoMonthCloseSchema` (`reference_month`, `status` enum `'open'|'closed'`, `closed_at` nullable, `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out` string→Number read-only, `breakdown` `unknown`) + `type CondoMonthClose` + enum `MonthCloseStatus`.
- `frontend/lib/api/hooks/use-reserves.ts` — `useReserves()` + `useReserve(id)` + `useCreate/Update/DeleteReserve` + `useDepositReserve` + `useWithdrawReserve` (ações POST → invalidam `reserves`+`reserveMovements`+`overview`).
- `frontend/lib/api/hooks/use-reserve-movements.ts` — `useReserveMovements(filters?)` (read; filtros `reserve_id`/`kind`/date range).
- `frontend/lib/api/hooks/use-income-entries.ts` — `useIncomeEntries(filters?)` + `useIncomeEntry(id)` + `useCreate/Update/DeleteIncomeEntry` (invalidam `incomeEntries`+`overview`).
- `frontend/lib/api/hooks/use-condo-month-closes.ts` — `useCondoMonthCloses(filters?)` + `useCloseMonth` + `useReopenMonth` (POST → invalidam `condoMonthCloses`+`overview`+`monthlyBalance`).
- `frontend/lib/api/hooks/use-finance-balance.ts` — `useFinanceOverview(year, month, buildingId?)` (`placeholderData: keepPreviousData`) + `useMonthlyBalance(year)` + `useByCategory(year, month, buildingId?)` + tipos `FinanceOverview*` hand-written (dashboard = **string**, não transformar).
- `frontend/lib/api/hooks/__tests__/use-reserves.test.tsx`, `__tests__/use-income-entries.test.tsx`, `__tests__/use-condo-month-closes.test.tsx`, `__tests__/use-finance-balance.test.tsx`.

**KPIs (dashboard)** — `frontend/app/(dashboard)/_components/finance-kpis/`
- `finance-kpi-row.tsx` — container `'use client'` (único que chama hook): `useFinanceOverview(year, month, buildingId?)`; renderiza 5 `StatCard` (Caixa/Reserva/Resultado/Atrasados/Saldo total) + skeleton + erro; `{year,month}` por estado local (default mês atual).
- `finance-kpi-row.test.tsx` (em `__tests__/`).

**Página de Reserva** — `frontend/app/(dashboard)/finances/reserve/`
- `page.tsx` — `'use client'`: `useReserves()` (a reserva é única — pegar a 1ª; design §5.2/§15 "uma por condomínio, sem UI de seleção"); card de saldo (`StatCard`/`AmountDisplay`); `DataTable` do ledger (`useReserveMovements`); botões **Depositar**/**Sacar** (gated `is_staff`) abrindo diálogos; export opcional.
- `_components/reserve-movement-columns.tsx` — colunas do ledger (data por split, tipo PT depósito/saque + ícone, valor `formatCurrency`, vínculo a conta quando `bill` setado vs transferência caixa quando `bill=null`).
- `_components/reserve-deposit-dialog.tsx` — Dialog + RHF + Zod (`amount`>0, `movement_date` default hoje, `reference?`/`notes?`); chama `useDepositReserve`.
- `_components/reserve-withdraw-dialog.tsx` — idem; chama `useWithdrawReserve`; erro do backend (saldo insuficiente) → `handleError`/`toast.error` (não simular saldo no front).
- `__tests__/reserve-page.test.tsx`, `__tests__/reserve-deposit-dialog.test.tsx`, `__tests__/reserve-withdraw-dialog.test.tsx`.

**Página de Receita avulsa** — `frontend/app/(dashboard)/finances/income-entries/`
- `page.tsx` — `useCrudPage<IncomeEntry>` + `DataTable` + filtros (`is_received`/`building_id`/date range) + AlertDialog delete + modal lazy + export.
- `_components/income-entry-columns.tsx` — colunas (descrição, prédio ou "Condomínio", competência/`income_date` por split, valor, recebido sim/não com ícone, ações gated).
- `_components/income-entry-form-modal.tsx` — Dialog + RHF + Zod; create via `useCreateIncomeEntry`, edit via `useUpdateIncomeEntry`; selects `useBuildings`/`useFinanceCategories`; `received_date` condicional a `is_received` (via `watch`).
- `__tests__/income-entries-page.test.tsx`, `__tests__/income-entry-form-modal.test.tsx`.

**Página de Fechamento mensal** — `frontend/app/(dashboard)/finances/month-close/`
- `page.tsx` — `useCondoMonthCloses()` + `DataTable` (competência por split, status open/closed + ícone, `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out` via `formatCurrency`, `closed_at`); botões **Fechar mês**/**Reabrir mês** (gated `is_staff`) abrindo diálogos `{year,month}`; o erro PT do backend (gap cronológico/já fechado/inexistente) é exibido via `toast.error`.
- `_components/month-close-action-dialog.tsx` — Dialog único reaproveitável (form `{year,month}`) parametrizado por modo `close|reopen`; chama `useCloseMonth`/`useReopenMonth`.
- `__tests__/month-close-page.test.tsx`, `__tests__/month-close-action-dialog.test.tsx`.

### Arquivos a modificar
- `frontend/lib/api/query-keys.ts` — estender o grupo `finances` (S39) com `reserves`/`reserveMovements`/`incomeEntries`/`condoMonthCloses`/`overview`/`monthlyBalance`/`byCategory`. Sub-grupos existentes **intactos**.
- `frontend/lib/utils/constants.ts` — adicionar `FINANCES_RESERVE: '/finances/reserve'`, `FINANCES_INCOME: '/finances/income-entries'`, `FINANCES_MONTH_CLOSE: '/finances/month-close'`. `FINANCES_BILLS` (S40) e rotas legadas **intactas**.
- `frontend/components/layouts/sidebar.tsx` — adicionar os 3 itens ao grupo **"Condomínio"** criado pela S40 (espelhar o formato `{ key: ROUTES.X, label }` de `financialChildren:44-58`). **Não** tocar nos itens existentes nem no grupo "Financeiro" legado.
- `frontend/app/(dashboard)/page.tsx` — montar `<FinanceKpiRow />` **acima** do `<CombinedCalendarSection />` (S40). **Não** remover/duplicar o calendário (decisão anotada no handoff).
- `frontend/tests/mocks/data/finances.ts` (S39) — **anexar** as factories Fase 4 (`createMockReserve`/`createMockReserveMovement`/`createMockIncomeEntry`/`createMockCondoMonthClose`/`createMockFinanceOverview`/`createMockMonthlyBalance`/`createMockByCategory`). Existentes intactas.
- `frontend/tests/mocks/handlers.ts` (S39) — **anexar** aos `financeHandlers` as rotas Fase 4 (CRUD + `deposit`/`withdraw`/`close`/`reopen` + `overview`/`monthly_balance`/`by_category`). Handlers existentes intactos.

### NÃO fazer (pertence a outras sessões)
- **Sem projeção/simulação** (tabela 12 meses como **gráfico**, `ComposedChart`, simulador, cards Real/Projetado, `cash-flow/{projection,simulate}`) — **Fase 5** (S47 BE → S48 FE). **Decisão pinada**: esta sessão pode exibir o JSON de `monthly_balance` numa **tabela simples** (read-only, sem chart), mas **não** monta a tela de projeção/simulação nem instala Recharts. (DEPENDENCY ORDER 47 → 48.)
- **Sem distribuição por proprietário / seção de donos externos** (cards "por proprietário", Tiago/Alvaro, `OwnerDistributionService`/`by_owner`) — **Fase 6** (S49 BE → S50 FE).
- **Sem donut por categoria como gráfico Recharts** — o `by_category` pode ser exibido como tabela (não-blocking); **não** instalar Recharts nem montar `PieChart` aqui (Fase 4 declara gráficos não-blocking; se desejado, fica como polish fora do gate).
- **Sem hooks/schemas/query-keys novos de Fase 2/3** — `bills`/`payments`/`billing-accounts`/`installments`/`employees` já existem (S39/S43). **Não** recriar. Se um hook necessário da S39 não existir, **PARE** e registre a lacuna.
- **Sem alterar** `use-combined-calendar.ts`, `finance-calendar/*`, `finances/bills/*` (S40), `use-rent-calendar.ts`, `rent-calendar/*`, `late-payments-alert.tsx`, nem o **módulo legado** (`expenses`/`daily`/`balance-cards.tsx`/`use-financial-dashboard`) — coexistência (design §1/§11/§15; não wirar os dois). O `balance-cards.tsx` legado é **só exemplar**, não tocar.
- **Sem mexer** em `client.ts`, `test-utils.tsx`, `query-client.ts`, `lib/types/api.ts`, `card.tsx`, `formatters.ts` — só **consumir**.
- **Sem backend** — `CondoBalanceService`/`CondoMonthCloseService`/serializers/viewsets/endpoints são da S45. Nada em `core/`/`finances/`.

---

## Especificação

Direção de dados (`frontend/CLAUDE.md` + `.claude/rules/architecture.md` Frontend Layers): **só os containers** (`finance-kpi-row.tsx`, as 3 `page.tsx`, e os modais/diálogos que disparam mutations) consomem hooks. Os demais componentes são **puros** (props in, callbacks out). **Nenhum componente chama `apiClient`/axios diretamente.** Forms = React Hook Form + Zod (nunca Ant Design Form). Moeda via `formatCurrency`/`AmountDisplay`; datas puras por **split** (nunca `new Date(iso)`). Mensagens ao usuário em **PT**; identificadores/tipos em **EN**.

### Decimal: CRUD vs dashboard (design §10, espelha S39)
- **CRUD** (`reserve`/`reserve-movement`/`income-entry`/`condo-month-close`): schema Zod transforma string→Number no boundary (`income.schema.ts:9-12` / `moneyToNumber` da S39). A UI usa `number`.
- **Dashboard** (`overview`/`monthly_balance`/`by_category`): tipos **hand-written**, dinheiro permanece **string** (como `use-combined-calendar`/`use-rent-calendar`); converter para `Number` **só** no boundary de exibição (`AmountDisplay`/`formatCurrency`). O front **nunca** recalcula KPIs do servidor.

### Primitivos `StatCard` / `AmountDisplay` (adaptados ao repo)
```ts
// components/ui/stat-card.tsx
type StatTone = 'brand' | 'positive' | 'negative' | 'warning' | 'neutral';
interface StatCardProps {
  label: string;
  value: React.ReactNode;       // já formatado (AmountDisplay ou string)
  icon?: React.ReactNode;
  tone?: StatTone;              // default 'neutral'
  className?: string;
}
```
- Usar `Card`/`CardContent` de `@/components/ui/card` (**sem** `surface` — esse repo não tem). Tons → tokens deste repo: `positive→text-success`, `negative→text-destructive`, `warning→text-warning`, `brand→text-primary`/`text-foreground`, `neutral→text-foreground`. Valor `text-2xl font-bold tabular-nums`; label `text-xs uppercase tracking-wider text-muted-foreground`. Ícone num quadrado tom-colorido (espelha `iconTone` do exemplar, adaptado).
- `AmountDisplay`: `formatCurrency(Math.abs(amount))` + sinal opcional; cor por `variant` (`positive`/`negative`/`neutral`) ou por sinal quando `variant` ausente; `tabular-nums`. **Sem** dependência nova.

### `FinanceKpiRow` (container — design §10, 5 KPIs)
- `'use client'`. `useState {year,month}` (default mês atual via `new Date()` — local, KISS). `useFinanceOverview(year, month, buildingId?)` (sem filtro de prédio obrigatório nesta fileira — pode omitir `buildingId`, KISS). Loading → 5 skeleton cards (espelha `BalanceCardsSkeleton:25-34`); erro → Card de erro PT (espelha `financial/page.tsx:32-38`).
- 5 `StatCard` em `grid gap-4 md:grid-cols-2 lg:grid-cols-5`:
  - **Caixa** (`cash_balance`, tom `positive` se ≥0 senão `negative` — caixa pode ser negativo, §4.3; ícone `Wallet`).
  - **Reserva** (`reserve_balance`, tom `brand`; ícone `PiggyBank`).
  - **Resultado do mês** (`result_of_month`, tom por sinal; ícone `TrendingUp`/`TrendingDown`). Rótulo PT "Resultado do mês — {formatMonthYear(year,month)}".
  - **Atrasados** (`overdue_bills_total`, tom `negative` se >0 senão `neutral`; ícone `AlertTriangle`). **Sub-texto** com o atraso de **aluguel** separado: `rent_overdue.total_fee` (§4.4 — figura distinta, não somar no KPI de contas).
  - **Saldo total** (`total_balance`, tom por sinal; ícone `DollarSign`). Rótulo "Saldo total (Caixa + Reserva)".
- Valores via `AmountDisplay`/`formatCurrency` lendo as **strings** do `overview` (converter no boundary). **Não** computar saldo/atraso no front (lê o servidor — §4.2/§4.4).
- `placeholderData: keepPreviousData` no hook → nav de mês (se houver) não pisca; **não** `useSuspenseQuery`.

### Página de Reserva (design §5.2/§4.3/§15)
- A reserva é **única por condomínio** (design §15 "múltiplas reservas com UI = futuro"): `useReserves()` → pegar `data[0]` (se vazio, empty state PT "Reserva não configurada" + botão de criar gated `is_staff`, ou ocultar ações). **Não** montar seletor de reserva (YAGNI).
- Card de saldo: `StatCard label="Saldo da reserva" value={<AmountDisplay amount={Number(reserve.balance)} variant="positive"/>}`.
- Ledger: `DataTable` de `useReserveMovements({ reserve_id })` ordenado por data; coluna tipo = depósito/saque PT + ícone (`ArrowDownCircle`/`ArrowUpCircle`); coluna vínculo: `bill` setado → "Pagamento de conta #{bill}" / `bill=null` → "Transferência (caixa)". Empty state PT.
- Diálogos depósito/saque (gated `is_staff`): form `amount` (>0, Zod PT), `movement_date` (default `formatDateISO(new Date())`), `reference?`/`notes?` (só depósito). Submit → `useDepositReserve({ reserve_id, ... })`/`useWithdrawReserve(...)` (`mutateAsync`) → sucesso `toast.success` + fechar; erro → `handleError(error, 'Erro ao movimentar reserva')` (a guarda de saldo insuficiente vem do backend; **exibir** a mensagem PT do servidor). **Não** simular saldo no front (design §18).
- **Zero-sum (§4.3, informativo)**: o depósito é caixa→reserva (saldo total inalterado) — **não** exibir nada que sugira que a reserva "soma" ao patrimônio; o card de Reserva é só o saldo da reserva. (A invariante é backend; o front só exibe.)

### Página de Receita avulsa (`IncomeEntry`)
- `useCrudPage<IncomeEntry>({ entityName: 'receita', entityNamePlural: 'receitas', deleteMutation: useDeleteIncomeEntry(), … })` (espelha `buildings/page.tsx:47-55`).
- Filtros (espelha `financial/incomes/page.tsx`): `is_received` (Select sim/não/todos), `building_id` (Select de `useBuildings`), date range (`income_date`).
- Colunas: Descrição · Prédio (null → "Condomínio") · Data (`income_date` por split) · Valor (`formatCurrency`) · Recebida (✔/✘ + ícone) · Ações (Editar/Excluir, gated `is_staff`).
- Form modal: `description` (req), `amount` (>0), `income_date` (`YYYY-MM-DD`), `is_received` (Switch), `received_date` (condicional a `is_received` via `watch` — só exibe/exige quando recebida), `building_id` (nullable), `category_id` (nullable), `notes`. Create `useCreateIncomeEntry`, edit `useUpdateIncomeEntry`; sucesso `toast.success` + close; erro `handleError`.

### Página de Fechamento mensal (`CondoMonthClose`)
- `useCondoMonthCloses()` → `DataTable`: Competência (`reference_month` por split → `formatMonthYear`) · Status (open/closed + ícone `Lock`/`Unlock` + rótulo PT) · Resultado (`net_result`) · Caixa fim (`cash_balance_end`) · Reserva fim (`reserve_balance_end`) · Carry-forward (`carry_forward_out`) · Fechado em (`closed_at` por split). Valores via `formatCurrency`.
- Botões **Fechar mês** / **Reabrir mês** (gated `is_staff`) → `month-close-action-dialog` (modo `close|reopen`): form `{ year, month }` (Select de mês 1–12 + Input/Select de ano). Submit → `useCloseMonth({year,month})`/`useReopenMonth({year,month})` (`mutateAsync`) → sucesso `toast.success` ("Mês fechado."/"Mês reaberto.") + fechar; erro → `toast.error(getErrorMessage(error, 'Erro ao processar fechamento'))` (o backend retorna PT para gap cronológico/já-fechado/inexistente — §18). **Não** validar cronologia no front (autoridade backend).
- **Decisão (KISS)**: um **único** `month-close-action-dialog` parametrizado por `mode` (título/label/hook diferentes), em vez de dois diálogos quase iguais (DRY). Documentar no código.

### Gating `is_staff` (toda escrita)
- Esconder: criar/editar/excluir receita; depositar/sacar reserva; fechar/reabrir mês; criar reserva. Leitura (KPIs, ledger, listas, status) sempre visível. Fonte: `useAuthStore()` (`financial/settings/page.tsx:36-37`) ou `useCurrentUser()`. Backend `FinancialReadOnly` é a autoridade; o front só esconde (`.claude/rules/security.md`).

### Invalidação (DRY — no hook, não na UI)
- Toda mutation de Fase 4 invalida o próprio recurso + `finances.overview.all` (uma reserva/income/fechamento muda os KPIs). `useCloseMonth`/`useReopenMonth` também invalidam `finances.monthlyBalance.all`. `useDeposit/WithdrawReserve` invalidam `reserves`+`reserveMovements`+`overview`. As páginas **não** chamam `invalidateQueries` (está no hook — design §11).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md` + memória do projeto): mockar **APENAS fronteiras externas**. Testes de **hook** → a rede via **MSW** (`server.use`, usando `tests/mocks/data/finances.ts`). Testes de **componente/página** → os **hooks de dados desta sessão** + `useBuildings`/`useFinanceCategories`/`useAuthStore`, via **`vi.spyOn` no módulo** (`late-payments-alert.test.tsx:67-70`) **ou** MSW. **NUNCA** mockar componentes internos, TanStack Query, `apiClient`, ORM ou os schemas Zod. `renderWithProviders`/`createWrapper` (`test-utils.tsx:55-78`).

### 1. RED — escrever os testes primeiro (devem falhar por inexistência)
```bash
cd frontend
npx vitest run "components/ui/__tests__/stat-card.test.tsx" "components/ui/__tests__/amount-display.test.tsx" \
  "lib/api/hooks/__tests__/use-reserves.test.tsx" "lib/api/hooks/__tests__/use-income-entries.test.tsx" \
  "lib/api/hooks/__tests__/use-condo-month-closes.test.tsx" "lib/api/hooks/__tests__/use-finance-balance.test.tsx" \
  "app/(dashboard)/_components/finance-kpis" "app/(dashboard)/finances/reserve" \
  "app/(dashboard)/finances/income-entries" "app/(dashboard)/finances/month-close"
```

Cobrir, no mínimo:

**`stat-card.test.tsx`**
- [ ] renderiza `label` + `value`; ícone presente quando passado.
- [ ] `tone='positive'`/`'negative'`/`'warning'`/`'neutral'` aplica a classe de token correta (`text-success`/`text-destructive`/`text-warning`/`text-foreground`).
- [ ] **não** usa a prop `surface` (regressão: `Card` deste repo não a tem) — montagem não quebra.

**`amount-display.test.tsx`**
- [ ] `amount=1500` → `formatCurrency(1500)` ("R$ 1.500,00"); `amount=-50` exibe negativo com cor `text-destructive`.
- [ ] `variant='positive'`/`'negative'`/`'neutral'` fixa a cor independentemente do sinal; `showSign` prefixa `+`/`-`.

**`use-reserves.test.tsx`** (MSW)
- [ ] `useReserves()` busca + `reserveSchema.parse` converte `balance` string→number (`typeof === 'number'`).
- [ ] `useDepositReserve` POST `/finances/reserves/{id}/deposit/` body `{ amount, movement_date }` → invalida `reserves`+`reserveMovements`+`overview` (spy em `invalidateQueries`).
- [ ] `useWithdrawReserve` POST `/finances/reserves/{id}/withdraw/`; **§18/§4.3**: handler 400 (saldo insuficiente) → `isError` (o hook **não** trata; a UI exibe). O front **não** simula saldo.
- [ ] `useReserveMovements({ reserve_id })` repassa `reserve_id`/`kind` na query string; lista parseada (`amount` number, `kind` enum).

**`use-income-entries.test.tsx`** (MSW)
- [ ] `useIncomeEntries()` + `parse` (`amount` string→number); filtros `is_received`/`building_id`/date range na query string.
- [ ] `useCreate/Update/DeleteIncomeEntry` invalidam `incomeEntries`+`overview`.
- [ ] erro 500 → `isError`.

**`use-condo-month-closes.test.tsx`** (MSW)
- [ ] `useCondoMonthCloses()` + `parse` (`status` enum `open|closed`; derivados string→number).
- [ ] `useCloseMonth` POST `/finances/condo-month-closes/close/` `{year,month}` → invalida `condoMonthCloses`+`overview`+`monthlyBalance`.
- [ ] `useReopenMonth` POST `.../reopen/` `{year,month}` → invalida.
- [ ] **§18**: handler 400 (gap cronológico) → `isError` com a mensagem PT no payload (o front a exibe; **não** valida cronologia).

**`use-finance-balance.test.tsx`** (MSW)
- [ ] `useFinanceOverview(2026, 6)` busca o `overview`; dinheiro permanece **string** (não transformado); `wedge_ok` bool; `rent_overdue` presente.
- [ ] `building_id` repassado só quando definido (espelha `use-combined-calendar`/`use-rent-calendar`).
- [ ] **`placeholderData: keepPreviousData`**: ao trocar `month`, `data` mantém o mês anterior (`isPlaceholderData===true`) sem voltar a `undefined`.
- [ ] `useMonthlyBalance(2026)` → 12 entradas com `is_closed`; `useByCategory(2026, 6)` → breakdown com `name`/`color`/`amount`.
- [ ] erro 500 → `isError`.

**`finance-kpi-row.test.tsx`** (mock dos hooks + `useAuthStore` via `vi.spyOn`)
- [ ] loading → 5 skeletons; erro → Card de erro PT.
- [ ] com dados → 5 `StatCard` com rótulos Caixa/Reserva/Resultado do mês/Atrasados/Saldo total; valores formatados via `formatCurrency` (1 asserção por KPI lendo a **string** do overview).
- [ ] **§4.3**: `cash_balance` negativo → KPI Caixa em `text-destructive` (caixa pode ser negativo).
- [ ] **§4.4**: KPI Atrasados exibe `overdue_bills_total` e, separado, `rent_overdue.total_fee` (atraso de aluguel **não** somado ao de contas).
- [ ] **Saldo total** == valor do `total_balance` do servidor (o front **não** soma caixa+reserva localmente — lê o KPI).

**`reserve-deposit-dialog.test.tsx` / `reserve-withdraw-dialog.test.tsx`** (mock do hook de ação via `vi.spyOn`)
- [ ] submit válido → `useDepositReserve().mutateAsync`/`useWithdrawReserve().mutateAsync` chamado com `{ reserve_id, amount, movement_date }`; sucesso → `toast.success` + `onClose`.
- [ ] `amount<=0` ou vazio → Zod barra (mensagem PT), mutation **não** chamada.
- [ ] **saque**: mutation rejeita (saldo insuficiente, backend) → `handleError`/`toast.error`; o componente **não** simula/valida saldo da reserva (§18).
- [ ] o componente **não** chama `useQueryClient`/`invalidateQueries` (invalidação no hook).

**`reserve-page.test.tsx`** (mock dos hooks + `useAuthStore`)
- [ ] `is_staff=false` → botões Depositar/Sacar **ausentes**; saldo e ledger ainda renderizam (leitura).
- [ ] `is_staff=true` → botões presentes; abrir Depositar mostra o diálogo.
- [ ] ledger: tipo PT depósito/saque por linha; `bill` setado → "Pagamento de conta", `bill=null` → "Transferência (caixa)"; datas por split; valores `formatCurrency`.
- [ ] empty state PT quando sem movimentos.

**`income-entries-page.test.tsx`** (mock dos hooks + `useAuthStore`)
- [ ] `is_staff=false` → "Nova Receita"/Editar/Excluir ausentes; tabela renderiza.
- [ ] `is_staff=true` → ações presentes.
- [ ] coluna Data por **split**; Valor `formatCurrency`; prédio null → "Condomínio"; Recebida ✔/✘ com ícone.
- [ ] filtro `is_received`/`building_id` repassado ao hook (verificar args do spy).

**`income-entry-form-modal.test.tsx`**
- [ ] create: preencher → `useCreateIncomeEntry().mutate(e)` com `{ description, amount, income_date, is_received, building_id?, category_id?, notes? }`.
- [ ] `is_received=true` (via `watch`) → mostra/exige `received_date`; `false` → esconde.
- [ ] sem descrição / `amount<=0` → Zod PT, `mutate` **não** chamado.
- [ ] edit: campos pré-preenchidos; submit → `useUpdateIncomeEntry`.

**`month-close-page.test.tsx`** (mock dos hooks + `useAuthStore`)
- [ ] lista com status open/closed (ícone + rótulo PT); colunas `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out` via `formatCurrency`; competência por split → `formatMonthYear`.
- [ ] `is_staff=false` → "Fechar mês"/"Reabrir mês" ausentes; lista renderiza.
- [ ] `is_staff=true` → botões presentes; abrir "Fechar mês" mostra o diálogo (modo close).

**`month-close-action-dialog.test.tsx`**
- [ ] `mode='close'` → submit `{year,month}` chama `useCloseMonth().mutateAsync`; título/label PT de fechamento.
- [ ] `mode='reopen'` → chama `useReopenMonth().mutateAsync`; título/label de reabertura.
- [ ] mutation rejeita (gap cronológico / inexistente, backend) → `toast.error` com a mensagem PT do servidor; o front **não** valida cronologia.
- [ ] o componente **não** invalida queries (hook faz).

> Rodar (devem **falhar**):
> ```bash
> cd frontend
> npx vitest run "components/ui/__tests__/stat-card.test.tsx" "components/ui/__tests__/amount-display.test.tsx" "lib/api/hooks/__tests__/use-reserves.test.tsx" "lib/api/hooks/__tests__/use-income-entries.test.tsx" "lib/api/hooks/__tests__/use-condo-month-closes.test.tsx" "lib/api/hooks/__tests__/use-finance-balance.test.tsx" "app/(dashboard)/_components/finance-kpis" "app/(dashboard)/finances/reserve" "app/(dashboard)/finances/income-entries" "app/(dashboard)/finances/month-close"
> ```

### 2. GREEN — implementar (mínimo para passar)
1. Primitivos `StatCard`/`AmountDisplay` em `components/ui/` (portados/adaptados — sem `surface`, `formatCurrency` daqui).
2. 4 schemas Zod em `lib/schemas/finances/` (reusar `moneyToNumber` da S39; FK dual; enums casando 1:1 com o backend).
3. Estender `query-keys.ts` (grupo `finances` ganha `reserves`/`reserveMovements`/`incomeEntries`/`condoMonthCloses`/`overview`/`monthlyBalance`/`byCategory`).
4. 5 hooks (`use-reserves`/`use-reserve-movements`/`use-income-entries`/`use-condo-month-closes`/`use-finance-balance`): CRUD espelha `use-expenses.ts`; dashboard espelha `use-combined-calendar`/`use-daily-control` (`placeholderData`). Tipos de dashboard hand-written (string); CRUD via `z.infer`.
5. `FinanceKpiRow` + montagem em `app/(dashboard)/page.tsx` acima do calendário (S40).
6. 3 páginas (`finances/reserve`, `finances/income-entries`, `finances/month-close`) + seus componentes (colunas/modais/diálogos).
7. `ROUTES` (3 novas) + 3 itens no grupo "Condomínio" do `sidebar.tsx`; estender `tests/mocks/data/finances.ts` + `financeHandlers`.
8. Imports diretos da fonte (S39/S45 + primitivos); **sem** redefinir tipos, **sem** re-export.

Rodar até verde (mesmos paths do RED).

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `StatCard`/`AmountDisplay` são a **fonte única** de KPI/valor — a `FinanceKpiRow` e os cards de saldo das páginas reusam (não repetir `Card` 5×). Helper de mapeamento `tone`/`variant`→token num único lugar.
- Um **único** `month-close-action-dialog` parametrizado por `mode` (DRY — não dois diálogos).
- `useDepositReserve`/`useWithdrawReserve` compartilham o mesmo padrão de invalidação (helper interno ou repetição mínima clara). Tipo `ReserveMovementKind` em uma fonte (schema).
- Datas por split num helper local **só se** repetir (preferir `formatDate`/`formatMonthYear` existentes); **não** recriar formatter.
- Sub-componentes pequenos de responsabilidade única; sem código especulativo (YAGNI); sem comentários supérfluos.

### 4. VERIFY — gate frontend (escopo desta sessão)
```bash
cd frontend
npx vitest run "components/ui/__tests__/stat-card.test.tsx" "components/ui/__tests__/amount-display.test.tsx" "lib/api/hooks/__tests__/use-reserves.test.tsx" "lib/api/hooks/__tests__/use-income-entries.test.tsx" "lib/api/hooks/__tests__/use-condo-month-closes.test.tsx" "lib/api/hooks/__tests__/use-finance-balance.test.tsx" "app/(dashboard)/_components/finance-kpis" "app/(dashboard)/finances/reserve" "app/(dashboard)/finances/income-entries" "app/(dashboard)/finances/month-close"
npx tsc --noEmit
npx eslint "components/ui/stat-card.tsx" "components/ui/amount-display.tsx" "lib/schemas/finances" "lib/api/hooks/use-reserves.ts" "lib/api/hooks/use-reserve-movements.ts" "lib/api/hooks/use-income-entries.ts" "lib/api/hooks/use-condo-month-closes.ts" "lib/api/hooks/use-finance-balance.ts" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "app/(dashboard)/page.tsx" "app/(dashboard)/_components/finance-kpis" "app/(dashboard)/finances/reserve" "app/(dashboard)/finances/income-entries" "app/(dashboard)/finances/month-close" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts"
```
Zero erros e zero avisos em todos.

---

## Constraints

- **Camada de UI + data layer Fase 4 só** (`.claude/rules/architecture.md` Frontend Layers): hooks = TanStack Query; schemas = Zod; **só** containers/modais que disparam mutations chamam hooks. **Nenhum** componente chama `apiClient`/axios. **Não** criar hooks/schemas de Fase 2/3 (já existem) nem de Fase 5/6.
- **TanStack Query v5**: `useQuery` + `placeholderData: keepPreviousData` no `useFinanceOverview` (e demais reads de dashboard); mutations invalidam no settle/success **dentro do hook** (DRY — a UI não duplica). **NÃO** `useSuspenseQuery` (descarta placeholderData — design §10).
- **Decimal**: CRUD = `number` (schema transform via `moneyToNumber` da S39); dashboard = `string` (converter só na exibição via `formatCurrency`/`AmountDisplay`). O front **nunca** recalcula KPIs/saldo do servidor (§4.2/§4.4); Saldo total vem de `total_balance`, não de caixa+reserva somados no front.
- **Reserva/fechamento = guarda no backend** (design §4.3/§18): o front **não** simula saldo da reserva nem valida cronologia do fechamento — envia a ação e **exibe** o erro PT do servidor (`handleError`/`getErrorMessage`/`toast.error`). Reserva é **única** (sem seletor — design §15).
- **Datas puras** `YYYY-MM-DD`/`YYYY-MM-01` por **split** (`late-payments-alert.tsx:17-21`), **nunca** `new Date(iso)` (bug de TZ). `formatMonthYear` → "Junho de 2026" (com " de ") — asserir exato.
- **`is_staff` gating**: esconder toda UI de escrita (depositar/sacar/criar income/editar/excluir/fechar/reabrir/criar reserva) quando `!user.is_staff`. Backend `FinancialReadOnly` é a autoridade (`.claude/rules/security.md`).
- **Status nunca só por cor** — sempre rótulo + ícone (acessibilidade): open/closed, recebida/não, depósito/saque, caixa negativo. Dark mode via tokens semânticos — **não** adicionar toggle de tema.
- **Primitivos adaptados ao repo**: `StatCard`/`AmountDisplay` usam o `Card` deste repo (**sem** `surface`) e `formatCurrency`/tokens daqui — o `controle-financeiro` é só design reference. **Não** copiar `formatCurrencyValue`/`text-income`/`text-expense` (tokens de lá).
- **`as`/`!` proibidos em produção** (regra do projeto + memória): componentes/hooks/schemas sem `as`/non-null — corrigir o tipo na raiz (`import type`, `??`, null guards, `noUncheckedIndexedAccess`).
- **CARVE-OUT (somente fixtures de teste)**: nos `*.test.tsx`, ao construir o retorno de um hook de query/mutation do TanStack (shape inviável sem assertion), É PERMITIDO `as <Result>` / `as unknown as <Mutation>` **restrito** aos helpers de fixture (`makeQueryResult`/`idleMutation`), **exatamente** como `late-payments-alert.test.tsx:35,55`. Em qualquer outro lugar (testes/produção), `as`/`!` proibidos.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o código. TypeScript strict + `noUncheckedIndexedAccess`.
- **Sem `from __future__`/`TYPE_CHECKING`** (irrelevante no FE) e **sem re-export / barrel files / shims**: importar tipos/hooks **direto da fonte** (`@/lib/api/hooks/*`, `@/lib/schemas/finances/*`, `@/components/ui/*`). Reusar `moneyToNumber` (S39) por import direto.
- **Sem deps novas** — Shadcn/Radix, lucide, sonner, RHF, Zod, date-fns, TanStack já no repo. **Não** instalar Recharts (gráficos = Fase 5; donut por categoria = não-blocking/tabela aqui).
- **Escopo de fases**: **sem** projeção/simulação (Fase 5 — S47/S48), **sem** distribuição/owner (Fase 6 — S49/S50), **sem** gráficos blocking. `monthly_balance`/`by_category` podem virar **tabela** read-only (sem chart).
- **Coexistência**: **não** alterar/remover `finance-calendar/*`/`finances/bills/*` (S40), `rent-calendar/*`, `late-payments-alert.tsx`, nem o módulo legado (`balance-cards.tsx`/`expenses`/`daily`/`use-financial-dashboard`) — design §1/§11/§15. Os legados são só exemplares.
- **SOLID/DRY/KISS/YAGNI**: primitivos extraídos uma vez; diálogo de fechamento único; componentes pequenos; sem código especulativo.
- **Não rodar a suíte completa** — só os arquivos desta sessão (xdist/Redis pré-existentes; memória do projeto).

---

## Critérios de Aceite (binários)

- [ ] `components/ui/stat-card.tsx` e `components/ui/amount-display.tsx` criados (portados/adaptados ao `Card`/`formatCurrency`/tokens deste repo, **sem** prop `surface`); testes verdes.
- [ ] 4 schemas em `frontend/lib/schemas/finances/` (`reserve`, `reserve-movement`, `income-entry`, `condo-month-close`) com Decimal string→Number no boundary (reusando `moneyToNumber` da S39), FK dual nested-read/`_id`-write, enums casando 1:1 com os `TextChoices` do backend, `type` inferido exportado; derivados do `CondoMonthClose` read-only.
- [ ] 5 hooks criados: `use-reserves` (incl. `useDepositReserve`/`useWithdrawReserve`), `use-reserve-movements`, `use-income-entries` (CRUD), `use-condo-month-closes` (incl. `useCloseMonth`/`useReopenMonth`), `use-finance-balance` (`useFinanceOverview` com `placeholderData: keepPreviousData` + `useMonthlyBalance` + `useByCategory`). CRUD espelha `use-expenses`; dashboard espelha `use-combined-calendar`/`use-daily-control`; dashboard mantém Decimal string.
- [ ] `query-keys.ts` estende o grupo `finances` com `reserves`/`reserveMovements`/`incomeEntries`/`condoMonthCloses`/`overview`/`monthlyBalance`/`byCategory` (forma `all`/`list`/`detail`/`month`; `buildingId ?? null`); sub-grupos da S39 intactos.
- [ ] `FinanceKpiRow` em `frontend/app/(dashboard)/_components/finance-kpis/`: 5 `StatCard` (Caixa/Reserva/Resultado do mês/Atrasados/Saldo total) lendo o `overview` (string→formatado); caixa negativo em `text-destructive` (§4.3); Atrasados separa contas de aluguel (`rent_overdue.total_fee`, §4.4); Saldo total = `total_balance` do servidor (não somado no front); skeleton + erro PT.
- [ ] `<FinanceKpiRow />` montado em `app/(dashboard)/page.tsx` **acima** do `<CombinedCalendarSection />` (S40); calendário **não** removido (decisão no handoff).
- [ ] Página de Reserva (`finances/reserve/`): saldo (`StatCard`/`AmountDisplay`) + ledger (`useReserveMovements`, tipo PT + vínculo conta vs transferência) + diálogos depósito/saque (gated `is_staff`); guarda de saldo é backend (front exibe o erro, não simula).
- [ ] Página de Receita avulsa (`finances/income-entries/`): `useCrudPage<IncomeEntry>` + `DataTable` + filtros + modal RHF/Zod (`received_date` condicional a `is_received` via `watch`); gated `is_staff`.
- [ ] Página de Fechamento (`finances/month-close/`): lista open/closed + colunas de derivados (`formatCurrency`) + diálogo único `close|reopen` (`{year,month}`); erro cronológico/já-fechado/inexistente exibido via `toast.error` (PT do backend); front não valida cronologia.
- [ ] Toda UI de escrita **gated por `is_staff`**; leitura sempre visível.
- [ ] Datas por **split** (sem `new Date(iso)`); moeda via `formatCurrency`/`AmountDisplay`; competência via `formatMonthYear` ("Junho de 2026"); prédio null → "Condomínio"; status sempre rótulo + ícone.
- [ ] `ROUTES.FINANCES_RESERVE`/`FINANCES_INCOME`/`FINANCES_MONTH_CLOSE` em `constants.ts`; 3 itens no grupo "Condomínio" do `sidebar.tsx` (S40); rotas/menu legados e da S40 intactos.
- [ ] `tests/mocks/data/finances.ts` e `financeHandlers` **estendidos** (factories + rotas Fase 4); existentes intactos.
- [ ] Componentes (exceto containers/modais com mutation) são **puros**; nenhum chama `apiClient`/axios; nenhuma página duplica `invalidateQueries`.
- [ ] Sem projeção/simulação/distribuição/owner; sem gráficos blocking; sem Recharts; sem hooks/schemas de Fase 2/3 recriados; S40/legado intactos.
- [ ] `npx vitest run` (os arquivos desta sessão) 100% verde.
- [ ] `npx tsc --noEmit` limpo; `npx eslint` (todos os arquivos tocados) zero erros/zero avisos — **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção (único `as` = carve-out de fixture de teste).
- [ ] Sem re-exports/barrel; sem dependência nova; `moneyToNumber` (S39) reusado por import direto.

---

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão — colar saída como evidência):
   ```bash
   cd frontend
   npx vitest run "components/ui/__tests__/stat-card.test.tsx" "components/ui/__tests__/amount-display.test.tsx" "lib/api/hooks/__tests__/use-reserves.test.tsx" "lib/api/hooks/__tests__/use-income-entries.test.tsx" "lib/api/hooks/__tests__/use-condo-month-closes.test.tsx" "lib/api/hooks/__tests__/use-finance-balance.test.tsx" "app/(dashboard)/_components/finance-kpis" "app/(dashboard)/finances/reserve" "app/(dashboard)/finances/income-entries" "app/(dashboard)/finances/month-close"
   npx tsc --noEmit
   npx eslint "components/ui/stat-card.tsx" "components/ui/amount-display.tsx" "lib/schemas/finances" "lib/api/hooks/use-reserves.ts" "lib/api/hooks/use-reserve-movements.ts" "lib/api/hooks/use-income-entries.ts" "lib/api/hooks/use-condo-month-closes.ts" "lib/api/hooks/use-finance-balance.ts" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "app/(dashboard)/page.tsx" "app/(dashboard)/_components/finance-kpis" "app/(dashboard)/finances/reserve" "app/(dashboard)/finances/income-entries" "app/(dashboard)/finances/month-close" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts"
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (**NÃO** editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 46 (status **concluída**) na tabela da feature Condomínio Finance (fecha a Fase 4 — frontend).
   - **Arquivos Criados**: `components/ui/{stat-card,amount-display}.tsx` (+2 testes); 4 schemas em `lib/schemas/finances/`; 5 hooks `use-*.ts` (+4 testes); `_components/finance-kpis/finance-kpi-row.tsx` (+teste); 3 páginas `finances/{reserve,income-entries,month-close}/page.tsx` + componentes + testes.
   - **Arquivos Modificados**: `query-keys.ts` (grupo `finances` estendido), `constants.ts` (3 rotas), `sidebar.tsx` (grupo "Condomínio"), `app/(dashboard)/page.tsx` (montagem `<FinanceKpiRow />`), `tests/mocks/data/finances.ts` + `handlers.ts` (Fase 4).
   - **Documentar decisões**: posição do `<FinanceKpiRow />` (acima do calendário, calendário mantido); reserva única (sem seletor); diálogo único `close|reopen`; `monthly_balance`/`by_category` como tabela (gráfico/donut = Fase 5 / não-blocking); guarda de reserva e cronologia do fechamento = backend (front exibe erro).
   - **Anotar divergências** se algum campo do serializer real da S45 diferir deste prompt (qual, como o schema foi ajustado).
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`):
   ```
   feat(finances): add balance KPIs + reserve/income/month-close frontend (phase 4 frontend)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **47 — Backend Fase 5 (`CondoProjectionService` + `CondoSimulationService` + `cash-flow/{projection,simulate}`)** — consome `CondoBalanceService.result_of_month`/baseline (S45). A S48 (FE Fase 5) **adiciona** a tela de projeção/simulação (tabela acumulada + `ComposedChart` + simulador) **reusando** `StatCard`/`AmountDisplay`/query-keys/`useFinanceOverview` desta sessão — **não** recria os KPIs nem a página de Reserva/Receita/Fechamento.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim nas Fases 5/6)

- **Primitivos** (`@/components/ui/stat-card`, `@/components/ui/amount-display`): `StatCard` (props `label`/`value`/`icon?`/`tone?`, sem `surface`) e `AmountDisplay` (props `amount`/`showSign?`/`size?`/`variant?`, usa `formatCurrency`). **Fonte única** de KPI/valor — a Fase 5 (projeção/simulação) e a Fase 6 (distribuição por dono) **reusam** (não recriam cards).
- **Schemas/tipos Fase 4** (`@/lib/schemas/finances/*`): `Reserve`, `ReserveMovement` (+ `ReserveMovementKind`), `IncomeEntry`, `CondoMonthClose` (+ `MonthCloseStatus`). Dinheiro CRUD = `number`; dashboard = `string`.
- **Hooks Fase 4** (`@/lib/api/hooks/*`): `useReserves`/`useReserve`/`useCreate|Update|DeleteReserve`/`useDepositReserve`/`useWithdrawReserve`; `useReserveMovements`; `useIncomeEntries`/`useIncomeEntry`/`useCreate|Update|DeleteIncomeEntry`; `useCondoMonthCloses`/`useCloseMonth`/`useReopenMonth`; `useFinanceOverview(year,month,buildingId?)` (placeholderData) / `useMonthlyBalance(year)` / `useByCategory(year,month,buildingId?)`. Invalidação no hook — a UI nunca duplica.
- **query-keys**: grupo `queryKeys.finances.*` estendido (`reserves`/`reserveMovements`/`incomeEntries`/`condoMonthCloses`/`overview`/`monthlyBalance`/`byCategory`) — as Fases 5/6 registram suas keys **nesse** grupo (não inline). A Fase 5 adiciona `projection`/`simulation`.
- **Rotas/menu**: `ROUTES.FINANCES_RESERVE`/`FINANCES_INCOME`/`FINANCES_MONTH_CLOSE` no grupo de menu "Condomínio" (criado pela S40) — as próximas telas registram nesse grupo.
- **`FinanceKpiRow`** (`@/app/(dashboard)/_components/finance-kpis/finance-kpi-row.tsx`): montada no dashboard **acima** do calendário (S40). A Fase 6 (distribuição) **adiciona** cards "por proprietário" + seção de externos **ao lado/abaixo** — **não** recria os 5 KPIs.
- **Guardas backend**: a guarda de saldo da reserva (`withdraw`/`funded_from=reserve`) e a cronologia do fechamento (`close`/`reopen`) **são do backend** (S45) — o front exibe o erro PT, **não** simula. As Fases seguintes seguem a mesma regra.
