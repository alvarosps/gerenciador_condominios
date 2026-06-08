# Sessão 41 — Backend: `InstallmentPlan`/`Installment` + `Employee` + migração + `convert_deferred` + estender geração

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → **41** → 42 → 43 → … → 50 (esta abre a **Fase 3 — Parcelas + Folha**)
> Esta sessão cria os modelos de **parcelamento** (`InstallmentPlan`/`Installment`, embutido + avulso) e de **folha** (`Employee`: autônomo, `payment_type`, `base_salary?`, `lease?` `SET_NULL`, abatimento §4.6, fim de lease via `is_deleted`); a **migração** que adiciona `Bill.installment`/`Bill.employee` FKs + `BillLineItem.installment` FK + as unique parciais; o serviço **`InstallmentPlanService.convert_deferred`** (atômico, sem duplicar/perder, item deferido → estado terminal fora de TODAS as somas); e **ESTENDE** `BillGenerationService.ensure_month_bills` com **parcelas** (não-embutidas → `Bill` próprio; embutidas → linha no `Bill` da conta recorrente, dedup) e **folha**, com o **sync realizado ↔ schedule** (`BillLineItem.amount` ↔ `Installment.amount`). **Sem reserva/income/fechamento (Fase 4, S47–S49); sem frontend (S43); sem serializers/viewsets/URLs novos.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.2, §3.3, §4.1, §4.4, §4.6, §5.2 blocos "Fontes"/"Pagável", §7 mapeamento, §8 "BillGenerationService"/"InstallmentPlanService.convert_deferred", §13 migrações, §14 Fase 3, §18 edge-cases "Parcelas" + "Folha")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Model filho `CASCADE` + unique parcial `(parent, number)` + `CheckConstraint(amount>=0)` + indexes + `__str__` PT** | `core/models.py:1150-1186` (`ExpenseInstallment`: FK `expense` `CASCADE` :1151; `installment_number`/`total_installments`/`amount`/`due_date` :1152-1155; managers duplos :1160-1161; `UniqueConstraint(fields=["expense","installment_number"], condition=Q(is_deleted=False))` :1166-1170; `CheckConstraint(amount__gte=0)` :1171-1174; `__str__` :1185-1186) | **Exemplar canônico** de `Installment` (filho `CASCADE` do `InstallmentPlan`, unique parcial `(plan, number)`). Copiar a forma de constraints/managers/`__str__` |
| **Model de folha (salário/variável/abatimento) + `total_paid` + `clean()` PT + unique parcial `(person, month)`** | `core/models.py:1280-1318` (`EmployeePayment`: `person` FK `PROTECT` :1281; `base_salary`/`variable_amount`/`rent_offset` :1283-1285; managers :1291-1292; `UniqueConstraint(condition=Q(is_deleted=False))` :1297-1301; `CheckConstraint(base_salary__gte=0)` :1302-1305; `clean()` PT :1311-1314; `total_paid` property :1316-1318) | **Referência de domínio** da folha legada (base+variável−abatimento). O **novo** `Employee` é o *cadastro* (não o pagamento mensal); o pagamento mensal vira `Bill(employee=…)` com linhas (design §4.6). NÃO copiar `EmployeePayment` 1:1 — ver Especificação |
| **Model com FKs nulláveis `SET_NULL` + `is_offset` + `end_date` + `clean()` PT + cascade soft-delete** | `core/models.py:1032-1075` (`Expense`: FKs `SET_NULL` :1037-1048; `is_offset` :1066-1069; `end_date` :1061-1065; managers duplos :1074-1075) | Forma de FKs nulláveis (`Employee.lease` `SET_NULL`; `InstallmentPlan.building`/`category`) e do `is_offset` na linha de abatimento |
| **`effective_rental_value` (abatimento §4.6 = valor efetivo do mês)** | `core/services/rent_schedule_service.py:122-139` (`@staticmethod effective_rental_value(lease, reference_month) -> Decimal`) | O abatimento da folha de funcionário-inquilino **deve igualar** `effective_rental_value(lease, competence_month)` (design §4.6). Reusar — **não** reimplementar |
| **`is_prepaid_for_month` (collectibility por mês — Rosa fora da receita)** | `core/services/rent_schedule_service.py:93-120` (`is_prepaid_for_month` :93; `is_collectible_for_month` :110) | A lease 205 (Rosa) tem `is_salary_offset=True` → já excluída de `collectible_leases`. Testar a invariante de que o aluguel é contado UMA vez (não receita, não despesa separada; só reduz a folha) |
| **`clamp_due_day` (gerador de datas puro — reuso DIRETO)** | `core/services/rent_schedule_service.py:65` (`@staticmethod clamp_due_day(due_day, year, month) -> int`) | A geração de `Bill` de parcela/folha reusa o **mesmo** `_due_date_for` do `BillGenerationService` (S37), que já chama `clamp_due_day` (31→último dia) |
| **`BillGenerationService.ensure_month_bills` (ESTENDER — não recriar)** | `finances/services/bill_generation_service.py` (S37: `ensure_month_bills(year, month, user=None) -> list[Bill]`, `_due_date_for`, `_is_account_eligible`, seed; **docstring marca o ponto de extensão**: "S41 estende com `Installment` de planos não-embutidos; S44 estende com folha; embutidos viram linha no `Bill` da conta recorrente, nunca `Bill` próprio") | Esta sessão **adiciona** a geração de parcelas (avulsas → `Bill` próprio; embutidas → linha) e folha **dentro** do `ensure_month_bills` (ou helpers privados que ele chama). NÃO duplicar a lógica de recorrentes/seed da S37 |
| **`Bill.objects.with_amounts(today)` (annotations — NÃO recomputar em Python)** | `finances/models.py` (S36: `BillQuerySet.with_amounts`, `amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue`; unique parcial `(billing_account, competence_month)`) | A geração e o sync leem/escrevem via ORM; o `amount_total` da conta embutida deriva das linhas (consumo + parcela) via `with_amounts`. **Nunca** somar linhas em Python |
| **`Bill` FKs de fonte (S36 deixou só `billing_account`; docstring reserva `installment`/`employee`)** | `finances/models.py` (S36: `Bill.billing_account` FK `SET_NULL`; docstring: "installment FK = S41; employee FK = S44") | **Esta sessão adiciona `Bill.installment` (S41) E `Bill.employee` (S41, antecipado da S44 porque a folha entra na geração nesta fase — ver Decisão pinada abaixo).** Adicionar via `add_field` na migração, **não** recriar o model |
| **Migração `add_field` + unique parcial + RLS já habilitada (tabelas existentes)** | `core/migrations/0047_enable_row_level_security.py:16-134` (`ENABLE_RLS`/`DISABLE_RLS`, `RunSQL(sql, reverse_sql)`) + qualquer `add_field` recente do `finances` (S38/S40) | Os modelos **novos** (`InstallmentPlan`/`Installment`/`Employee`) habilitam RLS na **mesma** migração (3 tabelas novas: `finances_installmentplan`, `finances_installment`, `finances_employee`). As FKs em `Bill`/`BillLineItem` são `add_field` em tabelas já com RLS (não re-habilitar) |
| **Service stateless `@staticmethod` + `transaction.atomic` + `select_for_update` + retorno/log** | `core/services/rent_schedule_service.py:61` (classe) + `toggle_payment` (`transaction.atomic`/`select_for_update`/retorno PT/`logger` EN) e `finances/services/bill_payment_service.py` (S37: `pay`/`unpay` atômicos) | **Estrutura-base** de `InstallmentPlanService.convert_deferred` (atômico, lock, msgs PT, logs EN) |
| **Factories `make_<model>()` (estilo `**kwargs`/`defaults`/`baker.make`)** | `tests/factories.py:72-86` (`make_lease`), `:98-125` (`make_expense`/`make_expense_installment`), `:190-205` (`make_rent_payment`/`make_employee_payment`) + factories `finances` da S36 (`make_billing_account`/`make_bill`/`make_bill_line_item`) e `make_condominium`/`make_building` (S34) | **Espelhar** o estilo: função módulo-nível, `defaults` dict, `user` opcional → `created_by`/`updated_by`, `baker.make("finances.<Model>", **defaults)`. Adicionar `make_installment_plan`, `make_installment`, `make_employee` |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **só `freezegun`** (congelar a data para `today_sp()`/`is_overdue`); ORM/serviços/`RentScheduleService` reais |

