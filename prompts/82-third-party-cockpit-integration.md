# Sessão 82 — Cockpit: pagar como terceiro, compra avulsa e docs vivos

**Fase 2 (terceiros) — sessão 6 de 6.** Frontend + documentação. **Encerra a fase.**

Design: `@docs/plans/2026-07-27-condo-third-party-payments-design.md` §8 (cockpit).

Depende de: S80 (API), S81 (camada de dados e schemas).

## Arquivos

- **Modificar**: `app/(dashboard)/finances/bills/_components/bill-pay-popover.tsx`, `bill-columns.tsx` (ou equivalente do cockpit), `lib/api/hooks/use-bills.ts`
- **Criar**: `_components/third-party-purchase-dialog.tsx`
- **Modificar**: `docs/FINANCES.md`, `CLAUDE.md`, `prompts/SESSION_STATE.md`

## Escopo

### 1. Origem "Terceiro" no popover de pagamento

O popover hoje tem origem caixa/reserva. Adicionar "Terceiro" → revela seletor de pessoa (obrigatório).

- Sem pessoa selecionada → botão desabilitado (o backend também rejeita, mas o usuário não deve descobrir por toast)
- Envia `funded_from: "third_party"` + `paid_by_person_id`
- **Sem optimistic update** — norma da fase 1 (`usePayBill` perdeu optimistic por completo na S71): mutação → invalidate → refetch do `month_board`
- Erro do backend → toast PT via `showFinanceMutationError`

### 2. Badge de compra de terceiro

Bill com `paid_by_person` → badge com o nome da pessoa, para distinguir de conta de concessionária no cockpit e no extrato da conta.

`paid_by_person` **já vem** no payload de `month_board` — a S80 o adicionou a `BillSerializer.Meta.fields` (allowlist explícita) e ao `select_related`. Se por algum motivo não vier, é regressão da S80: **reportar, não editar o backend nesta sessão**.

### 3. "Nova compra de terceiro"

Botão no header do cockpit (admin-gated) → modal: pessoa, descrição, valor, mês de competência, vencimento, categoria opcional, prédio opcional.

- `POST bills/create_purchase`; sucesso → invalida `month_board` + `finances.thirdParty.*`
- Deixar explícito na UI que a compra **nasce quitada** (texto curto: "A compra já foi paga pela pessoa e entra como dívida com ela") — senão o usuário estranha ela não aparecer em "a pagar"
- Parcelamento: se a S80 entregou, expor "N parcelas"; se não, **omitir o campo** (não simular no frontend)

### 4. Documentação viva (obrigatório, não opcional)

- `docs/FINANCES.md`: seção de terceiros — modelo (`Bill.paid_by_person`, `Payment.paid_by`, `ThirdPartySettlement`), a regra FIFO computada, o impacto no caixa e no wedge, e as rotas novas
- `CLAUDE.md`: modelo de dados e lista de rotas `/api/finances/` atualizados
- `prompts/SESSION_STATE.md`: bloco das sessões 77–82 com os contratos definidos

## TDD

- Popover: seleciona "Terceiro" → aparece seletor; sem pessoa → botão desabilitado; com pessoa → payload correto; erro → toast PT
- Modal de compra: payload correto; fecha e invalida no sucesso
- Badge aparece para bill com `paid_by_person` e não aparece para as demais
- MSW como única fronteira; nada de `vi.mock` de hook interno
- **Teste de fluxo integrado** (exigido pelo design §9, e nenhuma sessão anterior o cobre): `frontend/tests/flows/` — compra de terceiro → aparece no extrato da pessoa → acerto → saldo baixa. Hooks reais, MSW como única fronteira, cada passo asserido pelo request capturado e pelo reflexo na tela. Exemplar: `tests/flows/__tests__/condo-finance-main-flow.test.tsx` (S50)

## NÃO fazer

- **Não** alterar backend (se faltar campo, reportar).
- **Não** reintroduzir optimistic update em `usePayBill`.
- **Não** refatorar o cockpit além do necessário para encaixar a origem nova.

## Aceite

- `npm run test:unit` verde (escopo + suíte completa)
- `npm run lint` + `npm run type-check` + `npm run build` zerados
- **Gate final da Fase 2** (backend, confirmando que nada quebrou nas 6 sessões):
  - `ruff check && ruff format --check && mypy core/ finances/ && pyright && python -m pytest`
  - Cobertura `finances` ≥90%
- Documentação atualizada e commitada
