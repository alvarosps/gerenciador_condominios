# Sessão 20 — Frontend: PersonIncome Management + Polish + Testes E2E

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md`
- `@prompts/SESSION_STATE.md` — Estado atual

Leia os hooks criados na sessão 17:
- `@frontend/lib/api/hooks/use-person-incomes.ts`
- `@frontend/lib/schemas/person-income.schema.ts`

Leia os exemplares:
- `@frontend/app/(dashboard)/financial/persons/page.tsx` — CRUD page com cards e modais

---

## Escopo

### Arquivos a CRIAR

**PersonIncome Page:**
- `frontend/app/(dashboard)/financial/person-incomes/page.tsx`
- `frontend/app/(dashboard)/financial/person-incomes/_components/person-income-form-modal.tsx`

**Testes E2E:**
- `tests/e2e/test_financial_workflow.py` — Testes de fluxo completo

### Arquivos a MODIFICAR
- `frontend/lib/utils/constants.ts` — adicionar rota person-incomes se não existir
- `frontend/components/layouts/sidebar.tsx` — verificar/adicionar link

---

## Especificação

### 1. Página PersonIncome (`person-incomes/page.tsx`)

Gerencia o que cada pessoa TEM DIREITO a receber mensalmente.

**Colunas:**
- Pessoa (nome + badge relação)
- Tipo (badge: "Aluguel Apartamento" ou "Estipêndio Fixo")
- Apartamento (para tipo apartment_rent: "Apto 101/836" ou "-")
- Valor (formatCurrency — para fixed_stipend: fixed_amount; para apartment_rent: valor do lease ativo ou "Sem lease")
- Vigência (data_inicio — data_fim ou "Indefinido")
- Ativo (badge Sim/Não)
- Ações: editar, excluir

**Filtros:**
- `person_id` (select)
- `income_type` (select: Todos / Aluguel / Estipêndio)
- `is_active` (select: Todos / Ativos / Inativos)

**Modal de formulário:**
- `person_id` (select, obrigatório)
- `income_type` (select: apartment_rent / fixed_stipend)
- Se `apartment_rent`:
  - `apartment_id` (select — "Apto {number} - {building.name}")
  - Mostrar valor atual do lease (informativo, não editável)
- Se `fixed_stipend`:
  - `fixed_amount` (input monetário R$)
- `start_date` (date picker)
- `end_date` (date picker, opcional)
- `is_active` (switch, default true)
- `notes` (textarea, opcional)

### 2. Testes E2E — Fluxos Financeiros Completos

```python
# tests/e2e/test_financial_workflow.py

class TestFinancialCRUDWorkflow:
    """Testa fluxos CRUD completos via API."""

    test_create_person_with_cards_and_income
    # 1. Criar Person
    # 2. Criar CreditCard vinculado
    # 3. Criar PersonIncome (fixed_stipend)
    # 4. Verificar person_summary

    test_expense_lifecycle
    # 1. Criar Expense parcelada
    # 2. Gerar installments
    # 3. Marcar parcelas como pagas
    # 4. Verificar que aparecem no dashboard

    test_person_payment_flow
    # 1. Criar expenses para uma pessoa (cartão + empréstimo)
    # 2. Chamar get_person_summary → verificar net_amount
    # 3. Registrar PersonPayment parcial
    # 4. Chamar get_person_summary → verificar pending_balance reduzido
    # 5. Registrar segundo PersonPayment → verificar pending_balance = 0

    test_offset_reduces_person_total
    # 1. Criar expense normal (cartão) para pessoa
    # 2. Criar expense com is_offset=True para mesma pessoa
    # 3. Verificar que net_amount = normal - offset

    test_cash_flow_projection_with_end_date
    # 1. Criar FIXED_EXPENSE com end_date
    # 2. Projetar 12 meses
    # 3. Verificar que gasto não aparece após end_date

    test_daily_control_breakdown
    # 1. Criar lease com due_day=10
    # 2. Criar installment com due_date no dia 15
    # 3. Chamar daily_breakdown
    # 4. Verificar que rent aparece no dia 10, installment no dia 15

    test_vacant_apartment_no_revenue
    # 1. Marcar apartamento como is_rented=False
    # 2. Verificar que cash flow não inclui receita desse apartamento

    test_prepaid_lease_no_revenue
    # 1. Lease com prepaid_until futuro
    # 2. Verificar que cash flow não inclui receita

    test_salary_offset_lease_no_revenue
    # 1. Lease com is_salary_offset=True
    # 2. Verificar que cash flow não inclui receita

    test_subcategory_expense
    # 1. Criar categoria pai + subcategoria
    # 2. Criar expense com subcategoria
    # 3. Verificar que category_breakdown agrupa corretamente

    test_simulation_scenarios
    # 1. Projetar base
    # 2. Simular pay_off_early
    # 3. Simular change_rent
    # 4. Verificar compare retorna deltas corretos
```

### 3. Polish — Verificações Finais

Verificar e corrigir qualquer inconsistência:

- [ ] Todas as páginas financeiras acessíveis via sidebar
- [ ] Todos os formulários validam campos obrigatórios
- [ ] Todos os modais fecham após salvar
- [ ] Todas as tabelas têm loading states
- [ ] Todas as queries invalidam corretamente após mutations
- [ ] `formatCurrency` usado em todos os valores monetários (sem toFixed manual)
- [ ] Navegação entre páginas financeiras funciona
- [ ] Responsividade (mobile) verificada em todas as páginas
- [ ] Ações de editar/excluir funcionam com confirmação

---

## TDD

### Backend:
```bash
pytest tests/e2e/test_financial_workflow.py -v
```

### Frontend:
```bash
cd frontend && npm run type-check && npm run build && npm run test:unit
```

---

## Constraints

- NÃO modifique lógica de negócio existente — apenas teste
- NÃO modifique componentes de outras sessões — apenas verifique
- Testes E2E usam APIClient diretamente, não mocks
- Testes devem criar dados de teste com factories (model_bakery)
- Cada teste deve ser independente (setup/teardown)

---

## Critérios de Aceite

- [ ] Página PersonIncome: CRUD completo com formulário adaptativo (rent vs stipend)
- [ ] 11 testes E2E passando cobrindo todos os fluxos financeiros
- [ ] Todas as verificações de polish passando
- [ ] `pytest` completo passando (unit + integration + e2e)
- [ ] `npm run type-check && npm run build` passando
- [ ] Zero gaps restantes

---

## Handoff

1. Rodar `pytest` completo + `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md` — marcar TODAS as sessões como concluídas
3. Commitar: `feat(financial): add PersonIncome page + E2E tests + polish`
4. Módulo financeiro completo! 🎉
