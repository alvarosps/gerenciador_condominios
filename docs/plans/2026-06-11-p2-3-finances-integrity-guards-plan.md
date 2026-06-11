# Plano P2.3 — Integridade do app finances (guards de escrita, fechamento, parcelamento)

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P2 · **Branch sugerida:** `fix/finances-integrity-guards` · **Depende de:** nenhum

## Objetivo

Fechar os buracos de integridade do app `finances/` (o app NOVO, não legado) onde as rotas CRUD default do DRF e algumas decisões de service contornam guards que só existem nos paths "ricos" (actions/services). Hoje é possível: editar/pagar uma `Bill` paga ou de mês fechado via PATCH/POST default, dar HARD DELETE num `CondoMonthClose` fechado (destruindo a baseline do fold de caixa), pagar uma `Bill` `CANCELED` (dupla cobrança), perder o monitoramento de IPTU porque o plano vira `PAID` por materialização (sem pagamento), corromper o `carried_in` dos meses subsequentes no `reopen`, e congelar o saldo de reserva all-time em vez do saldo do fim do mês. Este plano move toda escrita de `Bill`/`Payment`/`CondoMonthClose` para os guards canônicos (ou os replica no caminho default sem quebrar o modal de edição da UI), corrige o fold/reserve do fechamento, e introduz um estado `MATERIALIZED` distinto de `PAID` para parcelas geradas mas não pagas.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | CRUD default de `BillViewSet` contorna guards (PATCH/POST ignora bill paga / mês fechado / `competence_month` imutável) | `finances/viewsets/crud_views.py:283-565` | Tornar `BillViewSet` read-only para o CRUD default (`update`/`partial_update`/`create`/`destroy` delegam aos guards ou são removidos) — escrita só via actions `create_with_lines`/`update_with_lines`/`pay`/transições |
| ALTO | `PaymentViewSet` POST com `amount` read-only → 500; PATCH muda `payment_date` desfazendo nada das alocações | `finances/viewsets/crud_views.py:153-187` | Restringir `PaymentViewSet` a list/retrieve + `destroy` (unpay); bloquear `create`/`update`/`partial_update` (405 PT) |
| ALTO→MÉDIO | `CondoMonthCloseViewSet` é `ModelViewSet` completo: DELETE = HARD DELETE de snapshot fechado destrói baseline; `reference_month`/`condominium_id` graváveis | `finances/viewsets/crud_views.py:674`, `finances/serializers.py:727-763` | `CondoMonthCloseViewSet` vira `ReadOnlyModelViewSet` + actions `close`/`reopen`; `reference_month`/`condominium_id` read-only no serializer |
| ALTO | `_mark_completed_plans_paid` marca plano `PAID` por MATERIALIZAÇÃO (sem pagamento) → `IptuAlertService` filtra `ACTIVE` e para de monitorar parcelas em aberto | `finances/services/bill_generation_service.py:306-323`, `iptu_alert_service.py:62-66` | Novo estado `InstallmentPlanState.MATERIALIZED`; `IptuAlertService` avalia `ACTIVE` E `MATERIALIZED` |
| ALTO | `reopen` corrompe `carried_in` dos meses subsequentes (não recomputa `carry_forward_out` em cascata anaorada) / `close` não recomputa forward | `finances/services/condo_month_close_service.py:100-144` | `reopen` recomputa `carry_forward_out` via fold anaorado no mesmo loop em que recomputa caixa |
| ALTO→MÉDIO | `reserve_balance_end` congela saldo de reserva all-time atual, não o do fim do mês | `finances/services/condo_month_close_service.py:155`, `condo_balance_service.py:134-155` | `reserve_balance(as_of=...)` filtra `movement_date < 1º dia de M+1`; `_apply_frozen_figures` passa o `as_of` do mês |
| MÉDIO | `assert_open` não cobre `create_with_lines`/`delete`/`set_state`/`ensure_month_bills`/`IncomeEntry`/`ReserveService` | `bill_service.py:191-301`, `bill_lifecycle_service.py:23-36`, serializers de `IncomeEntry`/`ReserveMovement` | Aplicar `assert_open` em `create_with_lines`, `BillService.delete`, `set_state`, e nos writes de `IncomeEntry`/reserva quando o mês de competência estiver fechado |
| MÉDIO | `pay()` não valida `lifecycle_state` (pagar bill `CANCELED`/`SUSPENDED`/`DEFERRED` = dupla cobrança) | `finances/services/bill_payment_service.py:54-97` | Rejeitar `pay()` quando `bill.lifecycle_state != ACTIVE` (PT 400) |
| MÉDIO | `BillSkip` via API não normaliza `reference_month` para o dia 1 (DRF pula `clean()`) | `finances/serializers.py:409-417`, `models.py:460-463` | `BillSkipSerializer.validate_reference_month` → `value.replace(day=1)` |
| MÉDIO | Vínculo `Payment`↔`ReserveMovement` por heurística (`bill+kind+amount` order by `-id`) — sem FK | `finances/services/bill_payment_service.py:111-119`, `models.py:710-712` | `ReserveMovement.payment` FK (`SET_NULL`); `pay` grava, `unpay` reverte pela FK determinística |

