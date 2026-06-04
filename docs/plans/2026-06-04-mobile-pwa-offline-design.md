# App Mobile Completo — Responsividade + PWA + Offline + Web Push — Design

**Data**: 2026-06-04
**Autor**: Alvaro Souza
**Status**: Aprovado (design)

---

## 1. Contexto e Objetivo

A aplicação web (Next.js 14 + React 18, Tailwind v4) é hoje **parcialmente** usável no celular, **não é instalável** como app (sem PWA), **não funciona offline** e **não envia notificações push pela web**. Existe um app mobile Expo separado (`mobile/`) que consome a API, mas a decisão de produto é **priorizar a web como experiência mobile principal** e deixar o app Expo para o futuro.

**Objetivo**: tornar a web um app mobile de primeira classe, em 4 frentes:

1. **Responsividade** — totalmente confortável no celular (tabelas viram cards, alvos de toque adequados, headers sem quebra).
2. **PWA instalável** — ícone na tela inicial, abre em modo standalone (sem barra do navegador).
3. **Offline read-only** — abrir o app sem internet e ver os últimos dados carregados.
4. **Web Push** — notificações do sistema operacional na web, reaproveitando o pipeline de notificações existente.

### 1.1 Decisões de produto travadas (brainstorming)

- **Offline**: somente **leitura** dos dados já carregados. Criar/editar continua exigindo internet (sem fila de sincronização — YAGNI).
- **Push**: **Web Push é prioridade**; o app Expo é secundário/futuro. Push para **admin e inquilinos** desde já (o pipeline atual já distingue destinatários).
- **Tabelas no mobile**: **cards empilhados** (rótulo: valor), com ações em botões grandes no rodapé.
- **Ícone do PWA**: **gerado** a partir da cor primária do tema (glyph de prédio); substituível depois.

---

## 2. Stack real (corrige o CLAUDE.md, que está defasado)

| Item | Realidade no disco |
|---|---|
| Next.js | **14.2.14** (App Router) |
| React | **18.3.1** |
| Tailwind | **v4.1.14** (CSS-first: `@import "tailwindcss"`, `@theme`, tokens OKLCH) — **container queries nativas** |
| Estado servidor | TanStack Query **v5.90.5** (cache **só em memória** hoje) |
| Estado cliente | Zustand 5 (persist só do perfil de auth) |
| Tabela | `components/tables/data-table.tsx` — componente **shadcn/Radix custom** (NÃO Ant Design), genérico `Column<T>` com `render` |
| `next.config.js` | CommonJS, `output: 'standalone'` |

**Implicações**: container queries do Tailwind v4 estão disponíveis sem plugin; e como o `DataTable` é um único componente compartilhado, torná-lo responsivo conserta todas as listas de uma vez.

---

## 3. Decisões técnicas-chave

| Decisão | Escolha | Alternativa rejeitada / motivo |
|---|---|---|
| Ferramenta PWA | **Serwist** (`@serwist/next`), modo *injectManifest*, SW custom em `app/sw.ts` | `next-pwa` sem manutenção; `@ducanh2912/next-pwa` é fork. Serwist (sucessor 2026, base Workbox) permite o **mesmo SW** fazer precache offline **e** os handlers de `push`/`notificationclick`. |
| Manifest + ícones | Nativo Next 14 (`app/manifest.ts`, `app/icon.png`, `app/apple-icon.png`) | Sem biblioteca extra; o Next injeta os `<link>` automaticamente. |
| Persistência offline | `PersistQueryClientProvider` + persister assíncrono em **IndexedDB** (`idb-keyval`) | localStorage tem limite ~5 MB e exige serialização. Como offline é read-only, o caveat de "reescreve tudo a cada mutation" é irrelevante. |
| Armazenar inscrição Web Push | **Novo model `WebPushSubscription`** | Estender `DeviceToken` seria hack (shape diferente: endpoint + p256dh + auth vs. string Expo). SOLID: model dedicado; o **envio** é que se unifica. |
| Tabela → cards | **Container queries** Tailwind v4 (`@container` + `@max-*`), tabela e cards no mesmo componente alternados por CSS | Medição via JS (ResizeObserver) traria risco de hidratação e complexidade. CSS puro é SSR-safe e adapta ao espaço real do componente. |

---

## 4. Frente A — Responsividade Mobile

