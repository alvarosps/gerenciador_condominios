# Sessão 19 — Frontend: Controle Diário de Entradas e Saídas

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md`
- `@prompts/SESSION_STATE.md` — Estado atual

Leia os hooks existentes:
- `@frontend/lib/api/hooks/use-cash-flow.ts` — CashFlowMonth, PersonSummary
- `@frontend/lib/api/hooks/use-financial-dashboard.ts` — upcoming, overdue
- `@frontend/lib/api/hooks/use-expenses.ts`
- `@frontend/lib/api/hooks/use-expense-installments.ts` — markPaid
- `@frontend/lib/api/hooks/use-rent-payments.ts`
- `@frontend/lib/api/hooks/use-person-payments.ts`

Leia os exemplares:
- `@frontend/app/(dashboard)/financial/_components/upcoming-installments.tsx` — Lista de parcelas próximas
- `@frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx` — Alertas de vencidos

---

## Escopo

### Arquivos a CRIAR

**Backend (novo endpoint):**
- `core/services/daily_control_service.py` — Serviço de controle diário
- `tests/unit/test_financial/test_daily_control_service.py`

**Frontend:**
- `frontend/app/(dashboard)/financial/daily/page.tsx` — Página de controle diário
- `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx` — Timeline dia a dia
- `frontend/app/(dashboard)/financial/daily/_components/daily-summary-cards.tsx` — Cards de resumo
- `frontend/app/(dashboard)/financial/daily/_components/daily-balance-chart.tsx` — Gráfico de saldo diário
- `frontend/app/(dashboard)/financial/daily/_components/day-detail-drawer.tsx` — Drawer com detalhe do dia
- `frontend/lib/api/hooks/use-daily-control.ts` — Hooks para o endpoint

### Arquivos a MODIFICAR
- `core/viewsets/financial_dashboard_views.py` — adicionar DailyControlViewSet ou actions no CashFlowViewSet
- `core/urls.py` — registrar rota
- `frontend/lib/utils/constants.ts` — adicionar rota no ROUTES

---

## Especificação

### Backend: DailyControlService

```python
class DailyControlService:
    @staticmethod
    def get_daily_breakdown(year: int, month: int) -> list[dict]:
        """
        Retorna dia a dia do mês com entradas e saídas esperadas/realizadas.

        Para cada dia do mês:
        {
            "date": "2026-03-07",
            "day_of_week": "Sábado",
            "entries": [
                {"type": "rent", "description": "Aluguel Apto 101/836", "amount": 1200, "expected": true, "paid": true, "payment_date": "2026-03-07"},
                {"type": "income", "description": "Aposentadoria", "amount": 1500, "expected": true, "paid": false},
            ],
            "exits": [
                {"type": "installment", "id": 42, "description": "MEGA BRICK 5/10", "person": "Rodrigo", "card": "Itau Azul", "amount": 60, "due": true, "paid": false},
                {"type": "iptu", "id": 99, "description": "Parcelamento IPTU 836", "amount": 508.33, "due": true, "paid": false},
            ],
            "total_entries": Decimal,
            "total_exits": Decimal,
            "day_balance": Decimal,        # entries - exits do dia
            "cumulative_balance": Decimal,  # saldo acumulado desde dia 1
        }

        Lógica:
        - Entradas: RentPayments esperados (lease.due_day == dia), Income recorrentes, Income avulsas
        - Saídas: ExpenseInstallments (due_date == dia), utility bills (por dia_vencimento), IPTU parcelas, gastos fixos (recurrence_day)
        - Para cada item: verificar se está pago (is_paid/is_received/RentPayment exists)
        """

    @staticmethod
    def get_month_summary(year: int, month: int) -> dict:
        """
        Resumo do mês:
        {
            "total_expected_income": Decimal,
            "total_received_income": Decimal,
            "total_expected_expenses": Decimal,
            "total_paid_expenses": Decimal,
            "overdue_count": int,
            "overdue_total": Decimal,
            "upcoming_7_days_count": int,
            "upcoming_7_days_total": Decimal,
            "current_balance": Decimal,     # received - paid até hoje
            "projected_balance": Decimal,   # total expected income - total expected expenses
        }
        """

    @staticmethod
    def mark_item_paid(item_type: str, item_id: int, payment_date: date) -> dict:
        """
        Marca um item como pago:
        - "installment" → ExpenseInstallment.is_paid = True
        - "expense" → Expense.is_paid = True
        - "income" → Income.is_received = True
        """
