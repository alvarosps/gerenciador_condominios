# Sessão 61 — Backend: `IptuAlertService` + endpoint `iptu_alerts` (uncached) + tipos de `Notification` (core) + `is_notification_sent_on` SP-aware + comando `send_finance_alerts` (resumo agregado + push best-effort)

> **Feature**: Contas de serviço tipadas (água/luz/IPTU) + parser de fatura + alerta de IPTU + modal responsivo (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: 56 → 57 → 58 → 59 → 60 → **61** → 62 → 63 → 64
> Esta sessão é a **Fase 5 — Alerta de IPTU**. Cria o `IptuAlertService.evaluate(today)` (read-only, via annotations `with_amounts`), o endpoint **UNCACHED** `GET /api/finances/finance-dashboard/iptu_alerts` (canal banner, load-bearing), os **tipos novos** de `Notification` em `core` (constantes nomeadas + `AlterField`), o helper `is_notification_sent_on(user, type, day)` **SP-aware** e o comando de cron `send_finance_alerts` que agrega **TODOS** os WARNINGs num **único** resumo por admin (+ CRITICALs), com push best-effort e idempotência SP-aware. **Sem parser/`parse_invoice` (S59/S60); sem banner React/`use-iptu-alerts` (S63); sem seed (S64); sem `update_with_lines`/statements (S58).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §6, §9 inteiro "Alerta de IPTU", §10.2 `convert_deferred` herda conta, §10.3 exclusão IPTU só no recorrente, §10.5 Atrasados inclui IPTU, §11 cache, §15 segurança, Apêndice A "Totais: 9 planos → 9 WARNING", Apêndice B "Fase 5")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`is_notification_sent_today` (a clonar SP-aware)** | `core/services/notification_service.py:137-142` (`today = timezone.now().date()` UTC → `filter(recipient, type, sent_at__date=today).exists()`) | `is_notification_sent_on(user, type, day)` é o espelho que **recebe** o `day` (sem `timezone.now()`). **NÃO** reusar o UTC — design §9.3 |
| **`create_notification` (persiste + push)** + **`send_push_notification`** | `notification_service.py:30-52` (`Notification.objects.create(..., sent_at=timezone.now(), data)` + push) + `:55-69` (Expo+WebPush; falhas logadas e ignoradas) | O comando usa `create_notification` (in-app garantida; push best-effort dentro dela). **Não** chamar `send_push_notification` direto. O teste "push no-op não derruba in-app" repousa no `:55-69` |
| **`notify_new_proof` (destinatários admin)** | `notification_service.py:145-157` (`User.objects.filter(is_staff=True, is_active=True)` → loop `create_notification`) | Destinatários do `send_finance_alerts` (`is_staff=True, is_active=True`). Diferença: **1 resumo agregado/admin**, não 1/plano (design §9.3) |
| **Comando cron diário + idempotência** | `core/management/commands/send_scheduled_notifications.py:56-83` (`handle`: `today` ⚠️UTC, loop, guard `is_notification_sent_today`, `self.style.SUCCESS`) + `:32-34` (constantes nomeadas, sem magic numbers) | **Estrutura-base** do `send_finance_alerts`. DIFERENÇA: `today_sp()` (não UTC) + `is_notification_sent_on(today_sp())` |
| **Action UNCACHED sensível a tempo/estado** | `finances/viewsets/dashboard_views.py:200-261` (`combined_calendar` + `overdue` — **sem `@cache_result`**, comentário `:202-204`; `today_sp()`; `FinancialReadOnly`) | **Molde exato** do `iptu_alerts`: `@action(detail=False, methods=["get"])`, sem cache (virada de meia-noite não é write → cache nunca invalidaria — design §11). Reusar o comentário-âncora |
| **Overdue via annotation `with_amounts` (sem N+1, sem soma em Python)** | `condo_balance_service.py:319-326` (`overdue_lookup: dict[str, object] = {"is_overdue": True}` + `Bill.objects.with_amounts(today_sp()).filter(**overdue_lookup)`) + `finances/models.py:159-206` (`is_overdue` = `due_date < today ∧ amount_remaining > 0 ∧ lifecycle_state==ACTIVE`) | `IptuAlertService` conta vencidas via `is_overdue` — **nunca** recomputa em Python. O `dict[str, object]` evita o django-stubs rejeitar o nome da annotation |
| Helper TZ SP | `finances/services/timezone.py:22-29` (`today_sp()`/`now_sp()`) | **Todo** "hoje" do alerta vem daqui. `evaluate` é **sempre** chamado com `today_sp()`; o teste trava que nunca recebe data UTC |
| **`Notification` (TYPE_CHOICES a estender)** | `core/models.py:1725-1763` (`TYPE_CHOICES` `:1728-1739`; `type = CharField(max_length=30, choices=TYPE_CHOICES)` `:1746`) | Constantes de classe `TYPE_IPTU_OVERDUE_RISK`/`TYPE_IPTU_PARCELAMENTO_LOST` + entradas + `AlterField`. `max_length=30` comporta `"iptu_parcelamento_lost"` (22) ✓ |
| **`InstallmentPlan`/`Installment`/`Bill` (query do alerta)** | `finances/models.py:417-486` (`embedded` `:441`; `lifecycle_state`/`InstallmentPlanState` `:404-408`; `billing_account` — renomeado S57) + `Installment` `:489-516` (`plan`/`number`/`due_date`) + `Bill.installment` FK `:239` (`related_name="bills"`) + `BillingAccountType.IPTU` (S56) | Query: `InstallmentPlan.objects.filter(lifecycle_state=ACTIVE, embedded=False, billing_account__account_type=IPTU)`. Parcela-bills = `Bill.objects.with_amounts(...).filter(installment__plan=plan)` |
| **Factories `finances`** | `tests/factories.py:281-349` (`make_billing_account` `:281`, `make_bill` `:296`, `make_installment_plan` `:323`, `make_installment` `:341`) | `make_billing_account(account_type="iptu", external_identifier=…)`; `make_installment_plan(embedded=False, billing_account=<IPTU>, lifecycle_state="active")`. **Não** criar factory nova salvo necessidade real (KISS) |
| Mock policy | `tests/CLAUDE.md` | Aqui = **`freezegun`** (congelar `today_sp()`/`is_overdue`) **e** o push (`send_expo_push`/`send_web_push` = fronteiras externas HTTP Expo+VAPID). **NUNCA** mockar `IptuAlertService`, `create_notification`, ORM, `with_amounts`, `is_notification_sent_on` |

