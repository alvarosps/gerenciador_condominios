# Sessão 65 — Backend: `Bill.amount_is_estimated` (migração + transições em serviço) + auditoria de confirmação P2.3

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida (`docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`, rev. 2)
> **Sessões da feature**: **65** → 66 → 67 → 68 → 69 → 70 → 71–76 (FE)
> **Primeira sessão da feature**: cria o branch `feat/condo-bills-cockpit` a partir de `master` e **commita o design doc**. Entrega: (a) o flag `Bill.amount_is_estimated` (BooleanField, default `False`) com **todas** as transições em serviço — NUNCA em viewset/serializer; (b) a **auditoria de confirmação do P2.3** (design §3.1): rodar as suítes de guards existentes (verdes) e REGISTRAR que o contrato vigente é `PATCH bills/{id}` → `BillService.update_header` guardado (**NÃO** 405; a edição inline do cockpit depende disso — não "reexecutar" o plano P2.3). **Sem `month_board` (S66); sem `statement`/`open_balance` (S67); sem `new_total` no `pay` (S68); sem `apply_invoice` (S69); sem consolidação (S70); zero frontend (S71–76); nada da Fase 2 (terceiros — design §7).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §1 "Integridade: JÁ RESOLVIDA", §3.1 auditoria P2.3, §3.3 bullets do flag `amount_is_estimated`, §5 modelo de dados, §9 testes do flag)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões + contratos AUTORITATIVOS (seção "Cockpit operacional de contas", Sessões 65–76 — se este prompt divergir, o SESSION_STATE prevalece)**: `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — VERIFICADOS; ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`Bill` (model que ganha o campo)** | `finances/models.py:304-378` (`lifecycle_state` `:334-336`, `notes` `:338`, `Meta`/constraints `:343-370`) | Adicionar `amount_is_estimated = models.BooleanField(default=False)` junto dos campos de estado. Sem mudança em `clean()`/constraints |
| **`_ensure_account_bill` (ÚNICO ponto que seta `True`)** | `finances/services/bill_generation_service.py:112-152` (`defaults` dict `:117-128`; `get_or_create` race-safe `:129-141`; linha-semente só quando `created` e `expected_amount>0` `:141-151`) | `True` entra pelos **`defaults`** do `get_or_create` — só bill recém-criada nasce estimada; re-runs idempotentes não re-marcam (created=False não toca em nada) |
| **Caminho da parcela embutida chama `_ensure_account_bill`** | `bill_generation_service.py:176-208` (`_generate_embedded_lines`; chamada em `:195`) | A bill hospedeira criada por este caminho TAMBÉM nasce `True` (mesma função — nenhum código extra; travar por teste) |
| **Parcela standalone / folha NÃO são estimadas** | `bill_generation_service.py:210-250` (`_generate_installment_bills` — bill SEM `billing_account`, só FK `installment`, valor real da parcela) + `:259-288` (payroll) | Esses caminhos têm valor real (schedule/salário) — ficam com o default `False`. Não tocar neles |
| **`pay` (seta `False` na MESMA transação)** | `finances/services/bill_payment_service.py:59-110` (guards de mês `:74-75`, ACTIVE `:76-77`, `locked`/`remaining` `:80-85`, over-allocation `:88-89`) + `unpay` `:113-130` | Após criar Payment+Allocation, limpar o flag sobre `locked` com `save(update_fields=…)`. `bulk_pay` delega a `pay` (`crud_views.py:404-408`) — coberto por delegação. `unpay` NÃO re-marca |
| **`update_with_lines` (seta `False`) / `create_with_lines` (default `False`) / `update_header` (não toca)** | `finances/services/bill_service.py:280-307` (`update_with_lines`, transação `:300-306`), `:206-260` (`create_with_lines`), `:309-321` (`update_header` só aplica `_EDITABLE_HEADER_FIELDS` `:128-140`) | Editar linhas = valor confirmado → `False` dentro da transação. `create_with_lines` cria com o default do model. `update_header`/PATCH nunca tocam o flag (fora do frozenset + read-only no serializer) |
| **`BillSerializer` (expor read-only)** | `finances/serializers.py:279-358` (`fields` `:324-353`, `read_only_fields` `:354`) | Adicionar `"amount_is_estimated"` a `fields` E `read_only_fields` — PATCH com o campo é ignorado (nunca chega em `validated_data`) |
| **Guards P2.3 (auditoria — SÓ RODAR, não reimplementar)** | `tests/integration/test_finances/test_finance_viewset_guards.py` + `test_finance_write_path_integrity.py`; `crud_views.py:575-598` (`update` delega a `update_header`) | Os 10 guards JÁ EXISTEM (commit `7005dd7`/PR #21/migração `0008`). A entrega é: rodar verde + registrar o contrato vigente no SESSION_STATE |
| **Factories** | `tests/factories.py:286` (`make_billing_account`), `:301` (`make_bill`), `:317` (`make_bill_line_item`), `:328` (`make_installment_plan`), `:346` (`make_installment`), `:385` (`make_payment`), `:400` (`make_payment_allocation`) | Dados dos testes. Não criar factory nova (KISS) |
| Mock policy | `tests/CLAUDE.md` | Nada externo aqui — **zero mocks** (ORM/serviços reais, banco real `--reuse-db`) |

### Setup do branch (fazer ANTES de tudo)

```bash
git checkout master && git pull
git checkout -b feat/condo-bills-cockpit
# Design doc + plano completo (12 prompts + contratos + roadmap) ainda não versionados:
git add docs/plans/2026-07-26-condo-bills-operational-redesign-design.md
git add prompts/65-finances-estimated-flag.md prompts/66-finances-month-board.md \
        prompts/67-finances-account-statement.md prompts/68-finances-pay-adjustment.md \
        prompts/69-finances-apply-invoice.md prompts/70-finances-consolidate-debt.md \
        prompts/71-finances-frontend-data-layer.md prompts/72-finances-accounts-page.md \
        prompts/73-finances-account-detail.md prompts/74-finances-cockpit-structure.md \
        prompts/75-finances-cockpit-interactions.md prompts/76-finances-close-preflight-audit.md \
        prompts/SESSION_STATE.md prompts/ROADMAP.md
