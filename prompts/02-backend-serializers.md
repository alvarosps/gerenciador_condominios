# Sessão 02 — Backend: Serializers + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 6 (Serializers)
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia estes exemplares:
- `@core/serializers.py` linhas 8-11 — BuildingSerializer (simples)
- `@core/serializers.py` linhas 20-89 — ApartmentSerializer (nested read + ID write + sync)
- `@core/serializers.py` linhas 107-199 — TenantSerializer (dependent handling)
- `@core/serializers.py` linhas 201-279 — LeaseSerializer (complexo)

Leia os models criados na Sessão 01:
- `@core/models.py` — Seção dos models financeiros (final do arquivo)

---

## Escopo

### Arquivos a CRIAR
- `tests/unit/test_financial/test_financial_serializers.py`

### Arquivos a MODIFICAR
- `core/serializers.py` — adicionar serializers financeiros ao final

---

## Especificação

### Serializers a criar (seguindo padrão nested read + ID write)

**1. PersonSerializer**
- Campos: todos os campos do model
- Read-only: `id`, audit fields, `credit_cards` (nested list, read only)
- user_id: PrimaryKeyRelatedField (write-only, optional, allow_null)

**2. CreditCardSerializer**
- Campos: todos os campos do model
- Nested read: `person` (PersonSerializer, read_only — SEM nested credit_cards para evitar recursão)
- Write: `person_id` (PrimaryKeyRelatedField, write-only)

**3. ExpenseCategorySerializer**
- Campos: todos os campos do model (simples, sem relações)

**4. ExpenseInstallmentSerializer**
- Campos: todos os campos do model
- Campos computados: `is_overdue` (SerializerMethodField — True se não pago e due_date < hoje)

**5. ExpenseSerializer**
- Nested read: `person`, `credit_card`, `building`, `category`, `installments`
- Write: `person_id`, `credit_card_id`, `building_id`, `category_id` (todos opcionais, allow_null)
- Campos computados:
  - `remaining_installments`: conta parcelas não pagas
  - `total_paid`: soma de parcelas pagas
  - `total_remaining`: soma de parcelas não pagas
- **Validação custom** (método `validate`):
  - `card_purchase` requer `credit_card`
  - `bank_loan` requer `person`
  - `water_bill`, `electricity_bill`, `property_tax` requerem `building`
  - `is_installment=True` requer `total_installments`
  - `is_recurring=True` requer `expected_monthly_amount`

**6. PersonIncomeSerializer**
- Nested read: `person`, `apartment` (se existir)
- Write: `person_id`, `apartment_id` (optional)
- Campo computado: `current_value` (SerializerMethodField — puxa rental_value do lease ativo se `apartment_rent`, ou `fixed_amount` se `fixed_stipend`)

**7. IncomeSerializer**
- Nested read: `person`, `building`, `category` (todos opcionais)
- Write: `person_id`, `building_id`, `category_id` (todos opcionais, allow_null)

**8. RentPaymentSerializer**
- Nested read: `lease` (com apartment e tenant info)
- Write: `lease_id`
- Validação: `reference_month` deve ser primeiro dia do mês

**9. EmployeePaymentSerializer**
- Nested read: `person`
- Write: `person_id`
- Read-only computado: `total_paid` (do model property)
- Validação: `reference_month` deve ser primeiro dia do mês

**10. FinancialSettingsSerializer**
- Campos: todos. Sem relações complexas.

### Alterações em Serializers Existentes

**ApartmentSerializer**: adicionar campo `owner` (nested PersonSerializer, read_only) e `owner_id` (write, optional, allow_null)

**LeaseSerializer**: adicionar campos `prepaid_until` e `is_salary_offset`

---

## TDD

### Passo 1: Escrever testes (RED)

**Cenários obrigatórios em `test_financial_serializers.py`:**

