# Sessão 37 — Backend serviços: `BillGenerationService` (recorrentes + seed) + `BillService.create_with_lines` + `BillPaymentService` + cache cross-app

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → **37** → 38 → 39 → 40 → 41 → … → 50 (ainda Fase 2)
> Esta sessão cria os **serviços de contas a pagar** sobre os modelos da S36: geração idempotente das contas recorrentes do mês + seed "pago até X" (atrasados visíveis), orquestração `Bill`+`BillLineItem` no serviço, e pagamento parcial/total com guarda de over-allocation. Cria também o **bloco único de constantes de prefixo de cache** (`finance-*`), o `finances/signals.py` real (receivers nos modelos do `finances`) e os **receivers cross-app NET-NEW** em `Apartment`/`Lease` + a extensão de `_invalidate_financial_caches` (RentPayment/FinancialSettings). Adiciona o helper read aditivo `RentScheduleService.received_collectible_total`. **Sem serializers/viewsets/API (S38); sem installment/folha na geração (Fase 3); sem reserva real (Fase 4).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.1, §4.4, §4.8, §8 "BillGenerationService"/"BillService.create_with_lines"/"BillPaymentService", §11 cache cross-app, §13 migrações, §14 Fase 2, §18 edge-cases "Datas/geração" + "Pagamento" + "Cross-app cache")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Service stateless só com `@staticmethod`, `Decimal`, `transaction.atomic`+`select_for_update`, msgs PT / logs EN** | `core/services/rent_schedule_service.py:61-62` (classe) + `toggle_payment` em `:380-445` (`transaction.atomic()` :399, `select_for_update()` :401/:407, retorno `{status, ...}` PT, `logger.info(...)` EN) | **Estrutura-base** dos 3 serviços novos. Copiar o idioma de lock + retorno + log. **Não** reimplementar o que já existe — `BillPaymentService` é o análogo de saída do `toggle_payment` |
| `clamp_due_day` (reuso DIRETO — gerador de datas puro) | `core/services/rent_schedule_service.py:64-83` (`@staticmethod clamp_due_day(due_day, year, month) -> int`, `calendar.monthrange`, ex.: 31 em fev→28) | O **gerador de datas** do `BillGenerationService` reusa ESTE método (31→último dia). **Não** recriar clamp; importar `RentScheduleService` |
| `received_total` (forma do helper read aditivo a clonar) | `core/services/rent_schedule_service.py:367-378` (`@staticmethod received_total(reference_month, building_id=None) -> Decimal`, `RentPayment.objects.filter(reference_month=...)`, `Sum("amount_paid")`, `or ZERO`) | **Espelho** de `received_collectible_total` (mesma forma, mas pré-filtrado por `collectible_leases`) — ver §"received_collectible_total" |
| `collectible_leases` (consumido pelo helper aditivo) | `core/services/rent_schedule_service.py:142-191` | `received_collectible_total` soma só `RentPayment` de leases em `collectible_leases(reference_month, building_id)` (design §4.5) |
| **`Bill.objects.with_amounts(today)` (annotations — NÃO recomputar em Python)** | `finances/models.py` (S36 — `BillQuerySet.with_amounts`, `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue`) | `BillPaymentService` lê `amount_remaining`/`amount_total` daqui para validar over-allocation. **Nunca** somar linhas/alocações em Python no serviço |
| **Unique parcial `(billing_account, competence_month)` (base da idempotência)** | `finances/models.py` (S36 — `Bill.Meta`, `condition=Q(is_deleted=False, billing_account__isnull=False)`) | `ensure_month_bills` repousa nesta unique para `get_or_create` race-safe / tolerar `IntegrityError` |
| **`BillSkip` sem soft-delete (consulta de skip)** | `finances/models.py` (S36 — `BillSkip.objects.filter(billing_account, reference_month)`) | A geração pula o mês quando existe `BillSkip` |
| `_invalidate_financial_caches` (ESTENDER aqui — DRY) | `core/signals.py:292-299` (glob `<prefix>*`, hífen não dois-pontos; comentário :295-296 explica) + chamadas RentPayment `:356-366`, FinancialSettings `:383-391` | Esta sessão **estende** este helper para invalidar `finance-*` (RentPayment/FinancialSettings já passam por aqui — DRY) |
| **Receivers Apartment/Lease (model-key, SEM hook financeiro — NET-NEW aqui)** | `core/signals.py:87-110` (Apartment save/delete → `invalidate_related_caches(..., ["Building", "Lease"])`) + `:173-184` (Lease post_save `sync_apartment_is_rented`) | Apartment/Lease **não** invalidam `finance-*` hoje (design §11 "NET-NEW, não additivo"). Adicionar a invalidação `finance-*` nesses fluxos (owner muda receita/projeção) |
| `CacheManager.invalidate_pattern` (montagem do glob) | `core/cache.py:213-255` (`full_pattern = f"{key_prefix}:1:{pattern}"` :239; LocMem → `cache.clear()` :230-235) | O bloco de prefixos `finance-*` alimenta este glob. Hífen-prefixado (não `:`) — espelhar o comentário de `:295-296` |
| `finances/signals.py` (stub da S34 — preencher) | `finances/signals.py` (S34: só docstring, zero receivers — ver SESSION_STATE S34) + `core/signals.py:1-53` (idioma de imports/`@receiver`/`logger`) | A S34 deixou o stub; esta sessão adiciona os receivers reais dos modelos do `finances`. `FinancesConfig.ready()` (S34) já o importa |
| Helper TZ SP (rotear "hoje/mês atual") | `finances/services/timezone.py` (S34: `today_sp()`, `current_month_sp()`, `SAO_PAULO_TZ`) | **Todos** os serviços do `finances` roteiam "hoje/mês atual" por aqui (design §4). `ensure_month_bills`/`BillPaymentService` usam `today_sp()` para `is_overdue` e defaults |
| Factories `finances` (S36) | `tests/factories.py` (S36: `make_finance_category`, `make_billing_account`, `make_bill`, `make_bill_line_item`, `make_bill_skip`, `make_payment`, `make_payment_allocation`) + `make_condominium`/`make_building` (S34) | Dados dos testes desta sessão. **Não** criar factory nova salvo necessidade real (KISS) |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **só `freezegun`**; ORM/serviços/`RentScheduleService` reais |

