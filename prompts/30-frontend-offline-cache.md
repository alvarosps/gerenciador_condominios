# Sessão 30 — Frontend: Cache offline read-only (persist + IndexedDB + banner + logout clear)

> Frente C do plano PWA. Esta sessão persiste o cache do TanStack Query em **IndexedDB** (via
> `idb-keyval`), troca o provider por `PersistQueryClientProvider`, adiciona o `OfflineBanner` e
> **limpa o cache no logout** (segurança: não deixar dados de um usuário para outro). Offline é
> **somente leitura** — sem fila de sync. Depende da Sessão 29 (SW do shell offline), mas a
> persistência do cache funciona **independente** do SW.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro; foco na **§6 Offline Read-Only** — §6.1 persistência, §6.2 UX, §6.3 segurança, §6.4 testes — e §9 dependências): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar Sessão 29 concluída antes de começar; se a 29 ainda não rodou, a persistência aqui **não depende** dela e pode prosseguir — anotar no handoff)
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — abrir e seguir)
- **QueryClient atual (adicionar `gcTime`/`networkMode`, **manter** o `retry` e `refetchOnWindowFocus`)**: `frontend/lib/config/query-client.ts:3-22` (o objeto `defaultOptions.queries` `:5-20` recebe os 2 novos campos; **não** remover o `retry` custom `:7-18`).
- **Provider atual (trocar `QueryClientProvider`→`PersistQueryClientProvider`)**: `frontend/app/providers.tsx:1-17` (import `:4`, uso `:11-14`). O `ThemeProvider`/`Toaster` permanecem.
- **Logout real (site EXATO da limpeza)**: `frontend/lib/api/hooks/use-auth.ts:76-96` — `useLogout()` já chama `clearAuth()` + `queryClient.clear()` em `onSuccess` `:84-88` **e** `onError` `:89-94`. Adicionar o `del` da chave do IndexedDB **nos dois ramos** (após `queryClient.clear()`). **Esse é o único site de logout** (grep confirmou; `TenantPortalLayout` e `Header` apenas chamam `useLogout().mutate()`).
- **Pontos de montagem do banner**: `frontend/components/layouts/main-layout.tsx:32-71` (montar logo após `<div className="min-h-screen">` `:33`, antes do header mobile) e `frontend/components/layouts/tenant-layout.tsx:32-54` (montar no topo do `<header>`/wrapper, antes do conteúdo).
- **Padrão de componente client com listeners + cleanup (`'use client'`, `useEffect`, `useState`)**: `frontend/components/layouts/main-layout.tsx:1-30` (efeito com cleanup implícito; aqui o efeito **registra/desregistra** listeners `online`/`offline`).
- **Teste de hook com store Zustand real + MSW + reset entre testes**: `frontend/lib/api/hooks/__tests__/use-auth.test.tsx:1-281` (em especial `useLogout` `:168-222` — `setAuth` antes, `mutate()`, `waitFor(!isPending)`, asserts no store; mock de `window.location` `:32-55`).
- **Setup de testes (mocks de boundary já existentes; `vi.mock`, `matchMedia`, `localStorage`)**: `frontend/tests/setup.ts:1-67` (ambiente é **`happy-dom`**, ver `frontend/vitest.config.mts:11`). `localStorage` já mockado `:36-43` — **não** redefinir globalmente; mockar `idb-keyval` por arquivo de teste.
- **`.env` frontend (documentar `NEXT_PUBLIC_BUILD_ID`)**: `frontend/.env.example:38-46` (seção APPLICATION SETTINGS — acrescentar a var lá).

### Contrato compartilhado (nomes verbatim — idênticos entre sessões)
- `frontend/lib/config/persister.ts` exporta `createIDBPersister()` (AsyncStorage persister sobre `idb-keyval` `get`/`set`/`del`).
- Chave única do IndexedDB: **string literal** `condominios-query-cache` (usada pelo persister **e** pelo `del` do logout — extrair como constante exportada do `persister.ts` para DRY).
- `query-client.ts` ganha `gcTime: 1000 * 60 * 60 * 24` e `networkMode: 'offlineFirst'`.
- `providers.tsx` usa `PersistQueryClientProvider` com `persistOptions { persister, maxAge: 1000 * 60 * 60 * 24, buster }`.
- `frontend/components/offline-banner.tsx` exporta `OfflineBanner` (client; `navigator.onLine` + eventos `online`/`offline`), montado em `main-layout.tsx` **e** `tenant-layout.tsx`.

## Escopo

### Arquivos a criar
- `frontend/lib/config/persister.ts`
- `frontend/components/offline-banner.tsx`
- `frontend/lib/config/__tests__/persister.test.ts`
- `frontend/components/__tests__/offline-banner.test.tsx`

