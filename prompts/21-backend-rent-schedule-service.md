# Sessão 21 — Backend: `RentScheduleService` + refactor DRY do `DailyControlService`

> **Feature**: Calendário de Controle de Aluguéis (Dashboard)
> **Sessões da feature**: 21 → 25 (esta é a 21, primeira)
> Esta sessão cria a **fonte única** da lógica "aluguel devido no mês" e **elimina a duplicação** existente no `DailyControlService` (DRY). **Sem endpoints, sem frontend.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §4.1, §4.2, §4.3, §4.4, §4.5, §5 inteiras)**: `@docs/plans/2026-06-02-rent-payment-calendar-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões**: `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `tests/CLAUDE.md`, `.claude/rules/design-principles.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| Classe-service só com `@staticmethod`, `Decimal`, sem estado | `core/services/fee_calculator.py:21-222` (classe `FeeCalculatorService`, abre na linha 21, arquivo termina na 222) | Estrutura-base do novo service |
| Multa de atraso (reuso direto) | `core/services/fee_calculator.py:49-99` (`calculate_late_fee(rental_value, due_day, current_date) -> dict`) | Retorna `is_late`/`late_days`/`late_fee`/`message`. **CUIDADO**: usa aritmética de dia-do-mês `current_date.day - due_day` (linhas 82-83) — só correta DENTRO do mês corrente (ver §"Multa só no mês corrente") |
| Clamp de dia ao mês (técnica) | `core/services/fee_calculator.py:101-105` (`_clamp_day` via `calendar.monthrange`) | Mesma técnica de `calendar.monthrange` para `clamp_due_day` |
| `end_date` do lease | `core/services/date_calculator.py:60-102` (`calculate_final_date(start_date, validity_months) -> date`) | Calcula o fim do contrato (com edge case Feb 29). É a janela de cobertura do lease |
| **Função módulo-nível ATUAL — entries (porção aluguel)** | `core/services/daily_control_service.py:328-365` (`def _collect_entries_by_day`, porção aluguel em :337-365) | **Função módulo-nível**, NÃO método de classe. Filtro `apartment__is_rented=True` + excludes owner/prepaid/salary_offset + `min(due_day, days_in_month)`. Chamada de `DailyControlService` em `:78` |
| **Função módulo-nível ATUAL — expected** | `core/services/daily_control_service.py:669-680` (`def _get_expected_rent_total`) | **Função módulo-nível**. Mesmo filtro, soma `lease.rental_value`. Chamada em `:142` |
| **Função módulo-nível ATUAL — received** | `core/services/daily_control_service.py:704-710` (`def _get_received_rent_total`) | **Função módulo-nível**. Soma `amount_paid` de **TODOS** os `RentPayment.objects.filter(reference_month=month_start)` — **SEM** filtro de cobrabilidade. Chamada em `:147` |
| `DAYS_OF_WEEK_PT` (mapa de dias da semana PT) | `core/services/daily_control_service.py:34-42` | Constante a mover para fonte única |
| MonthSnapshot finalizado (consulta) | `core/models.py` (`MonthSnapshot`, campo `is_finalized` em `:1507`) | `MonthSnapshot.objects.filter(reference_month=..., is_finalized=True).exists()` |
| Testes que DEVEM continuar verdes | `tests/unit/test_financial/test_daily_control_service.py` (16 testes) | Regressão obrigatória — ver §"Reconciliação obrigatória da fixture `lease`" |
| Factories disponíveis | `tests/factories.py` (`make_building`, `make_apartment`, `make_tenant`, `make_lease`, `make_person`, `make_rent_payment`) | **NÃO existe `make_month_snapshot`** — usar `baker.make("core.MonthSnapshot", ...)` |

### Campos de modelo relevantes (já existem, NÃO criar migration)

- `Tenant.due_day` (`core/models.py:446`, `PositiveIntegerField`, 1–31, validado).
- `Apartment.owner` (FK opcional para `Person`), `Apartment.is_rented`, `Apartment.rental_value`.
- `Lease.rental_value`, `Lease.start_date`, `Lease.validity_months`, `Lease.prepaid_until` (`:620`), `Lease.is_salary_offset` (`:623`), `Lease.pending_rental_value` (`:631`), `Lease.pending_rental_value_date` (`:638`), `Lease.responsible_tenant`.
- `RentPayment` (`core/models.py:1237-1271`): `lease`, `reference_month` (DateField, dia 1 do mês), `amount_paid`, `payment_date`. UniqueConstraint `(lease, reference_month)` **condicional a `is_deleted=False`** (`:1249-1254`) — soft-delete libera o slot para recriação. `objects` exclui soft-deleted; `all_objects` inclui.
- `MonthSnapshot` (`core/models.py`): `reference_month` (DateField, dia 1), `is_finalized` (bool, `:1507`).

---

## Escopo

### Arquivos a criar
- `core/services/rent_schedule_service.py` — `RentScheduleService` (6 `@staticmethod` conforme design §4.1).
- `tests/unit/test_financial/test_rent_schedule_service.py` — testes unitários.

### Arquivos a modificar
- `core/services/daily_control_service.py` — refatorar as **funções módulo-nível** `_collect_entries_by_day` (porção aluguel, `:337-365`), `_get_expected_rent_total` (`:669-680`) e `_get_received_rent_total` (`:704-710`) para **delegar** a `RentScheduleService`. **Preservar os call sites** em `:78`, `:142`, `:147` (assinaturas das funções inalteradas). Comportamento idêntico (ver §"Equivalência de comportamento"). Demais porções (income, exits, etc.) **intactas**.
- `tests/unit/test_financial/test_daily_control_service.py` — **APENAS a fixture `lease` (`:52-60`)**: ajustar `start_date` para que a janela de datas do contrato cubra março/2026 (ver §"Reconciliação obrigatória da fixture `lease`"). **NÃO alterar nenhum corpo/assert dos 16 testes.**

### NÃO fazer (pertence a outras sessões)
- **Nenhum** endpoint/`@action`/view (`rent_calendar`, `toggle_rent_payment` são da **Sessão 22**).
- **Não tocar** em `mark_rent_paid` (`core/views.py:722-775`) — sua remoção/unificação é da **Sessão 25**. Ele continua existindo e funcionando até lá.
- **Nenhum** frontend, hook, query-key ou componente (Sessões 23–24).
- **Nenhuma** migration, alteração de model, serializer ou URL.
- Não cachear nada (design §4.3 — YAGNI agora).
- Não refatorar income/exits do `DailyControlService` — apenas a porção de aluguel.
- **Não alterar assertions nem corpos** dos 16 testes do `DailyControlService` — só a fixture `lease`.

---

## Especificação — `RentScheduleService`

Service stateless, todos os métodos `@staticmethod`. `Decimal` para dinheiro; aritmética de data pura (todos `DateField`). Mensagens ao usuário em PT, logs em EN. Direção de dependência: o service importa de `core.models`, `core.services.fee_calculator`, `core.services.date_calculator` — **nunca** de views/serializers.

```python
from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.db.models import QuerySet
from core.models import Lease

