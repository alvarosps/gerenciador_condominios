# Sessão 36 — Backend modelos: `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation` + migração + annotations

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → **36** → 37 → 38 → 39 → 40 → 41 → … → 50 (Fase 2 começa aqui)
> Esta sessão cria o **núcleo de contas a pagar** do app `finances`: os modelos `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`, a **migração inicial do `finances`** (depende da migração do `core` que cria `Condominium`, da Sessão 34) e o **manager/queryset com `.with_amounts()`** que materializa `amount_total/amount_paid/amount_remaining/payment_status/is_overdue` como **annotations ORM (Sum-subquery)** — NÃO como properties Python. **Sem serviços (S37), sem serializers/viewsets (S38), sem frontend.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.1, §4.2, §4.4, §4.8, §5 inteira — especialmente §5.2 bloco "Pagável" e "Pagamentos", §13 migrações, §18 edge-cases)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| `SoftDeleteManager` (manager duplo) | `core/models.py:41-58` (`get_queryset` filtra `is_deleted=False`; `with_deleted`/`deleted_only`) | **Reusar** este manager do `core` (import direto), NÃO recriar. É a base do `objects` de todos os modelos com SoftDelete |
| `AuditMixin` | `core/models.py:61-108` | Mixin abstrato `created_at/updated_at/created_by/updated_by` — herdado por TODOS os modelos desta sessão |
| `SoftDeleteMixin` | `core/models.py:111-170+` (`delete()` com `hard_delete`/`deleted_by` em :149-170) | Soft delete (`is_deleted`, `deleted_at`, `restore()`). Herdado por todos EXCETO `BillSkip` |
| **Model com FKs nulláveis + `CheckConstraint(>=0)` + `is_offset` + `end_date`** | `core/models.py:1032-1136` (`Expense`: FKs `SET_NULL` em :1037-1048; managers duplos `all_objects`/`objects` em :1074-1075; `CheckConstraint(total_amount__gte=0)` em :1098-1106; `is_offset` em :1066-1069; `end_date` em :1061-1065; `clean()` PT em :1111-1114; cascade soft-delete em :1116-1136) | **Exemplar canônico** para `Bill`/`BillLineItem`. Copiar a forma de managers, constraints, `clean()` PT, cascade no `delete()` |
| Model filho `CASCADE` | `core/models.py:1150-1161` (`ExpenseInstallment`: `expense` FK `CASCADE` em :1151; managers duplos em :1160-1161) | Forma de `BillLineItem`/`PaymentAllocation` (filhos `CASCADE`) |
| **Partial unique `condition=Q(is_deleted=False)` + `CheckConstraint(>0/>=0)`** | `core/models.py:1253-1265` (`RentPayment.Meta`: `UniqueConstraint(condition=Q(is_deleted=False), name=…)` em :1256-1260; `CheckConstraint(amount_paid__gt=0)` em :1261-1264; indexes em :1266-1269) | **Exemplar canônico** das unique parciais idempotentes do `Bill` e das check constraints. Note: soft-delete libera o slot |
| Migração com RLS (`RunSQL`/`reverse_sql`) | `core/migrations/0047_enable_row_level_security.py:1-135` (`ENABLE_RLS`/`DISABLE_RLS` em :16-124; `dependencies` em :128-130; `RunSQL(sql=…, reverse_sql=…)` em :132-134) | **Obrigatório** (`.claude/rules/database.md`): toda tabela nova habilita RLS na **mesma migração**. Espelhar este padrão para as 7 tabelas novas do `finances` |
| `AppConfig.ready()` importando signals | `core/apps.py` (`CoreConfig.ready()` → `importlib.import_module(".signals", package="core")`) | A Sessão 34 cria `FinancesConfig.ready()` análogo; esta sessão **não** mexe em signals (S37+) |
| Factories `make_<model>()` (estilo `**kwargs`/`defaults`/`baker.make`) | `tests/factories.py:1-54` (imports + `make_building` :34-40 + `make_apartment` :43-54) | **Espelhar** o estilo: função módulo-nível, `defaults` dict, `user` opcional para `created_by`/`updated_by`, `baker.make("finances.<Model>", **defaults)` |
| Factories financeiras existentes | `tests/factories.py:98-251` (`make_expense` :98, `make_rent_payment` :190, `make_employee_payment` :205) | Padrão de factory para modelos financeiros com `Decimal` defaults |

### O que a Sessão 34 já entregou (PRÉ-REQUISITO — NÃO recriar nesta sessão)

A Sessão 34 (infra) criou e DEVE existir antes de começar — **verificar no SESSION_STATE.md** que a S34 está concluída:

