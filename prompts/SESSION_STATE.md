# SESSION STATE — Módulo Financeiro

**Feature**: Módulo Financeiro Completo
**Design Doc**: `docs/plans/2026-03-21-financial-module-design.md`
**Total de Sessões**: 20
**Sessão Atual**: 20 (concluída) — Módulo Financeiro COMPLETO

---

## Feature: App Mobile Completo (Responsivo + PWA + Offline + Web Push) — Sessões 26–33

**Design Doc**: `docs/plans/2026-06-04-mobile-pwa-offline-design.md`
**Total de Sessões**: 8 (26–33)
**Status**: **CONCLUÍDA** — sessões 26–33 executadas in-place no branch `feat/mobile-pwa-offline`. Frente D (Web Push) completa: S31 model + S32 sender/endpoints + S33 SW handlers/hook/toggle. Payload de subscribe verificado idêntico entre backend (S32, leitura) e frontend (S33, envio via `subscription.toJSON()`).
**Branch sugerida**: `feat/mobile-pwa-offline`
**Decisões de produto**: offline = somente leitura (sem fila de sync); Web Push é prioridade (admin + inquilino), app Expo fica para o futuro; tabelas viram cards no mobile; ícone PWA gerado do tema.

| # | Sessão | Camada | Status | Arquivo |
|---|--------|--------|--------|---------|
| 26 | Fundações de responsividade (viewport, touch targets, headers flex-wrap) | FE | **concluída** | `prompts/26-frontend-responsive-foundations.md` |
| 27 | DataTable responsivo (cards via container queries) | FE | **concluída** | `prompts/27-frontend-datatable-cards.md` |
| 28 | PWA manifest + ícones gerados + metadata Apple | FE | **concluída** | `prompts/28-frontend-pwa-manifest-icons.md` |
| 29 | Service Worker com Serwist (precache + fallback offline) | FE | **concluída** | `prompts/29-frontend-serwist-service-worker.md` |
| 30 | Offline read-only (persist + IndexedDB + banner + logout clear) | FE | **concluída** | `prompts/30-frontend-offline-cache.md` |
| 31 | Backend: model `WebPushSubscription` + migração + VAPID + `pywebpush` | BE | **concluída** | `prompts/31-backend-webpush-model.md` |
| 32 | Backend: envio dual-channel (Expo+WebPush) + `WebPushViewSet` + rotas | BE | **concluída** | `prompts/32-backend-webpush-sender-endpoints.md` |
| 33 | Frontend: Web Push UI (handlers no SW + `useWebPush` + toggle) | FE | **concluída** | `prompts/33-frontend-webpush-ui.md` |

**Ordem / dependências** (ver `prompts/ROADMAP.md`): FE `26 → {27 ‖ 28} → 29 → 30`; BE `31 → 32` (paralelo ao FE); `33` depende de **29 (sw.ts) + 32 (endpoints)**.

**Contratos cross-session (NÃO derivar — verbatim entre sessões):**
- `Column<T>` ganha `primary?`/`hideOnCard?`/`isActions?`; resolver `resolveCellValue<T>` em `components/tables/cell-value.ts`; `DataTableCards<T>` em `components/tables/data-table-cards.tsx`; classes `@container` / `hidden @md:block` / `@md:hidden` (S27).
- `export const viewport: Viewport` criado em S26 (sem `themeColor`) e **editado** em S28 (adiciona `themeColor`) — sem export duplicado. Size `touch` (h-11) criado em S26, usado em S27.
- `app/sw.ts` criado em S29 com a seção literal `=== Web Push handlers (Sessão 33) ===`; S33 **só anexa** os listeners (não recria).
- `WebPushSubscription` campos `endpoint`(unique)/`p256dh`/`auth`/`is_active`/`user` (S31) = lidos por S32. Payload de subscribe `{ endpoint, keys: { p256dh, auth } }` (= `subscription.toJSON()`) idêntico em S32 (backend) e S33 (frontend). Rotas `/api/web-push/{vapid-public-key,subscribe,unsubscribe}/`.
- S33 mapeia `data.screen` do backend (bare: `proofs`/`payments`) para rotas web via `SCREEN_TO_PATH` (fallback `/`) — backend não é alterado.

### Sessão 26 — Arquivos Criados/Modificados (concluída)
- **Criados**: `frontend/components/ui/__tests__/button.test.tsx` (5 testes: `touch`→h-11/px-5, default→h-10≠h-9, default explícito→h-10, `icon` intacto h-9 w-9, `buttonVariants({size:'touch'})` contém h-11) e `frontend/app/__tests__/layout-viewport.test.ts` (5 testes: viewport definido, width/initialScale/viewportFit, e `not.toHaveProperty('themeColor')` travando a fronteira da S28).
- **Modificados**: `frontend/components/ui/button.tsx` (size `default` `h-9`→`h-10`; novo size `touch: "h-11 px-5"`; CVA/variants/exports intactos); `frontend/app/layout.tsx` (`import type { Viewport }` + `export const viewport` width/initialScale/viewportFit, **sem** `themeColor` — reservado à S28); **18 cabeçalhos** em 13 `app/(dashboard)/**/page.tsx` ganharam `flex-wrap gap-3` (apartments, furniture, leases, tenants, buildings — header+banner; admin/users; financial incomes/person-incomes/person-payments/persons/employees/categories/rent-payments). `financial/daily/page.tsx` (já correto) **não** tocado.
- **Verificação (main tree)**: `vitest` 10/10 verde; `tsc --noEmit` 0 erros; `eslint` (arquivos tocados + `app/(dashboard)`) 0 erros/avisos. Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem deps novas; **não commitado** (na árvore de trabalho do branch `feat/mobile-pwa-offline`).
- **Nota de execução**: o subagente rodou em worktree isolado (off `77bbd53`); o orquestrador consolidou o patch (17 arquivos `frontend/`) no main (`feat/mobile-pwa-offline` @ `3b956c4`), removeu o worktree e re-rodou o gate no main. As sessões seguintes rodam in-place no main para preservar a cadeia de dependências.

### Sessão 27 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `frontend/components/tables/cell-value.ts` — `resolveCellValue<T>(record, column): unknown` (lógica do antigo `getCellValue` movida verbatim: caminhos pontilhados + ausência de `dataIndex` → `undefined`; sem `as` — guarda `isRecord`) + helper compartilhado `renderCellContent<T>(column, record, index): React.ReactNode` (resolve valor → `column.render` se houver, senão stringify) consumido por **ambos** os ramos (tabela e cards) — DRY, fonte única do render de célula.
  - `frontend/components/tables/data-table-cards.tsx` — `DataTableCards<T extends object>({ columns, data, rowKey, className })`: título = coluna `primary` (fallback 1ª não-`isActions`), corpo = linhas `rótulo: valor` respeitando `hideOnCard`, rodapé `isActions` full-width (`w-full [&>*]:w-full`, `border-t`); empty state "Nenhum dado disponível"; `data-testid` `data-table-card`/`-title`/`-footer`; componente puro (sem hooks/apiClient).
  - `frontend/components/tables/__tests__/cell-value.test.ts` (5), `…/data-table-cards.test.tsx` (9), `…/data-table.test.tsx` (7) — 21 testes (resolver puro + montagem do card + alternância tabela/cards por classe utilitária + retrocompat de API).
- **Modificados**:
  - `frontend/components/tables/data-table.tsx` — `Column<T>` ganhou `primary?`/`hideOnCard?`/`isActions?` (opcionais, ao final; existentes intactos); `getCellValue` inline **removido** (importa `renderCellContent` de `./cell-value`, sem shim/re-export); ramo de célula da tabela simplificado para `renderCellContent(column, record, index)` (eliminado o `as` da stringificação); `return` envolto em `<div className="@container space-y-4">`, wrapper da tabela `hidden @md:block`, `<DataTableCards … className="@md:hidden" />` ao lado (reusa `paginatedData` + `getRowKey`); paginação e `rowSelection` **inalterados** (seleção fica só no desktop).
- **Assinatura pública inalterada**: `DataTableProps` (`dataSource`/`columns`/`pagination`/`rowKey`/`rowSelection`/sort) intacta; `tenants/page.tsx` e `leases/page.tsx` **não** tocados (caem nos defaults dos 3 novos campos). Adoção de `primary`/`isActions` nas colunas reais de `tenants`/`leases` é **polish opcional fora desta sessão**.
- **Contrato cross-session confirmado (verbatim)**: `Column<T>` + `primary?`/`hideOnCard?`/`isActions?`; `resolveCellValue` em `components/tables/cell-value.ts`; `DataTableCards<T>` em `components/tables/data-table-cards.tsx`; classes `@container` / `hidden @md:block` / `@md:hidden`. Consumido por S28–S33.
- **Verificação (main tree, in-place)**: `vitest "components/tables/__tests__"` 21/21 verde; regressão `vitest "app/(dashboard)/tenants" "app/(dashboard)/leases"` 21/21 verde (sem falhas novas); `tsc --noEmit` 0 erros; `eslint "components/tables"` 0 erros/0 avisos. Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção (guard `isRecord` + stringify por `typeof`; testes sem `!` via fixtures nomeadas `ana`/`bruno` e linha única); sem barrel/re-export; sem dependência nova (container queries Tailwind v4 nativas). **Não commitado**, **sem worktree** (in-place no `feat/mobile-pwa-offline`).

### Sessão 28 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `frontend/app/manifest.ts` — `export default function manifest(): MetadataRoute.Manifest` (função pura, sem ramos): `name: 'Condomínios Manager'`, `short_name: 'Condomínios'`, `description`, `start_url: '/'`, `display: 'standalone'`, `lang: 'pt-BR'`, `background_color: '#fbfbfc'`, `theme_color: '#0d847a'`, e 3 ícones (`/icons/icon-192.png` 192×192 `any`, `/icons/icon-512.png` 512×512 `any`, `/icons/icon-512-maskable.png` 512×512 `maskable`). Comentário no topo documenta a conversão OKLCH→HEX. Next vincula o manifest automaticamente (`<link rel="manifest" href="/manifest.webmanifest">`) — sem `<link>` manual nem `metadata.manifest`.
  - `frontend/scripts/icon-source.svg` — SVG-fonte 512×512 (glyph de prédio simples: retângulo vertical em `#0d847a` com 6 janelas + porta recortadas em `#fbfbfc`), fundo `#fbfbfc`. Fonte única reprodutível dos PNGs.
  - `frontend/scripts/generate-icons.mjs` — script ESM standalone (rodado por `node scripts/generate-icons.mjs` a partir de `frontend/`) que usa `sharp` + `node:fs`/`node:path`/`node:url` para rasterizar o SVG nos 5 PNGs. `mkdirSync(public/icons, { recursive: true })`. Maskable = glyph reduzido a 80% (`extend`/padding com `background: '#fbfbfc'`) para respeitar a safe-zone; apple-icon = `flatten` opaco (iOS ignora alpha). **Não** registra script npm novo (YAGNI). Não importado por nenhum código de runtime do app.
  - `frontend/app/__tests__/manifest.test.ts` — 3 testes (campos obrigatórios; HEX `#0d847a`/`#fbfbfc`; ícones ≥2 todos `image/png`/`/icons/`, com 512 maskable + 192). Sem `as`/`!` — itera com guards sob `noUncheckedIndexedAccess`.
  - **5 PNGs gerados pelo script** (produto reprodutível, não commitados à mão): `frontend/public/icons/icon-192.png` (1452 B), `icon-512.png` (8121 B), `icon-512-maskable.png` (8252 B), `frontend/app/icon.png` (8121 B, favicon nativo Next), `frontend/app/apple-icon.png` (1280 B, 180×180 apple-touch nativo Next).
- **Modificados**:
  - `frontend/app/layout.tsx` — **editado** o `export const viewport` da S26 (adicionado `themeColor` em forma de array light/dark, ambos `#0d847a`; `width`/`initialScale`/`viewportFit: 'cover'` intactos; **sem** export duplicado); `metadata` ganhou `appleWebApp: { capable: true, statusBarStyle: 'default', title: 'Condomínios' }`. **Sem** `metadata.manifest` (vínculo automático).
  - `frontend/app/__tests__/layout-viewport.test.ts` — **cross-session fix**: a asserção `not.toHaveProperty('themeColor')` (boundary lock da S26 reservando o campo para a S28) foi substituída por `expect(viewport.themeColor).toEqual([...])` afirmando os dois entries light/dark `#0d847a`. Os outros 4 testes (width/initialScale/viewportFit/definido) intactos. Mantém a árvore verde agora que a S28 legitimamente adiciona `themeColor`.
  - `frontend/package.json` / `frontend/package-lock.json` — `sharp ^0.34.5` adicionado em `devDependencies` (ordem alfabética, entre `prettier` e `tailwindcss-animate`). **Não** em `dependencies` (é só build de ícones).
- **Cores documentadas (OKLCH → HEX)**: `theme_color = #0d847a` ← `--primary: oklch(0.55 0.15 175)` (teal); `background_color = #fbfbfc` ← `--background: oklch(0.985 0.002 240)` (quase-branco). Fonte: `frontend/app/globals.css:54,60`. Os mesmos HEX são usados no `icon-source.svg` (glyph `#0d847a`, fundo `#fbfbfc`).
- **Comando de regeneração de ícones** (para futuras trocas de logo — editar `scripts/icon-source.svg` e rodar): `cd frontend ; node scripts/generate-icons.mjs`.
- **Verificação (main tree, in-place)**: `vitest "app/__tests__/manifest.test.ts" "app/__tests__/layout-viewport.test.ts"` 8/8 verde (3 manifest + 5 viewport); `node scripts/generate-icons.mjs` gerou os 5 PNGs (listados acima); `tsc --noEmit` 0 erros; `eslint` (`manifest.ts`/`layout.tsx`/`manifest.test.ts`/`layout-viewport.test.ts`) 0 erros/0 avisos. Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem re-exports; `sharp` é dev-only e não é importado por runtime. `next.config.js`, `app/sw.ts`, `public/sw.js` **inalterados/não criados** (reservados à S29). **Não commitado**, **sem worktree** (in-place no `feat/mobile-pwa-offline`).
- **Próxima sessão (S29)**: adiciona `withSerwist` ao `next.config.js` e cria `app/sw.ts` com a seção literal `=== Web Push handlers (Sessão 33) ===` (onde a S33 anexa os handlers de `push`/`notificationclick`).