## Abordagem técnica

A ordem abaixo é a ordem de execução TDD (cada bloco: teste vermelho → fix → verde → próximo bloco). Os blocos com migration vêm agrupados no fim para um único `makemigrations`.

### 1. `pay()` rejeita bill não-ACTIVE (`bill_payment_service.py`)

Em `BillPaymentService.pay` (linha 54), logo após `CondoMonthCloseService.assert_open(bill.competence_month)` (linha 66) e antes do `with transaction.atomic()`, adicionar guard de lifecycle:

```python
if bill.lifecycle_state != BillLifecycleState.ACTIVE:
    raise ValidationError(_BILL_NOT_ACTIVE)
```

Importar `BillLifecycleState` de `finances.models` (já importa `Bill`, `FundedFrom`, etc. nas linhas 23-31). Adicionar a constante `_BILL_NOT_ACTIVE = "Só é possível pagar uma conta ativa."` junto às outras (linhas 45-47). O guard usa o `bill` recebido (o `lifecycle_state` não é annotation; é coluna real, lido direto). `bulk_pay` (crud_views.py:368) já delega a `pay`, então herda o guard automaticamente.

### 2. `assert_open` nos pontos faltantes

`BillService.create_with_lines` (bill_service.py:191) — adicionar `CondoMonthCloseService.assert_open(draft.competence_month)` no topo do método, antes do `try`. `update_with_lines` (linha 260) já chama `assert_open` (linha 280); `create` não chamava.

`BillService.delete` (bill_service.py:291) — adicionar `CondoMonthCloseService.assert_open(bill.competence_month)` no topo, antes do `with transaction.atomic()`. (Deletar uma bill de mês fechado muda o resultado congelado.)

`BillLifecycleService.set_state` (bill_lifecycle_service.py:23) e `reactivate` (linha 31) — adicionar `CondoMonthCloseService.assert_open(bill.competence_month)` no início de `set_state` (cobre suspend/defer/cancel/reactivate, todos passam por `set_state`). Importar `CondoMonthCloseService`.

`IncomeEntrySerializer` (serializers.py:665) e `ReserveMovement` (escrita via `ReserveService.deposit/withdraw`): a competência destes não é um `competence_month` direto — `IncomeEntry.income_date` e `ReserveMovement.movement_date`. Aplicar `assert_open(value.replace(day=1))` no `validate` do `IncomeEntrySerializer` sobre `income_date`/`received_date` (o mês cuja contabilidade muda), e em `ReserveService.deposit`/`withdraw` sobre `movement_date`. CRITICAL: serializers NUNCA importam services (regra de arquitetura) — portanto, para `IncomeEntry`, mover o guard para o `IncomeEntryViewSet.perform_create`/`perform_update` (crud_views.py:648) que chama `CondoMonthCloseService.assert_open`, OU deixar o guard só em `ReserveService` (service) e, para `IncomeEntry`, validar no viewset. Decisão: guard no viewset (`perform_create`/`perform_update` de `IncomeEntryViewSet`) e em `ReserveService.deposit`/`withdraw` (já é service). Não tocar no serializer de `IncomeEntry` para o guard.

### 3. `PaymentViewSet` — só leitura + destroy (crud_views.py:153)

`PaymentViewSet` continua `ModelViewSet` (precisa de `destroy` já sobrescrito em 174). Bloquear os writes default sobrescrevendo `create`/`update`/`partial_update` para retornar 405 PT:

```python
_PAYMENT_WRITE_BLOCKED = (
    "Pagamentos são criados/editados apenas via contas/{id}/pay e contas/{id}/unpay."
)

def create(self, request, *args, **kwargs):
    return Response({"detail": _PAYMENT_WRITE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

def update(self, request, *args, **kwargs):
    return Response({"detail": _PAYMENT_WRITE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

partial_update = update
```

(`amount`/`funded_from` já são read-only no serializer (serializers.py:454); o problema é o POST com `amount` read-only → o serializer aceita criar `Payment` sem `amount` → `IntegrityError`/500 no `payment_amount_positive`. Bloqueando `create`/`update` o caminho some.)

### 4. `BillViewSet` — fechar CRUD default de escrita (crud_views.py:283)

