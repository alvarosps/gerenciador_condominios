# Sessão 33 — Frontend: Web Push UI (handlers no SW + `useWebPush` + toggle em Settings/Profile)

> Frente D do design (parte frontend). Esta sessão **consome** o contrato backend já entregue na **Sessão 32**
> (`/api/web-push/*`) e **apenas anexa** os handlers de push ao `app/sw.ts` criado na **Sessão 29** — não
> reescreve o SW. Entrega: handlers `push`/`notificationclick` no SW + hook `useWebPush` (Axios client +
> TanStack onde fizer sentido) + componente `PushToggle` montado em duas páginas. Tudo via TDD/Vitest.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro; foco em **§7.4 Frontend — SW e subscrição**, §7.3 endpoints/config, §7.5 testes, §10-D): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar **S29 e S32 concluídas** antes de começar — S29 cria `app/sw.ts` com a seção marcada; S32 entrega `WebPushViewSet` em `/api/web-push/*`)
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Contrato cross-session (NÃO redefinir — usar verbatim)
- **Shape do payload de subscribe** (IDÊNTICO ao que o backend S32 lê em `WebPushViewSet.subscribe`):
  `{ endpoint: string, keys: { p256dh: string, auth: string } }` — exatamente o retorno de `subscription.toJSON()`.
- **Rotas** (S32, `basename web-push`): `GET /api/web-push/vapid-public-key/` → `{ publicKey }`;
  `POST /api/web-push/subscribe/` (body acima); `POST /api/web-push/unsubscribe/` (body `{ endpoint }`).
- `app/sw.ts` foi criado em S29; esta sessão **só anexa** na seção marcada por comentário (não reescrever Serwist/defaultCache/navigation fallback).

### Exemplares (arquivo:linha — exemplar > descrição, abrir e seguir)
- **Axios client (instância única, `withCredentials`, baseURL `/api`)** — toda chamada usa esta instância, nunca `axios` cru:
  `frontend/lib/api/client.ts:7-14` (`apiClient`).
- **Padrão de hook TanStack (query + mutation + `invalidateQueries` no sucesso, `apiClient.get`/`.post`)**:
  `frontend/lib/api/hooks/use-buildings.ts:10-23` (query) e `:43-57` (`useCreateBuilding`, mutation + invalidate).
- **Switch (Radix) apresentacional**: `frontend/components/ui/switch.tsx:8-29` (`<Switch checked disabled onCheckedChange />`).
- **Ponto de montagem ADMIN (página de Configurações, cards `Card`/`CardHeader`/`CardTitle`/`CardContent`, ícones lucide, `Separator`)**:
  `frontend/app/(dashboard)/settings/page.tsx:180-243` (seção "Minha Conta") e `:326` (`<Separator className="my-8" />`).
- **Ponto de montagem INQUILINO (perfil, cards empilhados, `'use client'`)**:
  `frontend/app/tenant/profile/page.tsx:34-114` (estrutura de cards do perfil).
- **Padrão de UI de notificações no inquilino (estados Bell/BellOff/Loader2/AlertCircle, `toast`, `getErrorMessage`)**:
  `frontend/app/tenant/notifications/page.tsx:1-86`.
- **Erro → mensagem PT**: `frontend/lib/utils/error-handler.ts:83-143` (`getErrorMessage`) e `:161-167` (`handleError`).
- **Teste de hook com MSW (renderHook + `createWrapper` + `waitFor` + `vi.spyOn(queryClient,'invalidateQueries')`)**:
  `frontend/lib/api/hooks/__tests__/use-persons.test.tsx:1-84`.
- **Test utils (providers/wrapper)**: `frontend/tests/test-utils.tsx:15-74` (`createTestQueryClient`, `createWrapper`, `renderWithProviders`).
- **Setup global de teste (MSW `server.listen`, `next/navigation` e `sonner` já mockados; SEM mock de `navigator.serviceWorker`/`PushManager`)**:
  `frontend/tests/setup.ts:1-19` e `:45-67`.
