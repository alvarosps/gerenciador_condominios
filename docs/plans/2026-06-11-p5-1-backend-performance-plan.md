# Plano P5.1 — Performance backend: N+1, IBGE assíncrono, memoização

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P5 (Performance) · **Branch sugerida:** `perf/backend-queries` · **Depende de:** nenhum (mas tocar serializers/querysets depois de P4.1 evita conflito de merge)

## Objetivo

Eliminar os gargalos de latência do backend que travam workers no Render e degradam o dashboard. Três frentes: (1) remover a chamada HTTP síncrona ao IBGE/SIDRA do caminho de request do alerta de reajuste, movendo-a para o cron diário já existente e cacheando o endpoint; (2) corrigir N+1 reais no `BillViewSet`/`overdue` do app `finances`, nos serializers de `Expense`/`ExpenseCategory` (core legado) e nos querysets de `leases`/`apartments`/`rent-payments`; (3) memoizar `CondoBalanceService._components` por request e fazer batch de `BillSkip` na projeção de 36 meses. Importa porque hoje um único load do dashboard de reajustes pode bloquear até 15s, e a projeção/overview reexecuta os mesmos cálculos 5×+ e dispara N×36 queries.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | IBGE/SIDRA síncrono (timeout 15s) no load do dashboard de reajustes, endpoint sem cache | `core/services/rent_adjustment_service.py:213-214` · `core/views.py:834,844` | Curto-circuitar `fetch_latest()` quando o índice já cobre o mês, cachear o endpoint, mover o fetch para o cron `send_finance_alerts` |
| ALTO→MÉDIO | N+1 no `BillSerializer` — `line_items__category` (e `installment__plan...`) sem prefetch, agravado por page_size grande | `finances/viewsets/crud_views.py:292-306` · `finances/viewsets/dashboard_views.py:229-235` · `finances/serializers.py:230-235` | Queryset base compartilhado com `prefetch_related("line_items__category", ...)` no `BillViewSet` e no `overdue` |
| ALTO→MÉDIO | N+1 em `/api/rent-payments/` — `RentPaymentSerializer` aninha `LeaseSerializer` completo sem prefetch correspondente | `core/viewsets/financial_views.py:446-449` · `core/serializers.py:1055-1056,376-396` | Serializer enxuto `RentPaymentSlimSerializer` (legado, mínimo) sem aninhar `LeaseSerializer` |
| ALTO→MÉDIO | Prefetches mortos + faltantes em `leases`/`apartments` (paga `tenants__dependents`/`tenants__furnitures` à toa; falta `apartment__owner`, `apartment__leases__responsible_tenant`) | `core/views.py:311-355,131-172` | Remover prefetches que `TenantSummarySerializer` não lê; adicionar os que `ApartmentSerializer.owner`/`active_lease` exigem |
| MÉDIO | `ExpenseSerializer` faz 3 queries por despesa (method fields `.count()`/`.aggregate()` ignoram o prefetch de `installments`) | `core/serializers.py:899-908` | Computar `remaining_installments`/`total_paid`/`total_remaining` em Python sobre `obj.installments.all()` |
| MÉDIO | `ExpenseCategorySerializer.get_subcategories` recursivo, 1 query por nó | `core/serializers.py:787-789` · `core/viewsets/financial_views.py:94` | `prefetch_related("subcategories__subcategories")` no `ExpenseCategoryViewSet` |
| MÉDIO | `CondoBalanceService._components` recomputado ~5×+ por `overview` (e walk de N meses em `cash_balance`) | `finances/services/condo_balance_service.py:182-215,220-272` | Memoizar `_components` por `(year, month, building_id)` via `functools.lru_cache` por request/thread-local de chamada |
| MÉDIO | `CondoProjectionService` faz `BillSkip.exists()` por (conta, mês) na projeção de 36 meses | `finances/services/bill_generation_service.py:49-63` · `finances/services/condo_projection_service.py:159-215` | Pré-carregar os `BillSkip` do horizonte inteiro em um `set` e consultá-lo em memória |

## Abordagem técnica

Ordem de execução pensada para isolar cada frente (cada item é testável e commitável separadamente). TDD: escrever o teste de regressão (assertNumQueries/comportamento) ANTES da correção em cada passo.

