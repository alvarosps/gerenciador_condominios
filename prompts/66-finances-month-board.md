# Sessão 66 — Backend: `CondoMonthBoardService` + `GET /api/finances/finance-dashboard/month_board` (UNCACHED)

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida (`docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`, rev. 2)
> **Sessões da feature**: 65 → **66** → 67 → 68 → 69 → 70 → 71–76 (FE)
> Esta sessão entrega a **fonte de dados única do cockpit** (design §3.3): `CondoMonthBoardService.build(year, month, today)` — Atrasadas cross-competência (critério PRÓPRIO do board), dívida adiada/suspensa fora dos totais, grupos por prédio, totais do mês e `generation.missing_count` — e a action **UNCACHED** `GET finance-dashboard/month_board?year&month`. **Sem `statement`/`open_balance` (S67); sem `new_total` no `pay` (S68); sem `apply_invoice` (S69); sem consolidação (S70); zero frontend (S71–76); nada da Fase 2 (terceiros).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.3 "Cockpit do mês" inteiro, §4 tabela de API — linha `month_board`, §8 erros, §9 testes do `month_board`)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado + contratos AUTORITATIVOS (S66 no SESSION_STATE prevalece sobre este prompt)**: `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — VERIFICADOS; ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Action UNCACHED com comentário-justificativa** | `finances/viewsets/dashboard_views.py:217-237` (`combined_calendar`, comentário `:219-221`) + `:279-305` (`iptu_alerts`, comentário `:281-282`) | **Molde exato** do `month_board`: `@action(detail=False, methods=["get"])`, SEM `@cache_result`, comentário explicando (estado de pagamento + `today_sp()`; virada de meia-noite não é write → cache nunca invalidaria) |
| **Parse de year/month em query param → 400 PT** | `dashboard_views.py:44-50` (`_parse_year_month_query` — default = mês SP corrente) + idioma do 400 em `:307-317` (`overview`) | Reusar `_parse_year_month_query` + `try/except ValueError` → 400 PT (mesma mensagem do `overview`). *(Atenção: o helper de query se chama `_parse_year_month_query`; `_parse_year_month` é o de body em `crud_views.py:82-88`)* |
| **Serialização de bills com annotations + total em Python** | `dashboard_views.py:239-277` (`overdue`: lookup `dict[str, object]` p/ annotation `:244`, Σ `amount_remaining` via `getattr` `:255-257`, `BillSerializer(bills, many=True)` `:265`) | Idioma de: filtrar por annotation sob django-stubs, somar annotations já carregadas, serializar via `BillSerializer` |
| **`with_amounts` / `with_list_relations`** | `finances/models.py:223-273` (annotations; `is_overdue` `:262-271`) + `:275-296` (eager-load p/ o `BillSerializer` sem N+1) | Queryset-base do board: `Bill.objects.with_amounts(today).with_list_relations()`. O critério de atraso do board é PRÓPRIO (ver Especificação) — **não** filtrar por `is_overdue` |
| **`is_account_eligible` (único predicado de elegibilidade)** | `finances/services/bill_generation_service.py:52-78` + `recurring_for_generation()` em `finances/models.py:132-143` (exclui IPTU, registry-only) | `generation.missing_count` usa **exatamente** este par (cobre BillSkip/tracking_start_month/end_date/estado) — nunca reimplementar o predicado |
| **`get_or_create` da geração (o que conta como "já existe")** | `bill_generation_service.py:129-141` (lookup `billing_account+competence_month+is_deleted=False` — a unique parcial NÃO filtra lifecycle) | Uma bill NÃO-deletada de **qualquer** lifecycle já ocupa o slot do mês → não é "faltante" (`generate_month` não criaria outra; o banner precisa zerar após gerar) |
| **Serviço que serializa com serializer do módulo (precedente)** | `finances/services/invoice_draft_service.py:23` (importa `BillingAccountSerializer`) | O board devolve o dict FINAL (bills já serializados via `BillSerializer`); a action só delega. Serviço nunca importa views |
| **Money como string** | `finances/money.py` (`money_str`) + uso em `dashboard_views.py:269` | `totals.*` em string decimal (`"1234.56"`) |
| **Testes de integração do dashboard** | `tests/integration/test_finances/test_finance_calendar_overdue_api.py` + fixtures `tests/conftest.py` (`authenticated_api_client` admin; `regular_authenticated_api_client` não-admin) | Forma dos testes de API (shape/401/403/400) |
| Mock policy | `tests/CLAUDE.md` | Sem fronteira externa — **zero mocks**; datas via factories com `due_date`/`competence_month` explícitos relativos a um `today` fixo passado ao serviço (unit) |

### O que a S65 já entregou (PRÉ-REQUISITO — NÃO recriar)
- `Bill.amount_is_estimated` (BooleanField, default False) + transições em serviço + `BillSerializer` expõe read-only (os badges "valor estimado"/"aguardando fatura" do cockpit leem esse campo do payload deste board). **Se a S65 não estiver concluída no branch, PARE.**

---

## Escopo

### Arquivos a criar
- `finances/services/condo_month_board_service.py` — `CondoMonthBoardService.build(year, month, today) -> dict`.
- `tests/unit/test_finances/test_condo_month_board_service.py` — regras do board (seções/totais/missing_count).
- `tests/integration/test_finances/test_finance_month_board_api.py` — action (shape/400/401/403/uncached).

### Arquivos a modificar
- `finances/viewsets/dashboard_views.py` — `@action(detail=False, methods=["get"]) def month_board(...)` em `FinanceDashboardViewSet` (`:212+`), UNCACHED, delegando ao serviço. Import direto `from finances.services.condo_month_board_service import CondoMonthBoardService`. Demais actions **intactas**.

### NÃO fazer (pertence a outras sessões)
- **`with_open_balance()` / `AccountStatementService` / action `statement`** — **S67**.
- **`new_total` no `pay`** — **S68**; **`apply_invoice`** — **S69**; **`consolidate_open_bills`/`consolidate_debt`** — **S70**.
- **Frontend** (hooks/`useMonthBoard`/página do cockpit/badges) — **S71/S74**.
- **Não** alterar a annotation `is_overdue`, o `overdue` legado do dashboard, `combined_calendar`, `generate_month`, nem `is_account_eligible`/`recurring_for_generation`.
- **Não** adicionar cache/invalidatação para o `month_board` (decisão explícita, design §10).
- **Sem migração/model/serializer novo**; nada da Fase 2 (terceiros).

---

## Especificação

> Serviço stateless (`@staticmethod`) em `finances/services/`. "Hoje" **sempre** vem do caller (`today_sp()` na action — import de `core.services.timezone`). Dinheiro via annotations do `with_amounts` (nunca property/soma refeita de linhas em Python; somar as annotations carregadas é o idioma do `overdue` `:255-257`). Mensagens PT; identificadores EN.

### `CondoMonthBoardService.build(year: int, month: int, today: date) -> dict[str, object]`

```python
class CondoMonthBoardService:
    @staticmethod
    def build(year: int, month: int, today: date) -> dict[str, object]:
        """Fonte única do cockpit do mês (design §3.3). Read-only, uncached.
        Sempre chamado com today_sp(). Bills serializados via BillSerializer sobre
        Bill.objects.with_amounts(today).with_list_relations()."""
