# Sessão 12 — Frontend: Páginas de Receitas, Pagamentos de Aluguel e Funcionários

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seções 7.1 e 7.3
- `@prompts/SESSION_STATE.md` — Estado atual

Leia estes exemplares:
- `@frontend/app/(dashboard)/financial/expenses/page.tsx` — Referência de página financeira (sessão 11)
- `@frontend/app/(dashboard)/buildings/page.tsx` — CRUD page canônica

Leia os hooks:
- `@frontend/lib/api/hooks/use-incomes.ts`
- `@frontend/lib/api/hooks/use-rent-payments.ts`
- `@frontend/lib/api/hooks/use-employee-payments.ts`

---

## Escopo

### Arquivos a CRIAR

**Receitas:**
- `frontend/app/(dashboard)/financial/incomes/page.tsx`
- `frontend/app/(dashboard)/financial/incomes/_components/income-form-modal.tsx`

**Pagamentos de Aluguel:**
- `frontend/app/(dashboard)/financial/rent-payments/page.tsx`
- `frontend/app/(dashboard)/financial/rent-payments/_components/rent-payment-form-modal.tsx`

**Funcionários:**
- `frontend/app/(dashboard)/financial/employees/page.tsx`
- `frontend/app/(dashboard)/financial/employees/_components/employee-payment-form-modal.tsx`

---

## Especificação

### Página de Receitas (`incomes/page.tsx`)

CRUD padrão com:

**Colunas:**
- Descrição
- Valor (formatCurrency)
- Data
- Pessoa (ou "-")
- Prédio (ou "-")
- Categoria (badge com cor ou "-")
- Recorrente (badge Sim/Não)
- Recebido (badge verde "Recebido" / amarelo "Pendente")
- Ações: editar, excluir, marcar como recebido

**Filtros:**
- `person_id` (select)
- `is_recurring` (select: Todos/Sim/Não)
- `is_received` (select: Todos/Sim/Não)
- `date_from`, `date_to` (date range)

**Modal de formulário:**
- description (text)
- amount (number, R$)
- income_date (date picker)
- person_id (select, opcional)
- building_id (select, opcional)
- category_id (select, opcional)
- is_recurring (switch)
- expected_monthly_amount (number, R$ — visível apenas se is_recurring)
- notes (textarea, opcional)

### Página de Pagamentos de Aluguel (`rent-payments/page.tsx`)

CRUD com visão mensal:

**Colunas:**
- Mês Ref. (format: "Mar/2026")
- Apartamento (number + building name)
- Inquilino (responsible_tenant name)
- Valor Pago (formatCurrency)
- Data Pgto. (formatDate)
- Ações: editar, excluir

**Filtros:**
- `building_id` (select — via lease→apartment→building)
- `apartment_id` (select — filtrado por building selecionado)
- `month_from`, `month_to` (month picker ou date)

**Modal de formulário:**
- lease_id (select — mostrar "Apt {number} - {building.name} ({tenant.name})")
- reference_month (month picker — salvar como primeiro dia do mês)
- amount_paid (number, R$)
- payment_date (date picker)
- notes (textarea, opcional)

### Página de Funcionários (`employees/page.tsx`)

Registros mensais de pagamento:

**Colunas:**
- Mês Ref. (format: "Mar/2026")
- Funcionário (person name)
- Salário Base (formatCurrency)
- Variável (formatCurrency)
- Compensação Aluguel (formatCurrency, cor cinza — informativo)
- Total Pago (formatCurrency, negrito — base + variável)
- Faxinas (número)
- Status (badge Pago/Pendente)
- Ações: editar, excluir, marcar como pago

**Modal de formulário:**
- person_id (select — filtrar por is_employee=true)
- reference_month (month picker)
- base_salary (number, R$)
- variable_amount (number, R$, default 0)
- rent_offset (number, R$, default 0 — informativo)
- cleaning_count (number, default 0)
- notes (textarea, opcional)
- **Total** exibido em tempo real: base_salary + variable_amount (sem rent_offset)

---

## TDD

1. Implementar na ordem: Receitas → Pagamentos → Funcionários (crescente em complexidade)
2. Verificar tipos e build:
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO implemente Dashboard ou Simulador nesta sessão
- NÃO modifique componentes compartilhados
- Para o select de lease no RentPayment, buscar via `useLeases()` e formatar como "Apt {number} - {building}"
- Para o select de person no EmployeePayment, filtrar `usePersons()` por `is_employee=true`
- O `reference_month` sempre salva como primeiro dia do mês (ex: 2026-03-01)
- Reutilize `formatCurrency` e `formatDate` dos utils existentes

---

## Critérios de Aceite

- [ ] Página de Receitas: CRUD completo com filtros e mark_received
- [ ] Página de Pagamentos: CRUD com filtros por prédio/apt/mês
- [ ] Página de Funcionários: CRUD com cálculo de total em tempo real
- [ ] reference_month formata corretamente (month picker)
- [ ] Filtros cascata building→apartment funciona
- [ ] `npm run type-check` e `npm run build` passando

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Income, RentPayment, and EmployeePayment pages`
