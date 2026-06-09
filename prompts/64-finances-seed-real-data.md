# Sessão 64 — Seed dos dados reais (água/luz/IPTU dos prédios 836 e 850) + comando idempotente `seed_condo_utilities`

> **Feature**: Condo utility-bills parser + IPTU (`docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`)
> **Sessões da feature**: 56 → 57 → 58 → 59 → 60 → 61 → 62 → 63 → **64** (Fase 7 — **última**: seed dos dados reais, local → prod após deploy)
> Esta sessão **não** cria modelos, serviços nem API — ela **popula** o banco com o inventário real do Apêndice A: cria as `BillingAccount` tipadas (água/luz/IPTU por prédio, com identidade — inscrição/UC/medidor/titular/endereço), os `InstallmentPlan` **embutidos** (água 836 46×, água 850 59×, luz 850 24×), os **9 termos avulsos de IPTU** (planos `embedded=False` vinculados às contas IPTU, com a parcela atual em atraso + a próxima em aberto), as **3 dívidas 2026** como `Bill(lifecycle_state=DEFERRED)` **com 1 `BillLineItem` do valor cheio + `billing_account=<conta IPTU>`**, e semeia as **parcelas de abertura** (atrasada/aberta) com **`competence_month=2026-06-01`** (due_date real preservada) para aparecerem no calendário e disparar o `IptuAlertService`. Fonte: `scripts/data/condo_utilities_seed.json` (criado aqui) + `python manage.py seed_condo_utilities` (idempotente, `--dry-run`). **NÃO backfilla parcelas pagas pré-tracking.** **Sem novos modelos/migrações; sem alterar serviços; sem frontend.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §10 "Geração/IPTU/diferidos" — §10.1/§10.2/§10.3/§10.4/§10.5; §12 "Backfill account_type"; §13 "Seed dos dados reais"; §14 Fase 7; Apêndice A "inventário real das contas"; Apêndice B "Fase 7")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `.claude/rules/database.md`, `.claude/rules/financial.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Importador JSON idempotente (`update_or_create` por chaves naturais, `--dry-run` via `transaction.set_rollback(True)`, `argparse`, stats, prints PT)** | `@scripts/import_financial_data.py:51-115` (classe + `run()` em `transaction.atomic()` :78-103; `stats` dict :59-71) + `:160-170` (`_parse_date`/`_require_date`) + `:1332-1378` (`main()`/`argparse`/`--dry-run`/path-resolve) | **Estrutura-base** do seed. Copiar o estilo: classe importadora, `transaction.atomic()`, `dry_run` → `set_rollback`, `_get_*` com `ValueError` PT, prints `[n/total]`. **Diferença**: aqui é um **management command** (`BaseCommand`), não script standalone — ver §"Por que management command" |
| **Template JSON real (estrutura de seções + `_instrucoes`/`_comentario`)** | `@scripts/data/financial_data_template.json:1-60` (cabeçalho `_instrucoes` :2-8; `configuracoes` :10-14; seções como dicts com `items` :16-18) | **Forma** do `condo_utilities_seed.json`: seções nomeadas (`contas`, `planos_embutidos`, `termos_iptu`, `dividas_2026`, `configuracoes`), valores `Decimal`-safe como strings/números, datas `YYYY-MM-DD`, sem R$/separador de milhar |
| **Management command (BaseCommand, `add_arguments`, `handle`, `self.stdout.write(self.style.SUCCESS(...))`, logs EN)** | `@core/management/commands/send_scheduled_notifications.py:56-83` (`class Command(BaseCommand)`, `help`, `handle`) + `@core/management/commands/generate_vapid_keys.py` (forma mínima de `add_arguments`) | **Esqueleto** do `seed_condo_utilities`. `--dry-run` em `add_arguments`; `handle` orquestra; saída de resumo via `self.style.SUCCESS` |
| **`BillingAccount` (campos da S56: `account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status`/`external_identifier`/`expected_amount`/`tracking_start_month`/`default_due_day`) + `recurring_for_generation()` (exclui IPTU)** | `finances/models.py:122-160` (campos + `clean()` rejeita `external_identifier` em branco p/ água/luz/IPTU — S56) + manager `recurring_for_generation()` (S56) | Chaves naturais do seed: água/luz = `(building, account_type, external_identifier=UC|inscrição)`; IPTU = idem. `update_or_create` nessas chaves. **Não** redefinir o predicado |
| **`InstallmentPlan` (S57 refactor: `billing_account` FK — embedded ⇒ conta de consumo; standalone livre) + `clean()`** | `finances/models.py:417-486` (`embedded`/`billing_account`/`lifecycle_state`/`installment_count`/`start_due_date`/`default_due_day`/`total_amount`; `clean()` embedded⇒conta) | Planos embutidos (água/luz) vinculam `billing_account=<conta>`; termos IPTU são `embedded=False` mas **com** `billing_account=<conta IPTU>` (regra §10.2 — o serializer/clean da S57 permite standalone com conta; ver §"Termos IPTU"). `full_clean()` antes de salvar |
| **`Bill(deferred)` + `BillLineItem` do valor cheio + `convert_deferred` (herda `billing_account`)** | `finances/services/installment_plan_service.py:72-142` (`convert_deferred(*, deferred_bill, installment_count, start_due_date, default_due_day, category?, user?)`; `total = with_amounts(today).amount_total` :98-99; bill→CANCELED :132) | As 3 dívidas 2026 = `Bill(lifecycle_state=DEFERRED, behavior=...)` com **1** `BillLineItem(amount=valor_dívida)` + `billing_account=<conta IPTU>`. Teste de `convert_deferred` usa `with_amounts` → exige a linha (senão plano R$0). **Não** alterar `convert_deferred` |
| **`BillGenerationService.ensure_month_bills` (gera recorrentes+embutidos+avulsos; exclui IPTU recorrente; standalone IPTU gera bills)** | `finances/services/bill_generation_service.py:38-205` (`ensure_month_bills` :66; recorrentes via `recurring_for_generation()` :77; embutidos :155-; avulsos :195-) | O seed **não** gera bills (o serviço gera sob demanda); mas os testes asseguram que, após o seed, a geração/projeção/atrasados refletem o estado esperado. **Não** chamar geração dentro do seed |
| **Factories `finances` (S56–S58 estendidas) + `make_condominium`/`make_building`** | `tests/factories.py:37-56` (`make_condominium`/`make_building`) + `:281-377` (`make_billing_account`/`make_bill`/`make_bill_line_item`/`make_installment_plan`) | Dados dos **testes do comando** (não do seed em si). O seed lê do JSON real; os testes rodam o comando sobre um JSON-fixture pequeno (ou o real) e asseguram contagens/idempotência |
| **RLS / advisor de prod (doc da execução)** | `core/migrations/0047_enable_row_level_security.py` (padrão RLS) + `.claude/rules/database.md` (backup antes; `pg_dump --schema=public`) + `.claude/rules/security.md` (advisor `get_advisors type=security` sem `rls_disabled`) | A seção §"Execução em produção" documenta o runbook pós-deploy. O seed **não** roda migração; as tabelas já existem (S56–S58) |
| Mock policy / banco real | `tests/CLAUDE.md` (Mock Policy — só fronteiras externas; `freezegun` p/ tempo) | Aqui = **só `freezegun`** (congelar 2026-06-08 p/ `today_sp()`/atraso). ORM/serviços/comando reais; `--reuse-db` |

### O que as S56–S63 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S56**: `BillingAccountType`/`SupplyStatus`; `BillingAccount.account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status`; unique `unique_active_billing_account_identity` `(building, account_type, external_identifier)` `condition=Q(is_deleted=False)`; `clean()`+serializer rejeitam `external_identifier` em branco p/ água/luz/IPTU; `BillingAccount.objects.recurring_for_generation()` (exclui IPTU) usado por geração/projeção/calendário.
- **S57**: `InstallmentPlan.linked_billing_account → billing_account` (rename); `clean()`/`serializer.validate` (embedded ⇒ conta de consumo); `convert_deferred` herda `billing_account`.
- **S58**: `WaterBillStatement`/`ElectricityBillStatement` (1:1 `Bill`, readings-only, RLS) + `create_with_lines`/`update_with_lines` estendidos.
- **S59–S60**: parser (`invoice_parsing`) + `parse_invoice` endpoint.
- **S61**: `IptuAlertService` + `iptu_alerts` (uncached) + `send_finance_alerts` + `Notification` types.
- **S62–S63**: modal responsivo + "Importar fatura"/banner.

> **Esta sessão depende de TODAS as anteriores** (56–63). Se qualquer modelo/serviço/predicado referenciado abaixo não existir, **PARE** — o seed apenas consome contratos já entregues.

---

## Escopo

### Arquivos a criar
- `scripts/data/condo_utilities_seed.json` — inventário real **completo** do Apêndice A (contas tipadas 836/850, planos embutidos, 9 termos IPTU, 3 dívidas 2026, `configuracoes`). Datas `YYYY-MM-DD`, valores numéricos sem R$/separador. **Sem CPF real** (titulares por primeiro nome, como no Apêndice A: RAUL/CELIA/PRANAS BIELAVICIUS).
- `finances/management/__init__.py` e `finances/management/commands/__init__.py` — pacotes vazios (se não existirem) para o command ser descoberto.
- `finances/management/commands/seed_condo_utilities.py` — `Command(BaseCommand)` idempotente: `--dry-run`, `--file` (default `scripts/data/condo_utilities_seed.json`); orquestra a criação via `update_or_create`/`get_or_create` por chaves naturais.
- `tests/unit/test_finances/test_seed_condo_utilities.py` — testes do comando (idempotência, competência 2026-06, diferidos fora de result/cash/overdue, `convert_deferred` total exato, etc.).

### Arquivos a modificar
- **Nenhum modelo/serviço/migração.** Possivelmente `tests/factories.py` **só** se faltar uma factory para os testes (improvável — S56–S58 cobriram). Não duplicar.

### NÃO fazer (pertence a outras sessões / fora de escopo)
- **Nenhuma alteração em modelos, migrações, serviços, serializers, viewsets, URLs ou frontend.** Tudo já existe (S56–S63). O seed apenas **escreve dados**.
- **NÃO chamar `BillGenerationService.ensure_month_bills` dentro do seed** — a geração de bills recorrentes/embutidos é sob demanda (mensal, S37/S41); o seed só cria contas/planos/dívidas. As parcelas **de abertura** (atrasada/aberta) dos termos IPTU são `Installment`/`Bill` materializados explicitamente pelo seed com `competence_month=2026-06-01` (§10.1) — ver §"Parcelas de abertura".
- **NÃO backfillar parcelas pagas pré-tracking** (§13) — só a parcela atual (em atraso) e a próxima (em aberto) de cada termo IPTU entram; parcelas 1..(atual−1) **não** são criadas (evita poluir result/cash de meses < `rent_tracking_start_date`).
- **NÃO rodar `migrate`** no fluxo do seed (as tabelas já existem). O runbook de prod (§"Execução em produção") roda migração **antes** do seed, mas isso é operação manual documentada, não código do comando.
- **NÃO inventar valores ausentes** — todo número/data vem do Apêndice A. Onde o Apêndice diz "a confirmar no seed" (status pago/não-pago de maio/junho; mês de origem de cada embutido), usar exatamente o estado do Apêndice A (luz paga até maio/junho não; água 850 junho paga; água 836 não paga/cortada) e registrar a premissa num comentário do JSON (`_premissas`). Sem chutes silenciosos.
- **NÃO armazenar anexos de fatura** (YAGNI §16). **NÃO** criar `MonthSnapshot`/`CondoMonthClose`/fechamento.

---

## Especificação

> O comando é **idempotente**: rodar 2×+ não duplica nada (todas as escritas via `update_or_create`/`get_or_create` em **chaves naturais**). `--dry-run` envolve tudo em `transaction.atomic()` + `set_rollback(True)` (espelha `import_financial_data.py:78-103`). Valores monetários sempre `Decimal(str(...))` (nunca `float`). Datas via `date.fromisoformat`. Mensagens ao usuário/saída em **PT**; logs/identificadores em **EN**. `full_clean()` antes de cada `save()` que não passe por `update_or_create(defaults=...)` para disparar as mensagens PT dos `clean()`.

### Por que management command (e não script standalone)
O exemplar `import_financial_data.py` é um script com `django.setup()` próprio. Esta sessão usa um **management command** (`python manage.py seed_condo_utilities`) porque o design §13 pede exatamente `python manage.py seed_condo_utilities` e porque o command é **testável** sem `subprocess` (via `call_command`), respeitando a mock policy (banco real, zero mocks de internals). A lógica de importação (parse JSON, `update_or_create`) vive no `handle()`/helpers do command; a estrutura (stats, `_get_building`, prints) espelha o importador.

### Chaves naturais (idempotência — §13)

| Entidade | Chave natural de `update_or_create`/`get_or_create` |
|----------|------------------------------------------------------|
| `BillingAccount` água/luz/IPTU | `(building, account_type, external_identifier)` — UC para luz, inscrição para água/IPTU. (= a unique `unique_active_billing_account_identity` da S56.) |
| `InstallmentPlan` embutido (água/luz) | `(billing_account, embedded=True, description)` — uma conta de consumo tem no máximo 1 plano embutido ativo; `description` desambigua reparcelamentos. |
| `InstallmentPlan` termo IPTU (avulso) | `(billing_account, embedded=False, description)` onde `description` inclui o nº do termo (ex.: `"IPTU termo 992988"`). |
| `Bill` dívida 2026 (deferred) | `(billing_account, behavior, competence_month)` ou descrição do lançamento (ex.: `"IPTU dívida 2026 lançamento 202600179949"`) — usar a unique parcial `(billing_account, competence_month)` existente. |
| `BillLineItem` do bill diferido | recriado idempotentemente: `bill.line_items` (com a manager certa) — apagar e recriar a única linha, ou `get_or_create(bill=bill, description=...)`. |
| `Installment` (parcela de abertura) | `(plan, number)`. |
| `Bill` da parcela de abertura (se materializada) | `(billing_account, competence_month, ...)` via a manager existente. |

### Inventário a semear (Apêndice A — verbatim, sem chutar)

**Prédio 836** (cadastro DMAE/IPTU «Av Circular 828»):
- **Água DMAE** — `WATER`, `external_identifier="117.111.0049.0519.00"` (inscrição), `secondary_identifier="003419142"` (imóvel), `supply_status=CUT` (água cortada/esgoto ligado), `registered_address="Av Circular 828"`, `default_due_day=4`, `holder_name` conforme prédio. Plano **embutido 46×** ~R$94,48, **parcela atual 24**, `embedded=True`, `billing_account=<água 836>`. (Reparcelamento iminente — **não** modelar o futuro; só o plano atual.)
- **Luz principal (840, solar)** — `ELECTRICITY`, `external_identifier="1.273.798.010-05"` (UC), `secondary_identifier="MD50721985"` (medidor), `holder_name="RAUL"`, classe Residencial Pleno, `supply_status=ACTIVE`. **Sem** plano. `expected_amount` da fatura 05/2026 R$921,49 (não paga).
- **Luz 2º relógio (836, tarifa social)** — `ELECTRICITY`, `external_identifier="650.847.010-16"` (UC), `secondary_identifier="MD33457946"`, `holder_name="RAUL"`, Baixa Renda. **Sem** plano. 05/2026 R$97,62 (não paga).
- **IPTU 836** — `IPTU`, `external_identifier="516449"` (inscrição), `holder_name="RAUL"`. **Dívida 2026** lançamento `202600179949` R$10.308,70 → `Bill(deferred)`. **4 termos** avulsos (10× cada): `992988` (saldo 27.181,69), `992989` (20.669,56), `992990` (15.036,95), `992991` (98,37). Cada termo: parcela **9 Em Atraso (venc. 29/05)** + parcela **10 Em Aberto (venc. 30/06)**.

**Prédio 850** (cadastro DMAE «Av Circular 838»; IPTU «Casa 1/Casa 2»):
- **Água DMAE** — `WATER`, `external_identifier="117.111.0049.0508.00"`, `secondary_identifier="000463540"`, `supply_status=ACTIVE`, `registered_address="Av Circular 838"`, `default_due_day=4`. Plano **embutido 59×** R$530,24, **parcela atual 3**. Junho informada como **paga**.
- **Luz (solar)** — `ELECTRICITY`, `external_identifier="1.273.678.010-60"` (UC), `secondary_identifier="MD50722005"`, `holder_name="CELIA"`, Residencial Pleno. Plano **embutido 24×** R$629,35, **parcela atual 19**. 05/2026 R$990,80.
- **IPTU Casa 1 (2 kitnets)** — `IPTU`, `external_identifier="516481"`, `holder_name="PRANAS BIELAVICIUS"`. **Dívida 2026** `202600179981` R$682,39 → `Bill(deferred)`. **1 termo** `992269` (10×; parcela 9 atraso R$136,05 / parcela 10 aberto R$137,31).
- **IPTU Casa 2 (fundos + casa)** — `IPTU`, `external_identifier="516503"`, `holder_name="PRANAS BIELAVICIUS"`. **Dívida 2026** `202600179990` R$6.741,33 → `Bill(deferred)`. **4 termos**: `1075071` (2021, 56×, 4.868,12), `1075073` (2021, 56×, 7.712,87), `992967` (2025, 10×, 11.932,12), `992968` (2025, 10×, 13.409,87). Cada termo: parcela **55/9 atraso (29/05)** + **56/10 aberto (30/06)**.

**Configurações** (`core.FinancialSettings`, singleton — `import_financial_data.py:176-191` é o exemplar): `initial_balance=0`, `initial_balance_date=2026-03-01`, `rent_tracking_start_date=2026-06-01`. (A nota de pagamento "a confirmar" do Apêndice A entra no JSON como `_premissas`.)

> **Totais esperados após o seed**: **9 planos de IPTU ativos** (4 do 836 + 1 do 850/Casa1 + 4 do 850/Casa2) + **3 dívidas 2026 diferidas** + **6 contas de consumo** (2 água + 4 luz) + **4 contas IPTU**. No estado atual (cada termo com 1 parcela em atraso) → **9 alertas WARNING** do `IptuAlertService` (§10.5 / Apêndice A).

### Termos IPTU = planos `embedded=False` **com** `billing_account` (decisão §10.2/§10.3)
Cada termo é um `InstallmentPlan(embedded=False, billing_account=<conta IPTU>, lifecycle_state=ACTIVE)`. A S57 permite **standalone com conta** (o `clean()` proíbe **embutido sem** conta e **embutido livre**, mas não proíbe standalone com conta — confirmar no `clean()`/`serializer.validate` da S57; se proibir, é bug da S57, não desta sessão — **PARE** e reporte). O `billing_account=IPTU` é o que torna os termos visíveis ao `IptuAlertService` (`account_type=IPTU`, `embedded=False` — query da S61). A `recurring_for_generation()` (S56) **exclui** as **contas** IPTU da geração recorrente, mas os **planos standalone** de IPTU **continuam** gerando 1 bill/parcela/mês (§10.3) — **não** confundir os dois ramos.

### Parcelas de abertura (§10.1 — competência 2026-06)
Para cada termo IPTU, materializar **apenas**:
- a **parcela atual** (em atraso, venc. 29/05/2026) e
- a **próxima** (em aberto, venc. 30/06/2026).

Cada uma é um `Installment(plan, number, due_date=<real>, amount=<real>)` **e** o `Bill` correspondente (via a manager/serviço de materialização existente, S41) com **`competence_month=date(2026, 6, 1)`** — a `due_date` real (29/05 ou 30/06) é **preservada** no bill/installment; só a **competência** é fixada em 2026-06 para que as parcelas atrasadas não caiam em meses < `rent_tracking_start_date` (2026-06-01) e não gerem net negativo pré-tracking (§10.1/Apêndice B Fase 7). **Parcelas 1..(atual−1) NÃO são criadas** (não-backfill). O `number` do `Installment` é o real (9, 10 / 55, 56), mas só essas duas existem.

> **Como materializar sem chamar a geração mensal**: criar o `Installment` (schedule) e o `Bill`+`BillLineItem` (realized) diretamente via ORM/factories-de-produção que a S41 expõe (ex.: o caminho que `ensure_month_bills` usa para avulsos — `BillService.create_with_lines` com `installment=<installment>` na linha, S58). **Reusar** o serviço de criação (`BillService.create_with_lines`) — **não** reimplementar a montagem de bill no seed. Passar `competence_month=date(2026,6,1)`, `due_date=<real>`, `line=[{amount, installment_id}]`, `billing_account=<conta IPTU>`. Se a parcela atual está **em atraso**, o bill fica **UNPAID** (sem pagamento) → aparece em "Atrasados".

### Dívidas 2026 diferidas (§10.4)
Cada dívida = `Bill(lifecycle_state=DEFERRED, billing_account=<conta IPTU>, competence_month=date(2026,6,1), due_date=<a definir do lançamento; usar 2026-06-30 se ausente>, description="IPTU dívida 2026 lançamento <num>")` **com 1 `BillLineItem(amount=<valor cheio da dívida>, is_offset=False)`**. O `lifecycle_state=DEFERRED` exclui a dívida de competência/caixa/atrasados (filtro `==ACTIVE` existente, §10.4). A linha do valor cheio é **obrigatória** (senão `convert_deferred` → `with_amounts().amount_total == 0` → plano R$0, §10.4). Usar `BillService.create_with_lines(..., lifecycle_state=DEFERRED)` (S37/S58) — **não** montar à mão.

### Idempotência (CRÍTICO — §13 / Apêndice B Fase 7)
Rerun do comando **não** duplica: contas via `update_or_create((building, account_type, external_identifier))`; planos via `update_or_create((billing_account, embedded, description))`; dívidas/parcelas de abertura via `get_or_create` na unique parcial existente. **Antes** de criar a `BillLineItem` única do bill diferido, fazer `get_or_create(bill=bill, description=<linha>)` (não acumular linhas no rerun). Stats reportam "criados" vs "atualizados".

### `handle()` (esqueleto)
```python
class Command(BaseCommand):
    help = "Seed real condo utility accounts/plans/IPTU debts (prédios 836 e 850)."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--file", default="scripts/data/condo_utilities_seed.json")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        data = self._load(options["file"])
        with transaction.atomic():
            self._seed_settings(data)
            self._seed_billing_accounts(data)     # água/luz/IPTU tipadas
            self._seed_embedded_plans(data)        # água 836/850, luz 850
            self._seed_iptu_terms(data)            # 9 termos standalone + parcelas de abertura
            self._seed_deferred_2026_debts(data)   # 3 Bill(deferred) + 1 line cada
            if options["dry_run"]:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(self._summary()))
