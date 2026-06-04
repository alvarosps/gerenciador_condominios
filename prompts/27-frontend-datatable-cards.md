# Sessão 27 — Frontend: DataTable responsivo (cards no mobile via container queries)

> Parte da feature "App Mobile Completo — Responsividade + PWA + Offline + Web Push" (Frente A, §4.1 do
> design doc). Esta sessão torna o `DataTable` compartilhado responsivo: **tabela** em containers largos,
> **cards empilhados** em containers estreitos, via **container queries** do Tailwind v4 (sem JS, SSR-safe).
> Como o `DataTable` é o único componente de tabela do app, isto conserta **todas** as listas de uma vez.
> Depende da Sessão 26 (que adicionou `size: 'touch'` ao `Button`); **não** altera a assinatura pública
> do `DataTable` — `tenants`/`leases` continuam passando exatamente as mesmas colunas.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro; foco em §2 Stack real, §3 Decisões, §4.1 DataTable responsivo, §4.3 Testes):
  `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares/TDD): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar Sessão 26 concluída — `Button` já tem `size: 'touch'`)
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`,
  `.claude/rules/design-principles.md`, `.claude/rules/architecture.md`

### Exemplares (arquivo:linha — abrir e seguir)
- **Componente alvo (ler inteiro)**: `frontend/components/tables/data-table.tsx:1-374`. Pontos exatos:
  - `interface Column<T>` a estender: `:23-34` (acrescentar 3 campos opcionais; **não** remover/renomear nada).
  - `getCellValue` inline (resolvedor de caminho pontilhado) a **extrair**: `:138-153`.
  - Wrapper externo `<div className="space-y-4">`: `:225`; wrapper da tabela `<div className="rounded-md border overflow-x-auto">`: `:226`.
  - Ramo de render de célula (lógica de fallback de valor a reusar no card): `:308-315`.
  - Paginação (já responsiva, `flex flex-col sm:flex-row` — **não** mexer): `:324-371`.
  - `getRowKey`: `:95-103`; estado de loading: `:209-222`.
- **Colunas reais que viram card** (verificar contra a especificação): `frontend/app/(dashboard)/tenants/page.tsx:165-334`:
  - 1ª coluna "Nome / Razão Social" (`:166-180`) → candidata natural a `primary` (título do card).
  - Coluna "Ações" (`:282-333`, `key: 'actions'`, `fixed: 'right'`) → candidata a `isActions` (rodapé do card).
  - As colunas com `render` (badges, botões "Ver"/"Trocar"/"Editar") provam que **o card deve usar `column.render`**, não o valor cru.
- **Consumidor a não regredir** (mesmas colunas, dois `DataTable`): `frontend/app/(dashboard)/tenants/page.tsx:497-528`
  e `frontend/app/(dashboard)/leases/page.tsx:466`.
- **`Button` `size: 'touch'`** (criado na S26; usar no rodapé do card): `frontend/components/ui/button.tsx:23-28`.
- **Tailwind v4 nativo** (container queries disponíveis sem plugin): `frontend/app/globals.css:1` (`@import "tailwindcss"`).
  → as variantes `@container`, `@md:block`, `@md:hidden` funcionam sem configuração extra.
- **Render de testes (providers)**: `frontend/tests/test-utils.tsx:55-64` (`renderWithProviders`).
- **Mocks globais do ambiente de teste** (jsdom não implementa container queries — ver Constraints/TDD):
  `frontend/tests/setup.ts:21-34` (`matchMedia` mockado).

### Contrato cross-session (NÃO divergir — nomes verbatim)
Estes símbolos são consumidos/produzidos por outras sessões da mesma feature; usar **exatamente** estes nomes:
- `Column<T>` ganha **três campos opcionais e retrocompatíveis**: `primary?: boolean`, `hideOnCard?: boolean`, `isActions?: boolean`.
- `frontend/components/tables/cell-value.ts` exporta `resolveCellValue<T>(record: T, column: Column<T>): unknown`.
- `frontend/components/tables/data-table-cards.tsx` exporta `DataTableCards<T extends object>`.
- Classes de container query: wrapper externo `@container`; ramo tabela `hidden @md:block`; ramo cards `@md:hidden`.

## Escopo

### Arquivos a criar
- `frontend/components/tables/cell-value.ts`
- `frontend/components/tables/data-table-cards.tsx`
- `frontend/components/tables/__tests__/cell-value.test.ts`
- `frontend/components/tables/__tests__/data-table-cards.test.tsx`
- `frontend/components/tables/__tests__/data-table.test.tsx`

