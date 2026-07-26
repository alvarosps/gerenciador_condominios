# Sessão 70 — Backend: `InstallmentPlanService.consolidate_open_bills` + `POST billing-accounts/{id}/consolidate_debt`

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida (`docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`, rev. 2)
> **Sessões da feature**: 65 → 66 → 67 → 68 → 69 → **70** → 71–76 (FE)
> **Fase**: parcelar saldo devedor (design §3.5). O caso DMAE ("cortada, acumulando, teria que ser parcelada") não tem fluxo hoje: `convert_deferred` opera 1 bill por vez e rejeita conta não-IPTU. Esta sessão entrega a generalização multi-bill/multi-tipo: N bills em aberto da conta → **1** `InstallmentPlan` com `total = Σ amount_remaining` (parciais contam o RESTO) → **cancelamento atômico das origens** (senão saldo devedor e Atrasadas dobram a dívida). `convert_deferred` (IPTU single-bill) permanece intocado.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.5 "Parcelar saldo devedor", §9 "consolidate_debt", §10 gate de arquitetura)**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões + CONTRATO AUTORITATIVO S70** (somente leitura): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`convert_deferred` (espelho single-bill — INTOCADO)** | `finances/services/installment_plan_service.py:102-186` — `select_for_update` `:127`, precondição de estado `:128-129`, guard IPTU `:134-138`, total = `amount_remaining` via `with_amounts` `:140-145` (B9: parcial reparcela só o resto), criação do plano `:147-161`, **cancelamento da origem `:175-178`** (CANCELED direto, sem `set_state`) | O `consolidate_open_bills` segue o MESMO idioma (lock → validar → plano → parcelas → cancelar origens), generalizado p/ N bills e qualquer tipo de conta |
| **Materialização existente (REUSAR — não reimplementar o loop)** | `installment_plan_service.py:74-100` (`materialize_schedule`: `_split_amount` + `_schedule_due_dates` + `Installment.objects.create`, idempotente) | O plano consolidado materializa suas parcelas chamando `materialize_schedule(plan, user)` logo após criar o plano (plano recém-criado não tem installments ⇒ o no-op idempotente nunca dispara) |
| **`_split_amount` (centavos exatos)** | `installment_plan_service.py:46-58` | Σ parcelas == total exato; resto na última — travar por teste |
| **Guard de viewset que este caminho NÃO usa** | `finances/services/bill_lifecycle_service.py:28-43` (`set_state`: `assert_not_paid` p/ suspend/cancel) | O cancelamento das origens é caminho de serviço PRÓPRIO que ADMITE pagamento parcial vivo — docstring explica o porquê (precedente: `convert_deferred` B9) |
| **Regra embedded ⇒ conta de consumo** | `finances/models.py:592-603` (`InstallmentPlan.clean`) + `_CONSUMPTION_TYPES` `:523-525` | Disparada via `full_clean()` do plano — NÃO duplicar a regra no serviço |
| **Dois braços de FK (posse da bill)** | `finances/models.py:275-296` (`with_list_relations` — cadeia `installment__plan__billing_account`) + design §3.4 | Bills de parcela avulsa têm `billing_account=None` e pertencem à conta via `installment.plan.billing_account` — o braço 2 resolve a posse para dar a rejeição PT específica (pureza v1: parcela de plano não consolida), em vez de "não encontrada" |
| **`with_amounts` (resto por bill)** | `finances/models.py:223-273` | `amount_remaining` — nunca somar alocações em Python |
| **Action fina exemplar (parse 400 PT → delegar)** | `finances/viewsets/crud_views.py:439-455` (`generate_month`) e `:801-818` (`_close_action`) | Estrutura da action `consolidate_debt` |
| **Onde a action entra** | `crud_views.py:121-141` (`BillingAccountViewSet`) | `@action(detail=True)` — rota auto-exposta pelo router |
| **Resposta 201** | `finances/serializers.py:498-530` (`InstallmentPlanSerializer`, aninha `installments`) | Shape do plano devolvido |
| **Testes exemplar** | `tests/unit/test_finances/test_installment_plan_service.py` + `tests/integration/test_finances/test_finance_viewset_guards.py` | Estilo unit/integração; factories `make_billing_account`/`make_bill`/`make_bill_line_item`/`make_installment_plan`/`make_installment`/`make_payment_allocation`/`make_condo_month_close` (`tests/factories.py`) |