- App `finances/` em `INSTALLED_APPS`, `finances/apps.py` com `FinancesConfig.ready()`, `finances/__init__.py`.
- **`Condominium`** model em `core` (`name`, `notes`) + **registro padrão** via data-migration + **`Building.condominium`** FK (faseada). A migração do core que cria `Condominium` é a **dependência explícita** da migração inicial do `finances` desta sessão.
- **Helper TZ único** `America/Sao_Paulo` (settings é `UTC` — `core/models.py:185` `TIME_ZONE = "UTC"`). Localização exata definida pela S34 (ex.: `finances/services/time.py` ou `finances/time_utils.py`). **Esta sessão NÃO o usa diretamente** (modelos não calculam "hoje"; `is_overdue` recebe a data como parâmetro — ver Especificação), mas o cita para o `make_condominium()`/escopo.
- **Factories base**: `make_condominium()` e `make_building(condominium=...)` (default para o condomínio-padrão). Esta sessão **adiciona** `make_finance_category`, `make_billing_account`, `make_bill`, `make_bill_line_item`, `make_bill_skip`, `make_payment`, `make_payment_allocation`.
- **Gate ampliado**: `finances` já em `--cov`/`[tool.coverage.run] source` (`pyproject.toml:374-375`), `mypy core/` → `mypy core/ finances/`, `pyrightconfig.json include` (`pyrightconfig.json:5-10`). Se a S34 não ampliou algum desses, é **bug da S34** — reportar, não corrigir aqui.

> **Se a S34 não estiver concluída, PARE.** Esta sessão depende dela (DEPENDENCY ORDER 34→35→36). Não criar `Condominium`/app/infra aqui.

---

## Escopo

### Arquivos a criar
- `finances/models.py` — os 7 modelos desta sessão + o `BillQuerySet`/`BillManager` com `.with_amounts()`. (A S34 pode ter criado o arquivo vazio/com imports; esta sessão preenche o núcleo de contas. Se a S34 já colocou outros modelos, **anexar** sem duplicar imports.)
- `finances/migrations/000X_bills_core.py` — gerada por `makemigrations finances`. Inclui os `CreateModel` dos 7 modelos **e** a `RunSQL` de RLS (`ENABLE`/`DISABLE`) para as 7 tabelas novas (ver §RLS). **Não** editar a numeração à mão — `makemigrations` resolve a partir do head do `finances` deixado pela S34.
- `tests/unit/test_finances/test_bill_models.py` — testes de modelo (constraints, `clean()` PT, soft-delete, partial-unique, `is_offset`).
- `tests/unit/test_finances/test_bill_annotations.py` — testes das annotations (`.with_amounts()`: `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue`).
- `tests/unit/test_finances/__init__.py` — se ainda não existir.

### Arquivos a modificar
- `tests/factories.py` — adicionar `make_finance_category`, `make_billing_account`, `make_bill`, `make_bill_line_item`, `make_bill_skip`, `make_payment`, `make_payment_allocation` (estilo `tests/factories.py:34-54`). Imports e factories existentes **intactos**.

### NÃO fazer (pertence a outras sessões)
- **Nenhum serviço** (`BillGenerationService`, `BillService.create_with_lines`, `BillPaymentService`, `CondoCalendarService`) — é a **Sessão 37**. O `pay()`/geração não existem aqui; os testes desta sessão criam `Payment`/`PaymentAllocation`/`Bill` **diretamente via factory/ORM**.
- **Nenhum serializer, viewset, URL ou ação de API** (`bills/`, `bills/{id}/pay`, `payments/`, etc.) — é a **Sessão 38**.
- **Nenhum frontend** (hooks/pages/schemas) — fases posteriores.
- **Nenhum signal/cache** (`finances/signals.py`, receivers cross-app, bloco de prefixos `finance-*`) — wiring é da S34 (estrutura) e a invalidação real entra com os serviços/viewsets (S37/S38 + §11). **Não** adicionar receivers nesta sessão.
- **Modelos de fases seguintes**: `Installment`/`InstallmentPlan`/`Employee` (Fase 3, S41/S44), `IncomeEntry`/`Reserve`/`ReserveMovement`/`CondoMonthClose` (Fase 4). **Decisão pinada abaixo (Bill source FKs).**
- **Não** alterar `core/models.py`, `core/signals.py`, `condominios_manager/settings.py` (a infra foi da S34).
- **Não** popular dados/categorias (design §13 — sem seed; o admin cria tudo).

---

## Especificação

