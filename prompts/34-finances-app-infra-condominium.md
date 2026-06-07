# Sessão 34 — Fundação: app `finances` + `Condominium` + `Building.condominium` + gate ampliado + helper TZ

> **Feature**: Módulo Financeiro do Condomínio (Saídas, Saldo, Reserva e Distribuição)
> **Sessões da feature**: 34 → 50 (esta é a **34**, primeira de todas; corresponde à **Fase 1a** do design §14)
> Esta sessão cria a **infraestrutura** do app novo `finances` e a **migração faseada de maior risco em PROD** (`Building.condominium`). Cria o app + `INSTALLED_APPS` + `FinancesConfig.ready()`, o model `core.Condominium` (+ registro padrão), o FK `Building.condominium` (nullable → backfill → non-null + index, com RLS), o **helper único de timezone** (`America/Sao_Paulo`) e **amplia o gate** (coverage/mypy/pyright passam a incluir `finances`). **Sem nenhum modelo do `finances` além da entidade `Condominium` (que vive no `core`); sem forms; sem `Category`/`Bill`/serviços.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §2 decisão 2, §3.1, §4 helper TZ, §5.1, §6 "Multi-condomínio", §12 "gate ampliado", §13 "Migrações", §14 Fase 1a, §16 riscos, §18 "Estruturais")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE)*: `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| `AppConfig` + `ready()` importando signals | `core/apps.py:9-23` (`CoreConfig`, `default_auto_field`, `ready()` faz `importlib.import_module(".signals", package="core")` dentro de try/except com `logger.exception`) | **Espelho exato** para `FinancesConfig`. Reusar o mesmo idioma de `ready()` (import dos signals); trocar `core`→`finances` |
| `INSTALLED_APPS` (bloco "Project apps") | `condominios_manager/settings.py:39-60` (`"core"` na linha 59, é o último; sem trailing app) | Adicionar `"finances"` **após** `"core"` |
| `TIME_ZONE = "UTC"` / `USE_TZ = True` | `condominios_manager/settings.py:185,189` | **Por isso** o helper TZ existe: `timezone.now().date()` dá data em UTC e erra a virada do mês no horário de SP (design §4) |
| Model simples (campos + dual managers + `__str__` + `delete()` soft) | `core/models.py:198-223` (`Building`: `all_objects = models.Manager()`, `objects = SoftDeleteManager()`, `__str__`) | Estrutura-base do `Condominium` (`AuditMixin, SoftDeleteMixin, models.Model` + managers duplos) |
| `Building` (model a alterar — receberá `condominium` FK) | `core/models.py:198-223` | O FK novo entra aqui; consumidores (`Apartment`/`Lease`) **inalterados** |
| Migração com `RunSQL` reversível (RLS) — **regra do projeto** | `core/migrations/0047_enable_row_level_security.py:127-134` (`migrations.RunSQL(sql=ENABLE_RLS, reverse_sql=DISABLE_RLS)`; comentário :1-12 explica o porquê Supabase) | **Toda tabela nova** deve habilitar RLS na **mesma** migração (`.claude/rules/database.md`, `.claude/rules/security.md`). `core_condominium` precisa de `ENABLE ROW LEVEL SECURITY` + reverse |
| Última migração do `core` (head atual) | `core/migrations/0047_enable_row_level_security.py` | A migração nova do `core` desta sessão **depende** de `0047`; rode `python manage.py showmigrations core` para confirmar o head (não fixar o número aqui) |
| Backup antes de migrate (precedente concreto) | `prompts/31-backend-webpush-model.md` (Sessão 31 rodou `uv run python scripts/backup_db.py` ANTES do `migrate`) | Mesmo procedimento obrigatório aqui |
| Factories base (`make_building`/`make_apartment`/`make_lease`) | `tests/factories.py:34-86` (`make_building` :34-40, `make_apartment` :43-54, `make_lease` :72-86) | Onde entram `make_condominium()` e o default `condominium=...` em `make_building()` |
| `[tool.coverage.run] source` | `pyproject.toml:374-375` (`source = ["core", "condominios_manager"]`) | Adicionar `"finances"` |
| `[tool.mypy]` (sem `files`; gate é `mypy core/`) | `pyproject.toml:282-321` (`strict = true`, `exclude` cobre `migrations/`) | O gate muda de `mypy core/` → `mypy core/ finances/` (CLI, não config) |
| `[[tool.mypy.overrides]] module = "*.migrations.*"` | `pyproject.toml:328-330` (`ignore_errors = true`) | Cobre as migrações do `finances` automaticamente (glob `*.migrations.*`) |
| `pytest.ini` `--cov=core` + `[coverage:run] source = core` | `pytest.ini:23,48` | Adicionar `--cov=finances` e `source = core\n    finances` |
| `pyrightconfig.json` `include` | `pyrightconfig.json:5-10` (`["core", "condominios_manager", "scripts", "tests"]`; `exclude` cobre `**/migrations` :12) | Adicionar `"finances"` ao `include` |
| `_invalidate_financial_caches` (NÃO tocar agora) | `core/signals.py:292-299` | **Contexto apenas** — os receivers cross-app `finance-*` são da **Sessão 41/4** (cache). Não criar `finances/signals.py` com lógica de invalidação agora; ver §"NÃO fazer" |

### Fatos PROD (design §17, somente leitura — guiam a migração)

- Prédios reais (não soft-deleted): **836** e **850**. Após o backfill, **ambos** devem apontar para o `Condominium` padrão.
- `FinancialSettings`: `initial_balance=0,00`, `initial_balance_date=2026-03-01`, `rent_tracking_start_date=2026-06-01` (não usado nesta sessão; contexto).
- PROD = Supabase `kaukiwhbmvnjjekodcmq`; local em `localhost:5433`, DB `condominio` (`.claude/rules/database.md`).

---

## Escopo

### Arquivos a criar
- `finances/__init__.py` — pacote vazio do app.
- `finances/apps.py` — `FinancesConfig(AppConfig)` (`name = "finances"`, `default_auto_field`, `ready()` importando `finances.signals` no mesmo idioma de `core/apps.py:13-23`).
- `finances/signals.py` — **stub mínimo** desta sessão: só docstring de módulo (a invalidação `finance-*` é da Sessão 41). Existe para que `ready()` tenha o que importar sem `try/except ImportError` (o `ready()` espelha o de `core`, com `importlib` + log). **Nenhum receiver** ainda.
- `finances/models.py` — **vazio de modelos** nesta sessão (todos os modelos do `finances` são S36+). Pode conter só o cabeçalho/docstring. *(O `Condominium` mora no `core`, não aqui — decisão §2/§5.1.)*
- `finances/migrations/__init__.py` — pacote de migrações do app.
- `finances/services/__init__.py` — pacote de serviços.
- `finances/services/timezone.py` — helper único de timezone SP (ver §Especificação).
- `core/migrations/00NN_condominium_and_building_fk.py` — **migração única, faseada** do `core` (ver §Especificação "Migração faseada"). Gerar por `makemigrations` + completar com `RunPython` (backfill) e `RunSQL` (RLS) e a operação de tornar non-null. **NÃO fixar o número** — `makemigrations` define; depende do head atual (`0047`).
- `tests/unit/test_finances/__init__.py` — pacote de testes do `finances`.
- `tests/unit/test_finances/test_app_infra.py` — testes de infraestrutura (app instalado, `ready()` importa signals, model `Condominium`, padrão criado, RLS).
- `tests/unit/test_finances/test_timezone_helper.py` — testes do helper TZ (virada de mês SP vs UTC, sob `freeze_time`).
- `tests/unit/test_finances/test_building_condominium_fk.py` — testes do FK + backfill (default não-nulo após migração, `make_building` traz `condominium`).

### Arquivos a modificar
- `condominios_manager/settings.py` — adicionar `"finances"` a `INSTALLED_APPS` (após `"core"`, `:59`).
- `core/models.py` — adicionar `class Condominium(AuditMixin, SoftDeleteMixin, models.Model)` (na seção DOMAIN MODELS, **antes** de `Building` para ordem de definição/leitura, ou logo após — escolher e justificar) e o campo `Building.condominium = models.ForeignKey("core.Condominium", on_delete=models.PROTECT, related_name="buildings", null=False)` (após a fase de migração; ver abaixo). O campo no model fica **non-null** (a nulabilidade transitória vive **só** na migração faseada).
- `tests/factories.py` — adicionar `make_condominium(**kwargs)` e dar a `make_building(...)` um default `condominium=` (cria/reusa o padrão se não passado), **sem quebrar** os call sites existentes (`make_building()` continua funcionando).
- `pyproject.toml` — `[tool.coverage.run] source` (`:375`) ganha `"finances"`.
- `pytest.ini` — `addopts` ganha `--cov=finances` (`:23`); `[coverage:run] source` (`:48`) ganha `finances`.
- `pyrightconfig.json` — `include` (`:5-10`) ganha `"finances"`.

### NÃO fazer (pertence a outras sessões)
- **Nenhum** modelo do `finances` além de `Condominium` (que vive no `core`). `Category`, `BillingAccount`, `Employee`, `InstallmentPlan`, `Installment`, `BillSkip`, `Bill`, `BillLineItem`, `Payment`, `PaymentAllocation`, `IncomeEntry`, `Reserve`, `ReserveMovement`, `CondoMonthClose` são **Sessão 36+** (Fase 2–4). Não criar `finances/serializers.py`/`viewsets`/`urls`.
- **Nenhum form** — expor `owner`/`is_salary_offset`/`prepaid_until` nos modais é **Sessão 35** (Fase 1b).
- **Nenhuma** lógica de invalidação de cache em `finances/signals.py` (só o stub). Os receivers cross-app `finance-*` (Apartment/Lease/RentAdjustment/MonthSnapshot + estender `_invalidate_financial_caches`) são da **Fase 4 / Sessão 41**. Não definir o **bloco de constantes de prefixo** (`finance-dashboard`/`finance-cash-flow`/`finance-projection`) ainda — ele nasce com o cache (S41), fonte única.
- **Nenhuma** migração inicial do `finances` (ela só faz sentido quando houver o primeiro model do `finances`, **Sessão 36**, e **dependerá explicitamente** da migração `core` desta sessão — anotar isso no Handoff como contrato).
- **Não** migrar/refatorar `Apartment.owner` (não-invasivo, §6). **Não** criar `CondominiumOwnership`.
- **Não** alterar `core/signals.py`, `core/cache.py`, `core/serializers.py`, `core/views.py`, `core/urls.py`.
- **Não** editar `prompts/SESSION_STATE.md` / `prompts/ROADMAP.md` (o orquestrador faz). O Handoff descreve **o que** anotar.

---

## Especificação

### `core.Condominium` (model novo)

Espelha o `Building` (`core/models.py:198-223`) em forma: herda `(AuditMixin, SoftDeleteMixin, models.Model)`, managers duplos, `__str__`.

```python
class Condominium(AuditMixin, SoftDeleteMixin, models.Model):
    """Condomínio (tenancy raiz). Por ora há um único registro-padrão invisível na UI;
    isolamento/permissões multi-condomínio são futuro (design §6, §15)."""

    name = models.CharField(max_length=100, help_text="Nome do condomínio")
    notes = models.TextField(blank=True, default="", help_text="Observações internas")

    all_objects = models.Manager()
    objects = SoftDeleteManager()

    def __str__(self) -> str:
        return self.name
