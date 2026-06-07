# Sessão 38 — Backend: serializers + viewsets + API `/api/finances/...` + `CondoCalendarService` + atrasados

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → **38** → 39 → 40 → 41 → … → 50 (fecha a Fase 2 no backend)
> Esta sessão expõe os modelos da S36 e os serviços da S37 pela **API namespaced `/api/finances/...`**: serializers **dual** (nested read / `_id` write), viewsets `ModelViewSet` + `FinancialReadOnly`, as **ações** (`bills/{id}/pay`, `bulk_pay`, `suspend|defer|cancel|reactivate`, `generate_month`, `create_with_lines`), o **`CondoCalendarService.combined_month`** (entradas via `RentScheduleService` + saídas via `Bill`/parcelas por `due_date`, em seções separadas) + o endpoint **`finance-dashboard/combined_calendar` (SEM cache)** e **`finance-dashboard/overdue`** (lista de atrasados via annotation). **Sem frontend (S39/S40). Sem KPIs de dinheiro (Fase 4 — saldo/reserva/caixa).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.1, §4.4, §4.5, §8 — especialmente `CondoCalendarService.combined_month`, §9 API inteira, §11 cache, §12 gate, §18 edge-cases de Fase 2)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md`
- **Prompt da S36 (modelos — contratos cross-session no rodapé)**: `@prompts/36-finances-models-bills.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Serializer dual (nested read + `_id` write, FK opcional `allow_null`)** | `core/serializers.py:772-846` (`ExpenseSerializer`: `person`/`person_id` :773-780, `building`/`building_id` :789-796, `category`/`category_id` :797-804, nested list read `installments` :805, `Meta.fields`/`read_only_fields` :810-846) | **Exemplar canônico** dos serializers desta sessão. Copiar a forma: `<fk> = XSerializer(read_only=True)` + `<fk>_id = PrimaryKeyRelatedField(queryset=…, source='<fk>', write_only=True, required=False, allow_null=True)` |
| Serializer simples (`fields="__all__"`) | `core/serializers.py:45-48` (`BuildingSerializer`) | Forma mínima — usar para `BillSkip` (sem FK nested além de `billing_account`) e como base de `CategorySerializer` |
| Serializer com `SerializerMethodField` (read-only derivado) | `core/serializers.py:806-808` (`remaining_installments`/`total_paid`/`total_remaining` em `ExpenseSerializer`) | Padrão para expor `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue` (annotations da S36) **como string Decimal** read-only no `BillSerializer` |
| **`ModelViewSet` + `FinancialReadOnly` + `get_queryset` com filtros por query param** | `core/viewsets/financial_views.py:56-90` (`PersonViewSet` :56-73, `CreditCardViewSet` :76-90) | Forma-base dos CRUD viewsets: `serializer_class`, `permission_classes=[FinancialReadOnly]`, `get_queryset` com `select_related`/`prefetch_related` + filtros `query_params` |
| `ModelViewSet` com `queryset`/`serializer_class` enxutos | `core/viewsets/financial_views.py:93-96` (`ExpenseCategoryViewSet`) | Forma mínima de registro (`CategoryViewSet`) |
| `ExpenseViewSet.get_queryset` (filtros id + bool + date range) | `core/viewsets/financial_views.py:137-170` (`get_queryset` :141-154; `_apply_*` :156-170) | Estrutura de filtros (`building_id`, `category_id`, `competence_month`, `lifecycle_state`, date range) extraídos em helpers privados |
| **`@action(detail=True, methods=['post'])` delegando a serviço + 400/404 PT** | `core/views.py:429-486` (`change_due_date`: leitura de `request.data` :439, validação obrigatório → 400 :441-444, `try/except ValueError/ValidationError` → 400 :474-480, delega ao serviço :450-458) | **Exemplar canônico** das ações `pay`/`suspend`/`defer`/`cancel`/`reactivate`/`generate_month`/`create_with_lines`: view fina, lógica no serviço, erros DRF-shape PT |
| `@action(detail=True, methods=['get'])` (instance action) | `core/views.py:402-403` (`calculate_late_fee`) | Forma de `@action(detail=True)`; `pk` é `int | None` |
| **Bare `ViewSet` + `@action(detail=False)` (dashboard read-only, agregação por serviço)** | `core/viewsets/financial_dashboard_views.py:24-87` (`FinancialDashboardViewSet`: `permission_classes=[FinancialReadOnly]` :27; `overview` :29-32 delega ao serviço; `category_breakdown` :61-73 lê `year`/`month` com 400 em `ValueError`) | **Exemplar canônico** do `FinanceDashboardViewSet` (bare, sem model) com `combined_calendar`/`overdue` |
| `@action(detail=False)` com validação `year`/`month` + range 1–12 | `core/viewsets/financial_dashboard_views.py:155-173` (`monthly` do `CashFlowViewSet`, range check :166-170) | Validação canônica de `year`/`month` para `combined_calendar`/`overdue` (reusar constante de range, não números mágicos) |
| Pagination | `core/pagination.py:7-18` (`CustomPageNumberPagination`: `page_size=20`, `page_size_query_param='page_size'`, `max_page_size=500`) | **Reusar** em todos os `ModelViewSet` desta sessão (`pagination_class = CustomPageNumberPagination`) |
| `FinancialReadOnly` (auth lê, `is_staff` escreve) | `core/permissions.py:107-121` | A permission de **toda** rota desta sessão (CRUD + ações + dashboard). **Import direto**, não inline |
| **Registro de router + `include`** | `core/urls.py:46-82` (router :46; `router.register(r"expenses", ExpenseViewSet, basename="expenses")` :62; `path("api/", include(router.urls))` :136) | Forma de registro. **Esta sessão cria `finances/urls.py`** (router próprio do `finances`) e adiciona `path("api/finances/", include("finances.urls"))` em `condominios_manager/urls.py:67` |
| `include("core.urls")` no projeto | `condominios_manager/urls.py:67` (`path("", include("core.urls"))`) | Onde anexar `path("api/finances/", include("finances.urls"))` (ver §URLs) |
| Export de viewsets via `__init__` | `core/viewsets/__init__.py:12-64` (imports diretos + `__all__`) | Forma do `finances/viewsets/__init__.py` (se a S37 não o criou; senão **anexar**) |
| **Service stateless (calendário/stats por mês)** | `core/services/rent_schedule_service.py:240-307` (`get_month_schedule` :240; estrutura `{year, month, days:[{day,date,weekday,items:[…]}], stats}`) | Forma e shape do dia do **`CondoCalendarService.combined_month`**; a porção de **entradas** reusa este service (DRY) |
| `RentScheduleService.collectible_leases` / `displayable_leases` / `received_collectible_total` | `core/services/rent_schedule_service.py:142,194` (+ `received_collectible_total` additivo da S37) | Fonte das **entradas** do calendário combinado e do sub-total de atraso de aluguel. **NÃO** reimplementar cobrabilidade |
| **Teste de integração — matriz `FinancialReadOnly` (parametrize)** | `tests/integration/test_financial_permissions.py:16-58` (listas de endpoints :16-34; `test_non_admin_cannot_write` 403 :40-43; admin passa do gate :45-49; `test_non_admin_can_read` 200 :51-54; `test_unauthenticated` 401 :56-58) | **Exemplar canônico** da matriz de permissão dos endpoints `/api/finances/...` |
| **Teste de integração — endpoint backed-by-service (sem mock de internals) + freezegun + disable throttle** | `tests/integration/test_rent_calendar_api.py:1-59` (docstring de política :1-10; `_REST_FRAMEWORK_NO_THROTTLE`/`_disable_throttling` :29-40; CPFs válidos :44-46; URLs :48-49) | **Exemplar canônico** do teste de `combined_calendar`/`overdue`/`pay`: View → Service → Model real, `freeze_time`, throttle off |
| Factories `finances` (S36) | `tests/factories.py` (`make_finance_category`, `make_billing_account`, `make_bill`, `make_bill_line_item`, `make_bill_skip`, `make_payment`, `make_payment_allocation`) | Reusar nos testes desta sessão; **NÃO** criar objetos manualmente |
| Fixtures de client autenticado | `tests/conftest.py` (`authenticated_api_client` = admin/`is_staff`; `regular_authenticated_api_client` = não-admin; `api_client` = anônimo) — usados em `test_financial_permissions.py` | Reusar; **NÃO** criar novas fixtures de auth |

