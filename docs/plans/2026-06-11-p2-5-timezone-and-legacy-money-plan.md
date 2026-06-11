# Plano P2.5 — Fronteira de timezone SP + bugs cirúrgicos de dinheiro no legado + fix de dado

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P2 · **Branch sugerida:** `fix/timezone-and-legacy-money` · **Depende de:** nenhum

## Objetivo

Eliminar a fronteira de dia UTC nos caminhos ativos do core: hoje `settings.TIME_ZONE="UTC"` e os services usam `timezone.now().date()`, então entre 21:00 e 23:59 de São Paulo (UTC-3) o servidor já está no dia seguinte — o guard de desmarcar pagamento dispara cedo, a multa conta +1 dia e os dashboards viram de mês às 21:00 no último dia. Este plano promove um helper SP-aware único (`today_sp()`) e o usa nos caminhos core ativos, corrige 5 bugs cirúrgicos de dinheiro no módulo financeiro legado (que ainda roda em prod e congela valores no `MonthSnapshot` imutável) e documenta a correção do dado vivo do lease 51 (apto 203/prédio 850), corrompido pela comparação `int == "850"` da migration 0022. Nenhuma refatoração profunda do legado.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MÉDIO | `today` em UTC no guard de desmarcar + agendamento de pagamento | `rent_schedule_service.py:252,414,459` | usar `today_sp()` como default de `as_of`/`today` |
| MÉDIO | `today` UTC no resumo de atraso do dashboard | `dashboard_service.py:315` | `today = today_sp()` |
| MÉDIO | debt installments somam offsets (sem `is_offset=False`) | `cash_flow_service.py:314` (`_collect_debt_installments`) | `Q(... is_offset=False)` |
| MÉDIO | IPTU installments somam offsets (sem `is_offset=False`) | `cash_flow_service.py:326` (`_collect_property_tax`) | `Q(... is_offset=False)` |
| MÉDIO | IPTU summary soma offsets | `financial_dashboard_service.py:943-951` (`_build_expense_summary`) | adicionar `expense__is_offset=False` |
| MÉDIO | IPTU detail soma offsets | `financial_dashboard_service.py:1907-1916` (`_detail_iptu`) | adicionar `expense__is_offset=False` |
| MÉDIO | IPTU vencido (meses anteriores) soma offsets | `financial_dashboard_service.py:697-705` (`_build_overdue_previous_months`) | adicionar `expense__is_offset=False` |
| MÉDIO | debt installments por prédio somam offsets | `financial_dashboard_service.py:1152-1157` (`_build_utility_by_building`) | adicionar `expense__is_offset=False` |
| MÉDIO | receita do legado usa `rental_value` cru (ignora reajuste pendente) | `cash_flow_service.py:72,648` + `financial_dashboard_service.py:746` | `RentScheduleService.effective_rental_value(lease, mês)` |
| MÉDIO | `_mark_credit_card_paid` marca o mês corrente do servidor, não o exibido | `daily_control_service.py:264-282` | receber `year/month` e filtrar por eles |
| MÉDIO | escrita escondida em GET cacheado (`_ensure_employee_payments`) | `financial_dashboard_service.py:881-903,992,1961` | remover criação automática do caminho de leitura |
| MÉDIO | dado vivo: lease 51 com `rental_value=1400`/`number_of_tenants=1` (deveria 1500/2) | `core/migrations/0022_occupancy_pricing.py:22` | corrigir via admin/`RentAdjustment` (gated por confirmação do dono) |

## Abordagem técnica

Ordem de execução pensada para isolar cada bug com seu próprio teste de regressão Red→Green.

### 1. Helper SP-aware neutro (base de todo o resto)

`finances/services/timezone.py` já expõe `now_sp()`, `today_sp()`, `current_month_sp()` e `SAO_PAULO_TZ`, mas vive em `services/` — local que força a inversão `serializer → services` (achado P4) e que torna o import a partir do core conceptualmente mais sujo. Conforme a espec ("promover um helper SP-aware neutro, `finances/timezone.py` ao lado de `money.py`"):

