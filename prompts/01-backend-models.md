# Sessão 01 — Backend: Models + Migration + Tests

## Contexto

Leia estes arquivos para entender o projeto e o que será implementado:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 3 (Modelos de Dados)
- `@prompts/SESSION_STATE.md` — Estado atual do progresso
- `@prompts/00-prompt-standard.md` — Padrão de prompts e referência de exemplares

Leia estes exemplares para seguir os padrões existentes:
- `@core/models.py` linhas 31-171 — SoftDeleteManager, AuditMixin, SoftDeleteMixin
- `@core/models.py` linhas 178-226 — Building e Furniture (models simples)
- `@core/models.py` linhas 453-570 — Lease (model complexo com validators e indexes)

---

## Escopo

### Arquivos a CRIAR
- `tests/unit/test_financial/` — novo diretório
- `tests/unit/test_financial/__init__.py`
- `tests/unit/test_financial/test_financial_models.py` — testes dos models
- `core/migrations/0009_add_financial_module.py` — gerada via makemigrations

### Arquivos a MODIFICAR
- `core/models.py` — adicionar 10 novos models + alterar Apartment e Lease

---

## Especificação

### Novos Models (todos herdam AuditMixin + SoftDeleteMixin, usam SoftDeleteManager)

**1. Person**
```python
name: CharField(max_length=200)
relationship: CharField(max_length=50)  # filho, genro, funcionária
phone: CharField(max_length=20, blank=True)
email: EmailField(blank=True)
is_owner: BooleanField(default=False)
is_employee: BooleanField(default=False)
user: OneToOneField(User, null=True, blank=True, on_delete=SET_NULL, related_name='person_profile')
notes: TextField(blank=True)
# Meta: ordering = ['name']
```

**2. CreditCard**
```python
person: ForeignKey(Person, related_name='credit_cards', on_delete=CASCADE)
nickname: CharField(max_length=100)
last_four_digits: CharField(max_length=4, blank=True)
closing_day: PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
due_day: PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
is_active: BooleanField(default=True)
# Meta: ordering = ['person', 'nickname'], unique_together = ['person', 'nickname']
```

**3. ExpenseCategory**
```python
name: CharField(max_length=100, unique=True)
description: TextField(blank=True)
color: CharField(max_length=7, default='#6B7280')
# Meta: ordering = ['name'], verbose_name_plural = 'Expense categories'
```

**4. ExpenseType (TextChoices)**
```python
CARD_PURCHASE = 'card_purchase', 'Compra no Cartão'
BANK_LOAN = 'bank_loan', 'Empréstimo Bancário'
PERSONAL_LOAN = 'personal_loan', 'Empréstimo Pessoal'
WATER_BILL = 'water_bill', 'Conta de Água'
ELECTRICITY_BILL = 'electricity_bill', 'Conta de Luz'
PROPERTY_TAX = 'property_tax', 'IPTU'
FIXED_EXPENSE = 'fixed_expense', 'Gasto Fixo Mensal'
ONE_TIME_EXPENSE = 'one_time_expense', 'Gasto Único'
EMPLOYEE_SALARY = 'employee_salary', 'Salário Funcionário'
```

**5. Expense**
```python
description: CharField(max_length=500)
expense_type: CharField(max_length=30, choices=ExpenseType.choices)
total_amount: DecimalField(max_digits=12, decimal_places=2)
expense_date: DateField()
person: ForeignKey(Person, null=True, blank=True, related_name='expenses', on_delete=SET_NULL)
credit_card: ForeignKey(CreditCard, null=True, blank=True, related_name='expenses', on_delete=SET_NULL)
building: ForeignKey(Building, null=True, blank=True, related_name='expenses', on_delete=SET_NULL)
category: ForeignKey(ExpenseCategory, null=True, blank=True, related_name='expenses', on_delete=SET_NULL)
is_installment: BooleanField(default=False)
total_installments: PositiveIntegerField(null=True, blank=True)
is_debt_installment: BooleanField(default=False)
is_recurring: BooleanField(default=False)
expected_monthly_amount: DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
recurrence_day: PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
is_paid: BooleanField(default=False)
paid_date: DateField(null=True, blank=True)
bank_name: CharField(max_length=100, blank=True)
interest_rate: DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
notes: TextField(blank=True)
# Meta: ordering = ['-expense_date'], indexes conforme design doc
```

