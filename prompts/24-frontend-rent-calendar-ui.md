# Sessão 24 — Frontend: Componentes UI do Calendário de Aluguéis + montagem no dashboard

> Parte da feature "Calendário de Controle de Aluguéis". Esta sessão constrói **somente a camada de
> UI** (5 componentes + montagem no dashboard + testes de componente). Os hooks/tipos/MSW já existem
> da Sessão 23 — esta sessão **consome** esse contrato, não o altera.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro, foco nas seções 1, 4.1, 4.3, 4.4, 6, UI/UX): `@docs/plans/2026-06-02-rent-payment-calendar-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar que Sessão 23 está concluída antes de começar)
- Mockup visual (light + dark, layout das 3 colunas, estados de status, chips, cards): `@docs/mockups/rent-calendar-mockup.html`
- Regras do projeto: `CLAUDE.md`, `frontend/CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/coding-standards.md`, `tests/CLAUDE.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — exemplar > descrição, abrir e seguir)
- **Estilos/tokens, lucide, sonner, `formatCurrency`, `handleError`, parsing de data ISO sem timezone**:
  `frontend/app/(dashboard)/_components/late-payments-alert.tsx:1-149` (em especial `formatDate` `:22-26` que faz split de `YYYY-MM-DD` — **não** usar `new Date(isoString)` para datas puras, há bug de timezone).
- **Ponto de montagem no dashboard**: `frontend/app/(dashboard)/page.tsx:1-41`.
- **Padrões de dia/status/badge/skeleton/overdue highlight, sub-componentes pequenos, `cn`**:
  `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx:62-70` (StatusBadge), `:164-191` (EntryRow), `:201-240` (overdue highlight `bg-destructive/10`), `:313-328` (skeleton), `:415-421` (empty state).
- **Painel/itens de dia com estados pago/pendente/vencido + botão por item**:
  `frontend/app/(dashboard)/financial/daily/_components/day-detail-drawer.tsx:65-237`.
- **Navegação de mês + filtro de prédio (Select shadcn) + estado `{year, month}` + cálculo prev/next**:
  `frontend/app/(dashboard)/financial/daily/page.tsx:33-110, 136-217` (NOTA: o filtro em `:197-217` filtra por **nome** do prédio; aqui usamos `buildingId` — o exemplar serve apenas como modelo **estrutural** do `Select`, não da chave de filtro).
- **`formatCurrency`**: `frontend/lib/utils/formatters.ts:5-15`.
- **`formatMonthYear`** (rótulo do mês em PT, formato "Junho/2026" — **com barra**): `frontend/lib/utils/formatters.ts:72-76`. **NOTA CRÍTICA**: a implementação usa `Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' })`, cuja saída é `"Junho/2026"` (barra, não espaço). O docstring exemplifica `"Março/2026"`. As asserções de teste DEVEM usar exatamente a saída real (ex.: `'Junho/2026'`).
- **`MONTH_NAMES`/`MONTH_ABBR`** (rótulos de mês/abreviação, se necessário para legenda): `frontend/lib/utils/formatters.ts:87-92`.
- **Switch (Radix)**: `frontend/components/ui/switch.tsx:1-29`. **Tooltip (Radix)**: `frontend/components/ui/tooltip.tsx:1-30`.
- **Teste de componente do dashboard (padrão a copiar)**: `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx:1-154` (helper `makeQueryResult` `:10-36`, `idleMutation` `:38-55`, `vi.spyOn` no módulo de hooks `:67-70`, `renderWithProviders`). **Atenção**: esse exemplar constrói os fixtures com `as <Result>` / `as unknown as <Mutation>` — ver carve-out na seção Constraints.
- **Render de testes (providers)**: `frontend/tests/test-utils.tsx:55-78`.

### Contrato de dados consumido (definido pela Sessão 23, NÃO redefinir)
Importar os **tipos e hooks** de `@/lib/api/hooks/use-rent-calendar` (`useRentCalendar`, `useToggleRentPayment`
e os tipos exportados). A forma de cada item do dia e das stats é a do design doc §4.3:

- **Item do dia**: `{ lease_id, tenant_name, apartment_number, building_number, rental_value (string),
  is_paid, payment_date|null, is_overdue, day_passed, can_toggle, late_fee (string), late_days }`.
- **Dia**: `{ day, date ("YYYY-MM-DD"), weekday, items: Item[] }`.
- **Schedule**: `{ year, month, today ("YYYY-MM-DD"), next_due_date ("YYYY-MM-DD"|null), days: Day[], stats }`.
- **Stats**: `{ received_total, to_receive_total, expected_total (strings), paid_count, due_count,
  overdue_count, overdue_total_fee (string), vacant_kitnets_count, vacant_kitnets_value (string) }`.
