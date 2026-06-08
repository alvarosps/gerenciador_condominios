# Sessão 56 — Backend: `BillingAccount.account_type` + identidade + `recurring_for_generation()` (exclui IPTU em geração/projeção/calendário)

> **Feature**: Contas de utilidade do condomínio — parser de faturas + IPTU (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: **56** → 57 → 58 → 59 → 60 → 61 → 62 → 63 → 64
> Esta sessão é a **Fase 1 — Tipo + identidade**. Adiciona os enums `BillingAccountType`/`SupplyStatus`, os **5 campos novos** de `BillingAccount` (`account_type`, `holder_name`, `registered_address`, `secondary_identifier`, `supply_status`), a **unique de identidade** `(building, account_type, external_identifier)` parcial, o `clean()`+serializer que **rejeitam `external_identifier` em branco** para contas tipadas (`WATER`/`ELECTRICITY`/`IPTU`), o filtro `account_type` no `BillingAccountViewSet`, e o **predicado único** `BillingAccount.objects.recurring_for_generation()` (exclui `account_type=IPTU`) **fiado** no `BillGenerationService` (geração) e no `CondoProjectionService._projected_expenses` (projeção) — de modo que uma conta IPTU gere **ZERO** bills recorrentes enquanto as parcelas **avulsas** de IPTU permanecem intactas. **Sem statements (S58); sem rename `linked_billing_account→billing_account` (S57); sem parser (S59/60); sem alerta IPTU (S61); sem frontend (S62/63); sem seed (S64).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.1 "`BillingAccount` — alterações", §6 "IPTU" da tabela §2, §10.3 "Exclusão de IPTU só no ramo recorrente", §12 "Migrações & RLS" itens (1), §14 Fase 1, Apêndice B "Fase 1")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`BillingAccount` (modelo a estender) + `clean()` PT + `CheckConstraint` + partial unique idioma** | `finances/models.py:109-155` (campos :112-133; managers duplos :135-136; `Meta.constraints` `CheckConstraint` :140-145; `clean()` PT normalizando `tracking_start_month` :150-155) | É o modelo a alterar. Anexar os 5 campos novos + a unique de identidade no `Meta.constraints` + a regra de `external_identifier` no `clean()`. **Espelhar** o idioma de `clean()` (PT, `raise ValidationError({...})`) |
| **`enum TextChoices`** | `finances/models.py:49-71` (`BillBehavior`/`BillLifecycleState`/`BillingAccountState`/`FundedFrom`) | Forma de `BillingAccountType`/`SupplyStatus` (value EN, label PT). Adicionar **antes** de `BillingAccount` |
| **partial unique `condition=Q(is_deleted=False)`** | `finances/models.py:93-101` (`Category.Meta`: `UniqueConstraint(condition=Q(is_deleted=False), …)`) + `:255-271` (`Bill.Meta` 3 uniques parciais) | Forma exata da `unique_active_billing_account_identity` (parcial em `is_deleted=False`; **sem** `nulls_distinct=False` — `building` nulo distinto é aceitável, design §3.1) |
| **`SoftDeleteManager.from_queryset(QuerySet)` (manager com método custom mantendo soft-delete)** | `finances/models.py:158-211` (`BillQuerySet.with_amounts` + `BillManager = SoftDeleteManager.from_queryset(BillQuerySet)` + `objects = BillManager()`) | **Padrão canônico** do `recurring_for_generation()`: criar `BillingAccountQuerySet(models.QuerySet["BillingAccount"])` com `recurring_for_generation()` → `SoftDeleteManager.from_queryset(...)` → `objects = BillingAccountManager()`. **Reusa** o filtro `is_deleted=False` do `SoftDeleteManager` + expõe o método novo (django-stubs friendly) |
| **`is_account_eligible` / `ensure_month_bills` (ramo recorrente a fiar)** | `finances/services/bill_generation_service.py:48-89` (`is_account_eligible` :48-63 — predicado único de elegibilidade; loop recorrente `for account in BillingAccount.objects.filter(lifecycle_state=ACTIVE)` :77-80) | A **fonte do iter recorrente**. Trocar `BillingAccount.objects.filter(lifecycle_state=ACTIVE)` (:77) por `BillingAccount.objects.recurring_for_generation()` — o filtro `lifecycle_state=ACTIVE` move-se p/ dentro do queryset (`recurring_for_generation` aplica ACTIVE **e** exclui IPTU). `is_account_eligible` continua o predicado por-mês (tracking/end/skip) |
| **`_projected_expenses` (ramo recorrente a fiar)** | `finances/services/condo_projection_service.py:158-212` (loop `accounts = BillingAccount.objects.all()` :172; `if BillGenerationService.is_account_eligible(...)` :176) | A **projeção** deve usar o MESMO predicado. Trocar `BillingAccount.objects.all()` (:172) por `BillingAccount.objects.recurring_for_generation()` (mantendo o `.filter(building_id=…)` :173-174). O ramo **embedded** :194-208 e **standalone** :183-192 (parcelas) **NÃO** mudam — IPTU só sai do ramo recorrente |
| **Calendário (lê bills materializados — exclusão é transitiva)** | `finances/services/condo_calendar_service.py:43-53` (`Bill.objects.with_amounts(today).filter(due_date__year=…, due_date__month=…)`) | **Não itera `BillingAccount`** — lê os `Bill` já gerados. Como a conta IPTU passa a gerar **0** bills recorrentes (geração fiada), o calendário **transitivamente** deixa de mostrar recorrentes de IPTU; parcelas avulsas (que têm `due_date` no mês) continuam aparecendo. **Confirmar por teste** (não há mudança de código de produção no calendário; só asserção de comportamento via geração) |
| **`BillingAccountViewSet` (filtros por query param)** | `finances/viewsets/crud_views.py:100-117` (`get_queryset` com `int_param`/`params.get(...)` p/ `building_id`/`category_id`/`lifecycle_state`) + helper `int_param` em `finances/viewsets/query_params.py` | Adicionar o filtro `account_type` (`params.get("account_type")`) no mesmo idioma de `lifecycle_state` (:114-116) |
| **`BillingAccountSerializer` (dual pattern; campos a estender)** | `finances/serializers.py:105-149` (nested read + `_id` write; `Meta.fields` lista :129-148) | Adicionar `account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status` ao `Meta.fields` + a regra de `external_identifier` em `validate()` (espelha o `clean()` do model — design §3.1) |
| **Migração com RLS (`RunSQL`/`reverse_sql`)** | `finances/migrations/0001_initial.py` (operações `migrations.RunSQL(...)` de ENABLE/DISABLE RLS ao final) + `core/migrations/0047_enable_row_level_security.py` | **Referência** do padrão RLS. **NESTA sessão a tabela `finances_billingaccount` JÁ existe e JÁ tem RLS** (criada na `0001`) → a migração `0004` só faz `AddField`×5 + `AddConstraint` (unique de identidade). **Sem novo RLS** (tabela existente) |
| **Factory `make_billing_account`** | `tests/factories.py:281-293` (`defaults` dict; `user`→`created_by`/`updated_by`; `baker.make("finances.BillingAccount", …)`) | `account_type`/`holder_name`/etc. caem nos defaults do model (`GENERIC`/`""`/`ACTIVE`) — a factory **não** precisa mudar (KISS). Testes passam `account_type=...`/`external_identifier=...` via `**kwargs`. **Só** estender a factory se um teste exigir (improvável) |
| **Mock policy / banco real** | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **nada** a mockar (modelos/managers/serviços reais; constraints via `transaction.atomic()` ao asserir `IntegrityError`). Banco real `--reuse-db`. `filterwarnings=error` |

