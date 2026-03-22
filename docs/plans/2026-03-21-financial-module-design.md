# Módulo Financeiro — Design Completo

**Data**: 2026-03-21
**Autor**: Alvaro Souza
**Status**: Aprovado (design)

---

## 1. Contexto e Objetivo

O sistema atual gerencia prédios, apartamentos, inquilinos e contratos, mas não possui controle financeiro. A receita dos aluguéis sustenta os sogros do Alvaro, que acumularam dívidas distribuídas em cartões de crédito e empréstimos nos nomes dos filhos e genro. Não existe controle centralizado dessas obrigações.

**Objetivo**: Implementar um módulo financeiro completo que permita:
- Registrar todas as saídas (cartões, empréstimos, contas, IPTU, gastos fixos/variáveis)
- Registrar todas as entradas (aluguéis, receitas extras)
- Visualizar fluxo de caixa mensal real e projetado (12 meses)
- Simular cenários "e se" para equilibrar o caixa
- Dar acesso de visualização aos filhos/familiares

---

## 2. Regras de Negócio

### 2.1 Pessoas e Papéis

| Pessoa | Relação | Proprietário | Recebe |
|--------|---------|-------------|--------|
| Rodrigo | Filho | Não | Estipêndio fixo R$1.100 + reembolso cartões/empréstimos |
| Tiago | Filho | Kitnets 101, 103 (prédio 836) | Aluguel dos kitnets + reembolso cartões/empréstimos |
| Alvaro | Genro | Kitnets 200, 203 (prédio 836) | Aluguel dos kitnets + reembolso cartões/empréstimos |
| Junior | Filho | Não | Estipêndio fixo R$1.100 + reembolso cartões/empréstimos |
| Rosa | Funcionária | Não | R$800 fixo + variável por serviços extras. Mora no kitnet 206/850 (aluguel compensado) |

### 2.2 Receitas (Entradas)

- **Aluguel**: Apenas apartamentos sem `owner` (pertencentes aos sogros) contam como receita do condomínio
- **Apartamentos com owner**: O aluguel é repassado ao proprietário — não é receita do condomínio, é uma obrigação de saída
- **Aluguel pré-pago**: Kitnet 113/836 — inquilina pagou R$20.700 em 23/04/2025 (18x R$1.150). Mudou para kitnet de R$1.300 em jan/2026. Crédito recalculado: 9 meses a R$1.150 + 8 meses a R$1.300. Pago até 29/09/2026. Não gera receita mensal durante o período (dinheiro já foi recebido e gasto)
- **Aluguel como salário**: Kitnet 206/850 — Rosa (funcionária), o aluguel é compensado no salário, nunca conta como entrada
- **Sistema "pagar para morar"**: Todos os aluguéis seguem o sistema onde o inquilino paga no dia X para morar do dia X até o dia X do mês seguinte (ex: paga dia 10/fev = período 10/fev a 10/mar)
- **Receitas extras**: Aposentadoria, valores avulsos de outras fontes — registradas manualmente

### 2.3 Despesas (Saídas)

#### Cartões de Crédito
- Cada pessoa pode ter N cartões
- Cada cartão tem compras, que podem ser à vista ou parceladas
- As compras misturam despesas do condomínio e pessoais dos sogros
- O condomínio reembolsa o total da fatura
- Categorização é opcional (o que conseguir categorizar, categoriza)

#### Empréstimos
- **Bancários**: Formais, em nome dos filhos/genro. Têm contrato, juros, parcelas fixas
- **Pessoais**: Informais, entre familiares. Podem ser parcelados ou valor único

#### Contas de Consumo (Água e Luz)
- Cada prédio tem suas contas separadas
- **Consumo mensal**: Valor variável, registrado todo mês
- **Parcelamento de dívida**: Dívida acumulada negociada em parcelas fixas (pode coexistir com o consumo mensal)

#### IPTU
- Por prédio (não por apartamento — os prédios não são cadastrados como múltiplos kitnets)
- **Parcelas anuais**: IPTU do ano corrente, parcelado pela prefeitura
- **Parcelamento de dívida**: Dívida de IPTU atrasado negociada separadamente

#### Gastos Fixos Recorrentes
- Internet por prédio e sítio
- Ração para galinhas (sítio)
- Gasolina
- Outros gastos mensais previsíveis

#### Gastos Únicos
- Manutenções, compras, consertos — aparecem só no mês em que ocorrem