### O que as S56/S57/S58 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S56**: enum `BillingAccountType` (`WATER`/`ELECTRICITY`/`IPTU`/`INTERNET`/`GENERIC`, default `GENERIC`) + `SupplyStatus`; campos novos em `BillingAccount` (`account_type`, `holder_name`, `registered_address`, `secondary_identifier`, `supply_status`); unique `unique_active_billing_account_identity`; `BillingAccount.objects.recurring_for_generation()` (exclui IPTU); migração + RLS.
- **S57**: refactor `InstallmentPlan.linked_billing_account → billing_account` (FK, `related_name="installment_plans"`, `clean()` cross-model: `embedded=True` exige conta de consumo, `embedded=False` livre) + espelho no serializer + `convert_deferred` herda `billing_account`. `grep linked_billing_account` = 0.

> **Esta sessão depende de S56 (enum `BillingAccountType.IPTU`) + S57 (`InstallmentPlan.billing_account`).** DEPENDENCY ORDER: **61 depende de 56, 57**. Não recriar enums/campos/refactor aqui. **Se a S56/S57 não estiverem concluídas, PARE** (a query do `evaluate` usa `billing_account__account_type` — falha em runtime/typecheck sem elas).

---

## Escopo

### Arquivos a criar
- `finances/services/iptu_alert_service.py` — `IptuAlertService` (`@staticmethod evaluate(today: date) -> list[IptuRiskRow]` + a dataclass tipada `IptuRiskRow` + os níveis WARNING/CRITICAL como constantes nomeadas).
- `core/management/commands/send_finance_alerts.py` — comando cron diário (resumo agregado por admin + push best-effort, idempotente SP-aware).
- `tests/unit/test_finances/test_iptu_alert_service.py` — testes do serviço (fronteiras 30/06 vs 01/07, deadline, agregação por inscrição, exclusão de embutido/não-IPTU, `today_sp()`).
- `tests/unit/test_finances/test_send_finance_alerts_command.py` — testes do comando (9 planos → 1 resumo/admin; idempotência SP-aware; push no-op não derruba in-app).
- `tests/integration/test_iptu_alerts_endpoint.py` — testes do endpoint (`iptu_alerts` UNCACHED: shape, reflete pagamento sem stale, 401/403, `FinancialReadOnly`).
- `tests/unit/test_notification_service_sent_on.py` — testes do `is_notification_sent_on` (SP-aware, virada de meia-noite).

### Arquivos a modificar
- `core/models.py` — em `Notification` (`:1725-1763`): adicionar as constantes de classe `TYPE_IPTU_OVERDUE_RISK = "iptu_overdue_risk"` e `TYPE_IPTU_PARCELAMENTO_LOST = "iptu_parcelamento_lost"` (antes de `TYPE_CHOICES`) **e** as 2 entradas em `TYPE_CHOICES` (referenciando as constantes, sem magic string). `max_length=30` intacto.
- `core/migrations/000X_alter_notification_type.py` — gerada por `makemigrations core`: `AlterField` em `Notification.type` (choices novos; SQL no-op em Postgres mas migração **obrigatória** — design §9.3/§12).
- `core/services/notification_service.py` — adicionar `is_notification_sent_on(user: User, notification_type: str, day: date) -> bool` (SP-aware: recebe o `day`; espelha `is_notification_sent_today` `:137-142` mas sem `timezone.now()`). `is_notification_sent_today` **intacto** (legado de aluguel usa-o).
- `finances/viewsets/dashboard_views.py` — adicionar `@action(detail=False, methods=["get"]) def iptu_alerts(...)` em `FinanceDashboardViewSet` (`:195+`), **UNCACHED**, delegando a `IptuAlertService.evaluate(today_sp())` + serializando as linhas em PT. Import direto de `IptuAlertService`. Demais actions **intactas**.
- `tests/factories.py` — só se faltar alguma factory para os testes (improvável; `make_installment_plan`/`make_installment`/`make_bill`/`make_billing_account` cobrem). Não duplicar.

### NÃO fazer (pertence a outras sessões)
- **Parser de fatura / `parse_invoice`** (`finances/services/invoice_parsing/`, `bills/parse_invoice`) — **S59/S60**. Esta sessão não importa nem toca o parser.
- **`update_with_lines` / `WaterBillStatement` / `ElectricityBillStatement` / `create_with_lines` estendido** — **S58**. Não tocar `BillService` nem os statements.
- **`IptuRiskBanner` React + `use-iptu-alerts` hook + `useParseInvoice` + `DialogBody`** — **S62/S63**. **Zero frontend** nesta sessão.
- **`seed_condo_utilities` / dados reais / `convert_deferred` herda conta** — **S64/S57**. O `evaluate` apenas **lê** os planos existentes; a herança de `billing_account` em `convert_deferred` é da S57 (esta sessão **confia** que ela já ocorreu — design §10.2).
- **Mudança na exclusão IPTU do ramo recorrente** (`recurring_for_generation()`) — é da **S56** (já feita). As parcelas avulsas de IPTU continuam gerando bills (não excluídas) — esta sessão só **lê** as parcela-bills vencidas.
- **Fallback de e-mail para CRITICAL / regra de risco genérica** — fora de escopo (design §16).
- **Cadência multi-dia de re-notificação WARNING** além do guard 1×/dia — a idempotência por `(recipient, type, sent_at__date)` já garante 1 resumo/dia; **não** inventar janela de N dias especulativa (YAGNI; design §9.3 deixa "máx 1×/N dias" como nota, mas o estado-base é 1×/dia via `is_notification_sent_on`).