1. Criar `finances/timezone.py` com o conteúdo idêntico ao atual `finances/services/timezone.py` (mover, não duplicar — DRY).
2. Apagar `finances/services/timezone.py`.
3. Atualizar TODOS os consumidores existentes do import antigo para `from finances.timezone import ...` (refatoração completa, sem re-export, sem shim):
   - `finances/serializers.py`
   - `finances/services/bill_payment_service.py`, `bill_service.py`, `condo_balance_service.py`, `condo_calendar_service.py`, `condo_month_close_service.py`, `condo_projection_service.py`, `installment_plan_service.py`
   - `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py`
   - `core/services/notification_service.py:17` (`from finances.services.timezone import SAO_PAULO_TZ` → `from finances.timezone import SAO_PAULO_TZ`)
   - `core/management/commands/send_finance_alerts.py`

   Confirmar via `rg "finances\.services\.timezone|finances/services/timezone"` que sobra zero referência.

> NOTA P4: este plano NÃO move `send_finance_alerts` para `finances/` nem refatora `InvoiceDraftService` — isso é escopo do P4. P2.5 apenas reposiciona o utilitário de timezone (puro, sem dependências de domínio) para o lugar neutro, deixando o import `core → finances.timezone` válido por ser um utilitário e não um service de domínio. A inversão arquitetural plena permanece para o P4.

### 2. Fronteira de timezone nos caminhos core ativos

Substituir `timezone.now().date()` por `today_sp()` (de `finances.timezone`) APENAS nos caminhos ativos do core. NÃO tocar nos caminhos do módulo pessoal deprecated que não estão na lista (ex.: `cash_flow_service.py:527` `get_cash_flow_projection` e `daily_control_service.py:115` `get_month_summary` ficam fora — só o `_mark_credit_card_paid` do daily-control é endereçado, por ser escrita de dado).

- `core/services/rent_schedule_service.py`
  - Linha 252 (`get_month_schedule`): `today = as_of if as_of is not None else timezone.now().date()` → `else today_sp()`.
  - Linha 326 (`get_month_stats`): idem `else today_sp()`.
  - Linha 414 (`toggle_payment`): `today = timezone.now().date()` → `today = today_sp()`. Isso conserta tanto o `payment_date=today` (linha 448) quanto o guard de desmarcar `clamped_due_date < today` (linha 459), que hoje proíbe desmarcar 3h antes do fim do dia de vencimento em SP.
  - Remover o import `from django.utils import timezone` se não restar nenhum outro uso no arquivo (verificar com `rg "timezone\." core/services/rent_schedule_service.py`); senão mantê-lo.
- `core/services/dashboard_service.py`
  - Linha 315 (`get_late_payment_summary`): `today = timezone.now().date()` → `today = today_sp()`. Afeta `month_start = today.replace(day=1)` e o ledger de atraso (não vira de mês às 21:00).

`as_of`/`today` continuam parametrizáveis: quem já passa `as_of` (a calendário condo-finance) não é afetado — só o default muda de UTC para SP.

### 3. `is_offset=False` nos 5 querysets legados de agregação

A regra do domínio (LESSONS_LEARNED) exige SEMPRE filtrar `is_offset=False` em totais — offsets são descontos da pessoa, não despesa real. Os 5 pontos abaixo somam offsets e congelam o erro no `MonthSnapshot`. O mesmo arquivo (`cash_flow_service._get_projected_expenses:699`) já filtra `expense__is_offset=False`, provando que a omissão é oversight.

- `core/services/cash_flow_service.py`
  - `_collect_debt_installments` (306-316): no `Q(expense__is_debt_installment=True)` passar a `Q(expense__is_debt_installment=True, expense__is_offset=False)`.
  - `_collect_property_tax` (318-328): `Q(expense__expense_type=ExpenseType.PROPERTY_TAX)` → `Q(expense__expense_type=ExpenseType.PROPERTY_TAX, expense__is_offset=False)`.