#### Funcionária (Rosa)
- Mora no kitnet 206/850 (aluguel compensado — não entra nem sai do caixa)
- Recebe salário com 3 componentes:
  - Valor fixo mensal: R$800
  - Valor variável por serviços extras realizados no mês (faxinas em kitnets desocupados, etc.)
  - Compensação do aluguel (informativo, sem movimentação de caixa)

### 2.4 Fluxo de Caixa

**Cálculo mensal:**
```
Receita bruta (aluguéis dos kitnets dos sogros + receitas extras)
- Repasses aos proprietários (aluguéis dos kitnets com owner)
- Estipêndios fixos (Rodrigo R$1.100, Junior R$1.100)
- Total parcelas de cartões (todas as pessoas)
- Total parcelas de empréstimos (bancários + pessoais)
- Contas de consumo (água + luz de todos os prédios)
- Parcelamentos de dívida (água + luz + IPTU)
- Parcelas IPTU anual
- Salário funcionária
- Gastos fixos recorrentes
- Gastos únicos do mês
= Saldo do mês
```

**Meses passados**: Usa dados reais (pagamentos registrados como `is_paid`).
**Meses futuros**: Projeta com base em:
- Leases ativos → receita esperada (exceto pré-pagos e salary-offset)
- Parcelas com vencimento futuro → saídas conhecidas
- Gastos fixos recorrentes → `expected_monthly_amount`
- Contas de consumo → média dos últimos 3 meses registrados
- Receitas extras recorrentes → valor registrado

### 2.5 Simulação "E se"

Cenários aplicáveis sobre o fluxo projetado (sem alterar dados reais):
- Quitar antecipado um cartão/empréstimo → remove parcelas futuras
- Aumentar/diminuir aluguel de um kitnet → recalcula receita
- Novo empréstimo → adiciona parcelas futuras
- Inquilino saiu → zera receita daquele kitnet
- Nova despesa fixa → adiciona saída mensal
- Remover despesa fixa → remove saída mensal

Exibe comparativo: **fluxo atual vs. fluxo simulado**, mês a mês, por 12 meses.

---

## 3. Modelos de Dados

### 3.1 Novos Modelos

Todos os modelos herdam `AuditMixin` + `SoftDeleteMixin`.

#### `Person` (Pessoa/Credor)

```python
class Person(AuditMixin, SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50)  # filho, genro, funcionária
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_owner = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=False)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
```

#### `CreditCard` (Cartão de Crédito)

```python
class CreditCard(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name='credit_cards', on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100)  # "Nubank Rodrigo"
    last_four_digits = models.CharField(max_length=4, blank=True)
    closing_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    due_day = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    is_active = models.BooleanField(default=True)
```

#### `ExpenseCategory` (Categoria de Despesa)

```python
class ExpenseCategory(AuditMixin, SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6B7280')  # hex para dashboard
```

#### `Expense` (Despesa)

```python
class ExpenseType(models.TextChoices):
    CARD_PURCHASE = 'card_purchase', 'Compra no Cartão'
    BANK_LOAN = 'bank_loan', 'Empréstimo Bancário'
    PERSONAL_LOAN = 'personal_loan', 'Empréstimo Pessoal'
    WATER_BILL = 'water_bill', 'Conta de Água'
    ELECTRICITY_BILL = 'electricity_bill', 'Conta de Luz'
    PROPERTY_TAX = 'property_tax', 'IPTU'
    FIXED_EXPENSE = 'fixed_expense', 'Gasto Fixo Mensal'
    ONE_TIME_EXPENSE = 'one_time_expense', 'Gasto Único'
    EMPLOYEE_SALARY = 'employee_salary', 'Salário Funcionário'

class Expense(AuditMixin, SoftDeleteMixin, models.Model):
    description = models.CharField(max_length=500)
    expense_type = models.CharField(max_length=30, choices=ExpenseType.choices)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()

    # Relacionamentos opcionais
    person = models.ForeignKey(Person, null=True, blank=True, related_name='expenses', on_delete=models.SET_NULL)
    credit_card = models.ForeignKey(CreditCard, null=True, blank=True, related_name='expenses', on_delete=models.SET_NULL)
    building = models.ForeignKey('Building', null=True, blank=True, related_name='expenses', on_delete=models.SET_NULL)
    category = models.ForeignKey(ExpenseCategory, null=True, blank=True, related_name='expenses', on_delete=models.SET_NULL)

    # Parcelamento
    is_installment = models.BooleanField(default=False)
    total_installments = models.PositiveIntegerField(null=True, blank=True)

    # Dívida negociada (água/luz/IPTU atrasados)
    is_debt_installment = models.BooleanField(default=False)

    # Recorrência (gastos fixos mensais)
    is_recurring = models.BooleanField(default=False)
    expected_monthly_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    recurrence_day = models.PositiveSmallIntegerField(null=True, blank=True)  # dia do mês

    # Pagamento (para despesas não-parceladas)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)

    # Campos específicos de empréstimo bancário
    bank_name = models.CharField(max_length=100, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['expense_type']),
            models.Index(fields=['expense_date']),
            models.Index(fields=['is_paid']),
            models.Index(fields=['person', 'expense_type']),
            models.Index(fields=['building', 'expense_type']),
        ]
```