git commit -m "docs(finances): design doc + plano (sessões 65-76) — cockpit operacional de contas"
```

> **CRITICAL — nunca `git add -A`/`git add .` nesta sessão.** O working tree de `master` contém arquivos alheios a esta feature (`.agents/`, `.codex/`, `AGENTS.md`, `.env.ci.test`, `bandit-report.json`, `.claude/settings.json` modificado). Adicionar tudo contaminaria o commit da feature — e `.env.ci.test`/`bandit-report.json` são exatamente o tipo de arquivo que não deve ser commitado. Sempre `git add` com caminhos explícitos, aqui e em TODAS as sessões 65–76.

---

## Escopo

### Arquivos a criar
- `finances/migrations/00XX_bill_amount_is_estimated.py` — **gerada por `makemigrations`** (NÃO fixar número: rodar `python manage.py showmigrations finances` para ver o head atual; os hooks do repo bloqueiam editar migrações existentes — sempre criar nova). Tabela `finances_bill` já existe → **sem ação de RLS** (design §5).
- `tests/unit/test_finances/test_bill_estimated_flag.py` — transições via serviços (gerar/editar/pagar/reverter).
- `tests/integration/test_finances/test_finance_bill_estimated_flag_api.py` — exposição no serializer + read-only + transições via API.

### Arquivos a modificar
- `finances/models.py` — campo `amount_is_estimated` no `Bill`.
- `finances/services/bill_generation_service.py` — `"amount_is_estimated": True` nos `defaults` de `_ensure_account_bill` (único ponto de `True`).
- `finances/services/bill_service.py` — `update_with_lines` limpa o flag na mesma transação.
- `finances/services/bill_payment_service.py` — `pay` limpa o flag na mesma transação (cobre `bulk_pay` por delegação).
- `finances/serializers.py` — `BillSerializer` expõe `amount_is_estimated` read-only.

### NÃO fazer (pertence a outras sessões)
- **`CondoMonthBoardService` / action `month_board` / badges** — **S66**.
- **`with_open_balance()` / `AccountStatementService` / action `statement`** — **S67**.
- **`new_total` no `pay` (ajuste de linha-semente / linha Juros/multa)** — **S68**. Aqui `pay` só ganha o clear do flag; a assinatura NÃO muda.
- **`apply_invoice`** — **S69** (o clear via `update_with_lines` já deixa o caminho pronto; não criar a action).
- **`consolidate_open_bills` / `consolidate_debt`** — **S70**.
- **Frontend (schemas/hooks/páginas/badges)** — **S71–76**.
- **Fase 2 (terceiros: `Payment.paid_by`, `ThirdPartyCharge`, extrato por pessoa)** — design §7, fora DESTAS sessões.
- **Reimplementar/alterar os guards P2.3** — já existem; a auditoria é rodar + registrar. **Não** transformar `PATCH bills/{id}` em 405.
- **Editar migrações existentes** (hooks bloqueiam); **sem** RLS nova; **sem** mudanças em `BillingAccount`/`InstallmentPlan`/`Payment`/fechamento (design §5).

---

## Especificação

> Transições **SEMPRE em serviço, NUNCA em viewset/serializer** (contrato S65 do SESSION_STATE — verbatim). Mensagens ao usuário em PT; identificadores em EN. Direção `finances → core` intacta.

### 1. Model (`finances/models.py`)

```python
class Bill(AuditMixin, SoftDeleteMixin, models.Model):
    ...
    lifecycle_state = models.CharField(...)  # existente
    amount_is_estimated = models.BooleanField(default=False)  # NOVO — valor ainda é a estimativa da conta