### O que as Sessões 36 e 37 já entregaram (PRÉ-REQUISITO — NÃO recriar)

**Verificar no `SESSION_STATE.md` que S36 e S37 estão concluídas.** Se qualquer uma não estiver, **PARE** (DEPENDENCY ORDER 36→37→38).

- **S36** — `finances/models.py`: `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`; enums `BillBehavior` (`one_time`/`recurring`/`installment`), `BillLifecycleState` (`active`/`suspended`/`deferred`/`canceled`), `BillingAccountState` (`active`/`suspended`/`deferred`/`ended`), `FundedFrom` (`caixa`/`reserve`); **`Bill.objects.with_amounts(today: date)`** anotando `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue` (Sum-subquery, **NÃO** property). `Bill` tem **só** `billing_account` como FK de fonte (`installment` = S41, `employee` = S44). Migração + RLS.
- **S37** — `finances/services/`: `BillGenerationService.ensure_month_bills(year, month)` (idempotente, race-safe, seed/atrasado); `BillService.create_with_lines(...)` (cria `Bill` + `BillLineItem`s no serviço); `BillPaymentService.pay(bill, payment_date, amount=None, funded_from='caixa')` (parcial, over-allocation rejeitada, bloqueio de mês fechado — `CondoMonthClose` não existe ainda; o bloqueio é no-op até a Fase 4, **a S37 define o ponto de extensão**); **helper TZ único `America/Sao_Paulo`** (S34) que **todos** os serviços do `finances` usam para "hoje/mês atual"; **`RentScheduleService.received_collectible_total`** (additivo, read). `finances/signals.py` + bloco de prefixos `finance-dashboard`/`finance-cash-flow`/`finance-projection` (wiring base da S34/S37).

> **Decisão pinada — `CondoCalendarService` é DESTA sessão (S38), não da S37.** O design (§8) lista `CondoCalendarService.combined_month` entre os serviços, mas ele é **consumido só pelo endpoint** `combined_calendar` (camada API). Para manter a Fase 2 coesa e evitar service órfão, **`CondoCalendarService` é criado aqui** (§Especificação). Se a S37 já o criou (verificar), **não recriar** — apenas wirar o endpoint e cobrir o gap de teste; reportar a divergência no `SESSION_STATE.md`.

---

## Escopo

### Arquivos a criar
- `finances/serializers.py` — `CategorySerializer`, `BillingAccountSerializer`, `BillSerializer`, `BillLineItemSerializer`, `BillSkipSerializer`, `PaymentSerializer` (dual: nested read / `_id` write; `amount_*` read-only string Decimal).
- `finances/viewsets/__init__.py` — exports dos viewsets (se a S37 não criou o pacote `finances/viewsets/`; senão anexar).
- `finances/viewsets/crud_views.py` — `CategoryViewSet`, `BillingAccountViewSet`, `BillViewSet` (+ ações), `BillSkipViewSet`, `PaymentViewSet` (`ModelViewSet` + `FinancialReadOnly` + `CustomPageNumberPagination`).
- `finances/viewsets/dashboard_views.py` — `FinanceDashboardViewSet` (bare `ViewSet` + `FinancialReadOnly`): ações `combined_calendar` (SEM cache) e `overdue`.
- `finances/services/condo_calendar_service.py` — `CondoCalendarService.combined_month(...)` (se não criado pela S37).
- `finances/urls.py` — `DefaultRouter` próprio do `finances` + registro dos viewsets (CRUD + `finance-dashboard`).
- `tests/integration/test_finances/__init__.py` — se ainda não existir.
- `tests/integration/test_finances/test_finance_crud_api.py` — CRUD + filtros + paginação + dual serializer + soft-delete.
- `tests/integration/test_finances/test_finance_bill_actions.py` — ações `pay`/`bulk_pay`/`suspend`/`defer`/`cancel`/`reactivate`/`generate_month`/`create_with_lines`.
- `tests/integration/test_finances/test_finance_calendar_overdue_api.py` — `combined_calendar` (seções entradas/saídas) + `overdue` (lista + sub-total) + sem-cache.
- `tests/integration/test_finances/test_finance_permissions.py` — matriz `FinancialReadOnly` (read 200 / write 403 não-admin / write não-403 admin / 401 anônimo).
- `tests/unit/test_finances/test_condo_calendar_service.py` — unit do `CondoCalendarService.combined_month` (sob `@freeze_time`), se o service for criado aqui.