- **Payload do toggle (§4.3)**: `useToggleRentPayment().mutate({ lease_id, reference_month })`, onde
  `reference_month` é `"YYYY-MM-01"` (dia 1 do `{year, month}` carregado).

Se algum nome de tipo/hook divergir do que a Sessão 23 exportou, **importar exatamente o nome real
do módulo** — nunca recriar/duplicar os tipos aqui (DRY, sem re-export).

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/_components/rent-calendar/rent-calendar-section.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/rent-month-grid.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/rent-day-panel.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/rent-stats-panel.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/rent-payment-toggle.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/__tests__/rent-day-panel.test.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/__tests__/rent-month-grid.test.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/__tests__/rent-stats-panel.test.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/__tests__/rent-payment-toggle.test.tsx`
- `frontend/app/(dashboard)/_components/rent-calendar/__tests__/rent-calendar-section.test.tsx`

### Arquivos a modificar
- `frontend/app/(dashboard)/page.tsx` — montar `<RentCalendarSection />` no **topo** da `<div className="space-y-6">`, **acima** de `<FinancialSummaryWidget />`.

## Especificação

Direção de dados (regra `frontend/CLAUDE.md`): os componentes **recebem props** ou consomem hooks
da Sessão 23. **Nenhum componente chama `apiClient`/axios diretamente.** Apenas `rent-calendar-section.tsx`
chama os hooks (`useRentCalendar`, `useToggleRentPayment`, `useBuildings`); os demais são puros (props in, callbacks out).

### Tokens de tema (light + dark) — usar os tokens semânticos do projeto, NÃO os CSS vars crus do mockup
O mockup usa `--success/--warn/--danger`; no app real esses já existem como classes Tailwind semânticas
(ver `late-payments-alert.tsx` e `daily-timeline.tsx`). Mapear:
- **Pago** → `text-success` / `border-success/20` / `bg-success/10` + ícone `Check`/`CheckCircle2` + rótulo "Pago".
- **A vencer** → âmbar: `text-amber-600 dark:text-amber-400` (ou o token de aviso já usado no projeto, conferir
  qual existe) + rótulo "A vencer".
- **Em atraso** → `text-destructive` / `bg-destructive/10` + ícone `AlertTriangle` + rótulo "Em atraso · N dias".
- **Hoje/Selecionado** (grade) → `border-primary` + `bg-primary/10` (selecionado), badge circular `bg-primary text-primary-foreground` (hoje).
- Dark mode é controlado por `next-themes` já no app — **não** adicionar toggle de tema; apenas usar tokens que respondem a `.dark`.

CRITICAL (UI/UX): **status nunca apenas por cor** — sempre acompanhar de rótulo textual e/ou ícone (acessibilidade).

### `rent-payment-toggle.tsx`
Componente apresentacional (Radix Switch + Tooltip). Props sugeridas:
```ts
interface RentPaymentToggleProps {
  isPaid: boolean;
  canToggle: boolean;
  isPending: boolean;
  onToggle: () => void;
  disabledReason?: string;
}
```
- Usa `<Switch checked={isPaid} disabled={!canToggle || isPending} onCheckedChange={() => onToggle()} />`.
- Label visível "Pago?" + estado acessível (`aria-label`).
- Quando `!canToggle`: envolver em `Tooltip`/`TooltipContent` exibindo `disabledReason` (texto em PT). O motivo
  vem do design §4.4: "Pagamento confirmado — o dia já passou, não é possível desmarcar" (pago + dia passou)
  e, quando aplicável, "Mês finalizado — não é possível alterar". O `disabledReason` é decidido pelo chamador
  (`rent-day-panel`), a partir das flags do item (`is_paid && day_passed`).
- `TooltipProvider` deve envolver a árvore que usa Tooltip (incluir no `rent-day-panel` ou no section).

### `rent-day-panel.tsx` (coluna 1)
Props: lista de `items` do dia selecionado, a `date`/label do dia, `today`, `next_due_date`, e callbacks
`onToggle(leaseId)`, `onGoToday()`, `onGoNextDue()`, além de `isPending` da mutation.
- Header: rótulo do dia selecionado (ex.: "Segunda, 15/06") + botões "Hoje" e "Próx. vencimento"
  (botão "Próx. vencimento" desabilitado se `next_due_date` for null).
- Para cada item renderiza um card com: nome do inquilino, "Apto {n} · Préd. {building_number}", valor
  (`formatCurrency(rental_value)`), chip de status (pago/a vencer/em atraso com ícone+rótulo), e `RentPaymentToggle`.
  Derivar o `disabledReason` aqui (ex.: `is_paid && day_passed` → texto do §4.4) e passar à toggle.
- **Em atraso**: destaque `bg-destructive/10` + exibir `+ multa {formatCurrency(late_fee)}` e `late_days` dias.
- **Pago**: exibir "Pago em {DD/MM}" usando parsing ISO por split (como `late-payments-alert.tsx:22-26`), nunca `new Date(iso)`.
- Empty state: "Nenhum vencimento neste dia".

### `rent-month-grid.tsx` (coluna 2)
Grade custom com `date-fns` (NÃO instalar dependência nova; `date-fns` já está no projeto). Props: `year`,
`month`, `days` (com items), `today`, `selectedDay`, `onSelectDay(day)`, `onPrevMonth()`, `onNextMonth()`.
- Cabeçalho de semana: Dom..Sáb. Construir a grade com `startOfMonth`/`getDay` (offset do 1º dia) e
  `getDaysInMonth`. Células vazias para o offset inicial.
- Cada célula: número do dia + até N chips (nome do inquilino) coloridos por status (pago=success,
  a vencer=âmbar, atraso=danger), `truncate`. Hoje destacado (badge circular primary), dia selecionado
  com `border-primary bg-primary/10`. Clique na célula chama `onSelectDay`.
- Navegação de mês (chevrons) chamando `onPrevMonth`/`onNextMonth`.
- Legenda no rodapé (Pago / A vencer / Em atraso / Hoje) — texto + amostra de cor (status não só por cor).

### `rent-stats-panel.tsx` (coluna 3)
Props: objeto `stats` + `year`/`month`. 4 cards:
1. **Mês** → `formatMonthYear(year, month)` → produz `"Junho/2026"` (com barra; ver exemplar `formatters.ts:72-76`).
2. **Recebido até hoje** → `formatCurrency(received_total)` + "{paid_count} de {due_count} aluguéis pagos".
3. **A receber ainda** → `formatCurrency(to_receive_total)` + "{due_count - paid_count} pendentes · {overdue_count} em atraso (+{formatCurrency(overdue_total_fee)} multa)" (só mostrar trecho de atraso se `overdue_count > 0`).
4. **Kitnets não alugados** → `vacant_kitnets_count` + "Potencial: {formatCurrency(vacant_kitnets_value)}/mês".

### `rent-calendar-section.tsx` (container)
- `'use client'`. Estado local (`useState`) para `{ year, month }` (default: mês atual) e `selectedDay` (default: dia de `today` se no mês atual, senão dia 1).
- Filtro de prédio: `useBuildings()` + `Select` (default "Todos os prédios" → `buildingId = undefined`), modelo estrutural em `daily/page.tsx:197-217` (lá filtra por nome; aqui o valor do `Select` é o `building_id`).
- Hooks: `useRentCalendar(year, month, buildingId)` e `useToggleRentPayment()`.
- **Derivação do `reference_month`**: antes de chamar a mutation, construir `reference_month` = dia 1 do
  `{year, month}` atualmente carregado, no formato `"YYYY-MM-01"` (ex.: `\`${year}-${String(month).padStart(2,'0')}-01\``).
  Esse é o segundo campo do payload do toggle (design §4.3); o `lease_id` vem do item.
