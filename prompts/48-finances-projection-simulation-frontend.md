# Sessão 48 — Frontend: projeção 12 meses (tabela acumulada + ComposedChart) + simulador

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46 → **47 → 48** → 49 → 50 (esta é a 48 — **Fase 5 FRONTEND**)
> Esta sessão entrega a **UI da projeção de 12 meses** do condomínio: a **tabela** (load-bearing — coluna de saldo acumulado + badge **Real/Projetado** por linha) é o artefato verificado no gate; o **`ComposedChart`** (Recharts, bar receita/despesa + linha acumulada) é **não-blocking no gate** (design §10/§12); e o **simulador what-if** (deltas efêmeros sobre a projeção base). Cria os **hooks + tipos** (`useCondoProjection`/`useCondoSimulation`), o grupo de query-keys, MSW data/handlers, e os **testes** dos hooks + da tabela. **Consome** o backend da Sessão 47 (`CondoProjectionService`/`CondoSimulationService` + endpoints `/api/finances/finance-cash-flow/{projection,simulate}`). **Sem distribuição por proprietário** (Fase 6 — Sessões 49/50).

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.5 receita filtrada, §4.7 fold/carry-forward ancorado, §8 `CondoProjectionService`/`CondoSimulationService`, §9 API `finance-cash-flow/{projection,simulate}`, §10 Frontend/Dashboard — tela 5, §11 cache `finance-projection`/`finance-cash-flow`, §12 gate por fase, §18 edge-cases das fases 5/4)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md` (confirmar **S47 concluída** — esta sessão consome `CondoProjectionService`/`CondoSimulationService` + endpoints; confirmar **S39/S46 concluídas** — esta sessão consome o grupo `queryKeys.finances.*`, `extractResults`, `financeHandlers`, KPIs de fechamento/saldo da S46). **Se S47 não estiver concluída, PARE** (DEPENDENCY ORDER 47→48).
- **Contrato de dados do backend (verbatim, NÃO derivar)**: a seção "Contratos cross-session definidos por esta sessão" no fim de `@prompts/47-finances-projection-simulation-backend.md` (shapes reais de `projection`/`simulate`). **Se algum campo divergir deste prompt, o export real da S47 prevalece** — ajustar o tipo, anotar a divergência no handoff; nunca inventar campo.
- **Camada de dados de `finances` já existente (consumir, NÃO recriar)**: `@prompts/39-finances-frontend-data-layer.md` (seção "Contratos cross-session") — grupo `queryKeys.finances.*`, `tests/mocks/data/finances.ts`, `financeHandlers`, separação **Decimal-string no dashboard × Number-no-boundary no CRUD**.
- **Regras do projeto**: `frontend/CLAUDE.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`.

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Hook de projeção read-only (`useQuery` + `params.months`)** | `frontend/lib/api/hooks/use-cash-flow.ts:46-54` (`CashFlowProjectionMonth` interface) + `:129-154` (`ProjectionOptions` + `useCashFlowProjection` `useQuery`+`params`+`staleTime`) | **Exemplar canônico** do `useCondoProjection`. Mesma forma: tipo hand-written de dashboard (Decimal pode vir string), `useQuery` com `params:{months}`, `staleTime`. **Mas**: usar `placeholderData: keepPreviousData` (§10) e **não** `refetchInterval` (projeção não precisa de poll agressivo — KISS). |
| **Hook de simulação (`useMutation` POST cenários→resultado)** | `frontend/lib/api/hooks/use-simulation.ts` (`useSimulation` `useMutation` POST `/cash-flow/simulate/` body=cenários → `{ base, simulated, comparison }`) | **Espelhar** o `useCondoSimulation` — `useMutation` que recebe deltas/cenários e devolve a projeção simulada. Tipos `SimulationScenario`/`SimulationResult`/`ComparisonMonth` são a forma a imitar (`finances` terá os seus). |
| **Tabela comparativa (TableFooter de totais, badge por linha, cor por sinal)** | `frontend/app/(dashboard)/financial/simulator/_components/comparison-table.tsx:39-117` (`reduce` de totais :40-42; `MONTH_NAMES`+`shortYear` :16-29,64-65; `<TableFooter>` total :94-112; cor `delta>=0 ? text-success : text-destructive` :84-89) | **Exemplar canônico** da **tabela de projeção** desta sessão (coluna acumulada + total no rodapé + formatação mês/ano). Acrescentar a coluna/badge **Real/Projetado** por linha (`is_actual`). |
| **ComposedChart bar(receita/despesa) + line(acumulado) + tooltip custom + badge projetado** | `frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx:24-48` (`toChartData` + `formatMonthLabel` + `is_projected`) + `:50-88` (`CustomTooltip` com "(projetado)") + `:253-299` (`ResponsiveContainer`/`ComposedChart`/`Bar`×2/`Line`/dual `YAxis`) | **Exemplar canônico** do **gráfico** (não-blocking no gate). Bar `income`/`expenses` (yAxis left, k-formatter) + Line `cumulative` (yAxis right) + tooltip marcando "(projetado)". O `is_projected`/`is_actual` controla badge/estilo. |
| **Gráfico comparativo base × simulado (linhas + Area de delta)** | `frontend/app/(dashboard)/financial/simulator/_components/comparison-chart.tsx:44-62` (`buildChartData` base+simulated por índice, `delta`) + `:114-171` (`Line` base sólida + `Line` simulada `strokeDasharray` + `Area` delta) | **Exemplar canônico** do gráfico do **simulador** (base sólida × simulada tracejada + área de delta). |
| **Página simulador (sheet de cenário + lista + chart full-width + grid impacto/tabela)** | `frontend/app/(dashboard)/financial/simulator/page.tsx:25-160` (estado `scenarios`/`simulationResult` :26-28; `useRef(simulation.mutate)` p/ estabilizar :32-33; `runSimulation` :35-50; loading/erro guards :66-84; layout `grid lg:grid-cols-4` :97-150; `<ScenarioBuilder>` sheet :153-157) | **Exemplar canônico** da **página de projeção+simulador** desta sessão. Reusar o padrão `useRef(mutate)` (decisão arquitetural #13 do SESSION_STATE — evita `eslint-disable` em deps). |
| **Hook calendário read-only + `placeholderData` (S39, já em finances)** | `frontend/lib/api/hooks/use-combined-calendar.ts` (criado na S39 — `useCombinedCalendar` com `placeholderData: keepPreviousData`, `staleTime` 30s, `building_id` condicional) | **Forma** do `useCondoProjection` quanto a `placeholderData` + `params` condicionais; **mesma família de hooks** de `finances` (consistência). |
| **CRUD/hook simples com `extractResults` + invalidate** | `frontend/lib/api/hooks/use-expenses.ts:1-141` (filtros limpos `Object.fromEntries(...v!==undefined)` :19-21; `useQuery` :23-33; mutation `invalidateQueries` :47-106) | Forma do `queryFn`/limpeza de params (a projeção do condo é uma lista achatada de meses — usar `extractResults` **só** se o endpoint paginar; se vier array cru, tipar `T[]` direto, como `useCashFlowProjection`). |
| **query-keys central — grupo `finances` + sub-grupo `cashFlow.projection(params)` legado** | `frontend/lib/api/query-keys.ts:98-106` (`cashFlow.projection(params)`) + `:131-135` (`rentCalendar`) + grupo `finances` adicionado na **S39** (`billingAccounts`/`bills`/`payments`/`combinedCalendar`/`overdueBills`) | **Espelhar** para adicionar os sub-grupos `finances.projection` + `finances.simulation` (estabilizar com `params`/`null`, `as const`). |
| **Helpers de paginação DRF** | `frontend/lib/types/api.ts:4-30` (`PaginatedResponse<T>`, `isPaginatedResponse`, `extractResults`) | Reusar `extractResults` **apenas** se o backend da S47 paginar a projeção (confirmar no handoff da S47). |
| **apiClient (Axios; desembrulha `results`; nunca axios cru)** | `frontend/lib/api/client.ts:7-14`,`:19-38` | **Toda** chamada HTTP via `apiClient` (`/finances/finance-cash-flow/...`; o `baseURL` já é `/api`). |
| **Formatters TZ-safe (moeda + mês/ano)** | `frontend/lib/utils/formatters.ts:5-15` (`formatCurrency`) + `:89-93` (`formatMonthYear`) + `:104` (`MONTH_ABBR`) | **Reusar** `formatCurrency` e `MONTH_ABBR` (não redefinir `MONTH_NAMES` inline como os componentes legados — DRY: importar `MONTH_ABBR`). |
| **`is_staff` gating de UI** | `frontend/app/(dashboard)/financial/expenses/page.tsx:10,24-25` (`useAuthStore` → `const isAdmin = user?.is_staff ?? false`) | Gate dos controles **de escrita** do simulador (se houver — what-if é só leitura efêmera; mas seguir o padrão se algum controle persistir/exportar). |
| **MSW handlers (`API_BASE`, reset, array final) + finances data (S39)** | `frontend/tests/mocks/handlers.ts:30` (`API_BASE`), `:43-52` (`resetMockData`), `financeHandlers` (S39) + `frontend/tests/mocks/data/finances.ts` (S39 factories) | Adicionar `createMockCondoProjection`/`createMockCondoSimulation` em `data/finances.ts` (**estender**, não recriar o arquivo) e novos handlers em `financeHandlers`. |
| **test-utils (wrapper/queryClient; `gcTime:0`)** | `frontend/tests/test-utils.tsx:15-28` (`createTestQueryClient`), `:69-74` (`createWrapper`) | Reusar **verbatim** nos testes de hook; `renderWithProviders` :55-64 nos testes de componente. |

### Contratos do backend que esta sessão CONSOME (S47 — verbatim, NÃO derivar)

> **Pré-requisito**: S47 expõe `GET /api/finances/finance-cash-flow/projection/?months=12` e `POST /api/finances/finance-cash-flow/simulate/` (bare `ViewSet` + `IsAuthenticated`, design §9). Decimais como **string** (como os demais endpoints de dashboard — manter string nos tipos, converter para `Number` **só** no boundary de exibição/redução, espelhando `use-cash-flow.ts` e `use-rent-calendar.ts`). Confirmar os shapes reais no `SESSION_STATE.md` da S47 antes de fixar os tipos.

- **`projection` (read)** → lista achatada de meses (12 por padrão), cada item (espelha `CashFlowProjectionMonth` com nomes de `finances`): `year`, `month`, `income_total` (**string Decimal** — receita filtrada por collectibility, §4.5), `expenses_total` (**string Decimal**), `net` (**string Decimal** — resultado de competência do mês), `cumulative_cash` (**string Decimal** — fold ancorado no último `CondoMonthClose`, §4.7), `is_actual` (bool — `mês < atual` = Real; futuro = Projetado, §8). *(Se a S47 nomear `is_actual` como `is_projected` invertido, **usar o nome real** e adaptar o badge — anotar no handoff.)*
- **`simulate` (write/efêmero)** → body `{ months?: number, deltas: SimulationDelta[] }` (deltas em memória, **sem persistência** — `CondoSimulationService`, §8); resposta `{ base: CondoProjectionMonth[], simulated: CondoProjectionMonth[], comparison: { month_by_month: CondoComparisonMonth[], totals?: {...} } }`. Cada `CondoComparisonMonth`: `year`, `month`, `base_net`/`base_cumulative`/`simulated_net`/`simulated_cumulative`/`delta` (**string Decimal**). *(Confirmar o formato exato do `delta`/totais com o handoff da S47; se a S47 reusar a forma do legado `ComparisonMonth`, espelhá-la com os nomes de `finances`.)*
- **Tipo de delta de simulação** (espelha os cenários do legado, §8): cada `SimulationDelta` = `{ type: <CondoSimulationType>, ...params }` (ex.: gasto extra mensal, nova parcela mensal, ocupação total). **Os valores de `type` casam 1:1** com os do `CondoSimulationService` da S47 — **importar/derivar do handoff**, não inventar.

> **NOTA crítica de URL**: endpoints de `finances` são **namespaced** sob `/api/finances/...` (design §9). Os hooks chamam `apiClient.get('/finances/finance-cash-flow/projection/', …)` e `apiClient.post('/finances/finance-cash-flow/simulate/', …)`. Nos testes MSW, `API_BASE = 'http://localhost:8008/api'` + caminho `/finances/finance-cash-flow/...`.

---

## Escopo

### Arquivos a criar
- `frontend/lib/api/hooks/use-condo-projection.ts` — tipos hand-written de dashboard (`CondoProjectionMonth`, `CondoSimulationDelta`, `CondoSimulationResult`, `CondoComparisonMonth`, `CondoSimulationType`) + `useCondoProjection(months?)` (`useQuery`, `placeholderData: keepPreviousData`, `staleTime`) + `useCondoSimulation()` (`useMutation` POST `simulate`). Decimais ficam **string** no tipo (converter na UI). **Sem re-export.**
- `frontend/app/(dashboard)/finances/projection/page.tsx` — página da projeção+simulador (`'use client'`): consome `useCondoProjection` + `useCondoSimulation`; loading/erro guards; layout (tabela load-bearing no topo, gráfico abaixo, painel de cenários lateral). Único arquivo que consome os hooks (componentes recebem props).
- `frontend/app/(dashboard)/finances/projection/_components/projection-table.tsx` — **tabela load-bearing**: colunas Mês / Receita / Despesa / Resultado / **Acumulado** + **badge Real/Projetado** por linha (de `is_actual`); `TableFooter` com totais; cor por sinal (espelha `comparison-table.tsx`). Componente puro (props), `import MONTH_ABBR`/`formatCurrency`.
- `frontend/app/(dashboard)/finances/projection/_components/projection-chart.tsx` — **ComposedChart não-blocking** (Bar receita+despesa eixo esq. + Line acumulado eixo dir. + `CustomTooltip` marcando "(projetado)"). Componente puro (props).
- `frontend/app/(dashboard)/finances/projection/_components/simulation-panel.tsx` — painel what-if: builder de deltas (inputs efêmeros — gasto extra/mês, parcela nova/mês, etc., conforme os `type` da S47), lista de cenários ativos, dispara `useCondoSimulation`. Apresentacional + estado local; chama `onSimulate(deltas)` recebido da page (a page detém o hook — padrão `simulator/page.tsx`).
- `frontend/app/(dashboard)/finances/projection/_components/simulation-comparison.tsx` — gráfico base × simulado (linhas + Area de delta) + (opcional) sub-tabela de delta mês a mês (espelha `comparison-chart.tsx`/`comparison-table.tsx`). **Não-blocking** (gráfico); a sub-tabela de delta, se incluída, é load-bearing.
- `frontend/lib/api/hooks/__tests__/use-condo-projection.test.tsx` — testes de hook (MSW): fetch/shape `projection`, `months` na querystring, `placeholderData` entre `months` diferentes, `is_actual` presente; `useCondoSimulation` POST com `deltas` no body, resposta `{base,simulated,comparison}`, erro 500.
- `frontend/app/(dashboard)/finances/projection/_components/__tests__/projection-table.test.tsx` — testes da **tabela** (render real, sem mock de internals): linhas Real/Projetado com badge correto a partir de `is_actual`; coluna **Acumulado** exibe `cumulative_cash`; totais no rodapé; cor por sinal do resultado; off-by-cent — total = soma dos meses (quantização no boundary).

### Arquivos a modificar
- `frontend/lib/api/query-keys.ts` — adicionar **sub-grupos** `projection` e `simulation` **dentro** do grupo `finances` já existente (S39): `finances.projection.list(months)` (`months ?? 12`) e `finances.simulation.all` (a simulação é `useMutation`, mas registrar `all` para consistência/invalidação se necessário). **Não** alterar outros grupos; manter `as const`.
- `frontend/tests/mocks/data/finances.ts` — **estender** (S39) com `createMockCondoProjection(overrides?)` (12 meses, `is_actual` mistos) + `createMockCondoSimulation(overrides?)` (`{base,simulated,comparison}`). Importar os tipos de `use-condo-projection`. **Fora** do barrel `data/index.ts`.
- `frontend/tests/mocks/handlers.ts` — adicionar a `financeHandlers` (S39): `GET /finances/finance-cash-flow/projection/` (lê `months`) + `POST /finances/finance-cash-flow/simulate/` (ecoa `deltas`). **Não** mexer em handlers existentes.
- `frontend/lib/utils/constants.ts` — adicionar `ROUTES.FINANCES_PROJECTION = '/finances/projection'`. **Não** alterar rotas existentes (legado `/financial/...` intacto — coexistência, design §1).
- `frontend/components/layouts/sidebar.tsx` — adicionar o item "Projeção" ao **grupo de menu "Condomínio"** criado na S40 (mesmo grupo das telas `finances/*`; **não** no grupo "Financeiro" legado). Se o grupo "Condomínio" ainda não existir no estado atual da árvore (S40 não consolidada), **anotar a divergência** e adicionar no grupo correto conforme o real.

### NÃO fazer (pertence a outras sessões)
- **Sem distribuição por proprietário** (`OwnerDistributionService`, cards "por proprietário", seção de donos externos Tiago/Alvaro, fold household Raul & Célia exibido) — **Fase 6, Sessões 49/50**. Esta sessão **não** cria `useOwnerDistribution` nem o sub-grupo `finances.ownerDistribution`, nem consome `displayable_leases`/agregação por dono. (DEPENDENCY ORDER 49→50; cross-phase: Fase 6 depende da Fase 5.)
- **Sem alterar** os hooks/schemas de `finances` da S39 (`use-bills`/`use-billing-accounts`/`use-payments`/`use-combined-calendar`/`useOverdueBills`) nem os de **fechamento/saldo da S46** (`useCondoBalance`/`useCondoMonthClose`/KPIs) — apenas **consumir** se a page referenciar saldo (não obrigatório aqui).
- **Sem mexer** no **módulo legado** (`use-cash-flow.ts`, `simulator/*`, `financial/*`) — coexistência (design §1/§15). **Não** wirar o `CashFlowChart` legado nesta tela; a projeção do condo é **escopo próprio** (§9).
- **Sem `combined_calendar`/KPIs de calendário** (S39/S40), **sem reserva/income/close UI** (Fase 4 — S46), **sem CRUD page** (S40/S43).
- **Sem mexer** em `client.ts`, `test-utils.tsx`, `lib/types/api.ts`, `query-client.ts` — só **consumir**.
- **Backend**: nenhuma alteração em `finances/services/`, viewsets ou URLs — a S47 entregou o backend; esta sessão é **só frontend**.

---

## Especificação

### Tipos de dashboard — Decimal como **string** (hand-written, não Zod)

Espelhar a separação da S39 (design §10): os endpoints `projection`/`simulate` são **dashboard read-only** → Decimais vêm como **string** e os tipos são **hand-written** (como `CashFlowProjectionMonth` em `use-cash-flow.ts:46-54`), **não** schemas Zod com `.transform(Number)`. A conversão `Number(...)` acontece **só** no boundary de exibição/redução (tabela/gráfico), via um helper local `toNumber(v: number | string): number` (espelha `comparison-table.tsx:31-33`) — **uma fonte só** por arquivo, ou um helper compartilhado se repetir.

```ts
// lib/api/hooks/use-condo-projection.ts
import { useQuery, useMutation, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

export interface CondoProjectionMonth {
  year: number;
  month: number;
  income_total: string;      // Decimal string (§4.5 receita filtrada por collectibility)
  expenses_total: string;    // Decimal string
  net: string;        // Decimal string (resultado de competência do mês)
  cumulative_cash: string; // Decimal string (fold ancorado no último CondoMonthClose, §4.7)
  is_actual: boolean;        // mês < atual = Real; futuro = Projetado (§8)
}

export type CondoSimulationType = '...';   // casar 1:1 com CondoSimulationService da S47 (handoff)
export interface CondoSimulationDelta { type: CondoSimulationType; /* params conforme S47 */ }