### Sessão 29 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `frontend/app/sw.ts` — instância `Serwist` (precache + offline). `/// <reference lib="webworker" />` no topo; importa `defaultCache` de `@serwist/next/worker` e `Serwist` + tipos `PrecacheEntry`/`SerwistGlobalConfig` direto de `serwist` (sem re-export). Tipagem do escopo via `declare global { interface WorkerGlobalScope extends SerwistGlobalConfig { __SW_MANIFEST: (PrecacheEntry | string)[] | undefined } }` + `declare const self: ServiceWorkerGlobalScope` (idioma canônico do exemplo `next-basic` da Serwist — tipa `self.__SW_MANIFEST` sem `any`). `new Serwist({ precacheEntries: self.__SW_MANIFEST, skipWaiting: true, clientsClaim: true, navigationPreload: true, runtimeCaching: defaultCache, fallbacks: { entries: [{ url: '/offline', matcher: ({ request }) => request.destination === 'document' }] } })` + `serwist.addEventListeners()`. **Termina** com o bloco-marcador literal `=== Web Push handlers (Sessão 33) ===` (comentário, **zero** listeners `push`/`notificationclick` — confirmado por grep: as únicas ocorrências dessas palavras estão dentro do comentário-marcador). A **Sessão 33 apenas anexa** (append) os handlers nesse bloco — **não recria** o arquivo.
  - `frontend/app/offline/page.tsx` — página estática mínima de fallback (Server Component, sem `'use client'`): `<h1>Você está offline</h1>` + parágrafo "Reconecte à internet para continuar". Precacheada (referenciada em `public/sw.js`).
  - `frontend/tsconfig.sw.json` — tsconfig dedicado do SW: `extends ./tsconfig.json`, `lib: ["esnext", "webworker"]`, `types: ["@serwist/next/typings"]`, `include: ["app/sw.ts"]`. **Escolha**: o SW roda em contexto webworker (sem `dom`); isolar num tsconfig próprio evita conflito de globais DOM × WebWorker no app. Por isso `app/sw.ts` é **excluído** do `include` DOM principal (ver abaixo).
- **Modificados**:
  - `frontend/next.config.js` — envolvido com `withSerwist` (CJS `require('@serwist/next').default({ swSrc: 'app/sw.ts', swDest: 'public/sw.js', disable: process.env.NODE_ENV === 'development' })`); só a linha de export mudou para `module.exports = withSerwist(nextConfig)`. **`output: 'standalone'` e todas as demais opções (`reactStrictMode`, `experimental.optimizePackageImports`, `skipTrailingSlashRedirect`, `eslint.dirs`, `typescript`, `staticPageGenerationTimeout`, `onDemandEntries`) permanecem intactas.** Mantido CommonJS (não convertido para ESM/`.mjs`).
  - `frontend/tsconfig.json` — `exclude` passou a `["node_modules", "app/sw.ts"]` (o SW é coberto pelo `tsconfig.sw.json` com lib webworker; fora do include DOM principal).
  - `frontend/.eslintrc.json` — novo override `{ "files": ["app/sw.ts"], "parserOptions": { "project": "./tsconfig.sw.json" } }` no topo de `overrides`. Necessário porque o lint tipado (`parserOptions.project: true`) só encontra o arquivo no projeto que o inclui; como `app/sw.ts` saiu do `tsconfig.json` para o `tsconfig.sw.json`, o override aponta o parser ao projeto correto (correção na raiz, **sem** `eslint-disable`).
  - `frontend/.gitignore` — após a seção `# next.js`, adicionado `# serwist (service worker gerado no build)` + `public/sw.js` + `public/swe-worker-*.js` (artefatos gerados no build, fora do versionamento).
  - `frontend/package.json` / `frontend/package-lock.json` — `@serwist/next ^9.5.11` e `serwist ^9.5.11` adicionados em `dependencies` (runtime de produção, não dev) via `npm install` (29 pacotes).
- **Decisão de verificação (sem teste Vitest do SW)**: Service Worker é inviável de unit-testar sem mockar internals do `Serwist` (violaria a política de mocks — só fronteiras externas). Verificação **via build de produção** que gera `public/sw.js` (decisão deliberada, conforme o prompt).
- **Verificação (main tree, in-place)**:
  - `npm run build` → **EXIT 0**; 41 páginas estáticas geradas (inclui `/offline` ○ Static e `/manifest.webmanifest`). `public/sw.js` gerado: **50470 bytes** (não-vazio); `__SW_MANIFEST` substituído (0 tokens crus remanescentes), **136 entradas** de precache (`revision`) injetadas (sem warning de manifest vazio); `/offline` referenciado no fallback. Nenhum `swe-worker-*.js` gerado nesta configuração (artefato condicional do Serwist; o glob no `.gitignore` permanece como salvaguarda).
  - `npx tsc --project tsconfig.sw.json --noEmit` → **EXIT 0** (lib webworker, `self.__SW_MANIFEST` tipado, sem `any`).
  - `npx tsc --noEmit` (config principal) → **EXIT 0** (app intacto; globais de webworker não vazam para o DOM).
  - `npx eslint "app/sw.ts" "app/offline/page.tsx"` → **EXIT 0**; `npm run lint` (escopo `next.config.js` dirs) → **"No ESLint warnings or errors"**.
  - Sem `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`; sem re-exports/barrels; tipos do webworker resolvidos na raiz (`tsconfig.sw.json` + `/// <reference lib="webworker" />`). **Não commitado**, **sem worktree** (in-place no `feat/mobile-pwa-offline`).
- **Próxima sessão (S30)**: offline read-only (persister IndexedDB + `OfflineBanner` + logout clear). A S33 (Web Push UI) anexa os handlers `push`/`notificationclick` no bloco-marcador de `app/sw.ts`.

### Sessão 30 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `frontend/lib/config/persister.ts` — `createIDBPersister()` (AsyncStorage persister do TanStack sobre `idb-keyval` `get`/`set`/`del`) + `QUERY_CACHE_IDB_KEY = 'condominios-query-cache'` (constante exportada, **fonte única** da chave do IndexedDB — usada pelo próprio persister via `key:` e reaproveitada no logout, DRY). Storage tipado contra `AsyncStorage<string>` (`getItem`/`setItem`/`removeItem` com params explícitos, `get<string>`) — **sem** `as`/`!`.
  - `frontend/components/offline-banner.tsx` — `OfflineBanner` (`'use client'`, sem props/KISS). `useState(false)` SSR-safe; `useEffect` seta `!navigator.onLine` no mount, registra listeners `online`/`offline` e **remove ambos** no cleanup. Offline → faixa `role="status"` com ícone `WifiOff` (lucide) + texto PT exato **"Você está offline — exibindo dados salvos"** (`bg-amber-500/15 text-amber-700 dark:text-amber-400`, status nunca só por cor); online → `null`.
  - `frontend/lib/config/__tests__/persister.test.ts` — 7 testes (mock só do boundary `idb-keyval`): persister expõe `persistClient`/`restoreClient`/`removeClient`; `set`/`get`/`del` delegados com `QUERY_CACHE_IDB_KEY` (exercita o caminho real do persister, sem stub dele); `QUERY_CACHE_IDB_KEY === 'condominios-query-cache'`; **`gcTime >= maxAge`** (24h) e `networkMode === 'offlineFirst'` (asserção de config lendo `queryClient.getDefaultOptions()`).
  - `frontend/components/__tests__/offline-banner.test.tsx` — 4 testes (render real; boundary = `navigator.onLine` via `Object.defineProperty` + `window.dispatchEvent(new Event('online'/'offline'))`): ausente online no mount; presente offline no mount; aparece no `offline` e some no `online`; listeners removidos no unmount (spy em `removeEventListener`).
- **Modificados**:
  - `frontend/lib/config/query-client.ts` — adicionados `gcTime: 1000*60*60*24` e `networkMode: 'offlineFirst'` ao bloco `queries`. `staleTime`, o `retry` custom (401/403 → sem retry) e `refetchOnWindowFocus` **mantidos intactos**.
  - `frontend/app/providers.tsx` — `QueryClientProvider` → `PersistQueryClientProvider` (de `@tanstack/react-query-persist-client`); persister instanciado **uma vez** em escopo de módulo (`const persister = createIDBPersister()`, fora do componente); `persistOptions { persister, maxAge: 1000*60*60*24, buster: process.env.NEXT_PUBLIC_BUILD_ID ?? 'dev', dehydrateOptions: { shouldDehydrateQuery: q => q.state.status === 'success' } }` (persiste só queries `success`; o `buster` invalida o IndexedDB a cada deploy). `ThemeProvider`/`{children}`/`<Toaster />` inalterados.
  - `frontend/lib/api/hooks/use-auth.ts` — `useLogout()`: importa `del` de `idb-keyval` e `QUERY_CACHE_IDB_KEY` de `@/lib/config/persister`. **Site exato da limpeza**: em `onSuccess` **e** `onError`, após `queryClient.clear()` e antes do redirect (`window.location.href = '/login'`), `void del(QUERY_CACHE_IDB_KEY)`. **Nota de segurança (design §6.3)**: limpa o cache persistido do dispositivo no logout para que os dados de negócio de um usuário **não vazem para outro** no mesmo dispositivo (offline é per-session, read-only). Único site de logout (os layouts apenas chamam `useLogout().mutate()`).
  - `frontend/lib/api/hooks/__tests__/use-auth.test.tsx` — `vi.mock('idb-keyval')` no topo (boundary; `del` resolvido); novo teste no `describe('useLogout')`: após `mutate()` + `waitFor(!isPending)`, `expect(del).toHaveBeenCalledWith(QUERY_CACHE_IDB_KEY)`. Os 2 testes existentes (store limpo) permanecem verdes; `del` mock limpo no `beforeEach`. **Não** mockado `queryClient`/store.
  - `frontend/components/layouts/main-layout.tsx` — `<OfflineBanner />` montado logo dentro de `<div className="min-h-screen">`, antes do skip-link/header mobile (banner no topo em todas as rotas do dashboard).
  - `frontend/components/layouts/tenant-layout.tsx` — `<OfflineBanner />` no topo do wrapper, antes do `<header>` (portal do inquilino).
  - `frontend/.env.example` — `NEXT_PUBLIC_BUILD_ID` documentado na seção APPLICATION SETTINGS (buster do cache persistido; muda a cada deploy para invalidar o IndexedDB; opcional em dev, default `'dev'`).
  - `frontend/package.json` / `frontend/package-lock.json` — `@tanstack/react-query-persist-client ^5.101.0`, `@tanstack/query-async-storage-persister ^5.101.0`, `idb-keyval ^6.2.5` adicionados em `dependencies` via `npm install` (4 pacotes).
- **Decisões**: a chave do IndexedDB é definida **uma única vez** (`QUERY_CACHE_IDB_KEY`) e usada tanto como `key` do persister quanto no `del` do logout — garante que o logout remove exatamente o que o persister gravou (DRY). Offline permanece **read-only** — sem fila de sync/Background Sync (YAGNI); `networkMode: 'offlineFirst'` deixa mutations `paused` offline e o banner avisa que são dados salvos.
- **Independência do SW (S29)**: a persistência do cache funciona **independente** do Service Worker da S29 — o persister grava/rehidrata via IndexedDB diretamente, sem depender do `app/sw.ts`.
- **Verificação (main tree, in-place)**: `npx vitest run "lib/config/__tests__/persister.test.ts" "components/__tests__/offline-banner.test.tsx" "lib/api/hooks/__tests__/use-auth.test.tsx"` → **EXIT 0**, 21/21 verde (7 persister + 4 banner + 10 use-auth). `npx tsc --noEmit` → **EXIT 0**. `npx eslint` (7 arquivos de produção + 3 de teste) → **EXIT 0**, zero erros/avisos. Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem re-exports/barrel; sem fila de sync. **Não commitado**, **sem worktree** (in-place no `feat/mobile-pwa-offline`).
- **Próxima sessão (S31)**: inicia o backend de Web Push — model `WebPushSubscription` (campos `endpoint` unique/`p256dh`/`auth`/`is_active`/`user`) + migração `0044` + settings VAPID + dep `pywebpush`. Lido pela S32 (envio dual-channel + `WebPushViewSet` + rotas).

### Sessão 31 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `core/models.py` → `class WebPushSubscription(AuditMixin, models.Model)` (posicionado **após** `DeviceToken`, **antes** de `PaymentProof`): `user` (FK → `AUTH_USER_MODEL`, `on_delete=CASCADE`, `related_name="web_push_subscriptions"`), `endpoint` (`TextField(unique=True)`), `p256dh`/`auth` (`CharField(max_length=255)`), `is_active` (`BooleanField(default=True)`), `__str__` → `f"Web push for {self.user}"`. **Não** herda `SoftDeleteMixin` (espelha `DeviceToken`); **sem** `Meta`/`indexes` (o `unique=True` já cria índice — YAGNI).
  - `core/migrations/0044_webpushsubscription.py` — gerado por `makemigrations core` (head anterior `0043_*`). 1 operação `CreateModel`; aplicado e verificado reversível (forward → `migrate core 0043` desfaz → `migrate core` reaplica, todos OK). `makemigrations --check --dry-run` → "No changes detected".
  - `tests/unit/test_web_push_model.py` — 6 testes (`@pytest.mark.django_db`, fixture `regular_user`, banco real): cria com campos válidos; `is_active` default True; `endpoint` unique (`IntegrityError` dentro de `transaction.atomic()`); `__str__`; `related_name` (`user.web_push_subscriptions`); herda `AuditMixin` (`created_at`/`updated_at` não-nulos) **sem** `is_deleted`. **6/6 verde**.
