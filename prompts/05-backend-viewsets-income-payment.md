# Sessão 05 — Backend: Income, RentPayment, EmployeePayment, PersonIncome ViewSets + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 5.1 (CRUD Endpoints)
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia o código já implementado:
- `@core/viewsets/financial_views.py` — ViewSets já criados (sessões 03-04)
- `@core/serializers.py` — Serializers financeiros (sessão 02)

---

## Escopo

### Arquivos a CRIAR
- `tests/integration/test_income_payment_api.py`

### Arquivos a MODIFICAR
- `core/viewsets/financial_views.py` — adicionar 4 ViewSets
- `core/urls.py` — registrar 4 novas rotas
- `core/serializers.py` — verificar que ApartmentSerializer e LeaseSerializer já incluem os novos campos (feito na sessão 02)

---

## Especificação

### IncomeViewSet (`/api/incomes/`)

ModelViewSet completo.

**Queryset:** `select_related('person', 'building', 'category')`

**Filtros:**
- `person_id`
- `building_id`
- `category_id`
- `is_recurring`
- `is_received`
- `date_from`, `date_to` (income_date range)

**Ação especial:**
`POST /api/incomes/{id}/mark_received/`
- Body opcional: `{"received_date": "2026-03-21"}`
- Marca `is_received=True`, `received_date`

### RentPaymentViewSet (`/api/rent-payments/`)

ModelViewSet completo.

**Queryset:** `select_related('lease', 'lease__apartment', 'lease__apartment__building', 'lease__responsible_tenant')`

**Filtros:**
- `lease_id`
- `apartment_id` (via lease__apartment_id)
- `building_id` (via lease__apartment__building_id)
- `reference_month` (exact)
- `month_from`, `month_to` (reference_month range)
- `payment_date_from`, `payment_date_to` (payment_date range)

### EmployeePaymentViewSet (`/api/employee-payments/`)

ModelViewSet completo.

**Queryset:** `select_related('person')`

**Filtros:**
- `person_id`
- `reference_month` (exact)
- `is_paid`
- `month_from`, `month_to` (reference_month range)

**Ação especial:**
`POST /api/employee-payments/{id}/mark_paid/`
- Body opcional: `{"payment_date": "2026-03-21"}`
- Marca `is_paid=True`, `payment_date`

### PersonIncomeViewSet (`/api/person-incomes/`)

ModelViewSet completo.

**Queryset:** `select_related('person', 'apartment', 'apartment__building')`

**Filtros:**
- `person_id`
- `income_type`
- `is_active`
- `apartment_id`

---

## TDD

### Passo 1: Escrever testes (RED)

```python
# IncomeViewSet
class TestIncomeAPI:
    test_list_incomes
    test_create_income  # receita extra simples
    test_create_recurring_income  # aposentadoria recorrente
    test_filter_by_person
    test_filter_by_is_recurring
    test_filter_by_is_received
    test_filter_by_date_range
    test_mark_received  # POST mark_received/
    test_mark_received_with_date

# RentPaymentViewSet
class TestRentPaymentAPI:
    test_list_rent_payments
    test_create_rent_payment  # com lease_id + reference_month
    test_retrieve_with_nested_lease  # inclui apartment, building, tenant
    test_filter_by_lease
    test_filter_by_apartment  # via lease
    test_filter_by_building  # via lease→apartment
    test_filter_by_month_range
    test_duplicate_reference_month  # erro: unique_together

# EmployeePaymentViewSet
class TestEmployeePaymentAPI:
    test_list_employee_payments
    test_create_employee_payment  # com 3 componentes
    test_total_paid_in_response  # inclui total_paid computado
    test_filter_by_person
    test_filter_by_is_paid
    test_mark_paid
    test_duplicate_reference_month  # erro: unique_together

# PersonIncomeViewSet
class TestPersonIncomeAPI:
    test_list_person_incomes
    test_create_apartment_rent  # com person + apartment
    test_create_fixed_stipend  # com person + fixed_amount
    test_current_value_apartment_with_lease  # retorna rental_value do lease
    test_current_value_apartment_no_lease  # retorna 0
    test_current_value_fixed_stipend  # retorna fixed_amount
    test_filter_by_person
    test_filter_by_income_type
    test_filter_by_is_active
```

### Passo 2-6: Ciclo TDD padrão

---

## Constraints

- NÃO crie services nesta sessão
- NÃO modifique models ou serializers existentes
- Para `PersonIncomeSerializer.current_value`, o cálculo de apartment_rent deve buscar o lease ativo do apartment (onde o lease existe e não está expirado)

---

## Critérios de Aceite

- [ ] 4 ViewSets criados e registrados
- [ ] Filtros funcionando para cada ViewSet
- [ ] mark_received e mark_paid ações funcionando
- [ ] PersonIncome.current_value computado corretamente
- [ ] RentPayment rejeita reference_month duplicado por lease
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Income, RentPayment, EmployeePayment, PersonIncome API endpoints`
