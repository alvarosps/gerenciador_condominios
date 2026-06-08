# Sessão 44 — Backend modelos: `Reserve`/`ReserveMovement` + `IncomeEntry` + `CondoMonthClose` + migração

> **Feature**: Condomínio Finance (saídas, saldo, reserva e distribuição — `docs/plans/2026-06-06-condominium-finance-design.md`)
> **Sessões da feature**: 34 → 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42 → 43 → **44** → 45 → 46 → … → 50 (esta abre a **Fase 4 — Saldo + Reserva + Receita avulsa + Fechamento**, camada de **modelos**)
> Esta sessão cria os **modelos** da Fase 4: `Reserve` + `ReserveMovement` (depósito/saque, `bill?` vs caixa, ledger determinístico), `IncomeEntry` (receita avulsa), `CondoMonthClose` (âncora leve do fold — `AuditMixin` **sem** SoftDelete; `open`/`closed`; `net_result`/`cash_balance_end`/`reserve_balance_end`/`carry_forward_out`; unique `(condominium, reference_month)`); a **migração** (4 tabelas novas + RLS); as **factories**; e os **testes de modelo** (constraints, `clean()` PT, soft-delete onde aplica, partial-unique, ledger ordenado, sinal de movimento). **Sem `CondoBalanceService`/saldo/`received_collectible_total`/`CondoMonthCloseService` (S45); sem serializers/viewsets/URLs (parte da S45/dashboard); sem frontend (S46).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.2, §4.3, §4.5, §4.7, §4.8, §5.2 blocos "Pagamentos / reserva / receita" e "Fechamento (âncora leve)", §7 mapeamento (Reserva/Empréstimo/Receita avulsa), §13 migrações, §14 Fase 4, §18 edge-cases "Reserva" + "Fold/fechamento")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| `SoftDeleteManager` (manager duplo) | `core/models.py:41-58` (`get_queryset` filtra `is_deleted=False`; `with_deleted` :52-54; `deleted_only` :56-58) | **Reusar** este manager do `core` (import direto), NÃO recriar. Base do `objects` de `Reserve`/`ReserveMovement`/`IncomeEntry` (que têm SoftDelete) |
| `AuditMixin` | `core/models.py:61-108` (`save()` atualiza `updated_at` :104-108) | Mixin abstrato herdado por **TODOS** os 4 modelos desta sessão (inclusive `CondoMonthClose`) |
| `SoftDeleteMixin` | `core/models.py:111-190` (`delete()` soft :149-173; `restore()` :175-190) | Herdado por `Reserve`/`ReserveMovement`/`IncomeEntry`; **NÃO** por `CondoMonthClose` (design §5.2 — só `AuditMixin`) |
| **Model `AuditMixin` SEM SoftDelete + unique `(parent, reference_month)` (sem condição)** | `core/models.py:1389-1410` (`ExpenseMonthSkip`: `(AuditMixin, models.Model)` :1389; `reference_month` 1º dia :1397-1399; `UniqueConstraint(fields=["expense","reference_month"])` **sem** `condition` :1402-1406; `__str__` PT :1409-1410) | **Exemplar canônico** do `CondoMonthClose` (sem SoftDelete) — só `AuditMixin`, manager simples `models.Manager()`, unique **sem** `condition=Q(is_deleted=False)` (não há `is_deleted`). Espelhar a forma da unique e `reference_month` dia 1 |
| **Model financeiro `reference_month` (1º dia) + valores `Decimal` + `CheckConstraint(amount>0)` + `clean()` PT** | `core/models.py:1321-1351` (`PersonPayment`: `reference_month` help "primeiro dia do mês" :1323-1325; `amount` :1326; `CheckConstraint(amount__gt=0)` :1339-1342; `clean()` PT :1348-1351) | Forma de `IncomeEntry.amount`/`ReserveMovement.amount` (`> 0`) e da normalização de `reference_month`/`income_date` |
| **Model com FKs nulláveis `SET_NULL` + managers duplos + `CheckConstraint(>=0)` + `clean()` PT + cascade soft-delete** | `core/models.py:1032-1147` (`Expense`: FKs `SET_NULL` :1037-1048; managers duplos :1074-1075; `CheckConstraint(total_amount__gte=0)` :1098-1106; `clean()` PT :1111-1114; **cascade soft-delete** no `delete()` :1116-1136 e `restore()` :1138-1147) | **Referência** do `ReserveMovement.bill` (`SET_NULL` — apagar o bill não apaga o movimento) e de `IncomeEntry.building`/`category` (`SET_NULL`). O cascade soft-delete só é relevante se houver filhos (não há nesta sessão) |
| **Model filho `CASCADE` + ordering + `__str__`** | `core/models.py:1150-1186` (`ExpenseInstallment`: FK `expense` `CASCADE` :1151; `Meta.ordering` :1164; `__str__` :1185-1186) | Forma de `ReserveMovement` (filho `CASCADE` do `Reserve`). **Ledger determinístico**: `Meta.ordering = ["movement_date", "id"]` (design §4.3) |
| **partial unique `condition=Q(is_deleted=False)` + `CheckConstraint`** | `core/models.py:1253-1265` (`RentPayment.Meta`: `UniqueConstraint(condition=Q(is_deleted=False))` :1256-1260; `CheckConstraint(amount_paid__gt=0)` :1261-1264) | Forma das check-constraints `> 0` de `ReserveMovement`/`IncomeEntry`. **`CondoMonthClose` NÃO usa esse padrão** (sem `is_deleted` → unique simples como `ExpenseMonthSkip`) |
| **`FinancialSettings` (baseline do caixa — só LEITURA, não tocar)** | `core/models.py:1413-1443` (`initial_balance` :1414; `initial_balance_date` :1415; `rent_tracking_start_date` :1423-1430) | `CondoMonthClose.cash_balance_end` é a **semente** do caixa do próximo mês (design §4.2); a S45 lê `FinancialSettings.initial_balance` quando não há fechado. Esta sessão **só** modela o campo `cash_balance_end`; **não** computa baseline (S45) |
| **Baseline "re-anda só a cauda aberta" (espelho condo-scoped — só LER, S45 usa)** | `core/services/daily_control_service.py:183-` (`_get_starting_balance(month_start) -> Decimal` :184) | Design §4.2: o caixa condo-scoped espelha esta técnica, **ancorado em `CondoMonthClose`**. **Esta sessão não implementa o service** — só cita para alinhar a semântica do campo `cash_balance_end` |
| Migração com RLS (`RunSQL`/`reverse_sql`) | `core/migrations/0047_enable_row_level_security.py:16-134` (`ENABLE_RLS`/`DISABLE_RLS` :16-124; `dependencies` :128-130; `RunSQL(sql=…, reverse_sql=…)` :132-134) | **Obrigatório** (`.claude/rules/database.md`): as 4 tabelas novas habilitam RLS na **mesma** migração. Espelhar este padrão |
| **Factories `make_<model>()` (estilo `**kwargs`/`defaults`/`baker.make`)** | `tests/factories.py:34-54` (`make_building` :34; `make_apartment` :43) + factories `finances` da S36 (`make_bill`, `make_payment`) e `make_condominium`/`make_building(condominium=…)` (S34) | **Espelhar** o estilo: função módulo-nível, `defaults` dict, `user` opcional → `created_by`/`updated_by`, `baker.make("finances.<Model>", **defaults)`. Adicionar `make_reserve`, `make_reserve_movement`, `make_income_entry`, `make_condo_month_close` |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` para tempo) | Aqui = **nada** a mockar (modelos não calculam "hoje"); `transaction.atomic()` ao asserir `IntegrityError`. ORM real (`--reuse-db`) |

### O que a S34/S36 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S34** (infra): app `finances/` em `INSTALLED_APPS`, `finances/apps.py` com `FinancesConfig.ready()` importando `finances/signals.py`, `finances/__init__.py`; **`core.Condominium`**(padrão) + data-migration do registro padrão + **`Building.condominium`** FK (faseada); helper TZ único `America/Sao_Paulo` (localização exata definida pela S34 — ex.: `finances/services/timezone.py` com `today_sp()`/`current_month_sp()`/`SAO_PAULO_TZ`); **gate ampliado** (`finances` em `--cov`/`[tool.coverage.run] source`/`pyproject [project]`, `mypy core/` → `mypy core/ finances/`, `pyrightconfig.json include`); factories base `make_condominium()` + `make_building(condominium=…)` (default ao condomínio-padrão).
- **S36** (modelos núcleo): `Category`, `BillingAccount`, `Bill`, `BillLineItem`, `BillSkip`, `Payment`, `PaymentAllocation`; enums `BillBehavior`/`BillLifecycleState`/`BillingAccountState`/**`FundedFrom` (`caixa`/`reserve`)**; `Bill.objects.with_amounts(today)` (annotations); migração inicial do `finances` + RLS; 7 factories. **A FK `ReserveMovement.bill` desta sessão aponta para o `Bill` da S36** (`SET_NULL`).

> **Esta sessão depende apenas da S36** (modelos núcleo — `Bill`, `Condominium`, mixins, `FundedFrom`). DEPENDENCY ORDER: **44 depende de 36**. Não recriar `Bill`/`Condominium`/app/infra/`FundedFrom` aqui. **Se a S34/S36 não estiverem concluídas, PARE.**

> **NOTA de roadmap (resolver ambiguidade S36↔S41):** o docstring do `Bill` (S36) reservava "`employee` FK = S44". A **S41 já antecipou** `Employee` + `Bill.employee` para a Fase 3 (folha entra na geração lá). Portanto **esta S44 NÃO cria `Employee` nem `Bill.employee`** — ela é a sessão de **modelos da Fase 4 (Reserve/Income/Close)**, conforme a tarefa canônica e o design §14 Fase 4. Se o docstring do `Bill` ainda disser "S44" para `employee`, é resíduo já reconciliado pela S41 — **não** mexer em `Bill` nesta sessão.

---

## Escopo

### Arquivos a criar
- `tests/unit/test_finances/test_reserve_models.py` — testes de `Reserve`/`ReserveMovement` (herança/managers, `kind`, `bill?` vs caixa, `CheckConstraint amount > 0`, `clean()` PT, soft-delete, **ledger determinístico** `ORDER BY (movement_date, id)`).
- `tests/unit/test_finances/test_income_entry_model.py` — testes de `IncomeEntry` (campos, `is_received`/`received_date`, `amount > 0`, `clean()` PT, soft-delete, `building?`/`category?` `SET_NULL`).
- `tests/unit/test_finances/test_condo_month_close_model.py` — testes de `CondoMonthClose` (`AuditMixin` **sem** `is_deleted`, `status` open/closed, unique `(condominium, reference_month)` **sem** condição, `carry_forward_out <= 0`, `reference_month` dia 1, `breakdown` JSON, `__str__` PT).

### Arquivos a modificar
- `finances/models.py` — **adicionar** `Reserve`, `ReserveMovement`, `IncomeEntry`, `CondoMonthClose` + os enums `ReserveMovementKind`, `CondoMonthCloseStatus`. Imports/modelos existentes (S36 e, se já presentes, S41) **intactos**; **não** alterar `Bill`/`BillLineItem`/`Payment`.
- `finances/migrations/000X_reserve_income_close.py` — gerada por `makemigrations finances`: `CreateModel` de `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` **e** `RunSQL` de RLS (ENABLE/DISABLE) para as **4 tabelas novas** (`finances_reserve`, `finances_reservemovement`, `finances_incomeentry`, `finances_condomonthclose`). Depende do head atual do `finances` (S43).
- `finances/signals.py` — **adicionar** receivers `post_save`/`post_delete` para `Reserve`, `ReserveMovement`, `IncomeEntry`, `CondoMonthClose` → `invalidate_finance_caches()` (mesma fonte de prefixos `finance-*` criada na S37). **Não** recriar o módulo nem os receivers existentes.
- `tests/factories.py` — adicionar `make_reserve`, `make_reserve_movement`, `make_income_entry`, `make_condo_month_close` (estilo `tests/factories.py:34-54`). Imports e factories existentes **intactos**.

### NÃO fazer (pertence a outras sessões)
- **Nenhum serviço** — `CondoBalanceService` (resultado de competência, variação de caixa, **caixa condo-scoped ancorado**, reserva, saldo total, atrasados, wedge), `CondoMonthCloseService` (`close`/`reopen`), `IncomeEntry` recebida no caixa, **guarda de saldo de reserva no `pay(funded_from=reserve)`** e `RentScheduleService.received_collectible_total` são da **Sessão 45**. Esta sessão entrega **só os modelos** + a **guarda estrutural no `clean()`/CheckConstraint do `ReserveMovement`** (saque ≤ saldo é regra de **serviço** — S45; o `clean()` aqui só valida sinal/positividade, **não** consulta o saldo agregado). **Decisão pinada abaixo.**
- **Nenhum serializer, viewset, URL ou ação de API** (`reserves/`, `reserve-movements/`, `income-entries/`, `condo-month-closes/`, `reserves/{id}/deposit|withdraw`, `condo-month-closes/{close,reopen}`) — é a **Sessão 45** (API da Fase 4).
- **Nenhum frontend** (hooks/pages/schemas/KPIs Caixa/Reserva/Resultado/Atrasados/Saldo total) — é a **Sessão 46**.
- **Nenhuma alteração de `Bill`/`BillLineItem`/`Payment`** — `Payment.funded_from='reserve'` já existe (S36) e continua **só persistido** até a S45 criar o `ReserveMovement(withdrawal, bill=…)` correspondente no `pay()`. **Não** alterar `BillPaymentService.pay` aqui.
- **Sem `OwnerDistributionService`/fold/carry-forward computado** (Fase 6, S49/S50). Esta sessão só modela o **campo** `carry_forward_out` (com `CheckConstraint <= 0`); o **algoritmo** do fold é de fases posteriores.
- **Sem `CondoProjectionService`/`CondoSimulationService`** (Fase 5). Sem tocar `core/models.py`, `core/signals.py`, `condominios_manager/settings.py`. Sem `django-money`/`django-treebeard`. Sem seed de dados (design §13).

---

## Especificação

> Convenções (design §5.2): `(AuditMixin, SoftDeleteMixin, models.Model)` + managers duplos (`all_objects = models.Manager()`, `objects = SoftDeleteManager()` do `core`), **EXCETO `CondoMonthClose`** (`(AuditMixin, models.Model)`, manager simples `objects = models.Manager()`, **sem** SoftDelete — design §5.2). `DecimalField(max_digits=12, decimal_places=2)`, partial unique `condition=Q(is_deleted=False)` (nos modelos com SoftDelete), `CheckConstraint amount > 0`/`>= 0` conforme campo, `clean()` em PT, `on_delete` `PROTECT` em FKs de referência / `CASCADE` em filhos / `SET_NULL` onde indicado. `condominium` FK em todo modelo de topo (escopo multi-condomínio futuro — design §6). Mensagens ao usuário em **PT**, logs/identificadores/enum values em **EN**.

### Decisão pinada — guarda de saldo negativo da reserva é do SERVIÇO (S45), não do model

Design §4.3 exige **rejeitar saque/`funded_from=reserve` que exceda o saldo da reserva** (reserva nunca negativa). Esse saldo é um **agregado do ledger** (`Σ depósitos − Σ saques`), que só faz sentido computar num **serviço** (`CondoBalanceService`/`BillPaymentService.pay`, S45) — um `clean()` de model **não** deve consultar agregados de outras linhas (acopla validação a estado global, viola SRP/`.claude/rules/architecture.md` "models = dados + validação só"). Portanto:

- **Nesta sessão**, o `ReserveMovement` garante apenas: `kind ∈ {deposit, withdrawal}`, `amount > 0` (CheckConstraint + `clean()` PT), `movement_date` presente, `bill` opcional. **Não** valida "saque ≤ saldo".
- **A guarda agregada "saque ≤ saldo da reserva" é da S45** (no `CondoBalanceService.reserve_balance` + checagem em `ReserveService.withdraw`/`BillPaymentService.pay(funded_from=reserve)`). **Documentar isto** no docstring de `ReserveMovement` e nos contratos cross-session (a S45 implementa a guarda; o teste de "saque > saldo rejeitado" do §18 "Reserva" pertence à **S45**, não a esta). Esta sessão **trava por teste** apenas a positividade e o sinal.

### Enums (em `finances/models.py`)

```python
class ReserveMovementKind(models.TextChoices):
    DEPOSIT = "deposit", "Depósito"
    WITHDRAWAL = "withdrawal", "Saque"