```
Cada `_seed_*` usa `update_or_create`/`get_or_create`, conta em `self.stats`, e imprime `[n/total]` + linhas `+ ...` (PT), espelhando `import_financial_data.py`. `_get_building(street_number)` levanta `CommandError` PT se o prédio não existir (os prédios 836/850 devem já estar cadastrados — pré-condição documentada).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **APENAS fronteiras externas** — aqui = **só `freezegun`** (`@freeze_time("2026-06-08")` p/ `today_sp()`/atraso coerentes). **NUNCA** mockar ORM, `call_command`, `BillService`, `InstallmentPlanService`, `IptuAlertService`, managers ou qualquer interno. Banco real (`--reuse-db`). Os testes rodam o comando via `django.core.management.call_command("seed_condo_utilities", "--file", <fixture>)`. Pré-criar os prédios 836/850 via `make_building(street_number=836)`/`make_building(street_number=850)` (mesmo `condominium`). Usar um **JSON-fixture pequeno** em `tests/` (subconjunto fiel: ≥1 conta de cada tipo, 1 plano embutido, 2 termos IPTU com parcela atual atrasada, 1 dívida 2026) **ou** o `condo_utilities_seed.json` real — **decidir e travar**; recomendo o **fixture pequeno** (rápido, determinístico) + **1 smoke** que roda o JSON real e confere os totais do Apêndice A (9 planos IPTU, 3 diferidos). `filterwarnings=error`: zero warnings.

### 1. RED — escrever os testes primeiro

#### `tests/unit/test_finances/test_seed_condo_utilities.py` (sob `@freeze_time("2026-06-08")`, `@pytest.mark.django_db`)

```python
def test_seed_creates_typed_billing_accounts_with_identity(self) -> None:
    """Roda o comando → cria BillingAccount água/luz/IPTU com account_type, external_identifier
    (inscrição/UC), secondary_identifier (imóvel/medidor), holder_name, registered_address,
    supply_status conforme o JSON-fixture; 836-água tem supply_status=CUT."""

