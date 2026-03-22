# SESSION STATE — Módulo Financeiro

**Feature**: Módulo Financeiro Completo
**Design Doc**: `docs/plans/2026-03-21-financial-module-design.md`
**Total de Sessões**: 15
**Sessão Atual**: 13 (concluída)

---

## Progresso por Sessão

| # | Sessão | Status | Notas |
|---|--------|--------|-------|
| 01 | Backend: Models + Migration + Tests | concluída | 10 models + 2 campos adicionados, 44 testes passando |
| 02 | Backend: Serializers + Tests | concluída | 10 serializers + alterações em ApartmentSerializer/LeaseSerializer (testes pendentes) |
| 03 | Backend: ViewSets Simples + Tests | concluída | 4 ViewSets + 4 rotas + 23 testes passando |
| 04 | Backend: Expense ViewSets + Tests | concluída | 2 ViewSets + 2 rotas + 33 testes passando |
| 05 | Backend: Income/Payment ViewSets + Tests | concluída | 4 ViewSets + 4 rotas + 33 testes passando |
| 06 | Backend: CashFlowService + Tests | concluída | CashFlowService implementado |
| 07 | Backend: FinancialDashboardService + Tests | concluída | 6 métodos, 21 testes passando |
| 08 | Backend: SimulationService + Endpoints + Tests | concluída | SimulationService (6 cenários + compare), FinancialDashboardViewSet (6 endpoints), CashFlowViewSet (4 endpoints), 56 testes passando |
| 09 | Frontend: Schemas + API Hooks | concluída | 10 schemas + 11 hooks + 4 test files (16 testes), MSW handlers, type-check + lint clean |
| 10 | Frontend: Navegação + Páginas Base | concluída | Sidebar expansível, 4 páginas (Persons CRUD + cartões, Categories CRUD hierárquica, Settings singleton, Financial placeholder), use-financial-settings hook, type-check + build clean |
| 11 | Frontend: Página de Despesas | pendente | |
| 12 | Frontend: Income + RentPayments + Employees | pendente | |
| 13 | Frontend: Dashboard Financeiro | concluída | 6 widgets (BalanceCards, CashFlowChart, PersonSummaryCards, UpcomingInstallments, OverdueAlerts, CategoryBreakdownChart), interfaces corrigidas para match backend, type-check + build clean |
| 14 | Frontend: Simulador | pendente | |
| 15 | Permissões + E2E Tests + Polish | pendente | |

---

## Decisões Arquiteturais

1. Migration gerada como `0012_add_financial_module.py` (não 0009, pois já existiam 0009-0011)
2. `FinancialSettings.save()` usa `force_update` quando pk=1 já existe (singleton pattern)
3. `FinancialSettings` não herda AuditMixin/SoftDeleteMixin — tem apenas `updated_at`/`updated_by` próprios
4. `from __future__ import annotations` removido de `financial_views.py` — Python 3.14 tem PEP 649 nativamente. Regra TC (flake8-type-checking) desabilitada no ruff. Target-version atualizado para py314.
5. SimulationService com dois modos: `simulate()` (pure dict-based, unit testável sem DB) e `simulate_from_db()` (resolve parâmetros via DB, usado pelo endpoint). O `compare()` é puro e funciona com ambos.
6. FinancialDashboardViewSet e CashFlowViewSet em `financial_dashboard_views.py` (não em `financial_views.py` que contém apenas ViewSets CRUD).
7. `PersonSimple` schema em `credit-card.schema.ts` (não em `person.schema.ts`) para evitar dependência circular Person→CreditCard→Person. Person importa CreditCard; schemas que precisam de person nested (expense, income, etc.) importam PersonSimple de credit-card.schema.ts.
8. `ExpenseCategory` usa `z.lazy()` para suportar subcategories recursivas no schema Zod.
9. Interfaces dos hooks `use-financial-dashboard.ts` e `use-cash-flow.ts` foram corrigidas na sessão 13 para match com os campos reais do backend (sessão 09 criou interfaces especulativas que divergiam dos endpoints implementados nas sessões 07-08).

## Arquivos Criados

### Backend
- `tests/unit/__init__.py`
- `tests/unit/test_financial/__init__.py`
- `tests/unit/test_financial/test_financial_models.py` — 44 testes
- `tests/unit/test_financial/test_financial_dashboard_service.py` — 21 testes
- `core/migrations/0012_add_financial_module.py`
- `core/services/financial_dashboard_service.py` — 6 métodos estáticos
- `tests/integration/__init__.py`
- `tests/integration/test_financial_api_simple.py` — 23 testes
- `core/viewsets/financial_views.py` — PersonViewSet, CreditCardViewSet, ExpenseCategoryViewSet, FinancialSettingsViewSet