class CondoMonthCloseStatus(models.TextChoices):
    OPEN = "open", "Aberto"
    CLOSED = "closed", "Fechado"
```

> `ReserveMovementKind` é o **sinal** do movimento (depósito soma, saque subtrai — design §4.3). `CondoMonthCloseStatus` é distinto de `BillLifecycleState`/`InstallmentPlanState` (não reusar — semântica diferente). `FundedFrom` (S36) **não** é redefinido aqui.

### Modelos (assinaturas de campo conforme design §5.2)

```python
# finances/models.py — ANEXAR (imports diretos; sem TYPE_CHECKING, sem __future__)
# já importados pela S36: Decimal, date, ValidationError, models, Q/Sum/.../Coalesce,
# AuditMixin, SoftDeleteMixin, SoftDeleteManager, Building, Condominium, Bill.
# (Bill já está definido neste módulo — usar referência direta ou string "Bill".)

class Reserve(AuditMixin, SoftDeleteMixin, models.Model):
    """Reserva (poupança do condomínio). Uma por condomínio na UI; modelo permite N (sem seletor agora — YAGNI).
    Saldo = Σ(ReserveMovement depósitos − saques) — DERIVADO no serviço S45 (NUNCA property/annotation aqui)."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="reserves")
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # __str__ PT (ex.: f"Reserva {self.name}")


class ReserveMovement(AuditMixin, SoftDeleteMixin, models.Model):
    """Movimento do ledger único da reserva. bill setado = saque p/ pagar conta;
    bill=null = transferência caixa↔reserva. amount armazenado POSITIVO; o SINAL vem de `kind`.
    Guarda 'saque <= saldo' é do SERVIÇO (S45), NÃO deste model (design §4.3 + Decisão pinada)."""
    reserve = models.ForeignKey(Reserve, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=10, choices=ReserveMovementKind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    movement_date = models.DateField()
    bill = models.ForeignKey(Bill, null=True, blank=True, on_delete=models.SET_NULL, related_name="reserve_movements")
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # Meta: ordering = ["movement_date", "id"] (LEDGER DETERMINÍSTICO — design §4.3);
    #       CheckConstraint amount > 0. clean() PT: amount > 0.
    # NOTA: amount_paid do Bill deriva SÓ de PaymentAllocation (S36 with_amounts) — JAMAIS de ReserveMovement.bill
    #       (design §4.3 — bill aqui é só o vínculo do saque; não conta como pagamento).


class IncomeEntry(AuditMixin, SoftDeleteMixin, models.Model):
    """Receita avulsa do condomínio (proventos de empréstimo, etc. — design §7).
    is_received=True conta no caixa (entradas_caixa, S45). NÃO recorrente (YAGNI — design §15)."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="income_entries")
    building = models.ForeignKey(Building, null=True, blank=True, on_delete=models.SET_NULL, related_name="income_entries")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="income_entries")
    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    income_date = models.DateField()
    is_received = models.BooleanField(default=False)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    all_objects = models.Manager()
    objects = SoftDeleteManager()
    # Meta: ordering = ["-income_date"]; CheckConstraint amount > 0.
    # clean() PT: amount > 0; is_received=True ⇒ received_date obrigatório; is_received=False ⇒ received_date deve ser None.


