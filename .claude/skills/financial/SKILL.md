---
name: financial
description: Use when implementing any financial logic — expenses, income, cash flow, installments, projections, simulations, dashboard financeiro, or payment tracking. Covers the complete financial module including the complex rules for rent, owners, prepaid, salary-offset, credit cards, loans, and person summaries.
argument-hint: "[what-to-implement]"
---

# Financial Module Implementation Guide

Current branch: !`git branch --show-current`
Financial design: see `docs/plans/2026-03-21-financial-module-design.md`

## Domain Knowledge — CRITICAL

Before writing any financial logic, internalize these business rules:

### Receitas (Entradas)

| Fonte | Regra |
|-------|-------|
| Aluguel normal | Apenas apartamentos SEM `owner` (pertencentes aos sogros) contam como receita |
| Apartamento com owner | Aluguel é SAÍDA (repasse ao proprietário), NÃO receita |
| Aluguel pré-pago (`prepaid_until`) | NÃO gera receita mensal durante o período — dinheiro já foi recebido |
| Aluguel como salário (`is_salary_offset`) | NUNCA conta como entrada — compensado no salário da funcionária |
| Receitas extras | Aposentadoria, valores avulsos — registradas manualmente como `Income` |
| Receitas recorrentes | Projetam `expected_monthly_amount` para meses futuros |

### Despesas (Saídas)

| Tipo | Regra |
|------|-------|
| Repasse ao owner | Aluguel de apt com owner vai como saída (obrigação mensal) |
| Estipêndio fixo | Rodrigo R$1.100, Junior R$1.100 — `PersonIncome(type=fixed_stipend)` |
| Cartões de crédito | Parcelas via `ExpenseInstallment`, due_date calculada com `CreditCard.due_day` |
| Empréstimos bancários | Parcelas fixas com juros, em nome dos filhos/genro |
| Empréstimos pessoais | Informais, podem ser parcelados ou valor único |
| Contas consumo (água/luz) | Por prédio, valor variável mensal + parcelamento de dívida separado |
| IPTU | Por prédio, parcelas anuais + parcelamento de dívida de IPTU atrasado |
| Gastos fixos recorrentes | Internet, ração, gasolina — `is_recurring=True` com `expected_monthly_amount` |
| Gastos únicos | Manutenções, compras — aparecem só no mês em que ocorrem |
| Salário funcionária (Rosa) | base_salary + variable_amount, aluguel compensado (informativo, sem movimentação) |

### Fluxo de Caixa

```
Receita bruta (aluguéis sem owner + extras)
- Repasses aos proprietários
- Estipêndios fixos
- Parcelas de cartões (todas as pessoas)
- Parcelas de empréstimos
- Contas consumo (água + luz)
- Parcelamentos de dívida
- IPTU
- Salário funcionária
- Gastos fixos recorrentes
- Gastos únicos do mês
= Saldo do mês
```

**Meses passados**: dados reais (`is_paid=True`)
**Meses futuros**: projeção com base em leases ativos, parcelas futuras, gastos recorrentes (`expected_monthly_amount`), consumo (média 3 meses)

### Simulação "E se"

6 cenários (efêmeros, sem persistência):
- `pay_off_early`: remove parcelas futuras de despesa parcelada
- `change_rent`: altera receita de um kitnet
- `new_loan`: adiciona nova obrigação parcelada
- `remove_tenant`: zera receita do kitnet
- `add_fixed_expense`: adiciona saída mensal
- `remove_fixed_expense`: remove saída mensal

Compare retorna: `base_balance vs simulated_balance + delta` por mês

## Services Architecture

| Service | Responsabilidade |
|---------|-----------------|
| `CashFlowService` | `get_monthly_income`, `get_monthly_expenses`, `get_monthly_cash_flow`, `get_cash_flow_projection`, `get_person_summary` |
| `FinancialDashboardService` | `get_overview`, `get_debt_by_person`, `get_debt_by_type`, `get_upcoming_installments`, `get_overdue_installments`, `get_expense_category_breakdown` |
| `SimulationService` | `simulate(base_projection, scenarios)`, `compare(base, simulated)` |

All services are stateless functions in `core/services/`. Use Django ORM aggregations (`annotate`, `aggregate`) for dashboard queries — never raw SQL.

## Models Reference

10 financial models (migration 0012):
- `Person`, `CreditCard`, `ExpenseCategory`
- `Expense` (9 types via TextChoices), `ExpenseInstallment`
- `PersonIncome` (apartment_rent, fixed_stipend)
- `Income`, `RentPayment`, `EmployeePayment`
- `FinancialSettings` (singleton, pk=1)

Alterações em existentes:
- `Apartment.owner` (FK Person) — apartamentos com dono
- `Lease.prepaid_until` — aluguel pré-pago
- `Lease.is_salary_offset` — aluguel compensado como salário

## Implementation Checklist

When implementing financial logic:

1. Check which business rules apply (owner, prepaid, salary_offset, etc.)
2. Verify `Expense.expense_type` — each type has required fields
3. Installment generation: use `CreditCard.due_day` for card purchases
4. Cash flow projection: real data for past, projected for future
5. All monetary values: `DecimalField(max_digits=12, decimal_places=2)`
6. Currency display: R$ 1.500,00 (Brazilian format)
7. Date display: DD/MM/YYYY
8. Error messages in Portuguese for user-facing, English for logs

## Frontend Patterns

- Expense form adapts fields based on `expense_type` (use `watch()` from RHF)
- Cascading filters: person → credit_card (filter cards by selected person)
- Installments: view in Sheet/Drawer, mark_paid via PATCH
- Dashboard: 6 independent widgets, each with its own hook
- Simulator: ephemeral state (useState), no persistence
- Charts: Recharts — ComposedChart for bar+line, PieChart for breakdowns
- Person summary cards: grid layout showing receives, cards, loans, net
