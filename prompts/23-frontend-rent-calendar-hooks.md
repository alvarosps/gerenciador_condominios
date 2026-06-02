# Sessão 23 — Frontend: Data Layer do Calendário de Aluguéis (hooks + tipos + MSW)

> Feature: **Calendário de Controle de Aluguéis** · Sessão **23 de 21–25**
> Esta sessão cria APENAS a camada de dados do frontend (hooks TanStack Query v5, tipos TS, query-keys, mocks MSW). **Nenhuma UI.** A UI vem na sessão 24; o refactor do `late-payments-alert` vem na 25.

---

## Contexto

Leia, nesta ordem, antes de escrever qualquer código:

1. **Design doc** (leia inteiro): `@docs/plans/2026-06-02-rent-payment-calendar-design.md`
   - Seção 4.3 (formato da resposta `rent_calendar` — o JSON canônico, linhas 140-150)
   - Seção 4.4 (regras do toggle / `can_toggle`)
   - Seção 6 (`use-rent-calendar.ts`: `useRentCalendar` + `useToggleRentPayment` optimistic)
   - Seção 9 (tabela de exemplares)
2. **Estado das sessões**: `@prompts/SESSION_STATE.md` (sessões 21 e 22 devem estar concluídas — backend `RentScheduleService` + endpoints `rent_calendar`/`toggle_rent_payment` já existentes)
3. **Padrão de prompts**: `@prompts/00-prompt-standard.md`
4. **Regras do projeto** (precedência sobre qualquer convenção genérica):
   - `@frontend/CLAUDE.md`, `@.claude/rules/coding-standards.md`, `@tests/CLAUDE.md`, `@.claude/rules/design-principles.md`, `@.claude/rules/architecture.md`

### Exemplares (arquivo:linha — exemplar > descrição)

| Padrão | Local exato |
|--------|-------------|
| Hooks de dashboard: `useQuery` + tipos TS hand-written + `apiClient`/`queryKeys`, e `useMarkRentPaid` (mutation atual, **não tocar nesta sessão**) | `frontend/lib/api/hooks/use-dashboard.ts:1-189` (mutation `useMarkRentPaid` em `:146-160`) |
| `useQuery` com query params `year`/`month` via `apiClient.get(url, { params })` | `frontend/lib/api/hooks/use-daily-control.ts:68-92` |
| Mutation simples com `invalidateQueries` no `onSuccess` (referência de invalidação) | `frontend/lib/api/hooks/use-expenses.ts:108-122` (`useMarkExpensePaid`) |
| Grupo de query-keys (estrutura `all` + funções com params) | `frontend/lib/api/query-keys.ts:91-130` (`dailyControl`, `dashboard`) |
| `apiClient` (axios instance + unwrap de paginação DRF) | `frontend/lib/api/client.ts:1-86` |
| Mock builder + array exportado (factory pattern) | `frontend/tests/mocks/data/person-payments.ts:1-41` |
| MSW handler com `new URL(request.url)` + `searchParams.get(...)` | `frontend/tests/mocks/handlers.ts:1213-1247` (`contractRuleHandlers`) e `:658-671` (`expenses/:id/mark_paid`) |
| Handler POST com `await delay(100)` + `await request.json()` (referência de delay para abrir janela) | `frontend/tests/mocks/handlers.ts:1473-1481` (`daily-control/mark_paid`) |
| Combinação final de handlers (array `handlers`) | `frontend/tests/mocks/handlers.ts:2053-2081` |
| Teste de hook: `renderHook` + `createWrapper`, fetch/shape, `server.use()` para edge cases, erro 500, imports (`waitFor`, `http`, `HttpResponse`, `server`) | `frontend/lib/api/hooks/__tests__/use-daily-control.test.tsx:1-132` |
| Teste de mutation: `vi.spyOn(queryClient, 'invalidateQueries')` + `createTestQueryClient`/`createWrapper(queryClient)` | `frontend/lib/api/hooks/__tests__/use-daily-control.test.tsx:88-106` (asserts de keys em `:102-105`) |
| Utilitários de teste (`createTestQueryClient`, `createWrapper`, `renderWithProviders`) | `frontend/tests/test-utils.tsx:1-79` |
| Import de `delay` do MSW (já disponível) | `frontend/tests/mocks/handlers.ts:9` (`import { delay, http, HttpResponse } from 'msw'`) |