```

### Backend: Endpoint

```
GET /api/daily-control/breakdown/?year=2026&month=3
GET /api/daily-control/summary/?year=2026&month=3
POST /api/daily-control/mark_paid/  body: {"item_type": "installment", "item_id": 42, "payment_date": "2026-03-22"}
```

### Frontend: Layout da Página

```
┌─────────────────────────────────────────────────────────┐
│ Controle Diário - Março 2026        [◄ Fev] [Abr ►]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                    │
│ │Saldo │ │Recebi│ │Paguei│ │Venci │                    │
│ │Atual │ │do    │ │      │ │das   │                    │
│ │R$2.3k│ │R$15k │ │R$12k │ │  5   │                    │
│ └──────┘ └──────┘ └──────┘ └──────┘                    │
│                                                         │
│ ┌─── Gráfico Saldo Diário (LineChart) ───────────────┐ │
│ │ Linha de saldo acumulado dia a dia                  │ │
│ │ Barras de entradas (verde) e saídas (vermelho)      │ │
│ │ Linha pontilhada = projeção (dias futuros)          │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─── Timeline ──────────────────────────────────────┐  │
│ │ 📅 07/03 (Sexta) ────────── Saldo: R$2.300       │  │
│ │   ↓ Aluguel Apto 101/836    +R$1.200  ✅ Pago    │  │
│ │   ↓ Aposentadoria            +R$1.500  ✅ Pago    │  │
│ │   ↑ MEGA BRICK 5/10          -R$60    ❌ Pendente │  │
│ │     [Marcar pago]                                  │  │
│ │                                                    │  │
│ │ 📅 09/03 (Domingo) ──────── Saldo: R$3.440       │  │
│ │   ↑ Fatura Itau Azul         -R$2.158  ❌ Vencida │  │
│ │     [Marcar pago]                                  │  │
│ │   ...                                              │  │
│ └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Widget: Daily Summary Cards

4 cards no topo:
| Card | Dado | Cor |
|------|------|-----|
| Saldo Atual | received - paid (até hoje) | Verde/Vermelho |
| Recebido | total_received_income | Azul |
| Pago | total_paid_expenses | Laranja |
| Vencidas | overdue_count (badge) + overdue_total | Vermelho se > 0 |

### Widget: Daily Balance Chart

`ComposedChart` (recharts):
- Eixo X: dias do mês (1-31)
- Barras: entradas (verde) e saídas (vermelho) por dia
- Linha: saldo acumulado
- Dias passados: cores sólidas
- Dias futuros: cores transparentes (projeção)
- Hoje: marcador vertical

### Widget: Daily Timeline

Lista agrupada por dia:
- Header: data + dia da semana + saldo acumulado do dia
- Cada item: ícone (↓ entrada / ↑ saída) + descrição + valor + status
- Status: ✅ Pago (verde) | ❌ Pendente (cinza) | ⚠️ Vencida (vermelho)
- Botão "Marcar pago" em cada item pendente/vencido
- Ao marcar como pago: chama `mark_paid`, invalida queries, atualiza inline

### Widget: Day Detail Drawer

Ao clicar num dia, abre drawer lateral com:
- Todas as entradas detalhadas
- Todas as saídas detalhadas
- Subtotais
- Botões de ação: marcar pago, registrar pagamento avulso

### Filtros
- Mês/ano (navegação com setas)
- Tipo: Todos / Entradas / Saídas
- Status: Todos / Pagos / Pendentes / Vencidos
- Pessoa (select)
- Prédio (select)

---

## TDD

### Backend:
```bash
pytest tests/unit/test_financial/test_daily_control_service.py -v
```

Testes obrigatórios:
```python
class TestDailyBreakdown:
    test_returns_all_days_of_month  # 28-31 dias
    test_rent_entries_on_due_day  # aluguel aparece no dia certo
    test_recurring_income_on_correct_day  # aposentadoria dia 7
    test_installments_on_due_date  # parcelas no dia de vencimento
    test_paid_items_marked  # itens pagos mostram status correto
    test_cumulative_balance  # saldo acumulado correto
    test_excludes_offset_expenses  # offsets não aparecem como saídas

class TestMonthSummary:
    test_summary_totals  # expected vs received vs paid
    test_overdue_count  # conta vencidas corretamente
    test_current_balance  # saldo até hoje

class TestMarkPaid:
    test_mark_installment_paid  # marca parcela como paga
    test_mark_expense_paid  # marca despesa como paga
    test_mark_income_received  # marca receita como recebida
```

### Frontend:
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO modifique outros dashboards ou páginas existentes
- O `mark_paid` endpoint deve validar que o item existe e não está já pago
- A timeline deve ser otimizada: não renderizar 31 dias se o mês tem poucos eventos
- Dias sem nenhuma entrada/saída podem ser colapsados
- Use `formatCurrency` e `formatDate` dos utils existentes
- Loading states em todos os widgets
- A página deve ser responsiva (mobile: timeline vertical, desktop: com gráfico lateral)

---

## Critérios de Aceite

- [ ] Backend: DailyControlService com 3 métodos
- [ ] Backend: Endpoint com breakdown, summary, mark_paid
- [ ] Backend: Todos os testes passando
- [ ] Frontend: Página de controle diário com 4 widgets
- [ ] Frontend: Summary cards com saldo atual, recebido, pago, vencidas
- [ ] Frontend: Gráfico de saldo diário com projeção
- [ ] Frontend: Timeline agrupada por dia com status visual
- [ ] Frontend: Botão "Marcar pago" funcional inline
- [ ] Frontend: Filtros por mês, tipo, status, pessoa, prédio
- [ ] Frontend: Drawer de detalhe do dia
- [ ] `npm run type-check` e `npm run build` passando
- [ ] `pytest` completo passando

---

## Handoff

1. Rodar `pytest` completo + `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add Daily Control page with timeline, balance chart, and mark-paid actions`
