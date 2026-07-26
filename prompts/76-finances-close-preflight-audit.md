# Sessão 76 — Frontend: preflight do fechamento + toasts acionáveis de mês fechado + varredura final + `/audit`

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida — `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (rev. 2)
> **Sessões da feature**: 65 → … → 74 → 75 → **76 (ÚLTIMA)**
> Fecho da feature: (1) **preflight do fechamento** — antes de confirmar `close`, buscar o `month_board` da competência e exibir as bills em aberto (contagem + total) no dialog, exigindo confirmação explícita; (2) **toasts acionáveis de mês fechado** em TODAS as mutações do cockpit (mensagem PT do backend + ação/link para `/finances/month-close` — design §6/§8); (3) **varredura final** do design §9 (checklist completo, BE+FE, com evidência por teste) e execução da skill **`/audit`** da feature contra o design doc.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §6 fechamento × pagador defasado — decisão explícita, §8 erros acionáveis, §9 testes — checklist da varredura, §10 gate de arquitetura, §11 YAGNI)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Contratos AUTORITATIVOS S66/S71/S76**: `@prompts/SESSION_STATE.md` (seção "Sessões 65–76")
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/*.md`

### Exemplares (arquivo:linha — VERIFICADOS; ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Página de fechamento** | `frontend/app/(dashboard)/finances/month-close/page.tsx:1-280` — `previousMonth` :25-30; `toReferenceMonth` :33-35; `buildDraftClose` :42-51; `handleConfirm` :180-203 (toast com `getErrorMessage`); seletor + botão "Fechar mês" :218-249; dialog :268-277 | Onde o preflight entra |
| **Dialog de fechar/reabrir** | `month-close/_components/month-close-action-dialog.tsx:1-60` (Props :16-23; AlertDialog com Confirmar/Cancelar) | Ganha o bloco de preflight quando `action === 'close'` |
| **Hooks de fechamento** | `frontend/lib/api/hooks/use-condo-month-closes.ts:39-73` (`useCloseMonth`/`useReopenMonth` — POST `close/`/`reopen/`) | Não mudam; o preflight é só leitura antes do confirm |
| **`useMonthBoard` (S71)** | `lib/api/hooks/` pós-S71 (`staleTime: 0`) + payload S66 (`groups`, `totals.remaining`) | Fonte do preflight (contagem/total em aberto da competência) |
| **Toast do repo = sonner** | `bills/page.tsx:5` (`import { toast } from 'sonner'`); `month-close/page.tsx:7` | Toast acionável via `toast.error(msg, { action: { label, onClick } })` — **novo precedente** (não há uso de `action` no repo hoje; sonner suporta nativamente) |
| **Rota canônica** | `frontend/lib/utils/constants.ts:79` — `FINANCES_MONTH_CLOSE: '/finances/month-close'` | Destino do link acionável — usar `ROUTES`, nunca string solta |
| **Error helpers** | `frontend/lib/utils/error-handler.ts` (`getErrorMessage` :77; `handleError` :165) | **Casa do helper novo** `showFinanceMutationError` (ao lado de `handleError`/`getErrorMessage`); envolve `getErrorMessage` — não reimplementar extração de mensagem |
| **Call-sites de mutação do cockpit (S74/S75)** | `bills/_components/`: `bill-pay-popover.tsx`, `bill-inline-edit.tsx`, `quick-bill-dialog.tsx`, `apply-invoice-dialog.tsx`, `generate-missing-banner.tsx`, `bill-status-actions.tsx`; + dialog S73 aberto pelo cockpit | Todos passam a usar o toast acionável no `onError` |
| **Teste de página MSW** | `bills/__tests__/bills-page-import.test.tsx:34-106` (padrão `server.use` + spies) | Padrão dos testes desta sessão |

### O que as sessões anteriores entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S66**: `month_board` — `groups` = bills ACTIVE da competência (pagas incluídas), `totals.remaining` = restante do mês. Guards de mês fechado respondem **400 com mensagem PT** (ex.: `pay`, `generate_month`, `apply_invoice`, `consolidate_debt`, `update_with_lines`).
- **S71**: `useMonthBoard(year, month)` (`staleTime: 0`) + `createMockMonthBoard`.
- **S74/S75**: cockpit completo (estrutura + interações), com `handleError` simples nos `onError` — que esta sessão troca pelo toast acionável.