class RentScheduleService:

    @staticmethod
    def clamp_due_day(due_day: int, year: int, month: int) -> int:
        """min(due_day, dias_do_mês) via calendar.monthrange. Ex.: 31 em fev/2026 → 28; em abr → 30."""

    @staticmethod
    def effective_rental_value(lease: Lease, reference_month: date) -> Decimal:
        """rental_value, exceto se pending_rental_value E pending_rental_value_date estão
        definidos E reference_month >= pending_rental_value_date → retorna pending_rental_value."""

    @staticmethod
    def collectible_leases(reference_month: date, building_id: int | None = None) -> QuerySet[Lease]:
        """Leases COBRÁVEIS que cobrem o mês (FONTE ÚNICA):
        - não-deletados (manager padrão Lease.objects)
        - apartment.owner is null  (repasse de proprietário NÃO é receita do condomínio)
        - is_salary_offset=False
        - prepaid_until NÃO cobre o mês (excluir prepaid_until >= reference_month)
        - janela start_date..end_date intersecta o mês:
            start_date <= último dia do mês  E  end_date >= reference_month,
            onde end_date = DateCalculatorService.calculate_final_date(start_date, validity_months)
        - building_id opcional → filtra por apartment__building_id
        - select_related('apartment', 'apartment__building', 'responsible_tenant')

        IMPORTANTE: a janela de datas é date-aware (NÃO depende do booleano apartment.is_rented).
        Os filtros ORM-expressáveis (owner, salary_offset, prepaid, building, start_date <=
        último dia do mês) ficam no queryset; o limite superior (end_date é calculado por
        DateCalculatorService) é aplicado em Python sobre o queryset já reduzido. Não usar
        apartment__is_rented em lugar nenhum — a cobrabilidade é puramente date-aware."""

    @staticmethod
    def get_month_schedule(year: int, month: int, building_id: int | None = None) -> dict:
        """Estrutura completa do mês:
        { year, month, today (iso), next_due_date (iso|None),
          days: [ { day, date (iso), weekday (PT), items: [item, ...] }, ... ],
          stats: {...} }  (stats = get_month_stats).
        Cada item (dict) conforme design §4.1:
          lease_id, tenant_name, apartment_number, building_number,
          rental_value (str Decimal), is_paid, payment_date (iso|None),
          is_overdue, day_passed, can_toggle, late_fee (str Decimal), late_days.
        Regras (design §4.1):
          - clamped_due = clamp_due_day(responsible_tenant.due_day, year, month) → clamped_due_date.
          - is_current_month = (year, month) == (today.year, today.month).
          - day_passed = clamped_due_date < today.
          - is_paid = existe RentPayment ativo (lease, reference_month=dia 1).
          - is_overdue = (not is_paid) and day_passed and (mês corrente OU mês passado)
            — overdue só faz sentido para o mês corrente/passado (design §4.1 linha 120).
          - month_finalized = MonthSnapshot finalizado para o mês.
          - can_toggle = (not month_finalized) and not (is_paid and day_passed).
          - late_fee/late_days: SOMENTE quando is_overdue E is_current_month → via
            FeeCalculatorService.calculate_late_fee(effective_value, clamped_due, today).
            Em QUALQUER outro caso (mês não-corrente, não-overdue) → late_fee="0.00", late_days=0.
            (Ver §"Multa só no mês corrente" para a justificativa.)
        next_due_date = menor clamped_due_date >= today entre itens NÃO pagos (ou None).
        O rótulo do mês NÃO é retornado (derivado no frontend)."""

    @staticmethod
    def get_month_stats(year: int, month: int, building_id: int | None = None) -> dict:
        """Design §4.5:
          received_total   = Σ amount_paid de TODOS os RentPayment ativos do mês
                             (reference_month = dia 1), SEM filtro de cobrabilidade —
                             ver §"Definição canônica de received_total".
          to_receive_total = Σ effective_rental_value dos collectible_leases SEM RentPayment ativo
          expected_total   = received_total + to_receive_total
          paid_count, due_count (= len collectible_leases), overdue_count, overdue_total_fee
          vacant_kitnets_count / vacant_kitnets_value = Apartment.objects.filter(is_rented=False)
            (manager padrão já exclui deletados), filtrado por building_id se aplicável →
            count + Σ rental_value.
          overdue_count/overdue_total_fee: contados apenas no mês corrente/passado; multa só no
            mês corrente (consistente com get_month_schedule).
        Todos os valores monetários como str de Decimal."""

    @staticmethod
    def toggle_payment(lease_id: int, reference_month: date, user: User) -> dict:
        """Cria ou soft-deleta o RentPayment do mês. Defesa em profundidade (revalida tudo):
          - reference_month deve ser normalizado para o dia 1 (defensivo).
          - lease deve ser cobrável no mês (estar em collectible_leases(reference_month)); senão recusa (PT).
          - mês finalizado (MonthSnapshot.is_finalized) → recusa (PT).
          - se já pago E dia já passou (clamped_due_date < today, no mês corrente) → recusa desmarcar (PT).
        Ações:
          - não pago → cria RentPayment(amount_paid=effective_rental_value, payment_date=today,
            created_by=user, updated_by=user). Usar transaction.atomic + select_for_update no lease.
          - pago (e permitido) → soft-delete do RentPayment (instance.delete() — soft delete).
        Retorna { status: 'ok'|'error', is_paid: bool, message: str (PT) }."""
