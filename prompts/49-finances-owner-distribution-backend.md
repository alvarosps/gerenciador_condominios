# Sessão 49 — Backend: `OwnerDistributionService` + agregação por proprietário + endpoint `finance-dashboard/by_owner`

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46 → 47 → 48 → **49 → 50** (esta abre a **Fase 6 — Distribuição por proprietário**, camada de **serviço + API**)
> Esta sessão entrega a **distribuição do resultado** do condomínio: `OwnerDistributionService.compute(year, month)` (**resultado do mês = renda do household Raul & Célia = o próprio condomínio**; fold com carry-forward ancorado, §4.7; consome `CondoBalanceService.result_of_month` — DRY, **não** re-deriva net) + a **agregação de donos externos** (Tiago/Alvaro: owner → Σ `effective_rental_value` de `displayable_leases`, **só exibição**) + o endpoint `finance-dashboard/by_owner`. **Sem frontend (S50); sem `CondominiumOwnership`/rateio individual/ponte versionada (futuro).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.5 receita filtrada, §4.7 distribuição + carry-forward (fold, on-read, ancorado) — INTEIRA, §6 receita do condomínio e proprietários (não-invasivo) — INTEIRA, §7 mapeamento (Tiago/Alvaro, Raul & Célia), §8 `OwnerDistributionService`/`CondoBalanceService`, §9 API `finance-dashboard/by_owner`, §10 tela 1 (resultado do household + seção de externos), §11 cache, §13 migrações, §14 Fase 6, §17 apêndice PROD, §18 edge-cases "Distribuição" + "Receita/collectibility" + "Fold/fechamento" + "Estruturais")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Prompt da S45 (`CondoBalanceService.result_of_month` + `CondoMonthCloseService` + `_fold`/carry-forward + `quantize_money` + baseline ancorado — contratos cross-session no rodapé, CONSUMIR verbatim)**: `@prompts/45-finances-balance-close-services-api.md`
- **Prompt da S44 (modelo `CondoMonthClose` — `net_result`/`carry_forward_out`≤0/`status`/`breakdown` que ancoram o fold)**: `@prompts/44-finances-reserve-income-close-models.md`
- **Prompt da S38 (serializers/viewsets/API + `FinanceDashboardViewSet` + helper de validação `year`/`month` + `finances/urls.py`)**: `@prompts/38-finances-serializers-viewsets-calendar.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

> **NOTA**: o app `finances/` é construído pelas Sessões 34→48 (parte ainda não no disco). As referências `finances/...` abaixo são **contratos cross-session** (consumir verbatim do `SESSION_STATE.md` / dos prompts S37/S44/S45), **não** `file:line` reais. Os exemplares com `file:line` concreto vêm de `core/` (existe no disco) — são o **padrão/forma** a imitar.

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`displayable_leases` (donos externos — `(lease, is_collectible, reason)`; `"owner_repass"` é o caso de Tiago/Alvaro) — CONSUMIR, não recriar** | `core/services/rent_schedule_service.py:194-237` (`displayable_leases(reference_month, building_id=None) -> list[tuple[Lease, bool, str | None]]`; owner-set → `(lease, False, "owner_repass")` :231-232; prepaid/pré-tracking ficam **escondidos**, não aparecem) | **Fonte única** da agregação de donos externos. A seção de externos = `Σ effective_rental_value` dos itens `reason == "owner_repass"`, agrupados por `lease.apartment.owner` (`Person`). **Reusar — zero mudança no SSOT** |
| **`effective_rental_value` (valor por mês, com aumento pendente) — CONSUMIR** | `core/services/rent_schedule_service.py:123-139` (`effective_rental_value(lease, reference_month) -> Decimal`; usa `pending_rental_value`/`pending_rental_value_date`, senão `rental_value`) | O valor agregado por dono externo é Σ deste (NUNCA `rental_value` cru) — espelha a receita do `CondoBalanceService` (DRY) |
| **`collectible_leases` (owner IS NULL = household/condomínio) — só p/ entender a fronteira** | `core/services/rent_schedule_service.py:142-191` (`.exclude(apartment__owner__isnull=False)` :175 + `is_salary_offset` + prepaid + pré-tracking) | A renda do **household (Raul & Célia)** = receita do condomínio = leases `owner=null` = `collectible_leases`. Donos externos (owner setado) **saem** daqui → confirma "externos = só exibição, fora do net". **Não** recriar collectibility |
| **`CondoBalanceService.result_of_month` (net de competência — CONSUMIR, NÃO re-derivar)** | `finances/services/condo_balance_service.py` (S45: `result_of_month(year, month, building_id=None) -> Decimal`; receita filtrada via `received_collectible_total` + esperado de cobráveis + `IncomeEntry`; despesa = Σ `Bill.amount_total` active) | A distribuição do household = `result_of_month` (design §8 explícito: "consome `CondoBalanceService.result_of_month` — sem re-derivar — DRY"). **Proibido** recomputar net/receita/despesa aqui |
| **`CondoMonthClose` congelado + `carry_forward_out`≤0 (âncora do fold) + `_fold` (helper puro da S45) — CONSUMIR** | `finances/services/condo_month_close_service.py` + `finances/models.py` (S44/S45: `CondoMonthClose.status='closed'`/`net_result`/`carry_forward_out`≤0/`breakdown`; helper puro `_fold(net_by_month)` da S45) | O fold da distribuição é o **mesmo** algoritmo do `close` (design §4.7): `disponível[M]=max(0, net[M]+carregado_in[M])`; `carregado_out[M]=min(0, net[M]+carregado_in[M])`; `carregado_in[M+1]=carregado_out[M]`. **Reusar o `_fold` da S45 se exposto**; senão espelhar a fórmula (design §4.7) **sem duplicar** — refator completo (DRY) |
| **`CondoBalanceService.cash_balance`/baseline ancorado + janela pré-tracking (`rent_tracking_start_date`)** | `finances/services/condo_balance_service.py` (S45: baseline do último `CondoMonthClose`) + `core/services/rent_schedule_service.py:73-90` (`rent_tracking_start_month`/`is_month_tracked`) | O fold **começa no 1º mês com fechamento/atividade**, **não antes** de `rent_tracking_start_date` (2026-06). Mês pré-tracking (receita estruturalmente 0) **não** entra no fold (evita net negativo espúrio — design §4.7). **Reusar** `is_month_tracked`, não recriar |
| **Service stateless `@staticmethod`, `Decimal`, retorno PT / log EN** | `core/services/rent_schedule_service.py:61` (classe `RentScheduleService`) + `core/services/financial_dashboard_service.py:125-` (`get_debt_by_person`: loop por entidade, `Coalesce(Sum(...), Decimal("0.00"))`, dict por entidade) | **Estrutura-base** de `OwnerDistributionService` (todos `@staticmethod`, sem estado). A **forma** da agregação por dono externo (loop por `Person`, dict por entidade com `id`/`name`/`total`) espelha `get_debt_by_person` |
| **Helper de quantização único `quantize_money` (fronteira de saída — REUSAR)** | `finances/services/money.py` (S45: `quantize_money(value: Decimal) -> Decimal`, `ROUND_HALF_UP`, `0.01`) | Toda figura exposta pela distribuição passa pelo **mesmo** helper (sem off-by-cent vs `result_of_month`/`overview` — design §4). Somatórios internos crus; só a fronteira quantiza. **Reusar — não duplicar** |
| **Helper TZ único `America/Sao_Paulo` (REUSAR)** | `finances/services/timezone.py` (S34: `today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`) | "Hoje/mês atual" via `current_month_sp()` (settings é UTC — §4/§17). Proibido `timezone.now().date()` cru |
| **`Apartment.owner` FK opcional (`SET_NULL`) → `Person`** | `core/models.py:322-328` (`owner = ForeignKey("Person", null=True, on_delete=SET_NULL, related_name="owned_apartments")`) + `core/models.py:927-960` (`Person`: `name` :928, `is_owner` :932) | O agrupamento de externos é por `lease.apartment.owner` (`Person`). PROD: só `836/101,103`→Tiago (id 2) e `836/200,203`→Alvaro (id 3) têm owner setado; resto `owner=null` (§17) |
| **Bare `ViewSet` read-only + `@action(detail=False)` + validação `year`/`month` 1–12 → 400 PT** | `core/viewsets/financial_dashboard_views.py:24-32` (`overview` delega ao serviço) + `:61-73` (`category_breakdown`: parse `year`/`month`, `ValueError` → 400 PT) | **Exemplar canônico** da ação `by_owner` (estender o `FinanceDashboardViewSet` da S38/S45; **não** recriar). Reusar o **helper de validação `year`/`month`** da S38 (constante de range — `MIN_MONTH`/`MAX_MONTH`/`MONTHS_IN_YEAR`, espelha `core/views.py:42-43`), sem duplicar |
| **`@cache_result` + prefixo `finance-dashboard` (consumir o literal da S37)** | `finances/cache.py` (S37: `FINANCE_DASHBOARD_PREFIX="finance-dashboard"`, `invalidate_finance_caches()`) + `core/cache.py:213-255` (`@cache_result`/`invalidate_pattern`) | `by_owner` usa `@cache_result(key_prefix=FINANCE_DASHBOARD_PREFIX, …)`; a invalidação já existe (S37/S44 invalidam `finance-*`; a S37 estende cross-app Apartment/Lease/RentAdjustment). Um char de diferença no prefixo silenciosamente não-invalida |
| **Registro no router próprio do `finances` + helper de validação `year`/`month`** | `finances/urls.py` (S38: router próprio + `path("api/finances/", include(...))`) + `core/views.py:42-43` (`MIN_MONTH=1`/`MAX_MONTH=12`) + `core/services/cash_flow_service.py` (`MONTHS_IN_YEAR`, importado em `core/viewsets/financial_dashboard_views.py:15`) | `by_owner` é uma `@action` num viewset **já registrado** (`finance-dashboard`) — **não** registra rota nova; só a ação. Reusar a constante de range existente |
| Permission (reuso direto) | `core/permissions.py:107-121` (`FinancialReadOnly`: auth lê, `is_staff` escreve, :114-121) | **`FinancialReadOnly`** no `FinanceDashboardViewSet` (GET `by_owner` para qualquer autenticado). Import direto |
| Pagination (reuso direto, NÃO se aplica a agregação) | `core/pagination.py:7-18` (`CustomPageNumberPagination`, `page_size=20`/`max_page_size=500`) | `by_owner` é agregação **não-paginada** (como `overview`/`category_breakdown`). **Não** paginar |
| **Teste de integração — matriz `FinancialReadOnly` + endpoint backed-by-service (sem mock de internals) + throttle off + freezegun** | `tests/integration/test_financial_permissions.py:16-58` (200/403/non-403/401) + `tests/integration/test_rent_calendar_api.py:1-59` (política :1-10; `_disable_throttling` :29-40; `freeze_time`; CPFs válidos) | Padrão dos testes de API desta sessão: View → Service → Model real, `freeze_time`, throttle off, matriz de permissão |
| Factories `finances`/core (S34/S36/S41/S44 + core) | `tests/factories.py` (`make_condominium`/`make_building` S34; `make_bill`/`make_billing_account` S36; `make_income_entry`/`make_condo_month_close` S44) + `make_lease`/`make_apartment`/`make_person`/`make_rent_payment` (core, `tests/factories.py`) | Dados dos testes (donos externos = `make_apartment(owner=make_person(is_owner=True))` + `make_lease`). **Reusar** — não criar objetos manualmente nem factory nova salvo necessidade real (KISS) |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **só `freezegun`** (congelar a data p/ `current_month_sp()`/fold por mês) + throttle off nos testes de API. ORM/serviços/`RentScheduleService`/`CondoBalanceService` reais |

### O que as Sessões 34/36/37/41/44/45 já entregaram (PRÉ-REQUISITO — NÃO recriar)

**Verificar no `SESSION_STATE.md` que a S45 está concluída.** Se não estiver, **PARE** (DEPENDENCY ORDER 45→49).

- **S34** (infra): app `finances` + `FinancesConfig.ready()` + `core.Condominium`(padrão) + `Building.condominium` + helper TZ `finances/services/timezone.py` (`today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`) + gate ampliado + factories base.
- **S37** (serviços de contas + cache): `finances/cache.py` (prefixos `finance-dashboard`/`finance-cash-flow`/`finance-projection` + `invalidate_finance_caches`); `finances/signals.py`; **`RentScheduleService.received_collectible_total`** (aditivo, read); **cross-app NET-NEW** (Apartment/Lease/RentAdjustment/MonthSnapshot invalidam `finance-*`).
- **S38** (API Fase 2): `finances/serializers.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py` (`FinanceDashboardViewSet`), `finances/urls.py` (router próprio + `path("api/finances/", …)`), **helper de validação `year`/`month`** (constante de range).
- **S44** (modelos Fase 4): `CondoMonthClose` (`status`/`net_result`/`cash_balance_end`/`carry_forward_out`≤0/`breakdown`) — âncora do fold.
- **S45** (serviços Fase 4): **`CondoBalanceService`** (`result_of_month`/`cash_balance` ancorado/`overview`/…); **`CondoMonthCloseService`** (`close`/`reopen`/`assert_open`, **fold `_fold`**, carry-forward); **`quantize_money`** (`finances/services/money.py`); dashboard `overview`/`monthly_balance`/`by_category`.

> **Se a S45 não estiver concluída, PARE.** Esta sessão consome `CondoBalanceService.result_of_month`, o `_fold`/carry-forward (`CondoMonthCloseService` da S45), o `CondoMonthClose` congelado, o `quantize_money` e a collectibility/`displayable_leases` do SSOT. **Não** recriar net/fold/baseline/helper de quantização/modelos.

---

## Escopo

### Arquivos a criar
- `finances/services/owner_distribution_service.py` — `OwnerDistributionService` (`compute(year, month)` = distribuição do household via fold ancorado consumindo `result_of_month` + agregação de donos externos via `displayable_leases`).
- `tests/unit/test_finances/test_owner_distribution_service.py` — testes da distribuição (household = condomínio, fold/carry-forward, externos fora do net, agregação por dono + edge-cases §18).
- `tests/integration/test_finances/test_finance_by_owner_api.py` — `finance-dashboard/by_owner` (shape, household + externos, cache, matriz `FinancialReadOnly`).

### Arquivos a modificar
- `finances/viewsets/dashboard_views.py` (S38/S45) — **anexar** a ação `by_owner` ao `FinanceDashboardViewSet` (delegando a `OwnerDistributionService.compute`; `@cache_result(FINANCE_DASHBOARD_PREFIX, …)`). `overview`/`monthly_balance`/`by_category`/`combined_calendar`/`overdue` (S38/S45) **intactos**.
- `finances/urls.py` (S38) — **NÃO** registrar viewset/rota nova (`by_owner` é `@action` num viewset já registrado — `finance-dashboard`). Listado só para deixar explícito que **não** se cria router/registro novo aqui.
- `tests/factories.py` — só se faltar factory para os testes (improvável; core já tem `make_person`/`make_apartment(owner=…)`/`make_lease`). **Não duplicar.**

### NÃO fazer (pertence a outras sessões)
- **Sem frontend** — cards "por proprietário", "resultado do household (Raul & Célia)", seção informativa de donos externos, hooks `use-finance-by-owner`, query-keys, Zod, formatters TZ-safe — é a **Sessão 50** (frontend da Fase 6). **Nada em `frontend/`.** A S50 consome o shape de `by_owner` **verbatim**.
- **Sem `CondominiumOwnership` / rateio individual / ponte versionada** (design §13/§15, decisão travada #13/#14) — Raul & Célia **não existem como `Person`** (§17) e a renda é do **household único** (= o próprio condomínio), **não** rateada por sócio. **Nenhum** modelo/migração/campo novo; nenhuma "ponte" (`contract_version`) para o futuro app pessoal. Isso é explicitamente **futuro** (§15).
- **Sem re-derivar net/receita/despesa/competência** — `result_of_month`/`cash_balance`/baseline/`_fold` são da **S45**. A distribuição do household **delega** a `result_of_month` (DRY — design §8). **Proibido** recomputar essas figuras aqui.
- **Sem mudar o SSOT de aluguel / o income** (design §6, memória do projeto): a receita do household = `collectible_leases` (`owner=null`) e a agregação de externos = `displayable_leases` (`owner_repass`) — **zero mudança** no `RentScheduleService`/`RentPayment`/`Apartment.owner`. Collectibility/prepaid/tracking **só** via `RentScheduleService` (`displayable_leases`/`collectible_leases`/`is_month_tracked`/`effective_rental_value`); **nunca** `prepaid_until >= month_start` cru, **nunca** `received_total`/`rental_value` cru.
- **Sem consumir a projeção da Fase 5** (`CondoProjectionService`) — a distribuição é do **mês de competência** (passado/atual), consome `CondoBalanceService.result_of_month`/`CondoMonthClose`, **não** a projeção futura (design §18 "Distribuição": Fase 6 consome `result_of_month`, **não** a projeção).
- **Sem alterar `CondoMonthCloseService.close`/`reopen`** (S45) — o `close` já congela `carry_forward_out` (§4.7). O `OwnerDistributionService` **lê** o fold (consome `_fold`/o `carry_forward_out` congelado); **não** re-fecha mês nem altera o algoritmo do `close`.
- **Sem modelos/migração/serializer novo** — `by_owner` retorna um dict agregado (sem ModelSerializer; como `overview`/`by_category`). **Sem** novo modelo. **Sem** tocar `core/models.py`/`core/signals.py`/`settings.py`.

---

## Especificação

> Serviço stateless em `finances/services/`, todos `@staticmethod`. `Decimal` para dinheiro; **somar Decimals crus e quantizar (`quantize_money`, S45 — `ROUND_HALF_UP`/`0.01`) só na fronteira de saída/agregado**, idêntico em todo serviço que re-deriva a mesma figura (design §4 — sem off-by-cent entre dashboard, fechamento e distribuição). "Hoje/mês atual" **sempre** via `finances.services.timezone.current_month_sp()`. Direção: o serviço importa de `finances.services.{timezone,money,condo_balance_service,condo_month_close_service}`, `finances.models` (`CondoMonthClose`), `core.services.rent_schedule_service`, `core.models` (`Person`) — **nunca** views/serializers. Mensagens ao usuário em **PT**, logs/identificadores em **EN**.

### `OwnerDistributionService` (design §4.7/§6/§8)

Service stateless, `@staticmethod`. **Resultado do mês = renda do household Raul & Célia (= o próprio condomínio)**; fold com carry-forward ancorado; donos externos = só exibição.

```python
from datetime import date
from decimal import Decimal
from typing import Any