### Passo 1 — IPCA: curto-circuito + cache + cron (ALTO)

1.1. **Curto-circuito do fetch externo.** Em `core/services/ipca_service.py`, adicionar um guard no início de `IPCAService.fetch_latest()` (linha 27): se já existe um `IPCAIndex` cujo `reference_month` é o mês imediatamente anterior ao mês corrente (`current_month - relativedelta(months=1)`, ou seja, o índice mais recente que o IBGE poderia ter publicado — o IPCA do mês M só sai em M+1), retornar esse índice SEM fazer `requests.get`. Concretamente: calcular `expected_latest = (today.replace(day=1) - relativedelta(months=1))`; se `latest is not None and latest.reference_month >= expected_latest`, retornar `latest` direto. Isso elimina a chamada externa em todo dia em que o banco já está em dia — o caso comum.

1.2. **`get_eligible_leases` não dispara fetch no request.** Em `core/services/rent_adjustment_service.py`, remover a chamada `IPCAService.fetch_latest()` da linha 213 (dentro de `get_eligible_leases`). O método passa a ler apenas o banco via `IPCAService.get_latest_available_month()` (linha 214) e `get_adjustment_percentage` (linha 220). O fallback ao `Landlord.rent_adjustment_percentage` (linhas 223-225) já cobre o caso de banco vazio, então nenhuma regressão funcional.

1.3. **Cron faz o fetch.** Em `core/management/commands/send_finance_alerts.py` (o cron diário SP-aware já existente, linha 54 `handle`), adicionar no início do `handle` uma chamada a `IPCAService.fetch_latest()` (import de `core.services.ipca_service`). Como o curto-circuito do 1.1 já evita a chamada quando desnecessária, o cron só baterá no SIDRA quando houver mês novo a buscar. Logar o resultado (`Fetched IPCA up to <month>`). Esse comando já importa de `finances` (linhas 20-21), então adicionar import de `core.services.ipca_service` é consistente (core→core, sem inversão).

1.4. **Cachear o endpoint de alertas.** Seguir o padrão de `finances/viewsets/dashboard_views.py:89-118` (função module-level decorada). Em `core/views.py`, criar uma função module-level `_cached_rent_adjustment_alerts()` decorada com `@cache_result(timeout=300, key_prefix="dashboard-rent-adjustment-alerts")` que chama `RentAdjustmentService.get_eligible_leases()`, e fazer `DashboardViewSet.rent_adjustment_alerts` (linha 834-848) chamar essa função em vez do service direto. Import: `from core.cache import cache_result` (já há `CacheManager` em uso no módulo de signals; confirmar import em `core/views.py`).

1.5. **Invalidação do novo cache.** Em `core/signals.py`, o handler de `Lease` (`invalidate_lease_cache_on_save`, linhas 209-233) e o de `RentAdjustment` (linhas 438-451) já rodam em mudanças que afetam os alertas. Adicionar nesses handlers `CacheManager.invalidate_pattern("dashboard-rent-adjustment-alerts*")`. Também adicionar handlers `post_save`/`post_delete` para `Landlord` (não existe hoje — `Landlord.rent_adjustment_percentage` alimenta o fallback) que invalidem o mesmo padrão. O cron que escreve `IPCAIndex` roda 1×/dia e o TTL de 300s já cobre a defasagem; NÃO criar signal para `IPCAIndex` (KISS — o cron + TTL bastam, e `IPCAIndex` não tem mixins/manager de soft delete).

### Passo 2 — N+1 no `finances` (ALTO→MÉDIO)

2.1. **Queryset base compartilhado do `Bill`.** O `BillViewSet.get_queryset` (linhas 292-306) já tem `select_related(... "installment__plan__billing_account")` e `prefetch_related("line_items", "allocations")`, mas `BillLineItemSerializer` (linhas 230-235) aninha `CategorySerializer` em cada `line_item` e o prefetch não traz `line_items__category` → N+1. O `overdue` (dashboard_views.py:229-235) repete o queryset SEM o `select_related` de `installment__plan__billing_account` (que `get_account_type` da serializers.py:404 precisa). Extrair um helper module-level em `finances/viewsets/` (ou método estático no `BillViewSet`) — ex.: `bill_list_queryset(as_of: date, *, building_id=None)` — que devolve `Bill.objects.with_amounts(as_of).select_related("building","category","billing_account","condominium","water_statement","electricity_statement","installment__plan__billing_account").prefetch_related("line_items__category","allocations")` e usá-lo nos dois pontos (DRY). Trocar `prefetch_related("line_items", ...)` por `prefetch_related("line_items__category", ...)` (prefetch de FK aninhada via `line_items__category` traz a categoria de cada linha em uma query agregada).