### Arquivos a modificar
- `condominios_manager/urls.py` — adicionar `path("api/finances/", include("finances.urls"))` (após `path("", include("core.urls"))` em `:67`). Demais rotas **intactas**.
- `finances/viewsets/__init__.py` — anexar os novos viewsets ao `__all__` (se já existir).

### NÃO fazer (pertence a outras sessões)
- **Nenhum frontend** (hooks `use-finance-*`, query-keys, schemas Zod, páginas, componentes, Recharts) — **Sessões 39 (hooks/calendário) e 40 (telas)**. Nada em `frontend/`.
- **Nenhum KPI de dinheiro** (Caixa / Reserva / Resultado do mês / Saldo total) — **Fase 4** (`CondoBalanceService`, `Reserve`/`ReserveMovement`, `CondoMonthClose`). `combined_calendar`/`overdue` exibem **só** entradas/saídas e atrasados (derivável de `Bill`), **sem** saldo/caixa/reserva.
- **Nenhum endpoint** de `installment-plans`/`installments`/`employees`/`income-entries`/`reserves`/`reserve-movements`/`condo-month-closes` (modelos/serviços de Fases 3/4 — **S41+/S44+**). E **nenhuma** ação `convert_deferred`/`deposit|withdraw`/`close|reopen`.
- **Nenhuma** ação `finance-dashboard/{overview,monthly_balance,by_owner,by_category}` (Fases 4/6). Só `combined_calendar` + `overdue` nesta sessão.
- **Não** criar/alterar modelos (`finances/models.py`) nem migração — é S36 (+S41/S44 para `Bill.installment`/`employee`).
- **Não** criar/alterar serviços de pagamento/geração (`BillPaymentService`/`BillGenerationService`/`BillService`) — é S37. Esta sessão **só os chama** das ações.
- **Não** adicionar receivers cross-app de cache (`Apartment`/`Lease`/`RentAdjustment`/`MonthSnapshot` → `finance-*`) — é a sessão de cache (Fase 2/§11) se ainda não feita pela S34/S37; **não** nesta. O `combined_calendar` é **explicitamente sem cache** (design §11).
- **Não** wirar o legado `DailyControlService`/`daily-control` no novo dashboard (design §10/§15 — o calendário novo supera o legado; não wirar os dois).

---

## Especificação

> Convenções (design §9): base **`/api/finances/...`** (namespace próprio, router no `finances/urls.py`). `ModelViewSet` + `FinancialReadOnly` (autenticado lê, `is_staff` escreve); dashboard = bare `ViewSet` + `FinancialReadOnly`. `CustomPageNumberPagination`. Serializers **dual** (nested read / `_id` write). **Decimal serializado como string**. Validação/mensagens ao usuário em **PT**; logs/identificadores em **EN**. `competence_month`/`reference_month` = **1º dia do mês** (a normalização já está no `clean()` do model — S36; o serializer não re-normaliza, mas testa o round-trip). View **fina**: toda lógica nos serviços (S37) — a ação só lê `request.data`, valida o shape (400 PT) e delega.

### 1. Serializers dual (`finances/serializers.py`)

Espelhar `ExpenseSerializer` (`core/serializers.py:772-846`). FKs read = nested; write = `<fk>_id` (`PrimaryKeyRelatedField(queryset=…, source='<fk>', write_only=True, required=False, allow_null=True)` quando a FK é nullable). Importar os serializers nested da própria `finances/serializers.py` (ordem de definição: `CategorySerializer` antes dos que o aninham). **Sem re-export.**

- **`CategorySerializer`** — `condominium`/`condominium_id`, `parent`/`parent_id` (self-FK nullable), `name`, `color`, `sort_order`. `fields` explícito + `read_only_fields=['id','created_at','updated_at']`.
- **`BillingAccountSerializer`** — `condominium`/`condominium_id`, `building`/`building_id` (nullable), `category`/`category_id` (nullable), `name`, `external_identifier`, `description`, `default_due_day`, `expected_amount` (Decimal string), `lifecycle_state`, `tracking_start_month`, `end_date`, `notes`.
- **`BillLineItemSerializer`** — `category`/`category_id` (nullable), `description`, `amount` (Decimal string ≥0), `is_offset`. Usado **read-only nested** dentro de `BillSerializer` (write de linhas é via `bills/create_with_lines` — §Ações). Não aceitar `bill_id` no write nested (o serviço dono cria as linhas).
- **`BillSerializer`** — `condominium`/`condominium_id`, `building`/`building_id` (nullable), `category`/`category_id` (nullable), `competence_month`, `due_date`, `issue_date`, `description`, `external_identifier`, `behavior`, `billing_account`/`billing_account_id` (nullable), `lifecycle_state`, `notes`, `line_items` (nested read-only `BillLineItemSerializer(many=True, read_only=True)`), e os **derivados read-only via `SerializerMethodField`** lidos da annotation `with_amounts(today)`: `amount_total`, `amount_paid`, `amount_remaining` (Decimal **string**), `payment_status` (`open|partial|paid`), `is_overdue` (bool). **CRÍTICO**: o `BillViewSet.get_queryset` DEVE retornar `Bill.objects.with_amounts(today=…)` para que os `SerializerMethodField` leiam `getattr(obj, 'amount_total')` etc. **sem N+1**; o `today` vem do helper TZ SP (S34) — nunca `timezone.now().date()` cru (design §4 TZ). Se a annotation não estiver presente (ex.: instância recém-`save`), o método retorna `"0.00"`/`open`/`False` (defensivo) — mas o caminho de list/retrieve sempre anota.
- **`BillSkipSerializer`** — `billing_account`/`billing_account_id`, `reference_month`. (BillSkip sem soft-delete; serializer simples.)
- **`PaymentSerializer`** — `condominium`/`condominium_id`, `payment_date`, `amount` (Decimal string >0), `method`, `funded_from`, `reference`, `notes`, `allocations` (nested read-only: `bill`/`amount` por alocação). **Write de Payment é via `bills/{id}/pay`/`bulk_pay`** (o serviço cria `Payment`+`PaymentAllocation` com a guarda de over-allocation) — `PaymentViewSet` expõe `create`/`update` padrão também (admin), mas a forma canônica de pagar é a ação. Documentar.