### O que a S34/S36/S37/S40 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S34** (infra): app `finances` + `FinancesConfig.ready()` importando `finances/signals.py` + `core.Condominium`(padrão) + `Building.condominium` + helper TZ `finances/services/timezone.py` (`today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`) + gate ampliado (`finances` em `--cov`/`mypy core/ finances/`/`pyrightconfig.json`) + `make_condominium`/`make_building`.
- **S36** (modelos núcleo): `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`; enums `BillBehavior` (`one_time`/`recurring`/`installment`), `BillLifecycleState` (`active`/`suspended`/`deferred`/`canceled`), `BillingAccountState` (`active`/`suspended`/`deferred`/`ended`), `FundedFrom`; `Bill.objects.with_amounts(today)`; unique parcial `(billing_account, competence_month)`; migração inicial + RLS; 7 factories. **`Bill` só tem `billing_account` de fonte; docstring reserva `installment`/`employee`. `BillLineItem` reserva `installment`.**
- **S37** (serviços de contas): `BillGenerationService.ensure_month_bills` (recorrentes + seed, idempotente race-safe, **pula embutidos/parcelas/folha — ponto de extensão documentado no docstring**), `BillService.create_with_lines`, `BillPaymentService.pay`/`unpay`; `finances/cache.py` (prefixos `finance-*` + `invalidate_finance_caches`); `finances/signals.py` real; `core/signals.py` estendido + cross-app NET-NEW; `RentScheduleService.received_collectible_total`.
- **S38/S39/S40**: API (serializers/viewsets/URLs de `bills`/`payments`/`billing-accounts`/calendário) + frontend data-layer + dashboard de contas. **Não dependemos do que essas sessões entregam para os modelos/geração desta**, mas **não** os quebrar.

> **Se a S36 ou a S37 não estiverem concluídas, PARE.** Esta sessão depende delas (DEPENDENCY ORDER 36→37→…→41). Não recriar modelos núcleo, geração de recorrentes, seed, cache ou signals aqui.

---

## Escopo

### Arquivos a criar
- `finances/services/installment_plan_service.py` — `InstallmentPlanService` (`convert_deferred` atômico).
- `tests/unit/test_finances/test_installment_models.py` — testes dos modelos `InstallmentPlan`/`Installment` (constraints, `clean()` PT, soft-delete, partial-unique, embedded vs avulso, `lifecycle_state`).
- `tests/unit/test_finances/test_employee_model.py` — testes do `Employee` (campos, `payment_type`, `base_salary?`, `lease?` `SET_NULL`, `is_deleted` da lease, `clean()` PT).
- `tests/unit/test_finances/test_installment_plan_service.py` — testes do `convert_deferred` (atômico, sem duplicar/perder, item deferido terminal fora das somas).
- `tests/unit/test_finances/test_generation_installments_payroll.py` — testes da **extensão** de `ensure_month_bills` (parcela avulsa → `Bill` próprio; embutida → linha no `Bill` recorrente, dedup; folha; sync realizado ↔ schedule; última parcela → plano `paid`; Rosa; variável-only).

### Arquivos a modificar
- `finances/models.py` — **adicionar** `InstallmentPlan`, `Installment`, `Employee` + enums `InstallmentPlanState`, `EmployeePaymentType`; **adicionar** as FKs `Bill.installment` (`SET_NULL`), `Bill.employee` (`SET_NULL`), `BillLineItem.installment` (`SET_NULL`) **no model existente** (S36 reservou esses campos — preencher, não recriar o model); **adicionar** as unique parciais `Bill (installment)` e `Bill (employee, competence_month)` ao `Bill.Meta.constraints`. Imports/modelos existentes **intactos**.
- `finances/migrations/000X_installments_employee.py` — gerada por `makemigrations finances`: `CreateModel` de `InstallmentPlan`/`Installment`/`Employee`, `AddField` de `Bill.installment`/`Bill.employee`/`BillLineItem.installment`, `AddConstraint` das 2 unique parciais novas do `Bill`, **e** `RunSQL` de RLS (ENABLE/DISABLE) para as **3 tabelas novas** (`finances_installmentplan`/`finances_installment`/`finances_employee`). Depende do head do `finances` (S40).
- `finances/services/bill_generation_service.py` — **ESTENDER** `ensure_month_bills` (no ponto de extensão documentado pela S37): gerar parcelas (não-embutidas → `Bill` próprio com 1 linha = `installment.amount`; embutidas → linha no `Bill` da `linked_billing_account` recorrente, com dedup) e folha (`Bill(employee=…, behavior=RECURRING)` com linhas base/variável/abatimento). Implementar o **sync realizado ↔ schedule** e a marcação da **última parcela → plano `paid`**. Funções/serviço de recorrentes/seed da S37 **inalterados** (só adicionar os novos passos).
- `tests/factories.py` — adicionar `make_installment_plan`, `make_installment`, `make_employee` (estilo `tests/factories.py:72-125`). Imports e factories existentes **intactos**.

### NÃO fazer (pertence a outras sessões)
- **Sem `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose`** e **sem** `CondoBalanceService`/`CondoMonthCloseService` — é a **Fase 4 (S47/S48/S49)**. `funded_from='reserve'` continua só persistido (S37). Bloqueio de mês fechado continua hook futuro documentado (S37/S49). **Não** criar esses modelos/serviços.
- **Sem `CondoProjectionService`/`CondoSimulationService`** (dedup de embutido na **projeção**, prepaid por mês) — é a **Fase 5 (S45/S46)**. Esta sessão entrega o **dedup na geração** (embutida não vira `Bill` próprio) e o sync realizado; a dedup da projeção futura (computada) é da Fase 5 e **consome** o `Installment`/campos de embutido daqui.
- **Sem `OwnerDistributionService`** (fold/carry-forward, household) — é a **Fase 6 (S49/S50)**.
- **Sem serializers/viewsets/URLs/ações de API novos** — `installment-plans/`, `installments/`, `employees/`, `installment-plans/{id}/convert_deferred` são da **Sessão 42** (API da Fase 3). Os serviços desta sessão são chamados pelos viewsets da S42, não expostos agora.
- **Sem frontend** (hooks/pages/schemas de parcelas/folha) — é a **Sessão 43**.
- **Sem alterar** `core/models.py`, `core/signals.py`, `condominios_manager/settings.py`. Os signals do `finances` (S37) já cobrem `Bill`/`BillLineItem`; os novos modelos (`InstallmentPlan`/`Installment`/`Employee`) **ganham receivers de invalidação `finance-*`** — ver §"Signals dos modelos novos".
- **Sem migração/refactor de owner**; **sem seed de dados/categorias** (design §13). **Sem** `django-money`/`django-treebeard`.