2.2. **`overdue` usa o mesmo helper.** Em `dashboard_views.py:229-235`, substituir o queryset inline pelo helper do 2.1 (mantendo o `.filter(is_overdue=True).order_by("due_date")` específico do overdue).

### Passo 3 — `/api/rent-payments/` serializer enxuto (ALTO→MÉDIO, legado mínimo)

3.1. `RentPaymentViewSet.get_queryset` (financial_views.py:446-449) faz `select_related` só de `lease/apartment/building/responsible_tenant`, mas `RentPaymentSerializer` (serializers.py:1055-1056) aninha `LeaseSerializer` completo, que por sua vez aninha `ApartmentSerializer` (owner via `PersonSimpleSerializer`, furnitures M2M, `active_lease` via `obj.leases.all()`), `tenants` M2M, `resident_dependent` etc. — dezenas de queries por linha. Como o módulo financeiro pessoal é DEPRECATED, a correção é **mínima e cirúrgica**: criar `RentPaymentSlimSerializer` em `core/serializers.py` com apenas os campos que a tela de admin/relatório de pagamentos precisa (`id`, `reference_month`, `amount_paid`, `payment_date`, `notes`, e uma referência leve do lease/apartment via `TenantSimpleSerializer`/string `f"Apto {number}"` — espelhar o que o frontend consome). Usar esse serializer no `RentPaymentViewSet` (e ajustar o `get_queryset` para o `select_related` mínimo correspondente). NÃO criar serializer enxuto para o portal do inquilino aqui (isso pertence a P3.x/segurança — fora de escopo).

### Passo 4 — Prefetches mortos/faltantes em `leases`/`apartments` (ALTO→MÉDIO)

4.1. **`LeaseViewSet.get_queryset`** (views.py:311-355): `tenants` é serializado por `TenantSummarySerializer` (serializers.py:93-99, fields = `id,name,cpf_cnpj,phone,due_day`) que NÃO lê `dependents` nem `furnitures` → remover `"tenants__dependents"` (336) e `"tenants__furnitures"` (337) — prefetches mortos. Adicionar os FALTANTES que o `ApartmentSerializer` aninhado lê: `apartment__owner` (ao `select_related`, linhas 326-331, pois `ApartmentSerializer.owner` usa `PersonSimpleSerializer`) e `apartment__leases__responsible_tenant` (ao `prefetch_related`, pois `ApartmentSerializer.get_active_lease` → `obj.leases.all()` → `LeaseNestedForApartmentSerializer.responsible_tenant`). Manter `apartment__furnitures`, `tenants`, `rent_adjustments`.

4.2. **`ApartmentViewSet.get_queryset`** (views.py:131-172): `ApartmentSerializer` lê `owner` (PersonSimpleSerializer) e `active_lease` (→ `obj.leases.all()` → `LeaseNestedForApartmentSerializer.responsible_tenant`). Adicionar `"owner"` ao `select_related` (linha 143) e `"leases__responsible_tenant"` ao `prefetch_related` (linhas 143-146). Manter `building`, `furnitures`, `leases`.

### Passo 5 — Method fields do `Expense`/`ExpenseCategory` sobre prefetch (MÉDIO)

5.1. **`ExpenseSerializer`** (serializers.py:899-908): o `ExpenseViewSet.get_queryset` (financial_views.py:142-144) já faz `.prefetch_related("installments")`, mas os 3 method fields fazem `.filter(...).count()`/`.aggregate(Sum)` que disparam novas queries ignorando o prefetch. Reescrever para iterar `obj.installments.all()` em Python:
   - `get_remaining_installments` → `sum(1 for i in obj.installments.all() if not i.is_paid)`
   - `get_total_paid` → `str(sum((i.amount for i in obj.installments.all() if i.is_paid), Decimal(0)))`
   - `get_total_remaining` → `str(sum((i.amount for i in obj.installments.all() if not i.is_paid), Decimal(0)))`
   Mantém a mesma saída (string Decimal) sobre o cache do prefetch.