### O que já existe (PRÉ-REQUISITO — NÃO recriar)

- **`finances` Fases 2–6 inteiras** já estão no disco (S36/S41/S44 modelos; serviços de geração/pagamento/projeção/calendário/saldo/fechamento/distribuição; serializers/viewsets/URLs; `finances/cache.py`+`invalidate_finance_caches`; `finances/signals.py`). Migrações `0001`–`0003`.
- **`BillingAccount.objects = SoftDeleteManager()`** hoje (`finances/models.py:136`); `all_objects = models.Manager()`. Esta sessão **troca** `objects` por `SoftDeleteManager.from_queryset(BillingAccountQuerySet)` (mantém `is_deleted=False` **e** adiciona `recurring_for_generation()`).
- **`is_account_eligible`** (`bill_generation_service.py:48-63`) é o predicado **por-mês** (tracking/end/skip) — **inalterado em assinatura**; só o **iter de origem** (`:77`) e o iter da projeção (`condo_projection_service.py:172`) passam a usar `recurring_for_generation()`.

> **Se as Fases 2–6 não estiverem no disco, PARE.** Esta sessão **estende** `BillingAccount` e fia o predicado nos serviços existentes — não recria modelos/serviços/migrações anteriores.

---

## Escopo

### Arquivos a criar
- `tests/unit/test_finances/test_billing_account_identity.py` — testes do model: enums, 5 campos novos + defaults, unique de identidade (4 contas reais coexistem; duplicata ativa rejeitada; soft-deletada permitida), `clean()` rejeita `external_identifier` em branco p/ tipo água/luz/IPTU.
- `tests/unit/test_finances/test_recurring_for_generation.py` — testes do manager + fiação: `recurring_for_generation()` exclui IPTU e não-ACTIVE; conta IPTU → 0 bills recorrentes; parcela avulsa IPTU intacta; **geração == projeção == calendário** ao centavo no predicado compartilhado.
- `tests/integration/test_billing_account_account_type_api.py` — testes de API: serializer expõe/aceita os campos novos; `validate()` rejeita `external_identifier` em branco p/ tipo tipado (400 PT); filtro `?account_type=` no `BillingAccountViewSet`.