def test_seed_is_idempotent_no_duplication_on_rerun(self) -> None:
    """call_command 2× → contagens de BillingAccount/InstallmentPlan/Bill(deferred)/BillLineItem
    do bill diferido idênticas após a 2ª rodada (update_or_create em chaves naturais; a única
    linha do bill diferido NÃO é duplicada — get_or_create)."""

def test_seed_embedded_plans_linked_to_consumption_accounts(self) -> None:
    """Planos embutidos (água/luz) → embedded=True, billing_account=<conta de consumo>,
    installment_count e total/parcela conforme fixture; clean() não rejeita (conta de consumo)."""

def test_seed_iptu_terms_are_standalone_with_iptu_account(self) -> None:
    """Cada termo IPTU → InstallmentPlan(embedded=False, billing_account=<conta IPTU>,
    lifecycle_state=ACTIVE); description contém o nº do termo; visível ao IptuAlertService."""

def test_opening_installments_use_competence_2026_06_with_real_due_dates(self) -> None:
    """Parcela atual (atraso 29/05) e próxima (aberto 30/06) materializadas: Bill.competence_month
    == date(2026,6,1) em AMBAS, mas due_date == date real (29/05 e 30/06). number == real (9 e 10)."""

def test_seed_does_not_backfill_paid_pre_tracking_installments(self) -> None:
    """Só as parcelas atual e próxima existem por termo: Installment.objects.filter(plan=termo)
    tem exatamente 2 (numbers {9,10}); parcelas 1..8 NÃO criadas (não-backfill, §13)."""