- **MSW: server + override por teste (`server.use(...)`) e array `handlers`**:
  `frontend/tests/mocks/server.ts:8-23`; `frontend/tests/mocks/handlers.ts:2081` (`export const handlers = [`).

## Escopo

### Arquivos a criar
- `frontend/lib/api/hooks/use-web-push.ts` — `useWebPush()` + helper `urlBase64ToUint8Array`.
- `frontend/components/notifications/push-toggle.tsx` — `PushToggle` (componente client).
- `frontend/lib/api/hooks/__tests__/use-web-push.test.tsx` — testes do hook + helper.
- `frontend/components/notifications/__tests__/push-toggle.test.tsx` — testes do componente.

### Arquivos a modificar
- `frontend/app/sw.ts` — **anexar** os listeners `push` e `notificationclick` na seção marcada pela S29 (sem reescrever o resto).
- `frontend/app/(dashboard)/settings/page.tsx` — montar `<PushToggle />` num `Card` próprio (admin), acima da `<Separator className="my-8" />` da seção do locador.
- `frontend/app/tenant/profile/page.tsx` — montar `<PushToggle />` num `Card` próprio (inquilino), no topo da `<div className="space-y-4">`.
- `frontend/tests/mocks/handlers.ts` — adicionar `webPushHandlers` (3 rotas) e incluir `...webPushHandlers` no array `handlers`.

## Especificação

Direção de dados (regra `frontend/CLAUDE.md`): **nenhum componente chama `apiClient`/`axios` diretamente** —
o `PushToggle` consome **apenas** o hook `useWebPush`. O hook usa a instância `apiClient` (`lib/api/client.ts`),
**nunca** `axios` cru.

### `frontend/app/sw.ts` (anexar na seção marcada da S29 — não reescrever o SW)
Adicionar dois listeners (tipos do lib `WebWorker`/Serwist já configurados pela S29). O payload do push é o
JSON enviado pelo backend (`send_web_push`, S32): `{ title, body, data }`, onde `data` pode conter `screen`.

**Atenção ao `data.screen`**: o backend emite valores **sem barra** (`'proofs'` p/ admin, `'payments'` p/ inquilino —
ver `core/services/notification_service.py:101,116,125`), pensados para a navegação do app Expo. NÃO tratar `screen`
como caminho literal: mapear para rotas web reais via `SCREEN_TO_PATH`, com fallback `/`. NÃO alterar o backend (fora do escopo).

```ts
interface PushPayload {
  title: string;
  body: string;
  data?: { screen?: string };
}

// data.screen do backend (bare) → rota web real; fallback '/'
const SCREEN_TO_PATH: Record<string, string> = {
  proofs: '/',
  payments: '/tenant/payments',
};

self.addEventListener('push', (event: PushEvent) => {
  const payload: PushPayload | undefined = event.data?.json(); // json() retorna any → sem `as`
  if (!payload) return;
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      data: payload.data ?? {},
    }),
  );
});

self.addEventListener('notificationclick', (event: NotificationClickEvent) => {
  event.notification.close();
  const data: unknown = event.notification.data;
  const screen =
    typeof data === 'object' && data !== null && 'screen' in data && typeof data.screen === 'string'
      ? data.screen
      : undefined;
  const targetPath = screen ? (SCREEN_TO_PATH[screen] ?? '/') : '/';
  event.waitUntil(focusOrOpen(targetPath));
});
```
- `focusOrOpen(path)`: `self.clients.matchAll({ type: 'window', includeUncontrolled: true })`; se houver um client
  cujo `new URL(client.url).pathname === path`, `client.focus()`; senão `self.clients.openWindow(path)`. Função pequena
  no mesmo arquivo (KISS), **sem `as`/`!`**.
- **NÃO** mexer no precache/defaultCache/navigation fallback da S29.