```

### Definição canônica de `received_total` (resolve a ambiguidade DRY)

O `_get_received_rent_total` atual (`daily_control_service.py:704-710`) soma `amount_paid` de **TODOS** os `RentPayment.objects.filter(reference_month=month_start)` — **sem** filtro de cobrabilidade. Para manter **comportamento idêntico** e **uma única definição** (DRY), a definição **canônica** de "aluguel recebido" é:

> `received_total` = Σ `amount_paid` de todos os `RentPayment` **ativos** cujo `reference_month` é o dia 1 do mês — **SEM** pré-filtrar por `collectible_leases`.

Implicações obrigatórias:
- `RentScheduleService.get_month_stats.received_total` **NÃO** filtra por cobrabilidade (a Especificação acima já reflete isso).
- `daily_control_service._get_received_rent_total` **delega** a essa mesma fonte (p.ex. um helper estático em `RentScheduleService`, ou `get_month_stats(...)["received_total"]` convertido para `Decimal`). Não pode existir uma segunda definição.
- `to_receive_total` e `due_count` continuam baseados em `collectible_leases` (esses sim filtrados), pois são "a receber"/"devido", não "recebido".

### Multa só no mês corrente (resolve o caveat de cross-month)

`FeeCalculatorService.calculate_late_fee` (`fee_calculator.py:82-86`) calcula `late_days = current_date.day - due_day` usando **apenas o dia do mês**. Como o calendário navega entre meses, passar um `due_day` clampado de um mês com `today` de outro mês produziria `late_days` **errado/negativo**. Regra obrigatória:

- `late_fee`/`late_days` só são calculados via `calculate_late_fee` quando o item é `is_overdue` **E** o mês exibido é o **mês corrente** (`(year, month) == (today.year, today.month)`).
- Em qualquer mês diferente do corrente → `late_fee = "0.00"`, `late_days = 0` (mesmo que `is_overdue` seja `True` para um mês passado não pago — a multa exibida só vale para o mês corrente, conforme design §4.1 linha 120).
- Isso vale tanto em `get_month_schedule` (por item) quanto em `get_month_stats.overdue_total_fee`.

### Constante de dias da semana (DRY)

`DAYS_OF_WEEK_PT` hoje vive em `daily_control_service.py:34-42`. Mover para `rent_schedule_service.py` (fonte única) e fazer `daily_control_service.py` **importar de lá** (import direto da fonte, **sem re-export, sem barrel, sem shim**). Atualizar todos os usos (`daily_control_service.py:106`).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> Mock policy (`tests/CLAUDE.md`): **mockar APENAS fronteiras externas**. Aqui isso significa **somente `freezegun`** para congelar a data (relógio do sistema). **NUNCA** mockar ORM, services internos, `FeeCalculatorService`, `DateCalculatorService` ou código de biblioteca. Banco real via `--reuse-db`. Dados via factories (`model-bakery`).

### 1. RED — escrever os testes primeiro

Criar `tests/unit/test_financial/test_rent_schedule_service.py`. Usar `@pytest.mark.django_db`, factories de `tests/factories.py` e `freeze_time`. Cobrir, no mínimo:

**`clamp_due_day`**
- [ ] 31 → fevereiro/2026 retorna 28 (não bissexto).
- [ ] 31 → fevereiro/2024 retorna 29 (bissexto).
- [ ] 31 → abril (30 dias) retorna 30.
- [ ] 10 → março retorna 10 (sem clamp).

**`effective_rental_value`**
- [ ] sem `pending_rental_value` → retorna `rental_value`.
- [ ] `reference_month` antes de `pending_rental_value_date` → retorna `rental_value` atual.
- [ ] `reference_month` igual/depois de `pending_rental_value_date` → retorna `pending_rental_value` (aumento pendente em vigor).

**`collectible_leases`**
- [ ] inclui lease ativo padrão cuja janela cobre o mês.
- [ ] **exclui** lease cujo `apartment.owner` está definido (repasse).
- [ ] **exclui** lease com `is_salary_offset=True`.
- [ ] **exclui** lease com `prepaid_until >= reference_month` (mês pré-pago).
- [ ] **exclui** lease cuja janela `start_date..end_date` NÃO intersecta o mês (ex.: contrato que terminou antes do mês, ou que começa depois) — **date-aware, independente de `is_rented`**. Incluir caso explícito: lease com `is_rented=True` mas janela fora do mês → **excluído**; e lease cuja janela cobre o mês com `is_rented` qualquer → **incluído**.
- [ ] `building_id` filtra por prédio (lease de outro prédio não aparece).
- [ ] não inclui lease soft-deleted.

**`get_month_schedule` / item**
- [ ] item aparece no dia certo (clamped) com `tenant_name`, `apartment_number`, `building_number`, `rental_value`.
- [ ] item pago (`RentPayment` ativo existe) → `is_paid=True`, `payment_date` preenchido.
- [ ] (mês corrente) item não pago com dia já vencido (`freeze_time` após o vencimento, mesmo mês) → `is_overdue=True`, `late_days>0`, `late_fee` > "0.00" (bate exatamente com `FeeCalculatorService.calculate_late_fee`).
- [ ] **(cross-month)** item de mês NÃO-corrente (ex.: `freeze_time("2026-06-15")`, consultar abril/2026) — mesmo vencido/não-pago → `late_fee="0.00"` e `late_days=0` (nunca multa espúria de outro mês). Asserir explicitamente.
- [ ] `can_toggle=False` quando pago e dia já passou.
- [ ] `next_due_date` aponta para o menor vencimento futuro não pago.

**`get_month_stats`**
- [ ] `received_total` soma `amount_paid` de **todos** os `RentPayment` ativos do mês — incluindo um caso onde existe pagamento de um lease que **não** está em `collectible_leases` (ex.: lease com owner) para provar que NÃO é pré-filtrado por cobrabilidade.
- [ ] `to_receive_total` soma valor efetivo de cobráveis sem pagamento; `expected_total = received + to_receive`.
- [ ] `vacant_kitnets_count`/`vacant_kitnets_value` = apartamentos `is_rented=False` (count + Σ `rental_value`), respeitando `building_id`.
- [ ] `overdue_count`/`overdue_total_fee` corretos sob `freeze_time` no mês corrente; e `overdue_total_fee` não acumula multa de mês não-corrente.

**`toggle_payment` (design §4.4)**
- [ ] não pago + a vencer → cria `RentPayment` (`is_paid=True`, `amount_paid == effective_rental_value`, `payment_date == today`), `status='ok'`.
- [ ] não pago + em atraso → cria `RentPayment` com `payment_date=today`, `status='ok'`.
- [ ] pago + dia NÃO passou → soft-delete (`RentPayment.objects` não acha; `all_objects` acha com `is_deleted=True`), `is_paid=False`.
- [ ] pago + dia JÁ passou → **recusa** (`status='error'`, mensagem PT), registro permanece ativo.
- [ ] mês finalizado (`baker.make("core.MonthSnapshot", reference_month=..., is_finalized=True)`) → **recusa** (`status='error'`).
- [ ] lease não cobrável (owner/offset/prepaid) → **recusa**.
- [ ] toggle cria → soft-deleta → cria de novo funciona (UniqueConstraint condicional a `is_deleted=False`).

> Rodar (devem **falhar**, pois o service ainda não existe):
> ```bash
> python -m pytest tests/unit/test_financial/test_rent_schedule_service.py -q
> ```

### 2. GREEN — implementar `RentScheduleService`

Criar `core/services/rent_schedule_service.py` implementando os 6 métodos conforme a Especificação. O mínimo para os testes passarem, reusando `FeeCalculatorService.calculate_late_fee` e `DateCalculatorService.calculate_final_date` (não reimplementar multa nem fim de contrato — DRY). Rodar até verde:
```bash
python -m pytest tests/unit/test_financial/test_rent_schedule_service.py -q
```

### 3. REFACTOR — DRY no `DailyControlService` (comportamento equivalente) + reconciliação da fixture

#### Reconciliação obrigatória da fixture `lease` (PRÉ-REQUISITO da troca de filtro)

> **Por que isto é necessário (não é opcional):** o filtro atual do `DailyControlService` usa `apartment__is_rented=True`; o novo `collectible_leases` é **date-aware** (janela `start_date..end_date`). A fixture `lease` compartilhada (`test_daily_control_service.py:52-60`) usa `start_date=date(2025, 1, 1)`, `validity_months=12` → `DateCalculatorService.calculate_final_date` ⇒ `end_date = 2026-01-01`. Os testes `test_rent_entries_on_due_day` (:79), `test_summary_totals` (:183) e `test_current_balance` (:220) consultam **março/2026** (`get_daily_breakdown(2026, 3)` / `get_month_summary(2026, 3)`, linhas 72/81/191/246). Sob `is_rented=True` o lease aparece; sob a janela `2025-01-01..2026-01-01` a interseção com março/2026 é **vazia**, então o lease seria **excluído** e esses 3 testes **falhariam**.
>
> A `collectible_leases` é a **fonte única** (design §4) e **prevalece** — portanto NÃO se reverte a troca de filtro. A reconciliação se faz **na fixture** (setup de dados, não asserção): editar **somente** `start_date` da fixture `lease` (`:52-60`) para que a janela cubra março/2026 — por exemplo `start_date=date(2025, 6, 1)` com `validity_months=12` ⇒ `end_date = 2026-06-01`, cuja janela `2025-06-01..2026-06-01` **contém** março/2026.

Instruções concretas da reconciliação:
- Editar **apenas** o argumento `start_date` da fixture `lease` (`test_daily_control_service.py:52-60`) para um valor cuja janela `start_date..end_date` contenha março/2026 (ex.: `date(2025, 6, 1)`). Manter `validity_months=12`, `rental_value`, `tag_fee` e os demais campos.
- **NÃO** alterar nenhum corpo de teste, nenhuma assertion, nenhuma outra fixture. Os 16 testes devem passar **inalterados** salvo essa única linha de `start_date`.
- Após a edição, confirmar que `due_day=7` (fixture `tenant`) e os asserts de "dia 7" / totais R$1200 continuam válidos (a mudança de `start_date` não afeta `due_day` nem `rental_value`).

#### Equivalência de comportamento — funções módulo-nível

> Estas são **funções módulo-nível** em `daily_control_service.py` (não métodos da classe), chamadas pela classe em `:78`, `:142`, `:147`. **Preservar as assinaturas** para não quebrar os call sites.

- `_collect_entries_by_day` (porção aluguel, `:337-365`): substituir o queryset inline (`Lease.objects.filter(apartment__is_rented=True)...`) + `min(due_day, days_in_month)` por `RentScheduleService.collectible_leases(month_start)` + `RentScheduleService.clamp_due_day(...)`. Manter **exatamente** a forma do dict `entry` atual (chaves `type`, `description`, `amount` (float), `expected`, `paid`, `payment_date`). O `amount` continua `float(lease.rental_value)` — **não** o valor efetivo (preservar o comportamento que os testes assumem).
- `_get_expected_rent_total` (`:669-680`): delegar a `RentScheduleService.collectible_leases(month_start)` e somar `lease.rental_value` (não o efetivo — preservar comportamento atual).
- `_get_received_rent_total` (`:704-710`): delegar à **definição canônica** de `received_total` (ver §"Definição canônica de `received_total`") — Σ `amount_paid` de todos os `RentPayment` ativos do mês, **sem** filtro de cobrabilidade. Resultado idêntico ao atual; zero duplicação.
- Mover `DAYS_OF_WEEK_PT` para `rent_schedule_service.py` e importar de lá no `daily_control_service.py` (`:106` e demais usos) — fonte única, import direto, sem re-export.

Rodar regressão (devem ficar **16/16 verdes** com apenas a fixture ajustada):
```bash
python -m pytest tests/unit/test_financial/test_daily_control_service.py -q
```

### 4. VERIFY — qualidade nos arquivos tocados

Rodar **apenas nos arquivos editados** (a suíte completa tem problemas pré-existentes de xdist/Redis — memória do projeto):
```bash
python -m pytest tests/unit/test_financial/test_rent_schedule_service.py tests/unit/test_financial/test_daily_control_service.py -q
ruff check core/services/rent_schedule_service.py core/services/daily_control_service.py tests/unit/test_financial/test_rent_schedule_service.py tests/unit/test_financial/test_daily_control_service.py
ruff format --check core/services/rent_schedule_service.py core/services/daily_control_service.py tests/unit/test_financial/test_rent_schedule_service.py tests/unit/test_financial/test_daily_control_service.py
mypy core/services/rent_schedule_service.py core/services/daily_control_service.py
pyright core/services/rent_schedule_service.py core/services/daily_control_service.py
```

---

## Constraints

- **Direção de dependência**: Views → Services → Models. O service só importa de `core.models` e de outros services (`fee_calculator`, `date_calculator`). **Nunca** importar views/serializers.
- **DRY**: zero duplicação da lógica de "aluguel cobrável" e de "aluguel recebido". `DailyControlService` passa a **delegar**; multa via `FeeCalculatorService`; fim de contrato via `DateCalculatorService`. `DAYS_OF_WEEK_PT` em fonte única. **Uma única** definição de `received_total`.
- **SOLID/KISS/YAGNI**: funções pequenas e focadas; sem cache, sem campos especulativos, sem parâmetros não usados.
- **Multa cross-month**: `late_fee`/`late_days`/`overdue_total_fee` só são calculados via `calculate_late_fee` para o **mês corrente**; meses não-correntes → `"0.00"`/`0`.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código de verdade. Tipos completos (mypy strict + pyright).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** — importar tipos diretamente (ex.: `from django.db.models import QuerySet`, `from django.contrib.auth.models import User`).
- **Sem re-exports / sem barrel files / sem shims de compatibilidade.**
- **Soft delete**: desmarcar = `instance.delete()` (soft). Validar slots com `RentPayment.objects` (exclui deletados) vs `RentPayment.all_objects` (inclui) nos testes.
- **Mock policy**: só `freezegun`. Nada de mock de ORM/services/lib.
- **Sem migration / sem mudança de model / serializer / URL / view.**
- **Não tocar** `mark_rent_paid` (Sessão 25) nem criar endpoints (Sessão 22).
- **Não alterar corpos/asserts** dos 16 testes do `DailyControlService` — só a fixture `lease` (`start_date`).
- Mensagens de erro ao usuário em **Português**; logs/devs em **Inglês**.
- Dinheiro em `Decimal`; valores no retorno serializados como `str` (como os demais endpoints do dashboard).

---

## Critérios de Aceite (binários)

- [ ] `core/services/rent_schedule_service.py` criado com `RentScheduleService` e os 6 `@staticmethod` (`clamp_due_day`, `effective_rental_value`, `collectible_leases`, `get_month_schedule`, `get_month_stats`, `toggle_payment`).
- [ ] `tests/unit/test_financial/test_rent_schedule_service.py` criado cobrindo todos os cenários listados, incluindo: clamping fev/abr + bissexto; valor efetivo c/ aumento pendente; filtro cobrável date-aware (independente de `is_rented`) excluindo owner/offset/prepaid + janela + building + soft-delete; schedule/item com overdue+multa+can_toggle+next_due_date; **caso cross-month sem multa espúria**; stats com `received_total` **não** pré-filtrado por cobrabilidade + to_receive/expected/vacant/overdue; toggle create+soft-delete + guards (dia-passou, mês-finalizado, lease não-cobrável) + recriação do slot.
- [ ] `python -m pytest tests/unit/test_financial/test_rent_schedule_service.py` passa 100%.
- [ ] `collectible_leases` é a fonte única date-aware (não usa `apartment__is_rented`); `_collect_entries_by_day` (rent) e `_get_expected_rent_total` delegam a ela.
- [ ] `received_total` tem **uma única** definição (Σ `amount_paid` de todos os `RentPayment` ativos do mês, sem filtro de cobrabilidade); `_get_received_rent_total` delega à mesma fonte.
- [ ] `DAYS_OF_WEEK_PT` em fonte única (no novo service), importado diretamente pelo `daily_control_service.py` (sem re-export).
- [ ] Fixture `lease` (`test_daily_control_service.py:52-60`) ajustada **apenas** no `start_date` para cobrir março/2026; nenhum corpo/assert dos 16 testes alterado.
- [ ] `python -m pytest tests/unit/test_financial/test_daily_control_service.py` fica **16/16 verdes**.
- [ ] Multa só calculada no mês corrente; itens de mês não-corrente reportam `late_fee="0.00"`/`late_days=0` (com teste asserindo isso).
- [ ] `ruff check` e `ruff format --check` limpos nos arquivos tocados.
- [ ] `mypy` e `pyright` limpos nos arquivos tocados — **sem** `# noqa`/`# type: ignore`.
- [ ] Nenhum endpoint/view/serializer/URL/migration/frontend alterado; `mark_rent_paid` intacto.

