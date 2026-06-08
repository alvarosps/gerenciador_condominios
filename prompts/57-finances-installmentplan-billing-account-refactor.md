# Sessão 57 — Refactor atômico `InstallmentPlan.linked_billing_account → billing_account` (rename + clean cross-model + checklist completo de consumidores BE+FE)

> **Feature**: Contas de serviço tipadas (água/luz/IPTU) + parser de fatura + alerta de IPTU + modal responsivo (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: 56 → **57** → 58 → 59 → 60 → 61 → 62 → 63 → 64
> Esta sessão é a **Fase 2** do design: **refatoração completa, sem backwards-compat**, do campo `InstallmentPlan.linked_billing_account` para `billing_account` (a conta dona de **qualquer** plano, não só embutido). É um refactor **atômico BE+FE** (uma única sessão): `RenameField` na migração, nova regra `clean()` cross-model (`embedded=True` ⇒ `billing_account` de **tipo consumo**), espelho em `serializer.validate()`, `convert_deferred` herdando a conta da dívida diferida (IPTU), e a atualização de **TODOS** os consumidores do checklist §4 (incluindo os 3 `select_related` string-literais que nenhum type-checker pega) + o frontend em lockstep. Ao final, `grep -rn linked_billing_account` no repo inteiro = **0 ocorrências**. **Sem statements (S58); sem parser (S59/S60); sem alerta IPTU (S61); sem mexer no `account_type`/identity (S56).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4 inteiro — "Refactor `InstallmentPlan.billing_account` (checklist completo de consumidores)" — §10.2 `convert_deferred` herda `billing_account`, §10.3 exclusão IPTU só no recorrente, §12 ordem das migrações, §14 Fase 2, Apêndice B "Fase 2")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Contratos de enum/manager da S56** (PRÉ-REQUISITO — não recriar): `BillingAccountType` (`WATER`/`ELECTRICITY`/`IPTU`/`INTERNET`/`GENERIC`, default `GENERIC`), `SupplyStatus`, `BillingAccount.account_type` e o manager `BillingAccount.objects.recurring_for_generation()` (exclui `account_type=IPTU`). **A S56 precede esta sessão** (a `clean()` desta sessão lê `account_type` do alvo da FK — design §4 "Ordem da migração: AddField `account_type` ANTES do `RenameField`").
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`, `frontend/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Campo FK a renomear + `clean()` embedded↔linked** | `finances/models.py:444-450` (campo `linked_billing_account` FK `PROTECT` `related_name="installment_plans"`) + `:472-486` (`clean()`: `:479` `self.linked_billing_account_id is None`, `:481`/`:485` chaves do dict de erro PT) | É **o** campo a renomear + a `clean()` a substituir. Manter `null/blank/PROTECT/related_name`; trocar o nome e a **regra** (embedded ⇒ tipo consumo) |
| **Espelho da regra no serializer (DRF não chama `Model.clean()`)** | `finances/serializers.py:337-344` (nested read `linked_billing_account` + write `_id`, **`source="linked_billing_account"` é string literal**), `:357-358` (`Meta.fields`), `:373-392` (`validate()`: `:377-379` lê `linked`, `:380-391` levanta com chaves `linked_billing_account_id`) | O `validate()` espelha a `clean()` (design §4). Trocar `source=`/`fields`/chaves e **estender a regra** ao tipo consumo |
| **Atributo `installment.plan.linked_billing_account` + `select_related` string** | `finances/services/condo_projection_service.py:200` (`.select_related("plan__linked_billing_account")` — **string literal, FieldError em runtime se não renomear**), `:204` (`installment.plan.linked_billing_account`) | Renomear o atributo **e** a string `'plan__billing_account'`. O teste de integração desta sessão executa este path |
| **Atributo + `select_related` string (geração embutida)** | `finances/services/bill_generation_service.py:150` (`.select_related(... "plan__linked_billing_account")`), `:169` (`account = plan.linked_billing_account`), `:170-174` (uso `account`) | Idem — renomear atributo + string `'plan__billing_account'` |
| **`select_related` string no viewset** | `finances/viewsets/installment_payroll_views.py:38-40` (`InstallmentPlan.objects.select_related("category", "building", "linked_billing_account", "condominium")`) | String `"billing_account"` — sem type-checker; executar via API no teste de integração |
| **`convert_deferred` (herdar a conta da dívida)** | `finances/services/installment_plan_service.py:72-134` (assinatura `:72-81`; `locked = Bill.all_objects.select_for_update()` `:94`; `plan = InstallmentPlan.objects.create(...)` `:105-118` — **sem `billing_account` hoje**) | Setar `billing_account=locked.billing_account` no `create` (a dívida diferida IPTU carrega a conta) + **assert `account_type == IPTU`** (design §10.2). `locked.billing_account` é a FK do `Bill` para a conta (S56/S37) |
| **Frontend — schema Zod (read+write)** | `frontend/lib/schemas/finances/installment-plan.schema.ts:38-39` (`linked_billing_account`/`_id`), `:46-55` (`superRefine` embedded⇒id, `path: ['linked_billing_account_id']`) | Renomear campos do schema + path do refine para `billing_account`/`billing_account_id` |
| **Frontend — form schema do modal** | `installment-plan-form-schema.ts:8` (docstring), `:20` (`linked_billing_account_id`), `:24-29` (`superRefine` + `path`) | Renomear o campo do form + path do refine |
| **Frontend — form modal (defaults/fallback/Controller)** | `installment-plan-form-modal.tsx:61` (`planToDefaults` default), `:76-77` (fallback `plan.linked_billing_account_id ?? plan.linked_billing_account?.id ?? null`), `:120` (submit), `:345` (`Controller name="linked_billing_account_id"`) | Renomear nas 4 ocorrências; fallback vira `plan.billing_account_id ?? plan.billing_account?.id ?? null` |
| **Frontend — hook (Omit + destructure)** | `frontend/lib/api/hooks/use-installment-plans.ts:43` (`'linked_billing_account'` no `Omit<…>`), `:105` (destructure `linked_billing_account: _linked_billing_account`) | Renomear no `Omit` do tipo write + na desestruturação que separa o nested read do payload |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas) | Aqui = **nada** a mockar no BE (ORM/serviços reais, `--reuse-db`); FE via MSW (boundary HTTP). `transaction.atomic()` ao asserir `IntegrityError`/constraint |

