# Sessão 58 — Backend: `WaterBillStatement` + `ElectricityBillStatement` (leituras) + `create_with_lines`/`update_with_lines` estendidos + cascade soft-delete + serializer + signals

> **Feature**: Contas de utilidade do condomínio — parser de fatura + IPTU (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: 56 → 57 → **58** → 59 → 60 → 61 → 62 → 63 → 64
> Esta sessão é a **Fase 3** do plano: cria as tabelas de detalhe **1:1 por tipo** (`WaterBillStatement`, `ElectricityBillStatement`, **só leituras/consumo — zero dinheiro**), **estende** `BillService.create_with_lines` para aceitar uma `statement` opcional + `installment_id` por linha (setando `BillLineItem.installment`), **adiciona** `BillService.update_with_lines` + `@action(detail=True) bills/update_with_lines` (substitui linhas + upsert da statement no MESMO `Bill`, só se UNPAID + mês OPEN), faz o **cascade soft-delete** da statement quando o `Bill` é soft-deletado, **aninha** `water_statement`/`electricity_statement` (read-only) no `BillSerializer`, e adiciona os **signals** `post_save`/`post_delete` das duas statements invalidando `finance-*`. **Sem parser (S59/S60), sem endpoint `parse_invoice` (S60), sem `IptuAlertService` (S61), sem frontend (S62/S63), sem seed (S64).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.2, §3.3, §3.4, §6, §7, §11 "Statements aninhadas", §13 migrações ordem (3), §14 Fase 3, §18 Apêndice B "Fase 3")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Exemplares de formato/escopo (mesma feature/condo-finance)**: `@prompts/44-finances-reserve-income-close-models.md` (modelos + RLS + signals + factories), `@prompts/37-finances-bill-services-cache.md` (serviços + cache).
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Model `(AuditMixin, SoftDeleteMixin)` + managers duplos + `clean()` PT + Meta** | `finances/models.py:282-317` (`BillLineItem`: `all_objects`/`objects` :300-301; `CheckConstraint` :304-308; `clean()` PT :314-317) | **Forma-base** das duas statements (mesmo idioma de mixins + manager duplo). As statements **não** têm `CheckConstraint` de dinheiro (não há dinheiro) |
| **`OneToOneField(...CASCADE, related_name=...)` + soft-delete não percorre relação** | `finances/models.py:289` (`bill = models.ForeignKey(Bill, on_delete=CASCADE, related_name="line_items")`) + `core/models.py:111-190` (`SoftDeleteMixin.delete()` só seta `is_deleted` no próprio registro — **não** percorre FKs) | `bill = OneToOneField(Bill, CASCADE, related_name="water_statement"/"electricity_statement")`. **Hard**-delete do bill leva a statement (`CASCADE`); **soft**-delete **não** → o serviço apaga a statement explicitamente (design §3.2) |
| **`Bill` model (soft-delete via `SoftDeleteMixin`, sem `delete()` custom)** | `finances/models.py:214-279` (managers :250-251; `Meta.constraints` unique parcial :253-271; `clean()` normaliza `competence_month` :276-279) | O `Bill` **não** sobrescreve `delete()`; o cascade soft-delete da statement vai no **serviço** (`BillService.delete`), não no model (design §7.3) |
| **`BillService.create_with_lines` (alvo da extensão)** | `finances/services/bill_service.py:24-91` (`BillLineInput` TypedDict :24-28; `BillDraft` dataclass :31-44; `create_with_lines` `@transaction.atomic` :61, `full_clean()` :77/:89) | **Estender** este método: aceitar `statement: StatementInput | None` + `BillLineInput.installment` (NotRequired). Manter `@transaction.atomic`/`full_clean()` |
| **Action `create_with_lines` (viewset — estender) + `_serialized_bill`** | `finances/viewsets/crud_views.py:323-369` (monta `BillDraft`+`lines` :339-364; `BillService.create_with_lines(...)` :365) + `_serialized_bill` :216-218 (re-busca com `with_amounts`) | A extensão lê `request.data.get("statement")` e `item.get("installment_id")`; `update_with_lines` espelha o parsing. `_serialized_bill` já re-anota |
| **`BillViewSet` queryset/destroy (default soft-delete) + `get_object`** | `finances/viewsets/crud_views.py:174-218` (`get_queryset` :179-185 `select_related`/`prefetch_related`; **sem** `destroy` override → `ModelViewSet.destroy` chama `SoftDeleteMixin.delete()` na instância) | O `destroy` do `Bill` (soft-delete) precisa de override que delegue ao `BillService.delete` (cascade da statement). `select_related` ganha `water_statement`/`electricity_statement` |
| **`BillSerializer` / `BillLineItemSerializer` (nested read-only)** | `finances/serializers.py:152-234` (`BillLineItemSerializer` :152-158; nested `line_items = …(many=True, read_only=True)` :190; `Meta.fields` :199-225; `validators=[]` :230) | Aninhar `water_statement = WaterBillStatementSerializer(read_only=True)` e `electricity_statement = …(read_only=True)` (ambos `required=False`/nullable — só um existe por bill, ou nenhum) |
| **`CondoMonthCloseService.assert_open(competence_month)` (guard mês fechado)** | `finances/services/condo_month_close_service.py:60-68` (`assert_open` levanta `ValidationError` PT se `status=CLOSED`; sem registro = aberto = no-op) | `update_with_lines` chama `assert_open(bill.competence_month)` (rejeita mês fechado com 400 PT) |
| **`with_amounts(today)` para `payment_status`/UNPAID (annotation, nunca Python)** | `finances/viewsets/crud_views.py:179-184` (`Bill.objects.with_amounts(today_sp())`) + `finances/models.py` (`BillManager.with_amounts` — `payment_status` ∈ `open`/`partial`/`paid`) | `update_with_lines` decide "UNPAID" via `with_amounts(today_sp()).get(pk=...).payment_status == 'open'` (ou `amount_paid == 0`). **Nunca** somar `allocations` em Python |
| **Signals do `finances` (adicionar receivers das statements)** | `finances/signals.py:34-69` (`_FINANCE_MODELS` tupla :34-49; loop `post_save.connect`/`post_delete.connect` :59-69) | Adicionar `WaterBillStatement`/`ElectricityBillStatement` à tupla `_FINANCE_MODELS` (o loop já conecta os dois sinais — **uma** linha cada, DRY) |
| **Migração com RLS (`RunSQL`/`reverse_sql`)** | `core/migrations/0047_enable_row_level_security.py:16-134` (`ENABLE_RLS`/`DISABLE_RLS`; `RunSQL(sql=…, reverse_sql=…)`) + `finances/migrations/0003_reserve_condomonthclose_incomeentry_reservemovement.py` (RLS das tabelas da S44 — mesmo padrão no app `finances`) | **Obrigatório** (`.claude/rules/database.md` + design §13 ordem (3)): as 2 tabelas novas (`finances_waterbillstatement`, `finances_electricitybillstatement`) habilitam RLS na **mesma** migração |
| **Factories `make_<model>()`** | `tests/factories.py` (`make_bill`, `make_bill_line_item`, `make_billing_account` — S36; estilo `**kwargs`/`defaults`/`baker.make`, `user` → `created_by`/`updated_by`) | Adicionar `make_water_statement`, `make_electricity_statement` (FK `bill` default = `make_bill`) |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` p/ tempo) | Aqui: ORM/serviços reais; `freezegun` só se precisar fixar `today_sp()` (overdue/UNPAID). `transaction.atomic()` ao asserir `IntegrityError`. `--reuse-db` |

### O que as S56/S57 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S56** (account-type + identidade): em `finances/models.py` — `class BillingAccountType(TextChoices)` (`WATER`/`ELECTRICITY`/`IPTU`/`INTERNET`/`GENERIC`, default `GENERIC`) e `class SupplyStatus(TextChoices)` (`ACTIVE="active","Ligada"`; `CUT="cut","Cortada"`); campos novos em `BillingAccount` (`account_type`, `holder_name`, `registered_address`, `secondary_identifier`, `supply_status`); `UniqueConstraint(... name="unique_active_billing_account_identity")`; `clean()`/serializer rejeitam `external_identifier` em branco quando `account_type ∈ {WATER,ELECTRICITY,IPTU}`; `BillingAccount.objects.recurring_for_generation()` (exclui `IPTU`); migração + RLS.
- **S57** (refactor `InstallmentPlan.billing_account`): `linked_billing_account` → `billing_account` em **todos** os consumidores (model/serializer/services/views/frontend/testes); `clean()` cross-model (`embedded=True ⇒ billing_account de tipo consumo`); `convert_deferred` seta `plan.billing_account`. `grep linked_billing_account` = 0.

> **`SupplyStatus` é da S56.** Esta sessão **importa** `SupplyStatus` de `finances.models` (já definido lá) para os campos `agua_status`/`esgoto_status` da `WaterBillStatement`. **Se a S56/S57 não estiverem concluídas, PARE** (DEPENDENCY ORDER 56,57 → 58). Não recriar enums/campos/refactor aqui.

> **`BillLineItem.installment` JÁ EXISTE** (`finances/models.py:293-295`, criado na S41 — `FK "Installment", SET_NULL, related_name="line_items"`). Esta sessão **só passa a setá-lo** em `create_with_lines`/`update_with_lines`; **não** cria o campo nem altera o model `BillLineItem` (salvo nada).

---

## Escopo

### Arquivos a criar
- `finances/migrations/000X_water_electricity_statement.py` — gerada por `makemigrations finances` (head atual `0003`): `CreateModel` de `WaterBillStatement` + `ElectricityBillStatement` **e** `RunSQL` de RLS (ENABLE/DISABLE) para as **2 tabelas novas** (`finances_waterbillstatement`, `finances_electricitybillstatement`). (Após a S56/S57, o head pode ser `0005`+ — `makemigrations` resolve a numeração.)
- `tests/unit/test_finances/test_bill_statement_models.py` — testes de modelo das 2 statements (herança/managers, campos/null, `OneToOne` CASCADE hard-delete, soft-delete via mixin, `agua_status`/`esgoto_status` choices `SupplyStatus`, `__str__` PT).
- `tests/unit/test_finances/test_bill_statement_service.py` — testes de `create_with_lines` (statement + `installment_id`) + `update_with_lines` (substitui linhas/upsert statement, guard UNPAID+OPEN) + cascade soft-delete + nested serializer.
- `tests/integration/test_finances_bill_statement_api.py` — testes do `@action bills/update_with_lines` (200 substitui; 400 pago; 400 mês fechado; nested no GET; 401/403).

### Arquivos a modificar
- `finances/models.py` — **adicionar** `WaterBillStatement` + `ElectricityBillStatement` (conforme §3.2/§3.3 do design). Importar `SupplyStatus` (S56) — já no módulo. **Não** alterar `Bill`/`BillLineItem`/`BillingAccount`.
- `finances/services/bill_service.py` — `BillLineInput` ganha `installment: NotRequired[Installment | None]`; novo `StatementInput`/`WaterStatementInput`/`ElectricityStatementInput` (TypedDict tipado por tipo); `create_with_lines` seta `BillLineItem.installment` + cria a statement 1:1 atômico; novo `BillService.update_with_lines(...)` (substitui linhas + upsert statement, guard UNPAID+OPEN) e `BillService.delete(bill, user=None)` (cascade soft-delete da statement).
- `finances/serializers.py` — `WaterBillStatementSerializer` + `ElectricityBillStatementSerializer` (read-only); aninhar `water_statement`/`electricity_statement` no `BillSerializer` (`read_only=True`, no `Meta.fields`).
- `finances/viewsets/crud_views.py` — estender a action `create_with_lines` (`:323-369`) para ler `statement` + `installment_id`; novo `@action(detail=True, methods=["post"]) update_with_lines`; override `destroy` no `BillViewSet` delegando a `BillService.delete`; `get_queryset` ganha `water_statement`/`electricity_statement` em `select_related`.
- `finances/signals.py` — adicionar `WaterBillStatement`/`ElectricityBillStatement` à tupla `_FINANCE_MODELS` (`:34-49`).
- `tests/factories.py` — `make_water_statement`, `make_electricity_statement`.

### NÃO fazer (pertence a outras sessões)
- **Parser de fatura** (`finances/services/invoice_parsing/`, `pdfplumber`, DMAE/CEEE) — **S59**. Esta sessão **não** importa `pdfplumber` nem cria parser.
- **Endpoint `bills/parse_invoice`** (`MultiPartParser`, draft em memória) — **S60**. Aqui só `update_with_lines` (que **persiste**).
- **`IptuAlertService` + `finance-dashboard/iptu_alerts` + `Notification` choices + `send_finance_alerts`** — **S61**.
- **Frontend** (`DialogBody`, modal responsivo, `useParseInvoice`/`useUpdateBillWithLines`, `bill.schema.ts`, banner IPTU) — **S62/S63**.
- **Seed de dados reais** (`scripts/`, competence `2026-06-01`) — **S64**.
- **Re-baseline de `Installment` futuros** (design §6 "Futuros") — é do parser/projeção (S59/S64), **não** desta sessão. `create_with_lines`/`update_with_lines` apenas **vinculam** `BillLineItem.installment` à parcela existente; **não** mexem em `Installment.amount` nem em meses < N.
- **Nenhuma alteração de `Bill`/`BillLineItem`/`BillingAccount`/`Payment`/`Installment`** (modelos das S36/S41/S56) — as statements só **referenciam** o `Bill`.

---

## Especificação

> Serviços stateless em `finances/services/`, `@staticmethod`. `@transaction.atomic` + `full_clean()` (mensagens PT). "Hoje" via `finances.services.timezone.today_sp()` (design §4). Direção `finances → core`. Mensagens ao usuário em **PT**; logs/identificadores/enum values/atributos em **EN**. **Sem dinheiro nas statements** — todo valor é `BillLineItem` (fonte única, design §3.2).

### Modelos (anexar a `finances/models.py`, conforme design §3.2/§3.3)

```python
# imports já no módulo: models, AuditMixin, SoftDeleteMixin, SoftDeleteManager, Bill, SupplyStatus (S56).

