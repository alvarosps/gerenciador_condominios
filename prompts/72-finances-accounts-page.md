# Sessão 72 — Frontend: página "Contas cadastradas" (`/finances/accounts`) — CRUD de `BillingAccount` + navegação

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida — `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (rev. 2, §3.2)
> **Sessões da feature**: 65 → 66 → 67 → 68 → 69 → 70 → 71 → **72** ∥ 73 → 74 → 75 → 76
> Esta sessão entrega o **cadastro de contas** que hoje não existe (design §1: "não há página para gerir o registro"): página CRUD `useCrudPage` + tabela com filtros prédio/tipo + colunas com badge "Cortada" e **saldo devedor** (`open_balance`, S67/S71) + modal RHF+Zod + rota/sidebar. A **célula-link** do nome leva ao extrato (`/finances/accounts/{id}`, página da S73 — o link nasce aqui mesmo que a rota só exista na S73, elas podem rodar em paralelo no mesmo branch).

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.2 página de contas, §1 diagnóstico, §10 gate de arquitetura)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Contratos AUTORITATIVOS** (S67 `open_balance`, S71 data layer, S72 esta sessão): `@prompts/SESSION_STATE.md` seção "Cockpit operacional de contas". Se este prompt divergir, **eles prevalecem**.
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Esqueleto de página CRUD** | `frontend/app/(dashboard)/finances/categories/page.tsx:20-142` (`useCrudPage` + `PageHeader` + colunas + `DataTable` + modal + `DeleteConfirmDialog`, gating `isAdmin` :22/:68/:105) | Esqueleto DIRETO desta página — copiar a estrutura, trocar entidade |
| **Filtros locais server-side** | `frontend/app/(dashboard)/finances/bills/page.tsx:64-86` (estado de filtro → objeto `filters` → hook) + Selects :242-266 | Padrão dos filtros prédio/tipo (estado local + `useBillingAccounts(filters)`; sem URL state) |
| **Builder de colunas** | `frontend/app/(dashboard)/finances/bills/_components/bill-columns.tsx:40-136` (`buildBillColumns({isAdmin, on…})`, helpers de data :19-31, `ACCOUNT_TYPE_LABELS` :62, dropdown de ações :97-133) | Padrão de `account-columns.tsx` (`buildAccountColumns`) |
| **Modal RHF+Zod (form schema local)** | `frontend/app/(dashboard)/finances/categories/_components/finance-category-form-modal.tsx:48-120` (form schema + DEFAULTS + reset no edit + mutateAsync + toasts PT) e o padrão `_id` write em `bill-form-modal.tsx:107-146` (defaults com `building_id`/`category_id` a partir do nested) | `account-form-modal.tsx`: read nested (`building`), write `_id` (dual pattern) |
| **Hooks de billing-accounts** | `frontend/lib/api/hooks/use-billing-accounts.ts:12-16` (`BillingAccountFilters` — **hoje SEM `account_type`**; esta sessão adiciona), `:23-36` list, `:56-92` create/update/delete | O backend já filtra `?account_type=` (S56, `finances/viewsets/crud_views.py`) — só falta o campo no filtro do hook |
| **Schema + labels** | `frontend/lib/schemas/finances/billing-account.schema.ts:20-48` (campos, `open_balance` opcional pós-S71) + `ACCOUNT_TYPE_LABELS`/`accountLabel` :51-70 (fonte única — NÃO duplicar mapa de labels) | Colunas/filtro/modal usam `ACCOUNT_TYPE_LABELS` |
| **DataTable (SEM onRowClick)** | `frontend/components/tables/data-table.tsx:36-49` (`Column<T>`) + :56-72 (props) | NÃO existe `onRowClick` e **não deve ganhar** — navegação por célula-link (`<Link>` do next dentro do `render`) |
| **Rotas + sidebar** | `frontend/lib/utils/constants.ts:75-84` (bloco Condomínio) + `frontend/components/layouts/sidebar.tsx:67-77` (`condominioChildren`) + :143-145/:197 (ativo por **igualdade exata** de pathname) | `FINANCES_ACCOUNTS` + entrada "Contas cadastradas" após "Contas". A igualdade exata basta para ESTA rota; o caso subrota `[id]` é tratado na **S73** |
| **Teste de sidebar** | `frontend/components/layouts/__tests__/sidebar.test.tsx:95-107` (auto-expand do grupo dono da rota ativa) | Adicionar cenário análogo para `/finances/accounts` |
| **Teste de página (MSW + auth real)** | `frontend/app/(dashboard)/finances/bills/__tests__/bills-page.test.tsx:1-60` (`setAdmin` via `useAuthStore.setState`, `server.use` para respostas, captura de params) | Espelho dos testes desta sessão |
| **MSW billing-accounts** | `frontend/tests/mocks/handlers.ts:2251-2285` (CRUD completo já existe) + factory `createMockBillingAccount` (`tests/mocks/data/finances.ts:68`, com `open_balance` pós-S71) | Nenhum handler novo deve ser necessário; `server.use` por teste para listas específicas |

### Pré-requisito (se faltar, PARE)

**S71 concluída**: `open_balance` opcional no `billingAccountSchema`, factories/handlers atualizados. Esta sessão **não** cria schema/hook de fetch — só consome (e estende o filtro).

---

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/finances/accounts/page.tsx` — página CRUD.
- `frontend/app/(dashboard)/finances/accounts/_components/account-columns.tsx` — `buildAccountColumns`.
- `frontend/app/(dashboard)/finances/accounts/_components/account-form-modal.tsx` — `AccountFormModal`.
- `frontend/app/(dashboard)/finances/accounts/__tests__/accounts-page.test.tsx`
- `frontend/app/(dashboard)/finances/accounts/_components/__tests__/account-form-modal.test.tsx`