---

## Especificação

> Convenções (design §5.2): `(AuditMixin, SoftDeleteMixin, models.Model)` + managers duplos (`all_objects = models.Manager()`, `objects = SoftDeleteManager()` do `core`), `DecimalField(max_digits=12, decimal_places=2)`, partial unique `condition=Q(is_deleted=False)`, `CheckConstraint amount >= 0`, `clean()` em PT, `on_delete` `PROTECT` em FKs de referência / `CASCADE` em filhos / `SET_NULL` onde indicado. `condominium` FK em todo modelo de topo. Mensagens ao usuário em **PT**, logs/identificadores/enum values em **EN**.

### Decisão pinada — `Bill.employee` entra na S41 (não na S44)

O design (§5.2) e o contrato da S36 reservaram `Bill.employee` para a "S44". **Nesta feature, a folha entra na geração já na Fase 3 (design §14 Fase 3: "ESTENDE `ensure_month_bills` com installment+folha")** — portanto o modelo `Employee` **e** a FK `Bill.employee` **são criados aqui (S41)**, junto da unique parcial `(employee, competence_month)`. A menção "S44" no contrato da S36 é resolvida assim: **a folha completa pertence à Fase 3 e é entregue nesta sessão**. **Não** há sessão 44 separada de folha — documentar isto no docstring de `Bill` (substituindo a nota "employee FK = S44" por "employee FK = S41") e no SESSION_STATE. (Se a numeração do roadmap exigir uma S44, o orquestrador a reconcilia; o **código** entrega folha+installment juntos nesta sessão, conforme o design §14.)

### Enums (em `finances/models.py`)

```python
class InstallmentPlanState(models.TextChoices):
    ACTIVE = "active", "Ativo"
    PAID = "paid", "Quitado"
    DEFERRED = "deferred", "Adiado"
    CANCELED = "canceled", "Cancelado"


class EmployeePaymentType(models.TextChoices):
    FIXED = "fixed", "Fixo"
    VARIABLE = "variable", "Variável"
    MIXED = "mixed", "Misto"
```

> `InstallmentPlanState` é **distinto** de `BillLifecycleState` (que tem `suspended`; o plano não suspende — tem `paid`). Não reusar uma para a outra (semântica diferente).

### Modelos (assinaturas de campo conforme design §5.2)

```python
# finances/models.py — ANEXAR (imports diretos; sem TYPE_CHECKING, sem __future__)
# já importados pela S36: Decimal, date, ValidationError, models, Q/Sum/.../Coalesce,
# AuditMixin, SoftDeleteMixin, SoftDeleteManager, Building, Condominium.
# NOVO import necessário: from core.models import Lease (FK Employee.lease)

class InstallmentPlan(AuditMixin, SoftDeleteMixin, models.Model):
    """Plano de parcelamento (embutido OU avulso). Materializa Installment (schedule)."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="installment_plans")
    building = models.ForeignKey(Building, null=True, blank=True, on_delete=models.PROTECT, related_name="installment_plans")  # null = nível-condomínio
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="installment_plans")
    description = models.CharField(max_length=500)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)  # >= 0
    installment_count = models.PositiveSmallIntegerField()  # > 0
    start_due_date = models.DateField()
    default_due_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    lifecycle_state = models.CharField(max_length=20, choices=InstallmentPlanState.choices, default=InstallmentPlanState.ACTIVE)
    embedded = models.BooleanField(default=False)  # True = parcela vira linha no Bill da conta recorrente
    linked_billing_account = models.ForeignKey(BillingAccount, null=True, blank=True, on_delete=models.PROTECT, related_name="installment_plans")  # só p/ embedded
    notes = models.TextField(blank=True)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # CheckConstraint total_amount >= 0; clean() PT: embedded=True ⇒ linked_billing_account obrigatório;
    #   embedded=False ⇒ linked_billing_account deve ser None (design §7). installment_count > 0.


class Installment(AuditMixin, SoftDeleteMixin, models.Model):
    """Parcela concreta (schedule). amount = projeção; sincronizado com BillLineItem.amount na realização (§sync)."""
    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name="installments")
    number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # >= 0; SCHEDULE (projeção)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # Meta: unique parcial (plan, number) condition=Q(is_deleted=False); CheckConstraint amount >= 0;
    #       ordering por due_date/number. __str__ PT (ex.: f"{plan.description} - Parcela {number}/{plan.installment_count}").


class Employee(AuditMixin, SoftDeleteMixin, models.Model):
    """Cadastro de funcionário (folha). Pagamento mensal = Bill(employee=…) com linhas (design §4.6)."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="employees")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="finance_employees")
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True)
    payment_type = models.CharField(max_length=10, choices=EmployeePaymentType.choices)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # null/0 p/ variable-only (Raymel)
    default_due_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    lease = models.ForeignKey(Lease, null=True, blank=True, on_delete=models.SET_NULL, related_name="finance_employees")  # salary-offset (Rosa, 850/205)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # CheckConstraint base_salary IS NULL OR base_salary >= 0; clean() PT:
    #   payment_type=fixed ⇒ base_salary obrigatório (> 0); payment_type=variable ⇒ base_salary null/0;
    #   payment_type=mixed ⇒ base_salary obrigatório. __str__ PT.
```

> `Person` (FK de `Employee.person`) e `Lease` (FK de `Employee.lease`) importados de `core.models`. `MinValueValidator`/`MaxValueValidator` já importados pela S36. **`Person` é `SET_NULL`** (cadastro pode existir sem `Person` formal; demais donos externos não viram funcionário).

### FKs novas em modelos existentes (S36 reservou — preencher, NÃO recriar)

Adicionar ao `Bill` (S36) **sem** recriar o model:
```python
    installment = models.ForeignKey("Installment", null=True, blank=True, on_delete=models.SET_NULL, related_name="bills")
    employee = models.ForeignKey("Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="bills")
```
Adicionar ao `Bill.Meta.constraints` (ao lado da unique `(billing_account, competence_month)` da S36):
```python
        models.UniqueConstraint(fields=["installment"], condition=Q(is_deleted=False, installment__isnull=False), name="unique_active_bill_per_installment"),
        models.UniqueConstraint(fields=["employee", "competence_month"], condition=Q(is_deleted=False, employee__isnull=False), name="unique_active_bill_per_employee_month"),
```
Adicionar ao `BillLineItem` (S36):
```python
    installment = models.ForeignKey("Installment", null=True, blank=True, on_delete=models.SET_NULL, related_name="line_items")  # parcela embutida
```

> Usar referências string (`"Installment"`/`"Employee"`) ou ordenar a definição dos modelos para que `Installment`/`Employee` venham **antes** de `Bill`/`BillLineItem`. **Decidir e documentar** (KISS — string refs evitam reordenar o arquivo da S36). `on_delete=SET_NULL` (não `PROTECT`): apagar uma parcela/funcionário não deve apagar o histórico de `Bill` real (passado = linhas reais, design §3.2).

### `InstallmentPlanService.convert_deferred(...)` (design §8 — atômico)