O modal da UI usa as actions `create_with_lines`/`update_with_lines` (S58/S63), NUNCA o PATCH/POST default do recurso `bills/`. Confirmar isso buscando consumidores em `frontend/` e `mobile/` (grep por `bills/${` e `useUpdateBill`/`api.patch('/bills`). O CRUD default não é usado pela UI, mas está exposto e contorna: (a) `BillService.update_with_lines` guard de bill paga / mês fechado; (b) imutabilidade de `competence_month` (o serializer `validate_competence_month` normaliza p/ dia 1 mas PERMITE reescrever a competência num PATCH default). Sobrescrever no `BillViewSet`:

```python
_BILL_WRITE_BLOCKED = (
    "Contas são criadas/editadas via contas/create_with_lines e contas/{id}/update_with_lines."
)

def create(self, request, *args, **kwargs):
    return Response({"detail": _BILL_WRITE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

def update(self, request, *args, **kwargs):
    return Response({"detail": _BILL_WRITE_BLOCKED}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

partial_update = update
```

`destroy` já está sobrescrito (linha 556) delegando a `BillService.delete` — após o passo 2 ele também ganha `assert_open`. As actions `pay`/`bulk_pay`/`suspend`/`defer`/`cancel`/`reactivate`/`generate_month`/`create_with_lines`/`update_with_lines`/`parse_invoice` permanecem (são o caminho rico, com guards).

### 5. `CondoMonthCloseViewSet` — read-only + actions (crud_views.py:674)

Trocar a base de `viewsets.ModelViewSet` para `viewsets.ReadOnlyModelViewSet`. Isso remove `create`/`update`/`partial_update`/`destroy` (o DELETE que faz HARD DELETE de snapshot fechado some). As actions `close` (linha 709) e `reopen` (linha 713) permanecem (`@action(detail=False)`). O `get_queryset` (linha 679) e o `_close_action` (linha 690) ficam inalterados.

No `CondoMonthCloseSerializer` (serializers.py:727): `reference_month` e `condominium_id` viram read-only. Hoje `reference_month` é gravável (fora de `read_only_fields`, linhas 752-763) e `condominium_id` é `PrimaryKeyRelatedField(write_only=True)` (linha 729). Como o viewset não terá mais write path default, o serializer só serve para leitura — adicionar `reference_month` a `read_only_fields` e remover `condominium_id` write (deixar só `condominium` nested read). Manter `validators: list[object] = []` não é necessário aqui (não há `UniqueTogetherValidator` problemático no read). O viewset não usa o serializer para escrever; as actions usam `CondoMonthCloseSerializer(close, ...)` só para serializar a resposta.

### 6. `reopen` recomputa `carry_forward_out` em cascata (condo_month_close_service.py:100)

Hoje `reopen` (linha 117-138) recomputa apenas o **caixa** (`running_cash`) dos meses subsequentes ainda fechados, chamando `_apply_frozen_figures` que internamente recomputa `carry_forward_out` via `folded_distribution` (linha 161). MAS `folded_distribution` → `carried_in_for` (linha 200) lê o `carry_forward_out` do "mais recente mês fechado anterior" no BANCO. Durante o loop, os snapshots anteriores do loop ainda não foram salvos com o novo `carry_forward_out` antes de o próximo ler — exceto que `snap.save()` (linha 138) ocorre a cada iteração, então o próximo `carried_in_for` lê o valor recém-salvo. PORÉM o mês `M` reaberto continua no banco com `status=OPEN` e seu `carry_forward_out` antigo (não zerado): `carried_in_for` filtra `status=CLOSED` (linha 205), então M reaberto é corretamente ignorado. O bug real: o **primeiro** mês subsequente fechado herda como `carried_in` o `carry_forward_out` de um mês ANTERIOR a M (correto), mas a baseline de caixa `running_cash` parte de `cash_balance(subsequent[0].reference_month)` que já reflete M aberto — consistente. Verificar com teste se o `carried_in` realmente corrompe; se sim, a correção é garantir que o loop recompute `carry_forward_out` ANCORADO no fold rodando (não relendo o banco a cada passo). Concretamente: passar um `carried_in` corrente pelo loop em vez de `carried_in_for` reler o banco:

- Em `_apply_frozen_figures`, extrair o cálculo de `carry_forward_out` para aceitar um `carried_in` opcional (quando fornecido pela cascata, usa-o; senão, lê do banco via `carried_in_for`). Inicializar `running_carried_in = carried_in_for(subsequent[0].reference_month)` antes do loop e, a cada iteração, `available, carried_out = fold_step(net, running_carried_in); running_carried_in = carried_out`.