### Arquivos a modificar
- `frontend/lib/utils/constants.ts` — `FINANCES_ACCOUNTS: '/finances/accounts'` no bloco Condomínio (`:75-84`).
- `frontend/components/layouts/sidebar.tsx` — `{ key: ROUTES.FINANCES_ACCOUNTS, label: 'Contas cadastradas' }` em `condominioChildren`, imediatamente após `FINANCES_BILLS` (`:67-77`).
- `frontend/components/layouts/__tests__/sidebar.test.tsx` — cenário do item novo ativo/auto-expand.
- `frontend/lib/api/hooks/use-billing-accounts.ts` — `BillingAccountFilters` ganha `account_type?: string` (`:12-16`; o filtro já existe no backend desde a S56).

### NÃO fazer (pertence a outras sessões)
- **Página de extrato `[id]`** — S73 (o `<Link href>` aponta para lá; só o link nasce aqui).
- **Cockpit** (`/finances/bills`) — S74/S75; não tocar em `bills/page.tsx` nem em `bill-columns.tsx`.
- **NÃO adicionar `onRowClick` ao `DataTable`** — decisão explícita do design (§3.2).
- **Nenhum backend**; nada da Fase 2; sem export xlsx/csv (não pedido — YAGNI).

---

## Especificação

> Texto de UI em **PT**; `formatCurrency` (`lib/utils/formatters.ts`); erros via `handleError`/`getErrorMessage`; camadas FE conforme `.claude/rules/architecture.md`.

### `page.tsx`

