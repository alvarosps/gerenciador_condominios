# Design — Calendário de Controle de Aluguéis (Dashboard)

**Data**: 2026-06-02
**Status**: Aprovado (design + mockup validados)
**Mockup**: `docs/mockups/rent-calendar-mockup.html` (light + dark)
**Sessões de implementação**: `prompts/21-*.md` a `prompts/25-*.md`

---

## 1. Objetivo

Bloco no **topo do dashboard** para controle manual mensal dos aluguéis: ver, por dia do
mês, os inquilinos cujo aluguel vence naquele dia, marcar/desmarcar pago via toggle,
destacar atrasos (com multa) e exibir um mini-resumo do mês. Processo hoje manual; no
futuro poderá integrar com conta bancária e com o dashboard financeiro — **fora de escopo agora**.

### Layout (3 colunas, responsivo)

1. **Painel do dia** — inquilinos do dia atual (ou do dia selecionado) + toggle pago + atraso/multa + botões "Hoje" e "Próximo vencimento".
2. **Grade do mês** — todos os dias, chips com nome do inquilino, hoje destacado, clique seleciona o dia (muda a coluna 1), navegação de mês.
3. **Stats do mês** — mês atual, recebido até hoje, a receber, kitnets não alugados (nº + soma de aluguel).

Mobile: as 3 colunas empilham verticalmente.

## 2. Escopo

### Incluído
- Endpoint de leitura do calendário (dias + itens + stats) por `year`/`month`/`building_id?`.
- Endpoint de toggle (marcar/desmarcar pago) reaproveitando `RentPayment`.
- Clamping do dia de vencimento ao último dia do mês (31 → 30/28/29).
- Multa de atraso exibida (reuso de `FeeCalculatorService`).
- Filtro opcional por prédio (default: todos agregados).
- UI 3 colunas responsiva, light + dark (tokens de tema).

### NÃO incluído (YAGNI)
- Integração com o dashboard financeiro (UI) ou conta bancária.
- Contas/despesas por dia (água/luz) no calendário.
- Pagamentos parciais, múltiplos pagamentos por mês, notas por dia.
- Novo model de persistência por dia.

## 3. Decisões (confirmadas)

| # | Decisão | Valor |
|---|---------|-------|
| D1 | Escopo de prédios | Todos agregados + filtro opcional por prédio |
| D2 | Quais aluguéis aparecem | **Só os cobráveis** — exclui `apartment.owner` (repasse), `is_salary_offset`, e meses já pré-pagos (`prepaid_until` **>** vencimento clampado do mês — modelo *pagar-para-morar*; a parcela que vence exatamente em `prepaid_until` é a próxima a vencer e é **mantida**) |
| D3 | Renderização do calendário | **Grid custom** com `date-fns` + Tailwind + primitivos shadcn (sem dayjs, sem nova dependência) |
| D4 | Atraso | Destacar em vermelho **e** exibir multa calculada (`FeeCalculatorService.calculate_late_fee`) |

### Premissas (derivadas, não levantam dúvida)
- **A1 — Permissão**: admin-only. Todo o `DashboardViewSet` já é `IsAdminUser` (`core/views.py:598`).
- **A2 — Finalização de mês**: o toggle **respeita** `MonthSnapshot` finalizado — `RentPayment` é dado compartilhado com o financeiro; não corromper meses fechados. Mês finalizado ⇒ `can_toggle=false`.
- **A3 — Dia de vencimento**: `lease.responsible_tenant.due_day` (1–31). Mesmo critério já usado em `DailyControlService._collect_entries_by_day`.
- **A4 — Pago = existência de `RentPayment`** para `(lease, reference_month=dia 1 do mês)`. Desmarcar = soft-delete do registro.
- **A5 — Valor ao marcar pago**: valor efetivo do mês (honra `pending_rental_value`/`pending_rental_value_date`); `payment_date = hoje`. One-click, sem modal.

## 4. Arquitetura

Direção de dependências respeitada (`.claude/rules/architecture.md`): **Views → Services → Models**.