#### `ExpenseInstallment` (Parcela)

```python
class ExpenseInstallment(AuditMixin, SoftDeleteMixin, models.Model):
    expense = models.ForeignKey(Expense, related_name='installments', on_delete=models.CASCADE)
    installment_number = models.PositiveIntegerField()
    total_installments = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['expense', 'installment_number']
        ordering = ['due_date', 'installment_number']
        indexes = [
            models.Index(fields=['due_date']),
            models.Index(fields=['is_paid']),
            models.Index(fields=['due_date', 'is_paid']),
        ]
```

#### `PersonIncome` (Direito de Recebimento)

```python
class PersonIncomeType(models.TextChoices):
    APARTMENT_RENT = 'apartment_rent', 'Aluguel de Apartamento'
    FIXED_STIPEND = 'fixed_stipend', 'Estipêndio Fixo'

class PersonIncome(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name='incomes', on_delete=models.CASCADE)
    income_type = models.CharField(max_length=20, choices=PersonIncomeType.choices)
    apartment = models.ForeignKey('Apartment', null=True, blank=True, on_delete=models.SET_NULL)  # para apartment_rent
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # para fixed_stipend
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # null = vigente indefinidamente
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
```

#### `Income` (Receita Extra)

```python
class Income(AuditMixin, SoftDeleteMixin, models.Model):
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    income_date = models.DateField()
    person = models.ForeignKey(Person, null=True, blank=True, related_name='extra_incomes', on_delete=models.SET_NULL)
    building = models.ForeignKey('Building', null=True, blank=True, related_name='extra_incomes', on_delete=models.SET_NULL)
    category = models.ForeignKey(ExpenseCategory, null=True, blank=True, on_delete=models.SET_NULL)
    is_recurring = models.BooleanField(default=False)
    expected_monthly_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_received = models.BooleanField(default=False)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
```

#### `RentPayment` (Pagamento de Aluguel)

```python
class RentPayment(AuditMixin, SoftDeleteMixin, models.Model):
    lease = models.ForeignKey('Lease', related_name='rent_payments', on_delete=models.CASCADE)
    reference_month = models.DateField()  # primeiro dia do mês de referência (ex: 2026-03-01)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['lease', 'reference_month']
        ordering = ['-reference_month']
        indexes = [
            models.Index(fields=['reference_month']),
            models.Index(fields=['payment_date']),
        ]
```

#### `EmployeePayment` (Pagamento de Funcionário)

```python
class EmployeePayment(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, related_name='employee_payments', on_delete=models.CASCADE)
    reference_month = models.DateField()  # primeiro dia do mês
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)  # valor fixo
    variable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # faxinas
    rent_offset = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # aluguel compensado (informativo)
    cleaning_count = models.PositiveIntegerField(default=0)  # qtd faxinas no mês
    payment_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['person', 'reference_month']
        ordering = ['-reference_month']

    @property
    def total_paid(self):
        """Total efetivo saindo do caixa (sem rent_offset)."""
        return self.base_salary + self.variable_amount
```

#### `FinancialSettings` (Configurações Financeiras)

```python
class FinancialSettings(models.Model):
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    initial_balance_date = models.DateField()
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = 'Financial settings'

    def save(self, *args, **kwargs):
        """Singleton — só permite um registro."""
        self.pk = 1
        super().save(*args, **kwargs)
```

### 3.2 Alterações em Modelos Existentes

#### `Apartment` — novo campo

