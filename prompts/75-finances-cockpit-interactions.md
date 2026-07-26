# Sessão 75 — Frontend: interações do cockpit (popover pagar c/ ajuste, editar inline, conta avulsa, importar na linha, CTA Parcelar)

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida — `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (rev. 2)
> **Sessões da feature**: 65 → … → 71 → 72 → 73 → 74 → **75** → 76
> Sobre a estrutura da S74 (board, seções, banner), esta sessão torna as linhas **operáveis**: (1) popover **"Pagar"** na linha (data default hoje, valor default resto; `new_total` p/ bill estimada e p/ juros/multa em confirmada — semântica S68); (2) popover de **edição inline** (vencimento → PATCH header; valor → `update_with_lines` — dinheiro vive nas linhas, NUNCA via PATCH); (3) **"+ Conta avulsa"** (form mínimo → `create_with_lines` com 1 linha); (4) **"Importar fatura"** na linha (parse-draft → warnings ANTES de aplicar → `apply_invoice`); (5) **CTA "Parcelar"** na sub-seção de dívida → `consolidate-debt-dialog` da S73 (**consome, não recria**). **Preflight do fechamento e toasts acionáveis com link são a S76.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.3 linhas operáveis, §3.5 consolidação, §4 `apply_invoice`, §8 erros — sem optimistic update)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Contratos AUTORITATIVOS S68/S69/S70/S71/S73/S75** (se este prompt divergir, ELES prevalecem): `@prompts/SESSION_STATE.md` (seção "Sessões 65–76")
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/*.md`

### Exemplares (arquivo:linha — VERIFICADOS; ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Dialog de pagamento (base da variante popover)** | `frontend/app/(dashboard)/finances/bills/_components/bill-payment-dialog.tsx` — `todayISO` :42-47; `paymentFormSchema` :49-59 (valor vazio = total); `FUNDED_FROM_LABELS` :63-66; submit :99-119 | Extrair schema/helpers p/ módulo compartilhado; popover reusa (DRY) |
| **`usePayBill` estendido (S71)** | `frontend/lib/api/hooks/use-bills.ts` (localizar pós-S71 — a S71 já removeu o optimistic por completo; ver Constraints) | S71 adiciona `new_total?` ao request; o popover envia |
| **Hook PATCH header** | `use-bills.ts:183-200` — **`useUpdateBill` hoje usa `apiClient.put`** (:195) | Contrato S75 exige **PATCH** `update_header`; ver Especificação (migrar PUT→PATCH) |
| **`useUpdateBillWithLines` / `useCreateBillWithLines`** | `use-bills.ts:169-181` / :135-144 | Valor inline e Conta avulsa |
| **`useParseInvoice` (draft, não grava)** | `use-bills.ts:151-162` | 1º passo do importar-na-linha (warnings antes de aplicar) |
| **`useApplyInvoice` (S71)** | `lib/api/hooks/` pós-S71 (FormData; POST `bills/{id}/apply_invoice/`) | 2º passo (aplica na bill alvo) |
| **Popover (JÁ usado no repo)** | `frontend/components/ui/popover.tsx:1-31`; consumidores: `app/(dashboard)/leases/_components/late-fee-modal.tsx:19`, `lease-form-modal.tsx:41`, `tenants/_components/tenant-lease-modal.tsx:36` | Edição inline = Popover dentro do `render` da célula — **NÃO estender `DataTable`** (`data-table.tsx:56-72` não tem `onRowClick` e assim fica) |
| **Builder de colunas (pós-S74)** | `bills/_components/bill-columns.tsx` (dropdown de ações :97-133; item Pagar :115-121) | Onde os popovers/itens novos entram |
| **Dialog de consolidação (S73 — consumir)** | `app/(dashboard)/finances/accounts/[id]/_components/consolidate-debt-dialog.tsx` (verificar path/props reais pós-S73) | CTA "Parcelar" abre este dialog — não recriar |
| **Página pós-S74** | `bills/page.tsx` (board, `OverdueSection`, modais) | Call-sites dos novos estados/dialogs |
| **Teste de página MSW (spies de body)** | `bills/__tests__/bills-page-import.test.tsx:77-106` (spy por captura de request-body; `uploadPdf` :101-106) | Padrão dos testes desta sessão |
| **Money → number no parse** | `lib/schemas/finances/money.ts:4` | Aritmética de `new_total` no front usa numbers do `Bill` parseado |