### O que a S34/S35/S36 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S34**: app `finances` + `FinancesConfig.ready()` importando `finances/signals.py` (stub) + `core.Condominium`(padrão) + `Building.condominium` + helper TZ `finances/services/timezone.py` + gate ampliado + `make_condominium`/`make_building`.
- **S36**: `finances/models.py` com `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`; enums `BillBehavior`/`BillLifecycleState`/`BillingAccountState`/`FundedFrom`; `Bill.objects.with_amounts(today)` (annotations); unique parcial `(billing_account, competence_month)`; migração inicial + RLS; 7 factories.

> **Se a S36 não estiver concluída, PARE.** Esta sessão depende dela (DEPENDENCY ORDER 36→37). Não recriar modelos/migração aqui.

---

## Escopo

### Arquivos a criar
- `finances/services/bill_generation_service.py` — `BillGenerationService` (`ensure_month_bills` + gerador de datas puro).
- `finances/services/bill_service.py` — `BillService` (`create_with_lines`).
- `finances/services/bill_payment_service.py` — `BillPaymentService` (`pay`, estorno via soft-delete).
- `finances/cache.py` — **bloco único** de constantes de prefixo (`FINANCE_DASHBOARD_PREFIX`, `FINANCE_CASH_FLOW_PREFIX`, `FINANCE_PROJECTION_PREFIX`) + helper `invalidate_finance_caches()` (fonte única consumida por signals e, futuramente, pelo `@cache_result` da S40/S41).
- `tests/unit/test_finances/test_bill_generation_service.py` — testes do gerador.
- `tests/unit/test_finances/test_bill_service.py` — testes do `create_with_lines`.
- `tests/unit/test_finances/test_bill_payment_service.py` — testes do pagamento.
- `tests/unit/test_finances/test_finance_cache_signals.py` — testes de invalidação (finances + cross-app).

### Arquivos a modificar
- `finances/signals.py` — preencher o stub da S34: `post_save`/`post_delete` nos modelos do `finances` (`Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`) chamando `invalidate_finance_caches()`. Imports diretos da fonte (`finances.models`, `finances.cache`).
- `core/signals.py` — (1) **estender** `_invalidate_financial_caches` (`:292-299`) para invalidar também os prefixos `finance-*` (importar de `finances.cache` — `core → finances` é OK para signals/cache cross-app? **NÃO**: ver §"Direção do import cross-app"); (2) adicionar invalidação `finance-*` nos receivers de `Apartment` (`:87-110`) e `Lease` (post_save/post_delete) — NET-NEW (design §11).
- `core/services/rent_schedule_service.py` — adicionar `@staticmethod received_collectible_total(reference_month, building_id=None) -> Decimal` (helper read **aditivo**, espelhando `received_total` `:367-378` mas pré-filtrado por `collectible_leases`). **Nenhuma** assinatura existente alterada.
- `tests/factories.py` — só se faltar alguma factory para os testes (improvável; a S36 cobriu as 7). Não duplicar.

### NÃO fazer (pertence a outras sessões)
- **Nenhum serializer, viewset, URL ou ação de API** (`bills/`, `bills/create_with_lines`, `bills/{id}/pay`, `payments/`, `bills/generate_month`) — é a **Sessão 38**. Os serviços desta sessão são chamados pelos viewsets da S38, não expostos agora.
- **Geração de `Installment`/folha** em `ensure_month_bills` — é a **Fase 3 (S41 installment, S44 folha)**. `ensure_month_bills` desta sessão gera **só recorrentes (BillingAccount) + seed**; **pula** planos embutidos e parcelas (os modelos `Installment`/`Employee` nem existem). Documentar o ponto de extensão no docstring para a S41/S44 estenderem.
- **Reserva real** (`funded_from=reserve` → `ReserveMovement` + guarda de saldo) — `Reserve`/`ReserveMovement` são **Fase 4 (S47/S48)**. `BillPaymentService.pay` aceita `funded_from='caixa'|'reserve'` (o campo já existe no `Payment`, S36) e **persiste** o `funded_from`, mas com `funded_from='reserve'` **não** cria `ReserveMovement` nem valida saldo de reserva nesta fase — ver §"funded_from nesta fase".
- **Bloqueio de mês fechado** (`CondoMonthClose.status=closed`) — `CondoMonthClose` é **Fase 4 (S49)**. `BillPaymentService.pay`/estorno **não** bloqueia por fechamento agora; documentar como **hook futuro** (ver §"Bloqueio de mês fechado = hook futuro"). NÃO criar `CondoMonthClose`.
- **`CondoCalendarService` / `CondoBalanceService` / KPIs de dinheiro** — calendário combinado é a S38/§10; saldo/caixa é a Fase 4. **Não** criar aqui.
- **`@cache_result` em endpoints** `finance-*` — não há endpoint ainda (S38). Esta sessão cria os **prefixos** e a **invalidação**; o consumo via decorator entra com os dashboards (S40/S41). Definir os prefixos agora evita o anti-padrão "um char de diferença não-invalida" (design §11).
- **Nenhuma migração / mudança de model** — os modelos são da S36; os serviços não criam campos.

---

## Especificação

> Serviços stateless em `finances/services/`, todos `@staticmethod`. `Decimal` para dinheiro; **quantização (`ROUND_HALF_UP`) só na fronteira de saída/agregado** (design §4) — os serviços somam cru. "Hoje/mês atual" **sempre** via `finances.services.timezone.today_sp()`/`current_month_sp()` (design §4 — settings é UTC). `@transaction.atomic` + `select_for_update` em leitura-modificação. Mensagens ao usuário em **PT**, logs/identificadores em **EN**. Direção: serviços importam de `finances.models`, `finances.services.timezone`, `core.services.rent_schedule_service` (clamp) — **nunca** de views/serializers.

### Direção do import cross-app (CRÍTICO — resolve onde vivem as constantes)