```python
# PersonSerializer
class TestPersonSerializer:
    test_serialize_person  # serializa com todos os campos
    test_create_person  # cria via serializer com dados válidos
    test_create_person_with_user  # cria vinculando user_id

# CreditCardSerializer
class TestCreditCardSerializer:
    test_serialize_credit_card  # inclui person nested
    test_create_credit_card  # cria com person_id
    test_no_recursive_nesting  # person nested não inclui credit_cards

# ExpenseCategorySerializer
class TestExpenseCategorySerializer:
    test_serialize_category  # campos básicos
    test_create_category  # cria com nome e cor

# ExpenseSerializer
class TestExpenseSerializer:
    test_serialize_expense_with_relations  # nested person, card, building, category
    test_create_card_purchase  # com credit_card_id, valida tipo
    test_create_bank_loan  # com person_id, bank_name
    test_create_utility_bill  # com building_id
    test_validation_card_purchase_requires_credit_card  # erro sem credit_card
    test_validation_bank_loan_requires_person  # erro sem person
    test_validation_utility_requires_building  # erro sem building
    test_validation_installment_requires_total  # erro is_installment sem total
    test_validation_recurring_requires_amount  # erro is_recurring sem amount
    test_computed_remaining_installments  # conta parcelas pendentes
    test_computed_total_paid  # soma parcelas pagas
    test_computed_total_remaining  # soma parcelas pendentes

# ExpenseInstallmentSerializer
class TestExpenseInstallmentSerializer:
    test_serialize_installment  # campos básicos
    test_is_overdue_true  # não pago e vencido
    test_is_overdue_false_paid  # pago
    test_is_overdue_false_future  # não pago mas futuro

# PersonIncomeSerializer
class TestPersonIncomeSerializer:
    test_serialize_apartment_rent  # com apartment nested
    test_current_value_from_lease  # puxa rental_value do lease ativo
    test_current_value_no_lease  # retorna 0 se sem lease ativo
    test_current_value_fixed_stipend  # retorna fixed_amount

# RentPaymentSerializer
class TestRentPaymentSerializer:
    test_serialize_rent_payment  # com lease nested
    test_create_rent_payment  # com lease_id
    test_validation_reference_month_first_day  # rejeita dia != 1

# EmployeePaymentSerializer
class TestEmployeePaymentSerializer:
    test_serialize_with_total_paid  # inclui total_paid computado
    test_total_paid_excludes_rent_offset  # base + variable, sem offset

# ApartmentSerializer (alteração)
class TestApartmentSerializerOwner:
    test_serialize_apartment_with_owner  # inclui owner nested
    test_create_apartment_with_owner_id  # cria com owner_id
    test_apartment_owner_nullable  # owner pode ser null

# LeaseSerializer (alteração)
class TestLeaseSerializerFinancialFields:
    test_serialize_lease_with_prepaid_until  # campo presente
    test_serialize_lease_with_salary_offset  # campo presente
```

### Passo 2: Rodar testes (devem FALHAR)
```bash
pytest tests/unit/test_financial/test_financial_serializers.py -v
```

### Passo 3: Implementar serializers em `core/serializers.py`

### Passo 4: Rodar testes (devem PASSAR)
```bash
pytest tests/unit/test_financial/test_financial_serializers.py -v
```

### Passo 5: Rodar suite completa
```bash
pytest
```

---

## Constraints

- NÃO crie views, URLs ou services nesta sessão
- NÃO modifique os models criados na Sessão 01
- NÃO crie um arquivo separado para serializers financeiros — adicione ao `core/serializers.py` existente
- Para evitar recursão no CreditCardSerializer, use uma versão simplificada de PersonSerializer (sem `credit_cards`) ou defina campos explícitos
- Siga EXATAMENTE o padrão nested read + ID write dos serializers existentes

---

## Critérios de Aceite

- [ ] 10 novos serializers criados em `core/serializers.py`
- [ ] Alterações em ApartmentSerializer e LeaseSerializer
- [ ] Todas as validações custom implementadas no ExpenseSerializer
- [ ] Campos computados funcionando (remaining_installments, total_paid, total_remaining, current_value, is_overdue)
- [ ] Todos os testes de `test_financial_serializers.py` passando
- [ ] Suite completa `pytest` passando (zero regressão)

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`:
   - Sessão 02 → `concluída`
   - Listar arquivos criados/modificados
3. Commitar: `feat(financial): add financial module serializers with validations`