class WaterBillStatement(AuditMixin, SoftDeleteMixin, models.Model):
    """Detalhe 1:1 de uma conta de ÁGUA (DMAE) — só leituras/consumo. Dinheiro = BillLineItem."""

    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="water_statement")
    consumo_m3 = models.PositiveIntegerField()
    leitura_anterior = models.PositiveIntegerField(null=True, blank=True)
    leitura_atual = models.PositiveIntegerField(null=True, blank=True)
    leitura_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    data_leitura = models.DateField(null=True, blank=True)
    agua_status = models.CharField(max_length=10, choices=SupplyStatus.choices, default=SupplyStatus.ACTIVE)
    esgoto_status = models.CharField(max_length=10, choices=SupplyStatus.choices, default=SupplyStatus.ACTIVE)

    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # __str__ PT (ex.: f"Água {self.consumo_m3} m³ — {self.bill}")


class ElectricityBillStatement(AuditMixin, SoftDeleteMixin, models.Model):
    """Detalhe 1:1 de uma conta de LUZ (CEEE) — só leituras/consumo. Dinheiro = BillLineItem."""

    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="electricity_statement")
    consumo_kwh = models.PositiveIntegerField()
    energia_injetada_kwh = models.PositiveIntegerField(null=True, blank=True)  # null = sem solar
    leitura_anterior = models.PositiveIntegerField(null=True, blank=True)
    leitura_atual = models.PositiveIntegerField(null=True, blank=True)
    leitura_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    classe = models.CharField(max_length=60, blank=True)
    bandeira = models.CharField(max_length=40, blank=True)

    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # __str__ PT (ex.: f"Luz {self.consumo_kwh} kWh — {self.bill}")