Isto torna o fold da cascata uma dobra rodada (running fold) idêntica em espírito à do caixa, sem depender de saves intermediários. CRITICAL: tudo dentro do mesmo `transaction.atomic()` já existente (linha 104).

Adicionalmente, garantir que `close()` recompute forward quando fecha um mês "no meio" (raro — o guard `_guard_no_gap` impede fechar M com M-1 aberto, então fechar sempre acontece na ponta; um fechamento fora de ordem só ocorre se um mês posterior já estiver fechado, o que `_guard_no_gap` permite). Se `close(M)` ocorrer com M+1 já fechado, M+1 precisa recomputar seu `carried_in` a partir do novo `carry_forward_out` de M. Adicionar ao final de `close`, dentro da mesma transação, uma chamada ao mesmo recompute-forward usado em `reopen` (extrair `_recompute_following(reference_month, condominium, user)` helper compartilhado, DRY).

### 7. `reserve_balance` com `as_of` (condo_balance_service.py:134 + condo_month_close_service.py:155)

`reserve_balance` ganha parâmetro `as_of: date | None = None`:

```python
@staticmethod
def reserve_balance(condominium_id: int | None = None, as_of: date | None = None) -> Decimal:
    movements = ReserveMovement.objects.filter(reserve__is_deleted=False)
    if condominium_id is not None:
        movements = movements.filter(reserve__condominium_id=condominium_id)
    if as_of is not None:
        movements = movements.filter(movement_date__lt=as_of)
    ...
```

`as_of` = 1º dia de M+1 (exclusivo: movimentos ATÉ o fim de M). Em `_apply_frozen_figures` (condo_month_close_service.py:155), trocar `CondoBalanceService.reserve_balance()` por `CondoBalanceService.reserve_balance(as_of=_next_month(snapshot.reference_month))`. `_next_month` já é importado (linha 25). Callers existentes (`total_balance` linha 161, `overview`, dashboard) continuam chamando sem `as_of` (saldo all-time atual) — comportamento inalterado.

### 8. `BillSkipSerializer.validate_reference_month` (serializers.py:409)

Adicionar método:

```python
def validate_reference_month(self, value: date) -> date:
    # DRF.create() não chama Model.clean(); normalizar para o 1º dia (espelha BillSkip.clean).
    return value.replace(day=1)
```

`date` já está importado (serializers.py:9). Espelha `BillSkip.clean` (models.py:460-463) e o padrão de `BillSerializer.validate_competence_month` (linha 359).

### 9. Estado `MATERIALIZED` + IPTU monitora `ACTIVE`+`MATERIALIZED` (models + bill_generation + iptu_alert)

`InstallmentPlanState` (models.py:466) ganha `MATERIALIZED = "materialized", "Materializado"` entre `ACTIVE` e `PAID`. Semântica: TODAS as parcelas geraram bill/line (não há mais o que gerar), MAS não significa pagas. `PAID` passa a ser reservado para quando o plano é efetivamente quitado (todas as bills pagas) — uma decisão futura/manual, fora deste plano (YAGNI: não auto-marcar PAID por pagamento aqui).

`_mark_completed_plans_paid` (bill_generation_service.py:306) renomeia para `_mark_completed_plans_materialized` e seta `InstallmentPlanState.MATERIALIZED` (não `PAID`). Atualizar o call site (linha 90) e a docstring (linhas 8-11, 71-72). O filtro do loop continua `lifecycle_state=ACTIVE` (só promove ACTIVE→MATERIALIZED).

`_active_installments_for_month` (linha 135) filtra `plan__lifecycle_state=ACTIVE` — um plano MATERIALIZED não deve regerar parcelas (já materializou), então mantém `ACTIVE` (correto: MATERIALIZED não regenera). Verificar que `is_account_eligible` e a geração embedded/standalone também filtram ACTIVE (linhas 145, 250 do iptu/installment query) — sim, todos via `_active_installments_for_month`.

`IptuAlertService.evaluate` (iptu_alert_service.py:62) muda o filtro de `lifecycle_state=ACTIVE` para `lifecycle_state__in=[ACTIVE, MATERIALIZED]`. Assim um plano de IPTU totalmente materializado (todas as parcelas viraram bills) MAS com parcelas vencidas não pagas continua sendo monitorado pelo alerta. `InstallmentSerializer.get_is_overdue` (serializers.py:467-470) compara `plan.lifecycle_state == ACTIVE` — mudar para `in (ACTIVE, MATERIALIZED)` (uma parcela materializada não-paga ainda está "overdue").

### 10. FK `ReserveMovement.payment` determinística (models + bill_payment_service)

`ReserveMovement` (models.py:695) ganha campo:

```python
payment = models.ForeignKey(
    Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="reserve_movements"
)
```