```

Migração: `python scripts/backup_db.py` → `python manage.py makemigrations finances` → `python manage.py migrate` → `python manage.py makemigrations --check --dry-run` ("No changes detected"). Testar forward/backward (`migrate finances <head_anterior>` e re-forward).

### 2. Tabela de transições (contrato AUTORITATIVO — SESSION_STATE S65)

| Caminho | Efeito no flag | Onde |
|---------|----------------|------|
| `BillGenerationService._ensure_account_bill` com `created=True` | **`True`** (único ponto) | `"amount_is_estimated": True` no dict `defaults` (`:117-128`) — vale também quando chamado pelo caminho da parcela embutida (`:195`) |
| `_ensure_account_bill` com `created=False` (re-run idempotente) | intocado (não re-marca nem desfaz `False`) | `defaults` só se aplica na criação |
| `_generate_installment_bills` / `_generate_payroll_bills` | `False` (default do model — valor real) | nenhum código |
| `BillService.create_with_lines` | `False` (default do model) | nenhum código |
| `BillService.update_with_lines` | **`False`** | dentro da transação existente (`:300-306`), após `_write_lines`/`_upsert_statement`: se `bill.amount_is_estimated`, setar `False` + `updated_by` e `save(update_fields=["amount_is_estimated", "updated_by"])` (AuditMixin acrescenta `updated_at`) |
| `BillPaymentService.pay` (total OU parcial) | **`False`** | dentro da transação (`:79-109`), sobre `locked`, após criar Payment/Allocation — mesmo idioma de `save(update_fields=…)`. Cobre `bulk_pay` por delegação (`crud_views.py:404-408`) |
| `BillPaymentService.unpay` | **intocado** (NÃO re-marca) | nenhum código |
| `BillService.update_header` / `PATCH bills/{id}` | intocado | flag fora de `_EDITABLE_HEADER_FIELDS` (`:128-140`) + read-only no serializer — nada a fazer, travar por teste |

### 3. Serializer (`finances/serializers.py`)

`BillSerializer.Meta`: `"amount_is_estimated"` em `fields` (junto de `lifecycle_state`) **e** em `read_only_fields`. É campo concreto do model — sem `SerializerMethodField`.

### 4. Auditoria de confirmação P2.3 (design §3.1 — entrega pequena)

```bash
python -m pytest tests/integration/test_finances/test_finance_viewset_guards.py \
  tests/integration/test_finances/test_finance_write_path_integrity.py -q
```
(a) Confirmar 100% verde. (b) Registrar no handoff (SESSION_STATE): "contrato vigente do P2.3: `PATCH bills/{id}` → `BillService.update_header` guardado (NÃO 405 — desvio deliberado do plano original; a edição inline do cockpit depende disso; testes travam)". (c) Itens extras já implementados que o restante do design assume: guard de mês de caixa em `pay`/`unpay`, guards de Income, bloqueio destroy/suspend/cancel com pagamento vivo, reversão `MATERIALIZED→ACTIVE`. **Nenhum código novo nesta entrega.**

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): zero mocks nesta sessão (nenhuma fronteira externa). Banco real (`--reuse-db`), factories. `filterwarnings=error`: zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_bill_estimated_flag.py`