> **TanStack Query v5 optimistic update**: não existe exemplar de optimistic no codebase — siga o padrão oficial v5 (`onMutate` → `cancelQueries` + `getQueriesData` (snapshot) + `setQueryData` (flip) + retorna context; `onError` → `setQueryData` (rollback do snapshot); `onSettled` → `invalidateQueries`). Se precisar confirmar a API v5, use o MCP Context7 (`resolve-library-id` → `query-docs` para `@tanstack/react-query`). **Não** mocke internals do TanStack — use `QueryClient` real (já é o que `createTestQueryClient` faz).

---

## Escopo

### Arquivos a criar
- `frontend/lib/api/hooks/use-rent-calendar.ts` — `useRentCalendar(year, month, buildingId?)` + `useToggleRentPayment()` (optimistic) + tipos TS hand-written
- `frontend/lib/api/hooks/__tests__/use-rent-calendar.test.tsx` — testes Vitest+MSW
- `frontend/tests/mocks/data/rent-calendar.ts` — builder de mock (`createMockRentCalendar(...)` + helper de item de dia)

### Arquivos a modificar
- `frontend/lib/api/query-keys.ts` — adicionar grupo `rentCalendar`
- `frontend/tests/mocks/handlers.ts` — adicionar handlers `GET /dashboard/rent_calendar/` e `POST /dashboard/toggle_rent_payment/`, e incluí-los no array `handlers`

---

## Especificação

### 1. `query-keys.ts` — novo grupo `rentCalendar`

Seguindo o estilo de `dailyControl` (`query-keys.ts:91-97`), adicione **dentro** do objeto `queryKeys`:

```ts
rentCalendar: {
  all: ['rent-calendar'] as const,
  month: (year: number, month: number, buildingId?: number) =>
    [...queryKeys.rentCalendar.all, 'month', year, month, buildingId ?? null] as const,
},
```

- `buildingId` opcional vira parte da key (use `?? null` para estabilizar a key quando ausente — `noUncheckedIndexedAccess`/strict não permite `undefined` implícito espalhado de forma ambígua; manter determinístico).

### 2. `use-rent-calendar.ts` — tipos + hooks

Imports no topo (mesma ordem de `use-dashboard.ts:1-3`):
```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
```

**Tipos hand-written** (espelham o JSON da seção 4.3 do design — valores monetários são `string` como nos demais endpoints do dashboard; datas são `string` ISO `YYYY-MM-DD`):

```ts
interface RentCalendarItem {
  lease_id: number;
  tenant_name: string;
  apartment_number: number;
  building_number: string;
  rental_value: string;
  is_paid: boolean;
  payment_date: string | null;
  is_overdue: boolean;
  day_passed: boolean;
  can_toggle: boolean;
  late_fee: string;
  late_days: number;
}

interface RentCalendarDay {
  day: number;
  date: string;        // YYYY-MM-DD
  weekday: string;     // ex.: "Sexta"
  items: RentCalendarItem[];
}

interface RentCalendarStats {
  received_total: string;
  to_receive_total: string;
  expected_total: string;
  paid_count: number;
  due_count: number;
  overdue_count: number;
  overdue_total_fee: string;
  vacant_kitnets_count: number;
  vacant_kitnets_value: string;
}

interface RentCalendar {
  year: number;
  month: number;
  today: string;               // YYYY-MM-DD
  next_due_date: string | null;
  days: RentCalendarDay[];
  stats: RentCalendarStats;
}

interface ToggleRentPaymentRequest {
  lease_id: number;
  reference_month: string;     // YYYY-MM-01
}

interface ToggleRentPaymentResponse {
  status: string;
  is_paid: boolean;
  message: string;
}
```