### `frontend/lib/api/hooks/use-web-push.ts`
Helper exportado (puro, testável isolado):
```ts
export function urlBase64ToUint8Array(base64: string): Uint8Array
```
- Converte a VAPID public key (base64url) em `Uint8Array` (padding `=`, troca `-`→`+` e `_`→`/`, `atob`, `charCodeAt`).

Hook exportado:
```ts
export type PushPermissionState = 'unsupported' | 'default' | 'denied' | 'granted';

export interface UseWebPushResult {
  isSupported: boolean;
  permission: PushPermissionState;
  isSubscribed: boolean;
  isPending: boolean;
  subscribe: () => Promise<void>;
  unsubscribe: () => Promise<void>;
}

export function useWebPush(): UseWebPushResult
```
- **Suporte**: `isSupported = typeof navigator !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window`.
  Se não suportado: `permission = 'unsupported'`, `subscribe`/`unsubscribe` no-op resolvido.
- **Estado inicial**: ao montar (effect), se suportado, ler `Notification.permission` e
  `(await navigator.serviceWorker.ready).pushManager.getSubscription()` para inicializar `permission`/`isSubscribed`.
- **`subscribe()`** (sequência):
  1. `Notification.requestPermission()`; se `!== 'granted'`, atualizar `permission` e retornar.
  2. Buscar a VAPID key: `apiClient.get<{ publicKey: string }>('/web-push/vapid-public-key/')`.
  3. `const registration = await navigator.serviceWorker.ready;`
  4. `const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) });`
  5. `apiClient.post('/web-push/subscribe/', subscription.toJSON());` — o body é **exatamente** `{ endpoint, keys: { p256dh, auth } }`.
  6. `isSubscribed = true`, `permission = 'granted'`.
- **`unsubscribe()`**:
  1. `const registration = await navigator.serviceWorker.ready;`
  2. `const subscription = await registration.pushManager.getSubscription();` — se `null`, no-op.
  3. `await subscription.unsubscribe();`
  4. `apiClient.post('/web-push/unsubscribe/', { endpoint: subscription.endpoint });`
  5. `isSubscribed = false`.
- `isPending` cobre a janela assíncrona de `subscribe`/`unsubscribe`. Erros: propagar (o `PushToggle` trata com `getErrorMessage`/`toast`).
- **TanStack onde fizer sentido**: a busca da VAPID key pode ser `useQuery` (`enabled: isSupported`, `staleTime` longo — a key é estável) com `queryFn` via `apiClient`; a inscrição/cancelamento envolvem APIs do browser além do POST, então ficam em callbacks `useCallback` (não force tudo em `useMutation` — KISS/YAGNI). Reaproveitar o estado do browser como fonte da verdade; **não** duplicar em cache de query.

### `frontend/components/notifications/push-toggle.tsx`
`'use client'`. Consome `useWebPush()`. Renderiza um bloco com `Switch` + rótulo "Ativar notificações" e
mensagem de estado em PT. Quatro estados (status nunca só por cor — sempre texto/ícone, acessível):
- **não suportado** (`!isSupported`): Switch `disabled`, texto "Notificações não são suportadas neste navegador." (ícone `BellOff`).
- **permissão negada** (`permission === 'denied'`): Switch `disabled`, texto "Permissão de notificações bloqueada — habilite nas configurações do navegador." (ícone `AlertCircle`).
- **inscrito** (`isSubscribed`): Switch `checked`, texto "Notificações ativadas." (ícone `Bell`). Ao desmarcar → `unsubscribe()`.
- **não inscrito** (suportado, não negado, não inscrito): Switch desmarcado, texto "Ative para receber avisos no dispositivo." Ao marcar → `subscribe()`.
- `Switch disabled={!isSupported || permission === 'denied' || isPending}`; `aria-label="Ativar notificações"`.
- Sucesso de `subscribe` → `toast.success('Notificações ativadas')`; sucesso de `unsubscribe` → `toast.success('Notificações desativadas')`;
  erro → `toast.error(getErrorMessage(err, 'Erro ao atualizar notificações'))` (padrão `tenant/notifications/page.tsx:42-48`).