### 2. Viewsets CRUD (`finances/viewsets/crud_views.py`)

Todos `ModelViewSet`, `permission_classes=[FinancialReadOnly]`, `pagination_class=CustomPageNumberPagination`, `serializer_class` correspondente. `get_queryset` com `select_related`/`prefetch_related` e filtros por `query_params` (espelhar `ExpenseViewSet.get_queryset`).

- **`CategoryViewSet`** — `queryset=Category.objects.select_related('parent','condominium').all()`; filtros `parent_id`, `condominium_id`.
- **`BillingAccountViewSet`** — `select_related('building','category','condominium')`; filtros `building_id`, `category_id`, `lifecycle_state`.
- **`BillViewSet`** — `get_queryset = Bill.objects.with_amounts(today).select_related('building','category','billing_account').prefetch_related('line_items','allocations')`; filtros `building_id`, `category_id`, `competence_month` (data 1º dia), `lifecycle_state`, `behavior`, `payment_status` (filtra sobre a annotation), `is_overdue` (filtra sobre a annotation). **Ações** abaixo.
- **`BillSkipViewSet`** — `select_related('billing_account')`; filtros `billing_account_id`, `reference_month`.
- **`PaymentViewSet`** — `select_related('condominium').prefetch_related('allocations','allocations__bill')`; filtros `funded_from`, date range (`payment_date`).

### 3. Ações do `BillViewSet` (design §9 — view fina, lógica no serviço S37)

Cada ação: ler `request.data`/`request.query_params`, validar shape (400 DRF-shape PT — `{"detail": "..."}` ou `{"error": "..."}` coerente com o exemplar `change_due_date`), delegar ao serviço, serializar a resposta com `BillSerializer` (re-anotado). Erros do serviço (`ValidationError` PT, guarda de over-allocation, mês fechado) → 400.

- **`pay`** — `@action(detail=True, methods=['post'])`. Lê `payment_date` (obrigatório, ISO), `amount` (opcional — `None` = total), `funded_from` (default `caixa`). Delega a `BillPaymentService.pay(bill, payment_date, amount, funded_from)`. Retorna o `Bill` re-anotado (com `amount_paid`/`payment_status` atualizados). Over-allocation → 400 PT. **`funded_from=reserve`** com saldo insuficiente → 400 PT (a guarda vive no serviço; a ação só repassa o erro). **Mês fechado** (Fase 4) → 400 PT (no-op até a Fase 4 existir).
- **`bulk_pay`** — `@action(detail=False, methods=['post'])`. Lê `bill_ids` (lista, obrigatória), `payment_date`, `funded_from`. Para cada id, delega a `BillPaymentService.pay(bill, payment_date, amount=None, funded_from=…)` **dentro de um `transaction.atomic`** (all-or-nothing). Retorna a lista de bills re-anotados. Lista vazia/ausente → 400 PT.
- **`suspend` / `defer` / `cancel` / `reactivate`** — `@action(detail=True, methods=['post'])`. Cada uma seta `Bill.lifecycle_state` para `suspended`/`deferred`/`canceled`/`active` respectivamente, via um método de serviço (S37; se a S37 não expôs um `BillLifecycleService`/método, **criar um helper mínimo de transição no serviço da S37 NÃO é desta sessão** — então a transição é feita por `BillService` se já existir, ou um método fino `BillService.set_lifecycle_state(bill, state)` **que pertence à S37**; se ausente, reportar gap e usar `bill.lifecycle_state = …; bill.full_clean(); bill.save(update_fields=['lifecycle_state','updated_by'])` na **camada de serviço**, nunca na view). `reactivate` só é válido a partir de `suspended`/`deferred` (não de `canceled` — terminal); transição inválida → 400 PT. Retorna o `Bill` re-anotado (após suspender, `is_overdue` vira `False`).
- **`generate_month`** — `@action(detail=False, methods=['post'])`. Lê `year`/`month` (obrigatórios, inteiros; range 1–12 → 400 PT). Delega a `BillGenerationService.ensure_month_bills(year, month)` (idempotente). Retorna `{ "created": <n>, "bills": [<BillSerializer…>] }` (ou o shape que a S37 retornar — **consumir verbatim** o retorno do serviço, não re-derivar).
- **`create_with_lines`** — `@action(detail=False, methods=['post'])`. Lê o payload `{ bill: {...campos…}, line_items: [{description, amount, is_offset, category_id}, …] }`. Valida com os serializers (sem `save` — só `is_valid`) e delega a `BillService.create_with_lines(...)` (o serviço cria `Bill`+`BillLineItem`s atômico). Retorna o `Bill` re-anotado, 201. Payload inválido → 400 PT.

### 4. `CondoCalendarService.combined_month(...)` (`finances/services/condo_calendar_service.py`, design §8)

Service stateless, `@staticmethod`. Shape espelhando `RentScheduleService.get_month_schedule` (`core/services/rent_schedule_service.py:240-307`), mas com **duas seções por dia**: entradas (aluguéis) e saídas (contas a pagar). "Hoje/mês atual" via **helper TZ SP** (S34) — nunca `timezone.now()` cru.