```

Payload (contrato AUTORITATIVO — SESSION_STATE S66, verbatim):

```python
{
    "overdue": [bill, ...],                # BillSerializer.data
    "deferred_suspended": [bill, ...],
    "groups": [{"building_id": int | None, "building_label": str, "bills": [bill, ...]}],
    "totals": {"due": str, "paid": str, "remaining": str, "overdue": str},  # money_str
    "generation": {"missing_count": int},
}
```

Regras (cada bullet vira teste):

1. **Queryset-base**: `Bill.objects.with_amounts(today).with_list_relations()` (sem N+1 no serializer).
2. **`overdue`** = `amount_remaining > 0 AND due_date < today AND lifecycle_state = ACTIVE`, de **qualquer competência**. Critério **PRÓPRIO do board** — construir os filtros explicitamente (lookup `dict[str, object]` p/ `amount_remaining__gt`) e documentar no docstring por que NÃO reusa a annotation `is_overdue` nem o `overdue` legado do dashboard: o critério do board é dono de si (design §3.3) e não pode derivar silenciosamente se a annotation mudar. `due_date == today` NÃO é atrasada (fronteira). Ordenar por `due_date` asc.
3. **`deferred_suspended`** = `lifecycle_state ∈ {SUSPENDED, DEFERRED}` com `amount_remaining > 0`, qualquer competência, **FORA de `totals`**. Ordenar por `due_date` asc.
4. **CANCELED nunca aparece** — em nenhuma seção, grupo ou total.
5. **`groups`** = bills **ACTIVE** com `competence_month == date(year, month, 1)` (pagas INCLUÍDAS), agrupadas por prédio. `building_label` = `str(building.street_number)`; bucket `building_id=None` → label `"Condomínio"`, **por último**. Grupos ordenados por `street_number` asc; bills do grupo por `due_date` asc.
6. **`totals`**: `due` = Σ `amount_total`, `paid` = Σ `amount_paid`, `remaining` = Σ `amount_remaining` — **só** das bills dos `groups` (o mês); `overdue` = Σ `amount_remaining` da seção `overdue` (cross-competência). Tudo `money_str`.
7. **`generation.missing_count`** = nº de contas com `BillGenerationService.is_account_eligible(account, month_start)` `True` (iterando `BillingAccount.objects.recurring_for_generation()` — IPTU registry-only fica de fora) **e sem Bill não-deletada** para `(billing_account, competence_month=month_start)`. "Não-deletada, qualquer lifecycle": é o mesmo lookup do `get_or_create` da geração (`:129-141`) — uma bill SUSPENDED/CANCELED no mês ocupa a unique parcial, `generate_month` não criaria outra, logo NÃO é faltante (senão o banner nunca zeraria).
8. **Sem writes** — serviço 100% read-only.

### Action `month_board` (em `FinanceDashboardViewSet`, `dashboard_views.py`)

```python
@action(detail=False, methods=["get"])
def month_board(self, request: Request) -> Response:
    # NO cache (design §10): operational board — depends on payment state + today_sp();
    # midnight rollover is not a write, so cache would never be invalidated — same
    # rationale as combined_calendar/overdue/iptu_alerts.
    try:
        year, month = _parse_year_month_query(request, current_month_sp())
    except ValueError:
        return Response(
            {"error": "Parâmetros year/month inválidos (mês entre 1 e 12)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(CondoMonthBoardService.build(year, month, today_sp()), status=status.HTTP_200_OK)
```

- `IsAdminUser` herdado do viewset (`:215`) — não-staff 403, anônimo 401, sem código extra.
- Defaults do helper: sem params → mês SP corrente (comportamento de `overview`).
- Rota auto-exposta pelo router (`finance-dashboard/month_board/`) — **sem** tocar `finances/urls.py`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: zero mocks (sem fronteira externa). Unit chama `build(year, month, today)` com `today` explícito — sem freezegun. Banco real (`--reuse-db`), factories (`make_billing_account:286`, `make_bill:301`, `make_bill_line_item:317`, `make_payment:385`, `make_payment_allocation:400`, `make_bill_skip:374`, `make_building:51`). Zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_condo_month_board_service.py`

```python
class TestMonthBoardOverdueSection:
    def test_overdue_includes_previous_competence(self) -> None:
        """Bill ACTIVE de competência anterior com resto>0 e due_date<today entra em overdue."""

    def test_overdue_excludes_due_today(self) -> None:
        """due_date == today não é atrasada (fronteira: só due_date < today)."""

    def test_overdue_only_active(self) -> None:
        """Bill SUSPENDED/DEFERRED vencida com resto>0 NÃO entra em overdue (vai p/ deferred_suspended)."""

    def test_overdue_excludes_paid(self) -> None:
        """Bill vencida com amount_remaining==0 não aparece em overdue."""

    def test_overdue_sorted_by_due_date(self) -> None:
        """Seção overdue ordenada por due_date asc (determinístico)."""


class TestMonthBoardDeferredSuspended:
    def test_deferred_suspended_any_competence_with_rest(self) -> None:
        """SUSPENDED e DEFERRED com resto>0 (qualquer competência) aparecem rotuladas na sub-seção."""

    def test_deferred_suspended_excludes_settled(self) -> None:
        """SUSPENDED com resto==0 não aparece."""

    def test_deferred_suspended_out_of_totals(self) -> None:
        """Dívida adiada/suspensa NÃO entra em totals.due/paid/remaining nem em totals.overdue."""


class TestMonthBoardGroupsAndTotals:
    def test_canceled_invisible_everywhere(self) -> None:
        """Bill CANCELED (mesmo vencida/com resto) não aparece em overdue, grupos nem totais."""

    def test_groups_only_selected_month_active_including_paid(self) -> None:
        """groups = bills ACTIVE da competência M, pagas incluídas; outra competência fica fora."""

    def test_group_without_building_is_condominio_last(self) -> None:
        """Bills com building=None caem no bucket 'Condomínio', posicionado por último."""

    def test_groups_ordered_by_street_number(self) -> None:
        """Grupos ordenados por street_number asc; bills do grupo por due_date asc."""

    def test_totals_due_paid_remaining_of_month(self) -> None:
        """totals.due/paid/remaining = Σ das annotations das bills dos groups (money_str)."""

    def test_totals_overdue_sums_overdue_section(self) -> None:
        """totals.overdue = Σ amount_remaining da seção overdue (cross-competência)."""

    def test_bills_serialized_with_amounts_and_estimated_flag(self) -> None:
        """Bills do payload têm amount_total/paid/remaining/payment_status e amount_is_estimated (S65)."""


class TestMonthBoardGeneration:
    def test_missing_count_eligible_account_without_bill(self) -> None:
        """Conta ativa elegível sem bill no mês conta como faltante."""

    def test_missing_count_zero_after_generation(self) -> None:
        """Após ensure_month_bills, missing_count == 0 (banner zera)."""

    def test_missing_count_respects_bill_skip(self) -> None:
        """Conta com BillSkip no mês NÃO é faltante (is_account_eligible)."""

    def test_missing_count_respects_tracking_start_and_end_date(self) -> None:
        """Conta com tracking_start_month futuro ou end_date passado NÃO é faltante."""

    def test_missing_count_ignores_iptu_registry_account(self) -> None:
        """Conta IPTU (registry-only, fora de recurring_for_generation) nunca conta."""

    def test_missing_count_bill_any_lifecycle_occupies_slot(self) -> None:
        """Bill SUSPENDED (não-deletada) no mês ocupa o slot → conta NÃO é faltante."""
```

#### `tests/integration/test_finances/test_finance_month_board_api.py`
`pytestmark = [pytest.mark.django_db, pytest.mark.integration]`; URL `finance-dashboard/month_board/`.

```python
def test_month_board_returns_full_shape(authenticated_api_client) -> None:
    """200 com chaves overdue/deferred_suspended/groups/totals{due,paid,remaining,overdue}/generation{missing_count}."""

def test_month_board_defaults_to_current_sp_month(authenticated_api_client) -> None:
    """Sem year/month → usa o mês SP corrente (groups refletem a competência atual)."""

def test_month_board_invalid_month_returns_400(authenticated_api_client) -> None:
    """month=13 → 400 PT (padrão _parse_year_month_query)."""

def test_month_board_non_numeric_year_returns_400(authenticated_api_client) -> None:
    """year=abc → 400 PT."""

def test_month_board_forbidden_for_non_admin(regular_authenticated_api_client) -> None:
    """Não-staff → 403 (IsAdminUser — módulo financeiro é admin-only)."""

def test_month_board_requires_authentication(api_client) -> None:
    """Anônimo → 401."""

def test_month_board_uncached_reflects_payment(authenticated_api_client) -> None:
    """Pagar uma bill atrasada via bills/{id}/pay e re-GET → some de overdue sem stale (uncached)."""
```

> Rodar (devem **falhar** — serviço/action não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_condo_month_board_service.py tests/integration/test_finances/test_finance_month_board_api.py -q
> ```

### 2. GREEN — implementar
1. `finances/services/condo_month_board_service.py` — `build` (uma passada no queryset-base + partição em Python por seção; `missing_count` via `recurring_for_generation()` + `is_account_eligible` + `exists()` do slot).
2. `dashboard_views.py` — action `month_board` (fina, conforme Especificação).

### 3. REFACTOR — DRY / clareza
- Partição das seções em helpers privados nomeados (`_overdue_bills`, `_deferred_suspended_bills`, `_month_groups`, `_missing_count`) — SRP, cada um testável pela API pública `build`.
- Confirmar que o critério de atraso do board está num único lugar (constante/filtro nomeado) com o docstring exigido (por que não reusa `is_overdue`).
- Nenhuma soma refeita a partir de linhas em Python — só as annotations carregadas.

### 4. VERIFY — gate (escopo desta sessão)

```bash
python -m pytest tests/unit/test_finances/test_condo_month_board_service.py \
  tests/integration/test_finances/test_finance_month_board_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check && ruff format --check
mypy core/ finances/
pyright
```

> **Regressão obrigatória** (actions irmãs do dashboard + geração intactas):
> ```bash
> python -m pytest tests/integration/test_finances/test_finance_calendar_overdue_api.py \
>   tests/integration/test_finances/test_finance_balance_dashboard_api.py \
>   tests/unit/test_finances/test_bill_generation_service.py -q
> ```

---

## Constraints

- **Lógica só no serviço** (`.claude/rules/architecture.md`): a action valida params (400 PT) e delega — zero regra de negócio na view.
- **UNCACHED obrigatório** com comentário-justificativa (mesmo racional de `combined_calendar`/`overdue`/`iptu_alerts`). Não adicionar prefixo de cache/invalidatação.
- **Critério de atraso PRÓPRIO** — proibido filtrar por `is_overdue` (annotation) ou reusar o `overdue` legado; docstring explica.
- **`missing_count` só via `is_account_eligible`** + `recurring_for_generation()` — proibido reimplementar o predicado (BillSkip/tracking/end_date/estado).
- **CANCELED nunca**; `deferred_suspended` fora dos totais; pagas do mês DENTRO dos groups/totals.
- **`today` do caller** (`today_sp()` na action); proibido `timezone.now().date()` no serviço.
- **Money via annotations** de `with_amounts` + `money_str`; nunca property Python.
- **Sem suppressions** (`# noqa`/`# type: ignore`), sem `from __future__`, sem `TYPE_CHECKING`, sem re-exports. Lookups de annotation via `dict[str, object]` (idioma `dashboard_views.py:244`).
- Mensagens ao usuário em PT; identificadores EN.

## Critérios de Aceite (binários)

- [ ] `CondoMonthBoardService.build(year, month, today) -> dict` com o payload EXATO do contrato (`overdue`/`deferred_suspended`/`groups`/`totals{due,paid,remaining,overdue}`/`generation{missing_count}`), bills via `BillSerializer` sobre `with_amounts(today).with_list_relations()`.
- [ ] `overdue` cross-competência, só ACTIVE, `due_date < today` estrito, resto>0; `deferred_suspended` fora dos totais; CANCELED invisível; groups = ACTIVE da competência (pagas incluídas), bucket "Condomínio" por último.
- [ ] `missing_count` via `is_account_eligible` + slot `(conta, mês)` não-deletado (qualquer lifecycle); zera após `generate_month`; IPTU/BillSkip/tracking respeitados.
- [ ] `GET finance-dashboard/month_board?year&month` UNCACHED, `IsAdminUser` (403/401), 400 PT em params inválidos, default = mês SP corrente; rota auto-exposta (`finances/urls.py` intacto).
- [ ] Testes desta sessão 100% verdes; **coverage `finances` ≥90%** no run escopado; regressão verde.
- [ ] `ruff check && ruff format --check` + `mypy core/ finances/` + `pyright` — **zero erros e zero warnings**, sem suppressions.
- [ ] Nenhum arquivo de S67–S76 criado; `is_overdue`/`overdue` legado/`combined_calendar`/`generate_month` intactos.

## Handoff

1. Rodar e confirmar verde o gate + regressão (seção VERIFY).
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`:
   - Linha da Sessão 66 → **concluída**.
   - **Criados**: `finances/services/condo_month_board_service.py`, `tests/unit/test_finances/test_condo_month_board_service.py`, `tests/integration/test_finances/test_finance_month_board_api.py`.
   - **Modificados**: `finances/viewsets/dashboard_views.py` (action `month_board` uncached).
   - **Nota p/ S71/S74**: shape do payload é o contrato do `useMonthBoard`/`month-board.schema.ts` (bills no shape do `BillSerializer`, com `amount_is_estimated`; totals em string decimal; objeto plano, não `{results,count}` — o interceptor do `client.ts` não desempacota).
3. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 66 — CondoMonthBoardService + uncached month_board dashboard action

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. Próxima sessão: **67 — `with_open_balance()` + `AccountStatementService` + `GET billing-accounts/{id}/statement`**.