(`SET_NULL` espelha `bill` na linha 710; soft-delete do Payment não apaga o histórico do movimento.) `BillPaymentService._withdraw_reserve_for_bill` (linha 127) ganha o `payment` como argumento e o repassa; `ReserveService.withdraw` precisa aceitar `payment=...`. Em `pay` (linha 94-95), passar `payment` ao withdraw. Em `unpay` (linha 110-121), trocar a heurística `ReserveMovement.objects.filter(bill=..., kind=..., amount=...).order_by("-id").first()` por `ReserveMovement.objects.filter(payment=payment, kind=ReserveMovementKind.WITHDRAWAL)` (determinístico; um payment pode ter no máx 1 withdrawal de reserva neste design, mas iterar e reverter todos é seguro).

`ReserveMovementSerializer` (serializers.py:640) adiciona `payment` aos `fields` como PK read-only (espelha `bill` na linha 651), para a UI exibir o vínculo. Migração de dados: backfill do `payment` nos movimentos de reserva existentes ligados a bills pagas (ver Migrations / dados).

## Arquivos a criar / modificar

**Modificar:**
- `finances/services/bill_payment_service.py` — guard `pay()` não-ACTIVE (passo 1); FK `payment` no withdraw/unpay (passo 10); constante `_BILL_NOT_ACTIVE`.
- `finances/services/bill_service.py` — `assert_open` em `create_with_lines` e `delete` (passo 2).
- `finances/services/bill_lifecycle_service.py` — `assert_open` em `set_state` (passo 2); import de `CondoMonthCloseService`.
- `finances/services/reserve_service.py` — `assert_open(movement_date.replace(day=1))` em `deposit`/`withdraw`; aceitar `payment=...` em `withdraw` (passos 2, 10).
- `finances/services/condo_month_close_service.py` — recompute-forward de `carry_forward_out` em `reopen` + helper `_recompute_following` chamado em `close` (passo 6); `reserve_balance(as_of=...)` em `_apply_frozen_figures` (passo 7).
- `finances/services/condo_balance_service.py` — `reserve_balance(..., as_of=...)` (passo 7).
- `finances/services/bill_generation_service.py` — `_mark_completed_plans_materialized` (estado MATERIALIZED), call site, docstrings (passo 9).
- `finances/services/iptu_alert_service.py` — filtro `lifecycle_state__in=[ACTIVE, MATERIALIZED]` (passo 9).
- `finances/viewsets/crud_views.py` — bloquear `create`/`update`/`partial_update` em `BillViewSet` e `PaymentViewSet`; `assert_open` em `IncomeEntryViewSet.perform_create/perform_update`; `CondoMonthCloseViewSet` → `ReadOnlyModelViewSet` (passos 3, 4, 5).
- `finances/serializers.py` — `BillSkipSerializer.validate_reference_month` (passo 8); `CondoMonthCloseSerializer`: `reference_month` read-only + remover `condominium_id` write (passo 5); `ReserveMovementSerializer` + campo `payment` read-only (passo 10); `InstallmentSerializer.get_is_overdue` inclui MATERIALIZED (passo 9).
- `finances/models.py` — `InstallmentPlanState.MATERIALIZED` (passo 9); `ReserveMovement.payment` FK (passo 10).

**Criar:**
- `finances/migrations/0007_installmentplan_materialized_reservemovement_payment.py` (auto via `makemigrations`) — adiciona o choice MATERIALIZED (não altera schema, choices não são DB-enforced; mas `AlterField` é gerado) + a coluna `ReserveMovement.payment` (nullable). RLS já habilitado nessas tabelas existentes (não cria tabela nova). Inclui `RunPython` de backfill (ver dados).

**Testes (criar/estender):**
- `tests/.../finances/test_bill_payment_service.py` — guards pay/lifecycle/reserve-FK.
- `tests/.../finances/test_bill_service_guards.py` — assert_open em create/delete.
- `tests/.../finances/test_bill_lifecycle_service.py` — assert_open em set_state.
- `tests/.../finances/test_condo_month_close_service.py` — reopen cascade carry_forward + reserve as_of.
- `tests/.../finances/test_bill_generation_service.py` — MATERIALIZED (não PAID).
- `tests/.../finances/test_iptu_alert_service.py` — monitora plano MATERIALIZED com parcela vencida.
- `tests/.../finances/test_crud_views_guards.py` — 405 nos writes default de Bill/Payment; CondoMonthClose sem DELETE.
- `tests/.../finances/test_serializers.py` — BillSkip dia-1; CondoMonthClose read-only.

(Localizar o diretório de testes exato com `python -m pytest --collect-only -q tests | findstr finances` antes de criar; seguir o layout existente.)

