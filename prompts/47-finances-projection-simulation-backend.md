# Sessão 47 — Backend: `CondoProjectionService` + `CondoSimulationService` + endpoints `finance-cash-flow/{projection,simulate}`

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46 → **47 → 48** → 49 → 50 (esta abre a **Fase 5 — Projeção + Simulação**, camada de **serviços + API**)
> Esta sessão entrega o **futuro computado** do condomínio: `CondoProjectionService.project(months=12)` (receita projetada com `is_prepaid_for_month` **por mês** + `IncomeEntry`; saídas = `Installment` futuras + `expected_amount` respeitando `end_date`/`BillSkip`/suspensão + folha; **dedup embutido**; acumulado = **fold ancorado** no último `CondoMonthClose`; `is_actual`) e `CondoSimulationService` (efêmero, deltas em memória — **sem persistência**), expostos em `finance-cash-flow/{projection,simulate}`. **Consome `CondoBalanceService`/`CondoMonthCloseService` (S45) e `Installment`/embutido (S41) — não re-deriva net/caixa.** **Sem frontend (S48); sem distribuição por proprietário (Fase 6).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.2 materializar/projetar/ancorar, §4.2 caixa/competência/baseline, §4.5 receita filtrada, §4.7 fold/âncora/janela pré-tracking, §7 mapeamento (parcela embutida/avulsa, suspensão, seed), §8 `CondoProjectionService`/`CondoSimulationService`/`CondoBalanceService`, §9 API `finance-cash-flow/{projection,simulate}`, §10 tela 5 (tabela acumulada + Real/Projetado), §11 cache (`finance-cash-flow`/`finance-projection`), §13 migrações, §14 Fase 5, §18 edge-cases "Parcelas" + "Receita/collectibility" + "Fold/fechamento" + "Estruturais")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Prompt da S45 (`CondoBalanceService`/`CondoMonthCloseService` + `quantize_money` + baseline ancorado — contratos cross-session no rodapé, CONSUMIR verbatim)**: `@prompts/45-finances-balance-close-services-api.md`
- **Prompt da S44 (modelos `IncomeEntry`/`CondoMonthClose` — campos `income_date`/`is_received`/`cash_balance_end`/`net_result`/`carry_forward_out`)**: `@prompts/44-finances-reserve-income-close-models.md`
- **Prompt da S41 (`InstallmentPlan`/`Installment` embutido+avulso + `Employee`/folha + `ensure_month_bills` estendido + `convert_deferred`)**: `@prompts/41-finances-installments-employee-models-services.md`
- **Prompt da S37 (serviços de contas + `received_collectible_total` + `finances/cache.py` com prefixos `finance-*`)**: `@prompts/37-finances-bill-services-cache.md`
- **Prompt da S38 (serializers/viewsets/API + `FinanceDashboardViewSet` + helper de validação `year`/`month` + `finances/urls.py`)**: `@prompts/38-finances-serializers-viewsets-calendar.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

> **NOTA**: o app `finances/` é construído pelas Sessões 34→46 (ainda não no disco). As referências `finances/...` abaixo são **contratos cross-session** (consumir verbatim do `SESSION_STATE.md` / dos prompts S37/S41/S44/S45), **não** `file:line` reais. Os exemplares com `file:line` concreto vêm de `core/` (existe no disco) — são o **padrão** a imitar. **Não** copiar a lógica do legado `CashFlowService`/`SimulationService` (escopo commingled, errado para o condo); usá-los **só** como forma/estrutura.

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Loop de projeção N meses: snapshot fechado vence o computado, acumulado do baseline, `is_projected`/`is_current`** | `core/services/cash_flow_service.py:503-610` (`get_cash_flow_projection`: baseline `FinancialSettings.initial_balance` :533-534; loop com wrap de mês :544-552; `MonthSnapshot.is_finalized` vence :556-575; `cumulative_balance += balance` :596; dict por mês :598-608) | **Exemplar canônico da FORMA** do `CondoProjectionService.project`. Espelhar: mês **fechado** (aqui = `CondoMonthClose.status='closed'`) lê o **congelado** e re-âncora o acumulado; mês aberto/futuro **computa**. **NÃO** copiar a lógica (legado é commingled): o baseline é o **`CondoMonthClose.cash_balance_end`** (S45), não `MonthSnapshot`; receita via SSOT filtrado |
| **Projeção de receita futura com prepaid por mês (forma)** | `core/services/cash_flow_service.py:642-656` (`_get_projected_income`: `RentScheduleService.collectible_leases(date(year, month, 1))` :647; soma `rental_value` :646-648) + `:666-680` (owner/prepaid via `is_prepaid_for_month(lease, year, month)` :677) | A receita projetada do condo = Σ `effective_rental_value` de `collectible_leases(M)` **por mês** (prepaid avaliado **mês a mês** — Adriana jun→jul/2027). **Reusar `RentScheduleService`** (collectibility/prepaid SSOT); **não** reimplementar nem usar `rental_value` cru (usar `effective_rental_value`) |
| **Projeção de despesa futura respeitando `end_date`/parcelas conhecidas (forma)** | `core/services/cash_flow_service.py:658-731` (`_get_projected_expenses`: instalments por `due_date` no mês :696-701; fixos `exclude(end_date__lt=month_start)` :707-717; folha = último pagamento por pessoa :719-729) | **Forma** da saída projetada: `Installment` futuras (por `due_date`) + recorrentes (`expected_amount` respeitando `end_date`/suspensão/`BillSkip`) + folha. **NÃO** copiar (legado usa `Expense`/`EmployeePayment`); aqui = `BillingAccount.expected_amount` + `Installment.amount` + folha da S41 |
| **Serviço de simulação EFÊMERO (deepcopy, deltas em memória, sem DB write) + validação de cenários** | `core/services/simulation_service.py:1-47` (docstring "ephemeral" :1-8; `VALID_SCENARIO_TYPES` frozenset :16-25; `_validate_scenarios` :35-47) + `:55-` (`_apply_*` puros via deepcopy) | **Exemplar canônico** do `CondoSimulationService`: cenários **efêmeros**, `copy.deepcopy` da projeção-base, `_apply_*` puros, **zero** persistência (design §8/§15, `.claude/rules/financial.md` "Simulation Service: ephemeral — no DB persistence"). Reusar a **forma** (validate → deepcopy base → aplicar deltas → comparar) |
| **Endpoints `projection` (GET, query params + ranges) / `simulate` (POST, `scenarios` validados)** | `core/viewsets/financial_dashboard_views.py:175-207` (`projection`: `months` int + `>=1` :177-191; flags `=="true"` :193-194; `Decimal(...)` com `InvalidOperation` :196-199; delega ao serviço :201-207) + `:247-268` (`simulate`: `scenarios` lista não-vazia → 400 :249-255; `validate_scenarios` → 400 :257-259; base+simulated+comparison :261-267) | **Exemplar canônico** das ações `finance-cash-flow/{projection,simulate}`. View **fina**: parse/validação → 400 PT; lógica no serviço. Espelhar a forma de `months`/`scenarios` |
| **Bare `ViewSet` read-only + `@action(detail=False)` + validação `year`/`month` 1–12 → 400 PT** | `core/viewsets/financial_dashboard_views.py:24-32` (`overview` delega) + `:61-73` (`category_breakdown`: parse `year`/`month`, `ValueError` → 400 PT) + `:166-170` (range 1–12 → 400 PT) | Forma do `FinanceCashFlowViewSet` desta sessão (bare `ViewSet` + `FinancialReadOnly`). **Reusar o helper de validação `year`/`month` da S38** (não duplicar a constante de range — `MONTHS_IN_YEAR`/`MIN_MONTH`/`MAX_MONTH`) |
| **`CondoBalanceService.result_of_month`/`cash_balance` (baseline) — CONSUMIR, não re-derivar** | `finances/services/condo_balance_service.py` (S45: `result_of_month(year, month, building_id=None) -> Decimal` competência filtrada; `cash_balance(as_of_month=None, building_id=None) -> Decimal` ancorado no último `CondoMonthClose`) | A projeção do **mês atual** (não-futuro) **delega** a `result_of_month` (DRY — design §8/§14 "Fase 5 consome `result_of_month`/baseline"); o **baseline** do acumulado é o `cash_balance` ancorado. **Nunca** recomputar net/caixa aqui |
| **`CondoMonthClose` congelado (mês fechado vence o computado) + fold/`carry_forward_out`** | `finances/services/condo_month_close_service.py` + `finances/models.py` (S44/S45: `CondoMonthClose.status='closed'`/`net_result`/`cash_balance_end`/`carry_forward_out` ≤0; `_fold(net_by_month)` helper puro da S45) | Mês fechado na projeção lê o **congelado** (`net_result`/`cash_balance_end`) — não recomputa (design §3.2). O acumulado **ancora** no último `CondoMonthClose` (igual à S45). **Reusar** o `_fold` da S45 se exposto; senão espelhar a fórmula (design §4.7) sem duplicar |
| **`received_collectible_total` / `collectible_leases` / `effective_rental_value` / `is_prepaid_for_month` / `is_month_tracked` (SSOT — reusar)** | `core/services/rent_schedule_service.py:142-191` (`collectible_leases`), `:123-139` (`effective_rental_value`), `:93-107` (`is_prepaid_for_month`), `:86-90` (`is_month_tracked`), `:73-83` (`rent_tracking_start_month`) + `finances/services/...` (S37: `received_collectible_total(reference_month, building_id=None) -> Decimal`) | Receita projetada = Σ `effective_rental_value` de `collectible_leases(M)` por mês; prepaid avaliado **mês a mês**; janela pré-tracking via `is_month_tracked` (mês não rastreado → receita estruturalmente 0). **Reusar** — zero mudança no SSOT |
| **`BillingAccount`/`Installment`/`BillSkip`/`Employee` (S37/S41 — CONSUMIR)** | `finances/models.py` (S36: `BillingAccount.expected_amount`/`lifecycle_state`/`tracking_start_month`/`end_date`; `BillSkip(billing_account, reference_month)`; S41: `Installment(plan, number, due_date, amount)`/`InstallmentPlan.embedded`/`linked_billing_account`; `Employee`/folha) | Saídas projetadas: `expected_amount` de `BillingAccount` **ativas** (não suspensa/deferida, dentro de `tracking_start_month..end_date`, respeitando `BillSkip`) + `Installment` futuras de planos **não-embutidos** + folha. **Dedup embutido**: `expected_amount` **exclui** a parcela; parcela só via plano (design §8) |
| **Helper de quantização único `quantize_money` (fronteira de saída — REUSAR)** | `finances/services/money.py` (S45: `quantize_money(value: Decimal) -> Decimal`, `ROUND_HALF_UP`, `0.01`) | Toda figura de dinheiro exposta pela projeção passa pelo **mesmo** helper (sem off-by-cent entre dashboard, fechamento e projeção — design §4). Somatórios internos crus; só a fronteira quantiza. **Reusar — não duplicar** |
| **Helper TZ único `America/Sao_Paulo` (REUSAR)** | `finances/services/timezone.py` (S34: `today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`) | "Hoje/mês atual" da projeção (âncora `is_actual`, mês inicial do loop) **sempre** via `today_sp()`/`current_month_sp()` — settings é UTC (design §4/§17). Proibido `timezone.now().date()` cru |
| **`@cache_result` + prefixos `finance-cash-flow`/`finance-projection` (consumir os literais da S37)** | `finances/cache.py` (S37: `FINANCE_CASH_FLOW_PREFIX="finance-cash-flow"`, `FINANCE_PROJECTION_PREFIX="finance-projection"`, `invalidate_finance_caches()`) + `core/cache.py:213-255` (`@cache_result`/`invalidate_pattern`) | `projection` usa `@cache_result(key_prefix=FINANCE_PROJECTION_PREFIX, …)`; a invalidação já existe (S37/S44 invalidam `finance-*`). **`simulate` NÃO cacheia** (POST efêmero, depende do body). Um char de diferença no prefixo silenciosamente não-invalida |
| **Registro no router próprio do `finances` + `include` no projeto** | `finances/urls.py` (S38: router próprio + `path("api/finances/", include(...))` no projeto) + `core/urls.py:8-17` (registro `DefaultRouter`) | **Anexar** `finance-cash-flow` ao `finances/urls.py` da S38 (não criar router/wiring novo). Rota: `GET /api/finances/finance-cash-flow/projection/`, `POST /api/finances/finance-cash-flow/simulate/` |
| Pagination / Permission (reuso direto) | `core/permissions.py:107-121` (`FinancialReadOnly`: auth lê, `is_staff` escreve, :121 `return bool(request.user.is_staff)`) | **`FinancialReadOnly`** no `FinanceCashFlowViewSet` (GET `projection` para qualquer autenticado; `simulate` é POST → só `is_staff` passa do gate). Import direto |
| **Teste de integração — matriz `FinancialReadOnly` + endpoint backed-by-service (sem mock de internals) + throttle off + freezegun** | `tests/integration/test_financial_permissions.py:16-58` (200/403/non-403/401) + `tests/integration/test_rent_calendar_api.py:1-59` (política :1-10; `_disable_throttling` :29-40; `freeze_time`) | Padrão dos testes de API desta sessão: View → Service → Model real, `freeze_time`, throttle off, matriz de permissão |
| Factories `finances` (S36/S41/S44) | `tests/factories.py` (S36: `make_billing_account`/`make_bill`/`make_payment`; S41: `make_installment_plan`/`make_installment`/`make_employee`; S44: `make_income_entry`/`make_condo_month_close`) + `make_condominium`/`make_building` (S34) + `make_lease`/`make_rent_payment` (core) | Dados dos testes. **Reusar** — não criar objetos manualmente nem factory nova salvo necessidade real (KISS) |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **só `freezegun`** (congelar a data p/ `today_sp()`/`is_actual`/prepaid por mês) + throttle off nos testes de API. ORM/serviços/`RentScheduleService`/`CondoBalanceService`/`CondoMonthCloseService` reais |

### O que as Sessões 34/36/37/38/41/44/45 já entregaram (PRÉ-REQUISITO — NÃO recriar)

**Verificar no `SESSION_STATE.md` que a S45 está concluída.** Se não estiver, **PARE** (DEPENDENCY ORDER 45→47).

- **S34** (infra): app `finances` + `FinancesConfig.ready()` + `core.Condominium`(padrão) + `Building.condominium` + helper TZ `finances/services/timezone.py` (`today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`) + gate ampliado + factories base.
- **S37** (serviços de contas + cache): `BillGenerationService.ensure_month_bills`; `finances/cache.py` (prefixos `finance-dashboard`/**`finance-cash-flow`**/**`finance-projection`** + `invalidate_finance_caches`); `finances/signals.py`; **`RentScheduleService.received_collectible_total`** (aditivo, read).
- **S38** (API Fase 2): `finances/serializers.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py` (`FinanceDashboardViewSet`), `finances/urls.py` (router próprio + `path("api/finances/", …)`), **helper de validação `year`/`month`** (constante de range).
- **S41** (Fase 3): `InstallmentPlan`/`Installment` (embutido+avulso, dedup, `linked_billing_account`); `Employee` (folha §4.6); `ensure_month_bills` estendido (parcelas + folha + abatimento).
- **S44** (modelos Fase 4): `IncomeEntry` (`income_date`/`is_received`/`received_date`), `CondoMonthClose` (`status`/`net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out`≤0/`breakdown`).
- **S45** (serviços Fase 4): **`CondoBalanceService`** (`result_of_month`/`cash_change_of_month`/`cash_balance` ancorado/`reserve_balance`/`total_balance`/`overdue_bills_total`/`overview`); **`CondoMonthCloseService`** (`close`/`reopen`/`assert_open`, fold `_fold`, carry-forward); **`quantize_money`** (`finances/services/money.py`); dashboard `overview`/`monthly_balance`/`by_category`.

> **Se a S45 não estiver concluída, PARE.** Esta sessão consome `CondoBalanceService.result_of_month`/`cash_balance` (baseline), o `_fold`/`CondoMonthClose` congelado, o `quantize_money` e a collectibility do SSOT. **Não** recriar serviços de saldo, fold, baseline, helper de quantização ou modelos.

---

## Escopo

### Arquivos a criar
- `finances/services/condo_projection_service.py` — `CondoProjectionService` (`project(months=12)` + helpers puros de receita/despesa projetada por mês, dedup embutido, fold ancorado).
- `finances/services/condo_simulation_service.py` — `CondoSimulationService` (efêmero: `validate_scenarios` + `simulate` por deltas em memória + `compare`).
- `tests/unit/test_finances/test_condo_projection_service.py` — testes da projeção (invariantes §4 + edge-cases §18: dedup, prepaid jun→jul/2027, fold ancorado, pré-tracking).
- `tests/unit/test_finances/test_condo_simulation_service.py` — testes da simulação (efêmera, deltas em memória, validação, sem persistência).
- `tests/integration/test_finances/test_finance_cash_flow_api.py` — `finance-cash-flow/{projection,simulate}` (shape, cache, matriz `FinancialReadOnly`).

### Arquivos a modificar
- `finances/viewsets/dashboard_views.py` (S38/S45) — **anexar** `FinanceCashFlowViewSet` (bare `ViewSet` + `FinancialReadOnly`, ações `projection`/`simulate`). `FinanceDashboardViewSet` (S38/S45) **intacto**.
- `finances/viewsets/__init__.py` — anexar `FinanceCashFlowViewSet` ao `__all__` (ordem alfabética).
- `finances/urls.py` (S38) — registrar `finance-cash-flow` → `FinanceCashFlowViewSet` no router existente. Registro de `finance-dashboard`/CRUD **intacto**.
- `tests/factories.py` — só se faltar factory para os testes (improvável; S36/S41/S44 cobriram). **Não duplicar.**

### NÃO fazer (pertence a outras sessões)
- **Sem frontend** — hooks `use-finance-projection`/`use-finance-simulation`, página "Projeção 12 meses" (tabela acumulada + badge Real/Projetado + `ComposedChart` Recharts), simulador, query-keys, Zod, formatters — é a **Sessão 48** (frontend da Fase 5). **Nada em `frontend/`.** A S48 consome os shapes desta sessão **verbatim**.
- **Sem `OwnerDistributionService` / distribuição por proprietário / agregação de donos externos** (`displayable_leases`, cards "por proprietário", seção de externos) — é a **Fase 6 (S49/S50)**. A projeção desta sessão é do **household/condomínio** (net agregado); **não** rateia por dono. O `OwnerDistributionService` (S49) consome `CondoBalanceService.result_of_month` (não esta projeção).
- **Sem re-derivar net/caixa/competência** — `result_of_month`/`cash_change_of_month`/`cash_balance`/baseline são da **S45**. A projeção do **mês atual** delega a `result_of_month`; o **acumulado** ancora no `cash_balance`/`CondoMonthClose.cash_balance_end`. **Proibido** recomputar essas figuras (DRY — design §8/§14).
- **Sem modelos/migração/serviços de saldo/fechamento novos** — `CondoMonthClose`, `Installment`, `BillingAccount`, `Employee`, `IncomeEntry`, `_fold`, `quantize_money` já existem (S36/S41/S44/S45). Esta sessão **não** cria modelo nem migra.
- **Sem persistência da simulação** (design §8/§15, `.claude/rules/financial.md`) — `CondoSimulationService` é **100% efêmero** (deltas em memória, `deepcopy`); **zero** `save()`/`create()`/`delete()`.
- **Sem mudança no SSOT de aluguel** (memória do projeto): collectibility/prepaid **só** via `RentScheduleService` (`collectible_leases`/`is_prepaid_for_month`/`is_month_tracked`/`received_collectible_total`/`effective_rental_value`); **nunca** `prepaid_until >= month_start` cru, **nunca** `received_total` cru.
- **Sem wirar o legado** `CashFlowService`/`cash-flow` no dashboard novo (design §10/§15) — o módulo novo supera o legado; não wirar os dois. **Não** importar `core.services.cash_flow_service`/`simulation_service` (só usar como exemplar de forma).
- **Sem alterar `BillGenerationService.ensure_month_bills`** (S37/S41) — a projeção do futuro é **computada** (não materializa `Bill`); ela **não** chama `ensure_month_bills` (design §3.2 "projetar futuro computado, sem criar linhas").

---

## Especificação

> Serviços stateless em `finances/services/`, todos `@staticmethod`. `Decimal` para dinheiro; **somar Decimals crus e quantizar (`quantize_money`, S45 — `ROUND_HALF_UP`/`0.01`) só na fronteira de saída/agregado**, idêntico em todo serviço que re-deriva a mesma figura (design §4 — sem off-by-cent entre dashboard, fechamento e projeção). "Hoje/mês atual" **sempre** via `finances.services.timezone.today_sp()`/`current_month_sp()`. Direção: serviços importam de `finances.models`, `finances.services.{timezone,money,condo_balance_service,condo_month_close_service}`, `core.services.rent_schedule_service` — **nunca** views/serializers. Mensagens ao usuário em **PT**, logs/identificadores/enum values/`scenario.type` em **EN**.

### `CondoProjectionService` (design §3.2/§4.5/§4.7/§8)

Service stateless, `@staticmethod`. **Materializa real / projeta futuro computado / ancora o fold** (design §3.2). Assinaturas:

```python
from datetime import date
from decimal import Decimal
from typing import Any

