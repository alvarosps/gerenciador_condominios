# Sessão 74 — Frontend: cockpit do mês reescrito sobre `useMonthBoard` (estrutura)

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida — `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (rev. 2)
> **Sessões da feature**: 65 → 66 → 67 → 68 → 69 → 70 → 71 → 72 → 73 → **74** → 75 → 76
> Esta sessão reescreve a **estrutura** de `/finances/bills` sobre a fonte única `month_board` (S66/S71): (1) `useBills` + agrupamento client-side + `page_size=10000` **saem** da página (o `useMemo` de agrupamento é removido); (2) seção fixa **"Atrasadas"** (Card não-colapsável ACIMA do Accordion, cross-competência) + sub-seção **"Dívida adiada/suspensa"** (badges de estado, fora dos totais); (3) corpo = Accordion por prédio vindo de `groups` do backend; (4) banner **"Gerar contas faltantes (N)"** quando `generation.missing_count > 0`; (5) badges **"valor estimado"** / **"aguardando fatura"** nas colunas; (6) faixa de totais do mês (`totals`). **Interações de linha (popover pagar/editar, conta avulsa, importar na linha, CTA Parcelar) são a S75; preflight do fechamento é a S76.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §1 diagnóstico, §2 decisões, §3.3 cockpit, §4 `month_board`, §8 erros, §9 testes FE)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Contratos AUTORITATIVOS S66/S71/S74** (se este prompt divergir, ELES prevalecem): `@prompts/SESSION_STATE.md` (seção "Cockpit operacional de contas — Sessões 65–76")
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — VERIFICADOS; ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Página atual do cockpit** | `frontend/app/(dashboard)/finances/bills/page.tsx:1-347` — filtros/estado :64-86; `useBills(filters)` :93; agrupamento client-side `useMemo` :99-114 (**REMOVER** — vem do backend `groups`); MonthNavigator :214-241 (**manter**, `shiftMonth` :88-91); select competência :242-253 (**remover** — ver Especificação); select situação :254-266 (**manter**); Accordion :274-301 (**manter** p/ corpo); modais :303-321 | Base da reescrita. `IptuRiskBanner` (:208-212) e modais existentes permanecem |
| **Builder de colunas** | `frontend/app/(dashboard)/finances/bills/_components/bill-columns.tsx:40-136` (Descrição :47-53; Total :74-78; Status c/ `BillStatusChip` :84-94) | Onde entram os badges "valor estimado"/"aguardando fatura" |
| **Hook do board (S71)** | `lib/api/hooks/` — `useMonthBoard(year, month)` criado na S71 (`staleTime: 0`; localizar o arquivo real pós-S71) + `month-board.schema.ts` em `lib/schemas/finances/` | Fonte única de dados desta página |
| **Hook gerar mês** | `frontend/lib/api/hooks/use-bills.ts:212-224` — **`useGenerateMonthBills`** (nome real; POST `generate_month/`, invalida caches) | O banner chama este hook existente — NÃO criar outro |
| **Formatação de datas sem `new Date(iso)`** | `bill-columns.tsx:19-31` (`competenceLabel`/`dueDateLabel` via `split`) | O badge de dias de atraso segue o mesmo cuidado de timezone |
| **Card / Badge / Alert** | `components/ui/card.tsx`, `components/ui/badge.tsx`, `components/ui/alert.tsx` | Seção Atrasadas = `Card`; badges de estado/estimativa |
| **`DataTable` (sem `onRowClick` — NÃO estender)** | `frontend/components/tables/data-table.tsx:40-72` (`Column.render` :40; props :56-72) | Tabelas das seções usam o mesmo `DataTable` |
| **Teste de página com MSW (padrão pós-migração P6.1)** | `frontend/app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx:1-297` (`setAdmin` :50-55; `server.use` + spies de body :77-99; `renderWithProviders`/`waitForQueriesToSettle`) | Espelho dos testes desta sessão — **MSW, nunca `vi.mock` de hooks internos** |
| **Factories MSW** | `frontend/tests/mocks/data/finances.ts` (`createMockBill` :107-132 — raw `z.input`, dinheiro string `'350.00'`); `createMockMonthBoard` (S71) | Montar payloads do board nos testes |
| **Regra de ordem dos handlers MSW** | `frontend/tests/mocks/handlers.ts:2245-2248` (actions de collection ANTES das rotas `:id`) | Handler de `finance-dashboard/month_board` |
| **Money no FE** | `frontend/lib/schemas/finances/money.ts:4` (`moneyField` → **number** após parse) | "aguardando fatura" = estimada com `amount_total === 0` (número, não `'0.00'`) |

### O que as S65–S73 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S65 (BE)**: `Bill.amount_is_estimated` read-only no `BillSerializer` (True ao gerar; False em editar/pagar/importar).
- **S66 (BE)**: `GET finance-dashboard/month_board?year&month` (UNCACHED, `IsAdminUser`, 400 em params inválidos). Payload (verbatim): `{ overdue: [bill…], deferred_suspended: [bill…], groups: [{building_id: int|null, building_label: str, bills: [bill…]}], totals: {due: str, paid: str, remaining: str, overdue: str}, generation: {missing_count: int} }`. Regras: `overdue` = resto > 0, `due_date < hoje`, ACTIVE, **qualquer competência**; `deferred_suspended` = SUSPENDED/DEFERRED com resto > 0, qualquer competência, **fora dos totais**; CANCELED nunca aparece; `groups` = bills ACTIVE da competência (pagas incluídas), bucket sem prédio = "Condomínio" por último; `totals.overdue` = Σ resto da seção overdue.
- **S71 (FE)**: `month-board.schema.ts` (raw-shape, `z.input` p/ MSW), `queryKeys.finances.monthBoard {all, month(y,m)}`, `useMonthBoard(year, month)` (`staleTime: 0`), factory `createMockMonthBoard`, handler MSW do board. `bill.schema.ts` já expõe `amount_is_estimated`.
- **S72/S73 (FE)**: página de contas cadastradas e extrato — não são tocadas aqui.

> **Se S66/S71 não estiverem concluídas, PARE.** Esta sessão consome o endpoint e o hook; não os cria.

---

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/finances/bills/_components/overdue-section.tsx` — `OverdueSection` (Card "Atrasadas" + sub-seção "Dívida adiada/suspensa"), recebe `overdue: Bill[]`, `deferredSuspended: Bill[]`, `columns` e `overdueTotal` por props.
- `frontend/app/(dashboard)/finances/bills/_components/generate-missing-banner.tsx` — `GenerateMissingBanner` (banner acionável quando `missingCount > 0`).
- `frontend/app/(dashboard)/finances/bills/_components/__tests__/overdue-section.test.tsx`
- `frontend/app/(dashboard)/finances/bills/_components/__tests__/generate-missing-banner.test.tsx`
- `frontend/app/(dashboard)/finances/bills/__tests__/bills-page-board.test.tsx` — página inteira sobre o board (MSW).