- `'use client'`; `useAuthStore` → `isAdmin = user?.is_staff ?? false`.
- Filtros locais (padrão `bills/page.tsx:64-86`): `buildingFilter` (Select com `useBuildings()`, opção "Todos os prédios" + "Condomínio"? **não** — só "Todos os prédios" + lista; conta sem prédio aparece em "Todos") e `typeFilter` (Select com `ACCOUNT_TYPE_LABELS`, opção "Todos os tipos"). Aplicados server-side: `useBillingAccounts({ building_id, account_type })` (campos omitidos quando "all").
- `useCrudPage<BillingAccount>({ entityName: 'conta cadastrada', entityNamePlural: 'contas cadastradas', deleteMutation: useDeleteBillingAccount(), deleteErrorMessage: 'Erro ao excluir conta. Verifique se não há faturas vinculadas.' })`.
- `PageHeader` title "Contas cadastradas", description "Registro das contas do condomínio (água, luz, IPTU, internet…)", action `isAdmin && <Button>Nova Conta Cadastrada</Button>`.
- Empty state: `Nenhuma conta cadastrada` (mesmo padrão `categories/page.tsx:114-117`).
- `DataTable<BillingAccount>` + `AccountFormModal` + `DeleteConfirmDialog` (nome do item = `account.name`).

### `account-columns.tsx` — `buildAccountColumns({ isAdmin, onEdit, onDelete }): Column<BillingAccount>[]`

| Coluna | Conteúdo |
|--------|----------|
| Nome | **célula-link**: `<Link href={`/finances/accounts/${id}`} className="text-primary underline-offset-4 hover:underline">{name}</Link>` (id `undefined` ⇒ texto puro); `primary: true`, sorter por nome |
| Prédio | `building ? building.name : 'Condomínio'` (padrão `bill-columns.tsx:57`) |
| Tipo | `ACCOUNT_TYPE_LABELS[account_type]` |
| Inscrição/UC | `external_identifier` ou `—` |
| Relógio/Imóvel | `secondary_identifier` ou `—` |
| Dia venc. | `default_due_day` |
| Valor esperado | `formatCurrency(expected_amount)` |
| Estado | `Badge` sobre o enum REAL `BillingAccountState` (4 valores): `active` → "Ativa" (secondary), `suspended` → "Suspensa", `deferred` → "Adiada", `ended` → "Encerrada" (outline). NAO existe `closed` no backend. |
| Fornecimento | `supply_status === 'cut'` → `Badge` destructive **"Cortada"**; senão `—` (o estado normal não ganha badge — sinal só onde há problema) |
| Saldo devedor | `open_balance === undefined ? '—' : formatCurrency(open_balance)`; quando `> 0`, `className="text-destructive font-medium"` |
| Ações (só `isAdmin`) | Dropdown Editar/Excluir (padrão `bill-columns.tsx:97-133`; sem ações de ciclo de vida aqui) |

### `account-form-modal.tsx` — `AccountFormModal({ open, account, onClose })`

- Form schema Zod **local** (padrão `finance-category-form-modal.tsx:48-62`), write no **dual pattern** (`_id`):
  - `name` (min 1, "Nome é obrigatório"), `building_id: number|null`, `category_id: number|null`, `account_type` (enum, default `generic`), `external_identifier`, `secondary_identifier`, `holder_name`, `registered_address` (strings, default `''`), `default_due_day` (int 1–31), `expected_amount` (number ≥ 0), `lifecycle_state` (`active|suspended|deferred|ended` — enum real `billingAccountStateEnum`), `supply_status` (`active|cut`), `tracking_start_month: string|null`, `end_date: string|null`, `description` (`Textarea` — o model `finances/models.py:174` e o schema expõem o campo; sem este input nenhuma UI o preencheria), `notes`.
- Selects: prédio (`useBuildings`, opção "Condomínio (sem prédio)" = null), categoria (`useFinanceCategories`, opção "Nenhuma" = null), tipo (`ACCOUNT_TYPE_LABELS`), estado, fornecimento. `Input type="date"` para `tracking_start_month` (enviar `YYYY-MM-01`) e `end_date`.
- **Validação espelho do backend (S56)**: `superRefine` — `external_identifier` em branco com `account_type` ∈ {water, electricity, iptu} ⇒ erro PT "Inscrição/UC é obrigatória para contas de água, luz e IPTU" (o backend rejeita; falhar cedo no form).
- Edit: `useEffect` reset a partir de `account` (nested → `_id`: `building_id: account.building_id ?? account.building?.id ?? null`, padrão `bill-form-modal.tsx:129-135`). Create: DEFAULTS.
- Submit: `useCreateBillingAccount`/`useUpdateBillingAccount` (payload plano com `building_id`/`category_id`); toasts "Conta cadastrada com sucesso"/"Conta atualizada com sucesso"; erro → `toast.error('Erro ao salvar conta')` + `handleError`.
- **Não** enviar `open_balance` (annotation read-only) nem objetos nested no write.

