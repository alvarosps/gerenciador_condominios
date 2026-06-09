# Sessão 59 — Backend parser de fatura PDF (núcleo): `invoice_parsing/` (DMAE água + CEEE luz) + `detect_and_parse` posicional

> **Feature**: Contas de serviço tipadas (água/luz/IPTU) + parser de fatura PDF + alerta de IPTU + modal responsivo (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: 56 → 57 → 58 → **59** → 60 → 61 → 62 → 63 → 64 (esta abre a **Fase 4 — Parser**, camada de **parsing puro**, sem endpoint)
> Esta sessão cria o pacote `finances/services/invoice_parsing/` — **só o parsing em memória**: dataclasses tipadas (`ParsedInvoice`/`ParsedLine`) + protocolo `InvoiceParser`, `DmaeWaterParser` (água) e `CeeeElectricityParser` (luz, 3 layouts) por **extração posicional** (`pdfplumber.extract_words`/`crop`, NÃO regex sobre `extract_text` plano), e `detect_and_parse(pdf_bytes)` que detecta o emissor por CNPJ. Adiciona `pdfplumber`+`pdfminer.six` (deps três-lugares + mypy override). Fixtures **sanitizadas** (texto extraído, sem CPF/código de barras real). **Sem endpoint `parse_invoice` (S60); sem `IptuAlertService`/banner (S61); sem frontend (S62/S63); sem persistência (`create_with_lines`/`update_with_lines` é S58, já feito).**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §5 inteira — "Parser de fatura"; §5.1 estrutura/SRP, §5.3 extração DMAE, §5.4 extração CEEE, §5.5 casamento/idempotência/erros/fixtures; §6 reconciliação de parcela; §10.3 exclusão IPTU; Apêndice A inventário real; Apêndice B "Fase 4")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Parser de fatura existente (dataclasses + map de rótulos + parse de competência/parcela `X/N`)** | `@scripts/parse_itau_fatura.py` (`@dataclass FaturaEntry`/`FaturaData` :25-46; `CATEGORY_MAP` :49+; parse de `NN/TT` e datas) | **Idioma de referência** das dataclasses + do mapeamento de rótulo→categoria + do reconhecimento de `PARCELA X/N`. Reusar o estilo (dataclass tipada, dict de mapeamento, helper de parse de valor BR), **NÃO** o `from __future__` nem `argparse`/CLI (este é serviço, não script) |
| **Service-layer puro do `finances` (módulo, docstring EN, assinaturas anotadas, msgs PT)** | `@prompts/37-finances-bill-services-cache.md` (estrutura de serviços stateless; idioma de retorno/log/PT-EN) + `finances/services/bill_generation_service.py` (`recurring_for_generation()`, `clamp_due_day`, `RECURRING`) | Forma do serviço `finances` (módulo em `finances/services/`, sem estado, tipos completos). O parser **não** toca ORM/banco (é parsing puro); só produz dataclasses |
| **Boundary de quantização de dinheiro (fonte única)** | `@finances/money.py` (`quantize_money(value)`/`money_str`, `CENTS`, `ROUND_HALF_UP` :13-26) | Valores parseados são `Decimal`; quantizar **só** ao montar o `ParsedLine.amount`/totais via `quantize_money` (mesma fronteira do resto do `finances` — DRY). Importar daqui, não recriar |
| **Enums de tipo de conta / supply (S56 — já existem)** | `finances/models.py` (`BillingAccountType` `WATER`/`ELECTRICITY`/`IPTU`/`INTERNET`/`GENERIC`; `SupplyStatus` `ACTIVE`/`CUT`) | `ParsedInvoice.account_type` usa `BillingAccountType`; o status água/esgoto/energia do statement usa `SupplyStatus`. Importar de `finances.models` (não redefinir) |
| **`BillBehavior` (S36 — valores do `behavior`)** | `finances/models.py:49-52` (`ONE_TIME`/`RECURRING`/`INSTALLMENT`) | `ParsedInvoice.behavior` = `BillBehavior.RECURRING` para consumo (água/luz parseadas; design §8 "fatura de consumo parseada = behavior=recurring") |
| **Statements 1:1 (S58 — já existem)** | `finances/models.py` (`WaterBillStatement`: `consumo_m3`/`leitura_anterior`/`leitura_atual`/`leitura_dias`/`data_leitura`/`agua_status`/`esgoto_status`; `ElectricityBillStatement`: `consumo_kwh`/`energia_injetada_kwh`/`leitura_anterior`/`leitura_atual`/`leitura_dias`/`classe`/`bandeira`) | O dict `ParsedInvoice.statement` carrega **exatamente** estas chaves (o serviço de persistência da S58 espera estes nomes). NÃO inventar nomes — espelhar os campos do model |
| **Override mypy de libs untyped (onde adicionar pdfplumber/pdfminer)** | `@pyproject.toml:332-356` (bloco `[[tool.mypy.overrides]] ignore_missing_imports = true` — `playwright.*`, `reportlab.*`, `pywebpush.*`…) | Adicionar `"pdfplumber.*"` e `"pdfminer.*"` AQUI (mesmo bloco). A fronteira untyped fica contida no import; o código do parser anota as próprias assinaturas |
| **Deps três-lugares** | `@requirements.txt:36-41` (bloco "PDF Generation") + `@pyproject.toml:43-46` (bloco "PDF Generation") | `pdfplumber`/`pdfminer.six` entram em **ambos** (regra do projeto) no bloco de PDF; + mypy override (linha acima) |
| **Mock policy / banco real** | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas) | Parsing puro: **nada de banco** nestes testes (o parser não toca ORM). Fixtures sanitizadas alimentam `pdfplumber`; `detect_and_parse` recebe bytes. Sem mock de `pdfplumber` (é a lib real lendo um PDF de fixture) |

