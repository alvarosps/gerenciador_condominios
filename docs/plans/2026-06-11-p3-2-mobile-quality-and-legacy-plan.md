# Plano P3.2 — Mobile: quality gates + Zod runtime + remoção das telas do financeiro legado

> **Estado:** PLANEJADO — não executado
> **Prioridade:** P3 (Mobile) · **Branch sugerida:** `chore/mobile-quality-gates` · **Depende de:** P3.1 (`fix/mobile-api-realignment` — auth por body + correção dos shapes de API divergentes)

## Objetivo

O app Expo (`mobile/`) viola as convenções obrigatórias do projeto: não tem ESLint, Prettier, testes nem validação Zod em runtime — os schemas em `mobile/lib/schemas/*.ts` só geram tipos (`z.infer`), nenhum `.parse()` roda, então ~10 divergências de contrato passaram silenciosamente. Este plano instala os quality gates (ESLint compartilhado com o web onde possível + Prettier + Vitest + scripts `lint`/`type-check`/`test`), faz os hooks validarem as respostas da API com `schema.parse()` (falha ruidosa em vez de tipo mentiroso), centraliza a formatação BR num único `mobile/lib/utils/formatters.ts` (Intl pt-BR, com separador de milhar correto) substituindo as 15+ cópias, remove o hook morto `useCalculateLateFee`, e **remove** as 4 telas do módulo Financeiro do mobile (que consomem o módulo financeiro pessoal DEPRECATED do core) em vez de corrigir shapes contra endpoints que serão desligados.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MEDIO | Zero quality gates: sem ESLint/Prettier/testes; Zod nunca executa `.parse()` (tipos mentem); hook morto `useCalculateLateFee` | `mobile/package.json:5-10`; `mobile/lib/api/hooks/use-admin-actions.ts:96-107` | Adicionar ESLint+Prettier+Vitest+scripts no gate; `schema.parse()` em todos os `queryFn`; deletar `useCalculateLateFee` |
| MEDIO | `formatCurrency` reimplementado em 15+ pontos com formato errado (`R$ 1500,00` sem milhar); datas ISO digitadas à mão sem máscara; DRY com o web | `mobile/app/(admin)/financial/{index,daily,purchases}.tsx:24/34/58` + 12 inline (grep `toFixed(2).replace`) | Criar `mobile/lib/utils/formatters.ts` (Intl pt-BR) e substituir todas as ocorrências |
| MEDIO | As 4 telas do Financeiro do mobile consomem o LEGADO deprecated → exibem NaN/vazio/zero | `mobile/lib/api/hooks/use-admin-financial.ts:5-121`; `mobile/app/(admin)/financial/*` | REMOVER as 4 telas + rotas + o hook inteiro + a tab "Financeiro" |

## Abordagem técnica

Ordem de execução desenhada para manter `tsc --noEmit` verde a cada passo (remoção do legado primeiro elimina os consumidores quebrados antes de tocar nos gates).

### 1. Remover as telas do financeiro legado (rotas, telas e hook)

As 4 telas e o hook apontam para o módulo financeiro pessoal DEPRECATED do core (`/financial-dashboard/*`, `/daily-control/*`), substituído pelo app `finances/`. Deletar por inteiro — sem corrigir shapes contra endpoints que serão desligados (P7.1 desliga o backend legado).

- Deletar os arquivos de tela e o layout do stack:
  - `mobile/app/(admin)/financial/index.tsx` (usa `useFinancialOverview`/`useUpcomingInstallments`/`useOverdueInstallments`)
  - `mobile/app/(admin)/financial/daily.tsx` (usa `useDailyBreakdown`/`useDailySummary`/`useMarkDailyPaid`)
  - `mobile/app/(admin)/financial/purchases.tsx` (usa `useMonthlyPurchases`)
  - `mobile/app/(admin)/financial/_layout.tsx` (`FinancialStackLayout` — registra `index`/`daily`/`purchases`)
  - Remover o diretório `mobile/app/(admin)/financial/` inteiro (passa a vazio).
