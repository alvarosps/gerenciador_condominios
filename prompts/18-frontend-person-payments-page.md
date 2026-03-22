# Sessão 18 — Frontend: Página de Pagamentos a Pessoas + PersonSummaryCards Atualizado

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md`
- `@prompts/SESSION_STATE.md` — Estado atual

Leia os hooks criados na sessão 17:
- `@frontend/lib/api/hooks/use-person-payments.ts`
- `@frontend/lib/api/hooks/use-cash-flow.ts` — `usePersonSummary()` com interface corrigida
- `@frontend/lib/api/hooks/use-persons.ts`

Leia os exemplares:
- `@frontend/app/(dashboard)/financial/rent-payments/page.tsx` — Padrão de página com filtros
- `@frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — Componente a atualizar

---

## Escopo

### Arquivos a CRIAR
- `frontend/app/(dashboard)/financial/person-payments/page.tsx`
- `frontend/app/(dashboard)/financial/person-payments/_components/person-payment-form-modal.tsx`
- `frontend/app/(dashboard)/financial/person-payments/_components/person-month-summary.tsx`

### Arquivos a MODIFICAR
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — usar dados completos do PersonSummary
- `frontend/lib/utils/constants.ts` — adicionar rota person-payments no ROUTES
- `frontend/components/layouts/sidebar.tsx` — adicionar link no submenu financeiro (se necessário)
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — adicionar toggle is_offset

---

## Especificação

### 1. Página de Pagamentos a Pessoas (`person-payments/page.tsx`)

Layout com duas seções:

**Seção superior — Resumo por pessoa (cards):**
Grid de cards, um por pessoa, mostrando o resumo do mês selecionado:
- Nome da pessoa + relação (badge)
- **Deve receber**: net_amount (receives - card - loan - fixed + offset)
- **Já pago**: total_paid (soma dos PersonPayments do mês)
- **Saldo pendente**: pending_balance (net_amount - total_paid)
  - Verde se 0 (quitado), vermelho se > 0 (pendente)
  - Se negativo (pagou a mais) → amarelo com indicação
- Botão "Registrar pagamento" → abre modal

Usar `usePersonSummary(personId, year, month)` para cada pessoa.
Usar `usePersons()` para listar todas as pessoas.

**Seção inferior — Histórico de pagamentos:**
Tabela com todos os pagamentos registrados:
- Pessoa
- Mês referência (format "Mar/2026")
- Valor (formatCurrency)
- Data pagamento (formatDate)
- Notas
- Ações: editar, excluir

**Filtros:**
- `person_id` (select)
- Mês/ano (month picker, default: mês atual)

### 2. Modal de Pagamento (`person-payment-form-modal.tsx`)

Campos:
- `person_id` (select — lista de pessoas)
- `reference_month` (month picker — salvar como primeiro dia do mês)
- `amount` (input monetário R$)
- `payment_date` (date picker — default: hoje)
- `notes` (textarea opcional)

Ao salvar: chama `useCreatePersonPayment()`, que invalida `['person-payments']` + `['cash-flow']`.

### 3. Resumo Mensal da Pessoa (`person-month-summary.tsx`)

Componente reutilizável que mostra o breakdown completo de uma pessoa num mês:

```
┌─────────────────────────────────────┐
│ Rodrigo - Março/2026          filho │
├─────────────────────────────────────┤
│ Recebe:                             │
│   Estipêndio fixo      R$ 1.100,00 │
│                                     │
│ Cartões:               R$ 6.489,12 │
│   Itau Azul             R$ 2.158,64│
│   Itau Visa             R$ 1.173,51│
│   Caixa                 R$ 3.157,97│
│                                     │
│ Empréstimos:           R$ 2.341,63 │
│   Panvel 1/5              R$ 57,73 │
│   TV 13/15               R$ 294,00 │
│   ...                               │
│                                     │
│ Gastos fixos:          R$ 2.230,00 │
│   Unimed                R$ 2.230,00│
│                                     │
│ Descontos:            -R$ 2.291,50 │
│   TV aniversário 8/10   -R$ 295,00 │
│   Máquina secar 7/12    -R$ 337,50 │
│   ...                               │
│                                     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Total devido:          R$ 9.869,25 │
│ Pago:                  R$ 5.000,00 │
│ Pendente:              R$ 4.869,25 │
│                                     │
│ Pagamentos:                         │
│   05/03 - R$ 5.000,00              │
│                                     │
│ [Registrar pagamento]               │
└─────────────────────────────────────┘
```

Este componente pode ser usado na página de pagamentos e no dashboard.

### 4. Atualizar PersonSummaryCards no Dashboard (Gap 14)

Substituir o uso de `useDebtByPerson()` por `usePersonSummary()` para cada pessoa.
Mostrar:
- Recebe: receives
- Cartões + Empréstimos + Fixos: card_total + loan_total + fixed_total
- Descontos: -offset_total
- **Net**: net_amount (bold, cor condicional)
- **Pago/Pendente**: total_paid / pending_balance (se houver PersonPayments no mês)

### 5. Toggle is_offset no formulário de despesas (Gap 15)

No `expense-form-modal.tsx`:
- Adicionar `is_offset` ao formSchema: `z.boolean().default(false)`
- Adicionar Switch UI: "Desconto (compra no cartão para os sogros/Camila)"
- Visível para tipos: `card_purchase`, `bank_loan`, `personal_loan`
- Se `is_offset=true`, mostrar label explicativo: "Este valor será subtraído do total da pessoa"

---

## TDD

1. Implementar na ordem:
   - Toggle is_offset no expense form
   - PersonMonthSummary component
   - PersonSummaryCards atualizado
   - Página de pagamentos
2. Verificar:
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO modifique o Dashboard principal (page.tsx da raiz financeiro)
- O PersonMonthSummary deve ser componente reutilizável em `financial/_components/`
- Use `formatCurrency` de `lib/utils/formatters.ts` em TODOS os valores
- O mês padrão da página é o mês atual
- Loading states em todos os cards e tabela

---

## Critérios de Aceite

- [ ] Página de pagamentos com resumo por pessoa + tabela de histórico
- [ ] Modal de registro de pagamento funcional
- [ ] PersonMonthSummary mostra breakdown completo (recebe, cartões, empréstimos, fixos, descontos, pago, pendente)
- [ ] PersonSummaryCards no dashboard atualizado com dados completos
- [ ] Toggle is_offset no formulário de despesas
- [ ] Saldo pendente com cor condicional (verde=quitado, vermelho=pendente)
- [ ] `npm run type-check` e `npm run build` passando

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add PersonPayments page + update PersonSummaryCards + is_offset toggle`
