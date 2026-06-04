# Sessão 29 — Frontend: Service Worker com Serwist (precache + fallback offline)

> Parte da feature "App Mobile Completo — PWA + Offline + Web Push" (Fase 2 do design). Esta sessão
> liga o **Service Worker** via Serwist: envolve o `next.config.js` com `withSerwist`, cria o SW custom
> `app/sw.ts` (precache do shell + runtime caching + fallback de navegação offline) e configura tipos de
> webworker. **NÃO** implementa handlers de Web Push — apenas deixa a seção marcada onde a **Sessão 33**
> vai inseri-los. A verificação desta sessão é **via build de produção** (gera `public/sw.js`), não via
> teste unitário (SW é difícil de unit-testar — ver TDD).

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro, foco nas seções 3, 5.2, 5.3, 8 Fase 2, 9): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar que a **Sessão 28** — manifest + ícones — está concluída; `app/manifest.ts` deve existir, pois o Serwist injeta o shell no precache)
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `.claude/rules/architecture.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — abrir e seguir)
- **`next.config.js` (CommonJS, a envolver)**: `frontend/next.config.js:1-27` — `const nextConfig = { ... }` em `:2-25`
  (com `output: 'standalone'` em `:4` e `experimental.optimizePackageImports` em `:5-7`); `module.exports = nextConfig;`
  em `:27`. Esta sessão troca **apenas** a linha de export por `module.exports = withSerwist(nextConfig);`, mantendo o
  objeto `nextConfig` **intacto** (todas as opções: `output`, `reactStrictMode`, `experimental`, `skipTrailingSlashRedirect`,
  `eslint`, `typescript`, `staticPageGenerationTimeout`, `onDemandEntries`).
- **`app/layout.tsx` (metadata/manifest já vinculados)**: `frontend/app/layout.tsx:1-22` — `export const metadata` em
  `:5-8`. **NÃO** modificar nesta sessão (viewport é S26, themeColor/appleWebApp é S28). Apenas confirmar que existe.
- **`tsconfig.json` (lib/paths/include)**: `frontend/tsconfig.json:1-43` — `lib: ["dom", "dom.iterable", "esnext"]`
  em `:4`; `include` em `:36-41`. O SW roda em contexto webworker (`WebWorker` lib + globals do Serwist), distinto do
  DOM — resolver via `tsconfig` dedicado (ver Especificação).
- **`.gitignore` (frontend)**: `frontend/.gitignore:12-14` — seção `# next.js`. Adicionar os artefatos gerados do SW
  logo após (ver Escopo).

### Contrato cruzado (NÃO redefinir aqui; criado/consumido por outras sessões)
- **S28 (pré-requisito)** criou `frontend/app/manifest.ts` (`MetadataRoute.Manifest`) + ícones; o Serwist precacheia o
  app shell automaticamente via `self.__SW_MANIFEST` injetado no build.
- **S33 (consumidor futuro)** vai **APENAS adicionar** (append) os listeners `push` e `notificationclick` ao **mesmo**
  arquivo `frontend/app/sw.ts` que esta sessão cria. Por isso esta sessão **deve** deixar uma seção marcada,
  com o comentário exato (ver Especificação), e **NÃO** implementar push/notificação aqui.

## Escopo

### Arquivos a criar
- `frontend/app/sw.ts` — instância Serwist (precache + `defaultCache` + `navigationPreload` + fallback offline) +
  seção marcada para os handlers de Web Push (S33).
- `frontend/app/offline/page.tsx` — página estática mínima de fallback offline (precacheada pelo SW).
- `frontend/tsconfig.sw.json` — tsconfig dedicado para o SW (lib `webworker`), estendendo o `tsconfig.json` base.

### Arquivos a modificar
- `frontend/next.config.js` — envolver com `withSerwist` (CommonJS), mantendo o objeto `nextConfig` e o `output: 'standalone'`.
- `frontend/tsconfig.json` — **excluir** `app/sw.ts` do `include` principal (DOM lib) — ele é coberto pelo `tsconfig.sw.json`.
- `frontend/.gitignore` — ignorar os artefatos gerados: `public/sw.js` e `public/swe-worker-*.js`.
- `frontend/package.json` — adicionar deps `@serwist/next` e `serwist` (via `npm install`, não editar à mão).

## Especificação

### Dependências (instalar com `npm install`, dentro de `frontend/`)
- `npm install @serwist/next serwist` — `@serwist/next` (plugin Next + `defaultCache` em `@serwist/next/worker`) e
  `serwist` (a classe `Serwist`). Ambas vão para `dependencies` (não são dev-only: o SW é runtime de produção).
