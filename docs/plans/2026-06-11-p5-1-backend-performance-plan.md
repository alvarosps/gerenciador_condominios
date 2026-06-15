# Plano P5.1 — Performance backend: N+1, IBGE assíncrono, memoização

> **Estado:** **EXECUTADO** (branch `perf/backend-queries`, local) — todos os 7 passos com TDD + gate verde (ruff/mypy/pyright limpos em `core/`+`finances/`; pyright 0 erros; regressão dirigida 753 testes backend + 19 frontend). **Desvios do plano (todos para melhor):** (1) Passo 2 precisou de prefetch mais fundo `line_items__category__condominium`/`__parent` (o `CategorySerializer` aninha condominium+parent) além do `line_items__category` planejado; (2) Passo 3 extraiu um `RentPaymentValidationMixin` (em vez de subclasse) p/ evitar conflito de tipo no override do campo `lease`, e exigiu a mudança FE acoplada em `rent-payment.schema.ts` (lease slim); (3) Passo 6 usou um **parâmetro `components` explícito por chamada** em vez de `functools.lru_cache` — o lru_cache global vazaria dados stale entre requests (bug real: `_monthly_balance`/month-close/owner-dist chamam os métodos direto, fora de overview/project), então o cache explícito request-scoped é a escolha segura; com isso, `project` não tem duplicação de `_components` (não precisou de clear).
> **Prioridade:** FASE P5 (Performance) · **Branch:** `perf/backend-queries` · **Depende de:** P4 (já mergeado em `master`, PR #18) — todas as âncoras abaixo foram re-verificadas contra o código pós-P4
>
> **Revisão 2026-06-12 (pós-merge de P4):** todas as `file:line` deste plano foram auditadas contra o `master` atual (P4.1/P4.2/P4.3 mergeados). P4.1 deslocou as âncoras de `core/views.py` (~+84 linhas abaixo do `LeaseViewSet`, que ganhou `perform_create`/`perform_update`). P4.2 **reescreveu a invalidação de cache** em `core/signals.py` (mapa `_CORE_MODEL_CACHE_PREFIXES` em vez de `invalidate_pattern` por handler) — o **item 1.5 foi reescrito** para o novo idioma. Demais correções: item 1.4 (`rent_adjustment_alerts` agora em 918-932; `cache_result` NÃO importado em views.py), Passo 7 (horizonte default é **12** meses, não 36; 36 é o teto), e Passo 6 (caller list de `_components` faltava `competence_pontas`). Âncoras de `finances/` sofreram apenas drift pré-P4 (sem conflito com P4); P5.2 (frontend) é P4-clean.

## Objetivo

Eliminar os gargalos de latência do backend que travam workers no Render e degradam o dashboard. Três frentes: (1) remover a chamada HTTP síncrona ao IBGE/SIDRA do caminho de request do alerta de reajuste, movendo-a para o cron diário já existente e cacheando o endpoint; (2) corrigir N+1 reais no `BillViewSet`/`overdue` do app `finances`, nos serializers de `Expense`/`ExpenseCategory` (core legado) e nos querysets de `leases`/`apartments`/`rent-payments`; (3) memoizar `CondoBalanceService._components` por request e fazer batch de `BillSkip` na projeção (horizonte parametrizável 1–36 meses, default 12). Importa porque hoje um único load do dashboard de reajustes pode bloquear até 15s, e a projeção/overview reexecuta os mesmos cálculos 5×+ e dispara N×(horizonte) queries de elegibilidade.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | IBGE/SIDRA síncrono (timeout 15s) no load do dashboard de reajustes, endpoint sem cache | `core/services/rent_adjustment_service.py:213-214` · `core/views.py:919,928` | Curto-circuitar `fetch_latest()` quando o índice já cobre o mês, cachear o endpoint, mover o fetch para o cron `send_finance_alerts` |
| ALTO→MÉDIO | N+1 no `BillSerializer` — `line_items__category` sem prefetch (e `installment__plan...` ausente só no `overdue`), agravado por page_size grande | `finances/viewsets/crud_views.py:318-332` · `finances/viewsets/dashboard_views.py:229-235` · `finances/serializers.py:234-240,402-410` | Queryset base compartilhado com `prefetch_related("line_items__category", ...)` no `BillViewSet` e no `overdue` |
| ALTO→MÉDIO | N+1 em `/api/rent-payments/` — `RentPaymentSerializer` aninha `LeaseSerializer` completo sem prefetch correspondente | `core/viewsets/financial_views.py:425-428` · `core/serializers.py:1104-1105,140-178` | Serializer enxuto `RentPaymentSlimSerializer` (legado, mínimo) sem aninhar `LeaseSerializer` |
| ALTO→MÉDIO | Prefetches mortos + faltantes em `leases`/`apartments` (paga `tenants__dependents`/`tenants__furnitures` à toa; falta `apartment__owner`, `apartment__leases__responsible_tenant`) | `core/views.py:333-385,136-177` | Remover prefetches que `TenantSummarySerializer` não lê; adicionar os que `ApartmentSerializer.owner`/`active_lease` exigem |
| MÉDIO | `ExpenseSerializer` faz 3 queries por despesa (method fields `.count()`/`.aggregate()` ignoram o prefetch de `installments`) | `core/serializers.py:933-942` | Computar `remaining_installments`/`total_paid`/`total_remaining` em Python sobre `obj.installments.all()` |
| MÉDIO | `ExpenseCategorySerializer.get_subcategories` recursivo, 1 query por nó | `core/serializers.py:821-823` · `core/viewsets/financial_views.py:94` | `prefetch_related("subcategories__subcategories")` no `ExpenseCategoryViewSet` |
| MÉDIO | `CondoBalanceService._components` recomputado ~5×+ por `overview` (e walk de N meses em `cash_balance`) | `finances/services/condo_balance_service.py:187-220,224-277` | Memoizar `_components` por `(year, month, building_id)` via `functools.lru_cache` por request/thread-local de chamada |
| MÉDIO | `CondoProjectionService` faz `BillSkip.exists()` por (conta, mês) na projeção (default 12, máx 36 meses) | `finances/services/bill_generation_service.py:50-65` · `finances/services/condo_projection_service.py:158-215` | Pré-carregar os `BillSkip` do horizonte inteiro em um `set` e consultá-lo em memória |

## Abordagem técnica

Ordem de execução pensada para isolar cada frente (cada item é testável e commitável separadamente). TDD: escrever o teste de regressão (assertNumQueries/comportamento) ANTES da correção em cada passo.

### Passo 1 — IPCA: curto-circuito + cache + cron (ALTO)

1.1. **Curto-circuito do fetch externo.** Em `core/services/ipca_service.py`, `IPCAService.fetch_latest()` é o `@staticmethod` em **linha 27** (decorator em 26); o `latest = IPCAIndex.objects.order_by("-reference_month").first()` está na linha 33 e o `requests.get` na linha 47 (dentro de try/except 46-51). Adicionar o guard logo **após a linha 33** (antes do `if latest:`), reaproveitando o `latest` já computado (sem segunda query): se já existe um `IPCAIndex` cujo `reference_month` é o mês imediatamente anterior ao mês corrente (`current_month - relativedelta(months=1)`, ou seja, o índice mais recente que o IBGE poderia ter publicado — o IPCA do mês M só sai em M+1), retornar esse índice SEM fazer `requests.get`. Concretamente: calcular `expected_latest = (today.replace(day=1) - relativedelta(months=1))`; se `latest is not None and latest.reference_month >= expected_latest`, retornar `latest` direto. `relativedelta` (import linha 12) e `timezone` (linha 13) já estão disponíveis. `get_latest_available_month()` existe em 125-129. Isso elimina a chamada externa em todo dia em que o banco já está em dia — o caso comum.

1.2. **`get_eligible_leases` não dispara fetch no request.** Em `core/services/rent_adjustment_service.py` (`get_eligible_leases` definido na linha 202), remover a chamada `IPCAService.fetch_latest()` da linha 213 **e o comentário órfão da linha 212** ("# Fetch latest IPCA data…"). O método passa a ler apenas o banco via `IPCAService.get_latest_available_month()` (linha 214) e `get_adjustment_percentage` (linha 220). O fallback ao `Landlord.rent_adjustment_percentage` (linhas 223-225) já cobre o caso de banco vazio, então nenhuma regressão funcional.

1.3. **Cron faz o fetch.** Em `core/management/commands/send_finance_alerts.py` (o cron diário SP-aware já existente, `handle` na linha 54, corpo começa na 55 com `today = today_sp()`), adicionar no início do `handle` uma chamada a `IPCAService.fetch_latest()`. O novo import `from core.services.ipca_service import IPCAService` vai no **bloco de imports do core (linhas 22-24)** — NÃO junto ao import de `finances` (que é só a **linha 20**, `from finances.services.iptu_alert_service import IptuAlertService, IptuRiskRow`; a linha 21 é em branco). Como o curto-circuito do 1.1 já evita a chamada quando desnecessária, o cron só baterá no SIDRA quando houver mês novo a buscar. Logar o resultado (`Fetched IPCA up to <month>`) via o `logger` do módulo (linha 26) ou `self.stdout.write`.

1.4. **Cachear o endpoint de alertas.** Seguir o padrão de `finances/viewsets/dashboard_views.py:84-120` (constantes de sub-prefixo em 84-86; funções module-level decoradas, ex. `_cached_overview` em 89-91). Em `core/views.py`, criar uma função module-level `_cached_rent_adjustment_alerts()` decorada com `@cache_result(timeout=300, key_prefix="dashboard-rent-adjustment-alerts")` que chama `RentAdjustmentService.get_eligible_leases()`, e fazer `DashboardViewSet.rent_adjustment_alerts` (def em **linha 919**, decorator `@action` em 918, chamada direta ao service em **linha 928** — `data = RentAdjustmentService.get_eligible_leases()`; **NÃO** 834-848, que após P4.1 aponta para `rent_control_calendar`/`toggle_rent_payment`) chamar essa função em vez do service direto. **`core/views.py` NÃO importa nada de `core.cache` hoje** (verificado por grep — zero ocorrências de `cache_result`/`CacheManager`/`from core.cache`) — **adicionar** `from core.cache import cache_result` aos imports. A assinatura `cache_result(timeout: int = 300, key_prefix: str = "")` existe em `core/cache.py:125`, então `@cache_result(timeout=300, key_prefix=...)` é válido.

1.5. **Invalidação do novo cache — via o mapa de prefixos do P4.2, NÃO `invalidate_pattern` à mão.** A P4.2 reescreveu `core/signals.py`: os handlers de cache não chamam mais `CacheManager.invalidate_pattern(...)` diretamente — eles delegam a `_invalidate_core_model_caches("<Model>")`, que lê os prefixos a invalidar de `_CORE_MODEL_CACHE_PREFIXES` (mapa model→tupla de prefixos, em `core/signals.py:82-94`). O comentário em `signals.py:68-73` reforça esse idioma e avisa que glob `"<prefix>:*"` nunca casa — usar sempre `"<prefix>*"` com chaves hifenizadas. Registrar o novo prefixo no mapa, **não** editar corpos de handler:

   - **Lease/Apartment/Building (de graça):** adicionar a string `"dashboard-rent-adjustment-alerts"` à tupla `_PROPERTY_CACHE_PREFIXES` (`core/signals.py:74-81`). Como `_CORE_MODEL_CACHE_PREFIXES` mapeia `Building`/`Apartment`/`Lease` todos para `_PROPERTY_CACHE_PREFIXES`, essa **única adição** faz save E delete dos três invalidarem o cache de alertas — os receivers `invalidate_lease_cache_on_save` (244-258) e `invalidate_lease_cache_on_delete` (261-268) já roteiam por `_invalidate_core_model_caches`. **NÃO editar o corpo de nenhum handler de Lease** (a etapa antiga "adicionar ao handler de Lease" fica redundante e sai).
   - **RentAdjustment (dois receivers):** os receivers `invalidate_rent_adjustment_finance_cache_on_save` (**468-475**) e `invalidate_rent_adjustment_finance_cache_on_delete` (**477-481**) hoje chamam só `_invalidate_finance_module_caches()` e RentAdjustment **não** está no mapa. Adicionar a chave `"RentAdjustment": ("dashboard-rent-adjustment-alerts",)` ao `_CORE_MODEL_CACHE_PREFIXES` (82-94) e acrescentar `_invalidate_core_model_caches("RentAdjustment")` a **ambos** os receivers (mantendo a chamada `_invalidate_finance_module_caches()` existente). (A âncora antiga 438-451 era o helper `_invalidate_rent_payment_caches` + receiver de RentPayment — não mexer nele.)
   - **Landlord (único receiver realmente novo):** não existe handler hoje (grep `Landlord` em `signals.py` = 0; `Landlord` em `core/models.py:901`, `rent_adjustment_percentage` em `core/models.py:960`). (1) adicionar `Landlord` ao import de `.models` (bloco 27-49); (2) adicionar `"Landlord": ("dashboard-rent-adjustment-alerts",)` ao `_CORE_MODEL_CACHE_PREFIXES`; (3) criar um par de receivers `post_save`/`post_delete` espelhando o par de `Building` (108-131), com corpo `_invalidate_core_model_caches("Landlord")`.
   - **NÃO** adicionar os novos receivers de `Landlord` ao `_TOGGLEABLE_RECEIVERS` (`signals.py:625-628`) — esse set é reservado só para o round-trip do sync `is_rented`; receivers de cache conectam uma vez no import via `@receiver`. Adicioná-los lá deixaria `disconnect_all_signals` desligar silenciosamente a invalidação do cache de alertas nos testes (poluição cross-test).
   - O cron que escreve `IPCAIndex` roda 1×/dia e o TTL de 300s já cobre a defasagem; NÃO criar signal para `IPCAIndex` (KISS — o cron + TTL bastam, e `IPCAIndex` não tem mixins/manager de soft delete).

### Passo 2 — N+1 no `finances` (ALTO→MÉDIO)

2.1. **Queryset base compartilhado do `Bill`.** O `BillViewSet.get_queryset` (linhas **318-332**) já tem `select_related` completo com os 7 FKs incl. `"installment__plan__billing_account"` (linhas 321-329) e `prefetch_related("line_items", "allocations")` (linha 330), construído de `Bill.objects.with_amounts(today_sp())` (`with_amounts` em `finances/models.py:223`, manager em 275). Mas `BillLineItemSerializer` (linhas **234-240**, `category = CategorySerializer(read_only=True)` em 235) aninha a categoria em cada `line_item` e o prefetch não traz `line_items__category` → N+1. O `overdue` (dashboard_views.py:229-235) repete o queryset SEM o `select_related` de `installment__plan__billing_account` (que `get_account_type` em `serializers.py:402-410`, acesso `obj.installment.plan.billing_account` em **408-409**, precisa) **e** sem `water_statement`/`electricity_statement`. Extrair um helper module-level em `finances/viewsets/` (ou método estático no `BillViewSet`) — ex.: `bill_list_queryset(as_of: date, *, building_id=None)` — que devolve `Bill.objects.with_amounts(as_of).select_related("building","category","billing_account","condominium","water_statement","electricity_statement","installment__plan__billing_account").prefetch_related("line_items__category","allocations")` e usá-lo nos dois pontos (DRY). Para o list path, a única mudança efetiva é `prefetch_related("line_items", ...)` → `prefetch_related("line_items__category", ...)` (o `select_related` do `BillViewSet` já está completo); o ganho maior é no `overdue`, que herda o `installment__plan__billing_account` + `line_items__category` que hoje lhe faltam.

2.2. **`overdue` usa o mesmo helper.** Em `dashboard_views.py:229-235` (queryset inline: `Bill.objects.with_amounts(today_sp()).filter(**overdue_lookup).select_related("building","category","billing_account","condominium").prefetch_related("line_items","allocations").order_by("due_date")`), substituir pelo helper do 2.1 mantendo o `.filter(**overdue_lookup).order_by("due_date")` específico do overdue. Efeito colateral aceitável: o `select_related` do overdue passa a incluir também `water_statement`/`electricity_statement` (inócuo, e mais correto).

### Passo 3 — `/api/rent-payments/` serializer enxuto (ALTO→MÉDIO, legado mínimo)

3.1. `RentPaymentViewSet.get_queryset` (financial_views.py:**425-428**) faz `select_related` só de `lease`/`lease__apartment`/`lease__apartment__building`/`lease__responsible_tenant`, mas `RentPaymentSerializer` (serializers.py:**1104-1105**, `lease = LeaseSerializer(read_only=True)` em 1105) aninha `LeaseSerializer` completo, que por sua vez aninha `ApartmentSerializer` (serializers.py:**140-178**: owner via `PersonSimpleSerializer` em 149, furnitures M2M, `active_lease` SMF em 157 → `get_active_lease` em 180-186 → `obj.leases.all()` → `LeaseNestedForApartmentSerializer` em 118-137, `responsible_tenant` em 121), `tenants` M2M, `resident_dependent` etc. — dezenas de queries por linha. Como o módulo financeiro pessoal é DEPRECATED, a correção é **mínima e cirúrgica**: criar `RentPaymentSlimSerializer` em `core/serializers.py` (não existe hoje — grep confirmado) com apenas os campos que a tela de admin/relatório de pagamentos precisa (`id`, `reference_month`, `amount_paid`, `payment_date`, `notes`, e uma referência leve do lease/apartment via `TenantSimpleSerializer`/string `f"Apto {number}"` — espelhar o que o frontend consome). Usar esse serializer no `RentPaymentViewSet` (e ajustar o `get_queryset` para o `select_related` mínimo correspondente). NÃO criar serializer enxuto para o portal do inquilino aqui (isso pertence a P3.x/segurança — fora de escopo).

### Passo 4 — Prefetches mortos/faltantes em `leases`/`apartments` (ALTO→MÉDIO)

4.1. **`LeaseViewSet.get_queryset`** (views.py:**333-385**; deslocado por P4.1, que adicionou `perform_create`/`perform_update` em ~288-297): `tenants` é serializado por `TenantSummarySerializer` (fields = `id,name,cpf_cnpj,phone,due_day`) que NÃO lê `dependents` nem `furnitures` → remover `"tenants__dependents"` (**366**) e `"tenants__furnitures"` (**367**) do `prefetch_related` (bloco 364-370) — prefetches mortos. Adicionar ao `select_related` (bloco **348-353**, hoje `apartment`/`apartment__building`/`responsible_tenant`/`resident_dependent`, **sem** owner) e ao `prefetch_related` os FALTANTES que o `ApartmentSerializer` aninhado lê: `"apartment__owner"` (ao `select_related`, pois `ApartmentSerializer.owner` usa `PersonSimpleSerializer`) e `"apartment__leases__responsible_tenant"` (ao `prefetch_related`, pois `ApartmentSerializer.get_active_lease` → `obj.leases.all()` → `LeaseNestedForApartmentSerializer.responsible_tenant`). Manter `apartment__furnitures` (368), `tenants` (365), `rent_adjustments` (369).

4.2. **`ApartmentViewSet.get_queryset`** (views.py:**136-177**): hoje `select_related("building").prefetch_related("furnitures", "leases")` no bloco **148-151** — falta `owner`. `ApartmentSerializer` lê `owner` (PersonSimpleSerializer) e `active_lease` (→ `obj.leases.all()` → `LeaseNestedForApartmentSerializer.responsible_tenant`). Trocar `select_related("building")` por `select_related("building", "owner")` (linha 148) e adicionar `"leases__responsible_tenant"` ao `prefetch_related` (148-151). Manter `building`, `furnitures`, `leases`.

### Passo 5 — Method fields do `Expense`/`ExpenseCategory` sobre prefetch (MÉDIO)

5.1. **`ExpenseSerializer`** (serializers.py:**933-942**): o `ExpenseViewSet.get_queryset` (financial_views.py:**141-144**, `prefetch_related("installments")` na linha 144) já faz o prefetch, mas os 3 method fields fazem `.filter(...).count()` (`get_remaining_installments` em 933-934) / `.aggregate(Sum)` (`get_total_paid` em 936-938, `get_total_remaining` em 940-942) que disparam novas queries ignorando o prefetch. Reescrever para iterar `obj.installments.all()` em Python:
   - `get_remaining_installments` → `sum(1 for i in obj.installments.all() if not i.is_paid)`
   - `get_total_paid` → `str(sum((i.amount for i in obj.installments.all() if i.is_paid), Decimal(0)))`
   - `get_total_remaining` → `str(sum((i.amount for i in obj.installments.all() if not i.is_paid), Decimal(0)))`
   Mantém a mesma saída (string Decimal) sobre o cache do prefetch.

5.2. **`ExpenseCategorySerializer`** (serializers.py:**821-823**, `get_subcategories` usa `obj.subcategories.all()` na 822): adicionar `.prefetch_related("subcategories", "subcategories__subcategories")` ao `ExpenseCategoryViewSet` (hoje `queryset = ExpenseCategory.objects.all()` como **atributo de classe na linha 94** — substituir por um `get_queryset` ou anexar o prefetch ao atributo). Como a recursão tem profundidade prática 2 (categoria→subcategoria), prefetchar 2 níveis cobre o caso real. `get_subcategories` passa a ler do prefetch.

### Passo 6 — Memoizar `_components` (MÉDIO)

6.1. Em `finances/services/condo_balance_service.py`, `_components(year, month, building_id)` está em **224-277** (`@staticmethod` em 224; `building_id` é **posicional obrigatório, sem default** — diferente de `result_of_month`/`cash_change_of_month`/`_wedge_residual`, que defaultam `building_id=None`). Seus chamadores são: `result_of_month` (**77**), `competence_pontas` (**92**), `cash_change_of_month` (**105**) e `_wedge_residual` (**370**). `overview` (**187-220**) **não** chama `_components` diretamente — alcança-o transitivamente via `result_of_month`, `cash_change_of_month`, `cash_balance` (walk de N meses → `cash_change_of_month` → `_components`) e `_wedge_residual`. **Crucial:** `CondoProjectionService.project` chega a `_components` via `competence_pontas` (92) e via o walk de caixa, então a memoização tem de ser limpa em **ambos** os entry points (`overview` E `project`). Memoizar `_components` por chamada. KISS: como `_components` é `@staticmethod` puro de leitura, envolvê-lo com `functools.lru_cache` no nível do módulo NÃO serve (não invalida entre requests). Em vez disso, introduzir um cache por-execução: manter `_components` e adicionar um wrapper memoizado via `functools.lru_cache(maxsize=None)`, com `cache_clear()` chamado no topo de `overview` E de `CondoProjectionService.project`. A chave `(year, month, building_id)` é inequívoca (os 3 são hashable e `building_id` é sempre passado explicitamente — sem mismatch posicional/kwarg). Documentar que a memoização é válida porque dentro de uma única request os dados não mudam (read-only, single transaction). Garantir thread-safety usando `lru_cache` (thread-safe para leitura) e limpando no entry point — aceitável para o tráfego admin baixo do módulo.

> Nota de implementação: confirmar com `assertNumQueries` o número de queries de `overview` antes (baseline) e depois (deve cair de ~5N para ~N+constante). Se `lru_cache` + `cache_clear` provar frágil sob concorrência nos testes, fallback para passar um `components_cache: dict[tuple, _Components]` explícito como parâmetro opcional pelos métodos internos (mais verboso mas determinístico). Escolher a opção que passar no gate sem warnings.

### Passo 7 — Batch de `BillSkip` na projeção (MÉDIO)

7.1. `CondoProjectionService._projected_expenses` (**158-215**) chama `BillGenerationService.is_account_eligible(account, month_start)` (bill_generation_service.py:**50-65**, `.exists()` em 63-65) em **DOIS loops** por mês: o loop de **contas recorrentes** (**178-180** — `for account in accounts: if is_account_eligible(account, reference_month)`) **e** o loop de **embedded** (**206-211** — `for installment in embedded: ... if is_account_eligible(host_account, reference_month)`). Ambos precisam do `skip_index` (o plano antigo enfatizava só o embedded; o loop recorrente é fonte igual ou maior do N+1). O horizonte é **parametrizável 1–36, default 12** (NÃO 36): `project(months: int = 12, ...)` (condo_projection_service.py:55); `DEFAULT_PROJECTION_MONTHS = 12` / `MAX_PROJECTION_MONTHS = 36` em `dashboard_views.py:38-39`; `_validated_months` clampa [1,36]. Logo são N×(meses-solicitados) queries de elegibilidade. Pré-carregar os skips do horizonte **efetivamente solicitado** (`first_month`..`last_month` derivados do arg `months`, não 36 fixo): no início de `project` (ou de `_projected_expenses`), carregar `set((ba_id, ref_month) for ba_id, ref_month in BillSkip.objects.filter(reference_month__gte=first_month, reference_month__lte=last_month).values_list("billing_account_id", "reference_month"))` e passar esse set adiante. Adicionar um parâmetro opcional a `is_account_eligible(account, month_start, *, skip_index: set[tuple[int, date]] | None = None)`: quando `skip_index` é fornecido, checar `(account.id, month_start) not in skip_index` em memória em vez do `.exists()`; quando `None`, manter o comportamento atual (uma query). Isso preserva os call sites de geração `ensure_month_bills` (bill_generation_service.py:82) e `_generate_embedded_lines` (176) — ambos passam `skip_index=None`, mantendo `.exists()` (mesma SSOT de elegibilidade) sem regressão; os dois loops da projeção (179 e 208) passam o set pré-carregado. A tupla do skip é `(account.id, month_start)`, espelhando o lookup `.filter(billing_account=account, reference_month=month_start)`.

## Arquivos a criar / modificar

- `core/services/ipca_service.py` — guard de curto-circuito em `fetch_latest` (passo 1.1).
- `core/services/rent_adjustment_service.py` — remover `IPCAService.fetch_latest()` de `get_eligible_leases` (passo 1.2).
- `core/management/commands/send_finance_alerts.py` — chamar `IPCAService.fetch_latest()` no `handle` (passo 1.3).
- `core/views.py` — **adicionar** `from core.cache import cache_result` (não há import de cache hoje); função module-level `_cached_rent_adjustment_alerts` com `@cache_result`; `rent_adjustment_alerts` (918-932) passa a chamá-la (passo 1.4); ajustar `LeaseViewSet`/`ApartmentViewSet` `get_queryset` (passos 4.1, 4.2 — âncoras 333-385 / 136-177).
- `core/signals.py` — registrar `"dashboard-rent-adjustment-alerts"` em `_PROPERTY_CACHE_PREFIXES` (74-81) e adicionar chaves `"RentAdjustment"`/`"Landlord"` em `_CORE_MODEL_CACHE_PREFIXES` (82-94); acrescentar `_invalidate_core_model_caches("RentAdjustment")` aos receivers de RentAdjustment (468-481); importar `Landlord` (27-49) + par de receivers `Landlord` post_save/post_delete (passo 1.5). NÃO tocar `_TOGGLEABLE_RECEIVERS` (625-628).
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
- `tests/integration/test_rent_adjustment_alerts_cache.py` (novo) — endpoint cacheado: 2ª chamada não recomputa; invalida ao salvar Lease/RentAdjustment/Landlord. **Atenção (P4.2):** `CacheManager.invalidate_pattern` cai em `cache.clear()` no backend LocMem dos testes (`core/cache.py:203-208`), então o teste de invalidação **passaria mesmo com prefixo errado/não-registrado** (tudo é limpo). Assertar que o prefixo está realmente cabeado — spy em `invalidate_pattern` chamado com `"dashboard-rent-adjustment-alerts*"`, ou verificar o registro em `_PROPERTY_CACHE_PREFIXES`/`_CORE_MODEL_CACHE_PREFIXES` — não apenas que a 2ª chamada recomputa.
- `tests/integration/test_bill_api.py` (ou existente do finances) — `assertNumQueries` no list de bills com line_items+categoria não cresce com o nº de bills; idem `overdue`.
- `tests/integration/test_rent_payment_api.py` — `assertNumQueries` constante no list de `/api/rent-payments/` com N pagamentos; payload do `RentPaymentSlimSerializer` não vaza PII de owner.
- `tests/integration/test_lease_api.py` / `test_apartment_api.py` — `assertNumQueries` constante no list com N leases/apartments (prova `apartment__owner`/`active_lease` resolvidos sem N+1).
- `tests/integration/test_expense_api.py` — `assertNumQueries` constante no list de despesas com installments; valores de `total_paid`/`total_remaining` idênticos ao comportamento anterior.
- `tests/unit/test_condo_balance_service.py` — `assertNumQueries` de `overview` cai (memoização) e os valores são idênticos.
- `tests/unit/test_condo_projection_service.py` — `assertNumQueries` de `project(months=…)` não cresce linearmente com o nº de contas (batch de BillSkip); valores idênticos com e sem skip. Cobrir tanto o loop recorrente quanto o embedded; o teste pode usar `months=36` (o teto) para amplificar, mas o default real é 12.

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
- `test_condo_projection_batches_bill_skips` — `project(months=36)` (teto, p/ amplificar) com K contas recorrentes + embedded e alguns skips: `assertNumQueries` não escala com K×meses (1 query de skips, não N×meses); meses pulados refletem o skip corretamente em AMBOS os loops (recorrente 178-180 e embedded 206-211); edge: skip exatamente no mês limite do horizonte. Cobrir também o default `project()` (months=12).
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
- [ ] `CondoProjectionService.project(months)` faz batch de `BillSkip` (1 query de skips, não N×meses) nos DOIS loops (recorrente + embedded); paridade com a versão por-query. Default 12, teto 36.
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