### Arquivos a modificar
- `finances/models.py` — `BillingAccountType`/`SupplyStatus` (enums, antes de `BillingAccount`); `BillingAccountQuerySet` + `BillingAccountManager = SoftDeleteManager.from_queryset(...)`; em `BillingAccount`: 5 campos novos, `objects = BillingAccountManager()`, unique de identidade em `Meta.constraints`, regra de `external_identifier` no `clean()`.
- `finances/services/bill_generation_service.py` — trocar o iter recorrente (`:77`) por `recurring_for_generation()`; `is_account_eligible` (predicado por-mês) **inalterado**.
- `finances/services/condo_projection_service.py` — trocar o iter recorrente (`:172`) por `recurring_for_generation()` (preservando `.filter(building_id=…)`); ramos embedded/standalone **inalterados**.
- `finances/serializers.py` — `BillingAccountSerializer`: 5 campos novos no `Meta.fields` + `validate()` espelhando a regra de `external_identifier`.
- `finances/viewsets/crud_views.py` — `BillingAccountViewSet.get_queryset`: filtro `account_type` (idioma de `lifecycle_state`).
- `finances/migrations/0004_billingaccount_account_type_identity.py` — gerada por `makemigrations finances`: `AddField`×5 + `AddConstraint` (unique de identidade). **Sem** RLS novo (tabela existente).
- `tests/factories.py` — **só se** um teste exigir um helper de identidade (improvável; preferir `make_billing_account(account_type=..., external_identifier=..., building=...)` via `**kwargs`). Não duplicar.

### NÃO fazer (pertence a outras sessões)
- **`RenameField InstallmentPlan.linked_billing_account → billing_account`** + `clean()` cross-model (`embedded ⇒ account de tipo consumo`) + `serializer.validate` + `convert_deferred` herdando `billing_account` — é a **Sessão 57**. **NÃO** tocar `InstallmentPlan`/`InstallmentPlanService`/`condo_projection_service` ramo embedded (`linked_billing_account` continua o nome até a S57). O `recurring_for_generation()` desta sessão é consumido pela projeção **sem** mexer no rename.
- **`WaterBillStatement`/`ElectricityBillStatement`** + `create_with_lines`/`update_with_lines` estendidos + nested serializer + RLS das novas tabelas — **Sessão 58**.
- **Parser de faturas** (`finances/services/invoice_parsing/`, `parse_invoice`, `pdfplumber`) — **Sessões 59/60**.
- **`IptuAlertService`/`iptu_alerts`/`send_finance_alerts`/`Notification` types** — **Sessão 61**.
- **Qualquer frontend** (`DialogBody`, modal, banner, hooks, schema) — **Sessões 62/63**.
- **Seed de dados reais** (`scripts/data/condo_utilities_seed.json`, `seed_condo_utilities`) — **Sessão 64**.
- **Backfill `account_type`** (data-migration tipando linhas existentes): o módulo subiu sem seed → `default=GENERIC` é inócuo (design §12). **NÃO** criar data-migration nesta sessão (YAGNI; o seed da S64 tipa).
- **Calendário**: nenhuma mudança de **código de produção** em `condo_calendar_service.py` (a exclusão é transitiva via geração). Só **asserção** por teste.
- **Nenhum signal novo** (os receivers de `BillingAccount` já invalidam `finance-*` — S37). **Nenhum** `@cache_result` novo.

---

## Especificação

> Convenções (design §3.1): `BillingAccount` é `(AuditMixin, SoftDeleteMixin, models.Model)`, managers duplos, `clean()` em PT, partial unique `condition=Q(is_deleted=False)`. Direção `finances → core`. Mensagens ao usuário em **PT**; values de enum/identificadores/logs em **EN**. **Sem** `from __future__ import annotations`/`TYPE_CHECKING`/`# noqa`/`# type: ignore`/re-export. Tipos completos (mypy strict + pyright strict).

### Enums (em `finances/models.py`, **antes** de `BillingAccount`)

```python
class BillingAccountType(models.TextChoices):
    WATER = "water", "Água"
    ELECTRICITY = "electricity", "Luz"
    IPTU = "iptu", "IPTU"
    INTERNET = "internet", "Internet"
    GENERIC = "generic", "Genérica"


class SupplyStatus(models.TextChoices):
    ACTIVE = "active", "Ligada"
    CUT = "cut", "Cortada"
```

> `SupplyStatus` é distinto de `BillingAccountState` (ligação física da água/luz, não ciclo de vida da conta) — **não** reusar. `default=GENERIC`/`default=ACTIVE`.

### Campos novos de `BillingAccount` (design §3.1)

```python
account_type = models.CharField(
    max_length=20, choices=BillingAccountType.choices, default=BillingAccountType.GENERIC
)
holder_name = models.CharField(max_length=200, blank=True)
registered_address = models.CharField(max_length=255, blank=True)
secondary_identifier = models.CharField(max_length=100, blank=True)
supply_status = models.CharField(
    max_length=10, choices=SupplyStatus.choices, default=SupplyStatus.ACTIVE
)
```

> `external_identifier` (já existe, `:122`) = inscrição/UC principal. `secondary_identifier` = imóvel/matrícula (DMAE), medidor (CEEE), nº lançamento (IPTU). `holder_name`/`registered_address` resolvem desambiguação de titular/endereço como consta na concessionária.

### Unique de identidade (em `BillingAccount.Meta.constraints`)

```python
models.UniqueConstraint(
    fields=["building", "account_type", "external_identifier"],
    condition=Q(is_deleted=False),
    name="unique_active_billing_account_identity",
)
```

> Parcial em `is_deleted=False` é **obrigatório** (soft-delete + recriação quebra sem ele). **Sem** `nulls_distinct=False` (`building` nulo distinto é aceitável — contas tipadas reais sempre têm prédio; design §3.1). O `CheckConstraint expected_amount >= 0` existente (`:141-144`) **permanece**.

