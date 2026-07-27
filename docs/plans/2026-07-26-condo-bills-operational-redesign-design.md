# Design — Redesenho operacional das contas do condomínio (Fase 1) + preparo para terceiros (Fase 2)

**Data:** 2026-07-26 (rev. 2 — após revisão profunda com 4 revisores independentes: deriva P2.3, backend, frontend, gaps de domínio)
**Status:** aprovado em brainstorming; rev. 2 incorpora os achados da revisão adversarial
**Módulo:** `finances/` (backend) + `frontend/app/(dashboard)/finances/`

---

## 1. Contexto e diagnóstico

A área de contas do módulo `finances/` está inoperante na prática. Diagnóstico validado:

- **Operação impraticável**: não há jeito prático de adicionar/editar/remover contas, marcar pago ou marcar atrasado. Os números estavam certos quando lançados (seed de 2026-06), mas ficaram para trás porque a manutenção mensal é cara demais.
- **Atrasadas somem**: a página filtra por competência; contas não pagas de meses anteriores desaparecem ao navegar para o mês atual.
- **Sem visão consolidada**: não existe visão única do mês (a pagar, pago, atrasado); parcelamentos, fechamento e projeção vivem em páginas separadas.
- **Sem cadastro de contas**: `BillingAccountViewSet` existe, mas não há página para gerir o registro — contas só aparecem como campo de seleção em formulários.
- **Integridade: JÁ RESOLVIDA.** O plano `docs/plans/2026-06-11-p2-3-finances-integrity-guards-plan.md` **foi executado** no fable-audit Fase 2 (commit `7005dd7`, PR #21, migration `0008`). Os 10 guards estão no código com 16+ testes de integração (`tests/integration/test_finances/test_finance_viewset_guards.py`, `test_finance_write_path_integrity.py`). Desvio deliberado e correto: `PATCH /bills/{id}/` não retorna 405 (como o plano pedia) — delega a `BillService.update_header` com guards; a edição inline do cockpit **depende** disso. Não reverter.
- **O modelo de dados NÃO é o problema**: 2 contas de luz/IPTU por prédio (identidade por inscrição/UC), água cortada que segue acumulando (`supply_status=cut` + `lifecycle_state=active`), parcelamento embutido em conta de consumo e planos avulsos de IPTU já são suportados. As falhas estão na operação e na visibilidade.

Casos reais que o desenho deve servir: água ativa + parcelada ao mesmo tempo; água cortada (DMAE) acumulando todo mês até ser parcelada; 2 contas de luz num prédio e 1 no outro; IPTU com 2 imóveis num prédio e parcelamentos diversos (incl. ano vencido a parcelar); pagamento cronicamente defasado (paga-se sempre a fatura do mês anterior); vencimentos variáveis (CEEE/DMAE).

## 2. Decisões de escopo (respostas do usuário)

| Decisão | Escolha |
| --- | --- |
| Pagamentos a terceiros (filhos/genro) | Prever no modelo/arquitetura; implementar na **Fase 2**. Ideal: tudo na mesma aplicação |
| Dados desatualizados no banco | **Recomeçar do mês atual**: manter histórico como está, corrigir cadastros, operar corretamente daqui em diante |
| Rotina mensal ideal | Gerar mês + confirmar; lançamento rápido; importar PDF; marcar pago em 1 clique |
| Contas atrasadas/acumulando | Saldo devedor por conta; atrasadas sempre à vista; histórico do padrão de pagamento. (Simulação de regularização: fora — YAGNI) |
| Faseamento | Contas primeiro (Fase 1), terceiros depois (Fase 2, só especificada aqui) |

Referência para a Fase 2: o modelo *family loans* do app `~/git/personal/financial-control` (extrato mês a mês por pessoa, cobranças tipadas, pagamento como valor único alocado FIFO ao mês aberto mais antigo, alocação computada e nunca persistida).

## 3. Fase 1 — entregas (nesta ordem)

### 3.1 Auditoria de confirmação do P2.3 (entrega pequena)

O P2.3 já está implementado (ver §1). Entrega reduzida a: (a) rodar a suíte de guards e confirmar verde; (b) registrar no plano de execução que o contrato vigente é `update_header` com guards (não 405) — testes travam isso; (c) itens extras já implementados além do plano e que o restante do design pode assumir: guard de mês de caixa em `pay`/`unpay` (sobre `payment_date`), guards de Income create/update/destroy, bloqueio de destroy/suspend/cancel em bill com pagamento vivo, reversão `MATERIALIZED→ACTIVE` ao deletar bill de parcela.

### 3.2 Página "Contas cadastradas" (`/finances/accounts`)

CRUD do registro de `BillingAccount` via `useCrudPage` + modal (padrão do projeto).

- Tabela com filtros por prédio e tipo. Colunas: nome, prédio, tipo, inscrição/UC (`external_identifier`), relógio/imóvel (`secondary_identifier`), dia de vencimento, valor esperado, estado (ativa/encerrada), fornecimento (badge **"Cortada"**) e **saldo devedor** (`open_balance`).
- `open_balance` = soma do resto das faturas **não-canceladas** da conta (ativas + suspensas + adiadas), incluindo as bills de parcela avulsa do caminho `installment__plan__billing_account` (senão conta IPTU zera — ver §3.4).
- Navegação ao extrato via célula-link explícita (o `DataTable` do projeto **não tem `onRowClick`** — não estendê-lo neste trabalho).
- Exemplares: esqueleto de `finances/categories/page.tsx` + padrão de filtros de `finances/bills/page.tsx`; colunas em `_components/account-columns.tsx` (padrão `bill-columns.tsx`). Navegação: `FINANCES_ACCOUNTS` em `constants.ts` + entrada em `condominioChildren` no `sidebar.tsx` (verificar lógica de item ativo com subrota antes de assumir `startsWith`).

### 3.3 Cockpit do mês (`/finances/bills`, redesenhada)

Fonte de dados única: `month_board` (agrupamento por prédio movido para o backend; o `useBills` + agrupamento client-side + `page_size=10000` saem desta página).

- **Topo fixo "Atrasadas"** (seção irmã ACIMA do Accordion, não colapsável): bills com `amount_remaining > 0`, `due_date < hoje` e `lifecycle_state = ACTIVE`, de **qualquer competência**, com badge de dias/meses de atraso. Critério próprio do board — **não** reusa a annotation `is_overdue` nem o `overdue` legado do dashboard.
- **Sub-seção "Dívida adiada/suspensa"**: bills SUSPENDED/DEFERRED com resto > 0 (qualquer competência), **fora dos totais do mês**, com badge de estado e CTA "Parcelar" (→ §3.5). CANCELED nunca aparece. Padrão do projeto é *mostrar e rotular*, não esconder (como o `combined_calendar` já faz).
- **Corpo**: mês selecionado agrupado por prédio (Accordion mantido), linhas operáveis:
  - **Pagar em 1 clique**: Popover na linha (variante do `bill-payment-dialog` existente; data default hoje via frontend — o backend exige `payment_date` explícito), valor default = resto, origem caixa.
    - **Valor pago ≠ total quando a bill é estimada**: o serviço ajusta a linha-semente para o valor real e aloca, numa única transação (`update_with_lines` + `pay` atômicos) — resolve fatura real R$230 sobre estimativa R$200 (hoje 400 por over-allocation) e o resto-fantasma de pagar R$180.
    - **Valor maior que o total em bill confirmada** (juros/multa CEEE/DMAE): o popover oferece "adicionar diferença como linha Juros/multa" antes de alocar (mesma transação). O guard de over-allocation do serviço permanece.
  - **Editar inline**: Popover dentro do `render` da célula (componente `popover.tsx` já usado no projeto; não criar célula editável genérica). Vencimento → `update_header` (PATCH); **valor → `update_with_lines`** (dinheiro vive em `BillLineItem`, não no header).
  - **Lançamento rápido**: "+ Conta avulsa" com formulário mínimo → `create_with_lines` com 1 linha (Bill sem linha tem total 0).
- **Gerar mês + confirmar**: `generation_status = { missing_count }` — diff entre contas elegíveis (`BillGenerationService.is_account_eligible`, que já trata `BillSkip`, `tracking_start_month`, `end_date`, estado) e bills existentes no mês. Banner "Gerar contas faltantes (N)" sempre que N > 0 (cobre conta criada no meio do mês; `generate_month` é idempotente). Mês fechado → 400 tratado no banner.
  - Bill gerada nasce com **`Bill.amount_is_estimated=True`** e badge "valor estimado". Conta com `expected_amount=0` gera bill **sem linha** (total 0): badge "aguardando fatura" — nunca se confunde com paga.
  - Transições da flag **sempre em serviço, nunca em viewset**: `True` em `_ensure_account_bill` quando `created` (inclusive via caminho da parcela embutida); `False` em `create_with_lines` (default do model), `update_with_lines`, `pay` e `apply_invoice`. `unpay` **não** re-marca estimada. Não há `finances/admin.py` (sem caminho de edição fora da API).
- **Importar PDF no fluxo**: na linha de uma bill de água/luz estimada, "Importar fatura" → `apply_invoice` (§4). O fluxo avulso atual (botão no header → draft → modal) permanece para faturas sem bill gerada.
- Ações de ciclo de vida existentes (suspender, adiar, pular mês) no menu da linha. Nota: `defer` hoje não move `due_date`/`competence_month` — "adiada" é rótulo; a dívida continua contada na sub-seção própria.

### 3.4 Extrato por conta (`/finances/accounts/[id]`)

**Primeiro precedente de rota `[id]` no dashboard** — assumir explicitamente no plano (padrão: `'use client'` + `useParams()` + `PageHeader` + `StatCard` + `DataTable`; orçar definição de loading/404).

- Bills da conta agregadas por `Q(billing_account=conta) | Q(installment__plan__billing_account=conta)` — sem o segundo braço, conta IPTU (registry-only, parcelas em bills standalone) mostraria extrato vazio e saldo 0.
- StatCards: **saldo devedor acumulado** (mesmo critério do `open_balance`), faturas em aberto, **atraso médio de pagamento**: média de `MAX(payment_date) − due_date` das últimas 12 bills **quitadas** (`amount_remaining = 0`), considerando só alocações e payments vivos (`allocation.is_deleted=False AND payment.is_deleted=False`, espelhando `with_amounts`) e **excluindo bills com `amount_total = 0`**.
- Tabela mês a mês: competência, vencimento, total, pago, resto, status, estado, data de pagamento.
- Parcelamentos vinculados (embutidos ou avulsos) com progresso (parcela N/M).

### 3.5 Parcelar saldo devedor (consolidação de dívida)

O caso DMAE ("cortada, acumulando, teria que ser parcelada para resolver") não tem fluxo hoje: `convert_deferred` opera 1 bill por vez e **rejeita conta não-IPTU**. Entrega nova:

- Ação **"Parcelar saldo devedor"** no extrato da conta (e CTA na sub-seção de dívida do cockpit): seleciona bills em aberto da conta → cria **1** `InstallmentPlan` (embutido ou avulso, escolha do usuário) com `total = Σ amount_remaining` das selecionadas → **cancela as bills de origem na mesma transação** (senão saldo devedor e Atrasadas dobram a dívida). Parciais: o resto (não o total) entra no plano.
- Serviço: generalização multi-bill/multi-tipo em `InstallmentPlanService` (ex.: `consolidate_open_bills`). `convert_deferred` (IPTU anual adiado) permanece para o caso single-bill.
- **Pureza v1**: a consolidação rejeita bills que já são parcela de plano (FK `installment`) ou que carregam linha de parcela embutida de plano vivo — erro em português orientando cancelar/tratar o plano antigo primeiro. Sem isso, o plano velho continuaria gerando parcelas em paralelo ao novo (dupla dívida) e o progresso N/M mentiria. O caso-alvo (faturas recorrentes acumuladas da DMAE) não é afetado.
- CANCELED sai de Atrasadas, do `open_balance` e dos totais por definição (§3.3) — a dívida passa a viver só no plano.

## 4. API (novos endpoints/actions)

| Endpoint | Método | Retorno / comportamento | Cache |
| --- | --- | --- | --- |
| `finance-dashboard/month_board?year&month` | GET | `{ overdue[], deferred_suspended[], groups_por_prédio[], totals{due,paid,overdue,remaining}, generation{missing_count} }` | **Sem cache** (operacional; mesmo racional do `combined_calendar`) |
| `billing-accounts/{id}/statement` | GET | conta + StatCards + linhas mês a mês + planos vinculados (agregação dos dois braços de FK) | **Sem cache** |
| `billing-accounts` (list) | GET | + annotation `open_balance` via `BillingAccountQuerySet.with_open_balance()` — subquery própria sobre `Bill.objects.with_amounts()` (não agregar `amount_remaining` diretamente; sem precedente no repo, construir explícito) | **Sem cache (como hoje** — o viewset atual não tem cache; corrigido da rev. 1) |
| `bills/{id}/apply_invoice` | POST | `build_draft` (parser + match por `account_type+identifier` já existentes) → valida match contra a bill alvo, **incluindo comparação de `building`** (hoje ausente do draft — adicionar) → `update_with_lines` (linhas + statement upsert + header, transação única, guards UNPAID/mês aberto já existentes) + limpa flag. **Substitui apenas linhas sem FK `installment`** — linha de parcela embutida é intocável | — |
| `billing-accounts/{id}/consolidate_debt` | POST | `{ bill_ids[], embedded, ... }` → 1 plano + cancelamento atômico das origens (§3.5) | — |

Serviços novos/estendidos: `CondoMonthBoardService`, `AccountStatementService`, `InstallmentPlanService.consolidate_open_bills`, extensão de `BillPaymentService` (pagar-com-ajuste em transação) e `InvoiceDraftService` (building no draft). Viewsets apenas delegam. Serializers no padrão dual.

## 5. Modelo de dados — mudanças

- **Fase 1**: apenas `Bill.amount_is_estimated` (BooleanField, default `False`). Migration sequencial; tabela existente ⇒ sem ação de RLS. Juros/multa e consolidação usam modelos existentes (linha + plano + cancelamento).
- **Sem mudanças** em BillingAccount, InstallmentPlan, Payment, fechamento.

## 6. Fechamento mensal × pagador cronicamente defasado (decisão explícita)

`pay` exige competência aberta (`assert_open`). Quem paga sempre a fatura do mês anterior não pode fechar um mês e pagar depois. Decisão: **manter o guard** (relaxá-lo mexeria nos invariantes de `carried_in`). Em troca:

- O erro 400 no cockpit vira **acionável**: toast com link para o fechamento ("Reabra 06/2026 para registrar este pagamento") — o fluxo reabrir → pagar → fechar é seguro pós-P2.3 (`_recompute_following` corrige a cascata).
- O `close` ganha **preflight**: lista bills em aberto da competência com total, exigindo confirmação explícita antes de fechar.
- Fechamento é opcional no dia a dia; a operação normal do cockpit não depende dele.

## 7. Fase 2 — Terceiros (especificação; NÃO implementar agora)

Direção invertida em relação ao *family loans*: os proprietários **devem** aos filhos/genro.

- **`Payment.paid_by`** (FK → `core.Person`, nula = caixa dos proprietários) + `FundedFrom.THIRD_PARTY`. Pagamento de terceiro quita a conta normalmente mas **não sai do caixa** — vira dívida com a pessoa. (`Person` não é removível — plano P7.1.)
- **`ThirdPartyCharge`** (modelo novo, RLS na mesma migration): compras que o terceiro faz para os proprietários — avulsa ou parcelada, com **mês de cobrança** (quando cai no cartão dele, análogo ao `billing_month`), fora do fluxo de contas do condomínio.
- **Extrato por pessoa**: `devido(mês) = pagamentos de contas feitos por ela + gastos com cobrança no mês − reembolsos`. Reembolso como valor único, **alocado FIFO ao mês aberto mais antigo**; alocação **computada, nunca persistida**. Status: aberto / parcial / quitado / crédito.
- **Acerto mensal**: tela por pessoa com devido acumulado e registro do acerto.
- **Ajuste previsto**: `CondoBalanceService` aprende que `funded_from=third_party` não é saída de caixa. O atraso médio (§3.4) não é afetado (usa `payment_date`, independe do pagador).

Por que a Fase 1 não cria obstáculo: `paid_by` é coluna aditiva; `FundedFrom` é TextChoices extensível; cockpit e extrato leem `Payment` via allocation sem saber quem financiou.

## 8. Tratamento de erros

- Guards respondem **400** com mensagem em português no shape já usado pelo módulo (`error`/`detail`/erros por campo — contrato travado por testes; não fazer sweep de shape aqui).
- Cockpit: estado de carregamento por linha + toast com a mensagem do backend. **Sem optimistic update** — linha só muda após confirmação (mutação → invalidate → refetch do `month_board`).
- `apply_invoice` com conta/prédio/inscrição divergente → aviso explícito antes de aplicar; nunca aplica silenciosamente.
- Mês fechado (pagar/gerar): erro acionável com link para o fechamento (§6).

## 9. Testes

- **Backend (integração view→service→model)**:
  - `month_board`: atrasadas cross-competência (só ACTIVE), sub-seção deferred/suspended fora dos totais, CANCELED invisível, `generation.missing_count` com BillSkip/tracking/conta nova no meio do mês, 400 só em `year`/`month` inválidos. **Correção rev. 3 (achado da varredura final):** `month_board` é GET read-only e NÃO retorna 400 em mês fechado — o cockpit precisa exibir competência fechada. O guard de mês fechado pertence ao `generate_month` (POST) que o banner dispara, e é lá que o 400 é testado.
  - `statement`/`open_balance`: braço `installment__plan__billing_account` (conta IPTU não zera), conta cortada acumulando, atraso médio (exclui `amount_total=0`, exige quitada, alocações/payments vivos).
  - Flag `amount_is_estimated`: gerar→True (incl. via caminho embutido), editar/importar/pagar→False, `unpay` não re-marca, `bulk_pay` coberto via serviço.
  - Pagar-com-ajuste: estimada com valor real maior/menor (linha-semente ajustada, sem resto fantasma), juros/multa em confirmada, atomicidade.
  - `apply_invoice`: match ok, mismatch de building/inscrição, preservação de linha de parcela embutida.
  - `consolidate_debt`: N bills (incl. parciais) → 1 plano com total = Σ restos + origens canceladas, atomicidade, dupla contagem impossível.
- **Frontend (Vitest + MSW)**: cockpit (popover pagar/editar, banner gerar faltantes, seções Atrasadas/adiada-suspensa), contas cadastradas (CRUD, célula-link), extrato (primeira página `[id]`). MSW: handlers de action de collection **antes** das rotas `:id` (regra documentada em `handlers.ts`); factories novas (`createMockMonthBoard`, `createMockAccountStatement`); blocos novos em `query-keys.ts` (`monthBoard`, `billingAccounts.statement`) antes dos hooks.
- **Gate**: ≥90% cobertura em `finances/`, zero warnings. Regressão com escopo (arquivos/apps tocados).
- **Mock policy**: só fronteiras externas (HTTP via MSW, PDF fixture); nunca código interno.

## 10. Conformidade com a arquitetura (gate)

| Regra | Como o design cumpre |
| --- | --- |
| Views → Services → Models | Lógica nova em serviços (`CondoMonthBoardService`, `AccountStatementService`, `consolidate_open_bills`); transições de flag em serviço; viewsets delegam |
| `finances → core` unidirecional | Mantido (Fase 2 usa `core.Person`, direção permitida) |
| Serializer dual pattern | Mantido em todos os serializers novos/alterados |
| Soft delete | Annotations e atraso médio replicam os filtros de `with_amounts` (alocação viva + payment vivo) |
| Cache + signals | `month_board`/`statement`/`billing-accounts` sem cache (decisão explícita, coerente com `combined_calendar`/`overdue`/`iptu_alerts`) |
| Frontend | TanStack Query, `useCrudPage`, Zod, RHF; Popover existente para inline (sem estender `DataTable`); primeiro `[id]` assumido explicitamente |
| Dinheiro via ORM annotation | `open_balance` como subquery própria; nunca `@property` |
| RLS | Sem tabela nova na Fase 1; `ThirdPartyCharge` (Fase 2) habilita RLS na própria migration |

## 11. Fora de escopo (YAGNI)

- Simulação de regularização ("se eu parcelar em N vezes, como fica o mês") — a projeção existente cobre o suficiente; o `consolidate_debt` (§3.5) resolve o ato, não a simulação.
- Mudanças no fechamento além do preflight (§6); reserva, distribuição e folha intactas.
- Remoção do legado `financial/` — plano P7.1, fora deste trabalho.
- Foto de fatura (OCR de imagem) — só PDF (parser DMAE/CEEE existente).
- Sweep de shape de erro `{error}→{detail}` — contrato travado por testes, decisão anterior mantida.