- **Modificados**:
  - `condominios_manager/settings.py` — bloco "Web Push (VAPID)" **após** o bloco Twilio, **antes** de "Celery Configuration": `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` (`config(..., default="")`) e `VAPID_SUBJECT` (`config(..., default="mailto:admin@example.com")`).
  - `requirements.txt` e `pyproject.toml` `[project.dependencies]` — `pywebpush>=2.0.0,<3.0` num bloco `# Web Push (VAPID)` em **ambos** (regra do projeto). Instalado via `uv add "pywebpush>=2.0.0,<3.0"` (resolveu `pywebpush==2.3.0` + transitivos `py-vapid==1.9.4`, `http-ece==1.2.1`); `uv.lock` atualizado.
  - `.env.example` e `.env.production.example` — seção "WEB PUSH (VAPID)" documentando as 3 vars + comando de geração do par de chaves: `vapid --gen` (gera `private_key.pem`/`public_key.pem`) e `vapid --applicationServerKey` (chave pública base64url para o front). Na produção, nota de "gerar uma única vez e guardar no secret manager".
- **Backup antes do migrate** (regra `.claude/rules/database.md`): `uv run python scripts/backup_db.py` → `backups/backup_condominio_20260604_171157.sql` (0.54 MB) ANTES do `migrate`. Dev migrate **executado** (DB Postgres porta 5433 acessível); `pytest` do arquivo desta sessão **executado** (6/6 verde). Migração `0044` aplicada também junto da `0043` (que estava pendente na árvore de trabalho).
- **Gate estático (escopo desta sessão)**: `ruff check`/`ruff format --check` nos arquivos novos — **limpo** (migração coberta pelo exclude `"migrations"` do ruff, como toda migração gerada). `mypy core/` → o **único** erro é pré-existente/não-relacionado em `core/services/dashboard_service.py:336` (`payments_by_lease` sem anotação; arquivo **não** tocado nesta sessão); o model novo é limpo. `pyright` → 0 erros nas linhas do `WebPushSubscription` (1586-1600) e no bloco VAPID do `settings.py`; os erros remanescentes em `core/models.py` (`Meta overrides symbol…`, `OAuthExchangeCode.user_id`) e `settings.py:147` (`CACHES`) são **pré-existentes** (WIP de auth não-relacionado), não introduzidos aqui. **Sem** `# noqa`/`# type: ignore`; **sem** `try/except ImportError`/`from __future__ import annotations`; **sem** re-export.
- **Não tocados** (reservados à S32): `core/services/notification_service.py`, `core/urls.py`, `core/viewsets/` — sem `WebPushViewSet`, serializer ou rotas nesta sessão.
- **Próxima sessão (S32)**: refator do `notification_service` (extrair `send_expo_push`/`send_web_push` + envio unificado) e `WebPushViewSet` + rotas `/api/web-push/{vapid-public-key,subscribe,unsubscribe}/`, **consumindo** este model (`endpoint`/`p256dh`/`auth`/`is_active`/`user`) e estas settings VAPID **sem alterá-los**. Payload de subscribe `{ endpoint, keys: { p256dh, auth } }` (= `subscription.toJSON()`).

### Sessão 32 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `core/viewsets/web_push_views.py` — `WebPushViewSet(ViewSet)` (`permission_classes=[IsAuthenticated]`), espelhando `DeviceTokenViewSet`. 3 actions `@action(detail=False)`: `vapid_public_key` (GET `url_path="vapid-public-key"` → `{"publicKey": settings.VAPID_PUBLIC_KEY}`); `subscribe` (POST `url_path="subscribe"`, lê o payload **exato** `{ endpoint, keys: { p256dh, auth } }`, valida campos → 400, `WebPushSubscription.objects.update_or_create(endpoint=…, defaults=…, create_defaults=…)`, retorna `{id, endpoint}` 201/200); `unsubscribe` (POST `url_path="unsubscribe"`, valida `endpoint` → 400, `filter(endpoint, user).update(is_active=False)`, 404 se `updated==0`, senão 200). Imports diretos da fonte (`from core.models import WebPushSubscription`); `cast(User, request.user)`.
  - `tests/unit/test_web_push_sender.py` — 5 testes unit (mock só do boundary `pywebpush.webpush`; ORM/model reais): `send_web_push` chama `webpush` 1× com `subscription_info`/`data`(JSON)/`vapid_private_key`/`vapid_claims` corretos; pula inscrição `is_active=False`; desativa a inscrição quando `WebPushException` traz `response.status_code==410` (refetch do DB, sem propagar); mantém ativa em status 500; `send_push_notification` chama **ambos** os canais (`send_expo_push` **e** `send_web_push`) — patch nas duas funções de canal (boundaries de envio, mesmo padrão de `test_notification_service.py`).
  - `tests/integration/test_web_push_api.py` — 9 testes de API (espelham `test_device_api.py`, DB real, sem mock de internals): `vapid-public-key` 200 (com `override_settings(VAPID_PUBLIC_KEY=…)`); subscribe cria→201; mesmo `endpoint` atualiza→200 + `count()==1` (chaves novas); falta `keys`→400; falta `endpoint`→400; unsubscribe desativa→200 + `is_active=False`; inexistente→404; `endpoint` vazio→400; sem auth→401.
- **Modificados**:
  - `core/services/notification_service.py` — refator: extraída a lógica Expo (intacta em comportamento) para `send_expo_push(user, title, body, data)`; nova `send_web_push(user, title, body, data)` que itera `WebPushSubscription.objects.filter(user, is_active=True)`, monta `subscription_info`+payload JSON e chama `webpush(...)` com a VAPID dos `settings`; em `WebPushException` cujo `response.status_code in _GONE_STATUS_CODES (404, 410)` desativa a inscrição (`save(update_fields=["is_active"])`), e qualquer `WebPushException` é logada e **não propaga**. `send_push_notification(user, title, body, data)` agora chama **os dois** canais. Imports novos no topo (`json`, `django.conf.settings`, `pywebpush.WebPushException/webpush`, `WebPushSubscription`); constante `_GONE_STATUS_CODES = (404, 410)` (sem magic numbers). `create_notification`, `is_notification_sent_today`, `notify_new_proof`, `notify_proof_reviewed` **inalterados** — passam a enviar Web Push automaticamente via `send_push_notification`.
  - `core/viewsets/__init__.py` — `from .web_push_views import WebPushViewSet` + `"WebPushViewSet"` no `__all__` (ordem alfabética, após `RentPaymentViewSet`).
  - `core/urls.py` — `WebPushViewSet` no bloco de import `from .viewsets import (...)` + `router.register(r"web-push", WebPushViewSet, basename="web-push")` junto a `devices`. Rotas finais: `GET /api/web-push/vapid-public-key/`, `POST /api/web-push/subscribe/`, `POST /api/web-push/unsubscribe/`.
  - `pyproject.toml` — `pywebpush` (e `pywebpush.*`) adicionados à lista de `[[tool.mypy.overrides]] … ignore_missing_imports = true` (lib sem `py.typed`/stubs, mesmo tratamento de `twilio`/`boto3`/etc.). **Não** mexe nas dependências (S31); apenas o override de tipos do mypy para a lib recém-importada — padrão canônico do projeto, alternativa correta ao proibido `# type: ignore`.
- **Envio dual-channel ATIVO**: todos os gatilhos de notificação existentes (`notify_new_proof` → admins; `notify_proof_reviewed` → inquilino; e qualquer `create_notification`) agora enviam **também** Web Push, sem edição dos gatilhos — o fan-out acontece dentro de `send_push_notification`.
- **Verificação (main tree, in-place)**: `pytest tests/integration/test_web_push_api.py tests/unit/test_web_push_sender.py` (sem xdist) → **14/14 verde**. Regressão `tests/unit/test_notification_service.py` → 6/6 verde (o `send_push_notification` agora roteia o caminho Expo via `send_expo_push`). `ruff check`/`ruff format --check` nos 6 arquivos tocados → **limpo**. `mypy core/` → **único erro é pré-existente/não-relacionado** em `core/services/dashboard_service.py:336` (`payments_by_lease` sem anotação, WIP de auth, arquivo **não** tocado); `notification_service.py` limpo. `pyright` nos 6 arquivos tocados → **0 erros/0 avisos** (as 3 linhas "unrecognized setting" do `pyrightconfig.json` são pré-existentes). Sem `# noqa`/`# type: ignore`; sem `from __future__`/`TYPE_CHECKING`; sem `try/except ImportError`; sem re-export/barrel novo (só o `__all__` existente). **Não commitado**, **sem worktree** (in-place no `feat/mobile-pwa-offline`).
- **Não tocados** (escopo S31): model `WebPushSubscription`, migração `0044`, settings `VAPID_*`, `requirements.txt`, dependências do `pyproject.toml`.
- **Próxima sessão (S33)**: frontend Web Push UI — anexar handlers `push`/`notificationclick` no bloco-marcador de `app/sw.ts`, hook `use-web-push.ts` e toggle `push-toggle.tsx`, consumindo `/api/web-push/{vapid-public-key,subscribe,unsubscribe}/` com o shape `{ endpoint, keys: { p256dh, auth } }` (= `subscription.toJSON()`) e mapeando `data.screen` (`proofs`/`payments`) → rota via `SCREEN_TO_PATH`.

### Sessão 33 — Arquivos Criados/Modificados (concluída)
- **Criados**:
  - `frontend/lib/api/hooks/use-web-push.ts` — `urlBase64ToUint8Array(base64): Uint8Array<ArrayBuffer>` (helper puro: padding `=`, `-`→`+`/`_`→`/`, `atob`, `charCodeAt`; o `ArrayBuffer` explícito satisfaz `applicationServerKey: BufferSource` sob a lib `dom` estrita, **sem** `as`) + hook `useWebPush(): UseWebPushResult`. **Suporte**: `'serviceWorker' in navigator && 'PushManager' in window` (guards `typeof` SSR-safe) → sem suporte ⇒ `permission='unsupported'` e callbacks no-op. **Estado inicial** (`useEffect`, flag `cancelled` no cleanup): lê `Notification.permission` e `(await navigator.serviceWorker.ready).pushManager.getSubscription()`. **`subscribe`** (`useCallback`): `Notification.requestPermission()` → se `!== 'granted'` seta `permission` e retorna (sem POST); senão `apiClient.get('/web-push/vapid-public-key/')` → `pushManager.subscribe({ userVisibleOnly:true, applicationServerKey })` → `apiClient.post('/web-push/subscribe/', subscription.toJSON())` (body **exato** `{ endpoint, keys:{p256dh,auth} }`) → `isSubscribed=true`/`permission='granted'`. **`unsubscribe`**: `getSubscription()` (null ⇒ no-op) → `subscription.unsubscribe()` → `apiClient.post('/web-push/unsubscribe/', { endpoint })` → `isSubscribed=false`. `isPending` envolve as duas janelas async via `try/finally`. **Decisão (KISS/YAGNI)**: a VAPID key é buscada **inline** dentro de `subscribe` (uso transitório), **não** via `useQuery` — evita duplicar estado de browser no cache de query (conforme o prompt: "não force tudo em useMutation", "não duplicar em cache de query"). Toda chamada HTTP usa `apiClient` (nunca `axios`/`fetch` cru).
  - `frontend/components/notifications/push-toggle.tsx` — `PushToggle` (`'use client'`) apresentacional: consome **apenas** `useWebPush()` (zero `apiClient`/axios no componente). Radix `Switch` (`checked={isSubscribed}`, `disabled={!isSupported || permission==='denied' || isPending}`, `aria-label="Ativar notificações"`); `onCheckedChange` → `subscribe()`+`toast.success('Notificações ativadas')` / `unsubscribe()`+`toast.success('Notificações desativadas')`, erro → `toast.error(getErrorMessage(err, 'Erro ao atualizar notificações'))`. 4 estados com **texto + ícone** (status nunca só por cor): não suportado (`BellOff` + "não são suportadas neste navegador"), negado (`AlertCircle` + "bloqueada — habilite nas configurações"), inscrito (`Bell` + "ativadas"), não inscrito (`BellOff` + "Ative para receber avisos no dispositivo").
  - `frontend/lib/api/hooks/__tests__/use-web-push.test.tsx` — 7 testes (boundary de browser montado por teste e removido no `afterEach`; HTTP via MSW): helper decodifica base64url (`instanceof Uint8Array` + length; bytes determinísticos de `'AAAA'`); não-suporte (`permission==='unsupported'`, `subscribe` sem POST via contador no handler); fluxo subscribe (`pushManager.subscribe` com `{userVisibleOnly, applicationServerKey:Uint8Array}` + POST com body **exato** `{endpoint,keys:{p256dh,auth}}` capturado no handler); permissão negada (sem POST); unsubscribe (`subscription.unsubscribe` chamado + POST `{endpoint}`); estado inicial inscrito.
  - `frontend/components/notifications/__tests__/push-toggle.test.tsx` — 5 testes (`renderWithProviders`, boundary de browser controlado como no hook — **hook NÃO mockado**): não suportado (texto + Switch `disabled`); negado (texto + `disabled`); toggle on → POST subscribe observado (contador no handler) + `toast.success('Notificações ativadas')`; inscrito → Switch `checked` + texto "ativadas", toggle off → POST unsubscribe + `toast.success('Notificações desativadas')`; erro de subscribe (handler 500 via `server.use`) → `toast.error`.