### Navegação

- `constants.ts`: `FINANCES_ACCOUNTS: '/finances/accounts'`.
- `sidebar.tsx`: entrada "Contas cadastradas" após "Contas" em `condominioChildren`. A lógica de ativo (`pathname === child.key`, `:143-145`) cobre a rota exata — **não** alterar o matching aqui (a subrota `[id]` é responsabilidade da S73).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> Mock policy: HTTP via **MSW** (handlers de billing-accounts já existem; `server.use` para cenários). **NUNCA** `vi.mock` de hooks internos. Auth real via `useAuthStore.setState` (`bills-page.test.tsx:30-36`).

### 1. RED

#### `accounts-page.test.tsx`
```ts
describe('AccountsPage', () => {
  it('lista as contas com nome, tipo (label PT), prédio e saldo devedor formatado', async () => {});
  // server.use com 2 createMockBillingAccount (uma com open_balance '412.50') → vê "R$ 412,50".
  it('renderiza badge "Cortada" apenas para supply_status=cut', async () => {});
  it('exibe "—" no saldo devedor quando open_balance ausente (payload antigo)', async () => {});
  it('a célula do nome é um link para /finances/accounts/{id}', async () => {});
  // getByRole('link', {name}) com href="/finances/accounts/1" — DataTable segue SEM onRowClick.
  it('filtra por tipo enviando account_type na query', async () => {});
  // captura searchParams do GET billing-accounts (padrão captureBillsParams de bills-page.test.tsx:56-60).
  it('filtra por prédio enviando building_id na query', async () => {});
  it('esconde "Nova Conta Cadastrada" e a coluna Ações para non-admin', async () => {});
  it('admin cria conta pelo modal e a lista invalida/refetcha', async () => {});
  // fluxo real: abrir modal, preencher mínimo, submit → POST MSW → toast sucesso.
  it('admin exclui conta via DeleteConfirmDialog', async () => {});
  it('mostra empty state PT quando a lista vem vazia', async () => {});
});
```

#### `account-form-modal.test.tsx`
```ts
describe('AccountFormModal', () => {
  it('cria com payload dual-pattern: building_id/category_id planos, sem objetos nested nem open_balance', async () => {});
  // handler captura o body do POST e asserta as chaves.
  it('preenche o Textarea de description e envia o valor no payload', async () => {});
  it('rejeita external_identifier vazio para water/electricity/iptu com mensagem PT', async () => {});
  it('aceita external_identifier vazio para generic/internet', async () => {});
  it('edição pré-preenche a partir do nested (building.id → building_id) e faz PUT com id', async () => {});
  it('valida default_due_day fora de 1–31', async () => {});
  it('erro 400 do backend mantém o modal aberto e mostra toast de erro', async () => {});
});
```

#### `sidebar.test.tsx` (cenários novos)
```ts
it('renderiza "Contas cadastradas" no grupo Condomínio e marca ativo em /finances/accounts', () => {});
// vi.mocked(usePathname).mockReturnValue('/finances/accounts') → grupo auto-expandido (padrão :95-100).
```

> Rodar (devem **falhar**):
> ```bash
> cd frontend
> npx vitest run "app/(dashboard)/finances/accounts" "components/layouts/__tests__/sidebar.test.tsx"
> ```

### 2. GREEN — implementar
1. `constants.ts` + `sidebar.tsx` (+ teste do sidebar verde).
2. `use-billing-accounts.ts` (`account_type` no filtro).
3. `account-columns.tsx` → `account-form-modal.tsx` → `page.tsx`.