- Deletar o hook inteiro `mobile/lib/api/hooks/use-admin-financial.ts` (todas as 8 funções: `useFinancialOverview`, `useUpcomingInstallments`, `useOverdueInstallments`, `useDailyBreakdown`, `useDailySummary`, `useMarkDailyPaid`, `useMonthlyPurchases`, e as interfaces locais). Grep confirma que NENHUM consumidor fora das 3 telas deletadas importa essas funções.
- Remover a aba "Financeiro" do tab navigator em `mobile/app/(admin)/_layout.tsx`: apagar o bloco `<Tabs.Screen name="financial" .../>` (linhas 34-43; ícone `money`). As demais abas (`index`, `properties`, `actions`, `notifications`) permanecem.
- Limpar os schemas do financeiro legado em `mobile/lib/schemas/admin.ts` que ficam órfãos após a remoção: `FinancialOverviewSchema`/`FinancialOverview`, `DailySummaryDataSchema`/`DailySummaryData`, `MonthlyPurchaseGroupSchema`/`MonthlyPurchaseGroup` (e seus `export type`). Verificar com grep antes de remover cada um que não há outro consumidor; manter `FinancialSummarySchema`/`LeaseMetricsSchema`/`LatePaymentItemSchema`/`RentAdjustmentAlertSchema` (esses são do dashboard admin não-legado, corrigidos em P3.1 e usados por `use-admin-dashboard.ts`).

### 2. Criar `mobile/lib/utils/formatters.ts` (DRY com o web, formato BR correto)

Espelhar `frontend/lib/utils/formatters.ts` (fonte canônica), porém só com o que o mobile usa hoje. `Intl.NumberFormat`/`Intl.DateTimeFormat` com locale `pt-BR` são suportados no Hermes (engine padrão do RN/Expo 54).

- `formatCurrency(value: number | string | null | undefined): string` — idêntico ao web: trata `null`/`undefined`/`NaN` → `"R$ 0,00"`, arredonda `Math.round(n*100)/100`, `new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })`. Isso corrige o formato sem milhar (`R$ 1500,00` → `R$ 1.500,00`).
- `formatPercentage(value: number): string` — `${value > 0 ? "+" : ""}${Intl.NumberFormat("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2}).format(value)}%` (cobre `adjustments.tsx:9`, que hoje monta o label de percentual à mão).
- `formatDateBR(value: string | Date | null | undefined): string` — copiar `parseDateString` + `formatDate` do web (trata `YYYY-MM-DD` como data LOCAL, evitando o off-by-one de UTC−3 que o `new Date(item.due_date + "T12:00:00")` inline tenta contornar manualmente em várias telas).
- Substituir TODAS as ocorrências de `parseFloat(x).toFixed(2).replace(".", ",")` (15+ pontos, ver lista em "Arquivos a criar / modificar") por `formatCurrency(...)`; substituir as conversões de data inline (`new Date(x + "T12:00:00").toLocaleDateString("pt-BR")`) por `formatDateBR(x)`; substituir o cálculo de percentual em `adjustments.tsx` por `formatPercentage`.
- Atenção a um caso de tipo: hoje `formatCurrency` local recebe `string`. A versão única aceita `number | string`, então pontos que hoje fazem `formatCurrency(grandTotal.toFixed(2))` (purchases — DELETADO) ou passam números devem passar o número direto. Não há regressão de tipo porque a assinatura é mais ampla.

> NOTA (datas digitadas à mão sem máscara): os `TextInput` de data ISO em `mark-paid.tsx`, `new-lease.tsx`, `rent-adjustment.tsx`, `pix.tsx` são UX hostil mas a substituição por date-picker nativo é escopo de UI maior. Este plano cobre a parte de DISPLAY (formatação de saída) e deixa um `parseDateBRtoISO` disponível em `formatters.ts` para o input. A troca dos inputs por máscara/date-picker fica fora deste plano (não introduzir dependência de UI nova aqui); registrar no Handoff.

### 3. Hooks validam a resposta com `schema.parse()` (Zod em runtime)

Cada `queryFn` passa a validar o que a API devolve com o schema Zod correspondente (que já existe), tornando qualquer drift de contrato uma falha ruidosa em vez de tipo mentiroso. Os schemas já corrigidos em P3.1 são a base. Para listas paginadas, usar `PaginatedResponseSchema(ItemSchema)` (já existe em `tenant.ts`; criar equivalente em `admin.ts` ou mover para um `schemas/shared.ts`).