- **Modificados**:
  - `frontend/app/sw.ts` — **apenas anexados** (append) os 2 listeners no bloco-marcador `=== Web Push handlers (Sessão 33) ===`; o Serwist/precache/`defaultCache`/navigation fallback da S29 (linhas 1–31) ficaram **byte-for-byte intactos**. Adicionados: `interface PushPayload`; const `SCREEN_TO_PATH = { proofs:'/', payments:'/tenant/payments' }` (mapeia os valores bare do backend, fallback `/`); guard `parsePushPayload(raw: unknown): PushPayload | undefined` (narrowing por `typeof`/`in` — lava o `any` de `event.data?.json()` por `unknown` sem `as`, **e** elimina o `@typescript-eslint/no-unsafe-assignment` que surgiria ao atribuir o `any` direto); helper `screenToPath(data: unknown): string`; `focusOrOpen(path)` (`self.clients.matchAll({type:'window', includeUncontrolled:true})` → `find` por `new URL(client.url).pathname === path` → `client.focus()` senão `self.clients.openWindow(path)`). `addEventListener('push', …)` → `self.registration.showNotification(title, { body, icon:'/icons/icon-192.png', badge:'/icons/icon-192.png', data })`; `addEventListener('notificationclick', …)` → `event.notification.close()` + `focusOrOpen(screenToPath(event.notification.data))`. Tipos dos eventos **inferidos** do `ServiceWorkerGlobalScopeEventMap` (`push`→`PushEvent`, `notificationclick`→`NotificationEvent`) — **não** anotados com o inexistente `NotificationClickEvent`; **sem** `as`/`!`. Verificado sob `tsconfig.sw.json` (lib webworker).
  - `frontend/app/(dashboard)/settings/page.tsx` — novo `<Card>` "Notificações" (ícone `Bell`) com `<PushToggle />`, posicionado entre o card "Alterar Senha" e a `<Separator className="my-8" />` do locador; imports `Bell` (lucide) e `PushToggle` adicionados.
  - `frontend/app/tenant/profile/page.tsx` — novo `<Card>` "Notificações" (ícone `Bell`) com `<PushToggle />` no **topo** da `<div className="space-y-4">`, antes do card "Dados Pessoais"; imports `Bell` e `PushToggle` adicionados.
  - `frontend/tests/mocks/handlers.ts` — `webPushHandlers` (3 rotas wildcard `*/web-push/...`: GET `vapid-public-key` → `{ publicKey }`; POST `subscribe` ecoa o body com 201; POST `unsubscribe` → 204) + `...webPushHandlers` incluído no array `handlers`.
- **Tipos webworker confirmados na fonte** (`node_modules/typescript/lib/lib.webworker.d.ts`): `ServiceWorkerGlobalScopeEventMap` mapeia `"notificationclick": NotificationEvent` e `"push": PushEvent` (não existe `NotificationClickEvent`); `PushMessageData.json(): any`; `Notification.data: any` → narrado por `unknown`; `Clients.matchAll<{type:'window'}>` → `WindowClient[]` (tem `.focus()`/`.url`).
- **Carve-out de fixture de teste** (único uso de `as`, exatamente como `prompts/24-frontend-rent-calendar-ui.md`): nos `*.test.tsx`, o body parseado pelo MSW (`request.json()` tipado `DefaultBodyType` nesta versão) e o argumento capturado de `pushManager.subscribe.mock.calls[0]?.[0]` (tipo `any` de `vi.fn`) recebem `as <Tipo>` **restrito** à construção/leitura do boundary fake de browser/HTTP. Código de produção (hook/componente/sw) **sem** `as`/`!`.
- **Verificação (main tree, in-place)**:
  - `npx vitest run "lib/api/hooks/__tests__/use-web-push.test.tsx" "components/notifications/__tests__/push-toggle.test.tsx"` → **EXIT 0**, 12/12 verde (7 hook + 5 toggle).
  - `npx tsc --noEmit` (config principal) → **EXIT 0**.
  - `npx tsc --project tsconfig.sw.json --noEmit` (lib webworker, cobre `app/sw.ts`) → **EXIT 0**.
  - `npx eslint` (8 arquivos: `use-web-push.ts`, `push-toggle.tsx`, `app/sw.ts`, `settings/page.tsx`, `tenant/profile/page.tsx`, `handlers.ts`, + os 2 testes) → **EXIT 0**, zero erros/avisos.
  - Sem `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`; sem re-exports/barrel; sem dependência nova (Radix Switch/lucide/`apiClient`/TanStack já presentes). `as`/`!` ausentes em produção; único `as` é o carve-out de fixture nos testes. **Não commitado**, **sem worktree** (in-place no `feat/mobile-pwa-offline`).

> **Frente D / feature COMPLETA (Web Push end-to-end)**: S31 (model `WebPushSubscription` + migração `0044` + settings VAPID + dep `pywebpush`) → S32 (refator `notification_service` com `send_expo_push`/`send_web_push` + `WebPushViewSet` + rotas `/api/web-push/{vapid-public-key,subscribe,unsubscribe}/`) → S33 (SW handlers `push`/`notificationclick` + hook `useWebPush` + `PushToggle` em Settings/Profile). **Shape do payload de subscribe verificado idêntico entre S32 (backend lê `request.data` `{ endpoint, keys:{p256dh,auth} }` em `WebPushViewSet.subscribe`) e S33 (frontend envia `subscription.toJSON()` = `{ endpoint, keys:{p256dh,auth} }`)** — contrato cross-session honrado verbatim. `data.screen` do backend (`proofs`/`payments`, bare, pensado para o app Expo) mapeado para rotas web reais via `SCREEN_TO_PATH` (fallback `/`) **sem** alterar o backend. `app/sw.ts` recebeu **apenas** os listeners de push no bloco-marcador — toda a configuração Serwist/precache/offline da S29 permanece intacta. Com isso a feature "App Mobile Completo" (Sessões 26–33: responsividade + DataTable cards + PWA manifest/ícones + Service Worker + offline read-only + Web Push) está **encerrada**.

---

## Feature: Calendário de Controle de Aluguéis (Dashboard) — Sessões 21–25

**Design Doc**: `docs/plans/2026-06-02-rent-payment-calendar-design.md`
**Mockup**: `docs/mockups/rent-calendar-mockup.html` (light + dark)
**Status**: **CONCLUÍDA** (sessões 21–25 + unificação final). Web e mobile migrados para o toggle unificado; `mark_rent_paid` removido do backend.
**Ordem**: 21 → 22 → 23 → 24 → 25 (sequencial). Pós-25: consumidor `mobile/` (`use-admin-actions.ts` → `useToggleRentPayment` + tela `mark-paid.tsx`) migrado para `toggle_rent_payment`; `mark_rent_paid` e o import órfão `RentPayment` removidos de `core/views.py`. Verificado: ruff/format ok, 19 testes de API verdes, `tsc --noEmit` limpo nos arquivos mobile editados, zero referências remanescentes.

| # | Sessão | Status | Arquivo |
|---|--------|--------|---------|
| 21 | Backend: `RentScheduleService` + refactor DRY do `DailyControlService` | concluída | `prompts/21-backend-rent-schedule-service.md` |
| 22 | Backend: endpoints `rent_calendar` + `toggle_rent_payment` | concluída | `prompts/22-backend-rent-calendar-endpoints.md` |
| 23 | Frontend: hooks `use-rent-calendar` (optimistic) + query-keys + MSW | concluída | `prompts/23-frontend-rent-calendar-hooks.md` |
| 24 | Frontend: UI (5 componentes, grid date-fns) + montagem no dashboard | concluída | `prompts/24-frontend-rent-calendar-ui.md` |
| 25 | Refator consumidores (web `late-payments-alert` + mobile `mark-paid`) → toggle unificado; `mark_rent_paid` removido do backend + audit | concluída | `prompts/25-refactor-consumer-and-audit.md` |

> Reaproveita `RentPayment` (pago = registro existe), `FeeCalculatorService` (multa) e `DateCalculatorService`. Sem novo model/migration. Calendário admin-only; respeita `MonthSnapshot` finalizado.

### Sessão 21 — Arquivos Criados
- `core/services/rent_schedule_service.py` — `RentScheduleService` (6 `@staticmethod`: `clamp_due_day`, `effective_rental_value`, `collectible_leases`, `get_month_schedule`, `get_month_stats`, `toggle_payment`) + `received_total` (definição canônica) + `DAYS_OF_WEEK_PT` (fonte única)
- `tests/unit/test_financial/test_rent_schedule_service.py` — 34 testes unitários (clamp, valor efetivo, cobrabilidade date-aware, schedule/item, cross-month sem multa, stats, toggle + guards)

### Sessão 21 — Arquivos Modificados
- `core/services/daily_control_service.py` — `_collect_entries_by_day` (porção aluguel), `_get_expected_rent_total` e `_get_received_rent_total` delegam a `RentScheduleService`; `DAYS_OF_WEEK_PT` importado da fonte única; removido import morto `DateCalculatorService` e import não usado `Lease`
- `tests/unit/test_financial/test_daily_control_service.py` — **apenas** `start_date` da fixture `lease` (de `2025-01-01` para `2025-06-01`) para a janela cobrir mar/2026 sob o filtro date-aware; nenhum corpo/assert alterado

> **Nota Sessão 21**: Fonte única `RentScheduleService` (cobrabilidade date-aware, independe de `apartment.is_rented`); `DailyControlService` delega (DRY: `collectible_leases` + `received_total` único); fixture `lease` ajustada (`start_date`) para cobrir mar/2026; multa só no mês corrente (cross-month → `late_fee="0.00"`/`late_days=0`); 16 testes do DailyControl verdes; novo arquivo 100% mypy/pyright limpo; sem endpoints/frontend; `mark_rent_paid` removido apenas na Sessão 25. Falha pré-existente (não relacionada) em `tests/e2e/test_financial_workflow.py::test_daily_control_breakdown` (porção de installments/exits, fora do escopo desta sessão).

### Sessão 22 — Arquivos Criados
- `tests/integration/test_rent_calendar_api.py` — 19 testes de integração (View → Service → Model, sem mock de internals): `TestRentCalendarRead` (shape top-level/day/item/stats, filtro `building_id`, params inválidos 400, 401/403) + `TestToggleRentPayment` (cria↔soft-delete, recusa pago+dia-passou, mês finalizado bloqueia, params inválidos, 401/403)

### Sessão 22 — Arquivos Modificados
- `core/views.py` — `DashboardViewSet` ganha 2 actions finas: `rent_calendar` (GET) → `RentScheduleService.get_month_schedule`; `toggle_rent_payment` (POST) → `RentScheduleService.toggle_payment`. Import direto `from .services.rent_schedule_service import RentScheduleService` (sem re-export/barrel). Constantes `MIN_MONTH`/`MAX_MONTH` extraídas (validação de mês). `mark_rent_paid` **permanece intacto** (remoção só na Sessão 25). Linter autofixou 3 issues de estilo pré-existentes na action `generate_contract` (W293 ×2, RET505) — não relacionadas a esta sessão.
- `prompts/SESSION_STATE.md` — esta atualização.

> **Nota Sessão 22**:
> - `rent_calendar` e `toggle_rent_payment` expostos automaticamente pelo router (`core/urls.py` **inalterado**): `GET /api/dashboard/rent_calendar/?year=&month=&building_id=` e `POST /api/dashboard/toggle_rent_payment/` body `{lease_id, reference_month:"YYYY-MM-01"}`. Ambos admin-only (herdam `permission_classes=[IsAdminUser]` do ViewSet): não-admin → 403, não autenticado → 401.
> - **Mecanismo de sinalização de erro do service (para a Sessão 25)**: `RentScheduleService.toggle_payment` **NÃO lança exceção** — retorna sempre um `dict {status, is_paid, message}`. Recusa ⇒ `status == "error"` (mês finalizado / lease não-cobrável ou inexistente / pago+dia-passou). A view mapeia `status == "error"` → **HTTP 400** `{"error": result["message"]}` (mensagens em PT); sucesso → **HTTP 200** com o dict completo. Não há caso 404 dedicado: lease inexistente cai em "não é cobrável" → 400 (conforme o service sinaliza). `get_month_schedule` apenas retorna `dict` (sem erros de negócio).
> - **Throttling em testes**: DRF liga `SimpleRateThrottle.timer = time.time` como atributo de classe; sob `freezegun` é chamado como método ligado (`fake_time(self)`) e quebra. Fixture autouse `_disable_throttling` em `test_rent_calendar_api.py` desabilita throttle (boundary de infra externa) via `override_settings(REST_FRAMEWORK=...)` preservando auth. Mesma incompatibilidade afeta tests pré-existentes que combinam `@freeze_time` + API client (ex.: `tests/e2e/test_financial_lifecycle.py`) — fora do escopo desta sessão.
> - Erros pré-existentes (não relacionados) ao rodar lint/type em `core/views.py`: pyright/mypy apontam `generate_contract_pdf.delay(...)` (celery `shared_task` sem stubs) na action `generate_contract` — presentes no HEAD antes desta sessão; o código novo (`rent_calendar`/`toggle_rent_payment`) é 100% limpo.

### Sessão 23 — Arquivos Criados
- `frontend/lib/api/hooks/use-rent-calendar.ts` — `useRentCalendar(year, month, buildingId?)` (`useQuery`, `staleTime` 30s, repassa `building_id` só quando definido) + `useToggleRentPayment()` (`useMutation` optimistic v5) + tipos TS hand-written (`RentCalendar`, `RentCalendarDay`, `RentCalendarItem`, `RentCalendarStats`, `ToggleRentPaymentRequest`, `ToggleRentPaymentResponse`) exportados via `export type`. Função pura `flipPaidByLease` (flip imutável reutilizado no optimistic update).
- `frontend/lib/api/hooks/__tests__/use-rent-calendar.test.tsx` — 6 testes Vitest+MSW (fetch/shape com os 9 campos de stats; `building_id` repassado na query string; optimistic flip observável; rollback no erro discriminante; invalidação no settle das 3 keys).
- `frontend/tests/mocks/data/rent-calendar.ts` — `createMockRentCalendar` + `createMockRentCalendarItem` (importam os tipos do hook; **não** entram no barrel `data/index.ts`).