def test_opening_overdue_installment_appears_in_overdue_not_pre_tracking(self) -> None:
    """A parcela atrasada (competence 2026-06, UNPAID) entra em 'Atrasados'; nenhum bill com
    competence_month < rent_tracking_start_date(2026-06-01) foi criado → sem net negativo
    pré-tracking (consultar via with_amounts/serviço de atrasados existente, sem recomputar em Python)."""

def test_deferred_2026_debts_excluded_from_result_cash_overdue(self) -> None:
    """As 3 (no real; ≥1 no fixture) dívidas 2026 são Bill(lifecycle_state=DEFERRED) com 1
    BillLineItem do valor cheio + billing_account=<IPTU>; NÃO aparecem em competência/caixa/
    atrasados (filtro ==ACTIVE) — assert via os serviços/queries existentes, banco real."""

def test_convert_deferred_on_seeded_debt_yields_exact_total(self) -> None:
    """InstallmentPlanService.convert_deferred(deferred_bill=<dívida 836 R$10.308,70>, ...) →
    plan.billing_account == conta IPTU 836 (§10.2) E plan.total_amount == Decimal('10308.70')
    (with_amounts da linha cheia); Σ Installment.amount == total; o IptuAlertService passa a
    enxergar o novo plano."""

def test_dry_run_writes_nothing(self) -> None:
    """call_command(..., '--dry-run') → BillingAccount/InstallmentPlan/Bill counts inalterados
    (transaction.set_rollback). Saída de resumo ainda impressa."""

