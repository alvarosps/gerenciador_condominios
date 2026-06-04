# Sessão 26 — Frontend: Fundações de responsividade (viewport, touch targets, headers flex-wrap)

> Primeira sessão da feature "App Mobile Completo" (Frente A — Responsividade, §4.2 do design). Esta sessão
> é **frontend-only, sem dependências novas**: 3 ajustes mecânicos de baixo risco — alvo de toque ≥44px no
> `Button`, `viewport` no `app/layout.tsx`, e `flex-wrap` nos cabeçalhos de página que hoje empurram botões
> para fora no celular. Espelha o header **já correto** em `financial/daily/page.tsx`. As Fases 2–4 (PWA, offline,
> Web Push) vêm em sessões posteriores e dependem desta base.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro; foco **§2 Stack real**, **§4.2 Varredura de polish**, **§4.3 Testes Frente A**, **§8 Sequenciamento**, **§9 Dependências**): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (a feature anterior, 21–25, está **concluída**; esta sessão **abre** a nova feature)
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/architecture.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — abrir e seguir, verificados neste repo)
- **`Button` (CVA, shape a preservar)**: `frontend/components/ui/button.tsx:7-35` — o objeto `variants.size` está em `:23-28` (`default: "h-9 px-4 py-2"` em `:24`; `icon: "h-9 w-9"` em `:27`). `ButtonProps`/`VariantProps` em `:37-41`; export em `:57`. **Manter o formato CVA intacto** — só editar o valor de `default` e adicionar a chave `touch`.
- **`app/layout.tsx` (onde criar o `viewport`)**: `frontend/app/layout.tsx:1` (`import type { Metadata } from 'next'`) e `:5-8` (`export const metadata: Metadata`). O novo `export const viewport` fica **logo abaixo** do `metadata` (`:8`).
- **Header CORRETO a espelhar (modelo)**: `frontend/app/(dashboard)/financial/daily/page.tsx:92` → `className="flex items-center justify-between flex-wrap gap-4"` (e o bloco de ações interno em `:99` usa `flex items-center gap-3 flex-wrap`). Este é o alvo do padrão.
- **Headers SEM `flex-wrap` a corrigir (amostra)**: `frontend/app/(dashboard)/tenants/page.tsx:360` e `frontend/app/(dashboard)/leases/page.tsx:281` — ambos `mb-4 flex justify-between items-center` (não quebram no mobile). A lista **completa e real** está na seção Escopo (o executor reconfirma via grep).
- **Setup/infra de teste Vitest**: `frontend/vitest.config.mts:8-16` (`environment: 'happy-dom'`, `globals: true`, `setupFiles: './tests/setup.ts'`, `include` cobre `**/*.test.tsx`/`**/*.test.ts`). Não há teste de `Button` nem de `layout` hoje — esta sessão os cria.

## Escopo

### Arquivos a criar
- `frontend/components/ui/__tests__/button.test.tsx`
- `frontend/app/__tests__/layout-viewport.test.ts`

