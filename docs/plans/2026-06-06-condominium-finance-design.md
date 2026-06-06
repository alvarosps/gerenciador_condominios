# Design — Módulo Financeiro do Condomínio (Saídas, Saldo, Reserva e Distribuição)

> Data: 2026-06-06 · **Versão 3 (FINAL — pronta para virar prompts de implementação)** · Status: revisada após 3 reviews multi-lente + verificação PROD + pesquisa June 2026 · Autor: Alvaro Souza (+ Claude)
> Substitui conceitualmente o módulo financeiro legado (`Person`/`Expense`/dashboard `financial/*`), que permanece operante até ser removido no futuro.

> **v2 → v3 (correções da review final, todas docs — nenhuma reabre decisão travada):** (1) **`MonthSnapshot` está VIVO** (trava aluguel + base do caixa legado) → o módulo novo **não o ignora nem o duplica**: usa um **anchor de fechamento LEVE e condo-scoped (`CondoMonthClose`)** como semente do fold (O(1)) + auditoria; o rent-lock continua no `MonthSnapshot` legado durante a coexistência. (2) **Caixa = escopos distintos** (condo ≠ commingled legado) — documentado, não é dual-authority. (3) **Produtor de receita filtrado por collectibility** (`received_collectible_total`) — não o `received_total` cru. (4) **Fold sem termo de reserva** (reserva = transferência de caixa, não reduz distribuição). (5) **Cache cross-app é NET-NEW** para Apartment/Lease — receivers novos + bloco de constantes de prefixo. (6) **Gate ampliado para `finances`** (coverage/mypy/pyright). (7) **TZ helper** `America/Sao_Paulo` (settings é UTC). (8) **Suspensão**: passado = linhas reais, nunca recomputado. (9) Removidas refs órfãs de `CondominiumOwnership`; overdue via **annotation ORM**; `BillService.create_with_lines`; race-path idempotente; guarda de reserva negativa; **worked examples** pinados; **splits de fase** + listas de **edge-cases por fase** (§18).

## Sumário

