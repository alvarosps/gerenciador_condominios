# Sessão 17 — Frontend: Schemas, Hooks e Interfaces — Correções + PersonPayment + PersonIncome

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md`
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md`

Leia o backend para alinhar interfaces:
- `@core/services/cash_flow_service.py` — `get_monthly_cash_flow()` e `get_person_summary()` retornos
- `@core/serializers.py` — `PersonPaymentSerializer`, `PersonIncomeSerializer`
- `@core/viewsets/financial_views.py` — `PersonPaymentViewSet`, `PersonIncomeViewSet`

Leia os hooks existentes:
- `@frontend/lib/api/hooks/use-cash-flow.ts` — Interfaces a corrigir
- `@frontend/lib/schemas/expense.schema.ts` — Falta is_offset

Leia os exemplares:
- `@frontend/lib/schemas/rent-payment.schema.ts` — Padrão de schema simples
- `@frontend/lib/api/hooks/use-rent-payments.ts` — Padrão de CRUD hooks

---

## Escopo

### Arquivos a CRIAR
- `frontend/lib/schemas/person-payment.schema.ts`
- `frontend/lib/schemas/person-income.schema.ts` — se não existir, ou verificar se está correto
- `frontend/lib/api/hooks/use-person-payments.ts`
- `frontend/lib/api/hooks/use-person-incomes.ts`
- `frontend/tests/mocks/data/person-payments.ts`

### Arquivos a MODIFICAR
- `frontend/lib/schemas/expense.schema.ts` — adicionar `is_offset`
- `frontend/lib/api/hooks/use-cash-flow.ts` — corrigir interfaces `CashFlowMonth` e `PersonSummary`
- `frontend/tests/mocks/handlers.ts` — adicionar handlers para person-payments e person-incomes
- `frontend/tests/mocks/data/index.ts` — exportar novos mocks

---

## Especificação

### 1. Corrigir `expense.schema.ts` — adicionar `is_offset` (Gap 10)

```typescript
// Adicionar ao expenseSchema:
is_offset: z.boolean().default(false),
```

### 2. Corrigir `CashFlowMonth` interface (Gap 9)

A interface atual NÃO corresponde ao backend. Corrigir para:

```typescript
export interface CashFlowMonth {
  year: number;
  month: number;
  income: {
    rent_income: number;
    rent_details: Array<{
      apartment_id: number;
      apartment_number: string;
      building_name: string;
      tenant_name: string;
      rental_value: number;
      is_paid: boolean;
      payment_date: string | null;
    }>;
    extra_income: number;
    extra_income_details: Array<Record<string, unknown>>;
    total: number;
  };
  expenses: {
    owner_repayments: number;
    person_stipends: number;
    card_installments: number;
    loan_installments: number;
    utility_bills: number;
    debt_installments: number;
    property_tax: number;
    employee_salary: number;
    fixed_expenses: number;
    one_time_expenses: number;
    total: number;
    // Cada categoria tem _details correspondente
    [key: string]: unknown;
  };
  balance: number;
}
```

### 3. Corrigir `PersonSummary` interface (Gap 5)

```typescript
export interface PersonSummary {
  person_id: number;
  person_name: string;
  receives: number;
  receives_details: Array<{ description: string; amount: number; source: string }>;
  card_total: number;
  card_details: Array<{
    description: string;
    card_name: string | null;
    installment: string;
    amount: number;
    due_date: string;
  }>;
  loan_total: number;
  loan_details: Array<{
    description: string;
    installment: string;
    amount: number;
    due_date: string;
  }>;
  offset_total: number;
  offset_details: Array<{
    description: string;
    installment: string | null;
    amount: number;
    due_date: string;
  }>;
  fixed_total: number;
  fixed_details: Array<{ description: string; amount: number }>;
  net_amount: number;
  total_paid: number;
  payment_details: Array<{
    amount: number;
    payment_date: string;
    notes: string;
  }>;
  pending_balance: number;
}
```

### 4. Criar `person-payment.schema.ts` (Gap 11)

```typescript
export const personPaymentSchema = z.object({
  id: z.number().optional(),
  person: personSimpleSchema.optional(),
  person_id: z.number().optional(),
  reference_month: z.string(),
  amount: z.string().or(z.number()).transform((val) => Number(val)),
  payment_date: z.string(),
  notes: z.string().optional().default(''),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type PersonPayment = z.infer<typeof personPaymentSchema>;
```

### 5. Criar `use-person-payments.ts` (Gap 12)

Hooks CRUD padrão seguindo `use-rent-payments.ts`:
- `usePersonPayments(filters?)` — queryKey `['person-payments', filters]`
- `useCreatePersonPayment()` — invalidates `['person-payments']` + `['cash-flow']`
- `useUpdatePersonPayment()` — same invalidation
- `useDeletePersonPayment()` — same invalidation

Filtros: `person_id`, `reference_month`, `month_from`, `month_to`

### 6. Criar `use-person-incomes.ts` (Gap 16)

Hooks CRUD padrão:
- `usePersonIncomes(filters?)` — queryKey `['person-incomes', filters]`
- `useCreatePersonIncome()`
- `useUpdatePersonIncome()`
- `useDeletePersonIncome()`

Filtros: `person_id`, `income_type`, `is_active`, `apartment_id`

### 7. Verificar/criar `person-income.schema.ts`

Se já existe, verificar que está correto. Se não existe, criar seguindo o padrão.

---

## TDD

### Passo 1: Implementar e verificar tipos

```bash
cd frontend && npm run type-check
```

### Passo 2: Verificar build

```bash
npm run build
```

### Passo 3: Atualizar MSW handlers e criar testes

```python
# Adicionar handlers para:
# GET /api/person-payments/ — retorna lista
# POST /api/person-payments/ — cria
# GET /api/person-incomes/ — retorna lista
# POST /api/person-incomes/ — cria
```

---

## Constraints

- NÃO modifique componentes de página nesta sessão — apenas schemas, hooks e interfaces
- NÃO crie páginas ou modais — isso será feito nas sessões 18 e 20
- As interfaces DEVEM corresponder exatamente ao backend response shape
- Mantenha backward compatibility nos hooks existentes que já são consumidos por páginas

---

## Critérios de Aceite

- [ ] `expense.schema.ts` inclui `is_offset`
- [ ] `CashFlowMonth` interface corresponde ao backend
- [ ] `PersonSummary` interface inclui receives, card_total, loan_total, offset_total, fixed_total, net_amount, total_paid, pending_balance
- [ ] `person-payment.schema.ts` criado com tipos corretos
- [ ] `use-person-payments.ts` com CRUD + filtros
- [ ] `use-person-incomes.ts` com CRUD + filtros
- [ ] MSW handlers para ambos os endpoints
- [ ] `npm run type-check` passando
- [ ] `npm run build` passando

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `fix(financial): correct CashFlow/PersonSummary interfaces + add PersonPayment/PersonIncome hooks`