```

- **Tabela** `core_condominium`. **RLS obrigatória** na migração (igual ao padrão `0047`: `ALTER TABLE public.core_condominium ENABLE ROW LEVEL SECURITY;` + reverse `DISABLE`).
- **Registro padrão** via `RunPython` (data-migration) na mesma migração: `Condominium.objects.get_or_create(name=DEFAULT_CONDOMINIUM_NAME, defaults=...)` — **idempotente**. Usar o app registry da migração (`apps.get_model("core", "Condominium")`), **nunca** importar o model real. `DEFAULT_CONDOMINIUM_NAME` é uma constante nomeada (sem magic string espalhada); reverse do `RunPython` = `migrations.RunPython.noop` (o registro fica; remover seria destrutivo e a coluna já terá sido revertida).

### `Building.condominium` (FK faseado — sub-fase de MAIOR risco PROD, design §13)

O campo final no model é **non-null** com `on_delete=PROTECT` (FK de referência, `.claude/rules/architecture.md` "PROTECT em FKs de referência") + `related_name="buildings"` + `db_index` (FK indexa por padrão; garantir índice). A **nulabilidade é transitória e existe só na migração**, em três operações na ordem pinada:

1. **`AddField`** `Building.condominium` `ForeignKey(..., null=True, on_delete=PROTECT, related_name="buildings")` — nullable, sem default.
2. **`RunPython`** backfill: para todo `Building` (incluindo via manager que veja todos — usar `apps.get_model("core", "Building").objects` que na migração ignora o soft-delete custom; **incluir soft-deleted** para não deixar coluna nula em linha alguma → usar `.all()` do manager base da migração) setar `condominium = <registro padrão>`. **Idempotente** (re-rodar não duplica nem falha). Reverse = `noop`.
3. **`AlterField`** para `null=False` (non-null + index).
4. **`RunSQL`** RLS de `core_condominium` (a tabela nova) — `ENABLE`/`DISABLE` reversível.

> **Ordem dentro de `operations`**: `CreateModel(Condominium)` → `RunSQL(RLS de core_condominium)` → `AddField(Building.condominium null=True)` → `RunPython(criar padrão)` → `RunPython(backfill buildings)` → `AlterField(null=False)`. (Criar o padrão **antes** do backfill; o backfill referencia o padrão.) Pode-se unir "criar padrão" e "backfill" num único `RunPython` — escolher o que ficar mais claro (KISS), desde que idempotente e com `apps.get_model`.

> **Forward E backward testáveis**: a migração deve aplicar e reverter limpo (`migrate core <anterior>` desfaz `AlterField`→`RunPython noop`→`AddField`→`RunSQL DISABLE`→`DeleteModel`). Verificar no Handoff.

### `finances/services/timezone.py` (helper único SP)

`settings.TIME_ZONE = "UTC"` (`settings.py:185`), então `timezone.now().date()` erra a virada do mês no fuso de SP. **Todos os serviços do `finances` (S36+) roteiam "hoje/mês atual" por aqui** — fonte única (DRY). Usar `zoneinfo.ZoneInfo` (stdlib 3.14; sem dependência nova).

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
from django.utils import timezone

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

def now_sp() -> datetime:
    """Agora no fuso de São Paulo (converte o now() aware de UTC do settings)."""

def today_sp() -> date:
    """Data de hoje no fuso de SP (NÃO timezone.now().date(), que é UTC)."""

def current_month_sp() -> date:
    """Primeiro dia do mês corrente em SP (dia=1) — alinhado a competence_month/reference_month."""
```

