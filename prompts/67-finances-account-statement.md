# Sessão 67 — Backend: `BillingAccountQuerySet.with_open_balance()` + `AccountStatementService` + `GET /api/finances/billing-accounts/{id}/statement` (UNCACHED)

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida (`docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`, rev. 2)
> **Sessões da feature**: 65 → 66 → **67** → 68 → 69 → 70 → 71–76 (FE)
> Esta sessão entrega o **saldo devedor por conta** (annotation `open_balance` — DOIS braços de FK, senão a conta IPTU registry-only zera) na listagem de `billing-accounts`, e o **extrato por conta** (design §3.4): `AccountStatementService.build(account_id, today)` com stats (saldo devedor, faturas em aberto, atraso médio), linhas mês a mês e planos vinculados com progresso — mais a action **UNCACHED** `GET billing-accounts/{id}/statement`. **Sem `month_board` (S66 é irmã, não tocar); sem `new_total` no `pay` (S68); sem `apply_invoice` (S69); sem `consolidate_debt` (S70 — o CTA "Parcelar saldo devedor" é FE/S73 sobre o serviço da S70); zero frontend (S71–76); nada da Fase 2.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.2 coluna `open_balance`, §3.4 "Extrato por conta" inteiro, §4 tabela de API — linhas `statement` e `billing-accounts` list, §9 testes de `statement`/`open_balance`, §10 "Dinheiro via ORM annotation")**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado + contratos AUTORITATIVOS (S67 no SESSION_STATE prevalece sobre este prompt)**: `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — VERIFICADOS; ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Subqueries correlacionadas de dinheiro (ESTILO A COPIAR)** | `finances/models.py:223-273` (`with_amounts`: `total_subquery` sobre `BillLineItem` `:231-238`; `paid_subquery` sobre `PaymentAllocation` com **`payment__is_deleted=False`** `:242-248`; `Coalesce`+`_ZERO_MONEY` `:249-254`) | `with_open_balance` é construído **explícito neste estilo** — subqueries escalares por braço somadas com `Coalesce`. O filtro de pagamento vivo (`:242-248`) é espelhado verbatim (alocação viva + payment vivo) |
| **`BillingAccountQuerySet` (onde o método entra)** | `finances/models.py:132-148` (`recurring_for_generation` + `BillingAccountManager = SoftDeleteManager.from_queryset(...)` `:148`) | O manager já propaga métodos do queryset — adicionar `with_open_balance` ao queryset o expõe em `BillingAccount.objects` sem mais nada |
| **Os DOIS braços de FK até a conta** | `finances/models.py:325-330` (`Bill.billing_account` + `Bill.installment`) + `:563-569` (`InstallmentPlan.billing_account`) — cadeia `bill.installment.plan.billing_account` | Bills de parcela IPTU são standalone: `billing_account=None`, vínculo só via `installment__plan__billing_account` (decisão S64 — setar os dois colidiria na unique `:355-359`). Sem o braço 2 a conta IPTU zera |
| **Estados/lifecycle** | `finances/models.py:55-59` (`BillLifecycleState`) | `open_balance` = bills **não-canceladas** (ACTIVE+SUSPENDED+DEFERRED), não-deletadas |
| **`BillingAccountSerializer` (ganha `open_balance`) + getters money do `BillSerializer`** | `finances/serializers.py:131-184` (fields/Meta) + `:391-398` (idioma `money_str(getattr(obj, "amount_...", Decimal(0)))`) | `open_balance` = `SerializerMethodField` lendo a annotation com fallback `Decimal(0)` (lista sem annotation não quebra) |
| **`BillingAccountViewSet` (queryset + nova action)** | `finances/viewsets/crud_views.py:121-141` | `get_queryset` passa a anotar `with_open_balance(today_sp())`; a action `statement` entra aqui (`@action(detail=True)`; `IsAdminUser` herdado; `get_object()` → 404 automático p/ conta inexistente/soft-deletada) |
| **Action UNCACHED com comentário-justificativa** | `finances/viewsets/dashboard_views.py:279-305` (`iptu_alerts`, comentário `:281-282`) | Molde do comentário NO-cache do `statement` (estado de pagamento + `today_sp()`) |
| **Progresso de materialização de plano (espelhar a leitura)** | `finances/services/bill_generation_service.py:325-349` (`_mark_completed_plans_materialized`: embedded → `BillLineItem.objects.filter(installment=...)`; standalone → `Bill.objects.filter(installment=...)`) | `plans[].materialized_count` conta parcelas materializadas com **exatamente** esses filtros (managers vivos) |
| **Serviço que serializa com serializer do módulo (precedente)** | `finances/services/invoice_draft_service.py:23` | `AccountStatementService` pode usar `BillingAccountSerializer` p/ a chave `account`; nunca importa views |
| **Factories** | `tests/factories.py:286` (`make_billing_account`), `:301` (`make_bill`), `:317` (`make_bill_line_item`), `:328` (`make_installment_plan`), `:346` (`make_installment`), `:385` (`make_payment`), `:400` (`make_payment_allocation`) | Dados dos testes (conta IPTU: plano `embedded=False` + parcelas + bills standalone com `installment=...` e `billing_account=None`) |
| Mock policy | `tests/CLAUDE.md` | Sem fronteira externa — **zero mocks**; `today` explícito nos testes de serviço |

### O que a S65/S66 já entregaram (PRÉ-REQUISITO)
- **S65**: `Bill.amount_is_estimated` + `BillSerializer` read-only — as linhas `months[]` do extrato expõem esse campo. **Se a S65 não estiver concluída no branch, PARE.**
- **S66**: `month_board` — irmã; esta sessão NÃO depende dela em código, mas roda depois no branch para evitar conflito em `crud_views.py`/`dashboard_views.py`.

---

## Escopo

### Arquivos a criar
- `finances/services/account_statement_service.py` — `AccountStatementService.build(account_id, today) -> dict`.
- `tests/unit/test_finances/test_billing_account_open_balance.py` — annotation (braços/exclusões/vivos).
- `tests/unit/test_finances/test_account_statement_service.py` — stats/months/plans.
- `tests/integration/test_finances/test_finance_account_statement_api.py` — action + `open_balance` na listagem.

### Arquivos a modificar
- `finances/models.py` — `BillingAccountQuerySet.with_open_balance(today)`.
- `finances/serializers.py` — `BillingAccountSerializer` ganha `open_balance` read-only (string decimal).
- `finances/viewsets/crud_views.py` — `BillingAccountViewSet.get_queryset` anota `with_open_balance(today_sp())`; nova action `statement`.

### NÃO fazer (pertence a outras sessões)
- **`CondoMonthBoardService`/`month_board`** — **S66** (não tocar).
- **`pay` com `new_total`** — **S68**. Esta sessão NÃO mexe em `BillPaymentService`.
- **`apply_invoice` / `building` no draft do parser** — **S69**.
- **`consolidate_open_bills` / `POST billing-accounts/{id}/consolidate_debt`** — **S70** (o extrato só LÊ; o botão "Parcelar" é S73/S75).
- **Frontend** (`useAccountStatement`/página `[id]`/StatCards) — **S71/S73**.
- **Sem migração/model novo** (annotation, não coluna); **sem cache** nos endpoints; nada da Fase 2 (terceiros).
- **Não** agregar `amount_remaining` do `with_amounts` (sem precedente de Sum-sobre-annotation-de-subquery; construir explícito).

---

## Especificação

> Dinheiro SEMPRE via annotation ORM (design §10 — nunca `@property`). "Hoje" do caller (`today_sp()` no viewset; import de `core.services.timezone`). Money serializado com `money_str`. Mensagens PT; identificadores EN.

### 1. `BillingAccountQuerySet.with_open_balance(today: date) -> BillingAccountQuerySet` (`finances/models.py`)

Annotation `open_balance` = Σ (`amount_total − amount_paid`) das bills **não-canceladas** (ACTIVE+SUSPENDED+DEFERRED) e **não-deletadas** da conta, somando os **DOIS braços** (contrato AUTORITATIVO):

- **Braço A (FK direta)**: bills com `billing_account = OuterRef("pk")`.
- **Braço B (parcela standalone)**: bills com `installment__plan__billing_account = OuterRef("pk")` — **excluindo** as já cobertas pelo braço A (`billing_account` da própria conta), para dupla contagem ser impossível por construção.

Implementação **explícita no estilo `models.py:231-248`** (NÃO agregar `amount_remaining` de `with_amounts`): por braço, uma subquery escalar de total de linhas (`BillLineItem`, net não-offset − offset) e uma de pago (`PaymentAllocation` com `payment__is_deleted=False` — espelho verbatim de `:242-248`), cada uma filtrando `bill__is_deleted=False` e `bill__lifecycle_state` ≠ CANCELED (managers de linha/alocação já excluem os próprios soft-deletados, mas NÃO o estado do bill — filtrar explícito). As "duas subqueries" do contrato = os dois braços de FK; cada braço se decompõe em lines−paid no estilo `with_amounts` (`models.py:231-248`) — o total de 4 subqueries é a leitura correta, não uma divergência. Hint: o `.values(...)` de agrupamento de cada subquery deve ser o lookup até a CONTA (ex.: `.values("billing_account")` / `.values("installment__plan__billing_account")`), não `.values("bill")` — senão a soma sai por bill, não por conta. Composição final:

```python
open_balance = (
    Coalesce(lines_direct, _ZERO_MONEY) - Coalesce(paid_direct, _ZERO_MONEY)
    + Coalesce(lines_installment, _ZERO_MONEY) - Coalesce(paid_installment, _ZERO_MONEY)
)
```

`today` faz parte da assinatura do contrato (paridade com `with_amounts`; o saldo em si não depende da data — documentar no docstring, sem usar a data em filtro).

### 2. `BillingAccountSerializer` (`finances/serializers.py`)

`open_balance = serializers.SerializerMethodField()` + entrada em `fields`; getter no idioma de `BillSerializer.get_amount_total` (`:391-392`): `money_str(getattr(obj, "open_balance", Decimal(0)))` → string decimal. Read-only por natureza (MethodField).

### 3. `BillingAccountViewSet.get_queryset` (`crud_views.py:126-141`)

Base vira `BillingAccount.objects.with_open_balance(today_sp()).select_related(...)` — a listagem `/api/finances/billing-accounts/` passa a carregar `open_balance` (design §4: **sem cache, como hoje** — o viewset não tem cache).

### 4. `AccountStatementService.build(account_id: int, today: date) -> dict[str, object]` (`finances/services/account_statement_service.py`)

```python
class AccountStatementService:
    @staticmethod
    def build(account_id: int, today: date) -> dict[str, object]:
        """Extrato da conta (design §3.4). Read-only, uncached. Sempre chamado com today_sp().
        Bills agregadas pelos DOIS braços: Q(billing_account=conta) | Q(installment__plan__billing_account=conta)."""