---

## Especificação

> Serviço stateless em `finances/services/`, `@staticmethod`. Leitura via annotations `Bill.objects.with_amounts(today)` — **nunca** recomputar `due_date < today`/contar em Python sobre objetos carregados (design §9.1 "via annotations, sem N+1"). "Hoje" **sempre** `finances.services.timezone.today_sp()`. Mensagens ao usuário em **PT**; logs/identificadores/enum values/dataclass em **EN**. Direção: serviço importa `finances.models`, `finances.services.timezone`, `core.models.Notification` (constantes de tipo) — **nunca** views/serializers.

### `IptuRiskRow` (dataclass tipada — fronteira de saída do serviço)

```python
# finances/services/iptu_alert_service.py
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class IptuRiskRow:
    """Uma linha de risco por plano de IPTU ativo. level ∈ {WARNING, CRITICAL}."""
    plan_id: int
    external_identifier: str          # inscrição (billing_account.external_identifier)
    building_label: str               # prédio (street_number) ou "Condomínio" se sem prédio
    level: str                        # IptuAlertService.LEVEL_WARNING / LEVEL_CRITICAL
    overdue_count: int                # nº de parcela-bills vencidas não pagas
    deadline: date | None             # due_date da 1ª parcela AINDA NÃO vencida (None em CRITICAL sem aberta)
    overdue_due_dates: list[date] = field(default_factory=list)  # vencimentos das parcelas em atraso (p/ a mensagem)
    message: str = ""                 # texto PT pronto p/ banner/push
```

### `IptuAlertService.evaluate(today: date) -> list[IptuRiskRow]`

```python
class IptuAlertService:
    LEVEL_WARNING = "warning"
    LEVEL_CRITICAL = "critical"

    @staticmethod
    def evaluate(today: date) -> list[IptuRiskRow]:
        """Risco de perda de parcelamento de IPTU. 1 parcela vencida = WARNING; >=2 = CRITICAL.
        Read-only via Bill.with_amounts(today).is_overdue — sem N+1, sem soma em Python.
        SEMPRE chamar com today_sp() (settings é UTC)."""
```

Regras (design §9.1, Apêndice B Fase 5):
- Query dos planos: `InstallmentPlan.objects.filter(lifecycle_state=InstallmentPlanState.ACTIVE, embedded=False, billing_account__account_type=BillingAccountType.IPTU)`. `select_related("billing_account", "building")` (evitar N+1 ao montar `external_identifier`/`building_label`). **Não** incluir planos `embedded=True` (água/luz), `lifecycle_state != ACTIVE` (deferred/paid/canceled), nem de conta não-IPTU.
- Para cada plano, as **parcela-bills** = `Bill.objects.with_amounts(today).filter(installment__plan=plan)`. **Vencidas não pagas** = as com `is_overdue=True` (a annotation já exige `due_date < today ∧ amount_remaining > 0 ∧ lifecycle_state==ACTIVE` — `finances/models.py:195-204`). `overdue_count = len([b for b in bills if b.is_overdue])` **lido da annotation** (não recomputar a condição).
- **Nível:** `overdue_count == 0` → **não emite linha** (sem alerta); `== 1` → `LEVEL_WARNING`; `>= 2` → `LEVEL_CRITICAL`.
- **Deadline** (design §9.1): `due_date` da **1ª parcela ainda não vencida** = a menor `due_date >= today` (i.e. **NÃO** `is_overdue` e `due_date >= today`) entre as parcela-bills não pagas do plano. Em CRITICAL pode ser `None` (sem parcela aberta restante). **Fronteira (Apêndice B):** `today == 30/06` e a parcela 10 vence 30/06 → `due_date < today` é **falso** no próprio dia → ela **não** é overdue → continua **WARNING** (1 vencida: a parcela 9 de 29/05) com `deadline = 30/06`; `today == 01/07` → a parcela 10 passa a overdue → **2 vencidas** → **CRITICAL**.
- **`overdue_due_dates`**: lista ordenada dos `due_date` das parcela-bills vencidas (para enumerar na mensagem).
- **Mensagem PT** (design §9.1 — montada no serviço, fonte única; o endpoint e o comando reusam):
  - WARNING: `f"IPTU {external_identifier} ({building_label}): 1 parcela atrasada (venc. {DD/MM}). Pague-a este mês junto com a próxima (venc. {DD/MM do deadline}) ou o parcelamento será cancelado."` (se `deadline is None`, omitir o trecho "junto com a próxima").
  - CRITICAL: `f"IPTU {external_identifier} ({building_label}): {N} parcelas atrasadas — parcelamento em risco. Reparcelar na prefeitura."` (**sem** "pague até X").
- **`building_label`**: `plan.building.street_number` se houver `building`, senão `"Condomínio"`. (As contas IPTU reais sempre têm prédio — Apêndice A — mas o serviço é defensivo.)
- **Ordenação**: retornar as linhas ordenadas por `(level CRITICAL antes de WARNING, external_identifier)` — determinístico (o banner/comando enumera estável). Definir a ordem e travar por teste.
- **Sem efeitos colaterais**: `evaluate` **não** cria `Notification`, **não** escreve nada (read-only). O comando é quem persiste.

### `GET /api/finances/finance-dashboard/iptu_alerts` (UNCACHED)

