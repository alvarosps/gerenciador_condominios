# SESSION STATE — Módulo Financeiro

**Feature**: Módulo Financeiro Completo
**Design Doc**: `docs/plans/2026-03-21-financial-module-design.md`
**Total de Sessões**: 15
**Sessão Atual**: 7 (concluída)

---

## Progresso por Sessão

| # | Sessão | Status | Notas |
|---|--------|--------|-------|
| 01 | Backend: Models + Migration + Tests | concluída | 10 models + 2 campos adicionados, 44 testes passando |
| 02 | Backend: Serializers + Tests | pendente | |
| 03 | Backend: ViewSets Simples + Tests | concluída | 4 ViewSets + 4 rotas + 23 testes passando |
| 04 | Backend: Expense ViewSets + Tests | pendente | |
| 05 | Backend: Income/Payment ViewSets + Tests | pendente | |
| 06 | Backend: CashFlowService + Tests | concluída | CashFlowService implementado |
| 07 | Backend: FinancialDashboardService + Tests | concluída | 6 métodos, 21 testes passando |
| 08 | Backend: SimulationService + Endpoints + Tests | pendente | |
| 09 | Frontend: Schemas + API Hooks | pendente | |
| 10 | Frontend: Navegação + Páginas Base | pendente | |
| 11 | Frontend: Página de Despesas | pendente | |
| 12 | Frontend: Income + RentPayments + Employees | pendente | |
| 13 | Frontend: Dashboard Financeiro | pendente | |
| 14 | Frontend: Simulador | pendente | |
| 15 | Permissões + E2E Tests + Polish | pendente | |

---

## Decisões Arquiteturais

1. Migration gerada como `0012_add_financial_module.py` (não 0009, pois já existiam 0009-0011)
2. `FinancialSettings.save()` usa `force_update` quando pk=1 já existe (singleton pattern)
3. `FinancialSettings` não herda AuditMixin/SoftDeleteMixin — tem apenas `updated_at`/`updated_by` próprios

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

### Frontend
- -

## Arquivos Modificados

- `core/models.py` — 10 novos models (Person, CreditCard, ExpenseCategory, ExpenseType, Expense, ExpenseInstallment, PersonIncomeType, PersonIncome, Income, RentPayment, EmployeePayment, FinancialSettings) + `owner` em Apartment + `prepaid_until`/`is_salary_offset` em Lease
- `pyproject.toml` — PLR2004 adicionado a per-file-ignores para tests (magic values em assertions)
- `core/viewsets/__init__.py` — exporta 4 novos ViewSets financeiros
- `core/urls.py` — 4 novas rotas financeiras (persons, credit-cards, expense-categories, financial-settings)

## Correções Pós-Design (sessão de brainstorming 2026-03-22)

- Estipêndio Rodrigo/Junior: R$1.100 (não R$1.000)
- Funcionária confirmada como Rosa: salário base R$800 + variável por serviços extras
- Prepaid kitnet 113/836: recalculado para 2026-09-29 (inquilina mudou de kitnet R$1.150 para R$1.300 em jan/2026)
- Sistema "pagar para morar": paga dia X para morar de X a X+1mês
- Design doc e prompts 06, 12 atualizados com essas correções

## Problemas Conhecidos

- Testes de serviço (test_contract_service, test_template_management_service) timeout sem Redis local — issue pré-existente, não relacionado ao módulo financeiro
- xdist workers crasham em Windows/Python 3.14 — issue pré-existente
