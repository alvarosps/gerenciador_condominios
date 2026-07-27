# Módulo Condomínio (`finances/`)

Doc consolidado do app **`finances/`** — o módulo financeiro ATUAL do condomínio (saídas/saldo/reserva/distribuição). Substitui o financeiro **pessoal** legado do `core` (Person/Expense/RentPayment), que está em depreciação (remoção em P7). O legado tem seu próprio doc: [LESSONS_LEARNED.md](LESSONS_LEARNED.md).

## Por que existe

O `core` legado misturava finanças pessoais do locador com o caixa do condomínio. O `finances/` modela só o **condomínio**: contas a pagar tipadas (água/luz/IPTU/…), parcelamentos, funcionários, reserva, receitas e o **fechamento mensal congelado**. Dependência unidirecional: **`finances` pode importar `core`; `core` NUNCA importa `finances`**.

## Modelo de dados (`finances/models.py` — 16 models)

| Model | Papel |
|---|---|
| `BillingAccount` | Conta tipada (`account_type`: water/electricity/iptu/internet/generic) + identidade (inscrição/UC/medidor/titular/endereço) + `SupplyStatus` |
| `Bill` → `BillLineItem` | Conta a pagar do mês; o dinheiro é a soma das linhas. `BillLineItem.is_offset` é armazenado **POSITIVO** e **subtraído** |
| `Payment` → `PaymentAllocation` | Pagamento e sua alocação por bill (`FundedFrom`: caixa/reserva) |
| `InstallmentPlan` → `Installment` | Parcelamento (embutido na conta de consumo, ou standalone p/ IPTU) |
| `Employee` | Funcionário (`EmployeePaymentType`: fixed/variable/mixed) |
| `Reserve` → `ReserveMovement` | Reserva (depósito/saque; `ReserveMovementKind`) |
| `IncomeEntry` | Receita do condomínio |
| `CondoMonthClose` | **Snapshot mensal congelado** (`CondoMonthCloseStatus`) — só `AuditMixin` (sem SoftDelete) |
| `BillSkip` | Marca uma conta como não cobrada num mês — só `AuditMixin` (sem SoftDelete) |
| `WaterBillStatement` / `ElectricityBillStatement` | 1:1 com `Bill` — **só leituras** (o dinheiro mora no `BillLineItem`) |
| `Category` | Categoria de conta (self-FK `parent` + `condominium`) |

`Condominium` é o **tenancy-root** e mora em **`core/models.py`** (referenciado por `finances` via FK; `Building.condominium` — migration 0048).

## Invariantes monetários

- Dinheiro do `Bill` via **`Bill.objects.with_amounts(today)`** (`amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue` como subquery anotada) — NUNCA somado em property Python.
- `BillLineItem.is_offset` armazenado **positivo** e subtraído; quantização (`quantize_money`) só na fronteira de saída (serializer/service) — o dashboard e o `CondoMonthClose` congelado nunca diferem por 1 centavo.
- "Hoje / mês corrente" só via `core.services.timezone.today_sp()` (settings é UTC).
- Geração mensal (`BillGenerationService.ensure_month_bills`) é **idempotente e race-safe** (get_or_create nas partial-uniques + tolerância a IntegrityError).
- FKs de origem do `Bill` usam `SET_NULL` — apagar a fonte nunca apaga o histórico.
- `Bill.amount_is_estimated` (BooleanField, default `False`): `True` quando a bill nasce da geração mensal (`BillGenerationService._ensure_account_bill`, inclusive via parcela embutida); `False` em `create_with_lines`/`update_with_lines`/`pay`/`apply_invoice`; `unpay` NUNCA re-marca. Badge "valor estimado" no frontend; conta com `expected_amount=0` gera bill sem linha ("aguardando fatura").
- `BillingAccountQuerySet.with_open_balance(today)` → anotação `open_balance` = soma de `amount_total − amount_paid` das bills não-canceladas (ACTIVE+SUSPENDED+DEFERRED), somando os DOIS braços de FK (`billing_account` direto **e** `installment__plan__billing_account` — sem o segundo, conta IPTU registry-only zeraria).