class CondoMonthClose(AuditMixin, models.Model):
    """Âncora LEVE e condo-scoped do fold/caixa + auditoria (design §3.2/§5.2). SEM SoftDelete (só AuditMixin).
    Congela net/caixa/reserva/carry_forward_out do mês FECHADO; semeia o caixa/fold do próximo mês (S45).
    NÃO trava aluguel (rent-lock = MonthSnapshot legado). reference_month = 1º dia."""
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="month_closes")
    reference_month = models.DateField(help_text="Primeiro dia do mês de referência (ex: 2026-06-01)")
    status = models.CharField(max_length=10, choices=CondoMonthCloseStatus.choices, default=CondoMonthCloseStatus.OPEN)
    closed_at = models.DateTimeField(null=True, blank=True)
    net_result = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    cash_balance_end = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    reserve_balance_end = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    carry_forward_out = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))  # <= 0 (design §4.7)
    breakdown = models.JSONField(default=dict, blank=True)  # mínimo p/ exibição (S45/S46)
    objects = models.Manager()  # SEM SoftDeleteManager (não há is_deleted)
    # Meta: UniqueConstraint(fields=["condominium", "reference_month"], name="unique_condo_month_close") — SEM condition;
    #       ordering = ["-reference_month"]; CheckConstraint carry_forward_out <= 0.
    # clean() PT: normaliza reference_month p/ dia 1; status=closed ⇒ closed_at obrigatório (S45 seta no close);
    #            carry_forward_out <= 0.
