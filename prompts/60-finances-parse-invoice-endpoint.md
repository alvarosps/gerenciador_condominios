# Sessão 60 — Backend: endpoint `POST /api/finances/bills/parse_invoice` (multipart, rascunho em memória, reconciliação de parcela)

> **Feature**: Contas de serviço tipadas + parser de fatura + alerta de IPTU + modal responsivo (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: 56 → 57 → 58 → 59 → **60** → 61 → 62 → 63 → 64
> **Fase**: 4b (Parser — camada de **API**). A S59 entregou o **core do parser** (`finances/services/invoice_parsing/`: `ParsedInvoice`/`InvoiceParser`, `DmaeWaterParser`, `CeeeElectricityParser`, `registry.detect_and_parse`). Esta sessão expõe a **action HTTP** que recebe o PDF (multipart), valida que é PDF, chama `detect_and_parse`, **casa** com a `BillingAccount` por `account_type`+inscrição/UC, **reconcilia** a parcela embutida (`ParsedLine.installment_number` → `Installment` do plano embutido), checa **idempotência** (bill ativo já existe para conta+competência → sinaliza substituição) e devolve um **rascunho JSON** — **gravando NADA** (o draft é persistido depois via `create_with_lines`/`update_with_lines` da S58, em sessão posterior do front, S63). Cobre o **Apêndice B / Fase 4** (multipart sem boundary → 400; parcela sem plano → linha genérica + warning; idempotência → substituição; parse do mês N não altera meses < N).

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §5.2 "Fluxo", §5.5 "Casamento, idempotência, erros", §6 "Reconciliação — passado imutável", §15 segurança `parse_invoice`=`is_staff`, §11 cache `iptu_alerts`/`parse_invoice` não-cacheados, e Apêndice B "Fase 4")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`@action(detail=False, methods=["post"])` fino, parse/valida → 400 PT → delega ao serviço** | `finances/viewsets/crud_views.py:323-369` (`create_with_lines`: lê `request.data`, valida shape → 400 PT, monta `BillDraft`/`BillLineInput`, chama `BillService`, retorna `dict` serializado) + `:305-321` (`generate_month`: `_parse_year_month` → 400 PT) | **Estrutura-base** da action `parse_invoice`. Copiar o idioma de validação (400 PT) + delegação. A action **não** tem lógica de negócio — orquestra registry + casamento + reconciliação |
| **Embedded installment → linha vinculada (`BillLineItem.installment`); plano ausente → pula/defensivo** | `finances/services/bill_generation_service.py:154-187` (`_generate_embedded_lines`: itera `Installment` ativos, `installment.plan`, `account = plan.linked_billing_account` (S57 → `billing_account`), `installment.number`, dedup `(bill, installment)`) | **Espelho** da reconciliação: dado `ParsedLine.installment_number`, achar o `Installment` nº X do plano **embutido** da conta casada. **Não auto-criar** plano — só vincular se existir; senão linha genérica + warning |
| **`convert_deferred` / leitura `with_amounts` / `select_related` de plano** | `finances/services/installment_plan_service.py:91-142` (`with_amounts(today_sp())`, `select_for_update`, msgs PT como constantes nomeadas) | Forma de ler "atrasado" via `with_amounts(today_sp())` e o idioma de constantes PT nomeadas no serviço de matching |
| **`BillSerializer` (serialização do bill no draft) + `FinancialReadOnly`/`is_staff`** | `finances/viewsets/crud_views.py:216-218` (`_serialized_bill` → `BillSerializer(...).data`) + `core/permissions.py:107-121` (`FinancialReadOnly`: SAFE→authenticated; write→`is_staff`) | O draft serializa os campos do bill no shape do `BillSerializer` (round-trip com o modal, S62/S63). `parse_invoice` é **POST** → `FinancialReadOnly` já exige `is_staff` |
| **Registro de rota via router (rota custom auto-exposta, `core/urls.py` inalterado)** | `finances/urls.py:25-41` (`SimpleRouter` registra `BillViewSet` em `bills`) + nota S22 em `@prompts/SESSION_STATE.md` ("actions @action expostas automaticamente pelo router") | `parse_invoice` é `@action(detail=False)` no `BillViewSet` já registrado → rota `POST /api/finances/bills/parse_invoice/` **sem** editar `finances/urls.py` |
| **`MultiPartParser` numa action (`parser_classes`) + `request.FILES`** | DRF `rest_framework.parsers.MultiPartParser` (a action **sobrescreve** `parser_classes=[MultiPartParser]`; as demais usam o default JSON) — ver `core/viewsets/` para o idioma de upload se houver (`PaymentProof`/contract upload) | A action lê `request.FILES["file"]`; sem arquivo / não-PDF → 400 PT. **Parse em memória** (`BytesIO`), arquivo **descartado** (design §5.2/decisão #4 — sem `Bill.attachment`) |
| **Contrato S59 (consumido verbatim — NÃO recriar)** | `finances/services/invoice_parsing/{base,registry}.py` (S59): `ParsedInvoice` dataclass `{competence_month, due_date, external_identifier, behavior, account_type, line_items: list[ParsedLine{description, amount, is_offset, installment_number?}], statement: dict\|None, matched_account, warnings: list[str]}`; `registry.detect_and_parse(pdf_bytes: bytes) -> ParsedInvoice` (emissor desconhecido → levanta o erro PT definido pela S59) | A action **chama** `detect_and_parse(pdf_bytes)` e **enriquece** o `ParsedInvoice` (casamento de conta + reconciliação de parcela + idempotência) antes de serializar. **Não** reimplementar parsing/posicional aqui |
| **Integração API: client admin, factories, asserts de shape** | `tests/integration/test_finances_installments_employee_api.py:1-90` (`pytestmark` django_db+integration; `authenticated_api_client` admin; factories `make_*`; asserts `response.status_code`/`response.data`) + `tests/conftest.py:200-205` (`authenticated_api_client`=admin/`is_staff`) e `:209-212` (`regular_authenticated_api_client`=não-admin) | Forma dos testes de integração desta sessão (multipart com fixture sanitizada) e os clients de auth (403 não-admin / 401 anônimo) |
| **Fixtures SANITIZADAS (sem CPF real) — política da S59** | design §5.5 ("fixtures = texto extraído sanitizado, fora do caminho do GitGuardian") + as fixtures `.txt`/`.json`/`.pdf` criadas pela S59 em `tests/fixtures/finances/invoices/` (localização exata definida pela S59 — ver SESSION_STATE S59) | Os testes desta sessão **reusam** as fixtures sanitizadas da S59. **Não** criar PDF com CPF real; **não** versionar PDF de cliente. Se a S59 deixou fixtures `.txt` (texto extraído) em vez de `.pdf`, **ver §"Fronteira do parser nos testes"** |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; ORM/serviços reais) | Aqui = **fronteira externa = `pdfplumber.open`** (lê bytes do PDF). ORM, `registry.detect_and_parse`, os parsers, `BillSerializer`, casamento e reconciliação são **reais**. Banco real (`--reuse-db`) |

