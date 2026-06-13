---
paths:
  - "core/services/cash_flow_service.py"
  - "core/services/financial_dashboard_service.py"
  - "core/services/simulation_service.py"
  - "core/services/expense_service.py"
  - "core/services/daily_control_service.py"
  - "core/services/rent_schedule_service.py"
---

# Financial Module Rules

## Business Logic Constants
- Tag fee: R$20 for 1 tenant, R$40 for 2+ (defaults `DEFAULT_TAG_FEE_SINGLE/MULTIPLE` in settings.py) — logic in `fee_calculator.py`
- Late fee: 5% daily x (rental_value / 30) x days_late — logic in `fee_calculator.py`
- Monetary values use `DecimalField(decimal_places=2)`; `max_digits` varies (10 in the legacy patrimonial models, 12 in the financial / `finances` models)
- NOTE: this file documents the LEGACY personal-financial module (`core` Person/Expense/RentPayment); the condominium money rules live in docs/FINANCES.md
- Currency display: R$ 1.500,00 (Brazilian format)
- Date display: DD/MM/YYYY

## Financial Models Patterns
- Expense types: `ExpenseType` TextChoices in `core/models.py` (source of truth) — each type has specific required fields
- ExpenseInstallment: auto-generated from Expense when is_installment=True
- CreditCard due_day affects installment due dates
- PersonIncome: apartment_rent or fixed_stipend types
- RentPayment: unique per (lease, reference_month)
- EmployeePayment: total_paid = base_salary + variable_amount
- FinancialSettings: singleton (forces pk=1)

## Cash Flow Service
- Monthly projections must account for: rent, cleaning fees, tag fees, expenses, installments, income, employee payments
- Recurring expenses/income project forward based on recurrence_day
- Debt installments use credit card due_day for scheduling
- Person summary aggregates all income sources and expenses per person

## Dashboard Service
- All aggregations use Django ORM (annotate, aggregate) — never raw SQL
- Debt calculations must include both direct expenses and installments
- Category breakdown uses ExpenseCategory colors for chart rendering

## Simulation Service
- Scenarios are ephemeral — no database persistence
- compare() method returns base vs simulated cash flow side-by-side
- Scenarios: pay_off_early, change_rent, new_loan, remove_tenant, add_fixed_expense, remove_fixed_expense
