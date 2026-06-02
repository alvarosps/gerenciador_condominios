# Sessão 25 — Refatorar consumidor web legado para o toggle unificado, remover `mark_rent_paid` e auditoria final

> Feature: **Calendário de Controle de Aluguéis** (Dashboard)
> Esta é a sessão **final** da feature. É a **única** sessão autorizada a remover o action `mark_rent_paid` do backend.
> Sequenciamento: as sessões 22–24 **adicionaram** `rent_calendar`/`toggle_rent_payment` (back) e `useRentCalendar`/`useToggleRentPayment` (front) **sem** remover o legado. Aqui migramos o último consumidor **web** e removemos o código morto, mantendo tudo verde.

---

## Contexto

- Ler design doc por inteiro: @docs/plans/2026-06-02-rent-payment-calendar-design.md — em especial §2 (Escopo: `:25-40`), §4.3 (Endpoints / unificação de `mark_rent_paid`: `:134,:138`), §4.4 (Regras do toggle) e §8 (Sessões: `:213-216`, linha de hooks/componente `:227-228`).
- Ler padrão de prompts: @prompts/00-prompt-standard.md
- Ler estado anterior: @prompts/SESSION_STATE.md e @prompts/ROADMAP.md
- Regras do projeto (precedência sobre tudo): @CLAUDE.md, @.claude/rules/architecture.md, @.claude/rules/coding-standards.md, @.claude/rules/testing.md, @.claude/rules/design-principles.md, @.claude/rules/api-design.md, @.claude/rules/security.md

### Escopo definido pelo design doc (literal — não expandir)

O design doc define o escopo desta feature e desta sessão. Confirmado por leitura:
- §2 (`:25-40`) **não** inclui o app React Native (`mobile/`). A única menção a "Mobile" (`:23`) é sobre **empilhamento responsivo das 3 colunas da UI web**, não sobre o app mobile.
- §4.3 (`:138`) nomeia explicitamente **apenas** o consumidor web a migrar: `late-payments-alert.tsx` / `use-dashboard.ts` (`useMarkRentPaid`).
- §8 (`:216`) descreve a sessão 25 como: *"Refator `late-payments-alert` p/ toggle unificado + `/audit` + lint/type/test + SESSION_STATE"*. **Nenhum** trabalho mobile.

Portanto, o escopo desta sessão é estritamente: **web (late-payments-alert.tsx + use-dashboard.ts)** + **remoção do backend `mark_rent_paid`** + **auditoria/limpeza**.

### ⚠️ Tensão de nível-design descoberta — ESCALAR antes de remover o backend

Durante o mapeamento, o `mobile/` é um **consumidor vivo** do endpoint que esta sessão deve remover:
`mobile/lib/api/hooks/use-admin-actions.ts:37-48` (`useMarkRentPaid`) e `mobile/app/(admin)/actions/mark-paid.tsx:5,14,35` postam em `/dashboard/mark_rent_paid/`. Remover o action backend **quebra o app mobile**.

O design doc **não escopou** o app mobile nesta feature (§2/§4.3/§8 acima). Isto é uma **tensão de design não resolvida**, não algo a absorver silenciosamente nesta sessão. Além disso, `mobile/package.json` (confirmado) define **apenas** os scripts `start`/`android`/`ios`/`web` — **não há** `type-check`, `lint` nem test runner, ou seja, **não há rede de segurança automatizada** para uma migração mobile (violaria o TDD Red→Green do `00-prompt-standard.md` e a regra de zero-tolerância a warnings, que aqui não poderia sequer ser verificada).

**Procedimento obrigatório (gate):** ANTES de remover `mark_rent_paid` do backend, a sessão **PARA** e reporta a descoberta ao usuário, oferecendo as duas únicas saídas válidas:

- **(A) Emendar o design doc primeiro** — atualizar §2 (incluir o consumidor mobile), §4.3 (descrever a migração mobile) e §8 (criar/ajustar uma sessão dedicada à migração mobile **com verificação configurada** — instalar/definir `type-check`/`lint`/test runner no `mobile/package.json`). Só então a remoção do backend pode prosseguir, numa sessão devidamente escopada. **Esta sessão não faz a migração mobile** e **não** remove o backend enquanto o consumidor mobile existir.
- **(B) Manter o backend `mark_rent_paid` por ora** — concluir **apenas** a migração web (late-payments-alert + use-dashboard) e a auditoria, **deixando o action backend e o consumidor mobile intactos**, e registrar no `SESSION_STATE.md` que a remoção de `mark_rent_paid` está **bloqueada** pela tensão mobile (a ser destravada por uma sessão de migração mobile devidamente escopada/verificada).

A remoção de `mark_rent_paid` (e a limpeza de imports mortos dela decorrente) **só é executada se** o usuário escolher (A) e o design doc for emendado para reconhecer e migrar o consumidor mobile com verificação. Caso contrário, seguir (B). **Não** migrar `mobile/` nesta sessão: está fora do escopo do design doc e é inverificável (sem test runner / type-check / lint).

> **Pré-requisito de sequenciamento**: as sessões 21–24 devem estar concluídas (verificar em `SESSION_STATE.md`). Em particular, `frontend/lib/api/hooks/use-rent-calendar.ts` precisa exportar `useToggleRentPayment()` com body `{ lease_id, reference_month }`, e o endpoint backend `POST /api/dashboard/toggle_rent_payment/` precisa existir. Se algum não existir, **parar** e reportar — esta sessão não os cria.

### Exemplares a ler (arquivo:linha) — exemplar > descrição

| O quê | Onde |
|---|---|
| Consumidor web legado a refatorar | `frontend/app/(dashboard)/_components/late-payments-alert.tsx:1-149` (uso de `useMarkRentPaid` em `:14-16,30,48-57,121-123`) |
| Teste do consumidor web legado | `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx:1-154` (mocka `useMarkRentPaid` em `:8,70,91,128,146`) |
| Hook `useMarkRentPaid` a remover (web) | `frontend/lib/api/hooks/use-dashboard.ts:143-160` (create-only, posta `/dashboard/mark_rent_paid/`) |
| Hook unificado destino (criado na sessão 23) | `frontend/lib/api/hooks/use-rent-calendar.ts` → `useToggleRentPayment()` (mutação optimistic, body `{ lease_id, reference_month }`) |
| Action backend a remover (somente sob saída A) | `core/views.py:722-775` (`mark_rent_paid`, `@action(detail=False, methods=["post"], url_path="mark_rent_paid")`) |
| Imports do backend afetados pela remoção | `core/views.py:4` (`Decimal, InvalidOperation`), `:5` (`cast`), `:7` (`User`), `:12` (`timezone`), `:19` (`RentPayment`) — ver §"Limpeza de imports mortos" |
| Padrão de invalidação em mutação | `frontend/lib/api/hooks/use-dashboard.ts:156-159` |
| Padrão `@action` no DashboardViewSet (actions vizinhos que permanecem) | `core/views.py:600-720` |
| Consumidor mobile (NÃO migrar aqui — apenas inventariar) | `mobile/lib/api/hooks/use-admin-actions.ts:37-48`, `mobile/app/(admin)/actions/mark-paid.tsx:5,14,35` |

---

## Objetivo desta sessão

1. Refatorar o consumidor **web** `late-payments-alert.tsx` para usar o **toggle unificado** (`useToggleRentPayment` de `use-rent-calendar.ts`), em vez do `useMarkRentPaid` create-only de `use-dashboard.ts`.
2. **Remover** o hook morto `useMarkRentPaid` de `frontend/lib/api/hooks/use-dashboard.ts` (sem re-export, sem shim, sem wrapper).
3. **Escalar** a tensão de design do consumidor mobile (ver §"Tensão de nível-design"). **Não** migrar `mobile/` nesta sessão.
4. **Remover** o action `mark_rent_paid` do `DashboardViewSet` (`core/views.py:722-775`) **e limpar os imports que ficam mortos** — **somente** se o usuário escolher a saída (A) e o design doc for emendado para migrar o consumidor mobile com verificação. Caso contrário (saída B), **manter** o action e registrar o bloqueio.
5. Atualizar todos os testes **web** afetados (regressão verde).
6. Rodar `/audit` contra o design doc §2/§8 (completude da feature web: sessões 21–25), lint + type-check + test nos arquivos editados.
7. Atualizar `prompts/SESSION_STATE.md` (sessões 21–25) e `prompts/ROADMAP.md`.