`@action(detail=False, methods=["get"]) def iptu_alerts(self, request) -> Response` em `FinanceDashboardViewSet`. Espelhar `combined_calendar`/`overdue` (`dashboard_views.py:200-261`): **sem `@cache_result`** (mesmo motivo — depende de `today_sp()` + estado de pagamento; a virada de meia-noite não é um write, logo cache não invalidaria — design §11). `permission_classes = [FinancialReadOnly]` (herdado do ViewSet — autenticado lê). Corpo:

```python
@action(detail=False, methods=["get"])
def iptu_alerts(self, request: Request) -> Response:
    # NO cache (design §11): depends on today_sp() + payment state; midnight rollover is not a
    # write, so cache would never be invalidated — same rationale as combined_calendar/overdue.
    rows = IptuAlertService.evaluate(today_sp())
    return Response(
        {
            "alerts": [
                {
                    "plan_id": r.plan_id,
                    "external_identifier": r.external_identifier,
                    "building_label": r.building_label,
                    "level": r.level,
                    "overdue_count": r.overdue_count,
                    "deadline": r.deadline,                       # date | None (DRF serializa ISO)
                    "overdue_due_dates": r.overdue_due_dates,
                    "message": r.message,
                }
                for r in rows
            ],
            "warning_count": sum(1 for r in rows if r.level == IptuAlertService.LEVEL_WARNING),
            "critical_count": sum(1 for r in rows if r.level == IptuAlertService.LEVEL_CRITICAL),
        },
        status=status.HTTP_200_OK,
    )
```
- **Não** retornar shape `{results, count}` (design §8.2 — o interceptor do `client.ts` desempacota `{results}`; o banner consome `alerts`/`warning_count`/`critical_count` diretamente). Sem paginação.
- Sem params obrigatórios (lê o estado atual). `building_id` opcional **não** está no escopo (o banner é condo-wide; YAGNI — não adicionar filtro especulativo).

### `is_notification_sent_on(user, notification_type, day)` — SP-aware (em `core/services/notification_service.py`)

```python
def is_notification_sent_on(user: User, notification_type: str, day: date) -> bool:
    """Whether a notification of the given type was sent to the user on `day` (caller passes
    today_sp(), NOT the UTC date). SP-aware mirror of is_notification_sent_today (design §9.3)."""
    return Notification.objects.filter(
        recipient=user, type=notification_type, sent_at__date=day
    ).exists()
```
- Adicionar `from datetime import date` ao topo se ausente. `is_notification_sent_today` (`:137-142`) **inalterado** (o legado de aluguel chama-o — não quebrar). **Por que SP-aware:** `sent_at` é gravado por `create_notification` com `timezone.now()` (UTC-aware); `sent_at__date=day` compara a parte de **data**. O comando passa `today_sp()` para que a janela de idempotência case com a virada de meia-noite **de São Paulo**, não a de UTC (design §9.3, Apêndice B "idempotência SP-aware (virada de meia-noite)").

### `send_finance_alerts` (comando cron diário — agregado + push best-effort + idempotente)

`core/management/commands/send_finance_alerts.py`, espelhando `send_scheduled_notifications.py:56-83` mas:
- `today = today_sp()` (**não** `timezone.now().date()`).
- `rows = IptuAlertService.evaluate(today)`.
- **Agregação (design §9.3 — obrigatória):** separar `warnings = [r for r in rows if level==WARNING]` e `criticals = [... CRITICAL]`. Para **cada admin** (`User.objects.filter(is_staff=True, is_active=True)`):
  - Se há `warnings` e **não** `is_notification_sent_on(admin, Notification.TYPE_IPTU_OVERDUE_RISK, today)` → **1** `create_notification` resumo com `type=TYPE_IPTU_OVERDUE_RISK`, título `"IPTU: parcelas atrasadas"`, corpo enumerando as inscrições em risco (ex.: `"3 inscrições com 1 parcela atrasada: 516481, 516503, 516449. Pague antes do próximo vencimento para não perder o parcelamento."`), `data={"screen": "finance", "level": "warning", "plan_ids": [...]}`.
  - Se há `criticals` e **não** `is_notification_sent_on(admin, Notification.TYPE_IPTU_PARCELAMENTO_LOST, today)` → **1** `create_notification` resumo com `type=TYPE_IPTU_PARCELAMENTO_LOST`, título `"IPTU: parcelamento em risco"`, corpo enumerando as inscrições com ≥2 atrasadas. (Tipos independentes → a escalada CRITICAL nunca é suprimida por um WARNING já enviado no mesmo dia — design §9.3.)
- **1 resumo por admin por tipo por dia**, não 1 por plano (o loop por-plano + idempotência por `(user,type)` derrubaria 8 dos 9 — design §9.3). Os 9 planos do estado real → **1** resumo WARNING/admin (Apêndice A: "9 planos → 9 WARNING" no banner, mas **1** Notification/admin).
- **Push best-effort:** o push acontece **dentro** de `create_notification` (`send_push_notification`), cujas falhas são engolidas (`notification_service.py:55-69`) → a Notification in-app + o banner permanecem o canal garantido. **Não** chamar `send_push_notification` direto nem condicionar a persistência ao push.
- `self.stdout.write(self.style.SUCCESS(f"Sent {sent} finance alerts."))` (contagem de Notifications criadas). Constantes nomeadas no topo (títulos/`screen`) — sem magic strings repetidas.
- Sem `building_id` (condo-wide). Sem args.

### Tipos novos em `Notification` (core — design §9.3/§12)