## Fechamento mensal (`CondoMonthClose`)

Snapshot imutável: ao fechar, as figuras (income_total/expenses_total/net/cash) são **congeladas no breakdown** ("frozen figures win" — o congelado vence qualquer edição posterior das bills). Invariante: o snapshot nunca difere do dashboard on-read por 1 centavo. Cuidado com reopen→close em cascata (P2.3).

## Contas tipadas + parser de fatura

Statements (água/luz) são 1:1 com a Bill e **só leituras**. O parser DMAE/CEEE roda **em memória, sem anexar o PDF** (`POST /api/finances/bills/parse_invoice/` lê → monta o rascunho → descarta o PDF). IPTU é conta-registro (não auto-gera): planos avulsos + dívida diferida; alerta IPTU = banner load-bearing + push agregado SP-aware via o cron `send_finance_alerts`.

## Cockpit operacional (`month_board`, extrato por conta, consolidação de dívida)

- **`CondoMonthBoardService.build(year, month, today)`** → `GET finance-dashboard/month_board?year&month` (**sem cache**, `IsAdminUser`): payload `{ overdue[], deferred_suspended[], groups[], totals{due,paid,remaining,overdue}, generation{missing_count} }`. `overdue` = bills `ACTIVE` com resto>0 e `due_date<hoje`, **qualquer competência** (critério próprio, não reusa `is_overdue`/`overdue` legado); `deferred_suspended` = `SUSPENDED`/`DEFERRED` com resto>0, **fora dos totais do mês**; `groups` = bills `ACTIVE` da competência (pagas incluídas), agrupadas por prédio (bucket sem prédio = "Condomínio", por último); `CANCELED` nunca aparece; `generation.missing_count` = contas elegíveis (`BillGenerationService.is_account_eligible`) sem bill não-deletada no mês.
- **`AccountStatementService.build(account_id, today)`** → `GET billing-accounts/{id}/statement` (**sem cache**, `IsAdminUser`, 404 se conta inexistente): payload `{ account, stats{open_balance, open_bills_count, avg_delay_days}, months[], plans[] }`. Bills agregadas por `Q(billing_account=conta) | Q(installment__plan__billing_account=conta)`; `avg_delay_days` = média de `paid_date − due_date` das últimas 12 bills **quitadas** (`amount_remaining=0` **e** `amount_total>0`), só alocações/payments vivos (espelha `with_amounts`); `months[]` exclui `CANCELED`.
- **`POST bills/{id}/apply_invoice`** (MultiPartParser, `IsAdminUser`): reparsa o PDF em memória e aplica direto à bill alvo via `BillService.update_with_lines` na mesma transação (substitui só linhas sem FK `installment`; limpa `amount_is_estimated`); 400 PT se conta/competência/prédio divergem, bill não-`ACTIVE`, paga/parcial, ou mês fechado. Resposta = bill serializada (sem `warnings` — o preview é feito via `parse_invoice`, passo 1 do fluxo de 2 passos).
- **`InstallmentPlanService.consolidate_open_bills`** → `POST billing-accounts/{id}/consolidate_debt` `{bill_ids[], embedded, installment_count, start_due_date, default_due_day}` → 201 com o plano: cria 1 `InstallmentPlan` (`total = Σ amount_remaining` das bills selecionadas, parciais contam o resto) e **cancela as bills de origem na mesma transação** (evita dupla contagem em Atrasadas/`open_balance`). Rejeita bill com FK `installment` viva ou linha de parcela embutida de plano vivo ("pureza v1" — trate/cancele o plano antigo antes).
- Fechamento mensal ganhou um **preflight no frontend** (não altera `close`/`reopen` no backend): antes de confirmar o fechamento, a UI busca o `month_board` da competência e lista as bills em aberto, exigindo confirmação explícita quando há alguma; falha na busca não bloqueia o fechamento (informativo, o guard real continua no backend via `CondoMonthCloseService.assert_open`).