- Componente apresentacional: **toda** a lógica de browser/HTTP vem do hook; o componente só orquestra `onCheckedChange` + toasts.

### Montagem
- `settings/page.tsx`: adicionar um `<Card>` "Notificações" (ícone `Bell`, padrão `:181-188`) contendo `<PushToggle />`,
  posicionado entre a seção "Alterar Senha" (`:245-324`) e a `<Separator className="my-8" />` (`:326`).
- `tenant/profile/page.tsx`: adicionar um `<Card>` "Notificações" contendo `<PushToggle />` no **topo** da
  `<div className="space-y-4">` (`:56`), antes do card "Dados Pessoais".

### `frontend/tests/mocks/handlers.ts` — `webPushHandlers`
Três handlers (mesmo estilo dos demais grupos no arquivo), incluídos em `...webPushHandlers` no array `handlers` (`:2081`):
- `http.get('*/web-push/vapid-public-key/', () => HttpResponse.json({ publicKey: 'BPtest...' }))`.
- `http.post('*/web-push/subscribe/', async ({ request }) => { const body = await request.json(); /* eco simples */ return HttpResponse.json(body, { status: 201 }); })`.
- `http.post('*/web-push/unsubscribe/', () => new HttpResponse(null, { status: 204 }))`.

## TDD

Rodar **somente os arquivos de teste desta sessão** (a suíte completa tem problemas pré-existentes de
xdist/Redis — ver memória do projeto). Mockar **apenas fronteiras externas**: `navigator.serviceWorker`/
`PushManager`/`Notification` (APIs do browser ausentes no jsdom) e o **HTTP via MSW**. **NUNCA** mockar o hook
`useWebPush` nos testes do `PushToggle` que verificam a integração de chamadas — ver carve-out abaixo.

### 1. Red — escrever os testes primeiro (devem falhar por arquivo inexistente)
Comando: `cd frontend && npx vitest run "lib/api/hooks/__tests__/use-web-push.test.tsx" "components/notifications/__tests__/push-toggle.test.tsx"`

**`use-web-push.test.tsx`** (montar um boundary mínimo de browser por teste e restaurar no `afterEach`; o MSW já intercepta o HTTP):
- **helper** `urlBase64ToUint8Array`: decodifica uma key base64url conhecida no `Uint8Array` esperado (asserir `instanceof Uint8Array` e `length` correto para uma key de exemplo).
- **não-suporte**: sem `serviceWorker`/`PushManager` em `navigator`/`window`, `isSupported === false` e `permission === 'unsupported'`; `subscribe()` resolve sem lançar e **não** dispara HTTP (MSW não recebe a chamada — asseverar via spy de `apiClient.post` *ou* contador no handler).
- **fluxo subscribe** (definir `navigator.serviceWorker.ready` → `{ pushManager: { subscribe, getSubscription } }`, `window.PushManager`, `Notification.requestPermission` → `'granted'`; o fake `subscribe` retorna um objeto com `endpoint` e `toJSON()` → `{ endpoint, keys: { p256dh, auth } }`): após `subscribe()`, `pushManager.subscribe` é chamado com `{ userVisibleOnly: true, applicationServerKey: <Uint8Array> }` e o **POST a `/web-push/subscribe/`** recebe body **exatamente** `{ endpoint, keys: { p256dh, auth } }` (capturar o body no handler MSW e asserir o shape); `isSubscribed === true`.
- **permissão negada no subscribe**: `Notification.requestPermission` → `'denied'` ⇒ `permission === 'denied'`, `isSubscribed === false`, **sem** POST de subscribe.
- **unsubscribe**: `getSubscription()` retorna uma inscrição fake com `endpoint` e `unsubscribe()`; após `unsubscribe()`, o fake `subscription.unsubscribe` é chamado e há **POST a `/web-push/unsubscribe/`** com body `{ endpoint }`; `isSubscribed === false`.
- **estado inicial inscrito**: `getSubscription()` retorna inscrição existente e `Notification.permission === 'granted'` ⇒ após montar, `isSubscribed === true`, `permission === 'granted'`.

