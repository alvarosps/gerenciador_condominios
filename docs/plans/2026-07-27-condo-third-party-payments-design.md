# Design — Fase 2: pagamentos e compras de terceiros (filhos, genro)

**Data:** 2026-07-27 (**rev. 2** — após duas revisões adversariais independentes: 3 Critical + 6 Important no desenho, 4 Critical + 5 Important no plano; todos incorporados — ver §10.1 e §10.2)
**Status:** em aprovação
**Módulo:** `finances/` (backend) + `frontend/app/(dashboard)/finances/`
**Antecede:** `docs/plans/2026-07-26-condo-bills-operational-redesign-design.md` §7 (esboço de 1 parágrafo, aqui detalhado e **corrigido** em 2 pontos — ver §10)

---

## 1. Problema

Os proprietários (Raul & Célia) não têm cartão próprio. Filhos e genro pagam contas do condomínio e compram coisas para eles usando os cartões deles. Hoje isso não existe no sistema: uma conta paga pelo Alvaro fica indistinguível de uma paga pelo caixa, e as compras não aparecem em lugar nenhum.

Consequências práticas:

- **O caixa mente**: uma conta de luz paga pelo genro é registrada como saída de caixa que nunca aconteceu.
- **A dívida com a família é invisível**: não há como saber quanto se deve a cada pessoa, nem desde quando.
- **O acerto é manual**: hoje é feito por fora, de cabeça ou em planilha.

Referência aprovada pelo usuário: o módulo *family loans* do app `controle-financeiro`, que é como ele já controla o que tem **a receber**. Aqui a direção é invertida — os proprietários **devem** ao terceiro.

## 2. Decisões de escopo (respondidas pelo usuário em 2026-07-27)

| Decisão | Escolha |
| --- | --- |
| Model de pessoa | **Reusar `core.Person`** (não criar `finances.ThirdParty`) |
| Escopo das cobranças | **Ambos**: pagamento de conta do condomínio **e** compras avulsas/parceladas |
| Acerto/reembolso | **FIFO automático, computado** — nunca persistido |
| Cartão emprestado (direção inversa) | **Fora do escopo** — é controle pessoal, vive no `controle-financeiro` |

## 3. A decisão arquitetural central

O esboço da §7 propunha um model novo `ThirdPartyCharge` "fora do fluxo de contas do condomínio". **Isso está errado e seria uma duplicação grave**, por uma razão que o esboço não considerou:

> `Employee` já é exatamente este caso. Docstring vigente: *"Payroll registry. The monthly payment is a `Bill(employee=…)` with lines"*.

Dívida do condomínio com uma **pessoa** já é modelada como `Bill`. O `Bill` já tem três FKs de origem mutuamente exclusivas (`billing_account`, `installment`, `employee`), cada uma com sua `UniqueConstraint` parcial. Uma compra feita por terceiro é a mesma forma: dinheiro que o condomínio deve a alguém, com competência, vencimento, linhas e ciclo de vida.

**Decisão: a compra do terceiro é um `Bill` com uma quarta FK de origem, `paid_by_person`.** Não existe `ThirdPartyCharge`.

O que isso compra de graça (zero código novo):

- linhas, offsets, anexo, categorias;
- o guard de mês fechado;
- o extrato, a consolidação de dívida e o cockpit, que leem `Bill` sem saber a origem;
- competência × caixa: a compra entra no resultado do mês pela competência, como qualquer despesa.

**O que NÃO vem de graça** (dois erros da versão inicial deste documento, corrigidos após revisão adversarial):

1. **Ciclo de vida**: suspender/cancelar/apagar uma compra **não funciona** pelo caminho normal — `assert_not_paid` bloqueia bill com pagamento vivo e a compra nasce paga. Ver §4.3.1.
2. **Parcelamento NÃO é reuso do `InstallmentPlan`.** A afirmação inicial ("plano avulso já resolve") é falsa: `InstallmentPlanService.materialize_schedule` cria só linhas `Installment`; as `Bill`s nascem depois, num **job mensal** (`BillGenerationService._generate_installment_bills:221-228`) a partir de um `defaults` **hardcoded**, sem passagem de `paid_by_person` — e nascem **não pagas**, contradizendo "a compra nasce paga". Ver §4.6.