> Convenções (design §5): `(AuditMixin, SoftDeleteMixin, models.Model)` + managers duplos (`all_objects = models.Manager()`, `objects = SoftDeleteManager()` do `core`), `DecimalField(max_digits=12, decimal_places=2)`, partial unique `condition=Q(is_deleted=False)`, `CheckConstraint amount >= 0` em toda linha de valor, `clean()` em PT, `on_delete` `PROTECT` em FKs de referência / `CASCADE` em filhos / `SET_NULL` onde indicado. Mensagens ao usuário em **PT**, logs/identificadores em **EN**. **`condominium` FK em todo modelo de topo** (escopo multi-condomínio futuro — design §6).

### Decisão pinada — FKs de fonte do `Bill` (documentar no docstring do model)

O design (§5.2) lista `Bill` com fontes nulláveis `billing_account`/`installment`/`employee`. **Nesta sessão cria-se APENAS `Bill.billing_account`** (FK para o `BillingAccount` desta sessão). As FKs `installment` e `employee` **NÃO** são criadas agora porque os modelos `Installment`/`Employee` só existem nas Fases 3/4 (S41/S44) — criar FKs para modelos inexistentes violaria a direção de dependência e exigiria stubs. **`Bill.installment` é adicionado na S41 e `Bill.employee` na S41, via migração de `add_field`** (a unique parcial `(installment)` e `(employee, competence_month)` também entram lá). Esta sessão entrega a unique parcial **`(billing_account, competence_month)`** (geração idempotente de recorrentes — Fase 2). O `behavior` enum já inclui `INSTALLMENT` (o valor existe; a FK chega na S41). Documentar isto explicitamente no docstring de `Bill` para a S41/S44 não recriarem o campo.

### `BillBehavior` (enum em `Bill`)

`models.TextChoices` com `ONE_TIME`, `RECURRING`, `INSTALLMENT` (design §3.3). `Bill.behavior` armazenado. **Não** confundir com `lifecycle_state`.

### `lifecycle_state` (armazenado, NÃO derivado)

`models.TextChoices` `{active, suspended, deferred, canceled}` em `Bill` (default `active`). É **armazenado** (design §4.4/§5.2) — o `is_overdue` exclui `≠ active`; suspended/deferred/canceled saem das somas de competência. `BillingAccount.lifecycle_state` usa `{active, suspended, deferred, ended}` (note o `ended` em vez de `canceled` — design §5.2). Definir **duas** enums distintas (não reusar uma para a outra — semântica diferente).

### Modelos (assinaturas de campo conforme design §5.2)