### Pré-requisitos

- Só **master** (+ S65 recomendada antes, apenas para evitar conflito de merge em `crud_views.py` — nenhuma dependência funcional). Não usa `month_board` (S66) nem `open_balance` (S67).

---

## Escopo

### Arquivos a criar
- `tests/integration/test_finances/test_finance_consolidate_debt_api.py`

### Arquivos a modificar
- `finances/services/installment_plan_service.py` — novo `consolidate_open_bills(...)` + constantes PT novas. `convert_deferred`/`materialize_schedule` intocados.
- `finances/viewsets/crud_views.py` — `@action(detail=True, methods=["post"]) consolidate_debt` no `BillingAccountViewSet` (import de `InstallmentPlanService` + `InstallmentPlanSerializer`).
- `tests/unit/test_finances/test_installment_plan_service.py` — cenários novos (abaixo).

### NÃO fazer (pertence a outras sessões / fora de escopo)
- **`convert_deferred` INTOCADO** (contrato S70) — o caso IPTU anual adiado single-bill continua existindo ao lado do novo caminho.
- **`pay`/`new_total`** — Sessão 68. **`apply_invoice`/draft** — Sessão 69. **`month_board`** — S66. **`open_balance`/`statement`** — S67. **Frontend (dialog de consolidação, CTA "Parcelar")** — S73/S75. **Terceiros (Fase 2)** — nada.
- **Nenhuma migração / mudança de model / serializer** — plano, parcelas e cancelamento usam modelos existentes (design §5).
- **Não relaxar** o guard de cancel do fluxo manual (`BillLifecycleService.set_state`/`assert_not_paid` intocados) — só o caminho de serviço da consolidação admite parcial vivo.
- **Não deletar** bills de origem (CANCELED, nunca soft-delete — histórico auditável, como `convert_deferred`).

---

## Especificação

> Serviço stateless (`@staticmethod`), mensagens PT como constantes nomeadas, "hoje" via `today_sp()` (`core/services/timezone.py`), transação única. A action só parseia (400 PT) e delega.

### `InstallmentPlanService.consolidate_open_bills` (contrato S70 — parâmetros verbatim)

```python
@staticmethod
def consolidate_open_bills(
    *,
    account: BillingAccount,
    bill_ids: list[int],
    embedded: bool,
    installment_count: int,
    start_due_date: date,
    default_due_day: int,
    user: User | None = None,
) -> InstallmentPlan:
    """Consolida N bills em aberto da conta em 1 InstallmentPlan e CANCELA as origens,
    atomicamente.

    Caminho de serviço próprio que ADMITE cancelar bill com pagamento parcial vivo
    (diferente do guard de viewset/BillLifecycleService): a parte paga permanece como
    história real (PaymentAllocation viva — precedente convert_deferred/B9) e só o RESTO
    (amount_remaining) entra no plano — logo não há dupla cobrança nem dinheiro perdido.
    """
```

Passos, dentro de UM `transaction.atomic()`:

1. **Validar entrada**: `installment_count > 0` (reusar `_COUNT_POSITIVE_MSG`); `bill_ids` não vazia e **sem duplicatas** → senão `ValidationError` PT (`_BILL_IDS_INVALID = "Informe uma lista de contas sem repetições."`).
2. **Resolver posse e travar em DUAS fases** — `select_for_update` com o OR dos braços FALHA no Postgres (`NotSupportedError`: FOR UPDATE no lado anulável de outer join):
   - **(a) Resolver posse/validações SEM lock**: `Bill.objects.filter(pk__in=bill_ids).filter(Q(billing_account=account) | Q(installment__plan__billing_account=account))`. `len(found) != len(bill_ids)` → `ValidationError` PT (`_BILLS_NOT_FOUND = "Uma ou mais contas não foram encontradas ou não pertencem a esta conta cadastrada."`) — cobre id inexistente, soft-deletada (o manager já exclui) e bill de outra conta, sem vazar qual.
   - **(b) Travar SEM join**: `Bill.objects.select_for_update().filter(pk__in=[b.pk for b in found])` — lock por pk, sem outer join.