```

Payload (contrato AUTORITATIVO — SESSION_STATE S67, verbatim):

```python
{
    "account": {...},   # BillingAccountSerializer (com open_balance) da conta anotada
    "stats": {"open_balance": str, "open_bills_count": int, "avg_delay_days": int | None},
    "months": [
        {"bill_id": int, "competence_month": "YYYY-MM-DD", "due_date": "YYYY-MM-DD",
         "description": str, "amount_total": str, "amount_paid": str, "amount_remaining": str,
         "payment_status": str, "lifecycle_state": str, "amount_is_estimated": bool,
         "paid_date": "YYYY-MM-DD" | None},
    ],
    "plans": [
        {"id": int, "description": str, "installment_count": int, "materialized_count": int,
         "lifecycle_state": str, "embedded": bool},
    ],
}
```

Regras:

1. **Fonte das bills**: `Bill.objects.with_amounts(today).filter(Q(billing_account=account) | Q(installment__plan__billing_account=account))` — o OR não duplica linhas; excluir CANCELED (decisão de produto "CANCELED invisível"; pós-consolidação/S70 a dívida vive só no plano). Ordenar `months` por `competence_month` desc, depois `due_date` desc (mais recente primeiro). Money via `money_str`.
2. **`paid_date`** por bill = `MAX(payment_date)` das alocações **vivas** com payment **vivo** (`allocation.is_deleted=False AND payment__is_deleted=False` — espelhar `models.py:242-248`); `None` sem pagamento vivo. Implementar como subquery correlacionada escalar (estilo `:242-248`), anotada junto no queryset das bills.
3. **`stats.open_balance`** = a annotation da conta (`with_open_balance(today)`) formatada com `money_str` — MESMO critério da listagem (nunca recomputar diferente).
4. **`stats.open_bills_count`** = nº de bills não-canceladas (dos dois braços) com `amount_remaining > 0`.
5. **`stats.avg_delay_days`** = média (arredondada p/ `int` via `round()`) de `(paid_date − due_date).days` das **últimas 12** bills **quitadas** — `amount_remaining == 0` **e** `amount_total > 0` (exclui total-zero) — ordenadas por `due_date` desc; ignorar defensivamente quitada sem `paid_date`; `None` se não houver nenhuma quitada elegível. Pode ser **negativo** (paga adiantado). Calculado sobre o MESMO conjunto de bills da tabela `months[]` (regra 1 — que já exclui CANCELED e deletadas).
6. **`plans`** = `InstallmentPlan.objects.filter(billing_account=account)` (manager vivo; embutidos E avulsos, qualquer `lifecycle_state`). `materialized_count` = parcelas do plano já materializadas — embedded: `BillLineItem.objects.filter(installment=inst).exists()`; standalone: `Bill.objects.filter(installment=inst).exists()` (espelho de `bill_generation_service.py:325-349`). Progresso N/M do FE (S73) = `materialized_count`/`installment_count`.
7. **Conta IPTU (registry-only)**: o extrato vem quase todo do braço `installment` — as parcelas standalone têm `billing_account=None`; o teste dedicado trava que months/stats NÃO ficam vazios/zerados.
8. **Sem writes** — serviço 100% read-only.

### 5. Action `statement` (em `BillingAccountViewSet`)

```python
@action(detail=True, methods=["get"])
def statement(self, request: Request, pk: str | None = None) -> Response:
    # NO cache (design §4/§10): depends on payment state + today_sp(); midnight rollover is
    # not a write, so cache would never be invalidated — same rationale as month_board/overdue.
    account = self.get_object()  # 404 p/ conta inexistente/soft-deletada (manager vivo)
    return Response(AccountStatementService.build(account.pk, today_sp()), status=status.HTTP_200_OK)