```python
# finances/models.py — imports diretos da fonte (sem TYPE_CHECKING, sem __future__)
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, F, Value, Case, When, DecimalField, BooleanField, QuerySet
from django.db.models.functions import Coalesce
from core.models import AuditMixin, SoftDeleteMixin, SoftDeleteManager, Building, Condominium


class BillBehavior(models.TextChoices):
    ONE_TIME = "one_time", "Avulsa"
    RECURRING = "recurring", "Recorrente"
    INSTALLMENT = "installment", "Parcelada"


class BillLifecycleState(models.TextChoices):
    ACTIVE = "active", "Ativa"
    SUSPENDED = "suspended", "Suspensa"
    DEFERRED = "deferred", "Adiada"
    CANCELED = "canceled", "Cancelada"


class BillingAccountState(models.TextChoices):
    ACTIVE = "active", "Ativa"
    SUSPENDED = "suspended", "Suspensa"
    DEFERRED = "deferred", "Adiada"
    ENDED = "ended", "Encerrada"


class Category(AuditMixin, SoftDeleteMixin, models.Model):
    """Árvore de classificação (self-FK). condominium-scoped. Sem treebeard (YAGNI)."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="categories")
    name = models.CharField(max_length=120)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    color = models.CharField(max_length=20, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # Meta: unique parcial (condominium, parent, name) condition=Q(is_deleted=False); ordering por sort_order/name


class BillingAccount(AuditMixin, SoftDeleteMixin, models.Model):
    """Template recorrente (água/luz/IPTU/internet). Gera Bill real quando a fatura é lançada (S37)."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="billing_accounts")
    building = models.ForeignKey(Building, null=True, blank=True, on_delete=models.PROTECT, related_name="billing_accounts")  # null = nível-condomínio
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="billing_accounts")
    name = models.CharField(max_length=200)
    external_identifier = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    default_due_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))  # projeção/seed
    lifecycle_state = models.CharField(max_length=20, choices=BillingAccountState.choices, default=BillingAccountState.ACTIVE)
    tracking_start_month = models.DateField(null=True, blank=True)  # seed; 1º dia do mês
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # CheckConstraint expected_amount >= 0; clean() normaliza tracking_start_month para dia 1


class Bill(AuditMixin, SoftDeleteMixin, models.Model):
    """Conta a pagar (real). amount_* via annotation .with_amounts() — NUNCA property Python."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="bills")
    building = models.ForeignKey(Building, null=True, blank=True, on_delete=models.PROTECT, related_name="bills")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="bills")
    competence_month = models.DateField()  # 1º dia
    due_date = models.DateField()
    issue_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=500)
    external_identifier = models.CharField(max_length=100, blank=True)
    behavior = models.CharField(max_length=20, choices=BillBehavior.choices)
    billing_account = models.ForeignKey(BillingAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="bills")
    # NOTA: installment FK = S41; employee FK = S41 (modelos não existem ainda — ver "Decisão pinada")
    lifecycle_state = models.CharField(max_length=20, choices=BillLifecycleState.choices, default=BillLifecycleState.ACTIVE)
    attachment = models.FileField(null=True, blank=True, upload_to="finances/bills/")  # confirmar storage com infra S34; se não houver, usar CharField(path) — DECIDIR e documentar
    notes = models.TextField(blank=True)
    all_objects = models.Manager()
    objects = BillManager()  # ver abaixo; expõe with_amounts() E o filtro soft-delete
    # Meta: unique parcial (billing_account, competence_month) condition=Q(is_deleted=False, billing_account__isnull=False)
    #       clean() normaliza competence_month para dia 1


class BillLineItem(AuditMixin, SoftDeleteMixin, models.Model):
    """Linha de uma conta. is_offset: armazenado POSITIVO, subtraído (design §4.1)."""
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="line_items")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="line_items")
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # >= 0 (CheckConstraint); fonte de verdade do histórico/caixa
    is_offset = models.BooleanField(default=False)
    # NOTA: installment FK (parcela embutida) = S41. clean(): amount >= 0 PT.


class Payment(AuditMixin, SoftDeleteMixin, models.Model):
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    method = models.CharField(max_length=50, blank=True)
    funded_from = models.CharField(max_length=10, choices=FundedFrom.choices, default=FundedFrom.CAIXA)  # {caixa, reserve}
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)


class PaymentAllocation(AuditMixin, SoftDeleteMixin, models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0


class BillSkip(AuditMixin, models.Model):
    """SEM SoftDelete (design §5.2): hard delete des-pula. Pula geração de um mês."""
    billing_account = models.ForeignKey(BillingAccount, on_delete=models.CASCADE, related_name="skips")
    reference_month = models.DateField()  # 1º dia
    objects = models.Manager()  # SEM SoftDeleteManager
    # Meta: unique (billing_account, reference_month) — SEM condition (não há is_deleted)
```

> `FundedFrom` (TextChoices `{caixa, reserve}`) e `MinValueValidator`/`MaxValueValidator` importados de `django.core.validators`. Confirmar com a infra da S34 se o **storage de `attachment`** já está configurado; se não, usar `models.CharField(max_length=500, blank=True)` para o caminho e documentar a decisão (KISS — não introduzir storage novo nesta sessão sem necessidade).

### `BillManager` / `BillQuerySet` com `.with_amounts()` (design §4.4 — CRÍTICO)

`amount_total/amount_paid/amount_remaining/payment_status/is_overdue` são **annotations (Sum-subquery), NÃO properties Python** (evita N+1 e filtro em Python). Definir um `BillQuerySet(models.QuerySet)` com `.with_amounts(today: date)` e um `BillManager(SoftDeleteManager)` que retorna esse queryset (preservando o filtro `is_deleted=False` do `SoftDeleteManager`).

```python
class BillQuerySet(models.QuerySet["Bill"]):
    def with_amounts(self, today: date) -> "BillQuerySet":
        """Anota amount_total/amount_paid/amount_remaining/payment_status/is_overdue.

        - amount_total = Σ(line_items NÃO offset, ativos) − Σ(line_items offset, ativos)
            via Subquery/aggregate por bill, Coalesce(..., Decimal('0')). is_offset POSITIVO,
            SUBTRAÍDO (design §4.1). EXCLUIR line_items soft-deleted da soma.
        - amount_paid = Σ(PaymentAllocation.amount, ativos) deste bill. Coalesce 0.
            EXCLUIR allocations soft-deleted; deriva SÓ de PaymentAllocation (nunca de ReserveMovement).
        - amount_remaining = amount_total − amount_paid (pode ser 0; nunca negativo na prática — guard no serviço S37, não no model).
        - payment_status = CASE: amount_paid <= 0 → 'open'; amount_paid >= amount_total → 'paid'; else → 'partial'.
        - is_overdue = (due_date < today) AND (amount_remaining > 0) AND (lifecycle_state = 'active').
            'today' é PARÂMETRO (a TZ SP é resolvida no serviço/view que chama — design §4: model não chama timezone.now()).
        Usar OuterRef/Subquery (ou .annotate(Sum(...)) com filter=) — escolher a forma SEM duplicar joins que inflem a soma.
        Quantização (ROUND_HALF_UP) NÃO acontece aqui — é na fronteira de saída/serviço (design §4). O annotation soma cru.
        """

class BillManager(SoftDeleteManager):
    def get_queryset(self) -> BillQuerySet:
        return BillQuerySet(self.model, using=self._db).filter(is_deleted=False)
    def with_amounts(self, today: date) -> BillQuerySet:
        return self.get_queryset().with_amounts(today)
```

