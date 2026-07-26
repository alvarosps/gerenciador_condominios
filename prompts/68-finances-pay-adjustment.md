# Sessão 68 — Backend: `pay` com ajuste de total (`new_total`: linha-semente estimada / linha "Juros/multa")

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida (`docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`, rev. 2)
> **Sessões da feature**: 65 → 66 → 67 → **68** → 69 → 70 → 71–76 (FE)
> **Fase**: pagar em 1 clique com valor real ≠ estimativa (design §3.3). Hoje, pagar R$230 sobre uma bill estimada em R$200 dá 400 por over-allocation; pagar R$180 deixa um resto-fantasma de R$20. Esta sessão estende `BillPaymentService.pay` com `new_total` opcional: numa bill **estimada**, ajusta a linha-semente para o valor real ANTES de alocar; numa bill **confirmada**, `new_total >` total adiciona uma linha "Juros/multa" com a diferença — tudo na MESMA transação. A action `pay` ganha o campo opcional `new_total`; `bulk_pay` NÃO ganha ajuste.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.3 "Cockpit — Pagar em 1 clique", §8 "Tratamento de erros", §9 "Pagar-com-ajuste")**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões + CONTRATOS AUTORITATIVOS S65/S68** (somente leitura — o orquestrador atualiza): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`pay` atual (base a estender)** | `finances/services/bill_payment_service.py:59-110` — guards de mês (competência `:74`, caixa `:75`), ACTIVE-only `:76-77`, `select_for_update` `:80`, leitura do resto via `with_amounts` `:82-83`, `amount=None ⇒ resto` `:84-85`, positivo `:86-87`, over-allocation `:88-89` | TODOS esses guards permanecem; o ajuste entra DEPOIS do lock e ANTES da leitura do resto |
| **`unpay`** | `bill_payment_service.py:112-130` | Fica INTOCADO — não reverte ajuste de linha nem re-marca `amount_is_estimated` (contrato S65) |
| **Constantes PT nomeadas** | `bill_payment_service.py:50-53` (`_AMOUNT_NON_POSITIVE`, `_OVER_ALLOCATION`, …) | Idioma das novas mensagens desta sessão |
| **Action `pay` (onde ler `new_total`)** | `finances/viewsets/crud_views.py:354-378` (parse 400 PT → delega → `_serialized_bill`) | A action só ganha o parse do campo; zero lógica nova na view |
| **`bulk_pay` (NÃO ganha ajuste)** | `crud_views.py:380-411` (delega ao `pay` por bill, `amount=None`) | Fica INTOCADO; payload com `new_total` é simplesmente ignorado |
| **Linha-semente da geração** | `finances/services/bill_generation_service.py:142-151` (`description=account.name`, `is_offset=False`, `category=account.category`) | Forma da semente a criar quando a bill estimada nasceu SEM linha (`expected_amount=0`, "aguardando fatura") |
| **Linha de parcela embutida (intocável)** | `bill_generation_service.py:199-208` (`installment=` FK setada) | Linha com FK `installment` NUNCA é ajustada pelo `new_total` |
| **`with_amounts` (dinheiro via annotation)** | `finances/models.py:223-273` | `amount_total`/`amount_remaining` — nunca somar em Python |
| **Testes exemplar (estilo + factories)** | `tests/unit/test_finances/test_bill_payment_service.py:1-80` (`_bill_with_total`, `_amounts`, `make_bill`/`make_bill_line_item`) + `tests/integration/test_finances/test_finance_bill_actions.py` | Estender esses arquivos, no mesmo idioma |

### O que a S65 já entregou (PRÉ-REQUISITO — NÃO recriar)

- `Bill.amount_is_estimated` (BooleanField, default `False`) + migração; `True` só em `BillGenerationService._ensure_account_bill` quando `created`; **`False` já é setado por `BillPaymentService.pay`** (cobre `bulk_pay` por delegação) e por `update_with_lines`; `unpay` NÃO re-marca; `BillSerializer` expõe read-only.

> **Se a S65 não estiver concluída, PARE.** Esta sessão lê `bill.amount_is_estimated` e NÃO reimplementa a limpeza da flag (só a trava por teste no caminho `new_total`).

---

## Escopo

### Arquivos a criar
- Nenhum.