- `core/services/financial_dashboard_service.py`
  - `_build_expense_summary` iptu_installments (943-951): adicionar `expense__is_offset=False` ao `.filter(...)`.
  - `_build_overdue_previous_months` unpaid_iptu (697-705): adicionar `expense__is_offset=False` ao `.filter(...)`.
  - `_build_utility_by_building` debt_installments (1152-1157): adicionar `expense__is_offset=False` ao `.filter(...)`.
  - `_detail_iptu` iptu_installments (1907-1916): adicionar `expense__is_offset=False` ao `.filter(...)`.

  (São 4 querysets em `financial_dashboard_service.py` + 2 em `cash_flow_service.py`; a tabela conta 5 "querysets legados" agrupando IPTU summary+detail como o mesmo tipo; corrigir todos os 6 sites listados.)

### 4. `effective_rental_value` nos 3 pontos de dinheiro do legado

`RentScheduleService.effective_rental_value(lease, reference_month)` é o SSOT do aluguel do mês (honra `pending_rental_value`/`pending_rental_value_date` de reajuste). O legado soma `lease.rental_value` cru, divergindo do calendário/daily-control quando há reajuste pendente ativado no mês — e congela o valor errado no snapshot.

- `core/services/cash_flow_service.py`
  - `get_monthly_income` (linha 72): `rent_income += lease.rental_value` → `rent_income += RentScheduleService.effective_rental_value(lease, reference_date)`. Ajustar também `rental_value` exposto no detail (linha 80) para o efetivo, para o detalhe não contradizer o total.
  - `_get_projected_income` (linha 648): `rent_income += lease.rental_value` → `effective_rental_value(lease, date(year, month, 1))`.
- `core/services/financial_dashboard_service.py`
  - `_build_income_summary` (linha 746): `rental_value = lease.rental_value` → `rental_value = RentScheduleService.effective_rental_value(lease, month_start)`. (`month_start` já está em escopo na função.)

> Fronteiras de início de contrato (`_collect_owner_repayments` `start_date__lte=month_start` etc.) NÃO são corrigidas neste plano — a espec restringe a "4 pontos de dinheiro"; aqui são 3 sites de aluguel (`get_monthly_income`, `_get_projected_income`, `_build_income_summary`); o 4º ponto do digest (`get_person_summary` em `cash_flow:806`) fica fora pois é o módulo pessoal deprecated puro sem caminho de snapshot. Manter o escopo cirúrgico.

### 5. `_mark_credit_card_paid` usa o mês exibido, não o do servidor

Contrato FE↔API (ambos os lados):

- **Backend** `core/services/daily_control_service.py`:
  - `mark_item_paid(item_type, item_id, payment_date, year, month)` (linha 214): adicionar `year: int | None = None, month: int | None = None`.
  - Repassar para `_mark_credit_card_paid(card_id, payment_date, year, month)`.
  - `_mark_credit_card_paid` (264-282): substituir `today = timezone.now().date(); month_start = today.replace(day=1); next_month = _next_month_start(today.year, today.month)` por: se `year`/`month` vierem, `month_start = date(year, month, 1); next_month = _next_month_start(year, month)`; senão derivar de `payment_date` (`month_start = payment_date.replace(day=1)`). O `payment_date` já é parseado a `date` no viewset (`financial_dashboard_views.py:325`), então é fonte confiável de fallback — preferir `year/month` explícitos, cair em `payment_date` quando ausentes (nunca mais o UTC do servidor).
  - O `bulk update` (linha 278) já filtra `is_offset=False` — manter.
- **Viewset** `core/viewsets/financial_dashboard_views.py`:
  - `_mark_standard_item_paid` (359+): para `item_type == "credit_card"`, extrair `year`/`month` opcionais de `request.data` (validar com `int()` em try, devolvendo 400 PT se inválidos) e repassar a `DailyControlService.mark_item_paid(...)`. Para os demais item_types, `year/month` ficam `None` (sem efeito).