```python
owner = models.ForeignKey(
    'Person', null=True, blank=True,
    related_name='owned_apartments',
    on_delete=models.SET_NULL
)
```

#### `Lease` — novos campos

```python
prepaid_until = models.DateField(
    null=True, blank=True,
    help_text='Aluguel pré-pago até esta data. Não gera receita mensal durante o período.'
)
is_salary_offset = models.BooleanField(
    default=False,
    help_text='Aluguel compensado como salário. Nunca conta como receita.'
)
```

---

## 4. Camada de Serviços

### 4.1 `CashFlowService`

Serviço principal que monta o fluxo de caixa.

```python
class CashFlowService:
    @staticmethod
    def get_monthly_income(year: int, month: int) -> dict:
        """
        Retorna receitas do mês:
        - rent_income: aluguéis dos kitnets dos sogros (sem owner, sem prepaid, sem salary_offset)
        - extra_income: receitas extras registradas
        - total: soma
        """

    @staticmethod
    def get_monthly_expenses(year: int, month: int) -> dict:
        """
        Retorna despesas do mês agrupadas:
        - owner_repayments: aluguéis repassados a proprietários
        - person_stipends: estipêndios fixos (Rodrigo, Junior)
        - card_installments: parcelas de cartão (agrupadas por pessoa → cartão)
        - loan_installments: parcelas de empréstimo (agrupadas por pessoa, tipo)
        - utility_bills: contas de consumo (por prédio)
        - debt_installments: parcelamentos de dívida (por prédio, tipo)
        - property_tax: IPTU (por prédio)
        - employee_salary: salário da funcionária
        - fixed_expenses: gastos fixos recorrentes
        - one_time_expenses: gastos únicos
        - total: soma de tudo
        """

    @staticmethod
    def get_monthly_cash_flow(year: int, month: int) -> dict:
        """
        Combina income e expenses:
        - income: resultado de get_monthly_income
        - expenses: resultado de get_monthly_expenses
        - balance: income.total - expenses.total
        """

    @staticmethod
    def get_cash_flow_projection(months: int = 12) -> list[dict]:
        """
        Projeção para N meses a partir do mês atual.
        Meses passados usam dados reais (is_paid=True).
        Meses futuros usam:
        - Leases ativos → receita esperada
        - ExpenseInstallments com due_date no mês → saídas conhecidas
        - Expenses com is_recurring=True → expected_monthly_amount
        - Contas de consumo → média dos últimos 3 meses
        - PersonIncome → obrigações mensais
        - Receitas extras recorrentes → expected_monthly_amount
        Retorna lista de {year, month, income, expenses, balance, cumulative_balance}
        """

    @staticmethod
    def get_person_summary(person_id: int, year: int, month: int) -> dict:
        """
        Resumo financeiro de uma pessoa no mês:
        - receives: o que tem direito a receber (aluguel ou estipêndio)
        - card_total: total de parcelas dos cartões dela
        - loan_total: total de parcelas de empréstimos dela
        - net_amount: receives + card_total + loan_total (o que o condomínio deve pagar a ela)
        """
```

### 4.2 `SimulationService`

Motor de simulação "e se".

```python
class SimulationService:
    @staticmethod
    def simulate(
        base_projection: list[dict],
        scenarios: list[dict]
    ) -> list[dict]:
        """
        Aplica cenários sobre a projeção base e retorna projeção simulada.

        Cenários suportados:
        - {"type": "pay_off_early", "expense_id": int}
          Remove parcelas futuras de uma despesa parcelada

        - {"type": "change_rent", "apartment_id": int, "new_value": Decimal}
          Altera receita de um kitnet

        - {"type": "new_loan", "amount": Decimal, "installments": int, "start_month": str}
          Adiciona nova obrigação parcelada

        - {"type": "remove_tenant", "apartment_id": int}
          Zera receita de um kitnet

        - {"type": "add_fixed_expense", "amount": Decimal, "description": str}
          Adiciona gasto fixo mensal

        - {"type": "remove_fixed_expense", "expense_id": int}
          Remove gasto fixo mensal

        Retorna lista no mesmo formato da projeção, com campo extra
        `delta` por mês (diferença entre simulado e real).
        """

    @staticmethod
    def compare(
        base: list[dict],
        simulated: list[dict]
    ) -> dict:
        """
        Gera comparativo:
        - month_by_month: lista com {month, base_balance, simulated_balance, delta}
        - total_impact: soma dos deltas em 12 meses
        - break_even_month: mês em que o saldo simulado vira positivo (se aplicável)
        """
```

