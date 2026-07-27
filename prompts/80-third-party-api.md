# Sessão 80 — API: acertos, extrato, compra de terceiro e `pay` estendido

**Fase 2 (terceiros) — sessão 4 de 6.** Backend (serializers, viewsets, URLs). Fecha o backend da fase.

Design: `@docs/plans/2026-07-27-condo-third-party-payments-design.md` §7.

Depende de: S77 (modelo), S78 (caixa), S79 (extrato).

## Contexto

- **Design (ler §7)**: `@docs/plans/2026-07-27-condo-third-party-payments-design.md`
- **Regras**: `CLAUDE.md`, `.claude/rules/architecture.md` (views→services→models), `.claude/rules/security.md` (admin-only), `.claude/rules/coding-standards.md`

### Exemplares (arquivo:linha)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Serializer dual + validate espelhando `clean()`** | `finances/serializers.py:584+` (`EmployeeSerializer`) | Padrão nested-read/`_id`-write e a duplicação deliberada da validação (DRF pula `full_clean`) |
| **ViewSet CRUD registrado** | `finances/viewsets/installment_payroll_views.py:146` (`EmployeeViewSet`) + registro em `finances/urls.py:33` | **Atenção**: os viewsets estão espalhados em mais de um módulo — `crud_views.py` tem Category/BillingAccount/Bill/Payment/Reserve/Income, e `installment_payroll_views.py` tem Employee/InstallmentPlan. Colocar o `ThirdPartySettlementViewSet` em `crud_views.py` (é CRUD simples) |
| **Ação de leitura em dashboard viewset** | `finances/viewsets/dashboard_views.py` (`by_owner`) | Forma da action, validação de query param → 400 PT, decisão de cache |
| **Serviço transacional criando Bill+linhas** | `finances/services/bill_service.py` (`create_with_lines`) | `transaction.atomic`, `full_clean`, criação de `BillLineItem` |
| **Guard duplo de mês fechado** | `finances/services/bill_payment_service.py:93-94` | `assert_open(competence_month)` **e** `assert_open(payment_date.replace(day=1))` |
| **Validação de `funded_from`** | `finances/viewsets/crud_views.py:96-106` (`_validated_funded_from`) | Ponto único; estender aqui, não no serializer |
| **`PaymentSerializer` read-only** | `finances/serializers.py:449-483` | `amount`/`funded_from` read-only; `Payment` só nasce em serviço |

## Arquivos

- **Modificar**: `finances/serializers.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py`, `finances/urls.py`, `finances/services/bill_payment_service.py`
- **Criar**: `finances/services/third_party_purchase_service.py`
- **Criar**: `tests/integration/test_finances/test_third_party_api.py`

## Escopo

### 1. `ThirdPartySettlementSerializer` + `ThirdPartySettlementViewSet`

CRUD completo, padrão dual (`person` nested read / `person_id` write via `PrimaryKeyRelatedField(write_only=True, source="person")`). Exemplar exato: `EmployeeSerializer` em `finances/serializers.py:592-599` — já faz precisamente isso com `Person`.

**`PersonSimpleSerializer` já existe** e é o usado para o lado read (`serializers.py:592`). Reusar; **não** criar outro serializer de pessoa. Aqui `person_id` é **obrigatório** (`required=True`, sem `allow_null`), ao contrário do `Employee` — um acerto sem pessoa não existe.

`IsAdminUser` (módulo inteiro é admin-only — `.claude/rules/security.md`). Registrar em `finances/urls.py` como `third-party-settlements`.

Validação no serializer espelhando `clean()` (DRF pula `full_clean`) — padrão explícito da casa (`finances/models.py:605`, "mirrored by EmployeeSerializer.validate").

### 2. `ThirdPartyPurchaseService` (novo serviço)

A compra nasce **paga** — o terceiro já pagou no cartão dele. Criar `Bill` + `Payment(THIRD_PARTY)` que a quita, **na mesma transação**:

```python
@staticmethod
def create_purchase(condominium, person, description, amount, competence_month,
                    due_date, category=None, building=None, user=None) -> Bill
```

- `Bill(paid_by_person=person, ...)` + 1 `BillLineItem` com o valor (bill sem linha tem total 0)
- `BillPaymentService.pay(bill, payment_date=due_date, funded_from=THIRD_PARTY, paid_by=person, user=user)`
- `transaction.atomic()` — falha em qualquer ponto → rollback total, **sem `Bill` órfã**
- `CondoMonthCloseService.assert_open` no mês de competência **e** no mês de caixa (mesmo guard duplo de `pay`, `bill_payment_service.py:93-94`)

**Parcelamento — NÃO usar `InstallmentPlan`** (§4.5 do design; a versão inicial errava aqui e a revisão adversarial provou):

`InstallmentPlanService.materialize_schedule` cria só linhas `Installment`; as `Bill`s nascem depois, num **job mensal** (`bill_generation_service.py:221-228`) a partir de um `defaults` **hardcoded** sem `paid_by_person`, e nascem **não pagas** — o oposto de "a compra nasce paga".

`create_purchase(..., installment_count=N)` cria ele mesmo, **numa transação**, N `Bill`s + N `Payment`s:

- parcela *i* → `Bill(paid_by_person=P, competence_month=mês_base + i, description="<desc> (i/N)")` + 1 linha, quitada por seu `Payment(THIRD_PARTY, paid_by=P)`
- divisão com `quantize_money` e **sobra de centavos na primeira parcela** — `Σ parcelas == total exato` (teste obrigatório: 3× sobre R$100,00)
- guard de mês fechado em **todas** as competências; alguma fechada → rejeita tudo
- `installment` da bill fica **vazio** (não é plano do condomínio)

**Não** tocar `BillGenerationService`, `InstallmentPlanService` nem criar `InstallmentPlan.paid_by_person`.

### 3. `BillPaymentService.pay` — parâmetro `paid_by`

```python
def pay(bill, payment_date, amount=None, funded_from=FundedFrom.CAIXA,
        new_total=None, paid_by=None, user=None) -> Payment
```

**Posição do parâmetro é obrigatória, não estética.** `paid_by` entra **depois** de `new_total` e **antes** de `user`. Motivo verificado: os chamadores de produção passam os 4 primeiros argumentos posicionalmente e o resto por keyword — `crud_views.py:505-512` (`bill, payment_date, amount, funded_from`) e `crud_views.py:548-550` (`bill, payment_date, None, funded_from`). Inserir `paid_by` antes de `funded_from` quebraria os dois silenciosamente. Há também um chamador posicional em teste (`tests/integration/test_finances_bill_statement_api.py:106`, terceiro arg `None`). Nenhum deles pode ser alterado por esta sessão.

- Repassar `paid_by` ao `Payment.objects.create`
- Validar a invariante da S77 **antes** de criar, importando as constantes públicas `ERR_THIRD_PARTY_NEEDS_PERSON`/`ERR_PERSON_ONLY_THIRD_PARTY` de `finances.models` (não duplicar texto). Necessário porque `Payment.objects.create()` **pula `full_clean()`** — o `clean()` da S77 sozinho não protege este caminho.
- `funded_from=THIRD_PARTY` **não** debita reserva (só `RESERVE` faz) — o `if` existente já garante; cobrir com teste

### 4. `_validated_funded_from` + `paid_by_person_id` nas actions

`_validated_funded_from` (`crud_views.py:96`) é o ponto único de validação. Estender `pay` **e `bulk_pay`** para exigir `paid_by_person_id` quando `funded_from == "third_party"`.

**`bulk_pay` é obrigatório**: sem ele, é caminho de escape para criar pagamento de terceiro sem pessoa. Cobrir com teste dedicado.

`paid_by_person_id` inválido/inexistente → 400 PT (não 500).