```
Backend
  core/services/rent_schedule_service.py   (NOVO)   ← fonte única da lógica "aluguel devido no mês"
      ├─ usado por DashboardViewSet (novo endpoint do calendário)
      └─ usado por DailyControlService (refatorado — elimina duplicação / DRY)
  core/services/fee_calculator.py          (REUSO)  multa de atraso
  core/services/date_calculator.py         (REUSO)  end_date do lease (calculate_final_date)
  core/views.py  DashboardViewSet          (+2 actions: rent_calendar, toggle_rent_payment)

Frontend
  lib/api/hooks/use-rent-calendar.ts       (NOVO)   useRentCalendar + useToggleRentPayment (optimistic)
  lib/api/query-keys.ts                     (+keys)
  app/(dashboard)/_components/rent-calendar/*  (NOVO)  5 componentes
  app/(dashboard)/page.tsx                  (montar no topo)
  app/(dashboard)/_components/late-payments-alert.tsx  (refatorar p/ toggle unificado)
```

### 4.1 `RentScheduleService` (novo) — `core/services/rent_schedule_service.py`

Service com `@staticmethod` (padrão `FeeCalculatorService`, `fee_calculator.py:20-197`).

```python
class RentScheduleService:
    @staticmethod
    def clamp_due_day(due_day: int, year: int, month: int) -> int:
        """min(due_day, dias_do_mês). Ex.: 31 em fev → 28/29."""

    @staticmethod
    def effective_rental_value(lease: Lease, reference_month: date) -> Decimal:
        """rental_value, ou pending_rental_value se reference_month >= pending_rental_value_date."""

    @staticmethod
    def collectible_leases(reference_month: date, building_id: int | None = None) -> QuerySet[Lease]:
        """Leases cobráveis ativos que cobrem o mês: não-deletados, apartment.owner is null,
        is_salary_offset=False, mês não pré-pago (prepaid_until > vencimento clampado do mês —
        pagar-para-morar; a parcela que vence exatamente em prepaid_until é a próxima a vencer,
        mantida), e janela start_date..end_date
        (via DateCalculatorService.calculate_final_date) intersecta o mês. Filtro opcional por prédio.
        select_related(apartment, apartment__building, responsible_tenant)."""

    @staticmethod
    def get_month_schedule(year: int, month: int, building_id: int | None = None) -> dict:
        """Estrutura completa: year, month, today, next_due_date, days[] (cada um com items[]),
        stats{}. O rótulo do mês ("Junho 2026") é derivado no frontend via date-fns/ptBR a partir
        de year/month — o backend NÃO retorna month_label."""

    @staticmethod
    def get_month_stats(year: int, month: int, building_id: int | None = None) -> dict:
        """received_total, to_receive_total, expected_total, paid_count, due_count,
        overdue_count, overdue_total_fee, vacant_kitnets_count, vacant_kitnets_value."""

    @staticmethod
    def toggle_payment(lease_id: int, reference_month: date, user: User) -> dict:
        """Cria ou soft-deleta RentPayment. Valida: lease cobrável, mês não finalizado,
        e (se pago + dia já passou) recusa desmarcar. Retorna {status, is_paid, message}."""
```

**Item do dia** (dict):
`lease_id, tenant_name, apartment_number, building_number, rental_value, is_paid,
payment_date|null, is_overdue, day_passed, can_toggle, late_fee, late_days`.

- `is_overdue = (not is_paid) and (clamped_due_date < today)` — apenas mês corrente/passado.
- `day_passed = clamped_due_date < today`.
- `can_toggle = (not month_finalized) and not (is_paid and day_passed)`.
- `late_fee`/`late_days` via `FeeCalculatorService.calculate_late_fee(effective_value, clamped_due_day, today)` quando `is_overdue`.

### 4.2 Refatoração DRY do `DailyControlService`

`_collect_entries_by_day` (rent, `daily_control_service.py:337-365`), `_get_expected_rent_total`
(`:669-680`) e `_get_received_rent_total` (`:704-710`) passam a usar `RentScheduleService`
(`collectible_leases` + `clamp_due_day` + `effective_rental_value`). A refatoração migra
**intencionalmente** a seleção de aluguel para a fonte única **date-aware**: a porção de aluguel
deixa de filtrar pelo booleano `apartment.is_rented` e passa a usar a janela `start_date..end_date`.
Na maioria dos casos o resultado é idêntico; difere (corretamente) nos casos de borda `is_rented`
vs janela — cobertos por `test_excludes_lease_window_outside_month_even_if_rented` e
`test_includes_lease_covering_month_regardless_of_is_rented`. Os 16 testes de
`tests/unit/test_financial/test_daily_control_service.py` permanecem verdes.