- `use-admin-dashboard.ts`: `useFinancialSummary` → `FinancialSummarySchema.parse(response.data)`; `useLatePayments` → schema do summary (corrigido em P3.1 para `total_late_leases`/`total_late_fees`/`late_leases`); `useLeaseMetrics` → `LeaseMetricsSchema.parse`; `useRentAdjustmentAlerts` → schema do objeto `{ alerts: [...] }` (corrigido em P3.1).
- `use-admin-properties.ts`: `useBuildings`/`useApartments`/`useLeases`/`useTenantSearch` → `PaginatedResponseSchema(Schema).parse(response.data)` e retornar `.results`; `useCreateLease`/`useGenerateContract` → `parse` na resposta (shapes já corrigidos em P3.1: `apartment_id`/`tenant_ids`, `{pdf_path,message}`/`{task_id,status}`).
- `use-tenant.ts`: `useTenantMe` → `TenantMeSchema.parse`; `useTenantPayments` → `PaginatedResponseSchema(RentPaymentSchema).parse`; `useTenantAdjustments` → `z.array(RentAdjustmentSchema).parse`.
- `use-tenant-pix.ts` / `use-tenant-proof.ts` / `use-tenant-simulate.ts` / `use-tenant-notifications.ts` / `use-admin-notifications.ts` / `use-admin-actions.ts`: aplicar `parse` nos `queryFn` e nas respostas de mutation que o app lê (ex.: `PixPayloadSchema.parse`, `SimulateDueDateSchema.parse`). Onde a resposta hoje é tipada por interface local sem schema (ex.: `ToggleRentPaymentResult`, `ReviewProofInput` result, `LateFeeResult`), criar o schema Zod no arquivo de schemas adequado e parsear; manter o tipo derivado por `z.infer`.
- Padrão: `const data = Schema.parse(response.data); return data;` — remover os generics `apiClient.get<T>` redundantes (o tipo agora vem do `parse`). NÃO usar `safeParse` silencioso: queremos que o erro suba para o React Query `onError` e apareça (objetivo do achado).
- DRY de paginação: extrair `PaginatedResponseSchema` para `mobile/lib/schemas/shared.ts` e importar em `tenant.ts`/`admin.ts` (hoje só existe em `tenant.ts`).

### 4. Remover o hook morto `useCalculateLateFee`

- Deletar `useCalculateLateFee` (`use-admin-actions.ts:96-107`) e a interface `LateFeeResult` (linhas 36-40) se não for usada por mais nada. Grep confirma: definido mas nunca importado por nenhuma tela.

### 5. Quality gates: ESLint + Prettier + Vitest + scripts

- **devDependencies** em `mobile/package.json` (versões alinhadas às do `frontend/` quando existirem lá; senão, latest estável compatível com Expo 54 / RN 0.81 / TS 5.9):
  - `eslint`, `eslint-config-expo` (config oficial Expo, base correta para RN), `@typescript-eslint/parser`, `@typescript-eslint/eslint-plugin`, `eslint-config-prettier` (desliga regras conflitantes com Prettier — mesmo pacote usado no `extends: ["...","prettier"]` do web), `prettier`.
  - `vitest`, `@vitest/coverage-v8` (testar a lógica pura de `formatters.ts`; não testar componentes RN aqui — fora de escopo, evita `@testing-library/react-native` + jsdom de RN).
- **ESLint config compartilhada com o web onde possível** (`mobile/.eslintrc.json` ou `eslint.config.js`): estender `eslint-config-expo` + `plugin:@typescript-eslint/strict-type-checked` + `plugin:@typescript-eslint/stylistic-type-checked` + `prettier` (mesmas três últimas extends do `frontend/.eslintrc.json`), `parserOptions.project: true`, e as mesmas regras-chave do web que fazem sentido em RN: `@typescript-eslint/no-explicit-any: error`, `@typescript-eslint/consistent-type-imports` (inline-type-imports), `@typescript-eslint/no-floating-promises: error`, `@typescript-eslint/no-misused-promises`, `eqeqeq`, `prefer-const`, `no-var`. NÃO incluir `next/core-web-vitals` (é do Next). `no-console: ["warn",{allow:["error","warn"]}]` igual ao web.
- **Prettier**: copiar `frontend/.prettierrc` verbatim para `mobile/.prettierrc` (semi, trailingComma es5, singleQuote, printWidth 100, tabWidth 2). Rodar `prettier --write .` uma vez (commit de formatação separado para diff limpo) — observe que o código mobile atual usa aspas duplas; o Prettier `singleQuote: true` vai reformatar.
- **tsconfig**: já é strict + `noUncheckedIndexedAccess` (`mobile/tsconfig.json`) — não alterar; o gate `tsc --noEmit` já funciona.
- **scripts** em `mobile/package.json`:
  ```json
  "lint": "eslint .",
  "lint:fix": "eslint . --fix",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "type-check": "tsc --noEmit",
  "test:unit": "vitest run"
  ```