### 3b. `paid_by_person` no `BillSerializer` — obrigatório (senão o badge da S82 não existe)

`BillSerializer.Meta.fields` (`finances/serializers.py:328+`) é **allowlist explícita**, não `__all__`. Sem esta entrega, o campo **não aparece** no payload de `month_board` (que serializa por ele) e o badge da S82 fica impossível — a revisão adversarial pegou exatamente esse buraco no plano.

- `paid_by_person` (nested read, reusar `PersonSimpleSerializer`) + `paid_by_person_id` (write) em `Meta.fields`
- adicionar a FK no `select_related` de `Bill.objects.with_list_relations()` (`finances/models.py:344`) — senão N+1 no cockpit
- teste: `month_board` traz `paid_by_person` preenchido numa compra e `null` numa conta comum; contagem de queries **não** cresce com o número de compras

### 4b. Ciclo de vida da compra — CRÍTICO (§4.3.1 do design)

A revisão adversarial provou que a compra de terceiro **nasce paga** e por isso `suspend`/`cancel`/`delete`/`update_with_lines` **falham** nela: `BillService.assert_not_paid` (`bill_service.py:63-71`) rejeita bill com pagamento vivo. Sem o abaixo, um lançamento errado é **incorrigível pela UI**.

1. **`BillPaymentService.unpay` rejeita compra de terceiro.** Se alguma bill alocada tem `paid_by_person`, `ValidationError` PT: `"Uma compra de terceiro não pode ter o pagamento desfeito — exclua a compra."`
   **Por quê:** hoje `unpay` deixaria a `Bill` ativa e **não paga** → ela vira "conta a pagar do caixa" no cockpit enquanto o extrato continua cobrando a dívida da pessoa. **O mesmo dinheiro duas vezes**, com risco de pagar de novo o que o filho já pagou.
2. **`ThirdPartyPurchaseService.delete_purchase(bill, user)`** — único caminho de correção. Numa transação: apaga `Payment` + alocação (chamando o caminho interno, **não** o `unpay` público que agora rejeita) e soft-delete da `Bill`. Guard de mês fechado nos dois meses.
3. **`bills/{id}/reassign_payer`** — corrige pagador errado: atualiza `Bill.paid_by_person` **e** `Payment.paid_by` na mesma transação. Necessário porque `paid_by_person` **não** está em `_EDITABLE_HEADER_FIELDS` (`bill_service.py:128-140`) e `update_with_lines` cai no `assert_not_paid`.

### 4c. `ThirdPartySettlementService` — guard de mês fechado (CRÍTICO)

O acerto é saída de caixa real; `CondoMonthClose.cash_balance_end` é congelado. Acerto criado/apagado em mês fechado corrompe o snapshot — **mesma classe de bug que o projeto já corrigiu para pagamentos** (B3, `bill_payment_service.py:13-16`).