- **Frontend**:
  - `frontend/lib/api/hooks/use-daily-control.ts`: `MarkPaidRequest` JÁ tem `year?: number; month?: number` (linhas 62-63) — nenhuma mudança de tipo.
  - `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx`: no `onClick` do `MarkPaidButton` (linha 92) e/ou no `handleMarkPaid` (374-377), quando `item_type === 'credit_card'`, incluir `year: filters.year, month: filters.month` no payload (o componente recebe `filters` com year/month via props — confirmar a forma de `filters` e propagar até o botão). Demais tipos não precisam.

### 6. Remover escrita escondida do GET cacheado

`FinancialDashboardService._ensure_employee_payments` cria `EmployeePayment` no banco dentro de `get_dashboard_summary`, que é `@cache_result(timeout=120)` (linha 407) — um GET muta o banco, de forma não-determinística (só em cache MISS) e sem `created_by/updated_by`. O carry-forward correto já existe em `MonthAdvanceService._carry_forward_employee_payments` (fechamento de mês).

- Remover o método `_ensure_employee_payments` (881-903) por completo.
- Remover a chamada em `_build_expense_summary` (linha 992) e em `_detail_employee` (linha 1961). Os blocos seguintes (que leem `EmployeePayment.objects.filter(reference_month=month_start)`) passam a reportar apenas os pagamentos que existem — funcionários sem pagamento simplesmente não aparecem no total do mês (comportamento correto: o carry-forward é responsabilidade do fechamento, não da leitura). Confirmar que `_check_unpaid_employees` (ou equivalente) ainda sinaliza funcionários sem pagamento; se não existir, NÃO criar — apenas não auto-criar no GET (YAGNI; reportar é fora de escopo).

### 7. Dado vivo (lease 51) — gated por confirmação do dono

A migration 0022 comparou `building.street_number` (int) com a string `"850"` (`if building.street_number == "850"`), que nunca casa, então o caso especial não foi aplicado: o lease do apto 203/prédio 850 ficou com `rental_value` derivado de `apartment.rental_value` e `number_of_tenants` default em vez de `1500`/`2`.

- NÃO editar a migration 0022 (hooks bloqueiam; e reescrever histórico é proibido).
- Verificação (somente leitura, antes de qualquer escrita), via `python manage.py shell`:
  ```python
  from core.models import Lease
  l = Lease.objects.get(id=51)
  print(l.id, l.apartment.number, l.apartment.building.street_number,
        l.rental_value, l.number_of_tenants)
  ```
  Confirmar que de fato está `1400`/`1` e que o apto/prédio são 203/850.
- **Gate:** perguntar ao dono qual o valor/contagem corretos (o digest indica 1500/2) ANTES de escrever. Sem confirmação, não alterar.
- Correção: preferir um `RentAdjustment` (preserva trilha `previous_value`/`new_value` e é o caminho de negócio para mudar aluguel) OU edição via Django admin se o dono tratar como correção de cadastro e não reajuste. Atualizar `number_of_tenants` no lease no mesmo passo. `backup` (`python scripts/backup_db.py`) antes de qualquer escrita; em prod, espelhar pela mesma operação de admin/shell (não rodar migrate). Documentar o valor aplicado e a data no Handoff.

## Arquivos a criar / modificar

**Criar**
- `finances/timezone.py` — movido de `finances/services/timezone.py` (conteúdo idêntico).
- `tests/unit/test_rent_schedule_timezone.py` — fronteira SP (toggle/guard/schedule/stats).
- `tests/unit/test_cash_flow_legacy_money.py` — `is_offset` + `effective_rental_value` em cash flow.
- `tests/unit/test_financial_dashboard_legacy_money.py` — `is_offset` (IPTU/debt) + `effective_rental_value` + ausência de escrita no GET.
- `tests/unit/test_daily_control_mark_credit_card.py` — `year/month` no `mark_credit_card`.

