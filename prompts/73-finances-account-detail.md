# Sessão 73 — Frontend: extrato por conta (`/finances/accounts/[id]`) — PRIMEIRA rota dinâmica do dashboard + `consolidate-debt-dialog`

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida — `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (rev. 2, §3.4 e §3.5)
> **Sessões da feature**: 65 → 66 → 67 → 68 → 69 → 70 → 71 → 72 ∥ **73** → 74 → 75 → 76
> Esta sessão entrega o **extrato da conta** (destino da célula-link da S72): página `[id]` — **primeiro precedente de rota dinâmica no dashboard** (não há NENHUM `[param]` fora do proxy `app/api/[...route]`) — com 3 StatCards (saldo devedor, faturas em aberto, atraso médio "~N dias"), tabela mês a mês, planos vinculados com `Progress` (N/M) e o **`consolidate-debt-dialog`** ("Parcelar saldo devedor", S70), que a S75 reutiliza no cockpit. Inclui o ajuste do sidebar para subrota ativa.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.4 extrato, §3.5 consolidação, §8 erros, §10 gate)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Contratos AUTORITATIVOS** (S67 payload do statement, S70 body do consolidate, S71 hooks, S73 esta sessão): `@prompts/SESSION_STATE.md` seção "Cockpit operacional de contas". Se este prompt divergir, **eles prevalecem**.
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Página client densa** | `frontend/app/(dashboard)/finances/bills/page.tsx:60-123` (`'use client'`, auth, hooks, estado local) | Estrutura base; aqui soma-se `useParams()` de `next/navigation` (primeiro uso no dashboard — NÃO existe exemplar interno, seguir a doc do App Router: `const { id } = useParams<{ id: string }>()`) |
| **`StatCard`** | `frontend/components/ui/stat-card.tsx:8-16` (props `label/value/icon/tone/subLabel/loading`) | Os 3 cards do topo (tone `destructive` p/ saldo > 0; `loading` do próprio componente durante fetch) |
| **`Progress`** | `frontend/components/ui/progress.tsx:8-28` (Radix, `value` 0–100) | Barra de progresso dos planos (`materialized_count/installment_count`) |
| **Colunas + helpers de data** | `frontend/app/(dashboard)/finances/bills/_components/bill-columns.tsx:19-31` (`competenceLabel`/`dueDateLabel` via split — NUNCA `new Date(iso)`) | Reusar os MESMOS helpers (extrair para util compartilhado se import cross-página incomodar — ver convenção abaixo) |
| **Dialog de ação (não-CRUD)** | `frontend/app/(dashboard)/finances/bills/_components/bill-payment-dialog.tsx:49-119` (form schema local, `todayISO`, mutate com toasts/handleError, reset no open) | Esqueleto do `consolidate-debt-dialog.tsx` |
| **Import cross-página de `_components` (convenção JÁ existente)** | `frontend/app/(dashboard)/_components/finance-calendar/combined-calendar-section.tsx:20` (importa `bills/_components/bill-payment-dialog`) e `bill-columns.tsx:16` (importa `_components` do dashboard) | Autoriza o dialog viver em `accounts/[id]/_components/` e ser importado pelo cockpit na S75 (contrato S73) |
| **Hooks da S71** | `frontend/lib/api/hooks/use-account-statement.ts` (`useAccountStatement(id)`, `enabled`, `staleTime: 0`) + `use-billing-accounts.ts` (`useConsolidateDebt`) + schemas `account-statement.schema.ts` | Esta sessão SÓ consome — nenhum hook/schema novo |
| **Sidebar — ativo por igualdade exata** | `frontend/components/layouts/sidebar.tsx:143-145` (`isChildActive` = `pathname === child.key`) + :197 (`isActive`) + teste `__tests__/sidebar.test.tsx:95-107` | **Confirmado no código**: em `/finances/accounts/7` o grupo Condomínio COLAPSA hoje. Esta sessão muda o matching para longest-match (ver Especificação) |
| **Empty state PT** | `frontend/app/(dashboard)/finances/categories/page.tsx:114-117` | Padrão dos estados id-inválido/404 |
| **Factory + handler do statement (S71)** | `frontend/tests/mocks/data/finances.ts` (`createMockAccountStatement`) + `tests/mocks/handlers.ts` (GET `billing-accounts/:id/statement/` registrado antes de `:id/`) | Base dos testes; `server.use` para variações |

### Pré-requisitos (se faltar, PARE)

- **S71 concluída**: `useAccountStatement`/`useConsolidateDebt`/schemas/factories/handlers.
- **S72 concluída OU em paralelo no mesmo branch**: `FINANCES_ACCOUNTS` em `ROUTES` e entrada no sidebar (se a S72 ainda não rodou, PARE — o ajuste de subrota desta sessão pressupõe o item no menu).

---

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/finances/accounts/[id]/page.tsx` — página do extrato.
- `frontend/app/(dashboard)/finances/accounts/[id]/_components/consolidate-debt-dialog.tsx` — `ConsolidateDebtDialog` (reutilizável pela S75).
- `frontend/app/(dashboard)/finances/accounts/[id]/__tests__/account-detail-page.test.tsx`
- `frontend/app/(dashboard)/finances/accounts/[id]/_components/__tests__/consolidate-debt-dialog.test.tsx`