> O rótulo do mês ("Junho 2026") é derivado no frontend (sessão 24) — o backend **não** retorna `month_label`. **Não** adicione esse campo aos tipos.

**`useRentCalendar(year, month, buildingId?)`** (siga `use-daily-control.ts:68-79`):
- `useQuery` com `queryKey: queryKeys.rentCalendar.month(year, month, buildingId)`
- `queryFn`: `apiClient.get<RentCalendar>('/dashboard/rent_calendar/', { params: { year, month, ...(buildingId !== undefined ? { building_id: buildingId } : {}) } })` e retorna `data`
- `staleTime` **curto** (ex.: `1000 * 30` — 30s). Justificativa: toggles exigem reflexo quase imediato; o design (seção 4.3) define endpoint não cacheado no backend, cliente compensa com staleTime curto + optimistic + invalidação.

**`useToggleRentPayment()`** — `useMutation` com **optimistic update** (v5):
- `mutationFn: (req: ToggleRentPaymentRequest) =>` `apiClient.post<ToggleRentPaymentResponse>('/dashboard/toggle_rent_payment/', req)` → retorna `data`.
- A mutation **não** sabe `year`/`month`/`buildingId`; o flip otimista deve agir sobre **todas** as queries do calendário em cache. Use `queryClient.getQueriesData<RentCalendar>({ queryKey: queryKeys.rentCalendar.all })` para snapshot e iterar no flip/rollback.
- `onMutate(req)`:
  1. `await queryClient.cancelQueries({ queryKey: queryKeys.rentCalendar.all })`
  2. snapshot: `const previous = queryClient.getQueriesData<RentCalendar>({ queryKey: queryKeys.rentCalendar.all })`
  3. para cada `[key, data]` do snapshot (pule `data` undefined com guard de null — strict): `queryClient.setQueryData<RentCalendar>(key, flipItem(data, req.lease_id))` onde `flipItem` retorna um novo `RentCalendar` com o item de `lease_id` correspondente tendo `is_paid` invertido (imutável — `map` em `days` e `items`, sem mutação in-place).
  4. `return { previous }` (context tipado).
- `onError(_err, _req, context)`: se `context?.previous`, restaure cada par com `queryClient.setQueryData(key, data)`.
- `onSettled()`: invalide as três áreas:
  ```ts
  void queryClient.invalidateQueries({ queryKey: queryKeys.rentCalendar.all });
  void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.latePaymentSummary() });
  void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.financialSummary() });
  ```

Exporte os tipos no final do arquivo via `export type { ... }` (mesmo estilo de `use-dashboard.ts:180-189`). **Não** crie re-export/barrel.

> **Não** toque em `useMarkRentPaid` (`use-dashboard.ts:146-160`). Ele continua existindo e em uso pelo `late-payments-alert.tsx` até a sessão 25. Esta sessão **adiciona** `useToggleRentPayment` em paralelo; nada do legado é removido aqui.

### 3. `tests/mocks/data/rent-calendar.ts` — builder

Siga `person-payments.ts:28-41`. Exporte:
- `createMockRentCalendarItem(overrides?: Partial<RentCalendarItem>): RentCalendarItem` — defaults coerentes (item a vencer: `is_paid:false, is_overdue:false, day_passed:false, can_toggle:true, late_fee:'0.00', late_days:0, payment_date:null`).
- `createMockRentCalendar(overrides?: Partial<RentCalendar>): RentCalendar` — estrutura completa com pelo menos 1 `RentCalendarDay` contendo 1 item, `stats` preenchido com os 9 campos, `today`/`next_due_date` plausíveis.