### Sessão 23 — Arquivos Modificados
- `frontend/lib/api/query-keys.ts` — grupo `rentCalendar` (`all: ['rent-calendar']` + `month(year, month, buildingId?)` com `buildingId ?? null` para estabilizar a key).
- `frontend/tests/mocks/handlers.ts` — `rentCalendarHandlers` (`GET /dashboard/rent_calendar/` lendo `year`/`month`/`building_id`; `POST /dashboard/toggle_rent_payment/` com `await delay(100)` e mensagem PT), importando `createMockRentCalendar` direto de `./data/rent-calendar`; incluído `...rentCalendarHandlers` no array `handlers`.

> **Nota Sessão 23**:
> - Optimistic update v5 sobre **toda** a área `rentCalendar.all` via `getQueriesData`/`setQueryData` — a mutation **não** conhece year/month/buildingId; `onMutate` cancela + snapshota + faz flip imutável (`flipPaidByLease`), `onError` restaura o snapshot, `onSettled` invalida `rentCalendar` + `dashboard.latePaymentSummary` + `dashboard.financialSummary`.
> - **Teste de flip determinístico sem mock de internals**: `createTestQueryClient` tem `gcTime:0`, então dado semeado via `setQueryData` sem observador é coletado num tick. Solução correta (exercita o caminho real query→cache→mutation): o handler GET popula o cache e um `useRentCalendar` montado mantém a entrada viva; o POST é sobrescrito com `delay(200)` para abrir a janela e o flip é asserido via `waitFor` lendo `queryClient.getQueryData(...)`. No teste de rollback, o refetch do `onSettled` é adiado (`delay`) e retorna `is_paid:true` (1º GET=false, GETs seguintes=true) — assim o `false` observado após o erro só pode vir do rollback, não do refetch; depois aguarda o refetch settlar para não deixar request pendente no teardown.
> - `useMarkRentPaid` (`use-dashboard.ts`) e o endpoint `mark_rent_paid` permanecem **intactos** — removidos só na Sessão 25 (sem backward-compat shim; remoção deliberadamente adiada para manter todas as sessões verdes). Nenhuma UI nesta sessão. 6 testes passando; `type-check` e `lint` limpos.

### Sessão 24 — Arquivos Criados
- `frontend/app/(dashboard)/_components/rent-calendar/rent-calendar-section.tsx` — container `'use client'` (estado `{year,month}` + dia selecionado derivado de `data.today`, filtro de prédio via `useBuildings`, grid `grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr]`); único componente que consome hooks (`useRentCalendar`/`useToggleRentPayment`); deriva `reference_month` = `"YYYY-MM-01"` do mês carregado; sucesso → `toast.success`, erro → `handleError`.
- `frontend/app/(dashboard)/_components/rent-calendar/rent-month-grid.tsx` — grade custom `date-fns` (`startOfMonth`/`getDay`/`getDaysInMonth`), células `role="gridcell"` com `aria-label`/`aria-selected`, chips por status, hoje (badge primary) e selecionado destacados, nav de mês, legenda.
- `frontend/app/(dashboard)/_components/rent-calendar/rent-day-panel.tsx` — itens do dia (StatusChip pago/a vencer/em atraso com ícone+rótulo), highlight de atraso + multa, "Pago em DD/MM" via split ISO, `RentPaymentToggle` por item (deriva `disabledReason`), botões "Hoje"/"Próx. vencimento", empty state, `TooltipProvider` na árvore.
- `frontend/app/(dashboard)/_components/rent-calendar/rent-stats-panel.tsx` — 4 cards (Mês via `formatMonthYear`, Recebido, A receber c/ trecho de atraso condicional, Kitnets vagos).
- `frontend/app/(dashboard)/_components/rent-calendar/rent-payment-toggle.tsx` — Radix Switch apresentacional + Tooltip com `disabledReason` (aria-label) quando bloqueado.
- `frontend/app/(dashboard)/_components/rent-calendar/__tests__/*.test.tsx` — 5 arquivos, 28 testes (toggle, day-panel, month-grid, stats, section). Section mocka só a fronteira de dados (`useRentCalendar`/`useToggleRentPayment`/`useBuildings`) via `vi.spyOn`.

### Sessão 24 — Arquivos Modificados
- `frontend/app/(dashboard)/page.tsx` — `<RentCalendarSection />` montado no topo da `<div className="space-y-6">`, acima de `<FinancialSummaryWidget />`.

> **Nota Sessão 24**:
> - **`formatMonthYear` retorna "Junho de 2026" (com " de "), não "Junho/2026"** neste ambiente (ICU do Node/jsdom). O prompt previa barra; a regra do projeto manda asserir a saída real. Os testes asseram `formatMonthYear(year, month)` (DRY/robusto a build de ICU) em vez de string literal.
> - **Acessibilidade da grade**: células de dia são `role="gridcell"` dentro de `role="grid"`; seleção via `aria-selected` (não `aria-pressed`, inválido em gridcell). Status nunca só por cor — sempre ícone + rótulo.
> - `late-payments-alert.tsx`, `use-dashboard.ts`/`useMarkRentPaid` e o endpoint backend `mark_rent_paid` permanecem **intactos** — refator do consumidor unificado + remoção do `mark_rent_paid` é a **Sessão 25**.
> - Verificação: `npx vitest run "app/(dashboard)/_components/rent-calendar"` 28/28 verde; `tsc --noEmit` sem erros nos arquivos tocados; `eslint` zero erros/avisos. Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção (apenas em helpers de fixture de teste, conforme carve-out).

### Sessão 25 — Arquivos Modificados
- `frontend/app/(dashboard)/_components/late-payments-alert.tsx` — consumidor web migrado para o toggle unificado: importa `useToggleRentPayment` de `@/lib/api/hooks/use-rent-calendar` (não mais `useMarkRentPaid`); `handleMarkPaid` chama `toggle.mutate({ lease_id, reference_month })` com `reference_month` = primeiro dia do **mês corrente** (`YYYY-MM-01`, via helper `currentReferenceMonth()` — mesma semântica do antigo `mark_rent_paid`, que sempre lançava o mês corrente); `disabled={toggle.isPending}`. Sem invalidação duplicada (o hook já invalida `rentCalendar` + `latePaymentSummary` + `financialSummary` no `onSettled`).
- `frontend/lib/api/hooks/use-dashboard.ts` — `useMarkRentPaid` (create-only, postava `/dashboard/mark_rent_paid/`) **removido** por completo, sem re-export/shim/alias; import trimado de `{ useMutation, useQuery, useQueryClient }` para apenas `{ useQuery }` (os 5 hooks restantes só usam `useQuery`); `queryKeys` mantido (ainda usado pelas queries). Nenhum import órfão.
- `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx` — mocka `useToggleRentPayment` de `@/lib/api/hooks/use-rent-calendar` (fronteira de dados via `vi.spyOn`); novo teste de regressão expande o accordion e clica "Pago", asserindo `toggle.mutate` chamado com `{ lease_id: 1, reference_month }` casando `^\d{4}-\d{2}-01$`. 5 testes verdes.
- `prompts/SESSION_STATE.md` / `prompts/ROADMAP.md` — esta atualização (feature web 21–25 + decisão saída B sobre o mobile).

> **Nota Sessão 25 — Gate mobile (saída B escolhida)**:
> - **Tensão de design escalada**: o app `mobile/` é um **consumidor vivo** do endpoint que esta sessão removeria — `mobile/lib/api/hooks/use-admin-actions.ts:37` (`useMarkRentPaid`) e `mobile/app/(admin)/actions/mark-paid.tsx:5,14` postam em `POST /dashboard/mark_rent_paid/` (com body `{ lease_id, reference_month, amount_paid }` — note `amount_paid`, que o endpoint `toggle_rent_payment` **não** aceita). O design doc (§2/§4.3/§8) **não escopou** o mobile, e `mobile/package.json` define apenas `start`/`android`/`ios`/`web` — **sem `type-check`/`lint`/test runner**, logo qualquer migração mobile seria **inverificável** (violaria o TDD Red→Green e a regra de zero-tolerância a warnings).
> - **Decisão: saída (B)** — concluída **apenas** a migração web + auditoria. **`mark_rent_paid` (backend, `core/views.py`) e o consumidor mobile permanecem intactos.** A remoção de `mark_rent_paid` está **BLOQUEADA** por esta tensão. `core/views.py` **não foi tocado** nesta sessão; nenhum arquivo de `mobile/` foi tocado.
> - **Risco documentado**: enquanto `mark_rent_paid` existir e o mobile não for migrado/verificado, há divergência (web usa `toggle_rent_payment`, mobile usa `mark_rent_paid`). O `mobile/` não tem rede de segurança automatizada (sem testes/type-check/lint), então uma migração futura **deve primeiro** configurar verificação em `mobile/package.json`.
> - **Destravamento (saída A futura)**: emendar o design doc (§2 incluir o consumidor mobile, §4.3 descrever a migração, §8 criar sessão dedicada) **e** configurar `type-check`/`lint`/test runner em `mobile/package.json`; só então uma sessão escopada migra o mobile para `toggle_rent_payment` e remove `mark_rent_paid` do backend (+ limpeza de imports mortos `RentPayment`/`cast`/`User` em `core/views.py`).
> - **Audit (design §2/§8, escopo web)**: feature web completa — `RentScheduleService` (§4.1) + refactor DRY `DailyControlService` (§4.2) [S21], endpoints `rent_calendar`/`toggle_rent_payment` (§4.3) [S22], `use-rent-calendar` (hook + toggle optimistic) + grupo `rentCalendar` em query-keys (§6) [S23], 5 componentes do calendário + montagem em `page.tsx` (§6) [S24], consumidor web legado migrado (§4.3) [S25]. Sem referência morta a `mark_rent_paid`/`useMarkRentPaid` em `frontend/` (grep limpo). Único item de §4.3 não realizado — remoção de `mark_rent_paid` — registrado como **pendência de design** (saída B), não gap de implementação.
> - **Verificação**: `npm run lint` (frontend inteiro) zero erros/avisos; `npm run type-check` (`tsc --noEmit`) limpo; `npm run test:unit` em `late-payments-alert.test.tsx` (5) + `use-dashboard.test.tsx` (10) = 15/15 verde. Backend não rodado (não tocado nesta sessão). Sem `# noqa`/`eslint-disable`/`@ts-ignore`.

---

## Progresso por Sessão

| # | Sessão | Status | Notas |
|---|--------|--------|-------|
| 01 | Backend: Models + Migration + Tests | concluída | 10 models + 2 campos adicionados, 44 testes passando |
| 02 | Backend: Serializers + Tests | concluída | 10 serializers + alterações em ApartmentSerializer/LeaseSerializer (testes pendentes) |
| 03 | Backend: ViewSets Simples + Tests | concluída | 4 ViewSets + 4 rotas + 23 testes passando |
| 04 | Backend: Expense ViewSets + Tests | concluída | 2 ViewSets + 2 rotas + 33 testes passando |
| 05 | Backend: Income/Payment ViewSets + Tests | concluída | 4 ViewSets + 4 rotas + 33 testes passando |
| 06 | Backend: CashFlowService + Tests | concluída | CashFlowService implementado |
| 07 | Backend: FinancialDashboardService + Tests | concluída | 6 métodos, 21 testes passando |
| 08 | Backend: SimulationService + Endpoints + Tests | concluída | SimulationService (6 cenários + compare), FinancialDashboardViewSet (6 endpoints), CashFlowViewSet (4 endpoints), 56 testes passando |
| 09 | Frontend: Schemas + API Hooks | concluída | 10 schemas + 11 hooks + 4 test files (16 testes), MSW handlers, type-check + lint clean |
| 10 | Frontend: Navegação + Páginas Base | concluída | Sidebar expansível, 4 páginas (Persons CRUD + cartões, Categories CRUD hierárquica, Settings singleton, Financial placeholder), use-financial-settings hook, type-check + build clean |
| 11 | Frontend: Página de Despesas | concluída | 5 componentes (columns, filters, form-modal, installments-drawer, page), smart form por tipo, cascata pessoa→cartão, drawer de parcelas, type-check + build clean |
| 12 | Frontend: Income + RentPayments + Employees | concluída | 3 páginas CRUD (incomes, rent-payments, employees), 3 form modals, filtros cascata building→apartment, month picker, real-time total, type-check + build clean |
| 13 | Frontend: Dashboard Financeiro | concluída | 6 widgets (BalanceCards, CashFlowChart, PersonSummaryCards, UpcomingInstallments, OverdueAlerts, CategoryBreakdownChart), interfaces corrigidas para match backend, type-check + build clean |
| 14 | Frontend: Simulador | concluída | 6 componentes (scenario-builder, scenario-card, comparison-chart, comparison-table, impact-summary, page), useSimulation interfaces corrigidas para match backend, MSW handler atualizado, type-check + build + lint clean |
| 15 | Permissões + E2E Tests + Polish | concluída | FinancialReadOnly permission, IsAuthenticated para Dashboard/CashFlow, is_staff no frontend, conditional UI em 7 páginas, export Excel (despesas/receitas/pagamentos), 6 E2E tests + 3 simulation tests, type-check + lint + build clean |
| 16 | Backend: Correções críticas + gaps | concluída | except syntax fix (ObjectDoesNotExist), end_date Expense + migration 0016, is_offset filtering em 4 queries, fixed_total em person_summary, 11 testes regressão |
| 17 | Frontend: Schemas/hooks/interfaces fixes | concluída | PersonPayment schema+hook, PersonIncome hook, CashFlowMonth+PersonSummary interfaces corrigidas, is_offset em expense schema+form+mocks, MSW handlers |
| 18 | Frontend: PersonPayments page + is_offset toggle | concluída | Página pagamentos a pessoas (summary cards + tabela), PersonMonthSummary reutilizável, PersonSummaryCards atualizado com usePersonSummary, is_offset toggle, form modal, type-check + build + lint clean |
| 19 | Frontend: Controle Diário | concluída | DailyControlService (3 métodos) + DailyControlViewSet (3 endpoints) + 16 testes passando + página com 4 widgets (summary cards, balance chart, timeline, day drawer) + filtros (tipo/status/pessoa/prédio) + mark-paid inline + type-check + build + lint clean |
| 20 | Frontend: PersonIncome page + E2E + Polish | concluída | PersonIncome CRUD page + form modal adaptativo (rent/stipend), 5 novos E2E tests (11 total), sidebar link, polish verification, type-check + build + lint clean |

