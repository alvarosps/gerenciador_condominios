# SESSION STATE — Módulo Financeiro

**Feature**: Módulo Financeiro Completo
**Design Doc**: `docs/plans/2026-03-21-financial-module-design.md`
**Total de Sessões**: 20
**Sessão Atual**: 18 (concluída) — sessões 19-20 pendentes (frontend pages + novas funcionalidades)

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
| 11 | Frontend: Página de Despesas | concluída | 5 componentes (columns, filters, form-modal, installments-drawer, page), smart form por tipo, cascata pessoa→cartão, drawer de parcelas, type-check + build clean |
| 12 | Frontend: Income + RentPayments + Employees | concluída | 3 páginas CRUD (incomes, rent-payments, employees), 3 form modals, filtros cascata building→apartment, month picker, real-time total, type-check + build clean |
| 13 | Frontend: Dashboard Financeiro | concluída | 6 widgets (BalanceCards, CashFlowChart, PersonSummaryCards, UpcomingInstallments, OverdueAlerts, CategoryBreakdownChart), interfaces corrigidas para match backend, type-check + build clean |
| 14 | Frontend: Simulador | concluída | 6 componentes (scenario-builder, scenario-card, comparison-chart, comparison-table, impact-summary, page), useSimulation interfaces corrigidas para match backend, MSW handler atualizado, type-check + build + lint clean |
| 15 | Permissões + E2E Tests + Polish | concluída | FinancialReadOnly permission, IsAuthenticated para Dashboard/CashFlow, is_staff no frontend, conditional UI em 7 páginas, export Excel (despesas/receitas/pagamentos), 6 E2E tests + 3 simulation tests, type-check + lint + build clean |
| 16 | Backend: Correções críticas + gaps | concluída | except syntax fix (ObjectDoesNotExist), end_date Expense + migration 0016, is_offset filtering em 4 queries, fixed_total em person_summary, 11 testes regressão |
| 17 | Frontend: Schemas/hooks/interfaces fixes | concluída | PersonPayment schema+hook, PersonIncome hook, CashFlowMonth+PersonSummary interfaces corrigidas, is_offset em expense schema+form+mocks, MSW handlers |
| 18 | Frontend: PersonPayments page + is_offset toggle | concluída | Página pagamentos a pessoas (summary cards + tabela), PersonMonthSummary reutilizável, PersonSummaryCards atualizado com usePersonSummary, is_offset toggle, form modal, type-check + build + lint clean |
| 19 | Frontend: Controle Diário | pendente | DailyControlService + página com timeline, gráfico saldo diário, mark-paid inline |
| 20 | Frontend: PersonIncome page + E2E + Polish | pendente | CRUD PersonIncome, 11 testes E2E, verificações finais |

---

### Sessão 17 — Arquivos Criados
- `frontend/lib/schemas/person-payment.schema.ts` — PersonPayment schema + type
- `frontend/lib/api/hooks/use-person-payments.ts` — CRUD hooks (4) + PersonPaymentFilters
- `frontend/lib/api/hooks/use-person-incomes.ts` — CRUD hooks (4) + PersonIncomeFilters
- `frontend/tests/mocks/data/person-payments.ts` — mock data + factory

### Sessão 17 — Arquivos Modificados
- `frontend/lib/schemas/expense.schema.ts` — adicionado `is_offset`
- `frontend/lib/api/hooks/use-cash-flow.ts` — CashFlowMonth interface corrigida (income/expenses/balance nested), PersonSummary corrigida (receives, card_total, loan_total, offset_total, fixed_total, net_amount, total_paid, pending_balance)
- `frontend/tests/mocks/handlers.ts` — handlers person-payments + person-incomes, cash-flow/monthly + person_summary atualizados para novas interfaces
- `frontend/tests/mocks/data/index.ts` — exporta person-payments
- `frontend/tests/mocks/data/expenses.ts` — is_offset adicionado em mock data
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — assertions atualizadas para nova CashFlowMonth
- `frontend/lib/api/hooks/__tests__/use-expenses.test.tsx` — is_offset no create mutation test
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — is_offset no form schema, defaultValues e reset

### Sessão 18 — Arquivos Criados
- `frontend/app/(dashboard)/financial/person-payments/page.tsx` — Página com resumo mensal por pessoa + tabela histórico pagamentos
- `frontend/app/(dashboard)/financial/person-payments/_components/person-payment-form-modal.tsx` — Form modal create/edit pagamento
- `frontend/app/(dashboard)/financial/_components/person-month-summary.tsx` — Componente reutilizável breakdown completo pessoa/mês

### Sessão 18 — Arquivos Modificados
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — Reescrito para usar usePersonSummary (antes usava useDebtByPerson)
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — Toggle is_offset para card_purchase/bank_loan/personal_loan
- `frontend/lib/utils/constants.ts` — FINANCIAL_PERSON_PAYMENTS rota adicionada
- `frontend/components/layouts/sidebar.tsx` — Link "Pgto. Pessoas" no submenu financeiro