```python
from datetime import date
from typing import Any
from core.services.rent_schedule_service import RentScheduleService
from finances.models import Bill
# helper TZ SP da S34 (import direto da fonte)

class CondoCalendarService:
    @staticmethod
    def combined_month(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Calendário combinado do mês:
        {
          year, month, today (iso),
          days: [
            { day, date (iso), weekday (PT),
              rent_entries: [ <item de RentScheduleService.get_month_schedule por dia> ],
              bill_exits:  [ { bill_id, description, building_number|None, category|None,
                               amount_total (str), amount_remaining (str), payment_status,
                               due_date (iso), is_overdue, lifecycle_state } ] },
            ...
          ],
        }
        - ENTRADAS: reusar RentScheduleService.get_month_schedule(year, month, building_id)
          (DRY — NÃO reimplementar cobrabilidade/clamp). Os itens de aluguel já vêm por dia.
        - SAÍDAS: Bill.objects.with_amounts(today).filter(
              competence_month no mês OU due_date no mês — DECIDIR: agrupar por DUE_DATE no mês,
              design §8 'Bill/parcelas com due_date no dia') excluindo lifecycle_state ∈
              {suspended, deferred, canceled} da exibição de saídas a pagar? — NÃO: exibir todas
              as ativas; suspended/deferred/canceled aparecem rotuladas mas NÃO contam como overdue
              (a annotation já garante is_overdue=False para ≠ active). building_id filtra
              building_id (e bills de nível-condomínio building=null aparecem quando building_id
              é None). Agrupar por due_date.day (clamp já está no due_date do bill, S36/S37).
        - SEM cache (design §11): o método é puro/on-read; o ENDPOINT é que declara no_cache.
        - SEM KPIs de dinheiro (saldo/caixa/reserva) — Fase 4. Só listas por dia.
        Decimais como string; datas ISO. Mês/dia via helper TZ SP."""
```

> **Decisão de agrupamento (pinar e travar por teste):** as **saídas** são agrupadas pelo **dia do `due_date`** do `Bill` (design §8 "Bills/parcelas com due_date no dia"), restritas ao mês `(year, month)` por `due_date__year/__month`. As **entradas** vêm prontas de `get_month_schedule` (agrupadas pelo vencimento clampado do aluguel). Documentar a escolha de "due_date no mês" vs "competence_month no mês" no docstring — para esta fase, **`due_date` no mês** (é um calendário de vencimentos).

### 5. Endpoints do dashboard (`finances/viewsets/dashboard_views.py`, bare `ViewSet`)

`FinanceDashboardViewSet(viewsets.ViewSet)`, `permission_classes=[FinancialReadOnly]`. Espelhar `FinancialDashboardViewSet` (`core/viewsets/financial_dashboard_views.py:24-87`).

- **`combined_calendar`** — `@action(detail=False, methods=['get'])`. Lê `year`/`month` (default = mês atual via helper TZ SP; 400 PT se não-inteiros; range 1–12 → 400 PT), `building_id` opcional. Delega a `CondoCalendarService.combined_month(year, month, building_id)`. **SEM cache** (design §11 — calendário combinado tem duas metades invalidadas por gatilhos diferentes; deixar sem cache ou TTL curto). **NÃO** decorar com `@cache_result`; **NÃO** ler/gravar `CacheManager`. Comentário no método explicando o porquê (design §11).
- **`overdue`** — `@action(detail=False, methods=['get'])`. Lê `building_id` opcional. Retorna a **lista de atrasados de contas** (design §4.4): `Bill.objects.with_amounts(today).filter(is_overdue=True)` (annotation: `due_date < today` E `amount_remaining > 0` E `lifecycle_state='active'`), serializada com `BillSerializer`, **ordenada por `due_date`**. Inclui o **sub-total** `overdue_bills_total = Σ amount_remaining` (KPI "Atrasados" = Σ remaining, **não** amount_total — design §4.4) **e** o sub-total separado de **atraso de aluguel** lido de `RentScheduleService.get_month_stats(...)['overdue_total_fee']`/`['overdue_count']` (sub-total separado, design §4.4) — **sem** somar os dois (são figuras distintas: contas vs aluguel). IPTU **deferido/suspenso não entra** (annotation já exclui). Shape: `{ "bills": [...], "overdue_bills_total": "…", "overdue_bills_count": n, "rent_overdue": { "count": …, "total_fee": "…" } }`. Decimais string.

### 6. URLs (`finances/urls.py` + projeto)

`finances/urls.py` cria `DefaultRouter` próprio e registra:
```
finance-categories   → CategoryViewSet
billing-accounts     → BillingAccountViewSet
bills                → BillViewSet
bill-skips           → BillSkipViewSet
payments             → PaymentViewSet
finance-dashboard    → FinanceDashboardViewSet  (basename, bare ViewSet)
```
`urlpatterns = [path("", include(router.urls))]`. No `condominios_manager/urls.py:67`, **após** `path("", include("core.urls"))`, adicionar `path("api/finances/", include("finances.urls"))`. Rotas finais (exemplos): `GET/POST /api/finances/bills/`, `POST /api/finances/bills/{id}/pay/`, `POST /api/finances/bills/bulk_pay/`, `POST /api/finances/bills/{id}/suspend/`, `POST /api/finances/bills/generate_month/`, `POST /api/finances/bills/create_with_lines/`, `GET /api/finances/finance-dashboard/combined_calendar/`, `GET /api/finances/finance-dashboard/overdue/`. Ações custom com **underscore** (`generate_month`, `create_with_lines`, `bulk_pay`, `combined_calendar`) — consistente com `core/urls` (`generate_contract`, `change_due_date`).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. Aqui = **`freezegun`** (relógio) e **disable throttle** (`override_settings(REST_FRAMEWORK=…)` — fronteira de infra, como `test_rent_calendar_api.py:29-40`). **NUNCA** mockar ORM, `BillPaymentService`/`BillGenerationService`/`BillService`/`CondoCalendarService`/`RentScheduleService`, serializers ou managers. Banco real via `--reuse-db`; dados via factories da S36. Exercitar **View → Serializer → Service → Model** de ponta a ponta.

### 1. RED — escrever os testes primeiro

Criar os 4 arquivos de integração + 1 de unit. `@pytest.mark.django_db`, factories da S36, fixtures de client do `conftest`. Cobrir, no mínimo:

**CRUD + filtros + paginação + dual serializer + soft-delete (`test_finance_crud_api.py`)**
- [ ] `GET /api/finances/finance-categories/` lista paginada (`results` array); `POST` (admin) cria com `parent_id`/`condominium_id`; resposta tem `parent` **nested** (read) e não `parent_id`.
- [ ] `GET /api/finances/billing-accounts/?building_id=…&lifecycle_state=active` filtra; `expected_amount` serializado como **string** Decimal.
- [ ] `GET /api/finances/bills/` retorna cada bill com `amount_total`/`amount_paid`/`amount_remaining` **string**, `payment_status ∈ {open,partial,paid}`, `is_overdue` bool, `line_items` nested — **lidos da annotation** (asserir valor exato de um bill com 2 linhas não-offset + 1 offset → `amount_total` correto).
- [ ] `GET /api/finances/bills/?payment_status=partial` e `?is_overdue=true` filtram sobre a annotation.
- [ ] paginação: criar > `page_size` bills, `?page_size=…`/`?page=2` respeitados (`CustomPageNumberPagination`).
- [ ] `POST /api/finances/bills/` (admin) com `building_id`/`category_id`/`billing_account_id` → cria; `competence_month` round-trip dia 1.
- [ ] **soft-delete**: `DELETE /api/finances/bills/{id}/` (admin) soft-deleta; o bill some do `GET` list (manager exclui `is_deleted`); `Bill.all_objects.with_deleted()` ainda o acha (asserção via ORM no teste).
- [ ] `GET /api/finances/payments/` lista com `allocations` nested; filtro `funded_from`.