### 4.3 `FinancialDashboardService`

Agrega dados para os widgets do dashboard.

```python
class FinancialDashboardService:
    @staticmethod
    def get_overview() -> dict:
        """
        Visão geral:
        - current_month_balance: saldo do mês atual
        - total_debt: soma de todas as parcelas futuras pendentes
        - total_monthly_obligations: soma mensal de todas as obrigações
        - total_monthly_income: soma mensal de receitas esperadas
        - months_until_break_even: projeção de quando o saldo acumula positivo (ou None)
        """

    @staticmethod
    def get_debt_by_person() -> list[dict]:
        """Por pessoa: total cartões, total empréstimos, total geral."""

    @staticmethod
    def get_debt_by_type() -> dict:
        """Total agrupado por tipo de despesa."""

    @staticmethod
    def get_upcoming_installments(days: int = 30) -> list[dict]:
        """Parcelas vencendo nos próximos N dias."""

    @staticmethod
    def get_overdue_installments() -> list[dict]:
        """Parcelas vencidas e não pagas."""

    @staticmethod
    def get_expense_category_breakdown(year: int, month: int) -> list[dict]:
        """Breakdown por categoria no mês (para gráfico de pizza)."""
```

---

## 5. API — Endpoints

### 5.1 CRUD Endpoints

Todos seguem o padrão existente (`ModelViewSet` no DRF Router):

| Recurso | Endpoint | Notas |
|---------|----------|-------|
| Person | `/api/persons/` | CRUD completo |
| CreditCard | `/api/credit-cards/` | CRUD, filtro por `person_id` |
| ExpenseCategory | `/api/expense-categories/` | CRUD simples |
| Expense | `/api/expenses/` | CRUD com filtros extensivos |
| Income | `/api/incomes/` | CRUD com filtros |
| RentPayment | `/api/rent-payments/` | CRUD, filtro por `lease_id`, `reference_month` |
| EmployeePayment | `/api/employee-payments/` | CRUD, filtro por `person_id`, `reference_month` |
| FinancialSettings | `/api/financial-settings/current/` | GET/PUT (singleton) |

### 5.2 Filtros da Expense

```
GET /api/expenses/?person_id=1
GET /api/expenses/?credit_card_id=3
GET /api/expenses/?expense_type=card_purchase
GET /api/expenses/?category_id=5
GET /api/expenses/?building_id=2
GET /api/expenses/?is_paid=false
GET /api/expenses/?is_installment=true
GET /api/expenses/?is_recurring=true
GET /api/expenses/?date_from=2026-01-01&date_to=2026-03-31
```

### 5.3 Ações Especiais da Expense

```
POST /api/expenses/{id}/mark_paid/         — Marca como pago (com paid_date)
POST /api/expenses/{id}/generate_installments/  — Gera parcelas automaticamente a partir de total_amount, total_installments e data inicial
```

### 5.4 Ações da ExpenseInstallment

```
POST /api/expense-installments/{id}/mark_paid/   — Marca parcela como paga
POST /api/expense-installments/bulk_mark_paid/    — Marca múltiplas parcelas como pagas
GET  /api/expense-installments/?expense_id=1      — Lista parcelas de uma despesa
GET  /api/expense-installments/?due_date_from=...&due_date_to=...
GET  /api/expense-installments/?is_paid=false&is_overdue=true
```

### 5.5 Dashboard Financeiro

```
GET /api/financial-dashboard/overview/
GET /api/financial-dashboard/debt_by_person/
GET /api/financial-dashboard/debt_by_type/
GET /api/financial-dashboard/upcoming_installments/?days=30
GET /api/financial-dashboard/overdue_installments/
GET /api/financial-dashboard/category_breakdown/?year=2026&month=3
```

### 5.6 Fluxo de Caixa e Simulação

```
GET  /api/cash-flow/monthly/?year=2026&month=3
GET  /api/cash-flow/projection/?months=12
GET  /api/cash-flow/person_summary/?person_id=1&year=2026&month=3
POST /api/cash-flow/simulate/
```

**Body do simulate:**
```json
{
  "scenarios": [
    {"type": "pay_off_early", "expense_id": 42},
    {"type": "change_rent", "apartment_id": 5, "new_value": "1300.00"}
  ]
}
```