### Arquivos a modificar
- `finances/services/bill_payment_service.py` — `pay(...)` ganha `new_total: Decimal | None = None` + método privado `_apply_new_total` + constantes PT novas.
- `finances/viewsets/crud_views.py` — action `pay` lê `new_total` opcional (decimal string) e repassa por keyword. **`bulk_pay` intocado.**
- `tests/unit/test_finances/test_bill_payment_service.py` — cenários novos (abaixo).
- `tests/integration/test_finances/test_finance_bill_actions.py` — action `pay` com `new_total` (abaixo).

### NÃO fazer (pertence a outras sessões / fora de escopo)
- **Parser/`apply_invoice`/draft** — Sessão 69. **`consolidate_open_bills`/`consolidate_debt`** — Sessão 70. **`month_board`/`statement`** — S66/S67. **Frontend (popover pagar)** — S75.
- **`bulk_pay` NÃO aceita ajuste** (contrato S68): não adicionar `new_total` ao `bulk_pay` — nem parse, nem repasse.
- **`unpay` intocado**: reverter um pagamento NÃO desfaz o ajuste de linha nem remove a linha "Juros/multa" (as linhas são história real da fatura) e NÃO re-marca `amount_is_estimated`.
- **Nenhuma migração / mudança de model / serializer** (o campo `amount_is_estimated` é da S65).
- **Não mexer** em `update_with_lines`/`update_header`/`create_with_lines` — a edição de valor pelo modal continua sendo `update_with_lines` (S58).

---

## Especificação

> Serviço stateless; toda a lógica no service (`.claude/rules/architecture.md`); a action só parseia (400 PT) e delega. Dinheiro SEMPRE via `Bill.objects.with_amounts(today_sp())` (`today_sp` de `core/services/timezone.py`). Mensagens ao usuário em PT, constantes nomeadas.

### Assinatura (contrato S68 — copiar verbatim)

```python
@staticmethod
def pay(
    bill: Bill,
    payment_date: date,
    amount: Decimal | None = None,
    funded_from: str = FundedFrom.CAIXA,
    new_total: Decimal | None = None,
    user: User | None = None,
) -> Payment:
```

*(Os call sites atuais — `pay` action, `bulk_pay`, testes — passam `bill, payment_date, amount, funded_from` posicionais e `user=` keyword: inserir `new_total` ANTES de `user` não quebra nenhum; confirmar por grep.)*

### Semântica do `new_total` (ajusta o TOTAL antes de alocar, na MESMA transação)

`new_total=None` ⇒ comportamento atual byte a byte. Com `new_total`:

1. Guards existentes ANTES do ajuste, inalterados: mês de competência aberto, mês de caixa aberto, `lifecycle_state == ACTIVE`.
2. Dentro do `transaction.atomic()` existente, após o `select_for_update` (`:80`), chamar `BillPaymentService._apply_new_total(locked, new_total, user)`; SÓ DEPOIS ler `amount_remaining` via `with_amounts` — assim `amount=None` defaulta para o **novo** resto e o guard de over-allocation (`:88-89`) vale **após** o ajuste.
3. **Linhas de parcela (FK `installment` setada) são intocáveis** em todos os caminhos.

`_apply_new_total(locked, new_total, user)` — regras por estado da flag:

- **`amount_is_estimated=True`** (bill estimada): "linhas-semente" = `BillLineItem.objects.filter(bill=locked, installment__isnull=True)` (vivas).
  - **Exatamente 1 semente**: ajustar por delta — `seed.amount += new_total − total_atual` (total via `with_amounts`); `seed.full_clean(exclude=["bill"])` + save. Resultado: total anotado == `new_total`; parcelas embutidas intocadas.
  - **0 sementes** (bill "aguardando fatura", `expected_amount=0`): **criar** a semente no formato da geração (`bill_generation_service.py:142-151`): `description=locked.description`, `amount = new_total − total_atual`, `is_offset=False`, `category=locked.category`. *(Decisão pinada: sem isto o pagar-em-1-clique de "aguardando fatura" ficaria impossível — S75.)*
  - **>1 semente**: `ValidationError` PT (`_ESTIMATED_MULTIPLE_LINES = "A conta estimada tem mais de uma linha — edite a conta pelas linhas."`).
  - Delta que deixaria a semente negativa (`new_total <` soma das parcelas embutidas) → `ValidationError` PT (`_NEW_TOTAL_BELOW_INSTALLMENTS = "O novo total é menor que a soma das parcelas embutidas da conta."`). Fronteira pinada: `new_total ==` Σ parcelas embutidas ⇒ a semente termina em EXATAMENTE 0 — permitido (constraint do model é `amount >= 0`).