### 4.3 Endpoints — `DashboardViewSet` (`core/views.py:578`)

Seguir o padrão `@action(detail=False)` já presente (`late_payment_summary` `:668`, `mark_rent_paid` `:722`).

- `GET /api/dashboard/rent_calendar/?year=&month=&building_id=` → `RentScheduleService.get_month_schedule(...)`.
- `POST /api/dashboard/toggle_rent_payment/` body `{lease_id, reference_month}` → `RentScheduleService.toggle_payment(...)`.
- **Unificar** `mark_rent_paid` (`:722`, só-cria/mês-fixo) → removido; o consumidor `late-payments-alert.tsx`/`use-dashboard.ts` (`useMarkRentPaid`) passa a usar `toggle_rent_payment` (sem backward-compat, conforme `.claude/rules/design-principles.md`).

**Resposta `rent_calendar`** (dicts, como os demais endpoints do dashboard):
```jsonc
{ "year":2026, "month":6, "today":"2026-06-02", "next_due_date":"2026-06-05",
  "days":[ { "day":5, "date":"2026-06-05", "weekday":"Sexta",
    "items":[{ "lease_id":12,"tenant_name":"João Silva","apartment_number":101,
      "building_number":"836","rental_value":"1500.00","is_paid":false,
      "is_overdue":false,"day_passed":false,"can_toggle":true,"late_fee":"0.00","late_days":0 }] } ],
  "stats":{ "received_total":"4950.00","to_receive_total":"9650.00","expected_total":"14600.00",
    "paid_count":3,"due_count":9,"overdue_count":2,"overdue_total_fee":"37.50",
    "vacant_kitnets_count":2,"vacant_kitnets_value":"1600.00" } }
```

**Cache**: endpoint **não** cacheado (toggles exigem reflexo imediato; query enxuta com
`select_related`). Cliente usa `staleTime` curto + optimistic update + invalidação. (Cache fica
para otimização futura — YAGNI.)

### 4.4 Regras do toggle

| Estado | dia passou | Ação | can_toggle |
|---|---|---|---|
| Não pago | não (a vencer) | cria `RentPayment` | ✅ |
| Não pago | sim (em atraso) | cria `RentPayment` (payment_date=hoje) | ✅ |
| Pago | não | soft-delete `RentPayment` | ✅ |
| Pago | sim | — | ❌ disabled |
| Qualquer | mês finalizado | — | ❌ disabled |

Servidor **sempre revalida** (defesa em profundidade); mensagens de erro em PT.

### 4.5 Stats — cálculo
- `received_total` = Σ `amount_paid` de **todos** os `RentPayment` ativos do mês (sem filtro de cobrabilidade — definição canônica de "recebido"), opcionalmente filtrado por `building_id`. Assimetria **intencional** com `to_receive_total` (baseado em leases cobráveis).
- `to_receive_total` = Σ valor efetivo dos leases cobráveis do mês **sem** `RentPayment`.
- `expected_total` = received + to_receive.
- `vacant_kitnets` = `Apartment.objects.filter(is_rented=False)` (default exclui deletados), filtrado por prédio se aplicável → `count` + Σ `rental_value`.

## 5. Edge cases
- Clamping 31→fev/abr/jun (`calendar.monthrange` no back; `getDaysInMonth`/`setDate` do `date-fns` no front).
- Ano bissexto coberto pelo clamping.
- Lease começando/terminando no meio do mês: incluído se a janela `start_date..end_date` intersecta o mês (date-aware, não depende do booleano `is_rented`).
- Datas: todos os campos relevantes são `DateField` — aritmética pura de data, sem datetime.

## 6. Frontend

- **`use-rent-calendar.ts`**: `useRentCalendar(year, month, buildingId?)` (`useQuery`, `staleTime` curto) e
  `useToggleRentPayment()` (`useMutation` optimistic: `onMutate` cancela+snapshot+flip, `onError` rollback,
  `onSettled` invalida `rentCalendar` + `latePaymentSummary` + `financialSummary`). Tipos TS hand-written
  como em `use-dashboard.ts:1-189`. API via `apiClient` (`lib/api/client.ts`).
