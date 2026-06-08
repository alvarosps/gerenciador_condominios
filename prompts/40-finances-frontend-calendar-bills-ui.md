# Sessão 40 — Frontend UI: calendário combinado + página de Contas (CRUD) + pagamento

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → **40** → 41 → … → 50 (Fase 2, **camada de UI** do frontend)
> Esta sessão constrói **somente a UI da Fase 2**: (1) **calendário combinado** no dashboard (seções *Aluguéis (entradas)* e *Contas a pagar (saídas)* separadas por dia + toggle otimista de pagamento de conta); (2) **página de Contas** (CRUD via `useCrudPage` + `DataTable` + form modal com **linhas** via `create_with_lines` + ações **suspender/deferir**); (3) **UI de pagamento** (parcial + `funded_from`). Os hooks/schemas/query-keys/MSW já existem da **Sessão 39** — esta sessão **consome** esse contrato, **não** o altera. **Sem KPIs de saldo (Fase 4), sem projeção (Fase 5).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.1 sinal de `is_offset`, §4.4 atrasado, §5 modelo, §9 API, §10 Frontend/Dashboard, §11 cache lado consumidor, §18 edge-cases das fases 2/4)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md` — **confirmar S39 concluída** (esta sessão consome schemas/hooks/query-keys/MSW que ela entregou). **Se S39 não estiver concluída, PARE** (DEPENDENCY ORDER 38 → 39 → 40).
- **Contrato de dados (verbatim, NÃO derivar)**: a seção "Contratos cross-session definidos por esta sessão (consumir verbatim na S40)" no fim de `@prompts/39-finances-frontend-data-layer.md`, **mais** as notas de divergência que a S39 tiver registrado no `SESSION_STATE.md` (se algum nome de tipo/hook/campo divergir deste prompt, o **export real da S39 prevalece** — importar o nome real, nunca recriar/duplicar).
- **Regras do projeto**: `frontend/CLAUDE.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`.

### Exemplares (arquivo:linha — abrir e seguir; exemplar > descrição)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **UI de calendário (3 colunas, dia↔grade↔stats, toggle, building filter, month nav) — exemplar canônico a espelhar** | `frontend/app/(dashboard)/_components/rent-calendar/rent-calendar-section.tsx` (container `'use client'`, `useState {year,month}`+`selectedDay`, `useBuildings()`+`Select`, `useRentCalendar`/`useToggleRentPayment`, grid `grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-4`) e os 4 sub-componentes irmãos (`rent-month-grid.tsx`, `rent-day-panel.tsx`, `rent-stats-panel.tsx`, `rent-payment-toggle.tsx`) | **Estrutura-base** do calendário combinado. O combinado **estende** o do aluguel: o painel do dia tem **duas seções** (entradas/saídas) e o toggle do dia agora paga **conta** (`usePayBill`), não aluguel. |
| **Toggle apresentacional (Radix Switch + Tooltip + `disabledReason` em PT)** | `frontend/app/(dashboard)/_components/rent-calendar/rent-payment-toggle.tsx` (props `isPaid`/`canToggle`/`isPending`/`onToggle`/`disabledReason`; `Switch checked disabled onCheckedChange`; Tooltip quando desabilitado) | Forma do toggle de pagamento de **conta** (`bill_payment_toggle`): props in / callback out, status nunca só por cor (rótulo + ícone). |
| **Parsing ISO de data pura por split (NUNCA `new Date(iso)`)** | `frontend/app/(dashboard)/_components/late-payments-alert.tsx:17-21` (`formatDate` faz `dateStr.split('-')`) | Datas `YYYY-MM-DD`/`YYYY-MM-01` exibidas via split (bug de timezone). Usar nos itens do calendário e nas colunas da tabela de contas. |
| **CRUD page canônica (`useCrudPage` + DataTable + form modal + AlertDialog de delete + export + bulk)** | `frontend/app/(dashboard)/buildings/page.tsx:42-242` (hook `useCrudPage<Building>` :47-55; colunas com ações Editar/Excluir :57-106; header :114-150; `<DataTable rowSelection>` :183-189; `<BuildingFormModal>` :191-195; 2 `<AlertDialog>` :197-239) | **Exemplar canônico** da página de Contas (`finances/bills/page.tsx`). Espelhar `useCrudPage<Bill>` + colunas + modais + delete dialog. |
| **`useCrudPage` (estado de CRUD: modal/edit/delete/bulk/export)** | `frontend/lib/hooks/use-crud-page.ts:156-311` (genérico `<T extends { id?: number }>`; `openCreateModal`/`openEditModal`/`closeModal`/`handleDelete`/`isDeleting`/`bulkOps`/`handleExport`) | Reusar **verbatim**. A página de Contas passa `deleteMutation = useDeleteBill()`. |
| **Form modal financeiro com campos condicionais + `useForm`+`zodResolver` + create/update + `toast`** | `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx:1-120` (Dialog shadcn :7-13; `useForm<…>({resolver: zodResolver, defaultValues})` :108-120; `useCreate/UpdateExpense` :99-101; selects de `usePersons`/`useBuildings`/`useExpenseCategories` :103-106; `validateExpenseRules` via `superRefine` :71-93) | **Exemplar canônico** do `bill-form-modal.tsx`: Dialog + RHF + Zod + create/update; selects de `useBuildings`/`useFinanceCategories`/`useBillingAccounts`. |
| **Linhas dinâmicas (`useFieldArray` — adicionar/remover linhas)** | `frontend/app/(dashboard)/tenants/_components/dependent-form-list.tsx:38-143` (`useFieldArray({control, name})` :39-42; `fields.map` com `field.id` :61; `append({...})` :53/133; `remove(index)` :72; empty state :46-58) | **Exemplar canônico** do editor de **linhas** do bill (`bill-line-items-field.tsx`): cada linha = `{ category_id, description, amount, is_offset }`; append/remove; sub-total derivado. |
| **Month nav + building filter (`Select`) + `is_staff` gating + `useState {year,month}`** | `frontend/app/(dashboard)/financial/daily/page.tsx:29-30` (`useAuthStore` → `isAdmin = user?.is_staff ?? false`), `:34-41` (estado `{year,month}` + prev/next), `:60` (`useBuildings`), `:63-73` (`goPrevMonth`/`goNextMonth`), `:111` (gating `{isAdmin && …}`), `:136-160` (Selects) | Modelo estrutural do header do calendário combinado: nav de mês, `Select` de prédio (valor = `building_id`), e gating de escrita por `is_staff`. |
| **`is_staff` gating (fonte do usuário)** | `frontend/store/auth-store.ts` (`user.is_staff: boolean`) lido via `useAuthStore()` (`daily/page.tsx:29`) **ou** `useCurrentUser()` em `frontend/lib/api/hooks/use-auth.ts:107` | Gating de UI de escrita: esconder botões criar/editar/excluir/pagar/suspender/deferir quando `!is_staff` (o backend `FinancialReadOnly` é a autoridade; o front só esconde). |
| **`formatCurrency` / `formatMonthYear` / `MONTH_NAMES`/`MONTH_ABBR`** | `frontend/lib/utils/formatters.ts:5` (`formatCurrency`), `:89` (`formatMonthYear` → `"Junho de 2026"` **com " de "**), `:104` (`MONTH_ABBR`), `:106` (`MONTH_NAMES`) | Moeda e rótulo de mês. **NOTA**: `formatMonthYear` produz `"Junho de 2026"` (com " de ") — asserir exatamente isso. |
| **`ROUTES` (constantes de rota) + sidebar (menu financeiro)** | `frontend/lib/utils/constants.ts:48-71` (`ROUTES`); `frontend/components/layouts/sidebar.tsx:44-57` (`financialChildren`: `{ key: ROUTES.X, label }`) e `:97-100` (item pai "Financeiro" com `children`) | Adicionar `ROUTES.FINANCES_BILLS` (e `ROUTES.FINANCES` se o calendário virar rota própria) + entrada no menu. Espelhar o formato de `financialChildren`. |
| **Teste de componente do dashboard (mock só da fronteira de dados via `vi.spyOn` no módulo de hooks; `renderWithProviders`)** | `frontend/app/(dashboard)/_components/__tests__/late-payments-alert.test.tsx:1-154` (`makeQueryResult` :10-36, `idleMutation` :38-55 com `as`-carve-out, `vi.spyOn(hooksModule, 'useX')` :67-70, `renderWithProviders`) | **Padrão a copiar** para os testes dos componentes desta sessão (mockar **só** os hooks da S39 + `useBuildings`/`useAuthStore`, nunca componentes internos/ORM/TanStack). |
| **Render de testes (providers)** | `frontend/tests/test-utils.tsx:55-78` (`renderWithProviders`/`createWrapper`) | Reusar verbatim. |
| **MSW data + handlers de `finances` (já existem da S39)** | `frontend/tests/mocks/data/finances.ts` (`createMockBill`/`createMockCombinedCalendar`/`createMockOverdueBills`/…) + `financeHandlers` em `frontend/tests/mocks/handlers.ts` | Disponíveis para os testes desta sessão; **não** recriar (DRY). Se um teste optar por integração via MSW (em vez de `vi.spyOn`), usar `server.use(...)` por teste. |

### Contrato de dados consumido (definido pela Sessão 39 — NÃO redefinir, NÃO derivar)

Importar **tipos e hooks** de `@/lib/schemas/finances/*` e `@/lib/api/hooks/*` (nomes reais da S39 — verbatim do handoff dela):

- **Schemas/tipos**: `Bill`/`BillLineItem` (+ enums `BillBehavior` `'one_time'|'recurring'|'installment'`, `BillLifecycleState` `'active'|'suspended'|'deferred'|'canceled'`, `PaymentStatus` `'open'|'partial'|'paid'`), `BillingAccount` (+ `BillingAccountState` `'active'|'suspended'|'deferred'|'ended'`), `Payment`/`PaymentAllocation` (+ `FundedFrom` `'caixa'|'reserve'`), `FinanceCategory`, `BillSkip`. **Dinheiro CRUD = `number`** (já transformado no schema); **dinheiro de dashboard = `string`** (converter na UI via `formatCurrency`).
- **Hooks CRUD**: `useBillingAccounts`/`useBillingAccount`/`useCreate|Update|DeleteBillingAccount`; `useBills`/`useBill`/`useCreateBillWithLines`/`useUpdate|DeleteBill`; `usePayments`/…; `useFinanceCategories`+CRUD; `useBillSkips`/`useCreate|DeleteBillSkip`.
- **Hook de calendário/atrasados**: `useCombinedCalendar(year, month, buildingId?)` (`placeholderData: keepPreviousData`) → `data.days[].rent_entries` (entradas, tipo `RentCalendarItem` reusado de `use-rent-calendar`) **+** `data.days[].bill_exits` (saídas) **+** `data.stats`; `useOverdueBills(buildingId?)` → lista de atrasados + KPI `overdue_total` (`Σ amount_remaining`, string Decimal; deferred/suspended fora — §4.4).
- **Mutations otimistas/ações** (flip/rollback/invalidate JÁ no hook — a S40 **não** reimplementa): `usePayBill().mutate({ bill_id, payment_date, amount?, funded_from? })` (otimista, mesmo contrato de `useToggleRentPayment`); `useGenerateMonthBills().mutate({ year, month })`; `useSuspendBill`/`useDeferBill`/`useCancelBill`/`useReactivateBill` (`.mutate(billId)`); `useCreateBillWithLines().mutate(payload)`.

> **NOTA crítica**: a invalidação/optimismo de `usePayBill` está **dentro do hook da S39**. A UI só chama `.mutate(...)` e trata `toast`/`handleError`. **Não** duplicar `invalidateQueries` aqui (DRY, design §11). O `combined_calendar` é **sem-cache no backend**; o hook usa `staleTime` 30s — a UI **não** precisa de lógica de cache.

---

## Escopo

### Arquivos a criar

**Calendário combinado (dashboard)** — `frontend/app/(dashboard)/_components/finance-calendar/`
- `combined-calendar-section.tsx` — container `'use client'` (único que chama hooks): `useState {year,month}`+`selectedDay`, `useBuildings`+`Select`, `useCombinedCalendar`, `usePayBill`, `useAuthStore` (gating); grid 3 colunas.
- `combined-month-grid.tsx` — grade do mês (date-fns), chips de entrada **e** saída por dia.
- `combined-day-panel.tsx` — painel do dia com **duas seções**: *Aluguéis (entradas)* (read-only, lista de `rent_entries`) e *Contas a pagar (saídas)* (lista de `bill_exits` + `BillPaymentToggle` por item).
- `bill-payment-toggle.tsx` — apresentacional (Radix Switch + Tooltip), props `paymentStatus`/`canPay`/`isPending`/`onPay`/`disabledReason`.
- `combined-calendar-section.test.tsx`, `combined-day-panel.test.tsx`, `combined-month-grid.test.tsx`, `bill-payment-toggle.test.tsx` (em `__tests__/`).

**Página de Contas (CRUD)** — `frontend/app/(dashboard)/finances/bills/`
- `page.tsx` — `useCrudPage<Bill>` + `DataTable` + header (criar/exportar/gerar mês) + AlertDialog de delete + montagem do form modal e do diálogo de pagamento.
- `_components/bill-columns.tsx` — definição de colunas (descrição, prédio, competência, vencimento, `amount_total`, `amount_remaining`, status, `is_overdue`, ações: editar/pagar/suspender/deferir/excluir, gated por `is_staff`).
- `_components/bill-form-modal.tsx` — Dialog + RHF + Zod; cria via `useCreateBillWithLines`, edita via `useUpdateBill`; embute o editor de linhas.
- `_components/bill-line-items-field.tsx` — `useFieldArray` de linhas (`category_id`/`description`/`amount`/`is_offset`); sub-total derivado (§4.1: offset positivo + subtraído).
- `_components/bill-payment-dialog.tsx` — diálogo de pagamento (valor parcial opcional + `funded_from` caixa/reserva); chama `usePayBill`.
- `_components/bill-status-actions.tsx` — botões/itens suspender/deferir/cancelar/reativar (chamam os hooks de status).
- `__tests__/bill-form-modal.test.tsx`, `__tests__/bill-line-items-field.test.tsx`, `__tests__/bill-payment-dialog.test.tsx`, `__tests__/bills-page.test.tsx` (gating + ações).

### Arquivos a modificar
- `frontend/lib/utils/constants.ts` — adicionar a `ROUTES`: `FINANCES_BILLS: '/finances/bills'` (e, se o calendário combinado for rota própria além de seção do dashboard, `FINANCES: '/finances'`). **Não** alterar rotas existentes (legado `/financial/...` intacto — coexistência, design §1).
- `frontend/components/layouts/sidebar.tsx` — adicionar a entrada de menu de Contas (espelhando `financialChildren:44-57`). **Decisão**: criar um **novo grupo "Condomínio"** (não misturar com o "Financeiro" legado) com o item "Contas" → `ROUTES.FINANCES_BILLS`. Não tocar nos itens existentes.
- `frontend/app/(dashboard)/page.tsx` — montar `<CombinedCalendarSection />` no dashboard. **Decisão de posicionamento (anotar no handoff)**: montar **abaixo** do `<RentCalendarSection />` existente (o calendário de aluguel é entrada-only; o combinado adiciona as saídas) — **não** remover nem duplicar o `RentCalendarSection` (são telas distintas até a consolidação futura; design §11/§15 "não wirar os dois calendários legados", mas o combinado é o novo SSOT visual de entradas+saídas). Se o combinado já cobrir entradas+saídas, **comentar no handoff** que a remoção do `RentCalendarSection` é decisão de produto fora desta sessão (YAGNI; não remover agora).

### NÃO fazer (pertence a outras sessões)
- **Sem KPIs de dinheiro** (Caixa / Reserva / Resultado do mês / Saldo total) nem cards de saldo — **Fase 4** (S44–S46). O `combined-calendar` pode exibir `stats` que a S38 já devolve (recebido/a pagar/atrasado do mês), **mas não** computar saldo/caixa/reserva nem montar `StatCard` de saldo. (DEPENDENCY ORDER 44 → 45 → 46.)
- **Sem projeção/simulação** (tabela 12 meses, `ComposedChart`, simulador) — **Fase 5** (S47–S48).
- **Sem distribuição por proprietário** (cards "por proprietário", seção de externos Tiago/Alvaro) — **Fase 6** (S49–S50).
- **Sem donut por categoria** (Recharts `PieChart`) — é parte do dashboard de saldo (Fase 4); **não** criar aqui. (Se desejado como polish, fica para a fase 4 — YAGNI agora.)
- **Sem UI de Parcelas/Folha/Funcionários** (`InstallmentPlan`/`Installment`/`Employee`) — **Fase 3** (S41–S44). O `bill-form-modal` cria contas avulsas/recorrentes com linhas; a linha **pode** referenciar uma parcela embutida apenas se a S39 já expôs o campo, mas **não** criar UI de plano de parcelas aqui.
- **Sem hooks/schemas/query-keys/MSW novos** — tudo vem da S39. Se um hook necessário não existir, **PARE** e registre a lacuna (não criar camada de dados aqui — é a S39).
- **Sem alterar** `use-rent-calendar.ts`, `rent-calendar/*`, `late-payments-alert.tsx`, nem schemas/hooks/páginas do **módulo legado** (`expenses`, `daily`, etc.) — coexistência (design §1; §11/§15 "não wirar os dois").
- **Sem mexer** em `client.ts`, `test-utils.tsx`, `query-client.ts`, `query-keys.ts`, `handlers.ts`, `tests/mocks/data/finances.ts` — só **consumir**.

---

## Especificação

Direção de dados (`frontend/CLAUDE.md` + `.claude/rules/architecture.md` Frontend Layers): **só os containers** (`combined-calendar-section.tsx`, `bills/page.tsx`, e os modais que disparam mutations) consomem hooks. Os demais componentes são **puros** (props in, callbacks out). **Nenhum componente chama `apiClient`/axios diretamente.** Forms = React Hook Form + Zod (nunca Ant Design Form). Moeda via `formatCurrency`; datas puras por **split** (nunca `new Date(iso)`). Mensagens ao usuário em **PT**; identificadores/tipos em **EN**.

### Tokens de status (light + dark) — semânticos, status nunca só por cor (acessibilidade)
Reusar os tokens já usados no `rent-calendar`/`late-payments-alert`/`daily-timeline` (sempre **rótulo + ícone**):
- **Pago** (`payment_status='paid'`) → `text-success`/`bg-success/10` + `Check`/`CheckCircle2` + "Pago".
- **Parcial** (`payment_status='partial'`) → âmbar `text-amber-600 dark:text-amber-400` + ícone + "Parcial · resta {formatCurrency(amount_remaining)}".
- **Em aberto / a vencer** (`payment_status='open'`, `is_overdue=false`) → neutro/âmbar + "Em aberto".
- **Em atraso** (`is_overdue=true`, §4.4) → `text-destructive`/`bg-destructive/10` + `AlertTriangle` + "Em atraso".
- **Suspensa/Adiada/Cancelada** (`lifecycle_state ∈ {suspended,deferred,canceled}`) → `text-muted-foreground` + ícone (`PauseCircle`/`CalendarClock`/`Ban`) + rótulo PT; **fora** do cômputo de atraso (§4.4 — deferido/suspenso excluídos).

### `bill-payment-toggle.tsx` (apresentacional)
```ts
interface BillPaymentToggleProps {
  paymentStatus: 'open' | 'partial' | 'paid';
  canPay: boolean;          // false quando lifecycle != 'active' OU mês fechado (a S40 só sabe lifecycle; mês fechado é Fase 4 → tratar canPay=false só por lifecycle/já-pago)
  isPending: boolean;
  onPay: () => void;        // abre o bill-payment-dialog (pagamento total/parcial), NÃO paga direto
  disabledReason?: string;  // PT, ex.: "Conta suspensa — reative para pagar"
}
```
- `Switch checked={paymentStatus==='paid'} disabled={!canPay || isPending || paymentStatus==='paid'} onCheckedChange={() => onPay()}`. **Decisão (KISS)**: o toggle do calendário **abre o diálogo de pagamento** (`onPay`) em vez de pagar o total direto — porque pagamento parcial/`funded_from` exigem input. Para pagamento rápido, o diálogo já vem com "valor = total restante" e `funded_from='caixa'` pré-preenchidos (1 clique a mais, mas explícito). Documentar essa escolha no código.
- `!canPay` → envolver em Tooltip com `disabledReason` (PT). Status com rótulo + ícone (nunca só cor).

### `bill-payment-dialog.tsx` (consome `usePayBill`)
- Campos: `amount` (opcional — vazio = pagar total restante; design §8 "amount omitido = total"), `funded_from` (`Select` caixa/reserva, default `'caixa'`), `payment_date` (default hoje, `formatDateISO(new Date())`).
- `funded_from='reserve'` → exibir aviso informativo "Pagamento sairá da reserva" (a **guarda de saldo é backend** — §4.3; o front **não** simula saldo da reserva, design §18 "o hook só envia o campo; a guarda de saldo é backend"). Em erro do backend (reserva insuficiente) → `handleError(error, 'Erro ao pagar conta')`.
- Submit → `usePayBill().mutate({ bill_id, payment_date, amount?, funded_from })` (ou `mutateAsync`); sucesso → `toast.success(result.message)` (mensagem PT do backend) + fechar; o flip/rollback/invalidate **já está no hook** (S39) — **não** reimplementar.
- **Pagamento parcial conservador** (design §39 nota): o otimismo do hook reflete "pago" só quando `amount` omitido/≥remaining; parcial reconcilia no `onSettled`. A UI **não** simula aritmética de parcial — exibe o que o servidor retorna.

### `bill-line-items-field.tsx` (`useFieldArray` — §4.1)
- `useFieldArray({ control, name: 'line_items' })`; cada linha: `category_id` (`Select` de `useFinanceCategories`), `description` (`Input`), `amount` (`Input` numérico ≥ 0), `is_offset` (`Switch` "Abatimento").
- **Sub-total derivado (display-only)**: `amount_total = Σ(linhas não-offset) − Σ(linhas offset)` (§4.1 — offset armazenado **positivo** e **subtraído**). Calcular **na UI só para exibição** (helper puro local; o backend é a autoridade — `create_with_lines` recomputa). Exibir o sub-total formatado abaixo da lista.
- **Validação Zod**: cada `amount >= 0` (CheckConstraint do backend — §4.1); pelo menos 1 linha; mensagens PT. `append`/`remove` como em `dependent-form-list.tsx:53,72,133`; empty state PT ("Nenhuma linha — adicione consumo e/ou parcela").
- **NÃO** permitir `amount` negativo na UI (abatimento usa `is_offset=true` com valor **positivo**, §4.1) — se o usuário digitar negativo, Zod barra com mensagem PT.

### `bill-form-modal.tsx`
- Dialog (shadcn) + `useForm` + `zodResolver`. **Schema do form** (local, espelha `expense-form-modal.tsx:71-93`): `description` (req), `building_id` (nullable — null = nível-condomínio), `category_id` (req), `competence_month` (`YYYY-MM-01`), `due_date` (`YYYY-MM-DD`), `behavior` (`Select` `BillBehavior`; default `'one_time'`), `external_identifier`/`issue_date`/`notes` (opcionais), `line_items` (≥1, via `bill-line-items-field`).
- **Create** → `useCreateBillWithLines().mutate({ ...campos, line_items })` (design §8 — orquestrado no serviço/endpoint dedicado, **não** via serializer nested writable). **Edit** → `useUpdateBill()` (campos do bill; edição de linhas pode ficar como "recriar via novo bill" se a S38 não expôs `bills/{id}/lines` — **verificar o contrato real da S39/S38**; se `create_with_lines` for o único caminho de linhas, o modal de edição edita só os campos do bill e desabilita a edição de linhas com nota PT). Documentar a escolha no handoff.
- Selects de `useBuildings`/`useFinanceCategories`/`useBillingAccounts` (para `billing_account_id` quando `behavior='recurring'`). Campos condicionais por `behavior` via `watch()` (`frontend/CLAUDE.md` "conditional rendering com watch()"): `recurring` → mostra `billing_account_id`; `installment` → **fora desta sessão** (Fase 3) — esconder/desabilitar com nota.
- Sucesso → `toast.success` + `onClose`; erro → `handleError(error, 'Erro ao salvar conta')`.

### `bills/page.tsx` (CRUD)
- `useBills(filters?)` (filtros: `building_id`/`lifecycle_state`/`competence_month` — `Select`s opcionais, espelhando `daily/page.tsx:136-160`), `useDeleteBill()`, `useGenerateMonthBills()`, `useAuthStore()` → `isAdmin`.
- `useCrudPage<Bill>({ entityName: 'conta', entityNamePlural: 'contas', deleteMutation, … })` (espelha `buildings/page.tsx:47-55`).
- Colunas (`bill-columns.tsx`): Descrição · Prédio (ou "Condomínio" quando `building` null) · Competência (`formatMonthYear` do `competence_month` por split) · Vencimento (split) · Total (`formatCurrency(amount_total)`) · Resta (`formatCurrency(amount_remaining)`) · Status (chip `payment_status` + `is_overdue`) · Ações.
- **Ações gated por `isAdmin`** (esconder quando `!isAdmin`): Editar (abre modal), **Pagar** (abre `bill-payment-dialog`), **Suspender/Deferir/Cancelar/Reativar** (`bill-status-actions`, condicionais ao `lifecycle_state`), Excluir (AlertDialog → soft-delete via `useDeleteBill`).
- Header: título "Contas do Condomínio", botão **"Gerar contas do mês"** (`useGenerateMonthBills().mutate({year,month})` — gated `isAdmin`; design §8 idempotente/race-safe — o front só dispara), botão "Nova Conta" (gated), e export (`crud.handleExport`).
- Loading: skeletons (padrão `daily-timeline`); empty state PT ("Nenhuma conta cadastrada").

### `combined-day-panel.tsx` (duas seções por dia — design §5/§10)
- Recebe `rentItems: RentCalendarItem[]` (entradas, **read-only** — pagamento de aluguel é da tela de aluguel; aqui só exibe) e `billItems: CombinedCalendarBillItem[]` (saídas) do dia selecionado, `today`, `isAdmin`, callbacks `onPayBill(billId)` + `isPending`.
- Seção *Aluguéis (entradas)*: lista de `rentItems` (nome/apto/valor/status) — **sem toggle** (não pagar aluguel aqui; design §11 "calendário combinado, seções separadas").
- Seção *Contas a pagar (saídas)*: lista de `billItems` (descrição/prédio/`amount_remaining`/status); cada um com `BillPaymentToggle` (gated `isAdmin`) que chama `onPayBill(billId)` → o section abre o `bill-payment-dialog`.
- Empty states PT por seção ("Nenhum aluguel neste dia" / "Nenhuma conta a pagar neste dia").

### `combined-calendar-section.tsx` (container)
- `'use client'`. `useState {year,month}` (default mês atual) + `selectedDay`. `useBuildings`+`Select` (default "Todos os prédios" → `buildingId=undefined`). `useCombinedCalendar(year, month, buildingId)` + `usePayBill()` + `useAuthStore()` (gating). Nav de mês (prev/next) como `daily/page.tsx:63-73`.
- Layout: grid `grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-4` (espelha `rent-calendar-section`); coluna 1 = `combined-day-panel`, coluna 2 = `combined-month-grid`, coluna 3 = `stats` do mês (recebido/a pagar/atrasado — **da S38**, **sem** saldo/caixa/reserva).
- Pagamento: o toggle de uma conta abre o `bill-payment-dialog`; o `usePayBill` (otimista, S39) reconcilia calendário + atrasados — a UI **não** invalida nada.
- `placeholderData: keepPreviousData` já está no hook (S39): a nav de mês **não** pisca; **não** usar `useSuspenseQuery`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md` + memória do projeto): mockar **APENAS fronteiras externas**. Aqui = (a) os **hooks de dados da S39** (`useCombinedCalendar`/`usePayBill`/`useBills`/`useCreateBillWithLines`/`useGenerateMonthBills`/status) + `useBuildings`/`useFinanceCategories`/`useAuthStore`, via **`vi.spyOn` no módulo** (padrão `late-payments-alert.test.tsx:67-70`) **ou** a rede via **MSW** (`server.use`, usando `tests/mocks/data/finances.ts` da S39). **NUNCA** mockar componentes internos, TanStack Query, `apiClient`, ORM ou os schemas Zod. Usar `renderWithProviders` (`test-utils.tsx:55-78`).

### 1. RED — escrever os testes primeiro (devem falhar por componente inexistente)
`cd frontend && npx vitest run "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills"`

Cobrir, no mínimo:

**`bill-payment-toggle.test.tsx`**
- [ ] `paymentStatus='paid'` → Switch marcado; `'open'`/`'partial'` → desmarcado.
- [ ] `disabled` quando `canPay=false` OU `isPending=true` OU `paymentStatus='paid'`.
- [ ] `onPay` chamado ao acionar quando habilitado; **não** chamado quando desabilitado.
- [ ] desabilitado por lifecycle (ex.: suspensa) → `disabledReason` (tooltip/`aria`) em PT.
- [ ] status com **rótulo + ícone** (não só cor) — verificar texto ("Pago"/"Parcial"/"Em atraso"/"Em aberto").

**`bill-line-items-field.test.tsx`** (montar dentro de um `useForm` host de teste)
- [ ] renderiza 1 linha inicial; `append` adiciona linha; `remove` retira (contagem de inputs muda).
- [ ] **§4.1 sub-total**: linhas `[600 não-offset, 400 não-offset, 100 offset]` → sub-total exibido `formatCurrency(900)` (`1000 − 100`); um caso com offset que **mantém** `amount_total >= 0` (ex.: `[100, 100 offset]` → `0`).
- [ ] `amount` negativo → Zod barra com mensagem PT (abatimento usa `is_offset`, valor positivo).
- [ ] empty state PT quando 0 linhas (se permitido remover todas) **ou** impede remover a última (escolher 1 comportamento e travar com teste).

**`bill-payment-dialog.test.tsx`** (mock do boundary `usePayBill` via `vi.spyOn`)
- [ ] submit sem `amount` → `mutate` chamado **sem** `amount` (pagamento total); `funded_from` default `'caixa'`.
- [ ] `amount` parcial preenchido → `mutate({ bill_id, payment_date, amount, funded_from:'caixa' })`.
- [ ] `funded_from='reserve'` selecionado → body inclui `funded_from:'reserve'` + aviso "sairá da reserva" visível (**§18 reserva**: front só envia o campo, guarda é backend).
- [ ] sucesso → `toast.success(result.message)` + `onClose` chamado; erro (mutation rejeita) → `handleError` (toast de erro).
- [ ] a UI **não** chama `invalidateQueries` (a invalidação é do hook S39) — verificar que o componente não importa `useQueryClient`.

**`bill-form-modal.test.tsx`**
- [ ] modo create: preencher campos + ≥1 linha → submit chama `useCreateBillWithLines().mutate` com `{ description, building_id, category_id, competence_month, due_date, behavior, line_items }`.
- [ ] `behavior='recurring'` (via `watch`) → mostra `Select` de `billing_account_id`; `behavior='one_time'` → esconde.
- [ ] `behavior='installment'` → bloqueado/escondido com nota PT (Fase 3 fora desta sessão).
- [ ] validação: sem descrição/sem linhas → mensagens PT, `mutate` **não** chamado.
- [ ] modo edit: campos pré-preenchidos do `bill`; submit chama `useUpdateBill` (linhas conforme decisão documentada — editáveis ou nota PT).

**`bills-page.test.tsx`** (mock dos hooks da S39 + `useAuthStore`)
- [ ] `isAdmin=false` → botões "Nova Conta"/"Gerar contas do mês"/Editar/Pagar/Suspender/Deferir/Excluir **ausentes** (gating de escrita; `FinancialReadOnly` é a autoridade backend). Tabela ainda renderiza (leitura).
- [ ] `isAdmin=true` → ações presentes; "Gerar contas do mês" chama `useGenerateMonthBills().mutate({year,month})`.
- [ ] coluna Competência usa **split** (não `new Date`) e exibe `formatMonthYear` (ex.: "Junho de 2026"); coluna Total/Resta via `formatCurrency`; prédio null → "Condomínio".
- [ ] chip de status reflete `payment_status`+`is_overdue` (rótulo + ícone); **§4.4** bill `deferred`/`suspended` → chip de lifecycle, **não** "Em atraso".
- [ ] loading → skeleton; empty → estado vazio PT.

**`combined-day-panel.test.tsx`**
- [ ] renderiza seção *Aluguéis (entradas)* com `rentItems` (read-only, **sem** toggle) e seção *Contas a pagar (saídas)* com `billItems` + toggle.
- [ ] `onPayBill(billId)` chamado ao acionar o toggle de uma conta (quando `isAdmin`); ausente quando `!isAdmin`.
- [ ] empty states PT por seção (sem aluguel / sem conta).
- [ ] datas/valores formatados (split + `formatCurrency`).

**`combined-month-grid.test.tsx`**
- [ ] nº correto de células para um mês conhecido (junho/2026 = 30) com offset do 1º dia (date-fns `startOfMonth`/`getDay`/`getDaysInMonth`).
- [ ] dia com `bill_exits` e/ou `rent_entries` mostra chips (texto presente, cor por status — entrada vs saída distinguíveis por rótulo/ícone, não só cor).
- [ ] clique numa célula chama `onSelectDay(day)`; hoje/selecionado destacados (via rótulo/elemento, não cor pura).

**`combined-calendar-section.test.tsx`** (mock dos hooks da S39 + `useBuildings`/`useAuthStore` via `vi.spyOn`)
- [ ] loading → skeleton; com dados → renderiza painel do dia + grade + stats (1 asserção por coluna).
- [ ] nav de mês muda `{year,month}` passados ao `useCombinedCalendar` (verificar args do spy); `placeholderData` é responsabilidade do hook (não asserir cache aqui).
- [ ] filtro de prédio: selecionar prédio passa `building_id` ao `useCombinedCalendar`.
- [ ] toggle de uma conta abre o `bill-payment-dialog` (o `usePayBill` é chamado a partir do diálogo, não do toggle direto); **§18**: a UI não invalida nada (sem `useQueryClient` no section além do que os hooks usam internamente).

> Rodar (devem **falhar**):
> ```bash
> cd frontend
> npx vitest run "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills"
> ```

### 2. GREEN — implementar componentes + páginas + montagem (mínimo para passar)
1. Calendário combinado: 4 componentes em `_components/finance-calendar/` (espelhar `rent-calendar/*`; o painel do dia ganha 2 seções; o toggle paga conta via diálogo).
2. Página de Contas: `page.tsx` (`useCrudPage<Bill>`) + 5 componentes em `finances/bills/_components/` (espelhar `buildings/page.tsx` + `expense-form-modal.tsx` + `dependent-form-list.tsx`).
3. `ROUTES.FINANCES_BILLS` (+ `FINANCES` se aplicável) em `constants.ts`; entrada no `sidebar.tsx` (grupo "Condomínio"); `<CombinedCalendarSection />` em `page.tsx`.
4. Reusar os hooks/tipos da S39 (`import` direto da fonte; **sem** redefinir tipos, **sem** re-export). `RentCalendarItem` importado de `use-rent-calendar` via `import type` (o tipo de entradas é o mesmo).

Rodar até verde:
```bash
cd frontend
npx vitest run "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Extrair `StatusChip` (chip de `payment_status`+`is_overdue`+lifecycle) **uma vez** e reusar no calendário e na tabela (DRY — fonte única do mapeamento status→rótulo/ícone/cor). Se o `rent-calendar` já tiver um chip equivalente para entradas, **não** acoplar (entradas vs saídas têm semânticas distintas) — extrair o de saída/conta como componente próprio pequeno.
- Helper puro de sub-total de linhas (`computeLineTotal(lines): number` — §4.1) num único módulo, reusado pelo `bill-line-items-field` e (se exibir total na tabela) pela coluna. **Não** recalcular `amount_total` para dados que vêm do backend (ler a annotation — §4.4); o helper de UI é só para o **form em edição** (preview antes de salvar).
- Sub-componentes pequenos (`DayCell`, `BillRow`, `RentRow`) com responsabilidade única; sem comentários supérfluos; sem código especulativo (YAGNI).

### 4. VERIFY — gate frontend (escopo desta sessão)
```bash
cd frontend
npx vitest run "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills"
npx tsc --noEmit
npx eslint "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills" "app/(dashboard)/page.tsx" "components/layouts/sidebar.tsx" "lib/utils/constants.ts"
```
Zero erros e zero avisos em todos.

---

## Constraints

- **Camada de UI só** (`.claude/rules/architecture.md` Frontend Layers): páginas/componentes consomem hooks da S39; **só** os containers e os modais que disparam mutations chamam hooks. **Nenhum** componente chama `apiClient`/axios. **Não** criar hooks/schemas/query-keys/MSW (S39).
- **TanStack Query v5**: usar os hooks da S39 (que já fazem `useQuery`+`placeholderData: keepPreviousData` e mutations otimistas). A UI **não** reimplementa optimismo/invalidação (DRY — `usePayBill` já faz; design §11). **Não** usar `useSuspenseQuery`.
- **Decimal**: CRUD = `number` (já transformado pela S39); dashboard = `string` (converter só na exibição via `formatCurrency`). O front **nunca** recalcula `amount_total` de dados do backend (lê a annotation — §4.4); o helper de sub-total é **só** preview do form.
- **Datas puras** `YYYY-MM-DD`/`YYYY-MM-01` formatadas por **split** (`late-payments-alert.tsx:17-21`), **nunca** `new Date(iso)` (bug de timezone). Grade do mês via `date-fns` (já no repo) — **não** instalar dependência.
- **`is_offset` (§4.1)**: na UI, abatimento = valor **positivo** + flag `is_offset=true`; sub-total = `Σ não-offset − Σ offset`; Zod barra `amount < 0`. O backend é a autoridade (`create_with_lines`); a UI só faz preview.
- **`is_staff` gating**: esconder toda UI de escrita (criar/editar/excluir/pagar/suspender/deferir/gerar mês) quando `!user.is_staff` (`useAuthStore`/`useCurrentUser`). O backend `FinancialReadOnly` é a autoridade — o front só esconde (`.claude/rules/security.md`).
- **Status nunca só por cor** — sempre rótulo + ícone (acessibilidade). Dark mode via `next-themes` (tokens semânticos `.dark`) — **não** adicionar toggle de tema.
- **`as`/`!` proibidos em produção** (regra do projeto + memória): componentes/páginas sem `as`/non-null — corrigir o tipo na raiz (`import type`, `??`, null guards, `noUncheckedIndexedAccess`).
- **CARVE-OUT (somente fixtures de teste)**: nos `*.test.tsx`, ao construir o objeto de retorno de um hook de query/mutation do TanStack (shape inviável sem assertion), É PERMITIDO `as <Result>` / `as unknown as <Mutation>` **restrito** aos helpers de fixture (`makeQueryResult`/`idleMutation`), **exatamente** como `late-payments-alert.test.tsx:35,55`. Em qualquer outro lugar (testes ou produção), `as`/`!` proibidos.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o código. TypeScript strict + `noUncheckedIndexedAccess`.
- **Sem `from __future__`/`TYPE_CHECKING`** (irrelevante no FE) e **sem re-export / barrel files / shims**: importar tipos/hooks **direto da fonte** (`@/lib/api/hooks/*`, `@/lib/schemas/finances/*`). `RentCalendarItem` via `import type` de `use-rent-calendar`.
- **Sem deps novas** — Shadcn/Radix, lucide, sonner, RHF, Zod, date-fns, TanStack já no repo. **Não** instalar nada (sem Recharts aqui — donut/charts são Fase 4/5).
- **Escopo de fases**: **sem** KPIs de saldo/caixa/reserva (Fase 4), **sem** projeção/simulação (Fase 5), **sem** distribuição/owner (Fase 6), **sem** UI de parcelas/folha (Fase 3), **sem** donut por categoria.
- **Coexistência**: **não** alterar/remover `rent-calendar/*`, `late-payments-alert.tsx`, nem o módulo legado (`expenses`/`daily`) — design §1/§11/§15 (não wirar os dois calendários).
- **SOLID/DRY/KISS/YAGNI**: componentes pequenos de responsabilidade única; chip de status e sub-total extraídos uma vez; sem código especulativo.
- **Não rodar a suíte completa** — só os arquivos desta sessão (xdist/Redis pré-existentes; memória do projeto).

---

## Critérios de Aceite (binários)

- [ ] Calendário combinado: 4 componentes em `frontend/app/(dashboard)/_components/finance-calendar/` (`combined-calendar-section` container + `combined-month-grid` + `combined-day-panel` com **duas seções** entradas/saídas + `bill-payment-toggle`), `'use client'` onde necessário; grid `grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-4`, empilha no mobile.
- [ ] `<CombinedCalendarSection />` montado em `page.tsx` (posição documentada no handoff; `RentCalendarSection` **não** removido).
- [ ] `combined-month-grid` usa `date-fns` (`startOfMonth`/`getDay`/`getDaysInMonth`) — grade custom, sem dependência nova; chips de entrada **e** saída distinguíveis por rótulo/ícone (não só cor).
- [ ] Página de Contas em `frontend/app/(dashboard)/finances/bills/`: `page.tsx` com `useCrudPage<Bill>` + `DataTable` + AlertDialog de delete; 5 componentes (`bill-columns`, `bill-form-modal`, `bill-line-items-field`, `bill-payment-dialog`, `bill-status-actions`).
- [ ] `bill-form-modal` usa RHF+Zod, cria via `useCreateBillWithLines` (linhas embutidas) e edita via `useUpdateBill`; campos condicionais por `behavior` via `watch()`; `installment` bloqueado/escondido (Fase 3) com nota PT.
- [ ] `bill-line-items-field` usa `useFieldArray` (append/remove); sub-total `Σ não-offset − Σ offset` (§4.1) exibido; `amount < 0` barrado por Zod (PT); abatimento = valor positivo + `is_offset`.
- [ ] `bill-payment-dialog` chama `usePayBill().mutate({ bill_id, payment_date, amount?, funded_from })`; `amount` vazio = total; `funded_from` caixa/reserva (default caixa) com aviso de reserva; **não** invalida queries (hook S39 faz); sucesso → toast PT, erro → `handleError`.
- [ ] Toda UI de escrita (criar/editar/excluir/pagar/suspender/deferir/gerar mês) **gated por `is_staff`** (`useAuthStore`/`useCurrentUser`); leitura sempre visível.
- [ ] Atrasado/lifecycle (§4.4): `deferred`/`suspended` exibem chip de lifecycle, **não** "Em atraso"; status sempre rótulo + ícone.
- [ ] Datas puras por **split** (sem `new Date(iso)`); moeda via `formatCurrency`; competência via `formatMonthYear` (ex.: "Junho de 2026", com " de "); prédio null → "Condomínio".
- [ ] `ROUTES.FINANCES_BILLS` adicionado em `constants.ts`; entrada de menu no `sidebar.tsx` (grupo "Condomínio") espelhando `financialChildren`; rotas/menu legados intactos.
- [ ] Componentes (exceto containers/modais com mutation) são **puros** (props/callbacks, sem API); nenhum chama `apiClient`/axios.
- [ ] Nenhum hook/schema/query-key/MSW novo; `use-rent-calendar.ts`/`rent-calendar/*`/`late-payments-alert.tsx`/módulo legado **intactos**; sem KPIs de saldo/projeção/distribuição/donut/parcelas/folha.
- [ ] `npx vitest run` (os arquivos desta sessão) 100% verde.
- [ ] `npx tsc --noEmit` limpo; `npx eslint` (todos os arquivos tocados) zero erros/zero avisos — **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção (único `as` = carve-out de fixture de teste).
- [ ] Sem re-exports/barrel; sem dependência nova; `RentCalendarItem` importado (não redefinido) via `import type`.

---

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão — colar saída como evidência):
   ```bash
   cd frontend
   npx vitest run "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills"
   npx tsc --noEmit
   npx eslint "app/(dashboard)/_components/finance-calendar" "app/(dashboard)/finances/bills" "app/(dashboard)/page.tsx" "components/layouts/sidebar.tsx" "lib/utils/constants.ts"
   ```
2. Atualizar `prompts/SESSION_STATE.md` (**NÃO** editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 40 (status **concluída**) na tabela de progresso da feature Condomínio Finance.
   - Listar **Arquivos Criados** (4 componentes de calendário + 5 testes; `bills/page.tsx` + 5 componentes + 4 testes) e **Modificados** (`constants.ts` `ROUTES.FINANCES_BILLS`, `sidebar.tsx` grupo "Condomínio", `page.tsx` montagem do `<CombinedCalendarSection />`).
   - **Documentar as decisões**: posição do `<CombinedCalendarSection />` (e que `RentCalendarSection` permanece); edição de linhas no `bill-form-modal` (editável vs nota PT, conforme o contrato real S38/S39); toggle do calendário abre diálogo (não paga direto).
   - **Anotar divergências** se algum nome de hook/tipo/campo da S39 diferir deste prompt (qual, como foi consumido).
   - **Anotar os contratos cross-session** (verbatim, ver abaixo) para a Fase 4 (S44+) consumir sem derivar.
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch se necessário — ex.: `feat/condo-finance`):
   ```
   feat(finances): add combined calendar + bills CRUD page + payment UI (phase 2 frontend)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **41 — Backend Fase 3 (Parcelas + Folha)** (`InstallmentPlan`/`Installment`/`Employee`, `convert_deferred`, estende `ensure_month_bills`). A S41 **não** mexe nesta UI; quando a UI de parcelas/folha vier (S44 FE), ela **adiciona** páginas — **não** recria o calendário combinado nem a página de Contas desta sessão.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim nas fases seguintes)

- **Componentes de calendário** (`@/app/(dashboard)/_components/finance-calendar/*`): `CombinedCalendarSection` (montado no dashboard), `combined-day-panel` com seções *Aluguéis (entradas)* / *Contas a pagar (saídas)*, `bill-payment-toggle`. A Fase 4 (KPIs de saldo) **adiciona** uma coluna/linha de KPIs **acima/ao lado** do calendário — **não** recria o calendário.
- **Página de Contas** (`@/app/(dashboard)/finances/bills/page.tsx` + `_components/*`): padrão `useCrudPage<Bill>` + `bill-form-modal` (`create_with_lines`) + `bill-payment-dialog` (`usePayBill`) + `bill-status-actions`. Telas futuras (Parcelas/Folha — Fase 3 FE) seguem o **mesmo** padrão (`useCrudPage` + form modal), em `finances/installment-plans/` e `finances/employees/`.
- **`StatusChip` / `computeLineTotal`**: helpers/componentes extraídos (fonte única do mapeamento status→rótulo/ícone e do sub-total `Σ não-offset − Σ offset`, §4.1) — reusar nas próximas telas (não duplicar).
- **Rota/menu**: `ROUTES.FINANCES_BILLS = '/finances/bills'` e o grupo de menu "Condomínio" no `sidebar.tsx` — as próximas telas de `finances` registram suas rotas/itens **nesse** grupo (não no "Financeiro" legado).
- **Pagamento de conta**: a UI sempre chama `usePayBill().mutate({ bill_id, payment_date, amount?, funded_from? })` (otimismo/invalidação no hook S39); **nenhuma** tela duplica `invalidateQueries`. `funded_from='reserve'` é enviado pelo front; a **guarda de saldo da reserva é backend** (Fase 4 — a UI exibe o erro do servidor, não simula saldo).