### Arquivos a modificar
- `frontend/components/ui/button.tsx` — `size.default`: `'h-9 px-4 py-2'` → `'h-10 px-4 py-2'`; **adicionar** `touch: 'h-11 px-5'` (alvo ≥44px) ao objeto `size`.
- `frontend/app/layout.tsx` — adicionar `import type { Viewport } from 'next'` e `export const viewport: Viewport = { width: 'device-width', initialScale: 1, viewportFit: 'cover' }`.
- **Cabeçalhos de página** — adicionar `flex-wrap gap-3` (modelo `daily/page.tsx:92`) a cada `<div>` cujo `className` contém `flex justify-between items-center` (18 ocorrências confirmadas por grep neste repo; reconfirmar antes de editar):
  - `frontend/app/(dashboard)/financial/incomes/page.tsx:263`
  - `frontend/app/(dashboard)/tenants/page.tsx:360` e `:407`
  - `frontend/app/(dashboard)/furniture/page.tsx:111` e `:158`
  - `frontend/app/(dashboard)/leases/page.tsx:281` e `:329`
  - `frontend/app/(dashboard)/buildings/page.tsx:116` e `:163`
  - `frontend/app/(dashboard)/apartments/page.tsx:231` e `:278`
  - `frontend/app/(dashboard)/admin/users/page.tsx:126`
  - `frontend/app/(dashboard)/financial/categories/page.tsx:175`
  - `frontend/app/(dashboard)/financial/employees/page.tsx:262`
  - `frontend/app/(dashboard)/financial/persons/page.tsx:123`
  - `frontend/app/(dashboard)/financial/person-incomes/page.tsx:219`
  - `frontend/app/(dashboard)/financial/rent-payments/page.tsx:212`
  - `frontend/app/(dashboard)/financial/person-payments/page.tsx:188`

> **OBRIGATÓRIO antes de editar os headers**: rodar o grep AGORA para reconfirmar os paths/linhas reais
> (os números acima podem ter deslizado): `cd frontend && npx eslint --version` não serve; usar a busca de
> conteúdo do harness por `flex justify-between items-center` em `app/(dashboard)/**/page.tsx`. Editar
> **exatamente** as ocorrências encontradas. `financial/daily/page.tsx` **NÃO** aparece (já tem `flex-wrap`) —
> não tocar nele.

## Especificação

### `button.tsx` (mudança cirúrgica, CVA intacto)
No objeto `variants.size` (`:23-28`):
- Trocar `default: "h-9 px-4 py-2"` por `default: "h-10 px-4 py-2"`.
- Adicionar a chave `touch: "h-11 px-5"` (44px de altura; `h-11` = 2.75rem; padding horizontal maior para ações de lista/card no mobile).
- **Não** alterar `sm`, `lg`, `icon`, os `variant`, `defaultVariants`, `ButtonProps`, nem os exports. `VariantProps<typeof buttonVariants>` propaga `'touch'` automaticamente ao tipo de `size` — nenhuma type-annotation manual.

### `layout.tsx` (criar `viewport`)
- Adicionar `Viewport` ao import de tipo: `import type { Metadata, Viewport } from 'next';` (a linha `:1` hoje importa só `Metadata`).
- Logo abaixo do `export const metadata` (`:8`), adicionar:
  ```ts
  export const viewport: Viewport = {
    width: 'device-width',
    initialScale: 1,
    viewportFit: 'cover',
  };
  ```
- **NÃO** incluir `themeColor` aqui — a **Sessão 28** vai *editar* este mesmo `export` para adicionar `themeColor` (cor do tema, derivada do PWA). Esta sessão **cria** o export; a 28 o **augmenta** (sem export duplicado). Manter `metadata` inalterado.

### Headers (varredura mecânica)
- Para cada header listado, inserir `flex-wrap gap-3` na string de `className` (preservando as classes existentes, ex.: `mb-4`, e — quando houver — `p-4 bg-primary/5 border ... rounded`). Resultado típico: `"mb-4 flex justify-between items-center"` → `"mb-4 flex justify-between items-center flex-wrap gap-3"`.
- Alternativa equivalente permitida (use a que ler melhor por header, sem misturar estilos no mesmo arquivo): `flex-col sm:flex-row sm:items-center sm:justify-between gap-3`. Preferir `flex-wrap gap-3` por ser a mudança mínima (KISS) e idêntica ao modelo `daily/page.tsx:92`.
- **Não** reordenar classes nem alterar a estrutura interna dos headers (filhos `<div>`, `<h1>`, botões permanecem).

## TDD

Rodar **somente os arquivos de teste desta sessão** — a suíte completa tem problemas pré-existentes
(xdist/Redis no backend; aqui é frontend, mas a regra de escopo do projeto vale: não rodar tudo).