## TDD — cenários de teste

**Pagamento / lifecycle (`bill_payment_service`):**
- `test_pay_rejeita_bill_canceled` — `pay()` numa bill `CANCELED` levanta `ValidationError` PT, nenhuma `Payment`/`PaymentAllocation` criada (regressão do bug de dupla cobrança).
- `test_pay_rejeita_bill_suspended` / `test_pay_rejeita_bill_deferred` — idem para os outros estados não-ACTIVE.
- `test_pay_aceita_bill_active` — caminho feliz preservado.
- `test_pay_reserve_grava_movement_com_payment_fk` — `funded_from='reserve'` cria `ReserveMovement` com `payment` apontando para o `Payment`.
- `test_unpay_reverte_pela_payment_fk` — `unpay` soft-deleta o `ReserveMovement` resolvido pela FK (não pela heurística); reserva restaurada ao saldo anterior.
- `test_unpay_reverte_com_dois_movements_mesmo_bill_amount` — edge: dois pagamentos distintos de reserva com mesmo `bill`+`amount`; `unpay` de um reverte SÓ o movimento daquele payment (a heurística antiga reverteria o errado — este é o teste de regressão do vínculo).

**Guards de mês fechado (`bill_service`, `bill_lifecycle_service`, `reserve_service`, viewset income):**
- `test_create_with_lines_rejeita_mes_fechado` — `assert_open` barra criação em competência fechada.
- `test_delete_rejeita_mes_fechado` — `BillService.delete` barra mês fechado.
- `test_set_state_rejeita_mes_fechado` — suspend/cancel/defer barrados em mês fechado.
- `test_reactivate_rejeita_mes_fechado` — idem (passa por set_state).
- `test_reserve_deposit_rejeita_mes_fechado` / `test_reserve_withdraw_rejeita_mes_fechado` — guard sobre `movement_date`.
- `test_income_entry_create_rejeita_mes_fechado` — `IncomeEntryViewSet.perform_create` barra `income_date` em mês fechado (via APIClient).
- `test_create_with_lines_mes_aberto_ok` / `test_set_state_mes_aberto_ok` — regressão dos caminhos felizes.

**Fechamento (`condo_month_close_service`):**
- `test_reopen_recomputa_carry_forward_dos_meses_seguintes` — fechar M, M+1, M+2 com nets negativos encadeados; reopen M; M+1/M+2 têm `carry_forward_out` recomputado pelo fold ancorado no novo baseline (valor exato verificado contra `fold_step`). REGRESSÃO do bug.
- `test_close_no_meio_recomputa_forward` — M+1 já fechado, fecha M (anterior); M+1 recomputa `carried_in` a partir do novo `carry_forward_out` de M.
- `test_reserve_balance_end_congela_saldo_do_fim_do_mes` — depósito de reserva em M+1 NÃO entra no `reserve_balance_end` do snapshot de M (filtro `movement_date < 1º de M+1`). REGRESSÃO do bug all-time.
- `test_reserve_balance_sem_as_of_inalterado` — chamada sem `as_of` continua somando tudo (dashboard).

**Geração / IPTU (`bill_generation_service`, `iptu_alert_service`):**
- `test_plano_totalmente_materializado_vira_materialized_nao_paid` — após `ensure_month_bills` que materializa todas as parcelas, `plan.lifecycle_state == MATERIALIZED`. REGRESSÃO.
- `test_iptu_alert_monitora_plano_materialized_com_parcela_vencida` — plano IPTU MATERIALIZED com 1 parcela-bill vencida não paga → 1 `IptuRiskRow` WARNING (antes: plano PAID era filtrado e o alerta sumia). REGRESSÃO.
- `test_iptu_alert_ignora_plano_canceled` — CANCELED continua fora do monitoramento.
- `test_materialized_nao_regenera_parcelas` — segundo `ensure_month_bills` não duplica linhas de um plano MATERIALIZED.

**Viewsets (`crud_views` via APIClient + is_staff):**
- `test_bill_patch_default_405` — `PATCH /api/finances/bills/{id}/` retorna 405 PT (não muda `competence_month`).
- `test_bill_post_default_405` — `POST /api/finances/bills/` retorna 405 PT.
- `test_bill_create_with_lines_ainda_funciona` — a action rica continua 201 (modal da UI intacto). REGRESSÃO do "não quebrar o modal".
- `test_bill_update_with_lines_ainda_funciona` — action de edição 200.
- `test_payment_post_default_405` / `test_payment_patch_default_405` — writes default bloqueados (antes: POST → 500).
- `test_payment_destroy_unpay_funciona` — DELETE ainda reverte via unpay.
- `test_condo_month_close_delete_405` — `DELETE /api/finances/condo-month-closes/{id}/` retorna 405 (ReadOnly). REGRESSÃO do hard-delete da baseline.
- `test_condo_month_close_post_default_405` / `test_condo_month_close_patch_405` — create/update default bloqueados.
- `test_condo_month_close_close_action_ok` / `reopen_action_ok` — actions canônicas intactas.