**`push-toggle.test.tsx`** (`renderWithProviders`; controlar o boundary de browser como nos testes do hook — **não** mockar o hook):
- **não suportado** → texto "não são suportadas" presente e Switch `disabled`.
- **permissão negada** → texto "bloqueada" presente e Switch `disabled`.
- **não inscrito** → marcar o Switch dispara o fluxo (POST subscribe observado via MSW) e mostra `toast.success` "Notificações ativadas".
- **inscrito** → Switch `checked`, texto "ativadas"; desmarcar dispara `unsubscribe` (POST unsubscribe observado) e `toast.success` "Notificações desativadas".
- **erro no subscribe** → handler MSW de `/web-push/subscribe/` retorna 500 ⇒ `toast.error` com mensagem PT (override por teste via `server.use`, padrão `tests/mocks/server.ts:21-23`).

### 2. Green — implementar o hook, o helper, o `PushToggle`, os handlers MSW e os 2 listeners no `sw.ts` + montagem
### 3. Refactor — extrair `focusOrOpen` e o estado de permissão em funções/`useCallback` pequenos; sem duplicação; sem comentários supérfluos
### 4. Verify (gate frontend — zero erros/avisos)
- `cd frontend && npx vitest run "lib/api/hooks/__tests__/use-web-push.test.tsx" "components/notifications/__tests__/push-toggle.test.tsx"` → tudo verde.
- `cd frontend && npx tsc --noEmit` (sem erros nos arquivos tocados, incluindo `app/sw.ts`).
- `cd frontend && npx eslint "lib/api/hooks/use-web-push.ts" "components/notifications/push-toggle.tsx" "app/sw.ts" "app/(dashboard)/settings/page.tsx" "app/tenant/profile/page.tsx" "tests/mocks/handlers.ts" "lib/api/hooks/__tests__/use-web-push.test.tsx" "components/notifications/__tests__/push-toggle.test.tsx"` → zero erros/avisos.

## Constraints (NÃO fazer)