### O que a S56 já entregou (PRÉ-REQUISITO — NÃO recriar)

- **S56** (Fase 1): `BillingAccountType` + `SupplyStatus` (enums), `BillingAccount.account_type` (default `GENERIC`) + `holder_name`/`registered_address`/`secondary_identifier`/`supply_status`, unique `unique_active_billing_account_identity` (`building`,`account_type`,`external_identifier`; `condition=Q(is_deleted=False)`), `clean()`+serializer rejeitando `external_identifier` em branco para `{WATER,ELECTRICITY,IPTU}`, e o manager `BillingAccount.objects.recurring_for_generation()` (predicado único excluindo IPTU, consumido por geração/projeção/calendário). Migração da S56 com `AddField account_type` + RLS.

> **Se a S56 não estiver concluída, PARE.** A `clean()` desta sessão lê `self.billing_account.account_type` (enum da S56) e a migração `RenameField` precisa vir **depois** do `AddField account_type` (design §4/§12). DEPENDENCY ORDER: **56 → 57**. Não recriar enums/`account_type`/manager aqui.

---

## Escopo

### Arquivos a criar
- `finances/migrations/000X_rename_installmentplan_billing_account.py` — gerada por `makemigrations finances`: **uma** operação `RenameField(model_name="installmentplan", old_name="linked_billing_account", new_name="billing_account")`. **Sem** RLS nova (não cria tabela; `RenameField` só renomeia a coluna `linked_billing_account_id → billing_account_id`). Depende do head da S56.
- `tests/integration/test_finances_installment_billing_account_query_paths.py` — teste de integração que **EXECUTA** cada um dos 3 query paths com `select_related` string-literal (prova de ausência de `FieldError`).

### Arquivos a modificar

**Backend (atributo/kwarg — mypy/pyright pegam):**
- `finances/models.py:444-450` — campo `linked_billing_account` → `billing_account` (mesmo `null/blank/on_delete=PROTECT/related_name="installment_plans"`); `:472-486` — `clean()`: trocar `self.linked_billing_account_id` por `self.billing_account_id`, trocar as chaves do dict de erro (`linked_billing_account` → `billing_account`) e **substituir a regra** (ver Especificação: embedded ⇒ conta de tipo consumo).
- `finances/serializers.py:337-344` — `linked_billing_account`/`linked_billing_account_id` → `billing_account`/`billing_account_id` (**`source="linked_billing_account"` → `source="billing_account"`**); `:357-358` — `Meta.fields`; `:373-392` — `validate()` (lê `billing_account`, estende a regra ao tipo consumo, chaves `billing_account_id`).
- `finances/services/condo_projection_service.py:200` — string `'plan__linked_billing_account'` → `'plan__billing_account'`; `:204` — `installment.plan.linked_billing_account` → `.billing_account`.
- `finances/services/bill_generation_service.py:150` — string `"plan__linked_billing_account"` → `"plan__billing_account"`; `:169` — `account = plan.linked_billing_account` → `.billing_account`.
- `finances/viewsets/installment_payroll_views.py:39` — string `"linked_billing_account"` → `"billing_account"` no `select_related`.
- `finances/services/installment_plan_service.py:105-118` — `convert_deferred`: setar `billing_account=locked.billing_account` no `InstallmentPlan.objects.create(...)` + assert `account_type == IPTU` (design §10.2).

