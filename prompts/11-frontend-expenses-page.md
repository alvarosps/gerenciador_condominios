# Sessão 11 — Frontend: Página de Despesas (Smart Form + Filters + Installments Drawer)

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seções 7.3 e 7.4 (Despesas)
- `@prompts/SESSION_STATE.md` — Estado atual

Leia estes exemplares:
- `@frontend/app/(dashboard)/leases/page.tsx` — Página complexa com modals extras e filtros
- `@frontend/app/(dashboard)/leases/_components/` — Componentes de lease (referência para organização)
- `@frontend/components/ui/sheet.tsx` — Sheet component (para drawer de parcelas)

Leia os hooks da sessão 09:
- `@frontend/lib/api/hooks/use-expenses.ts`
- `@frontend/lib/api/hooks/use-expense-installments.ts`
- `@frontend/lib/schemas/expense.schema.ts`

---

## Escopo

### Arquivos a CRIAR
- `frontend/app/(dashboard)/financial/expenses/page.tsx`
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx`
- `frontend/app/(dashboard)/financial/expenses/_components/expense-filters.tsx`
- `frontend/app/(dashboard)/financial/expenses/_components/installments-drawer.tsx`
- `frontend/app/(dashboard)/financial/expenses/_components/expense-columns.tsx`

---

## Especificação

### Página de Despesas (`expenses/page.tsx`)

Página mais complexa do módulo. Seguir padrão de leases/page.tsx com extensões:

1. Estado CRUD via `useCrudPage<Expense>()`
2. Estado extra:
   - `selectedExpenseForInstallments: Expense | null` — drawer de parcelas
   - `filters: ExpenseFilters` — filtros ativos
3. `useExpenses(filters)` com filtros aplicados
4. Colunas definidas em arquivo separado (`expense-columns.tsx`)

### Filtros (`expense-filters.tsx`)

Barra de filtros acima da tabela:
- **Tipo** (select): Todos, Compra no Cartão, Empréstimo Bancário, Empréstimo Pessoal, Conta de Água, Conta de Luz, IPTU, Gasto Fixo, Gasto Único, Salário
- **Pessoa** (select): lista de persons via `usePersons()`
- **Cartão** (select): filtrado pela pessoa selecionada, via `useCreditCards({person_id})`
- **Prédio** (select): lista de buildings via `useBuildings()`
- **Categoria** (select): lista via `useExpenseCategories()`
- **Status** (select): Todos, Pago, Pendente
- **Período** (date range): data início / data fim
- Botão "Limpar filtros"

Cascata: ao selecionar pessoa, cartão filtra automaticamente. Ao limpar pessoa, limpa cartão.

### Colunas da Tabela (`expense-columns.tsx`)

```typescript
[
  { title: 'Descrição', dataIndex: 'description' },
  { title: 'Tipo', dataIndex: 'expense_type', render: badge com cor por tipo },
  { title: 'Valor', dataIndex: 'total_amount', render: formatCurrency },
  { title: 'Pessoa', dataIndex: 'person.name', render: '-' se null },
  { title: 'Cartão', dataIndex: 'credit_card.nickname', render: '-' se null },
  { title: 'Prédio', dataIndex: 'building.name', render: '-' se null },
  { title: 'Categoria', render: badge com cor da categoria ou '-' },
  { title: 'Parcelas', render: "3/12" se parcelado, "-" se não },
  { title: 'Status', render: badge "Pago" verde ou "Pendente" amarelo },
  { title: 'Data', dataIndex: 'expense_date', render: formatDate },
  { title: 'Ações', render: botões editar, excluir, ver parcelas (se parcelado), marcar pago },
]
```

### Formulário Inteligente (`expense-form-modal.tsx`)

Modal com formulário que adapta campos conforme o tipo selecionado:

**Campos sempre visíveis:**
- `description` (text)
- `expense_type` (select — todos os 9 tipos, exceto employee_salary que redireciona)
- `total_amount` (number, prefix R$)
- `expense_date` (date picker)
- `category_id` (select, opcional)
- `notes` (textarea, opcional)

**Campos condicionais:**

| expense_type | Campos extras |
|---|---|
| `card_purchase` | person_id (obrigatório), credit_card_id (obrigatório, filtrado por person), is_installment, total_installments |
| `bank_loan` | person_id (obrigatório), bank_name, interest_rate, is_installment, total_installments |
| `personal_loan` | person_id (obrigatório), is_installment, total_installments |
| `water_bill` | building_id (obrigatório), is_debt_installment → se true: is_installment + total_installments |
| `electricity_bill` | building_id (obrigatório), is_debt_installment → se true: is_installment + total_installments |
| `property_tax` | building_id (obrigatório), is_debt_installment → se true: is_installment + total_installments |
| `fixed_expense` | is_recurring=true (auto), expected_monthly_amount, recurrence_day, building_id (opcional) |
| `one_time_expense` | building_id (opcional), person_id (opcional) |
| `employee_salary` | Mostrar mensagem: "Use a página de Funcionários para registrar pagamentos" e botão link |

**Ao salvar com is_installment=True:**
- Após criar a expense, chamar `useGenerateInstallments()` automaticamente
- Mostrar toast de sucesso com quantidade de parcelas geradas

**Form validation com Zod:**
- Validações condicionais baseadas no expense_type
- Usar `z.discriminatedUnion` ou validação manual no `superRefine`

### Drawer de Parcelas (`installments-drawer.tsx`)

Usa o `Sheet` component (slide-out da direita):
- Header: descrição da expense + tipo + valor total
- Lista de parcelas com:
  - Número (ex: "3/12")
  - Valor
  - Data de vencimento
  - Status: badge Pago/Pendente/Vencido (vermelho se overdue)
  - Botão "Marcar como pago" para cada parcela
- Botão "Marcar todas como pagas" no footer
- Ao marcar como pago, invalidar queries e atualizar UI

---

## TDD

1. Implementar componentes na ordem: columns → filters → form-modal → drawer → page
2. Testar manualmente via browser (componentes React complexos)
3. Verificar tipos e build:
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO crie páginas de Income, RentPayment ou Employee nesta sessão
- NÃO modifique componentes compartilhados (DataTable, Sheet, etc.)
- O formulário de expense_type=employee_salary NÃO implementa criação — apenas redireciona
- Parcelas são geradas via API (generate_installments), NÃO calcule no frontend
- Reutilize `formatCurrency` de `lib/utils/formatters.ts`
- Imports de hooks de outras entidades (usePersons, useBuildings) são permitidos para os selects

---

## Critérios de Aceite

- [ ] Tabela de despesas com 11 colunas e formatação correta
- [ ] 7 filtros funcionando com cascata pessoa→cartão
- [ ] Formulário adapta campos conforme tipo selecionado
- [ ] Validação condicional funciona (requer building para utility, etc.)
- [ ] Geração automática de parcelas ao salvar despesa parcelada
- [ ] Drawer de parcelas abre/fecha corretamente
- [ ] Marcar parcela como paga atualiza UI
- [ ] `npm run type-check` e `npm run build` passando

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Expenses page with smart form, filters, and installments drawer`