## Terceiros — contas e compras pagas por outra pessoa (S77–S82)

Os donos não têm cartão próprio: filhos e genro pagam contas do condomínio e compram coisas usando o dinheiro deles. Sem isso modelado, **o caixa mente** (uma conta de luz paga pelo genro virava saída de caixa que nunca aconteceu) e a dívida com a família fica invisível.

### Modelo — nenhum model paralelo

A decisão central é que **não existe `ThirdPartyCharge`**. Dívida do condomínio com uma **pessoa** já é um `Bill` (o precedente é `Employee`). São só três peças:

| Peça | Papel |
|---|---|
| `Payment.funded_from = THIRD_PARTY` + `Payment.paid_by` (FK `core.Person`) | Um terceiro quitou uma conta do condomínio. **Não sai do caixa** — a dívida migra da concessionária para a pessoa |
| `Bill.paid_by_person` (FK `core.Person`) | Compra que a pessoa fez para o condomínio. Nasce **quitada** (o `Bill` e o `Payment` que o quita são criados na MESMA transação) — senão apareceria como "a pagar", o que é falso |
| `ThirdPartySettlement` | O acerto: os donos pagam a pessoa. **É a única das três que sai do caixa de verdade.** `AuditMixin` + `SoftDeleteMixin`; `amount > 0` por CheckConstraint; sem FK de prédio (a dívida é com a pessoa, não de um prédio) |

`paid_by_person` é **ortogonal** às três FKs de origem (`billing_account`/`installment`/`employee`), não uma quarta origem: uma bill pode ter `billing_account` **e** `paid_by_person` (o terceiro pagou a água) ou `installment` **e** `paid_by_person` (compra parcelada de terceiro). Duas FKs de **origem** continuam sendo 400.

### Extrato FIFO — computado, nunca persistido

`ThirdPartyStatementService` aloca o pool de acertos da pessoa sobre o "devido" mês a mês, em ordem cronológica, **a cada leitura**. Não persistir é decisão arquitetural: uma correção retroativa (compra lançada no mês errado, acerto ajustado) é absorvida pela próxima leitura, sem migração de dados nem linhas de alocação órfãs. Sem cache, pelo mesmo motivo do `month_board`: o extrato depende de `today_sp()` e a virada de meia-noite não é uma escrita.

`devido(M)` = Σ pagamentos de terceiro da pessoa com `payment_date` em M + Σ `amount_total` das compras dela com `competence_month` == M (`CANCELED` fora; `SUSPENDED`/`DEFERRED` dentro — a dívida com a pessoa existe independentemente do ciclo de vida da bill). `amount_total` sempre de `with_amounts(today)`.

Seis status de mês: `paid`, `overdue`, `partially_paid`, `open`, `credit` e **`empty`** (mês dentro da janela sem nenhum movimento — a janela materializa lacunas). `empty` **nunca** pode ser pintado como "Quitado": entre dois meses atrasados isso leria como "esse mês foi acertado".

### Impacto no caixa e no wedge

- Pagamento de terceiro e compra de terceiro **não movem `cash_balance`** — `CondoBalanceService` usa allowlist de origens, então `third_party` fica de fora automaticamente.
- O **acerto** move: entra em `settlements_out` (Σ por `settlement_date` no mês) e compõe `cash_out = caixa_outflow + deposit_out + settlements_out`.
- Na reconciliação, `Δpayables = expense_competence − caixa_outflow − settlements_out`. Atenção: **o `wedge_ok` é vacuous para bugs de acerto** — o termo cancela dos dois lados da identidade. Só os testes de caixa dedicados (`tests/unit/test_finances/test_third_party_cash_impact.py`) fixam os KPIs concretos.
- `settlements_out` é **zerado na visão por prédio** (`building_id=X`): a dívida é com a pessoa, não de um prédio, e mantê-la contaminaria o caixa do prédio.

### Ciclo de vida (o que NÃO veio de graça)