**Backend (testes — quebram se não renomear):**
- `tests/unit/test_finances/test_installment_models.py:70-81` — kwarg `linked_billing_account=` → `billing_account=` + assert da chave do dict (`billing_account`). Estender com os cenários novos (ver TDD).
- `tests/unit/test_finances/test_generation_installments_payroll.py:63,89,106` — kwargs `linked_billing_account=` → `billing_account=`.
- `tests/unit/test_finances/test_condo_projection_service.py:134,154,220` — idem.
- `tests/integration/test_finances_installments_employee_api.py:61` (payload `linked_billing_account_id` → `billing_account_id`), `:66` (`response.data["linked_billing_account"]["id"]` → `["billing_account"]["id"]`).

**Frontend (lockstep com o payload do serializer):**
- `frontend/lib/schemas/finances/installment-plan.schema.ts:38-39,46-55`.
- `frontend/app/(dashboard)/finances/installment-plans/_components/installment-plan-form-schema.ts:8,20,24-29`.
- `frontend/app/(dashboard)/finances/installment-plans/_components/installment-plan-form-modal.tsx:61,76-77,120,345`.
- `frontend/lib/api/hooks/use-installment-plans.ts:43,105`.
- `frontend/tests/mocks/data/finances.ts` (campo `linked_billing_account*` nos mocks de `InstallmentPlan`).
- `frontend/app/(dashboard)/finances/installment-plans/_components/__tests__/installment-plan-form-modal.test.tsx`, `frontend/lib/api/hooks/__tests__/use-installment-plans.test.tsx`, `frontend/app/(dashboard)/finances/installment-plans/__tests__/installment-plans-page.test.tsx` — atualizar payloads/assertions para `billing_account*`.

### NÃO fazer (pertence a outras sessões)
- **`WaterBillStatement`/`ElectricityBillStatement`, `create_with_lines`/`update_with_lines` estendidos** — Fase 3 (**S58**).
- **Parser de fatura** (`invoice_parsing/`, `parse_invoice`) — Fase 4 (**S59/S60**).
- **`IptuAlertService`/`iptu_alerts`/banner/`send_finance_alerts`/tipos de `Notification`** — Fase 5 (**S61**).
- **`DialogBody`/modal responsivo/`useParseInvoice`/import de fatura** — Fase 6 (**S62/S63**).
- **Seed de dados reais** (`seed_condo_utilities`) — Fase 7 (**S64**).
- **Mexer no `account_type`/identity/unique/`recurring_for_generation()`** — é da **S56** (pré-requisito; só **consumir** o enum na `clean()`).
- **Nenhuma tabela/RLS nova** (é só um `RenameField`); **nenhum** statement/serializer novo além dos campos renomeados.

---

## Especificação

> Convenções: serviços stateless `@staticmethod`; mensagens ao usuário em **PT**, logs/identificadores/enum values em **EN**. Direção `finances → core`. **Refactor completo, sem shim/alias/re-export/backwards-compat** (`.claude/rules/design-principles.md`): renomear a fonte e **todos** os consumidores; `grep -rn linked_billing_account` final = 0.

### 1. `finances/models.py` — rename do campo + nova `clean()` cross-model

O campo passa de `linked_billing_account` para `billing_account` (mesmos atributos):

```python
billing_account = models.ForeignKey(
    BillingAccount,
    null=True,
    blank=True,
    on_delete=models.PROTECT,
    related_name="installment_plans",
)  # owner of any plan: consumption account (embedded) or IPTU account / None (standalone)
```

`clean()` — **regra nova** (design §4): `embedded=True` exige `billing_account` **de tipo consumo** (`WATER`/`ELECTRICITY`/`INTERNET`); `embedded=False` é livre (`billing_account=<conta IPTU>` para IPTU, `None` para empréstimo genérico):