def test_seed_settings_singleton(self) -> None:
    """FinancialSettings (pk=1) → initial_balance=0, initial_balance_date=2026-03-01,
    rent_tracking_start_date=2026-06-01 (update_or_create; rerun não duplica)."""

def test_seed_missing_building_raises_command_error(self) -> None:
    """JSON referenciando prédio inexistente → CommandError PT (não cria nada parcial:
    transaction.atomic envolve tudo)."""

def test_real_inventory_smoke_counts_match_appendix_a(self) -> None:
    """SMOKE: call_command com o condo_utilities_seed.json REAL (após criar prédios 836/850) →
    9 InstallmentPlan IPTU ativos (embedded=False, account_type=IPTU), 3 Bill(deferred),
    6 contas de consumo, 4 contas IPTU; IptuAlertService.evaluate(today_sp()) → 9 linhas WARNING."""
```

> Rodar (devem **falhar** — comando/JSON ainda não existem):
> ```bash
> python -m pytest tests/unit/test_finances/test_seed_condo_utilities.py -q
> ```

### 2. GREEN — implementar

1. `scripts/data/condo_utilities_seed.json` — inventário real completo (Apêndice A), com `_instrucoes`/`_premissas` (nota de pagamento "a confirmar"). Datas ISO; valores numéricos.
2. `finances/management/__init__.py` + `finances/management/commands/__init__.py` (vazios, se faltarem).
3. `finances/management/commands/seed_condo_utilities.py` — `Command` + helpers `_seed_*`, reusando `BillService.create_with_lines`/`InstallmentPlanService` (imports diretos da fonte; **nunca** reimplementar montagem de bill). `update_or_create`/`get_or_create` em chaves naturais; `--dry-run`; `CommandError` PT.
4. Fixture pequeno de teste (ex.: `tests/data/condo_utilities_seed_test.json` ou inline via `tmp_path`) — decidir e travar; recomendo `tmp_path` + dict Python serializado no teste (auto-contido, sem arquivo versionado extra) **exceto** o smoke que aponta para o JSON real.

Rodar até verde:
```bash
python -m pytest tests/unit/test_finances/test_seed_condo_utilities.py -q
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- Cada `_seed_*` é uma função pequena com responsabilidade única (SRP); `_get_building`/`_get_account` reusados; `Decimal(str(...))` centralizado num helper `_money(value) -> Decimal`.
- Reuso **direto** de `BillService.create_with_lines` e `InstallmentPlanService` — zero duplicação de montagem de bill/plano/installment.
- `competence_month=date(2026,6,1)` como **constante nomeada** (`_OPENING_COMPETENCE`) — fonte única (§10.1); `due_date` real vem do JSON.
- Strings PT de saída/erro como constantes nomeadas se repetidas (sem magic strings).
- Chaves naturais documentadas em docstring de cada `_seed_*` (idempotência explícita).