```

> `Bill`/`Category`/`Building`/`Condominium` já estão no módulo (S36). `JSONField` é `django.db.models.JSONField` (já há `import` de `models`). **`reserve_balance_end`/`cash_balance_end` podem ser negativos?** Caixa pode ficar negativo (aviso informativo, não bloqueio — design §4.3) → **sem** CheckConstraint `>= 0` neles. `reserve_balance_end` em tese nunca negativo (guarda do serviço S45), mas a **integridade é do serviço**, não do snapshot — **sem** CheckConstraint aqui (o snapshot só registra o que o serviço calculou). **`carry_forward_out <= 0`** é estrutural (design §4.7: `carregado_out = min(0, …)`) → **com** CheckConstraint.

### Normalização de datas para o 1º dia (DRY)

`CondoMonthClose.reference_month` é normalizado para o dia 1 no `clean()`, espelhando `Bill.clean()` (S36) e `ExpenseMonthSkip`/`PersonPayment` (1º dia do mês). **Se a S36 extraiu um helper** de normalização (ex.: `_first_day(d: date) -> date` em `finances/models.py`), **reusar** (import direto, sem re-export). Se não houver, criar um helper **privado** módulo-nível (`def _first_of_month(value: date) -> date: return value.replace(day=1)`) e usá-lo em `CondoMonthClose.clean()` — **uma** definição, sem duplicar a expressão `replace(day=1)` espalhada. `IncomeEntry.income_date`/`received_date` e `ReserveMovement.movement_date` são datas **reais** (NÃO normalizadas para dia 1 — são eventos de caixa).

### Ledger determinístico (design §4.3 — CRÍTICO)

`ReserveMovement.Meta.ordering = ["movement_date", "id"]`. O saldo da reserva (S45) re-anda o ledger nessa ordem; empates de `movement_date` resolvem por `id` (ordem de inserção) → **determinístico**. Esta sessão **trava por teste** que `Reserve.movements.all()` (e `ReserveMovement.objects.filter(reserve=…)`) retornam na ordem `(movement_date, id)` — incluindo o caso de mesma `movement_date` com `id` crescente. O **cálculo** do saldo é da S45; aqui só a **ordem** é garantida.

### Signals dos modelos novos (invalidação `finance-*`)

A S37 criou `finances/signals.py` com receivers `post_save`/`post_delete` chamando `invalidate_finance_caches()` (fonte única dos prefixos `finance-dashboard`/`finance-cash-flow`/`finance-projection` — design §11). **Adicionar** receivers análogos para `Reserve`, `ReserveMovement`, `IncomeEntry`, `CondoMonthClose` (mesmo idioma, import direto de `finances.models`/`finances.cache`; soft-delete dispara `post_save` nos 3 com SoftDelete; `CondoMonthClose` é hard delete → `post_delete`). Isso mantém os dashboards `finance-*` consistentes quando reserva/receita/fechamento mudam. **Não** tocar `core/signals.py` (cross-app já coberto pela S37). **Não** cachear nada nesta sessão (sem `@cache_result` em modelos) — só a invalidação via signal.

### RLS na mesma migração (design §13 + `.claude/rules/database.md`)

A migração desta sessão DEVE incluir `migrations.RunSQL(sql=ENABLE_RLS, reverse_sql=DISABLE_RLS)` habilitando RLS nas **4 tabelas novas** — espelhando `core/migrations/0047_enable_row_level_security.py:16-134`. Tabelas (nomes Django default): `finances_reserve`, `finances_reservemovement`, `finances_incomeentry`, `finances_condomonthclose`. `ENABLE ROW LEVEL SECURITY` é idempotente. `dependencies` da migração: o **head atual do `finances`** (S43) — `makemigrations` resolve.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. Aqui = **nada** a mockar (modelos não calculam "hoje"; sem tempo a congelar — usar `date(...)` explícito; `freeze_time` só se conveniente para `AuditMixin.created_at`). **NUNCA** mockar ORM, managers, `SoftDeleteManager`, signals ou `invalidate_finance_caches`. Banco real via `--reuse-db`; `transaction.atomic()` ao asserir `IntegrityError`. Dados via factories (`model-bakery`). `filterwarnings=error`: zero warnings. **Backup antes do migrate** (`.claude/rules/database.md`): `python scripts/backup_db.py` (a migração cria 4 tabelas + RLS; criar é menos arriscado que dropar, mas a regra backup-antes-de-migrate é primária).

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_reserve_models.py`
- [ ] `Reserve` e `ReserveMovement` herdam `AuditMixin` (`created_at`/`updated_at` não-nulos) **e** `SoftDeleteMixin` (`is_deleted=False` default); `objects` exclui soft-deleted, `all_objects.with_deleted()` inclui.
- [ ] `condominium` FK presente em `Reserve`; `reserve` FK `CASCADE` em `ReserveMovement` (hard-delete do `Reserve` leva os movimentos — smoke; soft-delete do `Reserve` segue o mixin).
- [ ] `ReserveMovement.kind` choices `{deposit, withdrawal}`; default ausente (campo obrigatório).
- [ ] **`amount > 0`**: `amount=0` ou negativo → `IntegrityError` (CheckConstraint `amount > 0`) **e** `clean()` PT rejeita (`ValidationError` PT). `amount` positivo OK.
- [ ] **`bill` opcional (vs caixa)**: `ReserveMovement(bill=<Bill>)` (saque p/ conta) e `ReserveMovement(bill=None)` (transferência caixa↔reserva) ambos válidos e **distinguíveis** (`bill_id is None` vs setado — design §4.3 "bill=null vs bill setado distintos").
- [ ] **`bill` `SET_NULL`**: hard-delete do `Bill` → `ReserveMovement.bill` vira `None` (FK `SET_NULL` — apagar a conta não apaga o movimento do ledger). Soft-delete do `Bill` **NÃO** dispara `SET_NULL` (a FK continua apontando; `bill.is_deleted=True`) — provar `mov.bill_id is not None` após soft-delete.
- [ ] **ledger determinístico (design §4.3 + §18 "ordenação determinística")**: criar movimentos fora de ordem de data **e** dois com a **mesma** `movement_date` em ordem de inserção; `Reserve.movements.all()` (e `ReserveMovement.objects.filter(reserve=…)`) retornam ordenados por `(movement_date, id)` — asserir a sequência exata de `pk`/`movement_date`.
- [ ] `__str__` PT coerente (smoke) para `Reserve` e `ReserveMovement`.
- [ ] **(documentar/comentar no teste)**: a guarda "saque > saldo rejeitado" **NÃO** é testada aqui — é da S45 (Decisão pinada). Este arquivo cobre só sinal/positividade/ordem.