**Modificar (backend)**
- `finances/serializers.py`, `finances/services/bill_payment_service.py`, `bill_service.py`, `condo_balance_service.py`, `condo_calendar_service.py`, `condo_month_close_service.py`, `condo_projection_service.py`, `installment_plan_service.py`, `finances/viewsets/crud_views.py`, `finances/viewsets/dashboard_views.py` — atualizar import de timezone.
- `core/services/notification_service.py` — atualizar import de timezone.
- `core/management/commands/send_finance_alerts.py` — atualizar import de timezone.
- `core/services/rent_schedule_service.py` — `today_sp()` em 252, 326, 414.
- `core/services/dashboard_service.py` — `today_sp()` em 315.
- `core/services/cash_flow_service.py` — `is_offset=False` (314, 326), `effective_rental_value` (72/80, 648).
- `core/services/financial_dashboard_service.py` — `is_offset=False` (943-951, 697-705, 1152-1157, 1907-1916), `effective_rental_value` (746), remover `_ensure_employee_payments` + suas 2 chamadas (992, 1961).
- `core/services/daily_control_service.py` — `year/month` em `mark_item_paid`/`_mark_credit_card_paid`.
- `core/viewsets/financial_dashboard_views.py` — repassar `year/month` no `_mark_standard_item_paid` (credit_card).

**Modificar (frontend)**
- `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx` — incluir `year/month` no payload de `credit_card`.
- `frontend/lib/api/hooks/__tests__/use-daily-control.test.ts` (se existir; senão criar) — asserir que o payload de credit_card carrega year/month.

**Sem alteração de tipo:** `frontend/lib/api/hooks/use-daily-control.ts` (já tem `year?`/`month?`).

## TDD — cenários de teste

### Backend — fronteira de timezone (freeze 21:00 SP → 00:00 UTC do dia seguinte)
Usar `freezegun` com um instante UTC que seja "dia seguinte em UTC, mas ainda hoje em SP" (ex.: `2026-06-10 23:30 UTC` ⇒ SP `2026-06-10 20:30`; e `2026-06-11 01:00 UTC` ⇒ SP `2026-06-10 22:00`). Lembrar do fix de flakiness freezegun×DRF-throttle já no projeto (pin do timer do `SimpleRateThrottle`) — não reintroduzir.
- `test_toggle_payment_unpay_guard_uses_sp_date` — às 22:00 SP (01:00 UTC do dia seguinte) com vencimento = hoje SP: desmarcar é PERMITIDO (regressão: hoje o guard recusa porque `today` UTC já passou). 
- `test_toggle_payment_marks_payment_date_in_sp` — `payment_date` gravado = data SP, não a UTC do dia seguinte.
- `test_get_month_stats_does_not_roll_month_at_21h_sp` — no último dia do mês às 22:00 SP, `is_current_month`/overdue computam contra o mês corrente SP, não o seguinte.
- `test_get_month_schedule_today_is_sp` — `today` no payload = ISO da data SP.
- `test_as_of_override_still_respected` — passar `as_of` continua sobrescrevendo (não regrediu).
- `test_late_payment_summary_today_is_sp` (dashboard_service) — `month_start` derivado de SP; não vira de mês às 21:00.

### Backend — is_offset em dobro
- `test_debt_installments_exclude_offset` (cash_flow) — criar installment de debt com `expense.is_offset=True` + um normal; total = só o normal.
- `test_property_tax_excludes_offset` (cash_flow) — idem para IPTU.
- `test_dashboard_iptu_summary_excludes_offset` — `_build_expense_summary` não soma IPTU offset.
- `test_dashboard_iptu_detail_excludes_offset` — `_detail_iptu` idem.
- `test_dashboard_overdue_iptu_excludes_offset` — IPTU vencido de meses anteriores ignora offset.
- `test_dashboard_utility_debt_by_building_excludes_offset` — debt por prédio ignora offset.