### Sessão 16 — Arquivos Criados
- `tests/unit/test_financial/test_gap_fixes.py` — 11 testes de regressão (4 classes)
- `core/migrations/0016_add_expense_end_date.py` — adiciona end_date ao Expense

### Sessão 16 — Arquivos Modificados
- `core/models.py` — end_date adicionado ao Expense
- `core/serializers.py` — end_date adicionado ao ExpenseSerializer.fields
- `core/services/simulation_service.py` — except syntax fixado com ObjectDoesNotExist, removido Lease import
- `core/services/cash_flow_service.py` — _collect_fixed_expenses com end_date+is_offset+person, _collect_utility_bills com is_offset, _get_projected_expenses com is_offset, get_person_summary com fixed_total
- `core/services/financial_dashboard_service.py` — get_expense_category_breakdown com is_offset

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
10. Expense form schema usa `z.boolean()` e `z.string()` (sem `.default()` ou `.optional()`) para compatibilidade com `zodResolver` — validação condicional por tipo feita manualmente no `handleSubmit` via `validateConditionalFields()` em vez de `superRefine` (que causa type mismatch com React Hook Form).
11. Em Zod 4, `z.number({ required_error: '...' })` não é válido — usar `z.number().min(1, '...')` ou `z.number({ error: '...' })`. Também evitar `.optional().default('')` em form schemas, preferir `.default('')` ou plain type com defaultValues no useForm.
12. `useSimulation` hook (sessão 09) tinha interfaces especulativas (`name` em vez de `type`, `results` em vez de `base/simulated/comparison`) — corrigidas na sessão 14 para match com o endpoint real `POST /api/cash-flow/simulate/` implementado na sessão 08. Cenários usam `type` (SimulationScenarioType union) e resposta retorna `{ base, simulated, comparison }`.
13. Simulador usa `useRef` para estabilizar `simulation.mutate` sem eslint-disable — padrão seguro para evitar deps infinitas em callbacks que chamam mutations.
14. `FinancialReadOnly` permission criada em `core/permissions.py` — idêntica em lógica a `ReadOnlyForNonAdmin` mas nomeada especificamente para o módulo financeiro. Aplicada em todos os CRUD ViewSets financeiros.
15. `FinancialDashboardViewSet` e `CashFlowViewSet` usam `IsAuthenticated` (não `FinancialReadOnly`) — qualquer usuário autenticado pode ler dashboard e rodar simulações.
16. `FinancialSettingsViewSet` mudou de `IsAdminUser` para `FinancialReadOnly` — non-admin pode ler configurações mas não alterar.
17. `is_staff` adicionado ao `User` interface no frontend (`auth-store.ts`) — usado para conditional rendering de botões de ação (criar/editar/excluir/marcar como pago).
18. `except (A, B):` em Python 3.14 é reformatado por ruff para `except A, B:` que tem semântica diferente (PEP 758: catch A, assign to B). Workaround: usar `except ObjectDoesNotExist:` (base class Django) em vez de `except (Apartment.DoesNotExist, Lease.DoesNotExist):`.

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
- `tests/e2e/__init__.py`
- `tests/e2e/test_financial_workflow.py` — 6 testes E2E (workflow completo, owner, prepaid, salary_offset, permissions, bulk_mark_paid)

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
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — 2 testes (simulation movido para arquivo próprio)
- `frontend/lib/api/hooks/__tests__/use-simulation.test.tsx` — 3 testes (scenarios, empty, error)

- `frontend/app/(dashboard)/financial/page.tsx` — Placeholder page
- `frontend/app/(dashboard)/financial/persons/page.tsx` — CRUD Pessoas (8 colunas, badges, useCrudPage)
- `frontend/app/(dashboard)/financial/persons/_components/person-form-modal.tsx` — Form modal (create/edit com Switch e Select)
- `frontend/app/(dashboard)/financial/persons/_components/credit-card-section.tsx` — Seção inline de cartões (create/delete)
- `frontend/app/(dashboard)/financial/categories/page.tsx` — CRUD Categorias (hierárquica com indentação)
- `frontend/app/(dashboard)/financial/categories/_components/category-form-modal.tsx` — Form modal (color picker, parent select, cor herdada)
- `frontend/app/(dashboard)/financial/settings/page.tsx` — Formulário singleton (GET/PUT)
- `frontend/lib/api/hooks/use-financial-settings.ts` — useFinancialSettings + useUpdateFinancialSettings

- `frontend/app/(dashboard)/financial/expenses/page.tsx` — Página de despesas com CRUD, filtros, drawer
- `frontend/app/(dashboard)/financial/expenses/_components/expense-columns.tsx` — 11 colunas com badges, formatação
- `frontend/app/(dashboard)/financial/expenses/_components/expense-filters.tsx` — 7 filtros com cascata pessoa→cartão
- `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` — Smart form adaptativo por tipo (9 tipos)
- `frontend/app/(dashboard)/financial/expenses/_components/installments-drawer.tsx` — Sheet drawer com mark paid