- **CRITICAL** (zero supressões): após instalar o ESLint strict-type-checked, vão aparecer erros reais no código existente (ex.: `no-floating-promises` nos `void qc.invalidate...` — já estão com `void`, ok; `no-misused-promises`; `consistent-type-imports`). Corrigir o CÓDIGO, nunca usar `eslint-disable`/`@ts-ignore`. Se algum erro for inerente a padrão RN legítimo, restringir via `overrides` por arquivo com justificativa — não por comentário inline.

## Arquivos a criar / modificar

**Criar:**
- `mobile/lib/utils/formatters.ts` — `formatCurrency`, `formatPercentage`, `formatDateBR`, `parseDateBRtoISO` (Intl pt-BR; espelha o web).
- `mobile/lib/utils/__tests__/formatters.test.ts` — testes Vitest (ver cenários abaixo).
- `mobile/lib/schemas/shared.ts` — `PaginatedResponseSchema` (movido de `tenant.ts`) + schemas de respostas que hoje são interfaces locais (ToggleRentPayment, ReviewProof, etc.).
- `mobile/.eslintrc.json` (ou `eslint.config.js`) — config compartilhada com o web.
- `mobile/.prettierrc` — cópia de `frontend/.prettierrc`.
- (opcional) `mobile/vitest.config.ts` — se necessário para resolver o alias `@/` nos testes (espelhar `frontend/vitest.config.mts`).

**Modificar:**
- `mobile/package.json` — devDependencies (eslint/prettier/vitest + plugins) e scripts (`lint`/`type-check`/`test:unit`/`format`).
- `mobile/app/(admin)/_layout.tsx` — remover `<Tabs.Screen name="financial" .../>`.
- `mobile/lib/schemas/admin.ts` — remover schemas/tipos do financeiro legado órfãos; importar `PaginatedResponseSchema` de `shared.ts`.
- `mobile/lib/schemas/tenant.ts` — mover `PaginatedResponseSchema` para `shared.ts` e reimportar.
- `mobile/lib/api/hooks/use-admin-dashboard.ts` — `.parse()` em todos os `queryFn`.
- `mobile/lib/api/hooks/use-admin-properties.ts` — `.parse()` (listas via `PaginatedResponseSchema`).
- `mobile/lib/api/hooks/use-admin-actions.ts` — `.parse()` + DELETAR `useCalculateLateFee` e `LateFeeResult`.
- `mobile/lib/api/hooks/use-tenant.ts`, `use-tenant-pix.ts`, `use-tenant-proof.ts`, `use-tenant-simulate.ts`, `use-tenant-notifications.ts`, `use-admin-notifications.ts` — `.parse()` nas respostas.
- Telas que formatam dinheiro/data (substituir cópias por `formatters.ts`):
  - `mobile/app/(tenant)/index.tsx:36,64`
  - `mobile/app/(tenant)/contract.tsx:98,104`
  - `mobile/app/(tenant)/payments/index.tsx:16`
  - `mobile/app/(tenant)/payments/adjustments.tsx:9,10,11` (usa `formatPercentage`+`formatCurrency`)
  - `mobile/app/(tenant)/payments/pix.tsx:93`
  - `mobile/app/(tenant)/payments/simulate.tsx:77,83`
  - `mobile/app/(admin)/index.tsx:67`
  - `mobile/app/(admin)/actions/mark-paid.tsx:89`
  - `mobile/app/(admin)/properties/[id].tsx:33`

**Deletar:**
- `mobile/app/(admin)/financial/index.tsx`
- `mobile/app/(admin)/financial/daily.tsx`
- `mobile/app/(admin)/financial/purchases.tsx`
- `mobile/app/(admin)/financial/_layout.tsx`
- `mobile/lib/api/hooks/use-admin-financial.ts`

## TDD — cenários de teste