- **`amount_is_estimated=False`** (bill confirmada) — nesta ordem (contrato S68 rev.: o nº de linhas NÃO importa aqui — fatura importada CEEE/DMAE é multi-linha e é exatamente o caso Juros/multa):
  1. `new_total < total` → `ValidationError` PT (`_NEW_TOTAL_BELOW_TOTAL = "Edite a conta para reduzir o valor."`).
  2. `new_total > total` → criar `BillLineItem(bill=locked, description="Juros/multa", amount=new_total − total, is_offset=False, category=None)` (full_clean + save, audit user) — vale para QUALQUER quantidade de linhas vivas.
  3. `new_total == total` → no-op.
- A limpeza de `amount_is_estimated` no `pay` **já existe (S65)** — não duplicar; apenas travar por teste que o caminho com `new_total` também termina com a flag `False`.

### Action `pay` (`crud_views.py:354-378`)

- Ler `new_total_raw = request.data.get("new_total")`; se presente, `new_total = Decimal(str(new_total_raw))` dentro do `try` existente (`InvalidOperation`/`ValueError` → o 400 PT atual "Valor, data ou forma de pagamento inválido."); repassar `new_total=new_total` por keyword. Nada mais muda na action; `bulk_pay` intocado.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): NADA a mockar aqui — ORM real, serviço real, banco real (`--reuse-db`). `filterwarnings=error`: zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_bill_payment_service.py` (estender — classe `TestPayWithNewTotal`)

- [ ] `test_new_total_none_keeps_current_behavior` — *"new_total ausente: pagamento total idêntico ao comportamento atual."*
- [ ] `test_estimated_seed_adjusted_up_and_fully_paid` — estimada 200, `new_total=230`, `amount=230` → semente 230, total 230, `payment_status="paid"`, resto 0. *"Fatura real maior que a estimativa: semente ajustada e paga sem over-allocation."*
- [ ] `test_estimated_seed_adjusted_down_no_ghost_remainder` — estimada 200, `new_total=180`, `amount=180` → total 180, resto 0. *"Fatura real menor: sem resto-fantasma de R$20."*
- [ ] `test_estimated_with_embedded_installment_adjusts_only_seed` — semente 200 + linha de parcela 530 (FK `installment`), `new_total=750` → semente 220, parcela intocada (mesmo pk/amount), total 750. *"Delta aplicado só na semente; linha de parcela intocável."*
- [ ] `test_estimated_zero_lines_creates_seed` — bill estimada sem linha, `new_total=150` → semente criada (`description == bill.description`, `is_offset=False`), total 150, paga. *"Bill 'aguardando fatura' paga em 1 clique cria a semente."*
- [ ] `test_estimated_multiple_non_installment_lines_rejected` — estimada com 2 linhas sem `installment` → `ValidationError`, nada persiste. *"Semente ambígua: rejeita e não altera nada."*
- [ ] `test_new_total_below_embedded_installments_rejected` — semente 200 + parcela 530, `new_total=500` → `ValidationError` PT; linhas inalteradas. *"new_total abaixo da soma das parcelas: semente negativa é impossível."*
- [ ] `test_estimated_new_total_equal_to_installments_zeroes_seed` — semente 200 + parcela 530, `new_total=530` → semente termina em EXATAMENTE 0 (viva), total 530. *"Fronteira: new_total == Σ parcelas embutidas zera a semente — permitido (constraint do model é amount >= 0)."*
- [ ] `test_over_allocation_still_guarded_after_adjustment` — estimada 200, `new_total=230`, `amount=250` → `ValidationError` `_OVER_ALLOCATION`; **nenhum** ajuste de linha persiste (atomicidade). *"Guard de over-allocation vale APÓS o ajuste, e o rollback desfaz o ajuste."*
- [ ] `test_confirmed_new_total_above_adds_juros_multa_line` — confirmada 1 linha 300, `new_total=315`, `amount=315` → linha nova `description="Juros/multa"`, `amount=15`, `is_offset=False`, `category is None`; total 315 pago. *"Juros/multa CEEE/DMAE em bill confirmada de linha única."*
- [ ] `test_confirmed_new_total_below_rejected` — confirmada 300, `new_total=280` → `ValidationError` com "Edite a conta para reduzir o valor.". *"Reduzir total em confirmada é edição, não pagamento."*
- [ ] `test_confirmed_multiple_lines_new_total_adds_juros_multa` — confirmada com 2 linhas não-parcela (total 350), `new_total=400`, `amount=400` → linha "Juros/multa" de 50 criada, as 2 linhas originais intocadas, total 400 pago. *"Juros/multa em confirmada multi-linha (fatura importada CEEE/DMAE paga com atraso)."*
- [ ] `test_confirmed_partially_paid_new_total_adds_juros_on_top` — confirmada total 300 com pagamento vivo de 100, `new_total=315`, `amount=215` → linha "Juros/multa" de 15 criada, bill quitada (resto 0). *"Juros sobre o resto: caso real de atraso em bill parcialmente paga."*
- [ ] `test_confirmed_new_total_equal_is_noop` — confirmada 300, `new_total=300` → nenhuma linha nova, pagamento normal. *"new_total igual ao total: no-op."*
- [ ] `test_amount_default_is_adjusted_remaining` — estimada 200, `new_total=230`, `amount=None` → `payment.amount == 230`. *"amount=None defaulta para o resto PÓS-ajuste."*
- [ ] `test_new_total_respects_active_and_closed_month_guards` — bill SUSPENDED + `new_total` → `ValidationError` `_BILL_NOT_ACTIVE`; competência fechada (`make_condo_month_close`) → `ValidationError`. *"Guards ACTIVE/mês fechado inalterados com new_total."*
- [ ] `test_estimated_flag_cleared_after_pay_with_new_total` — estimada (`amount_is_estimated=True`), pay com `new_total` → `refresh_from_db`, flag `False` (regressão do contrato S65). *"Pagar com ajuste também confirma a bill."*
- [ ] `test_unpay_keeps_adjustment_and_flag` — pagar confirmada com Juros/multa, `unpay` → linha "Juros/multa" continua viva; `amount_is_estimated` continua `False`. *"unpay reverte só o pagamento, nunca o ajuste de linhas/flag."*

#### `tests/integration/test_finances/test_finance_bill_actions.py` (estender)

- [ ] `test_pay_action_accepts_new_total_string` — POST `bills/{id}/pay/` `{payment_date, amount, new_total: "230.00"}` em bill estimada 200 → 200; `amount_total == "230.00"` na resposta; `amount_is_estimated is False`. *"Action repassa new_total (decimal string) e devolve a bill ajustada."*
- [ ] `test_pay_action_invalid_new_total_returns_400` — `new_total: "abc"` → 400 PT ("Valor, data ou forma de pagamento inválido."). *"new_total inválido → 400 PT."*
- [ ] `test_pay_action_confirmed_reduction_returns_400` — confirmada, `new_total` menor → 400 com "Edite a conta para reduzir o valor.". *"Erro de negócio PT atravessa a action como 400."*
- [ ] `test_bulk_pay_ignores_new_total` — POST `bills/bulk_pay/` com `new_total` no payload → 200, bills pagas pelo resto ATUAL, nenhuma linha criada/ajustada. *"bulk_pay não ganha ajuste (contrato S68)."*

> Rodar (devem **falhar**):
> ```bash
> python -m pytest tests/unit/test_finances/test_bill_payment_service.py tests/integration/test_finances/test_finance_bill_actions.py -q
> ```

### 2. GREEN — implementar

1. `bill_payment_service.py`: assinatura nova + `_apply_new_total` (privado, SRP) + constantes PT (`_ESTIMATED_MULTIPLE_LINES`, `_NEW_TOTAL_BELOW_INSTALLMENTS`, `_NEW_TOTAL_BELOW_TOTAL`).
2. `crud_views.py`: parse do `new_total` na action `pay` (dentro do `try` existente).

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `_apply_new_total` decide por flag e delega a duas funções privadas nomeadas (`_adjust_estimated_seed`, `_append_surcharge_line`) — cada uma UMA responsabilidade.
- Leitura de total/resto SEMPRE via `with_amounts` (nunca `Sum` manual em Python).
- Docstring do `pay` atualizada (semântica do `new_total` + por que o guard de over-allocation roda após o ajuste).

### 4. VERIFY — gate (escopo desta sessão)

```bash
python -m pytest tests/unit/test_finances/test_bill_payment_service.py tests/integration/test_finances/test_finance_bill_actions.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
ruff check finances/ tests/unit/test_finances/test_bill_payment_service.py tests/integration/test_finances/test_finance_bill_actions.py
ruff format --check finances/ tests/unit/test_finances/test_bill_payment_service.py tests/integration/test_finances/test_finance_bill_actions.py
mypy core/ finances/
pyright finances/services/bill_payment_service.py finances/viewsets/crud_views.py
```

> **Regressão dirigida** (pagamento/fechamento/guards não regridem):
> ```bash
> python -m pytest tests/unit/test_finances/test_finances_closed_month_guards.py tests/integration/test_finances/test_finance_viewset_guards.py tests/integration/test_finances/test_finance_write_path_integrity.py -q
> ```

---

## Constraints

- **Lógica só no serviço**; a action parseia (400 PT) e delega — zero regra na view.
- **Transação única**: ajuste de linha + Payment + PaymentAllocation no MESMO `transaction.atomic()`; falha em qualquer passo desfaz tudo (travado por teste).
- **Dinheiro via annotation** (`with_amounts(today_sp())`) — nunca `@property`/soma Python; `today_sp` de `core/services/timezone.py`.
- **Linha com FK `installment` intocável** em qualquer caminho do `new_total`.
- **`bulk_pay` e `unpay` intocados**; nenhuma migração/model/serializer/frontend.
- **Sem suppressions** (`# noqa`, `# type: ignore`), **sem** `from __future__ import annotations`/`TYPE_CHECKING`, **sem re-exports**. Mensagens ao usuário em PT (constantes nomeadas); logs em EN.
- Shape de erro das actions: `{"error": <msg PT>}` (idioma atual de `crud_views.py` — não introduzir `{detail}` aqui).

