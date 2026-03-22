# Sessão 09 — Frontend: Schemas Zod + API Hooks

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 7.1 (Estrutura de Arquivos frontend)
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia estes exemplares:
- `@frontend/lib/schemas/building.schema.ts` — Schema Zod simples
- `@frontend/lib/schemas/lease.schema.ts` — Schema Zod complexo com transforms
- `@frontend/lib/api/hooks/use-buildings.ts` — CRUD hooks padrão
- `@frontend/lib/api/hooks/use-leases.ts` — Hooks com mutations extras
- `@frontend/lib/api/hooks/use-dashboard.ts` — Dashboard hooks com staleTime
- `@frontend/lib/api/client.ts` — Axios instance (entender padrão de chamadas)

---

## Escopo

### Arquivos a CRIAR

**Schemas:**
- `frontend/lib/schemas/person.schema.ts`
- `frontend/lib/schemas/credit-card.schema.ts`
- `frontend/lib/schemas/expense.schema.ts`
- `frontend/lib/schemas/expense-installment.schema.ts`
- `frontend/lib/schemas/expense-category.schema.ts`
- `frontend/lib/schemas/income.schema.ts`
- `frontend/lib/schemas/rent-payment.schema.ts`
- `frontend/lib/schemas/employee-payment.schema.ts`
- `frontend/lib/schemas/financial-settings.schema.ts`
- `frontend/lib/schemas/person-income.schema.ts`

**Hooks:**
- `frontend/lib/api/hooks/use-persons.ts`
- `frontend/lib/api/hooks/use-credit-cards.ts`
- `frontend/lib/api/hooks/use-expenses.ts`
- `frontend/lib/api/hooks/use-expense-installments.ts`
- `frontend/lib/api/hooks/use-expense-categories.ts`
- `frontend/lib/api/hooks/use-incomes.ts`
- `frontend/lib/api/hooks/use-rent-payments.ts`
- `frontend/lib/api/hooks/use-employee-payments.ts`
- `frontend/lib/api/hooks/use-financial-dashboard.ts`
- `frontend/lib/api/hooks/use-cash-flow.ts`
- `frontend/lib/api/hooks/use-simulation.ts`

**Testes:**
- `frontend/lib/api/hooks/__tests__/use-persons.test.tsx`
- `frontend/lib/api/hooks/__tests__/use-expenses.test.tsx`
- `frontend/lib/api/hooks/__tests__/use-financial-dashboard.test.tsx`
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx`

---

## Especificação

### Schemas

Seguir padrão existente:
- `id` sempre `z.number().optional()`
- Campos monetários: `z.string().or(z.number()).transform((val) => Number(val))`
- Audit fields sempre opcionais
- Nested objects usam seus próprios schemas (read) + `_ids` suffix (write)
- Export tipo inferido: `export type Person = z.infer<typeof personSchema>`

**Exemplo (person.schema.ts):**
```typescript
export const personSchema = z.object({
  id: z.number().optional(),
  name: z.string(),
  relationship: z.string(),
  phone: z.string().optional().default(''),
  email: z.string().optional().default(''),
  is_owner: z.boolean().default(false),
  is_employee: z.boolean().default(false),
  user: z.number().nullable().optional(),
  notes: z.string().optional().default(''),
  credit_cards: z.array(creditCardSchema).default([]),
  // audit fields...
});
```

**expense.schema.ts** deve incluir:
- Todos os campos do model Expense
- `person`, `credit_card`, `building`, `category` como nested objects (read)
- `person_id`, `credit_card_id`, `building_id`, `category_id` como write fields
- `installments` como array de installmentSchema (read)
- Campos computados: `remaining_installments`, `total_paid`, `total_remaining`

### Hooks

**Padrão CRUD** (seguir use-buildings.ts):
- `usePersons()` — useQuery com queryKey ['persons'], page_size: 10000, Zod parse
- `usePerson(id)` — useQuery single
- `useCreatePerson()` — useMutation + invalidateQueries(['persons'])
- `useUpdatePerson()` — useMutation + invalidateQueries(['persons'])
- `useDeletePerson()` — useMutation + invalidateQueries(['persons'])

**Hooks com filtros** (useExpenses):
```typescript
export function useExpenses(filters?: ExpenseFilters) {
  return useQuery({
    queryKey: ['expenses', filters],
    queryFn: async () => {
      const { data } = await apiClient.get('/expenses/', { params: { page_size: 10000, ...filters } });
      // Zod parse
    },
  });
}
```

**Hooks com ações extras** (useExpenses):
- `useMarkExpensePaid()` — POST /expenses/{id}/mark_paid/
- `useGenerateInstallments()` — POST /expenses/{id}/generate_installments/
- `useMarkInstallmentPaid()` — POST /expense-installments/{id}/mark_paid/
- `useBulkMarkInstallmentsPaid()` — POST /expense-installments/bulk_mark_paid/
- `useMarkIncomeReceived()` — POST /incomes/{id}/mark_received/
- `useMarkEmployeePaymentPaid()` — POST /employee-payments/{id}/mark_paid/

**Dashboard hooks** (seguir use-dashboard.ts):
```typescript
// staleTime: 5 min, refetchInterval: 5 min
export function useFinancialOverview() { ... }
export function useDebtByPerson() { ... }
export function useDebtByType() { ... }
export function useUpcomingInstallments(days?: number) { ... }
export function useOverdueInstallments() { ... }
export function useCategoryBreakdown(year: number, month: number) { ... }
```

**Cash flow hooks:**
```typescript
export function useMonthlyCashFlow(year: number, month: number) { ... }
export function useCashFlowProjection(months?: number) { ... }
export function usePersonSummary(personId: number, year: number, month: number) { ... }
```

**Simulation hook:**
```typescript
export function useSimulation() {
  return useMutation({
    mutationFn: async (scenarios: SimulationScenario[]) => {
      const { data } = await apiClient.post('/cash-flow/simulate/', { scenarios });
      return data;
    },
  });
}
```

### Types para Dashboard/CashFlow/Simulation

Exportar interfaces TypeScript nos arquivos de hooks:
```typescript
export interface FinancialOverview { ... }
export interface DebtByPerson { ... }
export interface CashFlowMonth { ... }
export interface SimulationScenario { ... }
export interface SimulationResult { ... }
```

---

## TDD

### Passo 1: Escrever testes (RED)

Seguir padrão existente com MSW. Configurar handlers em `frontend/tests/mocks/handlers.ts` para as novas rotas.

**Adicionar mock data generators:**
- `frontend/tests/mocks/data/persons.ts`
- `frontend/tests/mocks/data/expenses.ts`

**Testes (4 arquivos — os mais críticos):**

```typescript
// use-persons.test.tsx
describe('usePersons', () => {
  it('fetches persons list')
  it('creates a person')
  it('updates a person')
  it('deletes a person')
})

