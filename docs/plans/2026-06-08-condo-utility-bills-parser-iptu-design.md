# Design — Contas de serviço tipadas (água/luz/IPTU) + parser de fatura PDF + alerta de IPTU + modal responsivo

> Data: 2026-06-08 · Status: **revisado** (5 lentes adversariais + verificação contra o código real, gaps corrigidos) · Autor: Alvaro Souza (+ Claude)
> Estende o módulo `finances` já implementado (app condo finance, S34–S50). NÃO substitui nada; é aditivo + um refactor pontual (`InstallmentPlan.linked_billing_account → billing_account`).
> Base conceitual: `docs/plans/2026-06-06-condominium-finance-design.md` (v3). Princípios obrigatórios: `.claude/rules/design-principles.md` (SOLID/DRY/KISS/YAGNI, sem workarounds, sem backwards-compat, refatoração completa de todos os consumidores, sem `# type: ignore`/`# noqa`, mypy+pyright strict, ruff, zero warnings, ≥90% em `finances`, mock só de fronteiras externas).

## Sumário

1. [Contexto e objetivo](#1-contexto-e-objetivo)
2. [Decisões travadas](#2-decisões-travadas)
3. [Modelo de dados](#3-modelo-de-dados)
4. [Refactor `InstallmentPlan.billing_account` (checklist completo de consumidores)](#4-refactor-installmentplanbilling_account-checklist-completo-de-consumidores)
5. [Parser de fatura (DMAE água + CEEE luz)](#5-parser-de-fatura-dmae-água--ceee-luz)
6. [Reconciliação de parcela — passado imutável, atual/futuro ajustável](#6-reconciliação-de-parcela--passado-imutável-atualfuturo-ajustável)
7. [Persistência: `create_with_lines` / `update_with_lines`](#7-persistência-create_with_lines--update_with_lines)
8. [Modal "Nova Conta" responsivo + import de fatura](#8-modal-nova-conta-responsivo--import-de-fatura)
9. [Alerta de IPTU (banner + push)](#9-alerta-de-iptu-banner--push)
10. [Invariantes financeiras afetadas](#10-invariantes-financeiras-afetadas)
11. [Cache & signals](#11-cache--signals)
12. [Migrações & RLS](#12-migrações--rls)
13. [Seed dos dados reais](#13-seed-dos-dados-reais)
14. [Faseamento + gate por fase](#14-faseamento--gate-por-fase)
15. [Segurança / permissões](#15-segurança--permissões)
16. [Fora de escopo (YAGNI)](#16-fora-de-escopo-yagni)
17. [Apêndice A — inventário real das contas](#apêndice-a--inventário-real-das-contas)
18. [Apêndice B — edge-cases por fase (testes RED)](#apêndice-b--edge-cases-por-fase-testes-red)

---

## 1. Contexto e objetivo

O módulo `finances` já modela contas recorrentes por prédio (`BillingAccount` → `Bill` + `BillLineItem`), parcelas embutidas e avulsas (`InstallmentPlan`/`Installment`), IPTU diferido (`Bill(deferred)` + `convert_deferred`), suspensão, pagamento parcial, projeção e fechamento. Esta feature acrescenta o que falta para operar as contas **reais e fixas** dos prédios 836 e 850 com precisão:

1. **Contas tipadas** (água/luz/IPTU) com identidade própria (inscrição/UC/medidor) e **dados estruturados de fatura por tipo**, mantendo contas genéricas.
2. **Parser de fatura PDF** (DMAE + CEEE): upload → lê os dados → pré-preenche o modal → o admin confere e salva. **Sem armazenar o PDF** (parse em memória).
3. **Alerta de IPTU**: nunca deixar passar de 1 parcela atrasada (senão perde o parcelamento) — banner no dashboard + push.
4. **Modal de contas 100% responsivo** (corrige footer que some, campos faltando, layout).
5. **Seed** das contas e parcelamentos reais (local; prod por último, após deploy).

Objetivo de qualidade: cada parte é TDD, gate por fase ≥90% em `finances`, zero warnings, sem regressão nas invariantes do módulo.

---

## 2. Decisões travadas

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | Tipo de conta | Enum `account_type` em `BillingAccount`: `WATER`, `ELECTRICITY`, `IPTU`, `INTERNET`, `GENERIC`. First-class + extensível. |
| 2 | Dados da fatura | Tabelas de detalhe **1:1 por tipo** (`WaterBillStatement`, `ElectricityBillStatement`) ligadas ao `Bill`, **só leituras/consumo** (o dinheiro fica em `BillLineItem` — fonte única). |
| 3 | Parser | `pdfplumber` (texto, sem OCR), **extração posicional** (`extract_words`/`crop` por bbox), por concessionária. Upload → rascunho → pré-preenche o modal → salvar. |
| 4 | Anexo do PDF | **NÃO armazenar** (parse em memória, arquivo descartado). `Bill.attachment` (campo pré-existente) fica intocado e sem uso. |
| 5 | Parcela | Embutida (`embedded=True`, água/luz) vs avulsa (`embedded=False`, IPTU). Refactor `linked_billing_account → billing_account` (conta dona de **qualquer** plano). |
| 6 | IPTU | Conta `account_type=IPTU` = só registro da inscrição + agrupador; **não auto-gera** conta recorrente. Parcelas via planos avulsos; dívida do ano = `Bill(deferred)` → `convert_deferred`. |
| 7 | Alerta IPTU | 1 atrasada = WARNING; ≥2 = CRITICAL. **Banner + Notification in-app = canal load-bearing; push = best-effort.** Notificação **agregada** (1 resumo/admin/dia), idempotência **SP-aware**. |
| 8 | Competência do seed | Parcelas em aberto/atrasadas do estado inicial entram com `competence_month = primeiro mês rastreado (2026-06)` (evita poluir mês pré-tracking); `due_date` real preservado. |
| 9 | Atrasados (KPI) | Inclui parcelas de IPTU vencidas (total real devido); o banner de IPTU é **drill-down de risco**, não um segundo total. |
| 10 | Modal | `DialogBody` reutilizável (header/footer fixos, corpo rola) no `components/ui/dialog.tsx`; aplica ao modal de contas + alinha os modais novos do `finances`. |

---

## 3. Modelo de dados

Convenções herdadas: `(AuditMixin, SoftDeleteMixin, models.Model)`, managers duplos, `DecimalField(max_digits=12, decimal_places=2)` para dinheiro, partial unique `condition=Q(is_deleted=False)`, `CheckConstraint`, `clean()` em PT, RLS habilitada na mesma migração de cada tabela nova.

### 3.1 `BillingAccount` — alterações

```python
class BillingAccountType(models.TextChoices):
    WATER = "water", "Água"
    ELECTRICITY = "electricity", "Luz"
    IPTU = "iptu", "IPTU"
    INTERNET = "internet", "Internet"
    GENERIC = "generic", "Genérica"

class SupplyStatus(models.TextChoices):
    ACTIVE = "active", "Ligada"
    CUT = "cut", "Cortada"
```

Campos novos:
- `account_type = CharField(choices=BillingAccountType.choices, default=GENERIC)` — **default GENERIC** (ver §12 sobre backfill).
- `holder_name = CharField(max_length=200, blank=True)` — titular cadastrado (RAUL / CELIA / PRANAS BIELAVICIUS).
- `registered_address = CharField(max_length=255, blank=True)` — endereço **como consta na concessionária** (resolve 850=«838», 836=«828»).
- `secondary_identifier = CharField(max_length=100, blank=True)` — imóvel/matrícula (DMAE), medidor (CEEE), nº lançamento (IPTU).
- `supply_status = CharField(choices=SupplyStatus.choices, default=ACTIVE)` — água/luz; a água do 836 está `CUT`.

`external_identifier` (já existe) = inscrição/UC principal.

**Unicidade (nova):**
```python
models.UniqueConstraint(
    fields=["building", "account_type", "external_identifier"],
    condition=Q(is_deleted=False),
    name="unique_active_billing_account_identity",
)
```
- `condition=Q(is_deleted=False)` é **obrigatório** (sem ele, soft-delete + recriação quebra — invariante do app).
- `clean()` + serializer **rejeitam `external_identifier` em branco** quando `account_type ∈ {WATER, ELECTRICITY, IPTU}` (Postgres trata `'' = ''` como igual → duas contas do mesmo tipo no prédio colidiriam). Mensagem PT: "Informe a inscrição/UC para contas de água, luz ou IPTU."
- `building` nulo (nível-condomínio): Postgres trata `NULL` como distinto (nulls_distinct default), então duas contas condo-level do mesmo tipo não colidem — aceitável (contas tipadas reais sempre têm prédio).
- As 4 linhas reais que precisam coexistir: 836 luz UC `…798…-05` vs UC `650.847.010-16`; 850 IPTU `516481` vs `516503` — todas com `external_identifier` distinto → passam. Teste pinado: as 4 inserem; duplicata ativa rejeitada; duplicata soft-deletada permitida.

### 3.2 `WaterBillStatement` (novo, 1:1 → `Bill`) — só leituras/consumo

```python
class WaterBillStatement(AuditMixin, SoftDeleteMixin, models.Model):
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="water_statement")
    consumo_m3 = models.PositiveIntegerField()                       # 158, 51, 13…
    leitura_anterior = models.PositiveIntegerField(null=True, blank=True)
    leitura_atual = models.PositiveIntegerField(null=True, blank=True)
    leitura_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    data_leitura = models.DateField(null=True, blank=True)
    agua_status = models.CharField(choices=SupplyStatus.choices, default=SupplyStatus.ACTIVE)
    esgoto_status = models.CharField(choices=SupplyStatus.choices, default=SupplyStatus.ACTIVE)
```
- **Sem campos de dinheiro** (água R$/esgoto R$/parcela/multa/juros são `BillLineItem` — fonte única; DRY).
- `SoftDeleteMixin` + `on_delete=CASCADE` (caminho hard-delete). Soft-delete do `Bill` **não** dispara `on_delete` → o serviço de delete do bill faz `water_statement.delete()` explicitamente (ver §7). Nested no `BillSerializer` → bill escondido nunca expõe statement vivo. RLS na mesma migração.
- Guard de plausibilidade no parser (não constraint): `leitura_atual >= leitura_anterior` salvo rollover → warning.

### 3.3 `ElectricityBillStatement` (novo, 1:1 → `Bill`) — só leituras/consumo

```python
class ElectricityBillStatement(AuditMixin, SoftDeleteMixin, models.Model):
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name="electricity_statement")
    consumo_kwh = models.PositiveIntegerField()                      # 1752, 269…
    energia_injetada_kwh = models.PositiveIntegerField(null=True, blank=True)  # null = sem solar
    leitura_anterior = models.PositiveIntegerField(null=True, blank=True)
    leitura_atual = models.PositiveIntegerField(null=True, blank=True)
    leitura_dias = models.PositiveSmallIntegerField(null=True, blank=True)
    classe = models.CharField(max_length=60, blank=True)             # "Residencial Pleno" / "Baixa Renda"
    bandeira = models.CharField(max_length=40, blank=True)           # "Verde", "Amarela"
```
- Mesma política de soft-delete/CASCADE/nested/RLS da §3.2. Cobre os 3 layouts CEEE (solar pleno 840/850, tarifa social 836). `energia_injetada_kwh` nulo nos não-solares.

### 3.4 IPTU — sem statement; conta = registro + agrupador
- `BillingAccount(account_type=IPTU)` por inscrição: identidade (`external_identifier`, `holder_name`, `registered_address`, nº lançamento em `secondary_identifier`). **Não auto-gera** conta recorrente (§10.3).
- Parcelamentos (termos) = `InstallmentPlan(embedded=False, billing_account=<conta IPTU>)`.
- Dívida do ano "Em Dívida" = `Bill(lifecycle_state=deferred, billing_account=<conta IPTU>)` **com 1 `BillLineItem` do valor total da dívida** (senão `convert_deferred` gera plano R$0). `convert_deferred` → `InstallmentPlan` herdando `billing_account` (§10.2).

---

## 4. Refactor `InstallmentPlan.billing_account` (checklist completo de consumidores)

`linked_billing_account` (hoje só permitido em embutido) generaliza para `billing_account` (conta dona de **qualquer** plano). `clean()`:
- `embedded=True` ⇒ `billing_account` obrigatório e de tipo consumo (`WATER`/`ELECTRICITY`/`INTERNET`) — leitura cross-model `self.billing_account.account_type`.
- `embedded=False` ⇒ livre (`billing_account=<conta IPTU>` para IPTU; `None` para empréstimo genérico).
- Mensagens de erro em PT (renomear as chaves do dict de erro também).
- **DRF não chama `Model.clean()`** → espelhar a regra em `serializer.validate()` (como o invariante embedded↔linked já é espelhado hoje em `serializers.py:373-392`).

**Ordem da migração:** AddField `account_type` (§3.1) **antes** do `RenameField` (o `clean()` lê `account_type` do alvo da FK).

### Checklist — atualizar TODOS os consumidores (sem shim, sem backwards-compat):

**Backend — atributo/kwarg (mypy/pyright pegam):**
- `finances/models.py:444` (campo), `:479-486` (`clean()`: `self.linked_billing_account_id` + chaves do dict).
- `finances/serializers.py:337-344` (nested + `_id`, **`source="linked_billing_account"` é string literal** → `source="billing_account"`), `:357-358` (Meta.fields), `:377-379`/`:383`/`:389` (`validate()` + chaves de erro).
- `finances/services/condo_projection_service.py:204` (atributo `installment.plan.linked_billing_account`).
- `finances/services/bill_generation_service.py:169`/`:170`/`:174` (atributo).

**Backend — `select_related` STRING LITERAL (nenhum type-checker pega; falha em runtime com `FieldError`):**
- `finances/services/condo_projection_service.py:200` → `'plan__billing_account'`.
- `finances/services/bill_generation_service.py:150` → `'plan__billing_account'`.
- `finances/viewsets/installment_payroll_views.py:39` → `'billing_account'`.
- → **teste de integração que EXECUTA cada query path** (prova de ausência de `FieldError`).

**Backend — testes (quebram se não renomear):**
- `tests/unit/test_finances/test_installment_models.py:70-81` (kwarg + assert da chave do dict).
- `tests/unit/test_finances/test_generation_installments_payroll.py:63,89,106`.
- `tests/unit/test_finances/test_condo_projection_service.py:134,154,220`.
- `tests/integration/test_finances_installments_employee_api.py:61` (payload `linked_billing_account_id`), `:66` (`response.data["linked_billing_account"]["id"]`).

**Frontend (lockstep com o payload do serializer):**
- `frontend/lib/schemas/finances/installment-plan.schema.ts:38-39,46-55`.
- `frontend/app/(dashboard)/finances/installment-plans/_components/installment-plan-form-schema.ts:20,24-29`.
- `installment-plan-form-modal.tsx:61,76-77,120,343-372` (campo, `planToDefaults`, fallback `plan.linked_billing_account_id ?? plan.linked_billing_account?.id`, Controller name).
- `frontend/lib/api/hooks/use-installment-plans.ts:43` (`Omit<…,'linked_billing_account'>`), `:105` (destructure).
- Mocks/testes: `frontend/tests/mocks/data/finances.ts:227-228`, `installment-plans-page.test.tsx:44-45`, `installment-plan-form-modal.test.tsx:49-57,104-108`, `use-installment-plans.test.tsx:103,130,139`.

**`convert_deferred` (`installment_plan_service.py:105-118`):** setar `plan.billing_account = locked.billing_account` e assertar que é tipo IPTU (ver §10.2).

Gate do refactor: `ruff && mypy core/ finances/ && pyright && pytest tests/unit/test_finances tests/integration/test_finances_installments_employee_api.py` + o teste de query-execution + `cd frontend && npm run type-check && npm run test:unit`. Rodar `grep -rn linked_billing_account` no repo inteiro = 0 ocorrências ao final.

---

## 5. Parser de fatura (DMAE água + CEEE luz)

### 5.1 Estrutura (SRP, service-layer)
`finances/services/invoice_parsing/`:
- `base.py` — `ParsedInvoice` (dataclass tipada: campos do bill + `line_items: list[ParsedLine]` + `statement` + `matched_account` + `warnings: list[str]`) e a interface `InvoiceParser`.
- `dmae.py` — `DmaeWaterParser`.
- `ceee.py` — `CeeeElectricityParser` (3 layouts).
- `registry.py` — `detect_and_parse(pdf_bytes) -> ParsedInvoice` (detecta emissor por CNPJ: DMAE `92.924.901/0001-98`; CEEE `08.467.115/0001-00`; nenhum → 422 PT).

**Tecnologia / deps:** `pdfplumber` + `pdfminer.six` adicionados a `requirements.txt` **e** `pyproject.toml [project.dependencies]` (regra três-lugares). Como são untyped, adicionar `"pdfplumber.*"` e `"pdfminer.*"` ao bloco `[[tool.mypy.overrides]] ignore_missing_imports = true` (pyproject:332-356, onde já vivem playwright/reportlab). Pyright já é tolerante (`reportMissingTypeStubs` off). O código do parser **anota as próprias assinaturas** (a fronteira untyped fica contida no import).

**Extração posicional:** usar `page.extract_words()` / `page.crop(bbox)` ancorado em rótulos estáveis, **não** regex sobre `extract_text()` plano (o texto reflui em layout multi-coluna → bind errado). Testes por variante (DMAE + as 3 CEEE) assertando **cada** campo do statement.

### 5.2 Fluxo
```
POST /api/finances/bills/parse_invoice  (multipart, is_staff, parser_classes=[MultiPartParser])
  → lê request.FILES; pdfplumber.open(BytesIO) (não-PDF → 400 PT)
  → registry.detect_and_parse(bytes)  [parse em MEMÓRIA; arquivo descartado]
  → 200 {bill, line_items, statement, matched_account, warnings}   (NÃO grava nada)
[Frontend] abre o modal pré-preenchido → admin confere → salva via create_with_lines/update_with_lines (§7)
```

### 5.3 Extração — DMAE (água)
- **Total-conservador:** cada linha de "DESCRIÇÃO DOS SERVIÇOS E TARIFAS" vira um `ParsedLine` usando o rótulo impresso como `description`; rótulos conhecidos mapeiam categoria (`AGUA`, `ESGOTO`, `PARCELAMENTO`, `MULTA`, `JUROS`, `ATUALIZACAO`), `DESCONTO …` → `is_offset=True`; **rótulos desconhecidos** (ex.: `TAXA COBRANCA`) → categoria genérica, **nunca descartados**.
- `PARCELAMENTO … PARCELA X/N` → reconcilia com o `Installment` nº X do plano embutido (§6); **se não houver plano** → linha genérica + warning "crie o parcelamento em Planos de Parcelamento" (não cria plano).
- Statement: `consumo_m3`, `leitura_anterior/atual/dias`, `agua_status`/`esgoto_status` (LIGADO/CORTADO), `data_leitura`.
- Cabeçalho: `competence_month` (da "FATURA MM/AAAA", `.replace(day=1)`), `due_date` (vencimento), `external_identifier` (inscrição).
- **Invariante (teste por fixture):** `Σ(linhas não-offset) − Σ(linhas offset) == total impresso`. Verificado no 850/Maio: 1.800,07+791,26+530,24+10,60+27,39+7,52−9,61−0,42 = **3.157,05** ✓. Resíduo ≠ 0 → warning forte + linha "Outros/Ajuste" para reconciliar.

### 5.4 Extração — CEEE (luz)
- Linhas: `Energia (líquida)`, `CIP`, `Multa`, `Correção`, `Juros`, e `Parcela X/N` (reconcilia, caso 850). **`Energia líquida = total − Σ(demais itens)`**; se der **negativo** (mês de alto crédito solar) → emitir como **`is_offset=True` com magnitude positiva** (respeita `CheckConstraint amount>=0` e a convenção stored-positive-subtracted). Teste com mês de crédito solar.
- Statement: `consumo_kwh`, `energia_injetada_kwh` (solar), `leitura_anterior/atual/dias`, `classe`, `bandeira`.
- Cabeçalho: UC, `competence_month` (do "Conta Mês", **não** emissão/vencimento), `due_date`, total.
- **"FATURA ARRECADADA / NÃO RECEBER"** (2ª via já paga) → detectar marcador e sinalizar no rascunho (warning; o admin decide criar como paga, gerando `Payment`/`PaymentAllocation`, para não virar falso atrasado).

### 5.5 Casamento, idempotência, erros
- **Match:** `BillingAccount` ativa por `account_type` + `external_identifier`/UC; sem match → warning (admin escolhe/cria).
- **Idempotência:** já existe `Bill` ativo para (conta, competência) → warning + caminho de **substituição** via `update_with_lines` (§7), **não** erro de constraint.
- **Fixtures sanitizadas:** os PDFs reais têm CPF/nomes/código de barras → **fixtures = texto extraído sanitizado** (`.txt`/`.json`) com valores sintéticos, fora de qualquer caminho escaneado por GitGuardian. Guard de pré-commit/CI falha em padrão de CPF nas fixtures.

---

## 6. Reconciliação de parcela — passado imutável, atual/futuro ajustável

| Período | O parser faz |
|---|---|
| **Passados** | **Nada.** Nunca toca `Bill`/`BillLineItem`/`Installment` de meses anteriores. "ÚLTIMOS CONSUMOS"/parcelas antigas do PDF são informativos. Guard `CondoMonthClose` bloqueia mês fechado. |
| **Atual** | Linha realizada com o valor lido; a parcela vincula `BillLineItem.installment` ao `Installment` nº X. |
| **Futuros** | `Installment.amount` (schedule/projeção) **re-baselina automaticamente** para o último valor lido (correção monetária), com edição manual via o PATCH de `installments` já existente. Nunca vira histórico. |

Teste pinado: "parse do mês N com parcela de valor diferente NÃO altera bills/linhas/installments dos meses < N; re-baselina N+1..".

---

## 7. Persistência: `create_with_lines` / `update_with_lines`

**Gap central corrigido:** hoje `BillService.create_with_lines` (+ `crud_views.py:323-369`) só aceita `{bill, line_items[description, amount, is_offset, category]}` — **não tem onde gravar a statement nem o vínculo da parcela**. Extensão (refactor real, end-to-end):

1. **`create_with_lines`** aceita opcional `statement` (objeto tipado por `account_type`) e, por linha, `installment_id` (a parcela embutida). `BillService.create_with_lines`:
   - cria `Bill` + `BillLineItem`s; setar `BillLineItem.installment` quando `installment_id` vier;
   - cria o `WaterBillStatement`/`ElectricityBillStatement` 1:1 atomicamente (`@transaction.atomic`, `full_clean()` em tudo).
2. **`update_with_lines`** (novo `@action(detail=True)` + `BillService.update_with_lines` + hook `useUpdateBillWithLines`): substitui linhas + faz upsert da statement, **mantendo o mesmo `Bill` (pk/pagamentos preservados)**, **apenas se UNPAID e mês OPEN** (guard `CondoMonthClose`); pago/fechado → 400 PT ("desfaça o pagamento / reabra o mês primeiro"). É o caminho de correção/re-upload (§5.5).
3. **Soft-delete do bill** (`BillService.delete`/`unpay` correlatos): soft-deletar a statement junto (pois `SoftDeleteMixin.delete()` não percorre relações).
4. Frontend: estender `CreateBillWithLines`/`BillLineInput` (`use-bills.ts`) com `statement` + `installment_id`; idem o payload do modal.

`bill.schema.ts`: aninhar `water_statement`/`electricity_statement` (nullable) no `billSchema` → o `invalidateBillCaches` existente cobre, e o prefill do modal no edit round-trip funciona (sem query-key novo).

---

## 8. Modal "Nova Conta" responsivo + import de fatura

### 8.1 Correção de layout (causa: footer dentro da área rolável)
- Adicionar `DialogBody` (`flex-1 overflow-y-auto`) em `components/ui/dialog.tsx`; `DialogContent` longo passa a `max-h-[90vh] flex flex-col` → **header fixo, corpo rola, footer fixo** (padrão que já existe no `contract-view-modal`). Aplicar ao modal de contas e **alinhar os modais novos do `finances`** (employee, installment-plan, income-entry, billing-account). Legado `financial/*` fora de escopo.
- Confirmado: os testes dos modais irmãos assertam labels/roles/texto/testids, **não** estrutura DOM/className → o refactor não os quebra.
- 100% responsivo: 1 coluna mobile / 2 `sm+`, `w-[calc(100vw-2rem)]`, footer sempre visível.

### 8.2 Campos e blocos
- Renderizar `external_identifier` (Inscrição/UC) e `issue_date` (Emissão) — **já estão no schema e no payload**; é só UI.
- Bloco de statement (água/luz) **condicional ao `account_type`**, normalmente preenchido pelo parser, editável; some em `GENERIC`.
- Botão **"Importar fatura (PDF)"** no bloco `{isAdmin && …}` da página (ao lado de "Nova Conta"); `useParseInvoice` envia `FormData` com `headers: { 'Content-Type': undefined }` (browser seta o boundary multipart). Confirmar que `parse_invoice`/`iptu_alerts` **não** retornam shape `{results,count}` (o interceptor do `client.ts` desempacota). Vitest: não-admin não vê "Nova Conta" nem "Importar fatura".
- **Mapeamento de `behavior`:** fatura de consumo parseada = `behavior=recurring` (parcela é uma linha vinculada); IPTU avulso = `installment` (gerido em Planos de Parcelamento, não neste modal). Trocar o alerta "Fase 3" por link a Planos de Parcelamento e **reescrever** o teste `bill-form-modal.test.tsx:115-126` (assertar o link novo, não deletar).
- **Desambiguação de conta:** os selects de conta renderizam `name — tipo · external_identifier [/ secondary_identifier]` (2 luzes no 836, 2 IPTU no 850). Vitest: duas contas do mesmo tipo → labels distintos.

---

## 9. Alerta de IPTU (banner + push)

### 9.1 `IptuAlertService.evaluate(today_sp())` — read-only, via annotations, sem N+1
Query exata: `InstallmentPlan.objects.filter(lifecycle_state=ACTIVE, embedded=False, billing_account__account_type=IPTU)`. Para cada plano, conta installment-bills vencidas não pagas (`Bill.objects.with_amounts(today_sp())`, `is_overdue`):

| Vencidas | Nível | Mensagem |
|---|---|---|
| 0 | — | sem alerta |
| **1** | **WARNING** | "IPTU [inscrição – prédio]: 1 parcela atrasada (venc. DD/MM). Pague-a este mês junto com a próxima (venc. DD/MM) ou o parcelamento será cancelado." |
| **≥2** | **CRITICAL** | "IPTU [inscrição]: N parcelas atrasadas — parcelamento em risco. Reparcelar na prefeitura." (sem "pague até X") |

- **Deadline** = `due_date` da **primeira parcela ainda não vencida** (na WARNING com parcela 9 vencida + 10 aberta → 30/06). Teste de fronteira: `today==30/06` → parcela 10 não-vencida (`due_date < today` é falso no próprio dia) → ainda WARNING; `01/07` → CRITICAL.
- **`today` sempre via `today_sp()`** (settings é UTC); `with_amounts(today_sp())`. Teste: `evaluate` nunca chamado com data UTC.

### 9.2 Banner (canal load-bearing)
- `GET /api/finances/finance-dashboard/iptu_alerts` (mesmo serviço, DRY) — **UNCACHED** (depende de `today_sp()` + estado de pagamento; a virada de meia-noite não é um write, então cache não invalidaria; igual a `combined_calendar`/`overdue`).
- `IptuRiskBanner` no dashboard de finanças + página de Contas; **agrupado por (prédio, IPTU, inscrição)**, cada termo listado com nº da parcela + venc; contagem reconcilia com os 9 planos ativos.

### 9.3 Push (best-effort) + Notification
- Novo comando `send_finance_alerts` (cron diário, hora SP-safe de manhã; SRP separado de `send_scheduled_notifications`).
- **Agregação obrigatória:** `evaluate` retorna linhas por plano; o comando agrega **TODOS** os WARNINGs num **único** resumo/admin (e CRITICALs idem / combinado), enumerando as inscrições em risco. (Loop por-plano + idempotência por `(user,type)` derrubaria 8 dos 9.)
- **Idempotência SP-aware:** adicionar `is_notification_sent_on(user, type, day)` (recebe `today_sp()`) — **não** reusar o `is_notification_sent_today` (UTC).
- **Tipos novos** em `core/models.py Notification.TYPE_CHOICES` como **constantes nomeadas** (`Notification.TYPE_IPTU_OVERDUE_RISK = "iptu_overdue_risk"`, `TYPE_IPTU_PARCELAMENTO_LOST = "iptu_parcelamento_lost"`) + migração `AlterField` (no-op SQL, obrigatória). `finances` importa as constantes (sem magic string); idempotência usa a mesma constante.
- **Destinatários:** `User.objects.filter(is_staff=True, is_active=True)` (padrão `notify_new_proof`). **Push é best-effort** (o admin pode não ter `DeviceToken` Expo / Web Push) → o **banner + a Notification in-app são o canal garantido**. Cadência: WARNING re-notifica no máximo 1×/N dias enquanto não resolvido (banner sempre visível); CRITICAL notifica na transição (tipos independentes → escalada nunca suprimida). Fallback de e-mail para CRITICAL = futuro (§16).

---

## 10. Invariantes financeiras afetadas

### 10.1 Competência das parcelas do estado inicial (decisão #8)
Parcelas em aberto/atrasadas existentes entram no seed com `competence_month = primeiro mês rastreado (2026-06-01)`, `due_date` real preservado (parcela 9 venc 29/05 → overdue; parcela 10 venc 30/06 → aberta). Assim: aparecem como atrasadas (Atrasados é agnóstico a competência) e **não** criam mês pré-tracking com net negativo espúrio (o `_expense_competence` não recebe competência pré-2026-06). De julho em diante, `generate_month` usa a competência natural. *(Nota: `due_date < competence_month` é permitido — representa obrigação de abertura; não há constraint contrária; o calendário agrupa por `due_date`, então a parcela 9 aparece em Atrasados, não no calendário de junho.)*

### 10.2 `convert_deferred` herda `billing_account` (decisão crítica)
`convert_deferred` copia `plan.billing_account = locked.billing_account` (a conta IPTU da dívida diferida) e asserta `account_type == IPTU`. Sem isso, as 3 dívidas 2026 reparceladas ficariam invisíveis ao `IptuAlertService` (o caso de alerta mais importante). Teste: `convert_deferred(dívida IPTU)` → `plan.billing_account == conta IPTU` **e** o alerta a enxerga.

### 10.3 Exclusão de IPTU só no ramo recorrente
Predicado único compartilhado `BillingAccount.objects.recurring_for_generation()` (exclui `account_type=IPTU`) usado por `BillGenerationService` + `condo_projection_service` + `condo_calendar_service`. As parcelas **avulsas** de IPTU (ramo standalone) **nunca** são excluídas (continuam gerando 1 bill/parcela/mês e entram na projeção). Teste: conta IPTU → 0 bills recorrentes; plano avulso → bills de parcela; geração == projeção ao centavo.

### 10.4 Diferidos fora de todas as somas
As 3 dívidas 2026 diferidas (`lifecycle_state=DEFERRED`) são excluídas de competência/caixa/atrasados pelo filtro `==ACTIVE` já existente; cada uma carrega **1 `BillLineItem`** do valor da dívida (senão `convert_deferred` → plano R$0). Testes: as 3 não aparecem em result/cash/overdue; `convert_deferred` → total exato.

### 10.5 Atrasados inclui IPTU (drill-down)
O KPI "Atrasados" soma todas as contas a pagar vencidas (inclui as 9 parcelas de IPTU); o `IptuRiskBanner` é **drill-down de risco** (perda do parcelamento), não um segundo total. Copy do dashboard deixa isso claro (sem dupla contagem visual).

---

## 11. Cache & signals
- Statements aninhadas no `BillSerializer`/`bill.schema.ts` → `invalidateBillCaches`/signals `finance-*` já cobrem. Adicionar receivers `post_save`/`post_delete` para `WaterBillStatement`/`ElectricityBillStatement` invalidando `finance-*` (consistência do detalhe do bill).
- `iptu_alerts` e `combined_calendar`/`overdue` = **uncached** (sensíveis a tempo/estado).

## 12. Migrações & RLS
- **Ordem:** (1) AddField `BillingAccount.account_type` + campos de identidade + `supply_status` + unique identity; (2) `RenameField InstallmentPlan.linked_billing_account → billing_account` + clean cross-model; (3) `WaterBillStatement` + `ElectricityBillStatement` (**RLS na mesma migração**, padrão `0047`); (4) `core` `AlterField Notification.type` (choices novos).
- **Backfill `account_type`:** verificar contagem de `BillingAccount` (o módulo subiu "sem seed" → provavelmente 0 linhas; default GENERIC inócuo). O seed usa `update_or_create` para tipar linhas existentes. Se houver linhas, data-migration tipando por `external_identifier`/`name`.
- Backup antes (`python scripts/backup_db.py`); testar forward/backward; `rolbypassrls` mantém o backend imune ao RLS.

## 13. Seed dos dados reais
- `scripts/data/condo_utilities_seed.json` + comando idempotente `python manage.py seed_condo_utilities` (`--dry-run`; `get_or_create`/`update_or_create` por chaves naturais: inscrição/UC/termo).
- Cria: contas tipadas (água/luz/IPTU por prédio com identidade), planos embutidos (água 836/850, luz 850) e avulsos (IPTU), as 3 dívidas 2026 como `Bill(deferred)` **com `BillLineItem`**, e gera as parcelas em aberto/atrasadas **com `competence_month=2026-06`** (§10.1) para aparecerem + disparar o alerta. **Não** backfilla parcelas pagas pré-tracking.
- A confirmar no seed (não chutar): status pago/não-pago de maio/junho de cada conta e o mês de origem de cada plano embutido (alinhar o nº da parcela atual).
- Ordem: **local primeiro** → validar → commit/PR/deploy → **prod por último** (backup `pg_dump`, migrações + seed, advisor de segurança sem `rls_disabled`).

## 14. Faseamento + gate por fase
Cada fase é TDD; só fecha com **≥90% em `finances`, `ruff check && ruff format --check && mypy core/ finances/ && pyright && pytest`, zero erros e zero warnings**, edge-cases (Apêndice B) cobertos, incluindo polish.

1. **Tipo + identidade** (`account_type`, campos, unique, `recurring_for_generation()` excluindo IPTU em geração/projeção/calendário).
2. **Refactor `billing_account`** (rename + clean cross-model + `serializer.validate` + checklist §4 + `convert_deferred` herda conta).
3. **Statements** (`WaterBillStatement`/`ElectricityBillStatement` readings-only + `create_with_lines`/`update_with_lines` estendidos + soft-delete cascade + nested serializer + RLS).
4. **Parser** (`invoice_parsing`, DMAE+CEEE posicional, `parse_invoice` MultiPartParser, reconciliação §6, invariantes §5, deps/mypy, fixtures sanitizadas).
5. **Alerta IPTU** (`IptuAlertService`, `iptu_alerts` uncached, banner, `send_finance_alerts` agregado+SP-aware, `Notification` types/constantes + migração core, push best-effort).
6. **Modal/UI** (`DialogBody`, responsivo, campos, statement condicional, "Importar fatura", `useParseInvoice` multipart, mapeamento behavior, desambiguação, alinhar modais irmãos).
7. **Seed** local → prod (após deploy).

Dependências: 1 → 2 → 3 → 4 → 5 → 6 → 7 (4 precisa de 1+2+3; 5 precisa de 1+2; 6 precisa de 1–4).

## 15. Segurança / permissões
- `parse_invoice` / `update_with_lines` / `seed`: `is_staff` (write gate `FinancialReadOnly`); banner endpoint = autenticado lê.
- Validar PDF de verdade no upload; **sem armazenar** o arquivo. Fixtures sanitizadas (sem CPF real) + guard de CPF no CI.
- Tabelas novas com RLS habilitada (deny-all à Data API; backend bypassa via `postgres`).

## 16. Fora de escopo (YAGNI)
- Armazenamento durável de anexos (Supabase Storage/django-storages) — futuro (serviria contratos; conserta também o bug latente de durabilidade do `PaymentProof`).
- Fallback de e-mail para alerta CRITICAL; OCR (faturas escaneadas); parser de IPTU (manual/parcelamento); multi-condomínio; regra de risco genérica para qualquer parcelamento (hoje só IPTU).

---

## Apêndice A — inventário real das contas

> Para não reenviar os PDFs. Valores/nº de parcela conforme as faturas de Maio/Junho/2026 e o extrato de parcelamentos da prefeitura.

**Prédio 836** *(cadastrado «Av Circular 828» no DMAE/IPTU)*
- Água DMAE — `account_type=WATER`, inscrição `117.111.0049.0519.00`, imóvel `003419142`, `supply_status=CUT` (água cortada, esgoto ligado), `due_day≈4`. Parcela **embutida 46×** ~R$94,48 (atual 24). Reparcelamento iminente (novo plano embutido quando ocorrer; o atual encerra).
- Luz principal (840, solar) — `ELECTRICITY`, UC `1.273.798.010-05`, medidor MD50721985, classe Residencial Pleno, titular RAUL. Sem parcela. 05/2026 R$921,49 (não paga).
- Luz 2º relógio (836, tarifa social) — `ELECTRICITY`, UC `650.847.010-16`, medidor MD33457946, Baixa Renda, titular RAUL. Sem parcela. 05/2026 R$97,62 (não paga).
- IPTU — `IPTU`, inscrição `516449`, titular RAUL. Dívida 2026 lançamento `202600179949` R$10.308,70 (→ deferred). **4 termos** avulsos (10× cada): `992988` (saldo 27.181,69), `992989` (20.669,56), `992990` (15.036,95), `992991` (98,37). Cada: parcela 9 Em Atraso (29/05) + 10 Em Aberto (30/06).

**Prédio 850** *(cadastrado «Av Circular 838» no DMAE; IPTU «Casa 1/Casa 2»)*
- Água DMAE — `WATER`, inscrição `117.111.0049.0508.00`, imóvel `000463540`, ligada, `due_day=4`. Parcela **embutida 59×** R$530,24 (atual 3).
- Luz (solar) — `ELECTRICITY`, UC `1.273.678.010-60`, medidor MD50722005, Residencial Pleno, titular CELIA. Parcela **embutida 24×** R$629,35 (atual 19). 05/2026 R$990,80.
- IPTU Casa 1 (2 kitnets) — `IPTU`, inscrição `516481`, titular PRANAS BIELAVICIUS. Dívida 2026 `202600179981` R$682,39 (→ deferred). **1 termo** `992269` (10×; 9 atraso R$136,05 / 10 aberto R$137,31).
- IPTU Casa 2 (fundos + casa) — `IPTU`, inscrição `516503`, titular PRANAS BIELAVICIUS. Dívida 2026 `202600179990` R$6.741,33 (→ deferred). **4 termos**: `1075071` (2021, 56×, 4.868,12), `1075073` (2021, 56×, 7.712,87), `992967` (2025, 10×, 11.932,12), `992968` (2025, 10×, 13.409,87). Cada: parcela 55/9 atraso (29/05) + 56/10 aberto (30/06).

**Totais:** 9 planos de IPTU ativos + 3 dívidas 2026 a parcelar → **9 alertas WARNING** no estado atual (1 atrasada cada). `FinancialSettings`: `initial_balance=0` (2026-03-01), `rent_tracking_start_date=2026-06-01`.

**Estado de pagamento (a confirmar no seed):** luz paga até Maio (Junho não); água 850 — Junho informada como paga; água 836 não paga (cortada, aguardando reparcelamento no DMAE).

---

## Apêndice B — edge-cases por fase (testes RED)

- **Fase 1:** 4 contas reais do mesmo tipo coexistem (2 luz/836, 2 IPTU/850); duplicata ativa rejeitada, soft-deletada permitida; `external_identifier` em branco rejeitado p/ tipo água/luz/IPTU; conta IPTU gera 0 recorrentes; geração==projeção==calendário no predicado compartilhado.
- **Fase 2:** `grep linked_billing_account` = 0; cada `select_related` string executa sem `FieldError`; `embedded=True` exige conta de consumo (clean + serializer.validate); `convert_deferred` herda `billing_account` IPTU.
- **Fase 3:** create_with_lines grava statement + `line.installment`; update_with_lines substitui linhas só em UNPAID+OPEN, rejeita pago/fechado; soft-delete do bill esconde a statement; bill escondido não expõe statement viva.
- **Fase 4:** soma==total (DMAE c/ `TAXA COBRANCA`); energia líquida negativa → linha offset; "ARRECADADA" sinalizada; parcela sem plano → linha genérica + warning; competência por emissor `.replace(day=1)`; multipart sem boundary → 400; cada campo de statement por variante CEEE; parse do mês N não altera meses < N.
- **Fase 5:** 9 planos → 1 resumo/admin (não 1); idempotência SP-aware (virada de meia-noite); `iptu_alerts` reflete pagamento sem cache stale; fronteira 30/06 WARNING vs 01/07 CRITICAL; tipos em `TYPE_CHOICES`; deadline = 1ª parcela não-vencida; push no-op (sem DeviceToken) não derruba banner/in-app.
- **Fase 6:** footer fixo/visível em mobile/tablet/desktop; modais irmãos intactos; "Importar fatura" só admin; selects desambiguam 2 luzes/2 IPTU; teste "Fase 3" reescrito p/ link Planos de Parcelamento; prefill da statement round-trip no edit.
- **Fase 7:** seed idempotente (rerun não duplica); parcelas de abertura com competência 2026-06 (sem net negativo pré-tracking); dívidas diferidas fora de result/cash/overdue + `convert_deferred` com total exato; advisor prod sem `rls_disabled`.