### 5.7 Export

```
GET /api/expenses/export/excel/?filters...
GET /api/expenses/export/csv/?filters...
GET /api/rent-payments/export/excel/
GET /api/incomes/export/excel/
```

---

## 6. Serializers

Seguem o padrão existente: nested read + ID write.

### 6.1 Exemplos de Padrão

```python
class ExpenseSerializer(serializers.ModelSerializer):
    # Leitura — objetos aninhados
    person = PersonSerializer(read_only=True)
    credit_card = CreditCardSerializer(read_only=True)
    building = BuildingSerializer(read_only=True)
    category = ExpenseCategorySerializer(read_only=True)
    installments = ExpenseInstallmentSerializer(many=True, read_only=True)

    # Escrita — IDs
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source='person', write_only=True, required=False, allow_null=True
    )
    credit_card_id = serializers.PrimaryKeyRelatedField(
        queryset=CreditCard.objects.all(), source='credit_card', write_only=True, required=False, allow_null=True
    )
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), source='building', write_only=True, required=False, allow_null=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseCategory.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )

    # Campos computados
    remaining_installments = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    total_remaining = serializers.SerializerMethodField()
```

### 6.2 Validações no Serializer

```python
def validate(self, data):
    expense_type = data.get('expense_type')

    # Compra no cartão requer credit_card
    if expense_type == ExpenseType.CARD_PURCHASE and not data.get('credit_card'):
        raise ValidationError({'credit_card_id': 'Obrigatório para compras no cartão.'})

    # Empréstimo bancário requer person
    if expense_type == ExpenseType.BANK_LOAN and not data.get('person'):
        raise ValidationError({'person_id': 'Obrigatório para empréstimos bancários.'})

    # Contas de consumo e IPTU requerem building
    if expense_type in (ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL, ExpenseType.PROPERTY_TAX):
        if not data.get('building'):
            raise ValidationError({'building_id': 'Obrigatório para contas de consumo e IPTU.'})

    # Parcelado requer total_installments
    if data.get('is_installment') and not data.get('total_installments'):
        raise ValidationError({'total_installments': 'Obrigatório para despesas parceladas.'})

    # Recorrente requer expected_monthly_amount
    if data.get('is_recurring') and not data.get('expected_monthly_amount'):
        raise ValidationError({'expected_monthly_amount': 'Obrigatório para gastos fixos recorrentes.'})

    return data
```

---

## 7. Frontend

### 7.1 Estrutura de Arquivos

```
frontend/
├── app/(dashboard)/
│   └── financial/                          # Nova seção
│       ├── page.tsx                        # Dashboard Financeiro
│       ├── _components/
│       │   ├── balance-card.tsx            # Saldo do mês
│       │   ├── cash-flow-chart.tsx         # Gráfico 12 meses
│       │   ├── person-summary-cards.tsx    # Cards por pessoa
│       │   ├── upcoming-installments.tsx   # Parcelas próximas
│       │   ├── overdue-alerts.tsx          # Alertas de vencidos
│       │   └── category-breakdown.tsx      # Gráfico por categoria
│       ├── persons/
│       │   ├── page.tsx
│       │   └── _components/
│       │       └── person-form-modal.tsx
│       ├── expenses/
│       │   ├── page.tsx
│       │   └── _components/
│       │       ├── expense-form-modal.tsx   # Formulário inteligente por tipo
│       │       ├── expense-filters.tsx      # Filtros extensivos
│       │       └── installments-drawer.tsx  # Drawer com lista de parcelas
│       ├── incomes/
│       │   ├── page.tsx
│       │   └── _components/
│       │       └── income-form-modal.tsx
│       ├── categories/
│       │   ├── page.tsx
│       │   └── _components/
│       │       └── category-form-modal.tsx
│       ├── rent-payments/
│       │   ├── page.tsx
│       │   └── _components/
│       │       └── rent-payment-form-modal.tsx
│       ├── employees/
│       │   ├── page.tsx
│       │   └── _components/
│       │       └── employee-payment-form-modal.tsx
│       ├── simulator/
│       │   ├── page.tsx
│       │   └── _components/
│       │       ├── scenario-builder.tsx     # Adicionar cenários
│       │       ├── comparison-chart.tsx     # Gráfico comparativo
│       │       └── scenario-card.tsx        # Card de cenário individual
│       └── settings/
│           └── page.tsx                     # Saldo inicial, configurações
├── lib/
│   ├── api/hooks/
│   │   ├── use-persons.ts
│   │   ├── use-credit-cards.ts
│   │   ├── use-expenses.ts
│   │   ├── use-expense-installments.ts
│   │   ├── use-expense-categories.ts
│   │   ├── use-incomes.ts
│   │   ├── use-rent-payments.ts
│   │   ├── use-employee-payments.ts
│   │   ├── use-financial-dashboard.ts
│   │   ├── use-cash-flow.ts
│   │   └── use-simulation.ts
│   └── schemas/
│       ├── person.schema.ts
│       ├── credit-card.schema.ts
│       ├── expense.schema.ts
│       ├── expense-installment.schema.ts
│       ├── expense-category.schema.ts
│       ├── income.schema.ts
│       ├── rent-payment.schema.ts
│       ├── employee-payment.schema.ts
│       └── financial-settings.schema.ts
```