```python
_CONSUMPTION_TYPES = frozenset(
    {BillingAccountType.WATER, BillingAccountType.ELECTRICITY, BillingAccountType.INTERNET}
)
_EMBEDDED_NEEDS_CONSUMPTION_MSG = (
    "Plano embutido exige uma conta de consumo (água, luz ou internet)."
)

def clean(self) -> None:
    super().clean()
    if self.total_amount is not None and self.total_amount < 0:
        raise ValidationError({"total_amount": "O valor total não pode ser negativo."})
    if self.installment_count is not None and self.installment_count <= 0:
        raise ValidationError({"installment_count": "O número de parcelas deve ser positivo."})
    if self.embedded:
        if self.billing_account_id is None:
            raise ValidationError({"billing_account": _EMBEDDED_NEEDS_CONSUMPTION_MSG})
        if self.billing_account.account_type not in _CONSUMPTION_TYPES:
            raise ValidationError({"billing_account": _EMBEDDED_NEEDS_CONSUMPTION_MSG})
```

- **Leitura cross-model**: `self.billing_account.account_type` — `clean()` só lê (não consulta agregados de outras linhas; respeita "models = dados + validação" do `.claude/rules/architecture.md`).
- `BillingAccountType` é importado de `finances.models` (mesmo módulo — referência direta; sem re-export).
- A regra antiga "`not embedded and linked is not None` ⇒ erro" é **REMOVIDA** (avulso agora **pode** ter `billing_account`, ex.: IPTU). Não manter a regra antiga.
- Mensagens em **PT**, como constantes nomeadas (sem magic strings repetidas).

### 2. `finances/serializers.py` — campos renomeados + `validate()` espelhando a `clean()`

- `linked_billing_account = BillingAccountSerializer(read_only=True)` → `billing_account = BillingAccountSerializer(read_only=True)`.
- `linked_billing_account_id = PrimaryKeyRelatedField(..., source="linked_billing_account")` → `billing_account_id = PrimaryKeyRelatedField(..., source="billing_account")` (mantém `queryset=BillingAccount.objects.all()`, `write_only`, `required=False`, `allow_null=True`).
- `Meta.fields`: trocar `"linked_billing_account"`/`"linked_billing_account_id"` por `"billing_account"`/`"billing_account_id"`.
- `validate()` — **espelhar a regra nova** (DRF não chama `Model.clean()`): `embedded=True` ⇒ `billing_account` presente **e** de tipo consumo; chaves de erro `billing_account_id` (a chave que o cliente envia). Reusar `_CONSUMPTION_TYPES` (importar do model — fonte única) ou checar `account_type` via o objeto `billing_account` resolvido pelo `source`. Mensagem PT idêntica à da `clean()`.

```python
def validate(self, attrs: dict[str, object]) -> dict[str, object]:
    # DRF does not call Model.clean(); mirror the embedded->consumption-account invariant (design §4).
    embedded = attrs.get("embedded", getattr(self.instance, "embedded", False))
    account = attrs.get("billing_account", getattr(self.instance, "billing_account", None))
    if embedded:
        if account is None or account.account_type not in _CONSUMPTION_TYPES:
            raise serializers.ValidationError(
                {"billing_account_id": _EMBEDDED_NEEDS_CONSUMPTION_MSG}
            )
    return attrs
```

- A regra antiga "avulso não pode ter conta" é removida (espelha o model).

### 3. `convert_deferred` herda `billing_account` (design §10.2 — decisão crítica)

No `InstallmentPlan.objects.create(...)` (`installment_plan_service.py:105-118`), **adicionar** `billing_account=locked.billing_account`. Antes do `create`, **assertar** que a conta é IPTU (a dívida diferida é sempre de uma conta IPTU — design §3.4/§10.2):

```python
if locked.billing_account is None or locked.billing_account.account_type != BillingAccountType.IPTU:
    raise ValidationError({"billing_account": _DEFERRED_NEEDS_IPTU_MSG})
...
plan = InstallmentPlan.objects.create(
    ...
    embedded=False,
    billing_account=locked.billing_account,
    created_by=user,
    updated_by=user,
)
```

- `_DEFERRED_NEEDS_IPTU_MSG` em PT (ex.: "A dívida diferida precisa estar vinculada a uma conta de IPTU."), constante nomeada.
- **Por quê**: sem herdar a conta, as dívidas 2026 reparceladas ficariam invisíveis ao `IptuAlertService` (S61) — a query do alerta é `billing_account__account_type=IPTU` (design §9.1). Teste pinado: `convert_deferred(dívida IPTU)` → `plan.billing_account == conta IPTU`.
- `locked.billing_account` é a FK existente do `Bill` para `BillingAccount` (não tocada aqui). O `convert_deferred` continua `embedded=False` (avulso) — agora **com** `billing_account` (regra antiga "avulso sem conta" não existe mais).