A compra nasce paga, então `assert_not_paid` bloqueia o caminho normal de suspender/cancelar/apagar. Daí os endpoints dedicados: `DELETE bills/{id}/delete_purchase` (remove `Bill` + `Payment` atomicamente) e `POST bills/{id}/reassign_payer` (corrige o pagador nos dois lados). `unpay` de um pagamento de compra é **rejeitado** com 400 PT — deixaria a bill ativa e não paga, contando o dinheiro duas vezes. Compra ou acerto em mês fechado → 400 dizendo **qual** mês.

Parcelamento **não** reusa `InstallmentPlan`: aquele materializa as `Bill`s num job mensal, com `defaults` hardcoded, sem `paid_by_person` e **não pagas**. `ThirdPartyPurchaseService` cria as N `Bill`s + N `Payment`s ele mesmo, numa transação (máx. **60** parcelas).

### Rotas

| Rota | O quê |
|---|---|
| `GET third-party/people/` | Índice: uma linha por pessoa com dívida viva (quem não deve nada é omitido). **Array puro**, não envelope DRF |
| `GET third-party/statement/?person_id=` | Extrato mês a mês + totais. **Objeto puro** |
| `third-party-settlements/` (CRUD) | Acertos. Guard de mês fechado em criar/editar/apagar |
| `POST bills/create_purchase/` | Compra de terceiro: `person_id`, `description`, `amount`, `competence_month`, `due_date`, `installment_count` (≤60), `category_id`/`building_id` opcionais → **array** de bills criadas |
| `DELETE bills/{id}/delete_purchase/` | Apaga `Bill` + `Payment` atomicamente |
| `POST bills/{id}/reassign_payer/` | Troca o pagador nos dois lados |
| `POST bills/{id}/pay/` e `bills/bulk_pay/` | Aceitam `funded_from="third_party"` + `paid_by_person_id` (obrigatório junto; `caixa` **com** `paid_by_person_id` também é 400) |

### Frontend

Rota `/finances/third-party` (índice) e `/finances/third-party/[id]` (extrato mês a mês, detalhe expansível por mês). No cockpit `/finances/bills`: o popover de pagamento ganhou a origem **Terceiro** com seletor de pessoa obrigatório (botão desabilitado sem pessoa — o backend também rejeita, mas o usuário não deve descobrir por toast), bills de compra ganham **badge com o nome da pessoa**, e o header tem **"Nova compra de terceiro"** (admin-gated), cujo modal diz explicitamente que a compra já foi paga pela pessoa e entra como dívida com ela. `usePayBill` continua **sem optimistic update** (norma da fase 1): mutação → invalidate → refetch do `month_board`; um pagamento/compra de terceiro invalida também `finances.thirdParty.*`.

## Permissões e RLS

- Todo o módulo é **admin-only** (`IsAdminUser` — `is_staff`/`is_superuser`); inquilino recebe 403 (P1.2).
- **RLS habilitado em toda tabela `public` nova na mesma migration** (padrão `core/migrations/0047`; em `finances/`, toda migration que cria uma tabela `public` habilita RLS — `finances/0001-0003, 0006`). RLS sem policy é o estado correto (o backend conecta como `postgres`, bypass).

## API — `/api/finances/` (16 routers)

`finance-categories`, `billing-accounts`, `bills`, `bill-skips`, `payments`, `installment-plans`, `installments`, `employees`, `reserves`, `reserve-movements`, `income-entries`, `condo-month-closes`, `finance-dashboard`, `finance-cash-flow`, `third-party-settlements`, `third-party`.

**Actions:** `bills/{id}/{pay,suspend,defer,cancel,reactivate}/`, `bills/{bulk_pay,generate_month,create_with_lines,parse_invoice}/`, `bills/{id}/{update_with_lines,apply_invoice}/`, `billing-accounts/{id}/{statement,consolidate_debt}/`, `condo-month-closes/{close,reopen}/`, `finance-dashboard/{overview,monthly_balance,iptu_alerts,overdue,combined_calendar,by_category,by_owner,month_board}`, `finance-cash-flow/{projection,simulate}`.