- **Versões**: usar a última estável compatível com Next 14.2.x (Serwist é o sucessor mantido do Workbox/next-pwa em 2026).
  Confirmar via `npm view @serwist/next version` antes de fixar; deixar o range do `npm install` (caret) como o projeto já usa.

### `frontend/next.config.js` (CommonJS — espelhar o estilo de `next.config.js:1`)
Envolver o `nextConfig` existente. Forma exata (CJS, `require(...).default`):
```js
const withSerwist = require('@serwist/next').default({
  swSrc: 'app/sw.ts',
  swDest: 'public/sw.js',
  disable: process.env.NODE_ENV === 'development',
});

const nextConfig = { /* ...intacto, com output: 'standalone' ... */ };

module.exports = withSerwist(nextConfig);
```
- `disable` em desenvolvimento evita o overhead/cache do SW no `npm run dev` (regenera só no build de produção).
- **NÃO** remover nem reordenar nenhuma opção de `nextConfig`; só trocar a linha `module.exports`.

### `frontend/app/sw.ts` (instância Serwist)
- Diretiva de referência de tipos do Serwist no topo (`/// <reference lib="webworker" />` + os tipos do Serwist).
- Declarar o escopo global do worker tipado (`declare const self: ServiceWorkerGlobalScope & { __SW_MANIFEST: ... }`)
  usando o tipo de manifesto exportado por `serwist` (`PrecacheEntry`/`SerwistGlobalConfig` conforme a API real — confirmar
  o nome exato importável de `serwist` ao implementar; **importar da fonte**, sem re-export).