**Pontos de atenção (testar):** somar `line_items` e `allocations` na **mesma** query com dois `Sum` faz **produto cartesiano** (cada allocation multiplica cada line item) → totais inflados. Usar `Subquery`/`OuterRef` por figura **ou** `Sum(..., filter=...)` com `distinct` cuidadoso — a forma escolhida DEVE passar o teste "bill com N linhas e M allocations não infla". `amount_remaining` e `payment_status` derivam dos dois `Sum` já anotados (usar `F(...)`/`Case/When`).

### RLS na mesma migração (design §13 + `.claude/rules/database.md`)

A migração inicial do `finances` desta sessão DEVE incluir uma `migrations.RunSQL(sql=ENABLE_RLS, reverse_sql=DISABLE_RLS)` habilitando RLS nas 7 tabelas novas — espelhando `core/migrations/0047_enable_row_level_security.py:16-134`. Tabelas (nomes Django default `finances_<model>`): `finances_category`, `finances_billingaccount`, `finances_bill`, `finances_billlineitem`, `finances_billskip`, `finances_payment`, `finances_paymentallocation`. `ENABLE ROW LEVEL SECURITY` é idempotente (no-op se já habilitada). **`dependencies`** da migração: a migração do `finances` deixada pela S34 (head) **e** explicitamente a migração do `core` que cria `Condominium` (design §13 — dependência cross-app explícita).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. Aqui = **nada** a mockar além de `freezegun` (não há tempo a congelar nos modelos; `is_overdue` recebe `today` como parâmetro — passar `date(...)` explícito, sem `freeze_time` salvo se conveniente). **NUNCA** mockar ORM, managers, `SoftDeleteManager`, ou o `BillQuerySet`. Banco real via `--reuse-db`. Dados via factories (`model-bakery`). Backend antes do migrate: **backup** (`python scripts/backup_db.py`) conforme `.claude/rules/database.md` (a migração cria tabelas novas + RLS; criar é menos arriscado que dropar, mas a regra de backup-antes-de-migrate é primária).

### 1. RED — escrever os testes primeiro

Criar `tests/unit/test_finances/test_bill_models.py` e `tests/unit/test_finances/test_bill_annotations.py`. Usar `@pytest.mark.django_db`, factories de `tests/factories.py` (incluindo as novas) e `transaction.atomic()` ao asserir `IntegrityError`. Cobrir, no mínimo:

**Estrutura / herança / managers (`test_bill_models.py`)**
- [ ] cada modelo (Category, BillingAccount, Bill, BillLineItem, Payment, PaymentAllocation) herda `AuditMixin` (`created_at`/`updated_at` não-nulos) **e** `SoftDeleteMixin` (`is_deleted=False` default); `BillSkip` tem `AuditMixin` mas **NÃO** `is_deleted` (sem `SoftDeleteMixin`).
- [ ] `Model.objects` exclui soft-deleted; `Model.all_objects.with_deleted()` inclui (Bill, BillLineItem, Payment, PaymentAllocation, Category, BillingAccount).
- [ ] `BillSkip.objects` é o manager simples (sem `with_deleted`) — `BillSkip` não tem soft-delete.
- [ ] `condominium` FK presente nos modelos de topo (Category, BillingAccount, Bill, Payment); escopo correto.