class CondoProjectionService:

    @staticmethod
    def project(months: int = 12, building_id: int | None = None) -> list[dict[str, Any]]:
        """Projeção do condomínio para N meses a partir do mês atual SP (current_month_sp()).
        Ordem por mês cronológico. Para cada mês M (0..months-1, com wrap de ano):
          - is_actual = (M < mês atual SP)            # passado/atual = REAL; futuro = projetado
          - month_close = CondoMonthClose(reference_month=M, status='closed')?
          - SE month_close existe (mês FECHADO):     # design §3.2 — congelado vence o computado
                income_total  = breakdown/derivado do close (NÃO recomputa)
                expenses_total = idem
                net           = month_close.net_result
                cumulative_cash = month_close.cash_balance_end       # re-âncora o acumulado
            SENÃO SE M == mês atual SP (aberto, real):
                net           = CondoBalanceService.result_of_month(year, month, building_id)   # DRY (S45)
                income_total/expenses_total = pontas de result_of_month (sem re-derivar net)
                cumulative_cash += net (ancorado no baseline cash_balance — S45)
            SENÃO (M futuro, computado):
                income_total  = _projected_income(year, month, building_id)
                expenses_total = _projected_expenses(year, month, building_id)
                net           = income_total − expenses_total
                cumulative_cash += net
          - dict por mês: { year, month, income_total, expenses_total, net,
                            cumulative_cash, is_actual, is_closed } (Decimais como STRING via quantize_money).
        BASELINE do acumulado = CondoBalanceService.cash_balance(as_of_month=1º dia do mês inicial) (S45,
        ancorado no último CondoMonthClose; fallback FinancialSettings.initial_balance). Re-âncora ao
        cruzar um mês fechado (cumulative_cash = month_close.cash_balance_end). NÃO re-deriva net/caixa
        (DRY — design §8/§14)."""

    @staticmethod
    def _projected_income(year: int, month: int, building_id: int | None = None) -> Decimal:
        """Receita PROJETADA do mês futuro (design §4.5, prepaid POR MÊS):
          = Σ effective_rental_value(lease, date(year,month,1)) de RentScheduleService.collectible_leases(date(year,month,1), building_id)
            + Σ IncomeEntry.amount com income_date no mês (competência projetada; recorrente = YAGNI, design §15).
        collectible_leases já avalia is_prepaid_for_month POR MÊS (Adriana 836/113 prepaid_until → jun
        excluída, jul/2027 incluída) E is_month_tracked (mês pré-tracking → receita estruturalmente 0).
        NUNCA rental_value cru (usar effective_rental_value); NUNCA received_total cru. Donos externos
        (owner setado) já saem por collectible_leases."""

    @staticmethod
    def _projected_expenses(year: int, month: int, building_id: int | None = None) -> Decimal:
        """Saídas PROJETADAS do mês futuro (design §3.2/§7/§8 — DEDUP EMBUTIDO):
          = Σ Installment.amount de Installment com due_date no mês, de InstallmentPlan ATIVO e
              NÃO-embutido (embedded=False)                                # parcela avulsa só via plano
            + Σ BillingAccount.expected_amount de contas ATIVAS no mês:    # recorrentes computadas
                lifecycle_state == 'active' (exclui suspended/deferred/ended),
                tracking_start_month <= 1º dia do mês,
                (end_date é null OU end_date >= 1º dia do mês),            # cutoff de end_date
                sem BillSkip(billing_account, reference_month=1º dia do mês)
            + folha projetada (Employee/folha da S41 — base + variável esperada − abatimento §4.6;
                reusar a forma da S41; abatimento = effective_rental_value da lease salary-offset no mês).
        DEDUP EMBUTIDO (design §8 'Pula planos embutidos'): a parcela de plano EMBUTIDO (embedded=True,
        linked_billing_account setado) NÃO entra aqui pela linha de Installment — ela já está dentro do
        expected_amount da BillingAccount vinculada. Contar a parcela embutida UMA vez (via expected_amount),
        a avulsa UMA vez (via Installment). NUNCA dobrar. building_id filtra building (nível-condomínio
        building=null entra quando building_id é None)."""
