# Sessão 77 — Modelo de terceiros: FKs, invariantes e migration

**Fase 2 (terceiros) — sessão 1 de 6.** Backend puro. Sem API, sem frontend, sem serviço de extrato.

Design: `@docs/plans/2026-07-27-condo-third-party-payments-design.md` §4 (modelo de dados).

## Contexto

Ler antes de escrever qualquer código:

- **Design (ler §3 decisão arquitetural, §4 modelo)**: `@docs/plans/2026-07-27-condo-third-party-payments-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md` (RLS)

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Model com FK p/ `Person`** | `finances/models.py:724-726` (`Employee.person`) | Estilo da FK cross-app `finances → core`. **Divergir só no `on_delete`** (aqui `PROTECT`, não `SET_NULL`) |
| **Model AuditMixin+SoftDelete completo** | `finances/models.py:495-525` (`Payment`) | Esqueleto do `ThirdPartySettlement`: managers, `Meta`, `CheckConstraint`, `clean()` PT, `__str__` |
| **Constantes de mensagem PT** | `finances/models.py:605-608` (`_ERR_BASE_SALARY_NEGATIVE` etc.) | Mensagens como constantes module-level, nunca string inline |
| **`clean()` que valida invariante** | `finances/models.py:522-525` (`Payment.clean`) | Levantar `ValidationError({"campo": MSG})` |
| **`Bill.clean` atual** | `finances/models.py:450-453` | **Só normaliza `competence_month`** — é aqui que entra a exclusividade de origem |
| **RLS em migration** | `finances/migrations/0002_installmentplan_employee_bill_employee_installment_and_more.py:525-538` | `RunSQL` com SQL estático + `reverse_sql`, como última operação |
| **Factories de teste** | `tests/factories.py` (`make_payment`, `make_person`) | `model_bakery` flat; usar, não recriar |
| **Teste de FK p/ Person** | `tests/unit/test_finances/test_employee_model.py:75-80` | Análogo mais próximo |

## Contexto mínimo

Filhos e genro pagam contas do condomínio e compram coisas para os proprietários (que não têm cartão). Esta sessão cria **só o alicerce de dados**: a origem `THIRD_PARTY`, quem financiou o pagamento, a compra como `Bill`, o model de acerto, e as invariantes que impedem estado inconsistente.

**Decisão arquitetural já tomada (§3 do design, não reabrir):** a compra de terceiro é um `Bill` com FK nova `paid_by_person` — **não** existe model `ThirdPartyCharge`. O precedente é `Employee`: dívida com uma pessoa já é `Bill(employee=…)` ("Payroll registry. The monthly payment is a Bill(employee=…) with lines", `finances/models.py:721`).

## Arquivos

- **Modificar**: `finances/models.py`
- **Criar**: `finances/migrations/0011_third_party_payments.py`
- **Criar**: `tests/unit/test_finances/test_third_party_models.py`

## Escopo

### 1. `FundedFrom.THIRD_PARTY` — **e alargar a coluna** (bug de produção)

```python
class FundedFrom(models.TextChoices):
    CAIXA = "caixa", "Caixa"
    RESERVE = "reserve", "Reserva"
    THIRD_PARTY = "third_party", "Terceiro"
```

**CRÍTICO — `Payment.funded_from` é `max_length=10` hoje (`finances/models.py:500-502`) e `"third_party"` tem 11 caracteres.** Sem alargar, o Postgres estoura `value too long for type character varying(10)` **no primeiro insert em produção**.

Alterar para `max_length=20` e incluir o `AlterField` correspondente na migration. Mudar só `choices` **não** altera a coluna.

**Armadilha que esconde o bug:** `Payment.objects.create()` pula `full_clean()`, então testes que não vão ao banco real podem passar. Teste obrigatório: criar de fato um `Payment(funded_from=THIRD_PARTY)` e reler do banco.

### 2. `Payment.paid_by`

