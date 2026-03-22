# Sessão 06 — Backend: CashFlowService + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seções 2.4 (Fluxo de Caixa) e 4.1 (CashFlowService)
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia estes exemplares:
- `@core/services/fee_calculator.py` — Padrão de service com @staticmethod e Decimal
- `@core/services/dashboard_service.py` — Padrão de service com agregações ORM

Leia os models financeiros:
- `@core/models.py` — Modelos financeiros (final do arquivo)

---

## Escopo

### Arquivos a CRIAR
- `core/services/cash_flow_service.py`
- `tests/unit/test_financial/test_cash_flow_service.py`

### Arquivos a MODIFICAR
- Nenhum

---

## Especificação

### CashFlowService

Classe com métodos estáticos. Todos os valores monetários usam `Decimal`.

**Método 1: `get_monthly_income(year: int, month: int) -> dict`**

Calcula receitas do mês:

```python
{
    "rent_income": Decimal,       # soma de rental_value dos leases ativos
                                  # EXCLUI: apartments com owner (não são receita do condomínio)
                                  # EXCLUI: leases com prepaid_until >= mês consultado
                                  # EXCLUI: leases com is_salary_offset=True
    "rent_details": [             # detalhe por kitnet
        {
            "apartment_id": int,
            "apartment_number": str,
            "building_name": str,
            "tenant_name": str,
            "rental_value": Decimal,
            "is_paid": bool,      # existe RentPayment para esse mês?
            "payment_date": date | None,
        }
    ],
    "extra_income": Decimal,      # soma de Income do mês (is_received=True) + projeção de recorrentes
    "extra_income_details": [...],
    "total": Decimal,
}
```

**Lógica para receitas de aluguel:**
1. Buscar todos os leases ativos
2. Excluir leases cujo `apartment.owner` não é null (aluguel vai para o proprietário, não para o condomínio)
3. Excluir leases com `prepaid_until >= date(year, month, 1)` (já pago — ex: kitnet 113/836 pago até 29/09/2026)
4. Excluir leases com `is_salary_offset=True` (compensado no salário — ex: kitnet 206/850, funcionária Rosa)
5. Para cada lease restante, verificar se existe `RentPayment` para aquele `reference_month`

**Nota**: O sistema de aluguel é "pagar para morar" — o inquilino paga no dia X para morar do dia X ao dia X do mês seguinte. O `reference_month` no RentPayment representa o mês em que o pagamento foi feito (ex: 2026-03-01 = pagamento feito em março).

**Método 2: `get_monthly_expenses(year: int, month: int) -> dict`**

Calcula despesas do mês:

```python
{
    "owner_repayments": Decimal,       # aluguel repassado aos proprietários
    "owner_repayments_details": [...], # por proprietário + apartamento
    "person_stipends": Decimal,        # estipêndios fixos (PersonIncome type=fixed_stipend)
    "person_stipends_details": [...],
    "card_installments": Decimal,      # parcelas de cartão vencendo no mês
    "card_installments_details": [...], # agrupado por pessoa → cartão
    "loan_installments": Decimal,      # parcelas de empréstimo vencendo no mês
    "loan_installments_details": [...],
    "utility_bills": Decimal,          # contas de consumo do mês
    "utility_bills_details": [...],    # por prédio + tipo (água/luz)
    "debt_installments": Decimal,      # parcelas de dívida negociada
    "debt_installments_details": [...],
    "property_tax": Decimal,           # IPTU do mês
    "property_tax_details": [...],
    "employee_salary": Decimal,        # salário funcionária
    "employee_salary_details": [...],
    "fixed_expenses": Decimal,         # gastos fixos recorrentes
    "fixed_expenses_details": [...],
    "one_time_expenses": Decimal,      # gastos únicos do mês
    "one_time_expenses_details": [...],
    "total": Decimal,
}
```

**Lógica para despesas:**
1. **owner_repayments**: Para cada apartment com owner que tem lease ativo → rental_value é saída (repasse ao proprietário)
2. **person_stipends**: PersonIncome com type=fixed_stipend e is_active=True → fixed_amount é saída
3. **card_installments**: ExpenseInstallment com due_date no mês e expense.expense_type=card_purchase
4. **loan_installments**: ExpenseInstallment com due_date no mês e expense.expense_type in (bank_loan, personal_loan)
5. **utility_bills**: Expense com expense_type in (water_bill, electricity_bill) e is_debt_installment=False e expense_date no mês
6. **debt_installments**: ExpenseInstallment com due_date no mês e expense.is_debt_installment=True
7. **property_tax**: ExpenseInstallment com due_date no mês e expense.expense_type=property_tax
8. **employee_salary**: EmployeePayment com reference_month no mês → total_paid
9. **fixed_expenses**: Expense com expense_type=fixed_expense e is_recurring=True → expected_monthly_amount
10. **one_time_expenses**: Expense com expense_type=one_time_expense e expense_date no mês