```

> **Filtro de contas ativas (DRY com o gerador):** a regra "conta gera no mês M" (ativa, dentro de `tracking_start_month..end_date`, sem `BillSkip`) é a **mesma** do `BillGenerationService.ensure_month_bills` (S37). **Reusar** o predicado/filtro da S37 se ele estiver exposto como função pura (ex.: `_billing_accounts_due_in(year, month, building_id)`); **não** duplicar a regra de elegibilidade (uma divergência entre projeção e geração = bug silencioso). Se a S37 não expôs um helper reusável, extrair um helper **puro** compartilhado (uma definição), consumido por ambos — refator completo (design-principles: DRY/no partial refactoring).

### `is_actual` / mês fechado vence (design §3.2)

- `is_actual = (M < mês atual SP)` — passado e mês corrente são **reais** (lidos via `result_of_month`/`CondoMonthClose`); futuro (`M > mês atual`) é **projetado computado**.
- **Mês fechado (`CondoMonthClose.status='closed'`) sempre vence** o computado — lê os números congelados (`net_result`/`cash_balance_end`/`breakdown`), **nunca** recomputa (design §3.2 "passado = linhas reais / fechado = congelado"). Re-âncora `cumulative_cash = cash_balance_end` (espelha `get_cash_flow_projection:574`).
- O acumulado (`cumulative_cash`) é o **caixa projetado ao fim de cada mês**; começa no baseline ancorado (`CondoBalanceService.cash_balance` do mês inicial) e soma `net` mês a mês, re-ancorando em cada mês fechado.

### `CondoSimulationService` (design §8/§15, `.claude/rules/financial.md` — EFÊMERO)

Service stateless, `@staticmethod`. **100% efêmero**: opera sobre a projeção-base (lista de dicts de `CondoProjectionService.project`) via `copy.deepcopy`, aplica deltas **em memória**, **zero** persistência. Assinaturas:

```python
import copy
from decimal import Decimal
from typing import Any

