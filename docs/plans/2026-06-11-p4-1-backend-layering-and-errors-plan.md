# Plano P4.1 — Camadas do backend: extrair services, padronizar erros, validar input

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** P4 (Arquitetura/Qualidade) · **Branch sugerida:** `refactor/backend-layering` · **Depende de:** P2 (para nao conflitar em arquivos quentes — `core/serializers.py`, `core/views.py`, `core/viewsets/*`)

---

## ⚠️ REVISÃO 2026-06-12 (pós P1/P2/HF-1) — LEIA PRIMEIRO; supera os passos abaixo onde conflitar

Este plano foi escrito em 2026-06-11, antes de P1/P2/HF-1 serem implementados+mergeados. Revisão code-grounded (file:linha confirmados no master #17):

### JÁ FEITO — remover do escopo (não recriar)
- **Fatia B inteira (PixService.resolve_recipient + cidade configurável)** → FEITO no P2.2. A API real é função module-level `resolve_pix_recipient(lease) -> dict` em `core/services/pix_service.py:130` (NÃO um método de classe com dataclass `PixRecipient`); `tenant_views.py:252` já delega; `_DEFAULT_CITY="Porto Alegre"` em `pix_service.py:15`. **Excluir a Fatia B.**
- **Fatia G passo 4 — "Criar `core/exceptions.py`" + "Registrar EXCEPTION_HANDLER"** → FEITO no HF-1. `core/exceptions.py:17` (`custom_exception_handler`, converte `DjangoValidationError`→400) e `settings.py:218` já existem. **NÃO recriar nem registrar** — apenas ESTENDER (ver gaps).
- **Unificação de `IsAdminUser`** → FEITO no P1.2 (`core/permissions.py:32` única classe; ninguém importa a do DRF).
- **Todas as referências file:linha estão defasadas.** Atuais: `LeaseSerializer.create`=534-563, `.update`=565-584; `ExpenseInstallmentSerializer`=825; `IncomeSerializer`=1038; `RentPaymentSerializer`=1088; `FinancialSettingsSerializer`=1264; `PaymentProofSerializer`=1281; `proof review`=`proof_views.py:57-102`; `generate_installments`=`financial_views.py:209-261`; `transfer`=`views.py:576-585`; `change_due_date`=`views.py:505` ({"error"} em :518); `adjust_rent` {"error"} em :609/615/623/634.

### REESCOPOS
- **Fatia G (padronização de erros)** → reescopar para: (1) **ESTENDER** `core/exceptions.py` p/ mapear `DoesNotExist`→`NotFound(404)` e `KeyError`→`ValidationError(400)` (o handler do HF-1 só cobre `DjangoValidationError`; KeyError em `lease_service.py:37`, DoesNotExist em `financial_views.py:202/348/434/525`, IntegrityError ainda dão **500**); (2) migrar as `Response({"error": ...})` manuais para `{"detail": ...}`. **⚠️ COORDENAÇÃO MOBILE:** `mobile/app/(admin)/actions/mark-paid.tsx:50` lê `error.response.data.error` do `proof_views.review` (`{"error"}` em :67/74/80/87). Migrar esse endpoint quebra o mobile (P3 não feito) → atualizar o consumidor mobile no MESMO PR, OU deixar o shape do proof-review como está e migrar só os endpoints sem consumidor mobile. Decidir explicitamente.
- **Fatia A passo 2 (`_DOUBLE_OCCUPANCY`)** → **NÃO remover do serializer** — usada em 3 validações (`serializers.py:196` max_tenants, :476 "1 ou 2", :493 resident_dependent), não só no create. Manter no serializer OU mover para módulo de constantes e importar nos dois.
- **Fatia A signal de sync `last_rent_increase_date`** → `transfer_lease` cria lease via `Lease.objects.create()` sem setar o campo (`lease_service.py:76-89`), e `terminate/transfer` usam `.update()` (não dispara post_save). Tratar esses caminhos OU documentar que o sync não cobre `.update()`. Considerar manter o sync no service em vez de signal.
- **Fatia F (ExpenseInstallmentSerializer → nested)** → **ALTO RISCO: NÃO fazer como descrito.** Frontend tem `expense: z.number()` (`expense-installment.schema.ts:5`); objeto aninhado **quebra o parse e esvazia a lista** (re-introduz o bug "parcelas vazias"). `ExpenseSimpleSerializer` NÃO existe. Módulo legado/deprecated → **reescopar p/ correção mínima OU pular** (gap de depreciação).
- **Fatia E item 3 (PaymentProof.validate_reference_month)** → o plano NORMALIZA (`replace(day=1)`), mas `RentPaymentSerializer.validate_reference_month` (:1109-1113) **REJEITA** dia≠1. Alinhar (rejeitar é o precedente) OU justificar a divergência.
- **Critério "?person_id=abc → 400 não 500"**: `rent_calendar`/`change_due_date`/`adjust_rent` já dão 400 (`views.py:790-808`, :521-553) — só o SHAPE está errado. 500 real só em `financial_views.py:161`, `transfer` (KeyError), `mark_paid` (DoesNotExist). Não superdimensionar.

### GAPS DA AUDITORIA QUE FALTAM (adicionar)
- **`UserAdminSerializer` (`user_admin_views.py:41,50`) chama `set_password()` sem `validate_password()`** — achado P4.1 em NENHUM plano. Adicionar `validate_password(password, user)` no create/update.
- **`month_advance_views.py:79, 99, 136`** usam `int(year)/int(month)` crus (além de 116/125/159) → cobrir TODOS no helper de parse de query-param.

### DEPENDÊNCIA / COLISÃO
- **Este plano (P4.1) é o DONO de `core/services/lease_creation_service.py` (`LeaseCreationService`) e da reescrita de `LeaseSerializer.create`.** O P4.3 (passo 2) tentava criar o MESMO arquivo + re-extrair a derivação → **P4.3 passa a depender de P4.1**; P4.3 NÃO recria esse service. (Roadmap atualizado: P4.3 `Depende de: P4.1`.)

---

## Objetivo

Restaurar as camadas documentadas do backend (`Views -> Services -> Models`; serializers apenas validacao/transformacao) extraindo a logica de negocio que hoje vive em serializers e viewsets para services stateless, padronizar o shape de erro de toda a API no formato DRF (`{"detail": ...}` / erros por campo), e eliminar a classe de bugs em que entradas invalidas geram 500 (KeyError, `int()`/datas cruas, `DoesNotExist`). O foco e os endpoints ATIVOS (Lease, portal do inquilino, PIX, comprovante PIX); no modulo financeiro pessoal DEPRECATED, apenas correcoes minimas de robustez (sem refatoracao profunda).

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MEDIO | Logica de negocio em `LeaseSerializer.create/update` (deriva `rental_value`, defaulta `last_rent_increase_date`, grava `Apartment.last_rent_increase_date`) | `core/serializers.py:501-551` | Extrair `LeaseCreationService` + mover sync do apartamento para signal `post_save` de Lease |
| MEDIO | `TenantViewSet.payments_pix` resolve chave PIX e hardcoda `city="Sao Paulo"` na view | `core/viewsets/tenant_views.py:263-294` | Extrair `PixService.resolve_recipient(lease)` (chave/nome/cidade configuravel) |
| MEDIO | `AdminProofViewSet.review` implementa maquina de estados do comprovante na view | `core/viewsets/proof_views.py:82-100` | Extrair `ProofReviewService.review(proof, action, reason, user)` |
| MEDIO | `ExpenseViewSet.generate_installments` faz geracao de parcelas (dinheiro) no viewset | `core/viewsets/financial_views.py:209-261` | Mover para `ExpenseService.generate_installments` (residuo na ultima parcela + clamp due_day + parse de data) |
| MEDIO | Shape de erro `{"error"}` vs `{"detail"}` inconsistente em toda a API | `core/views.py:447-498,505,514`; `tenant_views.py`, `proof_views.py` etc. | Padronizar para shape DRF (levantar exceptions DRF + `EXCEPTION_HANDLER` custom) |
| MEDIO->BAIXO | Entradas invalidas geram 500 (`KeyError` em transfer, `int()`/datas cruas em financial_views, `DoesNotExist` em mark_paid) | `core/views.py:507-516`; `financial_views.py:161-173,202`; `tenant_views.py` | Helper `parse_query_param` (int/date -> `ValidationError`) + serializer de payload + `get_object_or_404` |
| BAIXO | Validacao de dinheiro/datas ausente em serializers financeiros (`Income.amount` negativo aceito; `RentPayment` negativo -> 500) | `core/serializers.py:1005-1052,1055-1088,1248-1282` | `validate_amount`/`validate_amount_paid`/`validate_reference_month` + cross-date em `PersonIncomeSerializer` |
| BAIXO | Dual pattern: `ExpenseInstallmentSerializer.expense` cru read+write; `FinancialSettings.updated_by` gravavel | `core/serializers.py:795-809,1243-1245` | `expense` nested read-only + `expense_id` write_only; `updated_by` read-only |

## Abordagem técnica

Ordem de execucao por fatia (cada fatia: Red -> Green -> Refactor -> Verify escopado antes de avancar). As fatias A-D sao endpoints ATIVOS (prioridade); E-F sao legado (correcao minima); G e a padronizacao transversal de erros.

### Fatia A — `LeaseCreationService` + sync de apartamento via signal (ativo)

1. Criar `core/services/lease_creation_service.py` com `LeaseCreationService`:
   - `resolve_rental_value(apartment: Apartment, number_of_tenants: int) -> Decimal`: replica a regra hoje em `serializers.py:509-515` — usa `apartment.rental_value_double` quando `number_of_tenants == 2` (constante `_DOUBLE_OCCUPANCY`, hoje em `serializers.py`) e o valor existe; senao `apartment.rental_value`.
   - `create(*, validated_data: dict[str, Any], tenants: list[Tenant]) -> Lease`: aplica o default de `rental_value` (se ausente) e de `last_rent_increase_date` (= `start_date`, hoje `serializers.py:516-517`), faz `Lease(**validated_data)`, `full_clean()`, `save()`, e `lease.tenants.set(tenants)`. NAO grava o apartamento aqui (passa a ser signal).
2. Mover a constante `_DOUBLE_OCCUPANCY` para o service (unica fonte); remover do serializer.
3. `LeaseSerializer.create` (serializers.py:501-530) passa a: separar `tenants`, delegar a `LeaseCreationService.create(...)`, retornar o lease. `LeaseSerializer.update` (532-551) mantem a atualizacao de campos/tenants no serializer (transformacao), mas REMOVE o bloco `apartment.last_rent_increase_date = ...; apartment.save(...)` (525-528 e 545-549).
4. Mover o sync para signal: em `core/signals.py`, no receiver `post_save` de Lease (mesmo arquivo que ja tem `sync_apartment_is_rented`, models.py:linhas dos receivers — confirmar nome real via grep `sync_apartment_is_rented`), adicionar `sync_apartment_last_rent_increase`: quando `instance.last_rent_increase_date` difere de `instance.apartment.last_rent_increase_date`, atualizar `apartment.last_rent_increase_date` com `apartment.save(update_fields=["last_rent_increase_date", "updated_at"])` (incluir `updated_at` por causa do achado AuditMixin — ate P4.x corrigir o mixin, manter explicito aqui). Usar `dispatch_uid` unico.
   - ATENCAO: `rent_adjustment_service.py:103` ja faz esse mesmo sync (achado nota duplicacao). Apos o signal existir, REMOVER o sync manual de `rent_adjustment_service.py` (refatoracao completa — o signal vira fonte unica). Verificar com grep `last_rent_increase_date.*save` em `core/`.

### Fatia B — `PixService.resolve_recipient` (ativo, portal inquilino + mobile)

1. Em `core/services/pix_service.py` adicionar `resolve_recipient(lease: Lease) -> PixRecipient` (dataclass com `pix_key`, `pix_key_type`, `merchant_name`, `city`). Replica a logica hoje em `tenant_views.py:265-281`: prioriza `apt.owner.pix_key`/`apt.owner.name`; senao `FinancialSettings.objects.filter(pk=1).first().default_pix_key`/`default_pix_key_type` + `Landlord.get_active().name`; fallback `merchant_name="Condomínio"`.
2. Cidade: tornar configuravel — ler de `Landlord.get_active().city` (ou `FinancialSettings`) com fallback. NAO hardcodar `"Sao Paulo"` (imoveis sao de Porto Alegre). Confirmar se `Landlord` tem campo `city`; se nao, usar fallback `"Porto Alegre"` como constante nomeada `DEFAULT_PIX_CITY` no service (YAGNI: nao criar coluna nova neste plano — registrar como follow-up).
   - OBS: a sanitizacao ASCII do EMV (acentos no `merchant_name`/`city`) e o length-em-bytes do TLV sao bugs SEPARADOS (achado high em `pix_service.py:10-26,44-53`) tratados em outro plano (P-bugs). Este plano so move a resolucao do destinatario para o service; nao alterar `_crc16_ccitt`/`_emv_field`.
3. `TenantViewSet.payments_pix` (tenant_views.py:256-294) passa a: obter `lease`, chamar `PixService.resolve_recipient(lease)`, passar os campos a `generate_pix_payload(...)`. Manter o `try/except ValueError -> 400`.

### Fatia C — `ProofReviewService.review` (ativo, app mobile admin)

1. Criar `core/services/proof_review_service.py` com `ProofReviewService.review(*, proof: PaymentProof, action: str, reason: str, user: User) -> PaymentProof`:
   - Valida `proof.status == "pending"` (senao levanta `rest_framework.exceptions.APIException`/`ValidationError` mapeada a 409 — usar uma `Conflict` custom ou `ValidationError` com status; ver Fatia G para o handler). Hoje a view retorna 409 em `proof_views.py:76-80`.
   - Valida `action in {"approve","reject"}` -> senao `ValidationError`.
   - Seta `reviewed_by=user`, `reviewed_at=timezone.now()`, `status` e `rejection_reason`, salva com `update_fields=["status","reviewed_by","reviewed_at","rejection_reason","updated_at"]` (incluir `updated_at`), chama `notify_proof_reviewed(proof)`.
2. `AdminProofViewSet.review` (proof_views.py:55-100) passa a: `get_object_or_404(PaymentProof, pk=pk)` (substitui o try/except manual 63-74), delegar ao service, retornar `PaymentProofSerializer(proof).data`. A maquina de estados sai da view.

### Fatia D — `ExpenseService.generate_installments` (legado em prod — correcao de dinheiro)

1. Mover a logica de `financial_views.py:209-261` para `ExpenseService.generate_installments(*, expense: Expense, start_date: date | None, user: User) -> Expense` (mesmo lugar de `rebuild_installments`):
   - Parse de `start_date` ja resolvido na camada de view via helper de parse (Fatia 0/G) — o service recebe `date | None`.
   - Calcular `installment_amount = (total / n).quantize(Decimal("0.01"), ROUND_HALF_UP)` para as `n-1` primeiras parcelas e a ULTIMA = `total - installment_amount * (n-1)` (residuo, garante soma == total).
   - Vencimento: quando ha credit_card, `_clamp_day(base_date, due_day)` = `min(due_day, ultimo dia do mes)` via `calendar.monthrange` — evita `ValueError` para due_day 29-31 (hoje `.replace(day=due_day)` estoura, financial_views.py:238-240). Sem credit_card, `start_date + relativedelta(months=i-1)`.
2. `ExpenseViewSet.generate_installments` passa a: validar `is_installment`/`total_installments` (400), validar `installments.exists()` (400), fazer parse de `start_date` com o helper (400 em formato invalido), delegar ao service.

### Fatia E — Validacao de dinheiro/datas nos serializers financeiros (legado — correcao minima)

1. `IncomeSerializer` (serializers.py:1005-1052): adicionar `validate_amount(self, value)` -> rejeita `value <= 0` (`ValidationError({"amount": "O valor deve ser positivo."})`).
2. `RentPaymentSerializer` (1055-1088): adicionar `validate_amount_paid` -> rejeita `<= 0` (evita IntegrityError/500 da CheckConstraint `rent_payment_amount_positive`).
3. `PaymentProofSerializer` (1248-1282): adicionar `validate_reference_month(self, value): return value.replace(day=1)` (consistencia com `RentPayment`/`EmployeePayment`/`PersonPayment`).
4. `PersonIncomeSerializer` (994-1004): `validate(self, attrs)` cross-date -> se `end_date` e `start_date` presentes e `end_date < start_date`, `ValidationError`.
5. Constantes de mensagem em PT no topo do serializer (Clean Code: sem magic strings repetidas).

### Fatia F — Correcoes do dual pattern (legado — minima)

1. `ExpenseInstallmentSerializer` (serializers.py:795-809): trocar `expense` cru por `expense = ExpenseSimpleSerializer(read_only=True)` (criar serializer leve se nao existir, ou reusar existente) + `expense_id = PrimaryKeyRelatedField(write_only=True, source="expense", queryset=Expense.objects.all())`. Atualizar `Meta.fields` e os consumidores (grep `ExpenseInstallmentSerializer` em `core/` e `frontend/` — confirmar se algum cliente le `expense` como inteiro cru; se sim, ajustar para `expense.id`/`expense_id`).
2. `FinancialSettingsSerializer` (1243-1245): mover `updated_by` para `read_only_fields` (campo de auditoria nunca gravavel pelo cliente).

### Fatia 0/G — Helper de parse de query params + padronizacao de erros (transversal)

1. Criar `core/utils/query_params.py` (novo pacote `core/utils/` se nao existir, com `__init__.py`):
   - `parse_int_param(value: str | None, *, field: str) -> int | None`: `None` -> `None`; senao `int(value)` capturando `ValueError` -> `serializers.ValidationError({field: [PT msg]})`.
   - `parse_date_param(value: str | None, *, field: str) -> date | None`: idem com `date.fromisoformat`.
   - Usar nos filtros de `financial_views.py:148-153,161-173` (substituindo `int(...)`/datas cruas) e em `month_advance_views.py:116,125,159` (year `int()`).
2. `TransferLeaseSerializer` (em `core/serializers.py`): valida `apartment_id` (PrimaryKeyRelatedField), `responsible_tenant_id`, `tenant_ids` (opcional), `validity_months` (default 12, `min_value=1`). `LeaseViewSet.transfer` (views.py:507-516) valida via serializer ANTES de chamar `transfer_lease`, eliminando o `KeyError` 500 (lease_service.py:37-38). `transfer_lease` continua recebendo o dict ja validado.
3. `DoesNotExist -> 404`: em `mark_paid`/`mark_received`/`bulk_mark_paid` (financial_views.py:202,348,434,525) trocar `Model.objects.select_for_update().get(pk=pk)` por bloco que captura `Model.DoesNotExist` e levanta `rest_framework.exceptions.NotFound` (PT).
4. **Padronizacao do shape de erro**:
   - Registrar `EXCEPTION_HANDLER` custom em `condominios_manager/settings.py` (`REST_FRAMEWORK["EXCEPTION_HANDLER"] = "core.exceptions.custom_exception_handler"`). Criar `core/exceptions.py` com `custom_exception_handler` que chama o `exception_handler` padrao do DRF e garante o shape `{"detail": ...}` para erros de string (mantendo erros por campo e `non_field_errors`).
   - Refatorar as Responses manuais `{"error": ...}` para `{"detail": ...}` OU para levantar exceptions DRF (`ValidationError`, `NotFound`). Pontos confirmados em `views.py`: `change_due_date` (449,482,486,490,496), `generate_contract` (380-404), `adjust_rent` (540-566; trocar `{"error": e.message_dict}` por `ValidationError`), `rent_calendar` (726-748), `toggle_rent_payment` (774-804). Pontos em `proof_views.py` (65,72,78), `financial_views.py`, `template_views.py`, `rule_views.py`. Padronizar para `{"detail"}`.
   - **Frontend/mobile (mesmo PR — sem manter dois formatos)**: `frontend/lib/utils/error-handler.ts` (linhas 94-108) JA suporta `{error}`, `{message}`, `{detail}`, `{non_field_errors}` — apos a migracao, REMOVER o branch `responseData.error` (94-96) pois nenhum endpoint o produzira (refatoracao completa, sem shim). EXCECAO: `frontend/app/auth/callback/page.tsx:52` le `data?.error === 'not_admin'` — isso e um CODIGO de erro do fluxo OAuth (core/adapters/auth), NAO o shape inconsistente deste plano; NAO alterar. Verificar `mobile/` com grep `\.error\b|\.detail\b` em handlers de erro e alinhar ao mesmo shape `{detail}`.

## Arquivos a criar / modificar

**Criar:**
- `core/services/lease_creation_service.py` — `LeaseCreationService` (resolve_rental_value, create).
- `core/services/proof_review_service.py` — `ProofReviewService.review`.
- `core/utils/__init__.py` + `core/utils/query_params.py` — `parse_int_param`, `parse_date_param`.
- `core/exceptions.py` — `custom_exception_handler` (shape DRF unificado).
- `tests/unit/services/test_lease_creation_service.py`
- `tests/unit/services/test_proof_review_service.py`
- `tests/unit/services/test_pix_service.py` (ou estender o existente) — `resolve_recipient`.
- `tests/unit/services/test_expense_service.py` (estender) — `generate_installments`.
- `tests/unit/test_query_params.py` — helper de parse.
- `tests/integration/test_exception_handler.py` — shape de erro.

**Modificar:**
- `core/serializers.py` — `LeaseSerializer.create/update` (delegar/limpar sync), `IncomeSerializer`, `RentPaymentSerializer`, `PaymentProofSerializer`, `PersonIncomeSerializer`, `ExpenseInstallmentSerializer`, `FinancialSettingsSerializer`, novo `TransferLeaseSerializer`.
- `core/signals.py` — receiver `sync_apartment_last_rent_increase` (post_save Lease).
- `core/services/pix_service.py` — `resolve_recipient` + `PixRecipient` dataclass + `DEFAULT_PIX_CITY`.
- `core/services/expense_service.py` — `generate_installments` + `_clamp_day`.
- `core/services/rent_adjustment_service.py` — REMOVER sync manual de `apartment.last_rent_increase_date` (linha ~103) agora coberto pelo signal.
- `core/viewsets/tenant_views.py` — `payments_pix` delega ao `PixService`.
- `core/viewsets/proof_views.py` — `review` delega ao `ProofReviewService` + `get_object_or_404`.
- `core/viewsets/financial_views.py` — `generate_installments` delega; filtros usam helper de parse; `mark_paid`/etc. `DoesNotExist -> 404`.
- `core/viewsets/month_advance_views.py` — `int(year)` via helper de parse.
- `core/views.py` — `transfer` valida via `TransferLeaseSerializer`; Responses `{"error"}` -> `{"detail"}`/exceptions DRF.
- `condominios_manager/settings.py` — `REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
- `frontend/lib/utils/error-handler.ts` — remover branch `responseData.error`.
- `frontend/lib/utils/__tests__/error-handler.test.ts` — atualizar casos para `{detail}`.
- `mobile/` — handlers de erro alinhados a `{detail}` (se houver leitura de `.error` que nao seja codigo OAuth).

## TDD — cenários de teste

**`test_lease_creation_service.py`:**
- `test_resolve_rental_value_single_tenant_uses_rental_value`
- `test_resolve_rental_value_two_tenants_uses_double_when_present`
- `test_resolve_rental_value_two_tenants_falls_back_when_double_none`
- `test_create_defaults_last_rent_increase_date_to_start_date`
- `test_create_sets_tenants_m2m`
- `test_create_respects_explicit_rental_value` (nao sobrescreve quando fornecido)

**Signal (`tests/unit/test_signals.py` ou integration):**
- `test_lease_save_syncs_apartment_last_rent_increase_date` (regressao: prova que a remocao do serializer nao quebrou o sync)
- `test_apartment_updated_at_changes_on_rent_increase_sync` (inclui updated_at no update_fields)
- `test_rent_adjustment_no_longer_duplicates_apartment_sync` (apos remover o sync manual, o apartamento ainda atualiza via signal)

**`test_pix_service.py`:**
- `test_resolve_recipient_owner_pix_key_priority`
- `test_resolve_recipient_falls_back_to_financial_settings_and_landlord`
- `test_resolve_recipient_default_merchant_name_condominio`
- `test_resolve_recipient_city_not_hardcoded_sao_paulo` (cidade vem de config/fallback Porto Alegre)

**`test_proof_review_service.py`:**
- `test_review_approve_sets_status_and_reviewer`
- `test_review_reject_sets_rejection_reason`
- `test_review_non_pending_raises_conflict` (status != pending)
- `test_review_invalid_action_raises_validation_error`
- `test_review_sets_updated_at` (update_fields inclui updated_at)

**`test_expense_service.py` (generate_installments):**
- `test_generate_installments_sum_equals_total` (regressao: R$100 em 3x -> 33.34 + 33.33 + 33.33 == 100.00)
- `test_generate_installments_last_takes_residual`
- `test_generate_installments_clamps_due_day_31_in_february` (regressao: due_day=31, fev nao estoura ValueError)
- `test_generate_installments_clamps_due_day_30_in_30day_month`
- `test_generate_installments_without_credit_card_uses_relativedelta`

**`test_query_params.py`:**
- `test_parse_int_param_none_returns_none`
- `test_parse_int_param_valid`
- `test_parse_int_param_invalid_raises_validation_error` (regressao do 500 com `?person_id=abc`)
- `test_parse_date_param_invalid_raises_validation_error`
- `test_parse_date_param_valid_iso`

**Serializers financeiros (`tests/integration/test_*_api.py`):**
- `test_income_negative_amount_returns_400` (regressao: hoje aceito silenciosamente)
- `test_income_zero_amount_returns_400`
- `test_rent_payment_negative_amount_returns_400` (regressao do IntegrityError 500)
- `test_payment_proof_reference_month_normalized_to_day_one`
- `test_person_income_end_before_start_returns_400`
- `test_expense_installment_serializer_dual_pattern` (write via `expense_id`, read aninhado)
- `test_financial_settings_updated_by_read_only` (cliente nao consegue gravar)

**Viewsets / robustez (integration):**
- `test_transfer_lease_missing_apartment_id_returns_400` (regressao do KeyError 500)
- `test_transfer_lease_invalid_validity_months_returns_400`
- `test_expense_filter_invalid_person_id_returns_400` (regressao do `int()` 500)
- `test_expense_filter_invalid_date_returns_400`
- `test_mark_paid_nonexistent_expense_returns_404` (regressao do DoesNotExist 500)
- `test_month_advance_invalid_year_returns_400`

**`test_exception_handler.py`:**
- `test_validation_error_returns_detail_shape`
- `test_not_found_returns_detail_shape`
- `test_error_responses_never_use_error_key` (varredura: nenhum endpoint refatorado retorna `{"error": ...}`)

**Frontend (`error-handler.test.ts`, MSW na fronteira HTTP):**
- `test_get_error_message_reads_detail` (mantem)
- `test_get_error_message_no_longer_special_cases_error_key` (apos remocao do branch; cai no fallback por status)
- Atualizar testes que hoje fornecem `{error: "..."}` para `{detail: "..."}`.

## Migrations / dados

N/A para schema (nenhuma tabela/coluna nova — `DEFAULT_PIX_CITY` e constante de codigo, nao coluna). Se durante a Fatia E se decidir adicionar `MinValueValidator`/CheckConstraint em `Income.amount` (achado sugere, mas e legado), isso seria uma migration nova com **backup antes** (`python scripts/backup_db.py`) e RLS nao se aplica (tabela ja existe) — porem este plano mantem a validacao no serializer (KISS/YAGNI), deixando a migration de constraint como follow-up explicito fora deste escopo.

## Constraints (o que NÃO fazer)

- NAO alterar `_crc16_ccitt`/`_emv_field` em `pix_service.py` (bug de acento/bytes e de outro plano P-bugs). Aqui so move a resolucao do destinatario.
- NAO refatorar profundamente o modulo financeiro pessoal DEPRECATED (`Expense`/`Income`/`RentPayment`/`cash-flow`/`daily-control`/`financial-dashboard`): nas Fatias D/E/F aplicar apenas a correcao pontual descrita (residuo/clamp, validacao de valor/data, dual pattern), sem reescrever services nem mexer em agregacoes.
- NAO criar coluna nova de cidade para PIX neste plano (YAGNI) — usar config existente/fallback nomeado.
- NAO adicionar `MinValueValidator`/CheckConstraint via migration neste plano (validacao fica no serializer; constraint e follow-up).
- NAO manter os dois shapes de erro coexistindo: remover o branch `responseData.error` do frontend (sem backwards-compat shim).
- NAO alterar `auth/callback/page.tsx:52` (`data?.error === 'not_admin'` e codigo OAuth, nao o shape inconsistente).
- Proibido: `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `TODO/FIXME`, `from __future__ import annotations`, re-exports.

## Critérios de aceite (binários)

- [ ] `LeaseSerializer.create/update` nao contem mais logica de derivacao de `rental_value` nem `apartment.save(...)`; toda essa logica vive em `LeaseCreationService` + signal.
- [ ] `core/services/rent_adjustment_service.py` nao duplica o sync de `apartment.last_rent_increase_date` (signal e fonte unica).
- [ ] `TenantViewSet.payments_pix` nao resolve chave PIX nem cidade inline — delega a `PixService.resolve_recipient`; cidade nao e `"Sao Paulo"` hardcoded.
- [ ] `AdminProofViewSet.review` nao implementa maquina de estados — delega a `ProofReviewService`; usa `get_object_or_404`.
- [ ] `ExpenseService.generate_installments`: soma das parcelas == `total_amount` e due_day 29-31 nao estoura `ValueError` em meses curtos.
- [ ] Nenhum endpoint refatorado retorna `{"error": ...}`; todos usam shape DRF `{"detail": ...}`/erros por campo; `EXCEPTION_HANDLER` registrado.
- [ ] `?person_id=abc`, data malformada, `apartment_id` ausente em transfer e `pk` inexistente em mark_paid retornam 400/404 (nao 500).
- [ ] Serializers financeiros rejeitam `amount`/`amount_paid` <= 0; `PaymentProofSerializer.reference_month` normalizado para dia 1; `PersonIncome` rejeita `end_date < start_date`.
- [ ] `ExpenseInstallmentSerializer` segue dual pattern; `FinancialSettings.updated_by` e read-only.
- [ ] Frontend `error-handler.ts` nao tem mais branch `responseData.error`; testes atualizados verdes.
- [ ] Gate de verificacao (abaixo) passa sem erros e sem warnings nos arquivos editados + regressao dirigida.

## Gate de verificação

Backend (escopado nos arquivos editados + regressao dirigida; a suite cheia tem flakiness pre-existente de xdist/Redis e NAO e bloqueio):

```bash
ruff check core/ tests/ && ruff format --check core/ tests/
mypy core/
pyright
python -m pytest tests/unit/services/test_lease_creation_service.py tests/unit/services/test_proof_review_service.py tests/unit/services/test_pix_service.py tests/unit/services/test_expense_service.py tests/unit/test_query_params.py tests/integration/test_exception_handler.py -p no:xdist
# Regressao dirigida nos endpoints tocados:
python -m pytest tests/integration/test_lease_api.py tests/integration/test_tenant_portal.py tests/integration/test_proof_views.py tests/integration/test_expense_api.py tests/integration/test_income_api.py -p no:xdist
```

Frontend:

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Zero erros E zero warnings (Ruff, mypy, Pyright, ESLint, TypeScript, pytest).

## Handoff

**Commit sugerido:**

```
refactor(backend): extract business logic to services, standardize error shape, validate input

- Add LeaseCreationService + apartment last_rent_increase sync via post_save signal
- Add PixService.resolve_recipient (configurable city, no hardcoded Sao Paulo)
- Add ProofReviewService for payment-proof state machine
- Move generate_installments to ExpenseService (residual on last parcel, clamp due_day)
- Register custom EXCEPTION_HANDLER; unify error shape to DRF {"detail"} across API
- Add query-param parse helpers (int/date) and TransferLeaseSerializer to turn 500s into 400/404
- Add money/date validation to financial serializers; fix dual-pattern violations
- Frontend: drop legacy {error} branch from error-handler

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

**Estado/docs:** atualizar `MEMORY.md` (entrada P4.1) com: services extraidos, shape de erro unificado, e a remocao do sync duplicado em `rent_adjustment_service`. Registrar follow-ups deixados fora de escopo: (a) bug ASCII/bytes do EMV PIX (`pix_service.py:10-26,44-53`), (b) constraint `Income.amount >= 0` via migration, (c) coluna `city` configuravel para PIX.

**Proximo plano assume:** os services `LeaseCreationService`/`PixService.resolve_recipient`/`ProofReviewService`/`ExpenseService.generate_installments` como fontes unicas dessas regras; o shape de erro DRF `{"detail"}` em toda a API (sem `{"error"}`); e o helper `core/utils/query_params` disponivel para parse seguro de query params em novos endpoints.