---

### Sessão 17 — Arquivos Criados
- `frontend/lib/schemas/person-payment.schema.ts` — PersonPayment schema + type
- `frontend/lib/api/hooks/use-person-payments.ts` — CRUD hooks (4) + PersonPaymentFilters
- `frontend/lib/api/hooks/use-person-incomes.ts` — CRUD hooks (4) + PersonIncomeFilters
- `frontend/tests/mocks/data/person-payments.ts` — mock data + factory

### Sessão 17 — Arquivos Modificados
- `frontend/lib/schemas/expense.schema.ts` — adicionado `is_offset`
- `frontend/lib/api/hooks/use-cash-flow.ts` — CashFlowMonth interface corrigida (income/expenses/balance nested), PersonSummary corrigida (receives, card_total, loan_total, offset_total, fixed_total, net_amount, total_paid, pending_balance)
- `frontend/tests/mocks/handlers.ts` — handlers person-payments + person-incomes, cash-flow/monthly + person_summary atualizados para novas interfaces
- `frontend/tests/mocks/data/index.ts` — exporta person-payments
- `frontend/tests/mocks/data/expenses.ts` — is_offset adicionado em mock data
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — assertions atualizadas para nova CashFlowMonth
- `frontend/lib/api/hooks/__tests__/use-expenses.test.tsx` — is_offset no create mutation test
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — is_offset no form schema, defaultValues e reset

### Sessão 20 — Arquivos Criados
- `frontend/app/(dashboard)/financial/person-incomes/page.tsx` — CRUD PersonIncome (filtros pessoa/tipo/status, colunas adaptativas rent/stipend)
- `frontend/app/(dashboard)/financial/person-incomes/_components/person-income-form-modal.tsx` — Form modal adaptativo (apartment_rent: select apt + lease info, fixed_stipend: input R$)

### Sessão 20 — Arquivos Modificados
- `frontend/lib/utils/constants.ts` — FINANCIAL_PERSON_INCOMES rota adicionada
- `frontend/components/layouts/sidebar.tsx` — Link "Rendimentos" no submenu financeiro
- `tests/e2e/test_financial_workflow.py` — 5 novos testes E2E (person_payment_flow, offset_reduces_person_total, cash_flow_projection_with_end_date, daily_control_breakdown, subcategory_expense)

### Sessão 19 — Arquivos Criados
- `core/services/daily_control_service.py` — DailyControlService com 3 métodos (breakdown, summary, mark_paid)
- `tests/unit/test_financial/test_daily_control_service.py` — 16 testes (7 breakdown + 3 summary + 6 mark_paid)
- `frontend/lib/api/hooks/use-daily-control.ts` — useDailyBreakdown, useDailySummary, useMarkItemPaid hooks
- `frontend/app/(dashboard)/financial/daily/page.tsx` — Página controle diário com navegação mês, filtros, chart + timeline
- `frontend/app/(dashboard)/financial/daily/_components/daily-summary-cards.tsx` — 4 cards (saldo, recebido, pago, vencidas)
- `frontend/app/(dashboard)/financial/daily/_components/daily-balance-chart.tsx` — ComposedChart com barras + linha saldo acumulado
- `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx` — Timeline agrupada por dia com status visual + mark-paid inline
- `frontend/app/(dashboard)/financial/daily/_components/day-detail-drawer.tsx` — Sheet drawer detalhe do dia

### Sessão 19 — Arquivos Modificados
- `core/viewsets/financial_dashboard_views.py` — DailyControlViewSet adicionado (breakdown, summary, mark_paid endpoints)
- `core/viewsets/__init__.py` — export DailyControlViewSet
- `core/urls.py` — rota `daily-control` registrada
- `frontend/lib/utils/constants.ts` — FINANCIAL_DAILY rota adicionada
- `frontend/components/layouts/sidebar.tsx` — Link "Controle Diário" no submenu financeiro

### Sessão 18 — Arquivos Criados
- `frontend/app/(dashboard)/financial/person-payments/page.tsx` — Página com resumo mensal por pessoa + tabela histórico pagamentos
- `frontend/app/(dashboard)/financial/person-payments/_components/person-payment-form-modal.tsx` — Form modal create/edit pagamento
- `frontend/app/(dashboard)/financial/_components/person-month-summary.tsx` — Componente reutilizável breakdown completo pessoa/mês

### Sessão 18 — Arquivos Modificados
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — Reescrito para usar usePersonSummary (antes usava useDebtByPerson)
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — Toggle is_offset para card_purchase/bank_loan/personal_loan
- `frontend/lib/utils/constants.ts` — FINANCIAL_PERSON_PAYMENTS rota adicionada
- `frontend/components/layouts/sidebar.tsx` — Link "Pgto. Pessoas" no submenu financeiro

### Sessão 16 — Arquivos Criados
- `tests/unit/test_financial/test_gap_fixes.py` — 11 testes de regressão (4 classes)
- `core/migrations/0016_add_expense_end_date.py` — adiciona end_date ao Expense

### Sessão 16 — Arquivos Modificados
- `core/models.py` — end_date adicionado ao Expense
- `core/serializers.py` — end_date adicionado ao ExpenseSerializer.fields
- `core/services/simulation_service.py` — except syntax fixado com ObjectDoesNotExist, removido Lease import
- `core/services/cash_flow_service.py` — _collect_fixed_expenses com end_date+is_offset+person, _collect_utility_bills com is_offset, _get_projected_expenses com is_offset, get_person_summary com fixed_total
- `core/services/financial_dashboard_service.py` — get_expense_category_breakdown com is_offset

## Decisões Arquiteturais

1. Migration gerada como `0012_add_financial_module.py` (não 0009, pois já existiam 0009-0011)
2. `FinancialSettings.save()` usa `force_update` quando pk=1 já existe (singleton pattern)
3. `FinancialSettings` não herda AuditMixin/SoftDeleteMixin — tem apenas `updated_at`/`updated_by` próprios
4. `from __future__ import annotations` removido de `financial_views.py` — Python 3.14 tem PEP 649 nativamente. Regra TC (flake8-type-checking) desabilitada no ruff. Target-version atualizado para py314.
5. SimulationService com dois modos: `simulate()` (pure dict-based, unit testável sem DB) e `simulate_from_db()` (resolve parâmetros via DB, usado pelo endpoint). O `compare()` é puro e funciona com ambos.
6. FinancialDashboardViewSet e CashFlowViewSet em `financial_dashboard_views.py` (não em `financial_views.py` que contém apenas ViewSets CRUD).
7. `PersonSimple` schema em `credit-card.schema.ts` (não em `person.schema.ts`) para evitar dependência circular Person→CreditCard→Person. Person importa CreditCard; schemas que precisam de person nested (expense, income, etc.) importam PersonSimple de credit-card.schema.ts.
8. `ExpenseCategory` usa `z.lazy()` para suportar subcategories recursivas no schema Zod.
9. Interfaces dos hooks `use-financial-dashboard.ts` e `use-cash-flow.ts` foram corrigidas na sessão 13 para match com os campos reais do backend (sessão 09 criou interfaces especulativas que divergiam dos endpoints implementados nas sessões 07-08).
10. Expense form schema usa `z.boolean()` e `z.string()` (sem `.default()` ou `.optional()`) para compatibilidade com `zodResolver` — validação condicional por tipo feita manualmente no `handleSubmit` via `validateConditionalFields()` em vez de `superRefine` (que causa type mismatch com React Hook Form).
11. Em Zod 4, `z.number({ required_error: '...' })` não é válido — usar `z.number().min(1, '...')` ou `z.number({ error: '...' })`. Também evitar `.optional().default('')` em form schemas, preferir `.default('')` ou plain type com defaultValues no useForm.
12. `useSimulation` hook (sessão 09) tinha interfaces especulativas (`name` em vez de `type`, `results` em vez de `base/simulated/comparison`) — corrigidas na sessão 14 para match com o endpoint real `POST /api/cash-flow/simulate/` implementado na sessão 08. Cenários usam `type` (SimulationScenarioType union) e resposta retorna `{ base, simulated, comparison }`.
13. Simulador usa `useRef` para estabilizar `simulation.mutate` sem eslint-disable — padrão seguro para evitar deps infinitas em callbacks que chamam mutations.
14. `FinancialReadOnly` permission criada em `core/permissions.py` — idêntica em lógica a `ReadOnlyForNonAdmin` mas nomeada especificamente para o módulo financeiro. Aplicada em todos os CRUD ViewSets financeiros.
15. `FinancialDashboardViewSet` e `CashFlowViewSet` usam `IsAuthenticated` (não `FinancialReadOnly`) — qualquer usuário autenticado pode ler dashboard e rodar simulações.
16. `FinancialSettingsViewSet` mudou de `IsAdminUser` para `FinancialReadOnly` — non-admin pode ler configurações mas não alterar.
17. `is_staff` adicionado ao `User` interface no frontend (`auth-store.ts`) — usado para conditional rendering de botões de ação (criar/editar/excluir/marcar como pago).
18. `except (A, B):` em Python 3.14 é reformatado por ruff para `except A, B:` que tem semântica diferente (PEP 758: catch A, assign to B). Workaround: usar `except ObjectDoesNotExist:` (base class Django) em vez de `except (Apartment.DoesNotExist, Lease.DoesNotExist):`.

## Arquivos Criados

### Backend
- `tests/unit/__init__.py`
- `tests/unit/test_financial/__init__.py`
- `tests/unit/test_financial/test_financial_models.py` — 44 testes
- `tests/unit/test_financial/test_financial_dashboard_service.py` — 21 testes
- `core/migrations/0012_add_financial_module.py`
- `core/services/financial_dashboard_service.py` — 6 métodos estáticos
- `tests/integration/__init__.py`
- `tests/integration/test_financial_api_simple.py` — 23 testes
- `core/viewsets/financial_views.py` — PersonViewSet, CreditCardViewSet, ExpenseCategoryViewSet, FinancialSettingsViewSet

- `tests/integration/test_expense_api.py` — 33 testes (Expense + ExpenseInstallment API)
- `tests/integration/test_income_payment_api.py` — 33 testes (Income, RentPayment, EmployeePayment, PersonIncome API)
- `core/services/simulation_service.py` — SimulationService com 6 cenários (simulate + simulate_from_db + compare)
- `core/viewsets/financial_dashboard_views.py` — FinancialDashboardViewSet (6 endpoints) + CashFlowViewSet (4 endpoints)
- `tests/unit/test_financial/test_simulation_service.py` — 30 testes
- `tests/integration/test_financial_dashboard_api.py` — 15 testes
- `tests/integration/test_cash_flow_api.py` — 11 testes
- `tests/e2e/__init__.py`
- `tests/e2e/test_financial_workflow.py` — 6 testes E2E (workflow completo, owner, prepaid, salary_offset, permissions, bulk_mark_paid)

### Frontend
- `frontend/lib/schemas/person.schema.ts` — Person schema + type
- `frontend/lib/schemas/credit-card.schema.ts` — CreditCard + PersonSimple schemas + types
- `frontend/lib/schemas/expense-category.schema.ts` — ExpenseCategory schema (recursive via z.lazy)
- `frontend/lib/schemas/expense-installment.schema.ts` — ExpenseInstallment schema
- `frontend/lib/schemas/expense.schema.ts` — Expense schema (nested person/card/building/category/installments)
- `frontend/lib/schemas/income.schema.ts` — Income schema
- `frontend/lib/schemas/rent-payment.schema.ts` — RentPayment schema
- `frontend/lib/schemas/employee-payment.schema.ts` — EmployeePayment schema
- `frontend/lib/schemas/financial-settings.schema.ts` — FinancialSettings schema
- `frontend/lib/schemas/person-income.schema.ts` — PersonIncome schema
- `frontend/lib/api/hooks/use-persons.ts` — CRUD hooks (5)
- `frontend/lib/api/hooks/use-credit-cards.ts` — CRUD hooks (5)
- `frontend/lib/api/hooks/use-expense-categories.ts` — CRUD hooks (5)
- `frontend/lib/api/hooks/use-expenses.ts` — CRUD (4) + useMarkExpensePaid + useGenerateInstallments
- `frontend/lib/api/hooks/use-expense-installments.ts` — useExpenseInstallments + useMarkInstallmentPaid + useBulkMarkInstallmentsPaid
- `frontend/lib/api/hooks/use-incomes.ts` — CRUD (4) + useMarkIncomeReceived
- `frontend/lib/api/hooks/use-rent-payments.ts` — CRUD hooks (4)
- `frontend/lib/api/hooks/use-employee-payments.ts` — CRUD (4) + useMarkEmployeePaymentPaid
- `frontend/lib/api/hooks/use-financial-dashboard.ts` — 6 dashboard query hooks (staleTime 5min)
- `frontend/lib/api/hooks/use-cash-flow.ts` — useMonthlyCashFlow + useCashFlowProjection + usePersonSummary
- `frontend/lib/api/hooks/use-simulation.ts` — useSimulation (useMutation)
- `frontend/tests/mocks/data/persons.ts` — mock person data + factory
- `frontend/tests/mocks/data/expenses.ts` — mock expense data + factory
- `frontend/lib/api/hooks/__tests__/use-persons.test.tsx` — 4 testes
- `frontend/lib/api/hooks/__tests__/use-expenses.test.tsx` — 6 testes
- `frontend/lib/api/hooks/__tests__/use-financial-dashboard.test.tsx` — 3 testes
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — 2 testes (simulation movido para arquivo próprio)
- `frontend/lib/api/hooks/__tests__/use-simulation.test.tsx` — 3 testes (scenarios, empty, error)