```python
class TestEstimatedFlagOnGeneration:
    def test_generated_recurring_bill_is_estimated(self) -> None:
        """ensure_month_bills cria bill recorrente com amount_is_estimated=True."""

    def test_generated_bill_without_expected_amount_is_estimated(self) -> None:
        """Conta com expected_amount=0 gera bill SEM linha (total 0) e ainda assim True ("aguardando fatura")."""

    def test_embedded_path_creates_estimated_host_bill(self) -> None:
        """Bill hospedeira criada pelo caminho da parcela embutida (plano embedded) nasce True."""

    def test_regeneration_does_not_remark_flag(self) -> None:
        """2º ensure_month_bills no mesmo mês não re-marca True numa bill já confirmada (False)."""

    def test_standalone_installment_bill_not_estimated(self) -> None:
        """Bill de parcela standalone (installment FK, sem billing_account) nasce False (valor real)."""

    def test_payroll_bill_not_estimated(self) -> None:
        """Bill de folha (employee FK) nasce False."""


class TestEstimatedFlagTransitions:
    def test_create_with_lines_defaults_to_not_estimated(self) -> None:
        """create_with_lines cria com o default False (lançamento manual = valor confirmado)."""

    def test_update_with_lines_clears_flag(self) -> None:
        """update_with_lines numa bill estimada limpa o flag na mesma transação."""

    def test_update_with_lines_keeps_false(self) -> None:
        """update_with_lines numa bill já confirmada mantém False (idempotente)."""

    def test_pay_full_clears_flag(self) -> None:
        """pay total numa bill estimada limpa o flag."""

    def test_pay_partial_clears_flag(self) -> None:
        """pay PARCIAL também limpa (pagou = valor real conhecido)."""

    def test_unpay_does_not_remark_flag(self) -> None:
        """unpay reverte o pagamento mas NÃO re-marca amount_is_estimated."""

    def test_update_header_does_not_touch_flag(self) -> None:
        """update_header (header editável) não altera o flag (fora de _EDITABLE_HEADER_FIELDS)."""

    def test_failed_pay_keeps_flag(self) -> None:
        """pay rejeitado (over-allocation/bill não-ACTIVE) NÃO limpa o flag (transação intacta)."""
```

#### `tests/integration/test_finances/test_finance_bill_estimated_flag_api.py`
`pytestmark = [pytest.mark.django_db, pytest.mark.integration]`; client `authenticated_api_client` (admin).

```python
def test_bill_serializer_exposes_amount_is_estimated(authenticated_api_client) -> None:
    """GET bills/{id} inclui amount_is_estimated (bool) no payload."""

def test_patch_cannot_set_amount_is_estimated(authenticated_api_client) -> None:
    """PATCH bills/{id} com amount_is_estimated=true é IGNORADO (read-only; flag não muda)."""

def test_generate_month_marks_new_bills_estimated(authenticated_api_client) -> None:
    """POST bills/generate_month → bills recorrentes criadas voltam com amount_is_estimated=True."""

def test_pay_action_clears_flag(authenticated_api_client) -> None:
    """POST bills/{id}/pay numa estimada → resposta serializada com amount_is_estimated=False."""

def test_bulk_pay_clears_flag(authenticated_api_client) -> None:
    """POST bills/bulk_pay limpa o flag de todas as bills pagas (delegação a pay)."""

def test_update_with_lines_clears_flag_via_api(authenticated_api_client) -> None:
    """POST bills/{id}/update_with_lines numa estimada → amount_is_estimated=False na resposta."""
```

