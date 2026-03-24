# Sessão 15 — Permissões + E2E Tests + Export + Polish

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 8 (Permissões)
- `@prompts/SESSION_STATE.md` — Estado atual

Leia estes exemplares:
- `@core/views.py` linhas 19-46 — BuildingViewSet (permission_classes pattern)
- `@frontend/store/auth-store.ts` — Zustand auth store (user.is_staff check)
- `@frontend/lib/hooks/use-export.ts` — Hook de exportação existente
- `@tests/e2e/` — Testes e2e existentes (padrão a seguir)

---

## Escopo

### Arquivos a CRIAR
- `core/permissions.py` — (ou adicionar a existente) FinancialReadOnly permission
- `tests/e2e/test_financial_workflow.py` — E2E tests
- `frontend/lib/api/hooks/__tests__/use-simulation.test.tsx` — Teste de simulação

### Arquivos a MODIFICAR
- `core/viewsets/financial_views.py` — Aplicar permissions em todos os ViewSets
- `core/viewsets/financial_dashboard_views.py` — Aplicar permissions
- `frontend/lib/hooks/use-export.ts` — Adicionar colunas de export para entidades financeiras
- Todas as páginas financeiras no frontend — Condicional de is_staff nos botões

---

## Especificação

### 1. Permission Class (Backend)

```python
class FinancialReadOnly(BasePermission):
    """
    Leitura para qualquer usuário autenticado.
    Escrita (POST, PUT, PATCH, DELETE) apenas para admin (is_staff).
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff
```

Aplicar em TODOS os ViewSets financeiros:
- PersonViewSet, CreditCardViewSet, ExpenseCategoryViewSet: `permission_classes = [FinancialReadOnly]`
- ExpenseViewSet, ExpenseInstallmentViewSet: `permission_classes = [FinancialReadOnly]`
- IncomeViewSet, RentPaymentViewSet, EmployeePaymentViewSet: `permission_classes = [FinancialReadOnly]`
- PersonIncomeViewSet: `permission_classes = [FinancialReadOnly]`
- FinancialSettingsViewSet: `permission_classes = [FinancialReadOnly]`
- FinancialDashboardViewSet: `permission_classes = [IsAuthenticated]` (read-only, sem restricao)
- CashFlowViewSet: `permission_classes = [IsAuthenticated]` (read-only + simulate é leitura conceitual)

### 2. Frontend Conditional UI

Em TODAS as páginas CRUD financeiras, esconder botões de ação se `!user.is_staff`:
- Botão "Novo" (criar)
- Botão "Editar" na tabela
- Botão "Excluir" na tabela
- Botão "Marcar como pago"

Padrão:
```typescript
const { user } = useAuthStore();
const isAdmin = user?.is_staff ?? false;

// No JSX:
{isAdmin && <Button onClick={crud.openCreateModal}>Novo</Button>}
```

O Dashboard Financeiro e Simulador são visíveis para todos (read-only).

### 3. Export (Excel/CSV)

Adicionar configurações de export em `use-export.ts` para:

**Expenses:**
```typescript
{
  columns: [
    { header: 'Descrição', key: 'description' },
    { header: 'Tipo', key: 'expense_type' },
    { header: 'Valor', key: 'total_amount', format: currency },
    { header: 'Pessoa', key: 'person.name' },
    { header: 'Cartão', key: 'credit_card.nickname' },
    { header: 'Prédio', key: 'building.name' },
    { header: 'Categoria', key: 'category.name' },
    { header: 'Data', key: 'expense_date', format: date },
    { header: 'Pago', key: 'is_paid', format: yesNo },
  ],
  filename: 'despesas',
}
```

**Incomes:**
```typescript
{
  columns: [
    { header: 'Descrição', key: 'description' },
    { header: 'Valor', key: 'amount', format: currency },
    { header: 'Data', key: 'income_date', format: date },
    { header: 'Pessoa', key: 'person.name' },
    { header: 'Recebido', key: 'is_received', format: yesNo },
  ],
  filename: 'receitas',
}
```

**RentPayments:**
```typescript
{
  columns: [
    { header: 'Mês Ref.', key: 'reference_month', format: monthYear },
    { header: 'Apartamento', key: 'lease.apartment.number' },
    { header: 'Prédio', key: 'lease.apartment.building.name' },
    { header: 'Inquilino', key: 'lease.responsible_tenant.name' },
    { header: 'Valor', key: 'amount_paid', format: currency },
    { header: 'Data Pgto', key: 'payment_date', format: date },
  ],
  filename: 'pagamentos_aluguel',
}
```

