# Sessão 08 — Backend: SimulationService + Todos os Endpoints Financeiros + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seções 4.2 (SimulationService), 5.5 (Dashboard), 5.6 (Cash-Flow/Simulação)
- `@prompts/SESSION_STATE.md` — Estado atual

Leia o código já implementado:
- `@core/services/cash_flow_service.py` — CashFlowService (sessão 06)
- `@core/services/financial_dashboard_service.py` — FinancialDashboardService (sessão 07)
- `@core/views.py` linhas 438-581 — DashboardViewSet (exemplar para ViewSet read-only com @action)

---

## Escopo

### Arquivos a CRIAR
- `core/services/simulation_service.py`
- `core/viewsets/financial_dashboard_views.py` — ViewSets para dashboard, cash-flow, simulação
- `tests/unit/test_financial/test_simulation_service.py`
- `tests/integration/test_financial_dashboard_api.py`
- `tests/integration/test_cash_flow_api.py`

### Arquivos a MODIFICAR
- `core/viewsets/__init__.py` — exportar novos ViewSets
- `core/urls.py` — registrar rotas

---

## Especificação

### SimulationService

```python
class SimulationService:
    @staticmethod
    def simulate(base_projection: list[dict], scenarios: list[dict]) -> list[dict]:
        """
        Aplica cenários sobre a projeção base.
        Retorna projeção modificada com campo 'delta' por mês.

        Cenários suportados:
        1. {"type": "pay_off_early", "expense_id": int}
           - Remove todas as parcelas futuras dessa expense da projeção
           - Impacto: reduz expenses nos meses que teriam parcelas

        2. {"type": "change_rent", "apartment_id": int, "new_value": str(Decimal)}
           - Altera o rental_value projetado desse apartment
           - Impacto: muda income (se apt dos sogros) ou expenses (se repasse a owner)

        3. {"type": "new_loan", "amount": str(Decimal), "installments": int, "start_month": "YYYY-MM"}
           - Adiciona parcelas mensais (amount/installments) a partir de start_month
           - Impacto: aumenta expenses nos meses das parcelas

        4. {"type": "remove_tenant", "apartment_id": int}
           - Zera a receita de aluguel desse apartment
           - Impacto: reduz income

        5. {"type": "add_fixed_expense", "amount": str(Decimal), "description": str}
           - Adiciona gasto fixo mensal em todos os meses
           - Impacto: aumenta expenses

        6. {"type": "remove_fixed_expense", "expense_id": int}
           - Remove gasto fixo da projeção
           - Impacto: reduz expenses
        """

    @staticmethod
    def compare(base: list[dict], simulated: list[dict]) -> dict:
        """
        Retorna:
        {
            "month_by_month": [
                {
                    "year": int, "month": int,
                    "base_balance": Decimal,
                    "simulated_balance": Decimal,
                    "delta": Decimal,
                    "base_cumulative": Decimal,
                    "simulated_cumulative": Decimal,
                }
            ],
            "total_impact_12m": Decimal,  # soma dos deltas
            "break_even_month": str | None,  # "YYYY-MM" quando saldo vira positivo
        }
        """
```

### FinancialDashboardViewSet (`/api/financial-dashboard/`)

ViewSet read-only (não ModelViewSet). Seguir padrão do DashboardViewSet existente.

```python
@action(detail=False, methods=['get'])
def overview(self, request):
    # Chama FinancialDashboardService.get_overview()

@action(detail=False, methods=['get'])
def debt_by_person(self, request):
    # Chama FinancialDashboardService.get_debt_by_person()

@action(detail=False, methods=['get'])
def debt_by_type(self, request):
    # Chama FinancialDashboardService.get_debt_by_type()

@action(detail=False, methods=['get'])
def upcoming_installments(self, request):
    # Query param: ?days=30
    # Chama FinancialDashboardService.get_upcoming_installments(days)

@action(detail=False, methods=['get'])
def overdue_installments(self, request):
    # Chama FinancialDashboardService.get_overdue_installments()

@action(detail=False, methods=['get'])
def category_breakdown(self, request):
    # Query params: ?year=2026&month=3
    # Chama FinancialDashboardService.get_expense_category_breakdown(year, month)
```

### CashFlowViewSet (`/api/cash-flow/`)

ViewSet read-only + simulação.