### 1. Red — escrever os testes primeiro (devem falhar antes da implementação)
Comando: `cd frontend && npx vitest run "components/ui/__tests__/button.test.tsx" "app/__tests__/layout-viewport.test.ts"`

**`components/ui/__tests__/button.test.tsx`** (importa `Button`/`buttonVariants` de `@/components/ui/button`; renderiza com `@testing-library/react`, padrão do projeto):
- Renderiza `<Button size="touch">Ação</Button>` e o elemento `<button>` resultante tem a classe `h-11` (alvo de toque ≥44px) e `px-5`. (Asserir via `screen.getByRole('button').className` contendo `h-11`.)
- Renderiza `<Button>Padrão</Button>` (size default) e o `<button>` tem `h-10` e **não** tem `h-9` (regressão do bump default).
- Renderiza `<Button size="default">…</Button>` explícito → também `h-10`.
- Renderiza `<Button size="icon">…</Button>` → mantém `h-9 w-9` (inalterado; garante que só o `default` mudou).
- `buttonVariants({ size: 'touch' })` (chamada direta da CVA) retorna string contendo `h-11` (cobre o uso via `cn(buttonVariants(...))` em outros componentes, sem renderizar).

**`app/__tests__/layout-viewport.test.ts`** (importa `{ viewport }` de `@/app/layout`):
- `viewport` é um objeto definido (`expect(viewport).toBeDefined()`).
- `viewport.width === 'device-width'`.
- `viewport.initialScale === 1`.
- `viewport.viewportFit === 'cover'`.
- `viewport` **não** tem `themeColor` ainda (`expect(viewport).not.toHaveProperty('themeColor')`) — documenta que a Sessão 28 o adicionará; trava a fronteira entre as sessões.

> **NOTA sobre import de `app/layout.tsx` no teste**: importar **apenas** o named export `viewport` (`import { viewport } from '@/app/layout'`). Não renderizar `RootLayout` (puxa `Providers`/CSS global desnecessariamente). O `viewport` é uma constante pura — o import é barato e SSR-safe.

### 2. Green — implementar o mínimo para passar
1. Editar `button.tsx` (`default` → `h-10`, adicionar `touch: 'h-11 px-5'`).
2. Editar `layout.tsx` (import `Viewport` + `export const viewport`).
3. Aplicar `flex-wrap gap-3` nos 18 headers (reconfirmados por grep).

### 3. Refactor
Nada a extrair (mudanças atômicas; sem duplicação criada). Conferir que nenhum header foi alterado além da
classe de wrap e que o CVA do `Button` continua com uma única chave por size.

### 4. Verify (gate frontend — zero erros/avisos)
- `cd frontend && npx vitest run "components/ui/__tests__/button.test.tsx" "app/__tests__/layout-viewport.test.ts"` → tudo verde.
- `cd frontend && npx tsc --noEmit` → sem erros (o tipo de `size` aceita `'touch'` via `VariantProps`; `Viewport` tipa o export).
- `cd frontend && npx eslint "components/ui/button.tsx" "app/layout.tsx" "components/ui/__tests__/button.test.tsx" "app/__tests__/layout-viewport.test.ts" "app/(dashboard)"` → zero erros/avisos.