### 4. Consumidores `select_related` string-literais (FieldError em runtime — type-checker NÃO pega)

Renomear as 3 strings: `condo_projection_service.py:200` (`'plan__billing_account'`), `bill_generation_service.py:150` (`'plan__billing_account'`), `installment_payroll_views.py:39` (`'billing_account'`). **+ teste de integração** que executa cada path (Especificação TDD abaixo).

### 5. Frontend (lockstep com o payload)

Renomear `linked_billing_account`/`linked_billing_account_id` → `billing_account`/`billing_account_id` em todos os locais do checklist. O fallback do modal vira `plan.billing_account_id ?? plan.billing_account?.id ?? null`. O `path` dos `superRefine` vira `['billing_account_id']`. **Sem** mudar a lógica (só o nome) — a regra "embedded ⇒ conta de consumo" do design §4 é validada no backend; o frontend mantém o refine `embedded ⇒ billing_account_id` existente (não duplicar a regra de tipo no FE — KISS; o backend é a fronteira de validação canônica).

### Ordem da migração (design §4/§12)
`makemigrations finances` gera **uma** `RenameField`. O head da migração é o da **S56** (que adicionou `account_type`) — garante que `account_type` existe antes do rename. **Backup antes do migrate** (`python scripts/backup_db.py`). Testar forward **e** backward (o `RenameField` é reversível nativamente).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. BE = **nada** a mockar (ORM/serviços reais via `--reuse-db`; `transaction.atomic()` para `IntegrityError`). FE = MSW (boundary HTTP). `filterwarnings=error`: zero warnings. Factories `model-bakery` (`make_billing_account` da S56 aceita `account_type=`; `make_bill`/`make_installment_plan` existentes). **Não** mockar `InstallmentPlanService`/serializer/ORM.

### Testes a escrever

#### `tests/unit/test_finances/test_installment_models.py` (estender o existente `:70-81`)

```python
def test_embedded_plan_requires_billing_account(self) -> None:
    """clean() rejeita embedded=True sem billing_account (chave 'billing_account', PT)."""

def test_embedded_plan_requires_consumption_account_type(self) -> None:
    """clean() rejeita embedded=True com billing_account de tipo IPTU/GENERIC (só WATER/ELECTRICITY/INTERNET)."""

def test_embedded_plan_accepts_water_account(self) -> None:
    """clean() aceita embedded=True com billing_account account_type=WATER (full_clean sem erro)."""

def test_embedded_plan_accepts_electricity_and_internet_accounts(self) -> None:
    """clean() aceita embedded=True com ELECTRICITY e INTERNET (cobre os 3 tipos de consumo)."""

def test_standalone_plan_allows_iptu_billing_account(self) -> None:
    """clean() aceita embedded=False COM billing_account de tipo IPTU (regra antiga 'avulso sem conta' removida)."""

def test_standalone_plan_allows_null_billing_account(self) -> None:
    """clean() aceita embedded=False com billing_account=None (empréstimo genérico)."""

def test_billing_account_field_keeps_protect_and_related_name(self) -> None:
    """billing_account é FK PROTECT related_name='installment_plans' (atributos preservados no rename)."""
```

#### `tests/integration/test_finances_installments_employee_api.py` (atualizar `:61,:66` + cenário novo)

```python
def test_create_embedded_plan_with_billing_account_id(self) -> None:
    """POST payload billing_account_id (água) + embedded=True → 201; response.data['billing_account']['id'] == conta."""

def test_create_embedded_plan_with_iptu_account_id_is_rejected(self) -> None:
    """POST embedded=True + billing_account_id de conta IPTU → 400 com chave 'billing_account_id' (serializer.validate espelha clean)."""

def test_create_standalone_plan_with_iptu_account_id(self) -> None:
    """POST embedded=False + billing_account_id IPTU → 201 (avulso com conta IPTU permitido)."""
```

#### `tests/integration/test_finances_installment_billing_account_query_paths.py` (NOVO — FieldError guard, design §4)