---

## Escopo

### Arquivos a criar
- _Nenhum._ (Esta sessão não introduz funcionalidade nova — apenas migra o consumidor web e remove código morto.)

### Arquivos a modificar (web — sempre)
- `frontend/app/(dashboard)/_components/late-payments-alert.tsx` — usar `useToggleRentPayment` (de `use-rent-calendar.ts`); enviar `{ lease_id, reference_month }` (mês de referência = primeiro dia do mês corrente, `YYYY-MM-01`).
- `frontend/lib/api/hooks/use-dashboard.ts` — **remover** `useMarkRentPaid` (`:143-160`) e o que ficar exclusivamente dele (import `useMutation`/`useQueryClient` se não houver outro uso no arquivo — verificar antes de remover).
- `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx` — mockar `useToggleRentPayment` de `@/lib/api/hooks/use-rent-calendar` no lugar de `useMarkRentPaid`; manter regressão "botão Pago dispara o toggle".
- `frontend/lib/api/hooks/__tests__/use-dashboard.test.tsx` — remover qualquer referência a `useMarkRentPaid` (se houver). _Confirmado na leitura: o teste atual não importa `useMarkRentPaid`, mas reauditar após a edição._
- `prompts/SESSION_STATE.md` — registrar sessões 21–25 (e, na saída B, registrar o bloqueio da remoção de `mark_rent_paid` pela tensão mobile).
- `prompts/ROADMAP.md` — registrar a feature do calendário (21–25) e seu status.

### Arquivos a modificar (backend — SOMENTE sob saída A, após emenda do design doc)
- `core/views.py` — **remover** o action `mark_rent_paid` (`:722-775`) **e** os imports que ficam mortos (`RentPayment`, `cast`, `User` — ver §"Limpeza de imports mortos"). Se houver teste backend cobrindo `mark_rent_paid` (ex.: em `tests/integration/`), removê-lo (comportamento unificado em `toggle_rent_payment`, coberto pela sessão 22).

### Arquivos que esta sessão NÃO modifica
- `mobile/lib/api/hooks/use-admin-actions.ts` e `mobile/app/(admin)/actions/mark-paid.tsx` — **fora do escopo do design doc**, inverificáveis (sem type-check/lint/test no `mobile/`). Apenas inventariar e escalar.

---

## Especificação

### Frontend — `late-payments-alert.tsx`

- Trocar o import `useMarkRentPaid` de `@/lib/api/hooks/use-dashboard` por `useToggleRentPayment` de `@/lib/api/hooks/use-rent-calendar`. Manter `useDashboardLatePayments`.
- `const toggle = useToggleRentPayment();`
- `handleMarkPaid(leaseId)` passa a chamar `toggle.mutate({ lease_id: leaseId, reference_month })`, onde `reference_month` é o **primeiro dia do mês corrente** no formato `YYYY-MM-01` (mesma semântica do antigo `mark_rent_paid`, que sempre lançava o mês corrente — design §A4/§A5 e `core/views.py:746-747`). Usar `date-fns` (`startOfMonth(new Date())` + `format(..., 'yyyy-MM-01')`) ou montagem direta — seguir o padrão de datas já usado nos componentes do calendário (sessão 24) e em `frontend/lib/utils`.
- Manter `onSuccess`/`onError` com `toast`/`handleError` (PT ao usuário). Como o toggle é optimistic e já invalida `rentCalendar` + `latePaymentSummary` + `financialSummary` (sessão 23), **não** duplicar invalidação aqui.
- `disabled={toggle.isPending}` no botão.
- KISS/DRY: não recriar lógica de toggle — apenas consumir o hook unificado. Não introduzir novo estado de servidor (sem `useState` para dados de API).

### Frontend — `use-dashboard.ts`

