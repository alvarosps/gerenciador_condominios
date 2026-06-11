# Plano P4.2 — Resiliência de cache + reescrita da invalidação do core

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P4 · **Branch sugerida:** `fix/cache-resilience` · **Depende de:** nenhum

## Objetivo

Tornar a API resiliente a queda do Redis em runtime (hoje, sem degradacao graciosa, qualquer
endpoint cacheado **e** o throttle do DRF — que usa o mesmo cache — devolvem 500, derrubando a
API inteira). Em paralelo, consertar o esquema de invalidacao de cache do `core`, que hoje e
codigo morto: `CacheManager.invalidate_model` gera padroes `*Model*` que nunca casam com as
chaves reais (`dashboard-*`, `cash-flow-*`, `financial-dashboard-*`, `finance-*`). O resultado e
um sistema de invalidacao que invalida zero chaves, mascarado apenas pelos TTLs curtos (120-300s).
Este plano entrega: `IGNORE_EXCEPTIONS:True` no django-redis, invalidacao por prefixos reais
mapeados por model, invalidacao explicita apos bulk updates de pagamento, os 3 models financeiros
faltantes (PersonIncome/CreditCard/ExpenseCategory) e a remocao de codigo morto/enganoso de signals.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO→MEDIO | Sem degradacao graciosa: `cache_result` sem try/except + django-redis sem `IGNORE_EXCEPTIONS` → endpoints cacheados 500; throttle DRF no mesmo cache → API inteira 500 | `core/cache.py:147` · `condominios_manager/settings.py:130-146` | Adicionar `IGNORE_EXCEPTIONS:True` + `DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS` nas OPTIONS |
| MEDIO | `invalidate_model` gera `*Model*` que nunca casa com chaves reais → `invalidate_related_caches` do core e codigo morto | `core/cache.py:210,328-350` · `core/signals.py` (varios) | Reescrever por prefixos reais (como `_invalidate_financial_caches`), via loop unico com `dispatch_uid` |
| MEDIO→BAIXO | Bulk `.update()` em pagamentos nao dispara signals → dashboards mostram divida ja paga (TTL 120-300s) | `core/viewsets/financial_views.py:378` · `core/services/daily_control_service.py:271-278` | Invalidar caches financeiros explicitamente apos cada bulk update |
| MEDIO→BAIXO | Cascata soft-delete `Apartment.delete` via `.update()` nao dispara `sync_apartment_is_rented` → `is_rented` fica `True` sem lease | `core/models.py:436-441` | Iterar `lease.delete(deleted_by=...)` por instancia |
| MEDIO→BAIXO | PersonIncome/CreditCard/ExpenseCategory alimentam caches mas nao tem signal de invalidacao | `core/signals.py:27-49,328-534` | Adicionar os 3 models ao loop de invalidacao financeira |
| BAIXO | `disconnect_all_signals` no-op enganoso; handlers Notification/DeviceToken inocuos; `get_cache_stats` usa `KEYS` bloqueante | `core/signals.py:320,559-590,625-662` · `core/cache.py:306` | Reduzir codigo morto; trocar `keys()` por `scan_iter` |

## Abordagem técnica

Ordem de execucao (cada passo isolado, com teste antes do codigo — TDD Red→Green→Refactor→Verify).

### Passo 1 — Resiliencia: `IGNORE_EXCEPTIONS` no django-redis (ALTO→MEDIO)

`condominios_manager/settings.py:130-146`, dentro do bloco `if _redis_url:`, no dict `OPTIONS`,
adicionar duas chaves (o bloco `else` LocMemCache nao precisa — nunca falha por conexao):

```python
"OPTIONS": {
    "CLIENT_CLASS": "django_redis.client.DefaultClient",
    "IGNORE_EXCEPTIONS": True,
    "CONNECTION_POOL_KWARGS": { ... },   # inalterado
    "SOCKET_CONNECT_TIMEOUT": 5,
    "SOCKET_TIMEOUT": 5,
},
```

E, logo apos o dict `CACHES` (fora do `if/else`), adicionar a flag global do django-redis para
visibilidade:

```python
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True
```