class OwnerDistributionService:

    @staticmethod
    def compute(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Distribuição do resultado do mês por proprietário (design §4.7/§6).

        Estrutura (todos os Decimais como STRING via quantize_money na fronteira):
          {
            year, month,
            household: {                       # Raul & Célia = o próprio condomínio (renda do household)
              name: "Raul & Célia",            # rótulo do household (constante nomeada, NÃO Person — eles não existem como Person, §17)
              result_of_month: str,            # = CondoBalanceService.result_of_month(year, month, building_id)  (DRY — NÃO re-deriva)
              carried_in: str,                 # carregado_in[M] do fold ancorado (carry_forward_out do mês fechado anterior; <= 0)
              available: str,                  # max(0, result_of_month + carried_in)            (design §4.7 — distribuível)
              carried_out: str,                # min(0, result_of_month + carried_in)  (<= 0)     (carrega p/ o próximo mês)
            },
            external_owners: [                 # SÓ EXIBIÇÃO — fora do net/caixa/distribuição (design §4.7/§6)
              { owner_id, owner_name, leases_count, rent_total: str },   # Tiago / Alvaro
              ...
            ],
            external_total: str,               # Σ rent_total dos externos (só exibição)
          }

        REGRAS PINADAS:
        - household.result_of_month = CondoBalanceService.result_of_month(year, month, building_id) — DRY, consome, NÃO recomputa.
        - FOLD ANCORADO (design §4.7): carried_in[M] = carry_forward_out do ÚLTIMO CondoMonthClose 'closed'
          anterior a M (<= 0). Mês sem fechamento anterior ⇒ carried_in = 0.00. available = max(0, net+carried_in);
          carried_out = min(0, net+carried_in). SEM termo de reserva no fold (reserva é transferência de caixa,
          NÃO reduz a distribuição — design §4.7). REUSAR o _fold da S45 se exposto; senão espelhar a fórmula sem duplicar.
        - JANELA PRÉ-TRACKING (design §4.7): se o mês não é rastreado (RentScheduleService.is_month_tracked(year, month)
          False — antes de rent_tracking_start_date 2026-06), o household tem receita estruturalmente 0; o mês NÃO acumula
          net negativo espúrio no fold (net isolado / fora da janela). Pinar por teste.
        - EXTERNOS (design §6, só exibição): agregar RentScheduleService.displayable_leases(date(year, month, 1), building_id)
          filtrando reason == 'owner_repass'; agrupar por lease.apartment.owner (Person); para cada dono
          rent_total = Σ effective_rental_value(lease, date(year,month,1)). NUNCA entram em household/net/result_of_month
          (já saem por collectible_leases). owner_name = Person.name.
        """
```

### Fold ancorado — `carried_in` (design §4.7, DRY com S45)

- `carried_in[M]` é o `carry_forward_out` (≤ 0) do **último `CondoMonthClose` `status='closed'`** com `reference_month < date(year, month, 1)` (o mês fechado **imediatamente** anterior na cadeia). Mês sem nenhum fechamento anterior ⇒ `carried_in = Decimal("0.00")`.
- **DRY obrigatório:** o cálculo `available = max(0, net + carried_in)` / `carried_out = min(0, net + carried_in)` é **exatamente** a fórmula do fold do `CondoMonthCloseService.close` (S45). **Reusar o `_fold`/o helper de fold da S45 se ele estiver exposto** (import direto). Se a S45 deixou o fold **encapsulado** no `close` (não reusável), **extrair** um helper puro nomeado (ex.: `finances/services/condo_month_close_service.py` `fold_step(net, carried_in) -> tuple[available, carried_out]`) e fazer **ambos** (`close` e `OwnerDistributionService`) consumirem — refator completo, todos os consumidores atualizados (design-principles: DRY/no partial refactoring). **Não** duplicar a expressão `max(0, …)`/`min(0, …)` em dois lugares.
- **Sem termo de reserva no fold** (design §4.7): a reserva é transferência caixa↔reserva; **não** reduz `available`/`carried_out`. Travar por teste (cenário com depósito de reserva no mês não muda a distribuição do household).

### Externos = só exibição (design §6)

- A agregação de externos **lê** `RentScheduleService.displayable_leases(date(year, month, 1), building_id)` e considera **só** os itens cujo `reason == "owner_repass"` (Tiago/Alvaro). `salary_offset` (Rosa) **não** é externo (não tem owner; é tratado na folha — §4.6) — **não** entra na seção de externos.
- Agrupar por `lease.apartment.owner` (`Person`): `owner_id` = `owner.pk`, `owner_name` = `owner.name`, `leases_count` = nº de leases daquele dono, `rent_total` = Σ `effective_rental_value(lease, date(year,month,1))`.
- **Invariante pinado (§4.5/§4.7/§18):** nenhum lease com `owner` setado entra em `household.result_of_month` (sai por `collectible_leases`). Os externos são **estritamente exibição** — `external_total` **não** soma em `household.available`/`net`/caixa. Travar por teste.

### `name` do household (constante nomeada)

`household.name = "Raul & Célia"` é um **rótulo de exibição** (Raul e Célia **não existem como `Person`** — §17). Defini-lo como **constante nomeada** (ex.: `_HOUSEHOLD_NAME = "Raul & Célia"`) — sem magic string. O household **não** é um `Person`/FK; é o próprio condomínio (decisão travada #13).

---

## API (design §9)

Base `/api/finances/...` (router próprio do `finances`, S38). `by_owner` é uma `@action(detail=False, methods=['get'])` **no `FinanceDashboardViewSet`** (bare `ViewSet` + `FinancialReadOnly`, já registrado como `finance-dashboard` na S38). Decimal **string**; validação PT; agregação **não-paginada**.

### Ação (anexar a `FinanceDashboardViewSet`, S38/S45 — `finances/viewsets/dashboard_views.py`)
- **`by_owner`** — `@action(detail=False, methods=['get'])`. Lê `year`/`month` (default mês atual SP via `current_month_sp()`; range 1–12 → 400 PT, **reusando o helper de validação `year`/`month` da S38**) e `building_id` (int opcional → 400 PT se não-int). Delega a `OwnerDistributionService.compute(year, month, building_id)`. **Cacheado** via `@cache_result(key_prefix=FINANCE_DASHBOARD_PREFIX, …)` (chave inclui `year`/`month`/`building_id`; invalidação já existe — S37/S44 invalidam `finance-*`, incl. cross-app Apartment/Lease/owner). View **fina**: parse/validação → 400 PT DRF-shape; lógica no serviço. Retorna o dict de `compute` (`household` + `external_owners` + `external_total`).

### URLs (NÃO modificar `finances/urls.py`)
`finance-dashboard` já está registrado (S38). `by_owner` é uma ação underscore → rota final: `GET /api/finances/finance-dashboard/by_owner/`. **Não** registrar router/viewset novo.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui é **só `freezegun`** (congelar a data p/ `current_month_sp()`/fold por mês) e **disable throttle** nos testes de API (`override_settings(REST_FRAMEWORK=…)` — fronteira de infra, como `test_rent_calendar_api.py:29-40`). **NUNCA** mockar ORM, managers, `RentScheduleService`, `CondoBalanceService`, `CondoMonthCloseService`, `quantize_money`, `CacheManager`, signals ou qualquer interno. Banco real via `--reuse-db`; `transaction.atomic()` ao asserir erros. Dados via factories. `filterwarnings=error`: zero warnings. **Cache em teste é LocMem** (`configure_test_cache`) → asserir invalidação por efeito observável (probe `finance-dashboard:…` some após escrita), não por mock.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_owner_distribution_service.py` (sob `@freeze_time`)

**Household = condomínio + `result_of_month` consumido (§4.7/§6/§8 — DRY)**
- [ ] `compute(year, month)["household"]["result_of_month"]` == `CondoBalanceService.result_of_month(year, month)` **exatamente** (string, via `quantize_money` — sem off-by-cent). Exemplo trabalhado pinado (valores explícitos) batendo na unha. Provar que a distribuição **consome** o net (não recomputa): criar receita/despesa reais e asserir igualdade com `result_of_month`.
- [ ] `household.name == "Raul & Célia"` (rótulo constante; **não** é `Person`).

**Fold + carry-forward ancorado (§4.7/§18 "Fold/fechamento")**
- [ ] `carried_in` = `carry_forward_out` (≤0) do **último `CondoMonthClose` fechado** anterior; `available = max(0, net + carried_in)`; `carried_out = min(0, net + carried_in)`. Exemplo pinado.
- [ ] **carry com net≤0 (§4.7)**: `net + carried_in < 0` → `available == "0.00"` e `carried_out < 0` (= `net + carried_in`). Mês sem fechamento anterior → `carried_in == "0.00"`.
- [ ] **carga sequencial**: `carried_out` de M alimenta `carried_in` de M+1 — fechar M (via `CondoMonthCloseService.close`, S45) e computar M+1 → `carried_in[M+1] == carry_forward_out[M]`. Pinar a cadeia.
- [ ] **sem termo de reserva no fold (§4.7)**: um `ReserveMovement(deposit)` no mês (transferência caixa→reserva) **não** muda `household.available`/`carried_out` (reserva não reduz a distribuição). Asserir igualdade com e sem o depósito.
- [ ] **janela pré-tracking (§4.7/§18)**: mês **antes** de `rent_tracking_start_date` (2026-06; `is_month_tracked` False) → household receita 0; o mês **não** acumula net negativo espúrio no fold (net isolado / fora da janela — design §4.7). Pinar explicitamente (mês pré-tracking com um bill → não vira `carried_out` espúrio que contamine jun).

**Donos externos = só exibição (§6/§18 "Distribuição")**
- [ ] **agregação por dono**: dois leases owner=Tiago + um lease owner=Alvaro → `external_owners` tem 2 entradas (`owner_id`/`owner_name`/`leases_count`/`rent_total`); `rent_total` = Σ `effective_rental_value` por dono; `external_total` = Σ de todos. Valores pinados (espelha PROD: 836/101,103→Tiago, 836/200,203→Alvaro).
- [ ] **externos fora do net (§4.5/§4.7)**: criar um `RentPayment` de lease owner-set → **não** entra em `household.result_of_month` (sai por `collectible_leases`); `external_total` **não** soma em `household.available`/`carried_out`/`net`. Provar exclusão.
- [ ] **`effective_rental_value` (aumento pendente)**: lease owner-set com `pending_rental_value` em vigor no mês → `rent_total` usa o valor pendente, não `rental_value` cru.
- [ ] **salary-offset NÃO é externo (§4.6)**: lease `is_salary_offset=True` (Rosa, sem owner) → **não** aparece em `external_owners` (não tem owner; é folha). Asserir ausência.
- [ ] **mês pré-tracking esconde externos**: mês antes do tracking → `displayable_leases` retorna `[]` → `external_owners == []`, `external_total == "0.00"` (consistente com `displayable_leases` escondendo pré-tracking).

**Quantização / estrutural (§18)**
- [ ] somar cru e quantizar só na fronteira: figuras de `compute` quantizadas via `quantize_money`; sem off-by-cent entre `household.result_of_month` e `CondoBalanceService.result_of_month`/`overview`.
- [ ] **prédio sem leases / mês sem atividade**: `result_of_month` coerente, `external_owners == []`, `external_total == "0.00"`, `available`/`carried_out` coerentes.
- [ ] soft-deleted Apartment/Lease/owner excluído da agregação de externos (manager padrão já exclui — confirmar via `displayable_leases`).
- [ ] **`building_id` filtra**: `compute(year, month, building_id=<836>)` restringe `result_of_month` e os externos ao prédio (lease de outro prédio fora).

#### `tests/integration/test_finances/test_finance_by_owner_api.py` (freeze_time + throttle off)
- [ ] `GET finance-dashboard/by_owner?year=&month=` → `{ household:{name, result_of_month, carried_in, available, carried_out}, external_owners:[{owner_id, owner_name, leases_count, rent_total}], external_total }`; Decimais **string**; valores batendo no `OwnerDistributionService.compute`.
- [ ] default sem params → mês atual SP (`current_month_sp()`); `month=13`/`year=abc`/`building_id=abc` → 400 PT (DRF-shape).
- [ ] **household = condomínio + externos separados**: cenário com leases `owner=null` (household) + leases owner=Tiago/Alvaro (externos) → `household.result_of_month` reflete só os `owner=null`; `external_owners` lista Tiago/Alvaro; `external_total` **não** entra no household.
- [ ] **cache (§11)**: dois GETs de `by_owner` com a mesma `year`/`month`/`building_id` servem do cache; uma escrita que muda owner/lease/bill **entre** eles invalida `finance-dashboard*` (probe some — cross-app Apartment/Lease da S37) → o 2º GET reflete a mudança.
- [ ] **matriz `FinancialReadOnly`** (espelhar `test_financial_permissions.py:16-58`): não-admin `GET by_owner` → **200**; anônimo `GET by_owner` → **401**. (`by_owner` é GET-only; não há write — documentar que não há caso 403 de write nesta ação.)

> Rodar (devem **falhar** — serviço/ação/url ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_owner_distribution_service.py tests/integration/test_finances/test_finance_by_owner_api.py -q
> ```

### 2. GREEN — implementar

1. `finances/services/owner_distribution_service.py` — `OwnerDistributionService.compute` (consome `CondoBalanceService.result_of_month` da S45; `carried_in` do último `CondoMonthClose` fechado anterior; fold via `_fold`/`fold_step` da S45 — **reusar ou extrair p/ DRY**; externos via `RentScheduleService.displayable_leases` filtrando `owner_repass` + `effective_rental_value`; `is_month_tracked` p/ pré-tracking; `quantize_money` na fronteira; `current_month_sp()`). Imports diretos da fonte. `_HOUSEHOLD_NAME` constante.
2. Se necessário (S45 não expôs o fold reusável): extrair `fold_step(net, carried_in) -> tuple[Decimal, Decimal]` em `finances/services/condo_month_close_service.py`, atualizar o `close` (S45) a consumi-lo, e o `OwnerDistributionService` também — **refator completo** (DRY).
3. `finances/viewsets/dashboard_views.py` — anexar a ação `by_owner` ao `FinanceDashboardViewSet` (`@cache_result(FINANCE_DASHBOARD_PREFIX, …)` + validação `year`/`month`/`building_id` reusando o helper da S38). `combined_calendar`/`overview`/`monthly_balance`/`by_category`/`overdue` **intactos**.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_owner_distribution_service.py tests/integration/test_finances/test_finance_by_owner_api.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `OwnerDistributionService.compute` **consome** `CondoBalanceService.result_of_month` — **não** re-deriva net/receita/despesa. O teste "household.result_of_month == result_of_month" trava isso.
- **Fold num ponto único** (design §4.7): `available = max(0, net + carried_in)`/`carried_out = min(0, net + carried_in)` é o **mesmo** helper do `CondoMonthCloseService.close` (S45). Reusar/extrair `fold_step`/`_fold` — uma definição, ambos os consumidores atualizados (sem ramo duplicado).
- **Agregação de externos num helper puro nomeado** (ex.: `_external_owners(reference_month, building_id) -> list[dict]`) consumindo `displayable_leases`/`effective_rental_value` — função pequena, intenção clara; sem `rental_value` cru.
- **Quantização só na fronteira** via `quantize_money` (single source S45); somatórios internos crus; nenhum serviço quantiza no meio.
- A validação `year`/`month` (parse + range 1–12 → 400 PT) **reusa** o helper compartilhado da S38 (não duplicar a constante de range `MIN_MONTH`/`MAX_MONTH`/`MONTHS_IN_YEAR`).
- `_HOUSEHOLD_NAME` e mensagens PT como constantes nomeadas (sem magic strings).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_owner_distribution_service.py tests/integration/test_finances/test_finance_by_owner_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances/
ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances/
mypy core/ finances/
pyright finances/
```

> **Regressão obrigatória** (não quebrar o que já existe no `finances`): se o fold da S45 foi extraído/reusado, rodar os testes de fechamento/saldo da S45 e os de cache para garantir que o `close`/dashboard continuam verdes:
> ```bash
> python -m pytest tests/unit/test_finances/test_condo_month_close_service.py tests/unit/test_finances/test_condo_balance_service.py \
>   tests/integration/test_finances/test_finance_balance_dashboard_api.py tests/unit/test_finances/test_finance_cache_signals.py -q
> ```

---

## Constraints

- **Direção de dependência** (`.claude/rules/architecture.md`): `finances → core`. O serviço importa `CondoBalanceService`/`CondoMonthCloseService`/`quantize_money`/`timezone` (finances), `RentScheduleService` (core), `CondoMonthClose` (finances.models), `Person` (core.models) — **nunca** views/serializers. Viewset → serviço; ação **fina**: zero lógica de negócio na view.
- **Consome, não re-deriva** (DRY — design §8/§14): `household.result_of_month` = `CondoBalanceService.result_of_month`; o fold = o `_fold`/`fold_step` da S45 (reusar/extrair). **Proibido** recomputar net/receita/despesa/competência aqui.
- **Household = condomínio** (decisão travada #13): resultado do mês = renda do household Raul & Célia (= o próprio condomínio); **não** rateia por sócio; Raul & Célia **não** são `Person` (rótulo constante). **Sem `CondominiumOwnership`/ponte versionada** (futuro §15).
- **Externos = só exibição** (design §6): agregação owner→Σ `effective_rental_value` de `displayable_leases` (`owner_repass`); **fora** de net/caixa/distribuição; `external_total` nunca soma em `household.available`.
- **Sem termo de reserva no fold** (design §4.7): `carried_out = min(0, net + carried_in)`; reserva é transferência de caixa, **não** reduz a distribuição.
- **Janela pré-tracking** (design §4.7): mês não rastreado (`is_month_tracked` False, antes de `rent_tracking_start_date`) → receita 0; **não** acumula net negativo espúrio no fold.
- **Receita só pelo SSOT** (design §6, memória do projeto): household via `collectible_leases` (owner=null); externos via `displayable_leases` (`owner_repass`); valor via `effective_rental_value`; tracking via `is_month_tracked` — **nunca** `prepaid_until >= month_start` cru, **nunca** `received_total`/`rental_value` cru. **Sem mudança no SSOT/income/owner.**
- **TZ SP única** (design §4): "hoje/mês atual" só via `finances.services.timezone`. Proibido `timezone.now().date()` cru.
- **Quantização só na fronteira** (design §4): `quantize_money` único (S45); somatórios internos crus; sem off-by-cent entre `by_owner`, `overview` e `CondoMonthClose` congelado.
- **Cache** (design §11): `by_owner` usa `@cache_result(FINANCE_DASHBOARD_PREFIX)` (mesma string da S37 — um char de diferença não-invalida); invalidação já existe (S37/S44, incl. cross-app Apartment/Lease/owner).
- **Sem frontend (S50)**, **sem `CondominiumOwnership`/rateio individual/ponte versionada (futuro)**, **sem modelos/migração/serializer novo**, **sem consumir a projeção da Fase 5**, **sem alterar `CondoMonthCloseService.close`/`reopen`** (salvo a extração DRY do `fold_step`, com todos os consumidores atualizados).
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código. Tipos completos (mypy strict + pyright strict). `cast(User, request.user)` se necessário (padrão `web_push_views`).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from decimal import Decimal`, `from typing import Any`).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; o único `__init__`/`__all__` é o do pacote `finances/viewsets/` (não muda nesta sessão — `by_owner` é ação num viewset já exportado).
- **`DecimalField(12,2)`**; dinheiro serializado como **string**. **`FinancialReadOnly`** na rota; agregação **não-paginada**. Mensagens ao usuário em **Português** (DRF-shape: `error`/`errors`/field-level); logs/identificadores/url_path em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/services/owner_distribution_service.py` define `OwnerDistributionService.compute(year, month, building_id=None) -> dict` — `household` (`name="Raul & Célia"` constante, `result_of_month` = `CondoBalanceService.result_of_month` consumido sem re-derivar, `carried_in`/`available`/`carried_out` via fold ancorado §4.7), `external_owners` (agregação owner→Σ `effective_rental_value` de `displayable_leases`/`owner_repass`, só exibição) e `external_total`; quantização só na fronteira; pré-tracking sem net espúrio.
- [ ] O fold é **DRY** com o `CondoMonthCloseService.close` (S45) — `_fold`/`fold_step` reusado ou extraído (todos os consumidores atualizados; sem `max(0,…)`/`min(0,…)` duplicado).
- [ ] `result_of_month`/`_fold`/`quantize_money` (S45) e `displayable_leases`/`effective_rental_value`/`is_month_tracked` (SSOT) **consumidos sem mudança**; net/fold **não** re-derivados; SSOT de aluguel/income/owner intacto; **sem** `CondominiumOwnership`/rateio individual/ponte versionada.
- [ ] `finances/viewsets/dashboard_views.py` ganha a ação `by_owner` no `FinanceDashboardViewSet` (cacheada `FINANCE_DASHBOARD_PREFIX` + validação `year`/`month`/`building_id` → 400 PT reusando o helper da S38); `overview`/`monthly_balance`/`by_category`/`combined_calendar`/`overdue` intactos; `FinancialReadOnly`; ação fina delegando ao serviço; `finances/urls.py` **não** alterado (rota `GET /api/finances/finance-dashboard/by_owner/`).
- [ ] Testes cobrem TODOS os edge-cases §18 desta fase: **household = condomínio** (= `result_of_month`), **externos fora do net** (só exibição, `external_total` não soma no household), **per-owner aggregation** (Tiago vs Alvaro de `displayable_leases`/`effective_rental_value`); + fold carry net≤0/cadeia sequencial/sem termo de reserva, janela pré-tracking (sem net espúrio + externos escondidos), salary-offset não é externo, `effective_rental_value` (aumento pendente), `building_id` filtra, quantização sem off-by-cent, prédio sem leases, soft-deleted excluído; matriz `FinancialReadOnly` (200/401); cache `finance-dashboard*` invalidado (cross-app owner/lease).
- [ ] `python -m pytest` (os 2 arquivos + regressão S45 se o fold foi extraído) passa 100%; **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum modelo/migração/serializer novo; nenhum `CondominiumOwnership`/rateio individual/ponte versionada; nenhum frontend; `CondoBalanceService`/`CondoMonthCloseService.close`/`reopen` (salvo extração DRY do fold)/SSOT de aluguel/`core` intactos; projeção da Fase 5 não consumida; `combined_calendar` segue sem cache.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_owner_distribution_service.py tests/integration/test_finances/test_finance_by_owner_api.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_condo_month_close_service.py tests/unit/test_finances/test_condo_balance_service.py \
     tests/integration/test_finances/test_finance_balance_dashboard_api.py tests/unit/test_finances/test_finance_cache_signals.py -q  # regressão S45 (se fold extraído)
   ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances/
   ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances/
   mypy core/ finances/
   pyright finances/
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 49 (status **concluída**) na tabela da feature Condomínio Finance (abre a Fase 6 — backend).
   - **Arquivos Criados**: `finances/services/owner_distribution_service.py`, `tests/unit/test_finances/test_owner_distribution_service.py`, `tests/integration/test_finances/test_finance_by_owner_api.py`.
   - **Arquivos Modificados**: `finances/viewsets/dashboard_views.py` (ação `by_owner`); + `finances/services/condo_month_close_service.py` **só se** o `fold_step`/`_fold` precisou ser extraído p/ DRY (com `close` atualizado).
   - **Nota**: "Fase 6 backend — `OwnerDistributionService.compute` (resultado do mês = renda do household Raul & Célia = o próprio condomínio, via `CondoBalanceService.result_of_month` consumido — DRY; fold com carry-forward ancorado no último `CondoMonthClose` fechado, §4.7, **sem termo de reserva**, janela pré-tracking sem net espúrio; agregação de donos externos Tiago/Alvaro owner→Σ `effective_rental_value` de `displayable_leases`/`owner_repass`, **só exibição**, fora do net). API: `finance-dashboard/by_owner` (cacheado `finance-dashboard`). Sem `CondominiumOwnership`/rateio individual/ponte versionada (futuro); SSOT de aluguel/income/owner intacto; `quantize_money` único (sem off-by-cent). **Frontend = S50 (cards por proprietário + resultado do household + seção informativa de externos; consome `by_owner` verbatim).**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`):
   ```
   feat(finances): add OwnerDistributionService + by_owner dashboard endpoint (household distribution + external owners, Phase 6 backend)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **50 — Frontend: distribuição por proprietário** (Fase 6 frontend) — consome `GET /api/finances/finance-dashboard/by_owner?year=&month=&building_id=` **verbatim** (shape abaixo); cards "Resultado do mês (household Raul & Célia)" + seção informativa de donos externos (Tiago/Alvaro); TanStack Query v5 (`useQuery` + `placeholderData: keepPreviousData`, **não** `useSuspenseQuery`); query-keys centrais; formatters TZ-safe; `is_staff` gating onde aplicável. A S50 **não** altera o backend.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`OwnerDistributionService`** (`finances/services/owner_distribution_service.py`): `compute(year, month, building_id=None) -> dict`. Shape: `{ year, month, household: { name: "Raul & Célia", result_of_month: str, carried_in: str, available: str, carried_out: str }, external_owners: [{ owner_id: int, owner_name: str, leases_count: int, rent_total: str }], external_total: str }` (Decimais **string** via `quantize_money`). `household.result_of_month` = `CondoBalanceService.result_of_month` (consumido, DRY); fold ancorado (§4.7) `available=max(0, net+carried_in)`/`carried_out=min(0, net+carried_in)` (sem termo de reserva; pré-tracking sem net espúrio); externos = `displayable_leases`(`owner_repass`) agregados por `Apartment.owner`, **só exibição** (fora do net). **Não** consome a projeção (Fase 5); **não** cria `CondominiumOwnership`/rateio.
- **API Fase 6** (`/api/finances/...`, `FinancialReadOnly`): `GET finance-dashboard/by_owner?year=&month=&building_id=` → `OwnerDistributionService.compute` (cacheado `finance-dashboard`; default mês atual SP; `year`/`month` 1–12 validados; `building_id` opcional). GET-only (sem write/403). **Frontend da Fase 6 (S50)** consome esse shape verbatim.
- **Fold reusável** (se extraído): `fold_step(net, carried_in) -> tuple[available, carried_out]` (ou o `_fold` da S45) é **fonte única** da fórmula de carry-forward (design §4.7), consumida por `CondoMonthCloseService.close` (S45) **e** `OwnerDistributionService.compute`. Qualquer mudança no fold é uma única edição.
- **Invariantes pinadas por teste aqui**: household = condomínio (= `result_of_month`, sem re-derivar); externos estritamente exibição (`external_total` nunca soma em `household.available`/net/caixa); per-owner aggregation (Tiago vs Alvaro) de `displayable_leases`/`effective_rental_value`; fold sem termo de reserva; janela pré-tracking sem net espúrio; salary-offset não é externo; sem off-by-cent vs `overview`/`CondoMonthClose` congelado (`quantize_money` único). **Sem `CondominiumOwnership`/rateio individual/ponte versionada — futuro (§15).**