### 4. VERIFY — gate ampliado (escopo desta sessão)

> Rodar **apenas nos arquivos editados** (a suíte completa tem flakiness pré-existente de xdist/Redis — memória do projeto). Coverage ≥90% **standalone** de `finances` para os módulos tocados (o command + helpers).

```bash
python -m pytest tests/unit/test_finances/test_seed_condo_utilities.py \
  --cov=finances --cov-report=term-missing --cov-fail-under=90 -p no:cacheprovider -q
ruff check finances/management/ scripts/data/condo_utilities_seed.json tests/unit/test_finances/test_seed_condo_utilities.py
ruff format --check finances/management/ tests/unit/test_finances/test_seed_condo_utilities.py
mypy core/ finances/
pyright finances/management/ tests/unit/test_finances/test_seed_condo_utilities.py
```

> **Regressão obrigatória** (não quebrar os serviços que o seed consome): rodar os testes do `IptuAlertService` (S61), `convert_deferred` (S57), geração/projeção (S37/S41) para garantir que o estado semeado é compatível:
> ```bash
> python -m pytest tests/unit/test_finances -k "iptu_alert or convert_deferred or generation or projection" -q
> ```

### Execução em produção (runbook — documentar; **rodar manualmente após o deploy**, NÃO no CI)

> Ordem do design §13: **local primeiro → validar → commit/PR/deploy → prod por último.** Local já validado pelo gate acima. Pós-deploy do backend (S56–S63 já aplicadas em prod):
1. **Backup** (regra `.claude/rules/database.md` — obrigatório antes de qualquer escrita em prod):
   `pg_dump "<connection-string-do-Dashboard>" --schema=public --no-owner --no-acl -Fc > backup_prod_$(date +%Y%m%d_%H%M%S).dump`