### 3. REFACTOR
- Labels de tipo/estado/fornecimento: **uma** fonte (`ACCOUNT_TYPE_LABELS` já existe; estado/fornecimento como `Record` local no `account-columns.tsx`, reusado pelo modal via export nomeado se necessário — sem duplicar literais).
- Helpers puros extraídos se a célula ficar densa (ex.: `openBalanceCell(account)`).

### 4. VERIFY — gate
```bash
cd frontend
npx vitest run "app/(dashboard)/finances/accounts" "components/layouts/__tests__/sidebar.test.tsx"
npx vitest run "lib/api/hooks/__tests__/use-billing-accounts.test.tsx"   # regressão do hook tocado
npm run lint && npm run type-check && npm run test:unit
```

---

## Constraints

- **`DataTable` intocado** — sem `onRowClick`, sem prop nova; navegação SÓ por `<Link>` na célula (design §3.2).
- **Dual pattern** no write (`building_id`/`category_id`); read usa nested. `open_balance` é read-only — nunca no payload.
- **`useCrudPage` obrigatório** (padrão do projeto) — modal/delete por ele; filtros e mutations na página (a assinatura `use-crud-page.ts:156-167` não cobre filtros).
- **Filtros server-side** via `useBillingAccounts(filters)` — sem filtrar client-side a lista.
- **Rota/label**: `FINANCES_ACCOUNTS: '/finances/accounts'`, label "Contas cadastradas" — a página `/finances/bills` continua "Contas" (vira cockpit na S74; não renomear nada dela aqui).
- **Não alterar o matching de rota ativa do sidebar** (igualdade exata) — subrota é S73.
- Sem suppressions; `import type`; named exports; kebab-case; strings de UI em PT; TypeScript strict + `noUncheckedIndexedAccess` (acessos indexados sempre guardados).
- **Não mexer**: cockpit (S74/S75), extrato (S73), backend, Fase 2.

## Critérios de Aceite (binários)

- [ ] `/finances/accounts` lista contas com as 10 colunas do design §3.2 (nome-link, prédio, tipo, inscrição/UC, relógio/imóvel, dia venc., valor esperado, estado, fornecimento "Cortada", saldo devedor) + Ações para admin.
- [ ] `open_balance` ausente → `—` (lista não quebra); presente e > 0 → valor em destaque destructive.
- [ ] Filtros prédio/tipo aplicados server-side (`building_id`/`account_type` capturados na query em teste).
- [ ] `AccountFormModal` cria/edita no dual pattern; espelha a regra de identificador obrigatório p/ água/luz/IPTU; toasts PT.
- [ ] Non-admin: sem botão de criar, sem coluna Ações (leitura permitida).
- [ ] `FINANCES_ACCOUNTS` em `ROUTES`; "Contas cadastradas" no grupo Condomínio após "Contas"; teste de sidebar verde.
- [ ] `BillingAccountFilters.account_type?` adicionado; testes existentes de `use-billing-accounts` intactos.
- [ ] `DataTable` sem nenhuma mudança de API; nenhum arquivo do cockpit/extrato tocado.
- [ ] Todos os cenários da seção TDD verdes; `cd frontend && npm run lint && npm run type-check && npm run test:unit` — zero erros/warnings; zero suppressions.

## Handoff

1. Confirmar o gate verde.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (linha S72 → **concluída**; criados/modificados; nota: "página de cadastro no ar; célula-link aponta para `/finances/accounts/{id}` — rota entregue pela S73; `account_type` adicionado ao filtro do hook").
3. Rodar `/audit` contra os Critérios de Aceite e corrigir gaps.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 72 — página Contas cadastradas (CRUD BillingAccount + saldo devedor + navegação)

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. Próxima sessão: **73 — extrato `/finances/accounts/[id]`** (pode já ter rodado em paralelo; senão, é a próxima).