- `frontend/app/(dashboard)/financial/page.tsx` — Placeholder page
- `frontend/app/(dashboard)/financial/persons/page.tsx` — CRUD Pessoas (8 colunas, badges, useCrudPage)
- `frontend/app/(dashboard)/financial/persons/_components/person-form-modal.tsx` — Form modal (create/edit com Switch e Select)
- `frontend/app/(dashboard)/financial/persons/_components/credit-card-section.tsx` — Seção inline de cartões (create/delete)
- `frontend/app/(dashboard)/financial/categories/page.tsx` — CRUD Categorias (hierárquica com indentação)
- `frontend/app/(dashboard)/financial/categories/_components/category-form-modal.tsx` — Form modal (color picker, parent select, cor herdada)
- `frontend/app/(dashboard)/financial/settings/page.tsx` — Formulário singleton (GET/PUT)
- `frontend/lib/api/hooks/use-financial-settings.ts` — useFinancialSettings + useUpdateFinancialSettings

- `frontend/app/(dashboard)/financial/expenses/page.tsx` — Página de despesas com CRUD, filtros, drawer
- `frontend/app/(dashboard)/financial/expenses/_components/expense-columns.tsx` — 11 colunas com badges, formatação
- `frontend/app/(dashboard)/financial/expenses/_components/expense-filters.tsx` — 7 filtros com cascata pessoa→cartão
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — Smart form adaptativo por tipo (9 tipos)
- `frontend/app/(dashboard)/financial/expenses/_components/installments-drawer.tsx` — Sheet drawer com mark paid

- `frontend/app/(dashboard)/financial/incomes/page.tsx` — CRUD Receitas (9 colunas, filtros inline, mark_received)
- `frontend/app/(dashboard)/financial/incomes/_components/income-form-modal.tsx` — Form modal (create/edit, is_recurring toggle)
- `frontend/app/(dashboard)/financial/rent-payments/page.tsx` — CRUD Pagamentos Aluguel (6 colunas, cascata building→apartment, month range)
- `frontend/app/(dashboard)/financial/rent-payments/_components/rent-payment-form-modal.tsx` — Form modal (lease select formatado, month picker→YYYY-MM-01)
- `frontend/app/(dashboard)/financial/employees/page.tsx` — CRUD Funcionários (9 colunas, mark_paid, total bold)
- `frontend/app/(dashboard)/financial/employees/_components/employee-payment-form-modal.tsx` — Form modal (is_employee filter, real-time total via watch)

- `frontend/app/(dashboard)/financial/_components/balance-cards.tsx` — 4 stat cards com cor condicional
- `frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx` — ComposedChart 12 meses (Bar + Line)
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — Grid de cards por pessoa
- `frontend/app/(dashboard)/financial/_components/upcoming-installments.tsx` — Lista scrollable com highlights
- `frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx` — Alertas vencidos ou mensagem positiva
- `frontend/app/(dashboard)/financial/_components/category-breakdown-chart.tsx` — PieChart com cores das categorias

- `frontend/app/(dashboard)/financial/simulator/page.tsx` — Página do simulador (cenários efêmeros, gráfico + tabela comparativa)
- `frontend/app/(dashboard)/financial/simulator/_components/scenario-builder.tsx` — Sheet drawer para criar cenários (6 tipos)
- `frontend/app/(dashboard)/financial/simulator/_components/scenario-card.tsx` — Card compacto com ícone, título, descrição e botão remover
- `frontend/app/(dashboard)/financial/simulator/_components/comparison-chart.tsx` — ComposedChart com linhas base vs simulado + área delta
- `frontend/app/(dashboard)/financial/simulator/_components/comparison-table.tsx` — Tabela mês a mês com deltas coloridos e total no rodapé
- `frontend/app/(dashboard)/financial/simulator/_components/impact-summary.tsx` — Card resumo (impacto total, mês equilíbrio, saldos finais)

- `frontend/app/(dashboard)/financial/person-payments/page.tsx` — Página pagamentos a pessoas (summary cards + tabela histórico)
- `frontend/app/(dashboard)/financial/person-payments/_components/person-payment-form-modal.tsx` — Form modal create/edit pagamento a pessoa
- `frontend/app/(dashboard)/financial/_components/person-month-summary.tsx` — Componente reutilizável breakdown completo pessoa/mês

## Arquivos Modificados

- `core/models.py` — 10 novos models (Person, CreditCard, ExpenseCategory, ExpenseType, Expense, ExpenseInstallment, PersonIncomeType, PersonIncome, Income, RentPayment, EmployeePayment, FinancialSettings) + `owner` em Apartment + `prepaid_until`/`is_salary_offset` em Lease
- `pyproject.toml` — PLR2004 adicionado a per-file-ignores para tests (magic values em assertions)
- `core/viewsets/__init__.py` — exporta 4 novos ViewSets financeiros
- `core/urls.py` — 6 rotas financeiras (persons, credit-cards, expense-categories, financial-settings, expenses, expense-installments)
- `core/viewsets/__init__.py` — exporta 10 ViewSets financeiros
- `core/viewsets/financial_views.py` — adicionados IncomeViewSet, RentPaymentViewSet, EmployeePaymentViewSet, PersonIncomeViewSet
- `core/urls.py` — 10 rotas financeiras (persons, credit-cards, expense-categories, financial-settings, expenses, expense-installments, incomes, rent-payments, employee-payments, person-incomes)
- `core/viewsets/__init__.py` — exporta 12 ViewSets financeiros (+ FinancialDashboardViewSet, CashFlowViewSet)
- `core/urls.py` — 12 rotas financeiras (+ financial-dashboard, cash-flow)
- `frontend/tests/mocks/handlers.ts` — adicionados handlers financeiros (persons, expenses, installments, financial-dashboard, cash-flow, incomes, employee-payments) + fix non-null assertions pré-existentes
- `frontend/tests/mocks/data/index.ts` — exporta persons e expenses
- `frontend/lib/utils/constants.ts` — 9 rotas financeiras no ROUTES
- `frontend/components/layouts/sidebar.tsx` — Sub-menu expansível com chevron + active state
- `frontend/.eslintrc.json` — no-unnecessary-type-parameters off para test files
- `frontend/app/(dashboard)/tenants/page.tsx` — fix || → ?? (pre-existing lint error)
- `frontend/app/(dashboard)/financial/page.tsx` — substituído placeholder por dashboard com 6 widgets
- `frontend/lib/api/hooks/use-financial-dashboard.ts` — interfaces corrigidas para match backend (FinancialOverview, DebtByPerson, UpcomingInstallment, CategoryBreakdown)
- `frontend/lib/api/hooks/use-cash-flow.ts` — CashFlowProjectionMonth corrigido para match backend (income_total, expenses_total, balance, cumulative_balance, is_projected)
- `frontend/tests/mocks/handlers.ts` — MSW handlers atualizados para match novas interfaces
- `frontend/lib/api/hooks/__tests__/use-financial-dashboard.test.tsx` — testes atualizados para novas interfaces
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — testes atualizados para novas interfaces
- `frontend/lib/api/hooks/use-simulation.ts` — interfaces corrigidas para match backend (SimulationScenario.type, SimulationResult com base/simulated/comparison)
- `frontend/tests/mocks/handlers.ts` — MSW handler de simulate atualizado para retornar { base, simulated, comparison }
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — teste de simulação movido para use-simulation.test.tsx
- `core/permissions.py` — adicionada FinancialReadOnly permission class
- `core/viewsets/financial_views.py` — todos os ViewSets CRUD agora usam FinancialReadOnly (antes ReadOnlyForNonAdmin), FinancialSettingsViewSet mudou de IsAdminUser para FinancialReadOnly
- `core/viewsets/financial_dashboard_views.py` — DashboardViewSet e CashFlowViewSet mudaram de ReadOnlyForNonAdmin para IsAuthenticated, removido IsAdminUser do simulate action
- `frontend/store/auth-store.ts` — is_staff adicionado ao User interface
- `frontend/app/(dashboard)/financial/persons/page.tsx` — conditional UI (isAdmin) para botões criar/editar/excluir
- `frontend/app/(dashboard)/financial/categories/page.tsx` — conditional UI (isAdmin) para botões criar/editar/excluir
- `frontend/app/(dashboard)/financial/expenses/page.tsx` — conditional UI + botão exportar Excel
- `frontend/app/(dashboard)/financial/expenses/_components/expense-columns.tsx` — isAdmin no handler, edit/delete/markPaid condicionais
- `frontend/app/(dashboard)/financial/incomes/page.tsx` — conditional UI + botão exportar Excel
- `frontend/app/(dashboard)/financial/rent-payments/page.tsx` — conditional UI + botão exportar Excel
- `frontend/app/(dashboard)/financial/employees/page.tsx` — conditional UI (isAdmin) para botões criar/editar/excluir/marcar pago
- `frontend/app/(dashboard)/financial/settings/page.tsx` — campos e botão salvar desabilitados para non-admin
- `frontend/lib/hooks/use-export.ts` — adicionadas expenseExportColumns, incomeExportColumns, rentPaymentExportColumns

## Correções Pós-Design (sessão de brainstorming 2026-03-22)

- Estipêndio Rodrigo/Junior: R$1.100 (não R$1.000)
- Funcionária confirmada como Rosa: salário base R$800 + variável por serviços extras
- Prepaid kitnet 113/836: recalculado para 2026-09-29 (inquilina mudou de kitnet R$1.150 para R$1.300 em jan/2026)
- Sistema "pagar para morar": paga dia X para morar de X a X+1mês
- Design doc e prompts 06, 12 atualizados com essas correções
- Categorias simplificadas: 5 principais (Pessoal, Carros, Kitnets, Camila, Ajuda) + subcategorias via `parent` FK
- ExpenseCategory.parent adicionado (migration 0013), serializer atualizado com subcategories + parent_id
- Gastos fixos agora suportam `pessoa` (FK) — ex: Unimed R$2.230 via Rodrigo
- `valor_total` removido de empréstimos — calculado como `valor_parcela × total_parcelas`
- Prompts 09, 10 atualizados com subcategorias
- `Expense.is_offset` adicionado (migration 0014) — descontos: compras no cartão de uma pessoa que são para os sogros/Camila, subtraídas do total
- Dados do Alvaro completos: 3 cartões (Trigg, Players, Samsung), 21 parcelas, 4 descontos, 2 gastos únicos
- Dados do Tiago completos: 17 itens (fogão, geladeiras, alarme, starlink, etc.)
- Dados do Junior: placas solar (22/60), bolsa Camila (4x), perfume Camila (1x), faculdade (mensal até dez/2026)

## Problemas Conhecidos

- Testes de serviço (test_contract_service, test_template_management_service) timeout sem Redis local — issue pré-existente, não relacionado ao módulo financeiro
- xdist workers crasham em Windows/Python 3.14 — issue pré-existente
- Diretório `financial-employees-temp` é lixo de uma sessão abortada — deve ser deletado manualmente (arquivos foram substituídos por stubs vazios para não bloquear build)


---

## Feature: Modulo Financeiro do Condominio (Saidas/Saldo/Reserva/Distribuicao) - Sessoes 34-50

**Design Doc**: `docs/plans/2026-06-06-condominium-finance-design.md` (v3)
**Total de Sessoes**: 17 (34-50) - **Branch sugerida**: `feat/condo-finance`
**Status**: **prompts escritos + revisao de consistencia aplicada**. Nenhuma sessao executada.
**Ordem/dependencias**: ver `prompts/ROADMAP.md` (secao desta feature). Sequencial 34->50 recomendado (gate por fase, >=90% em `finances`).

**Decisoes de produto (detalhe no design v3):** app novo `finances` reusa `core`; separacao estrita condominio x pessoal (sitio = pessoal, fora); owner **nao-invasivo** (`owner=null`=condominio; PROD: so Tiago/Alvaro com owner; Rosa 850/205 salary-offset; Adriana 836/113 prepaid a registrar); household unico Raul&Celia (= o condominio); donos externos = so exibicao; pagamento parcial; reserva (`funded_from`); `CondoMonthClose` leve condo-scoped (ancora do fold + auditoria; NAO e o `MonthSnapshot` legado nem trava aluguel); tipos em dois eixos; materializar real/projetar futuro; gate ampliado p/ `finances`; TZ SP.

**Contratos cross-session AUTORITATIVOS** (mesma lista em `prompts/ROADMAP.md`): Bill.installment+Bill.employee = **S41**; `pay()` reserva/`assert_open` = **S45** (S44 models-only); cache receivers (incl. RentAdjustment/MonthSnapshot) = **S37**; calendario `rent_entries`/`bill_exits` (S38); projecao `net`/`cumulative_cash` (S47); `formatMonthYear`->"Junho de 2026"; RLS em toda tabela nova do finances; wedge mixed-term test (S45); gate >=90% standalone em `finances`.