### O que as S56/S57/S58 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S56**: `BillingAccountType`/`SupplyStatus`; campos novos do `BillingAccount` (`account_type`, `holder_name`, `registered_address`, `secondary_identifier`, `supply_status`); unique identity; `recurring_for_generation()` manager (exclui IPTU).
- **S57**: refactor `InstallmentPlan.linked_billing_account → billing_account` (campo + `clean()` cross-model + `serializer.validate` + checklist completo + `convert_deferred` herda conta).
- **S58**: `WaterBillStatement`/`ElectricityBillStatement` (readings-only, 1:1 `Bill`, RLS) + `BillService.create_with_lines` estendido (`statement` + `installment_id` por linha) + `update_with_lines` (substitui linhas + upsert statement só em UNPAID+OPEN) + soft-delete cascade da statement + nested serializer.

> **Esta sessão depende de S56 (enums/tipo) + S58 (campos do statement que o `ParsedInvoice.statement` espelha).** Não recria enums, modelos, statements nem `create_with_lines`. **Se a S56/S58 não estiverem concluídas, PARE.**

---

## Escopo

### Arquivos a criar
- `finances/services/invoice_parsing/__init__.py` — pacote (vazio; **sem** re-export/barrel — consumidores importam da fonte direta `finances.services.invoice_parsing.registry`).
- `finances/services/invoice_parsing/base.py` — dataclasses `ParsedLine` e `ParsedInvoice` + protocolo `InvoiceParser` + helpers de parse compartilhados (`parse_brl(text) -> Decimal`, `parse_competence_from(label) -> date`, `parse_installment_marker(text) -> int | None`).
- `finances/services/invoice_parsing/dmae.py` — `DmaeWaterParser` (água; total-conservador).
- `finances/services/invoice_parsing/ceee.py` — `CeeeElectricityParser` (luz; energia líquida = total − Σ itens; 3 layouts).
- `finances/services/invoice_parsing/registry.py` — `detect_and_parse(pdf_bytes: bytes) -> ParsedInvoice` (detecta emissor por CNPJ; nenhum → `ValueError` PT) + `DMAE_CNPJ`/`CEEE_CNPJ` constantes.
- `tests/unit/test_finances/test_invoice_parsing_dmae.py` — testes do parser DMAE (água).
- `tests/unit/test_finances/test_invoice_parsing_ceee.py` — testes do parser CEEE (luz, 3 variantes).
- `tests/unit/test_finances/test_invoice_parsing_registry.py` — testes do `detect_and_parse` (detecção por CNPJ + erro).
- `tests/unit/test_finances/fixtures/invoices/` — fixtures **sanitizadas** (PDFs gerados de texto extraído sanitizado **ou** `.txt`/`.json` consumidos por um gerador de PDF de teste — ver §"Fixtures"). Nomes: `dmae_850_maio.pdf` (+ `.txt`), `ceee_850_solar.pdf` (+ `.txt`), `ceee_836_baixa_renda.pdf` (+ `.txt`), `ceee_solar_credito.pdf` (+ `.txt`), `desconhecida.pdf` (emissor não reconhecido).

### Arquivos a modificar
- `requirements.txt` — adicionar `pdfplumber>=0.11.0,<1.0` e `pdfminer.six>=20240706` no bloco "PDF Generation" (`:36-41`).
- `pyproject.toml` — `[project.dependencies]` bloco "PDF Generation" (`:43-46`): adicionar `"pdfplumber>=0.11.0,<1.0"` e `"pdfminer.six>=20240706"`; `[[tool.mypy.overrides]]` (`:332-356`): adicionar `"pdfplumber.*"` e `"pdfminer.*"` à lista `ignore_missing_imports = true`.