```python
def test_condo_projection_service_executes_embedded_select_related(self) -> None:
    """CondoProjectionService project/_projected_expenses executa o select_related('plan__billing_account')
    com um plano embutido real → sem FieldError; total reflete a parcela embutida."""

def test_bill_generation_service_executes_embedded_select_related(self) -> None:
    """BillGenerationService.ensure_month_bills (ramo embutido) executa select_related('plan__billing_account')
    materializando a linha da parcela no Bill da conta de consumo → sem FieldError."""

def test_installment_plan_viewset_executes_select_related(self) -> None:
    """GET /api/finances/installment-plans/ (admin) executa o queryset com select_related('billing_account')
    → 200, sem FieldError; o item traz billing_account nested."""
```

#### `tests/unit/test_finances/test_condo_projection_service.py` + `test_generation_installments_payroll.py`
Atualizar os kwargs `linked_billing_account=` → `billing_account=` em `:134,:154,:220` e `:63,:89,:106` respectivamente (asserts de comportamento inalterados; só o nome do kwarg).

#### `tests/unit/test_finances/test_installment_plan_service.py` (cenário `convert_deferred` — adicionar ao arquivo existente, ou criar o método se ausente)

```python
def test_convert_deferred_inherits_iptu_billing_account(self) -> None:
    """convert_deferred de um Bill(deferred) com billing_account IPTU → plan.billing_account == a conta IPTU."""

def test_convert_deferred_rejects_non_iptu_billing_account(self) -> None:
    """convert_deferred de um Bill(deferred) sem conta / conta não-IPTU → ValidationError PT (chave 'billing_account')."""
```

#### Frontend

`frontend/lib/api/hooks/__tests__/use-installment-plans.test.tsx` (atualizar `:103,:130,:139`):
```ts
it('envia billing_account_id no payload de create de plano embutido', () => { /* MSW captura body com billing_account_id, sem linked_billing_account */ })
it('destructura billing_account (nested read) fora do payload de update', () => { /* o PATCH não envia billing_account nested, só billing_account_id */ })
```

`frontend/app/(dashboard)/finances/installment-plans/_components/__tests__/installment-plan-form-modal.test.tsx` (atualizar `:49-57,:104-108`):
```ts
it('preenche billing_account_id a partir de plan.billing_account_id ?? plan.billing_account?.id no edit', () => {})
it('exige billing_account_id quando embedded=true (superRefine, path billing_account_id)', () => {})
```

`frontend/app/(dashboard)/finances/installment-plans/__tests__/installment-plans-page.test.tsx` (atualizar `:44-45`): renderiza a linha com `billing_account` nested vindo do mock.

`frontend/tests/mocks/data/finances.ts`: o gerador de `InstallmentPlan` expõe `billing_account`/`billing_account_id` (não `linked_*`).

### 1. RED — escrever/atualizar os testes primeiro

Rodar (devem **falhar** — campo/strings/serializer ainda com nome antigo):
```bash
python -m pytest tests/unit/test_finances/test_installment_models.py \
  tests/unit/test_finances/test_condo_projection_service.py \
  tests/unit/test_finances/test_generation_installments_payroll.py \
  tests/unit/test_finances/test_installment_plan_service.py \
  tests/integration/test_finances_installments_employee_api.py \
  tests/integration/test_finances_installment_billing_account_query_paths.py -q
cd frontend && npx vitest run "installment-plan" "use-installment-plans"
```

### 2. GREEN — implementar (ordem)

1. `finances/models.py` — rename do campo + nova `clean()` (constantes PT + `_CONSUMPTION_TYPES`).
2. `python scripts/backup_db.py` → `python manage.py makemigrations finances` (gera o `RenameField`; head = S56) → `python manage.py migrate finances` → `python manage.py makemigrations --check --dry-run` ("No changes detected").
3. `finances/serializers.py` — campos `billing_account`/`_id` (`source="billing_account"`), `Meta.fields`, `validate()` espelhando a regra.
4. `finances/services/installment_plan_service.py` — `convert_deferred` seta `billing_account=locked.billing_account` + assert IPTU.
5. `condo_projection_service.py:200/204`, `bill_generation_service.py:150/169`, `installment_payroll_views.py:39` — renomear atributos **e** strings de `select_related`.
6. Frontend — renomear nos 4 arquivos de produção + mocks/testes (lockstep com o payload).

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/ tests/integration/test_finances_installments_employee_api.py \
  tests/integration/test_finances_installment_billing_account_query_paths.py -q