Converte um item **deferido** (ex.: IPTU anual marcado `lifecycle_state=deferred` no `Bill`, design §7) num `InstallmentPlan` — **sem duplicar nem perder valor**, e deixando o item deferido num **estado terminal fora de TODAS as somas**.

```python
@staticmethod
def convert_deferred(
    *,
    deferred_bill: Bill,
    installment_count: int,
    start_due_date: date,
    default_due_day: int,
    category: Category | None = None,
    user: User | None = None,
) -> InstallmentPlan:
    """Converte um Bill deferido em InstallmentPlan(avulso) atômico.

    - @transaction.atomic + select_for_update no deferred_bill.
    - Pré-condição: deferred_bill.lifecycle_state == DEFERRED → senão ValidationError PT
      ("Só é possível reparcelar uma conta adiada.").
    - total = deferred_bill.objects.with_amounts(today_sp()).amount_total (valor adiado; NUNCA somar em Python).
    - Cria InstallmentPlan(embedded=False, total_amount=total, installment_count, start_due_date,
      default_due_day, lifecycle_state=ACTIVE, condominium/building/category/created_by) + N Installment
      (number 1..N, due_date = start_due_date + (k-1) meses clampado via clamp_due_day, amount = total/N
      com o RESTO do arredondamento na ÚLTIMA parcela — Σ amount == total, sem perder centavos).
    - Estado terminal do item deferido: deferred_bill.lifecycle_state = CANCELED (já fora das somas de
      competência E do overdue — design §4.4: lifecycle != active sai de tudo). NÃO soft-delete o bill
      (passado = linhas reais; CANCELED é o terminal correto, auditável). Documentar a escolha.
    - Invariante (teste): total_amount do plano == amount_total do bill antes da conversão; Σ Installment.amount
      == total_amount; o bill deferido não aparece em nenhuma soma de competência/overdue após CANCELED.
    """
```

Regras:
- **Atomicidade**: tudo num `@transaction.atomic`; falha → rollback total (nem plano órfão, nem bill semi-convertido).
- **Sem duplicar/perder** (design §8 + §18): `total_amount == valor deferido`; `Σ Installment.amount == total_amount` (resto na última parcela, `ROUND_HALF_UP` na divisão, ajuste de centavo na última — testar `total=100, N=3 → 33.33 + 33.33 + 33.34`).
- **Item deferido → terminal**: `CANCELED` (fora das somas, design §4.4). O valor migra **inteiro** para o plano; nunca contado duas vezes.
- `start_due_date` define a 1ª parcela; as seguintes somam 1 mês (usar `dateutil.relativedelta` — já é dependência, design §13) e clampam o dia via `RentScheduleService.clamp_due_day`.

### Extensão de `ensure_month_bills` — parcelas + folha + sync (design §8/§14 Fase 3)

> A S37 deixou o ponto de extensão documentado no docstring de `ensure_month_bills`. Adicionar **três** passos novos ao método (ou helpers privados que ele chama, na mesma ordem determinística), **preservando** o passo de recorrentes+seed da S37. Tudo idempotente race-safe (mesma técnica `get_or_create`+`IntegrityError` na unique parcial — design §8).

**(A) Parcelas avulsas (não-embutidas) → `Bill` próprio.**
Para cada `Installment` ativo de `InstallmentPlan` com `embedded=False`, `lifecycle_state=ACTIVE`, cujo `due_date` cai em `M = date(year, month, 1)` (mês/ano do `due_date`):
- Garantir **um** `Bill(installment=inst, competence_month=M)` (unique parcial `(installment)`), `behavior=BillBehavior.INSTALLMENT`, `due_date=inst.due_date` (já clampado na criação do plano), `description=plan.description`, `building=plan.building`, `category=plan.category`, `condominium=plan.condominium`.
- Criar **uma** `BillLineItem(bill, amount=inst.amount, description=plan.description, category=plan.category)` quando o bill é **recém-criado** (idempotência: não re-criar linha).

**(B) Parcelas embutidas → linha no `Bill` da conta recorrente (dedup).**
Para cada `Installment` ativo de `InstallmentPlan` com `embedded=True`, `linked_billing_account` setado, cujo `due_date` cai em `M`:
- **NÃO** criar `Bill` próprio (dedup — design §7/§18 "embutida não duplica"). Em vez disso, localizar o `Bill` recorrente da `linked_billing_account` no mês `M` (o que a S37 garante via recorrentes). Se ele ainda não existe nesta passada, garantir-lo primeiro (a ordem do `ensure_month_bills` deve gerar recorrentes **antes** das embutidas — documentar a ordem).
- Garantir **uma** `BillLineItem(bill=<recorrente do mês>, installment=inst, amount=inst.amount, description=f"Parcela {inst.number}/{plan.installment_count}", category=plan.category)` — **dedup por `(bill, installment)`**: se já existe uma linha ativa com `installment=inst` naquele bill, não duplicar (idempotência; consulta `BillLineItem.objects.filter(bill=…, installment=inst).exists()`). Assim `amount_total` da conta = consumo (linha recorrente da S37) + parcela embutida (design §7 "1000 = 600 consumo + 400 parcela").

**(C) Folha → `Bill(employee=…, behavior=RECURRING)` com linhas base/variável/abatimento (design §4.6).**
Para cada `Employee` com `is_active=True` do condomínio:
- Garantir **um** `Bill(employee=emp, competence_month=M)` (unique parcial `(employee, competence_month)`), `behavior=BillBehavior.RECURRING`, `due_date=_due_date_for(emp, year, month)` (reusa `clamp_due_day`), `description=f"Folha {emp.name}"`, `condominium=emp.condominium`.
- Linhas (quando recém-criado):
  - **base** (não-offset): `amount = emp.base_salary` se `payment_type ∈ {fixed, mixed}` e `base_salary` setado/`>0`; **omitir a linha base** para `payment_type=variable` (Raymel — sem base; design §6/§18 "variável-only gera bill correto"). `description="Salário base"`.
  - **variável** (não-offset): **não** é gerada automaticamente com valor>0 (o admin lança o valor variável depois via S42 `bills/{id}/lines`). Na geração, **não** criar linha variável especulativa (YAGNI) — a folha gerada tem base (se houver) e abatimento (se houver). Documentar que o variável é lançado manualmente. *(Para variável-only sem base, o bill gerado pode ficar sem linhas até o admin lançar — `amount_total=0`, `payment_status='open'`; travar por teste.)*
  - **abatimento** (`is_offset=True`, positivo + subtraído): **somente** se `emp.lease` setado **e** a lease é salary-offset (`lease.is_salary_offset=True`) **e** a lease **não** está soft-deletada (`lease.is_deleted=False` — fim de lease para o abatimento por `is_deleted`, **não** por FK null; design §5.2/§18). `amount = RentScheduleService.effective_rental_value(lease, M)` (design §4.6 — o abatimento **deve igualar** o valor efetivo do mês). `description="Abatimento aluguel"`.
- **Fim de lease (§18)**: se `emp.lease` está soft-deletada no mês de competência → **não** gerar a linha de abatimento (o abatimento "para"). A lease segue acessível via `Lease.all_objects` mas a regra de geração usa `is_deleted=False`. Testar: deletar a lease (soft) → a folha do mês seguinte não tem abatimento.