### Arquivos a modificar
- `frontend/components/tables/data-table.tsx` — (1) estender `Column<T>` com `primary?`/`hideOnCard?`/`isActions?`;
  (2) **remover** o `getCellValue` inline e importar `resolveCellValue` de `./cell-value`; (3) envolver o conteúdo
  retornado num `<div className="@container">`, dar `hidden @md:block` ao wrapper da tabela e renderizar
  `<DataTableCards … className="@md:hidden" />` ao lado. Paginação **inalterada**.

> **Não** tocar em `tenants/page.tsx` nem em `leases/page.tsx` (a assinatura pública do `DataTable` não muda; os
> consumidores não passam os novos campos opcionais — eles caem nos defaults). Adotar `primary`/`isActions` nas
> colunas reais é polish opcional **fora desta sessão**.

## Especificação

### 1. `cell-value.ts` — `resolveCellValue` (DRY)
Mover a lógica de `data-table.tsx:138-153` para uma função pura, genérica e sem estado:
```ts
import type { Column } from './data-table';

export function resolveCellValue<T>(record: T, column: Column<T>): unknown {
  // se !column.dataIndex → undefined
  // split de String(column.dataIndex) por '.'; navega o objeto guardando typeof === 'object' && key in value
  // qualquer salto inválido → undefined
}
```
- Comportamento **idêntico** ao atual (incluindo caminhos pontilhados `'a.b.c'` e ausência de `dataIndex`).
- `data-table.tsx` passa a `import { resolveCellValue } from './cell-value'` e usa-o no lugar de `getCellValue`
  (o `getCellValue` inline é **apagado**, sem alias/shim — DRY, sem re-export).

### 2. `Column<T>` (em `data-table.tsx:23-34`) — 3 campos opcionais
Acrescentar **ao final** da interface, sem alterar os existentes:
```ts
  primary?: boolean;     // coluna vira o título do card
  hideOnCard?: boolean;  // omite a coluna no card
  isActions?: boolean;   // renderiza no rodapé do card (botões full-width)
```
Por serem opcionais, todas as colunas atuais permanecem válidas (retrocompatível).

### 3. `data-table-cards.tsx` — `DataTableCards<T>`
```ts
interface DataTableCardsProps<T extends object> {
  columns: Column<T>[];
  data: T[];
  rowKey: (record: T, index: number) => string;
  className?: string;
}

export function DataTableCards<T extends object>({ columns, data, rowKey, className }: DataTableCardsProps<T>): React.ReactElement;
```
Regras de montagem do card (para cada `record`, `index`):
- **Título**: valor renderizado da coluna com `primary === true`; *fallback* = primeira coluna **não** `isActions`.
  - O conteúdo do título usa o mesmo critério de render de célula: `column.render(value, record, index)` quando há
    `render`, senão o valor resolvido por `resolveCellValue` (mesma lógica de fallback de `data-table.tsx:308-315`).
- **Corpo**: para cada coluna que **não** é a `primary`, **não** é `isActions` e **não** tem `hideOnCard === true`,
  renderizar uma linha `rótulo: valor` — `rótulo = column.title`; `valor` = render da célula (mesmo critério acima).
- **Rodapé**: colunas com `isActions === true` (pode haver 0 ou 1; suportar ≥1) vão para o rodapé do card; cada
  ação ocupa a largura total (touch-friendly). O conteúdo é `column.render(undefined, record, index)`.
- Empty state: quando `data` vazio, exibir "Nenhum dado disponível" (mesmo texto do ramo tabela, `data-table.tsx:287`).
- `key` de cada card = `rowKey(record, index)`. Aplicar `className` recebido no contêiner da lista (será `@md:hidden`).
- **Importações**: `resolveCellValue` de `./cell-value`; `type Column` de `./data-table` (via `import type`); sem
  duplicar a lógica de resolução de valor (DRY). Componente puro: **sem** hooks de dados, **sem** `apiClient`.

> Botões de ação grandes no card: as ações vêm prontas via `column.render` (que já devolve `<Button>`); o card só
> precisa garantir o **layout full-width** no rodapé (ex.: `flex flex-col gap-2` com filhos `w-full` ou wrapper que
> estica). **Não** instanciar `<Button>` aqui só para teste de `size`; o `size: 'touch'` (S26) é adotado pelos
> consumidores quando migrarem suas colunas — esta sessão garante a **estrutura** de rodapé, não recria botões.

### 4. `data-table.tsx` — alternância tabela/cards por CSS
No `return` final (atualmente `data-table.tsx:224-373`), envolver tudo num contexto de container e renderizar os
dois ramos no **mesmo** componente:
```tsx
return (
  <div className="@container space-y-4">
    <div className="rounded-md border overflow-x-auto hidden @md:block">
      {/* <Table> … exatamente como hoje (linhas 227-321) */}
    </div>
    <DataTableCards
      columns={columns}
      data={paginatedData}
      rowKey={getRowKey}
      className="@md:hidden"
    />
    {/* paginação inalterada — data-table.tsx:324-371 */}
  </div>
);
```
- `getRowKey` (já existente, `:95-103`) é reusado para a `key` dos cards — **não** duplicar.
- A paginação fatia `paginatedData`; os cards exibem **o mesmo** `paginatedData` (consistência tabela/cards).
- O estado de `loading` (`:209-222`) e o `rowSelection` (checkboxes) **permanecem** no ramo tabela; cards **não**
  recebem `rowSelection` nesta sessão (seleção em massa fica no desktop — YAGNI no mobile).