```

`IsAdminUser` herdado (`:123`) — 403 não-staff, 401 anônimo. Rota auto-exposta (`billing-accounts/{id}/statement/`) — `finances/urls.py` intacto.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: zero mocks (sem fronteira externa). Banco real (`--reuse-db`), factories, `today` explícito. Zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_billing_account_open_balance.py`

```python
class TestWithOpenBalance:
    def test_open_balance_sums_direct_bills(self) -> None:
        """Bills com FK direta billing_account somam total−pago no open_balance."""

    def test_open_balance_includes_installment_arm(self) -> None:
        """Parcelas standalone (installment→plan→billing_account, billing_account=None) contam — conta IPTU não zera."""

    def test_open_balance_no_double_count_across_arms(self) -> None:
        """Bill que casaria nos dois braços conta UMA vez (braço B exclui as do braço A)."""

    def test_open_balance_partial_payment_counts_rest(self) -> None:
        """Pagamento parcial: entra só o resto (total − alocações vivas)."""

    def test_open_balance_excludes_canceled(self) -> None:
        """Bill CANCELED (mesmo com resto) fica fora; SUSPENDED/DEFERRED entram."""

    def test_open_balance_excludes_soft_deleted_bills(self) -> None:
        """Bill soft-deletada fica fora dos dois braços."""

    def test_open_balance_ignores_dead_allocations_and_payments(self) -> None:
        """Alocação soft-deletada OU payment soft-deletado não abate o saldo (espelho de with_amounts)."""

    def test_open_balance_zero_without_bills(self) -> None:
        """Conta sem bills → open_balance == 0 (Coalesce), nunca None."""

    def test_open_balance_scoped_per_account(self) -> None:
        """Duas contas: cada open_balance só enxerga as próprias bills (subquery correlacionada)."""
```