```python
@action(detail=False, methods=['get'])
def monthly(self, request):
    # Query params: ?year=2026&month=3
    # Chama CashFlowService.get_monthly_cash_flow(year, month)

@action(detail=False, methods=['get'])
def projection(self, request):
    # Query param: ?months=12
    # Chama CashFlowService.get_cash_flow_projection(months)

@action(detail=False, methods=['get'])
def person_summary(self, request):
    # Query params: ?person_id=1&year=2026&month=3
    # Chama CashFlowService.get_person_summary(person_id, year, month)

@action(detail=False, methods=['post'])
def simulate(self, request):
    # Body: {"scenarios": [...]}
    # 1. Obtém projeção base via CashFlowService.get_cash_flow_projection()
    # 2. Aplica cenários via SimulationService.simulate()
    # 3. Compara via SimulationService.compare()
    # 4. Retorna {base, simulated, comparison}
```

### URL Registration

```python
router.register(r"financial-dashboard", FinancialDashboardViewSet, basename="financial-dashboard")
router.register(r"cash-flow", CashFlowViewSet, basename="cash-flow")
```

---

## TDD

### Passo 1: Escrever testes (RED)

**SimulationService (`test_simulation_service.py`):**
```python
class TestSimulationPayOffEarly:
    test_removes_future_installments  # parcelas futuras removidas
    test_does_not_affect_past  # meses passados inalterados
    test_reduces_expenses  # total expenses diminui

class TestSimulationChangeRent:
    test_changes_income_for_sogros_apt  # altera receita
    test_changes_expense_for_owner_apt  # altera repasse

class TestSimulationNewLoan:
    test_adds_installments  # parcelas adicionadas nos meses corretos
    test_increases_expenses  # total expenses aumenta

class TestSimulationRemoveTenant:
    test_zeros_income  # receita daquele apt vira 0

class TestSimulationAddFixedExpense:
    test_adds_to_all_months  # gasto adicionado em todos os meses

class TestSimulationRemoveFixedExpense:
    test_removes_from_all_months  # gasto removido

class TestSimulationCompare:
    test_month_by_month_deltas  # delta por mês calculado
    test_total_impact  # soma dos deltas
    test_break_even_month  # mês onde saldo vira positivo

class TestSimulationMultipleScenarios:
    test_combined_scenarios  # múltiplos cenários aplicados juntos
```

**Endpoints (`test_financial_dashboard_api.py` e `test_cash_flow_api.py`):**
```python
class TestFinancialDashboardAPI:
    test_overview_endpoint  # GET /api/financial-dashboard/overview/
    test_debt_by_person_endpoint
    test_debt_by_type_endpoint
    test_upcoming_installments_endpoint
    test_upcoming_installments_custom_days  # ?days=7
    test_overdue_installments_endpoint
    test_category_breakdown_endpoint  # ?year=2026&month=3

class TestCashFlowAPI:
    test_monthly_endpoint  # GET /api/cash-flow/monthly/?year=2026&month=3
    test_projection_endpoint  # GET /api/cash-flow/projection/?months=12
    test_person_summary_endpoint  # GET ?person_id=1&year=2026&month=3
    test_simulate_endpoint  # POST /api/cash-flow/simulate/
    test_simulate_pay_off_early  # cenário pay_off_early
    test_simulate_multiple_scenarios  # múltiplos cenários
    test_simulate_invalid_scenario  # erro para tipo inválido
```

### Passo 2-6: Ciclo TDD padrão

---

## Constraints

- SimulationService trabalha com cópias dos dados — NUNCA altera dados reais
- Use `copy.deepcopy` para copiar a projeção base antes de aplicar cenários
- Todos os valores monetários como Decimal
- NÃO crie frontend nesta sessão
- Serialização dos responses dos endpoints pode usar `Response(data)` direto (dict → JSON), sem necessidade de serializer class para dashboard/cash-flow

---

## Critérios de Aceite

- [ ] SimulationService criado com 6 tipos de cenário + compare
- [ ] FinancialDashboardViewSet com 6 endpoints
- [ ] CashFlowViewSet com 4 endpoints (monthly, projection, person_summary, simulate)
- [ ] Simulação com múltiplos cenários simultâneos funciona
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add SimulationService and financial dashboard/cash-flow endpoints`