### O que as sessões anteriores entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S68 (BE)**: `pay` aceita `new_total` (decimal string) — na MESMA transação: bill **estimada** → ajusta a linha-semente (única linha sem FK `installment`) para `new_total`; bill **não-estimada** com `new_total >` total → adiciona linha `"Juros/multa"` com a diferença; `new_total <` total em não-estimada → 400 ("Edite a conta para reduzir o valor."); `new_total` em bill não-estimada com >1 linha não-parcela → 400. `bulk_pay` NÃO aceita ajuste.
- **S69 (BE)**: `POST bills/{id}/apply_invoice` (multipart) — parseia e aplica na bill alvo via `update_with_lines` + limpa `amount_is_estimated`; substitui apenas linhas sem FK `installment`; 400 se conta divergente/null, competência divergente, bill paga/parcial, mês fechado, PDF não parseável. O draft do `parse_invoice` (S60/S69) inclui `matched_account.building_id` + warning de divergência de prédio.
- **S70 (BE)** + **S73 (FE)**: `consolidate_debt` + `consolidate-debt-dialog.tsx` (multi-select de bills em aberto da conta, campos do plano, chama `useConsolidateDebt`) — reutilizável pelo cockpit.
- **S71 (FE)**: `usePayBill` estendido (`new_total?`), `useApplyInvoice()` (FormData), `useConsolidateDebt()` — todos invalidando `invalidateFinanceMoneyCaches` + `monthBoard` + `billingAccounts`.
- **S74 (FE)**: board, `OverdueSection` (ponto do CTA Parcelar), `GenerateMissingBanner`, badges.

> **Se S71/S73/S74 não estiverem concluídas, PARE.**

