# Sessão 16 — Backend: Correções Críticas + Gaps de Serviço

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md`
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md`

Leia o código a corrigir:
- `@core/services/simulation_service.py` — Bug crítico linhas 237 e 263
- `@core/services/cash_flow_service.py` — Gaps de lógica
- `@core/services/financial_dashboard_service.py` — Gap no category_breakdown
- `@core/models.py` — Expense model (precisa de end_date)

---

## Escopo

### Arquivos a CRIAR
- `core/migrations/0016_add_expense_end_date.py` — via makemigrations
- `tests/unit/test_financial/test_gap_fixes.py` — testes de regressão para todos os gaps

### Arquivos a MODIFICAR
- `core/models.py` — adicionar `end_date` ao Expense
- `core/serializers.py` — adicionar `end_date` ao ExpenseSerializer
- `core/services/simulation_service.py` — fix SyntaxError
- `core/services/cash_flow_service.py` — 4 correções
- `core/services/financial_dashboard_service.py` — 1 correção

---

## Especificação

### Fix 1: SyntaxError no SimulationService (Gap 7 — CRÍTICO)

```python
# ERRADO (Python 2):
except Apartment.DoesNotExist, Lease.DoesNotExist:

# CORRETO (Python 3):
except (Apartment.DoesNotExist, Lease.DoesNotExist):
```

Corrigir nas linhas ~237 e ~263. Verificar se há outras ocorrências no arquivo.

### Fix 2: Adicionar `end_date` ao Expense (Gap 2)

```python
# Em core/models.py, na classe Expense:
end_date = models.DateField(
    null=True, blank=True,
    help_text="Data fim para gastos fixos recorrentes. Projeção para após esta data."
)
```

Adicionar `end_date` ao `ExpenseSerializer.fields`.
Gerar migration.

### Fix 3: `_collect_fixed_expenses` — respeitar `end_date` e `person` (Gaps 1 e 2)

No `CashFlowService._collect_fixed_expenses()`:

```python
# Filtrar gastos fixos que ainda estão ativos no mês consultado
qs = Expense.objects.filter(
    expense_type=ExpenseType.FIXED_EXPENSE,
    is_recurring=True,
    is_offset=False,
)

# Excluir gastos que já terminaram (end_date antes do mês consultado)
qs = qs.exclude(end_date__lt=month_start)

# Para cada gasto fixo, incluir person_name nos details
```

No `get_person_summary()`, adicionar coleta de gastos fixos vinculados à pessoa:
```python
# Fixed expenses for this person
fixed_for_person = Expense.objects.filter(
    expense_type=ExpenseType.FIXED_EXPENSE,
    is_recurring=True,
    person=person,
    is_offset=False,
).exclude(end_date__lt=month_start)

fixed_total = sum(e.expected_monthly_amount or e.total_amount for e in fixed_for_person)
# Incluir no net_amount: net_amount = receives - card_total - loan_total - fixed_total + offset_total
```

### Fix 4: Projeção de parcelas futuras não filtra `is_offset` (Gap 4)

No `CashFlowService._get_projected_expenses()`, adicionar filtro:

```python
# Ao somar installments futuras para projeção:
installments_total = ExpenseInstallment.objects.filter(
    due_date__gte=month_start,
    due_date__lt=next_month,
    expense__is_offset=False,  # ADICIONAR
).aggregate(...)
```

### Fix 5: `_collect_utility_bills` não filtra `is_offset` (Gap 3)

```python
qs = Expense.objects.filter(
    expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
    is_debt_installment=False,
    is_offset=False,  # ADICIONAR
    expense_date__gte=month_start,
    expense_date__lt=next_month,
)
```

### Fix 6: `get_expense_category_breakdown` inclui offsets (Gap 6)

```python
expenses_in_month = Expense.objects.filter(
    expense_date__gte=month_start,
    expense_date__lt=next_month,
    is_offset=False,  # ADICIONAR
)
```

### Fix 7: Simulação não modela offsets (Gap 8)

Não criar novo cenário, apenas garantir que a projeção base (que vem do CashFlowService) já exclui offsets corretamente após os fixes 4 e 5.

---

## TDD

### Passo 1: Escrever testes (RED)

```python
class TestSimulationServiceSyntaxFix:
    test_simulate_from_db_does_not_crash  # importação do módulo funciona
    test_change_rent_scenario  # _db_change_rent funciona
    test_remove_tenant_scenario  # _db_remove_tenant funciona

class TestExpenseEndDate:
    test_create_expense_with_end_date  # campo aceita data
    test_end_date_nullable  # campo é opcional

class TestFixedExpenseEndDate:
    test_fixed_expense_with_end_date_excluded_after  # gasto fixo não aparece após end_date
    test_fixed_expense_without_end_date_projects_forever  # sem end_date continua projetando
    test_fixed_expense_with_person_in_person_summary  # gasto fixo aparece no resumo da pessoa

class TestIsOffsetFiltering:
    test_projected_installments_exclude_offset  # projeção não inclui offset
    test_utility_bills_exclude_offset  # contas de consumo não incluem offset
    test_category_breakdown_excludes_offset  # breakdown exclui offset
```

### Passo 2-6: Ciclo TDD padrão

```bash
pytest tests/unit/test_financial/test_gap_fixes.py -v
```

---

## Constraints

- NÃO altere a lógica de negócio existente que está funcionando
- NÃO modifique testes existentes
- O `end_date` deve ser usado APENAS para `FIXED_EXPENSE` com `is_recurring=True` — não afeta outros tipos
- Mantenha backward compatibility: `end_date=None` = sem data fim (projeta indefinidamente)

---

## Critérios de Aceite

- [ ] `simulation_service.py` importa sem erro no Python 3.14
- [ ] `end_date` adicionado ao Expense + migration gerada
- [ ] `_collect_fixed_expenses` respeita `end_date`
- [ ] `get_person_summary` inclui gastos fixos da pessoa
- [ ] Projeção de parcelas filtra `is_offset=False`
- [ ] `_collect_utility_bills` filtra `is_offset=False`
- [ ] `get_expense_category_breakdown` filtra `is_offset=False`
- [ ] Todos os testes passando
- [ ] Suite completa `pytest` passando

---

## Handoff

1. Rodar `pytest` completo
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `fix(financial): critical syntax fix + end_date + is_offset filtering gaps`