### `clean()` — rejeitar `external_identifier` em branco para contas tipadas (design §3.1)

Estender o `clean()` existente (`:150-155`, mantendo a normalização de `tracking_start_month` e a regra de `expected_amount`):

```python
_TYPED_IDENTITY_ACCOUNT_TYPES = frozenset(
    {BillingAccountType.WATER, BillingAccountType.ELECTRICITY, BillingAccountType.IPTU}
)
_ERR_IDENTIFIER_REQUIRED = "Informe a inscrição/UC para contas de água, luz ou IPTU."
```

No `clean()`: se `self.account_type in _TYPED_IDENTITY_ACCOUNT_TYPES` e `not (self.external_identifier or "").strip()` → `raise ValidationError({"external_identifier": _ERR_IDENTIFIER_REQUIRED})`. (Postgres trata `'' = ''` como igual → sem a regra, duas contas tipadas em branco no mesmo prédio colidiriam na unique; a regra é a guarda funcional, não estrutural.) Mensagem como **constante nomeada** (sem magic string).

### Manager / predicado `recurring_for_generation()` (design §10.3 — fonte única)

```python
class BillingAccountQuerySet(models.QuerySet["BillingAccount"]):
    def recurring_for_generation(self) -> "BillingAccountQuerySet":
        """Active accounts that generate a recurring Bill — IPTU is registry-only (design §10.3).

        Single shared predicate used by BillGenerationService.ensure_month_bills,
        CondoProjectionService._projected_expenses, and (transitively, via materialized
        bills) CondoCalendarService — so generation, projection and calendar never diverge.
        IPTU installments live on STANDALONE plans (own Bill) and are NOT excluded here.
        """
        return self.filter(lifecycle_state=BillingAccountState.ACTIVE).exclude(
            account_type=BillingAccountType.IPTU
        )


BillingAccountManager = SoftDeleteManager.from_queryset(BillingAccountQuerySet)
```

E em `BillingAccount`: `objects = BillingAccountManager()` (substitui `SoftDeleteManager()` — `from_queryset` herda o filtro `is_deleted=False` do `SoftDeleteManager`, então `objects.all()` continua excluindo soft-deletados, `with_deleted()`/`deleted_only()` continuam disponíveis). `all_objects = models.Manager()` **inalterado**.

> Os enums `BillingAccountState`/`BillingAccountType` já estão no módulo. `recurring_for_generation()` aplica **ACTIVE** (o `lifecycle_state=ACTIVE` que hoje está no `.filter(...)` do `ensure_month_bills:77`) **e** exclui IPTU — uma só definição. `is_account_eligible` (`:48-63`) **continua** o predicado por-mês (tracking/end/skip) aplicado **sobre** o queryset.

### Fiação no `BillGenerationService` (`bill_generation_service.py:77`)

Trocar:
```python
for account in BillingAccount.objects.filter(lifecycle_state=BillingAccountState.ACTIVE):
```
por:
```python
for account in BillingAccount.objects.recurring_for_generation():
```
`is_account_eligible(account, month_start)` (a checagem por-mês, `:78-79`) **permanece** dentro do loop. `_generate_embedded_lines`/`_generate_installment_bills`/`_generate_payroll_bills` **inalterados** (parcelas/folha não são "recorrentes de conta"; IPTU avulso é standalone). `BillingAccountState` pode ficar importado (ainda usado por `is_account_eligible`).

### Fiação no `CondoProjectionService._projected_expenses` (`condo_projection_service.py:172`)

Trocar:
```python
accounts = BillingAccount.objects.all()
```
por:
```python
accounts = BillingAccount.objects.recurring_for_generation()
```
mantendo `if building_id is not None: accounts = accounts.filter(building_id=building_id)` (`:173-174`) e o loop `if BillGenerationService.is_account_eligible(...)` (`:176`). Os ramos **standalone** (`:183-192`) e **embedded** (`:194-208`) **NÃO** mudam — parcelas de IPTU avulsas continuam somando. Assim **projeção == geração** ao centavo (mesma origem recorrente, mesmas parcelas).

### Serializer (`finances/serializers.py` — `BillingAccountSerializer`)

- Adicionar `account_type`, `holder_name`, `registered_address`, `secondary_identifier`, `supply_status` ao `Meta.fields` (`:129-148`) — após `external_identifier`, antes de `created_at`. São campos diretos (CharField/choices) → o `ModelSerializer` os mapeia sem nested.
- `validate(self, attrs)`: espelhar a regra do model (design §3.1 "clean() + serializer rejeitam") — em **create e update** (resolver `account_type`/`external_identifier` do `attrs` com fallback no `self.instance`): se `account_type ∈ {WATER, ELECTRICITY, IPTU}` e `external_identifier` resolvido em branco → `raise serializers.ValidationError({"external_identifier": _ERR_IDENTIFIER_REQUIRED})`. **Reusar a mesma constante** de mensagem (importar de `finances.models` — direção correta, sem re-export).

### ViewSet (`finances/viewsets/crud_views.py` — `BillingAccountViewSet.get_queryset`)

Adicionar, no idioma de `lifecycle_state` (`:114-116`):
```python
account_type = params.get("account_type")
if account_type is not None:
    queryset = queryset.filter(account_type=account_type)
```