Vitest cobre a lógica pura de `formatters.ts` (única lógica testável sem render RN; componentes/telas ficam fora de escopo, sem `@testing-library/react-native`). Os "testes de contrato dos hooks contra fixtures dos serializers reais" são implementados como testes Vitest que rodam o `schema.parse()` contra fixtures JSON capturadas das respostas reais da API (serializadores DRF), provando que o schema bate com o backend — não dependem de rede (a fronteira HTTP não é exercida; só o schema).

**`formatters.test.ts` — `formatCurrency`:**
- `formata número como BRL com separador de milhar` → `formatCurrency(1500)` contém `"1.500"` e `"R$"` (regressão do bug `R$ 1500,00`).
- `formata string numérica` → `formatCurrency("1500.50")` contém `"1.500"` e `"50"`.
- `formata zero` → contém `"0,00"`.
- `null/undefined → "R$ 0,00"`.
- `string não-numérica → "R$ 0,00"`.
- `arredonda precisão de ponto flutuante` → `formatCurrency(699.995)` contém `"700"`.
- `formata negativo` → `formatCurrency(-100)` contém `"100"`.

**`formatters.test.ts` — `formatPercentage`:**
- `positivo recebe sinal +` → `formatPercentage(5)` começa com `"+5"` e termina com `"%"`.
- `negativo mantém sinal -` → `formatPercentage(-3.5)` contém `"-3,50%"`.
- `zero sem +`.

**`formatters.test.ts` — `formatDateBR`:**
- `ISO date-only é local, sem off-by-one UTC−3` → `formatDateBR("2026-06-17")` === `"17/06/2026"` (regressão do shift de timezone).
- `string vazia/null/undefined → ""`.
- `data inválida → ""`.

**`use-admin-properties.contract.test.ts` (e demais hooks) — schema vs fixture do serializer real:**
- `LeaseSimpleSchema aceita o shape real do LeaseSerializer (apartment aninhado pós-P3.1)` → fixture capturada do DRF passa em `.parse()` sem throw (teste de regressão que prova o bug do achado: hoje `apartment: z.number()` rejeitaria o objeto aninhado real).
- `PaginatedResponseSchema(BuildingSchema) aceita /buildings/ real`.
- `TenantMeSchema aceita /tenant/me/ real (lease/apartment opcionais presentes)`.
- `PixPayloadSchema aceita o shape real (campos pix_copy_paste/qr_data pós-P3.1)` — prova que o campo `payload` inexistente não está mais no schema.
- `RentAdjustmentAlert schema aceita { alerts: [...] }` (shape corrigido em P3.1).
- Edge: `.parse()` LANÇA quando uma fixture com campo faltando/extra-incompatível é passada — prova que o gate é ruidoso (não silencioso).

> As fixtures vivem em `mobile/lib/schemas/__tests__/fixtures/*.json`, copiadas de respostas reais (ou de `tests/` do backend). Se um schema não passar na fixture real, isso indica que P3.1 não cobriu o shape — registrar e corrigir no schema (não relaxar para `z.unknown()`).

## Migrations / dados

N/A — mudança 100% frontend (mobile). Sem alteração de banco, sem migration, sem RLS.

## Constraints (o que NÃO fazer)

- NÃO corrigir os shapes das 4 telas financeiras — elas são REMOVIDAS (apontam para o módulo legado deprecated que P7.1 vai desligar). Não criar telas substitutas do `finances/` aqui (escopo futuro).
- NÃO tocar no backend (`/financial-dashboard/*`, `/daily-control/*` continuam existindo até P7.1; este plano só remove o consumo no mobile).
- NÃO refatorar auth nem corrigir os outros shapes de contrato divergentes — isso é P3.1 (dependência). Este plano ASSUME que P3.1 já alinhou os schemas (`LeaseSimpleSchema.apartment` objeto, PIX `pix_copy_paste`, late-payment keys, rent-adjustment `{alerts}`).
- NÃO usar `eslint-disable`, `@ts-ignore`, `# noqa`, `safeParse` silencioso para "passar" o gate — corrigir o código de verdade (regra CRITICAL do projeto).
- NÃO introduzir date-picker/máscara de input nesta entrega (só formatação de display + helper de parse) — registrar como follow-up.
- NÃO adicionar `@testing-library/react-native`/render de componentes — testar só lógica pura (`formatters`) e contratos de schema.
- NÃO reescrever a formatação para `parseFloat(...).toFixed(2).replace` em lugar nenhum — a fonte única é `formatters.ts`.
- Manter a paridade com `frontend/lib/utils/formatters.ts` (não divergir a lógica de `formatCurrency`/`formatDate`); idealmente avaliar pacote compartilhado depois (fora de escopo).