### Arquivos a modificar
- `frontend/lib/config/query-client.ts` — adicionar `gcTime` + `networkMode` (manter `retry`/`refetchOnWindowFocus`).
- `frontend/app/providers.tsx` — trocar para `PersistQueryClientProvider` com `persistOptions`.
- `frontend/lib/api/hooks/use-auth.ts` — `useLogout()`: `del` da chave IndexedDB nos dois ramos (`onSuccess` + `onError`).
- `frontend/lib/api/hooks/__tests__/use-auth.test.tsx` — novo teste: logout chama `del(QUERY_CACHE_IDB_KEY)`.
- `frontend/components/layouts/main-layout.tsx` — montar `<OfflineBanner />`.
- `frontend/components/layouts/tenant-layout.tsx` — montar `<OfflineBanner />`.
- `frontend/.env.example` — documentar `NEXT_PUBLIC_BUILD_ID` (buster do cache).
- `frontend/package.json` — dependências (`@tanstack/react-query-persist-client`, `@tanstack/query-async-storage-persister`, `idb-keyval`).

## Especificação

### `frontend/lib/config/persister.ts`
```ts
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { get, set, del } from 'idb-keyval';

export const QUERY_CACHE_IDB_KEY = 'condominios-query-cache';

export function createIDBPersister() {
  return createAsyncStoragePersister({
    storage: {
      getItem: (key) => get(key),
      setItem: (key, value) => set(key, value),
      removeItem: (key) => del(key),
    },
  });
}
```
- O `storage` adapta `idb-keyval` à interface `AsyncStorage` esperada pelo persister (`getItem`/`setItem`/`removeItem`). Tipar exatamente o que a lib espera (sem `any`); `get<string>`/`set` cobrem o shape serializado.
- Exportar `QUERY_CACHE_IDB_KEY` para reuso no logout (DRY — uma única definição da chave).

### `frontend/lib/config/query-client.ts` (modificar)
- Adicionar ao bloco `queries`:
  - `gcTime: 1000 * 60 * 60 * 24` — **≥ `maxAge`** do persister (senão o GC descarta a query antes da rehidratação; design §6.1).
  - `networkMode: 'offlineFirst'`.
- **Manter** `staleTime`, o `retry` custom (401/403 → não retry) e `refetchOnWindowFocus`.

### `frontend/app/providers.tsx` (modificar)
- Importar `PersistQueryClientProvider` de `@tanstack/react-query-persist-client` e `createIDBPersister` de `@/lib/config/persister`.
- Criar o persister **uma vez** (módulo-level `const persister = createIDBPersister()`, fora do componente — não recriar a cada render).
- Substituir `<QueryClientProvider client={queryClient}>` por:
```tsx
<PersistQueryClientProvider
  client={queryClient}
  persistOptions={{
    persister,
    maxAge: 1000 * 60 * 60 * 24,
    buster: process.env.NEXT_PUBLIC_BUILD_ID ?? 'dev',
    dehydrateOptions: {
      shouldDehydrateQuery: (query) => query.state.status === 'success',
    },
  }}
>
```
- `buster` invalida todo o cache persistido a cada deploy (build id muda). `dehydrateOptions` persiste **apenas** queries `success` (não persistir `error`/`pending` — design §6.1). `ThemeProvider`/`{children}`/`<Toaster />` inalterados.

### `frontend/components/offline-banner.tsx`
- `'use client'`. Estado `isOffline` inicial `false` (SSR-safe); no `useEffect`, setar `!navigator.onLine` e registrar listeners `window.addEventListener('online'/'offline', ...)`; **cleanup** removendo ambos.
- Quando `isOffline`, renderizar faixa fixa no topo do conteúdo com `role="status"` e texto PT: **"Você está offline — exibindo dados salvos"**. Quando online, renderizar `null`.
- Usar tokens semânticos do projeto (ex.: `bg-amber-500/15 text-amber-700 dark:text-amber-400`, `text-sm`, `px-4 py-2`, ícone `WifiOff` de `lucide-react`). Status nunca só por cor — sempre o rótulo textual + ícone (acessibilidade).
- Sem props (KISS). Componente puramente apresentacional/reativo aos eventos do browser.

### `frontend/lib/api/hooks/use-auth.ts` — `useLogout()` (modificar)
- Importar `del` de `idb-keyval` e `QUERY_CACHE_IDB_KEY` de `@/lib/config/persister`.
- Em `onSuccess` **e** em `onError`, após `queryClient.clear()`, chamar `void del(QUERY_CACHE_IDB_KEY)` para remover o cache persistido do dispositivo. **Segurança (design §6.3)**: garante que dados de negócio de um usuário não permaneçam visíveis para outro no mesmo dispositivo. Manter a ordem: `clearAuth()` → `queryClient.clear()` → `del(...)` → redirect.