Importe os tipos a partir de `@/lib/api/hooks/use-rent-calendar` (fonte única — nunca redeclare os tipos no arquivo de mock). Para isso, os tipos `RentCalendarItem`/`RentCalendar` precisam estar no `export type { ... }` do hook.

> **Não** adicione este arquivo ao barrel `frontend/tests/mocks/data/index.ts`. A regra do projeto proíbe novos re-exports; os handlers e o teste importam **direto** de `./data/rent-calendar` / `@/tests/mocks/data/rent-calendar`.

### 4. `handlers.ts` — handlers MSW

Crie `const rentCalendarHandlers = [...]` (estilo dos demais grupos, ex.: `dailyControlHandlers` `handlers.ts:1424-1482`), importando `createMockRentCalendar` de `./data/rent-calendar`. O `delay` já está importado no topo do arquivo (`handlers.ts:9`).

- `http.get(`${API_BASE}/dashboard/rent_calendar/`, ...)`:
  - leia `year`/`month`/`building_id` via `new URL(request.url).searchParams` (padrão `handlers.ts:1214-1215`),
  - retorne `HttpResponse.json(createMockRentCalendar({ year, month }))` (coerente com os params; default razoável quando ausentes).
- `http.post(`${API_BASE}/dashboard/toggle_rent_payment/`, ...)`:
  - **adicione `await delay(100)` no início** (espelha `daily-control/mark_paid` em `handlers.ts:1474`) — abre a janela para o flip otimista ser observável e mantém o teste determinístico,
  - leia o body `{ lease_id, reference_month }` via `await request.json()`,
  - retorne `HttpResponse.json<ToggleRentPaymentResponse>({ status: 'paid', is_paid: true, message: 'Aluguel marcado como pago' })` (mensagem em PT, conforme regra de mensagens ao usuário).

Adicione `...rentCalendarHandlers` ao array `handlers` (`handlers.ts:2053-2081`).

---

## TDD

> Memória do projeto: rode os testes **apenas dos arquivos editados** (a suíte completa tem problemas pré-existentes de xdist/Redis no Windows). Aqui isso é o arquivo de teste novo.
> Todos os comandos rodam a partir de `frontend/` (use caminho absoluto: `C:\Users\alvar\git\personal\gerenciador_condominios\frontend`).

### Como tornar o teste de optimistic flip determinístico (LEIA antes de escrever o teste)

O flip otimista acontece de forma síncrona dentro de `onMutate`, mas a asserção precisa de uma janela observável e não-flaky. Técnica obrigatória (combine as duas):

1. **Abra a janela com delay**: o handler `POST /dashboard/toggle_rent_payment/` já faz `await delay(100)` (item 4 acima). Para garantir uma janela ainda mais ampla e independente do default, **sobrescreva o handler dentro do teste de flip** com um delay maior:
   ```ts
   server.use(
     http.post(`${API_BASE}/dashboard/toggle_rent_payment/`, async () => {
       await delay(200);
       return HttpResponse.json({ status: 'paid', is_paid: true, message: 'Aluguel marcado como pago' });
     }),
   );
   ```
   (importe `delay` de `'msw'` no teste, junto de `http`/`HttpResponse`.)
2. **Aguarde o flip com `waitFor` (NÃO com sleep fixo)**: após `result.current.mutate(...)`, envolva a leitura do snapshot otimista em `waitFor`, lendo o estado **direto do `queryClient` real** (não do retorno do hook). Isso espera o `setQueryData` aplicar sem depender de timing fixo:
   ```ts
   await waitFor(() => {
     const snapshot = queryClient.getQueryData<RentCalendar>(queryKeys.rentCalendar.month(2026, 6));
     expect(snapshot?.days[0]?.items[0]?.is_paid).toBe(true);
   });
   ```
   Esse `waitFor` resolve **antes** de o request settlar (graças ao `delay(200)`), provando o flip otimista. Em seguida, opcionalmente, aguarde `result.current.isSuccess` para confirmar que o request settlou sem reverter.