### NÃO fazer (pertence a outras sessões)
- **Endpoint `POST /api/finances/bills/parse_invoice`** (`@action(detail=False, parser_classes=[MultiPartParser])`, `is_staff`, lê `request.FILES`, 200 `{bill, line_items, statement, matched_account, existing_bill_id, warnings}`, 400 não-PDF) — é a **Sessão 60**. Esta sessão entrega só o **núcleo de parsing** (recebe `bytes`, devolve `ParsedInvoice`). O viewset/serviço da S60 chama `detect_and_parse`, casa a conta, reconcilia a parcela (resolve `installment_id` na linha serializada — `installment_number` fica interno ao `ParsedLine`) e serializa o draft.
- **Casamento real com `BillingAccount` no banco (`matched_account`)** — `ParsedInvoice.matched_account` é o **identificador** lido (inscrição/UC string) + um warning quando o parser não tem como casar; a **busca no banco** (`BillingAccount` ativa por `account_type`+`external_identifier`) é da **S60** (precisa de ORM). Aqui `matched_account` é `None` (o parser não consulta o banco — parsing puro). Documentar no docstring do dataclass.
- **`IptuAlertService`/`iptu_alerts`/banner/push/`send_finance_alerts`/tipos de `Notification`** — Fase 5, **Sessão 61**.
- **Persistência** (`BillService.create_with_lines`/`update_with_lines`, gravar statement, vincular `BillLineItem.installment`) — feito na **S58**; esta sessão NÃO persiste nada (parsing em memória; arquivo descartado — design §2 decisão #4).
- **Reconciliação real de parcela com `Installment` do plano** (vincular `BillLineItem.installment` ao `Installment` nº X) — é da **S58/S60** (precisa de ORM). Aqui o parser só **expõe** `ParsedLine.installment_number = X` (de `PARCELA X/N`); quem casa com o `Installment` no banco é o caller. Sem plano no banco → o parser **não sabe** disso (não consulta banco); o warning "crie o parcelamento" é emitido pela **S60** ao não achar o plano. *(Esta sessão emite só warnings de parsing — ex.: resíduo de soma ≠ 0; leitura implausível.)*
- **Frontend** (`useParseInvoice`, modal, `bill.schema.ts` statements) — S62/S63.
- **Nenhuma migração / mudança de model** — enums/statements são S56/S58; o parser não cria campo.

---

## Especificação

> Pacote de **parsing puro** em `finances/services/invoice_parsing/`. **Zero ORM** (não importa `Bill`/`BillingAccount` instâncias do banco; importa só os **enums** `BillingAccountType`/`SupplyStatus`/`BillBehavior` de `finances.models` para tipar). Tudo anotado (mypy strict + pyright strict). `Decimal` para dinheiro; quantização **só** via `quantize_money` (`finances/money.py`) ao montar `ParsedLine.amount`/totais. Mensagens de erro/aviso ao usuário em **PT**; logs/identificadores/nomes-de-campo em **EN**. **Extração posicional** (`extract_words`/`crop`), nunca regex sobre `extract_text()` plano (o texto reflui em multi-coluna → bind errado — design §5.1).

### Direção de dependência

`invoice_parsing` importa: `finances.money` (`quantize_money`), `finances.models` (**só os enums** `BillingAccountType`/`SupplyStatus`/`BillBehavior`), `pdfplumber` (fronteira untyped, contida no import), stdlib (`dataclasses`, `datetime`, `decimal`, `io.BytesIO`, `typing.Protocol`). **Nunca** importa views/serializers/serviços de persistência. `registry` importa `dmae`/`ceee` da fonte direta (sem barrel). **Sem** `from __future__ import annotations`; **sem** `if TYPE_CHECKING` (PEP 649 — `.claude/rules/coding-standards.md`).

### `finances/services/invoice_parsing/base.py`

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from finances.models import BillBehavior, BillingAccountType


@dataclass
class ParsedLine:
    """Uma linha de DESCRIÇÃO da fatura → futura BillLineItem. amount POSITIVO (stored-positive);
    is_offset=True para descontos/créditos (subtraídos do total). installment_number = X de 'PARCELA X/N'
    (None quando a linha não é parcela). category = rótulo canônico EN (AGUA/ESGOTO/PARCELAMENTO/...) ou "" (genérica)."""
    description: str
    amount: Decimal
    is_offset: bool = False
    installment_number: int | None = None
    category: str = ""


@dataclass
class ParsedInvoice:
    """Rascunho tipado de uma fatura parseada (parsing PURO — sem ORM). O caller (S60) serializa isto
    e abre o modal pré-preenchido. matched_account é SEMPRE None aqui (a busca no banco é da S60);
    o parser só expõe o identificador lido em external_identifier."""
    competence_month: date          # 1º dia do mês de competência (.replace(day=1))
    due_date: date                  # vencimento impresso
    external_identifier: str        # inscrição (DMAE) / UC (CEEE)
    behavior: str = BillBehavior.RECURRING
    account_type: str = BillingAccountType.GENERIC
    line_items: list[ParsedLine] = field(default_factory=list)
    statement: dict[str, object] | None = None   # chaves = campos do Water/ElectricityBillStatement (S58)
    matched_account: None = None    # sempre None (parsing puro; o match no banco é da S60)
    warnings: list[str] = field(default_factory=list)


class InvoiceParser(Protocol):
    """Contrato de um parser por concessionária. parse() recebe um pdfplumber.PDF aberto e devolve o rascunho."""
    def parse(self, pdf: object) -> ParsedInvoice: ...
```

**Helpers compartilhados (DRY — usados por DMAE e CEEE):**
- `parse_brl(text: str) -> Decimal` — converte "1.800,07"/"R$ 9,61"/"-0,42" em `Decimal` (remove `R$`/espaços/`.` milhar, `,`→`.`); resultado **não** quantizado (o caller quantiza ao montar `ParsedLine`). Negativo preservado (o sinal é tratado pelo caller, ver CEEE/`is_offset`).
- `parse_competence(label: str) -> date` — extrai `MM/AAAA` do rótulo e devolve `date(AAAA, MM, 1)`.
- `parse_installment_marker(text: str) -> int | None` — de `... PARCELA 24/46` / `Parcela 19/24` devolve `24`/`19`; sem marcador → `None`.
- `words_in_bbox(pdf_page: object, bbox: tuple[float, float, float, float]) -> list[dict[str, object]]` — wrapper fino sobre `page.crop(bbox).extract_words()` (a fronteira untyped contida; anota o retorno). **Extração posicional**: cada parser ancora rótulos estáveis e recorta a região do valor.

> `category` canônico (EN, constantes nomeadas no `base.py` ou no parser): `AGUA`, `ESGOTO`, `PARCELAMENTO`, `MULTA`, `JUROS`, `ATUALIZACAO`, `CIP`, `ENERGIA`, `DESCONTO`. Rótulo desconhecido → `category=""` (genérica) **e a linha NUNCA é descartada** (total-conservador — design §5.3). Usar um `dict[str, str]` de mapeamento rótulo→categoria (estilo `CATEGORY_MAP` do `parse_itau_fatura.py`).

### `finances/services/invoice_parsing/dmae.py` — `DmaeWaterParser` (água, total-conservador)

`parse(pdf) -> ParsedInvoice`:
- **Cabeçalho** (posicional, ancorado em rótulos): `competence_month` ← `parse_competence` da "FATURA MM/AAAA"; `due_date` ← vencimento impresso; `external_identifier` ← inscrição; `account_type = BillingAccountType.WATER`; `behavior = BillBehavior.RECURRING`.
- **Linhas** (total-conservador — design §5.3): **cada** linha da seção "DESCRIÇÃO DOS SERVIÇOS E TARIFAS" vira um `ParsedLine` com `description` = rótulo impresso e `amount` = `quantize_money(parse_brl(valor))`. Mapeamento rótulo→`category` (AGUA/ESGOTO/PARCELAMENTO/MULTA/JUROS/ATUALIZACAO); `DESCONTO …` → `is_offset=True` (magnitude positiva); **rótulo desconhecido** (ex.: `TAXA COBRANCA`) → `category=""`, **nunca descartado**. `PARCELAMENTO … PARCELA X/N` → `installment_number = X` (de `parse_installment_marker`), `category="PARCELAMENTO"`.
- **Statement** (chaves = `WaterBillStatement`, S58): `{"consumo_m3": int, "leitura_anterior": int|None, "leitura_atual": int|None, "leitura_dias": int|None, "data_leitura": date|None, "agua_status": SupplyStatus, "esgoto_status": SupplyStatus}` (LIGADO→`ACTIVE`, CORTADO→`CUT`).
- **Invariante (teste por fixture)**: `Σ(linhas não-offset) − Σ(linhas offset) == total impresso`. Verificado no 850/Maio: `1800.07+791.26+530.24+10.60+27.39+7.52 − 9.61 − 0.42 = 3157.05`. Resíduo ≠ 0 → **warning forte** em PT + linha `description="Outros/Ajuste"`, `amount=|resíduo|`, `is_offset=(resíduo<0)`, `category=""` para reconciliar (mantém a soma).
- **Plausibilidade (warning, não constraint — design §3.2)**: `leitura_atual >= leitura_anterior` salvo rollover → senão `warnings.append("Leitura atual menor que a anterior — confira a leitura.")`.

### `finances/services/invoice_parsing/ceee.py` — `CeeeElectricityParser` (luz, 3 layouts)

`parse(pdf) -> ParsedInvoice`:
- **Cabeçalho**: `external_identifier` ← UC; `competence_month` ← `parse_competence` do **"Conta Mês"** (NÃO emissão/vencimento — design §5.4); `due_date` ← vencimento; total impresso lido posicionalmente; `account_type = BillingAccountType.ELECTRICITY`; `behavior = BillBehavior.RECURRING`.
- **Linhas**: itens lidos (`CIP`, `Multa`→MULTA, `Correção`→ATUALIZACAO, `Juros`→JUROS, `Parcela X/N`→PARCELAMENTO+`installment_number`), cada um `ParsedLine` com `amount = quantize_money(parse_brl(...))`. **`Energia (líquida)` = total impresso − Σ(demais itens)** — emitida como `ParsedLine(description="Energia (líquida)", category="ENERGIA")`. Se a energia líquida der **negativo** (mês de alto crédito solar) → `is_offset=True` com **magnitude positiva** (respeita `CheckConstraint amount>=0` e a convenção stored-positive-subtracted — design §5.4).
- **Statement** (chaves = `ElectricityBillStatement`, S58): `{"consumo_kwh": int, "energia_injetada_kwh": int|None, "leitura_anterior": int|None, "leitura_atual": int|None, "leitura_dias": int|None, "classe": str, "bandeira": str}`. `energia_injetada_kwh=None` nos layouts não-solares (tarifa social 836). `classe` = "Residencial Pleno"/"Baixa Renda"; `bandeira` = "Verde"/"Amarela".
- **"FATURA ARRECADADA / NÃO RECEBER"** (2ª via já paga — design §5.4): detectar o marcador → `warnings.append("Fatura já arrecadada (2ª via) — o admin decide registrá-la como paga.")`. **Não** decide pagamento (só sinaliza; a S60/admin cria como paga se quiser).
- **3 layouts** (Apêndice A): solar pleno (840/850, `energia_injetada_kwh` setado, classe Residencial Pleno) e tarifa social (836, `energia_injetada_kwh=None`, classe Baixa Renda) — uma fixture por variante + a de crédito solar (energia líquida negativa).

### `finances/services/invoice_parsing/registry.py` — `detect_and_parse`

```python
DMAE_CNPJ = "92.924.901/0001-98"
CEEE_CNPJ = "08.467.115/0001-00"


def detect_and_parse(pdf_bytes: bytes) -> ParsedInvoice:
    """Detecta o emissor por CNPJ e delega ao parser. Bytes não-PDF / emissor desconhecido → ValueError PT.
    Parse em MEMÓRIA (BytesIO); o arquivo nunca é gravado (design §2 decisão #4)."""
```

- Abre `pdfplumber.open(BytesIO(pdf_bytes))` (bytes inválidos → `pdfplumber` levanta; **converter em `ValueError` PT** `"Arquivo não é um PDF válido."` — o caller S60 mapeia para 400).
- Lê o texto da 1ª página (só para **detecção de emissor** — busca o CNPJ; a extração de dados é posicional dentro do parser); CNPJ DMAE → `DmaeWaterParser().parse(pdf)`; CNPJ CEEE → `CeeeElectricityParser().parse(pdf)`; nenhum → `ValueError("Emissor da fatura não reconhecido (apenas DMAE e CEEE são suportados).")` (o caller S60 mapeia para 422).
- CNPJ normalizado para comparação (remover espaços/quebras de linha que o `extract_text` possa inserir — comparar dígitos).

### Fixtures sanitizadas (design §5.5 — CRÍTICO de segurança)

Os PDFs reais têm CPF/nomes/código de barras → **proibido** versioná-los. As fixtures são **texto extraído sanitizado** com valores **sintéticos** (sem CPF/barcode real), convertido em PDF pequeno para o `pdfplumber` ler posicionalmente:
- Para cada caso (`dmae_850_maio`, `ceee_850_solar`, `ceee_836_baixa_renda`, `ceee_solar_credito`, `desconhecida`) criar um `.txt` sanitizado (o layout posicional aproximado, com os valores do Apêndice A mas **sem CPF/barcode**) **e** o `.pdf` gerado a partir dele.
- **Gerar os PDFs com `reportlab`** (já é dependência do projeto — `requirements.txt:39`) por um helper de fixture em `conftest`/no próprio teste que desenha o texto em posições fixas (para o `extract_words`/`crop` ter coordenadas estáveis). O `.txt` é a fonte legível/sanitizada; o `.pdf` é o artefato lido pelo parser. **Não** usar PDF real.
- CNPJ do emissor **vai** nas fixtures (é público, não é segredo) — DMAE `92.924.901/0001-98`, CEEE `08.467.115/0001-00`. CPF/nome do titular → valores fictícios (ex.: `000.000.000-00`, "TITULAR TESTE") ou omitidos. O guard de CPF do CI (design §5.5) não pode disparar nestas fixtures.
- A `desconhecida.pdf` tem um CNPJ qualquer **diferente** dos dois → `detect_and_parse` levanta `ValueError`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas**. Aqui a fronteira externa é o **PDF de entrada** — usar **fixtures sanitizadas reais** (PDF gerado por `reportlab`), **não** mockar `pdfplumber` (é a lib real lendo o PDF — o teste prova a extração posicional de ponta a ponta). **Sem banco** (parsing puro — os testes deste pacote não precisam de `@pytest.mark.django_db`; o import de enums de `finances.models` não exige DB). `filterwarnings=error`: zero warnings. Valores `Decimal` comparados via `quantize_money`/string (nunca float).

### 1. RED — escrever os testes primeiro

> Cada `.test` lê seu PDF de `tests/unit/test_finances/fixtures/invoices/` (gerado pelo helper de fixture `reportlab`). Padrão: helper `_pdf_bytes(fixture_name) -> bytes` no arquivo de teste (ou `conftest`) que renderiza o `.txt` sanitizado em PDF posicional.

#### `tests/unit/test_finances/test_invoice_parsing_dmae.py`
```python
def test_dmae_parses_competence_first_day_from_fatura_label() -> None:
    """DMAE: competence_month = date(AAAA, MM, 1) extraído de 'FATURA MM/AAAA' (.replace(day=1))."""

def test_dmae_external_identifier_and_account_type() -> None:
    """DMAE: external_identifier = inscrição lida; account_type == BillingAccountType.WATER; behavior == RECURRING."""

def test_dmae_every_description_row_becomes_a_line_total_conserving() -> None:
    """DMAE 850/Maio: cada linha de DESCRIÇÃO vira ParsedLine (AGUA/ESGOTO/PARCELAMENTO/MULTA/JUROS/ATUALIZACAO),
    nenhuma descartada; rótulos conhecidos recebem category canônica."""

def test_dmae_unknown_label_taxa_cobranca_kept_as_generic() -> None:
    """DMAE: 'TAXA COBRANCA' (rótulo desconhecido) vira ParsedLine com category='' — nunca descartada (total-conservador)."""

def test_dmae_desconto_line_is_offset() -> None:
    """DMAE: 'DESCONTO …' → ParsedLine.is_offset=True com amount positivo (magnitude)."""

def test_dmae_sum_minus_offsets_equals_printed_total() -> None:
    """DMAE 850/Maio: Σ(não-offset) − Σ(offset) == 3157.05 (incl. TAXA COBRANCA); sem warning de resíduo."""

def test_dmae_residual_emits_strong_warning_and_balancing_line() -> None:
    """DMAE com total que não bate as linhas → warning PT forte + linha 'Outros/Ajuste' que reconcilia a soma."""

def test_dmae_parcelamento_marker_sets_installment_number() -> None:
    """DMAE: 'PARCELAMENTO … PARCELA 24/46' → ParsedLine.installment_number == 24, category='PARCELAMENTO'."""

def test_dmae_statement_readings_and_supply_status() -> None:
    """DMAE: statement tem consumo_m3, leitura_anterior/atual/dias, data_leitura, agua_status/esgoto_status (CORTADO→CUT)."""

def test_dmae_reading_decrease_emits_plausibility_warning() -> None:
    """DMAE: leitura_atual < leitura_anterior (sem rollover) → warning de plausibilidade PT (não exceção)."""
```

#### `tests/unit/test_finances/test_invoice_parsing_ceee.py`
```python
def test_ceee_competence_from_conta_mes_not_due_or_issue() -> None:
    """CEEE: competence_month vem do 'Conta Mês' (não emissão/vencimento), dia 1."""

def test_ceee_external_identifier_uc_and_account_type() -> None:
    """CEEE: external_identifier = UC; account_type == ELECTRICITY; behavior == RECURRING; due_date lido."""

def test_ceee_energia_liquida_equals_total_minus_items() -> None:
    """CEEE solar pleno 850: Energia (líquida) == total − Σ(CIP/Multa/Correção/Juros/Parcela); Σ linhas == total."""

def test_ceee_negative_energia_liquida_becomes_offset_positive_magnitude() -> None:
    """CEEE crédito solar: energia líquida negativa → ParsedLine.is_offset=True com magnitude positiva (amount>=0)."""

def test_ceee_solar_statement_fields() -> None:
    """CEEE solar pleno: statement com consumo_kwh, energia_injetada_kwh (setado), leitura_anterior/atual/dias,
    classe='Residencial Pleno', bandeira."""

def test_ceee_baixa_renda_statement_no_injection() -> None:
    """CEEE tarifa social 836: energia_injetada_kwh is None; classe='Baixa Renda'; consumo_kwh lido."""

def test_ceee_parcela_marker_sets_installment_number() -> None:
    """CEEE 850: 'Parcela 19/24' → ParsedLine.installment_number == 19, category='PARCELAMENTO'."""

def test_ceee_arrecadada_marker_emits_warning() -> None:
    """CEEE com 'FATURA ARRECADADA / NÃO RECEBER' → warning PT (2ª via já paga); parsing prossegue."""
```

#### `tests/unit/test_finances/test_invoice_parsing_registry.py`
```python
def test_detect_dmae_by_cnpj_delegates_to_water_parser() -> None:
    """registry: PDF com CNPJ 92.924.901/0001-98 → ParsedInvoice account_type == WATER."""

def test_detect_ceee_by_cnpj_delegates_to_electricity_parser() -> None:
    """registry: PDF com CNPJ 08.467.115/0001-00 → ParsedInvoice account_type == ELECTRICITY."""

def test_unknown_issuer_raises_value_error_pt() -> None:
    """registry: CNPJ não reconhecido → ValueError com mensagem PT (caller S60 mapeia 422)."""

def test_non_pdf_bytes_raises_value_error_pt() -> None:
    """registry: bytes que não são PDF → ValueError PT 'Arquivo não é um PDF válido.' (caller S60 mapeia 400)."""

def test_cnpj_detection_tolerates_whitespace_from_extract_text() -> None:
    """registry: CNPJ com espaços/quebras inseridos pelo extract_text ainda casa (comparação por dígitos)."""
```

> Rodar (devem **falhar** — pacote/parsers/registry/deps ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_invoice_parsing_dmae.py \
>   tests/unit/test_finances/test_invoice_parsing_ceee.py \
>   tests/unit/test_finances/test_invoice_parsing_registry.py -q
> ```

### 2. GREEN — implementar

1. **Deps**: adicionar `pdfplumber`/`pdfminer.six` em `requirements.txt` + `pyproject.toml [project.dependencies]` + os 2 módulos ao `[[tool.mypy.overrides]] ignore_missing_imports`. Instalar via `uv add "pdfplumber>=0.11.0,<1.0" "pdfminer.six>=20240706"` (atualiza `uv.lock`).
2. **Fixtures**: criar os `.txt` sanitizados (valores do Apêndice A, **sem** CPF/barcode) + o helper `reportlab` que gera o `.pdf` posicional; gerar os PDFs em `tests/unit/test_finances/fixtures/invoices/`.
3. `finances/services/invoice_parsing/__init__.py` (vazio), `base.py` (dataclasses + protocolo + helpers de parse), `dmae.py`, `ceee.py`, `registry.py` — extração **posicional** (`extract_words`/`crop`), importando `quantize_money` (`finances/money.py`) e os enums (`finances.models`).

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_invoice_parsing_dmae.py tests/unit/test_finances/test_invoice_parsing_ceee.py tests/unit/test_finances/test_invoice_parsing_registry.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Helpers de parse (`parse_brl`/`parse_competence`/`parse_installment_marker`/`words_in_bbox`) vivem **só** em `base.py` (fonte única); DMAE e CEEE importam-nos (sem duplicar a lógica de valor BR / competência / marcador de parcela).
- Mapeamento rótulo→categoria como **dict nomeado** (uma definição por parser; rótulos canônicos EN como constantes — sem magic strings espalhadas). A regra "total-conservador / nunca descartar linha" é um único caminho (não ramos copiados).
- Mensagens PT de warning/erro como **constantes nomeadas** (sem strings repetidas). A fronteira untyped `pdfplumber` fica contida em `words_in_bbox`/`registry` (anotadas) — o resto do parser é totalmente tipado.
- `ParsedInvoice.matched_account` é sempre `None` aqui — documentar a fronteira (o match no banco é da S60). Confirmar **zero** import de ORM (`Bill`/`BillingAccount` instâncias) no pacote.

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados.

```bash
python -m pytest tests/unit/test_finances/test_invoice_parsing_dmae.py tests/unit/test_finances/test_invoice_parsing_ceee.py \
  tests/unit/test_finances/test_invoice_parsing_registry.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/services/invoice_parsing/ tests/unit/test_finances/
ruff format --check finances/services/invoice_parsing/ tests/unit/test_finances/
mypy core/ finances/
pyright finances/services/invoice_parsing/
```

> **Confirmação de deps três-lugares + dígitos do CNPJ** (não regressão):
> ```bash
> python -c "import pdfplumber, pdfminer; print('deps ok')"
> ```
> e conferir que `pdfplumber.*`/`pdfminer.*` estão no `[[tool.mypy.overrides]]` (mypy não acusa import-untyped).

---

## Constraints

- **Parsing puro / zero ORM**: o pacote `invoice_parsing` **não** importa instâncias do banco nem consulta `BillingAccount`/`Bill`. Importa **só os enums** (`BillingAccountType`/`SupplyStatus`/`BillBehavior`) e `quantize_money`. `matched_account` é sempre `None` (o match no banco é da S60).
- **Extração posicional** (design §5.1): `page.extract_words()`/`page.crop(bbox)` ancorado em rótulos estáveis — **proibido** regex sobre `extract_text()` plano para extrair dados (o texto reflui em multi-coluna). `extract_text` só para **detecção de emissor por CNPJ** no `registry`.
- **Total-conservador (DMAE)** (design §5.3): **toda** linha de DESCRIÇÃO vira `ParsedLine`; rótulo desconhecido → `category=""`, **nunca descartado**. Invariante `Σ(não-offset) − Σ(offset) == total` (resíduo → warning + linha de ajuste).
- **Energia líquida (CEEE)** (design §5.4): `Energia = total − Σ(itens)`; negativa → `is_offset=True` magnitude positiva (respeita `amount>=0`). Competência do **"Conta Mês"** (não emissão/vencimento). "FATURA ARRECADADA" → warning.
- **Statement = chaves do model S58**: as chaves do dict `statement` são **exatamente** os campos de `WaterBillStatement`/`ElectricityBillStatement` (a S58/S60 persiste sem renomear). Sem campos de dinheiro no statement (dinheiro é `ParsedLine` — fonte única, design §3.2).
- **Quantização só na fronteira** (`finances/money.py`): `parse_brl` devolve `Decimal` cru; `quantize_money` ao montar `ParsedLine.amount`/totais. **Nunca** `float` para dinheiro.
- **Fixtures sanitizadas** (design §5.5/§15 segurança): **proibido** versionar PDF real com CPF/barcode; fixtures são texto sanitizado (valores sintéticos) renderizado em PDF por `reportlab`. CNPJ do emissor (público) pode aparecer; CPF/nome → fictícios. Guard de CPF do CI não dispara.
- **Mensagens PT, logs/identificadores EN**: warnings/erros ao usuário em Português; nomes de campo/categoria/log em Inglês.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código. Tipos completos (mypy strict + pyright strict) — a fronteira untyped `pdfplumber`/`pdfminer` é resolvida via `[[tool.mypy.overrides]] ignore_missing_imports`, **não** via `# type: ignore`.
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from datetime import date`, `from decimal import Decimal`, `from typing import Protocol`).
- **Sem re-exports / barrel / shim**: `__init__.py` vazio; consumidores importam de `finances.services.invoice_parsing.registry`/`.base` direto. `registry` importa `dmae`/`ceee` da fonte.
- **Sem endpoint/serializer/viewset/URL** (S60); **sem** `IptuAlertService`/banner/push (S61); **sem** persistência/`create_with_lines` (S58, já feito); **sem** frontend (S62/S63); **sem** migração/model novo. **Sem** armazenar o PDF (parse em memória — design §2 decisão #4).

## Critérios de Aceite (binários)

- [ ] `finances/services/invoice_parsing/base.py` define `ParsedLine` (`description`/`amount`/`is_offset`/`installment_number`/`category`) e `ParsedInvoice` (`competence_month`/`due_date`/`external_identifier`/`behavior`/`account_type`/`line_items`/`statement`/`matched_account=None`/`warnings`) + protocolo `InvoiceParser` + helpers `parse_brl`/`parse_competence`/`parse_installment_marker`/`words_in_bbox`; importa enums de `finances.models` e `quantize_money` de `finances.money`; **zero** import de ORM.
- [ ] `DmaeWaterParser` (água): competência de "FATURA MM/AAAA" (dia 1); **toda** linha de DESCRIÇÃO vira `ParsedLine` (total-conservador — `TAXA COBRANCA` mantida genérica, `DESCONTO` offset, `PARCELAMENTO X/N`→`installment_number`); statement com leituras + `agua_status`/`esgoto_status` (CORTADO→CUT); invariante `Σ−offsets==total` (3157.05 no 850/Maio); resíduo→warning+linha de ajuste; leitura decrescente→warning de plausibilidade.
- [ ] `CeeeElectricityParser` (luz): competência do "Conta Mês"; `Energia líquida = total − Σ itens` (negativa→`is_offset` magnitude positiva); statement (`consumo_kwh`/`energia_injetada_kwh`/leituras/`classe`/`bandeira`); cobre solar pleno + tarifa social (sem injeção) + crédito solar; `Parcela X/N`→`installment_number`; "FATURA ARRECADADA"→warning.
- [ ] `detect_and_parse(pdf_bytes)` detecta DMAE (`92.924.901/0001-98`) e CEEE (`08.467.115/0001-00`) por CNPJ (tolera espaços do `extract_text`), delega ao parser; não-PDF→`ValueError` PT; emissor desconhecido→`ValueError` PT; parse em memória (`BytesIO`), **nada** gravado.
- [ ] `pdfplumber`+`pdfminer.six` adicionados a `requirements.txt` **e** `pyproject.toml [project.dependencies]` **e** `[[tool.mypy.overrides]] ignore_missing_imports`; `import pdfplumber, pdfminer` funciona; mypy não acusa import-untyped.
- [ ] Fixtures **sanitizadas** (texto sintético sem CPF/barcode, renderizado em PDF por `reportlab`) em `tests/unit/test_finances/fixtures/invoices/`: DMAE 850/Maio, CEEE solar, CEEE baixa-renda, CEEE crédito-solar, desconhecida.
- [ ] Testes cobrem Apêndice B / Fase 4: soma==total incl `TAXA COBRANCA`; energia líquida negativa→offset; "ARRECADADA" sinalizada; competência por emissor `.replace(day=1)`; cada campo de statement por variante CEEE + DMAE; CNPJ desconhecido→erro; não-PDF→erro.
- [ ] `python -m pytest tests/unit/test_finances/test_invoice_parsing_*` passa 100%, **coverage `finances` ≥90%** nos módulos tocados.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright finances/services/invoice_parsing/` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum endpoint/serializer/viewset/URL; nenhum `IptuAlertService`/banner/push; nenhuma persistência/`create_with_lines`/frontend; nenhum modelo/migração novo; nenhum PDF real versionado; nenhum import de ORM no pacote `invoice_parsing`.

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_invoice_parsing_dmae.py tests/unit/test_finances/test_invoice_parsing_ceee.py \
     tests/unit/test_finances/test_invoice_parsing_registry.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   ruff check finances/services/invoice_parsing/ tests/unit/test_finances/
   ruff format --check finances/services/invoice_parsing/ tests/unit/test_finances/
   mypy core/ finances/
   pyright finances/services/invoice_parsing/
   python -c "import pdfplumber, pdfminer; print('deps ok')"
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 59 (status **concluída**) na tabela da feature Contas tipadas + parser.
   - **Arquivos Criados**: `finances/services/invoice_parsing/{__init__,base,dmae,ceee,registry}.py`; `tests/unit/test_finances/{test_invoice_parsing_dmae,test_invoice_parsing_ceee,test_invoice_parsing_registry}.py`; fixtures `tests/unit/test_finances/fixtures/invoices/*.{txt,pdf}`.
   - **Arquivos Modificados**: `requirements.txt` (+pdfplumber/pdfminer.six), `pyproject.toml` (deps + mypy override), `uv.lock`.
   - **Nota**: "Fase 4 — núcleo do parser (parsing PURO, zero ORM): `ParsedInvoice`/`ParsedLine`/`InvoiceParser`; `DmaeWaterParser` total-conservador (toda linha→ParsedLine, TAXA COBRANCA genérica, DESCONTO offset, PARCELAMENTO X/N→installment_number, invariante Σ−offsets==total, statement leituras+supply); `CeeeElectricityParser` (energia líquida=total−Σitens, negativa→offset, statement kWh/injeção/classe/bandeira, ARRECADADA→warning, 3 layouts); `detect_and_parse` por CNPJ (DMAE/CEEE), não-PDF/desconhecido→ValueError PT, parse em memória. Extração POSICIONAL (extract_words/crop). Fixtures SANITIZADAS (sem CPF/barcode). matched_account=None (match no banco=S60). **Endpoint parse_invoice=S60; IptuAlert/banner=S61; frontend=S62/S63; persistência=S58.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir da branch da feature — ex.: `feat/condo-utility-bills`):
   ```
   feat(finances): complete session 59 — invoice parser core (DMAE water + CEEE electricity, positional pdfplumber, detect_and_parse)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **60 — Endpoint `POST /api/finances/bills/parse_invoice`** (`@action(detail=False)`, `parser_classes=[MultiPartParser]`, `is_staff`): lê `request.FILES`, chama `detect_and_parse` (bytes), serializa o `ParsedInvoice` em `{bill, line_items, statement, matched_account, warnings}`, faz o **match real** com `BillingAccount` ativa (account_type+external_identifier), warning de idempotência se já há `Bill` ativo na competência, mapeia `ValueError` → 400 (não-PDF) / 422 (emissor). A S60 **consome** `detect_and_parse`/`ParsedInvoice`; **não** recria o parser.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`finances.services.invoice_parsing.base`**: `ParsedLine{description: str, amount: Decimal, is_offset: bool=False, installment_number: int|None=None, category: str=""}`; `ParsedInvoice{competence_month: date, due_date: date, external_identifier: str, behavior: str=RECURRING, account_type: str=GENERIC, line_items: list[ParsedLine], statement: dict|None, matched_account: None, warnings: list[str]}`; protocolo `InvoiceParser`. **S60** serializa o `ParsedInvoice` em `{bill, line_items, statement, matched_account, warnings}`.
- **`finances.services.invoice_parsing.registry.detect_and_parse(pdf_bytes: bytes) -> ParsedInvoice`** — detecta emissor por CNPJ (`DMAE_CNPJ="92.924.901/0001-98"`, `CEEE_CNPJ="08.467.115/0001-00"`); não-PDF → `ValueError` PT (caller S60 → 400); emissor desconhecido → `ValueError` PT (caller S60 → 422). **S60** `bills/parse_invoice` chama-o com os bytes de `request.FILES` (parse em memória; arquivo descartado).
- **`statement` dict keys** = campos de `WaterBillStatement` (`consumo_m3`/`leitura_anterior`/`leitura_atual`/`leitura_dias`/`data_leitura`/`agua_status`/`esgoto_status`) e `ElectricityBillStatement` (`consumo_kwh`/`energia_injetada_kwh`/`leitura_anterior`/`leitura_atual`/`leitura_dias`/`classe`/`bandeira`) da S58 — a **S58/S60** persiste sem renomear.
- **`matched_account` é `None` aqui** — o match real com `BillingAccount` no banco (por `account_type`+`external_identifier`) + o warning de idempotência (já existe `Bill` ativo na competência) são da **S60**. `ParsedLine.installment_number` é o `X` de `PARCELA X/N`; a vinculação ao `Installment` nº X do plano embutido é da **S58/S60** (precisa de ORM).
- **Deps**: `pdfplumber`/`pdfminer.six` agora disponíveis (requirements + pyproject + mypy override) — a S60 pode importar `pdfplumber` indiretamente via `detect_and_parse` sem re-adicionar deps.