5.2. **`ExpenseCategorySerializer`** (serializers.py:787-789): adicionar `.prefetch_related("subcategories", "subcategories__subcategories")` ao `ExpenseCategoryViewSet.get_queryset` (hoje `queryset = ExpenseCategory.objects.all()` na linha 94 — adicionar um `get_queryset` ou ajustar o atributo). Como a recursão tem profundidade prática 2 (categoria→subcategoria), prefetchar 2 níveis cobre o caso real. `get_subcategories` já usa `obj.subcategories.all()` (linha 788), que passa a ler do prefetch.

### Passo 6 — Memoizar `_components` (MÉDIO)

6.1. Em `finances/services/condo_balance_service.py`, `overview` (182-215) chama `result_of_month` (1× `_components`), `cash_change_of_month` (1×), `cash_balance` (walk de N meses, cada um `cash_change_of_month`→`_components`) e `_wedge_residual` (que reexecuta `result_of_month` + `cash_change_of_month` + `_components`). Memoizar `_components(year, month, building_id)` (220-272) por chamada de overview/projeção. KISS: como `_components` é `@staticmethod` puro de leitura, envolvê-lo com `functools.lru_cache` no nível do módulo NÃO serve (não invalida entre requests). Em vez disso, introduzir um cache por-execução: transformar `_components` em uma função interna memoizada por um dict passado/escopado à chamada de `overview`/`project`, OU usar `django.utils.functional` / um pequeno helper `_components_cached` com `functools.lru_cache(maxsize=None)` LIMPO no início de cada `overview`/`project` (chamar `_components_cached.cache_clear()` no início). Decisão recomendada (mais simples e segura): manter `_components` como está e adicionar um wrapper `_components` memoizado via `functools.lru_cache` aplicado a um método interno, com `cache_clear()` chamado no topo de `overview` e de `CondoProjectionService.project`. Documentar que a memoização é válida porque dentro de uma única request os dados não mudam (read-only, single transaction). Garantir thread-safety usando `lru_cache` (que é thread-safe para leitura) e limpando no entry point — aceitável para o tráfego admin baixo do módulo.

> Nota de implementação: confirmar com `assertNumQueries` o número de queries de `overview` antes (baseline) e depois (deve cair de ~5N para ~N+constante). Se `lru_cache` + `cache_clear` provar frágil sob concorrência nos testes, fallback para passar um `components_cache: dict[tuple, _Components]` explícito como parâmetro opcional pelos métodos internos (mais verboso mas determinístico). Escolher a opção que passar no gate sem warnings.

### Passo 7 — Batch de `BillSkip` na projeção (MÉDIO)

7.1. `CondoProjectionService._projected_expenses` (159-215) chama `BillGenerationService.is_account_eligible(account, reference_month)` (bill_generation_service.py:49-63) por (conta, mês), e cada chamada termina com `BillSkip.objects.filter(...).exists()` → N×horizonte queries. Para a projeção (36 meses default no consumidor), pré-carregar os skips do horizonte inteiro: no início de `project` (ou de `_projected_expenses`), carregar `set((ba_id, ref_month) for ba_id, ref_month in BillSkip.objects.filter(reference_month__gte=first_month, reference_month__lte=last_month).values_list("billing_account_id", "reference_month"))` e passar esse set adiante. Adicionar um parâmetro opcional a `is_account_eligible(account, month_start, *, skip_index: set[tuple[int, date]] | None = None)`: quando `skip_index` é fornecido, checar `(account.id, month_start) not in skip_index` em memória em vez do `.exists()`; quando `None`, manter o comportamento atual (uma query) para os call sites de geração. Isso preserva o uso em `ensure_month_bills`/`_generate_embedded_lines` (mesma SSOT de elegibilidade) sem regressão. Aplicar o mesmo set também ao loop de `embedded` (linhas 206-211).

## Arquivos a criar / modificar