**Ações (`test_finance_bill_actions.py`)** — usar `freeze_time` onde "hoje" importa
- [ ] `POST bills/{id}/pay` total (`amount` omitido) → `payment_status='paid'`, `amount_remaining='0.00'`; cria `Payment`+`PaymentAllocation` (asserir via ORM).
- [ ] `POST bills/{id}/pay` parcial (`amount` < total) → `payment_status='partial'`, `amount_remaining` correto.
- [ ] **over-allocation rejeitada** (design §4.8): `pay` com `amount` > remaining → **400 PT**, nada criado.
- [ ] `POST bills/bulk_pay` com `bill_ids` paga todos atômico; um id inexistente → 400/404 e **nenhum** pagamento parcial persistido (rollback).
- [ ] `bulk_pay` com `bill_ids` vazio/ausente → 400 PT.
- [ ] `POST bills/{id}/suspend` → `lifecycle_state='suspended'`, e o bill (mesmo vencido/não pago) passa a `is_overdue=false` (design §4.4); `defer`/`cancel` análogos; `reactivate` de `suspended`→`active`.
- [ ] `reactivate` de `canceled` (terminal) → **400 PT** (transição inválida).
- [ ] `POST bills/generate_month` com `year`/`month` válidos → idempotente (chamar 2× não duplica — asserir count via ORM); `month` fora de 1–12 → 400 PT.
- [ ] `POST bills/create_with_lines` com `{bill, line_items}` → 201, cria `Bill`+N `BillLineItem`s atômico; `amount_total` reflete offset; payload inválido (linha com `amount` negativo) → 400 PT, nada criado.
- [ ] **§18 datas/geração**: `generate_month` respeitando `BillSkip` (mês pulado não gera) e suspensão (conta suspensa não gera) — via `BillingAccount`/`BillSkip` factory.

**Calendário combinado + atrasados (`test_finance_calendar_overdue_api.py`)** — `freeze_time` + throttle off
- [ ] `GET finance-dashboard/combined_calendar?year=&month=` → shape `{year, month, today, days:[…]}`; um dia com `rent_entries` (aluguel cobrável via `RentScheduleService`) **e** `bill_exits` (bill com `due_date` no dia) em **seções separadas**.
- [ ] entradas refletem **só** cobráveis (lease `owner=null`, não salary-offset/prepaid) — criar lease com owner → **não** aparece em `rent_entries`; criar bill → aparece em `bill_exits`.
- [ ] `bill_exits` agrupa por `due_date.day`; bill `suspended`/`deferred` aparece rotulado mas `is_overdue=false`.
- [ ] `combined_calendar` com `building_id` filtra entradas e saídas pelo prédio; bills de nível-condomínio (`building=null`) aparecem quando `building_id` ausente.
- [ ] params inválidos (`month=13`, `year=abc`) → 400 PT.
- [ ] **§18 cross-app/cache**: toggle de pagamento de aluguel (`POST /api/dashboard/toggle_rent_payment/`) **entre** dois GETs de `combined_calendar` reflete a mudança **sem stale** (prova de que o endpoint **não tem cache** — design §11). Asserir que o item de aluguel mudou de `is_paid=false` → `true` no segundo GET.
- [ ] `GET finance-dashboard/overdue` → lista de bills com `is_overdue=true` (vencido + remaining>0 + active), ordenada por `due_date`; `overdue_bills_total = Σ amount_remaining` (**não** amount_total); `rent_overdue` sub-total **separado** (não somado).
- [ ] **§18 atrasado**: bill `deferred`/`suspended` vencido **não** entra em `overdue`; bill pago integral não entra; seed (S37) gera atrasado visível (valor esperado>0) → aparece.

**Matriz `FinancialReadOnly` (`test_finance_permissions.py`)** — espelhar `test_financial_permissions.py:16-58`
- [ ] não-admin autenticado: `GET` em todos os endpoints (list + `combined_calendar` + `overdue`) → **200**.
- [ ] não-admin: `POST` em `finance-categories`/`billing-accounts`/`bills`/`bill-skips`/`payments` **e** ações `bills/{id}/pay`/`bulk_pay`/`suspend`/`generate_month`/`create_with_lines` → **403**.
- [ ] admin (`is_staff`): os mesmos `POST` passam do gate de permissão (≠ 403 — 400/200/201 aceitável).
- [ ] anônimo: `GET` em qualquer endpoint → **401**.

**Unit `CondoCalendarService.combined_month` (`tests/unit/test_finances/test_condo_calendar_service.py`)** — se o service for criado aqui, `@freeze_time`
- [ ] shape `{year, month, today, days:[{day,date,weekday,rent_entries,bill_exits}]}`.
- [ ] entradas vêm de `RentScheduleService.get_month_schedule` (criar lease cobrável → item no dia clampado).
- [ ] saídas vêm de `Bill.objects.with_amounts` por `due_date.day`; offset reflete em `amount_total`.
- [ ] `building_id` filtra ambas as seções; `building=null` (nível-condomínio) só sem filtro.
- [ ] **§18 estrutural**: mês sem leases → `rent_entries` vazias; prédio sem bills → `bill_exits` vazias; bill soft-deleted **excluído**.

> Rodar (devem **falhar** — serializers/viewsets/urls/service ainda não existem):
> ```bash
> python -m pytest tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py -q
> ```

### 2. GREEN — implementar

