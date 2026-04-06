# Sessão 13 — Frontend: Dashboard Financeiro

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 7.3 (Dashboard Widgets)
- `@prompts/SESSION_STATE.md` — Estado atual

Leia estes exemplares:
- `@frontend/app/(dashboard)/page.tsx` — Dashboard existente (composição de widgets)
- `@frontend/app/(dashboard)/_components/` — Widgets existentes (padrão a seguir)
- `@frontend/lib/utils/formatters.ts` — formatCurrency para uso consistente

Leia os hooks da sessão 09:
- `@frontend/lib/api/hooks/use-financial-dashboard.ts`
- `@frontend/lib/api/hooks/use-cash-flow.ts`

---

## Escopo

### Arquivos a CRIAR
- `frontend/app/(dashboard)/financial/page.tsx` — SUBSTITUIR o placeholder da sessão 10
- `frontend/app/(dashboard)/financial/_components/balance-card.tsx`
- `frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx`
- `frontend/app/(dashboard)/financial/_components/person-summary-cards.tsx`
- `frontend/app/(dashboard)/financial/_components/upcoming-installments.tsx`
- `frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx`
- `frontend/app/(dashboard)/financial/_components/category-breakdown-chart.tsx`

---

## Especificação

### Layout do Dashboard (`financial/page.tsx`)

Composição vertical de widgets independentes (cada um busca seus dados):

```tsx
export default function FinancialDashboardPage() {
  return (
    <div className="space-y-6">
      <h1>Dashboard Financeiro</h1>

      {/* Linha 1: 4 cards de resumo */}
      <BalanceCards />

      {/* Linha 2: Gráfico de fluxo de caixa 12 meses */}
      <CashFlowChart />

      {/* Linha 3: Cards por pessoa */}
      <PersonSummaryCards />

      {/* Linha 4: Duas colunas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <UpcomingInstallments />
        <OverdueAlerts />
      </div>

      {/* Linha 5: Gráfico de categorias */}
      <CategoryBreakdownChart />
    </div>
  );
}
```

### Widget 1: BalanceCards (`balance-card.tsx`)

4 stat cards em grid responsivo (1 col mobile, 2 col tablet, 4 col desktop):

| Card | Dado | Cor |
|------|------|-----|
| Saldo do Mês | `current_month_balance` | Verde se positivo, vermelho se negativo |
| Receitas do Mês | `current_month_income` | Azul |
| Despesas do Mês | `current_month_expenses` | Laranja |
| Dívida Total | `total_debt` | Vermelho |

- Hook: `useFinancialOverview()`
- Loading state: `<Skeleton />` cards
- Use `formatCurrency()` de `lib/utils/formatters.ts` — NÃO use toFixed manual
- Ícone + label + valor grande + sub-label (ex: "Receitas - Despesas")

### Widget 2: CashFlowChart (`cash-flow-chart.tsx`)

Gráfico de 12 meses usando `recharts`:

- **Tipo**: `ComposedChart` com `Bar` + `Line`
- **Barras empilhadas**: Receitas (verde), Despesas (vermelho) — lado a lado (não empilhadas de verdade, agrupadas)
- **Linha**: Saldo Acumulado (azul, eixo Y direito)
- **Eixo X**: meses (format "Mar/26")
- **Tooltip**: mostra receita, despesa, saldo do mês, saldo acumulado (formatCurrency)
- **Legenda**: Receitas, Despesas, Saldo Acumulado
- **Meses projetados**: barras com padrão listrado ou opacidade reduzida (distinguish real vs projected)

- Hook: `useCashFlowProjection(12)`
- Seguir padrão do `BuildingStatisticsChart` existente (BarChart com dual Y-axes)
- Loading: spinner centralizado
- Card wrapper com título "Fluxo de Caixa — 12 Meses"

### Widget 3: PersonSummaryCards (`person-summary-cards.tsx`)

Grid de cards, um por pessoa:

Para cada pessoa:
- **Nome** + **Relação** (badge)
- **Recebe**: valor do aluguel/estipêndio (formatCurrency)
- **Cartões**: total de parcelas do mês (formatCurrency) + badge com qtd cartões
- **Empréstimos**: total do mês (formatCurrency)
- **Líquido**: net_amount (formatCurrency, verde/vermelho)
- Mini lista dos cartões com nome + total (se hover ou expandido)

- Hook: `useDebtByPerson()` para resumo, ou iterar `usePersonSummary()` por pessoa
- Opção pragmática: usar `useDebtByPerson()` que já tem card_debt + loan_debt
- Para "receives": buscar via `useCashFlowProjection` ou criar um endpoint simples
  - **Decisão**: usar `useDebtByPerson()` para dívidas + `usePersons()` para dados
  - O monthly "receives" pode ser derivado de PersonIncome no backend (já retornado no person_summary)
  - Se necessário, chamar `useMonthlyCashFlow()` e extrair de lá

### Widget 4: UpcomingInstallments (`upcoming-installments.tsx`)

Card com lista scrollable:
- Header: "Parcelas Próximas (30 dias)" com badge mostrando total
- Lista com: data vencimento, descrição, pessoa, cartão, valor, parcela X/Y
- Itens ordenados por data
- Itens com vencimento ≤ 7 dias: highlight amarelo
- Itens vencidos (overdue que vazaram): highlight vermelho
- Botão "Marcar como pago" inline para cada item

- Hook: `useUpcomingInstallments(30)`
- Loading: `<Skeleton />` linhas

### Widget 5: OverdueAlerts (`overdue-alerts.tsx`)

Card de alertas:
- Header: "Parcelas Vencidas" com badge vermelho se > 0
- Se 0: mostrar mensagem positiva "Nenhuma parcela vencida"
- Se > 0: lista com: descrição, pessoa, dias de atraso, valor
  - Ordenado por dias de atraso DESC (mais atrasado primeiro)
  - Badge: "X dias de atraso" em vermelho

- Hook: `useOverdueInstallments()`

### Widget 6: CategoryBreakdownChart (`category-breakdown-chart.tsx`)

Gráfico de pizza do mês atual:

- **Tipo**: `PieChart` com `Pie` + `Cell` do recharts
- **Dados**: despesas do mês agrupadas por categoria
- **Cores**: usar a `color` de cada ExpenseCategory
- **"Sem Categoria"**: cor cinza (#9CA3AF)
- **Label**: nome da categoria + percentual
- **Tooltip**: nome, valor (formatCurrency), percentual, quantidade
- **Legenda**: abaixo do gráfico

- Hook: `useCategoryBreakdown(currentYear, currentMonth)`
- Card wrapper com título "Despesas por Categoria — {Mês/Ano}"
- Vazio: mensagem "Nenhuma despesa registrada neste mês"

---

## TDD

1. Implementar widgets na ordem: BalanceCards → CashFlowChart → PersonSummaryCards → UpcomingInstallments → OverdueAlerts → CategoryBreakdownChart → page.tsx
2. Cada widget é independente e pode ser testado isoladamente no browser
3. Verificar:
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO modifique o dashboard existente (page.tsx da raiz de dashboard)
- NÃO crie componentes em `components/` — mantenha tudo em `financial/_components/`
- Use `formatCurrency` de `lib/utils/formatters.ts` em TODOS os valores monetários
- Cada widget busca seus próprios dados (hooks independentes)
- Loading states obrigatórios em todos os widgets
- Gráficos usam `recharts` (já instalado no projeto)
- Cards usam as mesmas classes CSS do dashboard existente para consistência visual

---

## Critérios de Aceite

- [ ] 6 widgets implementados e compostos no dashboard
- [ ] BalanceCards mostra saldo com cor condicional
- [ ] CashFlowChart mostra 12 meses com barras e linha de acumulado
- [ ] PersonSummaryCards mostra card por pessoa com breakdown
- [ ] UpcomingInstallments lista parcelas com highlight por urgência
- [ ] OverdueAlerts mostra alertas ou mensagem positiva
- [ ] CategoryBreakdownChart gráfico de pizza com cores das categorias
- [ ] Loading states em todos os widgets
- [ ] `npm run type-check` e `npm run build` passando

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Financial Dashboard with 6 widgets`