A direção de dependência é `finances → core` (design §3.1, `.claude/rules/architecture.md`). `core/signals.py` precisa invalidar `finance-*` quando `Apartment`/`Lease`/RentPayment mudam — isso exigiria `core → finances`, que **inverte** a direção. **Decisão pinada (KISS, sem inversão):** as constantes de prefixo `finance-*` são **strings literais** que vivem em `finances/cache.py` (fonte única para o `finances`), **e** `core/signals.py` invalida via `CacheManager.invalidate_pattern("finance-dashboard*")` etc. usando as **mesmas strings literais** — **sem importar** `finances` (evita o ciclo `core ← finances`). Para garantir que as duas pontas usam o mesmo literal (o risco do design §11 "um char de diferença"), `tests/unit/test_finances/test_finance_cache_signals.py` **trava por teste** que os prefixos invalidados em `core/signals.py` são exatamente `FINANCE_DASHBOARD_PREFIX`/`FINANCE_CASH_FLOW_PREFIX`/`FINANCE_PROJECTION_PREFIX` de `finances/cache.py` (importando ambos no teste e comparando). Assim o teste é a fronteira que casa os dois lados sem acoplar `core` a `finances` em runtime.

### `finances/cache.py` — bloco único de prefixos (design §11)

```python
# finances/cache.py — fonte única dos prefixos finance-*. Hífen-prefixados (não ":"),
# como o resto do projeto (core/signals.py:295-296). invalidate_pattern monta
# f"{key_prefix}:1:{prefix}*" — um char de diferença não-invalida silenciosamente.
from core.cache import CacheManager

FINANCE_DASHBOARD_PREFIX = "finance-dashboard"
FINANCE_CASH_FLOW_PREFIX = "finance-cash-flow"
FINANCE_PROJECTION_PREFIX = "finance-projection"

FINANCE_CACHE_PREFIXES = (
    FINANCE_DASHBOARD_PREFIX,
    FINANCE_CASH_FLOW_PREFIX,
    FINANCE_PROJECTION_PREFIX,
)

def invalidate_finance_caches() -> None:
    """Invalidate every finance-* dashboard/cash-flow/projection cache (single source)."""
    for prefix in FINANCE_CACHE_PREFIXES:
        CacheManager.invalidate_pattern(f"{prefix}*")
```

> `finances/cache.py` importa `CacheManager` de `core.cache` (direção `finances → core`, correta). É a **única** definição dos prefixos no `finances`; signals do `finances` chamam `invalidate_finance_caches()`.

### `BillGenerationService.ensure_month_bills(year, month) -> list[Bill]`

Gera (idempotente, **race-safe**) os `Bill` recorrentes esperados do mês para todas as `BillingAccount` elegíveis do condomínio. Retorna a lista de bills garantidos (criados + já existentes), para o caller (S38 `bills/generate_month`) reportar.

Elegibilidade de uma `BillingAccount` para o mês `M` (= `date(year, month, 1)`):
- `lifecycle_state == BillingAccountState.ACTIVE` (exclui `suspended`/`deferred`/`ended` — **suspensa não gera novos `Bill`**; bills passados intactos, design §5.2/§7).
- `tracking_start_month` é `None` **ou** `tracking_start_month <= M` (seed: a partir do mês de início).
- `end_date` é `None` **ou** `end_date >= M` (cutoff — não gera após o fim).
- **não** existe `BillSkip.objects.filter(billing_account=acc, reference_month=M)` (pula o mês).

Para cada conta elegível, garantir **um** `Bill` com `(billing_account=acc, competence_month=M)`:
- **Race-safe**: `Bill.all_objects.get_or_create(billing_account=acc, competence_month=M, is_deleted=False, defaults={...})` dentro de `transaction.atomic()`; envolver em `try/except IntegrityError` (tolerar corrida na unique parcial) e re-buscar. **Não** recriar se já existe (idempotente — re-rodar o mês não duplica).
- `defaults`: `condominium=acc.condominium`, `building=acc.building`, `category=acc.category`, `behavior=BillBehavior.RECURRING`, `lifecycle_state=BillLifecycleState.ACTIVE`, `due_date=date(year, month, clamp_due_day(acc.default_due_day, year, month))` (reusa `RentScheduleService.clamp_due_day`), `description=acc.name`, `external_identifier=acc.external_identifier`, `created_by/updated_by` = `None` (geração automática; o caller S38 pode passar o user — aceitar `user: User | None = None` no método e propagar).
- **Seed "pago até X" (design §7/§11/§18):** ao garantir o `Bill`, criar **uma `BillLineItem`** com `amount = acc.expected_amount` (não-offset), `description = acc.name`, `category = acc.category`. Assim `amount_total = expected_amount > 0`, `amount_paid = 0` → o bill aparece como **atrasado** (`amount_remaining > 0` + `due_date < today_sp()`) a preencher/ajustar. **Só** criar a linha quando o `Bill` é **recém-criado** (não re-semear um bill já existente — idempotência: re-rodar não adiciona linhas duplicadas). Se `expected_amount == 0`, **ainda** criar o bill (sem linha, ou com linha 0 — DECIDIR e travar por teste; recomendo **sem** linha quando `expected_amount==0` → `amount_total=0`, `payment_status='open'`, não-atrasado).

**Gerador de datas puro:** um helper `_due_date_for(account, year, month) -> date` (função/staticmethod pura, sem ORM) = `date(year, month, RentScheduleService.clamp_due_day(account.default_due_day, year, month))`. Testável isolado (31 em fev → dia 28/29; abr → 30).

**Pula embutidos/parcelas/folha:** esta fase gera **só** `BillingAccount` (recorrentes). Planos embutidos (`InstallmentPlan.embedded=True`), parcelas avulsas e folha **não** são gerados aqui (modelos da Fase 3). Docstring marca o ponto de extensão: *"S41 estende com `Installment` de planos não-embutidos; S44 estende com folha; embutidos viram linha no `Bill` da conta recorrente, nunca `Bill` próprio."*

### `BillService.create_with_lines(...) -> Bill`

Cria um `Bill` **avulso** (ou qualquer `Bill` com linhas explícitas) + suas `BillLineItem`s **no serviço** (não em serializer nested — design §8/`.claude/rules/architecture.md`: orquestração no serviço). Assinatura:

```python
@staticmethod
def create_with_lines(
    *,
    condominium: Condominium,
    competence_month: date,
    due_date: date,
    description: str,
    behavior: str,                       # BillBehavior value
    lines: list[dict[str, object]],      # [{description, amount, is_offset?, category?}, ...]
    building: Building | None = None,
    category: Category | None = None,
    billing_account: BillingAccount | None = None,
    external_identifier: str = "",
    lifecycle_state: str = BillLifecycleState.ACTIVE,
    notes: str = "",
    user: User | None = None,
) -> Bill:
    """Cria Bill + BillLineItem(s) atômico. amount_total deriva das linhas via with_amounts."""
```

Regras:
- `@transaction.atomic` — cria o `Bill` e **todas** as linhas; se qualquer linha falhar (ex.: `amount < 0` → `CheckConstraint`), **rollback** total (nenhum `Bill` órfão).
- `competence_month` normalizado para dia 1 (defensivo; o `clean()` do model também faz — chamar `full_clean()` antes de salvar para mensagens PT, design §5).
- Cada item de `lines`: `BillLineItem(bill=bill, description=..., amount=Decimal(...), is_offset=bool, category=...)`. `is_offset` default `False`. `amount` armazenado **positivo** (design §4.1); validar `>= 0` (deixar o `CheckConstraint`/`clean()` do model levantar — não duplicar a regra).
- Propaga `created_by/updated_by = user` em `Bill` e linhas quando `user` dado.
- **Não** chama pagamento/geração; só monta a conta. Retorna o `Bill` (o caller pode re-buscar com `.with_amounts(today)` para os derivados).
- **Lista vazia de linhas** permitida (bill sem linhas → `amount_total=0`; estrutural §18) — DECIDIR se rejeita ou aceita; recomendo **aceitar** (caller pode adicionar linhas depois via S38 `bills/{id}/lines`).

### `BillPaymentService.pay(bill, payment_date, amount=None, funded_from='caixa', user=None) -> Payment`

Cria `Payment` + `PaymentAllocation` (total se `amount=None`; parcial se menor). Assinatura:

```python
@staticmethod
def pay(
    bill: Bill,
    payment_date: date,
    amount: Decimal | None = None,
    funded_from: str = FundedFrom.CAIXA,
    user: User | None = None,
) -> Payment:
    """Paga (parcial/total) um Bill. Σalloc == payment.amount; over-allocation rejeitada."""
```

Regras (design §4.8 + §18 "Pagamento"):
- `@transaction.atomic` + `select_for_update` no `bill` (relê o bill bloqueado para o cálculo de `remaining` ser consistente sob concorrência — espelha `toggle_payment` `:399-409`).
- Calcular `remaining` via annotation: `Bill.objects.with_amounts(today_sp()).get(pk=bill.pk).amount_remaining` (ou `.select_for_update()` no `Bill` + recomputar via `with_amounts` — **nunca** somar em Python). `today_sp()` para `is_overdue` coerente.
- `amount = remaining` quando `None` (pagamento total do restante).
- **Over-allocation rejeitada (v1 não cria crédito):** se `amount > remaining` → levantar `ValidationError` PT (`"O valor do pagamento excede o saldo devedor da conta."`). `amount <= 0` → `ValidationError` PT.
- Criar `Payment(condominium=bill.condominium, payment_date=payment_date, amount=amount, funded_from=funded_from, created_by/updated_by=user)` + **um** `PaymentAllocation(payment=payment, bill=bill, amount=amount)`. **Invariante (design §4.8):** `Σ(PaymentAllocation.amount do payment) == Payment.amount` — nesta fase é sempre 1 alocação = `amount`; travar por teste.
- `funded_from` (caixa|reserve) **persistido** no `Payment`; **nesta fase** `reserve` não cria `ReserveMovement` (ver abaixo).
- **Estorno = soft-delete**: método `unpay(payment, user=None)` (ou `reverse`) que `payment.delete(deleted_by=user)` (soft) → o cascade soft-delete da S36 leva as `PaymentAllocation`; `amount_remaining` do bill **recompõe** (annotation exclui alocações soft-deletadas). DECIDIR o nome (`unpay`/`reverse`) e travar por teste. **Cobertura §18 "estorno (soft-delete) recompõe amount_remaining".**

#### `funded_from` nesta fase (reserva = Fase 4)
`funded_from='reserve'` é **aceito e persistido** no `Payment` (o enum já existe — S36), mas `BillPaymentService` **não** cria `ReserveMovement` nem valida saldo de reserva agora (`Reserve`/`ReserveMovement` são S47/S48). Docstring marca: *"Fase 4 (S48) estende `pay()` para `funded_from=reserve` criar `ReserveMovement(withdrawal, bill=…)` com guarda de saldo; aqui só persiste o `funded_from`."* **Não** somar `reserve` ao caixa nem decidir caixa-vs-reserva nesta fase (não há `CondoBalanceService` ainda).

#### Bloqueio de mês fechado = hook futuro (Fase 4)
`CondoMonthClose` (S49) ainda não existe → `pay()`/`unpay()` **não** bloqueiam por mês fechado nesta fase. Docstring marca o ponto exato: *"Fase 4 (S49) insere aqui o guard `CondoMonthCloseService.assert_open(bill.competence_month)` (rejeita pay/unpay em mês `closed`, design §8) — antes do `select_for_update`."* **Não** criar stub/flag especulativo (YAGNI) — só o comentário-âncora no lugar onde o guard entrará. **Sem** `# TODO/FIXME` (proibido — `.claude/rules/design-principles.md`): a âncora é prosa no docstring, não um comentário-TODO.

### `received_collectible_total` (helper read aditivo em `RentScheduleService`)

Adicionar (design §4.5 — receita do net/distribuição usa o recebido **filtrado por collectibility**, nunca o `received_total` cru que somaria Tiago/Alvaro):

```python
@staticmethod
def received_collectible_total(reference_month: date, building_id: int | None = None) -> Decimal:
    """Σ amount_paid de RentPayment ATIVOS do mês, restrito a leases COBRÁVEIS
    (collectible_leases). Espelha received_total (:367-378) mas pré-filtrado por
    cobrabilidade — usado pelo caixa/net do condomínio (design §4.5)."""
```