### O que a S56/S57/S58/S59 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S56**: `BillingAccountType`/`SupplyStatus` enums; campos `account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status` em `BillingAccount`; unique `unique_active_billing_account_identity` (`building`,`account_type`,`external_identifier`); `clean()`+serializer rejeitam `external_identifier` em branco p/ WATER/ELECTRICITY/IPTU; manager `BillingAccount.objects.recurring_for_generation()` (exclui IPTU).
- **S57**: refactor `InstallmentPlan.linked_billing_account → billing_account` (FK, `clean()`+`serializer.validate()` cross-model embedded↔conta de consumo; `convert_deferred` seta `plan.billing_account`); **todos** os consumidores backend+frontend atualizados (`grep linked_billing_account` = 0).
- **S58**: `WaterBillStatement`/`ElectricityBillStatement` (1:1 → `Bill`, readings-only, RLS); `BillService.create_with_lines` **estendido** (aceita `statement` opcional + `installment_id` por linha) + `update_with_lines` (substitui linhas + upsert statement em UNPAID+OPEN); soft-delete cascade da statement; `bill.schema.ts` aninha `water_statement`/`electricity_statement`.
- **S59**: `finances/services/invoice_parsing/` (`base.py` `ParsedInvoice`/`ParsedLine`/`InvoiceParser`; `dmae.py` `DmaeWaterParser`; `ceee.py` `CeeeElectricityParser`; `registry.py` `detect_and_parse`); `pdfplumber`+`pdfminer.six` nas 3 fontes (`requirements.txt`+`pyproject.toml`+overrides mypy); fixtures sanitizadas.

> **Esta sessão depende da S58 (persistência/serializer) + S59 (parser core).** DEPENDENCY ORDER: 60 depende de **58, 59**. **Se a S58/S59 não estiverem concluídas, PARE.** Não recriar parser, modelos, statements nem `create_with_lines`.

---

## Escopo

### Arquivos a criar
- `finances/services/invoice_draft_service.py` — `InvoiceDraftService` (lógica de **enriquecimento** do `ParsedInvoice`: casamento de `BillingAccount`, reconciliação de parcela embutida, idempotência) + serialização do draft em `dict`. **Toda a lógica de negócio da action vive aqui** (a action é fina — `.claude/rules/architecture.md`).
- `tests/integration/test_parse_invoice_api.py` — testes de integração da action (multipart com fixtures sanitizadas; casamento/idempotência/reconciliação/auth/erros).
- `tests/unit/test_finances/test_invoice_draft_service.py` — testes unit do serviço de enriquecimento (matching, reconciliação, idempotência, past-immutable) sobre objetos `ParsedInvoice` da S59 + ORM real, sem HTTP.

### Arquivos a modificar
- `finances/viewsets/crud_views.py` — adicionar `@action(detail=False, methods=["post"], parser_classes=[MultiPartParser])` `parse_invoice` ao `BillViewSet`: lê `request.FILES`, valida PDF (`pdfplumber.open` levanta → 400 PT), chama `registry.detect_and_parse(pdf_bytes)` (emissor desconhecido → 400/422 PT conforme a S59), delega ao `InvoiceDraftService.build_draft(...)`, retorna o draft JSON (200). Imports diretos da fonte (`from finances.services.invoice_parsing.registry import detect_and_parse`; `from finances.services.invoice_draft_service import InvoiceDraftService`). **Sem** editar `finances/urls.py` (rota auto-exposta pelo router).