#### `tests/unit/test_finances/test_income_entry_model.py`
- [ ] `IncomeEntry` herda `AuditMixin` + `SoftDeleteMixin`; managers duplos (`objects` exclui soft-deleted; `all_objects.with_deleted()` inclui).
- [ ] `condominium` FK presente; `building`/`category` **opcionais** e `SET_NULL` (hard-delete do `Building`/`Category` → campo vira `None`, a receita sobrevive).
- [ ] **`amount > 0`**: `amount=0`/negativo → `IntegrityError` (CheckConstraint) **e** `clean()` PT.
- [ ] **`is_received`/`received_date` consistência (`clean()` PT)**: `is_received=True` **sem** `received_date` → `ValidationError` PT; `is_received=False` **com** `received_date` setado → `ValidationError` PT; `is_received=True` **com** `received_date` → OK; `is_received=False` **sem** `received_date` → OK.
- [ ] `Meta.ordering = ["-income_date"]` (smoke: dois entries, mais recente primeiro).
- [ ] `__str__` PT coerente (smoke).

#### `tests/unit/test_finances/test_condo_month_close_model.py`
- [ ] `CondoMonthClose` herda `AuditMixin` (`created_at`/`updated_at` não-nulos) **e NÃO** tem `is_deleted`/`SoftDeleteMixin` (asserir `not hasattr(instance, "is_deleted")` **ou** que `CondoMonthClose` não está em `SoftDeleteMixin.__subclasses__()` da forma idiomática — espelha o teste de `WebPushSubscription`/`ExpenseMonthSkip`). `objects` é `models.Manager` simples (**sem** `with_deleted`).
- [ ] `status` choices `{open, closed}`; default `OPEN`.
- [ ] **unique `(condominium, reference_month)` SEM condição**: dois `CondoMonthClose` com mesmo `(condominium, reference_month)` → `IntegrityError`; como **não há soft-delete**, **hard delete** do primeiro libera o slot (criar de novo OK — espelha `ExpenseMonthSkip`). Mesmo `reference_month` para **condomínio diferente** → OK.
- [ ] **`reference_month` normalizado para dia 1** no `clean()` (passar `2026-06-15` → salvar via `full_clean()` → `reference_month.day == 1`).
- [ ] **`carry_forward_out <= 0`**: `carry_forward_out = 50` (positivo) → `IntegrityError` (CheckConstraint `<= 0`) **e**/ou `clean()` PT; `0` e valores negativos OK (design §4.7 `carregado_out = min(0, …)`).
- [ ] **`status=closed` ⇒ `closed_at` obrigatório** (`clean()` PT): `status=closed` sem `closed_at` → `ValidationError` PT; `status=open` sem `closed_at` → OK.
- [ ] `net_result`/`cash_balance_end`/`reserve_balance_end` aceitam **negativos** (sem CheckConstraint — caixa/net podem ser negativos; design §4.2/§4.3). Asserir que salvar `cash_balance_end = -100` é permitido.
- [ ] `breakdown` JSONField default `{}` (vazio) e aceita dict arbitrário (smoke).
- [ ] `__str__` PT coerente (smoke, ex.: mês/ano + status).