### Arquivos a modificar
- `frontend/app/(dashboard)/finances/bills/page.tsx` — trocar `useBills`+`useMemo` por `useMonthBoard(period.year, period.month)`; montar seções/banner/totais; remover o select de competência; manter MonthNavigator, select de situação, `IptuRiskBanner`, modais e AlertDialog de exclusão.
- `frontend/app/(dashboard)/finances/bills/_components/bill-columns.tsx` — badges "valor estimado"/"aguardando fatura" na célula Descrição.
- `frontend/tests/mocks/handlers.ts` / `tests/mocks/data/finances.ts` — só se os testes precisarem de handler/ajuste de factory que a S71 não criou.

### NÃO fazer (pertence a outras sessões)
- **Nenhum popover** (pagar na linha, editar inline), **"+ Conta avulsa"**, **"Importar fatura" na linha**, **CTA "Parcelar"** — são a **S75**. As ações de linha existentes (dropdown com Editar/Pagar→dialog/lifecycle/Excluir) permanecem como estão nesta sessão.
- **Preflight do fechamento / toasts acionáveis com link** — **S76**. Aqui o 400 de mês fechado no banner usa `handleError` + `toast.error` com a mensagem do backend (sem link).
- **Nenhum backend**; **nada da Fase 2** (terceiros — design §7); **não** estender `DataTable` (sem `onRowClick`); **não** tocar outras páginas que usam `useBills` (o hook continua existindo para elas).
- **Não** reusar a annotation `is_overdue` para montar a seção Atrasadas — a lista `overdue` vem pronta do backend (critério próprio do board).

---

## Especificação

> Camadas FE (`frontend/CLAUDE.md` + `.claude/rules/architecture.md`): página consome hooks; componentes apresentacionais sem `apiClient`. Texto ao usuário em PT; moeda via `formatCurrency`; datas DD/MM/YYYY sem `new Date(iso)` (padrão split de `bill-columns.tsx:19-31`). Named exports, kebab-case, `import type`.