- `core/services/ipca_service.py` — guard de curto-circuito em `fetch_latest` (passo 1.1).
- `core/services/rent_adjustment_service.py` — remover `IPCAService.fetch_latest()` de `get_eligible_leases` (passo 1.2).
- `core/management/commands/send_finance_alerts.py` — chamar `IPCAService.fetch_latest()` no `handle` (passo 1.3).
- `core/views.py` — função module-level `_cached_rent_adjustment_alerts` com `@cache_result`; `rent_adjustment_alerts` passa a chamá-la (passo 1.4); ajustar `LeaseViewSet`/`ApartmentViewSet` `get_queryset` (passos 4.1, 4.2).
- `core/signals.py` — invalidar `dashboard-rent-adjustment-alerts*` nos handlers de `Lease`/`RentAdjustment`; novos handlers `Landlord` (passo 1.5).
- `core/serializers.py` — `RentPaymentSlimSerializer` novo (passo 3.1); reescrever 3 method fields de `ExpenseSerializer` (passo 5.1).
- `core/viewsets/financial_views.py` — `RentPaymentViewSet` usa `RentPaymentSlimSerializer` + `select_related` mínimo (passo 3.1); `ExpenseCategoryViewSet.get_queryset` com prefetch de 2 níveis (passo 5.2).
- `finances/viewsets/crud_views.py` — helper `bill_list_queryset` (ou método estático) com `prefetch_related("line_items__category", ...)`; `BillViewSet.get_queryset` usa-o (passo 2.1).
- `finances/viewsets/dashboard_views.py` — `overdue` usa o helper (passo 2.2).
- `finances/services/condo_balance_service.py` — memoização de `_components` em `overview` (passo 6.1).
- `finances/services/condo_projection_service.py` — pré-carregar `BillSkip` do horizonte e passar `skip_index` (passo 7.1).
- `finances/services/bill_generation_service.py` — `is_account_eligible` aceita `skip_index` opcional (passo 7.1).

**Testes (criar/estender):**
- `tests/unit/test_ipca_service.py` — curto-circuito (sem HTTP quando o índice já cobre o mês; com HTTP quando falta mês). Mockar `requests.get` (fronteira externa) para assertar 0 vs 1 chamada.
- `tests/unit/test_rent_adjustment_service.py` — `get_eligible_leases` NÃO chama `fetch_latest` (assertar via mock de `requests.get` que nenhuma chamada externa ocorre).
- `tests/integration/test_rent_adjustment_alerts_cache.py` (novo) — endpoint cacheado: 2ª chamada não recomputa; invalida ao salvar Lease/RentAdjustment/Landlord.
- `tests/integration/test_bill_api.py` (ou existente do finances) — `assertNumQueries` no list de bills com line_items+categoria não cresce com o nº de bills; idem `overdue`.
- `tests/integration/test_rent_payment_api.py` — `assertNumQueries` constante no list de `/api/rent-payments/` com N pagamentos; payload do `RentPaymentSlimSerializer` não vaza PII de owner.
- `tests/integration/test_lease_api.py` / `test_apartment_api.py` — `assertNumQueries` constante no list com N leases/apartments (prova `apartment__owner`/`active_lease` resolvidos sem N+1).
- `tests/integration/test_expense_api.py` — `assertNumQueries` constante no list de despesas com installments; valores de `total_paid`/`total_remaining` idênticos ao comportamento anterior.
- `tests/unit/test_condo_balance_service.py` — `assertNumQueries` de `overview` cai (memoização) e os valores são idênticos.
- `tests/unit/test_condo_projection_service.py` — `assertNumQueries` de `project(months=36)` não cresce linearmente com o nº de contas (batch de BillSkip); valores idênticos com e sem skip.

## TDD — cenários de teste

