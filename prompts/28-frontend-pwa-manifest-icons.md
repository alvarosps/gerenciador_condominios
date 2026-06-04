# Sessão 28 — Frontend: PWA manifest + ícones gerados + metadata Apple

> Parte da feature "App Mobile Completo — PWA" (Fase 2 do design). Esta sessão entrega o **manifest
> nativo do Next** (`app/manifest.ts`), os **ícones gerados por script reproduzível** (sem binários
> "mágicos" sem origem) e a **metadata Apple** no `layout.tsx`. **Depende da Sessão 26** (o
> `export const viewport: Viewport` já existe em `app/layout.tsx`); esta sessão **EDITA** esse mesmo
> export para adicionar `themeColor` — **nunca** cria um segundo export `viewport`. Não toca em
> Service Worker (Sessão 29) nem em offline/push (Sessões 30/33).

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro, foco nas seções **5.1, 5.2, 5.4, 9** e nas decisões §3): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar que a **Sessão 26 está concluída** — o `viewport` export deve existir em `app/layout.tsx` — antes de começar)
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `.claude/rules/architecture.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — abrir e seguir)
- **`layout.tsx` atual (alvo da edição)**: `frontend/app/layout.tsx:1-22` — hoje exporta só `metadata` (`:5-8`); a **Sessão 26** adicionou `export const viewport: Viewport = { width, initialScale, viewportFit: 'cover' }` (importando `type Viewport` de `next`). Esta sessão **acrescenta `themeColor`** a esse export existente e **acrescenta `appleWebApp` + `manifest` ausentes** ao objeto `metadata`. Se o export `viewport` **não existir**, a Sessão 26 não foi concluída — **parar e reportar** (não criar o export aqui).
- **Tokens OKLCH do tema (fonte das cores HEX)**: `frontend/app/globals.css:60` (`--primary: oklch(0.55 0.15 175)` — teal, será o `theme_color`) e `:54` (`--background: oklch(0.985 0.002 240)` — quase-branco, será o `background_color`). Converter para HEX aproximado e **documentar o valor** (ver Especificação).
- **`next.config.js` (CJS, `output: 'standalone'`)**: `frontend/next.config.js:1-27` — **NÃO** editar nesta sessão (o `withSerwist` é da Sessão 29). Apenas ler para confirmar que o manifest nativo do Next não conflita com a config atual.
- **Convenção de script Node em `frontend/scripts/`**: `frontend/scripts/generate-types.js` (script standalone executável via `node scripts/...`; o `package.json:18` registra `"generate-types": "node scripts/generate-types.js"`). Seguir o **mesmo estilo** (script único, sem dependências de runtime do app).
- **Bloco `devDependencies` do `package.json`**: `frontend/package.json:89-113` — `sharp` entra aqui (ordem alfabética).

## Escopo

### Arquivos a criar
- `frontend/app/manifest.ts` — `export default function manifest(): MetadataRoute.Manifest`.
- `frontend/scripts/icon-source.svg` — SVG-fonte (glyph de prédio simples na cor primária `#0d847a`), quadrado 512×512.
- `frontend/scripts/generate-icons.mjs` — script Node (ESM) que usa `sharp` para rasterizar o SVG nos PNGs alvo.
- `frontend/app/__tests__/manifest.test.ts` — teste unitário do objeto retornado por `manifest()`.
- **Ícones gerados pelo script** (não commitar à mão — produto do `generate-icons.mjs`):
  - `frontend/public/icons/icon-192.png` (192×192)
  - `frontend/public/icons/icon-512.png` (512×512)
  - `frontend/public/icons/icon-512-maskable.png` (512×512, com safe-zone/padding maskable)
  - `frontend/app/icon.png` (512×512 — favicon/app icon nativo do Next)
  - `frontend/app/apple-icon.png` (180×180 — apple-touch-icon nativo do Next)

### Arquivos a modificar
- `frontend/app/layout.tsx` — **EDITAR** o `export const viewport` da Sessão 26 (adicionar `themeColor`); **adicionar** `appleWebApp` e `manifest` ao objeto `metadata` existente.
- `frontend/package.json` — adicionar `sharp` em `devDependencies` (ver instrução de instalação).

> O diretório `frontend/public/` ainda **não existe** (confirmado: sem `public/`). Criá-lo via o script
> (`mkdir` recursivo de `public/icons/`) — o script é a fonte única dos PNGs.

## Especificação

