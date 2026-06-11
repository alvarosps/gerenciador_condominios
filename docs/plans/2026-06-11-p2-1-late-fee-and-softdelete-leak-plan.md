# Plano P2.1 — late_fee ciente de data real + vazamento de soft-deleted por related managers

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P2 (Correcao de dinheiro/dados) · **Branch sugerida:** `fix/late-fee-and-softdelete-leak` · **Depende de:** nenhum (pode rodar apos P1)

## Objetivo

Corrigir dois bugs reais de dinheiro/dados que rodam em producao. (1) `FeeCalculatorService.calculate_late_fee` decide atraso comparando apenas `current_date.day > due_day`, sem mes/ano — um aluguel vencido dia 25 e nao pago retorna multa R$0 entre os dias 1 e 25 do mes seguinte, e `due_day` 31 nunca atrasa em fevereiro; o endpoint `GET /api/leases/{id}/calculate_late_fee/` ainda ignora se o aluguel ja foi pago. (2) ~36 models declaram `all_objects = models.Manager()` ANTES de `objects` sem `Meta.default_manager_name`, tornando `all_objects` (que inclui deletados) o `_default_manager`; related managers (`lease.apartment.furnitures.all()`, `lease.tenants.all()`, `lease.rent_adjustments.all()`) entao vazam registros soft-deletados — mobilia deletada aparece no PDF do contrato e reajustes deletados entram no calculo. O plano fecha os dois na raiz, quantiza a multa e remove as compensacoes `filter(is_deleted=False)` que viraram redundantes.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | `calculate_late_fee` cego a mes/ano (`current_date.day > due_day`) — causa-raiz do bug de due-date; multa sem `quantize` (Decimal de ~28 digitos) | `core/services/fee_calculator.py:82` | Nova assinatura recebe `due_date: date` real; atraso = `(current_date - due_date).days`; multa quantizada 2 casas `ROUND_HALF_UP` |
| ALTO | Endpoint `calculate_late_fee` passa `due_day` cru + `timezone.now().date()` e IGNORA `RentPayment` | `core/views.py:420` | Clampar `due_day` ao ultimo dia do mes de referencia; checar `RentPayment` do mes antes de reportar multa |
| ALTO | `all_objects = Manager()` antes de `objects`, sem `Meta.default_manager_name` → `_default_manager` = `all_objects` → related managers incluem deletados | `core/models.py:218-219` (e ~35 outros) | `Meta.default_manager_name = "objects"` (via base mixin) → related managers excluem deletados |
| ALTO | Mobilia/tenant/reajuste soft-deletados vazam no contrato e no calculo de reajuste | `core/services/contract_service.py:129,133`; `core/services/rent_adjustment_service.py:252` | Consequencia direta do item acima — nenhuma mudanca extra de codigo nesses services, mas regressao explicita |

## Abordagem técnica

Ordem: primeiro o soft-delete (mudanca de base que muda comportamento de querysets), depois o late_fee (que reusa o resultado limpo). Cada etapa fecha com gate escopado.

### Etapa 1 — Fechar o vazamento de soft-deleted via `_default_manager`

1. **Diagnostico confirmado.** Em `core/models.py`, todos os models soft-delete declaram nesta ordem:
   ```python
   all_objects = models.Manager()  # Access all objects including deleted
   objects = SoftDeleteManager()
   ```
   Sem `Meta.default_manager_name`, o Django elege o PRIMEIRO manager declarado (`all_objects`) como `_default_manager`. Related managers (`lease.tenants`, `apartment.furnitures`, `lease.rent_adjustments`, `expense.installments`, `building.apartments`, `apartment.leases`, etc.) usam o `_default_manager` do modelo-alvo — logo retornam deletados.