```

> **Sem `CheckConstraint`** (campos `PositiveIntegerField` já barram negativos no DB; sem regra cross-field para a S58 — a plausibilidade `leitura_atual >= leitura_anterior` é **warning do parser**, S59, não constraint — design §3.2). **Soft-delete não percorre a relação** (`SoftDeleteMixin.delete()` só toca o próprio registro) → o cascade soft-delete fica no `BillService.delete` (abaixo). `CASCADE` cobre só o **hard**-delete.

### `bill_service.py` — extensão (design §7)

```python
from typing import NotRequired, TypedDict
from finances.models import (
    Bill, ElectricityBillStatement, Installment, WaterBillStatement, ...  # já: BillingAccount, BillLineItem, Category, BillLifecycleState
)

class BillLineInput(TypedDict):
    description: str
    amount: Decimal
    is_offset: NotRequired[bool]
    category: NotRequired[Category | None]
    installment: NotRequired[Installment | None]   # NOVO — a parcela embutida (BillLineItem.installment)


class WaterStatementInput(TypedDict):
    consumo_m3: int
    leitura_anterior: NotRequired[int | None]
    leitura_atual: NotRequired[int | None]
    leitura_dias: NotRequired[int | None]
    data_leitura: NotRequired[date | None]
    agua_status: NotRequired[str]
    esgoto_status: NotRequired[str]