Integrar botão de export nas páginas de Despesas, Receitas e Pagamentos.

### 4. E2E Tests (Backend)

```python
# tests/e2e/test_financial_workflow.py

class TestFinancialWorkflowE2E:
    """
    Testa o fluxo completo de um mês financeiro:
    1. Criar persons com cartões
    2. Criar categorias
    3. Registrar despesas (cartão parcelado, empréstimo, conta de água)
    4. Gerar parcelas automaticamente
    5. Registrar receitas extras
    6. Registrar pagamentos de aluguel
    7. Registrar pagamento funcionária
    8. Consultar fluxo de caixa mensal
    9. Consultar dashboard financeiro
    10. Rodar simulação
    """

    def test_complete_monthly_workflow(self):
        # Setup: criar person, cards, building, apartment, lease, tenant
        # Step 1: POST /api/persons/ + POST /api/credit-cards/
        # Step 2: POST /api/expense-categories/
        # Step 3: POST /api/expenses/ (card_purchase, parcelado)
        # Step 4: POST /api/expenses/{id}/generate_installments/
        # Step 5: POST /api/incomes/ (aposentadoria recorrente)
        # Step 6: POST /api/rent-payments/
        # Step 7: POST /api/employee-payments/
        # Step 8: GET /api/cash-flow/monthly/?year=2026&month=3
        # Step 9: GET /api/financial-dashboard/overview/
        # Step 10: POST /api/cash-flow/simulate/ (pay_off_early)
        # Assert: todos os valores calculados corretamente

    def test_owner_apartment_not_in_income(self):
        # Criar apartment com owner
        # Verificar que cash-flow não conta como receita
        # Verificar que aparece como repasse em despesas

    def test_prepaid_lease_not_in_income(self):
        # Criar lease com prepaid_until futuro
        # Verificar que não aparece na receita

    def test_salary_offset_lease_not_in_income(self):
        # Criar lease com is_salary_offset=True
        # Verificar que não aparece na receita

    def test_permissions_non_admin_read_only(self):
        # Criar user não-admin vinculado a Person
        # GET endpoints: 200
        # POST/PUT/DELETE endpoints: 403

    def test_bulk_mark_paid_completes_expense(self):
        # Criar expense com 3 parcelas
        # Marcar 2 parcelas: expense ainda pendente
        # Marcar última parcela: expense auto-completa
```

### 5. Frontend Test — Simulation

```typescript
// use-simulation.test.tsx
describe('useSimulation', () => {
  it('sends scenarios and returns comparison result')
  it('handles empty scenarios')
  it('handles API error gracefully')
})
```

---

## TDD

### Backend:
1. Escrever E2E tests
2. Rodar (devem passar — toda a lógica já existe)
3. Implementar permissions
4. Rodar novamente (verificar 403 para non-admin)
```bash
pytest tests/e2e/test_financial_workflow.py -v
pytest  # suite completa
```

### Frontend:
1. Adicionar conditional UI
2. Adicionar export
3. Rodar simulation test
```bash
cd frontend && npm run test -- --run && npm run type-check && npm run build
```

---

## Constraints

- NÃO modifique a lógica dos services ou ViewSets (apenas permissions)
- NÃO quebre permissões das rotas existentes (buildings, apartments, etc.)
- Permissions devem ser testadas nos E2E tests
- Export deve reutilizar o hook `useExport` existente
- Botões condicionais devem usar `user.is_staff`, NÃO crie um novo permission system no frontend

---

## Critérios de Aceite

- [ ] FinancialReadOnly permission aplicada em todos os ViewSets CRUD
- [ ] DashboardViewSet e CashFlowViewSet acessíveis por qualquer autenticado
- [ ] Non-admin recebe 403 em POST/PUT/DELETE
- [ ] Botões de criar/editar/excluir escondidos para non-admin no frontend
- [ ] Export Excel/CSV funcionando para Despesas, Receitas e Pagamentos
- [ ] E2E test do workflow completo passando
- [ ] Teste de simulação frontend passando
- [ ] Suite backend completa passando
- [ ] Suite frontend completa passando
- [ ] `npm run build` passando

---

## Handoff Final

1. Rodar `pytest` completo (backend)
2. Rodar `cd frontend && npm run test -- --run && npm run type-check && npm run build` (frontend)
3. Atualizar `prompts/SESSION_STATE.md` — todas as sessões concluídas
4. Commitar: `feat(financial): add permissions, export, E2E tests, and polish`
5. O módulo financeiro está completo!