**Sync realizado ↔ schedule (`BillLineItem.amount` ↔ `Installment.amount`, design §5.2).**
`Installment.amount` é o **schedule** (projeção); `BillLineItem.amount` é o **realizado** (fonte de verdade do histórico/caixa, S36). Quando a geração materializa a parcela (passos A/B) ela **copia** `installment.amount` → `line.amount` na **criação**. Se, depois, o admin editar o realizado (`BillLineItem.amount`) via S42, o **schedule não se altera retroativamente** (passado = linhas reais). **Não** propagar realizado→schedule automaticamente nesta sessão (a edição manual do realizado é da S42; o sync que esta sessão entrega é a **cópia schedule→realizado na materialização**). Documentar a direção. *(O design §5.2 fala em "sincronizado" — a leitura canônica fixada aqui: materialização copia schedule→realizado; edições posteriores do realizado são autoritativas para aquele mês e não reescrevem o schedule.)*

**Última parcela → plano `paid` (design §18).**
Após garantir os `Bill`/linhas das parcelas do mês: se **todas** as `Installment` ativas do plano já foram materializadas (existe `Bill`/`BillLineItem` ativo para cada — i.e. a última parcela do plano foi gerada neste mês), marcar `InstallmentPlan.lifecycle_state = PAID`. **Decisão pinada**: "materializada a última parcela" = `Installment.objects.filter(plan=…).count()` parcelas todas com `Bill`/linha ativa **e** a de maior `number == installment_count` está no mês `M`. Travar por teste (gerar o último mês → plano vira `paid`; gerar um mês intermediário → plano segue `active`). *(KISS: "paid" aqui = "totalmente materializado/agendado"; não confundir com `payment_status` do bill, que depende de `PaymentAllocation`.)*

> **Ordem determinística** dentro de `ensure_month_bills` (documentar): (1) recorrentes + seed (S37) → (2) embutidas (precisam do `Bill` recorrente do passo 1) → (3) parcelas avulsas → (4) folha. O retorno continua `list[Bill]` (todos os bills garantidos no mês). **Não** alterar a assinatura `ensure_month_bills(year, month, user=None) -> list[Bill]` (S37/S38 dependem dela).

### Signals dos modelos novos (invalidação `finance-*`)

A S37 criou `finances/signals.py` com receivers `post_save`/`post_delete` nos 7 modelos da S36 chamando `invalidate_finance_caches()`. **Adicionar** receivers análogos para `InstallmentPlan`, `Installment`, `Employee` (mesmo idioma, import direto de `finances.models`/`finances.cache`). Isso mantém os dashboards `finance-*` consistentes quando parcelas/folha mudam. **Não** tocar `core/signals.py` (cross-app já coberto pela S37).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui é **só `freezegun`** (congelar a data para `today_sp()`/`is_overdue`/geração do mês). **NUNCA** mockar ORM, managers, `Bill.with_amounts`, `RentScheduleService`, `BillGenerationService`, `CacheManager`, signals ou qualquer interno. Banco real via `--reuse-db`; `transaction.atomic()` ao asserir `IntegrityError`. Dados via factories (`model-bakery`). `filterwarnings=error`: zero warnings. **Backup antes do migrate** (`.claude/rules/database.md`): `python scripts/backup_db.py` (a migração cria 3 tabelas + 3 add_field + 2 constraints + RLS; criar/adicionar é menos arriscado que dropar, mas a regra backup-antes-de-migrate é primária).

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_installment_models.py`
- [ ] `InstallmentPlan` e `Installment` herdam `AuditMixin` (`created_at`/`updated_at` não-nulos) **e** `SoftDeleteMixin` (`is_deleted=False` default); `objects` exclui soft-deleted, `all_objects.with_deleted()` inclui.
- [ ] `InstallmentPlan.total_amount` negativo → `IntegrityError` (CheckConstraint); `installment_count <= 0` rejeitado.
- [ ] `Installment.amount` negativo → `IntegrityError`; `amount=0` permitido.
- [ ] **partial unique `(plan, number)`**: dois `Installment` ativos com mesmo `(plan, number)` → `IntegrityError`; após soft-delete do primeiro, criar o segundo funciona (slot liberado — espelha `ExpenseInstallment` :1166-1170).
- [ ] **`clean()` PT — embutido**: `embedded=True` **sem** `linked_billing_account` → `ValidationError` PT; `embedded=False` **com** `linked_billing_account` setado → `ValidationError` PT (mutuamente consistente, design §7).
- [ ] `Installment` é filho `CASCADE` do `InstallmentPlan` (deletar o plano via hard delete leva as parcelas — smoke; soft-delete do plano segue o cascade soft da S36/mixin).
- [ ] `lifecycle_state` default `ACTIVE`; choices `{active, paid, deferred, canceled}` (não `suspended`).
- [ ] `__str__` PT coerente (smoke).

#### `tests/unit/test_finances/test_employee_model.py`
- [ ] `Employee` herda `AuditMixin` + `SoftDeleteMixin`; managers duplos.
- [ ] `payment_type` choices `{fixed, variable, mixed}`.
- [ ] **`base_salary` opcional**: `payment_type=variable` com `base_salary=None` → válido (Raymel); `base_salary` negativo → `IntegrityError` (CheckConstraint `base_salary IS NULL OR >= 0`).
- [ ] **`clean()` PT**: `payment_type=fixed` sem `base_salary` (ou `<=0`) → `ValidationError` PT; `payment_type=variable` com `base_salary>0` → `ValidationError` PT (variável não tem base); `payment_type=mixed` sem `base_salary` → `ValidationError` PT.
- [ ] **`lease` `SET_NULL`**: hard-delete da lease → `Employee.lease` vira `None` (FK `SET_NULL`); **mas** soft-delete da lease **NÃO** dispara `SET_NULL` (a FK continua apontando; `lease.is_deleted=True`) — provar que o `Employee.lease` ainda referencia a lease soft-deletada (a regra de fim-de-lease é por `is_deleted`, não por FK null — design §5.2). Asserir `emp.lease_id is not None` após soft-delete + `Lease.all_objects.get(pk=…).is_deleted is True`.
- [ ] `person` `SET_NULL` (cadastro sobrevive sem `Person`).
- [ ] `__str__` PT coerente (smoke).

#### `tests/unit/test_finances/test_installment_plan_service.py` (sob `@freeze_time`)
- [ ] **conversão básica**: `Bill` deferido (`lifecycle_state=DEFERRED`) com `amount_total=1200` → `convert_deferred(installment_count=12, ...)` cria `InstallmentPlan(embedded=False, total_amount=1200, installment_count=12)` + **12** `Installment`; `Σ Installment.amount == 1200`; `due_date` de cada parcela = `start_due_date + (k-1)` meses clampado.
- [ ] **resto de arredondamento na última** (§18 "sem perder centavos"): `total=100, N=3` → parcelas `33.33, 33.33, 33.34`; `Σ == 100.00`.
- [ ] **item deferido → terminal fora das somas** (§18): após `convert_deferred`, `deferred_bill.lifecycle_state == CANCELED`; o bill **não** aparece em nenhuma soma de competência nem em overdue (via `with_amounts(today)` filtrado por `lifecycle_state='active'` → não conta). O valor migrou inteiro (`plan.total_amount == 1200`), nunca duplicado.
- [ ] **atomicidade**: forçar falha (ex.: `installment_count=0` → rejeitado **antes** de criar; ou simular violação) → **nenhum** `InstallmentPlan`/`Installment` criado e o `deferred_bill` permanece `DEFERRED` (rollback total).
- [ ] **pré-condição**: `convert_deferred` num bill `lifecycle_state=active` → `ValidationError` PT ("Só é possível reparcelar uma conta adiada.").

#### `tests/unit/test_finances/test_generation_installments_payroll.py` (sob `@freeze_time`)
**Parcela avulsa (não-embutida)**
- [ ] `InstallmentPlan(embedded=False)` com `Installment(number=1, due_date no mês M, amount=400)` → `ensure_month_bills(M.year, M.month)` gera **1** `Bill(installment=inst, behavior=INSTALLMENT)` com **1 linha** `amount=400`; `with_amounts(today).amount_total==400`. **Idempotência**: re-rodar → continua 1 bill + 1 linha.
- [ ] parcela cujo `due_date` **não** cai em M → nenhum bill no mês M.

**Parcela embutida + dedup (§18 "embutida não duplica")**
- [ ] `BillingAccount` recorrente (consumo `expected_amount=600`) **+** `InstallmentPlan(embedded=True, linked_billing_account=<conta>)` com `Installment(amount=400)` em M → `ensure_month_bills` gera **1** `Bill` (o recorrente), com **2 linhas**: consumo (600, da S37) + parcela embutida (400, `installment=inst`); `amount_total==1000` (design §7 "1000 = 600 consumo + 400 parcela"). **Nenhum** `Bill` próprio para a parcela embutida (`Bill.all_objects.filter(installment=inst).count()==0`).
- [ ] **idempotência da embutida**: re-rodar `ensure_month_bills` → continua **1 bill, 2 linhas** (dedup por `(bill, installment)`; não duplica a linha de parcela).
- [ ] **ordem**: a embutida acha o `Bill` recorrente gerado no mesmo `ensure_month_bills` (recorrentes antes de embutidas) — testar que rodar **uma** vez já produz as 2 linhas (não exige 2 passadas).

**Sync realizado ↔ schedule**
- [ ] na materialização, `BillLineItem.amount == Installment.amount` (cópia schedule→realizado). Depois, editar `line.amount` (ex.: 400→420) **não** altera `Installment.amount` (continua 400; schedule preservado — design §5.2, direção fixada nesta sessão).

**Última parcela → plano `paid` (§18)**
- [ ] plano `embedded=False` com 2 parcelas (jan, fev); gerar **fev** (última) → todas materializadas → `InstallmentPlan.lifecycle_state == PAID`; gerar só **jan** (intermediária) → plano segue `ACTIVE`.

**Folha (§18 "Folha")**
- [ ] `Employee(payment_type=mixed, base_salary=2000, lease=<850/205 salary-offset, rental 1000>)` (Rosa) → `ensure_month_bills` gera `Bill(employee=emp, behavior=RECURRING)` com linha **base** 2000 (não-offset) + linha **abatimento** 1000 (`is_offset=True`, = `effective_rental_value(lease, M)`); `amount_total == 2000 − 1000 == 1000` (caixa pago à Rosa, design §4.6). A lease 205 está em `is_salary_offset=True` → **não** está em `collectible_leases(M)` (provar: aluguel contado uma vez — não receita, não despesa separada).
- [ ] **abatimento = effective_rental_value** (§4.6 invariante): com `pending_rental_value` em vigor no mês, a linha de abatimento iguala o valor efetivo (não o `rental_value` cru) — bate exatamente com `RentScheduleService.effective_rental_value`.
- [ ] **variável-only (Raymel, §18)**: `Employee(payment_type=variable, base_salary=None, lease=None)` → `ensure_month_bills` gera `Bill(employee=emp)` **sem** linha base e **sem** abatimento (variável lançado manualmente depois) → `amount_total==0`, `payment_status='open'` (convenção travada).
- [ ] **fim de lease (§18)**: `Employee(lease=<salary-offset>)`; soft-delete da lease; gerar o mês seguinte → folha **sem** linha de abatimento (a FK ainda aponta — `lease_id` não-null — mas `lease.is_deleted=True` corta o abatimento; design §5.2 "fim de lease via is_deleted, não FK null").
- [ ] **idempotência da folha**: re-rodar `ensure_month_bills` → continua **1** `Bill(employee, M)` com as mesmas linhas (não duplica).

**Estrutural / não-regressão**
- [ ] condomínio **sem** `InstallmentPlan`/`Employee` → `ensure_month_bills` continua gerando só recorrentes/seed (comportamento S37 intacto); a lista de retorno inclui os bills de parcela/folha quando existem.
- [ ] **soft-deleted** `Installment`/`Employee`/`InstallmentPlan` (ou plano `lifecycle_state ∈ {paid, deferred, canceled}`) **não** gera bill no mês.

> Rodar (devem **falhar** — modelos/FKs/serviço/extensão/migração ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_installment_models.py tests/unit/test_finances/test_employee_model.py \
>   tests/unit/test_finances/test_installment_plan_service.py tests/unit/test_finances/test_generation_installments_payroll.py -q
> ```