export interface CondoComparisonMonth {
  year: number; month: number;
  base_net: string; base_cumulative: string;
  simulated_net: string; simulated_cumulative: string;
  delta: string;
}
export interface CondoSimulationResult {
  base: CondoProjectionMonth[];
  simulated: CondoProjectionMonth[];
  comparison: { month_by_month: CondoComparisonMonth[] };
}

const STALE_TIME = 1000 * 60 * 5;

export function useCondoProjection(months = 12) {
  return useQuery({
    queryKey: queryKeys.finances.projection.list(months),
    queryFn: async () => {
      const { data } = await apiClient.get<CondoProjectionMonth[]>(
        '/finances/finance-cash-flow/projection/',
        { params: { months } },
      );
      return data;
    },
    placeholderData: keepPreviousData, // §10: NÃO useSuspenseQuery
    staleTime: STALE_TIME,
  });
}

export function useCondoSimulation() {
  return useMutation<CondoSimulationResult, Error, CondoSimulationDelta[]>({
    mutationFn: async (deltas) => {
      const { data } = await apiClient.post<CondoSimulationResult>(
        '/finances/finance-cash-flow/simulate/',
        { deltas },
      );
      return data;
    },
  });
}
```

> **Decisão (KISS/YAGNI)**: `useCondoSimulation` é `useMutation` puro (sem cache de query — what-if é efêmero, design §8 "deltas em memória, sem persistência"). A page mantém o `SimulationResult` em `useState` (padrão `simulator/page.tsx:28`). **Não** persistir cenários, **não** exportar, **não** criar query para a simulação (espelha a decisão do simulador legado).

### Tabela de projeção (load-bearing) — badge Real/Projetado + coluna acumulada (§8, §10)

- Colunas: **Mês** (`MONTH_ABBR[m.month-1]/shortYear`, importado de `formatters.ts:104`), **Receita** (`income_total`), **Despesa** (`expenses_total`), **Resultado** (`net`, cor por sinal: `>=0 ? text-success : text-destructive`), **Acumulado** (`cumulative_cash`).
- **Badge por linha** (status nunca só por cor — sempre rótulo): `is_actual` → `Badge` "Real" (variante neutra/secondary); `!is_actual` → `Badge` "Projetado" (variante outline). Espelha o "(projetado)" do tooltip de `cash-flow-chart.tsx:67-69`, mas como **badge textual** na tabela.
- **`TableFooter` de totais** (espelha `comparison-table.tsx:94-112`): Σ receita, Σ despesa, Σ resultado; **acumulado NÃO soma** (o último valor da coluna acumulada é o saldo final — exibir o último `cumulative_cash`, não a soma). Documentar essa escolha no código (a coluna acumulada já é um fold; somá-la seria duplicar — §4.7).
- **Quantização (§4 / §18 off-by-cent)**: somar os Decimais convertidos (`toNumber`) e formatar com `formatCurrency` (que arredonda a 2 casas — `formatters.ts:9-10`). O total da tabela **não** pode divergir por centavo da soma dos meses (teste pinado).

### Gráfico de projeção (NÃO-blocking no gate) — ComposedChart (§10/§12)

- Espelha `cash-flow-chart.tsx:253-299`: `ResponsiveContainer` h=400; `Bar` `income`/`expenses` no `yAxisId="left"` (k-formatter); `Line` `cumulative` no `yAxisId="right"`; `CustomTooltip` marcando "(projetado)" quando `!is_actual`; `CartesianGrid`/`Legend`/cores `var(--success)`/`var(--destructive)`/`var(--info)`.
- **Não-blocking**: o gráfico **não** é exigido verde no gate (design §10 "gráficos = não-blocking", §12 "exceto gráficos, marcados não-blocking"). **Sem teste obrigatório** do gráfico (Recharts em jsdom é frágil — não escrever asserts de SVG). A **tabela** é o artefato verificado.

### Simulador what-if (efêmero, §8)

- `simulation-panel.tsx`: inputs efêmeros para cada `CondoSimulationType` da S47 (ex.: gasto extra/mês, parcela nova/mês). Estado local (`useState`), monta `CondoSimulationDelta[]`, e ao adicionar/remover chama `props.onSimulate(deltas)`.
- A **page** detém o hook (`useCondoSimulation`) e o resultado (`useState<CondoSimulationResult | null>`), espelhando `simulator/page.tsx:25-50` — inclusive o `useRef(simulation.mutate)` (decisão #13 do SESSION_STATE) para estabilizar o callback **sem** `eslint-disable`. Erro → `toast.error` (PT); pendente → indicador "Simulando...".
- `simulation-comparison.tsx`: render do `{base, simulated, comparison}` — gráfico base×simulado (não-blocking) + (opcional) sub-tabela de delta mês a mês (load-bearing se incluída).

### query-keys — sub-grupos dentro de `finances` (espelha S39)

```ts
// dentro do grupo finances existente (S39), após combinedCalendar/overdueBills:
projection: {
  all: ['finances', 'projection'] as const,
  list: (months: number) => [...queryKeys.finances.projection.all, months] as const,
},
simulation: {
  all: ['finances', 'simulation'] as const,
},
```

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md` + memória do projeto): mockar **APENAS fronteiras externas** = **HTTP via MSW**. **NUNCA** mockar TanStack Query, `queryClient`, hooks internos, `apiClient`, formatters, ou Recharts. Testes de hook em `lib/api/hooks/__tests__/` com `createWrapper`/`createTestQueryClient` (`test-utils.tsx:69-74`); testes de componente com `renderWithProviders` (`:55-64`), passando os dados como **props** (a tabela é pura — não precisa de MSW; o hook é testado à parte).