cd frontend && npx vitest run "installment-plan" "use-installment-plans"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `_CONSUMPTION_TYPES` e as mensagens PT são **constantes nomeadas únicas** no model; o serializer importa-as da fonte (sem duplicar a tupla nem a string).
- Confirmar que `clean()` e `validate()` aplicam **a mesma** regra (uma definição da semântica; o serializer só re-expressa porque o DRF não chama `clean()`).
- Confirmar `grep -rn linked_billing_account` no repo inteiro (BE+FE+migrations já existentes não-renomeadas + mocks + docs de teste) = **0 ocorrências** (a migração nova usa `RenameField`, que referencia `old_name="linked_billing_account"` — **essa é a única ocorrência aceitável**, pois descreve a renomeação; verificar que é só ela).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/ \
  tests/integration/test_finances_installments_employee_api.py \
  tests/integration/test_finances_installment_billing_account_query_paths.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/integration/
ruff format --check finances/ tests/unit/test_finances/ tests/integration/
mypy core/ finances/
pyright finances/
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Forward/backward da migração:
```bash
python manage.py migrate finances              # forward (RenameField)
python manage.py migrate finances <prev_head>  # backward (renomeia de volta)
python manage.py migrate finances              # re-forward
```

`grep` final (única ocorrência aceitável = o `old_name` do RenameField):
```bash
grep -rn "linked_billing_account" finances/ frontend/ tests/ --include="*.py" --include="*.ts" --include="*.tsx"
```

---

## Constraints