3. **Validar cada origem**:
   - `lifecycle_state == CANCELED` → `ValidationError` PT (`_BILL_CANCELED = "Não é possível consolidar uma conta cancelada."`). ACTIVE/SUSPENDED/DEFERRED são aceitas (a sub-seção "Dívida adiada/suspensa" é exatamente o alvo do CTA "Parcelar" — design §3.3/§3.5).
   - **Parcela de plano (pureza v1 — decisão do orquestrador)**: bill com FK `installment` setada OU com linha de parcela embutida (`BillLineItem.installment` vivo) de plano ATIVO → `ValidationError` PT orientando tratar o plano antigo primeiro (`_BILL_FROM_PLAN = "A conta #{id} é parcela de um plano ativo — cancele o plano antes de consolidar."`). Racional: sem isso o plano velho segue gerando parcelas em paralelo (dupla dívida) e o progresso N/M do extrato (S67) mente. O caso DMAE (bills recorrentes puras) não é afetado.
   - Competência aberta: `CondoMonthCloseService.assert_open(bill.competence_month)` p/ TODAS (400 acionável — a mensagem PT existente do serviço de fechamento já orienta reabrir) ANTES de qualquer escrita.
   - Resto: anotar via `Bill.objects.with_amounts(today_sp()).in_bulk(bill_ids)` (ou fetch equivalente) e exigir `amount_remaining > 0` em cada → senão `ValidationError` PT (`_BILL_NOT_OPEN = "A conta {description} não tem saldo em aberto."`).
4. **Criar o plano**: `total = Σ amount_remaining` (Decimal, resto — nunca `amount_total`); instanciar
   `InstallmentPlan(condominium=account.condominium, building=account.building, category=account.category, description=f"Consolidação de dívida — {account.name}", total_amount=total, installment_count=..., start_due_date=..., default_due_day=..., lifecycle_state=ACTIVE, embedded=embedded, billing_account=account)`
   e chamar **`plan.full_clean()`** antes de `save()` — é o `full_clean` que dispara a regra existente `embedded=True ⇒ conta de consumo` (`models.py:592-603`), com a mensagem PT canônica; não reimplementar a regra.
5. **Materializar as parcelas**: `InstallmentPlanService.materialize_schedule(plan, user)` (reuso — Σ == total exato, resto na última).
6. **Cancelar as origens** (mesmo idioma de `convert_deferred:175-178`): para cada bill travada, `lifecycle_state = CANCELED`, `notes` recebe a linha `"Consolidada no plano #{plan.pk}"` (append com `\n` se já houver notes), `updated_by = user`, `save(update_fields=["lifecycle_state", "notes", "updated_by"])`.
7. `logger.info` (EN) e retornar o plano.

Efeito nas visões (por definição, sem código extra): CANCELED sai de Atrasadas, dos totais do board (S66) e do `open_balance` (S67) — a dívida passa a viver só no plano (dupla contagem impossível).

### Action `consolidate_debt` (`BillingAccountViewSet`, `crud_views.py`)

```python
@action(detail=True, methods=["post"])
def consolidate_debt(self, request: Request, pk: str | None = None) -> Response:
    """Consolida N bills em aberto desta conta em 1 plano (cancela as origens)."""
```