- Remover completamente `useMarkRentPaid` (`:143-160`) e seu docstring.
- Após remover, verificar se `useMutation` e `useQueryClient` (`:1`) ainda são usados no arquivo. Se **não** forem mais usados, remover do import. Se forem, manter. **Não** deixar import morto (zero tolerância a warnings).
- **Não** criar re-export nem alias de compatibilidade. Consumidores importam `useToggleRentPayment` da fonte (`use-rent-calendar.ts`).

### Backend — `core/views.py` (somente sob saída A)

- Remover o método `mark_rent_paid` inteiro (`@action` + corpo, `:722-775`).
- O endpoint `POST /api/dashboard/toggle_rent_payment/` (criado na sessão 22 via `RentScheduleService.toggle_payment`) é o substituto canônico. **Não** alterá-lo aqui.

#### Limpeza de imports mortos (análise já confirmada por grep — remover/manter conforme abaixo)

Confirmado por leitura de `core/views.py` que os usos abaixo são os únicos no arquivo:

- **`RentPayment` (`:19`) — REMOVER.** Único uso em `:750` e `:763`, ambos dentro de `mark_rent_paid`. Após remover o action, fica morto. Tirar de `from .models import Apartment, Building, Furniture, Lease, RentPayment, Tenant`.
- **`cast` (`:5`) — REMOVER.** Único uso em `:762` (`user = cast(User, request.user)`), dentro de `mark_rent_paid`. Após a remoção, fica morto. Se `Any` (mesma linha) ainda for usado no arquivo, manter apenas `Any` em `from typing import Any`; caso contrário, avaliar a linha inteira.
- **`User` (`:7`) — REMOVER.** Único uso em `:762` (`cast(User, ...)`), dentro de `mark_rent_paid`. Após a remoção, fica morto. Remover `from django.contrib.auth.models import User`.
- **`Decimal`/`InvalidOperation` (`:4`) — MANTER.** Ainda usados em `:533-534` (fora do action removido).
- **`timezone` (`:12`) — MANTER.** Ainda usado em `:282` e `:412` (fora do action removido).

> Regra: nenhum import órfão, nenhum `# noqa`/`# type: ignore`. `cast` e `User` ficam **definitivamente** mortos após a remoção — Ruff/Pyright apontariam, e o projeto proíbe supressão e tem zero-tolerância a warnings. **Remover**, nunca suprimir. Confirmar com `Grep` após a edição que `cast`/`User`/`RentPayment` não aparecem mais em `core/views.py`.

---

## TDD (Red → Green → Refactor → Verify)

### 1. Mapear o terreno (antes de tocar em código)

Rodar grep para inventariar **todas** as referências vivas a `mark_rent_paid` / `useMarkRentPaid` no código (excluindo design docs e specs históricos):
```
Grep "mark_rent_paid|useMarkRentPaid|markRentPaid" (output_mode content, -n)
```
Esperado encontrar: `core/views.py`, `frontend/.../late-payments-alert.tsx` (+ seu teste), `frontend/lib/api/hooks/use-dashboard.ts`, `mobile/lib/api/hooks/use-admin-actions.ts`, `mobile/app/(admin)/actions/mark-paid.tsx`, e possivelmente um teste de integração backend.
Também grep por testes backend: `Grep "mark_rent_paid" tests/`.

**Gate de escalonamento (mobile):** ao confirmar que `mobile/` ainda posta em `/dashboard/mark_rent_paid/`, **PARAR** e seguir o §"Tensão de nível-design": reportar ao usuário e obter a decisão (A) ou (B). Não prosseguir para a remoção do backend sem essa decisão.

### 2. Red — atualizar testes web primeiro
- **Frontend (`late-payments-alert.test.tsx`)**: trocar a fonte do mock de `useMarkRentPaid` (`@/lib/api/hooks/use-dashboard`) para `useToggleRentPayment` (`@/lib/api/hooks/use-rent-calendar`). Ajustar o tipo do retorno mockado para `ReturnType<typeof rentCalendarHooks.useToggleRentPayment>`. Adicionar/garantir um teste de **regressão**: ao clicar em "Pago", `toggle.mutate` é chamado com `{ lease_id, reference_month }` onde `reference_month` termina em `-01` (primeiro dia do mês). Rodar — deve **falhar** (componente ainda usa `useMarkRentPaid`).
- **Mock policy** (`.claude/rules/testing.md`): este teste de componente mocka o **hook de fronteira** via `vi.spyOn` (a fronteira de rede já é coberta por MSW nos testes de hook da sessão 23). Não mockar lógica interna do componente. Mantém o padrão já existente neste arquivo de teste (que faz spy no hook).