- `handleToggle(leaseId)`: monta `{ lease_id: leaseId, reference_month }` e chama
  `useToggleRentPayment().mutate(...)` (ou `mutateAsync`); `toast.success(result.message)` em sucesso e
  `handleError(error, 'Erro ao atualizar pagamento')` em erro (padrão `late-payments-alert.tsx:48-57`).
  A invalidação/optimistic já está no hook da Sessão 23 — **não** reimplementar aqui.
- Layout: `<section>` com header (título "Controle de Aluguéis do Mês" + ícone calendário + filtro prédio + nav mês) e
  grid `grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-4`. Mobile empilha (1 coluna).
- Loading: skeletons (padrão `daily-timeline.tsx:313-328`). Empty/sem dados: estado vazio adequado.
- "Hoje" reseta `{year, month}` ao mês atual e `selectedDay` ao dia de hoje; "Próx. vencimento" seleciona o dia de `next_due_date` (e ajusta `{year,month}` se necessário — mas mantenha simples; `next_due_date` é sempre no mês carregado pelo back, então basta `selectedDay`).
- Montar em `page.tsx` no topo, acima de `<FinancialSummaryWidget />`.

## TDD

Rodar **somente os arquivos de teste desta sessão** (a suíte completa tem problemas pré-existentes de
xdist/Redis — ver memória do projeto).

