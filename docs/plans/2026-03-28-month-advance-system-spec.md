# Sistema de Avanço de Mês — Especificação Funcional (Gerenciador de Condomínios)

Documento de referência que descreve como o sistema de avanço de mês deve funcionar no gerenciador de condomínios, baseado na experiência do financial-control-ts e nas particularidades deste sistema.

---

## Diferenças fundamentais vs financial-control-ts

| Aspecto | financial-control-ts | gerenciador_condominios |
|---------|---------------------|------------------------|
| Arquitetura | Clean Architecture (domain/application/infra) | Django MVT + Service Layer |
| Entidades financeiras | CreditCard com sub-entidades (Installment, FixedCharge, MonthlyExpense, Refund) | Expense com ExpenseInstallment + tipos variados |
| Billing period | `currentBillingMonth/Year` no CreditCard | Sem tracking de período — tudo calculado on-demand |
| Histórico | Archives + snapshots | Nenhum — dados vivos, sem snapshots |
| Parcelas | Entity Installment separada, avança com progressToNextMonth() | ExpenseInstallment com due_date fixa, is_paid toggle |
| Contas recorrentes | RecurringBill template → MonthlyBill instância | Expense com is_recurring=True, sem instâncias mensais |
| Aluguéis | IncomeSource genérico | Lease com rental_value, RentPayment por mês |
| Pagamentos pessoa | FamilyLoanMonthlyPayment | PersonPayment + PersonPaymentSchedule |
| Offset/desconto | Não tem | is_offset=True (desconto, subtrai do total do condomínio) |

## Conceitos do sistema

### O que "avançar o mês" significa neste contexto

No gerenciador_condominios, a maioria dos dados já tem referência temporal (due_date, reference_month, expense_date). O avanço de mês aqui é mais sobre:

1. **Snapshot/Archive**: Congelar o estado financeiro do mês que está fechando
2. **Validação**: Verificar que todas as obrigações do mês foram registradas
3. **Transição**: Preparar o próximo mês (contas de água/luz precisam ser adicionadas manualmente)

### O que NÃO precisa avançar automaticamente

- **ExpenseInstallments**: Já têm `due_date` fixa por parcela. Não precisam ser "avançadas" — cada parcela é independente com sua data.
- **RentPayments**: Cada pagamento é um registro separado por `reference_month`. O próximo mês simplesmente terá novos RentPayments a serem criados.
- **EmployeePayments**: Mesma lógica — cada mês tem seu registro.
- **Expenses com is_recurring=True**: Já são projetadas pelo CashFlowService via `recurrence_day` e `end_date`. Não precisam de instâncias mensais.

### O que PRECISA do avanço de mês

1. **MonthSnapshot**: Congelar totais de receitas, despesas, saldo, detalhamento
2. **Validação pré-avanço**: Todas as parcelas do mês estão pagas? Aluguéis recebidos? Funcionários pagos?
3. **Alertas**: Contas de água/luz/gás ainda não registradas para o mês?
4. **PersonPaymentSchedule**: Verificar se os pagamentos programados foram feitos

---

## 1. MonthSnapshot (Novo modelo)

### Campos

```python
class MonthSnapshot(AuditMixin, models.Model):
    reference_month = models.DateField()  # 1st of month

    # Receitas
    total_rent_income = models.DecimalField(max_digits=12, decimal_places=2)
    total_extra_income = models.DecimalField(max_digits=12, decimal_places=2)
    total_person_payments_received = models.DecimalField(max_digits=12, decimal_places=2)
    total_income = models.DecimalField(max_digits=12, decimal_places=2)

    # Despesas
    total_card_installments = models.DecimalField(max_digits=12, decimal_places=2)
    total_loan_installments = models.DecimalField(max_digits=12, decimal_places=2)
    total_utility_bills = models.DecimalField(max_digits=12, decimal_places=2)
    total_fixed_expenses = models.DecimalField(max_digits=12, decimal_places=2)
    total_one_time_expenses = models.DecimalField(max_digits=12, decimal_places=2)
    total_employee_salary = models.DecimalField(max_digits=12, decimal_places=2)
    total_owner_repayments = models.DecimalField(max_digits=12, decimal_places=2)
    total_person_stipends = models.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2)

    # Saldo
    net_balance = models.DecimalField(max_digits=12, decimal_places=2)

    # Detalhamento
    detailed_breakdown = models.JSONField()  # Full breakdown por categoria

    # Metadata
    is_finalized = models.BooleanField(default=False)  # True when month is "closed"
    finalized_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('reference_month',)
        ordering = ['-reference_month']
```

### O que o breakdown JSON deve conter