## Constraints (NÃO fazer)
- **NÃO** instalar dependências novas — esta sessão é puramente CSS/markup + um export. (Serwist/idb-keyval/sharp/pywebpush vêm em sessões posteriores.)
- **NÃO** adicionar `themeColor` ao `viewport` — pertence à **Sessão 28** (que *edita* este export). Criar o export **uma vez** aqui; não duplicar.
- **NÃO** tocar em `financial/daily/page.tsx` (header já correto) nem em qualquer arquivo fora da lista de Escopo.
- **NÃO** mexer no `DataTable` (cards/container-query são **Sessão 27**), nem em `providers.tsx`, `query-client.ts`, `sw.ts`, layouts ou hooks de push (sessões futuras).
- **NÃO** reordenar/renomear `variant`s ou `size`s existentes do `Button`; só editar `default` e adicionar `touch`. Manter o shape CVA e os exports.
- **NÃO** alterar a estrutura interna dos headers (filhos, textos, botões) — somente as classes de layout do container.
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`; **NÃO** usar `as`/`!` em código de produção — o tipo `'touch'` deve vir naturalmente do `VariantProps`. Nos testes, asserir via leitura de `className`/propriedades reais (sem `as`).
- **NÃO** criar re-exports/barrels; importar `Button`/`buttonVariants`/`viewport` direto da fonte.
- **NÃO** rodar a suíte completa de testes — apenas os 2 arquivos desta sessão (regra de escopo do projeto).
- SOLID/DRY/KISS/YAGNI — mudança mínima e correta; sem código especulativo; sem comentários supérfluos.

## Critérios de Aceite
- [ ] `button.tsx`: `size.default` é `'h-10 px-4 py-2'`; existe `size.touch === 'h-11 px-5'`; `sm`/`lg`/`icon`/`variant`/`defaultVariants`/`ButtonProps`/exports inalterados.
- [ ] `<Button size="touch">` renderiza `<button>` com `h-11` e `px-5`; `<Button>` (default) renderiza `h-10` (sem `h-9`); `<Button size="icon">` mantém `h-9 w-9`.
- [ ] `layout.tsx`: importa `Viewport` de `next`; `export const viewport: Viewport = { width: 'device-width', initialScale: 1, viewportFit: 'cover' }`; **sem** `themeColor`; `metadata` inalterado.
- [ ] Os 18 headers `flex justify-between items-center` em `app/(dashboard)/**/page.tsx` (reconfirmados por grep) ganharam `flex-wrap gap-3` (ou `flex-col sm:flex-row` equivalente); `financial/daily/page.tsx` **não** foi tocado.
- [ ] `npx vitest run` dos 2 arquivos desta sessão 100% verde (10 cenários: 5 button + 5 viewport).
- [ ] `npx tsc --noEmit` sem erros; `eslint` zero erros/avisos nos arquivos tocados (incluindo `app/(dashboard)`).
- [ ] Sem dependência nova; sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem re-exports.

## Handoff
1. Rodar e confirmar verde (colar a saída como evidência):
   - `cd frontend && npx vitest run "components/ui/__tests__/button.test.tsx" "app/__tests__/layout-viewport.test.ts"`
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "components/ui/button.tsx" "app/layout.tsx" "components/ui/__tests__/button.test.tsx" "app/__tests__/layout-viewport.test.ts" "app/(dashboard)"`
2. Atualizar `prompts/SESSION_STATE.md`: abrir a nova feature **"App Mobile Completo — Responsividade + PWA + Offline + Web Push"** (design `docs/plans/2026-06-04-mobile-pwa-offline-design.md`, Sessões 26–33+); marcar **Sessão 26 concluída**; registrar os contratos cross-session que esta sessão **trava** para as próximas:
   - `app/layout.tsx` tem `export const viewport` — a **Sessão 28** vai *editá-lo* para adicionar `themeColor` (sem export novo).
   - `Button` ganhou `size: 'touch'` (`h-11 px-5`) e `default` virou `h-10` — a **Sessão 27** usa `size="touch"` nas ações dos cards do `DataTable`.
   - A **Sessão 27** estende `Column<T>` (`primary?`/`hideOnCard?`/`isActions?`), extrai `resolveCellValue` em `components/tables/cell-value.ts` e cria `DataTableCards` em `components/tables/data-table-cards.tsx` (layout container-query `@container` / `hidden @md:block` / `@md:hidden`).
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): responsive foundations — touch button size, viewport export, flex-wrap headers

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A Sessão 27 começa lendo o `SESSION_STATE.md`.
