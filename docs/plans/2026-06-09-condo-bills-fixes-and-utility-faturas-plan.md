# Plano — Correções e melhorias do módulo de Contas de Condomínio

**Data:** 2026-06-09
**Escopo:** corrigir os valores de parcela do IPTU em prod+local, resolver a página "Parcelas" vazia + edição de parcela, redesenhar a lista de "Contas" (por prédio, sem paginação, coluna "Tipo"), popular/permitir criar Categorias, e inserir as faturas mensais reais de água (DMAE) e luz (CEEE).
**Estado:** EM REVISÃO — não executar antes da aprovação. Toda alteração em prod segue backup-first (URI em `db.txt`, apagar após).
**Investigação base:** workflow de 4 lentes (parcelas-empty / value-fix / contas-redesign / categoria) + subagent água/luz (relatórios no transcript da sessão).

---

## 0. Princípios (obrigatórios)

SOLID/DRY/KISS/YAGNI, Clean Code. Sem `# noqa`/`# type: ignore`/`eslint-disable`, sem `from __future__`/`TYPE_CHECKING`, sem re-exports, refatoração completa (todos os consumidores). Gate por fase: `ruff check && ruff format --check && mypy core/ && pyright && pytest` (backend, escopo finances) e `npm run lint && npm run type-check && npm run test:unit` (frontend). Backup antes de qualquer migrate/escrita destrutiva. RLS permanece habilitado.

---

## 1. Tabelas de dados (verificar antes de inserir)

### 1.1 IPTU — valores corretos = **"atualizado"** (confirmado pelo usuário)

`SET` = valor a gravar (Installment.amount **e** BillLineItem.amount). `ERA` = semeado errado (saldo÷count).

| Termo | Prédio / Inscrição | Parc. | Venc. | ERA (errado) | **SET (atualizado)** | plano total_amount (SET) |
|---|---|---|---|---|---|---|
| 992988 | 836 / 516449 | 9 | 29/05 | 2.718,16 | **522,72** | **1.045,44** |
| 992988 | 836 / 516449 | 10 | 30/06 | 2.718,25 | **522,72** | |
| 992989 | 836 / 516449 | 9 | 29/05 | 2.066,95 | **397,49** | **794,98** |
| 992989 | 836 / 516449 | 10 | 30/06 | 2.067,01 | **397,49** | |
| 992990 | 836 / 516449 | 9 | 29/05 | 1.503,69 | **289,17** | **578,34** |
| 992990 | 836 / 516449 | 10 | 30/06 | 1.503,74 | **289,17** | |
| 992991 | 836 / 516449 | 9 | 29/05 | 9,83 | **49,15** | **98,37** |
| 992991 | 836 / 516449 | 10 | 30/06 | 9,90 | **49,22** | |
| 992269 | 850 C1 / 516481 | 9 | 29/05 | 136,05 | **137,31** | **274,62** |
| 992269 | 850 C1 / 516481 | 10 | 30/06 | 137,31 | **137,31** | |
| 992967 | 850 C2 / 516503 | 9 | 29/05 | 1.193,21 | **229,46** | **458,92** |
| 992967 | 850 C2 / 516503 | 10 | 30/06 | 1.193,23 | **229,46** | |
| 992968 | 850 C2 / 516503 | 9 | 29/05 | 1.340,98 | **257,88** | **515,76** |
| 992968 | 850 C2 / 516503 | 10 | 30/06 | 1.341,05 | **257,88** | |
| 1075071 | 850 C2 / 516503 | 55 | 29/05 | 86,93 | **162,25** | **324,50** |
| 1075071 | 850 C2 / 516503 | 56 | 30/06 | 86,97 | **162,25** | |
| 1075073 | 850 C2 / 516503 | 55 | 29/05 | 137,72 | **257,06** | **514,12** |
| 1075073 | 850 C2 / 516503 | 56 | 30/06 | 138,27 | **257,06** | |