### Migração (`0004_billingaccount_account_type_identity.py`)

`makemigrations finances` gera `AddField`×5 + `AddConstraint(unique_active_billing_account_identity)`. **Sem** `RunSQL` de RLS (a tabela `finances_billingaccount` já tem RLS desde a `0001` — design §12 item (1) é só AddField+unique; RLS novo só nas tabelas da S58). `dependencies` = head atual do `finances` (`0003_*`). `makemigrations --check --dry-run` → "No changes detected".

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. Aqui = **só `freezegun`** quando um teste de geração/projeção depende de "hoje/mês" (`today_sp()`/`is_overdue`); modelos/managers/serializers/serviços/ORM **reais**. `transaction.atomic()` ao asserir `IntegrityError`. Banco real `--reuse-db`. Factories `model-bakery` (`make_billing_account`, `make_bill_skip`, `make_building`, etc.). `filterwarnings=error`: zero warnings. **Backup antes do migrate** (`.claude/rules/database.md`): `python scripts/backup_db.py` (a migração é aditiva — AddField+AddConstraint, baixo risco — mas a regra backup-antes-de-migrate é primária).

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_billing_account_identity.py`

```python
def test_account_type_defaults_to_generic_and_supply_status_to_active(self) -> None:
    """make_billing_account sem args tipa account_type=GENERIC e supply_status=ACTIVE."""

def test_account_type_and_supply_status_choices(self) -> None:
    """BillingAccountType tem WATER/ELECTRICITY/IPTU/INTERNET/GENERIC; SupplyStatus tem ACTIVE/CUT (values EN, labels PT)."""

def test_identity_fields_persist(self) -> None:
    """holder_name/registered_address/secondary_identifier persistem; default blank ('')."""

def test_four_real_same_building_accounts_coexist(self) -> None:
    """2 luz no 836 (UC ...798...-05 vs 650.847.010-16) + 2 IPTU no 850 (516481 vs 516503): external_identifier distinto → as 4 inserem (Apêndice B Fase 1)."""

def test_duplicate_active_identity_rejected(self) -> None:
    """Mesma (building, account_type, external_identifier) ativa → IntegrityError (unique_active_billing_account_identity), dentro de transaction.atomic()."""

def test_soft_deleted_identity_allows_recreate(self) -> None:
    """Soft-delete da 1ª conta libera o slot: recriar (building, account_type, external_identifier) idêntico → OK (unique parcial is_deleted=False)."""

def test_different_account_type_same_identifier_same_building_ok(self) -> None:
    """Mesmo external_identifier mas account_type diferente no mesmo prédio → coexistem (account_type compõe a chave)."""

def test_blank_external_identifier_rejected_for_water(self) -> None:
    """account_type=WATER + external_identifier='' → clean() ValidationError PT 'Informe a inscrição/UC...'."""

def test_blank_external_identifier_rejected_for_electricity_and_iptu(self) -> None:
    """Idem para ELECTRICITY e IPTU (parametrizar/repetir): branco → ValidationError PT."""

def test_blank_external_identifier_allowed_for_generic_and_internet(self) -> None:
    """account_type=GENERIC e INTERNET aceitam external_identifier='' (clean() não rejeita)."""

def test_clean_still_normalizes_tracking_start_month_and_rejects_negative_amount(self) -> None:
    """A regra nova não quebra as existentes: tracking_start_month vira dia 1; expected_amount<0 → ValidationError (regressão do clean() :150-155)."""
```

#### `tests/unit/test_finances/test_recurring_for_generation.py` (sob `@freeze_time` onde houver geração)

```python
def test_recurring_for_generation_excludes_iptu(self) -> None:
    """Conta IPTU e conta WATER ambas ACTIVE → recurring_for_generation() retorna só a WATER."""

def test_recurring_for_generation_excludes_non_active(self) -> None:
    """Conta WATER SUSPENDED/ENDED → fora de recurring_for_generation() (mantém o ACTIVE-only)."""

def test_recurring_for_generation_excludes_soft_deleted(self) -> None:
    """Conta soft-deletada → fora (herda is_deleted=False do SoftDeleteManager.from_queryset)."""

def test_iptu_account_generates_zero_recurring_bills(self) -> None:
    """ensure_month_bills(2026, 6) com 1 conta IPTU ACTIVE e expected_amount>0 → 0 Bill recorrente para a conta IPTU (Apêndice B Fase 1)."""

def test_standalone_iptu_installment_bill_untouched(self) -> None:
    """Plano avulso (embedded=False) de parcelas IPTU com installment due no mês → ensure_month_bills gera 1 Bill(installment=...) (IPTU avulso NÃO é excluído — design §10.3)."""

def test_generation_equals_projection_to_the_cent(self) -> None:
    """Cenário com WATER recorrente (expected_amount) + 1 parcela avulsa IPTU due no mês: Σ amount_total dos bills gerados por ensure_month_bills == CondoProjectionService._projected_expenses(year, month) (mesmo predicado → sem divergência)."""

def test_calendar_excludes_iptu_recurring_transitively(self) -> None:
    """Após ensure_month_bills, CondoCalendarService.combined_month NÃO lista exit recorrente da conta IPTU (0 bills gerados); a parcela avulsa IPTU (due no mês) APARECE."""