**Serializers:**
- `test_bill_skip_normaliza_reference_month_dia_1` — POST com `reference_month=2026-06-15` persiste `2026-06-01`.
- `test_condo_month_close_serializer_reference_month_read_only` — campo não aparece como gravável; payload com `reference_month` é ignorado.

## Migrations / dados

**Migration:** `finances/migrations/0007_installmentplan_materialized_reservemovement_payment.py` (gerada por `makemigrations finances`).
- `AlterField` em `InstallmentPlan.lifecycle_state` (novo choice MATERIALIZED — choices não são DB-enforced, é metadado; a migration é gerada mesmo assim).
- `AddField` `ReserveMovement.payment` (`ForeignKey` nullable, `SET_NULL`).
- NÃO cria tabela nova → NÃO precisa de novo `ENABLE ROW LEVEL SECURITY` (as tabelas `installmentplan` e `reservemovement` já têm RLS habilitado de migrations anteriores). Confirmar com `python manage.py showmigrations finances` e checar se há `RunSQL` de RLS para essas tabelas; se a tabela `reservemovement`/`installmentplan` já estava sob RLS, nada a fazer.
- `RunPython` de backfill (com `reverse_code=migrations.RunPython.noop`):
  - **`payment` em `ReserveMovement`**: para cada `ReserveMovement(kind=WITHDRAWAL, bill__isnull=False, payment__isnull=True)`, resolver o `Payment` via `PaymentAllocation(bill=movement.bill, amount=movement.amount)` mais recente cujo `Payment.funded_from='reserve'`; setar `movement.payment`. Onde a heurística for ambígua (múltiplos candidatos), deixar `null` (o vínculo passa a ser determinístico só para movimentos novos — aceitável; os antigos continuam funcionando pela ausência de FK, e a UI mostra `payment=null`).
  - **`lifecycle_state` PAID→MATERIALIZED**: identificar planos hoje `PAID` que foram marcados por materialização (todas as parcelas têm bill/line mas NENHUM pagamento real registrado) e movê-los para `MATERIALIZED`. Heurística de detecção: plano `PAID` cujas bills de parcela existem mas cujas `PaymentAllocation` somadas < total das bills. CRITICAL: como prod ainda não tem o conceito de PAID-por-pagamento, na prática TODO plano `PAID` atual foi marcado por materialização → mover todos os `PAID` para `MATERIALIZED` é seguro e correto. Confirmar lendo os dados de prod antes (via Supabase MCP `execute_sql` read-only: `SELECT lifecycle_state, count(*) FROM finances_installmentplan GROUP BY 1`).

**Backup antes do migrate:** `python scripts/backup_db.py` (local) ANTES de `migrate`. Em prod, o deploy roda migrate — garantir backup Supabase (pg_dump da connection string do Dashboard) antes do deploy desta migration, conforme `.claude/rules/database.md`.

**Dado vivo em prod:** os planos de IPTU que hoje estão `PAID` por materialização e deixaram de ser monitorados serão re-incluídos no `IptuAlertService` ao virarem `MATERIALIZED` — verificar com o usuário se algum alerta IPTU "sumiu" recentemente (o digest cita 9 WARNING em prod via `project_condo_utility_bills`).

## Constraints (o que NÃO fazer)

- NÃO tocar no módulo financeiro legado do `core/` (Person/Expense/RentPayment/cash-flow/daily-control/financial-dashboard) nem na seção `app/(dashboard)/financial/` — fora do escopo (são DEPRECATED).
- NÃO quebrar o modal de edição de contas da UI: as actions `create_with_lines`/`update_with_lines`/`pay`/`bulk_pay`/transições DEVEM continuar funcionando exatamente. Os 405 são SÓ no CRUD default (`POST /bills/`, `PATCH /bills/{id}/`, writes de `payments/`, writes/DELETE de `condo-month-closes/`).
- NÃO auto-marcar plano como `PAID` por pagamento neste plano (YAGNI) — `MATERIALIZED` é o estado terminal da geração; `PAID` real é decisão futura.
- NÃO usar `# noqa`/`# type: ignore`/`eslint-disable`/`@ts-ignore`; sem `from __future__ import annotations`; sem TODO/FIXME; sem re-exports; sem shims de compat.
- Serializers NUNCA importam services — o `assert_open` de `IncomeEntry` vai no viewset (`perform_create`/`perform_update`), não no serializer.
- `Decimal` sempre com `quantize_money`/`money_str` no boundary; nada de `float`.
- NÃO editar migrations existentes (hooks bloqueiam) — criar nova via `makemigrations`.
- Mensagens de erro: PT para usuário (Response/ValidationError), EN para logs.
- NÃO adicionar `FORCE ROW LEVEL SECURITY`; NÃO mexer no estado RLS das tabelas (já habilitado).