**O que é genuinamente novo** são apenas duas coisas: marcar **quem financiou** um pagamento, e **computar o extrato por pessoa**.

### 3.1 Os dois lados da dívida com a pessoa

| Situação | Como é modelado | Efeito no caixa |
| --- | --- | --- |
| Terceiro paga uma conta do condomínio (água, luz, IPTU) | `Payment(funded_from=THIRD_PARTY, paid_by=Person)` alocado à `Bill` existente | **Não sai do caixa.** A conta é quitada; a dívida migra da concessionária para a pessoa |
| Terceiro compra algo para os proprietários | `Bill(paid_by_person=Person)` + `Payment(funded_from=THIRD_PARTY, paid_by=<a mesma pessoa>)` que a quita | **Não sai do caixa.** Nasce já devida à pessoa |
| Proprietários acertam com a pessoa | `ThirdPartySettlement` (model novo, o único) | **Sai do caixa** de verdade |

Uma compra de terceiro nasce **paga** (ele já pagou no cartão dele). Por isso o `Bill` vem acompanhado do `Payment` que o quita, na mesma transação — senão ela apareceria como "a pagar" no cockpit, o que é falso.

## 4. Modelo de dados

### 4.1 `FundedFrom.THIRD_PARTY` (valor novo no TextChoices)

```python
class FundedFrom(models.TextChoices):
    CAIXA = "caixa", "Caixa"
    RESERVE = "reserve", "Reserva"
    THIRD_PARTY = "third_party", "Terceiro"
```

### 4.2 `Payment.paid_by` (coluna nova, aditiva)

```python
paid_by = models.ForeignKey(
    Person, null=True, blank=True, on_delete=models.PROTECT, related_name="finance_payments_funded"
)
```

`PROTECT` (não `SET_NULL` como `Employee.person`): apagar a pessoa apagaria a dívida com ela. Deliberado e divergente do vizinho.

**Invariante (validada em serviço e em `clean()`):** `funded_from == THIRD_PARTY ⟺ paid_by is not None`. Um pagamento de caixa com `paid_by` preenchido, ou um de terceiro sem pessoa, é rejeitado (400 PT).

### 4.3 `Bill.paid_by_person` (coluna nova, aditiva)

```python
paid_by_person = models.ForeignKey(
    Person, null=True, blank=True, on_delete=models.PROTECT, related_name="finance_bills_purchased"
)
```

**NÃO é uma quarta FK de origem — é uma dimensão ortogonal de atribuição.** Esta distinção é load-bearing e foi corrigida após revisão adversarial:

- As três FKs de origem (`billing_account`, `installment`, `employee`) respondem **"de onde vem esta conta"**.
- `paid_by_person` responde **"quem financiou"**, e coexiste com qualquer uma delas.

Por que **tem** que coexistir: uma compra parcelada de terceiro vira `InstallmentPlan` avulso → cada parcela é uma `Bill` com `installment` preenchido (`bill_generation_service.py:244-247`). Se `paid_by_person` fosse exclusiva com `installment`, **compra parcelada de terceiro seria impossível** — e ela é caso de uso central ("comprei em 10× no cartão do Alvaro"). O mesmo vale para "Alvaro pagou a conta de água": aí a `Bill` tem `billing_account` **e** o pagamento é dele.

**Sem `UniqueConstraint`** — uma pessoa faz N compras no mesmo mês.

**Compra avulsa de terceiro** = `Bill` sem nenhuma das três FKs de origem (bill avulsa, já suportada) **com** `paid_by_person`.

**Invariante (escopo corrigido):** exclusividade mútua **apenas entre as três FKs de origem originais**. Hoje isso **não é validado** em lugar nenhum (verificado: `Bill.clean()` só normaliza `competence_month`, `finances/models.py:450-453`; nenhuma constraint cobre) — a Fase 2 fecha esse buraco pré-existente. `paid_by_person` fica **fora** da regra.

### 4.3.1 Ciclo de vida da compra de terceiro (correção pós-revisão)

A afirmação inicial de que a compra herdava o ciclo de vida "de graça" era **falsa**, e a revisão adversarial provou:

`BillService.assert_not_paid` (`bill_service.py:63-71`) bloqueia `suspend`, `cancel`, `delete` e `update_with_lines` em qualquer bill com pagamento vivo. A compra de terceiro **nasce paga** (§3.1) → **todas** essas operações falham nela. Um lançamento errado seria incorrigível pela UI.

Pior: `unpay` (`bill_payment_service.py:139-156`) não conhece compras. Desfazer o pagamento de uma compra deixaria a `Bill` ativa e **não paga** — ela apareceria no cockpit como conta a pagar do caixa, enquanto o extrato continuaria cobrando a dívida da pessoa (o extrato conta a compra por `paid_by_person`/`competence_month`, não pelo pagamento). **O mesmo dinheiro contado duas vezes**, e o risco real de pagar de novo o que o filho já pagou.

Correções obrigatórias:

1. **`unpay` rejeita compra de terceiro.** Se alguma bill alocada tem `paid_by_person`, erro PT: *"Uma compra de terceiro não pode ter o pagamento desfeito — exclua a compra."*
2. **`ThirdPartyPurchaseService.delete_purchase(bill, user)`**: caminho único de correção. Numa transação: remove `Payment` + alocação e faz soft-delete da `Bill`. Guard de mês fechado nos dois meses (competência e caixa), como `unpay`.
3. **Editar o pagador**: `Bill.paid_by_person` **não** está em `_EDITABLE_HEADER_FIELDS` (`bill_service.py:128-140`) e `update_with_lines` cai no `assert_not_paid`. Ação dedicada `bills/{id}/reassign_payer` atualiza `Bill.paid_by_person` **e** `Payment.paid_by` na mesma transação.

### 4.4 `ThirdPartySettlement` (o único model novo)

O acerto: dinheiro que os proprietários devolvem à pessoa.

```python
class ThirdPartySettlement(AuditMixin, SoftDeleteMixin, models.Model):
    """Acerto com um terceiro: saída de caixa que abate a dívida acumulada com a pessoa.

    Nunca vinculado a mês ou cobrança específica — a alocação é FIFO computada
    (ThirdPartyStatementService), jamais persistida.
    """
    condominium = models.ForeignKey(Condominium, on_delete=models.PROTECT, related_name="third_party_settlements")
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="finance_settlements")
    settlement_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
```

Constraint `amount > 0` + `clean()` PT, espelhando `Payment`. RLS habilitada na mesma migration.

**Guard de mês fechado — obrigatório (achado da revisão).** O acerto é saída de caixa real (§5), e `CondoMonthClose.cash_balance_end` é congelado a partir de `CondoBalanceService.cash_balance`. Um acerto criado (ou apagado) num mês já fechado corromperia silenciosamente esse snapshot. É **exatamente a classe de bug que o projeto já corrigiu para pagamentos** (B3 — ver `bill_payment_service.py:13-16`).

Portanto: **`ThirdPartySettlement` nunca é escrito por `ModelViewSet` puro.** Todo create/update/delete passa por `ThirdPartySettlementService`, que chama `CondoMonthCloseService.assert_open(settlement_date.replace(day=1))` na escrita **e** na exclusão.

**Sem FK de prédio, deliberadamente**: a dívida é com a pessoa, não de um prédio (§5.2).

**Por que não reusar `Payment`:** `PaymentAllocation.bill` é `NOT NULL` + `PROTECT`, e todo `Payment` existe para quitar uma `Bill`. Um acerto não quita conta nenhuma — quita um saldo agregado. Forçá-lo em `Payment` exigiria tornar `bill` nulo e reescrever `_caixa_outflow` e `_wedge_residual`. Model separado é mais simples e não toca invariante existente.

### 4.5 Compra parcelada de terceiro (§4.6 do escopo — desenho próprio)

O caso "comprei em 10× no cartão do Alvaro" **não** passa por `InstallmentPlan`. Razão: aquele mecanismo existe para dívida cujo cronograma é **materializado mês a mês** por um job; aqui o cronograma é **inteiramente conhecido no ato** e cada parcela já está paga (o cartão dele já foi debitado / vai ser, integralmente).

Portanto `ThirdPartyPurchaseService.create_purchase(..., installment_count=N)` cria, **numa única transação**, N `Bill`s + N `Payment`s:

- parcela *i* → `Bill(paid_by_person=P, competence_month = mês_base + i, description="<desc> (i/N)")` com 1 linha
- cada uma quitada por seu `Payment(THIRD_PARTY, paid_by=P)`
- valor: divisão com `quantize_money`, **sobra de centavos na primeira parcela** (nunca criar dinheiro do nada — Σ parcelas == total exato)
- guard de mês fechado em **todas** as competências envolvidas; se alguma estiver fechada, rejeita a operação inteira

Sem `InstallmentPlan`, sem `Installment`, sem tocar `BillGenerationService`. A `Bill` de parcela de terceiro **não** tem `installment` preenchido — logo a ortogonalidade de §4.3 nem é exercida aqui (mas continua valendo, porque um terceiro pode pagar a parcela de um plano existente do condomínio).

### 4.6 Migration

Uma única migration `0011`: `AddField` × 2 (`Payment.paid_by`, `Bill.paid_by_person`), `AlterField` em `Payment.funded_from`, `CreateModel` `ThirdPartySettlement` + `RunSQL` de RLS. Puramente aditiva — **sem backfill, sem DROP**.

**CRÍTICO (achado da revisão):** `Payment.funded_from` é `max_length=10` (`finances/models.py:500-502`) e `"third_party"` tem **11 caracteres**. O `AlterField` tem que **alargar a coluna para 20**, não só mudar `choices` — senão o Postgres estoura `value too long for type character varying(10)` no primeiro insert. Agrava: `Payment.objects.create()` pula `full_clean()`, então o bug **passa despercebido** em teste que não vai ao banco.

## 5. O caixa (a parte que mais importa)

Verificado diretamente no código, com dois agentes independentes confirmando:

- `CondoBalanceService._caixa_outflow` (`condo_balance_service.py:335-346`) filtra `payment__funded_from=FundedFrom.CAIXA` — **allowlist**. Um valor novo é excluído automaticamente. **Nenhuma linha muda.**
- `Bill.objects.with_amounts` soma `PaymentAllocation` **sem** olhar `funded_from` — a conta é quitada normalmente. É exatamente o desejado.
- Não existe nenhum outro ponto que trate `Payment` como saída de caixa: `condo_month_close_service`, `dashboard_views`, `condo_projection_service`, `condo_simulation_service` e `condo_calendar_service` **não referenciam `Payment`** — todos passam por `CondoBalanceService` ou leem o snapshot congelado `CondoMonthClose.cash_balance_end`.

**A única mudança no caixa** é somar os acertos como saída:

```python
cash_out = comp.caixa_outflow + comp.deposit_out + comp.settlements_out
```

`settlements_out` = Σ `ThirdPartySettlement.amount` do mês (por `settlement_date`), vivos.

### 5.1 Escopo por prédio — `settlements_out` zera quando filtrado

O acerto é **condo-level**: não tem prédio (§4.4). Se `settlements_out` fosse computado incondicionalmente, toda visão filtrada por prédio subtrairia do caixa daquele prédio um acerto do condomínio inteiro.

Precedente exato no código (`condo_balance_service.py:296-305`), que faz isso para transferências de reserva:

```python
# Reserve transfers are condo-level (no building) — only in the condo-wide view.
reserve_to_cash = ZERO
deposit_out = ZERO
if building_id is None:
    ...
```

Portanto: `settlements_out = ZERO` quando `building_id is not None`.

**Armadilha registrada:** o wedge continua **verde** mesmo com esse bug (verificado na revisão — o resíduo dá 0,00 de qualquer forma). Ou seja, o wedge **não protege** contra isto — só um teste dedicado (`cash_change_of_month(y, m, building_id=X)` não muda com acerto) pega.

### 5.2 O wedge (`wedge_ok`) — a armadilha

`_wedge_residual` reconcilia competência × caixa:

```
delta_payables = expense_competence - caixa_outflow
```

Uma compra de terceiro entra em `expense_competence` (é `Bill` ativa) mas **não** em `caixa_outflow`. Isso está **correto e já balanceado**: a despesa foi reconhecida por competência e o caixa não saiu — a dívida apenas mudou de credor. É o mesmo tratamento que uma conta não paga recebe.

O acerto, porém, é saída de caixa **sem** despesa de competência (a despesa já foi reconhecida quando a compra virou `Bill`). Sem ajuste, ele quebraria o wedge. Portanto `settlements_out` entra em `delta_payables` também:

```python
delta_payables = comp.expense_competence - comp.caixa_outflow - comp.settlements_out
```

**Isto é a única alteração de fórmula monetária da Fase 2.**

Álgebra conferida (residual 0,00 nos quatro casos: só compra; só acerto; ambos; terceiro pagando conta existente). `settlements_out` entra com sinais opostos nos dois lados da identidade e cancela.

**Mas atenção — `wedge_ok` é um teste FRACO aqui.** Justamente por cancelar dos dois lados, o resíduo dá zero para **qualquer** valor de `settlements_out`, inclusive um errado (sinal trocado, campo de data errado, escopo errado, contagem dupla). O único bug que ele pega é somar em `cash_out` e esquecer de `delta_payables`.

Portanto o teste de reconciliação **não pode** se limitar a `assert wedge_ok`. Tem que **fixar os KPIs concretos** — `assert cash_change_of_month == <valor à mão>` e `assert result_of_month == <valor à mão>` — e só então o resíduo. É o padrão que os testes de wedge existentes já usam (`test_condo_balance_service.py:284-287`).

## 6. O extrato por pessoa — `ThirdPartyStatementService`

Porta direta da regra do *family loans*, com a direção invertida. **Função pura sobre dados já buscados; alocação computada, nunca persistida.**

### 6.1 Devido do mês

```
devido(M) = Σ pagamentos de contas feitos pela pessoa (funded_from=THIRD_PARTY, paid_by=P, payment_date em M)
              EXCETO os que quitam uma Bill de compra dela      <-- ver dupla contagem
          + Σ amount_total das Bills de compra da pessoa (paid_by_person=P, competence_month = M, não canceladas)
```

**Dupla contagem (bug achado na execução da S80, corrigido).** Uma compra nasce paga (§3.1), logo gera **as duas coisas**: a `Bill(paid_by_person=P)` **e** o `Payment(THIRD_PARTY, paid_by=P)` que a quita. Somar os dois lados sem filtro conta o **mesmo dinheiro duas vezes** — uma compra de R$300 reportava R$600 devidos, e `total_atrasado` (o número que os proprietários olham) vinha dobrado.

A `Bill` de compra **é** a dívida; aquele pagamento é só o mecanismo que a marca paga. Portanto excluem-se os pagamentos alocados a uma bill com `paid_by_person`. Mantêm-se os que quitam uma conta **comum** do condomínio (água/luz/IPTU no cartão da pessoa) — esses não têm Bill de compra representando-os e sumiriam do extrato.

Verificado nos dois cenários: compra de R$300 → devido R$300 (item `purchase`); terceiro paga conta de luz de R$200 → devido R$200 (item `payment`).

**Por que a S79 não pegou:** o helper de teste dela criava a Bill de compra **sem** o pagamento, e o pagamento **sem** `paid_by_person` — a combinação "nasce paga", que é justamente a que a S80 produz, nunca foi exercitada. Cobertura de 100% e ainda assim o buraco existia.

O agrupamento usa `payment_date` para pagamentos e `competence_month` para compras — a competência da compra é o **mês em que cai no cartão dele**, que é o análogo direto do `billingMonth` da referência. Numa compra parcelada, cada parcela é uma `Bill` com sua própria competência, então cada parcela cai no mês certo sem lógica extra.

### 6.2 Alocação FIFO (pura, sem I/O)

**Pool com corte temporal (rev. 3 — decidido pelo usuário em 2026-07-27).** A referência *family loans* usa um pool único sem data nenhuma, o que deixaria um acerto **ainda não feito** quitar uma compra — mês verde antes de o dinheiro existir.

A primeira tentativa de corte (rev. 2: "no mês M só entram acertos datados até M") errou para o outro lado e quebrou a rotina real do usuário: **ele paga sempre o mês anterior**. Uma compra de junho acertada em 5 de julho é o caso NORMAL, e a regra reportava "junho atrasado R$300" com os R$120 pagos pendurados em `saldo_credor`, soltos.

**Regra vigente:** um acerto fica disponível a partir de `min(mês do acerto, primeiro mês da janela)` **se já foi feito** (`settlement_date <= hoje`); um acerto **datado no futuro** fica parado no mês dele.