- `account = self.get_object()` (404 p/ inexistente/deletada; `IsAdminUser` cobre 401/403).
- Body `{bill_ids: int[], embedded: bool, installment_count: int, start_due_date: "YYYY-MM-DD", default_due_day: int}` — parse no idioma de `generate_month`/`bulk_pay`: `bill_ids` lista não vazia de ints, `embedded` exige **bool JSON estrito** (`isinstance(raw, bool)`, senão 400 — NUNCA `bool(...)`: `bool("false")` é `True`), `int(...)`, `date.fromisoformat(...)`; `KeyError`/`ValueError`/`TypeError` → 400 PT (`{"error": "Parâmetros inválidos: bill_ids (lista), embedded, installment_count, start_due_date, default_due_day."}`). `default_due_day` fora de 1–31 é rejeitado pelo `full_clean` do plano (validators do model) — não duplicar.
- Delegar por keyword; `ValidationError` → 400 `{"error": <msg PT>}`.
- **201** com `InstallmentPlanSerializer(plan, context={"request": request}).data` (parcelas aninhadas).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: nada a mockar — ORM/serviços/banco reais (`--reuse-db`). Zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_installment_plan_service.py` (estender — classe `TestConsolidateOpenBills`)

- [ ] `test_consolidates_two_open_bills_into_one_plan` — 2 bills ACTIVE (300 + 200) → plano `total_amount=500`, `installment_count` parcelas com Σ==500 (resto na última), `billing_account=account`, origens CANCELED. *"N bills em aberto → 1 plano com o total exato."*
- [ ] `test_partial_payment_counts_remaining_not_total` — bill 300 com alocação viva de 100 → plano soma 200; a `PaymentAllocation` permanece viva. *"Parcial entra pelo RESTO (B9) — sem dupla cobrança."*
- [ ] `test_bill_with_installment_fk_rejected` — bill de parcela avulsa (`billing_account=None`, `installment.plan.billing_account=account`) → `ValidationError` PT `_BILL_FROM_PLAN`; nada persiste. *"Pureza v1: parcela standalone nunca consolida — o braço 2 resolve a posse só para dar o erro específico."*
- [ ] `test_bill_with_embedded_line_of_active_plan_rejected` — bill com linha de parcela embutida (`BillLineItem.installment` vivo) de plano ATIVO → `ValidationError` PT `_BILL_FROM_PLAN`. *"Plano vivo em paralelo = dupla dívida + progresso N/M mentiroso; cancele o plano antes."*
- [ ] `test_bill_of_other_account_rejected` — bill de outra conta na lista → `ValidationError`; nada persiste. *"Posse validada pelos dois braços — cross-account nunca passa."*
- [ ] `test_canceled_and_deleted_bills_rejected` — CANCELED na lista → `ValidationError`; id soft-deletado → `ValidationError` (não encontrada). *"CANCELED/deletada nunca consolida."*
- [ ] `test_suspended_and_deferred_bills_accepted` — SUSPENDED + DEFERRED com resto → consolidadas (caso do CTA da sub-seção de dívida). *"Dívida adiada/suspensa é o alvo do fluxo."*
- [ ] `test_fully_paid_bill_rejected` — bill com resto 0 → `ValidationError` PT. *"Sem saldo em aberto, nada a consolidar."*
- [ ] `test_closed_competence_rejected_before_any_write` — 2ª bill em competência fechada (`make_condo_month_close`) → `ValidationError`; NENHUM plano/parcela criado, 1ª bill segue ACTIVE. *"Todas as competências abertas + atomicidade (400 acionável)."*
- [ ] `test_embedded_requires_consumption_account` — `embedded=True` com conta IPTU → `ValidationError` com a mensagem canônica de `InstallmentPlan.clean`; com conta WATER → plano `embedded=True` criado. *"Regra existente via full_clean — não duplicada."*
- [ ] `test_duplicate_or_empty_bill_ids_rejected` — `[7, 7]` e `[]` → `ValidationError` PT. *"Entrada saneada no serviço."*
- [ ] `test_installment_count_non_positive_rejected` — `0` → `ValidationError` `_COUNT_POSITIVE_MSG`. *"Reusa a constante existente."*
- [ ] `test_origin_notes_receive_plan_reference` — origem com `notes` prévia → notes termina com `"Consolidada no plano #<id>"` preservando o texto anterior. *"Auditoria no próprio registro."*
- [ ] `test_installments_sum_equals_total_with_cents` — 3 bills somando 100.01, 3 parcelas → [33.33, 33.33, 33.35] (Σ exato via `materialize_schedule`/`_split_amount`). *"Centavos exatos, resto na última."*
- [ ] `test_convert_deferred_untouched` — cenário IPTU adiado da suite existente continua passando (regressão dirigida via o próprio arquivo). *"convert_deferred permanece intocado."*

#### `tests/integration/test_finances/test_finance_consolidate_debt_api.py` (novo)

`pytestmark = [pytest.mark.integration, pytest.mark.django_db]`; `URL = f"/api/finances/billing-accounts/{pk}/consolidate_debt/"`.

- [ ] `test_consolidate_debt_requires_authentication` — anônimo → 401. *"Anônimo → 401."*
- [ ] `test_consolidate_debt_forbidden_for_non_admin` — não-staff → 403. *"Não-admin → 403 (IsAdminUser)."*
- [ ] `test_consolidate_debt_happy_path_returns_201_plan` — 2 bills em aberto → 201; body com `total_amount`, `installments` (N itens), `billing_account.id == account.id`; origens CANCELED no banco. *"201 com o plano serializado (parcelas aninhadas)."*
- [ ] `test_consolidate_debt_invalid_payload_returns_400` — sem `bill_ids` / `start_due_date` inválida → 400 PT. *"Payload inválido → 400 PT."*
- [ ] `test_consolidate_debt_non_bool_embedded_returns_400` — payload `{"embedded": "false"}` → 400 PT; nada persiste. *"bool JSON estrito: bool('false') é True — string nunca passa."*
- [ ] `test_consolidate_debt_cross_account_bill_returns_400` — bill de outra conta → 400 PT; nada muda. *"Posse via API."*
- [ ] `test_consolidate_debt_closed_month_returns_400` — competência fechada → 400 com a mensagem PT do fechamento. *"Erro acionável de mês fechado atravessa a action."*
- [ ] `test_consolidate_debt_embedded_iptu_returns_400` — `embedded=True` em conta IPTU → 400 com a mensagem canônica. *"Regra embedded⇒consumo via API."*
- [ ] `test_consolidate_debt_unknown_account_returns_404` — pk inexistente → 404. *"Conta inexistente/deletada → 404."*

> Rodar (devem **falhar** — serviço/action não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_installment_plan_service.py tests/integration/test_finances/test_finance_consolidate_debt_api.py -q
> ```