### 7.2 Navegação (Sidebar)

Nova seção "Financeiro" com sub-itens:

```typescript
{
  label: 'Financeiro',
  icon: DollarSign,          // lucide-react
  children: [
    { label: 'Dashboard', path: '/financial' },
    { label: 'Despesas', path: '/financial/expenses' },
    { label: 'Receitas', path: '/financial/incomes' },
    { label: 'Pagamentos Aluguel', path: '/financial/rent-payments' },
    { label: 'Pessoas', path: '/financial/persons' },
    { label: 'Funcionários', path: '/financial/employees' },
    { label: 'Categorias', path: '/financial/categories' },
    { label: 'Simulador', path: '/financial/simulator' },
    { label: 'Configurações', path: '/financial/settings' },
  ]
}
```

### 7.3 Dashboard Financeiro — Widgets

**Linha 1 — Cards de resumo (4 cards):**
- Saldo do Mês (verde/vermelho)
- Total Receitas do Mês
- Total Despesas do Mês
- Total Dívida Pendente

**Linha 2 — Gráfico principal:**
- Fluxo de Caixa 12 meses (barras empilhadas: receitas vs despesas, linha de saldo acumulado)
- Usa `recharts` (BarChart + LineChart composto), seguindo o padrão do `BuildingStatisticsChart`

**Linha 3 — Cards por pessoa:**
- Um card para cada pessoa (Rodrigo, Tiago, Alvaro, Junior)
- Mostra: total que recebe, total cartões, total empréstimos, líquido

**Linha 4 — Duas colunas:**
- Esquerda: Parcelas vencendo nos próximos 30 dias (lista com status pago/pendente)
- Direita: Alertas (parcelas vencidas, meses futuros negativos)

**Linha 5 — Gráfico de categorias:**
- Pizza chart com breakdown por categoria das despesas do mês

### 7.4 Formulário de Despesa (Inteligente)

O formulário adapta os campos visíveis conforme o `expense_type` selecionado:

| Tipo | Campos extras visíveis |
|------|----------------------|
| Compra no Cartão | pessoa*, cartão*, parcelas |
| Empréstimo Bancário | pessoa*, banco, juros, parcelas |
| Empréstimo Pessoal | pessoa*, parcelas |
| Conta de Água | prédio* |
| Conta de Luz | prédio* |
| IPTU | prédio* |
| Gasto Fixo | valor mensal esperado, dia de recorrência |
| Gasto Único | (sem campos extras) |
| Salário Funcionário | pessoa* (redireciona para tela de funcionários) |

(*) campos obrigatórios para o tipo

Ao marcar "Parcelado", aparecem: total de parcelas + valor da parcela. Ao salvar, as parcelas são geradas automaticamente via API.

### 7.5 Simulador

**Layout da página:**
1. Gráfico principal mostrando projeção real de 12 meses
2. Painel lateral com lista de cenários adicionados
3. Botão "Adicionar cenário" abre modal com opções:
   - Quitar despesa antecipada (select da despesa parcelada)
   - Alterar aluguel (select do apartamento + novo valor)
   - Novo empréstimo (valor, parcelas, mês inicial)
   - Remover inquilino (select do apartamento)
   - Adicionar gasto fixo (valor, descrição)
   - Remover gasto fixo (select)
4. Ao adicionar cenários, o gráfico atualiza mostrando duas linhas: real vs simulado
5. Tabela comparativa mês a mês abaixo do gráfico
6. Card de "Impacto Total" mostrando a diferença acumulada em 12 meses