- `today_sp()` = `timezone.now().astimezone(SAO_PAULO_TZ).date()`. `current_month_sp()` = `today_sp().replace(day=1)`.
- Edge-case alvo (§18 "virada de mês na TZ SP"): instante UTC já no mês seguinte enquanto em SP ainda é o mês anterior (e simétrico) → o helper retorna o mês **de SP**, não o de UTC.

### `tests/factories.py` — `make_condominium` + default em `make_building`

- `make_condominium(user=None, **kwargs)` no estilo de `make_person` (`factories.py:89-95`): `defaults = {"name": "Test Condominium"}`, propaga `created_by`/`updated_by` se `user`, `baker.make("core.Condominium", **defaults)`.
- `make_building(...)`: ganhar parâmetro `condominium=None`; se `None`, **criar/usar** um `Condominium` (chamar `make_condominium`). Manter a assinatura retrocompatível (`make_building()` e `make_building(street_number=...)` continuam válidos). Passar `condominium=condominium` ao `baker.make("core.Building", ...)`.

### Gate ampliado (design §12, primeiro item da Fase 1)

- `pytest.ini`: `--cov=core` permanece **e** soma `--cov=finances`; `[coverage:run] source` lista `core` **e** `finances`.
- `pyproject.toml`: `[tool.coverage.run] source = ["core", "condominios_manager", "finances"]`.
- `pyrightconfig.json`: `include` ganha `"finances"` (o `exclude` `**/migrations` já cobre as migrações do app).
- O comando de type-check do gate passa a ser `mypy core/ finances/` (CLI; `[[tool.mypy.overrides]] *.migrations.*` já isenta migrações). **Atualizar a frase do gate** onde aparecer no Handoff/Critérios.
- **≥90% standalone em `finances`** nesta sessão: como o app quase só tem o helper TZ + `apps.py` + stub de signals, os testes do helper e da infra devem cobri-los; o `Condominium` (no `core`) é coberto pelos testes de infra/FK.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **só fronteiras externas**. Aqui isso é **apenas `freezegun`** (relógio do sistema) nos testes do helper TZ. **NUNCA** mockar ORM, `apps`, `zoneinfo`, `timezone` ou qualquer interno. Banco real (`--reuse-db`). Dados via factories (`model-bakery`). `filterwarnings=error` (pytest.ini): zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_app_infra.py`
- [ ] `"finances"` está em `django.conf.settings.INSTALLED_APPS`.
- [ ] `django.apps.apps.get_app_config("finances")` é instância de `FinancesConfig` e `name == "finances"`.
- [ ] `FinancesConfig.ready()` importa `finances.signals` sem erro (asserir que `importlib.import_module("finances.signals")` resolve; ou que o módulo está em `sys.modules` após o app carregar).
- [ ] `core.models.Condominium` existe, herda `AuditMixin` **e** `SoftDeleteMixin` (tem `created_at`/`updated_at`/`is_deleted`); managers duplos (`objects` é `SoftDeleteManager`, `all_objects` é `Manager`); `__str__` retorna `name`.
- [ ] **Registro padrão**: após as migrações, existe **exatamente um** `Condominium` com `name == DEFAULT_CONDOMINIUM_NAME` (`Condominium.objects.filter(name=...).count() == 1`). *(Testa o efeito da data-migration; sem re-rodar a migração.)*
- [ ] **RLS** (§18 estrutural / regra DB): `core_condominium` tem RLS habilitada — consultar `pg_class.relrowsecurity` via `connection.cursor()` para `relname='core_condominium'` retorna `True`. *(SQL parametrizado, sem string-format — `.claude/rules/security.md`.)*

#### `tests/unit/test_finances/test_timezone_helper.py` (sob `@freeze_time`)
- [ ] `current_month_sp()` retorna sempre dia 1.
- [ ] **Virada de mês (UTC à frente de SP)**: `freeze_time("2026-07-01 02:00:00")` (UTC) → em SP ainda é `2026-06-30 23:00` → `today_sp() == date(2026, 6, 30)` e `current_month_sp() == date(2026, 6, 1)` (não julho). Asserir explicitamente que difere de `timezone.now().date()` (que daria julho).
- [ ] **Virada de mês (SP já no mês seguinte)**: caso simétrico onde SP virou o mês e UTC também — `today_sp()`/`current_month_sp()` corretos para SP.
- [ ] `now_sp().tzinfo` é o fuso de SP (`ZoneInfo("America/Sao_Paulo")`); `today_sp()` é um `date` (não `datetime`).

#### `tests/unit/test_finances/test_building_condominium_fk.py`
- [ ] `make_building()` (sem passar `condominium`) cria um `Building` com `building.condominium` não-nulo.
- [ ] `make_building(condominium=cond)` respeita o `Condominium` passado (`building.condominium_id == cond.id`).
- [ ] `Building.condominium` é `PROTECT`: tentar `condominium.delete()` (hard) com prédio referenciando **levanta** `ProtectedError` (ou o soft-delete não desreferencia — testar o comportamento PROTECT no hard delete). *(Usar `transaction.atomic` para o `IntegrityError`/`ProtectedError`.)*
- [ ] `condominium.buildings.all()` (related_name) traz o prédio criado.
- [ ] (§18 estrutural) Nenhum `Building` no banco fica com `condominium_id` nulo após o setup das factories (a coluna é non-null — `make_building` sempre preenche).

> Rodar (devem **falhar** — app/model/helper ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/ -q
> ```