> **Se S74/S75 não estiverem concluídas, PARE.** Esta é a última sessão da feature.

---

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/finances/month-close/_components/close-preflight.tsx` — `ClosePreflight` (consome `useMonthBoard` da competência do dialog; renderiza contagem/total em aberto + checkbox de confirmação explícita).
- `frontend/app/(dashboard)/finances/month-close/_components/__tests__/close-preflight.test.tsx`
- `frontend/app/(dashboard)/finances/month-close/__tests__/month-close-preflight.test.tsx` — página inteira (MSW).
- `frontend/lib/utils/__tests__/error-handler-toast.test.ts` (ou incorporar ao teste existente de `error-handler.ts`).

### Arquivos a modificar
- `frontend/lib/utils/error-handler.ts` — helper `showFinanceMutationError(error, fallback, goToMonthClose)` (função pura de UI: decide toast simples × acionável; vive na casa dos helpers de erro, ao lado de `handleError`/`getErrorMessage`).
- `frontend/app/(dashboard)/finances/month-close/_components/month-close-action-dialog.tsx` — quando `action === 'close'`, renderizar `<ClosePreflight …/>` e condicionar o botão de confirmar à confirmação explícita quando houver contas em aberto.
- `frontend/app/(dashboard)/finances/month-close/page.tsx` — passar `year`/`month` do registro ao dialog (derivar do `reference_month` como em :182).
- **Todos os call-sites de mutação do cockpit** (S74/S75): `bill-pay-popover.tsx`, `bill-inline-edit.tsx` (PATCH e update_with_lines), `quick-bill-dialog.tsx`, `apply-invoice-dialog.tsx`, `generate-missing-banner.tsx`, `bill-status-actions.tsx` e o `onError` do wiring do dialog S73 no cockpit — trocar o `onError` por `showFinanceMutationError(error, '<fallback PT>', goToMonthClose)`.
- Testes das S74/S75 que asserem o toast simples de mês fechado — atualizar para o acionável (sem afrouxar).
- **Documentação viva (ATUALIZAR nesta sessão)**: `docs/FINANCES.md` (endpoints novos `month_board`/`statement`/`apply_invoice`/`consolidate_debt` + campos `amount_is_estimated`/`open_balance`); `CLAUDE.md` raiz (actions de `/api/finances/` + rotas `/finances/accounts` e `/finances/accounts/[id]`); `frontend/CLAUDE.md` SE existir (primeira rota `[id]` + novos hooks); índice de exemplares de `prompts/00-prompt-standard.md` (novos padrões: rota `[id]`, popover-em-célula, month board service).

### NÃO fazer
- **Nenhuma mudança no fechamento além do preflight** (design §11): não relaxar o guard de competência (`pay` exige mês aberto — decisão §6), não mexer em `close`/`reopen`/serializers/back-end, não alterar `carried_in`.
- **Não** adicionar `enabled`/opções novas ao `useMonthBoard` se dava para montar o componente condicionalmente (o `ClosePreflight` só monta quando o dialog de close abre — o mount já controla o fetch). Se ainda assim precisar de `enabled`, estender o hook da S71 com testes (não criar hook paralelo).
- **Nada da Fase 2** (terceiros); **sem** sweep de shape de erro `{error}→{detail}` (contrato travado — design §11); **sem** simulação de regularização.

---

## Especificação

### `showFinanceMutationError` (helper — fonte única)

```ts
// lib/utils/error-handler.ts — assinatura exata:
export function showFinanceMutationError(
  error: unknown,
  fallback: string,
  goToMonthClose: () => void
): void
```
- `const message = getErrorMessage(error, fallback)`.
- **Detecção de mês fechado**: HTTP 400 (axios) **e** `/fechad/i.test(message)` (mensagens PT do backend: "…está fechada/fechado…"). Detectado → `toast.error(message, { action: { label: 'Abrir fechamento', onClick: goToMonthClose } })`. Caso contrário → comportamento atual (`handleError(error, fallback)`).
- Call-sites obtêm `goToMonthClose` via `useRouter()` de `next/navigation`: `() => router.push(ROUTES.FINANCES_MONTH_CLOSE)` — rota SEMPRE de `constants.ts:79`, nunca literal.
- A detecção por substring é assumida explicitamente (o backend não expõe código de erro estruturado — design §8 mantém o shape atual travado por testes); documentar em comentário curto no helper.

### Preflight do fechamento (`ClosePreflight` + dialog)

- `ClosePreflight({ year, month, onConfirmationChange })`: monta **apenas** quando o dialog de `close` está aberto; chama `useMonthBoard(year, month)`.
- Deriva: `openBills` = bills de `board.groups` com `amount_remaining > 0` (competência do fechamento); `openCount = openBills.length`; `openTotal = board.totals.remaining` (**verbatim do payload** — não somar no front).
- Render:
  - **Loading** → skeleton curto **e o botão de fechar fica desabilitado até o fetch resolver** (sucesso OU erro).
  - **Erro na busca** → `onConfirmationChange(true)` + Alert PT ("Não foi possível verificar as contas em aberto") — **não bloquear** o fechamento por falha do preflight (preflight é informativo; o backend continua a barreira).
  - `openCount === 0` → linha verde "Nenhuma conta em aberto nesta competência." e `onConfirmationChange(true)`.
  - `openCount > 0` → Alert com "**{N} conta(s) em aberto** totalizando **{formatCurrency(openTotal)}**" + lista compacta (descrição — resto) das primeiras 5 + `Checkbox` **"Entendo que essas contas permanecerão em aberto e desejo fechar mesmo assim"**; `onConfirmationChange(checked)`.
- `MonthCloseActionDialog`: novas props `{ year, month }` (derivadas de `dialogRecord.reference_month` na página, split como :182); quando `action === 'close'`, renderiza o `ClosePreflight` no corpo e **desabilita** `AlertDialogAction` enquanto a confirmação explícita não vier (`isPending` continua desabilitando também). `action === 'reopen'`: dialog inalterado.
- Nenhuma mudança em `useCloseMonth`/`useReopenMonth`; o preflight não grava nada.

### Toasts acionáveis em TODAS as mutações do cockpit

Varredura mecânica: `rg "handleError\(" frontend/app/\(dashboard\)/finances/bills` + o wiring do dialog S73 no cockpit. Para **cada** `onError` de mutação de escrita do cockpit (pagar, PATCH vencimento, valor via update_with_lines, conta avulsa, apply_invoice, generate_month, suspend/defer/cancel/reactivate em `bill-status-actions.tsx`, consolidate via dialog S73 quando aberto do cockpit):
- Trocar por `showFinanceMutationError(error, '<fallback PT existente>', goToMonthClose)`.
- Fallbacks PT existentes são preservados (ex.: "Erro ao pagar conta", "Erro ao gerar contas do mês").
- Fora do cockpit (páginas S72/S73, dashboard) **não** é escopo — a S76 não faz sweep global.

### Varredura final — checklist do design §9 (copiar e evidenciar)

Antes do `/audit`, montar uma tabela `cenário → arquivo de teste → status` cobrindo **todos** os itens do §9 (verificar que cada um tem teste passando nas sessões 65–76; item sem evidência = gap a corrigir NESTA sessão se for FE, ou a reportar ao orquestrador se for BE):

- **Backend**: `month_board` (atrasadas cross-competência só ACTIVE; deferred/suspended fora dos totais; CANCELED invisível; `missing_count` com BillSkip/tracking/conta nova; mês fechado → 400) · `statement`/`open_balance`: braço `installment__plan__billing_account` (conta IPTU não zera), conta cortada acumulando, atraso médio (exclui `amount_total=0`, exige quitada, alocações/payments vivos) · flag `amount_is_estimated` (gerar→True incl. embutido; editar/importar/pagar→False; `unpay` não re-marca; `bulk_pay` via serviço) · pagar-com-ajuste (estimada maior/menor sem resto fantasma; juros/multa em confirmada; atomicidade) · `apply_invoice` (match ok; mismatch building/inscrição; preservação de linha de parcela) · `consolidate_debt` (N bills incl. parciais → 1 plano = Σ restos + origens canceladas; atomicidade; sem dupla contagem).
- **Frontend**: cockpit (popover pagar/editar, banner gerar faltantes, seções Atrasadas/adiada-suspensa) · contas cadastradas (CRUD, célula-link) · extrato (primeira página `[id]`) · MSW (actions de collection antes de `:id`; factories `createMockMonthBoard`/`createMockAccountStatement`; blocos `monthBoard`/`billingAccounts.statement` em `query-keys.ts`).
- **Gate**: ≥90% cobertura em `finances/` (BE), zero warnings, regressão com escopo, mock só de fronteiras externas.

### Fecho: skill `/audit`

Como último passo da sessão (após gate verde), **rodar a skill `/audit`** da feature inteira contra `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` (não só contra este prompt): comparar cada entrega §3.1–§3.5, §4, §5, §6 e §8 com o código; corrigir gaps FE encontrados; gaps BE → reportar ao orquestrador com arquivo/linha.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: MSW; `next/navigation` já é mockado globalmente pelo setup de testes do repo (verificar `tests/` — padrão existente); **NUNCA `vi.mock`** de hooks/utilitários internos do app.

### 1. RED

#### `lib/utils/__tests__/error-handler-toast.test.ts`
```ts
describe('showFinanceMutationError', () => {
  it('shows an actionable toast with "Abrir fechamento" for a 400 whose message mentions mês fechado', ...)
  // AxiosError 400 {detail:'Competência 06/2026 está fechada.'} → toast.error com action; onClick chama goToMonthClose.
  it('falls back to the plain handleError toast for non-closed-month errors', ...)
  // 400 de validação comum ("Valor inválido") → sem action.
  it('uses the PT fallback when the error carries no message', ...)
});
```

#### `month-close/_components/__tests__/close-preflight.test.tsx`
```ts
describe('ClosePreflight', () => {
  it('reports confirmation=true immediately when the competence has no open bills', ...)
  it('lists count and totals.remaining verbatim when there are open bills', ...)
  // groups com 3 bills (2 com resto>0), totals.remaining '350.00' → "2 conta(s)" + R$ 350,00.
  it('only reports confirmation=true after the explicit checkbox is checked', ...)
  it('does not block closing when the board request fails (informative preflight)', ...)
});
```

#### `month-close/__tests__/month-close-preflight.test.tsx`
```ts
describe('MonthClosePage — close preflight', () => {
  it('fetches the month board for the dialog competence when the close dialog opens', ...)
  // spy no GET month_board com year/month do reference_month selecionado.
  it('disables "Fechar mês" until the open-bills checkbox is confirmed', ...)
  it('closes normally (single confirm) when there are no open bills', ...)
  it('keeps the reopen dialog untouched (no preflight, no checkbox)', ...)
});
```

#### Cockpit — atualizar testes S74/S75 (mesmos arquivos)
```ts
it('shows an actionable "Abrir fechamento" toast when paying into a closed month', ...)
// POST pay → 400 'fechada' → toast com action apontando para ROUTES.FINANCES_MONTH_CLOSE.
it('shows an actionable toast when generate_month hits a closed month', ...)
it('shows an actionable toast on closed-month errors from inline edit, conta avulsa, apply_invoice and lifecycle actions', ...)
// parametrizar (it.each) sobre os call-sites — todos delegam ao MESMO helper.
```

> Rodar (devem **falhar**): `cd frontend && npx vitest run "app/(dashboard)/finances/month-close" "app/(dashboard)/finances/bills" "lib/utils/__tests__/error-handler-toast.test.ts"`

### 2. GREEN
1. `showFinanceMutationError` em `lib/utils/error-handler.ts`.
2. `close-preflight.tsx` → `month-close-action-dialog.tsx` (props + bloco + gate do botão) → `month-close/page.tsx` (year/month).
3. Sweep dos `onError` do cockpit para o helper (lista da Especificação).

### 3. REFACTOR
- Um único helper para o toast acionável — proibido duplicar a detecção de mês fechado em call-sites.
- `ClosePreflight` puro na derivação: extrair `deriveOpenBills(board)` (função pura testável).
- Remover imports de `handleError` que ficarem órfãos nos call-sites migrados.

### 4. VERIFY — gate + varredura
```bash
cd frontend
npx vitest run "app/(dashboard)/finances/month-close" "app/(dashboard)/finances/bills" "lib/utils"
npm run lint && npm run type-check && npm run test:unit
```
- Montar a tabela da varredura §9 (cenário → teste → status) e corrigir/reportar gaps.
- **Rodar a skill `/audit`** contra o design doc (feature inteira) como fecho.

---

## Constraints

- **Preflight é informativo, não barreira**: o guard real é o backend; erro ao buscar o board não impede fechar (Alert PT + confirmação normal). Com contas em aberto, exigir o checkbox explícito.
- **`totals.remaining` verbatim** — nunca somar restos no front para o total do preflight (contagem client-side sobre `groups` é permitida).
- **Guard de competência intacto** (design §6): nada de relaxar `pay`/`close`/`reopen`; o fluxo reabrir → pagar → fechar é o caminho suportado e o toast acionável é a ponte para ele.
- **Rota via `ROUTES.FINANCES_MONTH_CLOSE`** (`constants.ts:79`); navegação via `useRouter` de `next/navigation`.
- **Toast = sonner** (padrão do repo); o `action` do sonner é o mecanismo do link — novo precedente, documentado no helper.
- **Escopo do sweep acionável = cockpit** (S74/S75 + lifecycle + wiring S73); não varrer o app inteiro.
- **MSW only**; sem suppressions; `import type`; named exports; strings de UI em PT; sem TODO/FIXME; zero warnings.
- Divergência prompt × contratos S66/S71/S76 do `SESSION_STATE.md` → contratos prevalecem.

## Critérios de Aceite (binários)

- [ ] `showFinanceMutationError` em `lib/utils/error-handler.ts` (assinatura exata da Especificação): 400 + mensagem de mês fechado → toast com ação "Abrir fechamento" navegando para `ROUTES.FINANCES_MONTH_CLOSE`; demais erros → comportamento atual.
- [ ] TODAS as mutações do cockpit (pagar, vencimento PATCH, valor update_with_lines, conta avulsa, apply_invoice, generate_month, suspend/defer/cancel/reactivate, consolidate via dialog S73 no cockpit) usam o helper no `onError` — nenhum call-site com detecção duplicada.
- [ ] Dialog de fechar exibe o preflight (contagem + `totals.remaining` verbatim + lista compacta) e o botão "Fechar mês" só habilita com a confirmação explícita quando há contas em aberto; sem contas em aberto, fluxo de 1 confirmação; reopen inalterado.
- [ ] Falha na busca do board não bloqueia o fechamento (preflight informativo).
- [ ] Nenhuma mudança em backend, `useCloseMonth`/`useReopenMonth`, guards de competência ou shape de erro.
- [ ] Testes nomeados no TDD implementados e verdes; testes S74/S75 atualizados para o toast acionável sem afrouxar; MSW only.
- [ ] Tabela da varredura §9 completa (todos os cenários com evidência de teste); gaps FE corrigidos; gaps BE reportados com arquivo/linha.
- [ ] Skill `/audit` executada contra o design doc; gaps encontrados corrigidos ou reportados.
- [ ] Documentação viva atualizada: `docs/FINANCES.md` com `month_board`/`statement`/`apply_invoice`/`consolidate_debt` + `amount_is_estimated`/`open_balance`; `CLAUDE.md` raiz com as actions novas de `/api/finances/` + rotas `/finances/accounts` e `/finances/accounts/[id]`; `frontend/CLAUDE.md` (se existir) com a primeira rota `[id]` + hooks novos; índice de exemplares de `prompts/00-prompt-standard.md` com os padrões novos (rota `[id]`, popover-em-célula, month board service).
- [ ] `cd frontend && npm run lint && npm run type-check && npm run test:unit` — **zero erros e zero warnings**; sem suppressions.

## Handoff

1. Confirmar gate + varredura + `/audit` concluídos.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`: S76 **concluída — FEATURE COMPLETA**; criados/modificados; nota: "Preflight do fechamento (board da competência, contagem/total verbatim, checkbox explícito), toast acionável de mês fechado (helper único `showFinanceMutationError` em `lib/utils/error-handler.ts` + sonner action → ROUTES.FINANCES_MONTH_CLOSE) em todas as mutações do cockpit; varredura §9 tabulada; `/audit` da feature executado". Registrar a tabela da varredura (ou o caminho dela) na nota.
3. **Confirmar a documentação viva atualizada** (parte do escopo, não opcional): `docs/FINANCES.md`, `CLAUDE.md` raiz, `frontend/CLAUDE.md` (se existir) e `prompts/00-prompt-standard.md` conforme o Escopo.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 76 — close preflight + actionable closed-month toasts + final sweep
   ```
5. Feature encerrada: próximo passo é o fluxo de merge do branch `feat/condo-bills-cockpit` (fora do escopo das sessões — orquestrador decide PR/review).