Criar `finances/serializers.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py`, `finances/services/condo_calendar_service.py` (se ausente), `finances/urls.py`; wirar `condominios_manager/urls.py`. Imports diretos da fonte (`from finances.models import …`, `from core.permissions import FinancialReadOnly`, `from core.pagination import CustomPageNumberPagination`, `from core.services.rent_schedule_service import RentScheduleService`, helper TZ SP da S34) — **sem re-export/barrel novo** (só o `__init__`/`__all__` do pacote de viewsets). Ações **finas** delegando aos serviços da S37. Rodar até verde:
```bash
python -m pytest tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)

- Extrair a validação `year`/`month` (parse + range 1–12 → 400 PT) em **um** helper compartilhado por `generate_month` e `combined_calendar` (DRY; reusar a constante de range do exemplar `MONTHS_IN_YEAR` em vez de número mágico).
- Extrair o "re-anotar e serializar um `Bill`" das ações (`pay`/`bulk_pay`/`suspend`/…) em **um** helper (`_serialized_bill(bill) -> dict`) — todas as ações retornam o mesmo shape (DRY).
- Garantir que `BillViewSet.get_queryset` e o `combined_calendar`/`overdue` usam o **mesmo** `today` do helper TZ SP (fonte única) — sem `timezone.now().date()` espalhado.
- Confirmar que **nenhuma** lógica de pagamento/geração/transição vive na view (só nos serviços S37) — view é fina (design/architecture).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem problemas pré-existentes de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/serializers.py finances/viewsets/ finances/services/condo_calendar_service.py finances/urls.py condominios_manager/urls.py tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py
ruff format --check finances/serializers.py finances/viewsets/ finances/services/condo_calendar_service.py finances/urls.py condominios_manager/urls.py tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py
mypy core/ finances/
pyright finances/serializers.py finances/viewsets/ finances/services/condo_calendar_service.py finances/urls.py
```

---

## Constraints