### 1. Red — escrever os testes primeiro (devem falhar por componente inexistente)
Comando: `cd frontend && npx vitest run "app/(dashboard)/_components/rent-calendar"`

Cobrir, no mínimo:

**`rent-payment-toggle.test.tsx`**
- Renderiza switch marcado quando `isPaid=true`; desmarcado quando `false`.
- `disabled` quando `canToggle=false` ou `isPending=true`.
- `onToggle` é chamado ao clicar quando habilitado; **não** é chamado quando desabilitado.
- Quando desabilitado por "pago + dia passou", expõe `disabledReason` (tooltip/`aria`) com o motivo em PT.

**`rent-day-panel.test.tsx`**
- Renderiza item **a vencer** (rótulo "A vencer" + valor formatado).
- Renderiza item **pago** com "Pago em DD/MM" e toggle marcado.
- Item **pago + day_passed (can_toggle=false)** → toggle desabilitado.
- Item **em atraso** → rótulo "Em atraso", dias de atraso, multa `formatCurrency(late_fee)` visível, highlight de atraso (não apenas cor: verificar texto).
- Empty state "Nenhum vencimento neste dia" quando `items` vazio.
- Botões "Hoje" e "Próx. vencimento" disparam callbacks; "Próx. vencimento" desabilitado quando `next_due_date` null.

**`rent-month-grid.test.tsx`**
- Renderiza o número correto de células de dia para um mês conhecido (ex.: junho/2026 = 30 dias) com offset correto.
- Chips de inquilino aparecem nos dias com `items` (texto do nome presente).
- Clicar numa célula chama `onSelectDay` com o dia certo.
- Dia "hoje" e "selecionado" recebem destaque (verificar via rótulo/elemento, não cor pura).
- Clamping visual: um dia que recebe item de vencimento 31→30 mostra o inquilino no dia 30 (montar fixture conforme back).

**`rent-stats-panel.test.tsx`**
- Os 4 cards exibem números formatados a partir do `stats` fornecido. Para o card "Mês", asserir **exatamente** a saída de `formatMonthYear` — ex.: `expect(screen.getByText('Junho/2026')).toBeInTheDocument()` (com barra, não espaço).
- Trecho de atraso só aparece quando `overdue_count > 0`.

**`rent-calendar-section.test.tsx`** (mockar APENAS os hooks da Sessão 23 + `useBuildings`, via `vi.spyOn` no módulo — fronteira de dados, não mockar componentes internos)
- Loading → skeleton presente.
- Com dados → renderiza painel do dia, grade e stats (uma asserção por coluna).
- Toggle: ao acionar o switch de um item, a mutation (`useToggleRentPayment().mutate`/`mutateAsync`) é chamada com `{ lease_id, reference_month }` esperado, onde `reference_month` = dia 1 do mês carregado (`"YYYY-MM-01"`).

### 2. Green — implementar os 5 componentes + montagem, mínimo para passar os testes
### 3. Refactor — extrair sub-componentes pequenos (StatusChip, DayCell) e helpers de status; sem duplicação; sem comentários supérfluos
### 4. Verify
- `cd frontend && npx vitest run "app/(dashboard)/_components/rent-calendar"` → tudo verde.
- `cd frontend && npx tsc --noEmit` (type-check; sem erros nos arquivos tocados).
- `cd frontend && npx eslint "app/(dashboard)/_components/rent-calendar" "app/(dashboard)/page.tsx"` → zero erros/avisos.

## Constraints (NÃO fazer)