> Por que não asserir "antes do request resolver" com `expect` direto: sem `waitFor` a asserção corre antes de `onMutate` aplicar (race). `waitFor` re-tenta até o snapshot refletir o flip; o `delay` garante que a janela continua aberta enquanto isso. As duas técnicas juntas eliminam o flakiness. Leia os tipos do `queryClient.getQueryData` como `RentCalendar | undefined` e use guards de null (`?.`) — **sem** `as`/`!`.

### Red — escreva os testes primeiro
1. Crie `frontend/lib/api/hooks/__tests__/use-rent-calendar.test.tsx` cobrindo (modele imports/estrutura por `use-daily-control.test.tsx:1-132`; importe `delay` de `'msw'` além de `http`/`HttpResponse`):
   - **1.1 fetch / shape** (`useRentCalendar(2026, 6)`): `isLoading` inicial → `isSuccess`; `data` tem `year/month/today/days/stats`; `stats` tem os 9 campos; `days[0].items[0]` tem `lease_id`, `is_paid`, `can_toggle`, `late_fee`. (Use guards `?.[0]?.` como em `use-daily-control.test.tsx:22-25`.)
   - **1.2 building_id é repassado**: `useRentCalendar(2026, 6, 1)` resolve com sucesso; override `server.use(http.get(.../rent_calendar/, ({ request }) => { ... }))` que lê `new URL(request.url).searchParams.get('building_id')` e o reflete no retorno (ex.: building_number derivado), asserindo que `building_id=1` chegou na query string.
   - **1.3 optimistic flip**: com `queryClient` próprio (`createTestQueryClient` + `createWrapper(queryClient)`), faça `queryClient.setQueryData(queryKeys.rentCalendar.month(2026, 6), createMockRentCalendar({ ... }))` com 1 item `is_paid:false`; sobrescreva o POST com `delay(200)` (técnica acima); chame `result.current.mutate({ lease_id, reference_month: '2026-06-01' })`; **asserir via `waitFor`** que `queryClient.getQueryData<RentCalendar>(queryKeys.rentCalendar.month(2026, 6))?.days[0]?.items[0]?.is_paid` é `true` (flip otimista observável) — depois aguarde `isSuccess`.
   - **1.4 rollback no erro**: `server.use(http.post(.../toggle_rent_payment/, async () => { await delay(100); return new HttpResponse(null, { status: 500 }); }))`; após `waitFor(() => expect(result.current.isError).toBe(true))`, asserir que `queryClient.getQueryData<RentCalendar>(...)?.days[0]?.items[0]?.is_paid` voltou a `false` (snapshot restaurado).
   - **1.5 invalidação no settle**: `vi.spyOn(queryClient, 'invalidateQueries')`; após `isSuccess`, asserir que foi chamado com `{ queryKey: ['rent-calendar'] }`, `{ queryKey: ['dashboard', 'late_payment_summary'] }` e `{ queryKey: ['dashboard', 'financial_summary'] }` (use os arrays literais das keys, como em `use-daily-control.test.tsx:102-105`).
2. Rode (devem **falhar** — hook ainda não existe):
   - `npm run test:unit -- lib/api/hooks/__tests__/use-rent-calendar.test.tsx`

### Green — implemente o mínimo
3. Crie `tests/mocks/data/rent-calendar.ts` (builders + import dos tipos do hook).
4. Implemente `lib/api/hooks/use-rent-calendar.ts` (tipos + `useRentCalendar` + `useToggleRentPayment` optimistic).
5. Adicione o grupo `rentCalendar` em `lib/api/query-keys.ts`.
6. Adicione os handlers em `tests/mocks/handlers.ts` (com `await delay(100)` no POST) e inclua-os no array `handlers`.
7. Rode novamente até **passar**:
   - `npm run test:unit -- lib/api/hooks/__tests__/use-rent-calendar.test.tsx`