> Nota: sob a regra "atualizado", a parcela atrasada (9/55) recebe o valor atualizado e a aberta (10/56) o seu (lançado=atualizado). 17 das 18 parcelas mudam (só 992269/10 já estava certo). Dívidas diferidas (202600179949 = 10.308,70 / 202600179981 = 682,39 / 202600179990 = 6.741,33) estão **corretas** — fora de escopo.

### 1.2 Água/Luz — faturas mensais a inserir

Parcelas embutidas já semeadas com valores corretos: **água 836 = 94,48 (46x)**, **água 850 = 530,24 (59x)**, **luz 850 = 629,35 (24x)**.

**A) Luz principal 840 (solar) — UC 1.273.798.010-05 (electricity)**

| Comp | Venc | Total | Consumo | Injetada | Leitura | Obs |
|---|---|---|---|---|---|---|
| 04/2026 | 04/05/2026 | 1.106,40 | 2.054 kWh | 1.290 | 24/03→24/04 | ARRECADADA (paga) |
| 05/2026 | 16/06/2026 | 921,49 | 1.752 kWh | 1.172 | 24/04→25/05 | passível a corte |

Linhas (05/2026): Consumo TE 250,23 · Consumo TU 348,80 · Cons. Comp TE 81,52 · Cons. Comp TU 704,82 · Inj. TE −81,52 (offset) · Inj. TU −585,00 (offset) · Par.S/Des.GD2 137,35 · Ben.Tarif.Bruto SCEE TUSD 447,65 · Ben.Tarif.Bruto SCEE TE 67,66 · Adic. Bandeira 11,07 · Cip-Ilum 10,97 · Benef.Tarif.Líquido SCEE −494,12 (offset) · Multa 9,67 · Correção 5,78 · Juros 6,61. **Sem parcelamento.**

**B) Luz 2º relógio 836 (tarifa social) — UC 650.847.010-16 (electricity)**

| Comp | Venc | Total | Consumo | Leitura | Obs |
|---|---|---|---|---|---|
| 04/2026 | 04/05/2026 | 157,35 | 269 kWh | 24/03→24/04 | ARRECADADA |
| 05/2026 | 01/06/2026 | 97,62 | 189 kWh | 24/04→25/05 | passível a corte |

Linhas (05/2026): Consumo TE 42,03 · Consumo TUSD 45,97 · Ben.Tarif.Bruto TE 25,77 · Ben.Tarif.Bruto TUSD 26,86 · Adic. Bandeira 2,07 · Benef.Tarif.Líquido −52,63 (offset) · Multa 3,31 · Correção 1,98 · Juros 2,26. **Sem parcelamento.**

**C) Luz 850 (solar) — UC 1.273.678.010-60 (electricity)**

| Comp | Venc | Total | Consumo | Injetada | Leitura |
|---|---|---|---|---|---|
| 05/2026 | 16/06/2026 | 990,80 | 1.726 kWh | 1.405 | 24/04→25/05 |

Linhas: energia (TE/TU + comp + injeção, líquida) · Adic. Bandeira 1,90 · **Parcela 19/24 = 629,35** (embutida ✅) · Multa 34,92 · Correção 11,95 · Rel. Normal DJ 14,09 · Juros 18,13 · Cip-Ilum.

**D) Água DMAE 836 — Inscrição 117.111.0049.0519.00 (water)**

| Comp | Venc | Total | Consumo | Leitura | Água |
|---|---|---|---|---|---|
| 05/2026 | 04/06/2026 | 1.286,95 | 51 m³ | 619→670 | LIGADO |
| 06/2026 | 04/07/2026 | 1.319,13 | 13 m³ | 670→683 | **CORTADO** |

05/2026: Água 660,00 · Esgoto 528,00 · **Parcela 23/46 = 94,48** ⚠️(materializar) · Multa 2,31 · Juros 1,88 · Atualiz. 0,28
06/2026: Água 660,00 · Esgoto 528,00 · **Parcela 24/46 = 94,48** ✅ · Taxa Cobrança 6,50 · Multa 27,99 · Juros 1,88 · Atualiz. 0,28

