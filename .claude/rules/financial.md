---
paths:
  - "core/services/cash_flow_service.py"
  - "core/services/dashboard_service.py"
  - "core/models.py"
  - "core/serializers.py"
---

# Financial Module Rules

## Business Logic Constants
- Tag fee: R$50 for 1 tenant, R$80 for 2+ — logic in `fee_calculator.py`
- Late fee: 5% daily x (rental_value / 30) x days_late — logic in `fee_calculator.py`
- All monetary values use `DecimalField(max_digits=10, decimal_places=2)`
- Currency display: R$ 1.500,00 (Brazilian format)
- Date display: DD/MM/YYYY

## Financial Models Patterns
- Expense types: 9 types (TextChoices) — each type has specific required fields
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