### `page.tsx` — fonte única `useMonthBoard`

- `const { data: board, isLoading } = useMonthBoard(period.year, period.month);` — **remover** `useBills`, `competenceMode`, `competenceMonthParam`, o `useMemo` de grupos (:99-114) e o select "Competência" (:242-253). O board é sempre 1 mês (MonthNavigator) + Atrasadas cross-competência sempre à vista — o modo "Todas as competências" deixa de existir nesta página (design §3.3: fonte de dados única).
- **Filtro de situação permanece** (select :254-266), agora client-side sobre as seções: o valor filtra `bill.lifecycle_state` dentro de cada seção; **remover a opção "Canceladas"** (CANCELED nunca vem do board — design §2); "Todas as situações" = sem filtro. Com filtro `active`, a sub-seção adiada/suspensa fica vazia (ocultar seções vazias).
- **Faixa de totais do mês** (acima das seções): `A pagar {formatCurrency(totals.due)} · Pago {totals.paid} · Restante {totals.remaining} · Atrasado {totals.overdue}` — valores verbatim do payload (nunca recalcular no front). Nota: o schema da S71 mantém `totals` como **STRINGS decimais** (`z.string()`, verbatim do backend) — NÃO passa por `moneyField`/number; `formatCurrency` aceita string. Ajustar qualquer teste/tipagem que assuma number nos totals.
- **Ordem visual**: PageHeader → IptuRiskBanner → `GenerateMissingBanner` → MonthNavigator + filtro situação → totais → `OverdueSection` → Accordion por prédio.
- **Accordion**: espelhar :274-301, iterando `board.groups` (key = `String(building_id ?? 'condominio')`, label = `building_label`, contador de contas). Ordem = a do backend (não reordenar).
- Empty state quando `groups`, `overdue` e `deferred_suspended` vierem vazios (texto atual "Nenhuma conta cadastrada" serve).
- Modais existentes (`BillFormModal` create/edit/draft, `BillPaymentDialog`, AlertDialog de exclusão) e `buildBillColumns` continuam ligados como hoje (:118-135, :303-344).

### `OverdueSection` (novo)

- `Card` **não-colapsável**, título "Atrasadas" + `Badge` com contagem + total `formatCurrency(overdueTotal)`; corpo = `DataTable` com as MESMAS colunas do corpo + coluna extra "Atraso" com badge de dias: `daysLate(due_date)` — helper puro que constrói `new Date(y, m-1, d)` a partir do split (nunca `new Date(iso)`) e diff com hoje; exibir "N dia(s)" ou "N mês(es)" quando ≥ 60 dias.
- Sub-seção "Dívida adiada/suspensa" (dentro do mesmo Card, abaixo, com heading próprio): `DataTable` das `deferredSuspended` + `Badge` de estado por linha ("Suspensa"/"Adiada" — de `lifecycle_state`), com texto auxiliar PT deixando claro que esses valores **não entram nos totais do mês**. (O CTA "Parcelar" desta sub-seção é a S75 — não criar aqui.)
- Seção some (`return null`) quando ambas as listas estiverem vazias.

### `GenerateMissingBanner` (novo)

- Props: `missingCount: number`, `year`, `month`. Renderiza `null` quando `missingCount === 0`. Quando > 0: `Alert` com texto "Há {N} conta(s) recorrente(s) sem fatura gerada em {mês/ano}" + botão "Gerar contas faltantes ({N})" que chama **`useGenerateMonthBills`** (`use-bills.ts:212-224`) com `{year, month}`.
- Sucesso: `toast.success` com `result.created` + o board refaz fetch (o hook já invalida caches; garantir que a invalidação da S71 cobre `monthBoard` — se não cobrir, é bug da S71: reportar, não contornar aqui).
- Erro (inclui 400 de mês fechado): `handleError(error, 'Erro ao gerar contas do mês')` — mensagem PT do backend no toast. O link acionável para o fechamento é **S76**.
- Renderizado apenas para admin (`isAdmin`).

### Badges nas colunas (`bill-columns.tsx`)