```python
paid_by = models.ForeignKey(
    Person, null=True, blank=True, on_delete=models.PROTECT,
    related_name="finance_payments_funded",
)
```

`Person` **já está importado** em `finances/models.py:40` — não adicionar import.

`PROTECT` é deliberado e **diverge** de `Employee.person` (que é `SET_NULL`): apagar a pessoa apagaria a dívida com ela. Comentar essa divergência no código em uma linha.

Invariante em `Payment.clean()`, com as mensagens como constantes module-level no padrão de `_ERR_BASE_SALARY_NEGATIVE` (`finances/models.py:606`) — **mas SEM o prefixo `_`**: `ERR_THIRD_PARTY_NEEDS_PERSON` e `ERR_PERSON_ONLY_THIRD_PARTY`.

**Por quê sem underscore:** a S80 precisa validar a mesma invariante em `BillPaymentService.pay` antes do `Payment.objects.create()` (que **pula `full_clean()`**), e vai importar essas constantes. Importar nome privado entre módulos viola as regras do projeto. Deixá-las públicas desde já evita o vizinho errado.

- `funded_from == THIRD_PARTY` e `paid_by is None` → `ValidationError({"paid_by": "Pagamento de terceiro exige a pessoa que pagou."})`
- `funded_from != THIRD_PARTY` e `paid_by is not None` → `ValidationError({"paid_by": "Apenas pagamento de terceiro pode ter pessoa pagadora."})`

### 3. `Bill.paid_by_person`

```python
paid_by_person = models.ForeignKey(
    Person, null=True, blank=True, on_delete=models.PROTECT,
    related_name="finance_bills_purchased",
)
```

**Sem `UniqueConstraint`** — uma pessoa faz N compras no mesmo mês.

> **`paid_by_person` NÃO é uma quarta FK de origem.** É dimensão **ortogonal** de atribuição ("quem financiou"), e **coexiste** com qualquer FK de origem. Motivo verificado: a parcela de um plano avulso é uma `Bill` com `installment` preenchido (`finances/services/bill_generation_service.py:244-247`) — se fossem exclusivas, **compra parcelada de terceiro seria impossível**, e ela é caso central. Idem "Alvaro pagou a conta de água" (`billing_account` + pagamento dele).

### 4. Exclusividade das FKs de origem (fecha buraco pré-existente)

`Bill` tem hoje 3 FKs de origem (`billing_account`, `installment`, `employee`) e **nenhuma validação de exclusividade** — verificado: `Bill.clean()` só normaliza `competence_month` (`finances/models.py:450-453`), e nenhum serializer cobre isso.

Adicionar em `Bill.clean()`: no máximo **uma das TRÊS originais** pode estar preenchida. Mensagem PT constante: `"A conta pode ter no máximo uma origem (conta de cobrança, parcela ou funcionário)."`

> **Risco investigado e liberado (2026-07-27) — não repetir a checagem.** `BillingAccountQuerySet.with_open_balance` (`finances/models.py:195-198`) tem um `arm_b` que **explicitamente exclui** bills com `billing_account` **e** `installment` juntos, ou seja: o código existente **antecipa** essa combinação, e uma regra cega poderia quebrar dado real.
>
> Já verificado nos **dois** bancos (local e **produção**, via Supabase): `bill+installment = 0`, `bill+employee = 0`, `installment+employee = 0`, de 28 bills em cada. **Nenhum dado viola a regra** → pode impor com segurança.
>
> Se ainda assim algum teste revelar dado com duas origens, **PARAR e reportar** — não "consertar" o dado. A ortogonalidade de `paid_by_person` (o que a Fase 2 realmente precisa) não depende desta regra.

**`paid_by_person` fica FORA dessa regra** — não conta como origem. Um teste obrigatório trava isso (`installment` + `paid_by_person` = **válida**).