- `frontend/app/(dashboard)/financial/incomes/page.tsx` — CRUD Receitas (9 colunas, filtros inline, mark_received)
- `frontend/app/(dashboard)/financial/incomes/_components/income-form-modal.tsx` — Form modal (create/edit, is_recurring toggle)
- `frontend/app/(dashboard)/financial/rent-payments/page.tsx` — CRUD Pagamentos Aluguel (6 colunas, cascata building→apartment, month range)
- `frontend/app/(dashboard)/financial/rent-payments/_components/rent-payment-form-modal.tsx` — Form modal (lease select formatado, month picker→YYYY-MM-01)
- `frontend/app/(dashboard)/financial/employees/page.tsx` — CRUD Funcionários (9 colunas, mark_paid, total bold)
- `frontend/app/(dashboard)/financial/employees/_components/employee-payment-form-modal.tsx` — Form modal (is_employee filter, real-time total via watch)

- `frontend/app/(dashboard)/financial/_components/balance-cards.tsx` — 4 stat cards com cor condicional
- `frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx` — ComposedChart 12 meses (Bar + Line)
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx` — Grid de cards por pessoa
- `frontend/app/(dashboard)/financial/_components/upcoming-installments.tsx` — Lista scrollable com highlights
- `frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx` — Alertas vencidos ou mensagem positiva
- `frontend/app/(dashboard)/financial/_components/category-breakdown-chart.tsx` — PieChart com cores das categorias

- `frontend/app/(dashboard)/financial/simulator/page.tsx` — Página do simulador (cenários efêmeros, gráfico + tabela comparativa)
- `frontend/app/(dashboard)/financial/simulator/_components/scenario-builder.tsx` — Sheet drawer para criar cenários (6 tipos)
- `frontend/app/(dashboard)/financial/simulator/_components/scenario-card.tsx` — Card compacto com ícone, título, descrição e botão remover
- `frontend/app/(dashboard)/financial/simulator/_components/comparison-chart.tsx` — ComposedChart com linhas base vs simulado + área delta
- `frontend/app/(dashboard)/financial/simulator/_components/comparison-table.tsx` — Tabela mês a mês com deltas coloridos e total no rodapé
- `frontend/app/(dashboard)/financial/simulator/_components/impact-summary.tsx` — Card resumo (impacto total, mês equilíbrio, saldos finais)

- `frontend/app/(dashboard)/financial/person-payments/page.tsx` — Página pagamentos a pessoas (summary cards + tabela histórico)
- `frontend/app/(dashboard)/financial/person-payments/_components/person-payment-form-modal.tsx` — Form modal create/edit pagamento a pessoa
- `frontend/app/(dashboard)/financial/_components/person-month-summary.tsx` — Componente reutilizável breakdown completo pessoa/mês

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
- `frontend/lib/api/hooks/use-simulation.ts` — interfaces corrigidas para match backend (SimulationScenario.type, SimulationResult com base/simulated/comparison)
- `frontend/tests/mocks/handlers.ts` — MSW handler de simulate atualizado para retornar { base, simulated, comparison }
- `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` — teste de simulação movido para use-simulation.test.tsx
- `core/permissions.py` — adicionada FinancialReadOnly permission class
- `core/viewsets/financial_views.py` — todos os ViewSets CRUD agora usam FinancialReadOnly (antes ReadOnlyForNonAdmin), FinancialSettingsViewSet mudou de IsAdminUser para FinancialReadOnly
- `core/viewsets/financial_dashboard_views.py` — DashboardViewSet e CashFlowViewSet mudaram de ReadOnlyForNonAdmin para IsAuthenticated, removido IsAdminUser do simulate action
- `frontend/store/auth-store.ts` — is_staff adicionado ao User interface
- `frontend/app/(dashboard)/financial/persons/page.tsx` — conditional UI (isAdmin) para botões criar/editar/excluir
- `frontend/app/(dashboard)/financial/categories/page.tsx` — conditional UI (isAdmin) para botões criar/editar/excluir
- `frontend/app/(dashboard)/financial/expenses/page.tsx` — conditional UI + botão exportar Excel
- `frontend/app/(dashboard)/financial/expenses/_components/expense-columns.tsx` — isAdmin no handler, edit/delete/markPaid condicionais
- `frontend/app/(dashboard)/financial/incomes/page.tsx` — conditional UI + botão exportar Excel
- `frontend/app/(dashboard)/financial/rent-payments/page.tsx` — conditional UI + botão exportar Excel
- `frontend/app/(dashboard)/financial/employees/page.tsx` — conditional UI (isAdmin) para botões criar/editar/excluir/marcar pago
- `frontend/app/(dashboard)/financial/settings/page.tsx` — campos e botão salvar desabilitados para non-admin
- `frontend/lib/hooks/use-export.ts` — adicionadas expenseExportColumns, incomeExportColumns, rentPaymentExportColumns

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
- Diretório `financial-employees-temp` é lixo de uma sessão abortada — deve ser deletado manualmente (arquivos foram substituídos por stubs vazios para não bloquear build)