Em `core/models.py` `Notification` (`:1725`):
```python
class Notification(AuditMixin, models.Model):
    TYPE_IPTU_OVERDUE_RISK = "iptu_overdue_risk"
    TYPE_IPTU_PARCELAMENTO_LOST = "iptu_parcelamento_lost"

    TYPE_CHOICES = [
        # ... entradas existentes intactas ...
        (TYPE_IPTU_OVERDUE_RISK, "IPTU: parcela em risco"),
        (TYPE_IPTU_PARCELAMENTO_LOST, "IPTU: parcelamento perdido"),
    ]
```
- **Constantes nomeadas** (design §9.3: "`finances` importa as constantes, sem magic string; idempotência usa a mesma constante"). O comando importa `Notification.TYPE_IPTU_OVERDUE_RISK`/`TYPE_IPTU_PARCELAMENTO_LOST`.
- `AlterField` migração obrigatória (`makemigrations core` gera; choices não mudam SQL em Postgres, mas a migração registra o estado — design §12 "(no-op SQL, obrigatória)"). **Sem** RLS aqui (tabela `core_notification` já existe e tem RLS via `0047`).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. Aqui = **`freezegun`** (congelar a data para `today_sp()`/`is_overdue`) **e** o push externo (`core.services.notification_service.send_expo_push` + `send_web_push` — HTTP Expo + VAPID). **NUNCA** mockar `IptuAlertService`, `create_notification`, `is_notification_sent_on`, ORM, `Bill.with_amounts`, signals. Banco real via `--reuse-db`. Dados via factories. `filterwarnings=error`: zero warnings. **Backup antes do migrate** (`.claude/rules/database.md`): `python scripts/backup_db.py` (a migração é `AlterField` no-op, mas a regra é primária).

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_iptu_alert_service.py` (sob `@freeze_time`)

```python
def test_evaluate_returns_empty_when_no_iptu_plans(self) -> None:
    """Sem InstallmentPlan de IPTU ativo/avulso → evaluate retorna []."""

def test_evaluate_ignores_embedded_plans(self) -> None:
    """Plano embedded=True (água/luz) com parcela vencida NÃO gera linha (só avulso de IPTU)."""

def test_evaluate_ignores_non_iptu_account_type(self) -> None:
    """Plano avulso ligado a conta WATER/ELECTRICITY com parcela vencida NÃO gera linha."""

def test_evaluate_ignores_inactive_plan(self) -> None:
    """Plano IPTU avulso com lifecycle_state != ACTIVE (deferred/paid/canceled) é excluído."""

def test_one_overdue_installment_is_warning(self) -> None:
    """1 parcela-bill vencida não paga → level=WARNING, overdue_count=1."""

def test_two_overdue_installments_is_critical(self) -> None:
    """>=2 parcela-bills vencidas → level=CRITICAL, overdue_count=2, deadline pode ser None."""

def test_paid_overdue_installment_not_counted(self) -> None:
    """Parcela com due_date passado mas amount_remaining==0 (paga) NÃO é overdue (annotation)."""

def test_deadline_is_earliest_not_yet_overdue_installment(self) -> None:
    """deadline = menor due_date >= today entre as parcelas não pagas (1ª ainda não vencida)."""

def test_boundary_30_06_is_warning(self) -> None:
    """today=2026-06-30, parcela 9 venc 2026-05-29 (overdue) + parcela 10 venc 2026-06-30
    (due_date < today FALSO no próprio dia → não overdue) → WARNING (1 vencida), deadline=30/06."""

def test_boundary_01_07_is_critical(self) -> None:
    """today=2026-07-01: parcela 10 (venc 30/06) passa a overdue → 2 vencidas → CRITICAL."""

def test_warning_message_pt_includes_inscricao_and_deadline(self) -> None:
    """Mensagem WARNING contém a inscrição, o venc. da atrasada e o venc. do deadline (DD/MM)."""

def test_critical_message_pt_no_pay_until(self) -> None:
    """Mensagem CRITICAL enumera N parcelas e NÃO contém 'pague até'/deadline."""

def test_building_label_falls_back_to_condominio_when_no_building(self) -> None:
    """Plano IPTU sem building → building_label == 'Condomínio'."""

def test_rows_ordered_critical_before_warning_then_external_identifier(self) -> None:
    """Ordenação determinística: CRITICAL antes de WARNING; depois por external_identifier."""

def test_evaluate_uses_passed_today_not_utc(self) -> None:
    """is_overdue usa o `today` passado (freeze UTC já no dia seguinte de SP, mas o caller
    passa today_sp()) — provar que a contagem reflete a data SP, não a UTC."""
```

#### `tests/unit/test_notification_service_sent_on.py`

```python
def test_returns_false_when_none_sent(self) -> None:
    """Sem Notification do tipo no dia → False."""

def test_returns_true_when_sent_on_that_day(self) -> None:
    """Notification criada hoje (sent_at no dia) → True para is_notification_sent_on(today)."""

def test_scoped_by_type(self) -> None:
    """Notification de outro tipo no mesmo dia → False (filtra por type)."""

def test_scoped_by_user(self) -> None:
    """Notification para outro usuário → False (filtra por recipient)."""

def test_sp_aware_midnight_boundary(self) -> None:
    """sent_at numa data UTC X; is_notification_sent_on com day=X True, day=X-1/X+1 False
    (compara sent_at__date == day; o caller controla a data SP)."""
```

#### `tests/unit/test_finances/test_send_finance_alerts_command.py` (sob `@freeze_time`; push mockado)

```python
def test_nine_plans_one_warning_summary_per_admin(self) -> None:
    """9 planos IPTU com 1 parcela vencida cada + 2 admins → 2 Notifications WARNING (1/admin),
    NÃO 18; o corpo enumera as 9 inscrições."""

def test_critical_summary_separate_from_warning(self) -> None:
    """Planos WARNING + planos CRITICAL → 2 Notifications/admin (TYPE_IPTU_OVERDUE_RISK +
    TYPE_IPTU_PARCELAMENTO_LOST); tipos independentes."""

def test_idempotent_same_day_no_duplicate(self) -> None:
    """Rodar o comando 2x no mesmo dia SP → não cria Notification duplicada (is_notification_sent_on)."""