### 1. Conversão OKLCH → HEX (documentar o valor escolhido)
O tema é a **fonte da verdade** (`globals.css`). Converter os dois tokens para HEX e **escrever o valor
escolhido num comentário** no topo de `manifest.ts` (uma linha, ex.: `// theme_color = oklch(0.55 0.15 175)
≈ #0d847a (primary)`):
- `theme_color` / cor do glyph ← `--primary: oklch(0.55 0.15 175)` → **`#0d847a`** (teal; aproximação documentada — pode refinar com um conversor, mas **registrar o HEX final usado**).
- `background_color` ← `--background: oklch(0.985 0.002 240)` → **`#fbfbfc`** (quase-branco).

Usar **o mesmo HEX do glyph** (`#0d847a`) no `icon-source.svg` e o **mesmo `#fbfbfc`** como fundo dos
ícones (e/ou transparente para o maskable conforme abaixo). Manter os dois HEX **idênticos** entre
`manifest.ts` e `icon-source.svg` (DRY de intenção; não há import cruzado de cor, então a constância é
garantida pela documentação + revisão).

### 2. `app/manifest.ts`
```ts
import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  // theme_color = oklch(0.55 0.15 175) ≈ #0d847a (primary) ; background = oklch(0.985 0.002 240) ≈ #fbfbfc
  return {
    name: 'Condomínios Manager',
    short_name: 'Condomínios',
    description: 'Sistema de gerenciamento de locações',
    start_url: '/',
    display: 'standalone',
    lang: 'pt-BR',
    background_color: '#fbfbfc',
    theme_color: '#0d847a',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}
```
- Next vincula o manifest automaticamente (`<link rel="manifest" href="/manifest.webmanifest">`) ao
  existir `app/manifest.ts` — **não** adicionar `<link>` manual nem campo `manifest` apontando para um
  arquivo estático.
- Acentos PT-BR no `name` ("Condomínios Manager") são intencionais.

### 3. `app/layout.tsx` — edição cirúrgica (sem duplicar export)
- **`viewport`** (export criado na Sessão 26): adicionar **somente** o campo `themeColor` ao objeto
  existente, casando os tokens light/dark do tema (teal). Usar a forma de array do Next para
  light/dark scheme:
  ```ts
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#0d847a' },
    { media: '(prefers-color-scheme: dark)', color: '#0d847a' },
  ],
  ```
  (manter `width`, `initialScale`, `viewportFit: 'cover'` intactos). **Não** mover `themeColor` para
  `metadata` (no Next 14 ele pertence a `viewport`).
- **`metadata`** (objeto existente, `:5-8`): adicionar
  ```ts
  appleWebApp: { capable: true, statusBarStyle: 'default', title: 'Condomínios' },
  ```
  e **não** definir `metadata.manifest` (o vínculo é automático via `app/manifest.ts`). Manter `title`
  e `description` atuais.

### 4. `frontend/scripts/icon-source.svg`
SVG quadrado **512×512** (`viewBox="0 0 512 512"`), fundo `#fbfbfc` (ou transparente), com um **glyph de
prédio simples** na cor `#0d847a`: um retângulo vertical com algumas "janelas" (pequenos quadrados
recortados em cor de fundo) e uma porta. Geometria mínima (KISS) — basta ser reconhecível como prédio.
Sem dependências externas, sem `<image>` embutido, sem fontes externas.

### 5. `frontend/scripts/generate-icons.mjs`
Script ESM standalone (rodável por `node scripts/generate-icons.mjs` a partir de `frontend/`):
- Importar `sharp` e `node:fs`/`node:path` (`mkdirSync(..., { recursive: true })`).
- Ler `scripts/icon-source.svg`.
- Gerar, a partir do MESMO SVG-fonte:
  - `public/icons/icon-192.png` — `resize(192, 192)`.
  - `public/icons/icon-512.png` — `resize(512, 512)`.
  - `public/icons/icon-512-maskable.png` — `resize(512, 512)` com **safe-zone maskable** (o glyph dentro
    de ~80% central; aplicar via `extend`/padding com `background: '#fbfbfc'` OU compor o SVG já com
    padding — escolher a abordagem mais simples e documentar numa linha).
  - `app/icon.png` — `resize(512, 512)` (ícone nativo do Next; favicon de alta resolução).
  - `app/apple-icon.png` — `resize(180, 180)` (apple-touch-icon nativo do Next; fundo **sólido**
    `#fbfbfc`, sem transparência — iOS não respeita alpha no apple-touch).