## TDD

Rodar **somente os arquivos de teste desta sessão** + os testes de página de `tenants`/`leases` (regressão). A suíte
completa tem problemas pré-existentes de xdist/Redis — **não** rodá-la inteira.

### 1. Red — escrever os testes primeiro (devem falhar: arquivos/símbolos inexistentes)
Comando: `cd frontend && npx vitest run "components/tables/__tests__"`

Cobrir, no mínimo:

**`cell-value.test.ts`** (função pura — sem render)
- `dataIndex` simples (`'name'`) → retorna o valor do campo.
- Caminho pontilhado (`'apartment.building.street_number'`) sobre objeto aninhado → retorna o valor folha.
- Caminho com salto inexistente no meio → retorna `undefined` (não lança).
- Coluna **sem** `dataIndex` (ex.: coluna só com `render`) → retorna `undefined`.
- Paridade: para uma coluna `dataIndex: 'name'`, `resolveCellValue` devolve o mesmo que o acesso direto `record.name`.

**`data-table-cards.test.tsx`** (render via testing-library, `renderWithProviders`)
- **Título via `primary`**: marcando uma coluna `primary`, o título do card mostra o valor renderizado dessa coluna.
- **Fallback de título**: sem nenhuma coluna `primary`, o título usa a **primeira coluna não-`isActions`**.
- **Corpo `rótulo: valor`**: para uma coluna normal, o card mostra `column.title` (rótulo) e o valor renderizado.
- **`hideOnCard`**: uma coluna marcada `hideOnCard` **não** aparece no card (asserir ausência do rótulo dela).
- **`render` respeitado**: uma coluna com `render` que devolve um marcador específico (ex.: `<span>BADGE-X</span>`)
  exibe esse marcador no card (prova que o card usa `render`, não o valor cru).
- **`isActions` no rodapé**: uma coluna `isActions` cujo `render` devolve um botão com texto "Editar" aparece;
  e (asserção estrutural) o botão de ação fica num contêiner de rodapé distinto das linhas de corpo (verificar via
  `data-testid`/estrutura, não por cor) e ocupa largura total (classe `w-full` ou wrapper esticado).
- **Empty state**: `data={[]}` → exibe "Nenhum dado disponível".
- **`rowKey`**: dois registros distintos produzem dois cards (sem warning de key duplicada).

**`data-table.test.tsx`** (render via testing-library — testa a alternância e a não-regressão de API)
- Renderiza **ambos** os ramos no DOM: o wrapper da tabela com classes `hidden @md:block` **e** o contêiner de cards
  com `@md:hidden` (em jsdom, container queries não computam; asserir pela **presença das classes utilitárias**
  e da estrutura, conforme §4.3 do design — não pela visibilidade efetiva).
- O wrapper externo tem a classe `@container`.
- A tabela renderiza as linhas com os mesmos dados de antes (uma asserção de conteúdo de célula via `render`).
- Os cards renderizam os mesmos dados (uma asserção de conteúdo de card).
- **Retrocompatibilidade**: passar `columns` **sem** nenhum dos novos campos (`primary`/`hideOnCard`/`isActions`)
  funciona — título cai no fallback (1ª coluna) e nenhuma coluna é tratada como ação.
- Paginação ainda presente quando há dados (asserir os controles de página — `data-table.tsx:344-368`).

### 2. Green — implementar `cell-value.ts`, `data-table-cards.tsx` e refatorar `data-table.tsx` (mínimo p/ passar)

### 3. Refactor — extrair sub-render do card se houver duplicação entre título/corpo (helper local `renderCellContent(column, record, index)` único, reusando `resolveCellValue`); sem comentários supérfluos; funções pequenas

### 4. Verify
- `cd frontend && npx vitest run "components/tables/__tests__"` → tudo verde.
- **Regressão dos consumidores** (mesmas colunas, devem continuar verdes):
  `cd frontend && npx vitest run "app/(dashboard)/tenants" "app/(dashboard)/leases"` → sem falhas novas.
- `cd frontend && npx tsc --noEmit` → sem erros nos arquivos tocados.
- `cd frontend && npx eslint "components/tables"` → zero erros/avisos.

## Constraints (NÃO fazer)