Implementação: `RentPayment.objects.filter(reference_month=reference_month, lease__in=collectible_leases(reference_month, building_id))` → `Sum("amount_paid") or ZERO`. **Aditivo** — não altera `received_total` (continua sendo a definição crua para o `DailyControlService` legado, S21). Guarda/teste (design §4.5/§18): leases owner-set/salary-offset **não** têm `RentPayment` (o toggle só permite cobráveis) → `received_collectible_total == received_total` no caso normal, mas **diverge** quando existe um `RentPayment` de lease não-cobrável (provar por teste que o filtrado o exclui).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui é **só `freezegun`** (congelar a data para `today_sp()`/`is_overdue`). **NUNCA** mockar ORM, managers, `Bill.with_amounts`, `RentScheduleService`, `CacheManager`, signals ou qualquer interno. Banco real via `--reuse-db`. Dados via factories (`model-bakery`). `filterwarnings=error`: zero warnings. **Cache em teste é LocMem** (`configure_test_cache`, `tests/CLAUDE.md`) → `invalidate_pattern` faz `cache.clear()` (`core/cache.py:230-235`): testar invalidação por **efeito observável** (chave setada some após o save), não por mock do `CacheManager`.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_bill_generation_service.py` (sob `@freeze_time`)
**Gerador de datas puro**
- [ ] `_due_date_for` com `default_due_day=31` em fev/2026 → `date(2026, 2, 28)`; em fev/2024 (bissexto) → `date(2024, 2, 29)`; em abril → `date(2026, 4, 30)`; `default_due_day=10` em março → `date(2026, 3, 10)`.

**Geração idempotente + elegibilidade (§18 "Datas/geração")**
- [ ] conta `ACTIVE` com `expected_amount=600` → gera **1** `Bill` `(billing_account, competence_month=M)` com `behavior=RECURRING`, `due_date` clampado, **1 linha** `amount=600` não-offset; `with_amounts(today).amount_total == 600`.
- [ ] **idempotência**: chamar `ensure_month_bills(year, month)` **duas vezes** → continua **1** `Bill` e **1** linha (não duplica). `Bill.all_objects.filter(...).count() == 1`.
- [ ] **suspensão**: conta `lifecycle_state=SUSPENDED` → **não** gera bill no mês; um bill de mês passado (criado antes) permanece intacto (não tocado).
- [ ] **`BillSkip`**: existe `BillSkip(billing_account, reference_month=M)` → **não** gera bill em M; remover o skip (hard delete) e re-rodar → gera (des-pula).
- [ ] **`end_date` cutoff**: conta com `end_date` < M → não gera; `end_date` == M → gera; `end_date` > M → gera.
- [ ] **`tracking_start_month`** (seed): `tracking_start_month` futuro (> M) → não gera em M; `tracking_start_month <= M` → gera. **Seed cruzando virada de ano** (§18): `tracking_start_month=2025-11`, gerar para 2026-01 → gera (cobre a janela).
- [ ] **seed gera atrasado visível** (§18 "Atrasado"): `freeze_time` após o `due_date` do mês gerado → o bill gerado tem `is_overdue=True` (via `with_amounts(today_sp())`), `amount_remaining == expected_amount > 0`.
- [ ] **`expected_amount == 0`**: gera o bill **sem** linha → `amount_total=0`, `payment_status='open'`, `is_overdue=False` (convenção travada).
- [ ] **virada de mês na TZ SP** (§18): `freeze_time` num instante UTC já no mês seguinte enquanto SP ainda é o mês anterior → `ensure_month_bills` usa o mês de SP via `today_sp()`/`current_month_sp()` onde aplicável (asserir que o `due_date`/overdue refletem SP, não UTC). *(O `year`/`month` são parâmetros; o ponto é que `today_sp()` rege `is_overdue`.)*
- [ ] **pula embutidos/parcelas/folha**: nenhum `Bill` é gerado para algo que não seja `BillingAccount` (não há `Installment`/`Employee` — confirmar que o serviço só itera `BillingAccount`; smoke estrutural). Prédio sem `BillingAccount` → `ensure_month_bills` retorna `[]`.

#### `tests/unit/test_finances/test_bill_service.py`
- [ ] `create_with_lines` com 2 linhas `[{desc, 600}, {desc, 400}]` → 1 `Bill` + 2 `BillLineItem`; `with_amounts(today).amount_total == 1000`.
- [ ] linha com `is_offset=True` (ex.: `[{600}, {400}, {100, is_offset:True}]`) → `amount_total == 900` (design §4.1).
- [ ] **atomicidade**: uma linha com `amount` negativo → `IntegrityError`/`ValidationError`; **nenhum** `Bill` criado (rollback total; `Bill.all_objects.count()` inalterado).
- [ ] `competence_month` não-dia-1 normalizado para dia 1.
- [ ] `behavior=ONE_TIME` (avulsa) com `billing_account=None` → criado; `external_identifier`/`notes` persistidos.
- [ ] `lines=[]` → `Bill` criado, `amount_total=0` (convenção travada).
- [ ] `created_by/updated_by` propagados quando `user` dado (Bill **e** linhas).

#### `tests/unit/test_finances/test_bill_payment_service.py` (sob `@freeze_time`)
**Pagamento (§18 "Pagamento")**
- [ ] total (`amount=None`) de um bill `amount_total=900` sem pagamento → `Payment(amount=900)` + 1 `PaymentAllocation(900)`; `Σalloc == payment.amount`; `with_amounts(today).amount_paid==900`, `amount_remaining==0`, `payment_status='paid'`.
- [ ] **parcial-depois-total**: `pay(amount=300)` → `payment_status='partial'`, `amount_remaining==600`; depois `pay(amount=600)` → `paid`, `remaining==0`; `amount_paid==900` (Σ das 2 alocações).
- [ ] **over-allocation rejeitada**: bill `amount_total=900`; `pay(amount=1000)` → `ValidationError` PT; **nenhum** `Payment` criado. Após `pay(900)` (paid), `pay(amount=1)` → rejeitado (remaining 0).
- [ ] `amount <= 0` → `ValidationError` PT.
- [ ] **`funded_from` persistido**: `pay(funded_from='reserve')` → `Payment.funded_from == 'reserve'`; **nenhum** `ReserveMovement` criado (modelo nem existe — confirmar que o serviço não o referencia); **não** soma a caixa (não há `CondoBalanceService` — smoke: o serviço não chama nada de reserva).
- [ ] **estorno (soft-delete) recompõe** (§18): após `pay(900)` (paid), `unpay(payment)` → `payment` soft-deletado (`Payment.objects` não acha; `all_objects.with_deleted()` acha), `PaymentAllocation` soft-deletada via cascade; `with_amounts(today).amount_remaining==900`, `payment_status='open'`. Recriar pagamento depois funciona.
- [ ] **split caixa+reserva = dois `pay()`** (§18): `pay(amount=300, funded_from='caixa')` + `pay(amount=600, funded_from='reserve')` → 2 `Payment` distintos, 2 `PaymentAllocation`, `amount_paid==900`, `paid`. (Sem `ReserveMovement` nesta fase — só os 2 Payments.)
- [ ] **concorrência (smoke)**: o `pay` roda em `transaction.atomic` e lê `amount_remaining` sob `select_for_update` — testar que dois `pay` sequenciais de 600 num bill de 900 → o segundo é **rejeitado** (over-allocation), não cria crédito.

#### `tests/unit/test_finances/test_finance_cache_signals.py`
> Cache LocMem nos testes → `invalidate_pattern` faz `cache.clear()`. Estratégia: `cache.set("finance-dashboard:probe", "x")` (uma chave com cada prefixo), disparar o save/delete, asserir `cache.get(...) is None` (a chave foi limpa). **Não** mockar `CacheManager`.

**Casamento dos literais (resolve o risco design §11)**
- [ ] `from finances.cache import FINANCE_DASHBOARD_PREFIX, FINANCE_CASH_FLOW_PREFIX, FINANCE_PROJECTION_PREFIX` — os 3 são exatamente `"finance-dashboard"`/`"finance-cash-flow"`/`"finance-projection"` (sem `:`). `invalidate_finance_caches()` invalida os 3 (probe em cada → None após chamar).

**Signals do `finances`**
- [ ] `make_bill(...)` (save) → as 3 probes `finance-*` somem. Idem `make_billing_account`, `make_finance_category`, `make_payment`, `make_payment_allocation`, `make_bill_line_item`, `make_bill_skip` (cada model do finances invalida).
- [ ] **soft-delete** de um `Bill` (`bill.delete()`) dispara `post_save` (SoftDeleteMixin) → invalida `finance-*` (probe some).

**Cross-app NET-NEW (design §11)**
- [ ] `make_apartment(...)` (save) e mudar `apartment.owner` (save) → probes `finance-*` somem (owner muda receita/projeção). Apartment delete idem.
- [ ] `make_lease(...)` (save/delete) → probes `finance-*` somem.
- [ ] `make_rent_payment(...)` (save) → probes `finance-*` somem **E** a probe `dashboard-late-payment` continua sendo limpa (regressão design §11: o fluxo existente intacto). `FinancialSettings` save → idem.
- [ ] **regressão**: após a extensão, `_invalidate_financial_caches` continua limpando `daily-control*`/`cash-flow*`/`financial-dashboard*` (probes desses prefixos também somem) — não quebrar o legado.

> Rodar (devem **falhar** — serviços/cache/signals ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_generation_service.py \
>   tests/unit/test_finances/test_bill_service.py \
>   tests/unit/test_finances/test_bill_payment_service.py \
>   tests/unit/test_finances/test_finance_cache_signals.py -q
> ```