### Backend — effective_rental_value no mês com reajuste pendente
- `test_monthly_income_uses_effective_rental` (cash_flow) — lease com `pending_rental_value`/`pending_rental_value_date` no mês ⇒ `rent_income` usa o efetivo (não `rental_value`); detail idem.
- `test_projected_income_uses_effective_rental` (cash_flow) — `_get_projected_income` usa efetivo.
- `test_income_summary_uses_effective_rental` (dashboard) — `_build_income_summary` usa efetivo.
- `test_effective_equals_raw_without_pending` — sem reajuste pendente, efetivo == `rental_value` (não-regressão).

### Backend — credit_card year/month
- `test_mark_credit_card_uses_displayed_month` — usuário em maio (year=2026, month=5) marca cartão em 02/06: parcelas de MAIO são pagas; junho intacto (regressão direta do bug).
- `test_mark_credit_card_falls_back_to_payment_date` — sem year/month, usa o mês de `payment_date` (não o UTC do servidor).
- `test_mark_credit_card_already_paid` — sem parcelas no mês alvo ⇒ `already_paid` (não-regressão).

### Backend — sem escrita no GET
- `test_dashboard_summary_does_not_create_employee_payments` — chamar `get_dashboard_summary` num mês sem `EmployeePayment` NÃO cria nenhum registro (`EmployeePayment.objects.count()` inalterado). Regressão: hoje cria.
- `test_detail_employee_does_not_create_payments` — idem para `_detail_employee`.
- `test_month_advance_still_carries_forward` — `MonthAdvanceService._carry_forward_employee_payments` continua criando no fechamento (garante que o caminho correto não foi quebrado).

### Frontend (Vitest + MSW na fronteira HTTP)
- `mark_credit_card payload inclui year/month` — ao clicar pagar fatura de cartão com `filters={year:2026,month:5}`, o body POST para `/daily-control/mark_paid/` contém `item_type:'credit_card'`, `year:5? não — year:2026, month:5`. Asserir via handler MSW que captura o body.
- `mark_installment não inclui year/month` (ou inclui inócuo) — instalação normal continua funcionando.

## Migrations / dados

- **Sem migration de schema.** Nenhum dos fixes altera tabelas.
- **Dado vivo (lease 51):** correção pontual gated por confirmação do dono (seção 7). `python scripts/backup_db.py` ANTES de escrever; aplicar via `RentAdjustment`/admin (NÃO editar a migration 0022; NÃO rodar migrate). Em prod, espelhar pela mesma operação de admin/shell. Registrar valor e data aplicados no Handoff.

## Constraints (o que NÃO fazer)

- NÃO refatorar o módulo financeiro pessoal deprecated além dos 6 sites de `is_offset`, dos 3 de `effective_rental_value`, do `_mark_credit_card_paid` e da remoção do `_ensure_employee_payments`. Os demais `timezone.now().date()` do legado (`cash_flow_service.py:527`, `daily_control_service.py:115`, defaults de `DateCalculatorService`) ficam intocados neste plano.
- NÃO mover `send_finance_alerts` para `finances/` nem refatorar `InvoiceDraftService`/serializers↔services — isso é P4.
- NÃO corrigir fronteiras de início de contrato (`start_date__lte`) nem `get_person_summary` — fora do escopo cirúrgico.
- NÃO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `from __future__ import annotations`, re-exports ou shims de compat. O move de `timezone.py` é completo: zero referência ao caminho antigo.
- NÃO criar policies RLS (não há tabela nova).
- NÃO editar migrations existentes; nenhuma migration nova é necessária.
- NÃO mockar ORM/services internos — só fronteiras externas (tempo via `freezegun`, HTTP via MSW no FE).

## Critérios de aceite (binários)