> Rodar (devem **falhar** — modelos/enums/migração ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_reserve_models.py tests/unit/test_finances/test_income_entry_model.py tests/unit/test_finances/test_condo_month_close_model.py -q
> ```

### 2. GREEN — implementar modelos + migração + factories + signals

1. `finances/models.py` — **anexar** `ReserveMovementKind`/`CondoMonthCloseStatus`, `Reserve`, `ReserveMovement`, `IncomeEntry`, `CondoMonthClose` conforme a Especificação. Importar mixins/manager de `core.models` (já importados pela S36); `Bill`/`Category`/`Building`/`Condominium` já no módulo. **Sem** alterar `Bill`/`Payment`. Reusar/criar o helper de normalização de 1º dia (DRY — ver §"Normalização de datas").
2. `tests/factories.py` — `make_reserve(condominium=None, …)`, `make_reserve_movement(reserve=None, kind="deposit", amount=Decimal("100.00"), movement_date=date(...), bill=None, …)`, `make_income_entry(condominium=None, amount=Decimal("100.00"), …)`, `make_condo_month_close(condominium=None, reference_month=date(…,1), status="open", …)` (estilo `:34-54`; `user` opcional → `created_by`/`updated_by`).
3. Migração:
   ```bash
   python scripts/backup_db.py                       # backup ANTES (regra database.md)
   python manage.py makemigrations finances
   # completar a migração recém-gerada (antes do 1º commit) com a RunSQL de RLS (ENABLE/DISABLE) das 4
   # tabelas novas: finances_reserve, finances_reservemovement, finances_incomeentry, finances_condomonthclose — espelhar 0047
   python manage.py migrate finances
   python manage.py makemigrations --check --dry-run # "No changes detected"
   ```
4. `finances/signals.py` — receivers `post_save`/`post_delete` para `Reserve`/`ReserveMovement`/`IncomeEntry`/`CondoMonthClose` → `invalidate_finance_caches()` (import direto; mesma forma dos receivers da S37).

> **Nota sobre editar a migração recém-gerada**: o hook bloqueia edição de migrations **existentes**; a recém-gerada ainda não foi commitada — anexar a `RunSQL` de RLS na operação é parte da criação (mesmo padrão de `0047`). Não fragmentar em migração separada.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_reserve_models.py tests/unit/test_finances/test_income_entry_model.py tests/unit/test_finances/test_condo_month_close_model.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Normalização "1º dia do mês" via **um** helper (reusar o da S36 se existir; senão `_first_of_month`) — **sem** repetir `replace(day=1)` em vários `clean()`. Direção de uso: `CondoMonthClose.clean()`.
- Mensagens PT como constantes nomeadas se repetidas (sem magic strings) — ex.: `_ERR_AMOUNT_POSITIVE`, `_ERR_CLOSED_NEEDS_DATE`, `_ERR_RECEIVED_DATE`.
- Confirmar que **nenhum** model calcula saldo/agregado (sem `@property` de saldo em `Reserve`; sem annotation de saldo) — o saldo é **derivado no serviço S45** (design §4.3). Travar essa ausência por revisão (não há property/annotation de saldo nesta sessão).
- `invalidate_finance_caches()` continua a **única** fonte dos prefixos (S37); os receivers novos chamam-na (não repetem `invalidate_pattern` nem o glob).
- `ReserveMovement.Meta.ordering` é `["movement_date", "id"]` (uma definição; o serviço S45 não re-define a ordem — herda do model).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_reserve_models.py tests/unit/test_finances/test_income_entry_model.py \
  tests/unit/test_finances/test_condo_month_close_model.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/models.py finances/signals.py tests/unit/test_finances/ tests/factories.py
ruff format --check finances/models.py finances/signals.py tests/unit/test_finances/ tests/factories.py
mypy core/ finances/
pyright finances/models.py finances/signals.py
```

Forward/backward da migração (design §13):
```bash
python manage.py migrate finances              # forward
python manage.py migrate finances <prev_head>  # backward até antes desta migração (DISABLE_RLS roda; 4 tabelas dropadas)
python manage.py migrate finances              # re-forward (idempotente)
```

> **Regressão obrigatória** (não quebrar o que já existe no `finances`): rodar os testes de modelo da S36 (e S41 se presentes) para garantir que `Bill`/signals continuam verdes:
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_models.py tests/unit/test_finances/test_bill_annotations.py -q
> ```

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). `finances/models.py` importa de `core.models` (mixins/manager/`Building`/`Condominium`) — **nunca** o contrário; **nunca** importar views/serializers/services.
- **Modelos = dados + validação só** (`.claude/rules/architecture.md`): `clean()` valida sinal/consistência de campos do **próprio** registro; **zero** lógica de negócio/agregado no model (saldo da reserva, baseline do caixa, fold = serviços S45). `clean()` **não** consulta agregados de outras linhas (guarda de saldo é do serviço — Decisão pinada).
- **`CondoMonthClose` SEM SoftDelete** (design §5.2): só `AuditMixin`, manager simples, unique **sem** `condition=Q(is_deleted=False)`. **Não** herdar `SoftDeleteMixin`.
- **Ledger determinístico** (design §4.3): `ReserveMovement.Meta.ordering = ["movement_date", "id"]`. `amount` positivo; o sinal vem de `kind`.
- **`carry_forward_out <= 0`** (design §4.7) via CheckConstraint; `amount > 0` em `ReserveMovement`/`IncomeEntry` via CheckConstraint + `clean()` PT.
- **`amount_paid` do `Bill` jamais deriva de `ReserveMovement.bill`** (design §4.3) — o vínculo `bill` é só o saque; o pagamento é `PaymentAllocation` (S36). **Não** adicionar `ReserveMovement` à annotation `with_amounts` (não tocar `Bill`).
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código de verdade. Tipos completos (mypy strict + pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo — `.claude/rules/coding-standards.md`); importar tipos diretamente.
- **Sem re-exports / barrel files / shims**: `finances/models.py` exporta só o que define; importa mixins direto de `core.models`.
- **Sem serviço/serializer/viewset/URL/cache(`@cache_result`)/frontend** (S45/S46). **Sem** `CondoBalanceService`/`received_collectible_total`/guarda de saldo/`close`/`reopen`. **Sem** tocar `Bill`/`Payment`/`BillPaymentService`.
- **RLS na mesma migração** (`.claude/rules/database.md`) para as 4 tabelas; `RunSQL` com `reverse_sql`. **Backup antes do migrate**; migração testada forward **e** backward.
- **`DecimalField(12,2)`** em todo dinheiro; quantização só na fronteira (não no model). `reference_month` (CondoMonthClose) normalizado para dia 1; `income_date`/`received_date`/`movement_date` são datas reais (não normalizadas).
- Mensagens de erro ao usuário em **Português**; logs/identificadores/enum values em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `finances/models.py` define `Reserve`, `ReserveMovement`, `IncomeEntry`, `CondoMonthClose` + enums `ReserveMovementKind` (`deposit`/`withdrawal`) e `CondoMonthCloseStatus` (`open`/`closed`), importando mixins/manager de `core.models` (sem re-export); `Bill`/`Category`/`Payment` **intactos**.
- [ ] `Reserve`/`ReserveMovement`/`IncomeEntry` são `(AuditMixin, SoftDeleteMixin, models.Model)` com managers duplos; **`CondoMonthClose` é `(AuditMixin, models.Model)`** com manager simples e **sem** `is_deleted`.
- [ ] `ReserveMovement`: `kind` enum; `amount > 0` (CheckConstraint + `clean()` PT); `bill` opcional `SET_NULL` (saque p/ conta vs `bill=null` transferência — distinguíveis); **`Meta.ordering = ["movement_date", "id"]`** (ledger determinístico) com teste provando a ordem incl. empate de data por `id`.
- [ ] `IncomeEntry`: `amount > 0`; `building`/`category` `SET_NULL`; consistência `is_received`⇔`received_date` no `clean()` PT (ambos sentidos); `Meta.ordering = ["-income_date"]`.
- [ ] `CondoMonthClose`: unique `(condominium, reference_month)` **sem** condição (hard delete libera o slot; condomínio diferente OK); `reference_month` normalizado p/ dia 1; **`carry_forward_out <= 0`** (CheckConstraint); `status=closed ⇒ closed_at` obrigatório (`clean()` PT); `net_result`/`cash_balance_end`/`reserve_balance_end` aceitam negativos; `breakdown` JSON default `{}`.
- [ ] **`amount_paid` do `Bill` não referencia `ReserveMovement`** (design §4.3) — `Bill` não foi tocado; a guarda "saque ≤ saldo" é **explicitamente** deixada para a S45 (documentada no docstring de `ReserveMovement`).
- [ ] Migração do `finances` gerada (depende do head da S43), inclui `RunSQL` de RLS (ENABLE/DISABLE) para as **4 tabelas novas**; `makemigrations --check --dry-run` → "No changes detected"; forward/backward OK.
- [ ] `finances/signals.py` ganha receivers `post_save`/`post_delete` para os 4 modelos novos → `invalidate_finance_caches()` (fonte única dos prefixos; sem `invalidate_pattern` repetido); receivers da S37/S41 **intactos**.
- [ ] Factories `make_reserve`/`make_reserve_movement`/`make_income_entry`/`make_condo_month_close` em `tests/factories.py` (estilo existente).
- [ ] `tests/unit/test_finances/test_reserve_models.py` + `test_income_entry_model.py` + `test_condo_month_close_model.py` cobrem todos os cenários listados (herança/managers/`CondoMonthClose` sem SoftDelete, constraints/`clean()` PT, partial/simple unique, `bill?` vs caixa + `SET_NULL`, **ledger determinístico**, `carry_forward_out<=0`, `status=closed⇒closed_at`).
- [ ] `python -m pytest tests/unit/test_finances/...` passa 100%, **coverage `finances` ≥90%** nos módulos tocados; testes da S36 (`test_bill_models.py`/`test_bill_annotations.py`) seguem verdes.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/models.py finances/signals.py` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum serviço/serializer/viewset/URL/cache/frontend criado; `Bill`/`Payment`/`BillPaymentService` intactos; `core/models.py`/`core/signals.py`/`settings.py` intactos; nenhum modelo de outras fases.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_reserve_models.py tests/unit/test_finances/test_income_entry_model.py \
     tests/unit/test_finances/test_condo_month_close_model.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances/test_bill_models.py tests/unit/test_finances/test_bill_annotations.py -q  # regressão S36
   ruff check finances/models.py finances/signals.py tests/unit/test_finances/ tests/factories.py
   ruff format --check finances/models.py finances/signals.py tests/unit/test_finances/ tests/factories.py
   mypy core/ finances/
   pyright finances/models.py finances/signals.py
   python manage.py makemigrations --check --dry-run
   ```
2. Atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md` — o orquestrador cuida):
   - Adicionar a linha da Sessão 44 (status **concluída**) na tabela de progresso da feature Condomínio Finance.
   - Listar **Arquivos Criados** (`tests/unit/test_finances/test_reserve_models.py`, `test_income_entry_model.py`, `test_condo_month_close_model.py`) e **Modificados** (`finances/models.py` — 4 modelos + 2 enums Fase 4; `finances/migrations/000X_reserve_income_close.py`; `finances/signals.py` — 4 receivers novos; `tests/factories.py` — 4 factories novas).
   - Anotar os **contratos cross-session** (verbatim, ver abaixo) para a S45/S46 consumirem sem derivar.
   - Nota: "Modelos da Fase 4 (Reserve/ReserveMovement/IncomeEntry/CondoMonthClose); `CondoMonthClose` sem SoftDelete; ledger determinístico `(movement_date, id)`; **guarda de saldo da reserva é da S45** (não do model); `carry_forward_out<=0`; sem serviço/saldo/close/reopen/API/frontend; `Bill`/`Payment` intactos."
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch se necessário — ex.: `feat/condo-finance`):
   ```
   feat(finances): add Reserve/ReserveMovement, IncomeEntry, CondoMonthClose models + RLS migration (Phase 4 models)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **45 — Backend: `CondoBalanceService` (saldo/reserva/atrasados/wedge, caixa condo-scoped ancorado), `CondoMonthCloseService` (close/reopen), guarda de saldo da reserva no `pay(funded_from=reserve)`, `RentScheduleService.received_collectible_total` + API da Fase 4** — consome os modelos desta sessão. A S45 **adiciona** os serviços/guarda/endpoints; **não** recria modelos.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.models`** (Fase 4): `Reserve`, `ReserveMovement`, `IncomeEntry`, `CondoMonthClose`; enums `ReserveMovementKind` (`deposit`/`withdrawal`), `CondoMonthCloseStatus` (`open`/`closed`).