Na célula **Descrição** (:47-53), após o texto:
- `amount_is_estimated === true` e `(amount_total ?? 0) > 0` → `<Badge variant="outline">valor estimado</Badge>`;
- `amount_is_estimated === true` e `(amount_total ?? 0) === 0` → `<Badge variant="outline">aguardando fatura</Badge>` (conta gerada sem linha — nunca se confunde com paga; design §3.3).
- Comparação numérica (`moneyField` já converteu para number). Bills confirmadas: sem badge.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: HTTP via **MSW** (`server.use` + factories) — **NUNCA `vi.mock`** de hooks/módulos internos. `renderWithProviders`/`waitForQueriesToSettle` de `@/tests/test-utils`; `setAdmin` via `useAuthStore.setState` (padrão `bills-page-import.test.tsx:50-55`).

### 1. RED — escrever os testes primeiro

#### `__tests__/bills-page-board.test.tsx`
```ts
describe('BillsPage — month board structure', () => {
  it('renders the page from month_board and never calls the bills list endpoint', ...)
  // handler GET month_board responde createMockMonthBoard; handler GET /finances/bills/ registra
  // chamadas num array → assert 0 chamadas (useBills saiu da página).
  it('renders one accordion group per backend group, in backend order, with bill rows', ...)
  // groups com 2 prédios + bucket "Condomínio" → 3 AccordionItems na ordem do payload.
  it('renders the Atrasadas card above the accordion with cross-competence bills and a days-late badge', ...)
  // overdue com bill de competência de 2 meses atrás → aparece no Card fixo com badge de atraso.
  it('renders the deferred/suspended sub-section with state badges and keeps it out of month totals', ...)
  // deferred_suspended com 1 suspensa → badge "Suspensa"; totais exibidos = totals do payload verbatim.
  it('renders the month totals strip from the payload without recomputing', ...)
  // totals {due:'100.00', paid:'40.00', remaining:'60.00', overdue:'25.00'} → 4 valores formatados.
  it('shows the generate banner when missing_count > 0 and hides it when 0', ...)
  it('clicking "Gerar contas faltantes (N)" posts to generate_month and refetches the board', ...)
  // spy MSW no POST generate_month; após sucesso o GET month_board é chamado de novo (2ª resposta).
  it('shows the backend PT message on a 400 closed-month error from generate_month', ...)
  // handler 400 {detail:'Competência 06/2026 está fechada.'} → toast com a mensagem (sem link — S76).
  it('keeps the situação filter working client-side and drops the "Canceladas" option', ...)
  // filtro "Suspensas" → corpo/atrasadas vazios, sub-seção mostra só suspensas; option Canceladas ausente.
  it('removes the competence-mode select ("Todas as competências")', ...)
  it('hides the generate banner and admin actions for non-admin users', ...)
  it('shows the empty state when the board has no bills at all', ...)
});
```

#### `__tests__/overdue-section.test.tsx`
```ts
describe('OverdueSection', () => {
  it('returns null when both lists are empty', ...)
  it('shows count badge and formatted overdue total in the card header', ...)
  it('formats days late from due_date without new Date(iso) (timezone-safe)', ...)
  it('renders "N mês(es)" when the delay is 60 days or more', ...)
  it('labels suspended and deferred rows with their state badge', ...)
});
```

#### `__tests__/generate-missing-banner.test.tsx`
```ts
describe('GenerateMissingBanner', () => {
  it('renders null when missingCount is 0', ...)
  it('renders the count in the message and button label', ...)
  it('disables the button while the mutation is pending', ...)
});
```

#### `bill-columns` (badges) — adicionar ao teste existente das colunas (ou criar `__tests__/bill-columns.test.tsx` se não houver)
```ts
it('shows "valor estimado" badge when amount_is_estimated with a non-zero total', ...)
it('shows "aguardando fatura" badge when amount_is_estimated with amount_total 0', ...)
it('shows no estimate badge on confirmed bills', ...)
```

> Rodar (devem **falhar**): `cd frontend && npx vitest run "app/(dashboard)/finances/bills"`

### 2. GREEN — implementar
1. `bill-columns.tsx` — badges.
2. `overdue-section.tsx` + `generate-missing-banner.tsx`.
3. `page.tsx` — reescrita sobre `useMonthBoard` (remoções + montagem das seções).
4. Handlers/factories MSW só se faltarem (S71 deve ter criado `createMockMonthBoard` + handler).

### 3. REFACTOR
- `daysLate` como função pura exportada do componente (testável direto).
- Colunas: uma única chamada a `buildBillColumns` reusada pelas 3 tabelas (DRY).
- Zero código morto: apagar `competenceMode`/`competenceMonthParam`/`useMemo` e imports órfãos (`useBills`, `useMemo` se não usado).