- Criar diretórios alvo (`public/icons/`) antes de escrever.
- Log final listando os 5 arquivos gerados (evidência no console).
- **Não** registrar um script npm novo no `package.json` (YAGNI — geração é manual/raríssima); rodar
  diretamente por `node scripts/generate-icons.mjs`. Documentar o comando neste prompt e no
  SESSION_STATE.

### 6. `sharp` como devDependency
`sharp` é só de build de ícones (nunca importado pelo app em runtime) → **devDependency**. Instalar:
```powershell
cd frontend ; npm install --save-dev sharp
```
Confirmar que entrou em `package.json:devDependencies` (ordem alfabética, junto de `prettier`/`tailwindcss-animate`).

## TDD

Rodar **somente os arquivos de teste desta sessão** (a suíte completa tem problemas pré-existentes de
xdist/Redis — ver memória do projeto). Nada de `npm run test:unit` cheio.

### 1. Red — escrever o teste primeiro (deve falhar por `app/manifest.ts` inexistente)
Comando: `cd frontend && npx vitest run "app/__tests__/manifest.test.ts"`

`frontend/app/__tests__/manifest.test.ts` — importar `manifest` de `@/app/manifest` e chamar `manifest()`.
Cobrir, no mínimo:
- **Campos obrigatórios presentes**: `name === 'Condomínios Manager'`, `short_name === 'Condomínios'`,
  `start_url === '/'`, `display === 'standalone'`, `lang === 'pt-BR'`.
- **Cores HEX**: `theme_color === '#0d847a'` e `background_color === '#fbfbfc'` (asserir os HEX
  documentados — se refinar a conversão, atualizar a asserção para o valor real).
- **Ícones**: `result.icons` é array com **≥ 2** entradas; todas têm `type === 'image/png'`; existe
  **pelo menos uma** com `sizes === '512x512'` e `purpose === 'maskable'`; existe uma `192x192`.
  (Iterar com `noUncheckedIndexedAccess` em mente — usar `?.`/guards, sem `!`.)
- **`src` dos ícones** começam com `/icons/` (caminho público).

### 2. Green — implementar `manifest.ts`, o SVG, o `generate-icons.mjs`, editar `layout.tsx`, instalar `sharp`
- Implementar `manifest.ts` até o teste passar.
- Criar `icon-source.svg` + `generate-icons.mjs`; instalar `sharp`; **rodar o script** e confirmar que
  os 5 arquivos existem (evidência abaixo). Editar `layout.tsx` (viewport `themeColor` + metadata
  `appleWebApp`).

### 3. Refactor — sem duplicação; nomes claros; sem comentários supérfluos (manter só o comentário do HEX documentado)

### 4. Verify (gate frontend — apenas arquivos desta sessão)
- **Testes**: `cd frontend && npx vitest run "app/__tests__/manifest.test.ts"` → verde.
- **Geração de ícones (evidência empírica)**: `cd frontend ; node scripts/generate-icons.mjs` e então
  confirmar que existem (colar a listagem):
  `frontend/public/icons/icon-192.png`, `icon-512.png`, `icon-512-maskable.png`,
  `frontend/app/icon.png`, `frontend/app/apple-icon.png`.
- **Type-check**: `cd frontend && npx tsc --noEmit` → sem erros nos arquivos tocados.
- **Lint**: `cd frontend && npx eslint "app/manifest.ts" "app/layout.tsx" "app/__tests__/manifest.test.ts"`
  → zero erros/avisos. (O `.mjs` de script e o `.svg` ficam fora dos `dirs` lintados do `next.config.js:12`;
  o ESLint do app não os cobre — não forçar lint neles.)

## Constraints (NÃO fazer)

- **NÃO** criar um segundo `export const viewport` em `layout.tsx` — **editar** o da Sessão 26
  (adicionar `themeColor`). Se o export não existir, **parar e reportar** (pré-requisito da Sessão 26).
- **NÃO** definir `metadata.manifest` apontando para arquivo estático, nem inserir `<link rel="manifest">`
  manual — o vínculo é **automático** ao existir `app/manifest.ts`.