Efeito: com Redis fora do ar em runtime, `cache.get()` retorna `None` (cache miss → executa a
funcao e serve do banco) e `cache.set()` vira no-op, logando a excecao em vez de propagar. Cobre
**os dois** caminhos: o decorator `cache_result` (`core/cache.py:147`) e o backend de cache que o
throttle do DRF (`AnonRateThrottle`/`UserRateThrottle`, `settings.py:229-238`) usa internamente.
Nao mexer no `cache_result` — `IGNORE_EXCEPTIONS` no backend e a solucao de raiz; envolver o
wrapper em try/except seria redundante e nao cobriria o throttle.

Nota sobre `get_redis_connection`: `CacheManager.invalidate_pattern`/`get_cache_stats` chamam
`get_redis_connection("default")` diretamente (fora do backend), e ja estao envolvidos em
`try/except Exception` proprio (`core/cache.py:236-255`, `290-325`) — portanto a queda do Redis
nesses caminhos ja e tolerada (retornam 0/dict vazio). Confirmar isso no teste, sem alterar.

### Passo 2 — Reescrever a invalidacao do core por prefixos reais (MEDIO)

O mapeamento real chave→prefixo (confirmado por grep em `core/services/*`):

| Model core | Prefixos cacheados afetados |
| --- | --- |
| Building | `dashboard-financial-summary`, `dashboard-lease-metrics`, `dashboard-building-stats`, `dashboard-late-payment`, `dashboard-tenant-stats`, `cash-flow-projection`, `finance-dashboard`, `finance-projection` |
| Apartment | idem Building (entra em todos os dashboards de imovel + revenue/projection) |
| Lease | idem Building |
| Tenant | `dashboard-financial-summary`, `dashboard-lease-metrics`, `dashboard-tenant-stats`, `dashboard-late-payment` |
| Furniture | `dashboard-financial-summary`, `dashboard-lease-metrics` (entram em contratos/listas, mas nao em revenue) |
| Dependent | `dashboard-tenant-stats` |
| PaymentProof | `dashboard-late-payment` |

Implementacao em `core/signals.py`:

1. Definir um mapa nomeado no topo (apos `_FINANCE_CACHE_PREFIXES`):
   `_CORE_MODEL_CACHE_PREFIXES: dict[str, tuple[str, ...]]` com uma entrada por nome de model.
2. Criar um helper unico `_invalidate_core_model_caches(model_name: str) -> None` que faz
   `for prefix in _CORE_MODEL_CACHE_PREFIXES.get(model_name, ()): CacheManager.invalidate_pattern(f"{prefix}*")`.
   Usar `f"{prefix}*"` (glob `<prefix>*`), NUNCA `<prefix>:*` — as chaves sao hifenizadas
   (`dashboard-lease-metrics`), o `:` nunca casa (mesma armadilha ja documentada em
   `core/signals.py:318-319` e `finances/cache.py:5-9`).
3. Substituir TODAS as chamadas `invalidate_related_caches(instance, related_models=[...])` nos
   receivers de Building/Apartment/Tenant/Lease/Furniture/Dependent/PaymentProof e nos 3
   `m2m_changed` por `_invalidate_core_model_caches("<ModelName>")`.
4. **Remover** `invalidate_related_caches` de `core/cache.py:328-350` (e o import em
   `core/signals.py:26`) — vira morto apos a reescrita. Sem re-export, sem shim (regra de design).
5. **Remover** `CacheManager.invalidate_model` de `core/cache.py:192-211` — so era usado por
   `invalidate_related_caches` e pelos handlers Notification/DeviceToken (removidos no Passo 6).
   Confirmar com grep que nao restam consumidores antes de remover.

Manter `CacheManager.invalidate_pattern` (e o nucleo usado por tudo). O `_invalidate_financial_caches`
(`core/signals.py:315-325`) e `_invalidate_finance_module_caches` (`:62-65`) ja seguem este padrao
e ficam como referencia — nao reescrever, apenas reusar.

### Passo 3 — Invalidacao explicita apos bulk `.update()` de pagamento (MEDIO→BAIXO)

`.update()` de queryset nao dispara `post_save`, entao os dois caminhos bulk de pagamento legados
nao invalidam nada. Extrair a invalidacao financeira para um ponto reusavel e chama-la:

1. Em `core/signals.py`, o helper `_invalidate_financial_caches(model_name, pk)` ja existe
   (`:315-325`). Criar uma versao publica sem args de log para reuso fora dos signals, OU expor
   uma funcao `invalidate_legacy_financial_caches() -> None` no proprio modulo de signals que
   chama os mesmos `invalidate_pattern` (`daily-control*`, `cash-flow*`, `financial-dashboard*`)
   + `_invalidate_finance_module_caches()`. Preferir esta segunda (sem `pk`/`model_name` falsos).