### 4.1 `DataTable` responsivo (maior alavanca)

- Envolver o conteúdo num contexto de container: `<div className="@container">`.
- Renderizar **dois ramos** no mesmo componente:
  - `<table>` visível em containers largos: `hidden @md:block`.
  - Lista de **cards** visível em containers estreitos: `@md:hidden`.
- Estender `Column<T>` com campos **opcionais e retrocompatíveis** (colunas atuais continuam funcionando):
  - `primary?: boolean` — coluna que vira o **título** do card (fallback: primeira coluna).
  - `hideOnCard?: boolean` — oculta no card (ex.: coluna redundante).
  - `isActions?: boolean` — renderizada no **rodapé** do card, botões full-width (touch-friendly).
- Card padrão: título (coluna `primary`) no topo; demais colunas como linhas `rótulo: valor` (rótulo = `column.title`, valor = saída do `render`); ações no rodapé.
- A paginação atual (`flex flex-col sm:flex-row`) já é responsiva — manter.

**Isolamento**: a lógica de card fica num subcomponente `DataTableCards<T>` no mesmo arquivo (ou `data-table-cards.tsx`), recebendo `columns`, `paginatedData`, `getRowKey`, `getCellValue`. Mantém o `DataTable` focado e testável.

### 4.2 Varredura de polish (mecânica, baixo risco)

- **Headers de página**: adicionar `flex-wrap gap-*` (ou `flex-col sm:flex-row`) aos ~17 cabeçalhos `flex justify-between items-center` que hoje não quebram (modelo correto já existe em `financial/daily/page.tsx`).
- **Alvos de toque** ([components/ui/button.tsx](frontend/components/ui/button.tsx)): `size` default `h-9`→`h-10`; criar `size: 'touch'` (`h-11`) para ações de lista; ações da tabela passam a usar tamanho confortável (≥44px) no card.
- **Viewport** ([app/layout.tsx](frontend/app/layout.tsx)): adicionar `export const viewport: Viewport = { width: 'device-width', initialScale: 1, viewportFit: 'cover', themeColor: ... }`.

### 4.3 Testes (Frente A)

- Vitest: `DataTable` renderiza cards quando o container é estreito e tabela quando largo (testar presença/ausência via classes utilitárias e estrutura; usar os mocks existentes de `matchMedia`/container conforme `tests/setup.ts`).
- `DataTable` respeita `primary`/`hideOnCard`/`isActions`.
- Não quebrar testes existentes de `tenants`/`leases` que usam `DataTable`.

---

## 5. Frente B — PWA Instalável

### 5.1 Manifest e ícones

- `app/manifest.ts` → `MetadataRoute.Manifest`: `name: "Condomínios Manager"`, `short_name: "Condomínios"`, `start_url: "/"`, `display: "standalone"`, `background_color`/`theme_color` derivados do tema, `lang: "pt-BR"`, `icons` (192, 512, 512-maskable).
- Ícones gerados a partir da cor primária `oklch(0.55 0.15 175)` com glyph de prédio:
  - `app/icon.png` (512), `app/apple-icon.png` (180), variante maskable.
  - Geração via script Node único e versionado (ex.: `frontend/scripts/generate-icons.mjs`) usando `sharp` (devDependency) a partir de um SVG-fonte — reproduzível, sem binários "mágicos" sem origem.

### 5.2 Service Worker (Serwist)

- `withSerwist` envolvendo o `next.config.js` (compatível com CJS via `require("@serwist/next").default`), com `swSrc: "app/sw.ts"`, `swDest: "public/sw.js"`, `disable: NODE_ENV === "development"`.
- `app/sw.ts`: precache do app shell (manifest injetado pelo Serwist) + runtime caching (NetworkFirst para navegação, com **fallback offline**) + placeholders para os handlers de push (Frente D).
- Metadata em `app/layout.tsx`: `appleWebApp: { capable: true, statusBarStyle: "default", title: "Condomínios" }`, `manifest` é vinculado automaticamente ao existir `app/manifest.ts`.

### 5.3 Notas de plataforma

- **iOS 16.4+**: Web Push só funciona com o app **instalado na tela inicial** — instalável (Frente B) é pré-requisito do push (Frente D) no iOS.
- O `output: 'standalone'` do Next (modo servidor Node) é ortogonal ao `display: 'standalone'` do PWA — ambos permanecem.