- **NÃO** colocar `themeColor` em `metadata` (no Next 14 pertence a `viewport`).
- **NÃO** editar `next.config.js` (o `withSerwist`/SW é da **Sessão 29**) nem criar `app/sw.ts`/`public/sw.js`.
- **NÃO** commitar ícones PNG "à mão"/sem origem — **todos** os PNGs vêm do `generate-icons.mjs` a partir
  do `icon-source.svg` versionado (reprodutível).
- **NÃO** adicionar `sharp` em `dependencies` (é só build de ícones) — vai em `devDependencies`; e
  **NÃO** importar `sharp` em nenhum código de runtime do app.
- **NÃO** registrar script npm novo no `package.json` para a geração (YAGNI) — rodar via `node scripts/...`.
- **NÃO** rodar a suíte completa de testes (apenas `app/__tests__/manifest.test.ts`) — evitar falhas
  pré-existentes de xdist/Redis.
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`; **NÃO** usar `as`/`!` em código
  de produção (`manifest.ts`/`layout.tsx`) — tipar via `MetadataRoute.Manifest`/`Metadata`/`Viewport`,
  usar `import type`, `??` e guards (`noUncheckedIndexedAccess`). No teste, ler campos com `?.`/guards;
  **não** há necessidade de assertion (o retorno de `manifest()` já é tipado).
- **NÃO** introduzir barrels/re-exports; cada módulo importa da fonte.
- SOLID/DRY/KISS/YAGNI — `manifest()` é uma função pura sem ramos; o script faz só uma coisa (rasterizar).

## Critérios de Aceite

- [ ] `frontend/app/manifest.ts` existe, exporta `default function manifest(): MetadataRoute.Manifest`,
      com `display: 'standalone'`, `lang: 'pt-BR'`, `name`/`short_name`/`start_url` corretos e **≥ 2**
      ícones (incluindo um `512x512` `maskable` e um `192x192`).
- [ ] `theme_color === '#0d847a'` e `background_color === '#fbfbfc'`, com o comentário documentando a
      conversão OKLCH → HEX no topo de `manifest.ts`.
- [ ] `frontend/scripts/icon-source.svg` (512×512, glyph de prédio em `#0d847a`) versionado.
- [ ] `frontend/scripts/generate-icons.mjs` gera os **5** PNGs (192/512/512-maskable em `public/icons/`,
      `app/icon.png` 512, `app/apple-icon.png` 180), criando `public/icons/` se ausente.
- [ ] Os 5 PNGs existem após rodar `node scripts/generate-icons.mjs` (evidência colada na listagem).
- [ ] `app/layout.tsx`: o **mesmo** `export const viewport` da Sessão 26 ganhou `themeColor` (sem
      export duplicado); `metadata` ganhou `appleWebApp: { capable: true, statusBarStyle: 'default',
      title: 'Condomínios' }`; **sem** `metadata.manifest` manual.
- [ ] `sharp` em `frontend/package.json` `devDependencies` (não em `dependencies`); não importado em runtime.
- [ ] `next.config.js`, `app/sw.ts`, `public/sw.js` **inalterados/não criados** (Sessão 29).
- [ ] `npx vitest run "app/__tests__/manifest.test.ts"` 100% verde.
- [ ] `npx tsc --noEmit` sem erros nos arquivos tocados; `eslint` zero erros/avisos em
      `manifest.ts`/`layout.tsx`/`manifest.test.ts`.
- [ ] Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem `as`/`!` em produção; sem re-exports; sem
      dependência de runtime nova.

## Handoff

1. Rodar e confirmar verde (colar a saída como evidência):
   - `cd frontend && npx vitest run "app/__tests__/manifest.test.ts"`
   - `cd frontend ; node scripts/generate-icons.mjs` (+ listagem dos 5 PNGs gerados)
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "app/manifest.ts" "app/layout.tsx" "app/__tests__/manifest.test.ts"`
2. Atualizar `prompts/SESSION_STATE.md`: marcar Sessão 28 concluída; registrar:
   - HEX documentado (`theme_color #0d847a`, `background_color #fbfbfc`) e a origem OKLCH;
   - comando de regeneração de ícones (`node scripts/generate-icons.mjs`) para futuras trocas de logo;
   - que o `viewport` export (S26) agora inclui `themeColor` — a **Sessão 29** adiciona `withSerwist` ao
     `next.config.js` e cria `app/sw.ts` (deixando a seção marcada onde a **Sessão 33** anexa os
     handlers de `push`/`notificationclick`).
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): add PWA manifest, generated icons and Apple metadata

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A Sessão 29 começa lendo o `SESSION_STATE.md`.