- **NÃO** alterar/criar/duplicar hooks, tipos ou query-keys — consumir os da Sessão 23 (`use-rent-calendar.ts`). Importar da fonte, sem re-export.
- **NÃO** mexer em `late-payments-alert.tsx` nem em `use-dashboard.ts`/`useMarkRentPaid` — refator do consumidor unificado é **Sessão 25**.
- **NÃO** remover/alterar o endpoint/ação `mark_rent_paid` (backend) — pertence à Sessão 25.
- **NÃO** chamar `apiClient`/axios diretamente em componente.
- **NÃO** instalar dependências novas (usar `date-fns`, Radix Switch/Tooltip já presentes).
- **NÃO** usar `new Date(isoString)` para datas puras `YYYY-MM-DD` (bug de timezone) — fazer split, como em `late-payments-alert.tsx:22-26`.
- **NÃO** usar `# noqa`/`eslint-disable`/`@ts-ignore`; **em código de produção** (componentes), NÃO usar `as`/`!` — corrigir o tipo na raiz; usar `import type`, `??`, e null guards (`noUncheckedIndexedAccess`).
- **CARVE-OUT (somente fixtures de teste)**: nos arquivos `*.test.tsx`, ao construir o objeto de retorno de um hook de query/mutation do TanStack Query (cujo shape completo é inviável de satisfazer sem assertion), É PERMITIDO usar `as <Result>` / `as unknown as <Mutation>`, **exatamente como no exemplar** `late-payments-alert.test.tsx:35,55`. Esse uso fica restrito aos helpers de fixture (`makeQueryResult`, `idleMutation`-equivalente); em qualquer outro lugar dos testes e em todo o código de produção, `as`/`!` continuam proibidos.
- **NÃO** mockar componentes internos, ORM, biblioteca, TanStack Query — em `rent-calendar-section.test.tsx` mockar somente a fronteira de dados (hooks da Sessão 23 + `useBuildings`), via `vi.spyOn` no módulo (padrão `late-payments-alert.test.tsx`).
- **NÃO** adicionar toggle de tema (dark vem de `next-themes`); apenas usar tokens semânticos que respondem a `.dark`.
- **NÃO** rodar a suíte completa de testes (apenas os arquivos desta sessão) — evitar falhas pré-existentes de xdist/Redis.
- SOLID/DRY/KISS/YAGNI — funções pequenas, componentes de responsabilidade única, sem código especulativo.

## Critérios de Aceite

- [ ] Os 5 componentes existem em `frontend/app/(dashboard)/_components/rent-calendar/` com `'use client'` onde necessário.
- [ ] `rent-calendar-section.tsx` usa grid `grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-4` e empilha no mobile.
- [ ] `<RentCalendarSection />` está montado no **topo** de `page.tsx`, acima de `<FinancialSummaryWidget />`.
- [ ] `rent-month-grid.tsx` usa `date-fns` (`startOfMonth`/`getDay`/`getDaysInMonth`) — grade custom, sem dependência nova.
- [ ] Painel do dia mostra estados (a vencer / pago / em atraso) com rótulo + ícone (status nunca só por cor).
- [ ] Toggle desabilitado quando `can_toggle=false` (pago + dia passou) com tooltip em PT explicando o motivo (`disabledReason`).
- [ ] Em atraso destaca card e exibe dias de atraso + multa formatada.
- [ ] Stats panel exibe os 4 cards com valores formatados; o card "Mês" exibe a saída exata de `formatMonthYear` (ex.: `"Junho/2026"`, com barra) e valores via `formatCurrency`.
- [ ] Datas puras `YYYY-MM-DD` formatadas por split (sem `new Date(iso)`); moeda via `formatCurrency`; PT no usuário.
- [ ] Toggle chama `useToggleRentPayment` com `{ lease_id, reference_month }`, onde `reference_month` = dia 1 do mês carregado (`"YYYY-MM-01"`); sucesso → toast, erro → `handleError`.
- [ ] Loading mostra skeletons; estados vazios em PT ("Nenhum vencimento neste dia").
- [ ] Componentes (exceto o section) são puros: recebem props/callbacks, sem chamadas a API.
- [ ] `late-payments-alert.tsx`, `use-dashboard.ts` e `mark_rent_paid` **inalterados** nesta sessão.
- [ ] `npx vitest run "app/(dashboard)/_components/rent-calendar"` 100% verde.
- [ ] `npx tsc --noEmit` sem erros nos arquivos tocados; `eslint` zero erros/avisos nos arquivos tocados.
- [ ] Sem `# noqa`/`eslint-disable`/`@ts-ignore`; sem re-exports; sem dependência nova. `as`/`!` ausentes no código de produção; o único `as` permitido é nos helpers de fixture de teste (padrão `late-payments-alert.test.tsx`).

## Handoff

1. Rodar e confirmar verde (colar saída como evidência):
   - `cd frontend && npx vitest run "app/(dashboard)/_components/rent-calendar"`
   - `cd frontend && npx tsc --noEmit`
   - `cd frontend && npx eslint "app/(dashboard)/_components/rent-calendar" "app/(dashboard)/page.tsx"`
2. Atualizar `prompts/SESSION_STATE.md`: marcar Sessão 24 concluída; anotar que a **Sessão 25** ainda
   deve (a) refatorar `late-payments-alert.tsx` para o toggle unificado e (b) remover `mark_rent_paid`
   (backend) + `useMarkRentPaid` (path só-cria) — até lá ambos permanecem em uso.
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(frontend): add rent calendar UI components and mount on dashboard

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A Sessão 25 começa lendo o `SESSION_STATE.md`.
