# Sessão 81 — Frontend: índice de terceiros, extrato e acerto

**Fase 2 (terceiros) — sessão 5 de 6.** Frontend. Sem backend.

Design: `@docs/plans/2026-07-27-condo-third-party-payments-design.md` §8.

Depende de: S80 (API pronta e estável).

## Contexto

- **Design (ler §8)**: `@docs/plans/2026-07-27-condo-third-party-payments-design.md`
- **Contratos autoritativos da API**: bloco das sessões 77–82 em `@prompts/SESSION_STATE.md`. Se este prompt divergir da API real entregue pela S80, **a API real prevalece** — ajustar os tipos a ela e registrar a divergência (precedente: S50).
- **Regras**: `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `.claude/rules/architecture.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Rota `[id]` (único precedente)** | `frontend/app/(dashboard)/finances/accounts/[id]/page.tsx` | `useParams()`, loading, id inválido/404 — copiar a estrutura inteira |
| **Página CRUD + modal** | `frontend/app/(dashboard)/finances/categories/page.tsx` | `useCrudPage`, `DataTable`, `PageHeader`, gate `is_staff`, empty state PT |
| **`StatCard`** | `frontend/components/ui/stat-card.tsx` (`label/value/icon/tone/subLabel/loading`) | Os 3 cards do extrato |
| **Hook de leitura + query keys** | `frontend/lib/api/hooks/use-account-statement.ts` + `lib/api/query-keys.ts` | Forma do hook e onde registrar a chave |
| **Schema Zod dual (com a armadilha já corrigida)** | `frontend/lib/schemas/finances/installment-plan.schema.ts:45-55` (`superRefine` que aceita **objeto nested OU `_id`**) | O bug real: exigir só o `_id` write-only estoura no parse de leitura e **esvazia a lista inteira**. Copiar esta forma |
| **Sidebar longest-match** | `frontend/components/layouts/sidebar.tsx` (`isRouteCandidate`/`resolveActiveKey`) + `__tests__/sidebar.test.tsx:118-154` | Testes de subrota já existentes — espelhar para `/finances/third-party/7` |
| **Datas sem `new Date(iso)`** | `frontend/lib/utils/formatters.ts` (`competenceMonthLabel`, `dueDateLabel`, `formatCurrency`) — uso em `bills/_components/bill-columns.tsx:14` | Helpers compartilhados; `new Date(iso)` desloca o dia por fuso. **Reusar, não recriar** |
| **MSW factories/handlers** | `frontend/tests/mocks/data/finances.ts` + `tests/mocks/handlers.ts` | Onde registrar mock data e rotas |

## Arquivos

- **Criar**: `lib/schemas/finances/third-party.schema.ts`, `lib/api/hooks/use-third-party.ts`
- **Criar**: `app/(dashboard)/finances/third-party/page.tsx` + `_components/` (cards, modal de acerto)
- **Criar**: `app/(dashboard)/finances/third-party/[id]/page.tsx` + `_components/` (statcards, tabela mês a mês)
- **Modificar**: `lib/api/query-keys.ts`, `lib/utils/constants.ts`, `components/layouts/sidebar.tsx`
- **Criar**: testes MSW (handlers + mock data) e testes de componente

## Escopo

### 1. Camada de dados

`useThirdPartyPeople()`, `useThirdPartyStatement(personId)`, `useThirdPartySettlements()`, `useCreateSettlement()`, `useDeleteSettlement()`.

- Query keys em `finances.thirdParty.*`, ao lado de `ownerDistribution`
- Zod com **padrão dual** (nested read / `_id` write). **Armadilha registrada** (`project_parcelas_empty_zod_bug`): `superRefine` exigindo `_id` write-only quebra o parse na leitura e esvazia a lista — aceitar objeto nested **ou** `_id`
- Decimal-string → `Number` **só no boundary** (`toNumber`/`formatCurrency`); nunca aritmética em string
- Mutação de acerto **invalida** `statement` e `people` (senão o extrato fica velho)

### 2. Índice `/finances/third-party`

- Card por pessoa: nome, **devido em aberto** (destaque), atrasado (tom de alerta se > 0), data do último acerto
- Botão "Registrar acerto" → modal (pessoa, data default hoje, valor, método, observação)
- Célula-link para o extrato — o `DataTable` (`frontend/components/tables/data-table.tsx`, props em `:56-72`) **não tem `onRowClick`** e **não deve ser estendido** aqui
- Empty state PT: "Nenhuma dívida com terceiros"
- Ações de escrita **só para admin** (`user?.is_staff`), como nas outras telas

### 3. Extrato `/finances/third-party/[id]`

Precedente de rota `[id]` já existe (`finances/accounts/[id]`, criada na S73) — **seguir esse arquivo**, incluindo loading e 404.

- `StatCard`s: em aberto / atrasado / crédito
- Tabela mês a mês: mês, devido, aplicado, resto, badge de status
- Badge por status com cor e rótulo PT: `paid` "Quitado" / `overdue` "Atrasado" / `partially_paid` "Parcial" / `open` "Em aberto" / `credit` "Crédito"
- Detalhe expansível por mês: os `items` (pagamentos e compras) que compõem o devido
- **Nunca recalcular** no frontend — todos os números vêm do backend (mesma disciplina da S50: "lidos do backend, nunca recalculados")

### 4. Navegação

`FINANCES_THIRD_PARTY` em `constants.ts` + entrada "Terceiros" no grupo **Condomínio** do `sidebar.tsx`.

**Atenção (achado real da S73):** o sidebar resolve item ativo por **longest-match** (`isRouteCandidate`/`resolveActiveKey`). Conferir que `/finances/third-party/7` ativa "Terceiros" e não outro item. Teste obrigatório para a subrota.

## TDD

- **MSW é a única fronteira mockada.** Proibido `vi.mock` de hook interno (norma da casa, P6.1)
- Handlers + `createMockThirdPartyStatement` / `createMockThirdPartyPeople` em `tests/mocks/`
- Testes: renderiza cards; empty state; extrato renderiza os 5 status; expansível mostra itens; modal de acerto envia payload correto; erro da API vira toast PT; não-admin não vê ações de escrita; sidebar ativo em `/finances/third-party` e na subrota `[id]`

## NÃO fazer

- **Não** tocar backend.
- **Não** mexer no cockpit `/finances/bills` (S82).
- **Não** estender `DataTable` com `onRowClick`.
- **Não** usar `as` ou `!` em código de produção.

## Aceite

- `npm run test:unit` verde (escopo + suíte completa sem regressão)
- `npm run lint` + `npm run type-check` zerados
- `npm run build` exit 0 (**gate que nenhuma sessão da Fase 1 rodou até a revisão final — rodar aqui**)
- Zero `eslint-disable`/`@ts-ignore`