2. **Correcao na raiz, no mixin.** Em `SoftDeleteMixin` (`core/models.py:111`), adicionar na `class Meta` (hoje so `abstract = True`, linhas 146-147):
   ```python
   class Meta:
       abstract = True
       default_manager_name = "objects"
   ```
   `default_manager_name` e herdado por models concretos cuja `Meta` nao o sobrescreve. Isso faz `objects` (o `SoftDeleteManager`, que filtra `is_deleted=False`) ser o `_default_manager`, corrigindo TODOS os related managers de uma vez. Nenhum model concreto define `default_manager_name` hoje (grep confirmou: 0 ocorrencias), entao nao ha conflito.

3. **Garantir herança de Meta.** Models concretos que definem sua propria `class Meta` (ex.: Apartment linha 404, Tenant 534, Lease 721, Expense 1080, ExpenseInstallment 1233, etc.) NAO herdam `Meta` do abstract automaticamente quando declaram a propria. Validar: o caminho mais limpo e definir `default_manager_name` herdavel. Como Django NAO mescla `Meta` de abstract com `Meta` concreta campo-a-campo para `default_manager_name`, a abordagem robusta e: **declarar `objects` ANTES de `all_objects` em cada model soft-delete** (inverter a ordem de declaracao), pois o Django elege o primeiro manager declarado como default. Decidir entre as duas tecnicas no inicio da execucao com um teste-canario (ver TDD `test_default_manager_is_soft_delete_manager`):
   - **Opcao A (preferida se funcionar):** `default_manager_name = "objects"` no `SoftDeleteMixin.Meta` + auditar cada model concreto com `Meta` propria e adicionar `default_manager_name = "objects"` ali tambem (DRY-quebra minima, mas explicita).
   - **Opcao B (fallback):** inverter ordem para `objects = SoftDeleteManager()` PRIMEIRO, `all_objects = models.Manager()` depois, em todos os ~36 models. Mais linhas tocadas, zero dependencia de heranca de Meta.

   Rodar o teste-canario contra cada model que tem `Meta` propria (Apartment, Tenant, Lease, RentAdjustment, e os financeiros legados) para escolher A ou B de forma binaria — nao adivinhar.

4. **Remover compensacoes `filter(is_deleted=False)` redundantes.** Com related managers ja excluindo deletados, estas chamadas viram redundantes (KISS/DRY) e DEVEM ser simplificadas para `.all()` / sem o filtro:
   - `core/models.py:303` `self.apartments.filter(is_deleted=False)` → `self.apartments.all()` (Building.delete cascade)
   - `core/models.py:437` `self.leases.filter(is_deleted=False).update(...)` → `self.leases.all().update(...)` (Apartment.delete)
   - `core/models.py:1201` `self.installments.filter(is_deleted=False).update(...)` → `self.installments.all().update(...)` (Expense.delete cascade)
   - `core/serializers.py:996` `obj.apartment.leases.filter(is_deleted=False).first()` → `obj.apartment.leases.first()`
   - `core/services/cash_flow_service.py:804` e `core/services/financial_dashboard_service.py:742` `apt.leases.filter(is_deleted=False).first()` → `apt.leases.first()`
   - `core/viewsets/tenant_views.py:63` e `core/permissions.py:238` `tenant.leases_responsible.filter(is_deleted=False)` → `tenant.leases_responsible.all()` / `.exists()`

   NAO mexer em chamadas que filtram via `Model.objects.filter(is_deleted=False, ...)` (manager ja correto, redundante mas inofensivo) NEM em filtros ORM cross-relacionais de `dashboard_service.py:463-493` (`Q(leases_responsible__is_deleted=False)` em annotate/aggregate — esses NAO passam pelo manager do model-alvo, sao lookups de JOIN e PRECISAM do filtro). Tambem NAO tocar nas data-migrations (`0018`, `0025`) nem em constraints (`condition=Q(is_deleted=False)`).

5. **Nenhuma mudanca em `contract_service.py` nem `rent_adjustment_service.py`.** `calculate_lease_furniture` (linha 111) usa `lease.apartment.furnitures.all()` (129) e `lease.tenants.all()` (133); `get_eligible_leases` usa `lease.rent_adjustments.all()` (252). Com a Etapa 1 esses passam a excluir deletados automaticamente — a correcao e o teste de regressao, nao edicao desses arquivos.