**6. ExpenseInstallment**
```python
expense: ForeignKey(Expense, related_name='installments', on_delete=CASCADE)
installment_number: PositiveIntegerField()
total_installments: PositiveIntegerField()
amount: DecimalField(max_digits=12, decimal_places=2)
due_date: DateField()
is_paid: BooleanField(default=False)
paid_date: DateField(null=True, blank=True)
notes: TextField(blank=True)
# Meta: unique_together = ['expense', 'installment_number'], ordering = ['due_date', 'installment_number'], indexes conforme design doc
```

**7. PersonIncomeType (TextChoices) + PersonIncome**
```python
# PersonIncomeType
APARTMENT_RENT = 'apartment_rent', 'Aluguel de Apartamento'
FIXED_STIPEND = 'fixed_stipend', 'Estipêndio Fixo'

# PersonIncome
person: ForeignKey(Person, related_name='incomes', on_delete=CASCADE)
income_type: CharField(max_length=20, choices=PersonIncomeType.choices)
apartment: ForeignKey(Apartment, null=True, blank=True, on_delete=SET_NULL)
fixed_amount: DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
start_date: DateField()
end_date: DateField(null=True, blank=True)
is_active: BooleanField(default=True)
notes: TextField(blank=True)
# Meta: ordering = ['-start_date']
```

**8. Income**
```python
description: CharField(max_length=500)
amount: DecimalField(max_digits=12, decimal_places=2)
income_date: DateField()
person: ForeignKey(Person, null=True, blank=True, related_name='extra_incomes', on_delete=SET_NULL)
building: ForeignKey(Building, null=True, blank=True, related_name='extra_incomes', on_delete=SET_NULL)
category: ForeignKey(ExpenseCategory, null=True, blank=True, on_delete=SET_NULL)
is_recurring: BooleanField(default=False)
expected_monthly_amount: DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
is_received: BooleanField(default=False)
received_date: DateField(null=True, blank=True)
notes: TextField(blank=True)
# Meta: ordering = ['-income_date']
```

**9. RentPayment**
```python
lease: ForeignKey(Lease, related_name='rent_payments', on_delete=CASCADE)
reference_month: DateField()  # primeiro dia do mês (ex: 2026-03-01)
amount_paid: DecimalField(max_digits=12, decimal_places=2)
payment_date: DateField()
notes: TextField(blank=True)
# Meta: unique_together = ['lease', 'reference_month'], ordering = ['-reference_month'], indexes conforme design doc
```

**10. EmployeePayment**
```python
person: ForeignKey(Person, related_name='employee_payments', on_delete=CASCADE)
reference_month: DateField()
base_salary: DecimalField(max_digits=12, decimal_places=2)
variable_amount: DecimalField(max_digits=12, decimal_places=2, default=0)
rent_offset: DecimalField(max_digits=12, decimal_places=2, default=0)
cleaning_count: PositiveIntegerField(default=0)
payment_date: DateField(null=True, blank=True)
is_paid: BooleanField(default=False)
notes: TextField(blank=True)
# Meta: unique_together = ['person', 'reference_month'], ordering = ['-reference_month']
# Property: total_paid = base_salary + variable_amount (sem rent_offset)
```

**11. FinancialSettings (Singleton)**
```python
initial_balance: DecimalField(max_digits=12, decimal_places=2, default=0)
initial_balance_date: DateField()
notes: TextField(blank=True)
updated_at: DateTimeField(auto_now=True)
updated_by: ForeignKey(User, null=True, on_delete=SET_NULL)
# Meta: verbose_name_plural = 'Financial settings'
# Override save() para forçar pk=1 (singleton)
```

### Alterações em Models Existentes

**Apartment** — adicionar campo:
```python
owner = ForeignKey('Person', null=True, blank=True, related_name='owned_apartments', on_delete=SET_NULL)
```

**Lease** — adicionar campos:
```python
prepaid_until = DateField(null=True, blank=True, help_text='Aluguel pré-pago até esta data.')
is_salary_offset = BooleanField(default=False, help_text='Aluguel compensado como salário.')
```

---

## TDD

### Passo 1: Escrever testes (RED)

Criar `tests/unit/test_financial/__init__.py` e `tests/unit/test_financial/test_financial_models.py`.

**Cenários de teste obrigatórios:**