---

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/finances/bills/_components/bill-payment-form.ts` — extração compartilhada: `paymentFormSchema`, `todayISO`, `FUNDED_FROM_LABELS` (movidos de `bill-payment-dialog.tsx`; dialog passa a importar daqui — refatoração completa, sem duplicar).
- `frontend/app/(dashboard)/finances/bills/_components/bill-pay-popover.tsx` — `BillPayPopover` (popover "Pagar" na linha, com lógica de `new_total`).
- `frontend/app/(dashboard)/finances/bills/_components/bill-inline-edit.tsx` — `DueDatePopover` + `AmountPopover` (edição inline nas células).
- `frontend/app/(dashboard)/finances/bills/_components/quick-bill-dialog.tsx` — `QuickBillDialog` ("+ Conta avulsa").
- `frontend/app/(dashboard)/finances/bills/_components/apply-invoice-dialog.tsx` — `ApplyInvoiceDialog` (resumo do draft + warnings + confirmação).
- Testes: `_components/__tests__/bill-pay-popover.test.tsx`, `__tests__/bill-inline-edit.test.tsx`, `__tests__/quick-bill-dialog.test.tsx`, `__tests__/apply-invoice-dialog.test.tsx`, `bills/__tests__/bills-page-interactions.test.tsx`.

### Arquivos a modificar
- `frontend/lib/api/hooks/use-bills.ts` — **migrar `useUpdateBill` de PUT para PATCH** (`apiClient.patch`, :195) — o backend roteia `partial_update` por `BillService.update_header` guardado (contrato S65); atualizar TODOS os handlers MSW/testes que registram `http.put` de bills (refactor completo, sem shim).
- `frontend/app/(dashboard)/finances/bills/_components/bill-columns.tsx` — coluna Ações: "Pagar" vira `BillPayPopover` na linha (sai do dropdown); células Vencimento/Total ganham popover de edição inline (admin); item "Importar fatura" no dropdown quando elegível.
- `frontend/app/(dashboard)/finances/bills/_components/overdue-section.tsx` — CTA "Parcelar" por linha da sub-seção de dívida (quando a bill tem `billing_account`).
- `frontend/app/(dashboard)/finances/bills/page.tsx` — botão "+ Conta avulsa" no header; estados dos novos dialogs; wiring do `consolidate-debt-dialog` (S73).
- `frontend/app/(dashboard)/finances/bills/_components/bill-payment-dialog.tsx` — importar schema/helpers do módulo extraído (comportamento inalterado).
- `tests/mocks/handlers.ts` — PATCH de bills + `apply_invoice` (action junto de `pay`, ANTES das rotas `:id` — regra `handlers.ts:2245-2248`), se a S71 não tiver criado.

### NÃO fazer (pertence a outras sessões)
- **Preflight do fechamento / toasts acionáveis com link para month-close** — **S76**. Aqui, erros de mutação usam `handleError`/`toast.error` com a mensagem PT do backend.
- **Não recriar** `consolidate-debt-dialog` (S73), `useApplyInvoice`/`useConsolidateDebt`/`usePayBill` estendido (S71), nem qualquer backend.
- **Nada da Fase 2** (terceiros); **não** estender `DataTable`; **não** mexer no fluxo avulso "Importar fatura (PDF)" do header (permanece para faturas sem bill gerada).

---

## Especificação

### `BillPayPopover` — pagar em 1 clique (contrato S68 verbatim)

- Trigger: botão "Pagar" na célula de ações (visível p/ admin, `lifecycle_state === 'active'` e `payment_status !== 'paid'`). `PopoverContent` com RHF+Zod reusando `paymentFormSchema` + `todayISO` do módulo extraído; defaults: `payment_date = todayISO()`, `amount = ''` (vazio = resto), `funded_from = 'caixa'`. O default `amount = ''` (vazio ⇒ paga o resto) **CUMPRE** o "valor default resto" do contrato S75 — não criar prefill numérico do resto.
- Ao submeter com `valor` numérico digitado (senão `amount` omitido = paga o resto):
  - **Bill estimada** (`amount_is_estimated`) e `valor !== resto` → `usePayBill({bill_id, payment_date, amount: valor, funded_from, new_total: valor.toFixed(2)})` — a linha-semente é ajustada ao valor real e alocada numa transação (estimada nunca tem pagamento parcial: `pay` limpa a flag, logo resto === total).
  - **Bill confirmada** e `valor > resto` → exibir checkbox **"Adicionar diferença como Juros/multa"**; marcado → enviar `new_total = (amount_total + (valor - resto)).toFixed(2)` junto de `amount: valor`; desmarcado → bloquear submit com mensagem PT ("O valor excede o restante. Marque a opção de juros/multa ou reduza o valor.") — o guard de over-allocation do backend permanece a barreira real.
  - **Bill confirmada** e `valor < resto` → pagamento parcial normal (sem `new_total`).
  - `new_total` é **SEMPRE decimal string com 2 casas** — conversão explícita `valor.toFixed(2)` (e a soma do caso juros idem); **nunca** number.
- Sucesso: `toast.success` + fechar popover; o hook invalida (`monthBoard` incluso) → refetch. Erro: `handleError(error, 'Erro ao pagar conta')`.
- O `BillPaymentDialog` existente continua acessível (fallback pelo dropdown) e passa a importar schema/helpers do módulo compartilhado.

### Edição inline (`bill-inline-edit.tsx`) — Popover no `render` da célula

- **Vencimento** (`DueDatePopover`): célula Vencimento (admin) mostra a data + ícone de edição; popover com `<Input type="date">` + Salvar → `useUpdateBill` (**PATCH**) com `{id, due_date}` apenas. NUNCA enviar campos de dinheiro no PATCH.
- **Valor** (`AmountPopover`): permitido **somente** quando a bill tem exatamente **1 linha sem `installment`** e **sem** `water_statement`/`electricity_statement` (cobre estimadas geradas e avulsas genéricas — casos de correção rápida); caso contrário a célula não abre popover (edição completa via modal "Editar"). Popover com input numérico → `useUpdateBillWithLines({bill_id, line_items: [{...linha única, amount: novoValor}]})` preservando `description`/`is_offset`/`category_id` da linha. **Dinheiro NUNCA via PATCH** — vive em `BillLineItem` (design §3.3). Nota: editar valor limpa `amount_is_estimated` no backend (S65) — o badge some após refetch.
- Ambos: mutação → invalidate → refetch (sem optimistic); erro via `handleError`.

### `QuickBillDialog` — "+ Conta avulsa"

- Botão "+ Conta avulsa" no PageHeader (admin), ao lado de "Nova Conta". Form mínimo (RHF+Zod): descrição (obrigatória), prédio (select, opcional = Condomínio), valor (obrigatório > 0), vencimento (obrigatório, default `todayISO()`), categoria (opcional).
- Submit → `useCreateBillWithLines({ bill: { description, building_id?, due_date, competence_month: '<YYYY-MM-01 do mês do board>', behavior: 'one_time', category_id? }, line_items: [{ description, amount: valor, is_offset: false, category_id? }] })` — exatamente 1 linha; `competence_month` derivado do `period` da página (prop).
- Sucesso: toast + fechar; erro: `handleError`. O modal completo "Nova Conta" permanece intocado.

### "Importar fatura" na linha → `ApplyInvoiceDialog`

- Item "Importar fatura" no dropdown da linha, visível quando `account_type ∈ {water, electricity}` **e** `amount_is_estimated` **e** `payment_status === 'open'`.
- Fluxo em 2 passos (o aviso vem ANTES de aplicar — design §8):
  1. Seleção do PDF (input file oculto, padrão `page.tsx:184-198`) → `useParseInvoice` (draft, **não grava**). Guardar `{bill, draft, file}` em estado.
  2. `ApplyInvoiceDialog` mostra resumo (conta casada, competência, vencimento, total do draft) + **`warnings` do draft em `Alert`**. **Divergência de conta = bloqueante**: se `draft.matched_account` for null ou `matched_account.id !== bill.billing_account?.id`, exibir Alert destrutivo PT e **desabilitar** Confirmar (espelho do 400 do backend — que continua sendo a barreira real). Confirmar → `useApplyInvoice({ bill_id, file })` (o backend re-parseia e aplica atomicamente).
- Sucesso: toast "Fatura aplicada" + invalidate/refetch (hook S71). Erros 400 (competência divergente, paga/parcial, mês fechado, PDF inválido): mensagem PT do backend via `handleError` (link acionável = S76). O PDF nunca é persistido no front.

### CTA "Parcelar" (sub-seção de dívida) — consome a S73

- CTA **SOMENTE** nas linhas da sub-seção de dívida adiada/suspensa (contrato S75/design §3.5) — **NÃO** estender às linhas de "Atrasadas". Em cada linha de `deferredSuspended` **com `billing_account`**: botão/ítem "Parcelar" → abre o `ConsolidateDebtDialog` da S73 com as props VERBATIM da S73: `bills: ConsolidableBill[]`, `accountId`, `accountType`, `open`/`onClose`. Linhas sem conta: sem CTA (consolidação é por conta).
- Derivação `toConsolidableBills(board, accountId)` (função pura): filtra as seções do board pelas bills da conta (`billing_account.id === accountId`), mapeia `id → bill_id`, `amount_remaining`, e `accountType` vem de `bill.billing_account.account_type`.
- O dialog cuida do multi-select/validação/mutação (`useConsolidateDebt`); esta sessão só o abre do cockpit. Sucesso invalida `monthBoard` (hook S71) → a dívida sai das seções (origens canceladas).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: MSW com spies por captura de request-body (padrão `bills-page-import.test.tsx:77-99`); **NUNCA `vi.mock`** de hooks internos.

### 1. RED

#### `__tests__/bill-pay-popover.test.tsx`
```ts
describe('BillPayPopover', () => {
  it('pays the full remainder with today as default date when amount is left empty', ...)
  // spy no POST pay: body {payment_date: hoje, funded_from:'caixa'} sem amount nem new_total.
  it('sends new_total when paying an estimated bill with a value different from the remainder', ...)
  // bill amount_is_estimated, total/resto 200, valor 230 → body com new_total: '230.00' (string exata, 2 casas — SEM aceitação dupla '230'|230).
  it('does not send new_total when an estimated bill is paid at exactly the remainder', ...)
  it('shows the juros/multa checkbox only when a confirmed bill gets a value above the remainder', ...)
  it('sends new_total = amount_total + (valor - resto) when the checkbox is checked', ...)
  // confirmada total 100 resto 60, valor 75 → body com new_total: '115.00' (string exata, 2 casas), amount 75.
  it('blocks submit with a PT message when value exceeds remainder and the checkbox is unchecked', ...)
  it('sends a plain partial payment (no new_total) when value is below the remainder', ...)
  it('surfaces the backend 400 message via toast on error', ...)
});
```

#### `__tests__/bill-inline-edit.test.tsx`
```ts
describe('DueDatePopover', () => {
  it('PATCHes only {due_date} to bills/{id}/ and refetches on success', ...)
  // spy captura método PATCH + body — nenhum campo de dinheiro presente.
});
describe('AmountPopover', () => {
  it('updates the single non-installment line via update_with_lines preserving its fields', ...)
  it('is not offered for bills with multiple lines, installment lines or a statement', ...)
  it('never issues a PATCH when editing the amount', ...)
});
```

#### `__tests__/quick-bill-dialog.test.tsx`
```ts
describe('QuickBillDialog', () => {
  it('creates a one_time bill with exactly one line via create_with_lines', ...)
  // body: bill{description, due_date, competence_month do board, behavior:'one_time'} + 1 line.
  it('validates required fields (descrição, valor > 0, vencimento) in PT', ...)
  it('defaults competence_month to the month currently shown on the board', ...)
});
```

#### `__tests__/apply-invoice-dialog.test.tsx`
```ts
describe('ApplyInvoiceDialog', () => {
  it('shows draft warnings in an Alert before any apply request is made', ...)
  it('blocks confirmation when the matched account diverges from the bill account', ...)
  it('posts the file to bills/{id}/apply_invoice/ only after explicit confirmation', ...)
  it('surfaces the backend 400 (competência divergente / mês fechado) as a PT toast', ...)
});
```

#### `bills/__tests__/bills-page-interactions.test.tsx` (página inteira, MSW)
```ts
describe('BillsPage — cockpit interactions', () => {
  it('renders the pay popover on active unpaid rows for admins only', ...)
  it('offers "Importar fatura" only on estimated water/electricity open bills', ...)
  it('opens the S73 consolidate-debt dialog from the debt sub-section CTA (rows with an account)', ...)
  it('passes toConsolidableBills(board, accountId) to the dialog: bill_id, amount_remaining and accountType from bill.billing_account.account_type', ...)
  it('does not render the Parcelar CTA on Atrasadas rows (CTA only in the deferred/suspended sub-section)', ...)
  it('hides the Parcelar CTA on rows without a billing account', ...)
  it('adds a one-off bill through "+ Conta avulsa" and refetches the board', ...)
  it('refetches the month board after paying (mutation → invalidate → refetch, no optimistic row flip)', ...)
  // 1ª resposta board: bill aberta; após pay, 2ª resposta: paga — a linha só muda depois do refetch.
});
```

> Rodar (devem **falhar**): `cd frontend && npx vitest run "app/(dashboard)/finances/bills"`

### 2. GREEN
1. `bill-payment-form.ts` (extração) + `bill-payment-dialog.tsx` importando dela.
2. `use-bills.ts`: `useUpdateBill` PUT→PATCH + handlers/testes atualizados.
3. `bill-pay-popover.tsx` → `bill-inline-edit.tsx` → `quick-bill-dialog.tsx` → `apply-invoice-dialog.tsx`.
4. `bill-columns.tsx` (popover pagar, células editáveis, item importar) + `overdue-section.tsx` (CTA Parcelar) + `page.tsx` (estados/wiring).

### 3. REFACTOR
- `computeNewTotal(bill, valor)` como função pura exportada (estimada/juros-multa/parcial) — testável direto; o popover só a consome.
- Elegibilidade como predicados puros: `canEditAmountInline(bill)`, `canImportInvoice(bill)`, `canConsolidate(bill)`.
- Nenhuma duplicação do schema de pagamento (fonte única em `bill-payment-form.ts`).

### 4. VERIFY — gate
```bash
cd frontend
npx vitest run "app/(dashboard)/finances/bills"     # sessão + regressão S74/import
npm run lint && npm run type-check && npm run test:unit
```
> Regressão obrigatória: testes da S74 (`bills-page-board`), do import de header (`bills-page-import`) e do `bill-payment-dialog` seguem verdes (o dialog só mudou imports).

---

## Constraints

- **Sem optimistic update em NENHUMA mutação de dinheiro** (design §8): mutação → invalidate (`invalidateFinanceMoneyCaches` + `monthBoard`, já no hook S71) → refetch; a linha só muda após confirmação. A S71 já removeu o optimistic do `usePayBill` por completo; se um `onMutate` ainda existir ao iniciar esta sessão, é bug de execução da S71 — reportar e parar, não contornar.
- **Dinheiro NUNCA via PATCH** — valor sempre por `update_with_lines`/`create_with_lines` (linhas). PATCH = header (`due_date` etc.).
- **Semântica `new_total` = contrato S68 verbatim** (copiada acima); o front nunca "pré-valida" o que é guard do backend além do bloqueio de UX explicitado.
- **Warnings antes de aplicar**: `apply_invoice` só dispara após confirmação no dialog; divergência de conta bloqueia no front E é 400 no backend. PDF nunca persistido.
- **Popover dentro do `render` da célula** (`popover.tsx` existente); **proibido** estender `DataTable` (`onRowClick` não existe e assim fica).
- **S73 é consumida, não recriada**; verificar props reais do dialog antes de usar.
- **MSW only**; sem suppressions; `import type`; named exports; kebab-case; strings de UI em PT; sem TODO/FIXME.
- Divergência prompt × contratos S68–S75 do `SESSION_STATE.md` → contratos prevalecem.

## Critérios de Aceite (binários)

- [ ] Popover "Pagar" na linha com defaults (hoje/resto/caixa — `amount = ''` vazio cumpre o "valor default resto"); `new_total` enviado exatamente como no contrato S68 e SEMPRE como string decimal com 2 casas via `toFixed(2)` (estimada valor≠resto; confirmada valor>resto via checkbox com `new_total = total + diferença`); parcial sem `new_total`; excesso sem checkbox bloqueado com mensagem PT.
- [ ] `useUpdateBill` migrado PUT→PATCH com TODOS os consumidores/handlers/testes atualizados; vencimento inline envia só `{due_date}`.
- [ ] Valor inline só em bills de 1 linha sem installment e sem statement, via `update_with_lines` preservando os campos da linha; nunca PATCH para dinheiro.
- [ ] "+ Conta avulsa" cria bill `one_time` com 1 linha e competência do board; validações PT.
- [ ] "Importar fatura" na linha só em água/luz estimada aberta; warnings do draft exibidos ANTES de aplicar; divergência de conta bloqueia; `apply_invoice` só após confirmação.
- [ ] CTA "Parcelar" SOMENTE na sub-seção de dívida adiada/suspensa (nunca em Atrasadas), nas linhas com `billing_account`, abrindo o dialog da S73 com as props verbatim via `toConsolidableBills`; linhas sem conta não têm CTA.
- [ ] Nenhum optimistic update nos fluxos novos; toda mutação invalida e o board refaz fetch (teste de página cobre).
- [ ] Todos os testes nomeados no TDD implementados e verdes; MSW only; regressão S74/import/dialog verde.
- [ ] `cd frontend && npm run lint && npm run type-check && npm run test:unit` — **zero erros e zero warnings**; sem suppressions.
- [ ] Nenhum preflight/toast com link (S76); nenhum backend tocado; fluxo avulso do header intacto; `consolidate-debt-dialog` não recriado.

## Handoff

1. Confirmar o gate verde.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`: S75 **concluída**; criados/modificados; nota: "Interações do cockpit — popover pagar c/ `new_total` (S68), inline due_date PATCH / valor update_with_lines, conta avulsa 1-linha, apply_invoice com warnings pré-aplicação, CTA Parcelar → dialog S73; `useUpdateBill` PUT→PATCH".
3. Contratos p/ S76 (verbatim): call-sites de mutação do cockpit que a S76 torna acionáveis: `BillPayPopover`, `DueDatePopover`, `AmountPopover`, `QuickBillDialog`, `ApplyInvoiceDialog`, `GenerateMissingBanner` (S74), CTA Parcelar/dialog S73 e lifecycle actions (`bill-status-actions.tsx`).
4. Rodar `/audit` contra os Critérios de Aceite e corrigir gaps.
5. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 75 — interações do cockpit (pagar c/ ajuste, inline edit, avulsa, importar na linha, parcelar)
   ```
6. Próxima sessão: **76 — preflight do fechamento + toasts acionáveis + varredura final + `/audit`**.