### Etapa 2 — `calculate_late_fee` ciente de data real + quantize + endpoint

1. **Mudar a assinatura** de `FeeCalculatorService.calculate_late_fee` (`core/services/fee_calculator.py:50`) de
   `(rental_value: Decimal, due_day: int, current_date: date)` para
   `(rental_value: Decimal, due_date: date, current_date: date)`.
   - `late_days = (current_date - due_date).days` (atraso real cross-month).
   - `is_late = late_days > 0`.
   - Quando atrasado: `late_fee = (daily_rate * late_days * late_fee_percentage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. Importar `ROUND_HALF_UP` de `decimal`.
   - Ramo nao-atrasado: `late_days = 0`, `late_fee = Decimal("0.00")`, mensagem "Aluguel nao esta atrasado." (manter PT).
   - Atualizar docstring e exemplos (hoje em `due_day`); mensagem de erro de `rental_value < 0` permanece EN no log/raise.

2. **Atualizar os chamadores internos** (o clamp do `due_day` ao ultimo dia do mes ja existe nos chamadores como `clamped_due`; construir o `due_date` a partir dele):
   - `core/services/rent_schedule_service.py:355` (em `get_month_stats`): hoje
     `FeeCalculatorService.calculate_late_fee(effective_value, clamped_due, today)` →
     `FeeCalculatorService.calculate_late_fee(effective_value, clamped_due_date, today)` (a variavel `clamped_due_date = date(year, month, clamped_due)` ja existe na linha 351).
   - `core/services/rent_schedule_service.py:498` (em `_build_item`): hoje
     `FeeCalculatorService.calculate_late_fee(effective_value, clamped_due, today)` →
     `FeeCalculatorService.calculate_late_fee(effective_value, clamped_due_date, today)` (param `clamped_due_date` ja recebido na assinatura de `_build_item`, linha 477).
   - Reusar `RentScheduleService.clamp_due_day` (linha 65) sempre que precisar derivar `due_date` de `due_day` — nao reimplementar clamp.

3. **Endpoint `calculate_late_fee`** (`core/views.py:408-432`): hoje passa `due_day=lease.responsible_tenant.due_day` cru e `timezone.now().date()`, e ignora pagamento. Reescrever a action para:
   - `today = timezone.now().date()`; `reference_month = today.replace(day=1)`.
   - Se ja existe pagamento do mes — `RentPayment.objects.filter(lease=lease, reference_month=reference_month).exists()` — retornar `{"message": "Aluguel ja pago neste mes."}` com 200 (sem multa). `RentPayment` precisa ser importado em `core/views.py` (hoje so importa `Apartment, Building, Furniture, Lease, Tenant` na linha 19 — adicionar `RentPayment`).
   - Caso contrario, derivar o `due_date` real do mes corrente: `clamped_due = RentScheduleService.clamp_due_day(lease.responsible_tenant.due_day, today.year, today.month)` e `due_date = date(today.year, today.month, clamped_due)` (`date` ja importado na linha 3; `RentScheduleService` ja importado linha 38).
   - Chamar `FeeCalculatorService.calculate_late_fee(rental_value=lease.rental_value, due_date=due_date, current_date=today)`.
   - Manter o shape de resposta: atrasado → `{"late_days", "late_fee"}` 200; nao atrasado → `{"message"}` 200.
   - Permissao inalterada (`IsTenantOrAdmin`).

4. **Atualizar o teste** `tests/unit/test_financial/test_rent_schedule_service.py:473` (e o gemeo de stats em `:746`): hoje comparam `item["late_fee"] == str(expected["late_fee"])` chamando `FeeCalculatorService.calculate_late_fee(Decimal("1200.00"), 7, date(2026, 3, 20))` com a assinatura antiga (3o arg = `due_day=7`). Atualizar a chamada esperada para a nova assinatura `calculate_late_fee(Decimal("1200.00"), date(2026, 3, 7), date(2026, 3, 20))` e o valor passa a ser o quantizado. Como `RentScheduleService` ja produz o valor via a mesma funcao, a igualdade continua valida apos quantize — confirmar que ambos os lados usam o valor quantizado.

5. **`change_due_date` (views.py:435) NAO muda.** Usa `calculate_due_date_change_fee`, funcao distinta, fora de escopo.

## Arquivos a criar / modificar

- `core/models.py` — `SoftDeleteMixin.Meta` ganha `default_manager_name = "objects"` (e/ou inverter ordem de managers nos ~36 models concretos, conforme canario); remover `filter(is_deleted=False)` redundante em `:303`, `:437`, `:1201`.
- `core/serializers.py` — remover `filter(is_deleted=False)` redundante em `:996`.
- `core/services/cash_flow_service.py` — `:804` `apt.leases.first()`.
- `core/services/financial_dashboard_service.py` — `:742` `apt.leases.first()`.
- `core/viewsets/tenant_views.py` — `:63` simplificar related manager.
- `core/permissions.py` — `:238` simplificar related manager.
- `core/services/fee_calculator.py` — nova assinatura `calculate_late_fee(rental_value, due_date, current_date)` + `quantize(ROUND_HALF_UP)` + docstring/exemplos.
- `core/views.py` — importar `RentPayment` no import de `.models` (linha 19); reescrever a action `calculate_late_fee` (clamp do mes + checagem de `RentPayment`).
- `core/services/rent_schedule_service.py` — atualizar as 2 chamadas (`:355`, `:498`) para passar `clamped_due_date`.
- `tests/unit/test_fee_calculator.py` — reescrever a classe `TestCalculateLateFee` para a nova assinatura + casos cross-month/fev + quantize.
- `tests/unit/test_financial/test_rent_schedule_service.py` — atualizar `:471` e `:745` para a nova assinatura/valor quantizado.
- `tests/unit/test_contract_service.py` (ou local equivalente de `calculate_lease_furniture`) — regressao: mobilia soft-deletada NAO aparece.
- `tests/integration/` (viewset de leases) — regressao do endpoint: cross-month, due_day 31 em fev, e "ja pago neste mes".
- `tests/unit/` (models) — teste-canario `test_default_manager_is_soft_delete_manager` e regressao de related managers.

## TDD — cenários de teste

Soft-delete (raiz):
- `test_default_manager_is_soft_delete_manager` — para cada model soft-delete representativo (Furniture, Tenant, Lease, RentAdjustment, Expense, ExpenseInstallment), `Model._default_manager` e instancia de `SoftDeleteManager` (canario que decide opcao A vs B).
- `test_related_manager_excludes_soft_deleted_furniture` — apartamento com 2 mobilias, 1 soft-deletada → `apartment.furnitures.all()` retorna so 1.
- `test_related_manager_excludes_soft_deleted_tenant` — lease com 2 tenants M2M, 1 soft-deletado → `lease.tenants.all()` retorna so 1.
- `test_related_manager_excludes_soft_deleted_rent_adjustment` — lease com 2 reajustes, 1 soft-deletado → `lease.rent_adjustments.all()` retorna so 1.
- `test_all_objects_still_includes_deleted` — `Model.all_objects.filter(...)` continua incluindo deletados (nao quebrar a porta de escape).
- `test_contract_excludes_soft_deleted_furniture` (REGRESSAO do bug) — apartamento com mobilia soft-deletada → `ContractService.calculate_lease_furniture(lease)` NAO inclui a deletada.
- `test_eligible_leases_ignore_soft_deleted_adjustment` — reajuste soft-deletado nao vira `last_adjustment` em `RentAdjustmentService.get_eligible_leases`.

late_fee (service):
- `test_late_fee_cross_month_overdue` (REGRESSAO do bug) — `due_date=2026-01-25`, `current_date=2026-02-10` → `is_late=True`, `late_days=16`, multa > 0 (hoje retorna R$0).
- `test_due_day_31_overdue_in_february` (REGRESSAO) — chamador clampa due_day 31 → `due_date=2026-02-28`, `current_date=2026-03-05` → `is_late=True`, `late_days=5`.
- `test_late_fee_same_month` — `due_date=2025-01-10`, `current_date=2025-01-15` → `late_days=5`, multa = `quantize((1500/30)*5*0.05)`.
- `test_late_fee_on_due_date_is_zero` — `current_date == due_date` → `is_late=False`, `late_fee=0.00`.
- `test_late_fee_before_due_date_is_zero` — `current_date < due_date` → `is_late=False`.
- `test_late_fee_is_quantized_two_places` — multa tem exatamente 2 casas decimais (`-late_fee.as_tuple().exponent == 2`); valor com fracao que exige `ROUND_HALF_UP`.
- `test_negative_rental_raises` — mantem o `ValueError("non-negative")`.

Endpoint (integration):
- `test_calculate_late_fee_endpoint_overdue_current_month` — lease vencido no mes corrente, sem pagamento → 200 com `late_days`/`late_fee` > 0.
- `test_calculate_late_fee_endpoint_already_paid_returns_message` (REGRESSAO) — existe `RentPayment` do mes → 200 com mensagem "ja pago", sem multa.
- `test_calculate_late_fee_endpoint_not_overdue` — antes do vencimento → 200 com mensagem.
- `test_calculate_late_fee_endpoint_due_day_31_february` — due_day 31, mes fevereiro → clamp aplicado, sem 500.
- `test_calculate_late_fee_endpoint_permission` — tenant de outro lease recebe 403 (permissao `IsTenantOrAdmin` inalterada).

Frontend: nenhuma mudanca de contrato (shape de resposta do endpoint preservado: `{late_days, late_fee}` ou `{message}`). Sem novos testes vitest necessarios; se houver hook `useCalculateLateFee` em `frontend/lib/api/hooks/use-leases.ts`, confirmar que continua compativel (read-only — nao alterar).

## Migrations / dados

`default_manager_name` e mudanca de Python puro (opcao A) ou reordenacao de declaracao de managers (opcao B); **nenhuma das duas altera o schema do banco** — `makemigrations` NAO deve gerar migration. Rodar `python manage.py makemigrations --check --dry-run` para confirmar zero drift. Se (e somente se) a mudanca de managers gerar uma migration de "alter managers" (Django as vezes registra `Meta.managers`), criar a migration via `makemigrations` (nunca editar existente); ela e no-op de dados (so metadado de state) e nao precisa de RLS (nao cria tabela). Backup so se algo destrutivo aparecer — nao e o caso. Sem correcao de dado vivo: o vazamento e de leitura, nenhum registro foi gravado errado.

## Constraints (o que NÃO fazer)

- NAO refatorar os models legados alem do necessario: a unicidade incondicional sob soft-delete (Tenant.cpf_cnpj, Building.street_number, etc.) e outro achado/plano — fora de escopo aqui.
- NAO remover o manager `all_objects` nem mudar `SoftDeleteManager`/`with_deleted()`/`deleted_only()` — apenas garantir que `objects` seja o default.
- NAO remover filtros `Q(..._is_deleted=False)` de lookups cross-relacionais em `dashboard_service.py` (sao JOINs, nao related managers — quebrariam se removidos).
- NAO tocar em `calculate_due_date_change_fee` nem em `change_due_date`.
- NAO mudar o shape da resposta dos endpoints (FE depende dele).
- NAO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, TODO/FIXME, re-exports, shims de compat, nem `from __future__ import annotations`.
- NAO mockar ORM/services internos nos testes — usar banco real (`--reuse-db`) e `freezegun` so para o relogio.
- Dinheiro sempre `Decimal` com `quantize` 2 casas `ROUND_HALF_UP`; mensagens PT para usuario, EN para logs.

## Critérios de aceite (binários)

- [ ] `Furniture._default_manager`, `Tenant._default_manager`, `Lease._default_manager`, `RentAdjustment._default_manager`, `Expense._default_manager` sao `SoftDeleteManager`.
- [ ] `apartment.furnitures.all()`, `lease.tenants.all()`, `lease.rent_adjustments.all()` NAO retornam registros soft-deletados.
- [ ] `Model.all_objects` continua incluindo deletados.
- [ ] `ContractService.calculate_lease_furniture` exclui mobilia soft-deletada (teste de regressao verde).
- [ ] `RentAdjustmentService.get_eligible_leases` ignora reajuste soft-deletado.
- [ ] `calculate_late_fee(due_date=2026-01-25, current_date=2026-02-10)` retorna `is_late=True`, `late_days=16`, multa > 0.
- [ ] `due_day` 31 clampado para 28 em fevereiro produz atraso correto (sem 500).
- [ ] `late_fee` tem exatamente 2 casas decimais (`quantize` `ROUND_HALF_UP`).
- [ ] Endpoint retorna mensagem "ja pago" quando existe `RentPayment` do mes corrente, sem multa.
- [ ] Shape das respostas do endpoint preservado (`{late_days, late_fee}` | `{message}`).
- [ ] `python manage.py makemigrations --check --dry-run` sem drift (ou migration no-op de state criada via `makemigrations`, nunca editando existente).
- [ ] Gate escopado verde, zero warnings.

## Gate de verificação

Backend (escopado nos arquivos editados + regressao dirigida):
```bash
ruff check core/models.py core/views.py core/serializers.py core/permissions.py \
  core/services/fee_calculator.py core/services/rent_schedule_service.py \
  core/services/cash_flow_service.py core/services/financial_dashboard_service.py \
  core/viewsets/tenant_views.py