### 1. RED — escrever os testes primeiro

Criar os 2 arquivos de teste. Cobrir, no mínimo:

**`use-condo-projection.test.tsx`** (MSW; `server.use(...)` por teste)
- [ ] `useCondoProjection()` busca e retorna a lista de 12 meses; cada item tem `income_total`/`expenses_total`/`net`/`cumulative_cash` (string) + `is_actual` (bool).
- [ ] `useCondoProjection(24)` repassa `months=24` na query string (verificar via `new URL(request.url).searchParams.get('months')`).
- [ ] **`placeholderData: keepPreviousData`**: ao trocar `months` (re-render do hook com novo arg), `result.current.data` mantém os dados anteriores enquanto o novo carrega (`isPlaceholderData === true`), sem voltar a `undefined` (espelha o teste de `placeholderData` da S39 `use-combined-calendar.test.tsx`).
- [ ] **§18 (fold/janela pré-tracking)**: a projeção devolvida pode conter mês com `income_total='0.00'` (pré-tracking) **sem** quebrar o tipo; o hook **não** filtra/recalcula — só repassa (o fold é backend, §4.7). Asserir que um mês com receita zero vem intacto.
- [ ] `useCondoSimulation()` POST `/finances/finance-cash-flow/simulate/` com `{ deltas }` no body (capturar via `await request.json()` no handler) → retorna `{ base, simulated, comparison.month_by_month }`.
- [ ] `useCondoSimulation()` com `deltas: []` (sem cenário) → resposta válida (base == simulated; delta 0) **ou** o handler ecoa base — asserir que `comparison.month_by_month` existe.
- [ ] erro 500 em `projection` → `isError`; erro 500 em `simulate` (mutation) → `mutation.isError`.