**Não** adicionar `CheckConstraint` de banco — as FKs são nullable e a regra é de aplicação; `clean()` + serializer é o padrão da casa (ver `_EMBEDDED_NEEDS_CONSUMPTION_MSG`).

### 5. `ThirdPartySettlement`

Conforme §4.4 do design, verbatim. `AuditMixin, SoftDeleteMixin`, `all_objects`/`objects = SoftDeleteManager()`, `default_manager_name = "objects"`, `ordering = ["-settlement_date"]`, `CheckConstraint(amount__gt=0, name="third_party_settlement_amount_positive")`, `clean()` PT espelhando `Payment.clean` (`finances/models.py:522-525`), `__str__` no padrão PT do módulo.

### 6. Migration `0011`

Uma só: 2 `AddField`, 1 `AlterField` (choices de `funded_from`), 1 `CreateModel`, 1 `RunSQL` de RLS.

RLS **obrigatória** para a tabela nova — copiar o padrão exato de `finances/migrations/0002_...py:527-534`:

```python
migrations.RunSQL(
    sql="ALTER TABLE public.finances_thirdpartysettlement ENABLE ROW LEVEL SECURITY;",
    reverse_sql="ALTER TABLE public.finances_thirdpartysettlement DISABLE ROW LEVEL SECURITY;",
),
```

SQL estático, sem f-string (ruff S608). Migration puramente aditiva: **sem backfill, sem DROP, sem data migration**.

## TDD

Red primeiro. Testes mínimos:

1. `THIRD_PARTY` sem `paid_by` → `ValidationError` no campo `paid_by`
2. `CAIXA` **com** `paid_by` → `ValidationError`
3. `THIRD_PARTY` com `paid_by` → válido
4. `Bill` com 2 origens **reais** (`billing_account` + `installment`) → `ValidationError`
5. `Bill` com 1 origem e `Bill` com 0 origens (avulsa) → válidos
5b. **`Bill` com `installment` + `paid_by_person` → VÁLIDA** (compra parcelada de terceiro) — trava a ortogonalidade
5c. **`Bill` com `billing_account` + `paid_by_person` → VÁLIDA** (terceiro pagou a conta de água)
6. `ThirdPartySettlement` com `amount <= 0` → `ValidationError`; `> 0` → válido
7. Soft delete do settlement o remove de `objects` e o mantém em `all_objects`
8. Apagar `Person` com pagamento vinculado → `ProtectedError`

Factories: `tests/factories.py` (`make_payment`, `make_person`, flat `model_bakery`).

## NÃO fazer

- **Não** criar `ThirdPartyCharge` (decisão §3 — a compra é `Bill`).
- **Não** tocar `CondoBalanceService`, serializers, viewsets, URLs ou frontend (sessões seguintes).
- **Não** alterar `_caixa_outflow` — a allowlist já exclui `third_party` automaticamente.
- **Não** criar serviço de extrato (S79).
- **Não** rodar `migrate` em produção.

## Aceite

- `python -m pytest tests/unit/test_finances/test_third_party_models.py --cov-fail-under=0` verde

> **Por que `--cov-fail-under=0` é obrigatório em toda rodada escopada:** `pytest.ini:17-31` embute `--cov=core --cov=finances --cov-fail-under=90` no `addopts`. Rodar **um** arquivo mede cobertura do pacote inteiro (~14%) e o comando **sai com erro mesmo com 100% dos testes passando**. Foi bug real do plano da Fase 1. O gate de 90% vale na **suíte completa**, nunca numa rodada escopada.
- Suíte `finances` completa sem regressão
- `ruff check && ruff format --check && mypy core/ finances/ && pyright` zerados
- `makemigrations --check` → "No changes detected" depois da migration criada
- Migration forward → backward → forward OK
- RLS confirmada: `SELECT relrowsecurity FROM pg_class WHERE relname='finances_thirdpartysettlement'` → `t`
- **Backup do banco local antes do migrate** (`python scripts/backup_db.py`)