def test_critical_not_suppressed_by_prior_warning_same_day(self) -> None:
    """WARNING já enviado hoje não impede o CRITICAL (tipo distinto) de ser criado no mesmo dia."""

def test_no_admins_no_notifications(self) -> None:
    """Sem usuário is_staff/is_active → 0 Notifications, comando não falha."""

def test_no_iptu_risk_no_notifications(self) -> None:
    """Sem planos em risco → 0 Notifications."""

def test_push_failure_does_not_drop_in_app_notification(self) -> None:
    """send_expo_push/send_web_push mockados levantando exceção → a Notification in-app
    AINDA é persistida (push best-effort dentro de create_notification)."""

def test_no_device_token_still_creates_notification(self) -> None:
    """Admin sem DeviceToken/WebPushSubscription → Notification criada (push no-op, banner intacto)."""

def test_only_staff_active_admins_notified(self) -> None:
    """is_staff=False ou is_active=False → não recebe; só staff ativo."""
```

#### `tests/integration/test_iptu_alerts_endpoint.py` (sob `@freeze_time`; fixture autouse `_disable_throttling`)

> **Throttling sob freezegun**: replicar a fixture `_disable_throttling` de `tests/integration/test_rent_calendar_api.py` (DRF liga `SimpleRateThrottle.timer` e quebra sob `@freeze_time` — nota da S22 no SESSION_STATE). É boundary de infra externa.

```python
def test_iptu_alerts_returns_alerts_shape(self) -> None:
    """GET /api/finances/finance-dashboard/iptu_alerts → 200 {alerts:[...], warning_count, critical_count};
    NÃO tem {results, count} (não paginado)."""

def test_iptu_alerts_warning_row_fields(self) -> None:
    """Linha WARNING tem plan_id/external_identifier/building_label/level/overdue_count/deadline/
    overdue_due_dates/message; deadline em ISO (date | null)."""

def test_iptu_alerts_reflects_payment_without_stale_cache(self) -> None:
    """Pagar a parcela vencida (amount_remaining==0) e re-GET → o alerta some (uncached, sem stale)."""

def test_iptu_alerts_requires_authentication(self) -> None:
    """Sem auth → 401."""

def test_iptu_alerts_readonly_allows_authenticated_non_staff(self) -> None:
    """Usuário autenticado não-staff lê (FinancialReadOnly: read liberado) → 200."""
```

> Rodar (devem **falhar** — serviço/endpoint/comando/constantes ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_iptu_alert_service.py \
>   tests/unit/test_notification_service_sent_on.py \
>   tests/unit/test_finances/test_send_finance_alerts_command.py \
>   tests/integration/test_iptu_alerts_endpoint.py -q
> ```

### 2. GREEN — implementar

1. `core/models.py` — constantes `TYPE_IPTU_OVERDUE_RISK`/`TYPE_IPTU_PARCELAMENTO_LOST` + entradas em `TYPE_CHOICES` (referenciando as constantes). `python scripts/backup_db.py` → `python manage.py makemigrations core` (gera o `AlterField`) → `python manage.py migrate core` → `python manage.py makemigrations --check --dry-run` → "No changes detected".
2. `core/services/notification_service.py` — `is_notification_sent_on(user, type, day)` (import `from datetime import date` se faltar).
3. `finances/services/iptu_alert_service.py` — `IptuRiskRow` + `IptuAlertService.evaluate` (query + annotations + nível + deadline + mensagem PT + ordenação).
4. `finances/viewsets/dashboard_views.py` — `iptu_alerts` action UNCACHED (import `from finances.services.iptu_alert_service import IptuAlertService`).
5. `core/management/commands/send_finance_alerts.py` — `Command.handle` (agregação + idempotência SP-aware + push best-effort via `create_notification`).

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_iptu_alert_service.py tests/unit/test_notification_service_sent_on.py \
  tests/unit/test_finances/test_send_finance_alerts_command.py tests/integration/test_iptu_alerts_endpoint.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- A **mensagem PT** é montada **uma vez** no `IptuAlertService` (`IptuRiskRow.message`); o endpoint e o comando reusam (o comando agrega os textos por inscrição num resumo, mas não reinventa o formato por-plano). Sem magic strings de copy espalhadas — constantes nomeadas (`_WARNING_TITLE`, `_CRITICAL_TITLE`, `_SCREEN`).
- O cálculo de `overdue_count`/`deadline` lê **só** as annotations (`is_overdue`, `due_date`, `amount_remaining`) — confirmar que **nenhuma** condição `due_date < today` é recomputada em Python.
- O comando usa `Notification.TYPE_IPTU_OVERDUE_RISK`/`TYPE_IPTU_PARCELAMENTO_LOST` (constantes de `core.models`), nunca string literal — a idempotência e a criação usam a **mesma** constante.
- `iptu_alerts` action fina (delega ao serviço); a serialização das linhas pode virar um helper privado `_serialize_iptu_rows(rows)` se repetir (KISS — só se houver 2º consumidor; aqui não há, manter inline).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_iptu_alert_service.py tests/unit/test_notification_service_sent_on.py \
  tests/unit/test_finances/test_send_finance_alerts_command.py tests/integration/test_iptu_alerts_endpoint.py \
  --cov=finances --cov=core.services.notification_service --cov=core.management.commands.send_finance_alerts \
  --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ core/models.py core/services/notification_service.py core/management/commands/send_finance_alerts.py tests/unit/test_finances/ tests/unit/test_notification_service_sent_on.py tests/integration/test_iptu_alerts_endpoint.py