```json
{
  "rent_details": [
    { "lease_id": 1, "apartment": "113/836", "tenant": "João", "amount": 1400, "is_paid": true, "paid_date": "2026-03-05" }
  ],
  "extra_income_details": [...],
  "card_installments": [
    { "expense_id": 5, "description": "Notebook", "person": "Alvaro", "card": "Nubank ****1234", "installment": "3/12", "amount": 281.60, "is_paid": true }
  ],
  "loan_installments": [...],
  "utility_bills": [...],
  "fixed_expenses": [...],
  "one_time_expenses": [...],
  "employee_salaries": [...],
  "owner_repayments": [...],
  "person_stipends": [...],
  "person_payments": [...],
  "validation_warnings": [
    "Conta de água do prédio 836 não registrada",
    "Aluguel do apto 201/850 não pago"
  ]
}
```

---

## 2. Pipeline de Avanço de Mês

### Fase 0 — Validação

Verificar antes de avançar:

1. **Aluguéis**: Para cada lease ativo (excluindo prepaid e salary_offset), verificar se existe RentPayment para o reference_month
2. **Parcelas**: Para cada ExpenseInstallment com due_date no mês, verificar is_paid
3. **Funcionários**: Para cada Person com is_employee=True, verificar se existe EmployeePayment para o mês
4. **Contas de serviço**: Verificar se existem Expenses de tipo water_bill e electricity_bill para o mês (ALERTAR se não existem — precisam ser adicionadas manualmente)
5. **PersonPaymentSchedule**: Para cada schedule ativo no mês, verificar se PersonPayment correspondente existe

Se houver items não pagos ou faltantes:
- Retornar lista de warnings
- Permitir avanço com `force=True` (registrar warnings no snapshot)

### Fase 1 — Criar MonthSnapshot

Usar o CashFlowService existente:
```python
income_data = cash_flow_service.get_monthly_income(year, month)
expense_data = cash_flow_service.get_monthly_expenses(year, month)
```

Construir o snapshot com os dados retornados + breakdown detalhado.

### Fase 2 — Marcar mês como finalizado

- Setar `is_finalized = True` no MonthSnapshot
- Registrar `finalized_at = now()`
- Incluir `validation_warnings` no breakdown

### Fase 3 — Preparar próximo mês (informativo)

Não há mutações a fazer no próximo mês (as parcelas já têm due_dates, os aluguéis são calculados on-demand). Mas retornar informações úteis:

- Quais parcelas vencem no próximo mês
- Quais aluguéis são esperados
- Quais contas de serviço precisam ser adicionadas manualmente
- Quais pagamentos de funcionários precisam ser criados

---

## 3. Rollback

Simplesmente deletar o MonthSnapshot do mês. Como NÃO há mutações nos dados originais (tudo é calculado on-demand), o rollback é trivial — deletar o snapshot e o mês volta a ser "aberto".

---

## 4. API Endpoints

```
POST /api/month-advance/advance/
  Body: { "year": 2026, "month": 3, "force": false }
  Response: { "success": true, "snapshot_id": 1, "warnings": [...], "next_month_preview": {...} }

POST /api/month-advance/rollback/
  Body: { "year": 2026, "month": 3, "confirm": true }
  Response: { "success": true }

GET /api/month-advance/snapshots/
  Query: ?year=2026
  Response: [{ "reference_month": "2026-03-01", "is_finalized": true, "total_income": ..., "total_expenses": ..., "net_balance": ... }]

GET /api/month-advance/snapshots/{year}/{month}/
  Response: { full snapshot with breakdown }

GET /api/month-advance/status/
  Query: ?year=2026&month=3
  Response: { "is_finalized": false, "validation": { "unpaid_rent": [...], "unpaid_installments": [...], "missing_bills": [...] } }
```

---

## 5. Diferença-chave vs financial-control-ts

**No financial-control-ts**, o avanço de mês é uma operação PESADA que muta dados:
- Avança parcelas (currentInstallment++)
- Arquiva expenses/refunds
- Avança billing periods
- Cria archives com breakdown

**No gerenciador_condominios**, o avanço de mês é uma operação LEVE:
- Apenas SNAPSHOT — congela os dados calculados on-demand
- NÃO muta nenhum dado existente
- Parcelas já têm due_dates fixas (não precisam avançar)
- Aluguéis/pagamentos de funcionários são registros por mês (não avançam)
- O rollback é trivial (deletar o snapshot)

Isso é possível porque o design do banco de dados do gerenciador_condominios é fundamentalmente diferente — cada item financeiro tem sua própria referência temporal, em vez de depender de um "billing period" central.