**Método 3: `get_monthly_cash_flow(year: int, month: int) -> dict`**

```python
{
    "year": int,
    "month": int,
    "income": <resultado de get_monthly_income>,
    "expenses": <resultado de get_monthly_expenses>,
    "balance": income["total"] - expenses["total"],
}
```

**Método 4: `get_cash_flow_projection(months: int = 12) -> list[dict]`**

Projeta fluxo de caixa para N meses a partir do mês atual.

Para meses futuros sem dados registrados:
- **Aluguéis**: Leases ativos projetados (mesma lógica de income, sem verificar RentPayment)
- **Parcelas**: ExpenseInstallments com due_date futura → conhecidas
- **Contas de consumo**: Média dos últimos 3 meses registrados para aquele prédio/tipo
- **Gastos fixos**: expected_monthly_amount
- **Receitas extras recorrentes**: expected_monthly_amount

Retorna:
```python
[
    {
        "year": int,
        "month": int,
        "income_total": Decimal,
        "expenses_total": Decimal,
        "balance": Decimal,
        "cumulative_balance": Decimal,  # soma acumulada desde saldo inicial (FinancialSettings)
        "is_projected": bool,           # True se mês futuro
    }
]
```

**Método 5: `get_person_summary(person_id: int, year: int, month: int) -> dict`**

```python
{
    "person_id": int,
    "person_name": str,
    "receives": Decimal,              # aluguel dos kitnets ou estipêndio
    "receives_details": [...],
    "card_total": Decimal,            # total parcelas de cartão no mês
    "card_details": [...],            # por cartão
    "loan_total": Decimal,            # total parcelas de empréstimo
    "loan_details": [...],
    "net_amount": Decimal,            # receives + card_total + loan_total
}
```

---

## TDD

### Passo 1: Escrever testes (RED)

```python
class TestCashFlowServiceMonthlyIncome:
    test_rent_income_basic  # aluguéis ativos somados
    test_rent_excludes_owner_apartments  # apts com owner não contam
    test_rent_excludes_prepaid  # lease com prepaid_until futuro não conta
    test_rent_excludes_salary_offset  # lease salary_offset não conta
    test_rent_shows_payment_status  # is_paid=True quando RentPayment existe
    test_extra_income  # receitas extras do mês
    test_extra_income_recurring  # receitas recorrentes projetadas

class TestCashFlowServiceMonthlyExpenses:
    test_owner_repayments  # apts com owner geram saída
    test_person_stipends  # estipêndios fixos
    test_card_installments  # parcelas de cartão no mês
    test_loan_installments  # parcelas de empréstimo no mês
    test_utility_bills  # contas de consumo
    test_debt_installments  # parcelas de dívida
    test_property_tax  # IPTU
    test_employee_salary  # salário funcionária
    test_fixed_expenses  # gastos fixos recorrentes
    test_one_time_expenses  # gastos únicos

class TestCashFlowServiceMonthlyCashFlow:
    test_balance_calculation  # income - expenses = balance
    test_negative_balance  # quando despesas > receitas

class TestCashFlowServiceProjection:
    test_projection_12_months  # retorna 12 meses
    test_cumulative_balance_from_initial  # começa do saldo inicial
    test_future_months_projected  # is_projected=True
    test_utility_average_projection  # usa média dos últimos 3 meses
    test_known_installments_projected  # parcelas futuras aparecem

class TestCashFlowServicePersonSummary:
    test_owner_receives_rent  # proprietário recebe aluguel
    test_stipend_person_receives_fixed  # estipêndio fixo
    test_card_total  # soma parcelas de cartão
    test_loan_total  # soma parcelas de empréstimo
    test_net_amount  # receives + card + loan
```

### Passo 2-6: Ciclo TDD padrão

```bash
pytest tests/unit/test_financial/test_cash_flow_service.py -v
```

---

## Constraints

- NÃO crie endpoints nesta sessão — apenas o service
- Use `Decimal` para TODOS os cálculos monetários, nunca float
- Use `from datetime import date` para comparações de data
- Queries devem ser otimizadas: use `select_related`/`prefetch_related`, evite N+1
- Para projeção de contas de consumo, se não houver histórico, retorne Decimal('0')

---

## Critérios de Aceite

- [ ] CashFlowService criado com 5 métodos
- [ ] get_monthly_income exclui corretamente owner/prepaid/salary_offset
- [ ] get_monthly_expenses calcula corretamente todas as 10 categorias
- [ ] get_cash_flow_projection acumula saldo a partir do FinancialSettings.initial_balance
- [ ] get_person_summary calcula net_amount corretamente
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add CashFlowService with monthly calculation and projection`