#### `tests/unit/test_finances/test_account_statement_service.py`

```python
class TestStatementMonths:
    def test_months_include_both_arms(self) -> None:
        """months traz bills da FK direta E das parcelas standalone da conta (sem duplicar)."""

    def test_months_exclude_canceled_and_other_accounts(self) -> None:
        """CANCELED e bills de outra conta ficam fora."""

    def test_month_row_shape_and_money_strings(self) -> None:
        """Linha tem bill_id/competence_month/due_date/description/amount_*/payment_status/lifecycle_state/amount_is_estimated/paid_date; money em string."""

    def test_months_ordered_most_recent_first(self) -> None:
        """Ordenação: competence_month desc, due_date desc."""

    def test_paid_date_is_max_live_payment_date(self) -> None:
        """Dois pagamentos: paid_date = MAX(payment_date); payment soft-deletado é ignorado; sem pagamento → None."""


class TestStatementStats:
    def test_open_balance_matches_queryset_annotation(self) -> None:
        """stats.open_balance == with_open_balance da conta (mesmo critério da listagem), como string."""

    def test_open_bills_count(self) -> None:
        """Conta bills não-canceladas com resto>0 (dois braços); pagas/canceladas fora."""

    def test_avg_delay_days_mean_of_last_12(self) -> None:
        """13 quitadas: só as 12 mais recentes (due_date desc) entram na média."""

    def test_avg_delay_days_requires_fully_paid_and_positive_total(self) -> None:
        """Parciais e bills com amount_total==0 não entram."""

    def test_avg_delay_days_negative_when_paid_early(self) -> None:
        """Pagas antes do vencimento → média negativa (int)."""

    def test_avg_delay_days_null_without_settled_bills(self) -> None:
        """Sem quitada elegível → None."""


class TestStatementPlans:
    def test_plans_list_embedded_and_standalone_with_progress(self) -> None:
        """plans traz embutidos e avulsos da conta com materialized_count correto (linha p/ embedded, bill p/ standalone)."""

    def test_iptu_registry_account_statement_not_empty(self) -> None:
        """Conta IPTU: months/stats/plans vêm do braço installment (extrato não zera)."""
```