**E) Água DMAE 850 — Inscrição 117.111.0049.0508.00 (water)**

| Comp | Venc | Total | Consumo | Leitura |
|---|---|---|---|---|
| 05/2026 | 04/06/2026 | 3.157,05 | 158 m³ | 2731→2889 |
| 06/2026 | 04/07/2026 | 3.570,96 | 177 m³ | 2889→3066 |

05/2026: Água 1.800,07 · Esgoto 791,26 · **Parcela 2/59 = 530,24** ⚠️(materializar) · Multa 10,60 · Juros 27,39 · Atualiz. 7,52 · Desc. Acrés.Impon −9,61 (offset) · Desc. Débito Tipo −0,42 (offset)
06/2026: Água 2.118,83 · Esgoto 886,41 · **Parcela 3/59 = 530,24** ✅ · Multa 10,60 · Juros 27,39 · Atualiz. 7,52 · Descontos −9,61 / −0,42 (offsets)

---

## 2. Fase 1 — Correção dos valores do IPTU (dados + seed)

**Causa-raiz:** `_seed_iptu_terms` lê `current_amount`/`next_amount` verbatim do JSON (`seed_condo_utilities.py:294,302`); no JSON esses valores foram `saldo÷count`. A tela mostra `Σ BillLineItem.amount` (`models.py:229-268`), e a Bill de parcela tem **uma** linha copiada de `Installment.amount` na geração (`models.py:559-566`). Logo, corrigir só a `Installment.amount` NÃO muda a tela nem a fatura já gerada — é preciso tocar **Installment.amount + a BillLineItem da Bill gerada + plan.total_amount**.

**Passos:**
1. **Comando idempotente** `finances/management/commands/fix_iptu_parcela_amounts.py` (one-off, mas idempotente e com `--dry-run`):
   - Para cada termo+parcela da tabela 1.1: `Installment.amount = SET`; buscar a Bill via `Bill.objects.filter(installment=inst)` (NÃO `billing_account`, que é `None`); `bill.line_items` único → `amount = SET`; setar `plan.total_amount` uma vez por termo.
   - **Guarda de pagamento:** pular/abortar para qualquer Bill com `PaymentAllocation` não-deletada (hoje as 18 estão `active`/`paid=0`, mas mudar a linha sob uma alocação dessincronizaria `amount_paid`/`payment_status`). Defensivo, documentar a invariante.
   - `transaction.atomic()` + `full_clean()` em cada objeto; idempotente (re-rodar não muda nada); `--dry-run` via `set_rollback(True)`.
   - NÃO usar `update_with_lines` (tem guards e não seta `Bill.installment`).
   - **`total_amount` (semântica):** o `SET` da tabela 1.1 é o **saldo restante das 2 parcelas materializadas** (ex.: 992988 = 522,72×2 = 1.045,44), consistente com a convenção já aceita do 992269; o `installment_count` permanece 10/56 (não muda). Em prod isso **reduz** vários totais de plano (~26×) — esperado, não é bug.
2. **Corrigir o seed** `scripts/data/condo_utilities_seed.json`: trocar `current_amount`/`next_amount` dos 9 termos para os valores "atualizado" da tabela 1.1 + `total_amount` correto; atualizar `_premissas`.
3. **Testes + doc:** corrigir fixtures em `tests/unit/test_finances/test_seed_condo_utilities.py` (termos 992988, 992991, `overdue_total` linha ~369) + adicionar regressão sobre `BillLineItem.amount`; corrigir `docs/plans/2026-06-08-...-design.md` Apêndice A.
4. **Aplicar:** local (backup `python scripts/backup_db.py` → comando → verificar) → prod (backup `pg_dump` via `db.txt` → comando → **invalidar cache Redis** (ver §7) → verificar via MCP → apagar `db.txt`).