### 2. GREEN — implementar

1. `finances/models.py` — anexar `InstallmentPlanState`/`EmployeePaymentType`, `InstallmentPlan`, `Installment`, `Employee`; adicionar `Bill.installment`/`Bill.employee`/`BillLineItem.installment` (FKs `SET_NULL`) e as 2 unique parciais novas ao `Bill.Meta`; atualizar o docstring de `Bill` ("employee FK = S41"). Imports diretos (`from core.models import Lease`).
2. `tests/factories.py` — `make_installment_plan`, `make_installment`, `make_employee` (estilo `:72-125`).
3. Migração:
   ```bash
   python scripts/backup_db.py                       # backup ANTES (regra database.md)
   python manage.py makemigrations finances
   # completar a migração recém-gerada (antes do 1º commit) com a RunSQL de RLS (ENABLE/DISABLE) das 3
   # tabelas novas: finances_installmentplan, finances_installment, finances_employee — espelhar 0047
   python manage.py migrate finances
   python manage.py makemigrations --check --dry-run # "No changes detected"
   ```
4. `finances/services/installment_plan_service.py` — `convert_deferred` (atômico, `select_for_update`, `relativedelta`, `clamp_due_day`, `with_amounts` para o total; CANCELED terminal).
5. `finances/services/bill_generation_service.py` — estender `ensure_month_bills` com os passos (A) avulsas, (B) embutidas+dedup, (C) folha+abatimento, + sync schedule→realizado + última-parcela→`paid`, na ordem determinística. Helpers privados nomeados (`_generate_installment_bills`, `_generate_embedded_lines`, `_generate_payroll_bills`, `_mark_plan_paid_if_complete`) — funções pequenas.
6. `finances/signals.py` — receivers `post_save`/`post_delete` para `InstallmentPlan`/`Installment`/`Employee` → `invalidate_finance_caches()`.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_installment_models.py tests/unit/test_finances/test_employee_model.py tests/unit/test_finances/test_installment_plan_service.py tests/unit/test_finances/test_generation_installments_payroll.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- O gerador de datas das parcelas no `convert_deferred` reusa o **mesmo** `clamp_due_day` e o idioma de `_due_date_for` da S37 — **não** duplicar o clamp. Se útil, extrair `_schedule_due_dates(start, count, due_day)` puro (testável isolado).
- O cálculo "resto na última parcela" num helper puro nomeado (`_split_amount(total, count) -> list[Decimal]`), com `ROUND_HALF_UP` e ajuste de centavo na última — DRY, testado isolado.
- A elegibilidade "parcela cai no mês M" e "plano ativo" num helper privado claro; idempotência sempre via `get_or_create` na unique parcial (mesma técnica da S37).
- Confirmar que **nenhum** passo soma linhas/parcelas em Python — totais via `with_amounts`; o `convert_deferred` lê `amount_total` da annotation. Quantização só na fronteira (não nos serviços).
- `invalidate_finance_caches()` continua a única fonte dos prefixos (S37); os receivers novos chamam-na (não repetem `invalidate_pattern`).
- Mensagens PT como constantes nomeadas se repetidas (sem magic strings).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_installment_models.py tests/unit/test_finances/test_employee_model.py \
  tests/unit/test_finances/test_installment_plan_service.py tests/unit/test_finances/test_generation_installments_payroll.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/ tests/factories.py