#### `tests/integration/test_finances/test_finance_account_statement_api.py`
`pytestmark = [pytest.mark.django_db, pytest.mark.integration]`.

```python
def test_statement_returns_full_shape(authenticated_api_client) -> None:
    """GET billing-accounts/{id}/statement → 200 {account, stats{open_balance,open_bills_count,avg_delay_days}, months, plans} (objeto plano)."""

def test_statement_404_for_unknown_or_deleted_account(authenticated_api_client) -> None:
    """id inexistente E conta soft-deletada → 404."""

def test_statement_forbidden_for_non_admin(regular_authenticated_api_client) -> None:
    """Não-staff → 403 (IsAdminUser)."""

def test_statement_requires_authentication(api_client) -> None:
    """Anônimo → 401."""

def test_statement_uncached_reflects_payment(authenticated_api_client) -> None:
    """Pagar uma bill da conta e re-GET → open_balance/months refletem sem stale (uncached)."""

def test_billing_accounts_list_includes_open_balance(authenticated_api_client) -> None:
    """GET billing-accounts/ → cada item traz open_balance (string decimal) via queryset anotado."""
```

> Rodar (devem **falhar** — annotation/serviço/action não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_billing_account_open_balance.py \
>   tests/unit/test_finances/test_account_statement_service.py \
>   tests/integration/test_finances/test_finance_account_statement_api.py -q
> ```

### 2. GREEN — implementar
1. `finances/models.py` — `with_open_balance` (subqueries explícitas, estilo `:231-248`).
2. `finances/serializers.py` — `open_balance` no `BillingAccountSerializer`.
3. `finances/services/account_statement_service.py` — `build` (months/stats/plans).
4. `crud_views.py` — queryset anotado + action `statement`.

### 3. REFACTOR — DRY / clareza
- Subqueries por braço em helpers privados nomeados no queryset (ex.: `_open_lines_subquery(arm_filter)` / `_open_paid_subquery(arm_filter)`) — os dois braços compartilham a construção, mudando só o lookup (DRY sem abstração especulativa).
- `avg_delay_days`/`paid_date`/progresso em funções privadas do serviço (SRP); docstring do `paid_date` cita o espelho de `with_amounts` (`models.py:242-248`).
- Confirmar que NENHUM valor monetário é recomputado a partir de linhas em Python (só annotations carregadas + `money_str`).

### 4. VERIFY — gate (escopo desta sessão)

```bash
python -m pytest tests/unit/test_finances/test_billing_account_open_balance.py \
  tests/unit/test_finances/test_account_statement_service.py \
  tests/integration/test_finances/test_finance_account_statement_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check && ruff format --check
mypy core/ finances/
pyright
python manage.py makemigrations --check --dry-run   # annotation não gera migração
```

> **Regressão obrigatória** (listagem/CRUD de billing-accounts + consumidores do queryset intactos):
> ```bash
> python -m pytest tests/unit/test_finances/test_billing_account_identity.py tests/unit/test_finances/test_recurring_for_generation.py \
>   tests/integration/test_billing_account_account_type_api.py tests/integration/test_finances/test_finance_crud_api.py -q
> ```

---

## Constraints

- **`open_balance` = annotation ORM** (design §10) — nunca `@property` Python, nunca `Sum` sobre `amount_remaining` do `with_amounts` (sem precedente; construir explícito no estilo `models.py:231-248`).
- **Dois braços obrigatórios** (`billing_account` + `installment__plan__billing_account`); dupla contagem impossível (braço B exclui braço A); CANCELED e soft-deleted fora; alocação viva + payment vivo (espelho de `:242-248`).
- **Lógica só no serviço/queryset**: a action resolve o 404 via `get_object()` e delega — zero regra na view.
- **UNCACHED** com comentário-justificativa (mesmo racional de `combined_calendar`/`overdue`/`month_board`); a listagem de `billing-accounts` segue sem cache (como hoje).
- **`today` do caller** (`today_sp()` no viewset); proibido `timezone.now().date()`.
- **Serializer dual pattern intacto** no `BillingAccountSerializer` (`open_balance` é read-only MethodField; campos `_id` de escrita inalterados).
- **Sem suppressions** (`# noqa`/`# type: ignore`), sem `from __future__`, sem `TYPE_CHECKING`, sem re-exports. Annotation lida com `getattr(..., Decimal(0))` (idioma `serializers.py:391-398`).
- **Sem migração** (annotation, não coluna); **não tocar** `BillPaymentService`/`InstallmentPlanService`/`month_board`. Mensagens PT.

## Critérios de Aceite (binários)

- [ ] `BillingAccountQuerySet.with_open_balance(today)` anota `open_balance` (dois braços, não-canceladas + não-deletadas, alocações/payments vivos, `Coalesce` → 0), exposto em `BillingAccount.objects` via manager existente.
- [ ] `BillingAccountSerializer` expõe `open_balance` (string decimal) e a listagem `GET billing-accounts/` o carrega (queryset anotado); conta IPTU não zera (braço installment).
- [ ] `AccountStatementService.build(account_id, today)` devolve `{account, stats{open_balance, open_bills_count, avg_delay_days}, months[], plans[]}` EXATO ao contrato; `avg_delay_days` = média das últimas 12 quitadas (`amount_remaining=0` e `amount_total>0`), `paid_date` = MAX(payment_date) vivo, `None` sem quitadas; `plans` com `materialized_count` (espelho da materialização).
- [ ] `GET billing-accounts/{id}/statement` UNCACHED, `IsAdminUser` (403/401), 404 p/ conta inexistente/deletada; rota auto-exposta (`finances/urls.py` intacto).
- [ ] Testes desta sessão 100% verdes; **coverage `finances` ≥90%** no run escopado; regressão verde; `makemigrations --check` limpo.
- [ ] `ruff check && ruff format --check` + `mypy core/ finances/` + `pyright` — **zero erros e zero warnings**, sem suppressions.
- [ ] Nenhum arquivo de S68–S76 criado; `pay`/`month_board`/`convert_deferred` intocados.

## Handoff

1. Rodar e confirmar verde o gate + regressão (seção VERIFY).
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`:
   - Linha da Sessão 67 → **concluída**.
   - **Criados**: `finances/services/account_statement_service.py`, `tests/unit/test_finances/test_billing_account_open_balance.py`, `tests/unit/test_finances/test_account_statement_service.py`, `tests/integration/test_finances/test_finance_account_statement_api.py`.
   - **Modificados**: `finances/models.py` (`with_open_balance`), `finances/serializers.py` (`open_balance`), `finances/viewsets/crud_views.py` (queryset anotado + action `statement`).
   - **Nota p/ S70/S71/S73**: `open_balance`/`open_bills_count` são o critério canônico do "Parcelar saldo devedor" (S70 consome o mesmo conjunto de bills em aberto); shape do `statement` é o contrato do `account-statement.schema.ts`/`useAccountStatement` (objeto plano; `billing-account.schema` ganha `open_balance` OPCIONAL).
3. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 67 — with_open_balance annotation + AccountStatementService + uncached statement action

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. Próxima sessão: **68 — `pay` com ajuste de total (`new_total`)** (linha-semente estimada / linha Juros/multa, mesma transação).
