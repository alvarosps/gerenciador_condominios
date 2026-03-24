# Sessão 14 — Frontend: Simulador Financeiro

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seções 2.5 (Simulação) e 7.5 (Simulador)
- `@prompts/SESSION_STATE.md` — Estado atual

Leia o código já implementado:
- `@frontend/app/(dashboard)/financial/_components/cash-flow-chart.tsx` — Gráfico de fluxo (reutilizar padrão)
- `@frontend/lib/api/hooks/use-simulation.ts` — Hook de simulação
- `@frontend/lib/api/hooks/use-cash-flow.ts` — Hook de projeção

---

## Escopo

### Arquivos a CRIAR
- `frontend/app/(dashboard)/financial/simulator/page.tsx`
- `frontend/app/(dashboard)/financial/simulator/_components/scenario-builder.tsx`
- `frontend/app/(dashboard)/financial/simulator/_components/scenario-card.tsx`
- `frontend/app/(dashboard)/financial/simulator/_components/comparison-chart.tsx`
- `frontend/app/(dashboard)/financial/simulator/_components/comparison-table.tsx`
- `frontend/app/(dashboard)/financial/simulator/_components/impact-summary.tsx`

---

## Especificação

### Página do Simulador (`simulator/page.tsx`)

**Layout:**
```
┌──────────────────────────────────────────────┐
│  Simulador Financeiro                         │
├──────────────────────────────────────────────┤
│  [Gráfico Comparativo - Base vs Simulado]     │
│                                               │
├──────────┬───────────────────────────────────┤
│ Cenários │  [Impact Summary]                  │
│ ────────── ──────────────────────────────────│
│ [+Cenário]│  [Tabela Comparativa Mês a Mês]  │
│           │                                   │
│ Card 1    │                                   │
│ Card 2    │                                   │
│ Card 3    │                                   │
│           │                                   │
└──────────┴───────────────────────────────────┘
```

**Estado:**
```typescript
const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
const [isAddingScenario, setIsAddingScenario] = useState(false);
```

**Fluxo:**
1. Página carrega com projeção base via `useCashFlowProjection(12)`
2. Usuário adiciona cenários via ScenarioBuilder
3. A cada mudança nos cenários, chama `useSimulation()` com lista completa
4. Gráfico e tabela atualizam com resultado comparativo

### ScenarioBuilder (`scenario-builder.tsx`)

Modal/drawer para criar um cenário:

**Tipo de cenário** (select):
1. **Quitar Despesa Antecipada** (`pay_off_early`)
   - Select de despesas parceladas ativas (via `useExpenses({is_installment: true, is_paid: false})`)
   - Mostra: descrição, parcelas restantes, valor restante

2. **Alterar Aluguel** (`change_rent`)
   - Select de apartamento (via `useApartments()`)
   - Input: novo valor (R$)
   - Mostra: valor atual para referência

3. **Novo Empréstimo** (`new_loan`)
   - Input: valor total (R$)
   - Input: número de parcelas
   - Input: mês inicial (month picker)

4. **Remover Inquilino** (`remove_tenant`)
   - Select de apartamento ocupado (via `useApartments({is_rented: true})`)
   - Mostra: valor do aluguel que será perdido

5. **Adicionar Gasto Fixo** (`add_fixed_expense`)
   - Input: valor mensal (R$)
   - Input: descrição

6. **Remover Gasto Fixo** (`remove_fixed_expense`)
   - Select de gastos fixos ativos (via `useExpenses({expense_type: 'fixed_expense', is_recurring: true})`)

**Cada cenário após criado:**
- Aparece como um `ScenarioCard` no painel lateral
- Pode ser removido (botão X)
- Mostra resumo do cenário (ex: "Quitar Nubank Rodrigo — 8 parcelas de R$200")

### ScenarioCard (`scenario-card.tsx`)

Card compacto mostrando:
- Ícone por tipo de cenário
- Título (ex: "Quitar Cartão")
- Descrição resumida
- Impacto estimado (se disponível do resultado de simulação)
- Botão X para remover

### ComparisonChart (`comparison-chart.tsx`)

Gráfico `ComposedChart` do recharts:
- **Duas linhas**: Saldo Acumulado Base (cinza/azul) vs Saldo Acumulado Simulado (verde)
- **Área**: preenchimento entre as linhas mostrando o delta (verde se melhora, vermelho se piora)
- **Eixo X**: meses (12)
- **Tooltip**: base, simulado, delta (formatCurrency)
- **Legenda**: "Cenário Atual", "Cenário Simulado"

Se não há cenários, mostra só a linha base.

### ComparisonTable (`comparison-table.tsx`)

Tabela mês a mês:

| Mês | Receita Base | Despesa Base | Saldo Base | Receita Sim. | Despesa Sim. | Saldo Sim. | Delta |
|-----|-------------|-------------|-----------|-------------|-------------|-----------|-------|
| Mar/26 | R$ X | R$ Y | R$ Z | R$ X' | R$ Y' | R$ Z' | +R$ D |

- Valores formatados com `formatCurrency`
- Delta com cor: verde se positivo, vermelho se negativo
- Linha de total no rodapé
- Scroll horizontal no mobile

### ImpactSummary (`impact-summary.tsx`)

Card de resumo do impacto:
- **Impacto Total 12 meses**: soma dos deltas (formatCurrency, com cor)
- **Mês de Equilíbrio**: quando o saldo acumulado simulado vira positivo (ou "Não previsto nos próximos 12 meses")
- **Saldo Final Base**: acumulado no mês 12
- **Saldo Final Simulado**: acumulado no mês 12

---

## TDD

1. Implementar componentes bottom-up: ScenarioCard → ScenarioBuilder → ComparisonChart → ComparisonTable → ImpactSummary → page.tsx
2. Verificar com dados reais no browser
3. Verificar:
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO modifique o backend — use os endpoints existentes
- A simulação é client-side trigger, server-side compute (POST /api/cash-flow/simulate/)
- Cenários são efêmeros (não persistidos) — vivem no state da página
- NÃO adicione localStorage ou cache para cenários
- Se a API retornar erro na simulação, mostrar toast de erro e manter cenários (não limpar)
- O gráfico deve funcionar sem cenários (mostra apenas projeção base)

---

## Critérios de Aceite

- [ ] 6 tipos de cenário disponíveis no builder
- [ ] Cenários adicionados aparecem como cards no painel
- [ ] Cenários podem ser removidos
- [ ] Gráfico comparativo atualiza ao adicionar/remover cenários
- [ ] Tabela mês a mês com deltas coloridos
- [ ] ImpactSummary mostra impacto total e mês de equilíbrio
- [ ] Funciona sem cenários (mostra projeção base)
- [ ] `npm run type-check` e `npm run build` passando

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Financial Simulator with scenario builder and comparison`