2. `core/viewsets/financial_views.py` — `ExpenseInstallmentViewSet.bulk_mark_paid` (`:357-386`):
   apos `installments.update(is_paid=True, paid_date=paid_date)` (`:378`), dentro do
   `with transaction.atomic()`, chamar `invalidate_legacy_financial_caches()`.
3. `core/services/daily_control_service.py` — `_mark_credit_card_paid` (`:264-282`): apos
   `count = unpaid.update(...)` (`:278`), chamar `invalidate_legacy_financial_caches()` (so quando
   `count > 0`). Importar de `core.signals` (Views→Services pode importar signals; signals nao
   importa services — direcao mantida).

Nota de arquitetura: a logica de negocio fica no service; a invalidacao e efeito-colateral de
cache, aceitavel no service/viewset por ser o ponto onde o `.update()` ocorre. Modulo legado —
correcao pontual, sem refatorar a action inteira.

### Passo 4 — Cascata soft-delete de Apartment dispara signals (MEDIO→BAIXO)

`core/models.py:429-443` — `Apartment.delete`: trocar o bulk
`self.leases.filter(is_deleted=False).update(is_deleted=True, deleted_at=..., deleted_by=...)`
por iteracao que chama `SoftDeleteMixin.delete` por instancia:

```python
if not hard_delete:
    for lease in self.leases.filter(is_deleted=False):
        lease.delete(hard_delete=False, deleted_by=deleted_by)
```

Assim cada `lease.delete()` aciona `post_delete`? Nao — soft-delete vai por `save()` →
`post_save` (`sync_apartment_is_rented`, `core/signals.py:193-198`), que recomputa
`is_rented` via `Exists(...)`. Como todas as leases ficam deletadas, o `Exists` retorna `False`
e `is_rented` cai para `False` corretamente. Volume e minimo (OneToOne na pratica). Mesmo padrao
ja usado em `Building.delete` (`core/models.py:302-304`), que itera `apartment.delete()`.

`PersonPaymentScheduleService.bulk_configure` (citado no digest) usa modulo legado/deprecated; se
o escopo permitir, incluir `deleted_at=timezone.now()` + `deleted_by` no `.update()` e chamar
`invalidate_legacy_financial_caches()`. Caso contrario, deixar fora deste plano (registrar como
follow-up no Handoff) — nao bloquear.

### Passo 5 — Adicionar PersonIncome, CreditCard, ExpenseCategory ao loop financeiro (MEDIO→BAIXO)

Converter a secao de signals financeiros legados de `core/signals.py:328-534` (Person,
PersonPayment, PersonPaymentSchedule, ExpenseMonthSkip, Expense, ExpenseInstallment, Income,
EmployeePayment — os de invalidacao "pura" via `_invalidate_financial_caches`) para o padrao de
loop de `finances/signals.py:36-73` (tupla `_LEGACY_FINANCIAL_MODELS` + `post_save`/`post_delete`
`.connect(..., dispatch_uid=...)`), incluindo os **3 models faltantes**: `PersonIncome`,
`CreditCard`, `ExpenseCategory`.

Importante — NAO mover para o loop os receivers que tem logica extra alem da invalidacao
financeira pura (eles precisam continuar receivers individuais):
- `RentPayment` (`:413-424`) — chama `_invalidate_rent_payment_caches` + `dashboard-late-payment*`.
- `FinancialSettings` (`:427-435`) — + `dashboard-late-payment*`.
- `RentAdjustment` (`:438-451`), `MonthSnapshot` (`:454-467`) — chamam so
  `_invalidate_finance_module_caches` (subconjunto), nao `_invalidate_financial_caches`.

O loop cobre apenas os models cujo unico efeito e `_invalidate_financial_caches(name, pk)`. A
funcao do loop nao recebe `pk` util (o `pk` so vai para log), entao a assinatura
`(sender, instance, **kwargs)` igual a `finances/signals.py:56-60` serve. Adicionar import de
`PersonIncome`, `CreditCard`, `ExpenseCategory` em `core/signals.py` (ja importa de `.models`).

### Passo 6 — Reduzir codigo morto/enganoso de signals + `scan_iter` (BAIXO)