- [ ] `finances/services/timezone.py` não existe mais; `finances/timezone.py` existe; `rg "finances\.services\.timezone|finances/services/timezone"` retorna zero ocorrências.
- [ ] `rent_schedule_service.py` linhas 252/326/414 usam `today_sp()`; `dashboard_service.py:315` usa `today_sp()`.
- [ ] Os 6 querysets de IPTU/debt listados filtram `expense__is_offset=False`.
- [ ] `get_monthly_income`, `_get_projected_income` e `_build_income_summary` usam `effective_rental_value`.
- [ ] `mark_item_paid`/`_mark_credit_card_paid` aceitam e respeitam `year/month`; FE envia `year/month` no payload de credit_card.
- [ ] `_ensure_employee_payments` removido; nenhuma chamada a ele resta; `get_dashboard_summary`/`_detail_employee` não criam `EmployeePayment`.
- [ ] Todos os cenários de teste TDD acima passam (incl. os 4 de regressão que provam os bugs: unpay-guard SP, is_offset em dobro, effective com reajuste pendente, credit_card mês exibido, sem escrita no GET).
- [ ] Dado do lease 51: verificado em local; se confirmado pelo dono, corrigido local + prod (backup antes) e registrado no Handoff; senão, marcado como pendente de confirmação.
- [ ] Gate de verificação (abaixo) limpo: zero erros e zero warnings.

## Gate de verificação

Escopado nos arquivos editados + regressão dirigida (a suite cheia tem flakiness pré-existente de xdist/Redis — não é bloqueio).

```bash
# Backend — lint/format/types em tudo que mudou
ruff check core/services/rent_schedule_service.py core/services/dashboard_service.py \
  core/services/cash_flow_service.py core/services/financial_dashboard_service.py \
  core/services/daily_control_service.py core/viewsets/financial_dashboard_views.py \
  core/services/notification_service.py core/management/commands/send_finance_alerts.py \
  finances/ tests/unit/
ruff format --check core/ finances/ tests/unit/
mypy core/
pyright
# Testes escopados (novos + regressão dirigida)
python -m pytest tests/unit/test_rent_schedule_timezone.py tests/unit/test_cash_flow_legacy_money.py \
  tests/unit/test_financial_dashboard_legacy_money.py tests/unit/test_daily_control_mark_credit_card.py \
  tests/unit/test_dashboard_service.py -p no:xdist
# Regressão dirigida do app finances (o move de timezone toca muitos consumidores)
python -m pytest finances/ tests/ -k "timezone or finances" -p no:xdist

# Frontend
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Zero erros E zero warnings em Ruff, mypy, Pyright, ESLint, TypeScript e pytest.

## Handoff

Commit message sugerida:

```
fix(timezone+legacy): SP-aware "today" in active core paths + surgical money fixes

- promote finances/timezone.py (neutral home next to money.py); update all consumers
- rent_schedule/dashboard: today_sp() so the unpay guard, late fee and month rollover
  stop using the UTC date (off-by-one between 21:00-24:00 São Paulo)
- cash_flow/financial_dashboard: filter is_offset=False on IPTU/debt aggregations and
  use RentScheduleService.effective_rental_value (honors pending rent increases)
- daily_control: mark_credit_card_paid uses the displayed year/month, not the server month
- financial_dashboard: stop creating EmployeePayment inside the cached GET (carry-forward
  belongs to MonthAdvanceService)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

- Atualizar `MEMORY.md` com uma entrada curta: "P2.5 done — SP timezone boundary in active core paths + legacy money fixes (is_offset, effective_rental, credit_card month, no-write-in-GET); timezone helper promoted to finances/timezone.py".
- Se o dado do lease 51 for corrigido, registrar aqui o valor aplicado (esperado 1500/2), a data e o meio (RentAdjustment vs admin) em local E prod.
- **O próximo plano (P4) assume:** `finances/timezone.py` já é o local neutro do helper (P4 não precisa criá-lo, só relocar `send_finance_alerts` para `finances/` e ajustar `InvoiceDraftService`); os caminhos core ativos já usam `today_sp()`.