**Proibido expor `ModelViewSet` puro para este model.** Create/update/**delete** passam por `ThirdPartySettlementService`, que chama `CondoMonthCloseService.assert_open(settlement_date.replace(day=1))` — inclusive no delete.

### 5. Ações de leitura

- `GET third-party/people` → pessoas com dívida viva: `[{person_id, person_name, total_em_aberto, total_atrasado, last_settlement_date}]`, ordenado por `total_em_aberto` desc
- `GET third-party/statement?person_id=` → `ThirdPartyStatementService.build` verbatim
- `POST bills/create_purchase` → `ThirdPartyPurchaseService.create_purchase`

`person_id` ausente/inválido → 400 PT. Decimais **string**.

**NÃO cachear** — decisão fechada, não pesquisar. O extrato depende de `today_sp()`; virada de meia-noite não é escrita, então o cache nunca invalidaria. Precedentes: `month_board` (`dashboard_views.py:310-312`) e `AccountStatementService` ("read-only, uncached"). (Além disso `finances/signals.py` não mapeia model→prefixo: tudo passa por um `invalidate_finance_caches()` único — não há invalidação por prefixo a acrescentar.)

**Shape de erro** (o módulo usa dois, não misturar): guards de action → `{"error": "<PT>"}` (`crud_views.py:496,542`); validação de serializer → shape nativo do DRF (`{"campo": ["msg"]}`). `{"detail": …}` é só para 405.

**Nota da revisão da S77:** a regra de exclusividade de origem levanta `ValidationError({NON_FIELD_ERRORS: …})` (cobre 3 campos, não há campo único). Ao espelhar em serializer, levantar de `validate()` — **não** de `validate_<campo>()`. E no teste da resposta HTTP, esperar a chave **`non_field_errors`**: o DRF renomeia; não assumir a string literal `__all__`.

### 3c. Follow-up herdado da S77 (Important, corrigir aqui)

`_EDITABLE_HEADER_FIELDS` (`bill_service.py:128-140`) inclui `billing_account`, e `_apply_header` chama `full_clean()` (`:275`). Depois da S77, editar `billing_account` numa bill que já tem `installment` (parcela avulsa) **bate na regra nova de exclusividade** e devolve o erro genérico de múltiplas origens — mensagem inútil para o usuário.

Nenhum dado atual dispara isso (0 bills multi-origem, verificado local **e** em produção), mas o caminho existe. Corrigir: em `update_with_lines`, rejeitar `billing_account` quando a bill tem `installment`, com mensagem PT dedicada (ex.: `"Não é possível trocar a conta de cobrança de uma parcela."`). Teste obrigatório.

## TDD

Red primeiro. Obrigatórios:

1. CRUD do acerto (create/list/retrieve/update/delete) + `amount <= 0` → 400
2. Não-admin → 403 em **todas** as rotas novas
3. `pay` com `third_party` sem `paid_by_person_id` → 400 PT
4. **`bulk_pay` idem** → 400 PT
5. `pay` com `third_party` + pessoa → 201, bill quitada, caixa inalterado
6. `create_purchase` → `Bill` + `Payment` criados, bill já quitada, caixa inalterado
7. `create_purchase` com erro no meio → **rollback total** (nenhuma `Bill` órfã no banco)
8. `create_purchase` em mês fechado → 400 PT
9. `statement` sem `person_id` → 400; pessoa inexistente → 400 (não 500)
10. `people` ordena por dívida desc e omite quem não deve nada
11. Extrato reflete acerto imediatamente após criá-lo (pega cache velho se houver)
12. **`unpay` de pagamento de compra → 400 PT** (e a bill continua paga)
13. **`delete_purchase`** remove `Bill` **e** `Payment` atomicamente; a bill some do cockpit e a dívida some do extrato
14. **`reassign_payer`** troca os dois lados; extrato da pessoa antiga zera e o da nova recebe
15. **Acerto em mês fechado → 400 PT** no create, no update **e no delete**
16. `create_purchase` com competência aberta mas data de caixa em mês fechado → 400 dizendo **qual** mês
17. `bulk_pay` com `third_party` atribui **todas** as bills à mesma pessoa (comportamento desejado, travar com teste)

## NÃO fazer

- **Não** criar frontend (S81/S82).
- **Não** alterar `condo_balance_service` (S78) nem o serviço de extrato (S79).
- **Não** afrouxar `PaymentViewSet` (create/update seguem 405 — `Payment` só nasce em serviço).
- **Não** reimplementar cronograma de parcelas.

## Aceite

- Rodada escopada verde: `python -m pytest tests/integration/test_finances/test_third_party_api.py --cov-fail-under=0` (sem a flag falha mesmo com tudo verde — `pytest.ini` embute `--cov-fail-under=90`)
- Suíte `finances` completa sem regressão — é aqui que o gate de 90% vale
- `ruff` + `mypy core/ finances/` + `pyright` zerados
- `makemigrations --check` → "No changes detected"
- Cobertura `finances` ≥90%