### 4. VERIFY — gate
```bash
cd frontend
npx vitest run "app/(dashboard)/finances/bills"        # sessão + regressão irmã (import/página)
npm run lint && npm run type-check && npm run test:unit
```
> Regressão obrigatória: `bills-page.test.tsx` e `bills-page-import.test.tsx` existentes devem ser **atualizados** para o board (a página não chama mais a lista de bills) — adaptá-los é parte desta sessão, sem afrouxar o que testam (import de fatura, admin/non-admin).

---

## Constraints

- **Fonte única**: proibido chamar `useBills` nesta página; proibido reagrupar/reordenar/re-somar no front — `groups`/`totals`/`overdue` são verbatim do payload S66.
- **Sem optimistic update** em mutação de dinheiro: `generate_month` → invalidate → refetch (o hook existente já faz).
- **MSW only**: nenhum `vi.mock` de hooks internos; factories raw (`z.input`, dinheiro string `'350.00'`).
- **Timezone**: nunca `new Date('YYYY-MM-DD')` — sempre split (padrão `bill-columns.tsx:19-31`).
- **Não estender `DataTable`**; não tocar `useBills`/consumidores externos; `IptuRiskBanner`, modais e dropdown de ações permanecem.
- **Sem suppressions** (`eslint-disable`/`@ts-ignore`/`as`/`!` em produção); `import type`; named exports; strings de UI em PT.
- O que este prompt disser diferente dos contratos S66/S71/S74 do `SESSION_STATE.md` → **os contratos prevalecem**.

## Critérios de Aceite (binários)

- [ ] `page.tsx` consome exclusivamente `useMonthBoard(year, month)`; `useBills`, `page_size=10000`, `useMemo` de agrupamento e o select "Todas as competências" removidos da página; MonthNavigator (:214-241) e filtro de situação mantidos (sem opção "Canceladas").
- [ ] Card "Atrasadas" fixo, não-colapsável, ACIMA do Accordion, com bills cross-competência, badge de dias/meses de atraso e total da seção.
- [ ] Sub-seção "Dívida adiada/suspensa" com badges de estado, fora dos totais, com texto explicativo; some quando vazia.
- [ ] Corpo Accordion iterando `board.groups` na ordem do backend, bucket "Condomínio" incluído.
- [ ] `GenerateMissingBanner` aparece só com `missing_count > 0` (admin), chama `useGenerateMonthBills`, refetch do board no sucesso, 400 de mês fechado exibe a mensagem PT do backend (sem link — S76).
- [ ] Badges "valor estimado" (`amount_is_estimated` e total > 0) e "aguardando fatura" (`amount_is_estimated` e total === 0, comparação numérica) na coluna Descrição.
- [ ] Faixa de totais do mês renderiza `totals` verbatim (4 valores).
- [ ] Todos os testes nomeados no TDD implementados e verdes; testes irmãos existentes adaptados sem perder cobertura; MSW only.
- [ ] `cd frontend && npm run lint && npm run type-check && npm run test:unit` — **zero erros e zero warnings**; sem suppressions.
- [ ] Nenhum popover/conta avulsa/importar-na-linha/CTA Parcelar (S75); nenhum preflight/toast com link (S76); nenhum backend tocado.

## Handoff

1. Rodar e confirmar o gate acima verde.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`): linha da S74 → **concluída**; arquivos criados/modificados; nota: "Cockpit estrutura sobre `useMonthBoard` — seções Atrasadas/dívida, banner faltantes, badges de estimativa, totais verbatim; `useBills`/agrupamento client-side/competence-mode removidos da página; filtro de situação client-side sem 'Canceladas'".
3. Contratos p/ S75/S76 (verbatim): `OverdueSection({overdue, deferredSuspended, columns, overdueTotal})` é o ponto onde a S75 pluga o CTA "Parcelar"; `GenerateMissingBanner` é o call-site que a S76 troca por toast acionável; `buildBillColumns` segue sendo o builder único das 3 tabelas.
4. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
5. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 74 — cockpit estrutura sobre month_board (atrasadas, dívida, banner, badges)
   ```
6. Próxima sessão: **75 — interações do cockpit** (popover pagar c/ ajuste, editar inline, conta avulsa, importar na linha, CTA Parcelar).