- **Refactor completo, sem backwards-compat / shim / alias / re-export** (`.claude/rules/design-principles.md`): renomear a fonte **e todos** os consumidores; `grep -rn linked_billing_account` final = 0 (salvo o `old_name=` do `RenameField`, que é a descrição da renomeação).
- **Ordem da migração** (design §4/§12): `RenameField` **depois** do `AddField account_type` da S56 (a `clean()` lê `account_type`). `makemigrations` resolve o head — não fixar número.
- **Regra nova** (design §4): `embedded=True` ⇒ `billing_account` de tipo consumo (`WATER`/`ELECTRICITY`/`INTERNET`); `embedded=False` livre. A regra antiga "avulso não pode ter conta" é **removida** (avulso IPTU passa). `clean()` **e** `serializer.validate()` aplicam a mesma regra (uma semântica).
- **`select_related` strings** (`'plan__billing_account'` ×2, `'billing_account'`): renomear as 3; nenhum type-checker pega — o **teste de integração que executa cada path** é a prova de ausência de `FieldError`.
- **`convert_deferred`** (design §10.2): herda `billing_account=locked.billing_account` + assert `account_type==IPTU`. Sem isso o `IptuAlertService` (S61) não enxerga as dívidas reparceladas.
- **`clean()` só lê o próprio registro + o alvo da FK** — não consulta agregados (`.claude/rules/architecture.md` "models = dados + validação").
- **Direção `finances → core`**; serializer/serviços importam de `finances.models` (sem re-export). Frontend em lockstep com o payload do serializer.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`/`@ts-expect-error`. Corrigir o código. mypy strict + pyright strict + ESLint strict + TS strict (`noUncheckedIndexedAccess`).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto. Frontend usa `import type` para tipos.
- **Nenhuma tabela/RLS nova** (só `RenameField`); **nenhum** statement/parser/alerta/modal/seed (S58–S64). **Sem** mexer no `account_type`/identity/`recurring_for_generation()` da S56 (só consumir).
- **Backup antes do migrate** (`.claude/rules/database.md`); migração testada forward **e** backward.
- Mensagens ao usuário em **Português**; logs/identificadores/enum values em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `InstallmentPlan.linked_billing_account` renomeado para `billing_account` (FK `PROTECT`, `null/blank`, `related_name="installment_plans"` preservados) via `RenameField` (head = S56); `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] `clean()` aplica a regra nova: `embedded=True` ⇒ `billing_account` presente **e** de tipo consumo (`WATER`/`ELECTRICITY`/`INTERNET`); `embedded=False` livre (IPTU ou `None`); chaves de erro `billing_account` em PT; regra antiga "avulso sem conta" removida.
- [ ] `serializer.validate()` espelha a regra (chave `billing_account_id`); `billing_account`/`billing_account_id` (`source="billing_account"`) + `Meta.fields` renomeados; payload da API usa `billing_account*`.
- [ ] `convert_deferred` seta `billing_account=locked.billing_account` + assert `account_type==IPTU` (ValidationError PT se não-IPTU/None); teste prova que o plano herda a conta IPTU.
- [ ] As 3 strings de `select_related` renomeadas (`'plan__billing_account'` ×2 + `'billing_account'`); o teste de integração **executa** cada path sem `FieldError`.
- [ ] Frontend: schema, form-schema, form-modal (defaults/fallback/Controller), hook (`Omit`/destructure), mocks e testes renomeados para `billing_account*`; FE em lockstep com o payload do serializer; refine `embedded ⇒ billing_account_id` (path `billing_account_id`).
- [ ] `grep -rn linked_billing_account` no repo (BE+FE+tests) = 0 (única exceção: `old_name=` do `RenameField`).
- [ ] `python -m pytest tests/unit/test_finances/ tests/integration/test_finances_installments_employee_api.py tests/integration/test_finances_installment_billing_account_query_paths.py` passa 100%, **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check && ruff format --check && mypy core/ finances/ && pyright` limpos; `cd frontend && npm run lint && npm run type-check && npm run test:unit` limpos — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`eslint-disable`/`@ts-ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum statement/parser/alerta/modal/seed; nenhuma tabela/RLS nova; `account_type`/identity/`recurring_for_generation()` da S56 intactos.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/ \
     tests/integration/test_finances_installments_employee_api.py \
     tests/integration/test_finances_installment_billing_account_query_paths.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   ruff check finances/ tests/unit/test_finances/ tests/integration/
   ruff format --check finances/ tests/unit/test_finances/ tests/integration/
   mypy core/ finances/
   pyright finances/
   cd frontend && npm run lint && npm run type-check && npm run test:unit
   grep -rn "linked_billing_account" finances/ frontend/ tests/   # = 0 (salvo old_name do RenameField)
   python manage.py makemigrations --check --dry-run
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 57 (status **concluída**) na tabela da feature Contas de serviço tipadas.
   - **Arquivos Criados**: `finances/migrations/000X_rename_installmentplan_billing_account.py`, `tests/integration/test_finances_installment_billing_account_query_paths.py`.
   - **Arquivos Modificados**: `finances/models.py` (rename + clean cross-model), `finances/serializers.py` (campos + validate), `finances/services/{installment_plan_service,condo_projection_service,bill_generation_service}.py`, `finances/viewsets/installment_payroll_views.py`; testes BE (`test_installment_models`, `test_condo_projection_service`, `test_generation_installments_payroll`, `test_installment_plan_service`, `test_finances_installments_employee_api`); FE (`installment-plan.schema.ts`, `installment-plan-form-schema.ts`, `installment-plan-form-modal.tsx`, `use-installment-plans.ts`, `tests/mocks/data/finances.ts` + 3 arquivos de teste).
   - **Nota**: "Fase 2 — refactor atômico `linked_billing_account → billing_account` (sem backwards-compat). `RenameField` (head=S56); `clean()` cross-model embedded⇒conta de consumo (WATER/ELECTRICITY/INTERNET); `serializer.validate()` espelha; `convert_deferred` herda `billing_account` IPTU + assert. 3 `select_related` string-literais renomeadas + teste de integração executando cada path (FieldError guard). FE em lockstep. `grep linked_billing_account`=0."
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature):
   ```
   feat(finances): complete session 57 — rename InstallmentPlan.linked_billing_account to billing_account + cross-model clean + full consumer refactor (BE+FE)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **58 — `WaterBillStatement`/`ElectricityBillStatement` + `create_with_lines`/`update_with_lines` estendidos** — consome o `billing_account` renomeado (a parcela embutida vincula `BillLineItem.installment`). A S58 **adiciona** statements; **não** recria o rename.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`InstallmentPlan.billing_account`** (FK `BillingAccount`, `null`, `PROTECT`, `related_name="installment_plans"`) — substitui `linked_billing_account` em **todo** o sistema (BE+FE, payload da API `billing_account`/`billing_account_id`). **S58/S59/S60/S61** referenciam só `billing_account`.
- **Regra `clean()`/`validate()`**: `embedded=True` ⇒ `billing_account` de tipo consumo (`WATER`/`ELECTRICITY`/`INTERNET`); `embedded=False` livre. `_CONSUMPTION_TYPES` é a fonte única dos tipos de consumo.
- **`convert_deferred`** herda `billing_account=locked.billing_account` (a conta IPTU da dívida diferida) + assert `account_type==IPTU`. **S61** (`IptuAlertService`) confia que os planos convertidos têm `billing_account__account_type=IPTU` — a query do alerta é `InstallmentPlan.objects.filter(lifecycle_state=ACTIVE, embedded=False, billing_account__account_type=IPTU)`.
- **Paths de `select_related`**: `'plan__billing_account'` (projeção/geração) e `'billing_account'` (viewset) — executados no teste de integração desta sessão.