def test_projection_recurring_loop_skips_iptu(self) -> None:
    """_projected_expenses com só 1 conta IPTU ACTIVE (sem parcelas) → ramo recorrente soma 0 (IPTU fora de recurring_for_generation)."""
```

#### `tests/integration/test_billing_account_account_type_api.py`

```python
def test_serializer_exposes_new_fields(self) -> None:
    """GET retrieve de uma BillingAccount inclui account_type/holder_name/registered_address/secondary_identifier/supply_status."""

def test_create_with_account_type_and_identity(self) -> None:
    """POST account_type=water + external_identifier + holder_name → 201, persiste os campos."""

def test_create_blank_identifier_for_typed_account_rejected(self) -> None:
    """POST account_type=iptu sem external_identifier → 400 com a mensagem PT em external_identifier (validate())."""

def test_update_to_typed_without_identifier_rejected(self) -> None:
    """PATCH account_type=electricity numa conta com external_identifier='' → 400 PT (validate() resolve via instance)."""

def test_create_generic_blank_identifier_ok(self) -> None:
    """POST account_type=generic sem external_identifier → 201 (regra só p/ água/luz/IPTU)."""

def test_filter_by_account_type(self) -> None:
    """GET ?account_type=iptu retorna só contas IPTU; ?account_type=water só água (get_queryset)."""

def test_non_admin_cannot_write_account_type(self) -> None:
    """FinancialReadOnly: usuário não-staff → POST 403 (regressão de permissão)."""
```

> Rodar (devem **falhar** — campos/enums/manager/migração ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_billing_account_identity.py \
>   tests/unit/test_finances/test_recurring_for_generation.py \
>   tests/integration/test_billing_account_account_type_api.py -q
> ```

### 2. GREEN — implementar

1. `finances/models.py` — enums `BillingAccountType`/`SupplyStatus` (antes de `BillingAccount`); `BillingAccountQuerySet.recurring_for_generation()` + `BillingAccountManager = SoftDeleteManager.from_queryset(BillingAccountQuerySet)` (antes da classe `BillingAccount` ou logo após, espelhando `BillManager` :158-211); 5 campos novos + `objects = BillingAccountManager()` + unique de identidade no `Meta.constraints`; constantes `_TYPED_IDENTITY_ACCOUNT_TYPES`/`_ERR_IDENTIFIER_REQUIRED`; estender `clean()`.
2. Migração:
   ```bash
   python scripts/backup_db.py                       # backup ANTES (regra database.md)
   python manage.py makemigrations finances          # 0004: AddField×5 + AddConstraint
   python manage.py migrate finances
   python manage.py makemigrations --check --dry-run # "No changes detected"
   ```
3. `finances/services/bill_generation_service.py` — iter recorrente → `recurring_for_generation()` (`:77`).
4. `finances/services/condo_projection_service.py` — iter recorrente → `recurring_for_generation()` (`:172`, preservando `building_id`).
5. `finances/serializers.py` — `BillingAccountSerializer.Meta.fields` += 5 campos; `validate()` espelhando a regra (importa `BillingAccountType`/`_ERR_IDENTIFIER_REQUIRED` de `finances.models`).
6. `finances/viewsets/crud_views.py` — filtro `account_type` no `get_queryset`.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_billing_account_identity.py \
  tests/unit/test_finances/test_recurring_for_generation.py \
  tests/integration/test_billing_account_account_type_api.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `recurring_for_generation()` é a **única** fonte do "conta gera recorrente?" — geração e projeção a consomem; o calendário a herda transitivamente (via bills materializados). **Nenhuma** reescrita do filtro `lifecycle_state=ACTIVE`+`exclude(IPTU)` em mais de um lugar.