### 2. GREEN — implementar

1. `installment_plan_service.py` — `consolidate_open_bills` + constantes PT (`_BILL_IDS_INVALID`, `_BILLS_NOT_FOUND`, `_BILL_CANCELED`, `_BILL_NOT_OPEN`, `_BILL_FROM_PLAN`), reusando `_COUNT_POSITIVE_MSG` e `materialize_schedule`.
2. `crud_views.py` — action `consolidate_debt` no `BillingAccountViewSet` (imports diretos: `InstallmentPlanService`, `InstallmentPlanSerializer`).

### 3. REFACTOR — DRY / clareza
- Validações como funções privadas nomeadas (`_locked_owned_bills`, `_assert_consolidatable`) — SRP, cada uma uma responsabilidade.
- Confirmar reuso real de `materialize_schedule` (nenhum loop de `Installment.objects.create` novo no consolidate).
- Docstring do cancelamento explica o desvio consciente do guard B4 (parcial vivo admitido; precedente `convert_deferred` B9) — não é workaround, é regra de domínio.

### 4. VERIFY — gate (escopo desta sessão)

```bash
python -m pytest tests/unit/test_finances/test_installment_plan_service.py tests/integration/test_finances/test_finance_consolidate_debt_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
python -m pytest tests/unit/test_finances/test_generation_installments_payroll.py tests/integration/test_finances/test_finance_viewset_guards.py -q  # regressão dirigida
ruff check finances/ tests/unit/test_finances/test_installment_plan_service.py tests/integration/test_finances/test_finance_consolidate_debt_api.py
ruff format --check finances/ tests/unit/test_finances/test_installment_plan_service.py tests/integration/test_finances/test_finance_consolidate_debt_api.py
mypy core/ finances/
pyright finances/services/installment_plan_service.py finances/viewsets/crud_views.py
```

---

## Constraints

