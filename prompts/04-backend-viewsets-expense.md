# Sessão 04 — Backend: Expense + ExpenseInstallment ViewSets + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seções 5.2, 5.3, 5.4 (Filtros e ações especiais)
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia estes exemplares:
- `@core/views.py` linhas 65-127 — ApartmentViewSet (filtros por query params)
- `@core/views.py` linhas 201-435 — LeaseViewSet (custom @action methods)

---

## Escopo

### Arquivos a CRIAR
- `tests/integration/test_expense_api.py`

### Arquivos a MODIFICAR
- `core/viewsets/financial_views.py` — adicionar ExpenseViewSet, ExpenseInstallmentViewSet
- `core/urls.py` — registrar novas rotas

---

## Especificação

### ExpenseViewSet (`/api/expenses/`)

**CRUD completo** (ModelViewSet) com:

**Queryset otimizado:**
```python
Expense.objects.select_related('person', 'credit_card', 'building', 'category')
    .prefetch_related('installments')
```

**Filtros via query params:**
- `person_id` — FK direto
- `credit_card_id` — FK direto
- `expense_type` — CharField exact match
- `category_id` — FK direto
- `building_id` — FK direto
- `is_paid` — BooleanField
- `is_installment` — BooleanField
- `is_recurring` — BooleanField
- `is_debt_installment` — BooleanField
- `date_from` — expense_date >= valor
- `date_to` — expense_date <= valor

**Ações especiais:**

`POST /api/expenses/{id}/mark_paid/`
- Marca a expense como paga: `is_paid=True`, `paid_date=request.data.get('paid_date', date.today())`
- Retorna a expense atualizada

`POST /api/expenses/{id}/generate_installments/`
- Gera `ExpenseInstallment` automaticamente
- Requer: `expense.is_installment=True` e `expense.total_installments > 0`
- Body opcional: `{"start_date": "2026-04-01"}` (default: expense_date)
- Lógica:
  - `installment_amount = expense.total_amount / expense.total_installments`
  - Para cada parcela (1 a N): cria ExpenseInstallment com `due_date = start_date + (i-1) months`
  - Se a expense está vinculada a um `credit_card`, usar o `due_day` do cartão para calcular os vencimentos
- Retorna a expense com installments nested
- Erro 400 se já existem installments

### ExpenseInstallmentViewSet (`/api/expense-installments/`)

**CRUD completo** (ModelViewSet) com:

**Queryset:** `select_related('expense', 'expense__person', 'expense__credit_card')`

**Filtros:**
- `expense_id` — FK direto
- `is_paid` — BooleanField
- `is_overdue` — computed: `is_paid=False AND due_date < today`
- `due_date_from` — due_date >= valor
- `due_date_to` — due_date <= valor
- `person_id` — via expense__person_id
- `credit_card_id` — via expense__credit_card_id

**Ações especiais:**

`POST /api/expense-installments/{id}/mark_paid/`
- Marca parcela como paga: `is_paid=True`, `paid_date=request.data.get('paid_date', date.today())`
- Se TODAS as parcelas da expense ficarem pagas, marca a expense como paga também

`POST /api/expense-installments/bulk_mark_paid/`
- Body: `{"installment_ids": [1, 2, 3], "paid_date": "2026-03-21"}`
- Marca todas as parcelas listadas como pagas
- Para cada expense afetada, verifica se todas as parcelas estão pagas → marca expense como paga
- Retorna lista das parcelas atualizadas

---

## TDD

### Passo 1: Escrever testes (RED)

```python
# ExpenseViewSet
class TestExpenseAPI:
    # CRUD
    test_list_expenses  # GET /api/expenses/
    test_create_simple_expense  # POST gasto único
    test_create_card_purchase  # POST compra no cartão com person + card
    test_create_bank_loan  # POST empréstimo com parcelas
    test_retrieve_expense_with_installments  # GET inclui parcelas nested
    test_update_expense  # PUT
    test_delete_expense  # DELETE soft delete

    # Filtros
    test_filter_by_person  # ?person_id=X
    test_filter_by_credit_card  # ?credit_card_id=X
    test_filter_by_expense_type  # ?expense_type=card_purchase
    test_filter_by_category  # ?category_id=X
    test_filter_by_building  # ?building_id=X
    test_filter_by_is_paid  # ?is_paid=false
    test_filter_by_date_range  # ?date_from=X&date_to=Y
    test_filter_combined  # ?person_id=X&expense_type=card_purchase&is_paid=false

    # Ações
    test_mark_paid  # POST mark_paid/ marca como pago
    test_mark_paid_with_date  # POST com paid_date custom
    test_generate_installments  # POST gera parcelas corretas
    test_generate_installments_with_credit_card_due_day  # usa due_day do cartão
    test_generate_installments_already_exist  # erro 400
    test_generate_installments_not_installment  # erro 400 se is_installment=False

# ExpenseInstallmentViewSet
class TestExpenseInstallmentAPI:
    # CRUD
    test_list_installments  # GET /api/expense-installments/
    test_retrieve_installment  # GET /{id}/

    # Filtros
    test_filter_by_expense  # ?expense_id=X
    test_filter_by_is_paid  # ?is_paid=false
    test_filter_by_is_overdue  # ?is_overdue=true
    test_filter_by_due_date_range  # ?due_date_from=X&due_date_to=Y
    test_filter_by_person  # ?person_id=X (via expense)

    # Ações
    test_mark_paid  # marca parcela como paga
    test_mark_paid_completes_expense  # marca expense como paga quando todas as parcelas pagas
    test_bulk_mark_paid  # marca múltiplas parcelas
    test_bulk_mark_paid_completes_expense  # expense auto-completa
    test_bulk_mark_paid_invalid_ids  # erro para ids inexistentes
```

### Passo 2-6: Ciclo TDD padrão

---

## Constraints

- NÃO modifique models ou serializers
- NÃO implemente Income, RentPayment ou EmployeePayment ViewSets
- A lógica de `generate_installments` fica no ViewSet (ou extraída para um método helper), NÃO crie um service separado para isso
- Ao marcar parcela como paga, sempre verifique se a expense deve ser marcada como paga também (todas as parcelas pagas)

---

## Critérios de Aceite

- [ ] ExpenseViewSet com CRUD + 9 filtros + 2 ações especiais
- [ ] ExpenseInstallmentViewSet com CRUD + 6 filtros + 2 ações especiais
- [ ] generate_installments calcula datas corretamente (mensal, usando due_day do cartão quando aplicável)
- [ ] bulk_mark_paid funciona e auto-completa expense
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Expense and ExpenseInstallment API with filters and actions`
