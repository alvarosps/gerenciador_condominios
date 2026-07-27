# Sessão 69 — Backend: `POST /api/finances/bills/{id}/apply_invoice` + prédio no draft do parser

> **Feature**: Cockpit operacional de contas + extrato por conta + consolidação de dívida (`docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`, rev. 2)
> **Sessões da feature**: 65 → 66 → 67 → 68 → **69** → 70 → 71–76 (FE)
> **Fase**: importar PDF direto na linha do cockpit (design §3.3/§4). Hoje o parser só produz um DRAFT avulso (`parse_invoice`, S60) que o modal salva. Esta sessão: (a) o draft passa a expor `matched_account.building_id` + warning de divergência de prédio; (b) nova action `POST bills/{id}/apply_invoice` que parseia o PDF em memória e **aplica à bill alvo** via `BillService.update_with_lines` na mesma transação (linhas + statement + header do draft), **preservando as linhas de parcela embutida** e limpando `amount_is_estimated`. O fluxo avulso `parse_invoice` (draft → modal) permanece intocado em contrato e comportamento.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §3.3 "Importar PDF no fluxo", §4 linha `apply_invoice`, §8 "divergência → aviso explícito")**: `@docs/plans/2026-07-26-condo-bills-operational-redesign-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões + CONTRATOS AUTORITATIVOS S65/S69** (somente leitura): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Action `parse_invoice` (fluxo de PDF a reusar)** | `finances/viewsets/crud_views.py:541-567` (sem arquivo → 400 `_ERR_NO_FILE`; `pdfplumber.open` inválido → 400 `_ERR_NOT_PDF`; `detect_and_parse` emissor desconhecido → 422; delega) | `apply_invoice` repete EXATAMENTE esses passos de leitura/validação — extrair helper privado compartilhado (DRY); o comportamento do `parse_invoice` fica travado por `tests/integration/test_parse_invoice_api.py`, que deve passar SEM edição |
| **`InvoiceDraftService` (ponto de extensão)** | `finances/services/invoice_draft_service.py:63-99` (`build_draft`), `:107-112` (`_match_account`), `:49-60` (warnings PT), `:96` (`matched_account` = `BillingAccountSerializer(account).data`), `:136-164` (`_reconcile_line` — filtro de posse do plano embutido), `:166-182` (`_existing_bill_id`) | Onde entram `building_id` e o warning de divergência; a reconciliação de `installment_id` já existe — REUSAR |
| **`update_with_lines` (caminho de aplicação)** | `finances/services/bill_service.py:280-307` (guards `assert_not_paid` `:298` + `assert_open` `:299`; replace de linhas `:303-304`; `_apply_header` `:262-278` + `_EDITABLE_HEADER_FIELDS` `:128-140`) | Ganha a regra nova: **substituir APENAS linhas sem FK `installment`** (com dedup); depois a aplicação inteira delega aqui |
| **Dedup `(bill, installment)`** | `finances/services/bill_generation_service.py:197` | Espelho do dedup da linha de parcela na regra nova do `update_with_lines` |
| **Filtro de posse da parcela** | `crud_views.py:262-281` (`_resolve_owned_installment`: `plan__billing_account`, `plan__embedded=True`, `plan__lifecycle_state=ACTIVE`, `plan__is_deleted=False`) | O apply resolve `installment_id → Installment` com o MESMO filtro |
| **`ParsedInvoice` (campos disponíveis)** | `finances/services/invoice_parsing/base.py:43-62` | Header aplicável = `due_date` + `external_identifier` (**NÃO existe `issue_date` no parser** — divergência de contrato já reportada ao orquestrador; aplicar só os campos existentes) |
| **Fixtures sanitizadas (fronteira externa = PDF)** | `tests/unit/test_finances/fixtures/invoices/*.txt` + `tests/unit/test_finances/conftest.py:36-49` (`invoice_pdf_bytes`) | Testes postam PDFs renderizados das fixtures — NADA de mock de `pdfplumber` |
| **Integração multipart exemplar** | `tests/integration/test_parse_invoice_api.py:1-68` (`_pdf_upload`, `DMAE_UC`, clients 401/403) | Forma do novo `test_apply_invoice_api.py` |
| **Serialização da resposta** | `crud_views.py:350-352` (`_serialized_bill` — bill com amounts) | Response 200 do `apply_invoice` |

### O que sessões anteriores já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S58**: `BillService.update_with_lines` (replace + upsert statement + header, guards UNPAID/mês aberto); statements 1:1.
- **S59/S60**: parser core (`detect_and_parse`) + `InvoiceDraftService.build_draft` (match, reconciliação `installment_id`, idempotência) + action `parse_invoice`.
- **S65**: `Bill.amount_is_estimated`; **`update_with_lines` já limpa a flag** — o apply herda a limpeza por delegação (não reimplementar).

> **Se a S65 não estiver concluída, PARE.** DEPENDENCY ORDER: 69 depende de **65** (e do que já existe de 58-60 em master).

---

## Escopo

### Arquivos a criar
- `finances/services/invoice_apply_service.py` — `InvoiceApplyService.apply(bill, parsed, user)`: validações de match (400 PT) + montagem de linhas/statement/header + delegação a `update_with_lines`. O `InvoiceDraftService` continua **0 writes** (invariante documentada) — por isso o apply é um serviço separado.
- `tests/unit/test_finances/test_invoice_apply_service.py`
- `tests/integration/test_apply_invoice_api.py` (irmão de `test_parse_invoice_api.py`)

### Arquivos a modificar
- `finances/services/invoice_draft_service.py` — `build_draft(parsed, target_bill=None)`; `matched_account` ganha `building_id` plano; warning de divergência de prédio quando `target_bill` é dado.
- `finances/services/bill_service.py` — `update_with_lines`: substitui só linhas `installment__isnull=True` + dedup de linha entrante com `installment` já vivo.
- `finances/viewsets/crud_views.py` — helper privado `_read_parsed_invoice(request)` (extraído do `parse_invoice`, mesmos 400/422 PT) + action `apply_invoice`.
- `tests/unit/test_finances/test_invoice_draft_service.py` — casos novos (building_id, divergência).
- `tests/unit/test_finances/test_bill_service.py` — regra de preservação/dedup do `update_with_lines`.

### NÃO fazer (pertence a outras sessões / fora de escopo)
- **`pay`/`new_total`** — Sessão 68. **`consolidate_open_bills`/`consolidate_debt`** — Sessão 70. **`month_board`/`statement` endpoint** — S66/S67. **Frontend (`useApplyInvoice`, warnings no modal)** — S75.
- **Parser core (S59) intocado** — nenhuma mudança em `invoice_parsing/`.
- **Contrato do `parse_invoice` intocado**: `tests/integration/test_parse_invoice_api.py` passa **sem edição** (a extração do helper não muda status/mensagens/shape; o draft só GANHA `matched_account.building_id` — aditivo).
- **Não armazenar o PDF** (parse em memória, arquivo descartado). **Nenhuma migração / mudança de model / serializer** (`BillingAccountSerializer` fica intocado — o `building_id` plano é injetado no dict do draft pelo service, preservando o dual pattern do serializer).

---

## Especificação

> Mensagens ao usuário em PT (constantes nomeadas); logs EN. Direção: serviços importam `finances.models`/`finances.services.*` — nunca views/serializers de volta. `today_sp` de `core/services/timezone.py` quando precisar de "hoje".

### 1. Draft — `building_id` + warning de divergência (`invoice_draft_service.py`)

```python
@staticmethod
def build_draft(parsed: ParsedInvoice, target_bill: Bill | None = None) -> InvoiceDraft:
```

- `matched_account` passa a ser `{**BillingAccountSerializer(account).data, "building_id": account.building_id}` quando casou (`building_id: int|null` — o serializer expõe `building` aninhado e `building_id` só de escrita, então a chave plana é injetada aqui; serializer intocado).
- **Warning de divergência de prédio** (novo, constante `_WARN_BUILDING_MISMATCH`, PT com os dois lados, ex.: `"A conta casada pertence a outro prédio (conta: {account_building}; cobrança: {bill_building}). Confira antes de aplicar."`): emitido quando `target_bill is not None` **e** há conta casada **e** `target_bill.building_id != account.building_id`.
- **Warning de divergência de valor de PARCELA** (novo, constante `_WARN_INSTALLMENT_AMOUNT_MISMATCH`, PT com os dois valores): emitido no draft/apply quando `target_bill is not None` **e** a linha de PARCELA reconciliada do PDF tem valor ≠ da linha de parcela viva preservada na bill — **informa, não bloqueia; a divergência NUNCA é aplicada silenciosamente** (design §8; a linha viva preservada é a que vale, via dedup do item 2).
- `target_bill=None` (fluxo avulso `parse_invoice`) ⇒ comportamento e warnings atuais inalterados + a chave `building_id` nova. A action `parse_invoice` continua chamando `build_draft(parsed)`.

### 2. `update_with_lines` — substitui APENAS linhas sem FK `installment` (`bill_service.py:280-307`)

Regra nova (vale para TODOS os chamadores — refactor completo, sem flag de compat):

- O replace soft-deleta somente `BillLineItem.objects.filter(bill=bill, installment__isnull=True)`; linhas com FK `installment` (parcela embutida) **sobrevivem intactas** (mesmo pk).
- Linha ENTRANTE com `installment` setado cujo `(bill, installment)` já tem linha viva → **skip** (dedup, espelho de `bill_generation_service.py:197`) — o fluxo do modal (S63 reenvia a linha de parcela travada) e o apply (o parser reemite "PARCELA X/N" reconciliada) não duplicam dinheiro.
- Linha entrante com `installment` ainda SEM linha viva → criada normalmente (caminho atual).
- Atualizar a docstring; guards `assert_not_paid`/`assert_open` e o upsert de statement inalterados.

### 3. `InvoiceApplyService.apply` (novo serviço — toda a lógica de negócio da action)

```python
# finances/services/invoice_apply_service.py
class InvoiceApplyService:
    @staticmethod
    def apply(bill: Bill, parsed: ParsedInvoice, user: User | None = None) -> Bill:
        """Aplica uma fatura parseada À BILL ALVO via update_with_lines, na mesma transação."""
```

Passos (dentro de `transaction.atomic()`):

1. `draft = InvoiceDraftService.build_draft(parsed, target_bill=bill)` (reconciliação de `installment_id` + warnings, incl. divergência de prédio — o warning NÃO bloqueia; os bloqueios são os abaixo).
2. **Validações 400 (ValidationError PT, constantes nomeadas)**:
   - `matched_account` `None` **ou** `id` ≠ `bill.billing_account_id` (inclui bill sem conta) → `_ERR_ACCOUNT_MISMATCH = "A fatura não pertence à conta desta cobrança (inscrição/UC divergente)."`
   - `parsed.competence_month != bill.competence_month` → `_ERR_COMPETENCE_MISMATCH` (PT, com as duas competências `MM/AAAA`).
   - `bill.lifecycle_state != ACTIVE` (suspensa/adiada/cancelada) → `_ERR_BILL_NOT_ACTIVE = "Reative a conta antes de importar a fatura."` (400 PT).
   - Bill paga/parcial e mês fechado → já rejeitados por `update_with_lines` (delegação — não duplicar guards).
3. Montar `lines: list[BillLineInput]` a partir de `draft["line_items"]`: `Decimal(amount)`, `is_offset`, `category=None`, `installment` = objeto resolvido a partir do `installment_id` com o MESMO filtro de posse de `_resolve_owned_installment` (`crud_views.py:262-281`); `statement = cast(StatementInput, parsed.statement)` quando não-None; `header = {"due_date": parsed.due_date, "external_identifier": parsed.external_identifier}` (campos do draft que EXISTEM no `ParsedInvoice`; `issue_date` não existe no parser).
4. `BillService.update_with_lines(bill, lines, statement=statement, header=header, user=user)` — replace (preservando parcelas, item 2), upsert statement, header, e **limpeza de `amount_is_estimated` por delegação (S65)**.
5. Retornar `bill`.

### 4. Action `apply_invoice` (`crud_views.py`)

```python
@action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
def apply_invoice(self, request: Request, pk: str | None = None) -> Response:
    """Parseia o PDF em memória e aplica à bill alvo (grava via update_with_lines)."""
```

- Extrair de `parse_invoice` o helper privado `_read_parsed_invoice(request)` que devolve o `ParsedInvoice` ou levanta/retorna os MESMOS erros atuais (sem arquivo → 400 `_ERR_NO_FILE`; não-PDF → 400 `_ERR_NOT_PDF`; emissor desconhecido → 422 PT). `parse_invoice` e `apply_invoice` usam o helper; comportamento do `parse_invoice` idêntico (testes existentes verdes sem edição).
- `bill = self.get_object()` (404 p/ inexistente/deletada; `IsAdminUser` do viewset cobre 401/403).
- `try:` `InvoiceApplyService.apply(bill, parsed, user=cast(User, request.user))` `except ValidationError` → 400 `{"error": <msg PT>}`.
- Response **200** `self._serialized_bill(bill)` (bill com amounts; `amount_is_estimated=False`). Rota auto-exposta pelo router (`finances/urls.py` intacto).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy**: fronteira externa = o PDF, coberto por fixture real (`invoice_pdf_bytes` renderiza `.txt` sanitizado → PDF posicional). **NUNCA** mockar `detect_and_parse`, serviços, ORM, serializers. Banco real. Zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_invoice_draft_service.py` (estender)

- [ ] `test_matched_account_exposes_flat_building_id` — conta casada com prédio → `draft["matched_account"]["building_id"] == building.pk`; conta sem prédio → `None`. *"matched_account ganha building_id plano (int|null)."*
- [ ] `test_target_bill_building_mismatch_appends_warning` — `build_draft(parsed, target_bill=bill_de_outro_prédio)` → warning PT de divergência. *"Divergência de prédio contra a bill alvo vira warning (nunca bloqueio no draft)."*
- [ ] `test_target_bill_same_building_no_warning` — prédios iguais → sem warning novo. *"Sem divergência, sem ruído."*
- [ ] `test_no_target_bill_keeps_standalone_draft_unchanged` — `build_draft(parsed)` → nenhum warning de prédio; demais chaves/warnings idênticos ao contrato S60. *"Fluxo avulso intocado."*
- [ ] `test_reconciled_installment_amount_mismatch_appends_warning` — linha `PARCELA X/N` do PDF com valor ≠ da linha de parcela viva preservada na `target_bill` → warning PT informativo (`_WARN_INSTALLMENT_AMOUNT_MISMATCH`); linha viva intocada. *"Divergência de valor de parcela informa, nunca aplica silenciosamente (design §8)."*

#### `tests/unit/test_finances/test_bill_service.py` (estender)

- [ ] `test_update_with_lines_preserves_installment_lines` — bill com linha de parcela (FK) + semente; replace com 2 linhas novas sem parcela → parcela sobrevive (mesmo pk), semente soft-deletada, 2 novas vivas. *"Substitui apenas linhas sem FK installment."*
- [ ] `test_update_with_lines_dedups_incoming_installment_line` — payload reenvia a linha da parcela (`installment` já com linha viva) → nenhuma duplicata; total inalterado na parte da parcela. *"Dedup (bill, installment) — dinheiro nunca dobra."*
- [ ] `test_update_with_lines_creates_new_installment_line_when_absent` — linha entrante com `installment` sem linha viva → criada. *"Parcela nova entra pelo caminho normal."*

#### `tests/unit/test_finances/test_invoice_apply_service.py` (novo)

Constrói `ParsedInvoice` na mão (dataclass S59) + ORM real; bill alvo estimada gerada p/ a conta casada.

- [ ] `test_apply_replaces_lines_and_updates_header` — linhas do parser substituem a semente; `due_date`/`external_identifier` do parsed persistidos; `competence_month` intocada. *"Aplica linhas + header do draft à bill alvo."*
- [ ] `test_apply_upserts_statement` — `parsed.statement` de água → `WaterBillStatement` criado/atualizado no bill. *"Statement acompanha a aplicação."*
- [ ] `test_apply_clears_estimated_flag` — bill com `amount_is_estimated=True` → `False` após apply (via delegação S65). *"Aplicar a fatura confirma a bill."*
- [ ] `test_apply_preserves_embedded_installment_line` — bill com linha de parcela + parsed com linha `PARCELA X/N` reconciliada → uma única linha de parcela viva ao final. *"Linha de parcela embutida intocável + dedup."*
- [ ] `test_apply_account_mismatch_rejected` — bill de OUTRA conta (ou sem conta) → `ValidationError` `_ERR_ACCOUNT_MISMATCH`; nada muda no banco. *"Conta divergente/null → 400, aplicação nunca silenciosa."*
- [ ] `test_apply_competence_mismatch_rejected` — parsed 05/2026 × bill 06/2026 → `ValidationError` com as duas competências. *"Competência divergente → 400 PT."*
- [ ] `test_apply_non_active_bill_rejected` — bill SUSPENDED/DEFERRED/CANCELED → `ValidationError` `_ERR_BILL_NOT_ACTIVE`; nada muda no banco. *"apply_invoice só em bill ATIVA — 400 PT orientando reativar."*
- [ ] `test_apply_paid_bill_rejected` — bill com pagamento vivo → `ValidationError` (guard de `update_with_lines`); linhas intactas. *"Bill paga/parcial → 400 por delegação."*
- [ ] `test_apply_closed_month_rejected` — competência fechada → `ValidationError`; nada persiste. *"Mês fechado → 400 por delegação."*
- [ ] `test_apply_is_atomic` — forçar falha na etapa final (ex.: statement inválido) → linhas/header/flag TODOS inalterados. *"Tudo-ou-nada na mesma transação."*

#### `tests/integration/test_apply_invoice_api.py` (novo)

`pytestmark = [pytest.mark.integration, pytest.mark.django_db]`; `APPLY_URL = f"/api/finances/bills/{pk}/apply_invoice/"`; fixtures via `invoice_pdf_bytes` (espelhar `_pdf_upload` de `test_parse_invoice_api.py:40-43`, `DMAE_UC`).

- [ ] `test_apply_invoice_requires_authentication` — anônimo → 401. *"Anônimo → 401."*
- [ ] `test_apply_invoice_forbidden_for_non_admin` — não-staff → 403. *"Não-admin → 403 (IsAdminUser)."*
- [ ] `test_apply_invoice_happy_path_dmae` — conta WATER casada (`DMAE_UC`) + bill estimada na competência da fixture → 200; resposta com linhas reais, `amount_total` da fatura, `water_statement`, `amount_is_estimated is False`. *"Fluxo completo: PDF → linhas reais na bill alvo."*
- [ ] `test_apply_invoice_account_mismatch_returns_400` — bill de outra conta → 400 PT; bill inalterada. *"Divergência de conta → 400."*
- [ ] `test_apply_invoice_competence_mismatch_returns_400` — bill em outra competência → 400 PT. *"Divergência de competência → 400."*
- [ ] `test_apply_invoice_non_pdf_returns_400` — bytes inválidos → 400 `_ERR_NOT_PDF`. *"Não-PDF → 400 PT (helper compartilhado)."*
- [ ] `test_apply_invoice_unknown_issuer_returns_422` — fixture `desconhecida` → 422 PT. *"Emissor desconhecido → 422 (mesmo status do parse_invoice)."*
- [ ] `test_apply_invoice_paid_bill_returns_400` — bill paga → 400 PT. *"Guard UNPAID atravessa como 400."*
- [ ] `test_apply_invoice_preserves_installment_line_end_to_end` — fixture DMAE com `PARCELA X/N` + plano embutido ativo + linha materializada → 200 com UMA linha de parcela. *"Preservação da parcela end-to-end."*
- [ ] `test_parse_invoice_contract_untouched` — rodar `tests/integration/test_parse_invoice_api.py` inteiro verde SEM edição (regressão dirigida — não é um teste novo, é o critério). *"Fluxo avulso intocado."*

> Rodar (devem **falhar** — service/action/regra nova não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_invoice_apply_service.py tests/unit/test_finances/test_invoice_draft_service.py tests/unit/test_finances/test_bill_service.py tests/integration/test_apply_invoice_api.py -q
> ```

### 2. GREEN — implementar

1. `invoice_draft_service.py` — `target_bill` opcional + `building_id` + `_WARN_BUILDING_MISMATCH`.
2. `bill_service.py` — regra de preservação/dedup em `update_with_lines`.
3. `finances/services/invoice_apply_service.py` — `InvoiceApplyService.apply` (constantes `_ERR_ACCOUNT_MISMATCH`, `_ERR_COMPETENCE_MISMATCH`).
4. `crud_views.py` — helper `_read_parsed_invoice` + action `apply_invoice` (imports diretos da fonte).

### 3. REFACTOR — DRY / clareza
- `parse_invoice` e `apply_invoice` compartilham `_read_parsed_invoice` — nenhuma duplicação dos 400/422.
- O filtro de posse da parcela existe em UM lugar acessível aos dois consumidores (avaliar extrair a query de `_resolve_owned_installment` p/ o serviço — só se não acoplar view↔service na direção errada; caso contrário, espelhar com comentário cruzado).
- Confirmar **0 writes** no `InvoiceDraftService` (invariante S60 preservada — o apply escreve, o draft nunca).

### 4. VERIFY — gate (escopo desta sessão)

```bash
python -m pytest tests/unit/test_finances/test_invoice_apply_service.py tests/unit/test_finances/test_invoice_draft_service.py \
  tests/unit/test_finances/test_bill_service.py tests/integration/test_apply_invoice_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=0 -q
# ^ run ESCOPADO: --cov-fail-under=0 desliga o gate global (o addopts do projeto usa 90).
# O numero de 90% de `finances` e medido SEPARADAMENTE, na suite completa:
#   python -m pytest tests/unit/test_finances/ tests/integration/test_finances/ --cov=finances -q
python -m pytest tests/integration/test_parse_invoice_api.py tests/unit/test_finances/test_bill_statement_service.py \
  tests/integration/test_finances_bill_statement_api.py -q  # regressão dirigida (update_with_lines com linhas de installment)
ruff check finances/ tests/unit/test_finances/ tests/integration/test_apply_invoice_api.py
ruff format --check finances/ tests/unit/test_finances/ tests/integration/test_apply_invoice_api.py
mypy core/ finances/
pyright finances/services/invoice_apply_service.py finances/services/invoice_draft_service.py finances/services/bill_service.py finances/viewsets/crud_views.py
```

---

## Constraints

- **Lógica de negócio só nos serviços**; a action valida upload (400/422 PT via helper) e delega. Warning de prédio NUNCA bloqueia; os bloqueios (conta/competência/paga/mês fechado) são 400 PT.
- **Substituir apenas linhas sem FK `installment`** — regra no `update_with_lines`, valendo p/ todos os chamadores (refactor completo, sem parâmetro de compat).
- **`parse_invoice` intocado em contrato**: `test_parse_invoice_api.py` verde sem edição; draft muda só aditivamente (`building_id`).
- **Parse em memória, PDF descartado**; parser core (S59) intocado; **grava só via `update_with_lines`** (transação única).
- **Sem migração / model / mudança de serializer** (dual pattern do `BillingAccountSerializer` preservado — `building_id` plano injetado no dict do draft).
- **Sem suppressions** (`# noqa`, `# type: ignore`), sem `from __future__`/`TYPE_CHECKING`, sem re-exports. Shape de erro `{"error": <PT>}` (idioma atual das actions).
- **Mock só de fronteira externa** — e aqui nem isso: fixtures `.txt` → PDF real via `invoice_pdf_bytes`.

## Critérios de Aceite (binários)

- [ ] `build_draft(parsed, target_bill=None)`: `matched_account.building_id` (int|null) presente; warning PT de divergência quando `target_bill.building_id != account.building_id`; fluxo avulso sem `target_bill` inalterado.
- [ ] `update_with_lines` soft-deleta só linhas `installment__isnull=True`; dedup de entrante com `installment` vivo; entrante com `installment` novo criada; docstring atualizada.
- [ ] `InvoiceApplyService.apply(bill, parsed, user)`: 400 PT p/ conta divergente/null e competência divergente; linhas+statement+header (`due_date`/`external_identifier`) aplicados via `update_with_lines` em transação única; parcela embutida preservada; `amount_is_estimated` termina `False` (delegação S65); atômico.
- [ ] `POST /api/finances/bills/{id}/apply_invoice/` (MultiPartParser, `IsAdminUser`): 200 com a bill serializada (com amounts); 400 sem arquivo/não-PDF/regras de negócio; 422 emissor desconhecido; 401/403 auth; rota auto-exposta (`finances/urls.py` intacto).
- [ ] `parse_invoice` comportamento idêntico (`test_parse_invoice_api.py` 100% verde sem edição); helper `_read_parsed_invoice` compartilhado (zero duplicação dos erros de upload).
- [ ] Gate verde: pytest escopado 100% (com `--cov-fail-under=0`) + coverage `finances` ≥90% medido na SUITE COMPLETA de finances; `ruff check`/`format --check`, `mypy core/ finances/`, `pyright` — zero erros e zero warnings, sem suppressions.

## Handoff

1. Rodar e confirmar verde o gate do VERIFY + regressão dirigida.
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md`: Sessão 69 **concluída**; criados (`invoice_apply_service.py` + 2 arquivos de teste), modificados (`invoice_draft_service.py`, `bill_service.py`, `crud_views.py`, 2 testes estendidos); nota: "draft com `matched_account.building_id` + warning de divergência (`target_bill` opcional); `update_with_lines` preserva linhas de parcela (dedup); `apply_invoice` aplica o parse à bill alvo (400 conta/competência/paga/mês fechado, 422 emissor) e limpa a flag por delegação; `parse_invoice` intocado. **Header aplicado = due_date/external_identifier (ParsedInvoice não tem issue_date).**"
3. Rodar `/audit` (skill `audit`) contra os Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (na branch `feat/condo-bills-cockpit`):
   ```
   feat(finances): complete session 69 — apply_invoice endpoint (parse-and-apply to target bill, installment lines preserved) + building in parser draft

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
5. Próxima sessão: **70 — `consolidate_open_bills` + `consolidate_debt`** (só precisa de master/65).