- Importar `defaultCache` de `@serwist/next/worker` e `Serwist` de `serwist`.
- Instanciar:
  ```ts
  const serwist = new Serwist({
    precacheEntries: self.__SW_MANIFEST,
    skipWaiting: true,
    clientsClaim: true,
    navigationPreload: true,
    runtimeCaching: defaultCache,
    fallbacks: {
      entries: [
        { url: '/offline', matcher: ({ request }) => request.destination === 'document' },
      ],
    },
  });
  serwist.addEventListeners();
  ```
  - **Fallback offline de navegação**: rota `/offline` servida quando a navegação falha sem rede. **Criar** nesta sessão
    a página `frontend/app/offline/page.tsx` como página estática mínima em PT ("Você está offline — reconecte para
    continuar") — ela precisa estar no precache para o fallback funcionar. (É um arquivo desta sessão; a S28 não a cria.)
- **Seção marcada para a Sessão 33** — incluir EXATAMENTE este bloco de comentário, no fim do arquivo, **após**
  `serwist.addEventListeners();`, sem nenhum handler implementado:
  ```ts
  // =====================================================================
  // === Web Push handlers (Sessão 33) ===
  // S33 adiciona aqui os listeners 'push' (self.registration.showNotification)
  // e 'notificationclick' (focar/abrir a aba em event.notification.data.screen).
  // NÃO implementar nesta sessão — apenas o precache/offline acima.
  // =====================================================================
  ```

### `frontend/tsconfig.sw.json` (tipos do service worker)
- Estende o base e troca a `lib` para webworker (o SW não tem `dom`); cobre só `app/sw.ts`:
  ```json
  {
    "extends": "./tsconfig.json",
    "compilerOptions": {
      "lib": ["esnext", "webworker"],
      "types": ["@serwist/next/typings"]
    },
    "include": ["app/sw.ts"],
    "exclude": []
  }
  ```
- Em `frontend/tsconfig.json`, **excluir** `app/sw.ts` do `include` principal (que usa `dom` lib) para evitar conflito de
  globais DOM × WebWorker. Ajustar a chave `include` (`:36-41`) acrescentando o exclude do arquivo do SW (via `exclude`
  ou um glob negativo conforme suportado pelo `tsc` do projeto). Documentar a escolha na nota de handoff.
- **Documentar** no `frontend/CLAUDE.md`? **NÃO** — manter o escopo fechado; a documentação fica na nota do `SESSION_STATE.md`.

### `frontend/.gitignore`
- Logo após a seção `# next.js` (`:12-14`), adicionar:
  ```
  # serwist (service worker gerado no build)
  public/sw.js
  public/swe-worker-*.js
  ```

## TDD

**Service Worker é difícil de unit-testar** — não há DOM, o `self.__SW_MANIFEST` só existe no bundle do build, e mockar
o `Serwist` interno violaria a política de mocks do projeto (mockar só fronteiras externas, nunca código de lib/interno).
Portanto, **a verificação desta sessão é o build de produção** que gera `public/sw.js`. Não há arquivo de teste Vitest
novo; o "Red→Green" é o estado do artefato e dos type-checks.

### 1. Red — estado que deve falhar ANTES da implementação
- `cd frontend && npm run build` **falha ou não gera** `public/sw.js` (Serwist ainda não está configurado).
- `cd frontend && npx tsc --project tsconfig.sw.json --noEmit` falha (arquivo `app/sw.ts` inexistente).

Cenários concretos a satisfazer (cada um é binário, verificável no terminal):
- **C1 — Build gera o SW**: após a implementação, `npm run build` conclui sem erro **e** o arquivo `public/sw.js` passa
  a existir (não-vazio). Verificar com `Test-Path frontend/public/sw.js` (PowerShell) **ou** listando `frontend/public/`.
- **C2 — Precache do manifest**: `public/sw.js` referencia o manifesto injetado (contém o token `__SW_MANIFEST`
  substituído pela lista de URLs do precache do shell). Verificação: o build não emite warning de "manifest vazio".
- **C3 — Fallback offline**: a rota `/offline` (página existente/criada) é precacheada — `public/sw.js` referencia
  `/offline`; navegação sem rede para uma rota de documento cai no fallback (verificação manual descrita no handoff,
  não automatizada nesta sessão).
- **C4 — Dev não gera SW**: com `NODE_ENV=development` (`npm run dev`), o Serwist está `disable: true` — não regenera
  `public/sw.js` (sanity: nenhum erro de SW no dev server). Não bloquear; é asserção de configuração.
- **C5 — Tipos do SW limpos**: `npx tsc --project tsconfig.sw.json --noEmit` passa (lib webworker, `self.__SW_MANIFEST`
  tipado, sem `any`).
- **C6 — Tipos do app intactos**: `npx tsc --noEmit` (config principal) continua limpo — `app/sw.ts` está excluído do
  include DOM e não vaza globais de webworker para o app.
- **C7 — Seção S33 presente**: `frontend/app/sw.ts` contém o comentário literal `=== Web Push handlers (Sessão 33) ===`
  e **nenhum** listener `'push'`/`'notificationclick'` (grep deve retornar zero ocorrências desses eventos).

### 2. Green — implementar o mínimo
- `npm install @serwist/next serwist`; envolver `next.config.js`; criar `app/sw.ts` (precache + defaultCache +
  navigationPreload + fallback + seção S33); criar `tsconfig.sw.json`; excluir `app/sw.ts` do include principal;
  atualizar `.gitignore`; garantir a página `/offline`.

### 3. Refactor — sem duplicação; opções do `Serwist` legíveis (constantes nomeadas se necessário); sem comentários supérfluos
fora da seção marcada da S33. Não introduzir abstrações especulativas (YAGNI) — só o SW desta fase.

### 4. Verify (gate do projeto — frontend)
- **Build (verificação primária)**: `cd frontend && npm run build` → conclui sem erro **e** `public/sw.js` existe e é
  não-vazio (C1/C2).
- **Type-check do SW**: `cd frontend && npx tsc --project tsconfig.sw.json --noEmit` → zero erros (C5).
- **Type-check do app**: `cd frontend && npx tsc --noEmit` → zero erros (C6).
- **Lint**: `cd frontend && npx eslint "app/sw.ts" "next.config.js"` → zero erros/avisos. Se o `next.config.js` estiver
  fora do escopo do ESLint do projeto (dirs em `next.config.js:10-13`), lintar ao menos `app/sw.ts` e rodar
  `npm run lint` (escopo configurado) garantindo zero novos avisos.
- Colar as saídas como evidência no handoff. **NÃO** rodar a suíte completa de testes (problemas pré-existentes de
  xdist/Redis — ver memória do projeto); esta sessão não adiciona testes Vitest.

## Constraints (NÃO fazer)

- **NÃO** implementar handlers de Web Push (`push`/`notificationclick`) — pertencem à **Sessão 33**; apenas deixar a
  seção marcada com o comentário literal `=== Web Push handlers (Sessão 33) ===`.
- **NÃO** quebrar o build standalone: o objeto `nextConfig` (incluindo `output: 'standalone'` e demais opções) permanece
  **intacto**; só a linha `module.exports` muda para `withSerwist(nextConfig)`.
- **NÃO** converter `next.config.js` para ESM/`.mjs` — manter CommonJS (`require`/`module.exports`), como o projeto já usa.
- **NÃO** modificar `app/layout.tsx`, `app/manifest.ts` nem ícones (S28); **NÃO** criar o persister/offline-banner (S30)
  nem hooks/toggle de push (S33).
- **NÃO** mockar `Serwist`, `defaultCache` ou qualquer código de lib/interno — a política do projeto permite mock **apenas**
  de fronteiras externas (HTTP, `navigator.serviceWorker`/`PushManager`, Chrome, filesystem). Como SW é inviável de unit-testar
  sem mockar internals, esta sessão **não escreve teste Vitest** e verifica via build (decisão deliberada, documentada).
- **NÃO** rodar a suíte completa de testes (apenas o gate de build/type-check/lint desta sessão).
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error` — resolver os tipos do webworker na raiz (via
  `tsconfig.sw.json` + `/// <reference lib="webworker" />`), nunca suprimir.
- **NÃO** criar re-exports/barrels para os símbolos do Serwist — importar `Serwist` de `serwist` e `defaultCache` de
  `@serwist/next/worker` direto da fonte.
- **NÃO** adicionar `from __future__ import annotations` (regra do projeto; não há código Python nesta sessão, mas vale o lembrete).
- SOLID/DRY/KISS/YAGNI — o SW tem responsabilidade única (precache + offline); sem código especulativo para push.

## Critérios de Aceite

- [ ] `@serwist/next` e `serwist` instalados em `frontend/package.json` `dependencies` (via `npm install`).
- [ ] `frontend/next.config.js` envolve `nextConfig` com `withSerwist` (CJS `require('@serwist/next').default({ swSrc: 'app/sw.ts', swDest: 'public/sw.js', disable: NODE_ENV === 'development' })`); `output: 'standalone'` e todas as demais opções **intactas**.
- [ ] `frontend/app/sw.ts` existe: instancia `Serwist` com `precacheEntries: self.__SW_MANIFEST`, `runtimeCaching: defaultCache`, `navigationPreload: true` e `fallbacks` de navegação (`/offline`); chama `serwist.addEventListeners()`.
- [ ] `frontend/app/sw.ts` contém a seção literal `=== Web Push handlers (Sessão 33) ===` e **nenhum** listener `push`/`notificationclick` (zero ocorrências).
- [ ] Página de fallback `frontend/app/offline/page.tsx` **criada nesta sessão** e precacheada (referenciada em `public/sw.js`).
- [ ] `frontend/tsconfig.sw.json` criado (lib `webworker`, cobre `app/sw.ts`); `app/sw.ts` excluído do include DOM principal em `tsconfig.json`.
- [ ] `frontend/.gitignore` ignora `public/sw.js` e `public/swe-worker-*.js`.
- [ ] `cd frontend && npm run build` conclui sem erro **e** gera `public/sw.js` não-vazio (verificação primária).
- [ ] `npx tsc --project tsconfig.sw.json --noEmit` e `npx tsc --noEmit` (config principal) ambos sem erros.
- [ ] `npx eslint "app/sw.ts"` (e `npm run lint` no escopo configurado) sem erros/avisos.
- [ ] Sem `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`; sem re-exports/barrels; build standalone não quebrado.

## Handoff

1. Rodar e confirmar verde (colar saída como evidência):
   - `cd frontend && npm run build` (conferir que `public/sw.js` existe e é não-vazio — `Test-Path public/sw.js` no PowerShell)
   - `cd frontend && npx tsc --project tsconfig.sw.json --noEmit`
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "app/sw.ts"` + `npm run lint`
2. **Verificação manual (documentar, não bloqueia)** — cobre o critério de aceite §10-B do design (PWA instalável),
   que não é automatizável em CI: `npm run start` (build de produção), abrir o app, e nas DevTools:
   - **Application → Service Workers**: confirmar o SW ativo; em Network marcar "Offline" e recarregar uma rota de
     documento → deve cair na página `/offline`.
   - **Application → Manifest**: confirmar "Installable" sem erros e os ícones 192/512 carregados (valida o manifest da S28 + SW).
   - **iOS (se possível)**: Safari → Compartilhar → "Adicionar à Tela de Início" → o atalho abre em standalone com o ícone correto.
   Anotar os resultados no `SESSION_STATE.md`.
3. Atualizar `prompts/SESSION_STATE.md`: marcar **Sessão 29 concluída**; registrar:
   - que `frontend/app/sw.ts` foi criado e que a **Sessão 33** vai **apenas adicionar** (append) os handlers
     `push`/`notificationclick` na seção marcada `=== Web Push handlers (Sessão 33) ===` (não recriar o arquivo);
   - a decisão de verificação-via-build (sem teste Vitest do SW) e a escolha de `tsconfig.sw.json` (lib webworker) com
     `app/sw.ts` excluído do include DOM principal;
   - que `output: 'standalone'` permanece intacto e que `public/sw.js`/`swe-worker-*.js` agora são ignorados pelo git.
4. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): wire Serwist service worker (precache + offline fallback)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. A **Sessão 30** (offline read-only: persister IndexedDB + OfflineBanner) começa lendo o `SESSION_STATE.md`.