### 2. GREEN — implementar

1. `finances/cache.py` (prefixos + `invalidate_finance_caches`).
2. `finances/services/bill_generation_service.py`, `bill_service.py`, `bill_payment_service.py` — reusando `RentScheduleService.clamp_due_day`, `Bill.objects.with_amounts(today_sp())`, `today_sp()`/`current_month_sp()`. Imports diretos da fonte.
3. `finances/signals.py` — receivers `post_save`/`post_delete` nos 7 modelos do `finances` → `invalidate_finance_caches()` (idioma de `core/signals.py:56-110`).
4. `core/signals.py` — estender `_invalidate_financial_caches` (`:292-299`) com os 3 `invalidate_pattern("finance-*")` (literais idênticos a `finances/cache.py`, comentário citando o casamento); adicionar invalidação `finance-*` nos receivers de `Apartment` (`:87-110`) e `Lease` (post_save/post_delete). **Não** importar `finances` (evitar ciclo — literais).
5. `core/services/rent_schedule_service.py` — `received_collectible_total` (aditivo).

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_bill_generation_service.py tests/unit/test_finances/test_bill_service.py tests/unit/test_finances/test_bill_payment_service.py tests/unit/test_finances/test_finance_cache_signals.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- O gerador de datas (`_due_date_for`) é função pura pequena; o cálculo de elegibilidade da `BillingAccount` extraído num helper privado nomeado (`_is_account_eligible(account, month) -> bool`) — intenção clara (design-principles).
- `invalidate_finance_caches()` é a **única** fonte da lista de prefixos; `finances/signals.py` chama-a (não repete `invalidate_pattern` por prefixo). `core/signals.py` usa os 3 literais com o comentário de casamento (o teste trava a igualdade).
- Confirmar que **nenhum** serviço soma linhas/alocações em Python — tudo via `with_amounts` (design §4.4). Quantização só na fronteira (não nos serviços).
- Mensagens PT centralizadas como constantes nomeadas se repetidas (sem magic strings espalhadas).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_bill_generation_service.py tests/unit/test_finances/test_bill_service.py \
  tests/unit/test_finances/test_bill_payment_service.py tests/unit/test_finances/test_finance_cache_signals.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ core/signals.py core/services/rent_schedule_service.py tests/unit/test_finances/