- Dinheiro já entregue abate meses anteriores → a rotina "acertar o mês passado" funciona.
- Dinheiro ainda não entregue não pinta mês nenhum de verde → o risco original continua bloqueado.

**Armadilha do pseudocódigo (achada na implementação da S79):** implementar isso como um dicionário "acertos agrupados por mês da cobrança" **perde silenciosamente** todo acerto cujo mês não tem cobrança — ele some do `saldo_credor`. Usar ponteiro cronológico sobre a lista ordenada e, no fim, **drenar os acertos restantes** (posteriores à última cobrança) para o `saldo_credor`: são dinheiro já entregue.

```
para cada mês M em ordem cronológica:
    pool += Σ acertos com settlement_date dentro de M   # entram no mês em que ocorreram
    devido = devido(M)
    se devido < 0:  pool += |devido|; fillable = 0     # crédito propaga adiante
    senão:          fillable = devido
    aplicado  = min(pool, fillable)
    pool     -= aplicado
    resto     = fillable - aplicado
    se M <= mês atual: total_em_aberto += resto        # meses futuros não contam
sobra final do pool -> saldo_credor
```

### 6.3 Status (derivado, nunca coluna)

| Status | Regra |
| --- | --- |
| `credit` | `devido < 0` (mês só de descontos/estornos) |
| `paid` | `resto == 0` e `devido > 0` |
| `overdue` | `resto > 0` e mês **anterior** ao atual |
| `partially_paid` | `aplicado > 0`, `resto > 0`, mês atual/futuro |
| `open` | `aplicado == 0`, mês atual/futuro |

Totais: `total_devido` = **Σ max(0, devido(M))** (cobrança bruta — sem isso um mês de crédito cancela um mês de cobrança e o card diz "R$ 0 devido" a quem se deve 500), `total_pago`, `total_em_aberto` (≤ mês atual), `total_atrasado` (< mês atual), `saldo_credor`.

O card do índice mostra **`total_em_aberto`, `total_atrasado` e `saldo_credor`** — os três não-ambíguos. `total_devido` fica só no extrato.

### 6.3.1 Escopo e pessoas apagadas

- **Condomínio**: filtrar os **dois** lados (cobranças e acertos) por `condominium`, default `Condominium.get_default()`. Hoje só existe um, mas `ThirdPartySettlement` tem a FK e as cobranças também — deixar um lado sem filtro é bug latente.
- **`Person` soft-deletada**: resolver **nome** por `Person.all_objects` (precedente: `owner_distribution_service.py:97` — "a soft-deleted owner still shows its name"), mas o **índice** (`third-party/people`) lista só `Person.objects`. Uma dívida com pessoa apagada não some do extrato dela; ela só deixa de aparecer na lista. `PROTECT` impede hard-delete, mas **não** impede soft-delete.

### 6.4 Precisão monetária

Todo somatório via ORM (`Sum`), `quantize_money` só na fronteira, Decimal em toda a cadeia — mesma disciplina do resto do módulo. Nenhum `float`.

## 7. API

Prefixo `/api/finances/`, `IsAdminUser` (o módulo inteiro é admin-only — `security.md`).

| Rota | Método | Descrição |
| --- | --- | --- |
| `third-party-settlements` | CRUD | Acertos — **sempre via `ThirdPartySettlementService`** (guard de mês fechado no create/update/delete), nunca `ModelViewSet` puro |
| `third-party/people` | GET | Pessoas com dívida viva + saldo em aberto (lista do índice) |
| `third-party/statement?person_id=&from=&to=` | GET | Extrato mês a mês + totais |
| `bills/create_purchase` | POST | Compra de terceiro: `Bill` + `Payment(THIRD_PARTY)` numa transação |
| `bills/{id}/delete_purchase` | DELETE | **Único caminho de correção** de compra lançada errada (§4.3.1) |
| `bills/{id}/reassign_payer` | POST | Corrige o pagador: `Bill.paid_by_person` + `Payment.paid_by` na mesma transação |
| `bills/{id}/pay` | POST | **Estendida**: aceita `funded_from=third_party` + `paid_by_person_id` |

`bulk_pay` aceita **um** `paid_by_person_id` para todas as bills selecionadas — atribuição em lote é o comportamento desejado (pagar as contas do mês todas no cartão da mesma pessoa), e é assim que tem que ser documentado.