### 3. Green — implementar a migração web (e, sob saída A, a remoção backend)
1. `late-payments-alert.tsx` → usar `useToggleRentPayment` com `{ lease_id, reference_month }`.
2. `use-dashboard.ts` → remover `useMarkRentPaid` + imports mortos do arquivo.
3. **(Somente saída A)** `core/views.py` → remover `mark_rent_paid` + remover imports mortos `RentPayment`, `cast`, `User` (manter `Decimal`/`InvalidOperation`/`timezone`).
4. **(Somente saída A)** Remover teste de integração backend de `mark_rent_paid`, se existir (substituído por `toggle_rent_payment`, sessão 22).
Rodar os testes editados — devem **passar**.

### 4. Refactor
- Garantir DRY/KISS: nenhuma duplicação de lógica de toggle no consumidor; `reference_month` derivado de forma única e legível.
- Confirmar que não restou import, tipo, variável ou comentário morto em nenhum arquivo tocado. Em `core/views.py` (saída A), confirmar via `Grep` que `cast`, `User` e `RentPayment` não aparecem mais.

### 5. Verify — comandos (somente arquivos editados; suite completa tem issues pré-existentes de xdist/Redis — ver MEMORY)

Backend (**somente sob saída A**, a partir de `c:/Users/alvar/git/personal/gerenciador_condominios`):
```bash
ruff check core/views.py
ruff format --check core/views.py
pyright core/views.py
# Se removeu teste de integração de mark_rent_paid, rodar o arquivo de integração do calendário:
python -m pytest tests/integration/test_rent_calendar_api.py -p no:cacheprovider
```
Frontend (a partir de `frontend/`):
```bash
npm run lint -- app/(dashboard)/_components/late-payments-alert.tsx lib/api/hooks/use-dashboard.ts
npm run type-check
npm run test:unit -- app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx lib/api/hooks/__tests__/use-dashboard.test.tsx
```
Mobile: **não há comandos de verificação**. `mobile/package.json` define apenas `start`/`android`/`ios`/`web` — sem `type-check`, `lint` ou test runner. Por isso o `mobile/` **não é tocado** nesta sessão (ver §"Tensão de nível-design"). Não escrever comandos `npm run type-check`/`npm run lint` para `mobile/`: falhariam ("missing script").

Grep final de verificação:
```
Grep "mark_rent_paid|useMarkRentPaid" (output_mode content, -n)
```
- **Saída A** (backend removido + design emendado p/ migrar mobile depois): o grep não deve mais retornar ocorrências em `core/`, `frontend/` e `tests/`. Ocorrências remanescentes em `mobile/` são esperadas e **documentadas** (a migração mobile é uma sessão futura escopada). Referências em `docs/plans/`, `docs/superpowers/` e `prompts/` são histórico/spec.
- **Saída B** (backend mantido): o grep ainda retorna `core/views.py` e `mobile/` (esperado). O frontend web (`late-payments-alert.tsx` + teste + `use-dashboard.ts`) **não** deve mais conter `useMarkRentPaid`.