> Rodar (devem **falhar** — campo/transições não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_estimated_flag.py tests/integration/test_finances/test_finance_bill_estimated_flag_api.py -q
> ```

### 2. GREEN — implementar
1. `finances/models.py` — campo; depois **backup** (`python scripts/backup_db.py`) → `makemigrations finances` → `migrate` → `makemigrations --check --dry-run`.
2. `bill_generation_service.py` — `True` nos `defaults` de `_ensure_account_bill`.
3. `bill_service.py` — clear em `update_with_lines`.
4. `bill_payment_service.py` — clear em `pay`.
5. `finances/serializers.py` — campo read-only no `BillSerializer`.

### 3. REFACTOR — DRY / clareza
- O clear é 3 linhas idênticas em 2 serviços — **não** extrair helper prematuro (KISS); se ficar idêntico em 3+ lugares na S68/S69, extrair lá.
- Docstring de `_ensure_account_bill` menciona que bill recém-criada nasce estimada (badge do cockpit, design §3.3).
- Confirmar que NENHUM viewset/serializer escreve o flag (`grep amount_is_estimated finances/viewsets/ finances/serializers.py` → só leitura/Meta).

### 4. VERIFY — gate (escopo desta sessão)

```bash
python -m pytest tests/unit/test_finances/test_bill_estimated_flag.py \
  tests/integration/test_finances/test_finance_bill_estimated_flag_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check && ruff format --check
mypy core/ finances/
pyright
python manage.py makemigrations --check --dry-run
```

> **Regressão obrigatória** (arquivos tocados + auditoria P2.3):
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_generation_service.py tests/unit/test_finances/test_generation_installments_payroll.py \
>   tests/unit/test_finances/test_bill_service.py tests/unit/test_finances/test_bill_payment_service.py \
>   tests/integration/test_finances/test_finance_bill_actions.py tests/integration/test_finances/test_finance_crud_api.py -q
> python -m pytest tests/integration/test_finances/test_finance_viewset_guards.py tests/integration/test_finances/test_finance_write_path_integrity.py -q
> ```

---

## Constraints

- **Transições só em serviço** — proibido setar/limpar o flag em viewset, serializer, signal ou migração de dados. O serializer só **expõe** (read-only).
- **`True` num único ponto**: `_ensure_account_bill` quando `created` (via `defaults`). Nenhum outro caminho marca `True`.
- **`unpay` não re-marca** (contrato) — o valor real continua conhecido após reverter o pagamento.
- **Sem mudar assinaturas** de `pay`/`update_with_lines`/`create_with_lines` (o `new_total` é S68; `apply_invoice` é S69).
- **Migração nova via `makemigrations`** — sem número fixado; hooks bloqueiam editar migrações existentes. **Backup antes do migrate** (`.claude/rules/database.md`). Sem RLS (tabela existente).
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Sem `from __future__ import annotations`, sem `if TYPE_CHECKING`, sem re-exports/barrels.
- Mock só de fronteiras externas (aqui: nenhum). Mensagens ao usuário em PT.

## Critérios de Aceite (binários)

- [ ] Branch `feat/condo-bills-cockpit` criado de `master`; design doc commitado nele.
- [ ] `Bill.amount_is_estimated` (BooleanField, `default=False`) + migração sequencial gerada por `makemigrations` (sem RLS); forward/backward OK; `makemigrations --check` limpo.
- [ ] `True` só em `_ensure_account_bill` quando `created` (inclusive via caminho da parcela embutida); parcela standalone/folha/`create_with_lines` nascem `False`; re-run de geração não re-marca.
- [ ] `update_with_lines` e `pay` (total/parcial; `bulk_pay` por delegação) limpam o flag **na mesma transação**; `unpay` não re-marca; `update_header`/PATCH não tocam.
- [ ] `BillSerializer` expõe `amount_is_estimated` **read-only** (PATCH com o campo é ignorado).
- [ ] Auditoria P2.3: as 2 suítes de guards verdes; contrato `PATCH → update_header` (NÃO 405) registrado no handoff. Nenhum guard alterado.
- [ ] Testes desta sessão 100% verdes; **coverage `finances` ≥90%** no run escopado; regressão verde.
- [ ] `ruff check && ruff format --check` + `mypy core/ finances/` + `pyright` — **zero erros e zero warnings**, sem suppressions.
- [ ] Nenhum arquivo de S66–S76 criado (sem month_board/statement/new_total/apply_invoice/consolidate/frontend).

## Handoff

1. Rodar e confirmar verde o gate + regressão (seção VERIFY).
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`:
   - Linha da Sessão 65 → **concluída** na tabela da feature "Cockpit operacional de contas".
   - **Criados**: migração `finances 00XX` (registrar o número real), `tests/unit/test_finances/test_bill_estimated_flag.py`, `tests/integration/test_finances/test_finance_bill_estimated_flag_api.py`.
   - **Modificados**: `finances/models.py`, `finances/services/bill_generation_service.py`, `finances/services/bill_service.py`, `finances/services/bill_payment_service.py`, `finances/serializers.py`.
   - **Auditoria P2.3 registrada**: guards verdes; contrato vigente = `PATCH bills/{id}` → `BillService.update_header` guardado (NÃO 405).
3. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar no branch `feat/condo-bills-cockpit`:
   ```
   feat(finances): complete session 65 — Bill.amount_is_estimated + service-only transitions + P2.3 confirmation audit

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
5. Próxima sessão: **66 — `CondoMonthBoardService` + `GET finance-dashboard/month_board`** (consome o flag desta sessão nos badges do payload).