ruff format --check finances/ tests/unit/test_finances/ tests/factories.py
mypy core/ finances/
pyright finances/
```

> **Regressão obrigatória da geração da S37** (não quebrar recorrentes/seed): rodar os testes da S37 que cobrem `ensure_month_bills`:
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_generation_service.py -q
> ```

Forward/backward da migração (design §13):
```bash
python manage.py migrate finances        # forward
python manage.py migrate finances <head-anterior-S40>  # backward (DISABLE_RLS das 3 tabelas roda; FKs/constraints removidas)
python manage.py migrate finances        # re-forward (idempotente)
```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). `finances/models.py` importa `Lease`/`Person`/mixins de `core.models`; os serviços importam `RentScheduleService` (clamp/effective_rental_value), `Bill.with_amounts`, `today_sp()`, `BillGenerationService` (estendido) — **nunca** views/serializers. `finances/signals.py` importa `finances.models`/`finances.cache`.
- **Lógica de negócio só em serviços** (`.claude/rules/architecture.md`): geração/conversão/sync nos serviços; models só validam (`clean()`). `convert_deferred` e a extensão da geração **não** vivem no model.
- **Annotations, não Python** (design §4.4): `amount_total`/`amount_remaining` SEMPRE de `Bill.objects.with_amounts(today)`. Proibido somar linhas/parcelas em Python.
- **TZ SP única** (design §4): "hoje/mês atual" só via `finances.services.timezone`. Proibido `timezone.now().date()` nos serviços do `finances`.
- **Idempotência race-safe** (design §8): toda materialização via `get_or_create` na unique parcial (`(installment)`, `(employee, competence_month)`) + `try/except IntegrityError` em `transaction.atomic`. Re-rodar o mês não duplica bill/linha (avulsa, embutida ou folha).
- **Dedup embutido** (design §7/§18): parcela embutida vira **linha** no `Bill` recorrente (nunca `Bill` próprio); dedup por `(bill, installment)`. Recorrentes geram **antes** das embutidas (ordem documentada).
- **Sync schedule→realizado**: materialização copia `Installment.amount`→`BillLineItem.amount`; edição posterior do realizado (S42) **não** reescreve o schedule (direção fixada).
- **Abatimento §4.6**: linha de abatimento `is_offset=True` positivo+subtraído, `amount == effective_rental_value(lease, M)`; **só** quando `lease` salary-offset **e** `lease.is_deleted=False`. Aluguel contado uma vez (lease 205 fora de `collectible_leases`). Fim de lease por `is_deleted` (não FK null — `SET_NULL` só dispara em hard delete).
- **`convert_deferred` atômico, sem duplicar/perder**: `Σ Installment.amount == total_amount == amount_total` do bill antes; item deferido → `CANCELED` (terminal, fora de todas as somas); rollback total em falha.
- **Última parcela → plano `paid`** (design §18): marcado quando a última parcela é materializada.
- **RLS na mesma migração** (`.claude/rules/database.md`) para as **3 tabelas novas**; `add_field`/`add_constraint` em tabelas já-RLS **não** re-habilitam.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código. Tipos completos (mypy strict + pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from dateutil.relativedelta import relativedelta`, `from django.contrib.auth.models import User`, etc.).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; imports diretos da fonte.
- **Sem Reserva/Income/Fechamento (Fase 4)**, **sem Projeção/Simulação (Fase 5)**, **sem Distribuição (Fase 6)**, **sem serializers/viewsets/URLs/ações de API (S42)**, **sem frontend (S43)**. **Sem** alterar `core/models.py`/`core/signals.py`/`settings.py`.
- **`DecimalField(12,2)`**; quantização (`ROUND_HALF_UP`) só na fronteira (no `_split_amount` da conversão e na saída), não nos somatórios via annotation.
- **Backup antes do migrate** (`.claude/rules/database.md`); migração testada forward **e** backward.
- Mensagens ao usuário em **Português**; logs/identificadores/enum values em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/models.py` define `InstallmentPlan`, `Installment`, `Employee` + enums `InstallmentPlanState`/`EmployeePaymentType`, todos `(AuditMixin, SoftDeleteMixin, models.Model)` com managers duplos; `Bill` ganha `installment`/`employee` (FK `SET_NULL`) + unique parciais `(installment)` e `(employee, competence_month)`; `BillLineItem` ganha `installment` (FK `SET_NULL`); docstring de `Bill` atualizado ("employee FK = S41"). Imports diretos de `core.models` (sem re-export).
- [ ] `InstallmentPlan`: `embedded`/`linked_billing_account` consistentes via `clean()` PT (embedded⇒linked obrigatório; avulso⇒linked None); `total_amount>=0` (CheckConstraint); `installment_count>0`. `Installment`: filho `CASCADE`, unique parcial `(plan, number)` (soft-delete libera o slot), `amount>=0`.
- [ ] `Employee`: `payment_type {fixed,variable,mixed}`; `base_salary` opcional (`null OR >=0`); `clean()` PT por tipo (fixed/mixed⇒base obrigatória; variable⇒base null); `lease` `SET_NULL` (hard delete) mas fim-de-lease detectado por `is_deleted` (soft-delete não dispara `SET_NULL`); `person` `SET_NULL`.
- [ ] `InstallmentPlanService.convert_deferred(*, deferred_bill, installment_count, start_due_date, default_due_day, category=None, user=None) -> InstallmentPlan`: atômico; `total_amount == amount_total` do bill (via `with_amounts`); `Σ Installment.amount == total_amount` (resto na última); item deferido → `CANCELED` (fora de todas as somas); pré-condição `lifecycle_state==DEFERRED` (senão `ValidationError` PT); rollback total em falha.
- [ ] `ensure_month_bills` **estendido** (assinatura `(year, month, user=None) -> list[Bill]` **inalterada**): (A) parcela avulsa → `Bill(installment, behavior=INSTALLMENT)` + 1 linha; (B) parcela embutida → linha `installment=…` no `Bill` recorrente (dedup `(bill, installment)`, recorrentes antes), nunca `Bill` próprio; (C) folha → `Bill(employee, behavior=RECURRING)` com base (fixed/mixed) + abatimento (= `effective_rental_value`, só se lease salary-offset e `is_deleted=False`); sync schedule→realizado na materialização; última parcela → plano `paid`; tudo idempotente race-safe; recorrentes/seed da S37 **intactos**.
- [ ] `finances/signals.py` invalida `finance-*` em `post_save`/`post_delete` de `InstallmentPlan`/`Installment`/`Employee` (via `invalidate_finance_caches()`); `core/signals.py` **não** tocado.
- [ ] Migração gerada (depende do head do `finances` deixado pela S40): `CreateModel` ×3 + `AddField` ×3 + `AddConstraint` ×2 + `RunSQL` de RLS para as 3 tabelas novas; `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] Factories `make_installment_plan`/`make_installment`/`make_employee` em `tests/factories.py` (estilo existente).
- [ ] Os 4 arquivos de teste cobrem todos os cenários listados, incluindo os §18: parcela embutida (não duplica), sync realizado≠schedule, última parcela→plano paid, `convert_deferred` (sem duplicar/perder + terminal), Rosa (abatimento=effective uma vez, lease 205 fora da receita), variável-only, fim-de-lease via `is_deleted`.
- [ ] `python -m pytest tests/unit/test_finances/...` (os 4 + regressão `test_bill_generation_service.py`) passa 100%, **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum serializer/viewset/URL/frontend criado; nenhum modelo/serviço de Fase 4/5/6; `core/models.py`/`core/signals.py`/`settings.py` intactos; recorrentes/seed da S37 verdes.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_installment_models.py tests/unit/test_finances/test_employee_model.py \
     tests/unit/test_finances/test_installment_plan_service.py tests/unit/test_finances/test_generation_installments_payroll.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_bill_generation_service.py -q   # regressão geração S37
   ruff check finances/ tests/unit/test_finances/ tests/factories.py
   ruff format --check finances/ tests/unit/test_finances/ tests/factories.py
   mypy core/ finances/
   pyright finances/
   python manage.py makemigrations --check --dry-run
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 41 (status **concluída**) na tabela da feature Condomínio Finance (abre a Fase 3).
   - **Arquivos Criados**: `finances/services/installment_plan_service.py`, `tests/unit/test_finances/{test_installment_models,test_employee_model,test_installment_plan_service,test_generation_installments_payroll}.py`.
   - **Arquivos Modificados**: `finances/models.py` (`InstallmentPlan`/`Installment`/`Employee` + FKs `Bill.installment`/`Bill.employee`/`BillLineItem.installment` + 2 unique parciais), `finances/migrations/000X_installments_employee.py`, `finances/services/bill_generation_service.py` (estende `ensure_month_bills` com avulsa/embutida-dedup/folha/sync/última-parcela), `finances/signals.py` (receivers dos 3 modelos novos), `tests/factories.py` (3 factories).
   - **Nota**: "Fase 3 — parcelas + folha: `InstallmentPlan`/`Installment` (embutido+avulso, dedup, sync schedule→realizado), `convert_deferred` (atômico, sem duplicar/perder, item deferido→CANCELED terminal), `Employee` (variável-only, abatimento §4.6 = effective_rental_value contado uma vez, fim-de-lease via is_deleted). `ensure_month_bills` estendido (ordem: recorrentes→embutidas→avulsas→folha); última parcela→plano paid. `Bill.employee` FK antecipada para a S41 (folha entra na Fase 3 — design §14). **Reserva/income/fechamento=Fase 4 (S47–S49); projeção/simulação=Fase 5; distribuição=Fase 6; API=S42; frontend=S43.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-finance`):
   ```
   feat(finances): add InstallmentPlan/Installment + Employee models + convert_deferred service + extend bill generation with installments and payroll

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **42 — Backend serializers + viewsets + URLs da Fase 3** (`installment-plans/`, `installments/`, `employees/`, `installment-plans/{id}/convert_deferred`) — consome os modelos e serviços desta sessão (chama-os nos `@action`) e o `.with_amounts()` da S36. A S42 **adiciona** a API; **não** recria modelos/serviços. Depois, **43 — frontend** de parcelas/folha.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.models`**: `InstallmentPlan`, `Installment`, `Employee`; enums `InstallmentPlanState` (`active`/`paid`/`deferred`/`canceled`), `EmployeePaymentType` (`fixed`/`variable`/`mixed`). `InstallmentPlan` campos: `condominium`/`building?`/`category?`/`description`/`total_amount`/`installment_count`/`start_due_date`/`default_due_day`/`lifecycle_state`/`embedded`/`linked_billing_account?`/`notes`. `Installment` campos: `plan` (`CASCADE`)/`number`/`due_date`/`amount` (schedule); unique parcial `(plan, number)`. `Employee` campos: `condominium`/`person?` (`SET_NULL`)/`name`/`role`/`payment_type`/`base_salary?`/`default_due_day`/`lease?` (`SET_NULL`)/`is_active`/`notes`.
- **`Bill` FKs de fonte agora completas**: `billing_account` (S36) **+ `installment` + `employee`** (esta sessão, `SET_NULL`); unique parciais `(billing_account, competence_month)` (S36) + `(installment)` + `(employee, competence_month)` (esta sessão). `BillLineItem.installment` (`SET_NULL`) marca a linha de parcela embutida. **S42** serializa esses campos (dual: nested read / `_id` write); **Fase 5** lê `Installment`/`embedded`/`linked_billing_account` para a projeção (dedup futuro).
- **`InstallmentPlanService.convert_deferred(*, deferred_bill, installment_count, start_due_date, default_due_day, category=None, user=None) -> InstallmentPlan`** — atômico; `total_amount == amount_total` do bill; `Σ Installment.amount == total_amount`; item deferido → `CANCELED` (terminal, fora de todas as somas); pré-condição `DEFERRED`. **S42** `installment-plans/{id}/convert_deferred` chama-o.
- **`BillGenerationService.ensure_month_bills(year, month, user=None) -> list[Bill]`** (assinatura inalterada) agora gera **também** parcelas (avulsa → `Bill(installment, behavior=INSTALLMENT)`; embutida → linha `installment=…` no `Bill` recorrente, dedup) e **folha** (`Bill(employee, behavior=RECURRING)` com base + abatimento). Ordem determinística: recorrentes/seed (S37) → embutidas → avulsas → folha. Última parcela materializada → `InstallmentPlan.lifecycle_state=PAID`. **S38** `bills/generate_month` continua chamando o mesmo método (ganha parcelas/folha automaticamente). **Fase 5** consome o `Installment` para a projeção computada.
- **Sync realizado ↔ schedule** (direção fixada): materialização copia `Installment.amount` (schedule) → `BillLineItem.amount` (realizado); edições posteriores do realizado (S42) **não** reescrevem o schedule. **Fase 5** projeta o futuro do `Installment.amount` (schedule); o passado lê o realizado (`BillLineItem.amount`).
- **Abatimento (design §4.6, fixado por teste aqui)**: a folha de `Employee` com `lease` salary-offset tem linha de abatimento `is_offset=True` = `RentScheduleService.effective_rental_value(lease, competence_month)`, **só** enquanto `lease.is_deleted=False`. O aluguel da lease 205 (Rosa) é contado **uma vez** (fora de `collectible_leases`, reduzindo a folha) — **Fase 4/6** (`CondoBalanceService`/`OwnerDistributionService`) confiam nessa invariante.
- **Signals**: escrever em `InstallmentPlan`/`Installment`/`Employee` invalida `finance-*` (via `invalidate_finance_caches()` da S37). **S40/S42** podem confiar que os dashboards `finance-*` são invalidados nessas escritas.