## Critérios de aceite (binários)

- [ ] `POST /api/finances/bills/` e `PATCH /api/finances/bills/{id}/` retornam 405 com `detail` PT; `competence_month` jamais é alterado por essas rotas.
- [ ] `create_with_lines`/`update_with_lines` continuam 201/200 (modal da UI verificado por teste).
- [ ] `POST`/`PATCH`/`PUT` em `/api/finances/payments/` retornam 405 (antes: POST → 500); `DELETE` ainda reverte via `unpay`.
- [ ] `DELETE`/`POST`/`PATCH` em `/api/finances/condo-month-closes/{id}/` retornam 405; `close`/`reopen` actions intactas.
- [ ] `CondoMonthCloseSerializer.reference_month` e `condominium` são read-only.
- [ ] `pay()` em bill `CANCELED`/`SUSPENDED`/`DEFERRED` levanta `ValidationError` PT; nada é criado.
- [ ] `create_with_lines`, `BillService.delete`, `set_state`/`reactivate`, `ReserveService.deposit/withdraw`, `IncomeEntry` create/update barram mês fechado.
- [ ] `_mark_completed_plans_materialized` seta `MATERIALIZED` (nunca `PAID`); `IptuAlertService` retorna risco para plano IPTU `MATERIALIZED` com parcela vencida.
- [ ] `reopen` recomputa `carry_forward_out` dos meses fechados subsequentes pelo fold ancorado; `close` no meio recomputa forward.
- [ ] `reserve_balance_end` do snapshot reflete apenas movimentos com `movement_date < 1º de M+1`; `reserve_balance()` sem `as_of` inalterado.
- [ ] `BillSkip` via API persiste `reference_month` no dia 1.
- [ ] `ReserveMovement.payment` FK existe; `pay` grava, `unpay` reverte pela FK; backfill aplicado.
- [ ] Migration `0007_*` aplica e reverte sem erro; backup feito antes.
- [ ] Gate de verificação passa (escopado + regressão), zero erros e zero warnings.

## Gate de verificação

Backend, escopado nos arquivos editados + regressão dirigida do app finances:

```bash
ruff check finances/ && ruff format --check finances/
mypy core/ finances/
pyright finances/
python -m pytest tests -k "finances or bill or reserve or condo_month or iptu or payment" -p no:randomly
```

(A suite cheia tem flakiness pré-existente de xdist/Redis — NÃO é bloqueio; rodar escopado conforme `feedback_testing_scope`.) Migration: `python manage.py makemigrations finances --check` (sem migrations faltando após o trabalho) e `python manage.py migrate finances` num banco com backup.

Frontend (só se algum consumidor do CRUD default de bills/payments existir — verificar com grep antes; se a UI já usa só as actions, nenhuma mudança FE):

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

## Handoff

Commit sugerido:

```
fix(finances): close write-guard bypasses, fix close/reopen fold, split MATERIALIZED from PAID

- pay() rejects non-ACTIVE bills (no double charge)
- assert_open on create_with_lines/delete/set_state/reserve/income writes
- BillViewSet/PaymentViewSet block default CRUD writes (405 PT); modal actions intact
- CondoMonthCloseViewSet read-only (no hard-delete of frozen snapshot); reference_month read-only
- reopen recomputes carry_forward_out forward; close recomputes following; reserve_balance(as_of)
- InstallmentPlanState.MATERIALIZED (not PAID by materialization); IptuAlert monitors MATERIALIZED
- ReserveMovement.payment FK (deterministic unpay); BillSkip reference_month day-1

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar `MEMORY.md` (entrada nova: "Finances integrity guards") apontando para este doc e para a migration `0007`. Atualizar `prompts/SESSION_STATE.md` se o trabalho for executado como sessão numerada.

O próximo plano pode assumir: (1) escrita de `Bill`/`Payment`/`CondoMonthClose` só pelos paths canônicos com guards; (2) `MATERIALIZED` ≠ `PAID` (o `PAID`-por-pagamento real ainda NÃO existe — futuro plano se necessário); (3) `ReserveMovement.payment` é o vínculo determinístico (não usar mais a heurística bill+amount); (4) `reserve_balance(as_of=...)` disponível para qualquer snapshot histórico.