---

## Handoff

1. Rodar e confirmar verde:
   ```bash
   python -m pytest tests/unit/test_financial/test_rent_schedule_service.py tests/unit/test_financial/test_daily_control_service.py -q
   ruff check core/services/rent_schedule_service.py core/services/daily_control_service.py tests/unit/test_financial/test_rent_schedule_service.py tests/unit/test_financial/test_daily_control_service.py
   mypy core/services/rent_schedule_service.py core/services/daily_control_service.py
   pyright core/services/rent_schedule_service.py core/services/daily_control_service.py
   ```
2. Atualizar `prompts/SESSION_STATE.md`:
   - Adicionar linha da Sessão 21 (status **concluída**) na tabela de progresso.
   - Listar **Arquivos Criados** (`core/services/rent_schedule_service.py`, `tests/unit/test_financial/test_rent_schedule_service.py`) e **Arquivos Modificados** (`core/services/daily_control_service.py`, `tests/unit/test_financial/test_daily_control_service.py` — só a fixture `lease`).
   - Anotar nota: "Fonte única `RentScheduleService` (cobrabilidade date-aware); `DailyControlService` delega (DRY: collectible_leases + received_total único); fixture `lease` ajustada (start_date) para cobrir mar/2026; multa só no mês corrente; 16 testes do DailyControl verdes; sem endpoints/frontend; `mark_rent_paid` removido apenas na Sessão 25."
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`, criar branch se necessário):
   ```
   feat(backend): add RentScheduleService as single source of rent-due logic + DRY refactor of DailyControlService

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **22 — Backend: endpoints `rent_calendar`/`toggle_rent_payment`** (lê o `SESSION_STATE.md` atualizado). A Sessão 22 **adiciona** os endpoints mas **não remove** `mark_rent_paid` (isso é da Sessão 25), mantendo todas as sessões verdes.