- **NÃO** alterar a assinatura pública de `DataTable` (`DataTableProps`) — `dataSource`/`columns`/`pagination`/
  `rowKey`/`rowSelection`/sort permanecem idênticos; os 3 novos campos de `Column<T>` são **opcionais**.
- **NÃO** tocar em `tenants/page.tsx` nem `leases/page.tsx` (nem outros consumidores) — adotar os novos campos é fora de escopo.
- **NÃO** duplicar a lógica de resolução de valor: `resolveCellValue` é a **única** fonte; o `getCellValue` inline é
  removido por completo (sem shim/alias/re-export). DRY.
- **NÃO** usar medição por JS (ResizeObserver/`matchMedia`/`useState` de largura) para alternar tabela↔cards — a troca
  é **100% CSS** (container queries do Tailwind v4), evitando risco de hidratação e mantendo SSR-safe.
- **NÃO** instalar dependência nova (container queries do Tailwind v4 são nativas — `globals.css:1`).
- **NÃO** mockar componentes internos, ORM, biblioteca ou TanStack Query. O `DataTable`/`DataTableCards` são puros
  (props in) — testar com fixtures de `Column<T>`/`data` reais; o único "boundary" é o ambiente jsdom (que não computa
  container queries) — por isso asserir **classes utilitárias e estrutura**, não visibilidade efetiva (design §4.3).
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`; em código de produção, **sem** `as`/`!` — corrigir o tipo na
  raiz (`import type`, `??`, null guards; respeitar `noUncheckedIndexedAccess`). Usar `import type` para tipos.
- **NÃO** criar barrel/re-export em `components/tables/` — cada módulo exporta só o que define; consumidores importam da fonte.
- **NÃO** rodar a suíte completa de testes (apenas os arquivos desta sessão + páginas tenants/leases) — evitar falhas
  pré-existentes de xdist/Redis.
- SOLID/DRY/KISS/YAGNI — `DataTableCards` com responsabilidade única (montar cards), `DataTable` continua focado;
  sem código especulativo (sem `rowSelection` no card, sem prop de "modo" manual).

## Critérios de Aceite

- [ ] `frontend/components/tables/cell-value.ts` exporta `resolveCellValue<T>(record, column): unknown` com comportamento idêntico ao antigo `getCellValue` (caminhos pontilhados + ausência de `dataIndex`).
- [ ] `data-table.tsx` **importa** `resolveCellValue` e **não** contém mais o `getCellValue` inline (grep limpo).
- [ ] `Column<T>` tem `primary?`, `hideOnCard?`, `isActions?` (opcionais) e os campos existentes intactos.
- [ ] `data-table-cards.tsx` exporta `DataTableCards<T extends object>` com props `{ columns, data, rowKey, className? }`.
- [ ] Card: título = coluna `primary` (fallback 1ª não-`isActions`); corpo = linhas `rótulo: valor` respeitando `hideOnCard`; ações `isActions` no rodapé full-width; usa `column.render` quando presente.
- [ ] `DataTable` envolve o conteúdo em `<div className="@container …">`; wrapper da tabela com `hidden @md:block`; `DataTableCards` com `@md:hidden`. Paginação inalterada.
- [ ] Assinatura pública de `DataTable` inalterada; `tenants`/`leases` **não** modificados.
- [ ] `npx vitest run "components/tables/__tests__"` 100% verde (cell-value + cards + alternância/retrocompat).
- [ ] Regressão: `npx vitest run "app/(dashboard)/tenants" "app/(dashboard)/leases"` sem falhas novas.
- [ ] `npx tsc --noEmit` sem erros nos arquivos tocados; `eslint "components/tables"` zero erros/avisos.
- [ ] Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem re-export/barrel; sem dependência nova.

## Handoff

1. Rodar e confirmar verde (colar a saída como evidência):
   - `cd frontend && npx vitest run "components/tables/__tests__"`
   - `cd frontend && npx vitest run "app/(dashboard)/tenants" "app/(dashboard)/leases"`
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "components/tables"`
2. Atualizar `prompts/SESSION_STATE.md`: marcar Sessão 27 concluída; registrar os símbolos do contrato
   (`Column<T>` + `primary`/`hideOnCard`/`isActions`, `resolveCellValue`, `DataTableCards`, classes `@container`/
   `hidden @md:block`/`@md:hidden`) para as próximas sessões da feature (S28 viewport+ícones/`sharp`; S29 Serwist/
   `app/sw.ts`; S30 persist offline/`OfflineBanner`; S31-S33 Web Push). Anotar que a adoção de `primary`/`isActions`
   nas colunas reais de `tenants`/`leases` é polish opcional fora desta sessão.
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): make DataTable responsive with mobile cards via container queries

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A próxima sessão começa lendo o `SESSION_STATE.md`.