### 2. GREEN — implementar

1. **Backup obrigatório ANTES de qualquer migrate** (`.claude/rules/database.md`, precedente S31): `uv run python scripts/backup_db.py` — confirmar que gerou `backups/backup_condominio_<ts>.sql`. **Se o backup falhar, PARAR** e reportar (regra global de DB safety). *(Local em `localhost:5433`; PROD não é tocado nesta sessão — só local.)*
2. Criar o pacote `finances/` (`__init__.py`, `apps.py`, `signals.py` stub, `models.py` cabeçalho, `migrations/__init__.py`, `services/__init__.py`, `services/timezone.py`).
3. Adicionar `"finances"` ao `INSTALLED_APPS` (`settings.py:59`).
4. Implementar `core.models.Condominium` e o campo `Building.condominium` (non-null no model).
5. Gerar a migração do `core`: `python manage.py makemigrations core` → editar o arquivo gerado para a **forma faseada** (AddField null=True → RunPython criar padrão + backfill → AlterField null=False → RunSQL RLS), com `DEFAULT_CONDOMINIUM_NAME`, `apps.get_model`, idempotência e `reverse_sql`/`noop`. *(Hooks bloqueiam editar migrações **existentes**; esta é nova, criada nesta sessão — pode ser completada.)*
6. `make_condominium()` + default `condominium=` em `make_building()` (`tests/factories.py`).
7. Ampliar o gate: `pytest.ini`, `pyproject.toml`, `pyrightconfig.json` (ver §Especificação "Gate ampliado").
8. Aplicar a migração local: `python manage.py migrate core`. Verificar idempotência do backfill e o registro padrão.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/ -q
```

### 3. REFACTOR

- Garantir **uma única** definição de `DEFAULT_CONDOMINIUM_NAME` (usada na migração; se algum teste precisar, importar da fonte — sem duplicar a string). KISS: o helper TZ tem 3 funções pequenas, sem parâmetros não usados (YAGNI — nada de `tz` configurável agora).
- `finances/signals.py` permanece **stub** (docstring só); nada de receiver especulativo. `finances/models.py` sem modelos.
- Sem re-exports/barrels; imports diretos da fonte.

### 4. VERIFY — gate **ampliado** (escopo dos arquivos tocados + cobertura standalone do `finances`)

> Rodar escopado aos arquivos editados (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto), **mas** confirmar a cobertura **standalone ≥90%** do `finances`:
```bash
python -m pytest tests/unit/test_finances/ -q --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider
ruff check finances/ core/models.py tests/factories.py tests/unit/test_finances/
ruff format --check finances/ core/models.py tests/factories.py tests/unit/test_finances/
mypy core/ finances/
pyright finances/ core/models.py
python manage.py makemigrations core --check --dry-run   # deve dizer "No changes detected"
```
- Forward/backward da migração:
```bash
python manage.py migrate core            # forward (head)
python manage.py migrate core 0047       # backward até o anterior ao desta sessão (confirme o nº via showmigrations)
python manage.py migrate core            # re-forward (idempotente)
```

---

## Constraints

- **Direção de dependência** (`.claude/rules/architecture.md`): `finances → core`, nunca o inverso. `Condominium` vive no `core` (é tenancy raiz consumida por `core.Building`); o `finances` ainda não importa nada do `core` nesta sessão (só `apps.py`/`signals` stub/helper TZ).
- **Sem dependência nova**: `zoneinfo` é stdlib (3.14). **Não** adicionar `pytz`/`django-treebeard`/`django-money` (design §13/§15). Se mexer em deps (não deve), seria nos **três** lugares (regra do projeto) — mas aqui **não há** dep nova.
- **Migração faseada + RLS + backup**: nullable → backfill idempotente (`apps.get_model`, sem importar models reais) → non-null; RLS de `core_condominium` na mesma migração com reverse; backup **antes** do migrate; forward **e** backward verdes.
- **PROTECT** em `Building.condominium` (FK de referência). `Condominium` final é non-null no model (nulabilidade só transitória na migração).
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código. Tipos completos (mypy strict + pyright).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** — importar tipos direto (PEP 649 nativo; `.claude/rules/coding-standards.md`).
- **Sem `try/except ImportError` / `HAS_*`** para imports (regra do projeto). O `ready()` espelha `core/apps.py` (que usa `importlib` + try/except amplo em volta do log, **não** `ImportError`-guard de dependência opcional) — replicar exatamente esse idioma, sem inventar variação.
- **Sem re-exports / barrels / shims.** `finances/signals.py` é stub real (docstring), não um re-export.
- **Sem** os modelos/serviços/serializers/forms/cache do `finances` (Sessões 35/36+). Sem o bloco de constantes de prefixo de cache (S41). Sem migração inicial do `finances` (S36).
- **SQL parametrizado** nos testes que consultam `pg_class` (sem string-format — `.claude/rules/security.md`).
- Mensagens ao usuário em **Português**; logs/devs em **Inglês**. Dinheiro (não há nesta sessão) seria `Decimal(12,2)`.
- Não editar `SESSION_STATE.md`/`ROADMAP.md` (orquestrador).

---

## Critérios de Aceite (binários)

- [ ] App `finances` criado: `finances/__init__.py`, `apps.py` (`FinancesConfig`, `ready()` importa `finances.signals` no idioma de `core/apps.py:13-23`), `signals.py` (stub, zero receivers), `models.py` (sem modelos), `migrations/__init__.py`, `services/__init__.py`, `services/timezone.py`.
- [ ] `"finances"` em `INSTALLED_APPS` (`settings.py`, após `"core"`); `apps.get_app_config("finances")` é `FinancesConfig`.
- [ ] `core.models.Condominium` criado (`AuditMixin` + `SoftDeleteMixin` + managers duplos + `__str__`); tabela `core_condominium` com **RLS habilitada** na migração; **registro padrão** criado por data-migration idempotente (`get_or_create`).
- [ ] `Building.condominium` FK **non-null** no model, `PROTECT`, `related_name="buildings"`; nulabilidade **só** transitória na migração faseada (AddField null=True → backfill idempotente → AlterField null=False).
- [ ] Migração do `core` aplica **forward e backward** limpo; `makemigrations --check --dry-run` → "No changes detected"; backfill cobre todos os prédios (nenhum `condominium_id` nulo).
- [ ] `finances/services/timezone.py` com `SAO_PAULO_TZ`, `now_sp()`, `today_sp()`, `current_month_sp()`; testes de virada de mês SP×UTC passam (helper retorna o mês de **SP**).
- [ ] `make_condominium()` criado; `make_building()` tem default `condominium=` retrocompatível (call sites antigos funcionam).
- [ ] **Gate ampliado**: `pytest.ini` (`--cov=finances` + `source` com `finances`), `pyproject.toml` (`[tool.coverage.run] source` com `"finances"`), `pyrightconfig.json` (`include` com `"finances"`); type-check do gate é `mypy core/ finances/`.
- [ ] `python -m pytest tests/unit/test_finances/` passa 100% **com `--cov=finances --cov-fail-under=90`** (≥90% standalone no `finances`).
- [ ] `ruff check`/`ruff format --check` limpos; `mypy core/ finances/` e `pyright finances/ core/models.py` limpos — **sem** `# noqa`/`# type: ignore`; **sem** `from __future__`/`TYPE_CHECKING`; **sem** re-export.
- [ ] Backup gerado **antes** do migrate (`backups/backup_condominio_<ts>.sql`).
- [ ] Nenhum modelo/serializer/viewset/form/cache do `finances` além de `Condominium`/helper TZ; `core/signals.py`/`cache.py`/`serializers.py`/`views.py`/`urls.py` intactos; sem migração inicial do `finances`.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   uv run python scripts/backup_db.py
   python -m pytest tests/unit/test_finances/ -q --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider
   ruff check finances/ core/models.py tests/factories.py tests/unit/test_finances/
   ruff format --check finances/ core/models.py tests/factories.py tests/unit/test_finances/
   mypy core/ finances/
   pyright finances/ core/models.py
   python manage.py makemigrations core --check --dry-run
   python manage.py migrate core 0047 && python manage.py migrate core   # backward+forward
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar o arquivo):
   - Nova feature "Módulo Financeiro do Condomínio" (Sessões 34–50), Sessão 34 **concluída**, design `docs/plans/2026-06-06-condominium-finance-design.md`.
   - **Arquivos Criados**: `finances/{__init__,apps,signals,models}.py`, `finances/migrations/__init__.py`, `finances/services/{__init__,timezone}.py`, `core/migrations/00NN_condominium_and_building_fk.py`, `tests/unit/test_finances/{__init__,test_app_infra,test_timezone_helper,test_building_condominium_fk}.py`.
   - **Arquivos Modificados**: `condominios_manager/settings.py` (INSTALLED_APPS), `core/models.py` (`Condominium` + `Building.condominium`), `tests/factories.py` (`make_condominium` + default em `make_building`), `pyproject.toml` + `pytest.ini` + `pyrightconfig.json` (gate ampliado).
   - **Nota**: "Fase 1a — fundação `finances` + `Condominium`(padrão) + `Building.condominium` faseada (nullable→backfill→non-null, RLS na mesma migração, forward/backward verdes, backup antes); helper TZ único `America/Sao_Paulo` (todos os serviços do finances roteiam por aqui, S36+); gate ampliado (coverage/mypy/pyright incluem `finances`, ≥90% standalone). **Sem** modelos/forms/serviços/cache do finances; bloco de constantes de prefixo `finance-*` e receivers cross-app ficam para a S41; migração inicial do `finances` (S36) **dependerá explicitamente** desta migração do core."
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch da feature se necessário — ex. `feat/condominium-finance`):
   ```
   feat(finances): scaffold finances app + core.Condominium + phased Building.condominium FK + SP timezone helper + widened gate

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **35 — Forms (Fase 1b)**: expor `owner` (Apartamento) e `is_salary_offset`/`prepaid_until`/vínculo de funcionário (Locação) nos modais, gating `is_staff`, atualizar testes de form (depende desta sessão; lê o `SESSION_STATE.md` atualizado). A migração inicial do `finances` (modelos de classificação/contas) é a **Sessão 36** e **depende explicitamente** da migração `core` desta sessão.