// use-expenses.test.tsx
describe('useExpenses', () => {
  it('fetches expenses with filters')
  it('creates expense')
  it('marks expense as paid')
  it('generates installments')
})
describe('useExpenseInstallments', () => {
  it('marks installment as paid')
  it('bulk marks installments as paid')
})

// use-financial-dashboard.test.tsx
describe('useFinancialOverview', () => { it('fetches overview') })
describe('useDebtByPerson', () => { it('fetches debt by person') })
describe('useUpcomingInstallments', () => { it('fetches with custom days') })

// use-cash-flow.test.tsx
describe('useMonthlyCashFlow', () => { it('fetches monthly data') })
describe('useCashFlowProjection', () => { it('fetches projection') })
describe('useSimulation', () => { it('sends scenarios and returns result') })
```

### Passo 2: Rodar testes (devem FALHAR)
```bash
cd frontend && npm run test -- --run
```

### Passo 3: Implementar schemas e hooks

### Passo 4: Rodar testes (devem PASSAR)
```bash
cd frontend && npm run test -- --run
```

### Passo 5: Type-check
```bash
cd frontend && npm run type-check
```

---

## Constraints

- NÃO crie componentes ou páginas nesta sessão
- NÃO modifique hooks existentes (use-buildings, use-leases, etc.)
- Siga EXATAMENTE o padrão de queryKey, invalidation e Zod parse dos hooks existentes
- Todos os hooks de mutation devem invalidar as queries relevantes no onSuccess
- useExpenses mutations devem também invalidar ['financial-dashboard'] e ['cash-flow']

---

## Critérios de Aceite

- [ ] 10 schemas Zod criados com tipos exportados
- [ ] 11 arquivos de hooks criados
- [ ] Todos os CRUD hooks seguem padrão existente
- [ ] Dashboard hooks com staleTime/refetchInterval
- [ ] Simulation hook como useMutation
- [ ] MSW handlers configurados
- [ ] 4 arquivos de teste passando
- [ ] `npm run type-check` passando
- [ ] `npm run test -- --run` passando

---

## Handoff

1. Rodar `npm run test -- --run` e `npm run type-check`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add frontend schemas, API hooks, and tests for financial module`