**Constraints / `clean()` PT (`test_bill_models.py`)**
- [ ] `BillLineItem.amount` negativo → `IntegrityError` (CheckConstraint `amount >= 0`); `amount = 0` permitido (linha zerada legítima — espelha `Expense` :1098-1106).
- [ ] `Payment.amount <= 0` → rejeitado (`clean()` PT **e**/ou CheckConstraint `> 0`); `PaymentAllocation.amount <= 0` rejeitado.
- [ ] `BillingAccount.expected_amount` negativo rejeitado.
- [ ] **partial unique idempotente**: dois `Bill` ativos com mesmo `(billing_account, competence_month)` → `IntegrityError`; após soft-delete do primeiro, criar o segundo **funciona** (slot liberado — espelha `RentPayment` :1256-1260). `billing_account=null` (avulsa) **não** colide (condição `billing_account__isnull=False`).
- [ ] `Category` unique parcial `(condominium, parent, name)`: duplicata ativa → `IntegrityError`; soft-delete libera; mesma `name` sob `parent` diferente OK.
- [ ] `BillSkip` unique `(billing_account, reference_month)`: duplicata → `IntegrityError`; **hard delete** des-pula (cria de novo OK — sem soft-delete).
- [ ] `competence_month`/`reference_month`/`tracking_start_month` normalizados para dia 1 no `clean()`.
- [ ] `__str__` em PT/EN coerente para cada modelo (smoke).

**`is_offset` — sinal positivo + subtraído (`test_bill_annotations.py`, design §4.1 + §18 "is_offset mantém amount_total>=0")**
- [ ] linha `is_offset=True` armazenada **positiva**; `amount_total = Σ não-offset − Σ offset`. Ex.: linhas `[600 (não-offset), 400 (não-offset), 100 (offset)] → amount_total = 1000 − 100 = 900`.
- [ ] cenário onde offset ≥ não-offset → `amount_total >= 0` mantido (ex.: `[100 não-offset, 100 offset] → 0`; nunca negativo).

**`.with_amounts(today)` annotations (`test_bill_annotations.py`, design §4.4 + §18)**
- [ ] `amount_total` correto com mix de offset/não-offset (caso acima).
- [ ] **anti-cartesiano**: bill com **N line items** (ex. 3) **e** **M allocations** (ex. 2) → `amount_total` e `amount_paid` corretos (não inflados pelo join). Asserir os dois valores exatos.
- [ ] `amount_paid` = Σ `PaymentAllocation` ativos; **soft-deleted allocation excluída** da soma; allocation de **Payment soft-deletado** não conta (se o serviço/teste soft-deletar o Payment — testar via `PaymentAllocation` soft-delete direto, já que o cascade de Payment é da S37).
- [ ] `amount_paid` deriva **só** de `PaymentAllocation` (sem `ReserveMovement` — que nem existe nesta fase; documentar que o annotation jamais o referencia).
- [ ] `amount_remaining = amount_total − amount_paid` (parcial: total 900, pago 300 → 600; total = pago → 0).
- [ ] `payment_status`: sem allocation → `open`; allocation parcial → `partial`; allocation ≥ total → `paid`.
- [ ] **`is_overdue` (design §4.4 + §18)**: `due_date < today` **E** `amount_remaining > 0` **E** `lifecycle_state='active'` → `True`. Casos negativos: pago integral (remaining 0) → `False`; `due_date >= today` → `False`; `lifecycle_state ∈ {suspended, deferred, canceled}` → `False` mesmo vencido e não pago (IPTU adiado/suspenso **não** é atrasado).
- [ ] **soft-deleted Bill excluído** do queryset `.with_amounts()` (manager filtra `is_deleted=False`).
- [ ] **estrutural §18**: bill **sem** line items → `amount_total = 0`, `amount_remaining = 0`, `payment_status = paid` ou `open` (DECIDIR a convenção e travar por teste — recomendo `open` quando total 0 e pago 0; documentar); bill sem allocations → `amount_paid = 0`, `open`.