> O total de 9 alertas WARNING de IPTU é dirigido por "vencidas", não pelo valor — permanece 9 após a correção.
> **Cache:** `with_amounts` deriva o total ao vivo da `BillLineItem` (sem passo extra), mas o dashboard/projeção tem cache Redis (TTL 300s, invalidado por signals). O comando one-off roda com LocMem (evita Redis local) → **não invalida o Redis de prod**; tratar no §7.

---

## 3. Fase 2 — Página "Parcelas" vazia + edição de parcela ✅ CORRIGIDO (frontend; falta deploy)

**Causa-raiz (CONFIRMADA pelos logs do Render + payload real):** a API retorna os 12 planos corretamente (200, `count: 12`), mas o `superRefine` de `installmentPlanSchema` exigia `billing_account_id` para planos `embedded`. Na **leitura**, o serializer emite `billing_account` (aninhado) e **NÃO** `billing_account_id` (write_only) → para os 3 planos embutidos, `billing_account_id === undefined` → o `parse` **lança** → o `.map(installmentPlanSchema.parse)` da `queryFn` derruba a query inteira → `data=undefined` → "Nenhum plano" (e as **4 chamadas** vistas no Network = retry default ×3+1 do TanStack numa `queryFn` que rejeita). O erro `sw.js` "no-response" era um segundo sintoma (service worker do PWA), separado e transitório.

**Correção aplicada (gate verde: 11 testes, type-check, lint):**
1. `frontend/lib/schemas/finances/installment-plan.schema.ts` — `superRefine` agora aceita **`billing_account_id` (write) OU `billing_account` aninhado (read)**; só falha se ambos ausentes. Mantém a validação do form (que envia `billing_account_id`) e para de rejeitar a leitura.
2. `frontend/app/(dashboard)/finances/installment-plans/page.tsx` — ramo `isError` distinto do vazio (usa `getErrorMessage`), para que uma falha futura apareça como erro, nunca como "Nenhum plano" silencioso.
3. **Testes** (22 verdes): `use-installment-plans.test.tsx` — regressão do payload embedded de leitura; `lib/schemas/finances/__tests__/installment-plan.schema.test.ts` (novo) — casos positivos (read nested-only / write id-only) **e negativo** (embedded sem nenhum dos dois → `ZodError` em `billing_account_id`), fixando a guarda contra erosão futura; `installment-plans-page.test.tsx` — novo teste do ramo `isError` (mock parametrizado: `isError:true` → mostra erro, NÃO o vazio).

**Falta:** deploy do frontend (Vercel) para a correção valer em prod — **não há escrita em banco**. (Optei por NÃO usar `safeParse`-descarta-linha: silenciar linha ruim viola "no silent failures"; o ramo `isError` é a forma honesta de surfacing. Ressalva conhecida (baixa): um `ZodError` em qualquer outro campo ainda derruba a lista inteira e o `getErrorMessage` mostra o dump cru do Zod — o padrão `.map(parse)` por-linha persiste; fora de escopo deste fix.)

**Edição de parcela:** já funcionava ponta-a-ponta (`InstallmentViewSet` PATCH `amount`/`due_date` + Sheet "Cronograma" inline). Com a lista voltando a aparecer, a edição fica acessível pelo dropdown da linha. (Nota: editar `Installment.amount` **não** recalcula `plan.total_amount` — por design; o total se edita pela modal do plano.)

---

## 4. Fase 3 — Lista de "Contas" por prédio, sem paginação, coluna "Tipo"

**Estado atual:** uma única `DataTable` plana + filtros globais (prédio, situação); sem agrupamento. `BillViewSet` usa `CustomPageNumberPagination` com `max_page_size=500` (corta `page_size=10000` silenciosamente).

**Backend:**
1. `finances/serializers.py` `BillSerializer`: importar `BillingAccountType` de `finances.models`; adicionar `account_type = SerializerMethodField()` + `get_account_type(self, obj) -> str` = `obj.billing_account.account_type` senão `obj.installment.plan.billing_account.account_type` (quando `installment` e `plan.billing_account`) senão `BillingAccountType.GENERIC`; adicionar `'account_type'` em `Meta.fields`. (Serializer lê models, nunca services.)
2. `finances/viewsets/crud_views.py` `BillViewSet.get_queryset`: adicionar `'installment__plan__billing_account'` ao `select_related` (evita N+1 no caminho IPTU-parcela).
3. `BillViewSet`: `pagination_class = None` (retorna lista crua; `extractResults` já trata array) — para realmente "mostrar tudo".