1. `core/cache.py:306` — `get_cache_stats`: trocar `len(redis_client.keys(pattern))` por contagem
   via `sum(1 for _ in redis_client.scan_iter(match=pattern, count=100))` (nao-bloqueante,
   consistente com `invalidate_pattern` que ja usa `scan`). Mantem a semantica (contagem de chaves
   com prefixo), sem `KEYS` O(N) bloqueante em prod.
2. `core/signals.py:559-590` — handlers `Notification`/`DeviceToken`: chamam
   `CacheManager.invalidate_model("Notification"/"DeviceToken", pk)`, que (a) sera removido no
   Passo 2 e (b) nunca casou com chave alguma (esses endpoints nao sao cacheados). **Remover** os
   4 receivers + os imports `Notification`, `DeviceToken` se nao usados em outro lugar do arquivo.
   Confirmar com grep que nenhum `@cache_result` keia em `Notification`/`DeviceToken`.
3. `core/signals.py:625-662` + `:598-622` — `disconnect_all_signals`/`connect_all_signals`: o
   proprio comentario admite que so o par `sync_apartment_is_rented` e realmente
   desconectado/reconectado (Django keia em `(receiver, sender)`; os `disconnect(sender=X)` sem
   receiver explicito sao no-ops). Renomear para o que realmente fazem — ex.:
   `disable_is_rented_sync()` / `enable_is_rented_sync()` — e enxugar `disconnect_all_signals`
   para desconectar APENAS os 2 receivers de `_TOGGLEABLE_RECEIVERS`, removendo os ~20
   `disconnect(sender=...)` no-op. Atualizar TODOS os consumidores (grep
   `disconnect_all_signals|connect_all_signals` em `tests/` e `conftest.py`) para os novos nomes —
   refactor completo, sem alias.

## Arquivos a criar / modificar

- `condominios_manager/settings.py` — Passo 1: `IGNORE_EXCEPTIONS:True` nas OPTIONS do Redis +
  `DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True`.
- `core/cache.py` — Passo 2: remover `invalidate_model` e `invalidate_related_caches`; Passo 6:
  `get_cache_stats` usa `scan_iter`.
- `core/signals.py` — Passos 2,3,4(import),5,6: mapa `_CORE_MODEL_CACHE_PREFIXES` + helper
  `_invalidate_core_model_caches`; substituir chamadas `invalidate_related_caches`; funcao publica
  `invalidate_legacy_financial_caches`; loop `_LEGACY_FINANCIAL_MODELS` (com os 3 novos models);
  remover handlers Notification/DeviceToken; renomear/enxugar disconnect/connect; ajustar imports.
- `core/models.py` — Passo 4: `Apartment.delete` itera `lease.delete()` por instancia.
- `core/viewsets/financial_views.py` — Passo 3: `bulk_mark_paid` chama invalidacao apos `.update()`.
- `core/services/daily_control_service.py` — Passo 3: `_mark_credit_card_paid` invalida apos `.update()`.
- `tests/unit/test_cache.py` — testes de resiliencia + `scan_iter` em `get_cache_stats`.
- `tests/unit/test_signals.py` — testes de invalidacao por prefixo real + loop com 3 novos models +
  remocao de handlers + rename disconnect/connect.
- `tests/integration/` (novo `test_cache_resilience.py`) — endpoint serve do banco com Redis fora.
- `tests/unit/test_models.py` (ou `test_lease_signal.py`) — regressao `is_rented` apos
  `Apartment.delete`.
- `conftest.py` / fixtures que usem `disconnect_all_signals`/`connect_all_signals` — atualizar nomes.

## TDD — cenários de teste

### Backend — resiliencia (regressao que prova o bug)
- `test_cached_endpoint_serves_from_db_when_redis_down` — com `IGNORE_EXCEPTIONS:True` e
  `get_redis_connection` (fronteira externa) simulando `ConnectionError` no `get`/`set`, um GET em
  `/api/dashboard/financial_summary/` retorna 200 com dados do banco, nao 500.
- `test_throttle_does_not_500_when_redis_down` — com a mesma falha de conexao, uma request
  autenticada nao estoura 500 pelo `UserRateThrottle` (throttle no mesmo cache degrada gracioso).
- `test_cache_set_is_noop_on_redis_failure` — `cache.set` com Redis fora nao propaga excecao
  (verifica o efeito de `IGNORE_EXCEPTIONS`, fronteira `get_redis_connection` mockada).
- `test_invalidate_pattern_returns_zero_on_redis_failure` — confirma o try/except existente
  (`core/cache.py:249-251`) continua tolerante (sem regressao).