ruff format --check finances/ core/models.py core/services/notification_service.py core/management/commands/send_finance_alerts.py tests/
mypy core/ finances/
pyright finances/services/iptu_alert_service.py finances/viewsets/dashboard_views.py core/models.py core/services/notification_service.py core/management/commands/send_finance_alerts.py
```

> **Regressão obrigatória** (não quebrar o legado): rodar os testes do `notification_service` e do comando de aluguel + as actions existentes do dashboard:
> ```bash
> python -m pytest tests/unit/test_notification_service.py tests/unit/test_send_scheduled_notifications.py -q
> python -m pytest tests/integration -k "finance_dashboard or combined_calendar or overdue" -q
> ```

Forward/backward da migração (design §12):
```bash
python manage.py migrate core              # forward
python manage.py migrate core <prev_head>  # backward (AlterField reverte)
python manage.py migrate core              # re-forward
```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). `IptuAlertService` importa `Notification` (constantes de tipo) de `core.models` — OK; **nunca** o contrário. Serviço **não** importa views/serializers. `core/management/commands/send_finance_alerts.py` (em `core`) importa `IptuAlertService` de `finances` — é um **comando**, não o app `core` em runtime de request; aceitável (o comando é o orquestrador cron, fora da hierarquia de camadas de request). Confirmar que `core/models.py`/`core/signals.py` **não** importam `finances`.
- **Lógica de negócio só em serviço** (`.claude/rules/architecture.md`): o cálculo de risco vive em `IptuAlertService`; o endpoint e o comando **delegam** (action fina, comando fino). **Nenhuma** regra de nível/deadline na view ou no comando.
- **Annotations, não Python** (design §9.1): `overdue_count`/`is_overdue`/`deadline` SEMPRE de `Bill.objects.with_amounts(today)`. Proibido recomputar `due_date < today` ou somar/contar em Python sobre QuerySets carregados além do filtro por `is_overdue`.
- **TZ SP única** (design §9.1): `evaluate` é **sempre** chamado com `today_sp()`; o comando usa `today_sp()`; `is_notification_sent_on` recebe `today_sp()`. Proibido `timezone.now().date()` no fluxo de IPTU. `is_notification_sent_today` (UTC) permanece **só** para o legado de aluguel.
- **Endpoint UNCACHED** (design §11): `iptu_alerts` **sem** `@cache_result` (igual `combined_calendar`/`overdue`). **Não** adicionar prefixo `finance-*` nem invalidação para ele.
- **Agregação obrigatória** (design §9.3): **1** resumo/admin/tipo/dia, **não** 1/plano. Idempotência via `is_notification_sent_on` com a **constante** de tipo. CRITICAL e WARNING são tipos independentes (escalada nunca suprimida).
- **Push best-effort** (design §9.3): push acontece dentro de `create_notification`; falha não derruba a Notification in-app nem o banner. **Não** condicionar a persistência ao push nem chamar `send_push_notification` direto.
- **Tipos em `TYPE_CHOICES` como constantes nomeadas** + `AlterField` migração (sem magic string; design §9.3/§12). `max_length=30` comporta os valores.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código. Tipos completos (mypy strict + pyright strict). O truque `dict[str, object]` para a annotation `is_overdue` (espelhar `condo_balance_service.py:322`) evita o django-stubs rejeitar o nome — **não** é supressão.
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from decimal import Decimal`, `from dataclasses import dataclass`, `from django.contrib.auth.models import User`).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; imports diretos da fonte.
- **Sem parser / `parse_invoice` / statements / `update_with_lines` / frontend / seed** (S58/S59/S60/S63/S64). **Sem** novo model/tabela `finances` (só `AlterField` em `core`). **Sem** RLS nova (tabela `core_notification` já tem). **Sem** tocar `recurring_for_generation` (S56).
- Mensagens ao usuário em **Português**; logs/identificadores/enum values em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/services/iptu_alert_service.py` define `IptuRiskRow` (dataclass `frozen`) + `IptuAlertService.evaluate(today: date) -> list[IptuRiskRow]` com `LEVEL_WARNING`/`LEVEL_CRITICAL`; query `InstallmentPlan.objects.filter(lifecycle_state=ACTIVE, embedded=False, billing_account__account_type=IPTU)`; overdue via `with_amounts(today).is_overdue` (sem N+1, sem recompute em Python); 1 vencida → WARNING, ≥2 → CRITICAL, 0 → sem linha; deadline = 1ª parcela não-vencida; mensagens PT; ordenação CRITICAL→WARNING→inscrição; **sem efeitos colaterais**.
- [ ] Fronteira coberta: `today=30/06` (parcela 10 venc 30/06 não-overdue) → WARNING; `today=01/07` → CRITICAL.
- [ ] `GET /api/finances/finance-dashboard/iptu_alerts` adicionado em `FinanceDashboardViewSet`, **UNCACHED**, `FinancialReadOnly`, shape `{alerts:[...], warning_count, critical_count}` (NÃO `{results,count}`); reflete pagamento sem cache stale.
- [ ] `core/models.py Notification` ganha `TYPE_IPTU_OVERDUE_RISK="iptu_overdue_risk"` + `TYPE_IPTU_PARCELAMENTO_LOST="iptu_parcelamento_lost"` como **constantes nomeadas** + entradas em `TYPE_CHOICES`; `AlterField` migração `core` gerada; `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] `core/services/notification_service.py` ganha `is_notification_sent_on(user, type, day)` SP-aware; `is_notification_sent_today` **intacto**.
- [ ] `core/management/commands/send_finance_alerts.py`: `today_sp()`; agrega TODOS os WARNINGs num **único** resumo/admin (+ CRITICALs como tipo independente); destinatários `is_staff=True, is_active=True`; idempotente via `is_notification_sent_on(today_sp())` com as constantes de tipo; push best-effort dentro de `create_notification` (falha não derruba in-app). `SUCCESS` com contagem.
- [ ] Testes cobrem (Apêndice B Fase 5): 9 planos → 1 resumo/admin (não 1); idempotência SP-aware (virada de meia-noite); `iptu_alerts` reflete pagamento sem stale; fronteira 30/06 WARNING vs 01/07 CRITICAL; tipos em `TYPE_CHOICES`; deadline = 1ª parcela não-vencida; push no-op (sem DeviceToken/exceção) não derruba banner/in-app; exclusão de embedded/não-IPTU/inativo; ordenação; SP-aware do `evaluate`.
- [ ] `python -m pytest` dos 4 arquivos passa 100%, **coverage ≥90%** nos módulos tocados (`finances` + `notification_service` + `send_finance_alerts`); regressão (`test_notification_service.py`, `test_send_scheduled_notifications.py`, dashboard actions) verde.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright` nos arquivos tocados limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum parser/`parse_invoice`/statement/`update_with_lines`/frontend/seed criado; nenhum model/tabela `finances` novo; `recurring_for_generation` intacto; `is_notification_sent_today` e as demais actions do dashboard intactas; sem cache no `iptu_alerts`.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_iptu_alert_service.py tests/unit/test_notification_service_sent_on.py \
     tests/unit/test_finances/test_send_finance_alerts_command.py tests/integration/test_iptu_alerts_endpoint.py \
     --cov=finances --cov=core.services.notification_service --cov=core.management.commands.send_finance_alerts \
     --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_notification_service.py tests/unit/test_send_scheduled_notifications.py -q  # regressão
   python -m pytest tests/integration -k "finance_dashboard or combined_calendar or overdue" -q               # regressão dashboard
   ruff check finances/ core/models.py core/services/notification_service.py core/management/commands/send_finance_alerts.py tests/
   ruff format --check finances/ core/models.py core/services/notification_service.py core/management/commands/send_finance_alerts.py tests/
   mypy core/ finances/
   pyright finances/services/iptu_alert_service.py finances/viewsets/dashboard_views.py core/models.py core/services/notification_service.py core/management/commands/send_finance_alerts.py
   python manage.py makemigrations --check --dry-run
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`):
   - Linha da Sessão 61 (status **concluída**) na tabela da feature Contas de serviço tipadas.
   - **Arquivos Criados**: `finances/services/iptu_alert_service.py`; `core/management/commands/send_finance_alerts.py`; `tests/unit/test_finances/test_iptu_alert_service.py`; `tests/unit/test_finances/test_send_finance_alerts_command.py`; `tests/integration/test_iptu_alerts_endpoint.py`; `tests/unit/test_notification_service_sent_on.py`.
   - **Arquivos Modificados**: `core/models.py` (constantes + `TYPE_CHOICES` de IPTU); `core/migrations/000X_alter_notification_type.py`; `core/services/notification_service.py` (`is_notification_sent_on`); `finances/viewsets/dashboard_views.py` (action `iptu_alerts` uncached).
   - **Nota**: "Fase 5 — alerta de IPTU: `IptuAlertService.evaluate(today_sp())` (read-only via `with_amounts.is_overdue`; 1 vencida=WARNING, ≥2=CRITICAL; deadline=1ª não-vencida; fronteira 30/06 vs 01/07); `iptu_alerts` UNCACHED (`FinancialReadOnly`); tipos `iptu_overdue_risk`/`iptu_parcelamento_lost` em `Notification` (+AlterField); `is_notification_sent_on` SP-aware; comando `send_finance_alerts` (9 planos→1 resumo/admin/tipo/dia, push best-effort, idempotente SP-aware). **Banner React/`use-iptu-alerts`=S63; parser=S59/S60; seed=S64.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir da branch da feature — ex.: `feat/condo-utility-bills`):
   ```
   feat(finances): complete session 61 — IPTU alert service + uncached iptu_alerts endpoint + Notification types + SP-aware idempotency + send_finance_alerts command

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **62 — Frontend: `DialogBody` responsivo** (`components/ui/dialog.tsx`) — base do modal. Depois **63** consome este endpoint (`IptuRiskBanner` + `use-iptu-alerts`, uncached/refetch-on-focus).

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.services.iptu_alert_service`**: `IptuAlertService.evaluate(today: date) -> list[IptuRiskRow]` (`LEVEL_WARNING="warning"`, `LEVEL_CRITICAL="critical"`); `IptuRiskRow(plan_id, external_identifier, building_label, level, overdue_count, deadline: date|None, overdue_due_dates: list[date], message)`. **SEMPRE** chamado com `today_sp()`. Read-only (sem efeitos). O comando S64/seed confia que `convert_deferred` (S57) já setou `billing_account` IPTU nos planos reparcelados (senão o alerta não os vê — design §10.2).
- **Endpoint `GET /api/finances/finance-dashboard/iptu_alerts`** (UNCACHED, `FinancialReadOnly`): resposta `{alerts: [{plan_id, external_identifier, building_label, level, overdue_count, deadline, overdue_due_dates, message}], warning_count, critical_count}` — **não** paginado (sem `{results,count}`). **S63** (`use-iptu-alerts`) consome este shape **sem `staleTime` trickery**, `refetchOnWindowFocus` (sensível a tempo/pagamento). O interceptor do `client.ts` não desempacota (não é `{results}`).
- **`core.models.Notification`**: `TYPE_IPTU_OVERDUE_RISK = "iptu_overdue_risk"`, `TYPE_IPTU_PARCELAMENTO_LOST = "iptu_parcelamento_lost"` (constantes de classe + `TYPE_CHOICES`). Qualquer consumidor usa a **constante**, nunca a string literal.
- **`core.services.notification_service.is_notification_sent_on(user, notification_type, day) -> bool`** — SP-aware (caller passa `today_sp()`). `is_notification_sent_today` (UTC) permanece para o legado de aluguel.
- **Comando `send_finance_alerts`** (cron diário, hora SP-safe de manhã): 1 resumo agregado/admin/tipo/dia; push best-effort; idempotente SP-aware. **S64/deploy** agenda o cron (não recriar o comando).