**Frontend:**
4. `frontend/lib/schemas/finances/bill.schema.ts`: adicionar `account_type: billingAccountTypeEnum.optional()` (importar de `billing-account.schema`).
5. `bill-columns.tsx`: nova coluna "Tipo" usando `ACCOUNT_TYPE_LABELS[record.account_type ?? 'generic']` (reuso do mapa existente em `billing-account.schema.ts:51-57` — DRY; o `?? 'generic'` satisfaz `noUncheckedIndexedAccess`). Colocar após "Prédio".
6. `bills/page.tsx`: refatorar espelhando `leases/page.tsx`/`apartments/page.tsx` — `useBills()` busca todas (remover filtro `building_id` server-side), agrupar num `Map<number|null, Bill[]>` por `bill.building?.id` via `useMemo`, `<Accordion type="multiple">` com um `<AccordionItem>` + `<DataTable pagination={false}>` por prédio **+ um item "Condomínio" para `building==null`** (balde extra que Locações/Apartamentos não têm). `Badge` com contagem por grupo. Manter o filtro de **situação** (global, acima do accordion — KISS).
7. **Testes:** o `bills-page.test.tsx` existente valida a tabela plana ("Condomínio"/empty state) → precisa ser reescrito para o accordion (enumerar no gate, não só "rodar verde").

> **Acoplamento de deploy:** a coluna "Tipo" (frontend) só funciona com o campo `account_type` (backend) no ar — Fase 3 frontend e backend **devem ir no mesmo deploy** (senão "Tipo" fica sempre "Genérica"). `useBills` NÃO lê o envelope paginado, então `pagination_class=None` é seguro (verificado). A cadeia de `account_type` cobre as 3 dívidas diferidas (têm `billing_account`) e as parcelas (têm `installment`).

---

## 5. Fase 4 — Categoria (dropdown vazio) + Tipo vs Categoria

**Causa-raiz:** existem **ZERO** linhas `finances.Category` (o seed nunca cria; nenhuma migration semeia; **não há UI para criar**). O hook de **leitura** `useFinanceCategories` É usado (dropdowns de contas/receitas/parcelas) — só os hooks **`useCreateFinanceCategory`/Update/Delete** são órfãos. A "Categorias" do menu é a **legada** `ExpenseCategory` (`/financial/categories`) — tabela diferente. `account_type` (Água/Luz/IPTU/Internet/Genérica) é o **Tipo** estrutural (parser/statements/geração/unicidade); `Categoria` é uma tag **opcional, data-driven, por condomínio** — conceitos ortogonais; não duplicar `account_type` em Categoria.

**Passos:**
1. **Serializer:** `CategorySerializer` — adicionar `condominium_id` `required=False` **E** um método `validate()` que chama `_apply_default_condominium` (`serializers.py:48-61`; o helper só roda dentro de `validate()`, como em Reserve/IncomeEntry/Bill). Hoje `condominium_id` é obrigatório e não há `validate()` → POST sem ele dá 400.
2. **Seed inicial:** `_seed_categories(data)` + array `categorias` no JSON, criando raízes via `update_or_create` em `(condominium, parent, name)` escopadas a `Condominium.get_default()`. Conjunto: **Serviços/Utilidades, Impostos, Manutenção, Pessoal/Folha, Outros**. Rodar local + prod. (Tabela `finances_category` já existe e já tem RLS — sem migration.)
3. **Página de Categorias** sob o grupo "Condomínio": **nova** `FinanceCategoryFormModal` (campos `name`/`color`/`sort_order`/`parent` — NÃO reusar a `CategoryFormModal` legada, que é de `ExpenseCategory` com `description`/`subcategories`) + página no padrão `useCrudPage` + `DataTable` + `DeleteConfirmDialog`, ligada aos hooks `useFinanceCategories`/Create/Update/Delete (ativa os 3 órfãos — sem dead code). Adicionar `ROUTES.FINANCES_CATEGORIES = '/finances/categories'` (path da página Next; a rota da API é `/finances/finance-categories/`) + entrada no `condominioChildren` (`sidebar.tsx`).
4. **(Opcional)** "+ Nova categoria" inline na modal de Conta + `FormDescription` esclarecendo que Categoria ≠ Tipo de conta.