class ElectricityStatementInput(TypedDict):
    consumo_kwh: int
    energia_injetada_kwh: NotRequired[int | None]
    leitura_anterior: NotRequired[int | None]
    leitura_atual: NotRequired[int | None]
    leitura_dias: NotRequired[int | None]
    classe: NotRequired[str]
    bandeira: NotRequired[str]
```

`create_with_lines(draft, lines, statement=None, user=None) -> Bill`:
- **Assinatura estendida** (compat com o caller atual `:365`: 3º posicional vira `statement` opcional kw; o caller da S38 passa só `(draft, lines, user=...)` e continua válido — `statement` default `None`).
- `statement: WaterStatementInput | ElectricityStatementInput | None`. O **tipo** é decidido por `draft.billing_account.account_type` (`WATER` → `WaterBillStatement`; `ELECTRICITY` → `ElectricityBillStatement`). Sem `billing_account` ou `account_type` não-consumo → `statement` **deve ser `None`** (passar statement nesse caso → `ValidationError` PT `"Statement só é permitida para contas de água ou luz."`).
- Dentro do `@transaction.atomic` existente: após salvar o `bill` e as linhas (agora setando `installment=line.get("installment")`), se `statement is not None`, criar a `WaterBillStatement`/`ElectricityBillStatement(bill=bill, **statement)` + `full_clean()` + `save()`. **Atômico**: falha em qualquer ponto → rollback total (nenhum bill/linha/statement órfão).
- `created_by/updated_by = user` na statement quando `user` dado.

`update_with_lines(bill, lines, statement=None, user=None) -> Bill`:
- **Guard UNPAID** (design §7.2): relê `Bill.objects.with_amounts(today_sp()).get(pk=bill.pk)`; se `payment_status != "open"` (i.e. tem pagamento) → `ValidationError` PT `"Não é possível alterar uma conta com pagamento. Desfaça o pagamento primeiro."`. **Nunca** somar `allocations` em Python.
- **Guard mês OPEN**: `CondoMonthCloseService.assert_open(bill.competence_month)` (levanta PT se fechado — design §7.2 "reabra o mês primeiro").
- `@transaction.atomic`: **hard-delete** das `BillLineItem` vivas do bill (`bill.line_items.all().delete()` via `all_objects`? — usar `BillLineItem.objects.filter(bill=bill).delete()` que é soft-delete do mixin; **decidir e travar por teste**: substituição = soft-delete das antigas + criação das novas, preservando histórico de auditoria; `with_amounts` ignora soft-deletadas). Recriar as linhas (com `installment`). **Upsert da statement**: `update_or_create` 1:1 por `bill` (tipo decidido por `account_type`); statement de tipo divergente do já existente → soft-deletar a antiga e criar a nova (não pode haver duas).
- **Preserva o mesmo `Bill` (pk/pagamentos)** — não recria o bill. Retorna o `bill` (caller re-anota via `_serialized_bill`).

`delete(bill, user=None) -> None`:
- `@transaction.atomic`: soft-deletar a statement viva (se houver — `WaterBillStatement.objects.filter(bill=bill)` / idem electricity) com `deleted_by=user`, **depois** `bill.delete(deleted_by=user)` (soft). Espelha o cascade soft-delete de `Expense.delete()` (`core/models.py`). Cobre o gap design §7.3 ("`SoftDeleteMixin.delete()` não percorre relações").

### `crud_views.py` — actions + destroy

- **`create_with_lines`** (`:323-369`): ler `request.data.get("statement")` (dict|None) e, por linha, `item.get("installment_id")` → resolver `Installment.objects.filter(pk=...).first()`. Montar o `statement` tipado a partir do dict cru (coerções defensivas; `int(...)`/`date.fromisoformat(...)` sob `try/except → 400 PT`). Chamar `BillService.create_with_lines(draft, lines, statement=statement, user=...)`.
- **`update_with_lines`** (NOVO `@action(detail=True, methods=["post"])`): `bill = self.get_object()`; parsing idêntico de `line_items`+`statement`; `BillService.update_with_lines(bill, lines, statement=statement, user=...)` em `try/except ValidationError → 400 PT`; sucesso → `self._serialized_bill(bill)` 200.
- **`destroy`** (override no `BillViewSet`): `bill = self.get_object()`; `BillService.delete(bill, user=cast(User, request.user))`; `204`. (Default `ModelViewSet.destroy` chamaria `bill.delete()` direto, **deixando a statement viva** — o gap §7.3.)
- `get_queryset`: `select_related(..., "water_statement", "electricity_statement")` (1:1 → `select_related`, não `prefetch`).

### `serializers.py` — statements aninhadas (read-only)

```python
class WaterBillStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterBillStatement
        fields = ["id", "consumo_m3", "leitura_anterior", "leitura_atual", "leitura_dias",
                  "data_leitura", "agua_status", "esgoto_status"]
        read_only_fields = fields

class ElectricityBillStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectricityBillStatement
        fields = ["id", "consumo_kwh", "energia_injetada_kwh", "leitura_anterior", "leitura_atual",
                  "leitura_dias", "classe", "bandeira"]
        read_only_fields = fields
```

No `BillSerializer`: `water_statement = WaterBillStatementSerializer(read_only=True)` + `electricity_statement = ElectricityBillStatementSerializer(read_only=True)`; adicionar ambos a `Meta.fields`. O `OneToOne` reverso é `None` quando não há statement → o serializer emite `null` (não quebra). **Bill escondido nunca expõe statement viva** (a statement foi soft-deletada junto — design §3.2; o nested usa o reverse accessor, que sob `objects` (SoftDeleteManager) some — travar por teste).

### `signals.py` — receivers das statements

Adicionar `WaterBillStatement` e `ElectricityBillStatement` à tupla `_FINANCE_MODELS` (`:34-49`). O loop `:59-69` já conecta `post_save`/`post_delete` → `invalidate_finance_caches()` (consistência do detalhe do bill — design §11). **Uma** linha de import + duas na tupla; **sem** novo receiver (DRY).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui = `freezegun` quando precisar fixar `today_sp()`/UNPAID/overdue. **NUNCA** mockar ORM, managers, `with_amounts`, `BillService`, `CondoMonthCloseService`, signals. Banco real (`--reuse-db`); `transaction.atomic()` ao asserir `IntegrityError`. Factories (`model-bakery`). `filterwarnings=error`: zero warnings. **Backup antes do migrate**: `python scripts/backup_db.py` (a migração cria 2 tabelas + RLS).

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_bill_statement_models.py`
```python
def test_water_statement_inherits_audit_and_softdelete_mixins(self) -> None:
    """WaterBillStatement tem created_at/updated_at não-nulos e is_deleted=False default; objects exclui soft-deletados, all_objects.with_deleted() inclui."""
def test_electricity_statement_inherits_audit_and_softdelete_mixins(self) -> None:
    """ElectricityBillStatement idem (mixins + managers duplos)."""
def test_water_statement_is_one_to_one_with_bill(self) -> None:
    """bill é OneToOne: criar 2 WaterBillStatement para o MESMO Bill → IntegrityError (dentro de transaction.atomic)."""
def test_electricity_statement_is_one_to_one_with_bill(self) -> None:
    """ElectricityBillStatement idem (OneToOne)."""
def test_bill_hard_delete_cascades_statement(self) -> None:
    """Hard-delete do Bill (bill.all_objects... .delete() hard / Bill._base_manager) → a statement some (CASCADE)."""
def test_bill_soft_delete_does_not_remove_statement(self) -> None:
    """bill.delete() (soft, via mixin) NÃO apaga a statement: a statement segue viva (gap §7.3 — o serviço é quem cascateia)."""
def test_reverse_accessor_water_statement(self) -> None:
    """bill.water_statement retorna a instância criada (related_name)."""
def test_reverse_accessor_electricity_statement(self) -> None:
    """bill.electricity_statement retorna a instância (related_name)."""
def test_supply_status_choices_default_active(self) -> None:
    """agua_status/esgoto_status default SupplyStatus.ACTIVE; aceitam CUT; valor fora das choices rejeitado no full_clean()."""
def test_nullable_reading_fields(self) -> None:
    """leitura_anterior/atual/dias e data_leitura (água) e energia_injetada_kwh (luz) aceitam None (sem solar/sem leitura)."""
def test_consumo_required(self) -> None:
    """consumo_m3 / consumo_kwh são obrigatórios (full_clean() sem o campo → ValidationError)."""
def test_str_pt(self) -> None:
    """__str__ de ambas as statements é PT e legível (smoke)."""
```

#### `tests/unit/test_finances/test_bill_statement_service.py`  (sob `@freeze_time` onde UNPAID/overdue importa)
```python
def test_create_with_lines_creates_water_statement(self) -> None:
    """billing_account WATER + statement={consumo_m3:158,...} → 1 Bill + linhas + 1 WaterBillStatement(bill=bill); with_amounts.amount_total = Σ linhas."""
def test_create_with_lines_creates_electricity_statement(self) -> None:
    """billing_account ELECTRICITY + statement consumo_kwh=1752 → cria ElectricityBillStatement 1:1."""
def test_create_with_lines_sets_line_installment(self) -> None:
    """linha com installment=<Installment> → BillLineItem.installment == aquele Installment (parcela embutida)."""
def test_create_with_lines_statement_none_creates_no_statement(self) -> None:
    """statement=None → Bill+linhas, nenhuma statement (água/luz opcional)."""
def test_create_with_lines_rejects_statement_for_generic_account(self) -> None:
    """account_type GENERIC (ou billing_account=None) + statement != None → ValidationError PT; nada criado (rollback)."""
def test_create_with_lines_atomic_rollback_on_bad_statement(self) -> None:
    """statement inválida (consumo ausente) → ValidationError; nenhum Bill/linha/statement persistido."""
def test_update_with_lines_replaces_lines_keeps_bill_pk(self) -> None:
    """bill UNPAID + mês aberto: update_with_lines com novas linhas → mesmo bill.pk; linhas antigas soft-deletadas; with_amounts.amount_total reflete só as novas."""
def test_update_with_lines_upserts_statement(self) -> None:
    """update_with_lines com statement nova → upsert (1 statement viva por bill); valores atualizados (consumo novo)."""
def test_update_with_lines_rejects_when_paid(self) -> None:
    """bill com Payment (BillPaymentService.pay) → update_with_lines levanta ValidationError PT; linhas/statement inalteradas."""
def test_update_with_lines_rejects_when_month_closed(self) -> None:
    """CondoMonthClose(status=closed) na competência → update_with_lines levanta ValidationError PT (assert_open)."""
def test_delete_cascades_statement_soft(self) -> None:
    """BillService.delete(bill): bill e statement soft-deletados (objects não acha; all_objects.with_deleted() acha ambos)."""
def test_serializer_nests_live_water_statement(self) -> None:
    """BillSerializer(bill).data['water_statement'] traz consumo_m3 etc.; electricity_statement = None."""
def test_serializer_hidden_bill_does_not_expose_statement(self) -> None:
    """após BillService.delete(bill), re-serializar via reverse accessor sob objects (SoftDeleteManager) → statement não aparece viva (§3.2)."""
```