- **Direção de dependência** (`.claude/rules/architecture.md`): Views → Services → Models. Os viewsets importam de `finances.serializers`, `finances.services.*`, `core.services.rent_schedule_service`, `core.permissions`, `core.pagination` — **nunca** o contrário; serializers importam só de `finances.models`/`core.models` (**nunca** de serviços/views). Ações **finas**: zero lógica de negócio na view (delegar a S37).
- **Serializer dual** (CLAUDE.md, `.claude/rules/architecture.md`): nested read + `_id` write (`PrimaryKeyRelatedField(source=…, write_only=True, allow_null=True)` para FK nullable). `amount_*` **read-only** string Decimal lidos da annotation `with_amounts` — **nunca** recomputar em Python (design §4.4).
- **API namespaced** `/api/finances/...` via `finances/urls.py` (router próprio) + `include` no projeto — não registrar no `core/urls.py`.
- **`FinancialReadOnly` em TODA rota** (CRUD + ações + dashboard): autenticado lê, `is_staff` escreve. Import direto de `core.permissions` (não inline).
- **`CustomPageNumberPagination`** em todos os `ModelViewSet`. Respostas de list paginadas (`results`).
- **`combined_calendar` SEM cache** (design §11): não decorar com `@cache_result`, não tocar `CacheManager`. Comentário explicando o porquê (dupla-invalidação aluguel×bills).
- **Sem KPIs de dinheiro** (Fase 4): nenhum saldo/caixa/reserva/resultado-do-mês. `overdue` = Σ `amount_remaining` (não amount_total) + sub-total de aluguel **separado** (design §4.4). Sem `CondoBalanceService`.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código de verdade. Tipos completos (mypy strict + pyright strict). `cast(User, request.user)` quando necessário (padrão `web_push_views`).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo — `.claude/rules/coding-standards.md`); importar tipos diretamente.
- **Sem re-exports / barrel files / shims**: cada módulo exporta só o que define; consumidores importam da fonte. O único `__init__`/`__all__` é o do pacote `finances/viewsets/`.
- **Não criar/alterar** modelos, migração, serviços de pagamento/geração (S36/S37), nem nada de Fases 3/4 (installment/employee/reserve/income/month-close), nem frontend.
- **Não wirar** o legado `DailyControlService`/`daily-control` (design §15).
- **`DecimalField(12,2)`** — dinheiro serializado como **string**; quantização (se houver) só na fronteira (design §4) — mas esta sessão **só lê** annotations já somadas (não quantiza).
- Mensagens de erro ao usuário em **Português** (DRF-shape: `detail`/`error`/field-level); logs/identificadores/enum values/url_path em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/serializers.py` define `CategorySerializer`, `BillingAccountSerializer`, `BillSerializer` (com `line_items` nested + `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue` read-only string da annotation), `BillLineItemSerializer`, `BillSkipSerializer`, `PaymentSerializer` (com `allocations` nested) — todos **dual** (nested read / `_id` write, `allow_null` em FK nullable), importando da fonte (sem re-export).
- [ ] `finances/viewsets/crud_views.py` define `CategoryViewSet`, `BillingAccountViewSet`, `BillViewSet`, `BillSkipViewSet`, `PaymentViewSet` (`ModelViewSet` + `FinancialReadOnly` + `CustomPageNumberPagination`); `BillViewSet.get_queryset` usa `Bill.objects.with_amounts(today)` com `today` do helper TZ SP + filtros (`building_id`/`category_id`/`competence_month`/`lifecycle_state`/`behavior`/`payment_status`/`is_overdue`).
- [ ] `BillViewSet` expõe as ações `pay`, `bulk_pay`, `suspend`, `defer`, `cancel`, `reactivate`, `generate_month`, `create_with_lines` — **finas**, delegando a `BillPaymentService`/`BillGenerationService`/`BillService` (S37); erros (over-allocation, mês fechado, transição inválida, payload inválido, year/month inválido) → **400 DRF-shape PT**; `bulk_pay` atômico (rollback em falha).
- [ ] `finances/services/condo_calendar_service.py` (se ausente) define `CondoCalendarService.combined_month(year, month, building_id=None)` — entradas via `RentScheduleService.get_month_schedule` (DRY), saídas via `Bill.objects.with_amounts` agrupadas por `due_date.day`, **seções separadas**, **sem KPIs de dinheiro**, "hoje" via helper TZ SP.
- [ ] `finances/viewsets/dashboard_views.py` define `FinanceDashboardViewSet` (bare + `FinancialReadOnly`) com `combined_calendar` (**SEM cache** — sem `@cache_result`/`CacheManager`, comentário explicando) e `overdue` (lista `is_overdue=True` ordenada por `due_date` + `overdue_bills_total = Σ amount_remaining` + `rent_overdue` sub-total **separado**; deferido/suspenso excluídos).
- [ ] `finances/urls.py` registra `finance-categories`/`billing-accounts`/`bills`/`bill-skips`/`payments`/`finance-dashboard`; `condominios_manager/urls.py` inclui `path("api/finances/", include("finances.urls"))`; rotas resolvem em `/api/finances/...` com ações underscore.
- [ ] Testes de integração cobrem: CRUD + filtros + paginação + dual serializer (nested read / `_id` write) + soft-delete; ações (`pay`/`bulk_pay`/`suspend`/`defer`/`cancel`/`reactivate`/`generate_month` idempotente/`create_with_lines`) incl. over-allocation 400, bulk atômico, transição inválida 400, year/month inválido 400; `combined_calendar` (seções entradas/saídas, building filter, **sem-cache via toggle entre GETs**) + `overdue` (Σ remaining, rent sub-total separado, deferido/suspenso fora); matriz `FinancialReadOnly` (200/403/non-403/401). Unit do `CondoCalendarService` (se criado aqui).
- [ ] `python -m pytest tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py` passa 100%; **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright` limpo nos arquivos tocados — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum frontend; nenhum KPI de dinheiro; nenhum modelo/migração/serviço de pagamento alterado; nenhum endpoint de Fase 3/4; `daily-control` legado não wirado; `combined_calendar` não cacheado.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   ruff check finances/serializers.py finances/viewsets/ finances/services/condo_calendar_service.py finances/urls.py condominios_manager/urls.py tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py
   ruff format --check finances/serializers.py finances/viewsets/ finances/services/condo_calendar_service.py finances/urls.py condominios_manager/urls.py tests/integration/test_finances/ tests/unit/test_finances/test_condo_calendar_service.py
   mypy core/ finances/
   pyright finances/serializers.py finances/viewsets/ finances/services/condo_calendar_service.py finances/urls.py
   ```
2. Atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 38 (status **concluída**) na tabela de progresso da feature Condomínio Finance.
   - Listar **Arquivos Criados** (`finances/serializers.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py`, `finances/services/condo_calendar_service.py`, `finances/urls.py`, os 4 `tests/integration/test_finances/*.py` + `tests/unit/test_finances/test_condo_calendar_service.py`) e **Modificados** (`condominios_manager/urls.py` — include `api/finances/`; `finances/viewsets/__init__.py` — exports).
   - Anotar os **contratos cross-session** (verbatim, ver abaixo) para a S39/S40 (frontend) e Fases 4/6 consumirem sem derivar.
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch se necessário — ex.: `feat/condo-finance`):
   ```
   feat(finances): add finance serializers, viewsets, /api/finances API, bill actions, combined calendar + overdue endpoints

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **39 — Frontend: hooks `use-finance-*` (query-keys central, `placeholderData: keepPreviousData`, MSW) + calendário combinado** — consome os endpoints `/api/finances/...` desta sessão (shapes verbatim abaixo). A S39/S40 **não** alteram o backend.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim — S39/S40 frontend, Fases 4/6)

- **Base de API**: `/api/finances/...`. Recursos plural: `finance-categories`, `billing-accounts`, `bills`, `bill-skips`, `payments`. Dashboard bare: `finance-dashboard/combined_calendar`, `finance-dashboard/overdue`. Permission `FinancialReadOnly` (write gated em `is_staff`). Listas paginadas (`results`), `page_size`/`page` (`CustomPageNumberPagination`).
- **`BillSerializer` (shape de leitura)**: FKs nested (`building`/`category`/`billing_account`), `line_items: BillLineItemSerializer[]` (read-only), e os derivados **read-only string/bool da annotation**: `amount_total`, `amount_paid`, `amount_remaining` (string Decimal), `payment_status ∈ {open,partial,paid}`, `is_overdue` (bool). Write usa `*_id`. Linhas se criam via `bills/create_with_lines` (não nested writable).
- **Ações do `BillViewSet`** (todas `POST`): `bills/{id}/pay` (`{payment_date, amount?, funded_from?}` → `Bill` re-anotado; over-allocation → 400 PT); `bills/bulk_pay` (`{bill_ids[], payment_date, funded_from?}`, atômico); `bills/{id}/suspend|defer|cancel|reactivate` (`Bill` re-anotado; `reactivate` de `canceled` → 400); `bills/generate_month` (`{year, month}`, idempotente, retorna o shape do `BillGenerationService` da S37); `bills/create_with_lines` (`{bill:{…}, line_items:[{description,amount,is_offset,category_id}]}` → `Bill` 201).
- **`finance-dashboard/combined_calendar`** (GET, `?year=&month=&building_id=`): `{year, month, today, days:[{day, date, weekday, rent_entries:[…], bill_exits:[{bill_id, description, building_number, category, amount_total, amount_remaining, payment_status, due_date, is_overdue, lifecycle_state}]}]}`. **Seções separadas** entradas/saídas. **SEM cache** (reflete toggle de aluguel imediatamente).
- **`finance-dashboard/overdue`** (GET, `?building_id=`): `{bills:[BillSerializer…], overdue_bills_total (string=Σ amount_remaining), overdue_bills_count, rent_overdue:{count, total_fee}}`. KPI "Atrasados" de contas = `overdue_bills_total`; atraso de aluguel = sub-total **separado** (não somar). Deferido/suspenso/cancelado fora.
- **`CondoCalendarService.combined_month(year, month, building_id=None)`** — fonte do `combined_calendar`; entradas via `RentScheduleService.get_month_schedule` (DRY); saídas agrupadas por `due_date.day`; sem KPIs de dinheiro (Fase 4 adiciona saldo/caixa/reserva ao dashboard, não a este método).
- **Consumido da S36/S37**: `Bill.objects.with_amounts(today)` (annotations), `BillPaymentService.pay`/`BillGenerationService.ensure_month_bills`/`BillService.create_with_lines`, helper TZ SP, `RentScheduleService.received_collectible_total`/`get_month_schedule`/`get_month_stats`/`collectible_leases`/`displayable_leases` (não-invasivo, sem mudança no SSOT de aluguel).