Mês fechado no `create_purchase`: a competência (mês da fatura do cartão) e o caixa (data da compra) podem cair em meses diferentes; ambos são checados. A mensagem de erro deve dizer **qual** mês está fechado — senão o usuário recebe "Este mês está fechado" sem saber a qual se refere.

`_validated_funded_from` (`crud_views.py:96`) já é o ponto único de validação de `funded_from` em `pay`/`bulk_pay` — passa a exigir `paid_by_person_id` quando o valor é `third_party`. **`bulk_pay` também**, senão é um caminho de escape para criar pagamento de terceiro sem pessoa.

Decimais sempre **string** no JSON (contrato vigente do módulo).

## 8. Frontend

Rota nova `/finances/third-party` no grupo **Condomínio**:

- **Índice**: cards por pessoa (nome, devido em aberto, atrasado, último acerto) + botão "Registrar acerto".
- **Extrato** `/finances/third-party/[id]`: `StatCard`s (em aberto / atrasado / crédito) + tabela mês a mês com badge de status + detalhe expansível (quais contas e compras compõem o mês).
- **"Nova compra de terceiro"**: modal com pessoa, descrição, valor, mês de cobrança, categoria e parcelamento opcional (N parcelas → `InstallmentPlan` avulso).
- **Cockpit** (`/finances/bills`): o popover de pagamento ganha a origem "Terceiro" com seletor de pessoa. Bills de compra ganham badge com o nome da pessoa.

Padrão da casa, sem exceção: `useCrudPage` + modal + `DataTable` (`employees/` como exemplar), TanStack Query com `query-keys`, Zod com padrão dual, MSW nos testes (nunca `vi.mock` de hook interno), `formatCurrency` no boundary.

## 9. Testes

- **Unit** `ThirdPartyStatementService`: os 5 status; overpayment vira crédito do mês seguinte; crédito **antes** de mês vencido propaga adiante; mês futuro com resto não conta em `em_aberto`; múltiplas entradas no mesmo mês somam; pessoa sem nada → extrato vazio (não erro).
- **Monetários**: compra parcelada em 10× cai uma parcela por mês; acerto parcial; acerto maior que a dívida; sequência acerto → nova compra → acerto.
- **Caixa (crítico)**: pagamento de terceiro **não** move `cash_balance`; acerto **move**; `CondoMonthClose` congela o valor certo. Reconciliação **fixando os KPIs concretos** antes do `wedge_ok` (§5.2 — `wedge_ok` sozinho é vacuous). Acerto **não** afeta `cash_change_of_month(building_id=X)` (§5.1 — o wedge não pega esse bug).
- **Ciclo de vida (§4.3.1)**: `unpay` de pagamento de compra → 400 PT; `delete_purchase` remove `Bill` + `Payment` atomicamente; `reassign_payer` troca os dois lados; compra em mês fechado → 400 dizendo **qual** mês.
- **Guard de mês fechado no acerto**: criar/editar/apagar acerto em mês fechado → 400 PT.
- **Ortogonalidade (§4.3)**: `Bill` com `installment` **e** `paid_by_person` é **válida** (compra parcelada de terceiro); `Bill` com `billing_account` **e** `paid_by_person` é válida (terceiro pagou a conta de água); duas FKs de **origem** → 400.
- **Invariantes**: `THIRD_PARTY` sem `paid_by` → 400; `caixa` com `paid_by` → 400; `bulk_pay` idem; exclusividade das 4 FKs de origem.
- **Integração**: `create_purchase` cria `Bill` + `Payment` atomicamente (falha → rollback total, sem `Bill` órfã).
- **Frontend**: extrato renderiza os status; fluxo compra → extrato → acerto via MSW.

Gate: cobertura ≥90% na suíte `finances` completa; `ruff` + `mypy` + `pyright` + `eslint` + `tsc` zerados; zero supressões.

## 10. Divergências em relação ao esboço da §7 (deliberadas)