#### `tests/integration/test_finances_bill_statement_api.py`  (View → Service → Model, sem mock de internals)
```python
def test_update_with_lines_replaces_unpaid_open(self) -> None:
    """POST /api/finances/bills/{id}/update_with_lines/ {line_items, statement} em bill UNPAID+OPEN → 200, payload re-anotado com statement nova e amount_total novo."""
def test_update_with_lines_rejects_paid_bill(self) -> None:
    """bill com pagamento → 400 PT ('desfaça o pagamento')."""
def test_update_with_lines_rejects_closed_month(self) -> None:
    """competência fechada → 400 PT ('reabra o mês')."""
def test_create_with_lines_persists_statement_and_installment(self) -> None:
    """POST /api/finances/bills/create_with_lines/ com statement + line_items[installment_id] → 201; GET do bill traz water_statement nested e a linha com installment vinculada."""
def test_get_bill_nests_statement(self) -> None:
    """GET /api/finances/bills/{id}/ → water_statement/electricity_statement aninhados (um preenchido, outro null)."""
def test_destroy_bill_cascades_statement(self) -> None:
    """DELETE /api/finances/bills/{id}/ → 204; bill e statement somem de objects (cascade soft-delete via BillService.delete)."""
def test_update_with_lines_requires_staff(self) -> None:
    """usuário autenticado não-staff → 403 (FinancialReadOnly write gate); não autenticado → 401."""
```