---

## 6. Fase 5 — Faturas mensais de água/luz

**Estado:** contas (5) e parcelamentos embutidos (3) semeados; **faltam as faturas mensais reais**. Os parsers (DMAE/CEEE) são frágeis a acentos e o CEEE **colapsa** as linhas de energia numa só — caminho confiável = **semear via `create_with_lines`** (reproduzível, preserva o detalhe transcrito). ⚠️ `create_with_lines` **NÃO é idempotente** (ver passo 3).

**Passos:**
1. **Corrigir o OFF-BY-ONE das parcelas embutidas de água (REAL — confirmado pelos PDFs DMAE).** O seed fixou `number == current_installment` no venc 04/06 (primeiro ciclo), mas os PDFs reais dizem: **água 836** — comp 05 (venc 04/06) = **parcela 23/46**, comp 06 (venc 04/07) = 24/46; **água 850** — comp 05 (venc 04/06) = **parcela 2/59**, comp 06 (venc 04/07) = 3/59. Em prod estão gravadas como 24@04/06 e 3@04/06 (+1). Os **vencimentos estão certos; só os números estão +1**. `luz 850` (parcela 19 @ ciclo de junho) está **correta** — não mexer.
   - **Correção:** (a) JSON `current_installment` água 836 **24→23**, água 850 **3→2** + corrigir o design doc Apêndice A (`atual 24→23`, `atual 3→2`); (b) em prod/local, **re-materializar** as installments embutidas de água (deletar as existentes dos 2 planos + recriar a partir do `current` corrigido): água 836 → **23..46** (24 parcelas), água 850 → **2..59** (58 parcelas), vencimentos mensais a partir de 04/06/2026.
   - **Seguro:** nenhuma Bill referencia essas installments embutidas (o seed só cria Bill para IPTU/diferidas — verificado); asseverar `Bill.all_objects.filter(installment__plan=<plano água>)` vazio antes de re-materializar. Migration guarded/idempotente (skip se `min(number)` já == 23/2).
2. **Venc da água = dia 4 do mês SEGUINTE (decisão):** água é **entrada por seed/manual** (venc explícito da fatura); `BillGenerationService` **não deve auto-gerar** contas de água (o `_due_date_for` clamparia no mês errado). Documentar/garantir que `generate_month` não materializa contas de água (ou só luz). Sem mudança de geração neste plano.
3. **Semear as 7 faturas com venc 06/07** (`_seed_monthly_utility_bills` + seção `faturas_mensais` no JSON): para cada (conta, competência), **detectar Bill existente** (`Bill.all_objects.filter(billing_account=, competence_month=, is_deleted=False).exists()` → pular ou `update_with_lines`) ANTES de chamar `create_with_lines` — **não** confiar em idempotência do `create_with_lines` (ele estoura `_ERR_BILL_ALREADY_EXISTS` no re-run); espelhar o padrão do `_seed_opening_parcela`. Linhas da tabela 1.2 + readings no statement (water: consumo_m3/leitura/dias/status; electricity: consumo_kwh/injetada/leitura/classe/bandeira); negativas (injeção/benefício/descontos) como `is_offset=True` (amount positivo). **Vincular a linha de parcela à sua `Installment`** (`installment=`) para que o dedup `(bill, installment)` da geração futura não duplique. **Escopo:** luz 840 (comp 05/venc 16-06), luz 836 social (comp 05/venc 01-06), luz 850 (comp 05/venc 16-06), água 836 (comp 05 + 06), água 850 (comp 05 + 06). Abril NÃO entra. Rodar local + prod.
4. **expected_amount (projeção, decisão):** definir `expected_amount` das contas de água (~1.300 água 836 / ~3.500 água 850) para visibilidade na projeção de meses futuros (hoje 0 → invisível). Luzes já têm `expected_amount`. (Valor é só estimativa de projeção; a fatura real prevalece no mês corrente.)