### Arquivos a modificar
- `frontend/components/layouts/sidebar.tsx` — matching de item ativo passa a cobrir subrotas (ver Especificação).
- `frontend/components/layouts/__tests__/sidebar.test.tsx` — cenário: em `/finances/accounts/7`, "Contas cadastradas" ativo + grupo expandido.

### NÃO fazer (pertence a outras sessões)
- **Cockpit** (`/finances/bills`) — S74/S75. O CTA "Parcelar" da sub-seção de dívida do cockpit é **S75** (ela importa o dialog daqui).
- **Nenhum hook/schema novo** — data layer é S71 (se faltar algo, é bug da S71: reporte, não contorne).
- **Nenhum backend**; nada da Fase 2; sem breadcrumbs/rotas dinâmicas extras (só esta).

---

## Especificação

> Texto de UI em **PT**; `formatCurrency`; datas DD/MM/YYYY via helpers de split (nunca `new Date(iso)`); erros via `handleError`/`getErrorMessage`.

### `[id]/page.tsx` — primeiro `[id]` do dashboard

- `'use client'`. `const params = useParams<{ id: string }>()`; `const accountId = Number(params.id)`.
- **Guard de id inválido** (`!Number.isInteger(accountId) || accountId <= 0`): renderizar empty state PT — "Conta não encontrada" + `<Link href={ROUTES.FINANCES_ACCOUNTS}>Voltar para Contas cadastradas</Link>`. **Nunca** lançar/quebrar (sem tela branca/500) e **não** chamar o hook com id lixo: `useAccountStatement(isValidId ? accountId : null)` (o hook da S71 tem `enabled`).
- **Estados**: `isLoading` → 3 `StatCard loading` + `Loading`/skeleton da tabela; **erro/404** → mesmo empty state "Conta não encontrada" + link Voltar (o backend responde 404 p/ conta inexistente/deletada — S67).
- `PageHeader`: title `statement.account.name`, description "Extrato da conta — histórico mês a mês e saldo devedor", action `isAdmin && <Button>Parcelar saldo devedor</Button>` (desabilitado quando não há bill consolidável — ver dialog).
- **3 StatCards** (grid responsivo `sm:grid-cols-3`):
  1. "Saldo devedor" — `formatCurrency(Number(stats.open_balance))`; `tone="destructive"` se > 0, senão `"success"`.
  2. "Faturas em aberto" — `stats.open_bills_count`.
  3. "Atraso médio" — `stats.avg_delay_days === null ? '—' : `~${stats.avg_delay_days} dias`` (exibição literal "~N dias"; subLabel "últimas 12 faturas quitadas").
