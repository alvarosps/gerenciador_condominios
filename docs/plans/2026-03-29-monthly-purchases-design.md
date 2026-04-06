# Compras do Mês — Design Spec

**Data:** 2026-03-29
**Escopo:** Backend (novo endpoint + serviço) + Frontend (nova página + navegação)

## Problema

O dashboard financeiro mostra o total de despesas do mês, mas inclui parcelas em andamento de compras antigas. Não existe uma visão filtrada que mostre apenas **compras novas** do mês — o que foi efetivamente adquirido/contratado naquele período.

## Solução

Nova página "Compras do Mês" com endpoint dedicado que filtra apenas despesas novas: compras com parcela #1 no mês, contas de consumo, gastos únicos e fixos. Inclui gráficos por categoria (pizza) e por tipo (barras).

## Critério de Inclusão

| Tipo | Critério | Query |
|------|----------|-------|
| Compras no cartão | Parcela #1 vence no mês | `ExpenseInstallment.filter(installment_number=1, expense__expense_type=CARD_PURCHASE, due_date__gte=month_start, due_date__lt=next_month, expense__is_offset=False)` |
| Empréstimos (bancário/pessoal) | Parcela #1 vence no mês | `ExpenseInstallment.filter(installment_number=1, expense__expense_type__in=[BANK_LOAN, PERSONAL_LOAN], due_date__gte=month_start, due_date__lt=next_month, expense__is_offset=False)` |
| Contas de consumo (água, luz) | `expense_date` no mês | `Expense.filter(expense_type__in=[WATER_BILL, ELECTRICITY_BILL], expense_date__gte=month_start, expense_date__lt=next_month, is_offset=False)` |
| Gastos únicos | `expense_date` no mês | `Expense.filter(expense_type=ONE_TIME_EXPENSE, expense_date__gte=month_start, expense_date__lt=next_month, is_offset=False)` |
| Gastos fixos mensais | Ativo no mês | `Expense.filter(expense_type=FIXED_EXPENSE, is_recurring=True, expected_monthly_amount__isnull=False, is_offset=False)` + filtro `end_date` nulo ou >= month_start |

Todos excluem:
- `is_offset=True` (descontos)
- Itens em `ExpenseMonthSkip` para o mês consultado

## Backend

### Endpoint

`GET /api/financial-dashboard/monthly_purchases/?year=2026&month=3`

### Response

```json
{
  "year": 2026,
  "month": 3,
  "total": 5430.00,
  "by_type": {
    "card_purchases": {
      "total": 2500.00,
      "count": 5,
      "items": [
        {
          "description": "Compra Amazon",
          "amount": 500.00,
          "total_amount": 6000.00,
          "total_installments": 12,
          "person_name": "Rodrigo",
          "card_name": "Nubank",
          "category_name": "Eletrônicos",
          "category_color": "#ff6b6b",
          "date": "2026-03-15",
          "expense_type": "card_purchase"
        }
      ]
    },
    "loans": {
      "total": 800.00,
      "count": 1,
      "items": [...]
    },
    "utility_bills": {
      "total": 430.00,
      "count": 2,
      "items": [...]
    },
    "one_time_expenses": {
      "total": 1200.00,
      "count": 3,
      "items": [...]
    },
    "fixed_expenses": {
      "total": 500.00,
      "count": 2,
      "items": [...]
    }
  },
  "by_category": [
    {
      "category_id": 1,
      "category_name": "Alimentação",
      "color": "#ff6b6b",
      "total": 1200.00,
      "percentage": 22.1,
      "count": 5
    }
  ]
}
```

### Item Fields

Cada item em `by_type.*.items` contém:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `description` | string | Descrição da despesa |
| `amount` | decimal | Valor da parcela ou gasto |
| `total_amount` | decimal, nullable | Valor total da compra (para parcelados) |
| `total_installments` | int, nullable | Total de parcelas (para parcelados) |
| `person_name` | string, nullable | Nome da pessoa vinculada |
| `card_name` | string, nullable | Nome do cartão (para compras no cartão) |
| `category_name` | string, nullable | Nome da categoria |
| `category_color` | string, nullable | Cor da categoria (hex) |
| `date` | string (YYYY-MM-DD) | Data de vencimento (parcela) ou data da despesa |
| `expense_type` | string | Tipo da despesa |

### Serviço

Novo método estático em `core/services/financial_dashboard_service.py`:

```python
@staticmethod
def get_monthly_purchases(year: int, month: int) -> dict[str, Any]:
    """Return only new purchases/expenses for the given month."""
```

### ViewSet

Nova action em `core/viewsets/financial_dashboard_views.py`:

```python
@action(detail=False, methods=["get"])
def monthly_purchases(self, request: Request) -> Response:
```

## Frontend

### Página

**Rota:** `/financial/monthly-purchases`
**Arquivo:** `frontend/app/(dashboard)/financial/monthly-purchases/page.tsx`

### Layout

```
[Navegação de mês: < Março 2026 >]

[Card: Cartão]  [Card: Contas]  [Card: Empréstimos]  [Card: Únicos]  [Card: Fixos]
  R$ 2.500        R$ 430          R$ 800               R$ 1.200        R$ 500

[Gráfico pizza por categoria]     [Gráfico barras por tipo]

[Acordeões colapsáveis por tipo — read-only]
  ▸ Compras no Cartão (5 itens — R$ 2.500,00)
      | Descrição          | Pessoa   | Cartão  | Valor    | Total   | Parcelas |
      | Compra Amazon       | Rodrigo  | Nubank  | R$ 500   | R$ 6000 | 1/12     |
  ▸ Contas de Consumo (2 itens — R$ 430,00)
  ▸ Empréstimos (1 item — R$ 800,00)
  ▸ Gastos Únicos (3 itens — R$ 1.200,00)
  ▸ Gastos Fixos Mensais (2 itens — R$ 500,00)
```

### Componentes

| Componente | Responsabilidade |
|------------|-----------------|
| `MonthlyPurchasesPage` | Página principal com navegação de mês |
| `PurchaseSummaryCards` | 5 cards com total por tipo |
| `PurchaseCategoryChart` | Gráfico pizza — reutiliza padrão do `CategoryBreakdownChart` |
| `PurchaseTypeChart` | Gráfico barras — total por tipo |
| `PurchaseAccordion` | Acordeão por tipo com tabela de itens (read-only) |

Todos em `frontend/app/(dashboard)/financial/monthly-purchases/_components/`.

### Hook

`frontend/lib/api/hooks/use-monthly-purchases.ts`:

```typescript
export function useMonthlyPurchases(year: number, month: number) {
  return useQuery({
    queryKey: ['monthly-purchases', year, month],
    queryFn: () => apiClient.get('/financial-dashboard/monthly_purchases/', { params: { year, month } }),
  });
}
```

### Navegação

1. **Sidebar:** Nova entrada "Compras do Mês" no menu financeiro (entre "Despesas" e "Controle Diário")
2. **Dashboard financeiro:** Botão "Ver compras do mês →" no `ExpenseSummaryCard` ou como card dedicado

### Navegação de mês

Mesmo padrão usado em `daily/page.tsx` e `expenses/page.tsx`:
- `useState` para year/month
- Botões `<` e `>` com wrap Dez→Jan
- Label com nome do mês + ano

## Fora de Escopo

- Ações de edição/exclusão nos itens (somente visualização)
- IPTU (não é "compra do mês" — é imposto recorrente anual)
- Salários de funcionários (não são "compras")
- Estipêndios (não são "compras")
- Parcelas de dívida (`is_debt_installment=True`) — são renegociações, não compras novas
- Despesas offset (`is_offset=True`)