---

## 8. Permissões

### 8.1 Backend

Seguindo o padrão existente do projeto:

- **Admin (Alvaro)**: CRUD completo em todos os recursos financeiros
- **Visualização (filhos/familiares)**: Usa o `User` vinculado à `Person`. Novo permission class:

```python
class FinancialReadOnly(BasePermission):
    """
    Permite leitura para qualquer usuário autenticado.
    Escrita apenas para admin.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff
```

### 8.2 Frontend

- Sidebar mostra seção "Financeiro" para todos os logados
- Botões de criar/editar/excluir são condicionais: `user.is_staff`
- Dashboard e simulador são read-only para não-admin

---

## 9. Migrations

Nova migration sequencial: `0009_add_financial_module.py`

Criação dos modelos na ordem correta (respeitando FKs):
1. `Person`
2. `CreditCard`
3. `ExpenseCategory`
4. `Expense`
5. `ExpenseInstallment`
6. `PersonIncome`
7. `Income`
8. `RentPayment`
9. `EmployeePayment`
10. `FinancialSettings`
11. Alter `Apartment` — adicionar `owner`
12. Alter `Lease` — adicionar `prepaid_until`, `is_salary_offset`

---

## 10. Testes

### 10.1 Backend (pytest)

```
tests/
├── unit/
│   ├── test_financial/
│   │   ├── test_cash_flow_service.py
│   │   ├── test_simulation_service.py
│   │   ├── test_financial_dashboard_service.py
│   │   ├── test_expense_serializer.py
│   │   ├── test_person_serializer.py
│   │   └── test_financial_models.py
│   └── ...
├── integration/
│   ├── test_financial_api.py
│   ├── test_cash_flow_api.py
│   └── test_simulation_api.py
└── e2e/
    └── test_financial_workflow.py
```

**Cenários críticos a testar:**
- Fluxo de caixa com mix de dados reais e projetados
- Apartamento com owner não conta como receita
- Lease com `prepaid_until` não gera receita no período
- Lease com `is_salary_offset` nunca gera receita
- Geração automática de parcelas
- Simulação com múltiplos cenários sobrepostos
- PersonIncome com `apartment_rent` e lease inativo retorna R$0
- Média de consumo para projeção de utility bills

### 10.2 Frontend (vitest)

```
frontend/lib/api/hooks/__tests__/
├── use-persons.test.tsx
├── use-expenses.test.tsx
├── use-incomes.test.tsx
├── use-cash-flow.test.tsx
├── use-financial-dashboard.test.tsx
└── use-simulation.test.tsx
```

Seguem o padrão existente com MSW handlers.

---

## 11. Ordem de Implementação

### Fase 1 — Fundação (Backend)
1. Models + migration
2. Serializers com validações
3. ViewSets CRUD (Person, CreditCard, ExpenseCategory, Expense, ExpenseInstallment)
4. Testes unitários dos models e serializers
5. Testes de integração dos endpoints CRUD

### Fase 2 — Receitas e Pagamentos (Backend)
6. ViewSets CRUD (Income, RentPayment, EmployeePayment, PersonIncome)
7. Ações especiais (mark_paid, generate_installments, bulk_mark_paid)
8. Alterações em Apartment e Lease (owner, prepaid_until, is_salary_offset)
9. Testes

### Fase 3 — Serviços Financeiros (Backend)
10. CashFlowService
11. FinancialDashboardService
12. SimulationService
13. Endpoints de dashboard, cash-flow e simulação
14. Testes unitários e de integração dos serviços

### Fase 4 — Frontend Base
15. Schemas Zod para todos os novos modelos
16. API hooks (TanStack Query) para todos os endpoints
17. Sidebar com navegação financeira
18. CRUD pages: Pessoas, Categorias, Configurações

### Fase 5 — Frontend CRUD Principal
19. Página de Despesas com formulário inteligente
20. Drawer de parcelas
21. Página de Receitas
22. Página de Pagamentos de Aluguel
23. Página de Funcionários

### Fase 6 — Dashboard e Simulador (Frontend)
24. Dashboard Financeiro com todos os widgets
25. Página do Simulador com cenários
26. Testes frontend

### Fase 7 — Permissões e Polish
27. Permission classes no backend
28. Condicional de admin no frontend
29. Export Excel/CSV
30. Testes e2e