ruff format --check finances/ core/signals.py core/services/rent_schedule_service.py tests/unit/test_finances/
mypy core/ finances/
pyright finances/ core/signals.py core/services/rent_schedule_service.py
```

> **Regressão obrigatória do cache legado**: rodar os testes de signals existentes que cobrem `_invalidate_financial_caches`/RentPayment/FinancialSettings (se houver `tests/unit/test_signals*`/`test_financial/test_*signal*`) para garantir que a extensão não quebrou o legado:
> ```bash
> python -m pytest tests/unit -k "signal or invalidat" -q
> ```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). Serviços do `finances` importam `RentScheduleService` (clamp), `Bill.with_amounts`, `today_sp()` — **nunca** views/serializers. `core/signals.py` **não** importa `finances` (usa literais `finance-*` para evitar o ciclo `core ← finances`; o teste trava o casamento).
- **Lógica de negócio só em serviços** (`.claude/rules/architecture.md`): geração/pagamento/criação-com-linhas nos serviços, **nunca** no model/serializer/viewset. Models só validam (`clean()`).
- **Annotations, não Python** (design §4.4): `amount_remaining`/`amount_total`/`is_overdue` SEMPRE de `Bill.objects.with_amounts(today)`. Proibido somar `line_items`/`allocations` em Python no serviço.
- **TZ SP única** (design §4): "hoje/mês atual" só via `finances.services.timezone` (`today_sp()`/`current_month_sp()`). Proibido `timezone.now().date()` nos serviços do `finances`.
- **Idempotência race-safe** (design §8): `get_or_create` na unique parcial `(billing_account, competence_month)` + `try/except IntegrityError` dentro de `transaction.atomic`. Re-rodar o mês não duplica bill nem linha de seed.
- **Over-allocation rejeitada** (design §4.8): v1 não cria crédito; `amount > remaining` → `ValidationError` PT.
- **Reserva/fechamento = Fase 4**: `funded_from='reserve'` só persiste (sem `ReserveMovement`/guarda); `pay`/`unpay` sem bloqueio de mês fechado — **hooks futuros documentados em prosa no docstring** (sem `# TODO/FIXME/HACK` — proibido).
- **Sem geração de installment/folha/embutido** (Fase 3) — `ensure_month_bills` só recorrentes + seed; ponto de extensão no docstring.
- **`received_collectible_total` é aditivo** — `received_total`/`collectible_leases`/`is_prepaid_for_month` (SSOT de aluguel) **inalterados** (memória do projeto: rotear collectibility só pelo SSOT).
- **Bloco único de prefixos** (design §11): `finances/cache.py` é a única fonte; signals do `finances` chamam `invalidate_finance_caches()`. Hífen-prefixado (não `:`), glob `<prefix>*`.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código. Tipos completos (mypy strict + pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from django.contrib.auth.models import User`, `from django.db.models import QuerySet`, etc.).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; imports diretos da fonte.
- **Sem serializer/viewset/URL/frontend** (S38+). Sem `CondoCalendarService`/`CondoBalanceService`/`Installment`/`Employee`/`Reserve`/`ReserveMovement`/`CondoMonthClose`. **Sem migração / mudança de model**.
- **`DecimalField(12,2)`**; quantização (`ROUND_HALF_UP`) só na fronteira, não nos serviços (eles somam cru via annotation).
- **Soft delete**: estorno = `payment.delete(deleted_by=user)` (soft); validar slots com `Payment.objects` vs `all_objects.with_deleted()` nos testes.
- Mensagens ao usuário em **Português**; logs/identificadores/enum values em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/cache.py` define `FINANCE_DASHBOARD_PREFIX`/`FINANCE_CASH_FLOW_PREFIX`/`FINANCE_PROJECTION_PREFIX` (= `"finance-dashboard"`/`"finance-cash-flow"`/`"finance-projection"`, hífen) + `FINANCE_CACHE_PREFIXES` + `invalidate_finance_caches()`, importando `CacheManager` de `core.cache` (direção correta).
- [ ] `BillGenerationService.ensure_month_bills(year, month, user=None)` gera **só** recorrentes (`BillingAccount` ACTIVE, dentro de `tracking_start_month..end_date`, respeitando `BillSkip`), idempotente race-safe (`get_or_create`+`IntegrityError`), com seed (linha `expected_amount` quando recém-criado e `>0`); **pula** embutidos/parcelas/folha (ponto de extensão documentado); gerador de datas puro reusa `RentScheduleService.clamp_due_day`.
- [ ] `BillService.create_with_lines(...)` cria `Bill`+`BillLineItem`(s) atômico (rollback total em falha), `is_offset` positivo+subtraído, `competence_month` dia 1; orquestração **no serviço**.
- [ ] `BillPaymentService.pay(bill, payment_date, amount=None, funded_from='caixa', user=None)` cria `Payment`+1 `PaymentAllocation`, `Σalloc==payment.amount`, **over-allocation rejeitada** (PT), `amount<=0` rejeitado, `funded_from` persistido (sem `ReserveMovement` nesta fase); `unpay`/estorno por soft-delete recompõe `amount_remaining`; lê `remaining` via `with_amounts` sob `select_for_update`; bloqueio de mês fechado documentado como hook futuro (sem TODO).
- [ ] `RentScheduleService.received_collectible_total(reference_month, building_id=None)` adicionado (aditivo; pré-filtrado por `collectible_leases`); `received_total`/`collectible_leases` inalterados.
- [ ] `finances/signals.py` invalida `finance-*` em `post_save`/`post_delete` dos 7 modelos do `finances` (soft-delete via `post_save`), via `invalidate_finance_caches()`.
- [ ] `core/signals.py` estende `_invalidate_financial_caches` com `finance-*` (RentPayment/FinancialSettings cobertos por DRY) **e** adiciona invalidação `finance-*` em Apartment/Lease (NET-NEW); legado (`daily-control*`/`cash-flow*`/`financial-dashboard*`/`dashboard-late-payment*`) intacto; **sem** import de `finances` em `core`.
- [ ] Testes cobrem: gerador de datas (clamp fev/abr/bissexto), idempotência, suspensão, `BillSkip` (hard-delete des-pula), `end_date`/`tracking_start_month`/seed-cruza-ano, seed-atrasado-visível, `expected_amount==0`, virada-de-mês-SP; create_with_lines (offset, atomicidade, normalização, lines vazias, user); pay (total/parcial/over-allocation/amount<=0/funded_from/estorno/split/concorrência); cache (casamento de literais, 7 models finances, soft-delete, cross-app Apartment/owner/Lease/RentPayment/FinancialSettings, regressão legado).
- [ ] `python -m pytest tests/unit/test_finances/test_bill_*` + `test_finance_cache_signals.py` passa 100%, **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/ core/signals.py core/services/rent_schedule_service.py` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum serializer/viewset/URL/frontend criado; nenhum modelo/migração novo; sem `CondoCalendarService`/`CondoBalanceService`/reserva real/installment/folha/`CondoMonthClose`; `received_total`/`collectible_leases` (SSOT) intactos.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_bill_generation_service.py tests/unit/test_finances/test_bill_service.py \
     tests/unit/test_finances/test_bill_payment_service.py tests/unit/test_finances/test_finance_cache_signals.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit -k "signal or invalidat" -q   # regressão cache legado
   ruff check finances/ core/signals.py core/services/rent_schedule_service.py tests/unit/test_finances/
   ruff format --check finances/ core/signals.py core/services/rent_schedule_service.py tests/unit/test_finances/
   mypy core/ finances/
   pyright finances/ core/signals.py core/services/rent_schedule_service.py
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 37 (status **concluída**) na tabela da feature Condomínio Finance.
   - **Arquivos Criados**: `finances/cache.py`, `finances/services/{bill_generation_service,bill_service,bill_payment_service}.py`, `tests/unit/test_finances/{test_bill_generation_service,test_bill_service,test_bill_payment_service,test_finance_cache_signals}.py`.
   - **Arquivos Modificados**: `finances/signals.py` (receivers reais), `core/signals.py` (estende `_invalidate_financial_caches` + Apartment/Lease NET-NEW), `core/services/rent_schedule_service.py` (`received_collectible_total` aditivo).
   - **Nota**: "Fase 2 — serviços de contas: `ensure_month_bills` (recorrentes+seed, idempotente race-safe, pula embutidos/parcelas/folha→S41/S44), `create_with_lines` (orquestra no serviço), `pay`/`unpay` (parcial, over-allocation rejeitada, funded_from persistido sem reserva real, estorno soft-delete). Cache: bloco único de prefixos `finance-*` em `finances/cache.py`; `finances/signals.py` real; `core/signals.py` estende financial + NET-NEW Apartment/Lease (literais finance-* sem importar finances — teste trava o casamento). `received_collectible_total` aditivo no SSOT. **Reserva real / bloqueio de mês fechado = hooks futuros documentados (Fase 4 S48/S49); installment/folha na geração = Fase 3 S41/S44; API = S38.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`):
   ```
   feat(finances): add bill generation/creation/payment services + finance-* cache prefixes + cross-app invalidation

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **38 — Backend serializers + viewsets + URLs** (`bills/`, `bills/create_with_lines`, `bills/{id}/pay`, `bills/generate_month`, `payments/`, `billing-accounts/`, etc.) — consome os serviços desta sessão (chama-os nos `@action`) e o `.with_amounts()` da S36 (serializa `amount_*` como string Decimal). A S38 **adiciona** a API; **não** recria serviços nem modelos.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.cache`**: `FINANCE_DASHBOARD_PREFIX="finance-dashboard"`, `FINANCE_CASH_FLOW_PREFIX="finance-cash-flow"`, `FINANCE_PROJECTION_PREFIX="finance-projection"`, `FINANCE_CACHE_PREFIXES` (tupla), `invalidate_finance_caches()`. **S40/S41** usam estes prefixos no `@cache_result` dos dashboards (`finance-dashboard`/`finance-cash-flow`) e da projeção (`finance-projection`) — **a mesma string** (um char de diferença não-invalida). **S38** (calendário combinado) deixa `combined_calendar` **sem cache** ou TTL curto (design §11) — não usar estes prefixos lá.
- **`BillGenerationService.ensure_month_bills(year, month, user=None) -> list[Bill]`** — idempotente race-safe; só recorrentes + seed. **S41** estende com `Installment` de planos não-embutidos; **S44** com folha; embutidos viram linha no `Bill` da conta, nunca `Bill` próprio. **S38** `bills/generate_month` chama este método.
- **`BillService.create_with_lines(*, condominium, competence_month, due_date, description, behavior, lines, building=None, category=None, billing_account=None, external_identifier="", lifecycle_state=ACTIVE, notes="", user=None) -> Bill`** — **S38** `bills/create_with_lines` (ou `bills/` create) chama-o (não serializer nested). `lines = [{description, amount, is_offset?, category?}]`.
- **`BillPaymentService.pay(bill, payment_date, amount=None, funded_from='caixa', user=None) -> Payment`** + `unpay(payment, user=None)` (estorno soft-delete). **S38** `bills/{id}/pay`/`bulk_pay` chama-os. **S48** estende `pay` para `funded_from=reserve` criar `ReserveMovement(withdrawal, bill=…)` + guarda de saldo. **S49** insere `assert_open(competence_month)` (bloqueio de mês fechado) antes do `select_for_update`. `Σ(PaymentAllocation.amount)==Payment.amount` (invariante fixado aqui).
- **`RentScheduleService.received_collectible_total(reference_month, building_id=None) -> Decimal`** — recebido **filtrado por collectibility** (design §4.5). **S40** (`CondoBalanceService`) usa-o para o caixa/net do condomínio — **nunca** o `received_total` cru.
- **Invalidação cross-app**: escrever em `Apartment`/`Apartment.owner`/`Lease`/`RentPayment`/`FinancialSettings` + qualquer model do `finances` invalida `finance-*`. **S40/S41** podem confiar que os dashboards `finance-*` são invalidados nessas escritas. **S38/§11**: `combined_calendar` fica sem cache (dupla-metade aluguel/bills). Esta sessão TAMBÉM adiciona receivers em `RentAdjustment` (altera `effective_rental_value`→projeção) e `MonthSnapshot` (finalize/rollback) invalidando `finance-*` (design §11) — invalidar um prefixo cujo cache ainda não existe é no-op seguro; consolida toda a invalidação cross-app numa única sessão (com teste).