### Backend — invalidacao por prefixo real (prova o codigo morto)
- `test_lease_save_invalidates_dashboard_prefixes` — apos `lease.save()`, chaves sob
  `dashboard-lease-metrics*`, `dashboard-financial-summary*`, `cash-flow-projection*`,
  `finance-dashboard*` sao deletadas (semeadas antes via `cache.set`). Sem mock de internals —
  exercita o signal real.
- `test_apartment_save_invalidates_building_stats` — `dashboard-building-stats*` invalidado.
- `test_tenant_save_invalidates_tenant_stats_not_building_revenue` — `dashboard-tenant-stats*`
  invalidado; chave de `dashboard-building-stats*` NAO (mapa por model respeitado).
- `test_invalidate_uses_glob_star_not_colon` — garante `<prefix>*` (regressao da armadilha do `:`).
- `test_invalidate_model_and_related_removed` — `CacheManager` nao tem mais `invalidate_model`;
  `core.cache` nao exporta `invalidate_related_caches` (codigo morto removido).

### Backend — bulk update invalida cache (prova staleness pos-pagamento)
- `test_bulk_mark_paid_invalidates_financial_caches` — semear `financial-dashboard-overview*`,
  `cash-flow*`, `finance-dashboard*`; chamar `bulk_mark_paid` com pagamento PARCIAL (nem todas as
  parcelas do Expense); as chaves sao invalidadas (hoje, falha — bug vivo).
- `test_mark_credit_card_paid_invalidates_financial_caches` — idem via
  `DailyControlService.mark_item_paid("credit_card", ...)`.

### Backend — cascata soft-delete (prova is_rented quebrado)
- `test_apartment_delete_sets_is_rented_false` — apto com lease ativa; `apartment.delete()`;
  recarregar → `is_rented is False` (hoje fica `True` — regressao do bug).
- `test_apartment_delete_then_restore_not_falsely_rented` — delete + `restore()`; `is_rented`
  permanece `False` (nao ha lease ativa).

### Backend — 3 models faltantes
- `test_person_income_save_invalidates_financial_caches` — criar/desativar `PersonIncome` invalida
  `financial-dashboard-summary*`/`cash-flow-projection*`.
- `test_credit_card_save_invalidates_financial_caches`.
- `test_expense_category_save_invalidates_financial_caches`.
- `test_legacy_financial_models_loop_covers_all` — itera `_LEGACY_FINANCIAL_MODELS` e confirma que
  cada um tem receiver conectado com `dispatch_uid` (sem model esquecido).

### Backend — codigo morto / scan_iter
- `test_get_cache_stats_uses_scan_not_keys` — `get_cache_stats` nao chama `redis_client.keys`
  (verificar via fronteira: `keys` levantaria se chamado; `scan_iter` semeado retorna a contagem).
- `test_disable_is_rented_sync_round_trip` — `disable_is_rented_sync()` desliga
  `sync_apartment_is_rented`; `enable_is_rented_sync()` restaura (idempotente).
- `test_notification_device_token_handlers_removed` — nenhum receiver conectado para
  `Notification`/`DeviceToken` (handlers inocuos removidos).

(Sem testes de frontend — mudanca puramente backend/infra; nenhum contrato FE↔API alterado.)

## Migrations / dados

N/A — nenhuma alteracao de schema, nenhuma tabela nova (sem RLS a habilitar), nenhum dado vivo a
corrigir. Mudancas sao de configuracao (settings), logica de signals/cache e um metodo de model.
Sem necessidade de `python scripts/backup_db.py` (nao ha migrate destrutivo).

## Constraints (o que NÃO fazer)

- NAO envolver o wrapper de `cache_result` em try/except — `IGNORE_EXCEPTIONS` no backend e a raiz
  e cobre tambem o throttle do DRF (que o try/except no decorator nao cobriria).
- NAO refatorar a logica de negocio das actions `mark_paid`/`bulk_mark_paid` (modulo financeiro
  pessoal legado/DEPRECATED) — apenas adicionar a invalidacao apos o `.update()`.
- NAO adicionar policies RLS, NAO mexer em `page_size` (falsos positivos conhecidos).
- NAO inverter a direcao de dependencia: `core/signals.py` NAO importa `finances` (literais
  duplicados `_FINANCE_CACHE_PREFIXES` sao intencionais, travados por teste).