- A regra de `external_identifier` em branco vive como **constante nomeada** (`_ERR_IDENTIFIER_REQUIRED`) + `frozenset` (`_TYPED_IDENTITY_ACCOUNT_TYPES`) no model; o serializer **importa** a constante (não duplica a string nem a lista de tipos).
- `is_account_eligible` continua o predicado **por-mês** (SRP: queryset = "que contas?", `is_account_eligible` = "neste mês?"). Não fundir os dois.
- Confirmar que **nenhum** ramo embedded/standalone/payroll mudou (IPTU só sai do recorrente) e que o calendário **não** ganhou código de produção.

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_billing_account_identity.py tests/unit/test_finances/test_recurring_for_generation.py \
  tests/integration/test_billing_account_account_type_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/integration/test_billing_account_account_type_api.py
ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_billing_account_account_type_api.py
mypy core/ finances/
pyright finances/
```

Forward/backward da migração (design §12):
```bash
python manage.py migrate finances              # forward (0004)
python manage.py migrate finances 0003         # backward (RemoveConstraint + RemoveField; sem RLS a desfazer)
python manage.py migrate finances              # re-forward (idempotente)
```

> **Regressão obrigatória** (não quebrar geração/projeção/calendário existentes): rodar os testes que tocam o ramo recorrente para garantir que `recurring_for_generation()` não regrediu o caminho não-IPTU:
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_generation_service.py tests/unit/test_finances/test_generation_installments_payroll.py \
>   tests/unit/test_finances/test_condo_projection_service.py tests/unit/test_finances/test_condo_calendar_service.py \
>   tests/unit/test_finances/test_bill_models.py -q
> ```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). `finances/models.py` importa mixins/manager de `core.models` (já importados); serializer importa a constante/enum de `finances.models` (mesmo app); serviços importam de `finances.models` — **nunca** views/serializers de dentro de serviço.
- **Predicado único** (design §10.3): `recurring_for_generation()` é a fonte única do "gera recorrente?" (ACTIVE + exclui IPTU). Geração e projeção a usam; o calendário a herda via bills materializados. **Proibido** reescrever `exclude(account_type=IPTU)` em outro lugar.
- **IPTU exclui SÓ o ramo recorrente** (design §10.3): `_generate_embedded_lines`/`_generate_installment_bills`/`_generate_payroll_bills` e os ramos embedded/standalone da projeção **inalterados** — parcelas avulsas de IPTU continuam gerando 1 bill/mês e somando na projeção.
- **Lógica de negócio só em serviços/managers** (`.claude/rules/architecture.md`): o `clean()` valida só o **próprio** registro (sinal/branco); `recurring_for_generation()` é predicado de query (manager). Unique parcial `condition=Q(is_deleted=False)` **obrigatório** (soft-delete + recriação); **sem** `nulls_distinct=False` na identidade (`building` nulo distinto aceitável); `CheckConstraint expected_amount>=0` existente intacto.
- **Sem rename `linked_billing_account`** (S57): não tocar `InstallmentPlan`/`InstallmentPlanService`/ramo embedded. **Sem** statements/parser/alerta/frontend/seed (S58–64). **Sem** signal/`@cache_result` novo. **Sem** data-migration de backfill (YAGNI; `default=GENERIC`).
- **Calendário sem mudança de código de produção** — exclusão transitiva; só asserção por teste.
- **Migração `0004` aditiva** (AddField×5 + AddConstraint), **sem** RLS novo (tabela existente). Backup antes; forward **e** backward testados; `makemigrations --check` limpo.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`. Corrigir o código de verdade. **Sem** `from __future__ import annotations`/`if TYPE_CHECKING` (PEP 649 nativo); importar tipos direto. **Sem** re-export/barrel/shim.
- **`DecimalField(12,2)`** intacto; quantização só na fronteira (não nesta sessão). Mensagens ao usuário em **PT**; values de enum/logs em **EN**.

## Critérios de Aceite (binários)

- [ ] `finances/models.py` define `BillingAccountType` (`water`/`electricity`/`iptu`/`internet`/`generic`, default GENERIC) e `SupplyStatus` (`active`/`cut`, default ACTIVE); `BillingAccount` ganha `account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status`; `Bill`/`Category`/`Installment`/etc. **intactos**.
- [ ] `BillingAccount.Meta.constraints` ganha `unique_active_billing_account_identity` (`(building, account_type, external_identifier)`, parcial `is_deleted=False`); `CheckConstraint expected_amount>=0` permanece.
- [ ] `BillingAccount.clean()` rejeita `external_identifier` em branco (`""`/whitespace) quando `account_type ∈ {WATER, ELECTRICITY, IPTU}` com a mensagem PT `"Informe a inscrição/UC para contas de água, luz ou IPTU."` (constante nomeada); GENERIC/INTERNET aceitam branco; normalização de `tracking_start_month` e regra de `expected_amount` preservadas.
- [ ] `BillingAccount.objects = BillingAccountManager()` (`SoftDeleteManager.from_queryset(BillingAccountQuerySet)`) expõe `recurring_for_generation()` (ACTIVE + `exclude(account_type=IPTU)`) mantendo `is_deleted=False`/`with_deleted()`/`deleted_only()`; `all_objects` inalterado.
- [ ] `BillGenerationService.ensure_month_bills` itera `recurring_for_generation()` (`:77`); `is_account_eligible` (predicado por-mês) inalterado; embedded/standalone/payroll inalterados. Conta IPTU → **0** bills recorrentes; parcela avulsa IPTU intacta.
- [ ] `CondoProjectionService._projected_expenses` itera `recurring_for_generation()` (`:172`, preservando `building_id`); ramos embedded/standalone inalterados. **Geração == projeção** ao centavo no cenário misto (WATER recorrente + IPTU avulso).
- [ ] `CondoCalendarService` (sem mudança de produção) deixa de listar exit recorrente de IPTU **transitivamente** (0 bills); parcela avulsa IPTU due no mês aparece — provado por teste.
- [ ] `BillingAccountSerializer` expõe/aceita os 5 campos novos; `validate()` espelha a regra de `external_identifier` (create + update via instance), reusando a constante do model; `BillingAccountViewSet` filtra `?account_type=`.
- [ ] Migração `0004_billingaccount_account_type_identity` (AddField×5 + AddConstraint), **sem** RLS novo; `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] Testes cobrem Apêndice B Fase 1: 4 contas reais do mesmo tipo coexistem; duplicata ativa rejeitada / soft-deletada permitida; branco rejeitado p/ água/luz/IPTU; conta IPTU → 0 recorrentes; geração==projeção==calendário no predicado compartilhado; + API (campos, validate 400 PT, filtro, permissão).
- [ ] `python -m pytest` dos 3 arquivos passa 100%, **coverage `finances` ≥90%** nos módulos tocados; regressão (bill_generation/projection/calendar/installments-payroll/bill_models) segue verde.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum rename `linked_billing_account` / statement / parser / alerta IPTU / frontend / seed / data-migration de backfill; `InstallmentPlan`/`InstallmentPlanService`/calendário (produção) intactos.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_billing_account_identity.py tests/unit/test_finances/test_recurring_for_generation.py \
     tests/integration/test_billing_account_account_type_api.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_bill_generation_service.py tests/unit/test_finances/test_generation_installments_payroll.py \
     tests/unit/test_finances/test_condo_projection_service.py tests/unit/test_finances/test_condo_calendar_service.py -q   # regressão
   ruff check finances/ tests/unit/test_finances/ tests/integration/test_billing_account_account_type_api.py
   ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_billing_account_account_type_api.py
   mypy core/ finances/
   pyright finances/
   python manage.py makemigrations --check --dry-run
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`):
   - Linha da Sessão 56 (status **concluída**) na tabela da feature "Contas de utilidade do condomínio — parser + IPTU".
   - **Arquivos Criados**: `tests/unit/test_finances/test_billing_account_identity.py`, `tests/unit/test_finances/test_recurring_for_generation.py`, `tests/integration/test_billing_account_account_type_api.py`.
   - **Arquivos Modificados**: `finances/models.py` (2 enums + 5 campos + manager `recurring_for_generation` + unique de identidade + `clean()`), `finances/migrations/0004_billingaccount_account_type_identity.py`, `finances/services/bill_generation_service.py` (iter recorrente), `finances/services/condo_projection_service.py` (iter recorrente), `finances/serializers.py` (`BillingAccountSerializer` campos + `validate`), `finances/viewsets/crud_views.py` (filtro `account_type`).
   - **Nota**: "Fase 1 — Tipo + identidade: `BillingAccountType`/`SupplyStatus`; 5 campos novos; unique parcial `(building, account_type, external_identifier)`; `clean()`+serializer rejeitam external_identifier em branco p/ água/luz/IPTU; `recurring_for_generation()` (ACTIVE + exclui IPTU) é o predicado único de geração/projeção (calendário herda transitivamente) → conta IPTU gera 0 recorrentes, parcela avulsa IPTU intacta, geração==projeção. **Sem rename linked_billing_account (S57); sem statements (S58); sem parser (S59/60); sem alerta IPTU (S61); sem frontend (S62/63); sem seed (S64).**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-utility-bills`):
   ```
   feat(finances): complete session 56 — BillingAccount account_type + identity + recurring_for_generation (exclude IPTU)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **57 — Refactor `InstallmentPlan.linked_billing_account → billing_account`** (rename + `clean()` cross-model `embedded ⇒ billing_account de tipo consumo WATER/ELECTRICITY/INTERNET` + `serializer.validate` + `InstallmentPlanService.convert_deferred` herdando `plan.billing_account`) — consome `BillingAccountType` desta sessão. A S57 atualiza **todos** os consumidores de `linked_billing_account` (incl. `condo_projection_service` ramo embedded e `bill_generation_service._generate_embedded_lines`).

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.models`**: `BillingAccountType` (`WATER="water"`, `ELECTRICITY="electricity"`, `IPTU="iptu"`, `INTERNET="internet"`, `GENERIC="generic"`; default `GENERIC`); `SupplyStatus` (`ACTIVE="active"`, `CUT="cut"`; default `ACTIVE`). **S57** usa `BillingAccountType.{WATER,ELECTRICITY,INTERNET}` no `clean()` cross-model do `InstallmentPlan` (embedded ⇒ tipo consumo) e `.IPTU` no `convert_deferred`. **S58** usa `SupplyStatus` em `WaterBillStatement.agua_status/esgoto_status`. **S59/60** o parser preenche `account_type`/identidade. **S61** `IptuAlertService` filtra `billing_account__account_type=BillingAccountType.IPTU`.
- **`BillingAccount`** campos novos: `account_type`, `holder_name`, `registered_address`, `secondary_identifier`, `supply_status`; `external_identifier` (existente) = inscrição/UC principal. Unique de identidade `(building, account_type, external_identifier)` parcial `is_deleted=False`. `clean()`+serializer rejeitam `external_identifier` em branco p/ `{WATER,ELECTRICITY,IPTU}` (msg PT constante `_ERR_IDENTIFIER_REQUIRED`).
- **`BillingAccount.objects.recurring_for_generation() -> QuerySet[BillingAccount]`** — ACTIVE + `exclude(account_type=IPTU)`; mantém `is_deleted=False`. **Fonte única** do ramo recorrente: `BillGenerationService.ensure_month_bills` e `CondoProjectionService._projected_expenses` a usam; o `CondoCalendarService` a herda via bills materializados. **S57** (rename embedded) e **S64** (seed) confiam que IPTU **não** gera recorrentes mas parcelas avulsas IPTU sim. `is_account_eligible(account, month_start)` continua o predicado **por-mês** (tracking/end/skip) aplicado sobre o queryset.
- **`BillingAccountViewSet`** filtra `?account_type=<value>` (além de `building_id`/`category_id`/`lifecycle_state`). **S62/63** o frontend usa para listar contas por tipo e desambiguar selects (`name — tipo · external_identifier`).