### 5.4 Testes (Frente B)

- `app/manifest.ts` retorna os campos obrigatórios (test unitário do objeto).
- Build de produção gera `public/sw.js` (verificação no gate de build; sem teste E2E de SW por ora).

---

## 6. Frente C — Offline Read-Only

### 6.1 Persistência do cache

- Trocar `QueryClientProvider` por `PersistQueryClientProvider` em [app/providers.tsx](frontend/app/providers.tsx).
- Persister: `createAsyncStoragePersister({ storage })` onde `storage` adapta `idb-keyval` (`get`/`set`/`del`).
- [lib/config/query-client.ts](frontend/lib/config/query-client.ts):
  - `gcTime: 1000 * 60 * 60 * 24` (24h) — **≥ `maxAge`** do persister (senão o GC descarta antes).
  - `networkMode: 'offlineFirst'`.
  - Manter `retry` atual; o persister usa `maxAge: 24h` e `buster` = build id (env `NEXT_PUBLIC_BUILD_ID` ou similar) para invalidar em deploy.
  - `dehydrateOptions`: persistir apenas queries `success` (não persistir erros/loading).

### 6.2 UX offline

- Componente `OfflineBanner` (client): escuta `online`/`offline` + `navigator.onLine`; exibe faixa "Você está offline — exibindo dados salvos". Renderizado no `MainLayout` e no `TenantPortalLayout`.
- Mutations offline: com `networkMode: 'offlineFirst'`, ficam `paused`; a UI deve sinalizar que a ação será aplicada ao reconectar — porém, como o escopo é read-only, **desabilitar/avisar** nos formulários quando offline (sem fila de sync).

### 6.3 Segurança (CRÍTICO)

- No **logout**: `queryClient.clear()` **e** remover a chave do IndexedDB (`idb-keyval` `del`/`clear`) — não deixar dados de negócio de um usuário no dispositivo para outro.
- Nada sensível novo persistido: tokens continuam em cookie HttpOnly; o IndexedDB guarda apenas dados de negócio já visíveis ao usuário logado.

### 6.4 Testes (Frente C)

- Vitest: persister grava/lê via mock de `idb-keyval`; `gcTime ≥ maxAge` (asserção de config).
- `OfflineBanner` aparece/some conforme eventos `online`/`offline`.
- Logout limpa o cache persistido (mock de `idb-keyval`).

---

## 7. Frente D — Web Push

### 7.1 Backend — model e migração

- Novo model `WebPushSubscription(AuditMixin)`:
  - `user` (FK → AUTH_USER_MODEL, related_name `web_push_subscriptions`)
  - `endpoint` (URLField/TextField, **unique**)
  - `p256dh` (CharField)
  - `auth` (CharField)
  - `is_active` (bool, default True)
- Migração via `makemigrations` (sequencial; sem editar migrações existentes). **Backup antes de migrar** (`python scripts/backup_db.py`).
- Sem SoftDelete (igual `DeviceToken`/`Notification`).

### 7.2 Backend — envio unificado

Refatorar [core/services/notification_service.py](core/services/notification_service.py) (mantendo `create_notification()` intacto para os chamadores):

- Extrair `send_expo_push(user, title, body, data)` (lógica atual).
- Criar `send_web_push(user, title, body, data)` usando `pywebpush` + VAPID; payload JSON `{ title, body, data }`; tratar resposta **410/404 (Gone)** desativando a inscrição (`is_active=False`).
- `send_push_notification()` passa a chamar **ambos** os canais. Falhas continuam logadas e silenciosas (a `Notification` já está persistida).
- **Resultado**: todos os gatilhos existentes (`notify_new_proof`, `notify_proof_reviewed`, `send_scheduled_notifications`: `due_reminder`/`due_today`/`overdue`/`contract_expiring`/`adjustment_eligible`) passam a enviar Web Push **sem alteração nos gatilhos**.

### 7.3 Backend — endpoints e config

- `WebPushViewSet` (espelha [DeviceTokenViewSet](core/viewsets/device_views.py)), `IsAuthenticated`:
  - `GET /api/web-push/vapid-public-key/` → `{ "publicKey": VAPID_PUBLIC_KEY }`
  - `POST /api/web-push/subscribe/` → body `{ endpoint, keys: { p256dh, auth } }` → `update_or_create` por `endpoint`.
  - `POST /api/web-push/unsubscribe/` → body `{ endpoint }` → `is_active=False`.