```python
# Person
class TestPersonModel:
    test_create_person  # criar com campos básicos
    test_person_str     # __str__ retorna name
    test_person_with_user  # vincular a User
    test_person_soft_delete  # soft delete funciona
    test_person_restore  # restore funciona

# CreditCard
class TestCreditCardModel:
    test_create_credit_card  # criar vinculado a person
    test_credit_card_str  # __str__
    test_credit_card_unique_nickname_per_person  # unique_together
    test_closing_day_validators  # 1-31 range
    test_due_day_validators  # 1-31 range
    test_cascade_delete_with_person  # deleta ao deletar person (hard)

# ExpenseCategory
class TestExpenseCategoryModel:
    test_create_category  # criar com nome
    test_category_unique_name  # nome único
    test_category_default_color  # cor padrão #6B7280

# Expense
class TestExpenseModel:
    test_create_simple_expense  # gasto único sem relações
    test_create_card_expense  # com person + credit_card
    test_create_loan_expense  # com person, bank_name, interest_rate
    test_create_utility_expense  # com building
    test_create_recurring_expense  # com is_recurring + expected_monthly_amount
    test_create_installment_expense  # com is_installment + total_installments
    test_expense_type_choices  # todos os 9 tipos válidos
    test_expense_indexes  # verificar que indexes existem no Meta

# ExpenseInstallment
class TestExpenseInstallmentModel:
    test_create_installment  # criar parcela vinculada a expense
    test_installment_unique_together  # expense + installment_number único
    test_installment_ordering  # ordenado por due_date
    test_mark_as_paid  # is_paid + paid_date

# PersonIncome
class TestPersonIncomeModel:
    test_create_apartment_rent_income  # tipo apartment_rent com apartment
    test_create_fixed_stipend_income  # tipo fixed_stipend com fixed_amount
    test_income_active_by_default  # is_active=True default

# Income
class TestIncomeModel:
    test_create_income  # criar receita extra
    test_create_recurring_income  # com is_recurring
    test_income_optional_relations  # person, building, category todos opcionais

# RentPayment
class TestRentPaymentModel:
    test_create_rent_payment  # criar pagamento vinculado a lease
    test_rent_payment_unique_together  # lease + reference_month único
    test_rent_payment_ordering  # ordenado por -reference_month

# EmployeePayment
class TestEmployeePaymentModel:
    test_create_employee_payment  # criar com 3 componentes
    test_total_paid_property  # base_salary + variable_amount (sem rent_offset)
    test_employee_payment_unique_together  # person + reference_month único

# FinancialSettings
class TestFinancialSettingsModel:
    test_create_settings  # criar com saldo inicial
    test_singleton_enforcement  # segundo save sobrescreve o primeiro (pk=1)

# Alterações existentes
class TestApartmentOwnerField:
    test_apartment_owner_nullable  # owner pode ser null
    test_apartment_with_owner  # vincular owner a Person

class TestLeaseFinancialFields:
    test_lease_prepaid_until  # campo opcional
    test_lease_is_salary_offset  # default False
```

### Passo 2: Rodar testes (devem FALHAR)
```bash
pytest tests/unit/test_financial/test_financial_models.py -v
```

### Passo 3: Implementar models em `core/models.py`
- Adicionar todos os 10 novos models ao final do arquivo
- Adicionar os 2 novos campos aos models existentes
- Seguir exatamente os padrões dos exemplares

### Passo 4: Gerar migration
```bash
python manage.py makemigrations core --name add_financial_module
```

### Passo 5: Aplicar migration
```bash
python manage.py migrate
```

### Passo 6: Rodar testes (devem PASSAR)
```bash
pytest tests/unit/test_financial/test_financial_models.py -v
```

### Passo 7: Rodar suite completa (zero regressão)
```bash
pytest
```

---

## Constraints

- NÃO modifique models existentes além de adicionar `owner` em Apartment e `prepaid_until`/`is_salary_offset` em Lease
- NÃO crie serializers, views ou URLs nesta sessão
- NÃO adicione docstrings ou type annotations a código que não está sendo criado
- NÃO altere a ordem dos models existentes no arquivo
- NÃO crie mais de uma migration — tudo em uma única migration
- Siga EXATAMENTE o padrão de herança `(AuditMixin, SoftDeleteMixin, models.Model)` + `objects = SoftDeleteManager()`

---

## Critérios de Aceite

- [ ] 10 novos models criados em `core/models.py`
- [ ] 2 campos adicionados a `Apartment` e 2 a `Lease`
- [ ] Migration `0009_add_financial_module.py` gerada e aplicada sem erros
- [ ] Todos os testes de `test_financial_models.py` passando
- [ ] Suite completa `pytest` passando (zero regressão)
- [ ] Nenhum arquivo fora do escopo foi modificado

---

## Handoff

Ao finalizar:
1. Rodar `pytest` completo e confirmar 100% passando
2. Atualizar `prompts/SESSION_STATE.md`:
   - Sessão 01 → `concluída`
   - Listar arquivos criados/modificados
   - Registrar qualquer decisão tomada
3. Commitar: `feat(financial): add financial module models and migration`