> Rodar (devem **falhar** — modelos/manager/migração ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_models.py tests/unit/test_finances/test_bill_annotations.py -q
> ```

### 2. GREEN — implementar modelos + manager + migração

Criar `finances/models.py` com os 7 modelos, as 3 enums, `FundedFrom`, `BillQuerySet`/`BillManager`. Importar mixins/manager do `core` (`core/models.py:41,61,111`) — **import direto, sem re-export**. Adicionar as factories em `tests/factories.py`. Gerar e aplicar a migração:

```bash
python scripts/backup_db.py                       # backup ANTES (regra database.md)
python manage.py makemigrations finances
# editar a migração SÓ para anexar a RunSQL de RLS (ENABLE/DISABLE) das 7 tabelas — ver §RLS
python manage.py migrate finances
python manage.py makemigrations --check --dry-run # deve dizer "No changes detected"
```

> **Nota sobre editar a migração**: o hook bloqueia edição de migrations **existentes**; a recém-gerada ainda não foi commitada — anexar a `RunSQL` de RLS na operação é parte da criação (mesmo padrão de `0047`). Se o hook reclamar, gerar a migração de RLS como **operação adicional na mesma migração** via `makemigrations --empty` seria fragmentar — preferir a migração única gerada e completada antes do primeiro commit.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_bill_models.py tests/unit/test_finances/test_bill_annotations.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)

- Extrair as expressões de Subquery do `with_amounts` em helpers privados nomeados (ex.: `_total_subquery()`, `_paid_subquery()`) se ficarem longas — funções pequenas, intenção clara (design-principles).
- Garantir que `amount_total`/`amount_paid` usam a **mesma** convenção de `Coalesce(..., Value(Decimal("0")), output_field=DecimalField(max_digits=12, decimal_places=2))` (DRY; sem off-by-cent — §18 quantização).
- Confirmar que **nenhuma** property Python (`@property amount_*`) existe no `Bill` (design §4.4 proíbe) — só annotations.

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem problemas pré-existentes de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_bill_models.py tests/unit/test_finances/test_bill_annotations.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/models.py tests/unit/test_finances/ tests/factories.py
ruff format --check finances/models.py tests/unit/test_finances/ tests/factories.py
mypy core/ finances/
pyright finances/models.py
```

Forward/backward da migração (design §13):
```bash
python manage.py migrate finances        # forward
python manage.py migrate finances zero   # backward (DISABLE_RLS roda; tabelas dropadas)
python manage.py migrate finances        # re-forward (idempotente)
```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). `finances/models.py` importa de `core.models` (mixins/manager/Building/Condominium) — **nunca** o contrário; **nunca** importar views/serializers/services.
- **Modelos = dados + validação só** (`.claude/rules/architecture.md`): `clean()` valida; **zero lógica de negócio** no model (geração/pagamento = serviços S37). `is_overdue` recebe `today` por parâmetro — o model **não** chama `timezone.now()` nem o helper TZ (design §4: TZ resolvida no serviço/view).
- **Annotations, não properties** (design §4.4): `amount_total/paid/remaining/payment_status/is_overdue` SÓ via `.with_amounts()`. Proibido `@property` para essas figuras.
- **`is_offset` positivo + subtraído** (design §4.1): nunca armazenar negativo; `CheckConstraint amount >= 0` em toda linha.
- **Managers duplos** em todo modelo com SoftDelete (`all_objects`/`objects`); `BillSkip` **sem** SoftDelete (manager simples) e **fora** do RLS? — NÃO: `BillSkip` entra no RLS (é tabela nova). Só não tem soft-delete.
- **RLS na mesma migração** (`.claude/rules/database.md`) para as 7 tabelas; `RunSQL` com `reverse_sql`.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código de verdade. Tipos completos (mypy strict + pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo — `.claude/rules/coding-standards.md`); importar tipos diretamente (`from django.db.models import QuerySet`, etc.).
- **Sem re-exports / barrel files / shims**: `finances/models.py` exporta só o que define; importa mixins direto de `core.models`.
- **Sem serviço/serializer/viewset/URL/signal/cache/frontend** (S37/S38/fases seguintes). Sem `Installment`/`Employee`/`Reserve`/`IncomeEntry`/`CondoMonthClose`. Sem `Bill.installment`/`Bill.employee` (ambos S41).
- **`DecimalField(12,2)`** em todo dinheiro; quantização só na fronteira (não no model/annotation).
- **Backup antes do migrate** (`.claude/rules/database.md`); migração testada forward **e** backward.
- Mensagens de erro ao usuário em **Português**; logs/identificadores/enum values em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/models.py` define `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation` + `BillBehavior`/`BillLifecycleState`/`BillingAccountState`/`FundedFrom` + `BillQuerySet`/`BillManager`, importando mixins/manager de `core.models` (sem re-export).
- [ ] Todos os modelos `(AuditMixin, SoftDeleteMixin, models.Model)` com managers duplos, **exceto `BillSkip`** (`AuditMixin` + `models.Model`, manager simples, sem `is_deleted`).
- [ ] `Bill` tem **só** `billing_account` como FK de fonte; docstring documenta que `installment` (S41) e `employee` (S41) chegam depois; `behavior` enum já inclui `INSTALLMENT`.
- [ ] `.with_amounts(today)` anota `amount_total` (Σ não-offset − Σ offset), `amount_paid` (Σ alocações ativas), `amount_remaining`, `payment_status ∈ {open, partial, paid}`, `is_overdue` — **annotations Sum-subquery, zero property Python**; **não** infla com N linhas × M alocações (teste anti-cartesiano verde).
- [ ] `is_offset` armazenado positivo, subtraído; `amount_total >= 0` mantido; `CheckConstraint amount >= 0` em `BillLineItem`; `Payment`/`PaymentAllocation.amount > 0`; `BillingAccount.expected_amount >= 0`.
- [ ] partial unique idempotente `(billing_account, competence_month)` (condição `is_deleted=False` + `billing_account__isnull=False`); `Category (condominium, parent, name)`; `BillSkip (billing_account, reference_month)` (sem condição — hard delete des-pula). Soft-delete libera os slots (Bill/Category); testes provam.
- [ ] `competence_month`/`reference_month`/`tracking_start_month` normalizados para dia 1.
- [ ] Migração inicial do `finances` gerada, **depende explicitamente** da migração do `core` que cria `Condominium`, inclui `RunSQL` de RLS (ENABLE/DISABLE) para as 7 tabelas; `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] Factories `make_finance_category`/`make_billing_account`/`make_bill`/`make_bill_line_item`/`make_bill_skip`/`make_payment`/`make_payment_allocation` em `tests/factories.py` (estilo existente).
- [ ] `tests/unit/test_finances/test_bill_models.py` + `test_bill_annotations.py` cobrem todos os cenários listados (herança/managers, constraints/clean PT, partial-unique idempotente, is_offset, with_amounts incl. anti-cartesiano/overdue/soft-delete/estruturais §18).
- [ ] `python -m pytest tests/unit/test_finances/...` passa 100%, **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/models.py` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`.
- [ ] Nenhum serviço/serializer/viewset/URL/signal/cache/frontend criado; `core/models.py`/`core/signals.py`/`settings.py` intactos; nenhum modelo de fase 3/4.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_bill_models.py tests/unit/test_finances/test_bill_annotations.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   ruff check finances/models.py tests/unit/test_finances/ tests/factories.py
   ruff format --check finances/models.py tests/unit/test_finances/ tests/factories.py
   mypy core/ finances/
   pyright finances/models.py
   python manage.py makemigrations --check --dry-run
   ```
2. Atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 36 (status **concluída**) na tabela de progresso da feature Condomínio Finance.
   - Listar **Arquivos Criados** (`finances/models.py` núcleo de contas, `finances/migrations/000X_bills_core.py`, `tests/unit/test_finances/test_bill_models.py`, `test_bill_annotations.py`) e **Modificados** (`tests/factories.py` — 7 factories novas).
   - Anotar os **contratos cross-session** (verbatim, ver abaixo) para a S37/S38/S41/S44 consumirem sem derivar.
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch se necessário — ex.: `feat/condo-finance`):
   ```
   feat(finances): add bill-core models (Category, BillingAccount, Bill, BillLineItem, BillSkip, Payment, PaymentAllocation) with amount annotations + RLS migration

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **37 — Backend serviços de contas** (`BillGenerationService.ensure_month_bills`, `BillService.create_with_lines`, `BillPaymentService.pay`, `CondoCalendarService`) — consome os modelos e o `.with_amounts()` desta sessão. A S37 **adiciona** os serviços; **não** recria modelos.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.models`**: `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`; enums `BillBehavior` (`one_time`/`recurring`/`installment`), `BillLifecycleState` (`active`/`suspended`/`deferred`/`canceled`), `BillingAccountState` (`active`/`suspended`/`deferred`/`ended`), `FundedFrom` (`caixa`/`reserve`).
- **`Bill.objects.with_amounts(today: date)`** → queryset com `amount_total`, `amount_paid`, `amount_remaining`, `payment_status`, `is_overdue` (annotations). **S37/S38** (`CondoCalendarService`, listas de atrasados, serializers read) leem essas annotations — nunca recomputam em Python; **S38** serializa `amount_*` como string Decimal.
- **`Bill` FKs de fonte**: só `billing_account` agora. **S41** adiciona `Bill.installment` + unique parcial `(installment)`; **S41** adiciona `Bill.employee` + unique parcial `(employee, competence_month)` — via `add_field`, **não** recriar o model.
- **`BillLineItem`**: `is_offset` positivo+subtraído; **S41** adiciona `installment` FK (parcela embutida) à linha.
- **`BillPaymentService.pay`** (S37) cria `Payment(funded_from)` + `PaymentAllocation(→bill, amount)`; `amount_paid` do bill deriva **só** de `PaymentAllocation` (contrato fixado aqui pelo `with_amounts`).
- **Idempotência** de `BillGenerationService.ensure_month_bills` (S37) repousa na unique parcial `(billing_account, competence_month)` definida aqui (`get_or_create` race-safe).
- **`BillSkip`** sem soft-delete (hard delete des-pula) — `BillGenerationService` (S37) consulta `BillSkip.objects.filter(billing_account, reference_month)` para pular o mês.