- Badges de contexto junto ao header: tipo (`ACCOUNT_TYPE_LABELS`), `supply_status === 'cut'` → Badge destructive "Cortada", `lifecycle_state === 'closed'` → "Encerrada".
- **Tabela mês a mês** (`DataTable<StatementMonthRow>` sobre `statement.months`, `rowKey="bill_id"`): Competência (`competenceLabel`), Vencimento (`dueDateLabel`), Descrição, Total / Pago / Resto (`formatCurrency`), Status (Badge PT por `payment_status`: open→"Em aberto", partial→"Parcial", paid→"Paga" — **não** usar `BillStatusChip`, que exige `is_overdue` e o statement não o traz), Estado (badge PT por `lifecycle_state`; active sem badge), badge "valor estimado" quando `amount_is_estimated`, Data pgto. (`paid_date` DD/MM/YYYY ou `—`).
- **Planos vinculados** (`statement.plans`, seção abaixo da tabela; vazia → não renderiza): card por plano com descrição, badge "Embutido"/"Avulso" (`embedded`), estado, `Progress value={(materialized_count / installment_count) * 100}` (guardar divisão por zero) e label "Parcela {materialized_count}/{installment_count}".
- Botão "Parcelar saldo devedor" abre o `ConsolidateDebtDialog` com as rows consolidáveis.

### Sidebar — subrota ativa (longest-match)

Trocar o matching exato por **longest-match** em `sidebar.tsx`. ATENÇÃO: prefixo puro NÃO basta — há rotas que SÃO prefixo de rotas irmãs: `/financial` é a key do child "Dashboard" e é prefixo de 13 rotas irmãs (`/financial/expenses`, `/financial/incomes`…); com `startsWith` simples, "Dashboard" acenderia junto de "Despesas".

- Regra: entre os children cujo `key` casa com `pathname === key || pathname.startsWith(key + '/')`, **apenas o de key MAIS LONGA fica ativo** (os demais candidatos ficam inativos).
- Aplicar em `isChildActive` (`:143-145`), no `isActive` dos filhos (`:197`) e nos itens raiz (`:219`).
- Cenários que a regra cobre: em `/financial/expenses`, o child ativo é "Despesas", NÃO "Dashboard" (`/financial`); em `/finances/accounts/123`, o ativo é "Contas cadastradas"; `/finances/bills` nunca acende em subrotas de accounts.

### `consolidate-debt-dialog.tsx` — `ConsolidateDebtDialog` (design §3.5, contrato S70)

**Reutilizável pela S75** (cockpit importa daqui — convenção de import cross-página já existe, ver exemplares). Por isso as props recebem dados prontos, sem acoplar ao `useAccountStatement`:

```ts
export interface ConsolidableBill {
  bill_id: number;
  description: string;
  competence_month: string; // YYYY-MM-01
  due_date: string;
  amount_remaining: number; // RESTO (parciais contam o resto — S70)
}
export interface ConsolidateDebtDialogProps {
  open: boolean;
  onClose: () => void;
  accountId: number;
  accountType: BillingAccountType; // embedded só p/ consumo (water/electricity/internet)
  bills: ConsolidableBill[];       // já filtradas: amount_remaining > 0 e lifecycle_state ≠ canceled
}
```

- A página monta `bills` a partir de `statement.months` (filtro acima); a S75 montará a partir do `month_board`.
- **Multi-select**: checkbox por bill (competência + vencimento + descrição + `formatCurrency(resto)`); "Selecionar todas"; rodapé com **total do plano** = `formatCurrency(Σ amount_remaining selecionadas)` (display; o backend recalcula — fonte da verdade é o serviço S70).
- **Campos do plano** (RHF + Zod local, padrão `bill-payment-dialog.tsx:49-61`): `embedded: boolean` (Select "Embutido na conta"/"Plano avulso" — **desabilitado em "Plano avulso" fixo** quando `accountType` não é consumo, com hint PT "Parcelamento embutido só para contas de consumo"); `installment_count` (int ≥ 2 — decisão de UX deliberada: o backend/S70 aceita 1, mas parcelar em 1x não faz sentido na UI; NÃO "corrigir" para ≥ 1); `start_due_date` (date, default hoje); `default_due_day` (int 1–31, default dia do `start_due_date`).
- Submit (≥ 1 bill selecionada, senão erro PT "Selecione ao menos uma fatura"): `useConsolidateDebt().mutate({ account_id: accountId, bill_ids, embedded, installment_count, start_due_date, default_due_day })` → sucesso: toast "Saldo devedor parcelado — plano criado" + `onClose()` (invalidations vêm do hook S71 — não repetir aqui); erro 400 (competência fechada etc.) → `handleError(error, 'Erro ao parcelar saldo devedor')` mantendo o dialog aberto (mensagem PT do backend visível).
- Aviso fixo no corpo (Alert): "As faturas selecionadas serão canceladas e a dívida passará a viver apenas no plano." (§3.5 — origens canceladas na mesma transação).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> Mock policy: HTTP via **MSW** (`server.use` com o handler de `statement`/`consolidate_debt` da S71). **NUNCA** `vi.mock` de `useAccountStatement`/`useConsolidateDebt`/`apiClient`. `useParams` é fronteira do framework: mockar `next/navigation` como o `sidebar.test.tsx` já faz com `usePathname`.

