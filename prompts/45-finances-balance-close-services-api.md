# Sessão 45 — Backend: `CondoBalanceService` + `CondoMonthCloseService` + `received_collectible_total` (consumo) + serializers/viewsets/endpoints de saldo/reserva/income/fechamento

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → **44 → 45** → 46 → 47 → 48 → 49 → 50 (esta **fecha a Fase 4 — Saldo + Reserva + Income avulso + Fechamento**)
> Esta sessão entrega o **núcleo de dinheiro** do condomínio: `CondoBalanceService` (resultado de competência, variação de caixa, **caixa condo-scoped ancorado no último `CondoMonthClose`**, reserva sem dupla-contagem, saldo total, atrasados via annotation, **wedge identity**) consumindo o `received_collectible_total` (S37); `CondoMonthCloseService.close/reopen` (cronológico; reopen recomputa cascata); e a **API** dos modelos da S44 (`reserves`, `reserve-movements`, `income-entries`, `condo-month-closes`) + ações `deposit`/`withdraw`/`close`/`reopen` + dashboard `finance-dashboard/{overview,monthly_balance,by_category}`. **Sem projeção/simulação (Fase 5 — S47); sem distribuição por proprietário (Fase 6).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4 inteira — especialmente §4.2 caixa/competência/reserva/saldo, §4.3 reserva sem dupla-contagem, §4.4 atrasado via annotation, §4.5 receita filtrada, §4.6 Rosa contado uma vez, §4.7 âncora do fold/janela pré-tracking, §4.8 pagamentos; §5.2 blocos "Pagamentos/reserva/receita" e "Fechamento"; §6 receita não-invasiva; §8 `CondoBalanceService`/`CondoMonthCloseService`; §9 API; §11 cache; §13 migrações; §14 Fase 4; §18 edge-cases "Reserva" + "Atrasado/overdue" + "Receita/collectibility" + "Fold/fechamento" + "Estruturais")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Prompt da S44 (modelos `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` + extensão `pay()` reserva — contratos cross-session no rodapé)**: `@prompts/44-finances-reserve-income-close-models.md`
- **Prompt da S37 (serviços de contas + `received_collectible_total` + cache)**: `@prompts/37-finances-bill-services-cache.md`
- **Prompt da S38 (serializers/viewsets/API — exemplar do padrão dual + dashboard bare)**: `@prompts/38-finances-serializers-viewsets-calendar.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Caixa ancorado: baseline do último snapshot fechado + fallback `FinancialSettings`, re-anda só a cauda aberta** | `core/services/daily_control_service.py:184-211` (`_get_starting_balance(month_start)`: `MonthSnapshot.objects.filter(reference_month__lt=…, is_finalized=True).order_by('-reference_month').first()` :191-198; fallback `FinancialSettings.initial_balance` se `initial_balance_date <= month_start` :203-209; `Decimal("0.00")` :211) | **Exemplar canônico** do baseline do `CondoBalanceService.cash_balance`. Espelhar a lógica, mas **condo-scoped** (`CondoMonthClose.cash_balance_end` do último mês `closed`, NÃO o `MonthSnapshot` commingled — design §4.2/§8). Caixa do condo é **escopo próprio** |
| **Service stateless `@staticmethod`, `Decimal`, `transaction.atomic`+`select_for_update`, retorno PT / log EN** | `core/services/rent_schedule_service.py:61` (classe `RentScheduleService`) + `toggle_payment` (`transaction.atomic`/`select_for_update`/retorno `{status,…}` PT/`logger` EN) | **Estrutura-base** de `CondoBalanceService` e `CondoMonthCloseService`. `close/reopen` são leitura-modificação atômica (lock no `CondoMonthClose`) |
| **`received_collectible_total` (recebido FILTRADO por collectibility — CONSUMIR, não recriar)** | `core/services/rent_schedule_service.py` (S37: `@staticmethod received_collectible_total(reference_month, building_id=None) -> Decimal`, espelha `received_total` :367-378 mas pré-filtrado por `collectible_leases`) | A entrada de caixa "aluguel recebido" do `CondoBalanceService` usa **este** (design §4.5), **nunca** o `received_total` cru (somaria Tiago/Alvaro). **Reusar — não reimplementar cobrabilidade** |
| `collectible_leases` / `effective_rental_value` / `get_month_stats` (esperado + atraso de aluguel) | `core/services/rent_schedule_service.py:142` (`collectible_leases`), `:123` (`effective_rental_value`), `:308` (`get_month_stats` → `overdue_total_fee`/`overdue_count`) | Receita esperada do net = Σ `effective_rental_value` de cobráveis **não pagos** (design §4.5). O sub-total de **atraso de aluguel** do dashboard vem de `get_month_stats` (separado das contas) |
| `displayable_leases` (donos externos — só leitura, **NÃO** nesta fase) | `core/services/rent_schedule_service.py:194-237` (`(lease, False, "owner_repass")` p/ owner-set) | **Apenas para saber o que NÃO fazer aqui**: agregação por dono externo (Tiago/Alvaro) é **Fase 6 (S49/S50)**. `CondoBalanceService` exclui-os do net/caixa (não entram em `collectible_leases`) |
| **`Bill.objects.with_amounts(today)` (annotations — atrasados/competência via ORM, NUNCA Python)** | `finances/models.py` (S36: `BillQuerySet.with_amounts`, `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue`; `is_overdue` = `due_date<today` ∧ `amount_remaining>0` ∧ `lifecycle_state='active'`) | `CondoBalanceService` lê competência (Σ `amount_total` de bills `active` no mês) e atrasados (`is_overdue=True`) **só** via annotation. **Proibido** somar linhas/alocações em Python (design §4.4) |
| **`Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` (S44 — CONSUMIR, não recriar)** | `finances/models.py` (S44: `ReserveMovement.kind ∈ {deposit, withdrawal}`/`amount`/`movement_date`/`bill?`; `IncomeEntry.is_received`/`received_date`; `CondoMonthClose.status ∈ {open, closed}`/`net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out`/`breakdown` (JSON); unique `(condominium, reference_month)`) | Esta sessão **lê/escreve** esses modelos via serviços; **não** os cria nem migra (S44). `ReserveMovement` é o ledger único do caixa/reserva (design §4.3) |
| **`BillPaymentService.pay(...)` — base caixa (S37); ESTENDIDO nesta S45** | `finances/services/bill_payment_service.py` (S37 criou `pay`/`unpay` atômicos só com caixa) | Esta S45 adiciona `funded_from=reserve` (→ `ReserveMovement(withdrawal, bill=…)` + guarda de saldo) e o guard `assert_open` de mês fechado. `CondoBalanceService` só **lê** o ledger resultante |
| **Serializer dual (nested read + `_id` write, FK opcional `allow_null`)** | `core/serializers.py:772-846` (`ExpenseSerializer`: `<fk> = XSerializer(read_only=True)` + `<fk>_id = PrimaryKeyRelatedField(queryset=…, source='<fk>', write_only=True, required=False, allow_null=True)`; `read_only_fields` :810-846) | **Exemplar canônico** de `ReserveSerializer`/`ReserveMovementSerializer`/`IncomeEntrySerializer`/`CondoMonthCloseSerializer` (dual; Decimal **string**) |
| Serializer com `SerializerMethodField` (read-only derivado Decimal string) | `core/serializers.py:594` (`lease_summary`), `:742` (`is_overdue`) + S38 `BillSerializer.amount_*` (lidos da annotation) | Padrão p/ expor `cash_balance_end`/`reserve_balance_end`/`net_result`/`carry_forward_out` como **string** read-only |
| **Bare `ViewSet` + `@action(detail=False)` (dashboard read-only, agregação por serviço, validação `year`/`month` 1–12)** | `core/viewsets/financial_dashboard_views.py:24-87` (`FinancialDashboardViewSet`: `permission_classes=[FinancialReadOnly]` :27; `overview` :29-32 delega; `category_breakdown` :61-73 lê `year`/`month`, 400 em `ValueError`) + `:155-173` (`monthly` do `CashFlowViewSet`, range check) | **Exemplar canônico** do `FinanceDashboardViewSet` desta sessão (`overview`/`monthly_balance`/`by_category`) — **estender** o viewset criado na S38 (combined_calendar/overdue), não recriar |
| **`@action(detail=True, methods=['post'])` delegando a serviço + 400/404 PT** | `core/views.py:430-486` (`change_due_date`: `request.data` :439, validação obrigatório → 400 :441-444, `try/except ValidationError` → 400, delega ao serviço) | **Exemplar canônico** das ações `reserves/{id}/deposit|withdraw` e `condo-month-closes/{close|reopen}`: view fina, lógica no serviço, erros DRF-shape PT |
| `ModelViewSet` + `FinancialReadOnly` + `get_queryset` (filtros por query param) | `core/viewsets/financial_views.py:56-90` (`PersonViewSet`/`CreditCardViewSet`) + S38 `finances/viewsets/crud_views.py` (padrão já estabelecido p/ `bills`/`payments`) | Forma-base dos CRUD viewsets desta sessão (`ReserveViewSet`/`ReserveMovementViewSet`/`IncomeEntryViewSet`/`CondoMonthCloseViewSet`) — espelhar os da S38 |
| Pagination / Permission (reuso direto) | `core/pagination.py:7-18` (`CustomPageNumberPagination`, `page_size=20`/`max_page_size=500`) + `core/permissions.py:107-121` (`FinancialReadOnly`: auth lê, `is_staff` escreve, :121 `return bool(request.user.is_staff)`) | **Reusar** em todos os viewsets/ações desta sessão. Import direto, não inline |
| `@cache_result` + prefixos `finance-*` (consumir os literais da S37) | `finances/cache.py` (S37: `FINANCE_DASHBOARD_PREFIX="finance-dashboard"`, `invalidate_finance_caches()`) + `core/cache.py:213-255` (`@cache_result`/`invalidate_pattern`) | `overview`/`monthly_balance`/`by_category` usam `@cache_result(key_prefix=FINANCE_DASHBOARD_PREFIX, …)`; a invalidação já existe (S37/S44). **`combined_calendar` continua SEM cache** (S38/§11) |
| Registro de router + `include` no projeto | `core/urls.py:46-82` (router; `path("api/", include(router.urls))`) + `condominios_manager/urls.py:67` (`include("core.urls")`) + S38 `finances/urls.py` (router próprio do `finances`) | **Anexar** os novos viewsets ao `finances/urls.py` da S38 (não criar novo router/projeto wiring) |
| **Teste de integração — matriz `FinancialReadOnly`** | `tests/integration/test_financial_permissions.py:16-58` (listas de endpoints; `test_non_admin_cannot_write` 403; admin passa do gate; `test_non_admin_can_read` 200; `test_unauthenticated` 401) + S38 `tests/integration/test_finances/test_finance_permissions.py` | **Exemplar canônico** da matriz das rotas novas (`reserves`/`reserve-movements`/`income-entries`/`condo-month-closes` + ações + dashboard) |
| **Teste de integração — endpoint backed-by-service (sem mock de internals) + freezegun + throttle off** | `tests/integration/test_rent_calendar_api.py:1-59` (política :1-10; `_disable_throttling` :29-40; CPFs válidos) + S38 `tests/integration/test_finances/*` | Padrão dos testes de API desta sessão: View → Service → Model real, `freeze_time`, throttle off |
| Factories `finances` (S36/S41/S44) | `tests/factories.py` (S36: `make_billing_account`/`make_bill`/`make_bill_line_item`/`make_payment`/`make_payment_allocation`; S44: `make_reserve`/`make_reserve_movement`/`make_income_entry`/`make_condo_month_close`) + `make_condominium`/`make_building` (S34) + `make_lease`/`make_rent_payment` (core) | Dados dos testes. **Reusar** — não criar objetos manualmente nem factory nova salvo necessidade real (KISS) |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **só `freezegun`** (congelar a data p/ `today_sp()`/`is_overdue`/baseline); ORM/serviços/`RentScheduleService`/`BillPaymentService` reais |

### O que as Sessões 34/36/37/38/41/44 já entregaram (PRÉ-REQUISITO — NÃO recriar)

**Verificar no `SESSION_STATE.md` que S44 e S37 estão concluídas.** Se qualquer uma não estiver, **PARE** (DEPENDENCY ORDER 44→45 e 37→…→45).

- **S34** (infra): app `finances` + `FinancesConfig.ready()` importando `finances/signals.py` + `core.Condominium`(padrão) + `Building.condominium` + helper TZ `finances/services/timezone.py` (`today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`) + gate ampliado + `make_condominium`/`make_building`.
- **S36** (modelos núcleo): `Category`/`BillingAccount`/`Bill`/`BillLineItem`/`BillSkip`/`Payment`/`PaymentAllocation`; enums `BillBehavior`/`BillLifecycleState`/`BillingAccountState`/`FundedFrom`; **`Bill.objects.with_amounts(today)`** (annotations); unique parciais; migração + RLS.
- **S37** (serviços de contas + cache): `BillGenerationService.ensure_month_bills`, `BillService.create_with_lines`, `BillPaymentService.pay`/`unpay`; `finances/cache.py` (prefixos `finance-*` + `invalidate_finance_caches`); `finances/signals.py` real; `core/signals.py` estendido + cross-app NET-NEW Apartment/Lease; **`RentScheduleService.received_collectible_total`** (aditivo, read).
- **S38** (API Fase 2): `finances/serializers.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py` (`FinanceDashboardViewSet` com `combined_calendar`/`overdue`), `finances/services/condo_calendar_service.py`, `finances/urls.py` (router próprio) + `path("api/finances/", …)` no projeto.
- **S41** (Fase 3): `InstallmentPlan`/`Installment`/`Employee`; `Bill.installment`/`Bill.employee`/`BillLineItem.installment`; `convert_deferred`; `ensure_month_bills` estendido (parcelas + folha + abatimento §4.6 = `effective_rental_value`).
- **S44** (modelos Fase 4): `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` (`CondoMonthClose` e `BillSkip` = `AuditMixin` only, **sem** SoftDelete) + migração + RLS + factories; receivers `finance-*` dos modelos novos. **A S44 é models-only e NÃO toca `pay()`** — a extensão de `pay()` (`funded_from=reserve` + `assert_open`) é entregue NESTA sessão (S45).

> **Se a S44 ou a S37 não estiverem concluídas, PARE.** Esta sessão depende delas (DEPENDENCY ORDER 44→45, 37→…→45). Não recriar modelos, migração, `pay()` reserva, cache ou signals aqui.

---

## Escopo

### Arquivos a criar
- `finances/services/condo_balance_service.py` — `CondoBalanceService` (resultado de competência, variação de caixa, caixa condo-scoped ancorado, reserva, saldo total, atrasados, wedge identity).
- `finances/services/condo_month_close_service.py` — `CondoMonthCloseService` (`close`/`reopen`/`assert_open` + recompute cascata).
- `tests/unit/test_finances/test_condo_balance_service.py` — testes do balanço (invariantes §4 com exemplos trabalhados + edge-cases §18).
- `tests/unit/test_finances/test_condo_month_close_service.py` — testes do fechamento (cronológico, reopen cascata, assert_open).
- `tests/integration/test_finances/test_finance_reserve_income_api.py` — CRUD + ações `deposit`/`withdraw` (reserva sem dupla-contagem, guarda negativa) + `income-entries`.
- `tests/integration/test_finances/test_finance_monthclose_api.py` — CRUD + ações `close`/`reopen` (cronológico, bloqueio de write em mês fechado).
- `tests/integration/test_finances/test_finance_balance_dashboard_api.py` — `finance-dashboard/{overview,monthly_balance,by_category}` (KPIs string, wedge, atrasados).

### Arquivos a modificar
- `finances/serializers.py` (S38) — **anexar** `ReserveSerializer`, `ReserveMovementSerializer`, `IncomeEntrySerializer`, `CondoMonthCloseSerializer` (dual: nested read / `_id` write; Decimal string). Serializers existentes **intactos**.
- `finances/viewsets/crud_views.py` (S38) — **anexar** `ReserveViewSet` (+ ações `deposit`/`withdraw`), `ReserveMovementViewSet`, `IncomeEntryViewSet`, `CondoMonthCloseViewSet` (+ ações `close`/`reopen`). Viewsets existentes **intactos**.
- `finances/viewsets/dashboard_views.py` (S38) — **estender** `FinanceDashboardViewSet` com `overview`, `monthly_balance`, `by_category` (delegando a `CondoBalanceService`). `combined_calendar`/`overdue` da S38 **intactos** (`combined_calendar` continua sem cache).
- `finances/viewsets/__init__.py` — anexar os novos viewsets ao `__all__`.
- `finances/urls.py` (S38) — registrar `reserves`, `reserve-movements`, `income-entries`, `condo-month-closes` no router existente. Registro de `bills`/`payments`/`finance-dashboard` **intacto**.
- `core/services/rent_schedule_service.py` — **NÃO modificar** (apenas consumir `received_collectible_total`/`get_month_stats`/`collectible_leases`/`effective_rental_value` da S37; sem assinatura nova). Listado aqui só para deixar explícito que é **consumo aditivo, zero mudança no SSOT**.
- `tests/factories.py` — só se faltar factory para os testes (improvável; S44 cobriu as 4 novas). Não duplicar.

### NÃO fazer (pertence a outras sessões)
- **Sem `CondoProjectionService`/`CondoSimulationService`** (futuro computado, prepaid por mês, ancorado; `cash-flow/{projection,simulate}`) — é a **Fase 5 (Sessão 47)**. A Fase 5 **consome** `CondoBalanceService.result_of_month`/baseline desta sessão (DRY — não re-deriva net/caixa). **Não** criar `finance-cash-flow`/`finance-projection` endpoints aqui (os **prefixos** já existem desde a S37; o **consumo** via `@cache_result` é da S47).
- **Sem `OwnerDistributionService`** (fold/carry-forward por household, agregação de donos externos `displayable_leases`) e **sem** `finance-dashboard/{monthly_balance→distribuição, by_owner}` no sentido de rateio por proprietário — é a **Fase 6 (S49/S50)**. **Decisão pinada**: esta sessão entrega `carry_forward_out` **dentro do `CondoMonthClose`** (campo da S44, calculado no `close`), mas **não** expõe distribuição por proprietário nem a "seção de donos externos" (S50). O `OwnerDistributionService.compute` da Fase 6 **consome** `CondoBalanceService.result_of_month` desta sessão (design §8 — DRY).
- **Esta sessão (S45) ESTENDE `BillPaymentService.pay`/`unpay`** (criado na S37 só com caixa): adiciona o caminho `funded_from=reserve` (→ `ReserveMovement(withdrawal, bill=…)` + guarda de saldo) **e** o guard de mês fechado (`assert_open`). A S44 é models-only e NÃO toca `pay()`. `CondoBalanceService` apenas **lê** o ledger. **Não** duplicar o guard de mês fechado dentro do `pay`.
- **Sem modelos/migração novos** — `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` e seus campos são da S44. Esta sessão **não** adiciona campo nem migra.
- **Sem frontend** (hooks `use-finance-balance`/`use-reserve`, KPIs cards, donut por categoria, query-keys, Zod) — é a **Sessão seguinte de frontend da Fase 4**. Nada em `frontend/`.
- **Sem wirar o legado** `DailyControlService`/`daily-control` no dashboard novo (design §10/§15) — o calendário/saldo novo supera o legado; não wirar os dois.
- **Sem mudança no SSOT de aluguel** (memória do projeto): rotear collectibility **só** por `RentScheduleService` (`collectible_leases`/`received_collectible_total`/`is_prepaid_for_month`); **nunca** `prepaid_until >= month_start` cru, **nunca** `received_total` cru no net/caixa.

---

## Especificação

> Serviços stateless em `finances/services/`, todos `@staticmethod`. `Decimal` para dinheiro; **somar Decimals crus e quantizar (`ROUND_HALF_UP`) só na fronteira de saída/agregado**, num **único helper** idêntico em todo serviço que re-deriva a mesma figura (design §4 — sem off-by-cent entre dashboard e fechamento). "Hoje/mês atual" **sempre** via `finances.services.timezone.today_sp()`/`current_month_sp()` (settings é UTC). `@transaction.atomic` + `select_for_update` em leitura-modificação (`close`/`reopen`). Mensagens ao usuário em **PT**, logs/identificadores/enum values em **EN**. Direção: serviços importam de `finances.models`, `finances.services.timezone`, `core.services.rent_schedule_service` — **nunca** de views/serializers.

### Helper de quantização único (DRY — fronteira de saída)

Definir **um** helper (ex.: `finances/services/money.py` `quantize_money(value: Decimal) -> Decimal` com `ROUND_HALF_UP` em `Decimal("0.01")`, retornando string-friendly Decimal) **se ainda não existir** (verificar S37/S38 — se a S37 já criou um helper de quantização, **reusar**, não duplicar). Todo KPI exposto pelo `CondoBalanceService` e congelado pelo `CondoMonthCloseService` passa pelo **mesmo** helper (garante que `cash_balance_end` do `close` == caixa on-read do `CondoBalanceService` no fim do mês — sem divergência de centavo). Os somatórios internos são **crus**; só a figura de saída é quantizada.

### `CondoBalanceService` (design §4.2/§4.3/§4.4/§4.5/§8)

Service stateless, `@staticmethod`. Um **único ledger walk** por figura; baseline do último `CondoMonthClose`. Assinaturas:

```python
from datetime import date
from decimal import Decimal
from typing import Any

class CondoBalanceService:

    @staticmethod
    def result_of_month(year: int, month: int, building_id: int | None = None) -> Decimal:
        """Resultado do mês (COMPETÊNCIA) = receita_competência − despesa_competência.
        - receita_competência = received_collectible_total(M, building_id)            # recebido de cobráveis (S37)
            + Σ effective_rental_value de collectible_leases NÃO pagas no mês (esperado)  # design §4.5
            + Σ IncomeEntry.amount com income_date no mês (is_received OU não — DECIDIR e travar: competência usa income_date)
        - despesa_competência = Σ Bill.with_amounts(today).amount_total de bills com
            competence_month == M E lifecycle_state == 'active'  (exclui suspended/deferred/canceled — design §4.2)
        - building_id filtra building (bills nível-condomínio building=null entram quando building_id é None).
        - NUNCA received_total cru; NUNCA somar linhas em Python (amount_total via annotation).
        - Reserva NÃO entra (transferência de caixa, não competência — design §4.7)."""

    @staticmethod
    def cash_change_of_month(year: int, month: int, building_id: int | None = None) -> Decimal:
        """Variação de caixa do mês (por DATA DE PAGAMENTO) = entradas_caixa − saídas_caixa.
        - entradas_caixa = received_collectible_total(M, building_id) (RentPayment de cobráveis, por reference_month=M)
            + Σ IncomeEntry.amount com is_received=True e received_date no mês
            + Σ ReserveMovement(withdrawal, bill=null) com movement_date no mês   # saque reserva→caixa
        - saídas_caixa = Σ PaymentAllocation.amount cujo Payment.funded_from='caixa' e Payment.payment_date no mês
            + Σ ReserveMovement(deposit) com movement_date no mês                  # depósito caixa→reserva
        - Pagamento funded_from='reserve' NÃO conta como saída de caixa (debita só a reserva — design §4.3).
        - Ledger ordenado deterministicamente (movement_date, id)."""

    @staticmethod
    def cash_balance(as_of_month: date | None = None, building_id: int | None = None) -> Decimal:
        """Caixa atual condo-scoped = baseline + Σ variações de caixa dos meses ABERTOS desde o baseline.
        - baseline = CondoMonthClose.cash_balance_end do ÚLTIMO mês 'closed' (< as_of_month),
          ou FinancialSettings.initial_balance se não houver fechado E initial_balance_date <= as_of_month,
          senão Decimal('0.00').  (espelha _get_starting_balance :184-211, mas CONDO-SCOPED — design §4.2)
        - re-anda SÓ a cauda aberta (do mês após o último fechado até as_of_month) somando cash_change_of_month.
        - as_of_month None = mês atual (current_month_sp()). Caixa PODE ficar negativo (aviso, não bloqueio §4.3)."""

    @staticmethod
    def reserve_balance(condominium_id: int | None = None) -> Decimal:
        """Reserva = Σ ReserveMovement(deposit) − Σ ReserveMovement(withdrawal).  Nunca negativa (guarda no pay/withdraw, S44)."""

    @staticmethod
    def total_balance(as_of_month: date | None = None) -> Decimal:
        """Saldo total = cash_balance + reserve_balance (design §4.2)."""

    @staticmethod
    def overdue_bills_total(building_id: int | None = None) -> Decimal:
        """KPI 'Atrasados' (contas) = Σ amount_remaining de Bill.with_amounts(today).filter(is_overdue=True).
        (annotation: due_date<today ∧ amount_remaining>0 ∧ lifecycle_state='active' — design §4.4).
        NÃO amount_total; deferido/suspenso/cancelado fora. Atraso de ALUGUEL é figura SEPARADA
        (get_month_stats → overdue_total_fee) — NÃO somar aqui."""

    @staticmethod
    def overview(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """KPIs do mês (todos Decimal como string na fronteira via quantize_money):
        { year, month,
          result_of_month, cash_change_of_month, cash_balance, reserve_balance, total_balance,
          overdue_bills_total, overdue_bills_count,
          rent_overdue: { count, total_fee },          # de get_month_stats (separado)
          wedge_ok: bool }                              # ver §wedge
        Consome result_of_month/cash_change_of_month/cash_balance/reserve_balance/total_balance (DRY — não re-deriva)."""
```

### Wedge identity (reconciliação — testada, design §4.2)

`Variação_de_caixa[M] = Resultado_competência[M] − Δ(contas a receber)[M] + Δ(contas a pagar)[M] ± transferências de reserva[M]`. Os dois KPIs (`result_of_month` e `cash_change_of_month`) **não podem divergir silenciosamente**.

- Definir **um** método/teste de reconciliação `_wedge_residual(year, month, building_id) -> Decimal` (interno) que computa as duas pontas e o termo de ajuste (Δ a receber = aluguel/income esperado-não-recebido; Δ a pagar = bills-competência-não-pagos; transferências = depósitos/saques de reserva do mês). O **invariante pinado por teste** (§4.2): num cenário **totalmente liquidado e sem transferências de reserva** (tudo recebido e pago no mês, nenhum a-receber/a-pagar pendente), `cash_change_of_month == result_of_month` **exatamente**. Em cenários com pendências, o residual do wedge é `Decimal("0.00")` (identidade fecha). `overview.wedge_ok = (_wedge_residual(...) == 0)`.
- **Não** transformar o wedge num cálculo paralelo de caixa (KISS) — é uma **checagem de consistência** entre as duas figuras já computadas, não uma terceira fonte de verdade.

### `CondoMonthCloseService` (design §4.7/§5.2/§8)

Service stateless, `@staticmethod`. Atômico (`select_for_update` no `CondoMonthClose`).

```python
@staticmethod
def assert_open(competence_month: date) -> None:
    """Levanta ValidationError PT ('Este mês está fechado e não aceita lançamentos.')
    se existe CondoMonthClose(reference_month=mês de competence_month, status='closed').
    Consumido por BillPaymentService.pay/unpay (S44) ANTES de mexer no bill (design §8).
    Mês sem CondoMonthClose = aberto (no-op)."""

@staticmethod
def close(year: int, month: int, user: User | None = None) -> CondoMonthClose:
    """Fecha o mês M (1º dia). CRONOLÓGICO: rejeita fechar M se existe um mês ANTERIOR
    sem CondoMonthClose 'closed' (sem gap — design §8 'cronológico; sem gap') → ValidationError PT.
    Já fechado → ValidationError PT (idempotência explícita: não re-fecha).
    Congela (via CondoBalanceService, quantize_money):
      net_result = result_of_month(year, month)
      cash_balance_end = cash_balance(as_of_month = 1º dia do mês SEGUINTE)   # caixa ao FIM do mês
      reserve_balance_end = reserve_balance()
      carry_forward_out = min(0, net_result + carregado_in)                   # design §4.7 fold (carregado_in do mês anterior fechado)
      breakdown = JSON mínimo p/ exibição (os KPIs do overview)
      status='closed', closed_at=today_sp(), created_by/updated_by=user.
    get_or_create na unique (condominium, reference_month) — race-safe. @transaction.atomic + select_for_update."""

@staticmethod
def reopen(year: int, month: int, user: User | None = None) -> CondoMonthClose:
    """Reabre M (status→'open'). Recomputa em CASCATA os meses fechados SEGUINTES ainda dependentes:
    reabrir M invalida o baseline dos meses M+1, M+2, … fechados → re-derivar/atualizar
    cash_balance_end/net_result/carry_forward_out deles a partir do novo baseline (design §8
    'reopen recomputa cascata os meses abertos seguintes').
    DECISÃO pinada (travar por teste): reopen(M) marca M como 'open' E recomputa os snapshots
    'closed' de M+1.. (mantendo-os 'closed', com números atualizados a partir do baseline recomputado);
    NÃO reabre automaticamente os seguintes (só recomputa seus valores congelados). Documentar a escolha.
    Não existe CondoMonthClose p/ M → ValidationError PT. @transaction.atomic + select_for_update."""
```

> **Contrato de bloqueio de mês fechado:** `CondoMonthCloseService.assert_open` é **definido aqui** e **consumido** por `BillPaymentService.pay`/`unpay` (a S44 já inseriu a chamada — confirmar; se a S44 deixou a chamada como ponto de extensão sem o método existir, esta sessão **fecha o contrato** entregando o `assert_open` com a assinatura exata acima). **Não** duplicar o guard dentro do `pay`.

### Receita do `IncomeEntry` — competência vs caixa (pinar e travar)

`IncomeEntry` (S44) tem `income_date`, `is_received`, `received_date`. **Decisão pinada** (design §4.2/§4.5):
- **Competência** (`result_of_month`) usa **`income_date`** no mês (a receita "pertence" ao mês de competência, independente de recebida).
- **Caixa** (`cash_change_of_month`) usa **`received_date`** no mês **e** `is_received=True` (só entra no caixa quando recebida).
- Travar por teste o caso onde `income_date` e `received_date` caem em meses diferentes (competência num mês, caixa no outro) — sem dupla-contagem.

---

## API (design §9)

Base `/api/finances/...` (router próprio do `finances`, S38). `ModelViewSet` + `FinancialReadOnly`; dashboard = bare `ViewSet` + `FinancialReadOnly`. `CustomPageNumberPagination`. Serializers **dual**; Decimal **string**; `reference_month` = 1º dia.

### Serializers (anexar a `finances/serializers.py`)
- **`ReserveSerializer`** — `condominium`/`condominium_id`, `name`, `notes`, e `balance` (read-only string via `SerializerMethodField` ← `CondoBalanceService.reserve_balance`). FK nested read / `_id` write.
- **`ReserveMovementSerializer`** — `reserve`/`reserve_id`, `kind` (`deposit|withdrawal`), `amount` (string ≥0), `movement_date`, `bill`/`bill_id` (nullable — saque p/ pagar conta vs `null` = transferência caixa), `reference`, `notes`. **Write de movimento de reserva é via `reserves/{id}/deposit|withdraw`** (a guarda de saldo vive no serviço); `ReserveMovementViewSet` expõe list/retrieve (read) + create admin, mas a forma canônica é a ação. Documentar.
- **`IncomeEntrySerializer`** — `condominium`/`condominium_id`, `building`/`building_id` (nullable), `category`/`category_id` (nullable), `description`, `amount` (string >0), `income_date`, `is_received`, `received_date`, `notes`.
- **`CondoMonthCloseSerializer`** — `condominium`/`condominium_id`, `reference_month`, `status`, `closed_at`, `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out` (Decimal **string** read-only), `breakdown` (read-only). Write canônico é via `condo-month-closes/{close|reopen}`; create/update padrão não recalcula (read-only nos campos derivados).

### Viewsets CRUD (anexar a `finances/viewsets/crud_views.py`)
- **`ReserveViewSet`** — `select_related('condominium')`; ações `deposit`/`withdraw`.
- **`ReserveMovementViewSet`** — `select_related('reserve','bill')`; filtros `reserve_id`, `kind`, date range (`movement_date`).
- **`IncomeEntryViewSet`** — `select_related('building','category','condominium')`; filtros `building_id`, `category_id`, `is_received`, date range (`income_date`).
- **`CondoMonthCloseViewSet`** — `select_related('condominium')`; filtros `status`, `reference_month`; ações `close`/`reopen`.

### Ações (view fina, lógica no serviço — exemplar `change_due_date`)
- **`reserves/{id}/deposit`** — `@action(detail=True, methods=['post'])`. Lê `amount` (obrigatório, >0 → 400 PT), `movement_date` (ISO, default `today_sp()`), `reference`/`notes` opcionais. Cria `ReserveMovement(deposit, amount, movement_date)` (transferência **caixa→reserva**: caixa −amount, reserva +amount, **saldo total inalterado** — design §4.3). Retorna a `Reserve` com `balance` atualizado.
- **`reserves/{id}/withdraw`** — `@action(detail=True, methods=['post'])`. Lê `amount` (>0), `movement_date`. Cria `ReserveMovement(withdrawal, amount, movement_date, bill=null)` (transferência **reserva→caixa**). **Guarda**: `amount > reserve_balance` → 400 PT ("Saldo da reserva insuficiente.") — reserva nunca negativa (design §4.3/§18). Retorna a `Reserve` com `balance`.
- **`condo-month-closes/close`** — `@action(detail=False, methods=['post'])`. Lê `year`/`month` (1–12 → 400 PT). Delega a `CondoMonthCloseService.close(year, month, user)`. Gap cronológico / já-fechado → 400 PT. Retorna o `CondoMonthClose` serializado.
- **`condo-month-closes/reopen`** — `@action(detail=False, methods=['post'])`. Lê `year`/`month`. Delega a `CondoMonthCloseService.reopen(year, month, user)`. Mês inexistente → 400 PT. Retorna o `CondoMonthClose` (status `open`).

### Dashboard (estender `FinanceDashboardViewSet`, S38)
- **`overview`** — `@action(detail=False, methods=['get'])`. Lê `year`/`month` (default mês atual SP; 1–12 → 400 PT), `building_id` opcional. Delega a `CondoBalanceService.overview(...)`. **Cacheado** via `@cache_result(key_prefix=FINANCE_DASHBOARD_PREFIX, …)` (invalidação já existe — S37/S44). Retorna os KPIs (Caixa / Reserva / Resultado do mês / Atrasados / Saldo total) + `rent_overdue` + `wedge_ok`.
- **`monthly_balance`** — `@action(detail=False, methods=['get'])`. Lê `year` (obrigatório) + `building_id` opcional. Retorna a série dos 12 meses do ano: `[{ month, result_of_month, cash_change_of_month, cash_balance_end, reserve_balance_end, total_balance, is_closed }]` (mês fechado lê do `CondoMonthClose` congelado; aberto computa on-read via `CondoBalanceService` — design §3.2 "passado = linhas reais / fechado = congelado"). Cacheado `FINANCE_DASHBOARD_PREFIX`.
- **`by_category`** — `@action(detail=False, methods=['get'])`. Lê `year`/`month` + `building_id`. Breakdown de **despesa** por `Category` (Σ `Bill.amount_total` de bills `active` no mês, agrupado por categoria, com `color`/`name` da `Category`) — donut do dashboard. Decimais string. Cacheado `FINANCE_DASHBOARD_PREFIX`. *(Gráficos são não-blocking no gate; a tabela/JSON é o artefato load-bearing.)*

### URLs (anexar a `finances/urls.py`, S38)
Registrar no router existente: `reserves` → `ReserveViewSet`; `reserve-movements` → `ReserveMovementViewSet`; `income-entries` → `IncomeEntryViewSet`; `condo-month-closes` → `CondoMonthCloseViewSet`. Ações underscore (`monthly_balance`, `by_category`). Rotas finais (exemplos): `GET/POST /api/finances/reserves/`, `POST /api/finances/reserves/{id}/deposit/`, `POST /api/finances/reserves/{id}/withdraw/`, `GET/POST /api/finances/income-entries/`, `GET /api/finances/condo-month-closes/`, `POST /api/finances/condo-month-closes/close/`, `POST /api/finances/condo-month-closes/reopen/`, `GET /api/finances/finance-dashboard/overview/`, `GET /api/finances/finance-dashboard/monthly_balance/`, `GET /api/finances/finance-dashboard/by_category/`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui é **só `freezegun`** (congelar a data p/ `today_sp()`/`is_overdue`/baseline) e **disable throttle** nos testes de API (`override_settings(REST_FRAMEWORK=…)` — fronteira de infra, como `test_rent_calendar_api.py:29-40`). **NUNCA** mockar ORM, managers, `Bill.with_amounts`, `RentScheduleService`, `BillPaymentService`, `CondoBalanceService`, `CacheManager`, signals ou qualquer interno. Banco real via `--reuse-db`; `transaction.atomic()` ao asserir `ValidationError`/`IntegrityError`. Dados via factories. `filterwarnings=error`: zero warnings. **Cache em teste é LocMem** (`configure_test_cache`) → asserir invalidação por efeito observável (probe `finance-dashboard:…` some após escrita), não por mock.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_condo_balance_service.py` (sob `@freeze_time`)

**Resultado de competência (§4.2/§4.5)**
- [ ] `result_of_month` = received_collectible_total + Σ effective_rental_value de cobráveis não pagas + Σ IncomeEntry (por `income_date`) − Σ Bill.amount_total active no mês. Exemplo trabalhado pinado (valores explícitos) batendo na unha.
- [ ] **exclui** bills `suspended`/`deferred`/`canceled` da despesa de competência (design §4.2); IPTU **deferido** não entra.
- [ ] **receita filtrada (§4.5)**: criar um `RentPayment` de lease com **owner setado** (não-cobrável) → **não** entra em `result_of_month` (usa `received_collectible_total`, não `received_total`). Provar que o filtrado o exclui.
- [ ] **Rosa (§4.6)**: lease 850/205 `is_salary_offset=True` → fora de `collectible_leases` (não é receita); a folha da Rosa (`Bill(employee)` com base − abatimento, S41) entra como despesa **uma vez** (o abatimento = `effective_rental_value`); o aluguel **não** é receita nem despesa separada. Asserir que `result_of_month` conta o aluguel da Rosa **zero vezes** como receita e a folha líquida uma vez.

**Variação de caixa (§4.2/§4.3)**
- [ ] `cash_change_of_month` = entradas (received_collectible + IncomeEntry recebida + saque reserva→caixa) − saídas (`PaymentAllocation` funded_from='caixa' + depósito caixa→reserva). Exemplo trabalhado pinado.
- [ ] **pagamento `funded_from='reserve'` NÃO conta como saída de caixa** (§4.3): pagar um bill de 300 via reserva → `cash_change_of_month` inalterado pelo pagamento (debita só a reserva); `reserve_balance` −300.
- [ ] `IncomeEntry` com `income_date` em jan e `received_date`/`is_received` em fev → entra na **competência de jan** e no **caixa de fev** (sem dupla-contagem).

**Reserva sem dupla-contagem (§4.3 — exemplos trabalhados)**
- [ ] **transferência caixa→reserva de R$500**: um `ReserveMovement(deposit, 500)` → `cash_balance` −500, `reserve_balance` +500, **`total_balance` INALTERADO** (zero-sum pinado).
- [ ] reserva→caixa simétrico (saque `bill=null`) → total inalterado.
- [ ] pagamento `funded_from='reserve'` de 300 (via `BillPaymentService.pay`, S44): `Payment(300, reserve)` + `PaymentAllocation(→X, 300)` + `ReserveMovement(withdrawal, 300, bill=X)`; debita **só** a reserva; `Bill.amount_paid` deriva **só** de `PaymentAllocation` (não de `ReserveMovement.bill`).
- [ ] **guarda**: saque > saldo da reserva rejeitado (a guarda vive no `pay`/`withdraw` — S44/serviço; aqui asserir que `reserve_balance` nunca fica negativo no caminho de saldo).
- [ ] ordenação determinística do ledger (`movement_date, id`).

**Caixa condo-scoped ancorado (§4.2)**
- [ ] sem `CondoMonthClose`: `cash_balance` = `FinancialSettings.initial_balance` (0,00, `initial_balance_date=2026-03-01`) + Σ variações dos meses abertos desde o baseline (espelha `_get_starting_balance` :184-211 mas condo-scoped).
- [ ] com `CondoMonthClose(closed, cash_balance_end=X)` no mês anterior: `cash_balance` re-anda **só** a cauda aberta a partir de X (não recomputa o passado fechado).
- [ ] caixa **pode** ficar negativo (não bloqueia — aviso informativo §4.3).

**Saldo total / atrasados (§4.2/§4.4)**
- [ ] `total_balance == cash_balance + reserve_balance`.
- [ ] `overdue_bills_total` = Σ `amount_remaining` de bills `is_overdue=True` (annotation); **não** `amount_total`; deferido/suspenso/cancelado fora; atraso de **aluguel** é figura **separada** (`get_month_stats.overdue_total_fee`), **não** somada.

**Wedge identity (§4.2)**
- [ ] cenário totalmente liquidado e sem transferências de reserva → `cash_change_of_month == result_of_month` exatamente; `overview.wedge_ok=True`, residual `0.00`.
- [ ] cenário com pendências (a-receber + a-pagar) → a identidade fecha (residual `0.00`); os dois KPIs **não divergem silenciosamente**.

**Quantização / estrutural (§18)**
- [ ] somar cru e quantizar só na fronteira: `cash_balance_end` congelado pelo `close` == `cash_balance` on-read no fim do mês (sem off-by-cent).
- [ ] mês sem leases / prédio sem bills → figuras `0.00` coerentes; soft-deleted Bill/Payment/IncomeEntry excluído dos totais; `is_offset` mantém `amount_total>=0`.
- [ ] **virada de mês na TZ SP** (§18): instante UTC já no mês seguinte enquanto SP ainda no mês anterior → `cash_balance(as_of_month=None)` usa o mês de SP via `current_month_sp()`.

#### `tests/unit/test_finances/test_condo_month_close_service.py` (sob `@freeze_time`)
- [ ] `close(year, month)` cria `CondoMonthClose(closed)` com `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out`/`breakdown` corretos (batendo no `CondoBalanceService`); `closed_at=today_sp()`.
- [ ] **cronológico/sem gap (§8)**: `close(M)` com um mês anterior **não** fechado → `ValidationError` PT; fechar em ordem (M−1 depois M) funciona.
- [ ] **já fechado** → `ValidationError` PT (não re-fecha; idempotência explícita).
- [ ] **carry-forward com net≤0 (§4.7/§18)**: `net_result + carregado_in < 0` → `carry_forward_out = min(0, …) < 0`; `carregado_in` do próximo = `carry_forward_out` do anterior. Pinar o fold sequencial.
- [ ] **âncora do fold (§4.7)**: o fold começa no 1º mês com fechamento/atividade, não antes de `rent_tracking_start_date` (2026-06); mês pré-tracking (sem aluguel rastreado + com bill) → **não** acumulado no fold (net isolado, não espúrio).
- [ ] **reopen recomputa cascata (§8)**: fechar M, M+1, M+2 (com net positivo crescente); `reopen(M)` → M vira `open`, e `cash_balance_end`/`net_result`/`carry_forward_out` de M+1/M+2 são **recomputados** a partir do novo baseline (provar que mudaram coerentemente). `reopen` de mês inexistente → `ValidationError` PT.
- [ ] **`assert_open`**: mês `closed` → `ValidationError` PT; mês sem `CondoMonthClose` ou `open` → no-op (não levanta). Asserir que `BillPaymentService.pay` num bill de mês fechado é **bloqueado** (via `assert_open`, S44) — regressão integrada.

#### `tests/integration/test_finances/test_finance_reserve_income_api.py` (throttle off)
- [ ] CRUD `reserves`/`reserve-movements`/`income-entries` (dual serializer: nested read / `_id` write; `amount`/`balance` string Decimal; soft-delete onde aplicável — `IncomeEntry`/`Reserve`/`ReserveMovement` têm SoftDelete; `CondoMonthClose` **não**).
- [ ] `POST reserves/{id}/deposit` → `ReserveMovement(deposit)`; `reserve.balance` +amount; **`total_balance` inalterado** (asserir via `CondoBalanceService` no teste).
- [ ] `POST reserves/{id}/withdraw` com `amount <= reserve_balance` → ok; `amount > reserve_balance` → **400 PT** (guarda negativa); `amount<=0` → 400 PT.
- [ ] `income-entries` filtros `is_received`/`building_id`/date range; `income_date` round-trip.

#### `tests/integration/test_finances/test_finance_monthclose_api.py` (freeze_time + throttle off)
- [ ] `GET condo-month-closes/` lista; `POST close/` (admin) com `year`/`month` válidos → cria; `month` fora de 1–12 → 400 PT.
- [ ] `close` com gap cronológico → 400 PT; já fechado → 400 PT.
- [ ] `POST reopen/` → status `open`; mês inexistente → 400 PT.
- [ ] **bloqueio de write em mês fechado (§18)**: após `close(M)`, `POST bills/{id}/pay` de um bill com `competence_month=M` → **400 PT** (via `assert_open`, S44); `unpay` idem. Reabrir (`reopen`) libera o pagamento.

#### `tests/integration/test_finances/test_finance_balance_dashboard_api.py` (freeze_time + throttle off)
- [ ] `GET finance-dashboard/overview?year=&month=` → KPIs (`result_of_month`/`cash_change_of_month`/`cash_balance`/`reserve_balance`/`total_balance`/`overdue_bills_total`/`rent_overdue`/`wedge_ok`) todos string Decimal (exceto counts/bool); valores batendo no `CondoBalanceService`.
- [ ] `GET monthly_balance?year=` → 12 meses; mês fechado lê do `CondoMonthClose` congelado, aberto computa on-read; `is_closed` correto.
- [ ] `GET by_category?year=&month=` → breakdown de despesa por categoria com `color`/`name`; Decimais string.
- [ ] params inválidos (`month=13`, `year=abc`) → 400 PT.
- [ ] **cache (§11)**: dois GETs de `overview` com a mesma chave servem do cache; uma escrita de `Bill`/`Payment`/`ReserveMovement`/`IncomeEntry` **entre** eles invalida `finance-dashboard*` (probe some) → o 2º GET reflete a mudança. `combined_calendar` (S38) **continua sem cache** (regressão: não quebrar).

**Matriz `FinancialReadOnly`** (pode ficar no `test_finance_reserve_income_api.py` ou arquivo dedicado — espelhar `test_financial_permissions.py:16-58`)
- [ ] não-admin: `GET` em `reserves`/`reserve-movements`/`income-entries`/`condo-month-closes` + `overview`/`monthly_balance`/`by_category` → **200**.
- [ ] não-admin: `POST` em CRUD + ações `deposit`/`withdraw`/`close`/`reopen` → **403**.
- [ ] admin (`is_staff`): os mesmos `POST` passam do gate (≠ 403).
- [ ] anônimo: `GET` em qualquer endpoint → **401**.

> Rodar (devem **falhar** — serviços/serializers/viewsets/urls ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_condo_balance_service.py tests/unit/test_finances/test_condo_month_close_service.py \
>   tests/integration/test_finances/test_finance_reserve_income_api.py tests/integration/test_finances/test_finance_monthclose_api.py \
>   tests/integration/test_finances/test_finance_balance_dashboard_api.py -q
> ```

### 2. GREEN — implementar

1. `finances/services/money.py` (helper `quantize_money`) — **só se a S37/S38 não criou** (verificar; reusar se existe).
2. `finances/services/condo_balance_service.py` — `CondoBalanceService` (consome `received_collectible_total`/`collectible_leases`/`effective_rental_value`/`get_month_stats` da S37, `Bill.with_amounts(today_sp())`, ledger de `ReserveMovement`/`PaymentAllocation`/`IncomeEntry`; baseline do último `CondoMonthClose`). Imports diretos da fonte.
3. `finances/services/condo_month_close_service.py` — `assert_open`/`close`/`reopen` (atômico, `select_for_update`, cronológico, fold/carry-forward, recompute cascata). Consome `CondoBalanceService` (DRY).
4. `finances/serializers.py` — anexar `ReserveSerializer`/`ReserveMovementSerializer`/`IncomeEntrySerializer`/`CondoMonthCloseSerializer` (dual).
5. `finances/viewsets/crud_views.py` — anexar `ReserveViewSet`(+`deposit`/`withdraw`)/`ReserveMovementViewSet`/`IncomeEntryViewSet`/`CondoMonthCloseViewSet`(+`close`/`reopen`).
6. `finances/viewsets/dashboard_views.py` — estender `FinanceDashboardViewSet` com `overview`/`monthly_balance`/`by_category` (`@cache_result(FINANCE_DASHBOARD_PREFIX, …)`).
7. `finances/viewsets/__init__.py` + `finances/urls.py` — exports + registro dos novos viewsets.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_condo_balance_service.py tests/unit/test_finances/test_condo_month_close_service.py tests/integration/test_finances/test_finance_reserve_income_api.py tests/integration/test_finances/test_finance_monthclose_api.py tests/integration/test_finances/test_finance_balance_dashboard_api.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `CondoBalanceService.overview` **consome** `result_of_month`/`cash_change_of_month`/`cash_balance`/`reserve_balance`/`total_balance`/`overdue_bills_total` — não re-deriva nenhuma figura. `CondoMonthCloseService.close` **consome** o `CondoBalanceService` (DRY — o `net_result`/`cash_balance_end` do snapshot é exatamente o do serviço; o teste de "sem off-by-cent" trava isso).
- Baseline ancorado num helper privado nomeado (`_cash_baseline(as_of_month) -> Decimal`) espelhando `_get_starting_balance` (:184-211) mas condo-scoped — função pequena, intenção clara.
- O fold/carry-forward sequencial num helper puro nomeado (`_fold(net_by_month) -> list[…]`) testável isolado — DRY entre `close` e `reopen` (cascata).
- **Quantização só na fronteira** via `quantize_money` (single source) — somatórios internos crus; nenhum serviço quantiza no meio. **Nenhuma** soma de linhas/alocações em Python (tudo via annotation/aggregate ORM).
- A validação `year`/`month` (parse + range 1–12 → 400 PT) **reusa** o helper compartilhado da S38 (`generate_month`/`combined_calendar`) — não duplicar a constante de range.
- Mensagens PT como constantes nomeadas se repetidas (sem magic strings).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_condo_balance_service.py tests/unit/test_finances/test_condo_month_close_service.py \
  tests/integration/test_finances/test_finance_reserve_income_api.py tests/integration/test_finances/test_finance_monthclose_api.py \
  tests/integration/test_finances/test_finance_balance_dashboard_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances/
ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances/
mypy core/ finances/
pyright finances/
```

> **Regressão obrigatória**: rodar os testes de pagamento/calendário/cache da S37/S38/S44 que tocam o `pay()`/`combined_calendar`/invalidação, para garantir que `assert_open` e os novos signals/endpoints não quebraram o legado da feature:
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_payment_service.py tests/integration/test_finances/test_finance_calendar_overdue_api.py tests/unit/test_finances/test_finance_cache_signals.py -q
> ```

---

## Constraints

- **Direção de dependência** (`.claude/rules/architecture.md`): `finances → core`. Serviços importam `RentScheduleService` (`received_collectible_total`/`collectible_leases`/`effective_rental_value`/`get_month_stats`), `Bill.with_amounts`, `today_sp()`/`current_month_sp()` — **nunca** views/serializers. Viewsets → serviços → models; serializers → models (nunca serviços/views). Ações **finas**: zero lógica de negócio na view.
- **Receita só pelo SSOT** (design §4.5, memória do projeto): caixa/net usam `received_collectible_total` (filtrado) — **nunca** `received_total` cru; collectibility/prepaid **só** via `RentScheduleService` (nunca `prepaid_until >= month_start`). **Sem mudança no SSOT de aluguel.**
- **Annotations, não Python** (design §4.4): competência/atrasados via `Bill.objects.with_amounts(today)`; reserva/caixa via aggregate ORM do ledger `ReserveMovement`/`PaymentAllocation`/`IncomeEntry`. **Proibido** somar linhas/alocações em Python.
- **Caixa condo-scoped ancorado** (design §4.2): baseline do último `CondoMonthClose` (`cash_balance_end`), fallback `FinancialSettings.initial_balance` — **distinto** do caixa commingled legado (`MonthSnapshot`); re-anda só a cauda aberta. **Não** usar `MonthSnapshot` para o caixa do condo.
- **Reserva sem dupla-contagem + guarda** (design §4.3): transferência caixa↔reserva é zero-sum no saldo total; `funded_from='reserve'` debita só a reserva (não caixa); `Bill.amount_paid` deriva **só** de `PaymentAllocation`; reserva nunca negativa (guarda no `withdraw`/`pay` — S44). Ledger determinístico (`movement_date, id`).
- **Fold sem termo de reserva** (design §4.7): `carry_forward_out = min(0, net + carregado_in)`; reserva é transferência de caixa, **não** reduz a distribuição/fold.
- **TZ SP única** (design §4): "hoje/mês atual" só via `finances.services.timezone`. Proibido `timezone.now().date()` cru nos serviços do `finances`.
- **Quantização só na fronteira** (design §4): `quantize_money` único; somatórios internos crus; sem off-by-cent entre `overview` e `CondoMonthClose` congelado.
- **`assert_open` é o único guard de mês fechado** (design §8): definido aqui, consumido pelo `pay`/`unpay` (S44). **Não** duplicar.
- **Sem Projeção/Simulação (Fase 5 — S47)**, **sem Distribuição por proprietário/donos externos (Fase 6 — S49/S50)**, **sem frontend**. `OwnerDistributionService`/`CondoProjectionService` **consomem** `CondoBalanceService` depois (DRY) — não antecipar.
- **Sem modelos/migração novos**; `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` e o `pay()` reserva são da S44. Sem alterar `core/models.py`/`core/signals.py`/`settings.py`/SSOT de aluguel.
- **`combined_calendar` continua SEM cache** (S38/§11); `overview`/`monthly_balance`/`by_category` usam `@cache_result(FINANCE_DASHBOARD_PREFIX)` (mesma string da S37 — um char de diferença não-invalida).
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código. Tipos completos (mypy strict + pyright strict). `cast(User, request.user)` quando necessário (padrão `web_push_views`).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from decimal import Decimal`, `from django.contrib.auth.models import User`, etc.).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; o único `__init__`/`__all__` é o do pacote `finances/viewsets/`.
- **`DecimalField(12,2)`**; dinheiro serializado como **string**. **`FinancialReadOnly`** em toda rota (auth lê, `is_staff` escreve). **`CustomPageNumberPagination`** em todos os `ModelViewSet`.
- Mensagens ao usuário em **Português** (DRF-shape: `detail`/`error`/field-level); logs/identificadores/enum values/url_path em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/services/condo_balance_service.py` define `CondoBalanceService` com `result_of_month`/`cash_change_of_month`/`cash_balance`/`reserve_balance`/`total_balance`/`overdue_bills_total`/`overview` — receita via `received_collectible_total` (filtrado, nunca cru), competência/atrasados via `with_amounts` (annotation), caixa **condo-scoped ancorado** no último `CondoMonthClose` (fallback `FinancialSettings`), reserva sem dupla-contagem, saldo total, **wedge identity** testada; quantização só na fronteira.
- [ ] `finances/services/condo_month_close_service.py` define `assert_open`/`close`/`reopen` — `close` cronológico (sem gap, rejeita já-fechado), congela `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out`/`breakdown` (= `CondoBalanceService`, sem off-by-cent), fold `carry_forward_out=min(0, net+carregado_in)`, âncora no 1º mês com atividade (≥ `rent_tracking_start_date`); `reopen` recomputa cascata os meses seguintes; `assert_open` é o guard único de mês fechado (consumido pelo `pay`, S44); atômico + `select_for_update`.
- [ ] `received_collectible_total` (S37) **consumido** sem mudança; SSOT de aluguel (`collectible_leases`/`received_total`/`is_prepaid_for_month`) **intacto**.
- [ ] `finances/serializers.py` ganha `ReserveSerializer` (com `balance` read-only string)/`ReserveMovementSerializer`/`IncomeEntrySerializer`/`CondoMonthCloseSerializer` (dual; derivados string read-only); serializers da S38 intactos.
- [ ] `finances/viewsets/crud_views.py` ganha `ReserveViewSet`(+`deposit`/`withdraw` com guarda negativa)/`ReserveMovementViewSet`/`IncomeEntryViewSet`/`CondoMonthCloseViewSet`(+`close`/`reopen`); `FinanceDashboardViewSet` estendido com `overview`/`monthly_balance`/`by_category` (cacheados `FINANCE_DASHBOARD_PREFIX`); `combined_calendar` da S38 segue sem cache; todos `FinancialReadOnly` + `CustomPageNumberPagination`; ações finas delegando aos serviços, erros → 400 DRF-shape PT.
- [ ] `finances/urls.py` registra `reserves`/`reserve-movements`/`income-entries`/`condo-month-closes`; rotas resolvem em `/api/finances/...` com ações underscore (`deposit`/`withdraw`/`close`/`reopen`/`monthly_balance`/`by_category`); registro da S38 intacto.
- [ ] Testes cobrem TODOS os exemplos trabalhados (§4): Rosa (abatimento uma vez, lease 205 fora da receita), transferência caixa↔reserva zero-sum, `funded_from='reserve'` não-saída-de-caixa, wedge fechando; e os §18: reserva (zero-sum/guarda/`bill=null` vs `bill`/ordenação), atrasado (Σ remaining, deferido/suspenso fora), receita/collectibility (ignora externos), fold/fechamento (carry net≤0, âncora pré-tracking, reopen cascata, bloqueio mês fechado), estruturais (mês sem leases, soft-deleted excluído, quantização sem off-by-cent, virada de mês SP); matriz `FinancialReadOnly` (200/403/non-403/401); cache `finance-dashboard*` invalidado.
- [ ] `python -m pytest` (os 5 arquivos + regressão S37/S38/S44) passa 100%; **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum modelo/migração novo; nenhum `CondoProjectionService`/`CondoSimulationService`/`OwnerDistributionService`/distribuição por proprietário; nenhum frontend; `BillPaymentService.pay`/SSOT de aluguel/`core` intactos; `combined_calendar` segue sem cache; `daily-control` legado não wirado.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_condo_balance_service.py tests/unit/test_finances/test_condo_month_close_service.py \
     tests/integration/test_finances/test_finance_reserve_income_api.py tests/integration/test_finances/test_finance_monthclose_api.py \
     tests/integration/test_finances/test_finance_balance_dashboard_api.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_bill_payment_service.py tests/integration/test_finances/test_finance_calendar_overdue_api.py tests/unit/test_finances/test_finance_cache_signals.py -q  # regressão
   ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances/
   ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances/
   mypy core/ finances/
   pyright finances/
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 45 (status **concluída**) na tabela da feature Condomínio Finance (fecha a Fase 4 — backend).
   - **Arquivos Criados**: `finances/services/condo_balance_service.py`, `finances/services/condo_month_close_service.py`, `tests/unit/test_finances/{test_condo_balance_service,test_condo_month_close_service}.py`, `tests/integration/test_finances/{test_finance_reserve_income_api,test_finance_monthclose_api,test_finance_balance_dashboard_api}.py` (+ `finances/services/money.py` se criado aqui).
   - **Arquivos Modificados**: `finances/serializers.py` (4 serializers Fase 4), `finances/viewsets/crud_views.py` (4 viewsets + ações), `finances/viewsets/dashboard_views.py` (overview/monthly_balance/by_category), `finances/viewsets/__init__.py`, `finances/urls.py`.
   - **Nota**: "Fase 4 fechada — `CondoBalanceService` (resultado competência, variação de caixa, caixa condo-scoped ancorado no último `CondoMonthClose` + fallback `FinancialSettings`, reserva sem dupla-contagem, saldo total, atrasados via annotation, wedge identity), `CondoMonthCloseService` (close cronológico/sem gap + fold carry-forward + âncora pré-tracking; reopen recomputa cascata; `assert_open` = guard único de mês fechado consumido pelo `pay` da S44). API: `reserves`(+deposit/withdraw guarda negativa)/`reserve-movements`/`income-entries`/`condo-month-closes`(+close/reopen) + dashboard `overview`/`monthly_balance`/`by_category` (cacheados `finance-dashboard`). `received_collectible_total` consumido sem mudança no SSOT. **Projeção/simulação = Fase 5 (S47, consome `result_of_month`/baseline); distribuição por proprietário/donos externos = Fase 6 (S49/S50, consome `result_of_month`).**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`):
   ```
   feat(finances): add CondoBalanceService + CondoMonthCloseService + reserve/income/month-close API + balance dashboard endpoints

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **46 — Frontend Fase 4** (KPIs Caixa/Reserva/Resultado/Atrasados/Saldo total + Reserva + Receita avulsa + Fechamento mensal); depois a **S47** entrega `CondoProjectionService`+`CondoSimulationService`+`cash-flow/{projection,simulate}` (Fase 5) — consome `CondoBalanceService.result_of_month`/baseline e o `Installment`/embutido (S41) para a projeção computada; usa os prefixos `finance-cash-flow`/`finance-projection` (S37) no `@cache_result`. A S46 **não** re-deriva net/caixa.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`CondoBalanceService`** (`finances/services/condo_balance_service.py`): `result_of_month(year, month, building_id=None) -> Decimal` (competência; receita filtrada via `received_collectible_total` + esperado de cobráveis + `IncomeEntry` por `income_date`; despesa = Σ `Bill.amount_total` active no mês); `cash_change_of_month(...)`; `cash_balance(as_of_month=None, building_id=None)` (ancorado no último `CondoMonthClose`); `reserve_balance(...)`; `total_balance(...)`; `overdue_bills_total(...)`; `overview(year, month, building_id=None) -> dict`. **Fase 5 (S46)** consome `result_of_month`/`cash_balance` (baseline) — **não** re-deriva. **Fase 6 (S49/S50)** consome `result_of_month` no `OwnerDistributionService` (household = condomínio). Receita **sempre** filtrada por collectibility; nunca `received_total` cru.
- **`CondoMonthCloseService`** (`finances/services/condo_month_close_service.py`): `assert_open(competence_month) -> None` (guard único de mês fechado — `BillPaymentService.pay`/`unpay` da S44 chamam-no); `close(year, month, user=None) -> CondoMonthClose` (cronológico/sem gap, congela `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out`/`breakdown`, fold `carry_forward_out=min(0, net+carregado_in)`); `reopen(year, month, user=None) -> CondoMonthClose` (recomputa cascata os meses fechados seguintes). O `CondoMonthClose` congelado é o **baseline** do caixa/fold (consumido pelo `cash_balance` e pela Fase 5/6).
- **API Fase 4** (`/api/finances/...`): `reserves` (+ `reserves/{id}/deposit` `{amount, movement_date?}`, `reserves/{id}/withdraw` `{amount, movement_date?}` — guarda `amount>reserve_balance` → 400 PT), `reserve-movements`, `income-entries`, `condo-month-closes` (+ `condo-month-closes/close` `{year, month}`, `condo-month-closes/reopen` `{year, month}`). Dashboard: `finance-dashboard/overview?year=&month=&building_id=` (KPIs Caixa/Reserva/Resultado/Atrasados/Saldo total + `rent_overdue` + `wedge_ok`, cacheado `finance-dashboard`), `finance-dashboard/monthly_balance?year=` (12 meses, `is_closed`), `finance-dashboard/by_category?year=&month=` (donut despesa por categoria). Todos `FinancialReadOnly`, paginados, Decimal string. **Frontend da Fase 4** consome esses shapes verbatim.
- **`quantize_money`** (helper único de fronteira, em `finances/services/money.py` se criado aqui ou reusado da S37/S38): toda figura de dinheiro exposta/congelada passa por ele (`ROUND_HALF_UP`, `0.01`). Garante `overview` == `CondoMonthClose` congelado (sem off-by-cent). **Fase 5/6** usam o mesmo helper.
- **Wedge identity** (design §4.2, fixado por teste aqui): `cash_change_of_month == result_of_month` em mês totalmente liquidado sem transferências de reserva; `overview.wedge_ok` reporta a reconciliação. Fases seguintes podem confiar que os dois KPIs não divergem silenciosamente.