**`projection-table.test.tsx`** (render real, props, sem MSW)
- [ ] linha com `is_actual=true` mostra badge **"Real"**; linha com `is_actual=false` mostra badge **"Projetado"** (asserir o texto do badge por linha — status com rótulo, não só cor).
- [ ] coluna **Acumulado** exibe `formatCurrency(cumulative_cash)` de cada mês (asserir o valor formatado de ≥1 linha).
- [ ] resultado negativo (`net` < 0) recebe classe `text-destructive`; positivo `text-success` (asserir via classe no elemento da célula de resultado).
- [ ] **`TableFooter`**: Σ receita e Σ despesa = soma dos meses (asserir o total formatado); **Acumulado no rodapé = último `cumulative_cash`** (não a soma) — asserir explicitamente que o rodapé acumulado ≠ soma das linhas quando há ≥2 meses com acumulado distinto.
- [ ] **§18 off-by-cent / quantização**: com meses contendo centavos (ex.: `'100.10'`, `'200.20'`, `'300.30'`), o total exibido = `formatCurrency(600.60)` exato (sem off-by-cent) — provar que a redução converte→soma→formata no boundary.
- [ ] tabela vazia (`months=[]`) → render do empty state (sem crash; rodapé não soma).

> Rodar (devem **falhar** — hooks/componentes/handlers ainda não existem):
> ```bash
> cd frontend
> npx vitest run "lib/api/hooks/__tests__/use-condo-projection.test.tsx" "app/(dashboard)/finances/projection/_components/__tests__/projection-table.test.tsx"
> ```