---

## 7. Fase 6 — Atualização de prod + verificação

**Pré-condições (verificadas hoje):** **0** linhas `CondoMonthClose` em prod → nenhum fechamento congelou os valores errados. Se algum mês contendo competência 2026-06 for **fechado antes** da Fase 1, reabrir+refechar após a correção (o snapshot congela `net_result`/`breakdown` com os valores das bills). **Sem migrations / sem tabela nova / sem mudança de RLS** em nenhuma fase (verificado: `account_type` é `SerializerMethodField`, Categoria usa tabela existente, Fases 1/5 são escrita de dados) — **não rodar `makemigrations`**.

Para cada fase com escrita em prod (1, 4-seed, 5-seed):
1. **Backup:** `pg_dump "<uri de db.txt>" --schema=public --no-owner --no-acl -Fc > backups/backup_PROD_<ts>.dump` (ou `.sql`).
2. **Aplicar:** rodar o comando/seed contra prod (pooler 6543, `prepare_threshold=None`).
3. **Invalidar o cache Redis de prod:** o comando one-off roda com LocMem (evita Redis local), então os signals dele **não** limpam o Redis do servidor web (dashboard/projeção, TTL 300s) → totais ficariam stale ≤5 min. Apontar o comando para o **Redis de prod** (signals invalidam ao vivo) **ou** dar flush nas chaves `finance-dashboard*`/`finance-projection*` após aplicar (ou aceitar/documentar o self-heal de ≤5 min). A verificação por SQL (passo 4) ignora o cache — não confiar só nela.
4. **Verificar via Supabase MCP:** conferir `BillLineItem.amount` dos 18 IPTU = tabela 1.1; parcelas embutidas de água re-numeradas (836→23.., 850→2..); categorias criadas; faturas água/luz com totais da tabela 1.2; RLS intacto (`get_advisors type=security` sem `rls_disabled`); 9 WARNING IPTU mantidos.
5. **Apagar `db.txt`** ao final.

---

## 8. Decisões (travadas)

1. **IPTU = "atualizado"** — ✅ confirmado (tabela 1.1).
2. **Água/luz:** inserir **somente as faturas com vencimento em 06 ou 07/2026** (as anteriores já estão pagas). → 7 faturas: luz 840 solar (comp 05, venc 16/06), luz 836 social (comp 05, venc 01/06), luz 850 solar (comp 05, venc 16/06), água 836 (comp 05 venc 04/06 + comp 06 venc 04/07), água 850 (comp 05 venc 04/06 + comp 06 venc 04/07). **Abril (venc 04/05) NÃO entra.**
3. **Alerta de corte água/luz:** ❌ **fora deste plano** (futuro). O status de corte permanece visível no statement/conta, sem banner/push dedicado.
4. **Categoria:** ✅ **página de Categorias + seed inicial**. Conjunto inicial: **Serviços/Utilidades, Impostos, Manutenção, Pessoal/Folha, Outros**.
5. **Filtro de situação na lista de Contas:** global acima do accordion (KISS).

---

## 9. Ordem de execução sugerida

1. Fase 1 (IPTU dados+seed) — maior urgência (valores errados em prod).
2. Fase 2 (Parcelas vazia: diagnóstico + hardening).
3. Fase 3 (Contas por prédio + Tipo).
4. Fase 4 (Categoria).
5. Fase 5 (faturas água/luz).
6. Fase 6 (prod) intercalada por fase com escrita.

Cada fase: TDD onde aplicável, gate verde (lint+types+tests escopados), e — para fases com prod — backup-first + verificação por MCP.