1. **`ThirdPartyCharge` não existe.** A compra é `Bill(paid_by_person=…)`, seguindo o precedente `Employee`/`Bill`. Um model paralelo duplicaria parcelamento, linhas, ciclo de vida e competência — violação direta de DRY/YAGNI.
2. **`CondoBalanceService` não "aprende" que `third_party` não é saída** — ele já usa allowlist, então isso é automático. O ajuste real, que o esboço não previu, é o **acerto** entrar como saída de caixa e no wedge (§5.2).

## 10.1 Correções da revisão adversarial (rev. 2, 2026-07-27)

Revisão independente encontrou 3 Critical + 6 Important. Todos incorporados:

| # | Achado | Onde foi corrigido |
| --- | --- | --- |
| C-1 | `unpay` de compra deixa a bill ativa e não paga → **dinheiro contado duas vezes** | §4.3.1 (rejeitar) |
| C-2 | `assert_not_paid` torna a compra **incorrigível** (nasce paga → cancel/delete falham) | §4.3.1 (`delete_purchase`) |
| C-3 | Acerto sem guard de mês fechado corrompe `cash_balance_end` congelado | §4.4 (service obrigatório) |
| I-1 | `settlements_out` sem zerar por prédio contamina caixa do prédio | §5.1 |
| I-2 | FIFO com pool sem data deixa acerto quitar compra futura | §6.2 (corte temporal) |
| I-3 | `total_devido` somando meses negativos vira número sem sentido | §6.3 |
| I-4 | Sem caminho para corrigir pagador errado | §4.3.1 (`reassign_payer`) |
| I-5 | **Contradição interna**: exclusividade de origem impediria compra parcelada de terceiro | §4.3 (`paid_by_person` é ortogonal, não é origem) |
| I-6 | Escopo de condomínio só num lado do extrato | §6.3.1 |
| M-1..M-4 | Person soft-deletada; atraso médio; mês fechado ambíguo; `bulk_pay` em lote | §6.3.1, §7 |

Achado que **não** virou mudança de código, mas mudou o plano de testes: o `wedge_ok` é **vacuous** para bugs de acerto (cancela dos dois lados da identidade) — o teste tem que fixar os KPIs concretos (§5.2).

## 10.2 Correções da revisão do PLANO (mesma data)

Segunda revisão, sobre os prompts de execução, achou 4 Critical + 5 Important. Os que mudaram o desenho:

| # | Achado | Correção |
| --- | --- | --- |
| C1 | **`Payment.funded_from` é `max_length=10`; `"third_party"` tem 11 chars** → estouraria no primeiro insert em produção. Pior: `create()` pula `full_clean()`, então passaria despercebido em teste | §4.6 (alargar p/ 20 no `AlterField`) |
| C2 | Todo comando `pytest` escopado do plano **falhava por construção** (`pytest.ini` embute `--cov-fail-under=90` sobre `core`+`finances`; rodar 1 arquivo dá ~14%) — mesmo bug da Fase 1, reproduzido | Aceites das S77–S80 (`--cov-fail-under=0` no escopado) |
| C3 | `BillSerializer.Meta.fields` é **allowlist**; ninguém adicionava `paid_by_person` → o badge da S82 **não teria como existir** | S80 §3b |
| C4 | **Parcelamento não vinha de graça**: `InstallmentPlan` materializa `Bill`s num job mensal, com `defaults` hardcoded sem `paid_by_person`, e **não pagas** | §4.5 (serviço cria N Bills + N Payments) |
| I1 | `_components` não tem condomínio no escopo — instrução era inimplementável | S78 (sem filtro de condomínio) |
| I2 | Motivo errado para zerar por prédio (o certo é que **cancela no wedge**); e caixa por prédio não é conciliável | §5.1 + S78 |
| I3 | Constantes de mensagem privadas (`_`) seriam importadas entre módulos | S77 (nomes públicos) |
| I4/I5 | Retorno `dict` cru em vez de `TypedDict`; cache deixado em aberto | S79/S80 |

Verificação extra feita antes de fechar: a regra de exclusividade de origem foi checada **no banco local e em produção** — 0 bills com duas origens em 28. Seguro impor.

## 11. Fora de escopo

- Cartão emprestado / direção inversa (o terceiro devendo aos proprietários).
- Rateio da dívida entre Raul e Célia individualmente (o household é uma unidade — §15 do design anterior).
- Notificação/cobrança automática da pessoa.
- Migração ou importação do histórico que hoje vive fora do sistema.