- **NÃO** reescrever o `app/sw.ts` da S29 — apenas **anexar** os 2 listeners na seção marcada; precache/defaultCache/navigation fallback ficam intactos.
- **NÃO** alterar o shape do payload de subscribe — deve ser **idêntico** ao backend S32: `{ endpoint, keys: { p256dh, auth } }` (= `subscription.toJSON()`). O unsubscribe envia `{ endpoint }`.
- **NÃO** chamar `axios` cru nem `fetch` direto em componente/hook — usar a instância `apiClient` (`lib/api/client.ts`).
- **NÃO** chamar `apiClient`/axios em componente — `PushToggle` consome só `useWebPush`.
- **NÃO** mockar código interno (o hook `useWebPush`, ORM, biblioteca, internals do TanStack Query) — mockar **apenas** as fronteiras externas: `navigator.serviceWorker`/`PushManager`/`Notification` (ausentes no jsdom) e o HTTP via MSW.
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`; **em produção** (hook/componente/sw), NÃO usar `as`/`!` — corrigir o tipo na raiz (`import type`, `??`, null guards; `noUncheckedIndexedAccess`).
- **CARVE-OUT (somente fixtures de teste)**: nos `*.test.tsx`, ao construir o boundary fake de browser (`navigator.serviceWorker`, objeto de inscrição, `PushManager`) cujo shape completo é inviável de satisfazer, É PERMITIDO `as <Tipo>` / `as unknown as <Tipo>` restrito a esses helpers de fixture — exatamente como o carve-out de `prompts/24-frontend-rent-calendar-ui.md` (~linha 206). Em qualquer outro lugar dos testes e em todo o código de produção, `as`/`!` continuam proibidos.
- **NÃO** instalar dependências novas nesta sessão (Serwist/idb-keyval/etc. já vieram em S29/S30; backend `pywebpush` em S31). Apenas Radix Switch/lucide/`apiClient`/TanStack já presentes.
- **NÃO** rodar a suíte completa de testes — só os 2 arquivos desta sessão (evitar falhas pré-existentes de xdist/Redis).
- SOLID/DRY/KISS/YAGNI; sem re-exports/barrels (cada módulo importa da fonte); sem `from __future__` (irrelevante no frontend, mas válido como princípio: importar tipos direto). Status nunca só por cor (acessibilidade).

## Critérios de Aceite

- [ ] `frontend/lib/api/hooks/use-web-push.ts` exporta `useWebPush()` e `urlBase64ToUint8Array(base64): Uint8Array`.
- [ ] `useWebPush` detecta suporte (`'serviceWorker' in navigator && 'PushManager' in window`); sem suporte → `permission === 'unsupported'`, callbacks no-op.
- [ ] `subscribe()` chama `Notification.requestPermission`, GET `/web-push/vapid-public-key/`, `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })` e POST `/web-push/subscribe/` com body **`{ endpoint, keys: { p256dh, auth } }`** (= `subscription.toJSON()`).
- [ ] `unsubscribe()` chama `subscription.unsubscribe()` e POST `/web-push/unsubscribe/` com body `{ endpoint }`.
- [ ] Todas as chamadas HTTP do hook usam `apiClient` (nunca `axios` cru/`fetch`).
- [ ] `frontend/app/sw.ts` tem `addEventListener('push', ...)` → `self.registration.showNotification(title, { body, icon: '/icons/icon-192.png', badge, data })` e `addEventListener('notificationclick', ...)` → foca/abre client na rota mapeada de `data.screen` via `SCREEN_TO_PATH` (fallback `/`), **sem `as`/`!`**; o restante do SW da S29 **inalterado**.
- [ ] `PushToggle` reflete os 4 estados (não suportado / negado / inscrito / não inscrito) com texto+ícone (status não só por cor); marca/desmarca dispara subscribe/unsubscribe + `toast`.
- [ ] `<PushToggle />` montado em `settings/page.tsx` (admin) e `tenant/profile/page.tsx` (inquilino).
- [ ] `webPushHandlers` (3 rotas) adicionados a `tests/mocks/handlers.ts` e incluídos no array `handlers`.
- [ ] Nenhum componente chama `apiClient`/axios — `PushToggle` consome só `useWebPush`.
- [ ] `npx vitest run` dos 2 arquivos 100% verde; `npx tsc --noEmit` sem erros nos arquivos tocados; `eslint` zero erros/avisos.
- [ ] Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem re-exports; sem dependência nova. `as`/`!` ausentes em produção; único `as` permitido é nos helpers de fixture de teste (carve-out).

## Handoff

1. Rodar e confirmar verde (colar saída como evidência):
   - `cd frontend && npx vitest run "lib/api/hooks/__tests__/use-web-push.test.tsx" "components/notifications/__tests__/push-toggle.test.tsx"`
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "lib/api/hooks/use-web-push.ts" "components/notifications/push-toggle.tsx" "app/sw.ts" "app/(dashboard)/settings/page.tsx" "app/tenant/profile/page.tsx" "tests/mocks/handlers.ts" "lib/api/hooks/__tests__/use-web-push.test.tsx" "components/notifications/__tests__/push-toggle.test.tsx"`
2. Atualizar `prompts/SESSION_STATE.md`: marcar **Sessão 33 concluída**; registrar que a Frente D está completa
   (S31 model/migração + S32 sender/endpoints/VAPID + S33 SW handlers/hook/toggle); anotar que o payload de
   subscribe foi verificado idêntico entre S32 (leitura) e S33 (envio via `subscription.toJSON()`), e que
   `app/sw.ts` recebeu **apenas** os listeners de push (S29 intacto).
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): add web push UI (SW handlers, useWebPush hook, settings/profile toggle)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A próxima sessão começa lendo o `SESSION_STATE.md`.