2. **Migrações** (as tabelas/colunas das S56–S58 + `core` AlterField Notification da S61): `python manage.py migrate` (idempotente; já devem estar aplicadas pelo deploy — confirmar `showmigrations`).
3. **Seed**: `python manage.py seed_condo_utilities` (sem `--dry-run`); conferir o resumo (9 planos IPTU, 3 diferidos, 6+4 contas).
4. **Advisor de segurança** (`.claude/rules/security.md`): `get_advisors type=security` no projeto Supabase `kaukiwhbmvnjjekodcmq` → **zero** `rls_disabled` (CRITICAL). O `rls_enabled_no_policy` (INFO) é esperado. As tabelas `WaterBillStatement`/`ElectricityBillStatement` (S58) já habilitam RLS na migração.
5. **Validação funcional**: o `IptuRiskBanner` (S63) deve mostrar 9 riscos WARNING; o calendário/atrasados refletem as parcelas de abertura (competência 2026-06).

> O comando é idempotente — se já rodado, um rerun não duplica (seguro). **Não** rodar `--clear-first` (não existe; o seed nunca apaga dados).

---

## Constraints

- **Apenas dados** — **NÃO** alterar modelos, migrações, serviços, serializers, viewsets, URLs, signals ou frontend. O seed consome contratos das S56–S63 verbatim.
- **Idempotência total** (§13): toda escrita via `update_or_create`/`get_or_create` em chave natural; rerun não duplica (incl. a linha única do bill diferido via `get_or_create`).
- **Competência das parcelas de abertura = `date(2026,6,1)`** (§10.1) com `due_date` real preservada; **NÃO** backfillar parcelas pagas pré-tracking (só atual + próxima por termo).
- **Dívidas 2026 = `Bill(DEFERRED)` com 1 `BillLineItem` do valor cheio + `billing_account=<IPTU>`** (§10.4) — a linha é obrigatória (senão `convert_deferred` → plano R$0).
- **Termos IPTU = `InstallmentPlan(embedded=False, billing_account=<IPTU>)`** (§10.2/§10.3) — visíveis ao `IptuAlertService`; a exclusão de IPTU é **só** no ramo recorrente (`recurring_for_generation()`), nunca nos planos standalone.
- **Reuso de serviços** — montar bills/planos/installments **via** `BillService.create_with_lines`/`InstallmentPlanService` (imports diretos), **nunca** reimplementar a montagem no seed (DRY).
- **`Decimal(str(...))` para dinheiro** — nunca `float`. Datas via `date.fromisoformat`.
- **Sem chutes** — todo valor/data do Apêndice A; premissas "a confirmar" registradas em `_premissas` no JSON. **Sem CPF real** (titulares por nome, como no Apêndice A) — guard de CPF do CI continua verde.
- **`--dry-run`** envolve tudo em `transaction.atomic()` + `set_rollback(True)`; **não** roda `migrate`.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`. Corrigir o código. Tipos completos (mypy strict + pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** (PEP 649 nativo); importar tipos direto (`from argparse import ArgumentParser`, `from datetime import date`, `from decimal import Decimal`).
- **Sem re-exports / barrels / shims**: o command importa direto da fonte (`finances.models`, `finances.services.*`, `core.models.FinancialSettings`).
- **Produção é manual** (runbook §"Execução em produção"): backup `pg_dump` ANTES; advisor sem `rls_disabled` DEPOIS. **NUNCA** delegar a escrita em prod sem backup.

## Critérios de Aceite (binários)

- [ ] `scripts/data/condo_utilities_seed.json` contém o inventário real **completo** do Apêndice A: 2 contas água + 4 contas luz + 4 contas IPTU (com `account_type`/`external_identifier`/`secondary_identifier`/`holder_name`/`registered_address`/`supply_status`/`default_due_day`), planos embutidos (água 836 46×/atual 24, água 850 59×/atual 3, luz 850 24×/atual 19), 9 termos IPTU (4 836 / 1 850-Casa1 / 4 850-Casa2) com parcela atual+próxima, 3 dívidas 2026 com valor cheio, `configuracoes` (saldo 0 / 2026-03-01 / tracking 2026-06-01), `_premissas`. **Sem CPF real.**
- [ ] `finances/management/commands/seed_condo_utilities.py` (`Command(BaseCommand)`): `--file`/`--dry-run`; idempotente (`update_or_create`/`get_or_create` em chaves naturais); reusa `BillService.create_with_lines`/`InstallmentPlanService`; `CommandError` PT para prédio ausente; resumo via `self.style.SUCCESS`.
- [ ] Contas tipadas criadas com identidade (836-água `supply_status=CUT`); planos embutidos vinculados às contas de consumo; termos IPTU standalone com `billing_account=<IPTU>` (visíveis ao `IptuAlertService`); 3 dívidas 2026 `Bill(DEFERRED)` com 1 `BillLineItem` do valor cheio + `billing_account=<IPTU>`.
- [ ] Parcelas de abertura: `competence_month=date(2026,6,1)` em ambas, `due_date` real (29/05 atraso e 30/06 aberto), `number` real; **sem** backfill de parcelas pagas pré-tracking (exatamente 2 `Installment` por termo).
- [ ] Idempotência: 2ª rodada não duplica nada (contas/planos/bills/linha do diferido); `--dry-run` não escreve.
- [ ] `convert_deferred` sobre uma dívida semeada → `plan.billing_account == conta IPTU` **e** `plan.total_amount == valor cheio exato`; Σ installments == total; alerta passa a enxergar o plano.
- [ ] Diferidos **fora** de result/cash/overdue (filtro `==ACTIVE`); nenhum bill com `competence_month < 2026-06-01` criado (sem net negativo pré-tracking).
- [ ] Testes cobrem: contas tipadas+identidade, idempotência, dry-run, embutidos, termos IPTU standalone, competência 2026-06 com due_date real, não-backfill, atrasado em "Atrasados", diferidos fora das somas, `convert_deferred` total exato, settings singleton, prédio ausente→`CommandError`, smoke do inventário real (9 alertas WARNING).
- [ ] `python -m pytest tests/unit/test_finances/test_seed_condo_utilities.py` passa 100%, **coverage `finances` ≥90%** nos módulos tocados; regressão `iptu_alert`/`convert_deferred`/`generation`/`projection` verde.
- [ ] `ruff check` + `ruff format --check` limpos; `mypy core/ finances/` limpo; `pyright` limpo — **zero erros e zero warnings**, **sem** `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.
- [ ] Nenhum modelo/migração/serviço/serializer/viewset/URL/frontend alterado; runbook de prod (backup `pg_dump` → migrate → seed → advisor sem `rls_disabled`) documentado neste prompt (executado manualmente após o deploy, fora do CI).

