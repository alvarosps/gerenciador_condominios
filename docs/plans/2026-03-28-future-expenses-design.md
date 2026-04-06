# Future Expenses — Design Spec

**Data:** 2026-03-28
**Escopo:** Puramente frontend — zero mudanças no backend

## Problema

O sistema financeiro permite registrar despesas para qualquer data, mas a UX não oferece um fluxo intuitivo para registrar despesas de meses futuros. Exemplos:

- **Gasto único com pessoa:** Alvaro pagou algo no mercado, mas o valor só será cobrado em Abril. Não há como registrar esse gasto para Abril — o formulário sugere a data atual (Março).
- **Contas de consumo:** A fatura de água de Abril já chegou, mas o formulário não facilita registrá-la para o mês seguinte.
- **Parcelas:** Já suportam datas futuras via `due_date` em cada `ExpenseInstallment`. Não precisam de mudanças.

## Solução

Adicionar um segundo botão **"Nova Despesa ({próximo mês})"** ao lado do botão existente em todas as páginas financeiras que listam despesas. O botão abre o mesmo formulário, mas com `expense_date` pré-preenchida no mês seguinte ao visualizado.

## Validação Técnica

O backend **já suporta** despesas com datas futuras:

- `Expense.expense_date` aceita qualquer data (sem validação min/max)
- `ExpenseSerializer.validate()` não restringe datas futuras
- `CashFlowService._collect_one_time_expenses()` filtra por mês exato (`expense_date__gte=month_start, expense_date__lt=next_month`)
- `DailyControlService._collect_dated_expense_exits()` idem
- `MonthAdvanceService` não precisa de tratamento especial — despesas futuras já estão no mês correto

## Páginas Afetadas

| Página | Arquivo | Botão hoje? | Ação |
|--------|---------|-------------|------|
| Expense Details | `frontend/app/(dashboard)/financial/expenses/details/page.tsx` | Sim ("Nova Despesa") | Adicionar segundo botão ao lado |
| Expenses (lista) | `frontend/app/(dashboard)/financial/expenses/page.tsx` | Não | Adicionar ambos os botões |
| Daily Control | `frontend/app/(dashboard)/financial/daily/page.tsx` | Não | Adicionar ambos os botões |

**Excluídas:** Dashboard financeiro (visualização), Month Advance (ação de fechamento), páginas de configuração.

## Comportamento dos Botões

### Botão "Nova Despesa ({mês atual})"

- Abre o formulário existente
- `expense_date` pré-preenchida com a data equivalente no mês sendo visualizado
- Ex: visualizando Março, hoje dia 28 → `expense_date = 2026-03-28`

### Botão "Nova Despesa ({próximo mês})"

- Abre o mesmo formulário
- `expense_date` pré-preenchida com a data equivalente no mês seguinte ao visualizado
- Ex: visualizando Março, hoje dia 28 → `expense_date = 2026-04-28`
- **Edge case:** Se hoje é dia 31 e o próximo mês tem 30 dias → usa o último dia do mês (ex: 30)

### Labels Dinâmicos

- Usam abreviação do mês: "Nova Despesa (Mar)" e "Nova Despesa (Abr)"
- Baseados no mês sendo visualizado, não no mês calendário atual
- Se visualizando Janeiro, "próximo mês" = Fevereiro (independente de que mês estamos)

## Layout

```
[+ Nova Despesa (Mar)]  [+ Nova Despesa (Abr)]
     (primary)              (outline/secondary)
```

- Botão do mês atual: variante `default` (primary, destaque)
- Botão do próximo mês: variante `outline` (secundário, ação menos comum)
- Ambos lado a lado com `gap` padrão

## Lógica de Data

```typescript
/**
 * Calcula a data default para uma despesa em um mês/ano alvo,
 * usando o dia atual como referência.
 */
function getDefaultExpenseDate(year: number, month: number): string {
  const today = new Date();
  const day = today.getDate();
  const lastDay = new Date(year, month, 0).getDate();
  const targetDay = Math.min(day, lastDay);
  return `${year}-${String(month).padStart(2, '0')}-${String(targetDay).padStart(2, '0')}`;
}
```

Usada em ambos os botões:
- Mês atual: `getDefaultExpenseDate(year, month)` (onde `year`/`month` são do mês visualizado)
- Próximo mês: `getDefaultExpenseDate(nextYear, nextMonth)` (calculado com wrap Dez→Jan)

## Formulário

O formulário existente (`ExpenseFormModal` / `ExpenseEditModal`) **não precisa de mudanças**. Recebe o `expense_date` como valor default. O usuário pode ajustar a data livremente dentro do formulário.

## Avanço de Mês

**Nenhum ajuste necessário.** Despesas com `expense_date` em meses futuros já aparecem automaticamente no mês correto quando consultadas pelo `CashFlowService` e `DailyControlService`. Ao avançar o mês, não há flags para limpar ou dados para migrar.

## Fora de Escopo

- Mudanças no backend (models, serializers, services, views)
- Flag `is_future` no model Expense
- Seção/tab separada para despesas futuras
- Parcelas (`ExpenseInstallment`) — já suportam datas futuras via `due_date`
- Despesas recorrentes (`is_recurring`) — já projetam automaticamente