- **Ledger da reserva**: `ReserveMovement` ordenado por `(movement_date, id)` (`Meta.ordering`). Saldo = `Σ(deposit) − Σ(withdrawal)` — **derivado no `CondoBalanceService` (S45)**, nunca property/annotation no model. `amount` é **positivo**; o sinal vem de `kind`.
- **`ReserveMovement.bill`** (`SET_NULL`): `bill` setado = saque p/ pagar conta; `bill=null` = transferência caixa↔reserva. **`amount_paid` do `Bill` NÃO inclui `ReserveMovement`** (design §4.3) — o pagamento é só `PaymentAllocation` (S36). A S45, no `pay(funded_from=reserve)`, cria `Payment` + `PaymentAllocation(→bill)` **e** `ReserveMovement(withdrawal, bill=…)` (debita só a reserva), com a **guarda de saldo** (esta sessão **não** valida saldo).
- **Guarda de saldo negativo da reserva**: **responsabilidade da S45** (`CondoBalanceService.reserve_balance` + checagem em `ReserveService.withdraw`/`BillPaymentService.pay`). O teste §18 "saque > saldo rejeitado" é da S45. Esta sessão garante só `amount > 0`/sinal/ordem.
- **`IncomeEntry`**: `is_received=True` (com `received_date`) é o que conta no **caixa** (entradas_caixa, S45 — junto de `received_collectible_total` + saques de reserva→caixa). Não recorrente (design §15).
- **`CondoMonthClose`** (âncora do fold/caixa, design §3.2/§4.2): `cash_balance_end` semeia o caixa do próximo mês (baseline da S45 quando há mês fechado; senão `FinancialSettings.initial_balance`); `reserve_balance_end` semeia a reserva; `net_result`/`carry_forward_out` (≤0) alimentam o fold da distribuição (S49/S50). `status` `open`→`closed` (com `closed_at`); **reopen** (status→open) recomputa cascata os meses abertos seguintes — **algoritmo na S45** (`CondoMonthCloseService`), esta sessão só modela os campos. Unique `(condominium, reference_month)` (1 fechamento por mês/condomínio). **Não trava aluguel** (rent-lock = `MonthSnapshot` legado).
- **Signals**: os 4 modelos novos invalidam `finance-*` via `invalidate_finance_caches()` (S37). A S45 (combined_calendar/dashboard) confia nessa invalidação.