- **`query-keys.ts`**: adicionar grupo `rentCalendar`.
- **Componentes** em `app/(dashboard)/_components/rent-calendar/`:
  - `rent-calendar-section.tsx` — container 3 colunas (`grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-4`), estado mês/dia selecionado, filtro de prédio.
  - `rent-month-grid.tsx` — grade `date-fns` (`startOfMonth`/`getDay`/`getDaysInMonth`), chips por dia, hoje/selecionado destacados, nav de mês.
  - `rent-day-panel.tsx` — itens do dia + `RentPaymentToggle` + atraso/multa + botões "Hoje"/"Próx. vencimento".
  - `rent-stats-panel.tsx` — 4 cards (mês, recebido, a receber, kitnets vagos).
  - `rent-payment-toggle.tsx` — Radix Switch (`@radix-ui/react-switch`) com label + estado disabled + tooltip explicando o porquê.
- **Montagem**: `<RentCalendarSection />` no topo de `page.tsx`, acima de `<FinancialSummaryWidget />`.
- **Refator**: `late-payments-alert.tsx` passa a usar o toggle unificado.

### UI/UX
- Status nunca só por cor: Pago (verde + ✓ + "Pago"), A vencer (âmbar + "A vencer"), Em atraso (vermelho + ⚠ + dias + multa).
- Tokens de tema (light/dark) como no mockup; dark via `next-themes` (já no app).
- Skeletons no loading; empty states ("Nenhum vencimento neste dia" / "Todos alugados").
- `formatCurrency`/`handleError` (`lib/utils/`), datas DD/MM/YYYY (`date-fns` + ptBR). PT no usuário, EN nos logs.

## 7. Testes (regras `tests/CLAUDE.md`)

- **Backend unit** (`tests/unit/test_financial/test_rent_schedule_service.py`): clamping (31→fev/abr); valor efetivo c/ aumento pendente; `collectible_leases` (exclui owner/offset/prepaid; janela de datas); toggle cria+soft-delete; guards (pago+dia-passou recusa; mês finalizado bloqueia); stats (received/to_receive/vacant). `model-bakery` + `freezegun`.
- **Backend integração** (`tests/integration/test_rent_calendar_api.py`): `rent_calendar` (dias/stats), toggle cria↔apaga, permissão (non-admin 403), filtro por prédio. + regressão `DailyControlService`.
- **Frontend** (Vitest+MSW): hook fetch/shape; toggle optimistic + rollback + invalidação; componentes (painel do dia c/ estados/disabled, atraso+multa, stats, grade c/ chips/seleção, botões hoje/próximo).

## 8. Sessões de implementação

| # | Sessão | Conteúdo |
|---|--------|----------|
| 21 | Backend: `RentScheduleService` + refactor DRY do `DailyControlService` + unit tests | Fonte única da lógica + extração |
| 22 | Backend: endpoints `rent_calendar`/`toggle_rent_payment` + unificar `mark_rent_paid` + integration tests | API + permissão |
| 23 | Frontend: data layer (`use-rent-calendar`, query-keys, tipos, MSW) + hook tests | Optimistic update |
| 24 | Frontend: UI (5 componentes + montagem no dashboard + responsivo/dark) + component tests | Grid custom date-fns |
| 25 | Refator `late-payments-alert` p/ toggle unificado + `/audit` + lint/type/test + SESSION_STATE | Verificação final |

## 9. Exemplares (arquivo:linha)

| Padrão | Local |
|--------|-------|
| Service `@staticmethod` | `core/services/fee_calculator.py:20-197` |
| Lógica rent atual (a extrair) | `core/services/daily_control_service.py:337-365, 669-710` |
| `@action` no DashboardViewSet | `core/views.py:578-776` |
| Multa de atraso | `core/services/fee_calculator.py:49-99` |
| end_date do lease | `core/services/date_calculator.py:60-102` |
| Dashboard hooks | `frontend/lib/api/hooks/use-dashboard.ts:1-189` |
| Componente de alerta (estilos/tokens) | `frontend/app/(dashboard)/_components/late-payments-alert.tsx` |
| Página dashboard (montagem) | `frontend/app/(dashboard)/page.tsx` |
| Switch (Radix) | `@radix-ui/react-switch` (em `package.json`) |