### 6. `/audit` da feature (sessões 21–25)
Invocar o skill **`/audit`** comparando o implementado contra o design doc §2 (Escopo Incluído, `:25-40`) e §8 (tabela de sessões, `:213-216`). Verificar completude de ponta a ponta **do escopo do design doc** (web + backend; o mobile NÃO está no escopo do design):
- Backend: `RentScheduleService` (§4.1), refactor DRY do `DailyControlService` (§4.2), endpoints `rent_calendar` + `toggle_rent_payment` (§4.3); `mark_rent_paid` removido **se** saída A, ou bloqueio registrado **se** saída B.
- Frontend web: `use-rent-calendar.ts` (hook + toggle optimistic), `query-keys` (grupo `rentCalendar`), 5 componentes do calendário + montagem em `page.tsx`, consumidor legado web migrado.
- Sem referência morta a `mark_rent_paid` no consumidor web migrado.
Se o audit encontrar gap dentro do escopo desta sessão (migração web/remoção backend/limpeza), **corrigir agora**. Gaps que pertençam a outras sessões (ver "NÃO fazer") são apenas **registrados** no SESSION_STATE, não implementados aqui. A tensão mobile é registrada como pendência de design, não como gap de implementação desta sessão.

---

## Constraints — NÃO fazer

- **NÃO** introduzir funcionalidade nova (sem novos endpoints, sem novos componentes, sem novos campos). Esta sessão é migração web + (condicionalmente) remoção backend + auditoria.
- **NÃO** migrar o app `mobile/` (`use-admin-actions.ts`, `mark-paid.tsx`): está **fora do escopo do design doc** (§2/§4.3/§8) e é **inverificável** (sem `type-check`/`lint`/test runner no `mobile/package.json`). Em vez disso, **escalar** a tensão de design conforme §"Tensão de nível-design".
- **NÃO** remover `mark_rent_paid` do backend enquanto o consumidor mobile existir e o design doc não tiver sido emendado para migrá-lo com verificação (isso deixaria o app mobile órfão/quebrado). Seguir o gate (A)/(B).
- **NÃO** deixar referência morta a `mark_rent_paid`/`useMarkRentPaid` no consumidor **web** migrado (`late-payments-alert.tsx`, seu teste, `use-dashboard.ts`).
- **NÃO** criar re-export, barrel file, alias ou shim de `useMarkRentPaid` apontando para o toggle. Consumidores importam da fonte (`use-rent-calendar.ts`).
- **NÃO** manter backwards-compat no que for removido: quando o action backend e o hook web forem removidos, são **removidos**, não deprecados.
- **NÃO** alterar a assinatura/comportamento de `useToggleRentPayment`, `useRentCalendar` nem do endpoint `toggle_rent_payment` (pertencem às sessões 22/23 — já entregues e testados).
- **NÃO** mexer no `RentScheduleService` nem no refactor do `DailyControlService` (sessão 21).
- **NÃO** criar/editar os 5 componentes do calendário nem a montagem no `page.tsx` (sessão 24).
- **NÃO** suprimir lint/type errors com `# noqa`, `# type: ignore`, `eslint-disable` ou `@ts-ignore` — corrigir a causa raiz (ex.: remover `cast`/`User`/`RentPayment` mortos).
- **NÃO** rodar a suite completa de testes (xdist crasha no Windows/Python 3.14 e serviços sem Redis dão timeout — issues pré-existentes). Rodar apenas os arquivos editados, conforme §Verify.
- **NÃO** tocar no banco de dados (nenhuma migration nesta sessão; nada destrutivo).

---

## Critérios de Aceite (binários)

### Web (sempre)
- [ ] `late-payments-alert.tsx` importa `useToggleRentPayment` de `@/lib/api/hooks/use-rent-calendar` e **não** importa mais `useMarkRentPaid`.
- [ ] O botão "Pago" chama `toggle.mutate({ lease_id, reference_month })` com `reference_month` = primeiro dia do mês corrente (`YYYY-MM-01`).
- [ ] `useMarkRentPaid` foi **removido** de `frontend/lib/api/hooks/use-dashboard.ts`; nenhum import órfão restou no arquivo.
- [ ] `late-payments-alert.test.tsx` mocka `useToggleRentPayment` e tem teste de regressão do clique em "Pago" (verde).
- [ ] `use-dashboard.test.tsx` não referencia `useMarkRentPaid` (verde).
- [ ] `npm run lint` (arquivos web editados) + `npm run type-check` (frontend) limpos (zero warnings).
- [ ] `npm run test:unit` dos arquivos de teste web editados passa.
- [ ] Grep por `mark_rent_paid|useMarkRentPaid` **não** retorna ocorrências no consumidor web migrado (`frontend/app/(dashboard)/_components/late-payments-alert.tsx` + seu teste, `frontend/lib/api/hooks/use-dashboard.ts`).