1. [Contexto e objetivo](#1-contexto-e-objetivo)
2. [Decisões travadas](#2-decisões-travadas)
3. [Arquitetura geral](#3-arquitetura-geral)
4. [Invariantes financeiras (pinadas, com exemplos)](#4-invariantes-financeiras-pinadas-com-exemplos)
5. [Modelo de dados](#5-modelo-de-dados)
6. [Receita do condomínio e proprietários (não-invasivo)](#6-receita-do-condomínio-e-proprietários-não-invasivo)
7. [Mapeamento dos casos reais](#7-mapeamento-dos-casos-reais)
8. [Regras de negócio e serviços](#8-regras-de-negócio-e-serviços)
9. [API](#9-api)
10. [Frontend / Dashboard](#10-frontend--dashboard)
11. [Cache e signals (cross-app)](#11-cache-e-signals-cross-app)
12. [Testes e gate de qualidade por fase](#12-testes-e-gate-de-qualidade-por-fase)
13. [Migrações e dados](#13-migrações-e-dados)
14. [Faseamento da implementação](#14-faseamento-da-implementação)
15. [Fora de escopo agora (YAGNI, arquitetura pronta)](#15-fora-de-escopo-agora-yagni-arquitetura-pronta)
16. [Riscos e mitigações](#16-riscos-e-mitigações)
17. [Decisões resolvidas + apêndice de verificação PROD](#17-decisões-resolvidas--apêndice-de-verificação-prod)
18. [Apêndice — edge-cases por fase (testes RED)](#18-apêndice--edge-cases-por-fase-testes-red)

---

## 1. Contexto e objetivo

O sistema controla **entradas** via aluguéis (`RentScheduleService` = SSOT de aluguel cobrável,
pré-pago, salário-compensado, valor efetivo, calendário, marcação de pago). **Não há controle de
saídas.** Esta feature cria esse controle, **separando estritamente condomínio de pessoal**:

- Módulo novo = **só operacional do condomínio** (contas dos prédios + nível-condomínio). Pessoal e
  **sítio** ficam **fora** (futuro sistema financeiro pessoal).
- O **resultado mensal do condomínio** é um output computável que, no futuro, vira a **renda** desse
  sistema pessoal — sem acoplar schemas.

A falha do legado foi misturar pessoal e condomínio. A v3 evita isso por construção **e** reconcilia
com a infraestrutura compartilhada de receita (`RentScheduleService`/`FinancialSettings`/`MonthSnapshot`),
em vez de duplicá-la ou ignorá-la.

Objetivos: contas por prédio (água/luz/IPTU 1+, parcela embutida ou avulsa) e de nível condomínio
(funcionários, placas solares, empréstimos, manutenção, reformas, móveis — **tipos extensíveis**); dia
de vencimento variável, identificador, descrição; **atrasado** (seed "pago até X"), **suspensa**,
**adiada** (IPTU anual); **pagamento parcial**; **reserva**; **receita avulsa**; dashboard entradas+saídas
(calendário diário combinado), **saldo do mês / atrasados / saldo total / por proprietário**; **histórico
+ projeção + simulação**; **distribuição por proprietário** (household Raul & Célia).

---

## 2. Decisões travadas

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | Modelos | App `finances` novo; legado operante até remoção. |
| 2 | `Condominium` | **Só a entidade agora** (condomínio-padrão invisível) + `Building.condominium` FK + `condominium` FK nos modelos do `finances`. Isolamento/permissões multi-condomínio = futuro. |
| 3 | Pagamento | **Parcial completo** (`Payment` + `PaymentAllocation` M:N; `amount_paid`/`remaining`/`payment_status` **derivados via annotation ORM**). |
| 4 | Parcela embutida | **Conta + itens de linha** (consumo + parcela→`Installment`); cobre embutido e avulso. |
| 5 | Calendário | **Combinado por dia**, seções separadas *Aluguéis (entradas)* / *Contas a pagar (saídas)*. |
| 6 | Funcionários | Folha própria (base + variável + abatimento), autônomos (sem 13º), **só-variável** (Raymel); provisionamento pronto. |
| 7 | Materialização | **Materializar real + parcelas; projetar futuro computado; histórico do passado = linhas reais (nunca recomputado do template).** |
| 8 | Fechamento | **`CondoMonthClose` LEVE e condo-scoped** (open/closed/reopen; net/caixa/reserva/carry_forward_out) como **âncora do fold (O(1)) + auditoria**. **Não** é o `MonthSnapshot` legado (commingled, escopo diferente). **Não** é a autoridade de rent-lock (essa fica no `MonthSnapshot` legado durante a coexistência). |
| 9 | Settings/caixa | **Reusar `FinancialSettings`** (`initial_balance`/`initial_balance_date`/`rent_tracking_start_date`). Caixa do condomínio é **escopo próprio** (≠ caixa commingled legado). |
| 10 | Tipos | **Dois eixos**: `BillBehavior` (enum em `Bill`) + `Category` data-driven. |
| 11 | Popular dados | **Do zero** com seed "pago até X" (gera os atrasados **com valor esperado**, para aparecerem). |
| 12 | Reserva | **Reserva única + movimentos**; `Payment.funded_from = caixa|reserva`; **sem dupla-contagem**; **guarda de saldo negativo**. |
| 13 | Distribuição | **Resultado do mês = renda household Raul & Célia (= o próprio condomínio)**, fold com carry-forward (sem termo de reserva). **Donos externos (Tiago/Alvaro) = só exibição**. `CondominiumOwnership`/ponte versionada = futuro. |
| 14 | Proprietários | **Não-invasivo** (PROD: `owner=null`=condomínio; Tiago/Alvaro já setados). **Sem mudança no income SSOT, sem migração de owner.** Forms expõem `owner` + `prepaid_until`/`is_salary_offset`. |
| 15 | App mobile | Ignorado nesta feature. |
| 16 | Qualidade | **Gate por fase** (TDD, **≥90% em `finances`**, edge cases, 100% antes de avançar) + **gate ampliado** (coverage/mypy/pyright incluem `finances`). |
| 17 | Tempo | **Helper único `America/Sao_Paulo`** para "hoje/mês atual" (settings é `UTC`). |

---

## 3. Arquitetura geral

### 3.1 App `finances` reusando `core`
App Django novo `finances`, dependência unidirecional `finances → core`. Reusa `AuditMixin`,
`SoftDeleteMixin`, `SoftDeleteManager` (abstratos), `Condominium`, `Building`, `Apartment`, `Lease`,
`Person`, `RentScheduleService` (leitura). Migrações próprias com **dependência explícita** na migração
do `core` que cria `Condominium`. `FinancesConfig.ready()` importa `finances/signals.py`. Adicionar
`finances` a `INSTALLED_APPS`. *(Coupling ao core é real e documentado.)*

### 3.2 Materializar real, projetar futuro, ancorar o fechamento
- **Parcelas** (`Installment`): linhas concretas → projeção + geração da conta da parcela do mês.
- **Recorrentes** (água/luz/IPTU/internet/serviços): `BillingAccount` (template) → `Bill` real quando a
  fatura é lançada; futuro = projeção computada (`expected_amount`), sem criar linhas.
- **Passado = linhas reais.** Histórico/saldo de meses passados lê os `Bill`/`Payment`/`RentPayment`
  reais — **nunca recomputa o passado a partir do template** (garante histórico determinístico de
  suspensão/skip/etc.).
- **`CondoMonthClose` (âncora):** fechamento mensal **leve e condo-scoped** (net_result,
  cash_balance_end, reserve_balance_end, carry_forward_out, status). Mês "aberto" = computado on-read
  **a partir do último fechado** (O(1), re-anda só a cauda aberta). Mês "fechado" = números congelados
  (auditoria/imutabilidade); escritas de `Bill`/`Payment` nesse mês são bloqueadas pela finalização do
  módulo novo. **Não** é o `MonthSnapshot` legado (que é commingled) e **não** trava aluguel.

### 3.3 Dois eixos de tipo
- **Comportamento** (enum fechado, em `Bill`): `BillBehavior = {ONE_TIME, RECURRING, INSTALLMENT}`.
- **Classificação** (data-driven): árvore `Category` (self-FK). Novo tipo = nova linha, zero migração.

### 3.4 Separação condomínio × pessoal e a ponte
Módulo só com operacional do condomínio. `CondoMonthClose.net_result` é o output da ponte; o app
pessoal futuro consome via contrato read-only (deferido). Personal nunca entra.

---

## 4. Invariantes financeiras (pinadas, com exemplos)

> Cada invariante tem teste dedicado **com exemplo numérico trabalhado**. Dinheiro = `Decimal(12,2)`;
> **somar Decimals crus e quantizar (`ROUND_HALF_UP`) só na fronteira de saída/agregado**, num único
> helper, idêntico em todo serviço que re-deriva a mesma figura. "Hoje/mês atual" via **helper único
> `America/Sao_Paulo`** (settings é `UTC` — `timezone.now().date()` erra na virada do mês).

### 4.1 Sinal de `is_offset`
Linhas de abatimento são **armazenadas POSITIVAS** com `is_offset=True` e **subtraídas**:
`Bill.amount_total = Σ(linhas não-offset) − Σ(linhas offset)`. `CheckConstraint amount >= 0` em toda
linha. Num único helper.

### 4.2 Caixa, competência, reserva, saldo total (rótulos sem ambiguidade)
- **Resultado do mês (competência)** = receita_competência − despesa_competência (despesa por
  `Bill.competence_month`; **exclui** bills cujo `lifecycle_state ∈ {suspended, deferred, canceled}`).
- **Variação de caixa do mês** = entradas_caixa − saídas_caixa (por data de pagamento).
- **Caixa atual (condo-scoped)** = baseline + Σ(entradas_caixa) − Σ(saídas_caixa), onde **baseline** =
  `CondoMonthClose.cash_balance_end` do último mês fechado, ou `FinancialSettings.initial_balance` se
  não houver fechado (re-anda só a cauda aberta — espelha `DailyControlService._get_starting_balance`,
  mas **condo-scoped**, distinto do caixa commingled legado).
  - entradas_caixa = **`received_collectible_total`** (Σ `RentPayment.amount_paid` de leases em
    `collectible_leases`) + `IncomeEntry` recebidas + saques de reserva→caixa.
  - saídas_caixa = `PaymentAllocation` com `funded_from=caixa` + depósitos caixa→reserva.
- **Reserva** = Σ(`ReserveMovement` depósitos − saques). **Saldo total = Caixa + Reserva.**
- **Wedge (reconciliação, testada):** `Variação_de_caixa[M] = Resultado_competência[M] − Δ(contas a
  receber) + Δ(contas a pagar) ± transferências de reserva`. Os dois KPIs não podem divergir
  silenciosamente.

### 4.3 Reserva sem dupla-contagem (exemplo trabalhado)
- Transferência caixa→reserva de R$500: **um** `ReserveMovement(deposit, 500)`; caixa −500, reserva
  +500; **Saldo total inalterado** (teste pinado). Reserva→caixa: simétrico.
- Pagamento `funded_from=reserva` de R$300 do `Bill` X: `Payment(300, funded_from=reserve)` +
  `PaymentAllocation(→X, 300)` + `ReserveMovement(withdrawal, 300, bill=X)`; debita **só a reserva**
  (não conta como saída de caixa). `Bill.amount_paid` deriva **só** de `PaymentAllocation` (nunca de
  `ReserveMovement.bill`).
- **Guarda:** rejeitar saque/`funded_from=reserva` que exceda o saldo da reserva (reserva nunca
  negativa). Caixa pode ficar negativo (aviso informativo, não bloqueio).
- Ordenação determinística do ledger: `ORDER BY (movement_date, id)`.

### 4.4 Atrasado (derivado por annotation ORM, nunca flag)
`Bill` com `due_date < hoje` **E** `amount_remaining > 0` **E** `lifecycle_state = active` (exclui
suspended/deferred/canceled). `amount_total`/`amount_paid`/`amount_remaining` são **annotations
(Sum-subquery)**, não properties Python (evita N+1 / filtro em Python). **KPI "Atrasados"** =
`Σ amount_remaining` dos bills atrasados (não `amount_total`); exibido com sub-total separado do
atraso de aluguel (de `RentScheduleService.get_month_stats`). IPTU anual deferido **não** entra.

### 4.5 Receita do condomínio (filtrada por collectibility)
Para o **net/distribuição**: receita = `received_collectible_total` (recebido de cobráveis) + Σ
`effective_rental_value` de cobráveis **não pagos** (esperado) + `IncomeEntry`. **Nunca** o
`received_total` cru (somaria aluguel de Tiago/Alvaro). Guarda/teste: nenhum lease owner-set/
salary-offset tem `RentPayment` (o toggle só permite cobráveis — invariante hoje, fixado por teste).

### 4.6 Funcionário-inquilino (Rosa, lease 850/205) — abatimento contado UMA vez (exemplo)
- A lease 205 tem `is_salary_offset=true` → **excluída da receita** (não entra em
  `collectible_leases`).
- A folha da Rosa = `Bill(behavior=RECURRING, employee=Rosa)` com linhas: `base` (+, ex. R$X),
  `variável` (+, ex. R$Y), `abatimento` (−, `is_offset`, = **`effective_rental_value` da lease 205 no
  mês de competência**, ex. R$1000). `amount_total = X + Y − 1000` (caixa pago à Rosa).
- **Invariante (clean()/serviço + teste):** para `Employee` com lease salary-offset, a linha de
  abatimento **deve igualar** o `effective_rental_value` da lease no mês. O aluguel é contado **uma vez
  só**: não é receita (excluído) e não é despesa separada; só reduz o caixa pago à funcionária.

### 4.7 Distribuição + carry-forward (fold, on-read, ancorado)
- **Resultado do mês = renda do household Raul & Célia (= o próprio condomínio).** Fold sequencial
  ancorado no último `CondoMonthClose`: `disponível[M] = max(0, net[M] + carregado_in[M])`;
  `carregado_out[M] = min(0, net[M] + carregado_in[M])`; `carregado_in[M+1] = carregado_out[M]`.
- **Sem termo de reserva no fold.** Reserva é transferência de caixa (caixa↔reserva), **não reduz a
  distribuição** (o dinheiro continua sendo do household, só muda de "pote"). *(Removida a noção de
  "reserva é a única dedução" da v2 — era contraditória.)*
- **Âncora do fold + janela pré-tracking:** o fold começa no **primeiro mês com fechamento/atividade do
  condomínio**, não antes de `rent_tracking_start_date` (2026-06). Meses antes do tracking têm receita
  estruturalmente zero (`collectible_leases` vazio) — **não** entram no fold (evita net negativo
  espúrio). Exemplo pinado: mês sem aluguel rastreado + com bill → tratado como fora da janela / net
  isolado, não acumulado.
- Donos externos (Tiago/Alvaro) **não entram** em net/caixa/distribuição — só exibição (agregação
  owner→Σ`effective_rental_value` a partir de `displayable_leases`).

### 4.8 Pagamentos
`sum(PaymentAllocation.amount por Payment) == Payment.amount` (serviço + teste). **Over-allocation
rejeitada** (v1 não cria crédito). **Split caixa+reserva = dois `pay()`** (dois `Payment`), explícito.

---

## 5. Modelo de dados

Convenções: `(AuditMixin, SoftDeleteMixin, models.Model)`, managers duplos, `DecimalField(12,2)`,
partial unique `condition=Q(is_deleted=False)`, `CheckConstraint` ≥ 0, `clean()` (PT), `on_delete`
`PROTECT` em FKs de referência / `CASCADE` em filhos / `SET_NULL` onde indicado.

### 5.1 `core` (adições/alterações)
- **`Condominium`** *(novo)* — `name`, `notes`. **Registro padrão** via migração (invisível na UI).
- **`Building.condominium`** — FK nova, **migração faseada** (nullable → data-migration backfill p/ o
  padrão → non-null + index). Consumidores de `Building` (Apartment/Lease) inalterados.
- **`Apartment.owner`** — já existe. **Não-invasivo (§6):** `owner=null`=condomínio; exposto no form.

### 5.2 App `finances`

**Classificação**
- **`Category`** — `condominium` FK, `name`, `parent` (self-FK), `color`, `sort_order`.
  `unique(condominium, parent, name)` parcial.

**Fontes**
- **`BillingAccount`** (recorrente) — `condominium` FK, `building` FK (nullable=nível-condomínio),
  `category` FK, `name`, `external_identifier`, `description`, `default_due_day`, `expected_amount`
  (projeção/seed), `lifecycle_state = {active, suspended, deferred, ended}`, `tracking_start_month`
  (seed; 1º dia), `end_date` (nullable), `notes`. **Suspensão** = enquanto `suspended`, não gera novos
  `Bill`; bills passados (reais) intactos → histórico correto sem novo modelo.
- **`Employee`** (folha) — `condominium` FK, `person` FK (nullable), `name`, `role`,
  `payment_type = {fixed, variable, mixed}`, `base_salary` (nullable/0), `default_due_day`, `lease` FK
  (nullable, `SET_NULL`), `is_active`, `notes`. **Fim de lease:** abatimento para quando
  `lease.is_deleted=True` (detecção por `is_deleted`, **não** por FK null — soft-delete não dispara
  SET_NULL).
- **`InstallmentPlan`** — `condominium` FK, `building` FK (nullable), `category` FK, `description`,
  `total_amount`, `installment_count`, `start_due_date`, `default_due_day`,
  `lifecycle_state = {active, paid, deferred, canceled}`, `embedded` (bool),
  `linked_billing_account` FK (nullable, p/ embutido).
- **`Installment`** — `plan` FK (`CASCADE`), `number`, `due_date`, `amount` (**schedule**; projeção).
  `unique(plan, number)` parcial. Na realização, `Installment.amount` é sincronizado com
  `BillLineItem.amount` (realizado) — ver §8.
- **`BillSkip`** — `billing_account` FK (`CASCADE`), `reference_month` (1º dia).
  `unique(billing_account, reference_month)`. Pula geração de um mês. (Sem SoftDelete; hard delete des-pula.)

**Pagável**
- **`Bill`** — `condominium` FK, `building` FK (nullable), `category` FK, `competence_month` (1º dia),
  `due_date`, `issue_date` (nullable), `description`, `external_identifier` (nullable),
  `behavior` (`BillBehavior`), fontes nulláveis (`billing_account`/`installment`/`employee`),
  `lifecycle_state = {active, suspended, deferred, canceled}` (**armazenado**), `attachment` (nullable),
  `notes`. **Derivados via annotation** (Sum-subquery, não property): `amount_total` (Σ linhas com sinal
  de offset), `amount_paid` (Σ alocações), `amount_remaining`, `payment_status ∈ {open, partial, paid}`,
  `is_overdue`. Unique parciais p/ geração idempotente: `(billing_account, competence_month)`,
  `(installment)`, `(employee, competence_month)`.
- **`BillLineItem`** — `bill` FK (`CASCADE`), `category` FK, `description`, `amount` (≥0; **realizado**
  — fonte de verdade p/ histórico/caixa), `installment` FK (nullable; parcela embutida),
  `is_offset` (bool). Sinal: positivo + subtraído (§4.1).

**Pagamentos / reserva / receita**
- **`Payment`** — `condominium` FK, `payment_date`, `amount`, `method` (opcional),
  `funded_from = {caixa, reserve}`, `reference` (opcional), `notes`.
- **`PaymentAllocation`** — `payment` FK (`CASCADE`), `bill` FK (`PROTECT`), `amount`.
- **`IncomeEntry`** — `condominium` FK, `building` FK (nullable), `category` FK (nullable),
  `description`, `amount`, `income_date`, `is_received`, `received_date` (nullable), `notes`.
- **`Reserve`** — `condominium` FK, `name`, `notes`. *(Uma por condomínio; modelo permite N no futuro,
  sem UI de seleção agora.)*
- **`ReserveMovement`** — `reserve` FK (`CASCADE`), `kind = {deposit, withdrawal}`, `amount`,
  `movement_date`, `bill` FK (nullable — saque p/ pagar conta vs `bill=null` = transferência p/ caixa),
  `reference`/`notes`. Ledger único autoritativo deriva caixa/reserva.

**Fechamento (âncora leve)**
- **`CondoMonthClose`** *(AuditMixin; **sem** SoftDelete)* — `condominium` FK, `reference_month` (1º
  dia), `status = {open, closed}`, `closed_at` (nullable), `net_result`, `cash_balance_end`,
  `reserve_balance_end`, `carry_forward_out` (Decimal, ≤ 0), `breakdown` (JSONField mínimo p/ exibição).
  `unique(condominium, reference_month)`. Congela os números do mês fechado (auditoria) e semeia o fold/
  caixa do próximo mês. **Reopen** (status→open) recomputa em cascata os meses seguintes ainda abertos.
  **Não trava aluguel** (rent-lock = `MonthSnapshot` legado).

### 5.3 Diagrama
```
core: Condominium(padrão) ─ Building(condominium) ─ Apartment(owner→Person) ─ Lease ─ RentPayment (income SSOT, read)
      MonthSnapshot legado (rent-lock + caixa commingled) — coexiste, NÃO duplicado/usado pelo finances p/ caixa condo
finances:
 ├─ Category(self-FK)
 ├─ BillingAccount ─┐  Employee ─┐  InstallmentPlan ─┐  BillSkip
 │                  │            │    └─ Installment   │
 │                  ▼            ▼                     ▼
 │                Bill ◄──────────── (source FKs nulláveis) · behavior · lifecycle_state
 │                 ├─ BillLineItem(category, amount realizado, installment?, is_offset)
 │                 └─ amount_total/paid/remaining/payment_status/is_overdue (ANNOTATIONS)
 ├─ Payment(funded_from) ─ PaymentAllocation(→Bill)
 ├─ IncomeEntry
 ├─ Reserve ─ ReserveMovement(→Bill? | →caixa)
 └─ CondoMonthClose (âncora leve do fold/caixa + auditoria; open/closed/reopen)
(passado = linhas reais; futuro = projeção computada; fold ancorado no último CondoMonthClose)
(CondominiumOwnership / rateio individual / ponte versionada = futuro)
```

---

## 6. Receita do condomínio e proprietários (não-invasivo)

Confirmado no PROD (§17): kitnets de **Raul & Célia já são `owner=null`** (= condomínio) e eles **não
existem como `Person`**; só **Tiago** (`836/101,103`) e **Alvaro** (`836/200,203`) têm `owner` setado;
único salary-offset é `850/205` (Rosa); `836/113` (Adriana) tem `prepaid_until=null` (a registrar). A
regra atual `owner IS NULL = condomínio` **já produz a receita certa**.

**Decisão: NÃO-INVASIVA — zero mudança no income SSOT, resultado idêntico, household único.**
- **Receita** = kitnets `owner=null` (escopo via `Building.condominium`) = exatamente
  `RentScheduleService.collectible_leases` (owner IS NULL − salary_offset − prepaid). Para o caixa/net,
  usar **`received_collectible_total`** (novo helper read em `RentScheduleService`, additivo) e
  `effective_rental_value`.
- **Donos externos** (Tiago/Alvaro) = `Person` com `Apartment.owner` setado → já saem da receita e
  aparecem em `displayable_leases` (`owner_repass`). **Só exibição** (agregação owner→Σ por dono).
- **Resultado do mês** = renda household Raul & Célia (= o condomínio); sem `CondominiumOwnership` v1.
- **Forms:** expor `owner` (Apartamento) e `is_salary_offset`/`prepaid_until`/vínculo de funcionário
  (Locação) — serializers já têm os campos; **os MODAIS de form não os renderizam** (Fase 1b), com
  gating `is_staff` e atualização dos testes de form existentes.

**Multi-condomínio (futuro, sem refactor):** tenancy = `Condominium` + `Building.condominium` (agora).
`owner=null` nunca é ambíguo (escopa pelo prédio→condomínio). Rateio individual (Persons de Raul/Célia
+ `CondominiumOwnership`) e permissões = aditivos. *(Nota: `FinancialSettings` é singleton global, **não**
condo-scoped — ver §15.)*

---

## 7. Mapeamento dos casos reais

| Caso | Modelagem |
|---|---|
| Água/luz/IPTU 1+ por prédio, valor variável | `BillingAccount` → `Bill` do mês (admin digita total) |
| Dia de vencimento variável | `Bill.due_date` por ocorrência (default `default_due_day`, clamp) |
| Nº id + descrição | `external_identifier` + `description` |
| Parcela **embutida** (1000 = 600 consumo + 400 parcela) | `Bill` com 2 `BillLineItem` (consumo + parcela→`Installment` de plano `embedded=True`) |
| Parcela **avulsa** | `InstallmentPlan(embedded=False)` → 1 `Bill`/parcela |
| IPTU anual a reparcelar (não é atraso) | `lifecycle_state=deferred`; `convert_deferred` atômico → `InstallmentPlan` (§8) |
| Água suspensa | `lifecycle_state=suspended` → não gera novos `Bill`; passado intacto |
| Seed "pago até X" | `tracking_start_month`; gera bills com linha de valor esperado → aparecem como atrasados |
| Empréstimo (proventos + quitação) | `InstallmentPlan` (quitação) + `ReserveMovement(deposit)`/`IncomeEntry` (proventos) |
| Rosa (850/205, fixo+variável+abatimento) | `Employee(payment_type=mixed, lease=205)`; folha c/ linha abatimento = `effective_rental_value` (§4.6) |
| Raymel (só variável) | `Employee(payment_type=variable, base_salary=null)` |
| Adriana (836/113 pré-pago) | `Lease.prepaid_until` (via form); `is_prepaid_for_month` exclui por mês |
| Tiago/Alvaro | `Apartment.owner` setado; **só exibição** (agregação por dono) |
| Raul & Célia | kitnets `owner=null` → receita do condomínio (household); **sem `CondominiumOwnership` v1** |
| Receita avulsa | `IncomeEntry` |
| Reserva | `Reserve` + `ReserveMovement`; `Payment.funded_from=reserve` |
| Pagamento parcial / marcar pago | `Payment` + `PaymentAllocation` |
| Saldo/atrasado/total/por dono/histórico/projeção/simulação | serviços §8 (on-read, ancorado em `CondoMonthClose`) |

---

## 8. Regras de negócio e serviços

Stateless em `finances/services/`. PT ao usuário, EN nos logs. `@transaction.atomic` +
`select_for_update` em leitura-modificação. "Hoje" via helper SP (§4).

- **`BillGenerationService.ensure_month_bills(year, month)`** — gera (idempotente, **race-safe**:
  `get_or_create` na unique parcial tolerando `IntegrityError`, ou `select_for_update`) os `Bill`
  esperados: `BillingAccount` ativas (não suspensa/deferida, dentro de `tracking_start_month..end_date`,
  respeitando `BillSkip`), parcelas (`Installment` de planos **não-embutidos**), folha. **Pula planos
  embutidos** (parcela vira linha no `Bill` da conta recorrente). Gerador de datas = função pura
  reusando `RentScheduleService.clamp_due_day` (31→último dia). **Seed:** ao criar conta com
  `tracking_start_month`, gera de `tracking_start_month`..mês atual **com linha de valor esperado**
  (`expected_amount`) → `amount_remaining>0` → aparecem como atrasados a preencher/ajustar.
  *(Fase 2 entrega recorrentes+seed; Fase 3 ESTENDE com installment+folha.)*
- **`BillService.create_with_lines(...)`** — criação de `Bill` + `BillLineItem`s orquestrada no
  **serviço** (não em serializer nested writable). Endpoint dedicado (`bills/` create chama o serviço,
  ou `bills/{id}/lines`).
- **`BillPaymentService.pay(bill, payment_date, amount=None, funded_from='caixa')`** — `Payment` +
  `PaymentAllocation` (total se `amount=None`; parcial se menor; **over-allocation rejeitada**).
  `funded_from=reserve` cria `ReserveMovement(withdrawal, bill=…)` com **guarda de saldo**. Estorno =
  soft-delete. Bloqueia mês **fechado** (`CondoMonthClose.status=closed`) para mark **e** unmark.
  `@transaction.atomic`+`select_for_update`. *(Aluguel permanece binário via `RentPayment` — assimetria
  intencional.)*
- **`CondoBalanceService`** — §4 (resultado competência, variação de caixa, caixa condo-scoped ancorado,
  reserva, saldo total, atrasados via annotation, wedge). Um único ledger walk; baseline do último
  `CondoMonthClose`.
- **`CondoProjectionService.project(months=12)`** — futuro computado: receita projetada (cobráveis com
  `is_prepaid_for_month` por mês — Adriana jun→jul/2027 — + `IncomeEntry`) − saídas (`Installment`
  futuras + `expected_amount` respeitando `end_date`/`BillSkip`/suspensão + folha). **Dedup embutido:**
  `expected_amount` exclui a parcela; parcela só via plano. Acumulado = fold ancorado. `is_actual=mês<atual`.
- **`CondoSimulationService`** — efêmero (deltas em memória; sem persistência).
- **`CondoCalendarService.combined_month(...)`** — por dia: entradas (aluguéis via RentScheduleService)
  + saídas (`Bill`/parcelas com `due_date` no dia) + stats. *(Supera o legado `DailyControlService`;
  não wirar ambos no mesmo dashboard.)*
- **`CondoMonthCloseService`** — `close(year, month)` (snapshot net/caixa/reserva/carry_forward_out;
  cronológico; sem gap), `reopen(year, month)` (recomputa cascata os meses abertos seguintes).
- **`OwnerDistributionService.compute(year, month)`** — consome **`CondoBalanceService.result_of_month`**
  (sem re-derivar — DRY); fold/carry-forward (§4.7); household Raul & Célia; agregação de donos externos
  por `displayable_leases`. *(Rateio individual + ponte versionada = futuro.)*
- **`InstallmentPlanService.convert_deferred(...)`** — atômico: fecha o item deferido (IPTU anual,
  estado terminal **excluído de TODAS as somas**) e cria o `InstallmentPlan` (`total == valor deferido`;
  nem duplica nem some).

---

## 9. API

Base `/api/finances/...`. DRF `ModelViewSet` + `FinancialReadOnly` (autenticado lê, `is_staff` escreve);
agregações/admin via bare `ViewSet` + `IsAdminUser`. `CustomPageNumberPagination`. Serializers dual;
Decimal string; validação PT; `competence_month`/`reference_month` = 1º dia.

CRUD: `finance-categories`, `billing-accounts`, `bill-skips`, `employees`, `installment-plans`,
`installments`, `bills`, `payments`, `income-entries`, `reserves`, `reserve-movements`,
`condo-month-closes`. Ações: `bills/create_with_lines` (ou `bills/{id}/lines`), `bills/{id}/pay`,
`bills/bulk_pay`, `bills/{id}/suspend|defer|cancel|reactivate`, `bills/generate_month`,
`installment-plans/{id}/convert_deferred`, `reserves/{id}/deposit|withdraw`,
`condo-month-closes/{close|reopen}`. Dashboard (bare):
`finance-dashboard/{overview,monthly_balance,overdue,by_owner,by_category,combined_calendar}`,
`finance-cash-flow/{projection,simulate}`. *(Sem `condominium-ownerships`; ponte versionada = futuro.)*

---

## 10. Frontend / Dashboard

Next.js 14, **TanStack Query v5**, **Recharts v3.3** (já a stack do repo — React 18.3/Next 14.2
verificados; não é risco), Shadcn/Radix/Tailwind, Zod 4 + RHF, Zustand (auth). Hooks DRF, query-keys
centralizados, `useCrudPage`, formatters TZ-safe, escrita gated em `is_staff`, componentes pequenos.
Primitivos espelhando `controle-financeiro`: `StatCard`, `AmountDisplay`, `ChartCard`,
`useMonthNavigation` ({year,month} na query key, prefetch ±1, **`placeholderData: keepPreviousData`** —
usar `useQuery`, **não** `useSuspenseQuery** (que descarta placeholderData)).

Telas: (1) **Dashboard** — calendário combinado (entradas/saídas separadas por dia, toggle de pago
otimista); KPIs **Caixa / Reserva / Resultado do mês / Atrasados / Saldo total**; resultado do mês do
**household (Raul & Célia)**; **seção informativa de donos externos**; donut por categoria
(**gráficos = não-blocking no gate**, a tabela é o artefato load-bearing). (2) Contas (CRUD + lançar
fatura + linhas + suspender/deferir). (3) Folha. (4) Reserva. (5) Projeção 12 meses (tabela acumulada +
badge Real/Projetado + ComposedChart) + simulador.

---

## 11. Cache e signals (cross-app)

**Bloco único de constantes de prefixo** (consumido por `@cache_result` E pelos globs de signal —
`invalidate_pattern` monta `f'{prefix}:1:{pattern}'`; um char de diferença silenciosamente não-invalida):
`finance-dashboard`, `finance-cash-flow`, `finance-projection`.

- `finances/signals.py` (em `FinancesConfig.ready()`): `post_save`+`post_delete` nos modelos do
  `finances` invalidando `finance-*` (soft-delete dispara `post_save`).
- **Cross-app (NET-NEW, não "additivo"):** `RentPayment`/`FinancialSettings` já chamam
  `_invalidate_financial_caches` (estender lá, DRY). Mas **`Apartment` e `Lease` usam
  `invalidate_related_caches` (model-key) e NÃO têm hook financeiro** — adicionar receivers (ou estender)
  para invalidar `finance-*` em escritas de `Apartment`/`Lease`/`Apartment.owner`. Adicionar também
  **`RentAdjustment`/pending_rental_value** (muda `effective_rental_value` → projeção) e
  **`MonthSnapshot` finalize/rollback**. Guard de over-match no glob.
- **Calendário combinado** tem duas metades (aluguel via core, bills via finances): um toggle de
  aluguel invalida só o lado do aluguel → **deixar o `combined_calendar` sem cache** (ou TTL curto, como
  o calendário de aluguel 30s) para evitar dupla-invalidação.
- Regressão: garantir que o fluxo mobile `toggle_rent_payment` e a invalidação `dashboard-late-payment*`
  continuam disparando após as edições aditivas.

---

## 12. Testes e gate de qualidade por fase

Três camadas (pytest + pytest-django, model-bakery), `filterwarnings=error`, mock só de fronteiras
externas. **Gate ampliado (Fase 1, primeiro item):** adicionar `finances` a `--cov`/`[coverage:run]
source`/`pyproject [tool.coverage.run] source`/`pyrightconfig.json include`; mudar `mypy core/` →
`mypy core/ finances/`; rodar `--cov=finances --cov-fail-under=90` nas fases do `finances` (≥90%
**standalone** do app, não só combinado). `make_<model>()` por modelo novo (+ `make_condominium()`,
`make_building(condominium=...)` default).

Unit: serviços com **edge cases** (§18) sob `@freeze_time`. Integration: endpoints (CRUD + ações +
filtros, paginação, dual serializer, soft-delete, matriz `FinancialReadOnly`). Testes confirmando
receita (`owner=null`) e seção de externos via `RentScheduleService` (sem mudança no SSOT).

**Gate por fase:** cada fase só "fecha" com TODOS os testes verdes, **≥90% em `finances`**, `ruff check
&& ruff format --check && mypy core/ finances/ && pyright && pytest`, **zero erros e zero warnings**,
business logic verificada, **incluindo polish/itens não-blocking** (exceto gráficos, marcados
não-blocking). Não se avança com bug/gap.

---

## 13. Migrações e dados

- **Ordenação pinada (Fase 1a, sub-fase de maior risco PROD):** (1) migração `core` cria `Condominium`
  + data-migration do registro padrão + `Building.condominium` **faseada** (nullable → backfill →
  non-null + index); (2) migração inicial do `finances` **depende explicitamente** da migração do core
  que cria `Condominium`. Testar forward **e** backward; backfill idempotente.
- **Backup antes de qualquer migração destrutiva:** `python scripts/backup_db.py` (PROD = Supabase
  `kaukiwhbmvnjjekodcmq`; local desatualizado).
- **Sem migração/refactor de owner** (não-invasivo). **Sem seed de dados/categorias** — o admin cria
  tudo (cada prédio terá água/luz/IPTU; nenhum dado pré-cadastrado).
- `python-dateutil` já existe; **sem** `django-treebeard`/`django-money` agora.

---

## 14. Faseamento da implementação

Cada fase é TDD e só avança após o gate (§12). **Contratos de dados entre fases (DRY):** Fase 6
consome `CondoBalanceService.result_of_month` (não re-deriva net); Fase 5 consome `Installment`/campos
de embutido da Fase 3; Fase 4 (caixa) consome `received_collectible_total`/`CondoMonthClose`.

1a. **Infra + migração (maior risco PROD):** app `finances` + `INSTALLED_APPS` + `FinancesConfig.ready()`
    + wiring de signals; `Condominium`(padrão) + `Building.condominium` faseada + `condominium` FK nos
    modelos do `finances`; **gate ampliado** (coverage/mypy/pyright incluem `finances`); helper TZ SP;
    factories base. Backup + teste forward/backward.
1b. **Forms:** expor `owner` (Apartamento) e `is_salary_offset`/`prepaid_until`/funcionário (Locação),
    gating `is_staff`, atualizar testes de form.
2. **Categorias + Contas + Pagamentos + Calendário + Atrasados:** `Category`, `BillingAccount`, `Bill`,
   `BillLineItem`, `BillSkip`, `Payment`/`PaymentAllocation`; `BillGenerationService` (recorrentes +
   seed/atrasado), `BillService.create_with_lines`, `BillPaymentService` (parcial, guarda); annotations
   (amount_*/overdue); `lifecycle_state` × `payment_status`; `CondoCalendarService` + calendário
   combinado + **lista de atrasados** (derivável só de `Bill`). Cache cross-app (§11). *(KPIs de dinheiro
   ficam para a Fase 4.)*
3. **Parcelas + Folha:** `InstallmentPlan`/`Installment` (embutido+avulso, dedup, sync realizado),
   `convert_deferred`, `Employee` (variável-only, abatimento §4.6, fim de lease via `is_deleted`);
   ESTENDE `ensure_month_bills` com installment+folha.
4. **Saldo + Reserva + Receita avulsa + Fechamento:** `CondoBalanceService` (invariantes §4 +
   `received_collectible_total`), `Reserve`/`ReserveMovement` (sem dupla-contagem + guarda),
   `IncomeEntry`, `CondoMonthClose` + `CondoMonthCloseService` (close/reopen, âncora do fold); KPIs no
   dashboard.
5. **Projeção + Simulação:** `CondoProjectionService` (dedup, prepaid por mês, ancorado),
   `CondoSimulationService`; tabela + ComposedChart (gráfico não-blocking).
6. **Distribuição por proprietário:** `OwnerDistributionService` (fold/carry-forward, consome Fase 4) +
   agregação por dono (de `displayable_leases`) + cards "por proprietário" + seção de externos.

---

## 15. Fora de escopo agora (YAGNI, arquitetura pronta)

App pessoal + ponte versionada/contract_version; isolamento/permissões multi-condomínio (entidade+FK
prontas; **`FinancialSettings` é singleton global, NÃO condo-scoped** — `CondoBalanceService` não é
multi-condo-safe até isso mudar); rateio individual/`CondominiumOwnership`; rent-lock unificado (fica no
`MonthSnapshot` legado até a remoção); provisionamento 13º/férias; ledger partidas dobradas;
`django-money`/`django-treebeard`; conciliação bancária; OCR; múltiplas reservas com UI; `IncomeEntry`
recorrente; colunas especulativas. *(Calendário novo supera o `DailyControlService` legado — não wirar
os dois.)*

---

## 16. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Coexistência com `MonthSnapshot`/caixa commingled | Caixa do condo é escopo próprio ancorado em `CondoMonthClose`; rent-lock fica no legado; documentado como escopos distintos (não dual-authority) |
| Caixa/receita inconsistentes | `received_collectible_total` (filtrado); baseline do último `CondoMonthClose`; wedge identity testada |
| Dupla-contagem caixa/reserva/embutido | Invariantes §4 com exemplos + ledger único; dedup explícito; guarda de reserva |
| Histórico não-determinístico | Passado = linhas reais (nunca recomputado); `CondoMonthClose` congela + audita meses fechados |
| Cache velho cross-app (owner/lease/ajuste) | Receivers NET-NEW em `Apartment`/`Lease`/`RentAdjustment`/`MonthSnapshot`; constantes de prefixo únicas; combined_calendar sem cache |
| Gate não-vinculante p/ `finances` | Ampliar coverage/mypy/pyright na Fase 1a; ≥90% standalone |
| TZ UTC vs mês SP | Helper único SP; teste de virada de mês |
| `due_day`=31 em meses curtos | `clamp_due_day` reusado (testado) |
| Concorrência pagamento/geração | `select_for_update`/`get_or_create` race-safe + invariantes |
| Migração faseada `Building.condominium` em PROD | Backup; nullable→backfill→non-null; forward/backward; Fase 1a isolada |

---

## 17. Decisões resolvidas + apêndice de verificação PROD

**Resolvidos:** owner **não-invasivo**; rateio = **household único Raul & Célia**; **donos externos =
só exibição**; **API `/api/finances/...`**; **sem seed**; multi-condomínio via `Condominium`+
`Building.condominium`; fechamento via **`CondoMonthClose` leve condo-scoped** (não o `MonthSnapshot`
legado); caixa condo-scoped; gate ampliado; TZ SP.

### Apêndice — verificação PROD (Supabase `kaukiwhbmvnjjekodcmq`, 2026-06-06, somente leitura)
- **Prédios:** 836 (kitnets 101–214) e 850 (kitnets 100–206). *(7777/19999 = lixo soft-deleted.)*
- **`Apartment.owner` setado só em:** 836/101, 836/103 → **Tiago** (id 2); 836/200, 836/203 → **Alvaro**
  (id 3). Demais = `owner=null` (= condomínio = household Raul & Célia).
- **`Person`:** Tiago(2,is_owner), Alvaro(3,is_owner), Rosa(5,is_employee), Alessandra(7), Camila(6),
  Junior(4), Rodrigo(1). **Raul e Célia NÃO existem como Person.**
- **Salary-offset:** único lease `850/205` (Rosa), `is_salary_offset=true` (rental 1000,00).
- **Prepaid:** `836/113` (Adriana) `prepaid_until=null` — a registrar via form.
- **`FinancialSettings`:** `initial_balance=0,00`, `initial_balance_date=2026-03-01`,
  `rent_tracking_start_date=2026-06-01`.
- **Implicação:** `owner IS NULL = condomínio` já produz a receita certa → confirma o não-invasivo. A
  janela do fold/caixa começa ~2026-06 (rent tracking), não 2026-03.

---

## 18. Apêndice — edge-cases por fase (testes RED)

Lista verbatim de casos que cada fase **deve** cobrir antes de fechar o gate (não exaustiva; adicionar
os que surgirem):

- **Datas/geração:** `due_day=31` em fev/meses de 30; `BillSkip` num mês; seed cruzando virada de ano;
  `end_date` cutoff; suspensão (mês suspenso não gera bill; passado intacto); virada de mês na TZ SP.
- **Pagamento:** parcial-depois-total (`Σ alloc == payment.amount`); over-allocation rejeitada;
  `funded_from=reserve` não conta como saída de caixa; split caixa+reserva = dois `pay()`; estorno
  (soft-delete) recompõe `amount_remaining`; bloqueio de mark/unmark em mês fechado.
- **Reserva:** transferência caixa↔reserva nета zero no saldo total; saque > saldo da reserva rejeitado;
  `bill=null` (→caixa) vs `bill` setado (pagamento) distintos; ordenação determinística.
- **Atrasado/overdue:** `amount_remaining>0` + `due_date<hoje` + `active`; deferido/suspenso excluídos;
  seed gera atrasado visível (valor esperado>0); KPI = Σ remaining.
- **Parcelas:** embutida não duplica na projeção (consumo via `expected_amount`, parcela via plano);
  realizado (`BillLineItem.amount`) ≠ schedule (`Installment.amount`) → sync; última parcela marca plano
  `paid`; `convert_deferred` sem duplicar/perder e item deferido vira estado terminal fora de todas as
  somas.
- **Folha:** variável-only (sem base) gera bill correto; Rosa — abatimento = `effective_rental_value`,
  lease 205 fora da receita, contado uma vez; fim de lease (`is_deleted`) para o abatimento no mês.
- **Receita/collectibility:** `received_collectible_total` ignora aluguel de externos; nenhum lease
  owner-set/salary-offset tem `RentPayment`; prepaid (Adriana) jun→jul/2027.
- **Fold/fechamento:** carry-forward com net≤0; âncora no último `CondoMonthClose`; janela pré-tracking
  (mês sem aluguel rastreado + bill); reopen recomputa cascata.
- **Distribuição:** household = condomínio; externos fora do net (só exibição); per-owner aggregation
  (Tiago vs Alvaro) de `displayable_leases`/`effective_rental_value`.
- **Estruturais:** prédio sem bills; mês sem leases; soft-deleted Bill/Payment excluído dos totais;
  `is_offset` mantém `amount_total>=0`; quantização (somar cru, quantizar na fronteira) — sem off-by-cent
  entre dashboard e projeção.
- **Cross-app cache:** toggle de aluguel/owner/lease/ajuste invalida `finance-*`; combined_calendar
  reflete toggle sem cache stale; mobile `toggle_rent_payment` e `dashboard-late-payment*` intactos.

---

> **Próximo passo:** esta v3 está pronta para `/prompt-writing` → prompts numerados (TDD, ≥90% em
> `finances`, gate por fase, edge-cases do §18), na ordem do §14 (1a → 1b → 2 → 3 → 4 → 5 → 6).