VALID_SCENARIO_TYPES = frozenset([
    "add_expense",        # add_expense: { amount, months? }  → soma amount às despesas dos meses futuros
    "remove_expense",     # remove_expense: { amount, months? } → subtrai amount das despesas
    "change_rent",        # change_rent: { delta, months? }   → soma delta à receita dos meses futuros
    "add_income",         # add_income: { amount, months? }   → soma amount à receita
])  # (conjunto mínimo — YAGNI; nomes EN; espelha a forma do legado simulation_service.py:16-25)

class CondoSimulationService:

    @staticmethod
    def validate_scenarios(scenarios: list[dict[str, Any]]) -> list[str]:
        """Retorna lista de mensagens PT para cenários inválidos (type ausente/inválido, amount/delta
        ausente ou não-decimal). Espelha _validate_scenarios (simulation_service.py:35-47); mensagens PT."""

    @staticmethod
    def simulate(base: list[dict[str, Any]], scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """deepcopy(base); aplica cada cenário (deltas em memória sobre income_total/expenses_total dos
        meses FUTUROS — is_actual=False; meses reais/atual NÃO são alterados); recomputa net e
        cumulative_cash do ponto de alteração em diante (re-fold do acumulado a partir do baseline já
        presente no base). Decimais string via quantize_money. NÃO toca o DB, NÃO muta `base`."""

    @staticmethod
    def compare(base: list[dict[str, Any]], simulated: list[dict[str, Any]]) -> dict[str, Any]:
        """Comparação base × simulado por mês + agregados (Δ cumulative_cash final, Δ net por mês).
        Espelha compare() do legado (estrutura side-by-side). Decimais string. Efêmero."""
```

> **Cenários só afetam o FUTURO:** os deltas de simulação aplicam-se **apenas** aos meses `is_actual=False` (futuro projetado). Meses reais/fechados/atual são **imutáveis** na simulação (são fato consumado — design §3.2). Travar por teste: aplicar um cenário e asserir que os meses `is_actual=True` ficam **idênticos** ao base.

### Cache (design §11)

- `projection` (GET) usa `@cache_result(key_prefix=FINANCE_PROJECTION_PREFIX, …)` (literal `finance-projection` da S37; a invalidação já existe — S37/S44 invalidam `finance-*` em escritas). A chave inclui `months`/`building_id`.
- `simulate` (POST) **NÃO** cacheia (efêmero, depende do body — design §11/§15).

---

## API (design §9)

Base `/api/finances/...` (router próprio do `finances`, S38). Bare `ViewSet` + `FinancialReadOnly`. `CustomPageNumberPagination` **não se aplica** (agregação não-paginada, como `CashFlowViewSet`). Decimal **string**; validação PT.

### Viewset (anexar a `finances/viewsets/dashboard_views.py`)
- **`FinanceCashFlowViewSet(viewsets.ViewSet)`** — `permission_classes = [FinancialReadOnly]`.
  - **`projection`** — `@action(detail=False, methods=['get'])`. Lê `months` (int, default 12, `>=1` → 400 PT, **teto** ex. `<=36` → 400 PT, evitando loop absurdo) e `building_id` (int opcional → 400 PT se não-int). Delega a `CondoProjectionService.project(months, building_id)`. **Cacheado** `FINANCE_PROJECTION_PREFIX`. Retorna a lista de meses (`year`/`month`/`income_total`/`expenses_total`/`net`/`cumulative_cash`/`is_actual`/`is_closed`).
  - **`simulate`** — `@action(detail=False, methods=['post'])`. Lê `scenarios` (lista não-vazia → 400 PT); `months`/`building_id` opcionais (default 12). `CondoSimulationService.validate_scenarios(scenarios)` → 400 PT se erros. Base = `CondoProjectionService.project(months, building_id)`; `simulated = CondoSimulationService.simulate(base, scenarios)`; `comparison = CondoSimulationService.compare(base, simulated)`. Retorna `{ base, simulated, comparison }`. **Sem cache.**

### URLs (anexar a `finances/urls.py`, S38)
Registrar no router existente: `finance-cash-flow` → `FinanceCashFlowViewSet`. Ações underscore não se aplicam (`projection`/`simulate` são uma palavra). Rotas finais: `GET /api/finances/finance-cash-flow/projection/`, `POST /api/finances/finance-cash-flow/simulate/`. Registro da S38/S45 **intacto**.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui é **só `freezegun`** (congelar a data p/ `today_sp()`/`is_actual`/prepaid por mês) e **disable throttle** nos testes de API (`override_settings(REST_FRAMEWORK=…)` — fronteira de infra, como `test_rent_calendar_api.py:29-40`). **NUNCA** mockar ORM, managers, `RentScheduleService`, `CondoBalanceService`, `CondoMonthCloseService`, `quantize_money`, `CacheManager`, signals ou qualquer interno. Banco real via `--reuse-db`. Dados via factories. `filterwarnings=error`: zero warnings. **Cache em teste é LocMem** (`configure_test_cache`) → asserir invalidação por efeito observável (probe `finance-projection:…` some após escrita), não por mock.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_condo_projection_service.py` (sob `@freeze_time`)

**Receita projetada (§4.5 — prepaid POR MÊS, SSOT)**
- [ ] `_projected_income` = Σ `effective_rental_value` de `collectible_leases(M)` + Σ `IncomeEntry` por `income_date` no mês. Exemplo trabalhado pinado (valores explícitos) batendo na unha.
- [ ] **prepaid jun→jul/2027 (Adriana 836/113, §18 "Receita/collectibility")**: lease com `prepaid_until` tal que o mês de junho é prepaid e julho não (avaliado **mês a mês** via `is_prepaid_for_month`) → `_projected_income(jun)` exclui a lease, `_projected_income(jul)` inclui. Asserir explicitamente os dois meses.
- [ ] **receita filtrada (§4.5)**: lease com **owner setado** (Tiago/Alvaro) e lease **salary-offset** (Rosa 850/205) → **não** entram em `_projected_income` (saem por `collectible_leases`). Provar exclusão.
- [ ] **`effective_rental_value` (aumento pendente)**: lease com `pending_rental_value`/`pending_rental_value_date` em vigor no mês projetado → receita usa o **valor pendente**, não o `rental_value` cru.
- [ ] **janela pré-tracking (§4.7/§18)**: mês **antes** de `rent_tracking_start_date` (2026-06) → `_projected_income` = `0.00` (receita estruturalmente zero via `is_month_tracked`/`collectible_leases.none()`).

**Saídas projetadas + DEDUP embutido (§3.2/§8/§18 "Parcelas")**
- [ ] `_projected_expenses` = Σ `Installment.amount` (planos não-embutidos, `due_date` no mês) + Σ `BillingAccount.expected_amount` (ativas no mês) + folha. Exemplo trabalhado pinado.
- [ ] **dedup embutido (§18)**: plano **embutido** (`embedded=True`, `linked_billing_account` setado) com parcela no mês **e** a `BillingAccount` vinculada com `expected_amount` → a parcela embutida é contada **uma vez** (via `expected_amount`), **não** somada de novo pela linha de `Installment`. Plano **avulso** (`embedded=False`) → contado **uma vez** (via `Installment`). Asserir que nenhum é dobrado.
- [ ] **`expected_amount` respeita `end_date` (§18 "end_date cutoff")**: `BillingAccount` com `end_date` antes do mês projetado → **não** entra; `end_date` >= mês → entra.
- [ ] **`expected_amount` respeita suspensão (§18)**: `BillingAccount.lifecycle_state='suspended'`/`deferred`/`ended` → **não** entra na projeção (mês futuro não gera). Voltar a `active` → entra.
- [ ] **`expected_amount` respeita `BillSkip` (§18)**: `BillSkip(billing_account, reference_month=mês)` → conta **pulada** naquele mês; mês sem skip → entra.
- [ ] **`tracking_start_month`**: conta com `tracking_start_month` depois do mês projetado → **não** entra antes do início.
- [ ] **folha projetada (§4.6)**: `Employee` da S41 entra com base+variável esperada − abatimento; abatimento = `effective_rental_value` da lease salary-offset (Rosa) no mês; aluguel da Rosa **não** vira receita (excluído) nem despesa separada.
- [ ] **`building_id` filtra**: bill de nível-condomínio (`building=null`) entra quando `building_id is None`; com `building_id` setado, só as do prédio.

**Fold ancorado / `is_actual` / mês fechado (§3.2/§4.7/§18 "Fold/fechamento")**
- [ ] `project(months)` retorna `months` meses cronológicos a partir do mês atual SP; `is_actual = (M < atual)`; `is_closed` correto.
- [ ] **fold ancorado (§4.7)**: `cumulative_cash` do 1º mês começa no baseline `CondoBalanceService.cash_balance(as_of_month=1º mês)` (ancorado no último `CondoMonthClose`; fallback `FinancialSettings.initial_balance` 0,00). Asserir o baseline exato.
- [ ] **mês fechado vence o computado (§3.2)**: mês com `CondoMonthClose(status='closed', net_result=X, cash_balance_end=Y)` → a projeção lê `net=X`, `cumulative_cash=Y` (re-âncora), **não** recomputa. Asserir que mudar bills daquele mês **não** altera a linha congelada.
- [ ] **mês atual delega a `result_of_month` (DRY)**: o mês corrente (aberto, real) usa `CondoBalanceService.result_of_month` (não `_projected_income/_expenses`). Asserir igualdade com `result_of_month`.
- [ ] **âncora pré-tracking no fold (§4.7/§18)**: mês pré-tracking (sem aluguel rastreado + com bill) → receita 0, mas **não** acumula net negativo espúrio fora da janela (tratado como fora da janela / net isolado — design §4.7). Pinar.
- [ ] **dedup vs dashboard (§18 estrutural)**: para o mês corrente, `income_total − expenses_total` da projeção == `result_of_month` (sem off-by-cent — `quantize_money` único).

**Quantização / estrutural (§18)**
- [ ] somar cru e quantizar só na fronteira: figuras da projeção quantizadas via `quantize_money`; sem off-by-cent entre projeção e `overview`/`CondoMonthClose` congelado.
- [ ] mês sem leases / prédio sem bills → `0.00` coerente; soft-deleted Bill/Installment/IncomeEntry/BillingAccount excluído dos totais.
- [ ] **virada de mês na TZ SP (§18)**: instante UTC já no mês seguinte enquanto SP ainda no anterior → o mês inicial da projeção usa `current_month_sp()`.

#### `tests/unit/test_finances/test_condo_simulation_service.py` (sob `@freeze_time`)
- [ ] `validate_scenarios`: `type` ausente/inválido → mensagem PT; `amount`/`delta` ausente ou não-decimal → PT; cenário válido → sem erro.
- [ ] **efêmero / sem persistência (design §8/§15)**: `simulate(base, scenarios)` **não** chama `save()`/`create()`/`delete()` (asserir via contagem de objetos no DB antes/depois inalterada) **e** **não muta** `base` (deepcopy — `base` idêntico após a chamada).
- [ ] **delta em memória — só futuro**: cenário `add_expense`/`change_rent` altera só os meses `is_actual=False`; meses `is_actual=True` (real/fechado/atual) ficam **idênticos** ao base. Asserir explicitamente.
- [ ] **re-fold do acumulado**: aplicar `add_expense` em mês futuro → `net` e `cumulative_cash` dos meses **seguintes** recompostos coerentemente (o acumulado re-anda do ponto de alteração; meses anteriores intactos).
- [ ] `compare(base, simulated)`: estrutura side-by-side por mês + Δ `cumulative_cash` final + Δ `net`; Decimais string.
- [ ] múltiplos cenários compõem (ex.: `change_rent` + `add_expense`) sobre o mesmo deepcopy.

#### `tests/integration/test_finances/test_finance_cash_flow_api.py` (freeze_time + throttle off)
- [ ] `GET finance-cash-flow/projection?months=12` → 12 meses; cada item com `year`/`month`/`income_total`/`expenses_total`/`net`/`cumulative_cash`/`is_actual`/`is_closed`; Decimais **string**; valores batendo no `CondoProjectionService`.
- [ ] `projection` params inválidos: `months=abc` → 400 PT; `months=0`/negativo → 400 PT; `months` acima do teto → 400 PT; `building_id=abc` → 400 PT.
- [ ] `POST finance-cash-flow/simulate` com `scenarios` válidos → `{ base, simulated, comparison }`; meses `is_actual=True` idênticos entre `base` e `simulated`.
- [ ] `simulate` sem `scenarios`/lista vazia → 400 PT; cenário inválido (`type` desconhecido) → 400 PT (do `validate_scenarios`).
- [ ] **cache (§11)**: dois GETs de `projection` com a mesma `months`/`building_id` servem do cache; uma escrita de `Bill`/`Installment`/`BillingAccount`/`IncomeEntry`/`CondoMonthClose` **entre** eles invalida `finance-projection*` (probe some) → o 2º GET reflete a mudança. `simulate` (POST) **nunca** cacheia (regressão: dois POSTs idênticos batem no serviço).
- [ ] **matriz `FinancialReadOnly`** (espelhar `test_financial_permissions.py:16-58`): não-admin `GET projection` → **200**; não-admin `POST simulate` → **403**; admin (`is_staff`) `POST simulate` → passa do gate (≠403); anônimo `GET projection` → **401**.

> Rodar (devem **falhar** — serviços/viewset/url ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_condo_projection_service.py tests/unit/test_finances/test_condo_simulation_service.py \
>   tests/integration/test_finances/test_finance_cash_flow_api.py -q
> ```

### 2. GREEN — implementar

1. `finances/services/condo_projection_service.py` — `CondoProjectionService` (consome `CondoBalanceService.result_of_month`/`cash_balance` da S45 para mês atual/baseline; `CondoMonthClose` congelado para mês fechado; `RentScheduleService.collectible_leases`/`effective_rental_value` para receita futura; `Installment`/`BillingAccount.expected_amount`/folha da S41 para despesa futura — com **dedup embutido**; `quantize_money` na fronteira; `today_sp()`/`current_month_sp()`). Reusar o predicado de elegibilidade de conta da S37 (DRY).
2. `finances/services/condo_simulation_service.py` — `CondoSimulationService` (`VALID_SCENARIO_TYPES`, `validate_scenarios`, `simulate` por `deepcopy` + deltas só no futuro + re-fold, `compare`). **Zero** persistência. `quantize_money` na fronteira.
3. `finances/viewsets/dashboard_views.py` — anexar `FinanceCashFlowViewSet` (`projection` cacheado `FINANCE_PROJECTION_PREFIX` + validação `months`/`building_id`; `simulate` POST sem cache + `validate_scenarios`). Reusar o helper de validação `year`/`month`/range da S38 onde aplicável (constante de teto de `months` nomeada, sem magic number).
4. `finances/viewsets/__init__.py` — anexar `FinanceCashFlowViewSet` ao `__all__`.
5. `finances/urls.py` — registrar `finance-cash-flow` → `FinanceCashFlowViewSet`.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_condo_projection_service.py tests/unit/test_finances/test_condo_simulation_service.py tests/integration/test_finances/test_finance_cash_flow_api.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `CondoProjectionService.project` **consome** `result_of_month`/`cash_balance` (S45) para mês atual/baseline e `CondoMonthClose` congelado — **não** re-deriva net/caixa nem o fold (reusar `_fold`/baseline da S45). O teste de "mês atual == `result_of_month`" e "sem off-by-cent vs `overview`" trava isso.
- **Elegibilidade de conta recorrente** (ativa, `tracking_start_month..end_date`, sem `BillSkip`) num **único** predicado puro compartilhado com `BillGenerationService.ensure_month_bills` (S37) — projeção e geração **nunca** divergem (DRY; refator completo se a S37 não expôs helper).
- **Dedup embutido** num ponto único (a parcela embutida só conta via `expected_amount`; a avulsa só via `Installment`) — função pequena, intenção clara; sem ramo duplicado.
- **Quantização só na fronteira** via `quantize_money` (single source S45); somatórios internos crus; nenhum serviço quantiza no meio. **Nenhuma** soma de linhas/alocações em Python que possa ir ao ORM (receita via `effective_rental_value`/`received_collectible_total`; despesa via aggregate de `Installment`/`expected_amount`).
- `CondoSimulationService` **efêmero**: deepcopy + `_apply_*` puros nomeados por cenário (espelha `simulation_service.py:55-`), re-fold num helper puro reusando a fórmula do acumulado da projeção (DRY entre `project` e `simulate`).
- Constante de teto de `months` (ex.: `MAX_PROJECTION_MONTHS = 36`) nomeada; mensagens PT como constantes nomeadas se repetidas (sem magic strings).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_condo_projection_service.py tests/unit/test_finances/test_condo_simulation_service.py \
  tests/integration/test_finances/test_finance_cash_flow_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances/
ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances/
mypy core/ finances/
pyright finances/
```

> **Regressão obrigatória** (não quebrar o que já existe no `finances`): rodar os testes de saldo/fechamento/cache da S45 e geração da S37 que esta projeção consome, para garantir que o consumo aditivo não quebrou o legado da feature:
> ```bash
> python -m pytest tests/unit/test_finances/test_condo_balance_service.py tests/unit/test_finances/test_condo_month_close_service.py \
>   tests/integration/test_finances/test_finance_balance_dashboard_api.py tests/unit/test_finances/test_finance_cache_signals.py -q
> ```

---

## Constraints

- **Direção de dependência** (`.claude/rules/architecture.md`): `finances → core`. Serviços importam `CondoBalanceService`/`CondoMonthCloseService`/`quantize_money`/`timezone` (finances) e `RentScheduleService` (core) — **nunca** views/serializers. Viewsets → serviços; ações **finas**: zero lógica de negócio na view.
- **Consome, não re-deriva** (DRY — design §8/§14): mês atual via `result_of_month`; baseline via `cash_balance`; mês fechado via `CondoMonthClose` congelado; fold via `_fold`/fórmula da S45. **Proibido** recomputar net/caixa/competência aqui.
- **Receita só pelo SSOT** (design §4.5, memória do projeto): receita projetada via `collectible_leases`/`effective_rental_value`; prepaid avaliado **por mês** via `is_prepaid_for_month`; janela via `is_month_tracked` — **nunca** `prepaid_until >= month_start` cru, **nunca** `received_total`/`rental_value` cru. **Sem mudança no SSOT de aluguel.**
- **Dedup embutido** (design §8): a parcela de plano embutido só conta via `expected_amount`; a avulsa só via `Installment`. **Nunca** dobrar. **Pular planos embutidos** na linha de `Installment`.
- **`expected_amount` respeita** `lifecycle_state`/`tracking_start_month`/`end_date`/`BillSkip` — **mesmo** predicado de elegibilidade do `ensure_month_bills` (S37, DRY).
- **Futuro = computado, não materializado** (design §3.2): a projeção **não** chama `ensure_month_bills` nem cria `Bill`/`Installment`. Passado/fechado = real/congelado.
- **Simulação efêmera** (design §8/§15, `.claude/rules/financial.md`): `deepcopy`, deltas em memória, deltas **só no futuro**, **zero** `save/create/delete`, **não** muta `base`.
- **TZ SP única** (design §4): "hoje/mês atual" só via `finances.services.timezone`. Proibido `timezone.now().date()` cru.
- **Quantização só na fronteira** (design §4): `quantize_money` único (S45); somatórios internos crus; sem off-by-cent entre projeção, `overview` e `CondoMonthClose` congelado.
- **Cache** (design §11): `projection` usa `@cache_result(FINANCE_PROJECTION_PREFIX)` (mesma string da S37); `simulate` (POST) **sem** cache. Invalidação já existe (S37/S44).
- **Sem frontend (S48)**, **sem distribuição por proprietário/donos externos (Fase 6 — S49/S50)**, **sem modelos/migração/serviço de saldo-fechamento novos**, **sem wirar o legado** `cash-flow`/`CashFlowService`. **Não** importar `core.services.cash_flow_service`/`simulation_service`.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código. Tipos completos (mypy strict + pyright strict). `cast(User, request.user)` se necessário (padrão `web_push_views`).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from decimal import Decimal`, `from typing import Any`).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; o único `__init__`/`__all__` é o do pacote `finances/viewsets/`.
- **`DecimalField(12,2)`**; dinheiro serializado como **string**. **`FinancialReadOnly`** na rota. Mensagens ao usuário em **Português** (DRF-shape: `error`/`errors`/field-level); logs/identificadores/enum values/`scenario.type`/url_path em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/services/condo_projection_service.py` define `CondoProjectionService` com `project(months=12, building_id=None)` + `_projected_income`/`_projected_expenses` — receita via `collectible_leases`/`effective_rental_value` (prepaid **por mês**, janela pré-tracking), despesa via `Installment` não-embutidos + `expected_amount` (ativas, `end_date`/`BillSkip`/suspensão) + folha, **dedup embutido**, acumulado = fold **ancorado** no último `CondoMonthClose` (baseline `cash_balance` S45), `is_actual`/`is_closed`; mês atual delega a `result_of_month`; mês fechado lê o congelado; quantização só na fronteira.
- [ ] `finances/services/condo_simulation_service.py` define `CondoSimulationService` (`validate_scenarios`/`simulate`/`compare`) **100% efêmero** (deepcopy, deltas só no futuro, re-fold, zero persistência, não muta `base`).
- [ ] `CondoBalanceService.result_of_month`/`cash_balance` (S45), `CondoMonthClose` congelado, `quantize_money` (S45) e a collectibility do SSOT **consumidos sem mudança**; net/caixa **não re-derivados**; SSOT de aluguel intacto.
- [ ] `finances/viewsets/dashboard_views.py` ganha `FinanceCashFlowViewSet` (`projection` cacheado `FINANCE_PROJECTION_PREFIX` + validação `months`/teto/`building_id` → 400 PT; `simulate` POST sem cache + `validate_scenarios` → 400 PT); `FinanceDashboardViewSet` (S38/S45) intacto; `FinancialReadOnly`; ações finas delegando aos serviços.
- [ ] `finances/viewsets/__init__.py` e `finances/urls.py` registram `FinanceCashFlowViewSet`/`finance-cash-flow`; rotas `GET /api/finances/finance-cash-flow/projection/` e `POST /api/finances/finance-cash-flow/simulate/`; registro da S38/S45 intacto.
- [ ] Testes cobrem TODOS os edge-cases §18 desta fase: **dedup** (embutido uma vez via `expected_amount`, avulso uma vez via `Installment`, nunca dobrado), **prepaid jun→jul/2027** (avaliado por mês), **fold ancorado** (baseline + re-âncora em mês fechado + mês fechado vence o computado), **pré-tracking** (receita 0, não acumula espúrio); + receita filtrada (owner/salary-offset fora), `end_date`/suspensão/`BillSkip`, folha §4.6, mês atual == `result_of_month` (sem off-by-cent), simulação efêmera/só-futuro, matriz `FinancialReadOnly` (200/403/non-403/401), cache `finance-projection*` invalidado, `simulate` sem cache.
- [ ] `python -m pytest` (os 3 arquivos + regressão S37/S45) passa 100%; **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum modelo/migração/serviço de saldo-fechamento novo; nenhum `OwnerDistributionService`/distribuição por proprietário; nenhum frontend; nenhuma persistência na simulação; `CondoBalanceService`/`CondoMonthCloseService`/SSOT de aluguel/`core`/`ensure_month_bills` intactos; legado `cash-flow`/`CashFlowService` não wirado nem importado.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_condo_projection_service.py tests/unit/test_finances/test_condo_simulation_service.py \
     tests/integration/test_finances/test_finance_cash_flow_api.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_condo_balance_service.py tests/unit/test_finances/test_condo_month_close_service.py \
     tests/integration/test_finances/test_finance_balance_dashboard_api.py tests/unit/test_finances/test_finance_cache_signals.py -q  # regressão S37/S45
   ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances/
   ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances/
   mypy core/ finances/
   pyright finances/
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 47 (status **concluída**) na tabela da feature Condomínio Finance (abre a Fase 5 — backend).
   - **Arquivos Criados**: `finances/services/condo_projection_service.py`, `finances/services/condo_simulation_service.py`, `tests/unit/test_finances/{test_condo_projection_service,test_condo_simulation_service}.py`, `tests/integration/test_finances/test_finance_cash_flow_api.py`.
   - **Arquivos Modificados**: `finances/viewsets/dashboard_views.py` (`FinanceCashFlowViewSet`), `finances/viewsets/__init__.py`, `finances/urls.py`.
   - **Nota**: "Fase 5 backend — `CondoProjectionService.project` (receita projetada via `collectible_leases`/`effective_rental_value` com prepaid **por mês** + `IncomeEntry`; saídas = `Installment` não-embutidos + `expected_amount` respeitando `lifecycle_state`/`tracking_start_month`/`end_date`/`BillSkip` + folha; **dedup embutido**; acumulado = fold **ancorado** no último `CondoMonthClose` com baseline `CondoBalanceService.cash_balance`; mês atual delega a `result_of_month`, mês fechado lê o congelado; `is_actual`/`is_closed`). `CondoSimulationService` **efêmero** (deepcopy, deltas só no futuro, re-fold, zero persistência). API: `finance-cash-flow/{projection (cacheado finance-projection), simulate (POST, sem cache)}`. Consome S45/S41/S37 sem re-derivar net/caixa; SSOT de aluguel intacto; `quantize_money` único (sem off-by-cent). **Frontend = S48 (tabela acumulada + Real/Projetado + ComposedChart + simulador, gráficos não-blocking); distribuição por proprietário = Fase 6 (S49/S50, consome `result_of_month`, não esta projeção).**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`):
   ```
   feat(finances): add CondoProjectionService + CondoSimulationService + finance-cash-flow projection/simulate endpoints (Phase 5 backend)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **48 — Frontend: Projeção 12 meses (tabela acumulada + badge Real/Projetado) + simulador** (Fase 5 frontend) — consome `GET /api/finances/finance-cash-flow/projection?months=&building_id=` e `POST /api/finances/finance-cash-flow/simulate` **verbatim** (shapes abaixo); TanStack Query v5 (`useQuery` + `placeholderData: keepPreviousData`, **não** `useSuspenseQuery`); Recharts v3 `ComposedChart` (**gráfico não-blocking no gate**, a tabela é o artefato load-bearing); Zod 4 + RHF no simulador; `is_staff` gating no `simulate`. A S48 **não** altera o backend.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`CondoProjectionService`** (`finances/services/condo_projection_service.py`): `project(months=12, building_id=None) -> list[dict]`. Cada item: `{ year: int, month: int, income_total: str, expenses_total: str, net: str, cumulative_cash: str, is_actual: bool, is_closed: bool }` (Decimais **string** via `quantize_money`). Ordem cronológica a partir do mês atual SP. Mês atual delega a `CondoBalanceService.result_of_month`; mês fechado lê `CondoMonthClose` congelado (vence o computado); futuro = computado; baseline do acumulado = `CondoBalanceService.cash_balance` (ancorado). Helpers internos `_projected_income`/`_projected_expenses` (receita SSOT-filtrada com prepaid por mês; despesa = `Installment` não-embutidos + `expected_amount` ativas + folha, **dedup embutido**). **Não** re-deriva net/caixa; **não** materializa `Bill`.
- **`CondoSimulationService`** (`finances/services/condo_simulation_service.py`): `VALID_SCENARIO_TYPES = {add_expense, remove_expense, change_rent, add_income}` (nomes EN; cada cenário `{ type, amount|delta, months? }`); `validate_scenarios(scenarios) -> list[str]` (PT); `simulate(base, scenarios) -> list[dict]` (deepcopy, deltas **só no futuro** `is_actual=False`, re-fold, **efêmero/zero persistência**, não muta `base`); `compare(base, simulated) -> dict` (side-by-side + Δ `cumulative_cash` final + Δ `net`, Decimais string).
- **API Fase 5** (`/api/finances/...`, `FinancialReadOnly`): `GET finance-cash-flow/projection?months=&building_id=` → `CondoProjectionService.project` (lista de meses; cacheado `finance-projection`; `months` 1..teto, default 12; `building_id` opcional); `POST finance-cash-flow/simulate` body `{ scenarios: [{type, amount|delta, months?}], months?, building_id? }` → `{ base, simulated, comparison }` (sem cache; `scenarios` lista não-vazia validada). **Frontend da Fase 5 (S48)** consome esses shapes verbatim.
- **Cache**: `projection` invalidado por escritas de `Bill`/`Installment`/`BillingAccount`/`IncomeEntry`/`CondoMonthClose`/`RentPayment`/owner/lease via `finance-*` (S37/S44 — já existe). `simulate` (POST) **nunca** cacheado.
- **Invariantes pinadas por teste aqui**: dedup embutido (parcela embutida uma vez via `expected_amount`, avulsa uma vez via `Installment`); prepaid avaliado **por mês** (Adriana jun excluída/jul incluída); fold ancorado (re-âncora em mês fechado; congelado vence); janela pré-tracking (receita 0, sem net espúrio); mês atual `income_total − expenses_total == result_of_month` (sem off-by-cent — `quantize_money` único); simulação efêmera e só-futuro. **Fase 6 (S49/S50)** NÃO consome esta projeção — consome `CondoBalanceService.result_of_month` (household = condomínio).