### Montagem do banner
- `main-layout.tsx`: `<OfflineBanner />` logo dentro de `<div className="min-h-screen">` (`:33`), antes do header mobile, para aparecer no topo em todas as rotas do dashboard.
- `tenant-layout.tsx`: `<OfflineBanner />` no topo do wrapper (`:33`), antes do `<header>`.

### `.env.example`
- Acrescentar na seção APPLICATION SETTINGS: `NEXT_PUBLIC_BUILD_ID` (buster do cache persistido; muda a cada deploy para invalidar o IndexedDB — opcional em dev, default `'dev'`).

## TDD

Rodar **somente os arquivos de teste desta sessão** (a suíte completa tem problemas pré-existentes de
xdist/Redis — ver memória do projeto). Mockar **apenas** boundaries externos (`idb-keyval`, eventos do
`window`); **nunca** mockar TanStack Query, o store Zustand ou código interno.

### 1. Red — escrever os testes primeiro (devem falhar por arquivo/comportamento inexistente)
Comando: `cd frontend && npx vitest run "lib/config/__tests__/persister.test.ts" "components/__tests__/offline-banner.test.tsx" "lib/api/hooks/__tests__/use-auth.test.tsx"`

**`persister.test.ts`** (mockar `idb-keyval` como boundary: `vi.mock('idb-keyval', () => ({ get: vi.fn(), set: vi.fn(), del: vi.fn() }))`)
- `createIDBPersister()` retorna um persister com os métodos esperados (`persistClient`/`restoreClient`/`removeClient`).
- O `storage.getItem` delega a `idb-keyval.get`; `setItem` delega a `set`; `removeItem` delega a `del` — verificar via `persistClient`/`restoreClient`/`removeClient` que as funções de `idb-keyval` são chamadas com a chave esperada (testar o caminho real do persister, sem stub do persister em si).
- `QUERY_CACHE_IDB_KEY === 'condominios-query-cache'` (asserção literal — contrato cross-sessão).
- **`gcTime >= maxAge`** (asserção de config): importar `queryClient` e `maxAge` literal (`1000*60*60*24`); `expect(queryClient.getDefaultOptions().queries?.gcTime).toBeGreaterThanOrEqual(MAX_AGE)`; e `networkMode === 'offlineFirst'`.

**`offline-banner.test.tsx`** (render real; controlar `navigator.onLine` via `Object.defineProperty(navigator, 'onLine', { configurable:true, value:false })` e disparar `window.dispatchEvent(new Event('online'/'offline'))`)
- Online no mount → banner **ausente** (`queryByRole('status')` null / texto ausente).
- `navigator.onLine=false` no mount → banner **presente** com o texto exato "Você está offline — exibindo dados salvos".
- Dispatch de `offline` quando estava online → banner **aparece**; dispatch de `online` em seguida → banner **some** (usar `act`/`waitFor`).
- Listeners são removidos no unmount (sem warning de leak; opcional: spy em `removeEventListener`).

**`use-auth.test.tsx`** (estender o arquivo existente; mockar `idb-keyval` como boundary no topo)
- No `describe('useLogout')`, novo teste: após `mutate()` e `waitFor(!isPending)`, `expect(del).toHaveBeenCalledWith('condominios-query-cache')`. Manter os 2 testes existentes (`:168-221`) verdes (store limpo no logout).
- Mockar `idb-keyval` (`del`) no escopo do arquivo; **não** mockar `queryClient`/store.

### 2. Green — implementar persister, banner, edição de query-client/providers/use-auth + montagem nos layouts
### 3. Refactor — extrair `QUERY_CACHE_IDB_KEY` como única fonte (importada no logout); subcomponente/ícone do banner sem duplicação; sem comentários supérfluos
### 4. Verify
- `cd frontend && npx vitest run "lib/config/__tests__/persister.test.ts" "components/__tests__/offline-banner.test.tsx" "lib/api/hooks/__tests__/use-auth.test.tsx"` → tudo verde.
- `cd frontend && npx tsc --noEmit` (type-check; zero erros nos arquivos tocados).
- `cd frontend && npx eslint "lib/config/persister.ts" "lib/config/query-client.ts" "app/providers.tsx" "components/offline-banner.tsx" "lib/api/hooks/use-auth.ts" "components/layouts/main-layout.tsx" "components/layouts/tenant-layout.tsx"` → zero erros/avisos.

## Constraints (NÃO fazer)

