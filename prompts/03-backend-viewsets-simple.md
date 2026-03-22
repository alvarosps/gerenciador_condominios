# Sessão 03 — Backend: ViewSets Simples + Tests

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 5 (API Endpoints)
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia estes exemplares:
- `@core/views.py` linhas 19-46 — BuildingViewSet (CRUD simples)
- `@core/viewsets/landlord_views.py` linhas 24-83 — LandlordViewSet (singleton pattern)
- `@core/urls.py` linhas 8-17 — Router registration

---

## Escopo

### Arquivos a CRIAR
- `core/viewsets/financial_views.py` — ViewSets financeiros simples
- `tests/integration/test_financial_api_simple.py` — Testes de integração

### Arquivos a MODIFICAR
- `core/viewsets/__init__.py` — Exportar novos ViewSets
- `core/urls.py` — Registrar rotas no router

---

## Especificação

### ViewSets a criar em `core/viewsets/financial_views.py`

**1. PersonViewSet** (`/api/persons/`)
- ModelViewSet completo
- Queryset: `Person.objects.all()`
- Serializer: PersonSerializer
- Filtros via query params: `is_owner`, `is_employee`, `search` (name icontains)
- prefetch_related: `credit_cards`

**2. CreditCardViewSet** (`/api/credit-cards/`)
- ModelViewSet completo
- Queryset com select_related: `person`
- Filtros: `person_id`, `is_active`

**3. ExpenseCategoryViewSet** (`/api/expense-categories/`)
- ModelViewSet completo
- Queryset: `ExpenseCategory.objects.all()`
- Sem filtros extras

**4. FinancialSettingsViewSet** (`/api/financial-settings/`)
- ViewSet (NÃO ModelViewSet) — singleton pattern
- Uma única action `current`:
  - GET: retorna settings atual (cria com defaults se não existir)
  - PUT/PATCH: atualiza settings
- Seguir padrão do LandlordViewSet

### URL Registration

Adicionar ao router em `core/urls.py`:
```python
router.register(r"persons", PersonViewSet)
router.register(r"credit-cards", CreditCardViewSet)
router.register(r"expense-categories", ExpenseCategoryViewSet)
router.register(r"financial-settings", FinancialSettingsViewSet, basename="financial-settings")
```

---

## TDD

### Passo 1: Escrever testes (RED)

**Cenários obrigatórios em `test_financial_api_simple.py`:**

```python
# PersonViewSet
class TestPersonAPI:
    test_list_persons  # GET /api/persons/ retorna lista
    test_create_person  # POST /api/persons/ cria person
    test_retrieve_person  # GET /api/persons/{id}/ retorna detalhes
    test_update_person  # PUT /api/persons/{id}/ atualiza
    test_partial_update_person  # PATCH /api/persons/{id}/
    test_delete_person  # DELETE /api/persons/{id}/ soft delete
    test_filter_by_is_owner  # ?is_owner=true
    test_filter_by_is_employee  # ?is_employee=true
    test_search_by_name  # ?search=rodrigo

# CreditCardViewSet
class TestCreditCardAPI:
    test_list_credit_cards  # GET /api/credit-cards/
    test_create_credit_card  # POST com person_id
    test_filter_by_person  # ?person_id=1
    test_filter_by_is_active  # ?is_active=true
    test_credit_card_includes_person  # response inclui person nested

# ExpenseCategoryViewSet
class TestExpenseCategoryAPI:
    test_list_categories  # GET /api/expense-categories/
    test_create_category  # POST
    test_update_category  # PUT
    test_delete_category  # DELETE soft delete

# FinancialSettingsViewSet
class TestFinancialSettingsAPI:
    test_get_current_creates_default  # GET cria se não existir
    test_get_current_returns_existing  # GET retorna existente
    test_update_settings  # PUT atualiza
    test_partial_update_settings  # PATCH atualiza parcial
    test_singleton_enforcement  # sempre retorna mesmo registro
```

Use `APIClient` do DRF para os testes. Crie fixtures com `@pytest.fixture` para user admin autenticado e dados de teste.

### Passo 2: Rodar testes (devem FALHAR)
```bash
pytest tests/integration/test_financial_api_simple.py -v
```

### Passo 3: Implementar ViewSets e registrar URLs

### Passo 4: Rodar testes (devem PASSAR)
```bash
pytest tests/integration/test_financial_api_simple.py -v
```

### Passo 5: Rodar suite completa
```bash
pytest
```

---

## Constraints

- NÃO crie os ViewSets de Expense, Income, RentPayment ou EmployeePayment nesta sessão
- NÃO modifique serializers ou models
- NÃO adicione os ViewSets em `core/views.py` — use `core/viewsets/financial_views.py`
- Siga o padrão de permissions existente (ReadOnlyForNonAdmin ou IsAuthenticated)

---

## Critérios de Aceite

- [ ] 4 ViewSets criados em `core/viewsets/financial_views.py`
- [ ] 4 rotas registradas em `core/urls.py`
- [ ] FinancialSettings funciona como singleton (GET cria se necessário)
- [ ] Filtros funcionando (person_id, is_owner, is_active, search)
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Person, CreditCard, Category, Settings API endpoints`