- NAO criar re-exports/shims/aliases ao remover `invalidate_model`/`invalidate_related_caches`/
  renomear `disconnect_all_signals` — refactor completo, todos os consumidores atualizados.
- NAO usar `# noqa`/`# type: ignore`/`eslint-disable`; sem `from __future__ import annotations`.
- NAO usar `redis_client.keys()` em nenhum caminho sincrono novo — sempre `scan`/`scan_iter`.
- NAO mockar ORM/services internos nos testes — mockar SO `get_redis_connection` (fronteira externa).

## Critérios de aceite (binários)

- [ ] `condominios_manager/settings.py` tem `IGNORE_EXCEPTIONS:True` nas OPTIONS do Redis e
  `DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True`.
- [ ] Com Redis simulado fora do ar, GET em endpoint cacheado retorna 200 (serve do banco), nao 500.
- [ ] `CacheManager.invalidate_model` e `core.cache.invalidate_related_caches` nao existem mais
  (grep retorna zero).
- [ ] Cada receiver core (Building/Apartment/Tenant/Lease/Furniture/Dependent/PaymentProof + m2m)
  invalida os prefixos reais mapeados; nenhum padrao `*Model*` remanescente em `core/signals.py`.
- [ ] `bulk_mark_paid` e `_mark_credit_card_paid` invalidam caches financeiros apos o `.update()`.
- [ ] `Apartment.delete()` deixa `is_rented=False` (apto sem lease ativa).
- [ ] PersonIncome, CreditCard, ExpenseCategory tem signal de invalidacao via loop com `dispatch_uid`.
- [ ] `get_cache_stats` usa `scan_iter`, nao `keys`.
- [ ] `disconnect_all_signals`/`connect_all_signals` renomeados para o escopo real; consumidores
  (conftest/tests) atualizados; handlers Notification/DeviceToken removidos.
- [ ] Todos os cenarios de teste acima passam; cobertura dos arquivos editados nao regride.
- [ ] Gate de verificacao limpo (zero erros E zero warnings).

## Gate de verificação

Escopado nos arquivos editados + regressao dirigida (a suite cheia tem flakiness pre-existente de
xdist/Redis — nao bloqueia):

```bash
ruff check core/cache.py core/signals.py core/models.py core/viewsets/financial_views.py core/services/daily_control_service.py condominios_manager/settings.py
ruff format --check core/cache.py core/signals.py core/models.py core/viewsets/financial_views.py core/services/daily_control_service.py
mypy core/
pyright
python -m pytest tests/unit/test_cache.py tests/unit/test_signals.py tests/unit/test_models.py tests/unit/test_lease_signal.py tests/integration/test_cache_resilience.py -p no:xdist
# regressao dirigida do financeiro legado afetado:
python -m pytest tests/unit/test_financial tests/unit/test_finances -p no:xdist
```

Frontend: N/A (sem mudanca de FE).

## Handoff

- Commit sugerido:

  ```
  fix(cache): graceful Redis degradation + rewrite core invalidation by real key prefixes

  - django-redis IGNORE_EXCEPTIONS so a Redis outage no longer 500s cached
    endpoints nor the shared DRF throttle (API-wide outage -> graceful miss)
  - replace dead *Model* invalidation with real prefix map per core model
  - invalidate financial caches after bulk .update() pay paths (no stale debt)
  - Apartment.delete cascades via lease.delete() so is_rented stays correct
  - add PersonIncome/CreditCard/ExpenseCategory to the financial invalidation loop
  - get_cache_stats uses scan_iter; drop dead Notification/DeviceToken handlers;
    rename disconnect/connect to the real is_rented-sync toggle

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

- Atualizar `MEMORY.md`: registrar que a invalidacao do core agora e por prefixo real e que o
  Redis degrada gracioso (IGNORE_EXCEPTIONS) — referenciar este plano.
- Follow-up opcional (fora de escopo se nao couber no Passo 4): `PersonPaymentScheduleService.bulk_configure`
  ainda usa `.update()` sem `deleted_at`/`deleted_by` nem invalidacao — corrigir no proximo plano
  do modulo legado.
- Proximo plano pode assumir: invalidacao de cache do core funcional e mapeada; Redis nao e mais
  single point of failure de disponibilidade; padrao de loop com `dispatch_uid` consolidado tanto
  em `finances/signals.py` quanto na secao financeira legada de `core/signals.py`.