### 1. RED

#### `account-detail-page.test.tsx`
```ts
describe('AccountDetailPage', () => {
  it('renderiza os 3 StatCards com saldo devedor formatado, faturas em aberto e atraso médio "~N dias"', async () => {});
  // server.use com createMockAccountStatement({stats: {open_balance: '412.50', open_bills_count: 2, avg_delay_days: 6}}) → "R$ 412,50", "2", "~6 dias".
  it('mostra "—" no atraso médio quando avg_delay_days é null', async () => {});
  it('lista as linhas mês a mês com competência, vencimento, total/pago/resto e data de pagamento', async () => {});
  it('exibe badge "valor estimado" só na linha com amount_is_estimated=true', async () => {});
  it('renderiza planos vinculados com progresso "Parcela N/M" e badge Embutido/Avulso', async () => {});
  it('id inválido (ex.: "abc") mostra empty state PT com link Voltar, sem chamar a API', async () => {});
  // useParams mockado com {id:'abc'}; spy MSW confirma zero requests ao statement.
  it('404 do backend mostra o mesmo empty state "Conta não encontrada"', async () => {});
  it('esconde "Parcelar saldo devedor" para non-admin', async () => {});
  it('admin abre o dialog de consolidação apenas com as bills consolidáveis (resto>0, não-canceladas)', async () => {});
});
```

#### `consolidate-debt-dialog.test.tsx`
```ts
describe('ConsolidateDebtDialog', () => {
  it('lista as bills com resto formatado e atualiza o total do plano conforme a seleção', async () => {});
  it('posta o body do contrato S70 (bill_ids selecionadas, embedded, installment_count, start_due_date, default_due_day)', async () => {});
  // handler MSW captura o body em billing-accounts/:id/consolidate_debt/ e responde 201.
  it('bloqueia submit sem seleção com mensagem PT', async () => {});
  it('trava embedded em "Plano avulso" quando accountType é iptu/generic (hint PT visível)', async () => {});
  it('permite escolher Embutido para conta de consumo (water)', async () => {});
  it('erro 400 do backend mantém o dialog aberto e exibe a mensagem via handleError', async () => {});
  it('sucesso fecha o dialog e dispara toast de plano criado', async () => {});
});
```

#### `sidebar.test.tsx` (cenário novo)
```ts
it('mantém "Contas cadastradas" ativo e o grupo expandido na subrota /finances/accounts/7', () => {});
// usePathname → '/finances/accounts/7'; item ativo; '/finances/bills' NÃO ativo.
it('em /financial/expenses ativa "Despesas" e NÃO "Dashboard" (/financial é prefixo — longest-match)', () => {});
// usePathname → '/financial/expenses'; e em '/finances/accounts/123' o ativo é "Contas cadastradas".
```

> Rodar (devem **falhar**):
> ```bash
> cd frontend
> npx vitest run "app/(dashboard)/finances/accounts/[id]" "components/layouts/__tests__/sidebar.test.tsx"
> ```

### 2. GREEN — implementar
1. `sidebar.tsx` (`isRouteActive`) + teste verde.
2. `consolidate-debt-dialog.tsx` (componente isolado primeiro — testável sem a página).
3. `[id]/page.tsx` (guard → estados → StatCards → tabela → planos → dialog).

### 3. REFACTOR
- `competenceLabel`/`dueDateLabel`: se importar de `bills/_components/bill-columns.tsx` criar acoplamento estranho, extrair para `lib/utils/formatters.ts` e atualizar **todos** os consumidores (refatoração completa — sem duplicar os helpers).
- Mapa de labels de `payment_status`/`lifecycle_state` como `Record` const único no arquivo de colunas da página.
- Funções puras para as derivações (`consolidableBills(months)`, `planProgress(plan)`).