- **NÃO** implementar fila de sync / offline write / Background Sync — offline é **READ-ONLY** (design §6.2, §11/YAGNI). Formulários offline devem **desabilitar/avisar** (o `networkMode: 'offlineFirst'` deixa mutations `paused`); **mencionar** isso no banner/UX, sem construir fila.
- **NÃO** persistir tokens nem nada sensível novo: tokens continuam em cookie HttpOnly; o IndexedDB guarda só dados de negócio já visíveis ao usuário logado (design §6.3).
- **NÃO** persistir queries `error`/`pending` — só `success` (via `dehydrateOptions.shouldDehydrateQuery`).
- **NÃO** remover o `retry` custom nem `refetchOnWindowFocus` do `query-client.ts` — apenas **acrescentar** `gcTime`/`networkMode`.
- **NÃO** criar um segundo site de logout — usar o `useLogout()` existente (`use-auth.ts:76-96`); adicionar `del` nos **dois** ramos.
- **NÃO** redefinir a chave do IndexedDB em mais de um lugar — `QUERY_CACHE_IDB_KEY` é a única fonte (DRY); o logout importa de `persister.ts`.
- **NÃO** recriar o persister a cada render — instanciar uma vez em escopo de módulo no `providers.tsx`.
- **NÃO** instalar `@serwist/next`/`serwist` aqui (Sessão 29) nem `pywebpush` (backend, Sessão 31). Adicionar **apenas** `@tanstack/react-query-persist-client`, `@tanstack/query-async-storage-persister`, `idb-keyval` via `npm install` no diretório `frontend/`.
- **NÃO** mockar `idb-keyval` parcialmente nem TanStack Query/Zustand/código interno — mock só do boundary externo (`idb-keyval`, eventos do `window`). Sem mock de componentes internos.
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`; **em código de produção** NÃO usar `as`/`!` — tipar na raiz (`AsyncStorage` do persister tem tipo; `noUncheckedIndexedAccess` exige guards/`??`). `import type` para tipos.
- **NÃO** usar `from __future__ import annotations` (regra do projeto — só relevante se algum util backend for tocado; aqui não há backend).
- **NÃO** rodar a suíte completa de testes — apenas os 3 arquivos desta sessão (evitar falhas pré-existentes de xdist/Redis).
- SOLID/DRY/KISS/YAGNI — funções/componentes de responsabilidade única, sem código especulativo, sem re-export/barrel.

## Critérios de Aceite

- [ ] `frontend/lib/config/persister.ts` exporta `createIDBPersister()` (AsyncStorage sobre `idb-keyval`) e `QUERY_CACHE_IDB_KEY === 'condominios-query-cache'`.
- [ ] `query-client.ts` tem `gcTime: 1000*60*60*24` e `networkMode: 'offlineFirst'`; `retry` custom e `refetchOnWindowFocus` **mantidos**.
- [ ] `gcTime >= maxAge` validado por teste (asserção de config).
- [ ] `providers.tsx` usa `PersistQueryClientProvider` com `persistOptions { persister, maxAge: 1000*60*60*24, buster: NEXT_PUBLIC_BUILD_ID ?? 'dev', dehydrateOptions(shouldDehydrateQuery → status==='success') }`; persister instanciado uma vez em escopo de módulo.
- [ ] `OfflineBanner` (client) aparece quando offline (texto exato "Você está offline — exibindo dados salvos" + ícone) e some quando online; reage a `online`/`offline`; listeners limpos no unmount.
- [ ] `<OfflineBanner />` montado em `main-layout.tsx` **e** `tenant-layout.tsx`.
- [ ] `useLogout()` chama `del(QUERY_CACHE_IDB_KEY)` após `queryClient.clear()` nos **dois** ramos (`onSuccess`/`onError`); validado por teste; store ainda limpo.
- [ ] `.env.example` documenta `NEXT_PUBLIC_BUILD_ID`.
- [ ] Deps `@tanstack/react-query-persist-client`, `@tanstack/query-async-storage-persister`, `idb-keyval` em `package.json`.
- [ ] `npx vitest run` nos 3 arquivos da sessão 100% verde; `tsc --noEmit` sem erros nos arquivos tocados; `eslint` zero erros/avisos.
- [ ] Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem re-exports; sem fila de sync; offline permanece read-only.

## Handoff

1. Rodar e confirmar verde (colar saída como evidência):
   - `cd frontend && npx vitest run "lib/config/__tests__/persister.test.ts" "components/__tests__/offline-banner.test.tsx" "lib/api/hooks/__tests__/use-auth.test.tsx"`
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "lib/config/persister.ts" "lib/config/query-client.ts" "app/providers.tsx" "components/offline-banner.tsx" "lib/api/hooks/use-auth.ts" "components/layouts/main-layout.tsx" "components/layouts/tenant-layout.tsx"`
2. Atualizar `prompts/SESSION_STATE.md`: marcar Sessão 30 concluída (criar bloco da feature PWA se ainda não existir); anotar que a **Sessão 31** inicia o backend de Web Push (model `WebPushSubscription` + migração `0044` + settings VAPID), e que a persistência aqui é independente do SW da Sessão 29.
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): persist query cache offline (IndexedDB) + offline banner + logout clear

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A Sessão 31 começa lendo o `SESSION_STATE.md`.