## Handoff

1. Rodar e confirmar verde (gate ampliado, escopo desta sessão):
   ```bash
   python -m pytest tests/unit/test_finances/test_seed_condo_utilities.py \
     --cov=finances --cov-report=term-missing --cov-fail-under=90 -q
   python -m pytest tests/unit/test_finances -k "iptu_alert or convert_deferred or generation or projection" -q
   ruff check finances/management/ tests/unit/test_finances/test_seed_condo_utilities.py
   ruff format --check finances/management/ tests/unit/test_finances/test_seed_condo_utilities.py
   mypy core/ finances/
   pyright finances/management/ tests/unit/test_finances/test_seed_condo_utilities.py
   ```
2. **Validar o seed real localmente** (banco de dev — backup antes, regra `.claude/rules/database.md`):
   ```bash
   python scripts/backup_db.py
   python manage.py seed_condo_utilities --dry-run    # conferir o resumo sem gravar
   python manage.py seed_condo_utilities              # aplicar; conferir 9 planos IPTU / 3 diferidos / 6+4 contas
   python manage.py seed_condo_utilities              # rerun → idempotente (sem duplicação)
   ```
3. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 64 (status **concluída**) na tabela da feature condo utility-bills.
   - **Arquivos Criados**: `scripts/data/condo_utilities_seed.json`, `finances/management/__init__.py`, `finances/management/commands/__init__.py`, `finances/management/commands/seed_condo_utilities.py`, `tests/unit/test_finances/test_seed_condo_utilities.py`.
   - **Nota**: "Fase 7 (final) — seed idempotente dos dados reais (Apêndice A): 6 contas consumo + 4 contas IPTU tipadas com identidade (836-água CUT), planos embutidos água 836/850 + luz 850, 9 termos IPTU standalone (billing_account=IPTU) com parcela atual(atraso 29/05)+próxima(aberto 30/06) em competência 2026-06 (due_date real, sem backfill), 3 dívidas 2026 Bill(DEFERRED) com BillLineItem cheio. Idempotente (update_or_create em chaves naturais), --dry-run. convert_deferred herda conta IPTU → total exato. **Prod = runbook manual pós-deploy: backup pg_dump → migrate → seed → advisor sem rls_disabled.** Sem modelos/migrações/serviços/frontend."
   - **Contratos cross-session** (verbatim, ver abaixo).
4. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
5. Commitar (a partir do branch da feature):
   ```
   feat(finances): complete session 64 — seed real condo utility/IPTU data + idempotent seed_condo_utilities command

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
6. **Após o deploy do backend em prod**: executar o runbook §"Execução em produção" (backup `pg_dump` → `migrate` → `seed_condo_utilities` → `get_advisors type=security` sem `rls_disabled`). Esta é a **última** sessão da feature — com o seed em prod, o módulo opera as contas reais dos prédios 836/850.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`scripts/data/condo_utilities_seed.json`** — fonte única do inventário real (Apêndice A). Atualizações futuras (reparcelamento DMAE da água 836, novos termos IPTU) editam este JSON e re-rodam o comando idempotente.
- **`python manage.py seed_condo_utilities [--file <path>] [--dry-run]`** — comando idempotente; chaves naturais: conta = `(building, account_type, external_identifier)`, plano = `(billing_account, embedded, description)`, dívida diferida = unique `(billing_account, competence_month)`, installment = `(plan, number)`. Reusa `BillService.create_with_lines`/`InstallmentPlanService.convert_deferred`. Rerun seguro.
- **Estado semeado** (consumido por dashboards/alertas): 9 `InstallmentPlan(embedded=False, account_type=IPTU, ACTIVE)` → 9 alertas WARNING (`IptuAlertService`); 3 `Bill(DEFERRED)` com `BillLineItem` cheio + `billing_account=IPTU` → `convert_deferred` produz o plano com total exato; parcelas de abertura em `competence_month=2026-06-01` (due_date real) → "Atrasados" inclui IPTU (drill-down via banner, §10.5). `FinancialSettings`: `initial_balance=0`/`2026-03-01`/`rent_tracking_start_date=2026-06-01`.
- **Runbook de prod** (manual, pós-deploy): backup `pg_dump --schema=public` → `migrate` → `seed_condo_utilities` → `get_advisors type=security` (sem `rls_disabled`). Nunca escrever em prod sem backup.