### NÃO fazer (pertence a outras sessões)
- **Nenhuma gravação no banco** — `parse_invoice` é **read-only de efeito** (não cria `Bill`/`BillLineItem`/statement/`Payment`). O draft é persistido **depois**, pelo front (S63), chamando `create_with_lines`/`update_with_lines` (S58). Esta action **só monta e devolve** o rascunho.
- **`update_with_lines`/`create_with_lines`** — são da **S58** (já existem). Esta sessão **não** os altera nem os chama; apenas **referencia** o caminho de substituição no warning de idempotência.
- **Parsing posicional / detecção de emissor / leitura de campos do PDF** — é a **S59** (`registry.detect_and_parse` + parsers). Esta sessão **não** abre o PDF para extrair campos; só valida que é PDF e repassa os bytes ao registry.
- **`IptuAlertService`/`iptu_alerts`/banner/`send_finance_alerts`/`Notification` types** — é a **Sessão 61**.
- **`DialogBody`/modal responsivo/`useParseInvoice`/`IptuRiskBanner`/frontend** — é a **Sessão 62/63**.
- **Seed dos dados reais** (`seed_condo_utilities`) — é a **Sessão 64**.
- **Armazenar o PDF** (`Bill.attachment`, Supabase Storage) — **fora de escopo** (decisão #4 / §16 — parse em memória, arquivo descartado).
- **Nenhuma migração / mudança de model** — modelos são S56/S58.

---

## Especificação

> Service stateless em `finances/services/` (`@staticmethod`). A action é **fina** (parse/valida 400 PT → delega). "Hoje" **sempre** via `finances.services.timezone.today_sp()` (settings é UTC) — usado em `with_amounts(today_sp())` p/ idempotência/overdue. Mensagens ao usuário em **PT**; logs/identificadores em **EN**. Direção: serviço importa `finances.models`, `finances.services.invoice_parsing.base`, `finances.services.timezone` — **nunca** views/serializers. A action serializa o bill-draft via `BillSerializer` (round-trip com o modal).

### Fronteira do parser nos testes (CRÍTICO — resolve "como testar multipart sem PDF real")

O **único** mock permitido é a fronteira externa **`pdfplumber.open`** (lê o arquivo do disco/`BytesIO`). Há **dois** caminhos possíveis conforme o que a S59 deixou (ler o SESSION_STATE da S59):

1. **Se a S59 versionou PDFs sanitizados** (`tests/fixtures/finances/invoices/*.pdf` — PDFs sintéticos, gerados, sem CPF real): os testes de integração **postam o `.pdf` real** (multipart) e **nada é mockado** — `pdfplumber.open` lê o PDF sintético, `detect_and_parse` parseia de verdade. Caminho preferido (exercita o stack completo).
2. **Se a S59 deixou só texto extraído sanitizado** (`*.txt`/`*.json` — porque gerar PDF posicional fiel é inviável): então a fronteira `pdfplumber.open` é mockada para **devolver um objeto-página cujo `extract_words()`/`crop()` produz o texto sanitizado da fixture** (mock só da fronteira de I/O do PDF; o parser roda real). Documentar a decisão no topo do teste citando a política de mocks. O `parse_invoice` em si **valida** que `pdfplumber.open(BytesIO(bytes))` não levanta → para o teste de "não-PDF → 400" basta postar bytes não-PDF (ex.: `b"isto nao e um pdf"`) e asserir 400 PT — **esse** caminho nunca mocka.

> **Decisão pinada:** seguir o que a S59 entregou (não recriar fixtures). O teste "multipart sem boundary / não-PDF → 400" usa **bytes inválidos reais** (sem mock). Os testes de casamento/reconciliação/idempotência usam as fixtures da S59 pelo caminho que a S59 escolheu (1 ou 2). **Não** introduzir uma terceira convenção de fixture.

### `InvoiceDraftService` — enriquecimento do `ParsedInvoice` (toda a lógica de negócio)

```python
# finances/services/invoice_draft_service.py
from finances.services.invoice_parsing.base import ParsedInvoice

class InvoiceDraftService:
    @staticmethod
    def build_draft(parsed: ParsedInvoice) -> dict[str, object]:
        """Enriquece um ParsedInvoice (S59) com casamento de conta + reconciliação de
        parcela + idempotência, e devolve o RASCUNHO serializado (grava NADA)."""
```

`build_draft` retorna um `dict` com **exatamente** estas chaves (consumido pelo modal, S63):

- `bill`: `dict` no shape do `BillSerializer` (campos do cabeçalho do `ParsedInvoice`: `competence_month` ISO `YYYY-MM-01`, `due_date` ISO, `external_identifier`, `behavior`, `account_type`, `description`, e — quando casou — `building_id`/`category_id` herdados da conta casada). **`description`** é populado por `build_draft`: o **nome da conta casada** (`matched_account.name`) quando há match; senão `f"{tipo} {MM/AAAA}"` (ex.: `"Água 06/2026"`). **Não** instanciar/salvar `Bill`; montar o `dict` (usar `BillSerializer` para serializar uma instância **não salva**, ou montar o dict diretamente — escolher a forma que round-trip com o modal e travar por teste).
- `line_items`: `list[dict]` — uma por `ParsedLine`: `{description, amount (str Decimal), is_offset, category_id (int|None), installment_id (int|None)}`. `installment_id` é **resolvido por esta sessão** na **reconciliação** (abaixo): quando o `ParsedLine.installment_number` interno casa um `Installment` do plano embutido → o `pk`; senão `None` (+ warning). **`installment_number` é INTERNO ao `ParsedLine` (S59) e NÃO entra no draft serializado** — o draft expõe apenas `installment_id`. `category_id` é `None` quando a linha não tem categoria resolvida.
- `statement`: `dict | None` — o `parsed.statement` repassado (S59 já tipou por `account_type`: `WaterBillStatement`/`ElectricityBillStatement` fields).
- `matched_account`: `dict | None` — a `BillingAccount` casada serializada (id + identidade) ou `None`.
- `warnings`: `list[str]` — os `parsed.warnings` da S59 **acrescidos** dos warnings desta sessão (sem-match, idempotência/substituição, parcela-sem-plano). Mensagens PT.

#### Casamento de conta (design §5.5)
- `account = BillingAccount.objects.filter(account_type=parsed.account_type, external_identifier=parsed.external_identifier).first()` (conta **ativa** — `objects` já exclui soft-deleted). Casou → `matched_account` serializado e o bill herda `building_id`/`category_id` da conta. **Sem match** → `matched_account=None` + warning PT (ex.: `"Nenhuma conta de {tipo} encontrada para a inscrição/UC {ident}. Selecione ou crie a conta."`). **Nunca** criar conta automaticamente (admin decide no modal).

#### Reconciliação de parcela embutida (design §5.3/§6 — passado imutável)
- Para cada `ParsedLine` com `installment_number` **e** conta casada: achar o `Installment` nº X do **plano embutido ativo** dessa conta — `Installment.objects.filter(plan__billing_account=account, plan__embedded=True, plan__lifecycle_state=ACTIVE, plan__is_deleted=False, number=installment_number).first()` (espelha `bill_generation_service.py:154-187`).
  - Achou → `line["installment_id"] = installment.pk` (o vínculo é gravado **depois**, por `create_with_lines`/S58 — aqui só anota no draft).
  - **Não achou plano/parcela** → **linha genérica** (mantém a linha de `PARCELAMENTO`/`Parcela X/N` **sem** `installment_id`) + warning PT (ex.: `"Parcela {X}/{N} sem plano de parcelamento cadastrado — crie o plano em Planos de Parcelamento."`). **Nunca** auto-criar `InstallmentPlan`/`Installment`.
- **Passado imutável (invariante §6 + Apêndice B):** `build_draft` **não** lê, escreve ou altera `Bill`/`BillLineItem`/`Installment` de **nenhum** mês — só **monta o draft em memória**. A reconciliação apenas **lê** o `Installment` para descobrir o `pk` a anotar. Não há `.save()` em parte alguma do serviço. (O re-baseline de N+1 do design §6 é do schedule/PATCH existente — **não** desta sessão.)

#### Idempotência (design §5.5)
- Quando há conta casada **e** `parsed.competence_month` definido: se já existe `Bill` **ativo** para `(billing_account=account, competence_month=parsed.competence_month)` (`Bill.objects.filter(...).exists()`) → **warning PT de substituição** (ex.: `"Já existe uma conta para {nome} em {MM/AAAA}. Salvar substituirá as linhas dela (use Atualizar)."`) e incluir no draft o **`existing_bill_id`** (a pk do bill ativo) para o modal direcionar ao caminho `update_with_lines` (S58). **Não** levantar erro de constraint; **não** gravar nada. Sem bill existente → sem warning, `existing_bill_id` ausente/`None`.

### `parse_invoice` (action no `BillViewSet`)

```python
@action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
def parse_invoice(self, request: Request) -> Response:
    """Recebe um PDF de fatura (multipart), parseia em MEMÓRIA e devolve um RASCUNHO
    (grava NADA). is_staff (FinancialReadOnly write gate). O draft é salvo depois via
    create_with_lines/update_with_lines (S58)."""
```

Fluxo (espelha `crud_views.py:323-369`, mas multipart):
1. `uploaded = request.FILES.get("file")`; ausente → 400 PT (`"Envie o arquivo da fatura no campo 'file'."`).
2. `pdf_bytes = uploaded.read()`; validar PDF: `with pdfplumber.open(io.BytesIO(pdf_bytes))` num `try/except` (qualquer exceção de abertura → 400 PT `"O arquivo enviado não é um PDF válido."`). **Boundary externa = `pdfplumber.open`** (única chamada de I/O de PDF na action; o parsing fica no registry/S59). *(KISS: abrir uma vez para validar e descartar; o `detect_and_parse` reabre dos bytes — aceitável, é em memória.)*
3. `parsed = detect_and_parse(pdf_bytes)` num `try/except` do erro PT que a S59 levanta p/ emissor desconhecido → mapear para 400 (ou 422 conforme a S59 definiu — **usar o status que a S59 documentou**; o design §5.1 diz 422) PT.
4. `draft = InvoiceDraftService.build_draft(parsed)`.
5. `return Response(draft, status=200)`.

**`parser_classes=[MultiPartParser]`** sobrescreve o default JSON **só nesta action** (as outras actions JSON do `BillViewSet` ficam intactas). **`FinancialReadOnly`** (herdado do viewset) já exige `is_staff` em POST → não-admin 403, anônimo 401 (sem código extra). **Uncached** (design §11 — `parse_invoice` depende do upload, não cacheável).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS** a fronteira externa **`pdfplumber.open`** (e somente no caminho 2 da §"Fronteira do parser nos testes"). **NUNCA** mockar `detect_and_parse`, os parsers, `InvoiceDraftService`, `BillSerializer`, ORM, managers ou signals. Banco real (`--reuse-db`). Fixtures sanitizadas da S59 (sem CPF). `filterwarnings=error`: zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_invoice_draft_service.py`
Constrói `ParsedInvoice`/`ParsedLine` (dataclasses da S59) **na mão** (sem PDF) + ORM real; exercita `InvoiceDraftService.build_draft`.

- [ ] `test_build_draft_matches_account_by_type_and_identifier` — `make_billing_account(account_type=WATER, external_identifier="117.111.0049.0508.00")`; `ParsedInvoice(account_type="water", external_identifier="117...0508.00", ...)` → `draft["matched_account"]["id"] == account.id`; `draft["bill"]["building_id"]`/`category_id` herdados da conta. *"Casa a conta por account_type + inscrição/UC e herda prédio/categoria."*
- [ ] `test_build_draft_no_match_emits_warning_and_null_account` — sem conta cadastrada para a inscrição → `draft["matched_account"] is None` e um warning PT mencionando a inscrição; nenhuma conta criada (`BillingAccount.objects.count()` inalterado). *"Sem match: warning PT + matched_account None + nunca cria conta."*
- [ ] `test_build_draft_reconciles_embedded_installment` — conta WATER casada com `InstallmentPlan(embedded=True, billing_account=account, lifecycle_state=ACTIVE)` + `Installment(number=3)`; `ParsedLine(description="Parcela 3/59", amount=..., installment_number=3)` → a line do draft tem `installment_id == installment.pk`. *"Reconcilia ParsedLine.installment_number ao Installment nº X do plano embutido."*
- [ ] `test_build_draft_installment_without_plan_keeps_generic_line_and_warns` — `ParsedLine(installment_number=3)` mas **sem** plano embutido → a line permanece (genérica, sem `installment_id`) e há warning PT sobre "crie o plano em Planos de Parcelamento"; **nenhum** `InstallmentPlan`/`Installment` criado. *"Parcela sem plano: linha genérica + warning, nunca auto-cria plano (Apêndice B Fase 4)."*
- [ ] `test_build_draft_idempotency_flags_replacement_for_existing_bill` — conta casada + `make_bill(billing_account=account, competence_month=date(2026,5,1), lifecycle_state=ACTIVE)`; `ParsedInvoice(competence_month=date(2026,5,1))` → warning PT de substituição + `draft["existing_bill_id"] == bill.pk`. *"Idempotência: bill ativo já existe → warning de substituição + existing_bill_id (caminho update_with_lines)."*
- [ ] `test_build_draft_no_existing_bill_no_replacement_warning` — sem bill para (conta, competência) → sem warning de substituição, `existing_bill_id` ausente/None. *"Sem bill existente: sem warning de substituição."*
- [ ] `test_build_draft_writes_nothing_to_db` — contar `Bill`/`BillLineItem`/`Installment`/`Payment` antes e depois de `build_draft` (com conta casada + plano + bill existente) → **iguais**. *"Past-immutable: build_draft grava NADA (parse mês N não altera meses < N)."*
- [ ] `test_build_draft_preserves_parser_warnings_and_appends` — `ParsedInvoice(warnings=["resíduo de soma ≠ 0"])` sem match → `draft["warnings"]` contém o warning do parser **e** o de sem-match. *"Warnings do parser (S59) preservados e acrescidos dos desta sessão."*
- [ ] `test_build_draft_serializes_statement_passthrough` — `ParsedInvoice(statement={"consumo_m3": 158, ...})` → `draft["statement"] == {...}` (repasse). `statement=None` → `draft["statement"] is None`. *"statement repassado verbatim (None ou dict tipado)."*
- [ ] `test_build_draft_line_amounts_are_string_decimal_and_offset_preserved` — `ParsedLine(amount=Decimal("530.24"), is_offset=False)` + `ParsedLine(amount=Decimal("9.61"), is_offset=True)` → `line_items[0]["amount"] == "530.24"`, `is_offset is False`; offset line `is_offset is True`. *"Money serializado como string Decimal; is_offset preservado."*
- [ ] `test_build_draft_description_from_matched_account_name` — conta WATER casada `name="Conta de Água - 850"` → `draft["bill"]["description"] == "Conta de Água - 850"`. *"description = nome da conta casada quando há match."*
- [ ] `test_build_draft_description_fallback_when_no_match` — `ParsedInvoice(account_type="water", competence_month=date(2026,6,1))` sem conta cadastrada → `draft["bill"]["description"]` cai no fallback `"{tipo} {MM/AAAA}"` (ex.: contém `"06/2026"`). *"description = '{tipo} {MM/AAAA}' quando sem match."*
- [ ] `test_build_draft_line_exposes_installment_id_not_installment_number` — `ParsedLine(installment_number=3)` reconciliado → a line do draft tem chave `installment_id` e **não** tem `installment_number` (interno ao parser, fora do draft serializado). *"Draft serializado expõe installment_id, nunca installment_number."*

#### `tests/integration/test_parse_invoice_api.py`
`pytestmark = [pytest.mark.django_db, pytest.mark.integration]`. URL `PARSE_URL = "/api/finances/bills/parse_invoice/"`. Posta multipart (`format="multipart"`, campo `file`).

- [ ] `test_parse_invoice_requires_authentication` — `api_client` (anônimo) POST → 401. *"Anônimo → 401."*
- [ ] `test_parse_invoice_forbidden_for_non_admin` — `regular_authenticated_api_client` (não-`is_staff`) POST com um PDF válido → 403 (FinancialReadOnly write gate). *"Não-admin → 403 (§15)."*
- [ ] `test_parse_invoice_missing_file_returns_400` — `authenticated_api_client` POST sem campo `file` → 400 PT (`error` menciona 'file'). *"Sem arquivo → 400 PT."*
- [ ] `test_parse_invoice_non_pdf_returns_400` — POST `file` = bytes não-PDF (`b"isto nao e um pdf"`, sem mock) → 400 PT `"...não é um PDF válido."`. **Cobre Apêndice B "multipart sem boundary → 400"** (bytes inválidos = mesma falha de `pdfplumber.open`). *"Não-PDF → 400 PT."*
- [ ] `test_parse_invoice_unknown_issuer_returns_4xx` — PDF válido cujo conteúdo **não** casa nenhum emissor (CNPJ ausente) → 400/422 PT (status que a S59 documentou). *"Emissor desconhecido → 4xx PT (design §5.1)."*
- [ ] `test_parse_invoice_dmae_water_returns_draft` — posta a fixture **DMAE água** sanitizada (S59); conta WATER casada cadastrada (`make_billing_account`) → 200; `response.data["matched_account"]["id"] == account.id`; `response.data["bill"]["account_type"] == "water"`; `competence_month` ISO dia 1; `statement` com `consumo_m3`; `line_items` não vazio. **Cobre Apêndice B "cada campo de statement por variante".** *"DMAE: draft 200 com bill/line_items/statement/matched_account."*
- [ ] `test_parse_invoice_ceee_electricity_returns_draft` — fixture **CEEE luz** sanitizada → 200; `account_type == "electricity"`; `statement` com `consumo_kwh`; (se a fixture CEEE escolhida tem solar) `energia_injetada_kwh` presente. *"CEEE: draft 200 com statement de luz."*
- [ ] `test_parse_invoice_no_matching_account_returns_draft_with_warning` — fixture DMAE válida **sem** conta cadastrada → 200; `matched_account is None`; `warnings` contém a mensagem PT de sem-match; **grava nada** (`Bill.objects.count() == 0`). *"Sem match: 200 + warning + grava nada."*
- [ ] `test_parse_invoice_existing_bill_flags_replacement` — fixture DMAE + conta casada + `make_bill(billing_account=account, competence_month=<a competência da fixture>, lifecycle_state=ACTIVE)` → 200; warning de substituição + `existing_bill_id == bill.pk`. *"Idempotência via API: warning + existing_bill_id (Apêndice B)."*
- [ ] `test_parse_invoice_writes_nothing` — fixture DMAE + conta casada; contar `Bill`/`BillLineItem` antes/depois do POST → iguais; resposta 200. **Cobre Apêndice B "parse mês N não altera meses < N"** (a action é puramente leitora). *"parse_invoice grava NADA."*
- [ ] `test_parse_invoice_embedded_installment_reconciled_via_api` — fixture DMAE com linha `Parcela X/N` + conta casada com plano embutido ativo + `Installment` nº X → a line do draft tem `installment_id == installment.pk`. *"Reconciliação de parcela end-to-end via API."*

> Rodar (devem **falhar** — service/action ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py -q
> ```

### 2. GREEN — implementar

1. `finances/services/invoice_draft_service.py` — `InvoiceDraftService.build_draft(parsed)` (casamento + reconciliação + idempotência + serialização do draft). Imports diretos (`finances.models`, `finances.services.invoice_parsing.base`, `finances.services.timezone.today_sp`). Mensagens PT como **constantes nomeadas** (`_WARN_NO_MATCH`, `_WARN_REPLACEMENT`, `_WARN_INSTALLMENT_NO_PLAN` — com placeholders `.format(...)`).
2. `finances/viewsets/crud_views.py` — `import io`, `import pdfplumber`, `from rest_framework.parsers import MultiPartParser`, `from finances.services.invoice_parsing.registry import detect_and_parse`, `from finances.services.invoice_draft_service import InvoiceDraftService`; adicionar a action `parse_invoice` ao `BillViewSet` conforme a Especificação. Constantes PT nomeadas (`_ERR_NO_FILE`, `_ERR_NOT_PDF`).

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Casamento, reconciliação e idempotência são **funções privadas nomeadas** no serviço (`_match_account`, `_reconcile_line`, `_existing_active_bill`) — intenção clara, SRP (cada uma uma responsabilidade).
- A reconciliação reusa o **mesmo filtro** de `Installment` embutido que `bill_generation_service._active_installments_for_month` aplica (`plan__embedded=True`, `plan__lifecycle_state=ACTIVE`, `plan__is_deleted=False`) — confirmar consistência (DRY conceitual; não extrair se acoplaria a geração).
- A action permanece **fina**: zero lógica de negócio (só validação 400 PT + delegação). Toda regra no serviço.
- Mensagens PT centralizadas como constantes (sem magic strings espalhadas).
- Confirmar **zero** `.save()`/`create()` no `InvoiceDraftService` (past-immutable — travado por `test_build_draft_writes_nothing_to_db`).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/ tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py
ruff format --check finances/ tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py
mypy core/ finances/
pyright finances/services/invoice_draft_service.py finances/viewsets/crud_views.py
```

> **Regressão obrigatória** (não quebrar as actions JSON do `BillViewSet` nem o parser core):
> ```bash
> python -m pytest tests/integration/test_finances_bills_api.py tests/unit/test_finances -k "parse or invoice or bill_service or create_with_lines" -q
> ```
> *(Ajustar os nomes dos arquivos de teste do BillViewSet/parser conforme existirem — S38/S58/S59.)*

---

## Constraints

- **Direção de dependência**: `finances → core` (unidirecional). O serviço/action importam `finances.models`, `finances.services.invoice_parsing.*`, `finances.services.timezone`, `BillSerializer` — **nunca** o inverso. A action **não** reimplementa parsing.
- **Lógica de negócio só no serviço** (`.claude/rules/architecture.md`): casamento/reconciliação/idempotência no `InvoiceDraftService`; a action só valida (400 PT) e delega. **Nada** de regra na view.
- **GRAVA NADA**: `parse_invoice`/`build_draft` são puramente leitores — **zero** `.save()`/`.create()`/`.delete()`. Past-immutable (design §6/Apêndice B) — travado por teste de contagem.
- **Não auto-criar** `BillingAccount`/`InstallmentPlan`/`Installment` — sem match/sem plano → warning PT, o admin decide no modal.
- **Sem armazenar o PDF** (decisão #4): parse em memória (`BytesIO`), arquivo descartado; `Bill.attachment` intocado.
- **TZ SP única** (design §11): "hoje" só via `today_sp()` (em `with_amounts(today_sp())`). Proibido `timezone.now().date()`.
- **Boundary externa = `pdfplumber.open`** (a única chamada de I/O de PDF na action); o teste de "não-PDF → 400" usa bytes inválidos reais (sem mock). Mock de `pdfplumber.open` **só** no caminho-2 de fixture (texto extraído), conforme a S59.
- **`parser_classes=[MultiPartParser]`** só na action `parse_invoice`; as demais actions do `BillViewSet` (JSON) **intactas**.
- **`is_staff` write gate** (§15): `FinancialReadOnly` já cobre (POST → admin). Sem checagem inline de permissão (`.claude/rules/security.md`).
- **Money como string Decimal** no draft (linhas), competência/datas ISO (`YYYY-MM-DD`, competência dia 1).
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código. Tipos completos (mypy strict + pyright strict). `pdfplumber` já tem override `ignore_missing_imports` (S59) — **não** adicionar `# type: ignore`.
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from decimal import Decimal`, etc.).
- **Sem re-exports / barrels / shims**: cada módulo exporta só o que define; imports diretos da fonte.
- **Sem migração / mudança de model / serializer novo / frontend** (S58 statements, S61 alerta, S62/S63 front, S64 seed). **Sem** `update_with_lines`/`create_with_lines` (S58 — só referenciados no warning).
- Mensagens ao usuário em **Português**; logs/identificadores em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `BillViewSet.parse_invoice` (`@action(detail=False, methods=["post"], parser_classes=[MultiPartParser])`): lê `request.FILES["file"]` (ausente → 400 PT); valida PDF via `pdfplumber.open(BytesIO)` (inválido → 400 PT); chama `detect_and_parse` (emissor desconhecido → 4xx PT conforme S59); delega ao `InvoiceDraftService.build_draft`; retorna o draft (200). `is_staff` (FinancialReadOnly): não-admin 403, anônimo 401. Rota auto-exposta (`finances/urls.py` **intacto**).
- [ ] `InvoiceDraftService.build_draft(parsed) -> dict` devolve `{bill, line_items, statement, matched_account, existing_bill_id, warnings}`: casa `BillingAccount` por `account_type`+`external_identifier` (sem match → warning PT + `matched_account=None`, sem criar conta); `bill.description` = `matched_account.name` quando há match, senão `f"{tipo} {MM/AAAA}"`; reconcilia `ParsedLine.installment_number` (interno) ao `Installment` nº X do plano **embutido ativo** da conta, anotando `installment_id` (int|None) na **linha serializada** (que expõe `installment_id`, **nunca** `installment_number`); cada linha carrega `category_id` (int|None); sem plano → linha genérica (`installment_id=None`) + warning PT (nunca auto-cria plano); idempotência (bill ativo p/ conta+competência → warning de substituição + `existing_bill_id` a pk, senão `None`); **grava NADA** (travado por contagem).
- [ ] `parse_invoice`/`build_draft` não criam/alteram/apagam **nenhum** registro (past-immutable §6); arquivo do PDF **não** armazenado (parse em memória).
- [ ] Money das linhas serializado como **string Decimal**; competência/datas ISO (competência dia 1); `is_offset` preservado; warnings do parser (S59) preservados e acrescidos dos desta sessão.
- [ ] Testes cobrem (Apêndice B Fase 4): multipart sem arquivo/não-PDF → 400; emissor desconhecido → 4xx; DMAE e CEEE → draft 200 com statement por variante; sem match → warning + grava nada; idempotência → warning + `existing_bill_id`; parcela sem plano → linha genérica + warning; reconciliação de parcela end-to-end; parse não altera meses < N (grava nada); auth (401/403).
- [ ] `python -m pytest tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py` passa 100%, **coverage `finances` ≥90%** nos módulos tocados; regressão das actions JSON do `BillViewSet` + parser core verde.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/services/invoice_draft_service.py finances/viewsets/crud_views.py` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhuma migração/modelo/serializer novo/frontend; `finances/urls.py` intacto; `create_with_lines`/`update_with_lines` (S58) **não** alterados; parser core (S59) **não** alterado; nada gravado no banco.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/integration/test_finances_bills_api.py tests/unit/test_finances -k "parse or invoice or bill_service or create_with_lines" -q  # regressão
   ruff check finances/ tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py
   ruff format --check finances/ tests/unit/test_finances/test_invoice_draft_service.py tests/integration/test_parse_invoice_api.py
   mypy core/ finances/
   pyright finances/services/invoice_draft_service.py finances/viewsets/crud_views.py
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`):
   - Linha da Sessão 60 (status **concluída**) na tabela da feature "Contas de serviço tipadas + parser".
   - **Arquivos Criados**: `finances/services/invoice_draft_service.py`, `tests/unit/test_finances/test_invoice_draft_service.py`, `tests/integration/test_parse_invoice_api.py`.
   - **Arquivos Modificados**: `finances/viewsets/crud_views.py` (action `parse_invoice` no `BillViewSet`).
   - **Nota**: "Fase 4b — `POST /api/finances/bills/parse_invoice/` (multipart, `is_staff`): valida PDF (`pdfplumber.open`→400 PT), `detect_and_parse` (S59), `InvoiceDraftService.build_draft` casa conta por `account_type`+UC/inscrição, reconcilia parcela embutida (`installment_number`→`Installment`, sem plano→linha+warning), idempotência (bill ativo→warning de substituição+`existing_bill_id`→`update_with_lines` S58), devolve draft `{bill,line_items,statement,matched_account,warnings,existing_bill_id?}` — **grava NADA** (past-immutable §6). Sem armazenar PDF (parse em memória). **Alerta IPTU=S61; modal/`useParseInvoice`/banner=S62/S63; seed=S64.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (na branch da feature):
   ```
   feat(finances): complete session 60 — parse_invoice endpoint (multipart draft, account match + installment reconciliation + idempotency)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **61 — Alerta de IPTU** (`IptuAlertService.evaluate(today_sp())`, `GET /api/finances/finance-dashboard/iptu_alerts` uncached, `send_finance_alerts` agregado SP-aware, `Notification` types/constantes + migração core). Independente desta (depende de S56/S57).

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`POST /api/finances/bills/parse_invoice/`** (multipart, campo `file`, `is_staff`): retorna 200 com o draft `{bill, line_items, statement, matched_account, existing_bill_id, warnings}` (objeto plano — **não** `{results,count}`) — **grava NADA**. Erros: sem arquivo/não-PDF → 400 PT; emissor desconhecido → 4xx PT (status da S59); não-admin 403; anônimo 401.
- **`InvoiceDraftService.build_draft(parsed: ParsedInvoice) -> dict[str, object]`** — `bill` no shape do `BillSerializer`: `competence_month`/`due_date`/`external_identifier`/`behavior`/`account_type` + `description` (`matched_account.name` se casou, senão `f"{tipo} {MM/AAAA}"`) + `building_id`/`category_id` (herdados da conta casada, `None` sem match); `line_items: list[dict]` (`{description, amount: str, is_offset, category_id: int|None, installment_id: int|None}` — **`installment_id` resolvido aqui; `installment_number` NÃO entra no draft, fica interno ao `ParsedLine` S59**); `statement: dict|None` (repasse S59); `matched_account: dict|None`; `existing_bill_id: int|None` (idempotência → caminho `update_with_lines` S58); `warnings: list[str]` (parser S59 + sem-match/substituição/parcela-sem-plano).
- **Draft do front (S62/S63)**: o modal pré-preenche com o draft; salvar **roteia por `existing_bill_id`** (NÃO por `matched_account`): **truthy** ⇒ `update_with_lines` (S58, substitui linhas do bill existente, `bill_id=existing_bill_id`); **null/ausente** ⇒ `create_with_lines` (S58, cria novo). `line["installment_id"]` setado ⇒ `BillLineItem.installment` vinculado por `create_with_lines`/`update_with_lines`. `useParseInvoice` (S63) envia `FormData` com `headers {'Content-Type': undefined}`; o interceptor do `client.ts` **não** desempacota `{results,count}` (resposta plana).
- **Reconciliação (S6)**: `parse_invoice` **só** anota `installment_id` no draft; o vínculo é gravado por `create_with_lines`/`update_with_lines` (S58). `parse_invoice` é **imutável quanto ao passado** (não toca bills/linhas/parcelas de mês nenhum).