### 2. GREEN — implementar hooks + query-keys + MSW + componentes + page

1. Criar `use-condo-projection.ts` (tipos hand-written + `useCondoProjection` + `useCondoSimulation`). Decimais ficam string; conversão só no boundary de exibição.
2. Adicionar os sub-grupos `projection`/`simulation` em `query-keys.ts` (dentro de `finances`, `as const`).
3. Estender `tests/mocks/data/finances.ts` (`createMockCondoProjection`/`createMockCondoSimulation`) + adicionar handlers em `financeHandlers` (`projection` GET lendo `months`; `simulate` POST ecoando `deltas`).
4. Criar `projection-table.tsx` (load-bearing — badge `is_actual` + coluna acumulada + footer; importar `formatCurrency`/`MONTH_ABBR`), `projection-chart.tsx` (ComposedChart, não-blocking), `simulation-panel.tsx`, `simulation-comparison.tsx`, e `page.tsx` (detém os hooks; `useRef(mutate)`; loading/erro guards; gating `is_staff` se algum controle persistir).
5. Modificar `constants.ts` (`FINANCES_PROJECTION`) e `sidebar.tsx` (item "Projeção" no grupo "Condomínio").

Rodar até verde:
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-condo-projection.test.tsx" "app/(dashboard)/finances/projection/_components/__tests__/projection-table.test.tsx"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `toNumber` (string→Number no boundary) extraído como helper local único por arquivo (ou compartilhado se repetir entre tabela/gráfico) — espelha `comparison-table.tsx:31-33`. **Sem** redefinir `MONTH_NAMES` inline: importar `MONTH_ABBR` de `formatters.ts:104` (DRY).
- Garantir que **nenhum** componente recalcula `cumulative_cash` (lê o fold do backend, §4.7) — só converte para exibir/somar.
- `useRef(simulation.mutate)` para o callback estável (decisão #13) — **sem** `eslint-disable`.
- Confirmar que o gráfico é **não-blocking** (sem teste de SVG) e a **tabela** carrega a verificação.

### 4. VERIFY — gate frontend (escopo desta sessão)
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-condo-projection.test.tsx" "app/(dashboard)/finances/projection/_components/__tests__/projection-table.test.tsx"
npx tsc --noEmit
npx eslint "lib/api/hooks/use-condo-projection.ts" "app/(dashboard)/finances/projection" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "lib/api/hooks/__tests__/use-condo-projection.test.tsx"
```
Zero erros e zero avisos em todos.

---

## Constraints

- **Camadas FE** (`.claude/rules/architecture.md` Frontend Layers): hooks = TanStack Query (comunicação); page usa hooks + lógica mínima; componentes recebem **props** (sem chamada de API direta). O `simulation-panel`/`projection-table`/`*-chart` **não** consomem hooks — só a `page.tsx` consome.
- **Toda chamada HTTP via `apiClient`** (`frontend/CLAUDE.md`) — **nunca** `axios`/`fetch` cru em produção; testes mockam a rede via **MSW**.
- **TanStack Query v5**: `useQuery` + `placeholderData: keepPreviousData` para a projeção — **NÃO** `useSuspenseQuery` (descarta `placeholderData`, design §10). `useCondoSimulation` = `useMutation` (efêmero, sem cache).
- **Recharts v3.3** já no repo (não instalar). O **gráfico é não-blocking** no gate (§10/§12) — **sem** teste de SVG (Recharts/jsdom frágil). A **tabela** é o artefato load-bearing.
- **Decimal como string no dashboard** → `Number` **só** no boundary de exibição/redução (espelha `use-cash-flow.ts`/`comparison-table.tsx`). O front **nunca** recalcula `cumulative_cash`/net (lê do backend, §4.7/§8). Quantização no boundary (`formatCurrency` arredonda) — **sem off-by-cent** (§18).
- **DRY**: importar `MONTH_ABBR`/`formatCurrency` de `formatters.ts` (não redefinir `MONTH_NAMES` inline); `toNumber` único; query-keys central (sem keys inline); estender `data/finances.ts`/`financeHandlers` (não recriar). **Sem re-export / barrel files / shims.**
- **`as`/`!` proibidos em produção** (regra + memória): hooks/componentes/page sem `as`/non-null. Em testes, `as` só no carve-out de fixture de boundary (corpo MSW/`request.json()`), exatamente como `prompts/24`/`33`/`39` documentaram — **nunca** em produção.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o código de verdade. TypeScript strict + `noUncheckedIndexedAccess` (guardas em índices de array — `arr[i] ?? fallback`, como `comparison-table.tsx:64`).
- **Sem `from __future__`/`TYPE_CHECKING`** (irrelevante no FE) e **sem re-export**: importar tipos/hooks **direto da fonte** (`@/lib/api/hooks/use-condo-projection`, `@/lib/utils/formatters`). `import type` para tipos.
- **Namespaced URLs** `/finances/finance-cash-flow/...` (design §9) — **não** colidir com o legado (`/cash-flow/...`). **Não** wirar o `CashFlowChart`/simulador legados nesta tela.
- **Escopo de fase**: **sem Fase 6** (distribuição/owner) — nem hook, nem query-key, nem componente. `is_staff` gating só se algum controle escrever/persistir (what-if é leitura efêmera).
- Mensagens ao usuário em **Português** (toasts, empty states, badges "Real"/"Projetado"); identificadores/tipos/logs em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `use-condo-projection.ts` criado com tipos hand-written de dashboard (Decimal **string**) + `useCondoProjection(months?)` (`useQuery`, `placeholderData: keepPreviousData`, `staleTime`) + `useCondoSimulation()` (`useMutation` POST `simulate`). Decimais não transformados no hook (convertidos só na UI). Sem re-export.
- [ ] `query-keys.ts` ganha os sub-grupos `finances.projection.list(months)` + `finances.simulation.all` (dentro do grupo `finances` da S39), `as const`; grupos existentes intactos.
- [ ] Página `frontend/app/(dashboard)/finances/projection/page.tsx` + 4 componentes (`projection-table`, `projection-chart`, `simulation-panel`, `simulation-comparison`): a **page** detém os hooks (`useRef(mutate)` p/ estabilizar), componentes recebem props.
- [ ] **Tabela load-bearing**: colunas Mês/Receita/Despesa/Resultado/**Acumulado** + **badge Real/Projetado** por linha (de `is_actual`) + `TableFooter` (Σ receita/despesa/resultado; acumulado = **último** `cumulative_cash`, não soma); cor por sinal; **sem off-by-cent** (quantização no boundary).
- [ ] **Gráfico não-blocking**: `projection-chart` (ComposedChart Bar receita+despesa + Line acumulado + tooltip "(projetado)") e `simulation-comparison` (base×simulado + Area delta) presentes, **sem** teste de SVG exigido no gate.
- [ ] Simulador what-if efêmero: `simulation-panel` monta `CondoSimulationDelta[]` (tipos casando 1:1 com a S47) → page chama `useCondoSimulation` → exibe `{base,simulated,comparison}`; erro → `toast.error` (PT); pendente → "Simulando...".
- [ ] `tests/mocks/data/finances.ts` estendido (`createMockCondoProjection`/`createMockCondoSimulation`, fora do barrel) + `financeHandlers` com `projection`/`simulate` (handlers existentes intactos); mock data importado direto de `./data/finances`.
- [ ] `constants.ts` ganha `FINANCES_PROJECTION`; `sidebar.tsx` ganha "Projeção" no grupo "Condomínio" (não no "Financeiro" legado).
- [ ] 2 arquivos de teste cobrem todos os cenários listados (projeção: shape/`months`/`placeholderData`/janela-zero/`is_actual`; simulação: POST `deltas`/resposta/erro; tabela: badge Real-Projetado/acumulado/cor-por-sinal/footer-último-acumulado/off-by-cent/empty).
- [ ] `npx vitest run` (os 2 arquivos) passa 100%.
- [ ] `npx tsc --noEmit` limpo; `npx eslint` (todos os arquivos tocados) zero erros/zero avisos — **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção.
- [ ] **Sem distribuição/owner** (Fase 6); legado (`use-cash-flow`/`simulator/*`/`financial/*`) intacto; `client.ts`/`test-utils.tsx`/`lib/types/api.ts`/`query-client.ts` não tocados; nenhuma alteração de backend.

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão):
   ```bash
   cd frontend
   npx vitest run "lib/api/hooks/__tests__/use-condo-projection.test.tsx" "app/(dashboard)/finances/projection/_components/__tests__/projection-table.test.tsx"
   npx tsc --noEmit
   npx eslint "lib/api/hooks/use-condo-projection.ts" "app/(dashboard)/finances/projection" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "lib/api/hooks/__tests__/use-condo-projection.test.tsx"
   ```
   (Frontend gate canônico — `.claude/rules/coding-standards.md`: `npm run lint && npm run type-check && npm run test:unit`. Aqui escopado aos arquivos tocados, conforme memória do projeto.) Zero erros **e** zero warnings.
2. Atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 48 (status **concluída**) na tabela de progresso da feature Condomínio Finance.
   - Listar **Arquivos Criados** (`use-condo-projection.ts`, `finances/projection/page.tsx` + 4 componentes, 2 testes) e **Modificados** (`query-keys.ts` sub-grupos `projection`/`simulation`, `data/finances.ts`, `handlers.ts`, `constants.ts`, `sidebar.tsx`).
   - **Anotar os contratos cross-session (verbatim, ver abaixo)** para a S49/S50 (Fase 6) consumir sem derivar.
   - **Anotar divergências** se algum shape real da S47 diferir do deste prompt (`is_actual` vs `is_projected`, nomes de `delta`/totais, valores de `CondoSimulationType`) e como o tipo foi ajustado; e se o grupo "Condomínio" do sidebar diferir do esperado.
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`; criar branch se necessário):
   ```
   feat(finances): add 12-month projection table + ComposedChart + what-if simulator (phase 5 frontend)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **49 — Backend: `OwnerDistributionService` + agregação por dono (Fase 6)** — consome `CondoBalanceService.result_of_month` (Fase 4, S45/S46) e `displayable_leases`/`effective_rental_value`. A S50 (FE da distribuição) **consome** os hooks/query-keys/tabela desta sessão como referência de padrão (cards "por proprietário" + seção de externos).

---

### Contratos cross-session definidos por esta sessão (consumir verbatim na S49/S50)

- **Hooks** (`@/lib/api/hooks/use-condo-projection`): `useCondoProjection(months = 12)` (read-only, `placeholderData`) + `useCondoSimulation()` (`useMutation`, efêmero). Tipos `CondoProjectionMonth` (Decimais **string**: `income_total`/`expenses_total`/`net`/`cumulative_cash` + `is_actual`), `CondoSimulationDelta`/`CondoSimulationType`, `CondoSimulationResult`/`CondoComparisonMonth`. **A Fase 6 NÃO redefine** esses tipos — importa daqui (DRY).
- **query-keys**: sub-grupos `queryKeys.finances.projection.list(months)` + `queryKeys.finances.simulation.all` (dentro do grupo `finances`). A S50 adiciona `finances.ownerDistribution.*` **ao lado** (não dentro de `projection`).
- **Página/rota**: `ROUTES.FINANCES_PROJECTION = '/finances/projection'`; item "Projeção" no grupo de menu "Condomínio" do `sidebar.tsx`. A S50 (distribuição) registra sua rota/item **no mesmo grupo**.
- **Padrão de tabela/dashboard de finances** (load-bearing × gráfico não-blocking): `projection-table.tsx` (badge Real/Projetado + coluna acumulada + footer) e `projection-chart.tsx` (ComposedChart não-blocking) são o **template** que as telas "por proprietário" da S50 seguem (tabela verificada no gate; gráfico não-blocking; Decimal-string→Number só no boundary; `formatCurrency`/`MONTH_ABBR` de `formatters.ts`).
- **Decimal no boundary**: dashboard de `finances` = **string** no tipo, `Number()` só na UI (helper `toNumber`), quantização via `formatCurrency` (sem off-by-cent) — convenção mantida da S39, reafirmada aqui.
- **MSW**: `createMockCondoProjection`/`createMockCondoSimulation` em `tests/mocks/data/finances.ts` + handlers `projection`/`simulate` em `financeHandlers` — disponíveis para os testes da S50 (que mockam só o boundary de dados via MSW, **não** os hooks).