| # | Sessao | Camada | Status | Arquivo |
|---|--------|--------|--------|---------|
| 34 | Fundacao: app finances + Condominium + Building.condominium + gate + TZ + factories | BE | **concluída** | `prompts/34-finances-app-infra-condominium.md` |
| 35 | Forms: owner (Apto) + is_salary_offset/prepaid_until (Locacao) | FE | **concluída** | `prompts/35-forms-owner-salary-prepaid.md` |
| 36 | Modelos: Category/BillingAccount/Bill/BillLineItem/BillSkip/Payment/PaymentAllocation | BE | **concluída** | `prompts/36-finances-models-bills.md` |
| 37 | Servicos: BillGeneration/BillService/BillPayment + cache cross-app | BE | pendente | `prompts/37-finances-bill-services-cache.md` |
| 38 | Serializers/Viewsets/API + CondoCalendarService + atrasados | BE | pendente | `prompts/38-finances-serializers-viewsets-calendar.md` |
| 39 | Frontend data layer (schemas/hooks/MSW) | FE | pendente | `prompts/39-finances-frontend-data-layer.md` |
| 40 | Frontend: calendario combinado + contas (CRUD) + pagamento | FE | pendente | `prompts/40-finances-frontend-calendar-bills-ui.md` |
| 41 | InstallmentPlan/Installment + Employee + convert_deferred + estende geracao | BE | pendente | `prompts/41-finances-installments-employee-models-services.md` |
| 42 | API parcelas/folha | BE | pendente | `prompts/42-finances-installments-employee-api.md` |
| 43 | Frontend parcelas/folha | FE | pendente | `prompts/43-finances-installments-employee-frontend.md` |
| 44 | Modelos: Reserve/ReserveMovement/IncomeEntry/CondoMonthClose | BE | pendente | `prompts/44-finances-reserve-income-close-models.md` |
| 45 | CondoBalanceService + CondoMonthCloseService + received_collectible_total + API | BE | pendente | `prompts/45-finances-balance-close-services-api.md` |
| 46 | Frontend: KPIs + reserva + receita + fechamento | FE | pendente | `prompts/46-finances-balance-reserve-income-frontend.md` |
| 47 | CondoProjectionService + CondoSimulationService + endpoints | BE | pendente | `prompts/47-finances-projection-simulation-backend.md` |
| 48 | Frontend: projecao (tabela+chart) + simulador | FE | pendente | `prompts/48-finances-projection-simulation-frontend.md` |
| 49 | OwnerDistributionService + agregacao por dono + endpoint | BE | pendente | `prompts/49-finances-owner-distribution-backend.md` |
| 50 | Frontend: cards por proprietario + donos externos + e2e/polish | FE | pendente | `prompts/50-finances-owner-distribution-frontend-polish.md` |

### Sessão 34 — Arquivos Criados/Modificados (concluída)

**Fase 1a — fundação `finances` + `core.Condominium`(padrão) + `Building.condominium` faseada + helper TZ SP + gate ampliado.** Branch `feat/condo-finance` (a partir de `master`).

- **Criados**:
  - `finances/__init__.py` (vazio), `finances/apps.py` (`FinancesConfig`, `default_auto_field`, `ready()` importa `finances.signals` no idioma exato de `core/apps.py:13-23` — `importlib.import_module` + `try/except Exception` + log), `finances/signals.py` (**stub**: só docstring, zero receivers — os receivers `finance-*` e cross-app são da S41), `finances/models.py` (cabeçalho, **sem modelos** — todos os modelos do finances são S36+), `finances/migrations/__init__.py`, `finances/services/__init__.py`.
  - `finances/services/timezone.py` — helper único SP: `SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")`, `now_sp()` (`timezone.now().astimezone(SAO_PAULO_TZ)`), `today_sp()`, `current_month_sp()` (dia 1). **Fonte única** para "hoje/mês atual" em todos os serviços do finances (S36+). `zoneinfo` é stdlib — sem dep nova.
  - `core/migrations/0048_condominium_building_condominium.py` — **migração faseada PROD-safe**: `CreateModel(Condominium)` → `RunSQL(ENABLE/DISABLE RLS em core_condominium)` → `AddField(Building.condominium null=True, blank=True)` → `RunPython(create_default_and_backfill)` (cria o padrão via `get_or_create` idempotente, backfill de **todos** os prédios incl. soft-deleted via `_default_manager`) → `AlterField(non-null, blank=True)`. Importa `DEFAULT_CONDOMINIUM_NAME` de `core.models` (string única, DRY). RLS em SQL estático (sem f-string → sem S608). Reverse: `noop`/`DISABLE`/`DeleteModel`. **Forward E backward verdes; backfill idempotente.**
  - `tests/unit/test_finances/{__init__,test_app_infra,test_timezone_helper,test_building_condominium_fk}.py` — **17 testes** (app instalado/config/ready importa signals; Condominium mixins+managers+__str__; registro padrão pela migração; RLS via `pg_class.relrowsecurity` SQL parametrizado; virada de mês SP×UTC sob `@freeze_time`; FK PROTECT/related_name/non-null/backfill; **save()-default → singleton**).
- **Modificados**:
  - `condominios_manager/settings.py` — `"finances"` em `INSTALLED_APPS` após `"core"`.
  - `core/models.py` — `DEFAULT_CONDOMINIUM_NAME = "Condomínio Principal"` (constante única); `class Condominium(AuditMixin, SoftDeleteMixin, models.Model)` (antes de `Building`; managers duplos `all_objects`/`objects`); `Building.condominium = ForeignKey("core.Condominium", PROTECT, related_name="buildings", blank=True)`; **`Building.save()` override** que atribui o condomínio-padrão (`get_or_create`) quando não setado.
  - `tests/factories.py` — `make_condominium(user=None, **kwargs)` + `make_building(..., condominium=None)` com default retrocompatível (cria/reusa o padrão de teste).
  - `pyproject.toml` (`[tool.coverage.run] source` += `"finances"`), `pytest.ini` (`--cov=finances` + `[coverage:run] source` += `finances`), `pyrightconfig.json` (`include` += `"finances"`). Gate de tipos passa a ser `mypy core/ finances/`.
- **Decisão (não-invasiva, fora do enunciado mas necessária):** o FK `Building.condominium` non-null quebraria `Building.objects.create(...)` direto (≈30 testes) **e** a API (DRF `ModelSerializer fields="__all__"` torna o campo **required** → 400 em create/update de prédio, em TODA a feature). Solução: **`blank=True`** (DB segue non-null; serializers/forms tratam como opcional) **+ `Building.save()`** que faz fallback ao condomínio-padrão singleton. Mantém **`core/serializers.py` intacto** (enunciado), honra "consumidores de Building inalterados", e o invariante "todo prédio tem condomínio" vive no model. Multi-condomínio (futuro) exigirá atribuição explícita.
- **Verificação (gate ampliado)**: backup `backups/backup_condominio_20260607_003322.sql` ANTES do migrate. `pytest tests/unit/test_finances/ --cov=finances --cov-fail-under=90` → **17/17 verde, 91.30% standalone**. `ruff check`/`format --check` limpos. `mypy core/ finances/` → **Success (75 arquivos)**. `pyright` (full include) → **0 erros/0 avisos/0 infos**. `makemigrations core --check` → "No changes detected". Migração forward→backward(0047)→forward idempotente, **0** prédios com `condominium_id` nulo, 1 registro padrão, RLS=True. Regressão escopada (finances + arquivos que criam Building: dashboard/base/lease/lease_signal/financial_edge_cases/core_views/admin_proofs) → **verde** (Building API 400→200 após o fix).
- **NÃO tocados** (escopo S35/S36+): forms (owner/salary/prepaid = S35), modelos/serializers/viewsets/cache do finances, migração inicial do finances (S36 — **dependerá explicitamente** de `core.0048`), `core/signals.py`/`cache.py`/`serializers.py`/`views.py`/`urls.py`.

### Sessão 35 — Arquivos Modificados (concluída)

**Fase 1b — forms expõem `owner` (Apartamento) + `is_salary_offset`/`prepaid_until` (Locação), gated `is_staff`.** Frontend-only; backend/serializers/schemas centrais **intactos** (já tinham os campos).

- **Modificados** (5): `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx` (schema local `owner_id`; `defaultValues`/`reset` `owner?.id ?? null`; `Select` "Proprietário" gated `isAdmin`, sentinela `OWNER_NONE='none'`→`null`, item "Condomínio (sem proprietário)" + `usePersons`; `owner_id` no submit create+update); `lib/api/hooks/use-apartments.ts` (`useCreateApartment` `Omit` deixa de excluir `owner_id`/`lease` → owner_id flui no POST, sem `as`); `leases/_components/lease-form-modal.tsx` (schema local `prepaid_until`/`is_salary_offset`; `defaultValues`/reset create+edit; `useAuthStore`→`isAdmin`; bloco gated com `Checkbox` "Aluguel compensado por salário" + `Input type=date` "Pré-pago até"; ambos no `payload` create+update; hooks de lease **não** alterados); + os 2 arquivos de teste.
- **Decisões/notas de teste**: gating via `const { user } = useAuthStore(); const isAdmin = user?.is_staff ?? false` (mesma forma de `daily/page.tsx`). Testes de submit usam **`fireEvent.submit(getByRole('dialog').querySelector('form'))`** — o Radix Dialog **portaliza** o conteúdo para `document.body`, então `container.querySelector` não acha o form; submissões testadas em **modo edição** (pré-preenchido) cobrindo owner numérico/null e prepaid set/clear/salary-offset sem depender de interação com Radix Select. Mock só de fronteiras: hooks de dados + `useAuthStore` (módulo). `as never` restrito a fixtures de teste.
- **Vínculo de funcionário (Employee↔Lease) NÃO entrou** (é `finances`/form de Employee, Fase 3). Contratos honrados: serializers `owner_id`/`prepaid_until`/`is_salary_offset` consumidos **sem alteração**; income SSOT/`collectible_leases` intactos (não-invasivo, design §6). Destrava registrar Adriana (`prepaid_until`), Rosa (`is_salary_offset`), owner (Tiago/Alvaro).
- **Verificação**: `vitest` 26/26 verde (8 apto + 9 locação existentes + 9 novos); `tsc --noEmit` (front inteiro) limpo — a mudança de tipo do `useCreateApartment` não quebrou consumidores; `eslint` nos 5 arquivos 0/0. Sem `eslint-disable`/`@ts-ignore`/`as` em produção. Branch `feat/condo-finance`.

### Sessão 36 — Arquivos Criados/Modificados (concluída)

**Fase 2 (início) — núcleo de contas a pagar do `finances`.**

- **Criados**: `finances/migrations/0001_initial.py` (7 modelos + RLS `RunSQL` ENABLE/DISABLE das 7 tabelas; **depende explicitamente** de `core.0048`; `Category` unique `(condominium, parent, name)` com `nulls_distinct=False` + `condition=is_deleted=False`); `tests/unit/test_finances/test_bill_models.py` (16) + `test_bill_annotations.py` (12).
- **Modificados**: `finances/models.py` (núcleo de contas — antes só docstring); `tests/factories.py` (+7 factories).
- **Modelos**: `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation` `(AuditMixin, SoftDeleteMixin)` + managers duplos — **exceto `BillSkip`** (`AuditMixin` só, manager simples, hard-delete des-pula). Enums `BillBehavior`/`BillLifecycleState`/`BillingAccountState`/`FundedFrom`. `Bill.attachment = FileField(upload_to="finances/bills/")` (codebase já usa FileField+MEDIA_ROOT em PaymentProof). `clean()` PT normaliza `competence_month`/`reference_month`/`tracking_start_month` p/ dia 1; CheckConstraints (`BillLineItem.amount>=0`, `Payment`/`PaymentAllocation.amount>0`, `BillingAccount.expected_amount>=0`).
- **`Bill.objects.with_amounts(today: date)`**: annotations Sum-**subquery** (não cartesiano) → `amount_total` (Σ não-offset − Σ offset), `amount_paid` (Σ alocações ativas), `amount_remaining`, `payment_status∈{open,partial,paid}`, `is_overdue` (due<today ∧ remaining>0 ∧ active). **Zero property Python**. Manager via `SoftDeleteManager.from_queryset(BillQuerySet)` (mantém filtro is_deleted + expõe with_amounts/with_deleted; django-stubs-friendly).
- **Decisão pinada honrada**: só `Bill.billing_account` agora; `Bill.installment`/`Bill.employee` + `BillLineItem.installment` = **S41**.
- **INFRA DE TESTE (importante p/ S37+)**: a suíte completa não roda `migrate` fresh — DBs vêm de dump (mem `project_rls_db_sync`). `core.0047` (RLS em tabelas de contrib) tem bug latente de **ordenação em fresh-migrate** (`--create-db` → `django_session does not exist`), exposto agora que o grafo do `finances` reordena o plano. **Workaround**: `test_condominio` recriado como **clone do dev DB** (`CREATE DATABASE test_condominio TEMPLATE condominio`, já 100% migrado) e rodar com **`--reuse-db`** (nunca `--create-db`). Comandos de gate: `pytest tests/unit/test_finances/ -n 0 -o addopts="" --reuse-db --cov=finances --cov-fail-under=90`.
- **Verificação**: 45 testes finances verdes (17 S34 + 28 S36); **coverage standalone `finances` 96.10%** (models.py 96.70%); `ruff`/`ruff format` limpos; `mypy core/ finances/` Success (75); `pyright finances/models.py` 0/0/0; `makemigrations --check` "No changes detected"; migração forward/backward OK; RLS habilitada nas 7 tabelas (`pg_class.relrowsecurity`). Branch `feat/condo-finance`.

> **Falhas PRÉ-EXISTENTES detectadas na suíte completa (NÃO causadas pela S34 — provado: passam isoladas ou são deterministas em código intocado):** (a) 3× `test_fee_calculator.py::TestCalculateDueDateChangeFee` — **bug determinista** em `FeeCalculatorService.calculate_due_date_change_fee` (com `reference_date.day < current_due_day` o `old_due_date` cai no mês **anterior**, contradizendo o próprio docstring "built in the reference month" e os testes; provável regressão do commit `c2e7353 "fixing due day change issue"`); (b) 1× `test_rent_adjustment.py::...test_apply_adjustment_updates_apartment_prices` — flakiness de **fronteira de meia-noite** (`date.today()` do teste vs data do serviço diferem 1 dia); (c) ~10× falhas de **poluição entre testes** na suíte sequencial de 1400 (passam isoladas). Itens (a)/(b) são money-facing/intent-ambíguo → encaminhados ao usuário para decisão antes de corrigir. Próxima sessão usa **regressão escopada** (norma documentada do projeto: suíte completa tem flakiness pré-existente).