## Critérios de Aceite (binários)

- [ ] `BillPaymentService.pay(bill, payment_date, amount=None, funded_from=CAIXA, new_total=None, user=None)` — assinatura exata; `new_total=None` preserva o comportamento atual (suite antiga verde sem edição).
- [ ] Estimada: 1 semente → delta até total==`new_total`; 0 sementes → semente criada no formato da geração; >1 → 400 PT; parcelas embutidas intocadas; semente negativa impossível (400 PT).
- [ ] Confirmada (qualquer nº de linhas): `new_total <` total → 400 "Edite a conta para reduzir o valor."; `new_total >` total → linha "Juros/multa" (`is_offset=False`, sem categoria) com a diferença; igual → no-op.
- [ ] Ajuste ANTES da alocação, mesma transação; `amount=None` defaulta ao resto pós-ajuste; over-allocation/positivo/ACTIVE/mês fechado valem após o ajuste; rollback desfaz o ajuste.
- [ ] `amount_is_estimated` termina `False` no caminho `new_total` (via S65, sem duplicação); `unpay` não reverte ajuste nem re-marca.
- [ ] Action `pay` aceita `new_total` (decimal string, inválido → 400 PT); `bulk_pay` ignora o campo (código intocado).
- [ ] Gate verde: pytest escopado 100% + coverage `finances` ≥90% nos módulos tocados; `ruff check`/`format --check`, `mypy core/ finances/`, `pyright` — zero erros e zero warnings, sem suppressions.

## Handoff

1. Rodar e confirmar verde o gate do VERIFY + regressão dirigida.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`: Sessão 68 **concluída**; arquivos modificados (`bill_payment_service.py`, `crud_views.py`, 2 arquivos de teste); nota: "pay ganhou `new_total` (estimada: delta na semente/cria semente; confirmada: linha Juros/multa; bloqueios PT do contrato S68), mesma transação, guards intactos pós-ajuste; action `pay` com `new_total` opcional; `bulk_pay`/`unpay` intocados."
3. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (na branch `feat/condo-bills-cockpit`):
   ```
   feat(finances): complete session 68 — pay with new_total (estimated seed adjust / juros-multa line, single transaction)

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
5. Próxima sessão: **69 — `apply_invoice`** (depende da 65; usa o parser S59/S60 existente).