### Backend (somente sob saída A — design doc emendado)
- [ ] O action `mark_rent_paid` foi **removido** de `core/views.py`.
- [ ] `RentPayment` foi removido do import `from .models import ...` (estava em uso só em `:750/:763`, dentro do action).
- [ ] `cast` foi removido de `from typing import ...` (estava em uso só em `:762`, dentro do action) — definitivamente morto após a remoção.
- [ ] `User` foi removido (`from django.contrib.auth.models import User`) (estava em uso só em `:762`, dentro do action) — definitivamente morto após a remoção.
- [ ] `Decimal`/`InvalidOperation`/`timezone` foram **mantidos** (ainda usados em `:533-534` e `:282/:412`).
- [ ] Teste backend de `mark_rent_paid` (se existia) foi removido.
- [ ] `ruff check` + `ruff format --check` + `pyright` limpos em `core/views.py` (zero warnings — incluindo zero import não usado).
- [ ] Grep confirma que `cast`, `User` e `RentPayment` não aparecem mais em `core/views.py`.

### Escalonamento / documentação (sempre)
- [ ] A tensão de design do consumidor mobile foi **escalada** ao usuário e a decisão (A) ou (B) foi registrada no `SESSION_STATE.md`.
- [ ] Nenhuma alteração foi feita em `mobile/` nesta sessão.
- [ ] **(Saída B)** O `SESSION_STATE.md` registra que a remoção de `mark_rent_paid` está **bloqueada** pela tensão mobile (a destravar por sessão de migração mobile escopada/verificada).

### Auditoria + handoff (sempre)
- [ ] `/audit` contra design §2/§8 confirma a feature **web** completa (sessões 21–25), sem gaps no escopo desta sessão.
- [ ] `prompts/SESSION_STATE.md` atualizado com sessões 21–25 (status + arquivos criados/modificados + decisão (A)/(B)).
- [ ] `prompts/ROADMAP.md` atualizado com a feature do calendário (21–25) e seu status.

---

## Handoff

1. **Gate mobile primeiro**: antes de qualquer remoção backend, escalar a tensão de design (§"Tensão de nível-design") e obter a decisão (A)/(B). Registrar a escolha.
2. **Verify**: rodar os comandos de §5 (lint + type-check + arquivos de teste web editados; backend somente sob saída A) e confirmar verde antes de qualquer alegação de conclusão (evidência antes de asserção).
3. **Audit**: registrar o resultado do `/audit` (feature web 21–25 completa) no `SESSION_STATE.md`.
4. **SESSION_STATE.md**: adicionar bloco da feature "Calendário de Controle de Aluguéis" cobrindo sessões 21–25 — status, lista de arquivos criados e modificados, decisões arquiteturais (ex.: `reference_month` = mês corrente no consumidor web legado) e **a decisão (A)/(B)** sobre o mobile (incluindo, na saída B, o bloqueio explícito da remoção de `mark_rent_paid` e a risco documentado de ausência de testes/type-check/lint no `mobile/`).
5. **ROADMAP.md**: adicionar a feature do calendário (21–25), dependências (24→25) e seu status; se houver migração mobile pendente, listá-la como item futuro escopado.
6. **Commit** (somente quando o usuário pedir; se estiver na branch default, criar branch antes). Mensagem sugerida (ajustar conforme saída A/B):
   ```
   refactor(rent-calendar): migrate web late-payments consumer to unified toggle

   - late-payments-alert now uses toggle_rent_payment via useToggleRentPayment
   - remove dead useMarkRentPaid web hook
   - (sob saída A) remove mark_rent_paid backend action + dead imports (RentPayment, cast, User)
   - update affected web tests; escalate mobile consumer as design-level pending

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
7. A feature **web** está completa após esta sessão. A migração do consumidor mobile (se aprovada via saída A) fica para uma sessão futura **devidamente escopada no design doc e com verificação configurada** (`type-check`/`lint`/test runner no `mobile/`).