## Critérios de aceite (binários)

- [ ] `mobile/app/(admin)/financial/` não existe mais (4 arquivos deletados) e a aba "Financeiro" não aparece no tab navigator admin.
- [ ] `mobile/lib/api/hooks/use-admin-financial.ts` deletado; nenhum import remanescente (grep retorna 0).
- [ ] `useCalculateLateFee` deletado; nenhum import remanescente (grep retorna 0).
- [ ] `mobile/lib/utils/formatters.ts` existe e é a ÚNICA implementação de formatação BR; `grep -r "toFixed(2).replace" mobile/` retorna 0 ocorrências.
- [ ] Todas as 3 `function formatCurrency` locais removidas das telas.
- [ ] Todos os `queryFn` dos hooks restantes chamam `Schema.parse(response.data)`; nenhum retorna `response.data` cru.
- [ ] `mobile/package.json` tem scripts `lint`, `type-check`, `test:unit`, `format`, `format:check` e devDependencies de eslint/prettier/vitest.
- [ ] `mobile/.eslintrc.json` (ou `eslint.config.js`) e `mobile/.prettierrc` existem; Prettier alinhado ao web.
- [ ] `cd mobile && npm run lint` → 0 erros / 0 warnings.
- [ ] `cd mobile && npm run type-check` → 0 erros.
- [ ] `cd mobile && npm run test:unit` → todos verdes, incluindo o teste de regressão `formatCurrency(1500)` contém `"1.500"` e o teste de contrato que prova que `LeaseSimpleSchema.parse` aceita o `apartment` aninhado real.
- [ ] Zero supressões (`eslint-disable`/`@ts-ignore`/`safeParse` silencioso) introduzidas.

## Gate de verificação

Frontend/mobile (escopado ao app que mudou):
```bash
cd mobile && npm install
cd mobile && npm run lint
cd mobile && npm run type-check
cd mobile && npm run test:unit
cd mobile && npm run format:check
```
Regressão dirigida (provas dos achados):
```bash
# 0 ocorrências do formato errado e do hook morto:
rg "toFixed\(2\)\.replace" mobile/
rg "useCalculateLateFee|use-admin-financial" mobile/
# financial screens removidas:
ls mobile/app/(admin)/financial 2>/dev/null   # deve falhar (dir inexistente)
```
Zero erros E zero warnings em ESLint, TypeScript e Vitest. (Backend não é tocado — sem gate de backend.)

## Handoff

- **Commit message sugerida:**
  ```
  chore(mobile): add ESLint/Prettier/Vitest gates, runtime Zod validation, single formatters; remove legacy financial screens

  - add eslint-config-expo + @typescript-eslint strict-type-checked (shared with web) + prettier + vitest; scripts lint/type-check/test:unit
  - validate all hook responses with schema.parse() (no more lying types)
  - new mobile/lib/utils/formatters.ts (Intl pt-BR, milhar correto) replacing 15+ copies; delete 3 local formatCurrency
  - delete dead useCalculateLateFee
  - remove the 4 legacy financial screens + use-admin-financial.ts + "Financeiro" tab (consume deprecated core financial module; replaced by finances/)

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```
- **Docs/estado:** marcar P3.2 como concluído em `docs/plans/2026-06-11-audit-remediation-roadmap.md` (linha 35) e no checklist "Mobile: ... quality gates ativos" (linha 87). Atualizar a entrada de memória de mobile, se aplicável.
- **O próximo plano (P7.1 — remoção do módulo financeiro pessoal legado BE+FE+mobile) assume:** o mobile JÁ não consome mais nenhum endpoint `/financial-dashboard/*` ou `/daily-control/*` (este plano removeu o consumo), então P7.1 pode desligar o backend legado sem quebrar o app. P7.1 também depende de o app `finances/` cobrir todos os casos do legado.
- **Follow-up registrado (fora de escopo deste plano):** substituir os `TextInput` de data ISO digitada à mão por date-picker nativo / máscara DD/MM/YYYY em `mark-paid.tsx`, `new-lease.tsx`, `rent-adjustment.tsx`, `pix.tsx` (usar `parseDateBRtoISO` de `formatters.ts`); avaliar pacote compartilhado de formatters+tipos entre `frontend/` e `mobile/`.