- `test_fetch_latest_short_circuits_when_index_covers_month` — banco com índice do mês anterior ao corrente → `requests.get` NÃO é chamado; retorna o índice do banco.
- `test_fetch_latest_calls_api_when_month_missing` — banco defasado → `requests.get` é chamado 1×.
- `test_get_eligible_leases_does_not_hit_external_api` — regressão do bug ALTO: chama `get_eligible_leases`; assertar 0 chamadas a `requests.get` (mock na fronteira HTTP).
- `test_get_eligible_leases_uses_fallback_when_db_empty` — sem `IPCAIndex` → usa `Landlord.rent_adjustment_percentage`; sem regressão funcional.
- `test_send_finance_alerts_fetches_ipca` — o cron chama `fetch_latest` (mock) uma vez.
- `test_rent_adjustment_alerts_endpoint_is_cached` — 2 GETs consecutivos: o 2º não recomputa (spy no service ou cache HIT).
- `test_rent_adjustment_alerts_cache_invalidated_on_lease_save` / `_on_rent_adjustment_save` / `_on_landlord_save` — salvar invalida `dashboard-rent-adjustment-alerts*`.
- `test_bill_list_no_n_plus_one_with_line_item_categories` — criar 10 bills com line_items categorizados; `assertNumQueries` ≤ limite fixo independente de N.
- `test_overdue_endpoint_no_n_plus_one` — idem para `/finances/finance-dashboard/overdue/`, incluindo `account_type` (precisa `installment__plan__billing_account`).
- `test_rent_payments_list_no_n_plus_one` — N pagamentos → queries constantes com `RentPaymentSlimSerializer`.
- `test_rent_payment_slim_serializer_omits_owner_pii` — payload não contém `owner.phone/email/notes` (prova que o serializer enxuto não aninha `PersonSimpleSerializer`).
- `test_lease_list_no_n_plus_one_includes_apartment_owner_and_active_lease` — leases com apartamento/owner/active_lease → queries constantes; remover prefetches mortos não quebra a saída.
- `test_apartment_list_no_n_plus_one` — apartments com owner + active_lease → queries constantes.
- `test_expense_serializer_totals_use_prefetch` — `assertNumQueries` no list de despesas constante; `total_paid`/`total_remaining`/`remaining_installments` idênticos ao baseline (incluindo edge: despesa sem installments → "0"; parcelas mistas pagas/não pagas).
- `test_expense_category_subcategories_no_n_plus_one` — árvore de categorias com subcategorias → queries constantes.
- `test_condo_overview_memoizes_components` — `assertNumQueries` de `overview` cai vs baseline; valores (result/cash/wedge_ok) idênticos; `wedge_ok=True` preservado.
- `test_condo_projection_batches_bill_skips` — `project(months=36)` com K contas e alguns skips: `assertNumQueries` não escala com K×36; meses pulados refletem o skip corretamente (edge: skip exatamente no mês limite do horizonte).
- `test_is_account_eligible_skip_index_matches_db` — `is_account_eligible(account, m, skip_index=...)` retorna o MESMO booleano que a versão com `.exists()` para o mesmo dado (paridade do batch vs query).

## Migrations / dados

N/A. Nenhuma mudança de schema, nenhuma tabela nova (sem RLS a habilitar), nenhuma correção de dado vivo. Apenas querysets, serializers, cache e ordem de chamadas. Não há `migrate` destrutivo — backup não requerido por este plano.

## Constraints (o que NÃO fazer)

- NÃO refatorar profundamente o módulo financeiro pessoal legado (`core/serializers.py` Expense/RentPayment, `financial_views.py`): apenas as correções de performance/N+1 listadas. Sem mudar regras de negócio, sem mover lógica para services novos além do estritamente necessário.
- NÃO criar serializer enxuto para o portal do inquilino (`/api/tenant/payments/`) aqui — é tema de segurança/PII (P3.x), fora de escopo deste plano.
- NÃO adicionar signal de invalidação para `IPCAIndex` (o cron 1×/dia + TTL 300s bastam — KISS).
- NÃO mexer no `with_amounts`/`LargePageNumberPagination` do `BillViewSet` (page_size grande é intencional, não é bug).
- NÃO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `from __future__ import annotations`, re-exports nem shims de compat. Tipos importados diretamente no topo.
- NÃO quebrar a paridade `is_account_eligible` entre projeção e geração: o `skip_index` é um caminho alternativo que DEVE retornar o mesmo booleano da query (coberto por teste de paridade).
- NÃO alterar a saída pública (campos/strings Decimal) de `ExpenseSerializer` ou `overview`/`project` — só a forma de computar. Os testes de valor idêntico travam isso.
- Dinheiro sempre `Decimal` (sem float); strings monetárias mantêm a formatação atual.

