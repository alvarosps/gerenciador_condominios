# Sessão 07 — Backend: FinancialDashboardService + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 4.3 (FinancialDashboardService)
- `@prompts/SESSION_STATE.md` — Estado atual

Leia estes exemplares:
- `@core/services/dashboard_service.py` — Padrão de dashboard com agregações ORM
- `@core/services/cash_flow_service.py` — CashFlowService criado na sessão 06

---

## Escopo

### Arquivos a CRIAR
- `core/services/financial_dashboard_service.py`
- `tests/unit/test_financial/test_financial_dashboard_service.py`

---

## Especificação

### FinancialDashboardService

**Método 1: `get_overview() -> dict`**
```python
{
    "current_month_balance": Decimal,       # saldo do mês atual (via CashFlowService)
    "current_month_income": Decimal,        # receita do mês
    "current_month_expenses": Decimal,      # despesas do mês
    "total_debt": Decimal,                  # soma de todas ExpenseInstallments futuras não pagas
    "total_monthly_obligations": Decimal,   # soma mensal estimada de todas obrigações
    "total_monthly_income": Decimal,        # soma mensal estimada de receitas
    "months_until_break_even": int | None,  # meses até saldo acumulado positivo (max 60 meses, ou None)
}
```

**Método 2: `get_debt_by_person() -> list[dict]`**
```python
[
    {
        "person_id": int,
        "person_name": str,
        "card_debt": Decimal,         # soma parcelas futuras de cartão não pagas
        "loan_debt": Decimal,         # soma parcelas futuras de empréstimo não pagas
        "total_debt": Decimal,
        "monthly_card": Decimal,      # parcelas de cartão do mês atual
        "monthly_loan": Decimal,      # parcelas de empréstimo do mês atual
        "cards_count": int,           # número de cartões ativos
    }
]
```

**Método 3: `get_debt_by_type() -> dict`**
```python
{
    "card_purchases": Decimal,        # total futuro não pago
    "bank_loans": Decimal,
    "personal_loans": Decimal,
    "water_debt": Decimal,            # dívida negociada de água
    "electricity_debt": Decimal,      # dívida negociada de luz
    "property_tax_debt": Decimal,     # dívida negociada de IPTU
    "total": Decimal,
}
```

**Método 4: `get_upcoming_installments(days: int = 30) -> list[dict]`**
```python
[
    {
        "id": int,
        "expense_description": str,
        "expense_type": str,
        "person_name": str | None,
        "credit_card_nickname": str | None,
        "installment_number": int,
        "total_installments": int,
        "amount": Decimal,
        "due_date": date,
        "days_until_due": int,
    }
]
# Ordenado por due_date ASC
```

**Método 5: `get_overdue_installments() -> list[dict]`**
Mesmo formato de upcoming, mas `due_date < today` e `is_paid=False`.
Campo extra: `days_overdue: int`.

**Método 6: `get_expense_category_breakdown(year: int, month: int) -> list[dict]`**
```python
[
    {
        "category_id": int | None,    # None para sem categoria
        "category_name": str,         # "Sem Categoria" para null
        "color": str,
        "total": Decimal,
        "percentage": float,          # porcentagem do total de despesas
        "count": int,                 # quantidade de despesas
    }
]
# Ordenado por total DESC
```

---

## TDD

### Passo 1: Escrever testes (RED)

```python
class TestFinancialDashboardOverview:
    test_overview_basic  # retorna todos os campos
    test_overview_with_debts  # total_debt calcula corretamente
    test_months_until_break_even  # calcula meses até positivo
    test_months_until_break_even_already_positive  # retorna 0
    test_months_until_break_even_never  # retorna None se > 60 meses

class TestFinancialDashboardDebtByPerson:
    test_debt_per_person  # separa card e loan
    test_person_no_debt  # pessoa sem dívida retorna zeros
    test_multiple_persons  # lista todas as pessoas com expenses

class TestFinancialDashboardDebtByType:
    test_debt_by_type  # agrupa por tipo
    test_only_future_unpaid  # ignora parcelas pagas e passadas

class TestFinancialDashboardUpcoming:
    test_upcoming_30_days  # parcelas nos próximos 30 dias
    test_upcoming_custom_days  # days=7
    test_upcoming_excludes_paid  # não mostra parcelas pagas
    test_upcoming_ordering  # ordenado por due_date

class TestFinancialDashboardOverdue:
    test_overdue_installments  # parcelas vencidas não pagas
    test_overdue_excludes_paid  # não mostra pagas mesmo se vencidas
    test_days_overdue_calculation  # dias de atraso corretos

class TestFinancialDashboardCategoryBreakdown:
    test_breakdown_by_category  # agrupa por categoria
    test_null_category  # "Sem Categoria" para expenses sem category
    test_percentage_calculation  # percentuais somam ~100%
    test_empty_month  # mês sem despesas retorna lista vazia
```

### Passo 2-6: Ciclo TDD padrão

```bash
pytest tests/unit/test_financial/test_financial_dashboard_service.py -v
```

---

## Constraints

- Reutilize o CashFlowService onde fizer sentido (ex: `get_overview` pode chamar `get_monthly_cash_flow`)
- NÃO crie endpoints nesta sessão
- Use agregações do Django ORM (`Sum`, `Count`, `F`, `Q`, `Subquery`) sempre que possível
- Evite iterar querysets em Python quando o banco pode fazer a agregação

---

## Critérios de Aceite

- [ ] FinancialDashboardService criado com 6 métodos
- [ ] get_overview calcula months_until_break_even corretamente
- [ ] get_debt_by_person separa card vs loan
- [ ] get_upcoming/overdue filtram e ordenam corretamente
- [ ] get_expense_category_breakdown inclui "Sem Categoria" para null
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add FinancialDashboardService with aggregations`