- Registrar rotas em `core/urls.py`.
- Dependência **`pywebpush`** adicionada a **`requirements.txt` E `pyproject.toml`** `[project.dependencies]` (regra do projeto — nunca em só um lugar; sem `try/except ImportError`).
- Env: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (`mailto:...`) via `python-decouple`; documentar em `.env.example` e `.env.production.example`. Gerar par de chaves VAPID e documentar o comando no plano.

### 7.4 Frontend — SW e subscrição

- `app/sw.ts`: handler `push` (cria `self.registration.showNotification(title, { body, data, icon, badge })`) e `notificationclick` (foca/abre a aba na `data.screen`, ex.: `/proofs`, `/tenant/payments`).
- Hook `useWebPush()`:
  - lê suporte (`'serviceWorker' in navigator && 'PushManager' in window`),
  - `requestPermission()`, busca a VAPID public key, `registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })`, POST `subscribe/`.
  - `unsubscribe()` → `subscription.unsubscribe()` + POST `unsubscribe/`.
- Toggle **"Ativar notificações"** em [/settings](frontend/app/(dashboard)/settings/page.tsx) (admin) e `/tenant/profile` (inquilino), com estados: não suportado / permissão negada / inscrito / não inscrito.
- Hooks de API em `lib/api/hooks/use-web-push.ts` (via Axios client + TanStack Query, padrão do projeto).

### 7.5 Testes (Frente D)

- Backend (pytest): `subscribe/unsubscribe` (auth, validação, `update_or_create`); `send_web_push` desativa inscrição em 410 (mock **apenas do boundary externo** `pywebpush`/HTTP, nunca de código interno); `send_push_notification` chama os dois canais.
- Frontend (Vitest): `useWebPush` fluxos de permissão/inscrição (mock de `navigator.serviceWorker`/`PushManager` como boundary); toggle reflete estados.

---

## 8. Sequenciamento (fases independentes, cada uma entregável)

1. **Fase 1 — Responsividade** (sem dependências novas): polish (headers/touch/viewport) + `DataTable` cards. Valor imediato.
2. **Fase 2 — PWA shell**: Serwist + `app/sw.ts` + manifest + ícones. App instalável e abre offline.
3. **Fase 3 — Offline de dados**: persist + IndexedDB + `OfflineBanner` + limpeza no logout.
4. **Fase 4 — Web Push**: backend (model/migração/sender/endpoints/VAPID) + frontend (handlers no SW + hook + toggle). Depende do SW da Fase 2.

Cada fase segue **TDD** e passa o **gate de verificação** do projeto:
- Backend: `ruff check && ruff format --check && mypy core/ && pyright && python -m pytest`
- Frontend: `cd frontend && npm run lint && npm run type-check && npm run test:unit`

---

## 9. Dependências e ambiente

**Frontend (novas):** `@serwist/next`, `serwist`, `@tanstack/react-query-persist-client`, `@tanstack/query-async-storage-persister`, `idb-keyval`; devDependency `sharp` (geração de ícones).

**Backend (nova):** `pywebpush` → `requirements.txt` + `pyproject.toml [project.dependencies]`.

**Env novas:** `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (backend); opcional `NEXT_PUBLIC_BUILD_ID` (buster do cache). Atualizar `.env.example` e `.env.production.example`.

---

## 10. Critérios de aceitação

- **A**: em viewport de 360px, listas de Inquilinos/Locações/financeiro exibem cards legíveis com ações tocáveis (≥44px); nenhum header empurra botões para fora; sem scroll horizontal forçado.
- **B**: Lighthouse PWA "installable" ok; "Adicionar à tela inicial" no iOS abre em standalone com ícone correto.
- **C**: com a rede desligada, recarregar o app abre o shell e exibe os últimos dados carregados; banner de offline visível; logout limpa o cache persistido.
- **D**: ativar notificações inscreve o dispositivo; ao um inquilino enviar comprovante, o admin recebe push no navegador/instalado; inscrições expiradas são desativadas automaticamente.

---

## 11. Fora de escopo (YAGNI)

- Fila de sincronização de mutations offline (offline write).
- Background Sync / Periodic Background Sync.
- Push no app Expo (mantido como está; foco na web).
- Refatorações não relacionadas às 4 frentes.