- **Transação única e explícita** (`transaction.atomic`): plano + parcelas + cancelamentos são tudo-ou-nada; validações (posse, estado, competências, resto) ANTES de qualquer escrita.
- **Dinheiro via annotation** (`with_amounts(today_sp())`) — total do plano = Σ `amount_remaining` (resto), nunca `amount_total` nem soma de alocações em Python.
- **Posse pelos DOIS braços** (`billing_account` OU `installment__plan__billing_account`) na fase (a) SEM lock — obrigatório para dar a rejeição PT específica (`_BILL_FROM_PLAN`) em vez de "não encontrada"; lock na fase (b) por `pk__in` sem join (`FOR UPDATE` com outer join anulável quebra no Postgres).
- **Cancelamento direto no serviço** (espelho `convert_deferred:175-178`) — NUNCA via `BillLifecycleService.set_state` (o `assert_not_paid` de lá continua valendo p/ o cancel manual do viewset); origens CANCELED, nunca soft-deletadas.
- **`embedded ⇒ consumo` via `plan.full_clean()`** — regra única em `InstallmentPlan.clean` (`models.py:592-603`); proibido duplicá-la no serviço/action.
- **`convert_deferred` e `materialize_schedule` intocados**; nenhuma migração/model/serializer; sem frontend.
- **Lógica só no serviço**; action fina (parse 400 PT → delega → 201). Shape de erro `{"error": <PT>}`.
- **Sem suppressions** (`# noqa`, `# type: ignore`), sem `from __future__`/`TYPE_CHECKING`, sem re-exports; mensagens PT nomeadas, logs EN.

## Critérios de Aceite (binários)

- [ ] `consolidate_open_bills(account, bill_ids, embedded, installment_count, start_due_date, default_due_day, user)` cria 1 plano `total = Σ amount_remaining` das origens (parciais = resto), `billing_account=account`, parcelas via `materialize_schedule` (Σ exato, resto na última), e cancela as origens com `notes += "Consolidada no plano #<id>"` — tudo numa transação (posse resolvida SEM lock, `select_for_update` por `pk__in` sem join).
- [ ] Validações: posse pelos dois braços; lista não vazia/sem duplicatas; nenhuma CANCELED/deletada; nenhuma parcela de plano (FK `installment` OU linha embutida de plano ATIVO → `_BILL_FROM_PLAN`, pureza v1); `amount_remaining > 0` em todas; TODAS as competências abertas (400 acionável); `installment_count > 0`; `embedded=True` só com conta de consumo (via `full_clean`); `embedded` bool JSON estrito na action.
- [ ] Falha em qualquer validação ⇒ NADA persiste (plano, parcelas, cancelamentos) — travado por teste.
- [ ] Pagamento parcial vivo é admitido no cancelamento (docstring explica; alocação permanece viva); guard manual de cancel (`set_state`/`assert_not_paid`) intocado.
- [ ] `POST /api/finances/billing-accounts/{id}/consolidate_debt/` (`IsAdminUser`): 201 com `InstallmentPlanSerializer` (parcelas aninhadas); 400 payload/regras PT; 404 conta; 401/403 auth; rota auto-exposta (`finances/urls.py` intacto).
- [ ] `convert_deferred` intocado (suite existente verde sem edição).
- [ ] Gate verde: pytest escopado 100% + coverage `finances` ≥90% nos módulos tocados; `ruff check`/`format --check`, `mypy core/ finances/`, `pyright` — zero erros e zero warnings, sem suppressions.

## Handoff

1. Rodar e confirmar verde o gate do VERIFY + regressão dirigida.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`: Sessão 70 **concluída**; criado (`test_finance_consolidate_debt_api.py`), modificados (`installment_plan_service.py`, `crud_views.py`, `test_installment_plan_service.py`); nota: "consolidação multi-bill/multi-tipo: N bills em aberto (ACTIVE/SUSPENDED/DEFERRED; posse pelos dois braços SEM lock + `select_for_update` por pk sem join; parcelas de plano rejeitadas — pureza v1) → 1 plano (total = Σ restos, `materialize_schedule` reusado) + origens CANCELED com nota, atômico; caminho de serviço admite parcial vivo (docstring/B9); action 201 no `BillingAccountViewSet` (`embedded` bool JSON estrito); `convert_deferred` intocado."
3. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (na branch `feat/condo-bills-cockpit`):
   ```
   feat(finances): complete session 70 — consolidate_open_bills service + consolidate_debt action (N open bills -> 1 plan, atomic origin cancel)

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
5. Próxima sessão: **71 — FE data layer** (schemas/query-keys/hooks/MSW consumindo os contratos de 66–70).