## Critérios de aceite (binários)

- [ ] `get_eligible_leases` não dispara `requests.get` (teste de mock prova 0 chamadas).
- [ ] `IPCAService.fetch_latest` faz curto-circuito quando o índice já cobre o mês corrente-1.
- [ ] `send_finance_alerts` chama `fetch_latest` no `handle`.
- [ ] `GET /api/dashboard/rent_adjustment_alerts/` é cacheado e invalidado por Lease/RentAdjustment/Landlord.
- [ ] `BillViewSet` list e `overdue` resolvem `line_items.category` e `account_type` sem N+1 (`assertNumQueries` constante).
- [ ] `/api/rent-payments/` usa `RentPaymentSlimSerializer`, queries constantes, sem PII de owner no payload.
- [ ] `leases`/`apartments` list: prefetches mortos removidos, `apartment__owner`/`active_lease` sem N+1.
- [ ] `ExpenseSerializer` totals/contagem computados sobre o prefetch (queries constantes, valores idênticos).
- [ ] `ExpenseCategory` subcategorias sem N+1.
- [ ] `CondoBalanceService.overview` recomputa `_components` ≤ uma vez por (year, month, building_id) na chamada; valores idênticos, `wedge_ok=True`.
- [ ] `CondoProjectionService.project(36)` faz batch de `BillSkip` (1 query de skips, não N×36); paridade com a versão por-query.
- [ ] Gate de verificação passa sem erros e sem warnings nos arquivos tocados + regressão dirigida.

## Gate de verificação

Backend (escopado nos arquivos editados + regressão dirigida; a suite cheia tem flakiness pré-existente de xdist/Redis que NÃO bloqueia):

```bash
ruff check core/ finances/ tests/ && ruff format --check core/ finances/ tests/
mypy core/ finances/
pyright
python -m pytest tests/unit/test_ipca_service.py tests/unit/test_rent_adjustment_service.py \
  tests/unit/test_condo_balance_service.py tests/unit/test_condo_projection_service.py \
  tests/integration/test_bill_api.py tests/integration/test_rent_payment_api.py \
  tests/integration/test_lease_api.py tests/integration/test_apartment_api.py \
  tests/integration/test_expense_api.py tests/integration/test_rent_adjustment_alerts_cache.py -p no:randomly
```

Frontend: N/A (nenhuma mudança de contrato FE↔API neste plano — `RentPaymentSlimSerializer` deve manter os campos que o frontend já lê; se algum campo for removido, atualizar o hook/tipo correspondente e rodar `cd frontend && npm run lint && npm run type-check && npm run test:unit`). Confirmar antes de fechar que `lib/api/hooks/use-rent-payments.ts` (ou equivalente) não lê campos que o slim serializer deixou de expor.

## Handoff

Commit message sugerida:

```
perf(backend): kill IBGE sync fetch on dashboard, fix N+1 in bills/leases/expenses, memoize condo components

- IPCAService.fetch_latest short-circuits when DB already covers the month; fetch moved to send_finance_alerts cron
- get_eligible_leases reads DB only; rent_adjustment_alerts endpoint cached + invalidated via signals
- BillViewSet/overdue share a queryset with line_items__category + installment plan prefetch
- /api/rent-payments/ uses a slim serializer (no nested LeaseSerializer, no owner PII)
- leases/apartments: remove dead tenants__dependents/furnitures prefetch, add apartment__owner + active_lease
- ExpenseSerializer totals computed over prefetch; ExpenseCategory subtree prefetched
- CondoBalanceService.overview memoizes _components; CondoProjectionService batches BillSkip over the horizon

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar a entrada de memória `project_*` (criar `project_p5_backend_performance.md`) registrando: cron `send_finance_alerts` agora também faz o fetch IPCA (a ops do cron no Render permanece a mesma); o curto-circuito depende de o IPCA do mês M sair em M+1. O próximo plano de performance (frontend/infra) pode assumir que o backend não tem mais HTTP síncrono externo no caminho de request e que os list endpoints quentes (bills, leases, apartments, rent-payments, expenses) estão sem N+1.