### Refactor
8. Extraia `flipItem`/lógica de transformação imutável para função pura local bem nomeada (DRY entre flip e rollback se aplicável; KISS). Sem alterar comportamento — testes seguem verdes.

### Verify (apenas arquivos tocados)
9. Type-check e lint **dos arquivos editados** (estes comandos checam o projeto, mas só editamos estes arquivos — nenhum novo erro/warning é tolerado nos arquivos tocados):
   - `npm run type-check`
   - `npm run lint`
10. Re-rode o arquivo de teste para confirmar verde final:
    - `npm run test:unit -- lib/api/hooks/__tests__/use-rent-calendar.test.tsx`

---

## Constraints

- **Direção de dependências**: componentes/páginas → hooks → `apiClient`. Toda chamada HTTP passa pelo `apiClient` (`lib/api/client.ts`). Não chame `axios` diretamente.
- **Mock policy** (`tests/CLAUDE.md`): mocke **somente** o boundary HTTP via MSW. **Nunca** mocke internals do TanStack Query, do `apiClient`, dos hooks ou de qualquer código da aplicação. `QueryClient` é real (`createTestQueryClient`). `vi.spyOn(queryClient, 'invalidateQueries')` é permitido — é observar uma chamada real, não substituir comportamento interno. O `delay` do MSW e o `waitFor` do testing-library controlam timing do **boundary HTTP / DOM**, não do nosso código — uso permitido e correto.
- **Sem supressões inline**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `// type: ignore`. Corrija o tipo de verdade.
- **TypeScript strict**: `import type` para imports só-de-tipo; `??` em vez de `||` para nulos; guards de null em acesso por índice (`noUncheckedIndexedAccess` — sempre `?.[0]?.`); proibido `as`/`!` — use type narrowing real. Tipos monetários são `string` (não converta para number).
- **Sem re-exports / barrels**: não adicione `rent-calendar` ao `data/index.ts`; importe direto.
- **Sem backwards-compat shims**: não crie wrappers/aliases. (E **não** remova `useMarkRentPaid` — sua remoção é da sessão 25, não desta.)
- **SOLID/DRY/KISS/YAGNI**: tipos hand-written enxutos (apenas os campos do contrato da seção 4.3), nada especulativo.
- **Mensagens**: PT para usuário (mensagens de mock/resposta), EN para logs/identificadores de código.

### NÃO fazer (pertence a OUTRAS sessões)
- **Qualquer componente de UI** (`rent-calendar-section`, `rent-month-grid`, `rent-day-panel`, `rent-stats-panel`, `rent-payment-toggle`) — **sessão 24**.
- **Montar** o calendário em `app/(dashboard)/page.tsx` — **sessão 24**.
- **Tocar** em `late-payments-alert.tsx`, em `useMarkRentPaid`, ou **remover** `mark_rent_paid` (backend) — **sessão 25**.
- Lógica/derivação de rótulo de mês, grid `date-fns`, formatação `formatCurrency` — **sessão 24** (UI).
- Backend (`RentScheduleService`, endpoints) — **sessões 21/22** (já concluídas).

---

## Critérios de Aceite