### 4. VERIFY — gate
```bash
cd frontend
npx vitest run "app/(dashboard)/finances/accounts" "components/layouts/__tests__/sidebar.test.tsx"
npx vitest run "app/(dashboard)/finances/bills"   # regressão se bill-columns/formatters foram tocados
npm run lint && npm run type-check && npm run test:unit
```

---

## Constraints

- **Primeiro `[id]` do dashboard**: `'use client'` + `useParams()`; **sem** `generateStaticParams`/server component/`params` como prop async — o dashboard inteiro é client-side e este padrão vira o precedente.
- **Guard antes do fetch**: id inválido nunca chama a API nem lança; 404 = empty state PT (design §3.4 "orçar loading/404").
- **Atraso médio**: exibição literal "~N dias" (contrato S73); `null` → `—`. NUNCA recalcular no front — o número vem pronto (`stats.avg_delay_days`).
- **Dinheiro**: sempre `formatCurrency`; totais do dialog são display — o backend é a fonte (`total = Σ amount_remaining` recalculado no serviço S70).
- **Dialog desacoplado**: props `ConsolidableBill[]`/`accountId`/`accountType` — S75 reutiliza SEM tocar no arquivo; não importar `useAccountStatement` dentro do dialog.
- **Sidebar**: matching por **longest-match** (candidato = `pathname === key || pathname.startsWith(key + '/')`; só a key mais longa ativa) — prefixo puro dá falso-positivo porque `/financial` é prefixo de 13 rotas irmãs.
- **Invalidations só no hook S71** — o dialog não chama `invalidateQueries` direto.
- Sem suppressions; `import type`; named exports (página usa `export default` — exigência do App Router, única exceção); kebab-case; UI em PT; TypeScript strict + `noUncheckedIndexedAccess`.
- **Não mexer**: cockpit (S74/S75), data layer (S71), backend, Fase 2.

## Critérios de Aceite (binários)

- [ ] `/finances/accounts/{id}` renderiza header + badges (tipo/Cortada/Encerrada) + 3 StatCards (saldo devedor com tone condicional, faturas em aberto, atraso médio "~N dias" ou "—").
- [ ] Tabela mês a mês completa (competência, vencimento, descrição, total, pago, resto, status, estado, badge "valor estimado", data pgto.) via `statement.months`.
- [ ] Planos vinculados com `Progress` + "Parcela N/M" + badge Embutido/Avulso; seção oculta sem planos.
- [ ] Id inválido e 404 → empty state PT "Conta não encontrada" + link Voltar; zero chamadas de API no id inválido; nenhum crash.
- [ ] `ConsolidateDebtDialog`: multi-select com total dinâmico, campos do plano, regra de `embedded` por tipo, body S70 exato capturado em teste, erro 400 mantém aberto, sucesso fecha com toast.
- [ ] Dialog importável de fora (named export + props desacopladas) — pronto para a S75.
- [ ] Sidebar ativa "Contas cadastradas" na subrota `[id]` (longest-match), sem ativar rotas irmãs; em `/financial/expenses` o ativo é "Despesas", não "Dashboard"; testes antigos do sidebar intactos.
- [ ] Todos os cenários da seção TDD verdes; `cd frontend && npm run lint && npm run type-check && npm run test:unit` — zero erros/warnings; zero suppressions.

## Handoff

1. Confirmar o gate verde.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (linha S73 → **concluída**; criados/modificados; nota: "primeiro `[id]` do dashboard estabelecido (`'use client'`+`useParams`+guard+empty-state 404); `ConsolidateDebtDialog` em `accounts/[id]/_components/` com props desacopladas (`ConsolidableBill[]`) — S75 importa daqui; sidebar com matching de subrota por longest-match").
3. Rodar `/audit` contra os Critérios de Aceite e corrigir gaps.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 73 — extrato da conta (/finances/accounts/[id]) + consolidate-debt-dialog

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. Próxima sessão: **74 — cockpit estrutura** (`month_board`, seções Atrasadas/adiada-suspensa, banner de faltantes, badges).