- `tests/integration/test_expense_api.py` — 33 testes (Expense + ExpenseInstallment API)
- `tests/integration/test_income_payment_api.py` — 33 testes (Income, RentPayment, EmployeePayment, PersonIncome API)
- `core/services/simulation_service.py` — SimulationService com 6 cenários (simulate + simulate_from_db + compare)
- `core/viewsets/financial_dashboard_views.py` — FinancialDashboardViewSet (6 endpoints) + CashFlowViewSet (4 endpoints)
- `tests/unit/test_financial/test_simulation_service.py` — 30 testes
- `tests/integration/test_financial_dashboard_api.py` — 15 testes
- `tests/integration/test_cash_flow_api.py` — 11 testes

### Frontend
- `frontend/lib/schemas/person.schema.ts` — Person schema + type
- `frontend/lib/schemas/credit-card.schema.ts` — CreditCard + PersonSimple schemas + types
- `frontend/lib/schemas/expense-category.schema.ts` — ExpenseCategory schema (recursive via z.lazy)
- `frontend/lib/schemas/expense-installment.schema.ts` — ExpenseInstallment schema
- `frontend/lib/schemas/expense.schema.ts` — Expense schema (nested person/card/building/category/installments)
- `frontend/lib/schemas/income.schema.ts` — Income schema
- `frontend/lib/schemas/rent-payment.schema.ts` — RentPayment schema
- `frontend/lib/schemas/employee-payment.schema.ts` — EmployeePayment schema
- `frontend/lib/schemas/financial-settings.schema.ts` — FinancialSettings schema
- `frontend/lib/schemas/person-income.schema.ts` — PersonIncome schema
- `frontend/lib/api/hooks/use-persons.ts` — CRUD hooks (5)
- `frontend/lib/api/hooks/use-credit-cards.ts` — CRUD hooks (5)
- `frontend/lib/api/hooks/use-expense-categories.ts` — CRUD hooks (5)
- `frontend/lib/api/hooks/use-expenses.ts` — CRUD (4) + useMarkExpensePaid + useGenerateInstallments
- `frontend/lib/api/hooks/use-expense-installments.ts` — useExpenseInstallments + useMarkInstallmentPaid + useBulkMarkInstallmentsPaid
- `frontend/lib/api/hooks/use-incomes.ts` — CRUD (4) + useMarkIncomeReceived
- `frontend/lib/api/hooks/use-rent-payments.ts` — CRUD hooks (4)
- `frontend/lib/api/hooks/use-employee-payments.ts` — CRUD (4) + useMarkEmployeePaymentPaid
- `frontend/lib/api/hooks/use-financial-dashboard.ts` — 6 dashboard query hooks (staleTime 5min)
- `frontend/lib/api/hooks/use-cash-flow.ts` — useMonthlyCashFlow + useCashFlowProjection + usePersonSummary
- `frontend/lib/api/hooks/use-simulation.ts` — useSimulation (useMutation)
- `frontend/tests/mocks/data/persons.ts` — mock person data + factory
- `frontend/tests/mocks/data/expenses.ts` — mock expense data + factory
- `frontend/lib/api/hooks/__tests__/use-persons.test.tsx` — 4 testes
- `frontend/lib/api/hooks/__tests__/use-expenses.test.tsx` — 6 testes
- `frontend/lib/api/hooks/__tests__/use-financial-dashboard.test.tsx` — 3 testes
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — 3 testes

- `frontend/app/(dashboard)/financial/page.tsx` — Placeholder page
- `frontend/app/(dashboard)/financial/persons/page.tsx` — CRUD Pessoas (8 colunas, badges, useCrudPage)
- `frontend/app/(dashboard)/financial/persons/_components/person-form-modal.tsx` — Form modal (create/edit com Switch e Select)
- `frontend/app/(dashboard)/financial/persons/_components/credit-card-section.tsx` — Seção inline de cartões (create/delete)
- `frontend/app/(dashboard)/financial/categories/page.tsx` — CRUD Categorias (hierárquica com indentação)
- `frontend/app/(dashboard)/financial/categories/_components/category-form-modal.tsx` — Form modal (color picker, parent select, cor herdada)
- `frontend/app/(dashboard)/financial/settings/page.tsx` — Formulário singleton (GET/PUT)
- `frontend/lib/api/hooks/use-financial-settings.ts` — useFinancialSettings + useUpdateFinancialSettings

- `frontend/app/(dashboard)/financial/_components/balance-cards.tsx` — 4 stat cards com cor condicional
- `frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx` — ComposedChart 12 meses (Bar + Line)
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — Grid de cards por pessoa
- `frontend/app/(dashboard)/financial/_components/upcoming-installments.tsx` — Lista scrollable com highlights
- `frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx` — Alertas vencidos ou mensagem positiva
- `frontend/app/(dashboard)/financial/_components/category-breakdown-chart.tsx` — PieChart com cores das categorias