- [ ] `frontend/lib/api/query-keys.ts` tem o grupo `rentCalendar` com `all` e `month(year, month, buildingId?)`.
- [ ] `frontend/lib/api/hooks/use-rent-calendar.ts` exporta `useRentCalendar` e `useToggleRentPayment` e os tipos (`RentCalendar`, `RentCalendarDay`, `RentCalendarItem`, `RentCalendarStats`, `ToggleRentPaymentRequest`, `ToggleRentPaymentResponse`) via `export type`.
- [ ] `useRentCalendar` usa `apiClient.get('/dashboard/rent_calendar/', { params })` com `staleTime` curto e repassa `building_id` apenas quando definido.
- [ ] `useToggleRentPayment` faz POST em `/dashboard/toggle_rent_payment/` com optimistic: `onMutate` (cancel + snapshot + flip imutável), `onError` (rollback), `onSettled` (invalida `rentCalendar` + `latePaymentSummary` + `financialSummary`).
- [ ] `frontend/tests/mocks/data/rent-calendar.ts` exporta `createMockRentCalendar` e `createMockRentCalendarItem`, importando os tipos do hook (sem redeclarar) e **sem** entrar no barrel `data/index.ts`.
- [ ] `frontend/tests/mocks/handlers.ts` tem `GET /dashboard/rent_calendar/` e `POST /dashboard/toggle_rent_payment/` (POST com `await delay(100)`), incluídos no array `handlers`; mensagem da resposta do toggle em PT.
- [ ] Teste novo cobre: fetch/shape; building_id repassado; optimistic flip; rollback no erro; invalidação no settle (asserindo as 3 keys).
- [ ] O teste de **optimistic flip** é determinístico: sobrescreve o POST com `delay` para abrir a janela E asserta o flip via `waitFor` lendo `queryClient.getQueryData(...)` (sem sleep fixo, sem race).
- [ ] `npm run test:unit -- lib/api/hooks/__tests__/use-rent-calendar.test.tsx` passa 100% (sem warnings de teste).
- [ ] `npm run type-check` sem erros.
- [ ] `npm run lint` sem erros nem warnings nos arquivos tocados.
- [ ] Nenhum `eslint-disable`/`@ts-ignore`/`@ts-expect-error` adicionado; nenhum `as`/`!`; nenhum re-export/barrel novo.
- [ ] `useMarkRentPaid` e o handler/endpoint `mark_rent_paid` permanecem **intactos** (removidos só na sessão 25).

---

## Handoff

1. **Verificar verde** (apenas arquivos editados):
   - `npm run test:unit -- lib/api/hooks/__tests__/use-rent-calendar.test.tsx`
   - `npm run type-check`
   - `npm run lint`
2. **Atualizar `prompts/SESSION_STATE.md`**:
   - Marque a sessão 23 como **concluída** com nota curta (hooks `useRentCalendar`/`useToggleRentPayment` optimistic, query-keys `rentCalendar`, mocks MSW, N testes passando).
   - Liste em "Arquivos Criados": `frontend/lib/api/hooks/use-rent-calendar.ts`, `frontend/lib/api/hooks/__tests__/use-rent-calendar.test.tsx`, `frontend/tests/mocks/data/rent-calendar.ts`.
   - Liste em "Arquivos Modificados": `frontend/lib/api/query-keys.ts`, `frontend/tests/mocks/handlers.ts`.
   - Registre como decisão: optimistic update sobre `rentCalendar.all` via `getQueriesData`/`setQueryData` (a mutation não conhece year/month); teste de flip determinístico via `delay` no handler + `waitFor` lendo o `queryClient`; `useMarkRentPaid` mantido até a sessão 25 (sem backward-compat shim — a remoção é deliberadamente adiada para manter todas as sessões verdes).
3. **Commitar** (a partir de uma branch, não na `master` — se estiver na `master`, crie branch antes):
   - Mensagem sugerida:
     ```
     feat(frontend): add rent calendar data layer (hooks + types + MSW)

     - useRentCalendar(year, month, buildingId?) querying /dashboard/rent_calendar/
     - useToggleRentPayment() with TanStack Query v5 optimistic update
       (onMutate flip + onError rollback + onSettled invalidation)
     - rentCalendar query keys + MSW handlers (POST delayed) + mock builder
     - session 23/25; useMarkRentPaid kept until session 25

     Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
     ```
4. **Próxima sessão**: `prompts/24-frontend-rent-calendar-ui.md` (5 componentes + montagem no dashboard + responsivo/dark), que consome estes hooks.
