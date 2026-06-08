# Sessão 50 — Frontend: cards por proprietário + seção de donos externos + polish/E2E

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46 → 47 → 48 → 49 → **50** (esta é a 50 — **Fase 6 FRONTEND, ÚLTIMA da feature**)
> Esta sessão entrega a **UI da distribuição por proprietário**: (1) **cards "por proprietário"** = o resultado do mês do **household Raul & Célia (= o próprio condomínio)** com **carry-forward** acumulado (§4.7); (2) uma **seção informativa de donos externos** (Tiago/Alvaro) — **só exibição** (agregação `owner→Σ effective_rental_value` de `displayable_leases`), **fora** do net/caixa/distribuição (§4.7/§6). Consome o backend da **Sessão 49** (`OwnerDistributionService.compute` + endpoint `/api/finances/finance-dashboard/by_owner`). Encerra com **polish geral** e um **teste de fluxo integrado ("E2E" via Vitest+MSW)** do caminho principal (lançar conta → pagar parcial → mover reserva → fechar mês → projeção → distribuição) e a **verificação final do gate em `finances`**. **Sem nada de futuro** (`CondominiumOwnership`, rateio individual, ponte versionada, isolamento multi-condomínio).

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.5 receita filtrada por collectibility, §4.7 distribuição + carry-forward/fold ancorado + janela pré-tracking + donos externos só exibição, §6 receita do condomínio e proprietários não-invasivo, §8 `OwnerDistributionService.compute`, §9 API `finance-dashboard/by_owner`, §10 Frontend/Dashboard — "resultado do mês do household" + "seção informativa de donos externos", §11 cache `finance-dashboard`, §12 gate por fase, §14 Fase 6, §15 fora de escopo, §17 verificação PROD, §18 edge-cases da Fase 6/distribuição)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md` — **confirmar S49 (BE distribuição) concluída** (esta sessão consome `OwnerDistributionService` + endpoint `by_owner`). **Se S49 não estiver concluída, PARE** (DEPENDENCY ORDER 49 → 50). **Confirmar também S48 concluída** (DEPENDENCY ORDER 48 → 50 — esta sessão segue o **template** de tabela/hook/query-keys/MSW da projeção e reusa `formatCurrency`/`MONTH_ABBR`, `StatCard`/`AmountDisplay` da S46, o grupo de menu "Condomínio" e `ROUTES.FINANCES_*`). Se S48/S46/S40 não estiverem consolidadas, **anotar a divergência** e adaptar ao estado real.
- **Contrato do backend (verbatim, NÃO derivar)**: a seção "Contratos cross-session definidos por esta sessão" no fim de `@prompts/49-finances-owner-distribution-backend.md` (shape real de `by_owner`: `household` com fold/carry-forward + `external_owners[]`). **Se algum campo do export real da S49 divergir deste prompt, o export real prevalece** — ajustar o tipo, anotar a divergência no handoff; **nunca inventar campo**.
- **Padrão de tabela/hook/dashboard de `finances` a seguir (S48 — template)**: a seção "Contratos cross-session definidos por esta sessão" no fim de `@prompts/48-finances-projection-simulation-frontend.md` (tabela load-bearing × gráfico não-blocking; Decimal-string→Number só no boundary; `placeholderData: keepPreviousData`; query-keys central; MSW estendido).
- **Primitivos de KPI (S46) a reusar**: `StatCard`/`AmountDisplay` (criados na S46 em `components/ui/`) + a fileira `FinanceKpiRow` (S46) e os hooks de saldo (`use-finance-balance`).
- **Camada de dados `finances` (a estender, NÃO recriar)**: contratos no fim de `@prompts/39-finances-frontend-data-layer.md` (grupo `queryKeys.finances.*`, `tests/mocks/data/finances.ts`, `financeHandlers`, separação Decimal-string-no-dashboard × Number-no-boundary-no-CRUD).
- **Regras do projeto**: `frontend/CLAUDE.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`.

### Exemplares (arquivo:linha — abrir e seguir; exemplar > descrição)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Hook de dashboard read-only (`useQuery`+`params`+`placeholderData`) — template da S48** | `frontend/lib/api/hooks/use-condo-projection.ts` (S48 — `useCondoProjection(months)` `useQuery`+`placeholderData: keepPreviousData`+`staleTime`, Decimal **string** no tipo, sem transform) | **Exemplar canônico** do `useOwnerDistribution(year, month, buildingId?)`: mesma forma `useQuery` + `params:{year,month,building_id?}` + `placeholderData`. **NÃO** `useSuspenseQuery` (§10). |
| **Hook calendário/`placeholderData` + `building_id` condicional (mesma família finances)** | `frontend/lib/api/hooks/use-combined-calendar.ts` (S39 — `building_id` só quando definido; `staleTime`; `keepPreviousData`) | Forma de `building_id` condicional nos `params` (espelhar; o by_owner aceita `building_id` opcional, §9). |
| **Hook de overview/saldo (string Decimal, hand-written, `{year,month,building_id?}`)** | `frontend/lib/api/hooks/use-finance-balance.ts` (S46 — `useFinanceOverview` `placeholderData`, dinheiro string não transformado) | **Mesma família**; consistência de tipos hand-written de dashboard. O `useOwnerDistribution` espelha exatamente este shape de hook. |
| **Tabela load-bearing (badge por linha + coluna acumulada + `TableFooter` + cor por sinal + `MONTH_ABBR`/`shortYear`)** | `frontend/app/(dashboard)/financial/simulator/_components/comparison-table.tsx:31-33` (`toNumber`), `:39-42` (`reduce` de totais), `:62-92` (linha: `MONTH_NAMES[m.month-1] ?? ''` :64, `shortYear` :65, cor `delta>=0 ? text-success : text-destructive` :84-89), `:94-112` (`<TableFooter>` total) | **Exemplar canônico** da **tabela do household** (resultado/carry-forward acumulado por mês). **DRY**: importar `MONTH_ABBR` de `formatters.ts:104` (NÃO redefinir `MONTH_NAMES` inline como este legado); `toNumber` único; guarda `?? ''`/`?? 0` sob `noUncheckedIndexedAccess`. |
| **Tabela de projeção da feature (badge Real/Projetado + coluna acumulada + footer = último acumulado)** | `frontend/app/(dashboard)/finances/projection/_components/projection-table.tsx` (S48) | **Template direto** da `household-distribution-table.tsx` desta sessão (mesma convenção de coluna acumulada cujo total no rodapé = **último** valor do fold, não soma — §4.7). |
| **`StatCard` (KPI primitivo) — porta da S46** | `frontend/components/ui/stat-card.tsx` (S46 — props `label`/`value`/`icon?`/`tone?`; tons → tokens `text-success`/`text-destructive`/`text-warning`/`text-foreground`) | **Reusar** para o card "Resultado do mês (household)" e "Disponível para distribuição" — **não** recriar Card. |
| **`AmountDisplay` (valor monetário) — porta da S46** | `frontend/components/ui/amount-display.tsx` (S46 — `formatCurrency`, sinal/variante, `tabular-nums`) | **Reusar** nos cards do household e na seção de externos. |
| **Card de KPI real do repo (grid + skeleton + tom condicional)** | `frontend/app/(dashboard)/financial/_components/balance-cards.tsx:25-34` (`BalanceCardsSkeleton`), `:48` (grid `grid gap-4 md:grid-cols-2 lg:grid-cols-4`), `:88-99` (tom `>=0 ? text-success : text-destructive`) | **Estrutura/skeleton/grid/tokens** dos cards do household (skeleton de loading espelha este). |
| **Página de dashboard de `finances` (detém hooks, loading/erro guards, `{year,month}` por estado local)** | `frontend/app/(dashboard)/finances/projection/page.tsx` (S48 — `'use client'`, detém os hooks, componentes recebem props, loading/erro guards) | **Exemplar canônico** da `finances/distribution/page.tsx` (única que consome o hook; componentes puros). |
| **Seção informativa read-only (tabela simples + empty state, sem ações)** | `frontend/app/(dashboard)/_components/late-payments-alert.tsx:17-21` (datas por **split** `dateStr.split('-')`) + lista read-only | Forma da **seção de donos externos** (read-only, sem escrita; datas/competência por split, nunca `new Date(iso)`). |
| **`is_staff` gating de UI (fonte do usuário)** | `frontend/store/auth-store.ts` (`user.is_staff`) via `useAuthStore()` (`financial/settings/page.tsx:36-37`) ou `useCurrentUser()` (`frontend/lib/api/hooks/use-auth.ts:107`) | A distribuição é **read-only** (não há escrita nesta tela). Gating só se algum controle exportar/persistir — caso contrário, **não** adicionar gating supérfluo (YAGNI). |
| **query-keys central — grupo `finances` (S39) + sub-grupos `projection`/`simulation` (S48)** | `frontend/lib/api/query-keys.ts:131-134` (`rentCalendar.month(year,month,buildingId)` — forma `buildingId ?? null`) + grupo `finances` (S39/S46/S48) | **Adicionar** `finances.ownerDistribution.month(year,month,buildingId?)` **ao lado** de `projection`/`simulation` (não dentro). Estabilizar com `buildingId ?? null`, `as const`. |
| **Formatters TZ-safe (moeda + mês/ano + abreviação)** | `frontend/lib/utils/formatters.ts:5-15` (`formatCurrency` → "R$ 1.500,00"), `:89-93` (`formatMonthYear(year,month)`), `:104` (`MONTH_ABBR`) | **Reusar** `formatCurrency`/`MONTH_ABBR`. **NOTA**: `formatMonthYear` usa `Intl.DateTimeFormat('pt-BR',{month:'long',year:'numeric'})` → produz **"Junho de 2026"** (não "Junho/2026" — o S46 anotou "barra" por engano; **asserir o output real** "Junho de 2026" com inicial maiúscula, `:92`). |
| **apiClient (Axios; desembrulha `results`; nunca axios cru)** | `frontend/lib/api/client.ts:7-14`,`:19-38` | **Toda** chamada HTTP via `apiClient` (`/finances/finance-dashboard/by_owner`; `baseURL` já é `/api`). |
| **MSW (`API_BASE`, reset, array final) + finances data/handlers (S39, estendidos S46/S48)** | `frontend/tests/mocks/handlers.ts:30` (`API_BASE`), `:43-52` (`resetMockData`), `financeHandlers` + `frontend/tests/mocks/data/finances.ts` (factories S39/S46/S48) | **Estender** `data/finances.ts` (`createMockOwnerDistribution`) + `financeHandlers` (`by_owner` GET lendo `year`/`month`). **Não** recriar os existentes (DRY). |
| **test-utils (wrapper/queryClient `gcTime:0`; `renderWithProviders`/`createWrapper`)** | `frontend/tests/test-utils.tsx:55-64` (`renderWithProviders`), `:69-74` (`createWrapper`), `:15-28` (`createTestQueryClient`) | Reusar **verbatim** nos testes de hook/componente; e no **teste de fluxo integrado** (render real + MSW, sem mock de internals). |

### Contrato do backend que esta sessão CONSOME (S49 — verbatim, NÃO derivar)

> **Pré-requisito**: S49 expõe `GET /api/finances/finance-dashboard/by_owner?year=&month=&building_id=` (bare `ViewSet` + `IsAuthenticated`/`FinancialReadOnly`, design §9), servindo `OwnerDistributionService.compute(year, month)` (§8). Decimais como **string** (convenção de dashboard). `reference_month` = 1º dia.

- **`by_owner` (read)** → objeto com **duas partes** (espelha §4.7/§10):
  - **`household`** (= condomínio = Raul & Célia, fold/carry-forward §4.7): `year`, `month`, `net_result` (**string** — resultado de competência do mês, vindo de `CondoBalanceService.result_of_month`, §8/DRY), `carried_in` (**string** — `carregado_in[M]`, ≤ 0), `available` (**string** — `max(0, net + carried_in)`, distribuível), `carried_out` (**string** — `min(0, net + carried_in)`, ≤ 0, vai para o próximo mês). *(Se a S49 também devolver a série mensal `months[]` para a tabela acumulada, usar o nome real — ver nota abaixo.)*
  - **`external_owners`** (**só exibição**, §6/§4.7): lista de `{ owner_id, owner_name, total }` onde `total` (**string**) = `Σ effective_rental_value` dos `displayable_leases` daquele dono no mês (agregação `owner→Σ`). **Tiago** (`836/101,103`) e **Alvaro** (`836/200,203`) — os únicos com `owner` setado em PROD (§17). **Estes valores NÃO entram** em `household`/net/caixa.
- **Série mensal do household (para a tabela acumulada)**: se a S49 expuser `household.months[]` (cada item `year`/`month`/`net_result`/`available`/`carried_out`/`cumulative`), a tabela load-bearing usa essa série; **se** a S49 entregar apenas o mês corrente (sem série), a "tabela" vira **cards do mês** (resultado / carregado / disponível / próximo carry) e a coluna acumulada exibe o `cumulative`/`carried_out` do mês — **anotar a forma real no handoff** e adaptar. Em nenhum caso o front **recalcula** o fold (lê do backend, §4.7).

> **NOTA crítica de URL**: endpoints de `finances` são **namespaced** sob `/api/finances/...` (design §9). O hook chama `apiClient.get('/finances/finance-dashboard/by_owner', { params })`. Nos testes MSW, `API_BASE = 'http://localhost:8008/api'` + caminho `/finances/finance-dashboard/by_owner`.

> **NOTA crítica de fold (§4.7)**: o `household` já vem **ancorado** (`carried_in` do último `CondoMonthClose`; janela pré-tracking → receita estruturalmente zero, não acumula net negativo espúrio). O front **só exibe**: `available = max(0, net + carried_in)` e `carried_out = min(0, …)` chegam prontos. **Não** reimplementar `max`/`min`/fold no front.

---

## Escopo

### Arquivos a criar

**Camada de dados (hook + tipos + MSW)**
- `frontend/lib/api/hooks/use-owner-distribution.ts` — tipos hand-written de dashboard (Decimal **string**): `OwnerHouseholdMonth` (`year`/`month`/`net_result`/`carried_in`/`available`/`carried_out`/`cumulative?`), `OwnerHouseholdDistribution` (mês corrente + opcional `months[]`), `ExternalOwnerEntry` (`owner_id`/`owner_name`/`total`), `OwnerDistribution` (`household` + `external_owners[]`) + `useOwnerDistribution(year, month, buildingId?)` (`useQuery`, `placeholderData: keepPreviousData`, `staleTime`). Decimais ficam **string** no tipo (converter só na UI). **Sem re-export.**
- `frontend/lib/api/hooks/__tests__/use-owner-distribution.test.tsx` — testes de hook (MSW): fetch/shape `household`+`external_owners`; `year`/`month`/`building_id` na query string; `placeholderData` entre meses; janela pré-tracking (`net_result='0.00'`, `available='0.00'`) intacta; erro 500.

**Tela de distribuição** — `frontend/app/(dashboard)/finances/distribution/`
- `page.tsx` — `'use client'`: única que consome `useOwnerDistribution`; `useState {year,month}` (default mês atual via `new Date()`, KISS); loading → skeleton; erro → Card PT; passa dados como **props** aos componentes. Navegação de mês simples (mesmo padrão das telas finances).
- `_components/household-distribution.tsx` — **load-bearing**: cards "por proprietário" do **household** (Raul & Célia = condomínio): **Resultado do mês** (`net_result`, tom por sinal), **Carregado do mês anterior** (`carried_in`, ≤ 0), **Disponível para distribuição** (`available`, tom positivo), **A carregar (próximo mês)** (`carried_out`, ≤ 0) — via `StatCard`/`AmountDisplay`. **Se** houver `household.months[]`, renderiza também a **tabela acumulada** (Mês / Resultado / Disponível / Acumulado), `TableFooter` cujo Acumulado = **último** `cumulative` (não soma — §4.7), badge/rótulo do mês corrente. Componente **puro** (props), `import MONTH_ABBR`/`formatCurrency`.
- `_components/external-owners-section.tsx` — **seção informativa** (read-only): tabela "Donos externos" (Dono / Total no mês = `Σ effective_rental_value`), com **nota explícita PT** "Apenas informativo — não entra no resultado do condomínio" (§4.7/§6). Empty state PT "Nenhum dono externo neste mês". Componente puro.
- `_components/__tests__/household-distribution.test.tsx` — testes da parte load-bearing (render real, props, sem MSW): cards com rótulos PT corretos + valores `formatCurrency`; **`available = max(0, …)` exibido como veio do backend** (front não recalcula); cor por sinal do `net_result`; (se tabela) Acumulado no footer = último `cumulative`; off-by-cent/quantização; mês corrente destacado.
- `_components/__tests__/external-owners-section.test.tsx` — testes da seção (render real, props): linhas Tiago/Alvaro com `owner_name` + total `formatCurrency`; **nota informativa PT presente**; empty state quando `external_owners=[]`; os totais externos **não** aparecem em nenhum card/total do household (asserir separação).

**Teste de fluxo integrado ("E2E" via Vitest + MSW — fronteira HTTP)**
- `frontend/tests/flows/__tests__/condo-finance-main-flow.test.tsx` — **fluxo principal** do condomínio, render real de páginas, **MSW como única fronteira** (sem mock de hooks/componentes/TanStack/`apiClient`): lançar conta (`bills/create_with_lines`) → pagar parcial (`bills/{id}/pay`) → mover reserva (`reserves/{id}/deposit`) → fechar mês (`condo-month-closes/close`) → ver projeção (`finance-cash-flow/projection`) → ver distribuição (`finance-dashboard/by_owner`). Verifica que cada passo dispara o request certo (capturado no handler) e que a tela reflete o resultado (KPIs/tabela atualizam, sem stale). **Read-flow primário**; mutations apenas confirmando o request/efeito, sem testar SVG (gráficos não-blocking).

### Arquivos a modificar
- `frontend/lib/api/query-keys.ts` — adicionar `finances.ownerDistribution.month(year, month, buildingId?)` (forma `buildingId ?? null`, `as const`), **ao lado** de `projection`/`simulation` (S48). Sub-grupos existentes **intactos**.
- `frontend/lib/utils/constants.ts` — adicionar `FINANCES_DISTRIBUTION: '/finances/distribution'`. `FINANCES_*` existentes (S40/S46/S48) e rotas legadas **intactas** (coexistência, §1).
- `frontend/components/layouts/sidebar.tsx` — adicionar o item "Distribuição" ao **grupo de menu "Condomínio"** (mesmo grupo das telas `finances/*`, criado na S40; espelhar o formato `{ key: ROUTES.X, label }` de `financialChildren:44-57`). **Não** tocar nos itens existentes nem no grupo "Financeiro" legado. Se o grupo "Condomínio" ainda não existir no estado real da árvore, **anotar a divergência** e registrar no grupo correto.
- `frontend/tests/mocks/data/finances.ts` — **estender** (S39/S46/S48) com `createMockOwnerDistribution(overrides?)` (`household` com fold + `external_owners` Tiago/Alvaro). Importar os tipos de `use-owner-distribution`. **Fora** de qualquer barrel.
- `frontend/tests/mocks/handlers.ts` — adicionar a `financeHandlers` (S39): `GET /finances/finance-dashboard/by_owner` (lê `year`/`month`/`building_id`). **Não** mexer em handlers existentes.

### NÃO fazer (pertence a outras sessões / futuro)
- **NADA do futuro (design §15)**: **sem** `CondominiumOwnership`, **sem** rateio individual (Persons de Raul/Célia), **sem** ponte versionada/`contract_version`/app financeiro pessoal, **sem** isolamento/permissões multi-condomínio, **sem** seletor de condomínio. A distribuição é **household único** (Raul & Célia = condomínio) + **donos externos só exibição** (§4.7/§6/§13). **Não** criar hook/query-key/componente para nenhum desses.
- **Sem backend** — `OwnerDistributionService`, agregação por dono e o endpoint `by_owner` são da **S49**. Nada em `core/`/`finances/` (nem service, nem viewset, nem URL, nem migration).
- **Sem recriar** os hooks/schemas/tipos de fases anteriores: `use-condo-projection`/`use-condo-simulation` (S48), `use-finance-balance`/`use-reserves`/`use-income-entries`/`use-condo-month-closes` (S46), `use-bills`/`use-payments`/`use-billing-accounts`/`use-combined-calendar` (S39/S40), `StatCard`/`AmountDisplay` (S46). **Importar da fonte** (DRY). Se um hook necessário não existir no estado real, **PARE** e registre a lacuna.
- **Sem mexer** no **módulo legado** (`financial/*`, `use-cash-flow.ts`, `simulator/*`, `balance-cards.tsx`) — coexistência (§1/§15). O `comparison-table.tsx`/`balance-cards.tsx` legados são **só exemplares**, não tocar.
- **Sem** alterar `client.ts`, `test-utils.tsx`, `query-client.ts`, `lib/types/api.ts`, `card.tsx`, `formatters.ts` — só **consumir**.
- **Sem gráfico blocking**: se um gráfico de distribuição/donut for incluído como polish, é **não-blocking** no gate (§10/§12) — **sem** teste de SVG, **sem** instalar Recharts novo (já no repo). A **tabela/cards** é o artefato load-bearing.
- **Sem Playwright/browser E2E** — o repo não tem Playwright; o "fluxo principal" é um **teste de integração Vitest + MSW** (fronteira HTTP), conforme a mock policy. **Não** adicionar dependência de E2E de navegador.

---

## Especificação

Direção de dados (`frontend/CLAUDE.md` + `.claude/rules/architecture.md` Frontend Layers): **só a `page.tsx`** (container) consome `useOwnerDistribution`. `household-distribution.tsx` e `external-owners-section.tsx` são **puros** (props in). **Nenhum componente chama `apiClient`/axios direto.** Moeda via `formatCurrency`/`AmountDisplay`; mês via `MONTH_ABBR`/`formatMonthYear`; datas/competência por **split** (nunca `new Date(iso)`). Mensagens ao usuário em **PT**; identificadores/tipos em **EN**.

### Decimal: dashboard = string (design §10, espelha S48)
- `by_owner` é **dashboard read-only** → Decimais vêm **string**; tipos **hand-written** (como `CondoProjectionMonth`/`FinanceOverview`), **não** schema Zod com `.transform(Number)`. `Number(...)` só no boundary de exibição/redução, via helper local `toNumber(v: number | string): number` (espelha `comparison-table.tsx:31-33`) — **uma fonte por arquivo**. O front **nunca** recalcula `available`/`carried_out`/`cumulative` (lê o fold do backend, §4.7).

```ts
// lib/api/hooks/use-owner-distribution.ts
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';

export interface OwnerHouseholdMonth {
  year: number;
  month: number;
  net_result: string;     // resultado de competência (= CondoBalanceService.result_of_month, §8)
  carried_in: string;     // carregado_in[M], <= 0 (§4.7)
  available: string;      // max(0, net + carried_in) — distribuível (§4.7)
  carried_out: string;    // min(0, net + carried_in), <= 0 — vai p/ o próximo mês (§4.7)
  cumulative?: string;    // acumulado do fold, se a S49 expuser série mensal
}

export interface ExternalOwnerEntry {
  owner_id: number;
  owner_name: string;     // Tiago / Alvaro (§17)
  total: string;          // Σ effective_rental_value dos displayable_leases do dono (§4.7/§6) — só exibição
}

export interface OwnerHouseholdDistribution extends OwnerHouseholdMonth {
  months?: OwnerHouseholdMonth[]; // série acumulada (se a S49 a expuser; senão indefinido → cards do mês)
}

export interface OwnerDistribution {
  household: OwnerHouseholdDistribution;
  external_owners: ExternalOwnerEntry[];
}

const STALE_TIME = 1000 * 60 * 5;

export function useOwnerDistribution(year: number, month: number, buildingId?: number) {
  return useQuery({
    queryKey: queryKeys.finances.ownerDistribution.month(year, month, buildingId),
    queryFn: async () => {
      const { data } = await apiClient.get<OwnerDistribution>(
        '/finances/finance-dashboard/by_owner',
        { params: { year, month, ...(buildingId !== undefined ? { building_id: buildingId } : {}) } },
      );
      return data;
    },
    placeholderData: keepPreviousData, // §10: NÃO useSuspenseQuery
    staleTime: STALE_TIME,
  });
}
```

> **Decisão (KISS/YAGNI)**: um único `useQuery` read-only — sem mutation (distribuição é computada no backend). Sem cache extra, sem `useState` de servidor. Se a S49 não expor `months[]`, a UI degrada para **cards do mês** sem quebrar (`months` opcional).

### Cards "por proprietário" — household (§4.7/§10)
- 4 `StatCard` em `grid gap-4 md:grid-cols-2 lg:grid-cols-4` (espelha `balance-cards.tsx:48`):
  - **Resultado do mês** (`net_result`, tom por sinal `>=0 ? positive : negative`; rótulo "Resultado do mês — {formatMonthYear(year,month)}" → "...Junho de 2026"). É o resultado do **household = condomínio** (§4.7).
  - **Carregado do mês anterior** (`carried_in`, ≤ 0; tom `negative` se < 0 senão `neutral`; rótulo PT "Carregado do mês anterior").
  - **Disponível para distribuição** (`available`, tom `positive`; rótulo "Disponível para distribuição"). É `max(0, net + carried_in)` — **lido do backend**, não recalculado.
  - **A carregar (próximo mês)** (`carried_out`, ≤ 0; tom `neutral`/`warning`; rótulo "A carregar para o próximo mês").
- Valores via `AmountDisplay`/`formatCurrency` lendo as **strings** (converter no boundary). **Não** somar/aplicar `max`/`min` no front (§4.7).
- **Tabela acumulada (se `household.months[]` existir)**: colunas Mês (`MONTH_ABBR[m.month-1]/shortYear`) / Resultado (`net_result`, cor por sinal) / Disponível (`available`) / **Acumulado** (`cumulative`); `TableFooter` com Σ resultado e **Acumulado = último `cumulative`** (não soma — o fold já acumula, §4.7); mês corrente com badge/destaque PT "Mês atual". Espelha `projection-table.tsx`/`comparison-table.tsx:94-112`.

### Seção informativa de donos externos (§4.7/§6 — só exibição)
- Tabela simples read-only: **Dono** (`owner_name`) · **Total no mês** (`total`, `formatCurrency`). Sem ações, sem gating de escrita (é leitura).
- **Nota informativa obrigatória (PT)** acima/abaixo da tabela: "Apenas informativo — repasse aos donos externos; não entra no resultado do condomínio." (§4.7 "donos externos não entram em net/caixa/distribuição — só exibição"). Esta nota é **load-bearing** (asserida no teste).
- Empty state PT "Nenhum dono externo neste mês" quando `external_owners=[]`.
- Os totais externos **nunca** são somados a nada do household — a separação é visual e estrutural (asserir no teste que não há card/total combinando os dois).

### Polish geral (§12 — incluído no gate, exceto gráficos)
- Revisar as telas de `finances/*` quanto a: rótulos PT consistentes; `formatCurrency`/`MONTH_ABBR` (sem `MONTH_NAMES` inline duplicado); datas por split; skeletons de loading; empty states; responsividade (cards via grid `md:`/`lg:`); `tabular-nums` em valores. **Sem** refator do legado. Polish = correções pequenas e DRY **nas telas de `finances` criadas nesta feature**, não reescrita. (Se um polish exigir tocar arquivo de outra sessão já fechada, **anotar no handoff** em vez de alterar silenciosamente.)
- **Gráficos = não-blocking** (§10/§12): qualquer chart adicionado é opcional, sem teste de SVG.

### query-keys — sub-grupo dentro de `finances` (espelha S48)
```ts
// dentro do grupo finances existente, ao lado de projection/simulation (S48):
ownerDistribution: {
  all: ['finances', 'owner-distribution'] as const,
  month: (year: number, month: number, buildingId?: number) =>
    [...queryKeys.finances.ownerDistribution.all, year, month, buildingId ?? null] as const,
},
```

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md` + memória do projeto): mockar **APENAS fronteiras externas** = **HTTP via MSW**. **NUNCA** mockar TanStack Query, `queryClient`, hooks internos, `apiClient`, formatters, `StatCard`/`AmountDisplay`, ou Recharts. Testes de **hook** em `lib/api/hooks/__tests__/` com `createWrapper`/`createTestQueryClient` (`test-utils.tsx:69-74`); testes de **componente** com `renderWithProviders` (`:55-64`), passando dados como **props** (componentes puros não precisam de MSW). O **teste de fluxo** usa MSW + render real de páginas — **nenhum** mock de internals.

### 1. RED — escrever os testes primeiro (devem falhar por inexistência)
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-owner-distribution.test.tsx" \
  "app/(dashboard)/finances/distribution/_components/__tests__/household-distribution.test.tsx" \
  "app/(dashboard)/finances/distribution/_components/__tests__/external-owners-section.test.tsx" \
  "tests/flows/__tests__/condo-finance-main-flow.test.tsx"
```

Cobrir, no mínimo:

**`use-owner-distribution.test.tsx`** (MSW; `server.use(...)` por teste)
- [ ] `useOwnerDistribution(2026, 6)` busca e retorna `{ household, external_owners }`; `household` tem `net_result`/`carried_in`/`available`/`carried_out` (string); `external_owners` é lista de `{ owner_id, owner_name, total }`.
- [ ] `year`/`month` na query string; `building_id` repassado **só** quando definido (verificar via `new URL(request.url).searchParams`) — espelha `use-combined-calendar`/`use-rent-calendar`.
- [ ] **`placeholderData: keepPreviousData`**: ao trocar `month` (re-render com novo arg), `data` mantém o mês anterior (`isPlaceholderData === true`), sem voltar a `undefined`.
- [ ] **§18 (janela pré-tracking / fold)**: mês pré-tracking devolvido com `net_result='0.00'`, `available='0.00'`, `carried_out='0.00'`, `external_owners=[]` → o hook **não** filtra/recalcula, só repassa intacto (o fold é backend, §4.7). Asserir os zeros vêm como vieram.
- [ ] erro 500 → `isError`.

**`household-distribution.test.tsx`** (render real, props, sem MSW)
- [ ] 4 cards com rótulos PT: "Resultado do mês — {formatMonthYear}", "Carregado do mês anterior", "Disponível para distribuição", "A carregar para o próximo mês"; valores via `formatCurrency` (1 asserção por card lendo a **string** do household).
- [ ] **§4.7 — front não recalcula**: dado `net_result='100.00'`, `carried_in='-30.00'`, `available='70.00'`, `carried_out='0.00'` → o card "Disponível" exibe **`formatCurrency('70.00')`** (o valor do backend), **não** uma soma local. Caso negativo: `net_result='-50.00'`, `carried_in='-10.00'`, `available='0.00'`, `carried_out='-60.00'` → "Disponível" = R$ 0,00, "A carregar" = -R$ 60,00 (lidos, não computados).
- [ ] cor por sinal do `net_result`: negativo → `text-destructive`; positivo → `text-success`.
- [ ] **se tabela** (`months[]` presente): coluna **Acumulado** exibe `cumulative` por mês; `TableFooter` Acumulado = **último** `cumulative` (≠ soma quando ≥2 meses distintos); mês corrente com badge/rótulo "Mês atual".
- [ ] **§18 off-by-cent**: meses com centavos (`'100.10'`/`'200.20'`/`'300.30'`) → total/exibição `formatCurrency` exato (sem off-by-cent) — redução converte→soma→formata no boundary.
- [ ] sem `months` → renderiza só os cards do mês (degrade graceful, sem crash).

**`external-owners-section.test.tsx`** (render real, props)
- [ ] linhas Tiago/Alvaro com `owner_name` + `total` via `formatCurrency`.
- [ ] **nota informativa PT presente** ("não entra no resultado do condomínio" / "apenas informativo") — asserir o texto (load-bearing, §4.7).
- [ ] empty state PT quando `external_owners=[]`.
- [ ] **separação (§4.7/§6)**: os totais externos **não** aparecem em nenhum elemento de card/total do household — asserir que renderizar a seção de externos com um household não introduz soma combinada (ex.: o total do household exibido continua igual com/sem externos).

**`condo-finance-main-flow.test.tsx`** (MSW como única fronteira; render real)
- [ ] **fluxo principal** encadeado, cada passo asserido pelo request capturado no handler MSW e pelo reflexo na UI:
  1. **Lançar conta** → `POST /finances/bills/create_with_lines` com linhas (capturar body) → a conta aparece / KPI Atrasados reflete.
  2. **Pagar parcial** → `POST /finances/bills/{id}/pay` com `amount` parcial (capturar) → `amount_remaining > 0` refletido (pagamento parcial, §18).
  3. **Mover reserva** → `POST /finances/reserves/{id}/deposit` (capturar `amount`) → saldo de reserva reflete; **saldo total inalterado** exibido (zero-sum, §4.3 — KPI Saldo total lido do `overview`, não recalculado).
  4. **Fechar mês** → `POST /finances/condo-month-closes/close` `{year,month}` (capturar) → status do mês = fechado.
  5. **Projeção** → `GET /finances/finance-cash-flow/projection?months=12` → tabela de projeção com `is_actual` mistos (sem testar SVG).
  6. **Distribuição** → `GET /finances/finance-dashboard/by_owner?year=&month=` → cards do household + seção de externos refletindo os mocks.
- [ ] o fluxo **não** mocka nenhum hook/componente/`apiClient`/TanStack — só os handlers MSW (fronteira HTTP). Gráficos **não** são asseridos (não-blocking).
- [ ] após cada mutation, a UI **não** fica stale (invalidação dos hooks reflete) — asserir o valor atualizado, não o anterior.

> Rodar (devem **falhar** — hook/componentes/handlers/fluxo ainda não existem):
> ```bash
> cd frontend
> npx vitest run "lib/api/hooks/__tests__/use-owner-distribution.test.tsx" "app/(dashboard)/finances/distribution/_components/__tests__/household-distribution.test.tsx" "app/(dashboard)/finances/distribution/_components/__tests__/external-owners-section.test.tsx" "tests/flows/__tests__/condo-finance-main-flow.test.tsx"
> ```

### 2. GREEN — implementar (mínimo para passar)
1. Criar `use-owner-distribution.ts` (tipos hand-written string + `useOwnerDistribution`). Decimais string; conversão só no boundary.
2. Adicionar `finances.ownerDistribution.month(...)` em `query-keys.ts` (ao lado de `projection`/`simulation`, `as const`).
3. Estender `tests/mocks/data/finances.ts` (`createMockOwnerDistribution`) + handler `by_owner` GET (lendo `year`/`month`/`building_id`) em `financeHandlers`. Para o teste de fluxo, garantir que os handlers de `create_with_lines`/`pay`/`deposit`/`close`/`projection` já existem (S40/S46/S48) — se faltar algum, **estender** `financeHandlers` (não recriar).
4. Criar `household-distribution.tsx` (load-bearing — 4 cards via `StatCard`/`AmountDisplay` + tabela acumulada opcional; `formatCurrency`/`MONTH_ABBR`), `external-owners-section.tsx` (seção informativa + nota PT), e `page.tsx` (detém o hook; loading/erro guards; nav de mês local).
5. Modificar `constants.ts` (`FINANCES_DISTRIBUTION`) e `sidebar.tsx` (item "Distribuição" no grupo "Condomínio").
6. Criar `tests/flows/__tests__/condo-finance-main-flow.test.tsx` (render real + MSW; sem mock de internals).
7. Polish: varrer as telas `finances/*` desta feature (rótulos PT, `MONTH_ABBR` em vez de `MONTH_NAMES` inline, datas por split, skeletons/empty states) — apenas correções DRY/clareza, sem reescrever.
8. Imports diretos da fonte (S39/S46/S48/S49 + primitivos); **sem** redefinir tipos, **sem** re-export.

Rodar até verde (mesmos paths do RED).

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `toNumber` (string→Number no boundary) extraído como helper local único por arquivo (ou compartilhado se repetir entre cards/tabela) — espelha `comparison-table.tsx:31-33`. **Sem** `MONTH_NAMES` inline: importar `MONTH_ABBR` de `formatters.ts:104` (DRY) — corrigir também o legado **só** se estiver dentro do escopo desta feature (não tocar `comparison-table.tsx` legado).
- Garantir que **nenhum** componente recalcula `available`/`carried_out`/`cumulative` (lê o fold do backend, §4.7) — só converte para exibir/somar.
- `StatCard`/`AmountDisplay` (S46) são a **fonte única** de KPI/valor — reusar (não repetir `Card`). Helper de mapeamento tom→token num único lugar (já na S46).
- Confirmar que a seção de externos é puramente informativa (sem ação/escrita) e que a separação household × externos é estrutural (sem soma combinada).
- O teste de fluxo usa o **mesmo** MSW data/handlers das fases anteriores (DRY) — não duplicar factories.

### 4. VERIFY — gate frontend (escopo desta sessão) + gate final de `finances`
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-owner-distribution.test.tsx" "app/(dashboard)/finances/distribution" "tests/flows/__tests__/condo-finance-main-flow.test.tsx"
npx tsc --noEmit
npx eslint "lib/api/hooks/use-owner-distribution.ts" "app/(dashboard)/finances/distribution" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "tests/flows/__tests__/condo-finance-main-flow.test.tsx"
```
Zero erros e zero avisos em todos.

**Verificação final do gate em `finances` (encerramento da feature — §12)**: como esta é a **última sessão da feature**, rodar uma passada de confirmação do gate ampliado no backend de `finances` (o backend não é alterado aqui, mas o gate de fase exige confirmar que a fase fecha 100% verde):
```bash
ruff check && ruff format --check && mypy core/ finances/ && pyright && python -m pytest --cov=finances --cov-report=term-missing --cov-fail-under=90
```
> Rodar **escopado** conforme a memória do projeto (a suíte completa tem problemas pré-existentes de xdist/Redis). O objetivo é confirmar **≥90% standalone em `finances`** e zero erros/warnings em `mypy core/ finances/` + `pyright`. Se houver falha pré-existente **não relacionada** a esta feature, **anotar** (não corrigir fora de escopo); se houver gap **dentro** de `finances`, **PARAR e corrigir** antes de fechar (gate por fase).

---

## Constraints

- **Camadas FE** (`.claude/rules/architecture.md` Frontend Layers): hook = TanStack Query (comunicação); `page.tsx` usa o hook + lógica mínima; `household-distribution`/`external-owners-section` recebem **props** (sem chamada de API direta). **Só** a `page.tsx` consome `useOwnerDistribution`.
- **Toda chamada HTTP via `apiClient`** (`frontend/CLAUDE.md`) — **nunca** `axios`/`fetch` cru em produção; testes mockam a rede via **MSW**.
- **TanStack Query v5**: `useQuery` + `placeholderData: keepPreviousData` — **NÃO** `useSuspenseQuery` (descarta `placeholderData`, §10). Sem mutation (distribuição é read-only computada no backend).
- **Decimal como string no dashboard** → `Number` **só** no boundary de exibição/redução (espelha `use-condo-projection`/`comparison-table.tsx:31-33`). O front **nunca** recalcula `available`/`carried_out`/`cumulative`/net (lê do backend, §4.7/§8). Quantização no boundary (`formatCurrency` arredonda — `formatters.ts:9-10`) — **sem off-by-cent** (§18).
- **Donos externos = só exibição** (§4.7/§6): a seção é informativa, **fora** de net/caixa/distribuição; **nota PT obrigatória**; **nunca** somar externos ao household.
- **DRY**: importar `MONTH_ABBR`/`formatCurrency` de `formatters.ts` (não redefinir `MONTH_NAMES` inline); `toNumber` único; query-keys central; reusar `StatCard`/`AmountDisplay` (S46) e o template de tabela (S48); estender `data/finances.ts`/`financeHandlers` (não recriar). **Sem re-export / barrel files / shims.**
- **`as`/`!` proibidos em produção** (regra + memória): hook/componentes/page sem `as`/non-null; guardas em índices de array (`arr[i] ?? fallback`, como `comparison-table.tsx:64`). Em testes, `as` só no carve-out de fixture de boundary (corpo MSW/`request.json()`), exatamente como `prompts/24`/`33`/`39`/`48` documentaram — **nunca** em produção.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o código de verdade. TypeScript strict + `noUncheckedIndexedAccess`.
- **Sem `from __future__`/`TYPE_CHECKING`** (irrelevante no FE) e **sem re-export**: importar tipos/hooks **direto da fonte** (`@/lib/api/hooks/use-owner-distribution`, `@/components/ui/stat-card`, `@/lib/utils/formatters`). `import type` para tipos.
- **Namespaced URLs** `/finances/finance-dashboard/by_owner` (§9) — **não** colidir com o legado (`/financial-dashboard/...`). **Não** wirar nada do legado nesta tela.
- **Escopo de fase**: **NADA do futuro** (`CondominiumOwnership`, rateio individual, ponte versionada, multi-condo isolation) — nem hook, nem query-key, nem componente. Distribuição = household único + externos só exibição.
- **Gráficos não-blocking** (§10/§12): qualquer chart é opcional, sem teste de SVG, sem dependência nova.
- **"E2E" = Vitest + MSW** (não Playwright/navegador — o repo não tem E2E de browser): fronteira única = HTTP via MSW; render real; **sem** mock de hooks/componentes/`apiClient`/TanStack.
- Mensagens ao usuário em **Português** (rótulos dos cards, nota dos externos, empty states, erros); identificadores/tipos/logs em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `use-owner-distribution.ts` criado com tipos hand-written de dashboard (Decimal **string**: `net_result`/`carried_in`/`available`/`carried_out`/`cumulative?`/`total`) + `useOwnerDistribution(year, month, buildingId?)` (`useQuery`, `placeholderData: keepPreviousData`, `staleTime`, `building_id` condicional). Decimais não transformados no hook (convertidos só na UI). Sem re-export.
- [ ] `query-keys.ts` ganha `finances.ownerDistribution.month(year, month, buildingId?)` (`buildingId ?? null`, `as const`), ao lado de `projection`/`simulation` (S48); grupos existentes intactos.
- [ ] Página `frontend/app/(dashboard)/finances/distribution/page.tsx` + 2 componentes (`household-distribution`, `external-owners-section`): a **page** detém o hook; componentes recebem props; loading/erro/empty guards PT.
- [ ] **Cards "por proprietário" (household)**: Resultado do mês / Carregado anterior / **Disponível para distribuição** / A carregar (próximo mês) via `StatCard`/`AmountDisplay`; valores **lidos do backend** (front não aplica `max`/`min`/soma — §4.7); cor por sinal; (se `months[]`) tabela acumulada com Acumulado no footer = **último** `cumulative` (não soma).
- [ ] **Seção informativa de donos externos**: tabela Dono/Total (Tiago/Alvaro), **nota PT "não entra no resultado do condomínio"** presente, empty state PT; totais externos **nunca** somados ao household (separação asserida).
- [ ] **Sem off-by-cent** (quantização no boundary via `formatCurrency`); datas/competência por **split**; `MONTH_ABBR`/`formatCurrency` reusados (sem `MONTH_NAMES` inline duplicado).
- [ ] `tests/mocks/data/finances.ts` estendido (`createMockOwnerDistribution`, fora de barrel) + `financeHandlers` com `by_owner` (handlers existentes intactos); mock data importado direto de `./data/finances`.
- [ ] `constants.ts` ganha `FINANCES_DISTRIBUTION`; `sidebar.tsx` ganha "Distribuição" no grupo "Condomínio" (não no "Financeiro" legado).
- [ ] **Teste de fluxo integrado** `condo-finance-main-flow.test.tsx` cobre lançar conta → pagar parcial → mover reserva → fechar mês → projeção → distribuição, **só com MSW** (sem mock de internals), asserindo request + reflexo na UI a cada passo, sem testar SVG.
- [ ] 4 arquivos de teste cobrem todos os cenários listados (hook: shape/`params`/`placeholderData`/janela-zero/erro; household: 4 cards/não-recalcula/cor/tabela-acumulada-footer/off-by-cent/degrade-sem-months; externos: linhas/nota-PT/empty/separação; fluxo: 6 passos encadeados).
- [ ] `npx vitest run` (os 4 arquivos) passa 100%; `npx tsc --noEmit` limpo; `npx eslint` (todos os arquivos tocados) zero erros/zero avisos — **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção.
- [ ] **Verificação final do gate `finances`**: `mypy core/ finances/` + `pyright` limpos; `python -m pytest --cov=finances` **≥90% standalone** (escopado conforme memória; falhas pré-existentes não relacionadas anotadas). A Fase 6 fecha 100% verde.
- [ ] **NADA do futuro** (`CondominiumOwnership`, rateio individual, ponte, multi-condo isolation); legado intacto; `client.ts`/`test-utils.tsx`/`query-client.ts`/`lib/types/api.ts`/`card.tsx`/`formatters.ts` não tocados; nenhuma alteração de backend.

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão):
   ```bash
   cd frontend
   npx vitest run "lib/api/hooks/__tests__/use-owner-distribution.test.tsx" "app/(dashboard)/finances/distribution" "tests/flows/__tests__/condo-finance-main-flow.test.tsx"
   npx tsc --noEmit
   npx eslint "lib/api/hooks/use-owner-distribution.ts" "app/(dashboard)/finances/distribution" "lib/api/query-keys.ts" "lib/utils/constants.ts" "components/layouts/sidebar.tsx" "tests/mocks/data/finances.ts" "tests/mocks/handlers.ts" "tests/flows/__tests__/condo-finance-main-flow.test.tsx"
   ```
   (Frontend gate canônico — `.claude/rules/coding-standards.md`: `npm run lint && npm run type-check && npm run test:unit`. Aqui escopado aos arquivos tocados, conforme memória do projeto.) Zero erros **e** zero warnings.
2. Rodar a **verificação final do gate `finances`** (encerramento da feature — §12): `mypy core/ finances/ && pyright && python -m pytest --cov=finances --cov-report=term-missing --cov-fail-under=90` (escopado; ≥90% standalone). Anotar qualquer falha pré-existente não relacionada; corrigir gaps **dentro** de `finances`.
3. Atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 50 (status **concluída**) na tabela de progresso da feature Condomínio Finance e marcar a **feature COMPLETA** (Fase 6 / S50 fecha o ciclo 34→50).
   - Listar **Arquivos Criados** (`use-owner-distribution.ts`, `finances/distribution/page.tsx` + 2 componentes, 3 testes + `tests/flows/__tests__/condo-finance-main-flow.test.tsx`) e **Modificados** (`query-keys.ts` sub-grupo `ownerDistribution`, `data/finances.ts`, `handlers.ts`, `constants.ts`, `sidebar.tsx`).
   - **Anotar divergências** se o shape real da S49 diferir (`household.months[]` ausente → cards do mês; nomes de `carried_in`/`carried_out`/`available`/`net_result`; campos de `external_owners`) e como o tipo foi ajustado; e se o grupo "Condomínio" do sidebar diferir do esperado.
   - Anotar o resultado da **verificação final do gate `finances`** (coverage % standalone, mypy/pyright limpos).
4. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
5. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`; criar branch se necessário):
   ```
   feat(finances): add per-owner distribution cards + external-owners section + main-flow E2E (phase 6 frontend)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
6. **Última sessão da feature** — não há próxima. Confirmar no handoff que a feature "Condomínio Finance" (saídas/saldo/reserva/projeção/distribuição) está **encerrada**: backend (`finances` app + serviços + endpoints, Fases 1a–6) e frontend (calendário combinado, contas/pagamentos, parcelas/folha, saldo/reserva/income/fechamento, projeção/simulação, distribuição por proprietário) completos, gate `finances` ≥90%, legado coexistindo intacto. O futuro (`CondominiumOwnership`, rateio individual, ponte versionada para o app pessoal, isolamento multi-condomínio) permanece **fora de escopo** (§15).

---

### Contratos cross-session consumidos por esta sessão (verbatim — não derivar)

- **Backend S49** (`@/api/finances/finance-dashboard/by_owner`): `OwnerDistribution = { household: OwnerHouseholdDistribution, external_owners: ExternalOwnerEntry[] }`; `household` = fold/carry-forward (`net_result`/`carried_in`/`available`/`carried_out`/`cumulative?`/opcional `months[]`), **lido do backend, nunca recalculado** (§4.7); `external_owners` = agregação `owner→Σ effective_rental_value` de `displayable_leases` (`rent_schedule_service.py:194`), **só exibição** (§4.7/§6). Decimais **string**.
- **Frontend S48** (template): `useCondoProjection`/tabela load-bearing × gráfico não-blocking; `placeholderData: keepPreviousData`; query-keys central (`finances.projection`/`simulation` → esta sessão adiciona `finances.ownerDistribution` **ao lado**); Decimal-string→Number só no boundary; `ROUTES.FINANCES_PROJECTION` + grupo "Condomínio" do sidebar (esta sessão adiciona `FINANCES_DISTRIBUTION` no mesmo grupo); MSW `data/finances.ts` + `financeHandlers` estendidos.
- **Frontend S46** (primitivos): `StatCard`/`AmountDisplay` (`components/ui/`) + `formatCurrency`/`MONTH_ABBR`/`formatMonthYear` (`formatters.ts:5,89,104` — `formatMonthYear` produz "Junho de 2026", não "/").
- **PROD (§17)**: únicos donos externos = **Tiago** (`836/101,103`) e **Alvaro** (`836/200,203`); demais `owner=null` = household Raul & Célia = condomínio. **Raul/Célia não existem como `Person`** (household, não rateio individual — §13/§15).