## Arquivos Modificados

- `core/models.py` — 10 novos models (Person, CreditCard, ExpenseCategory, ExpenseType, Expense, ExpenseInstallment, PersonIncomeType, PersonIncome, Income, RentPayment, EmployeePayment, FinancialSettings) + `owner` em Apartment + `prepaid_until`/`is_salary_offset` em Lease
- `pyproject.toml` — PLR2004 adicionado a per-file-ignores para tests (magic values em assertions)
- `core/viewsets/__init__.py` — exporta 4 novos ViewSets financeiros
- `core/urls.py` — 6 rotas financeiras (persons, credit-cards, expense-categories, financial-settings, expenses, expense-installments)
- `core/viewsets/__init__.py` — exporta 10 ViewSets financeiros
- `core/viewsets/financial_views.py` — adicionados IncomeViewSet, RentPaymentViewSet, EmployeePaymentViewSet, PersonIncomeViewSet
- `core/urls.py` — 10 rotas financeiras (persons, credit-cards, expense-categories, financial-settings, expenses, expense-installments, incomes, rent-payments, employee-payments, person-incomes)
- `core/viewsets/__init__.py` — exporta 12 ViewSets financeiros (+ FinancialDashboardViewSet, CashFlowViewSet)
- `core/urls.py` — 12 rotas financeiras (+ financial-dashboard, cash-flow)
- `frontend/tests/mocks/handlers.ts` — adicionados handlers financeiros (persons, expenses, installments, financial-dashboard, cash-flow, incomes, employee-payments) + fix non-null assertions pré-existentes
- `frontend/tests/mocks/data/index.ts` — exporta persons e expenses
- `frontend/lib/utils/constants.ts` — 9 rotas financeiras no ROUTES
- `frontend/components/layouts/sidebar.tsx` — Sub-menu expansível com chevron + active state
- `frontend/.eslintrc.json` — no-unnecessary-type-parameters off para test files
- `frontend/app/(dashboard)/tenants/page.tsx` — fix || → ?? (pre-existing lint error)
- `frontend/app/(dashboard)/financial/page.tsx` — substituído placeholder por dashboard com 6 widgets
- `frontend/lib/api/hooks/use-financial-dashboard.ts` — interfaces corrigidas para match backend (FinancialOverview, DebtByPerson, UpcomingInstallment, CategoryBreakdown)
- `frontend/lib/api/hooks/use-cash-flow.ts` — CashFlowProjectionMonth corrigido para match backend (income_total, expenses_total, balance, cumulative_balance, is_projected)
- `frontend/tests/mocks/handlers.ts` — MSW handlers atualizados para match novas interfaces
- `frontend/lib/api/hooks/__tests__/use-financial-dashboard.test.tsx` — testes atualizados para novas interfaces
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — testes atualizados para novas interfaces

## Correções Pós-Design (sessão de brainstorming 2026-03-22)

- Estipêndio Rodrigo/Junior: R$1.100 (não R$1.000)
- Funcionária confirmada como Rosa: salário base R$800 + variável por serviços extras
- Prepaid kitnet 113/836: recalculado para 2026-09-29 (inquilina mudou de kitnet R$1.150 para R$1.300 em jan/2026)
- Sistema "pagar para morar": paga dia X para morar de X a X+1mês
- Design doc e prompts 06, 12 atualizados com essas correções
- Categorias simplificadas: 5 principais (Pessoal, Carros, Kitnets, Camila, Ajuda) + subcategorias via `parent` FK
- ExpenseCategory.parent adicionado (migration 0013), serializer atualizado com subcategories + parent_id
- Gastos fixos agora suportam `pessoa` (FK) — ex: Unimed R$2.230 via Rodrigo
- `valor_total` removido de empréstimos — calculado como `valor_parcela × total_parcelas`
- Prompts 09, 10 atualizados com subcategorias
- `Expense.is_offset` adicionado (migration 0014) — descontos: compras no cartão de uma pessoa que são para os sogros/Camila, subtraídas do total
- Dados do Alvaro completos: 3 cartões (Trigg, Players, Samsung), 21 parcelas, 4 descontos, 2 gastos únicos
- Dados do Tiago completos: 17 itens (fogão, geladeiras, alarme, starlink, etc.)
- Dados do Junior: placas solar (22/60), bolsa Camila (4x), perfume Camila (1x), faculdade (mensal até dez/2026)

## Problemas Conhecidos

- Testes de serviço (test_contract_service, test_template_management_service) timeout sem Redis local — issue pré-existente, não relacionado ao módulo financeiro
- xdist workers crasham em Windows/Python 3.14 — issue pré-existente