ruff format --check core/ tests/
mypy core/
pyright
python manage.py makemigrations --check --dry-run
python -m pytest tests/unit/test_fee_calculator.py \
  tests/unit/test_financial/test_rent_schedule_service.py \
  tests/unit/test_contract_service.py \
  -p no:randomly
# regressao dirigida (models/managers + endpoint leases + reajuste):
python -m pytest -k "soft_delet or default_manager or late_fee or furniture or eligible_leases" -p no:randomly
```
Suite cheia tem flakiness pre-existente de xdist/Redis — NAO e bloqueio; rodar escopado + dirigido acima. Frontend: nenhuma mudanca de codigo FE; se algum hook foi tocado, `cd frontend && npm run lint && npm run type-check && npm run test:unit`. Zero erros E zero warnings.

## Handoff

Commit message sugerida:
```
fix(core): late_fee ciente de data real + para vazamento de soft-deleted via related managers

- calculate_late_fee passa a receber due_date (date) e calcula (current_date - due_date).days,
  corrigindo multa R$0 em atraso cross-month e due_day 31 em fevereiro; quantiza 2 casas ROUND_HALF_UP
- endpoint /leases/{id}/calculate_late_fee/ clampa o due_day ao mes e respeita RentPayment do mes
- SoftDeleteMixin define objects como default manager (default_manager_name/ordem) — related managers
  (furnitures, tenants, rent_adjustments) deixam de vazar registros soft-deletados (contrato e reajuste)
- remove compensacoes filter(is_deleted=False) que viraram redundantes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar memoria/estado: registrar em `MEMORY.md` que o `_default_manager` dos models soft-delete agora e `SoftDeleteManager` (related managers excluem deletados por padrao) e que `calculate_late_fee` mudou de assinatura (`due_date` em vez de `due_day`). O proximo plano (unicidade condicional sob soft-delete) assume que related managers ja estao corretos e NAO precisa reabordar o leak. Verificar tambem o consumidor mobile (`mobile/`) — o endpoint `calculate_late_fee` mantem shape, mas confirmar via grep antes de fechar.