> Rodar (devem **falhar** — modelos/serviço/migração ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_statement_models.py \
>   tests/unit/test_finances/test_bill_statement_service.py \
>   tests/integration/test_finances_bill_statement_api.py -q
> ```

### 2. GREEN — implementar

1. `finances/models.py` — anexar `WaterBillStatement` + `ElectricityBillStatement` (§Modelos). Importar `SupplyStatus` (já no módulo, S56).
2. Migração + RLS:
   ```bash
   python scripts/backup_db.py                       # backup ANTES (regra database.md)
   python manage.py makemigrations finances
   # completar a migração recém-gerada com a RunSQL de RLS (ENABLE/DISABLE) das 2 tabelas novas:
   # finances_waterbillstatement, finances_electricitybillstatement — espelhar 0047 / finances 0003
   python manage.py migrate finances
   python manage.py makemigrations --check --dry-run # "No changes detected"
   ```
3. `tests/factories.py` — `make_water_statement(bill=None, consumo_m3=158, ...)`, `make_electricity_statement(bill=None, consumo_kwh=1752, ...)` (FK `bill` default = `make_bill`; `user` → `created_by`/`updated_by`).
4. `finances/services/bill_service.py` — TypedDicts novos; estender `create_with_lines` (statement + `installment`); `update_with_lines`; `delete`.
5. `finances/serializers.py` — 2 serializers + nesting no `BillSerializer`.
6. `finances/viewsets/crud_views.py` — estender `create_with_lines`; `update_with_lines`; `destroy`; `select_related`.
7. `finances/signals.py` — 2 entradas na tupla `_FINANCE_MODELS` + import.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_bill_statement_models.py tests/unit/test_finances/test_bill_statement_service.py tests/integration/test_finances_bill_statement_api.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- O parsing do `statement` cru → TypedDict é o **mesmo** em `create_with_lines` e `update_with_lines` (viewset): extrair um helper privado (`_parse_statement(data, account_type) -> StatementInput | None`) — fonte única (DRY), `try/except → 400 PT` num lugar só.
- A resolução "tipo da statement por `account_type`" vive **uma vez** no `BillService` (helper privado `_statement_model_for(account_type)`), consumida por create e update — sem repetir o `if WATER/ELECTRICITY`.
- Mensagens PT como constantes nomeadas (`_ERR_STATEMENT_TYPE`, `_ERR_BILL_PAID`, `_ERR_MONTH_CLOSED` — reusar a do `CondoMonthCloseService` se aplicável; **não** duplicar string).
- Confirmar que **nenhuma** statement tem campo de dinheiro e que `amount_*` continua só de `with_amounts` (annotation) — zero soma em Python.
- `_FINANCE_MODELS` continua a **única** lista de senders; signals não ganham receiver novo.

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` nos módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_bill_statement_models.py tests/unit/test_finances/test_bill_statement_service.py \
  tests/integration/test_finances_bill_statement_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances_bill_statement_api.py tests/factories.py
ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances_bill_statement_api.py tests/factories.py
mypy core/ finances/
pyright finances/ tests/unit/test_finances/ tests/integration/test_finances_bill_statement_api.py
```

Forward/backward da migração (design §13):
```bash
python manage.py migrate finances              # forward
python manage.py migrate finances <prev_head>  # backward (DISABLE_RLS roda; 2 tabelas dropadas)
python manage.py migrate finances              # re-forward (idempotente)
```

> **Regressão obrigatória** (não quebrar S37/S38): rodar os testes de `create_with_lines`/`BillSerializer`/signals existentes:
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_service.py tests/integration -k "bill" -q
> python -m pytest tests/unit -k "signal or invalidat" -q   # cache finance-*
> ```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). Statements importam `Bill`/`SupplyStatus`/mixins de `finances.models`/`core.models` — **nunca** views/serializers.
- **Lógica de negócio só em serviços** (`.claude/rules/architecture.md`): criação da statement, substituição de linhas, guards UNPAID/mês-fechado e cascade soft-delete vivem em `BillService`; o viewset só parseia (400 PT) e delega; o model só valida (`clean()`/`full_clean()`).
- **Statements = só leituras** (design §3.2): **zero** campo de dinheiro; todo R$ é `BillLineItem`; **não** adicionar property/annotation de valor às statements.
- **`amount_*` sempre via `with_amounts`** (annotation): o guard UNPAID lê `payment_status`/`amount_paid` da annotation; **proibido** somar `allocations`/linhas em Python.
- **Soft-delete cascade no serviço, não no model** (design §7.3): `BillService.delete` soft-deleta a statement antes do `bill.delete()`. **Não** sobrescrever `Bill.delete()` nem `SoftDeleteMixin`.
- **`update_with_lines` só em UNPAID + mês OPEN** (design §7.2): pago → 400 PT; fechado → 400 PT (`assert_open`). Preserva o mesmo `Bill` (pk/pagamentos).
- **Não tocar passado** (design §6): vincular `BillLineItem.installment` à parcela; **não** alterar `Installment.amount` nem bills/linhas de meses < N (re-baseline é S59/S64).
- **TZ SP única**: "hoje" só via `finances.services.timezone.today_sp()`. Proibido `timezone.now().date()` no serviço.
- **RLS na mesma migração** (`.claude/rules/database.md` + design §13): `finances_waterbillstatement` + `finances_electricitybillstatement`; `RunSQL` com `reverse_sql`. **Backup antes do migrate**; testar forward **e** backward.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código. Tipos completos (mypy strict + pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from django.contrib.auth.models import User`, etc.). **Sem re-exports / barrels / shims** — cada módulo exporta só o que define; imports diretos da fonte.
- **Sem parser/`pdfplumber`/`parse_invoice`/`IptuAlertService`/`Notification` choices/`send_finance_alerts`/frontend/seed** (S59–S64). **Sem** alterar `Bill`/`BillLineItem`/`BillingAccount`/`Payment`/`Installment`.
- Mensagens ao usuário em **Português**; logs/identificadores/enum values/atributos em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/models.py` define `WaterBillStatement` e `ElectricityBillStatement` (`(AuditMixin, SoftDeleteMixin)` + managers duplos), `OneToOneField(Bill, CASCADE, related_name="water_statement"/"electricity_statement")`, campos de leitura conforme §3.2/§3.3, `agua_status`/`esgoto_status` = `SupplyStatus` (default ACTIVE), **zero** campo de dinheiro; `Bill`/`BillLineItem`/`BillingAccount` **intactos**.
- [ ] Migração do `finances` gerada (head atual), inclui `RunSQL` de RLS (ENABLE/DISABLE) das **2 tabelas novas**; `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] `BillService.create_with_lines(draft, lines, statement=None, user=None)` cria a statement 1:1 atômico (tipo por `account_type`; `GENERIC`/sem conta + statement → `ValidationError` PT), seta `BillLineItem.installment` por linha; rollback total em falha; caller atual `(draft, lines, user=...)` continua válido.
- [ ] `BillService.update_with_lines(bill, lines, statement=None, user=None)` substitui as linhas (soft-delete das antigas + novas) + upsert da statement **no mesmo `Bill`**, **só** se UNPAID (`payment_status == "open"`) e mês OPEN (`assert_open`); pago/fechado → `ValidationError` PT.
- [ ] `BillService.delete(bill, user=None)` soft-deleta a statement viva e depois o bill (cascade soft-delete, gap §7.3); `destroy` do `BillViewSet` delega a ele.
- [ ] `WaterBillStatementSerializer`/`ElectricityBillStatementSerializer` (read-only) aninhados no `BillSerializer` (`Meta.fields`); bill sem statement → `null`; bill soft-deletado → statement não aparece viva via reverse accessor (SoftDeleteManager).
- [ ] `@action(detail=True) bills/update_with_lines` (200 substitui; 400 pago; 400 fechado) + `create_with_lines` estendida (statement + `installment_id`); `select_related` ganha as 2 statements; gate de escrita `is_staff` (403/401).
- [ ] `finances/signals.py`: `WaterBillStatement`/`ElectricityBillStatement` na tupla `_FINANCE_MODELS` (post_save/post_delete → `invalidate_finance_caches()`); sem receiver novo (DRY).
- [ ] Factories `make_water_statement`/`make_electricity_statement` em `tests/factories.py`.
- [ ] Testes cobrem o Apêndice B (Fase 3): create_with_lines grava statement + `line.installment`; update_with_lines substitui só em UNPAID+OPEN e rejeita pago/fechado; soft-delete do bill esconde a statement; bill escondido não expõe statement viva; OneToOne/CASCADE/mixins/choices/null.
- [ ] `python -m pytest tests/unit/test_finances/test_bill_statement_* tests/integration/test_finances_bill_statement_api.py` passa 100%, **coverage `finances` ≥90%** nos módulos tocados; regressão S37/S38 (`test_bill_service.py`, integration `-k bill`, signals) verde.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum parser/`pdfplumber`/`parse_invoice`/`IptuAlertService`/`Notification` choices/`send_finance_alerts`/frontend/seed criado; `Bill`/`BillLineItem`/`BillingAccount`/`Payment`/`Installment` intactos.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_bill_statement_models.py tests/unit/test_finances/test_bill_statement_service.py \
     tests/integration/test_finances_bill_statement_api.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_bill_service.py tests/integration -k "bill" -q   # regressão S37/S38
   python -m pytest tests/unit -k "signal or invalidat" -q                                          # regressão cache finance-*
   ruff check finances/ tests/unit/test_finances/ tests/integration/test_finances_bill_statement_api.py tests/factories.py
   ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_finances_bill_statement_api.py tests/factories.py
   mypy core/ finances/
   pyright finances/ tests/unit/test_finances/ tests/integration/test_finances_bill_statement_api.py
   python manage.py makemigrations --check --dry-run
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`):
   - Linha da Sessão 58 (status **concluída**) na tabela da feature Contas de utilidade (parser + IPTU).
   - **Arquivos Criados**: `finances/migrations/000X_water_electricity_statement.py`, `tests/unit/test_finances/{test_bill_statement_models,test_bill_statement_service}.py`, `tests/integration/test_finances_bill_statement_api.py`.
   - **Arquivos Modificados**: `finances/models.py` (2 statements), `finances/services/bill_service.py` (`create_with_lines` estendido + `update_with_lines` + `delete`), `finances/serializers.py` (2 serializers + nesting), `finances/viewsets/crud_views.py` (`update_with_lines` + `destroy` + `select_related`), `finances/signals.py` (2 senders), `tests/factories.py` (2 factories).
   - **Nota**: "Fase 3 — statements 1:1 só leituras (`WaterBillStatement`/`ElectricityBillStatement`, soft-delete, OneToOne CASCADE, RLS na mesma migração); `create_with_lines` grava statement + `BillLineItem.installment`; `update_with_lines` substitui linhas + upsert statement no mesmo Bill só em UNPAID+OPEN; `BillService.delete` cascateia soft-delete da statement; nested read-only no `BillSerializer`; signals `finance-*`. **Parser = S59; endpoint parse_invoice = S60; IPTU alert = S61; frontend = S62/S63; seed = S64.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (na branch da feature — ex.: `feat/condo-utility-bills`):
   ```
   feat(finances): complete session 58 — bill statements (water/electricity) + create/update_with_lines + cascade soft-delete + nested serializer

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **59 — Parser de fatura (DMAE água + CEEE luz)** (`finances/services/invoice_parsing/{base,dmae,ceee,registry}.py`, `pdfplumber`) — produz a `ParsedInvoice` (`statement` + `line_items`) que a S60 envia ao modal e a S58 persiste via `create_with_lines`/`update_with_lines`.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.models`** (Fase 3): `WaterBillStatement` (`bill` OneToOne CASCADE → `related_name="water_statement"`; `consumo_m3`, `leitura_anterior/atual/dias`, `data_leitura`, `agua_status`/`esgoto_status` ∈ `SupplyStatus`) e `ElectricityBillStatement` (`related_name="electricity_statement"`; `consumo_kwh`, `energia_injetada_kwh`, `leitura_anterior/atual/dias`, `classe`, `bandeira`). **Só leituras — dinheiro é `BillLineItem`.** `(AuditMixin, SoftDeleteMixin)`.
- **`BillService.create_with_lines(draft, lines, statement=None, user=None) -> Bill`** — `lines: list[BillLineInput]` com `installment: NotRequired[Installment | None]`; `statement: WaterStatementInput | ElectricityStatementInput | None` (tipo por `draft.billing_account.account_type`). **S60** (`parse_invoice` → modal) e a UI da S62/S63 montam o payload `{bill, line_items[..., installment_id], statement}`.
- **`BillService.update_with_lines(bill, lines, statement=None, user=None) -> Bill`** — substitui linhas + upsert statement no MESMO bill, só UNPAID+OPEN. **S63** (`useUpdateBillWithLines`) chama `POST /api/finances/bills/{id}/update_with_lines/`. Caminho de correção/re-upload (design §5.5).
- **`BillService.delete(bill, user=None)`** — cascade soft-delete da statement; `destroy` do `BillViewSet` delega. **`BillSerializer`** ganha `water_statement`/`electricity_statement` (read-only, nullable). **S63** `bill.schema.ts` aninha esses dois campos (nullable) → prefill do modal no edit round-trip sem query-key novo (design §7/§11).
- **Endpoints**: `POST /api/finances/bills/create_with_lines/` (estendido) e `POST /api/finances/bills/{id}/update_with_lines/` (novo) — `is_staff` (write gate `FinancialReadOnly`). **S60** adiciona `bills/parse_invoice` (draft em memória, não persiste) que **alimenta** estes.
- **Signals**: `WaterBillStatement`/`ElectricityBillStatement` invalidam `finance-*` (`invalidate_finance_caches`, S37). **S61/S63** confiam nessa invalidação para o detalhe do bill.
