# Plano P7.1 — Remoção do módulo financeiro pessoal legado (backend + frontend + mobile)

> **Estado:** PLANEJADO — não executado
> **Prioridade:** Fase P7 (Remoção do legado) · **Branch sugerida:** `refactor/remove-legacy-financial` · **Depende de:** P3.2 (telas mobile legadas do financeiro removidas) + app `finances/` cobrindo 100% dos casos restantes + backup de produção feito (`scripts/backup_db.py` / dump prod)

## Objetivo

Remover em bloco o módulo financeiro pessoal legado — a seção `app/(dashboard)/financial/` do frontend (sidebar "Financeiro", ~18k LOC), os hooks/schemas/query-keys/constants associados, e os models/serializers/services/viewsets/rotas legados do backend — substituído pelo app `finances/` (sidebar "Condomínio"). É o **único plano do roadmap que deleta dado e tabela**, portanto exige que o substituto esteja 100% no ar e backup feito antes de qualquer migrate. O ponto não-óbvio (descoberto na leitura do código): **`Person`, `RentPayment` e `FinancialSettings` NÃO são removíveis** — o app NOVO `finances/` depende deles (`finances.Employee.person` FK, `condo_balance_service` importa `RentPayment`/`FinancialSettings`, `owner_distribution_service` usa `Person`, e `core.Apartment.owner` FK aponta para `Person`). O plano remove só o que é genuinamente legado-exclusivo e mantém o subconjunto load-bearing.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MÉDIO | Mapa de remoção do legado frontend (~18k LOC; 67 .tsx/15.441 LOC, 19 hooks/~2.027 LOC, 13 schemas) — só 2 acoplamentos via `use-persons` impedem deletar em bloco | `frontend/app/(dashboard)/financial` (diretório) | Desacoplar os 2 pontos `use-persons`, depois deletar em bloco rotas+hooks+schemas+constants+sidebar+query-keys+testes |
| MÉDIO | Acoplamento 1: select de owner do apartamento usa `usePersons` (módulo legado) | `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx:39,71` | Trocar para hook slim `useOwners` (mantido) que continua lendo `/persons/` |
| MÉDIO | Acoplamento 2: vínculo `person` do Employee do app NOVO usa `usePersons` legado | `frontend/app/(dashboard)/finances/employees/_components/employee-form-modal.tsx:37,83` | Trocar para o mesmo hook slim `useOwners` |
| LOW | `BaseService` é código morto (nenhum consumidor de produção; só `__init__` + teste) | `core/services/base.py:17-207` | Deletar `base.py`, o re-export em `__init__.py` e o teste |
| (depreciação) | Models/services/viewsets/urls legados do financeiro pessoal | `core/models.py:1033-1620`, `core/services/*`, `core/viewsets/financial_*`, `core/urls.py:58-76` | Remover models legado-exclusivos + camadas, mantendo `Person`/`RentPayment`/`FinancialSettings` |

## Abordagem técnica

O plano é executado em **3 sub-sessões sequenciais** (cada uma com gate verde antes da próxima). Ordem obrigatória: desacoplar → deletar frontend → deletar backend.

### Conjunto KEEP vs REMOVE (decidido lendo o código — não readivinhar)

**MANTER (load-bearing para o app NOVO `finances/` ou para `core` patrimonial):**
- `core.Person` — FK de `finances.Employee.person` (`finances/models.py:598-600`), `core.Apartment.owner` (`core/models.py:392-398`), `owner_distribution_service.py:19,97`, `finances/serializers.py:553`.
- `core.RentPayment` — importado por `finances/services/condo_balance_service.py:26`; alimentado pelo calendário de aluguéis (`DashboardViewSet.toggle_rent_payment`, `core/views.py:754`, via `RentScheduleService`).
- `core.FinancialSettings` — importado por `finances/services/condo_balance_service.py:26` (`initial_balance`, `rent_tracking_start_date`).
- Serializers: `PersonSimpleSerializer` (`core/serializers.py:67`), `PersonSerializer` (`:702`), `RentPaymentSerializer` (`:1055`), `FinancialSettingsSerializer`, `FinalizedMonthProtectionMixin` (`:676`) — todos usados por `Apartment.owner` nested, `finances`, e/ou pelos serializers mantidos.
- ViewSets: `PersonViewSet`, `RentPaymentViewSet`, `FinancialSettingsViewSet` (todos em `core/viewsets/financial_views.py`) — `PersonViewSet` serve o select de owner; `RentPaymentViewSet`/`FinancialSettingsViewSet` ainda têm consumidores.

**REMOVER (legado-exclusivo — verificado por grep que `finances/` só os cita em comentários/docstrings, nunca em código):**
- Models: `CreditCard`, `ExpenseCategory`, `Expense`, `ExpenseInstallment`, `Income`, `EmployeePayment`, `PersonIncome`, `PersonPayment`, `PersonPaymentSchedule`, `ExpenseMonthSkip`, `MonthSnapshot` (`core/models.py:1033,1069,1102,1220,1284,1350,1391,1424,1459,1543`).
- Services: `core/services/base.py`, `cash_flow_service.py`, `daily_control_service.py`, `expense_service.py`, `financial_dashboard_service.py`, `month_advance_service.py`, `person_payment_schedule_service.py`, `simulation_service.py`.
- ViewSets: `core/viewsets/financial_dashboard_views.py` (inteiro), `core/viewsets/month_advance_views.py` (inteiro), e de `core/viewsets/financial_views.py` remover só `CreditCardViewSet`, `ExpenseCategoryViewSet`, `ExpenseViewSet`, `ExpenseInstallmentViewSet`, `IncomeViewSet`, `EmployeePaymentViewSet`, `PersonIncomeViewSet`, `PersonPaymentViewSet`, `PersonPaymentScheduleViewSet`, `ExpenseMonthSkipViewSet` (mantendo `PersonViewSet`/`RentPaymentViewSet`/`FinancialSettingsViewSet`).
- Serializers legado-exclusivos em `core/serializers.py`: `CreditCardSerializer`, `ExpenseCategorySerializer`, `ExpenseSerializer`, `ExpenseInstallmentSerializer`, `IncomeSerializer`, `EmployeePaymentSerializer`, `PersonIncomeSerializer`, `PersonPaymentSerializer`, `PersonPaymentScheduleSerializer`, `ExpenseMonthSkipSerializer`, `MonthSnapshotSerializer`.

### Sub-sessão A — Desacoplar os 2 pontos `use-persons` (refactor explicit-owner, frontend)

1. Criar hook slim `frontend/lib/api/hooks/use-owners.ts` exportando `useOwners()` — cópia enxuta do `usePersons` atual (`use-persons.ts:7-18`): `GET /persons/?page_size=10000`, `extractResults`, `.map(ownerSchema.parse)`. O endpoint `/persons/` (servido por `PersonViewSet`, mantido) continua sendo a fonte. Usar uma `queryKeys.owners` nova (`['owners']`) — NÃO reusar `queryKeys.persons` (que será deletada).
2. Criar `frontend/lib/schemas/owner.schema.ts` com um `ownerSchema` mínimo (`id`, `name`) — o select só precisa de `id`+`name` (`apartment-form-modal.tsx:280-281`, `employee-form-modal.tsx:280-281`). Não reusar `person.schema.ts` (será deletado).
3. Em `apartment-form-modal.tsx`: trocar `import { usePersons } from '@/lib/api/hooks/use-persons'` (linha 39) por `useOwners`, e `const { data: persons } = usePersons()` (linha 71) por `const { data: owners } = useOwners()`; renomear `persons` → `owners` no JSX do select (linha ~372+). Campo `owner_id` (linhas 61,86,109,122,129) permanece igual (continua FK para `Person` via `Apartment.owner`).
4. Em `finances/employees/_components/employee-form-modal.tsx`: trocar `usePersons` (linha 37) por `useOwners` e `persons` (linha 83) por `owners` (JSX linhas 278-281). `person_id` continua FK para `Person` (`finances.Employee.person`).
5. Gate frontend verde. **Nenhum endpoint backend muda nesta sub-sessão.**

### Sub-sessão B — Deletar o frontend legado em bloco

1. Deletar o diretório inteiro `frontend/app/(dashboard)/financial/` (67 .tsx + testes).
2. Deletar os 19 hooks legado-exclusivos em `frontend/lib/api/hooks/`: `use-persons.ts`, `use-credit-cards.ts`, `use-expense-categories.ts`, `use-expenses.ts`, `use-expense-installments.ts`, `use-expense-month-skips.ts`, `use-incomes.ts`, `use-employee-payments.ts`, `use-person-incomes.ts`, `use-person-payments.ts`, `use-person-payment-schedules.ts`, `use-cash-flow.ts`, `use-daily-control.ts`, `use-financial-dashboard.ts`, `use-month-advance.ts`, `use-monthly-purchases.ts`, `use-simulation.ts`, mais `use-rent-payments.ts` e `use-financial-settings.ts` **somente se nenhum consumidor fora de `financial/` restar** (grep antes — se algum sobrar, mantê-los). Deletar os testes correspondentes em `frontend/lib/api/hooks/__tests__/`.
3. Deletar os 13 schemas legado-exclusivos em `frontend/lib/schemas/`: `person.schema.ts`, `credit-card.schema.ts`, `expense.schema.ts`, `expense-category.schema.ts`, `expense-installment.schema.ts`, `expense-month-skip.schema.ts`, `income.schema.ts`, `employee-payment.schema.ts`, `person-income.schema.ts`, `person-payment.schema.ts`, `person-payment-schedule.schema.ts`, `financial-settings.schema.ts`, `rent-payment.schema.ts` — cada um só após confirmar zero importadores remanescentes (grep). Manter `apartment.schema.ts`, `lease.schema.ts`, `tenant.schema.ts`, `landlord.schema.ts`, `rent-adjustment.schema.ts`, `furniture.schema.ts`, `building.schema.ts` e tudo em `schemas/finances/`.
4. Em `frontend/components/layouts/sidebar.tsx`: remover o array `financialChildren` (linhas 45-59) e o item de menu "Financeiro" (linhas 110-115). Manter `condominioChildren` e o item "Condomínio" (linhas 116-121). Ajustar `mobile-nav.tsx` se espelhar o grupo.
5. Em `frontend/lib/utils/constants.ts`: remover as constantes `FINANCIAL*` do `ROUTES` (linhas 58-70). Confirmar zero usos remanescentes por grep.
6. Em `frontend/lib/api/query-keys.ts`: remover as chaves `expenses`, `expenseInstallments`, `expenseCategories`, `expenseMonthSkips`, `persons`, `creditCards`, `incomes`, `rentPayments`, `employeePayments`, `personIncomes`, `personPayments`, `personPaymentSchedules`, `dailyControl`, `cashFlow`, `financialDashboard`, `monthAdvance`, `financialSettings` (linhas 22-302) — cada uma após confirmar que `use-owners`/`finances/*` não a referenciam.
7. Deletar utilitários legado-exclusivos restantes (ex.: `lib/utils/expense-type-con*` citado no digest) após grep de importadores.
8. Gate frontend verde (lint + type-check + test:unit).

### Sub-sessão C — Deletar o backend legado + migration de remoção

1. **Backup obrigatório antes de qualquer alteração de schema:** `python scripts/backup_db.py` (local) e o dump de produção (`pg_dump "<prod-uri>" --schema=public --no-owner --no-acl`) — conforme `.claude/rules/database.md`. Sem backup bem-sucedido, **parar**.
2. `core/serializers.py`: remover os 11 serializers legado-exclusivos listados acima. **Manter** `PersonSimpleSerializer`, `PersonSerializer`, `RentPaymentSerializer`, `FinancialSettingsSerializer`, `FinalizedMonthProtectionMixin`. Atualizar quaisquer imports.
3. `core/viewsets/financial_views.py`: remover os 10 viewsets legado-exclusivos; manter `PersonViewSet`, `RentPaymentViewSet`, `FinancialSettingsViewSet`. Deletar `core/viewsets/financial_dashboard_views.py` e `core/viewsets/month_advance_views.py` inteiros.
4. `core/viewsets/__init__.py`: remover dos imports/`__all__` (linhas 13-55) tudo que foi deletado (`CashFlowViewSet`, `DailyControlViewSet`, `FinancialDashboardViewSet`, `CreditCardViewSet`, `EmployeePaymentViewSet`, `ExpenseCategoryViewSet`, `ExpenseInstallmentViewSet`, `ExpenseMonthSkipViewSet`, `ExpenseViewSet`, `IncomeViewSet`, `PersonIncomeViewSet`, `PersonPaymentScheduleViewSet`, `PersonPaymentViewSet`, `MonthAdvanceViewSet`). Manter `PersonViewSet`, `RentPaymentViewSet`, `FinancialSettingsViewSet`.
5. `core/urls.py`: remover os `router.register` de `credit-cards`, `expense-categories`, `expenses`, `expense-installments`, `incomes`, `employee-payments`, `person-incomes`, `person-payments`, `financial-dashboard`, `cash-flow`, `daily-control`, `person-payment-schedules`, `expense-month-skips`, `month-advance` (linhas 59-76). Manter `persons` (58), `financial-settings` (61), `rent-payments` (65). Limpar imports órfãos no topo.
6. `core/services/`: deletar `base.py`, `cash_flow_service.py`, `daily_control_service.py`, `expense_service.py`, `financial_dashboard_service.py`, `month_advance_service.py`, `person_payment_schedule_service.py`, `simulation_service.py`. Remover de `core/services/__init__.py` os re-exports (`BaseService` em `:13,:22` e os demais).
7. `core/signals.py`: remover os receivers e os imports (linhas 32-45) dos models deletados (`EmployeePayment`, `Expense`, `ExpenseInstallment`, `ExpenseMonthSkip`, `Income`, `MonthSnapshot`, `PersonPayment`, `PersonPaymentSchedule`, `PersonIncome`, `CreditCard`, `ExpenseCategory`). **Manter** os receivers de `Person` (`:328-343`), `RentPayment` (`:47`) e `FinancialSettings`, pois os models permanecem e alimentam o cache `finance-*` do app novo (`_invalidate_financial_caches`).
8. `core/models.py`: remover as 11 classes de model legado-exclusivas (`CreditCard`, `ExpenseCategory`, `Expense`, `ExpenseInstallment`, `Income`, `EmployeePayment`, `PersonIncome`, `PersonPayment`, `PersonPaymentSchedule`, `ExpenseMonthSkip`, `MonthSnapshot`) + os enums órfãos (`PersonIncomeType:1259`). **Não tocar** em `Person`, `RentPayment`, `FinancialSettings`, `Apartment.owner`, `Lease`. Remover o re-export em `core/admin.py` se algum dos models deletados estiver registrado (verificar — atualmente o admin só registra `Building/Furniture/Apartment/Tenant/Lease/WhatsAppVerification/DeviceToken/PaymentProof/Notification`, então provavelmente nada a fazer).
9. Gerar a migration: `python manage.py makemigrations core` → produz `core/migrations/0050_*.py` com `DeleteModel` para cada um dos 11 models. Adicionar manualmente, na mesma migration, o `reverse_sql` de RLS via `migrations.RunSQL` com **SQL estático** para reabilitar RLS no rollback (espelhando o padrão de `0047`/`0048`): a operação forward é `DeleteModel` (drop da tabela, RLS some junto); o `reverse_sql` recria RLS só se o reverse do `DeleteModel` recriar a tabela — como Django recria a tabela no reverse, anexar `RunSQL("ALTER TABLE public.core_expense ENABLE ROW LEVEL SECURITY; ...", reverse_sql=migrations.RunSQL.noop)` **depois** dos `DeleteModel` na lista `operations`, condicionado à direção. Padrão concreto: usar `migrations.RunSQL(sql=migrations.RunSQL.noop, reverse_sql="ALTER TABLE public.core_creditcard ENABLE ROW LEVEL SECURITY; ... <11 tabelas>")` como **primeira** operação, de modo que no forward é no-op e no reverse (após Django recriar as tabelas) reabilita RLS — mantendo o invariante "toda tabela public tem RLS". Tabelas: `core_creditcard, core_expensecategory, core_expense, core_expenseinstallment, core_income, core_employeepayment, core_personincome, core_personpayment, core_personpaymentschedule, core_expensemonthskip, core_monthsnapshot`.
10. `python manage.py migrate core` (local, após backup) e validar.
11. Deletar os testes legado em `tests/` (lista na seção TDD). Gate backend verde.
12. Aplicar a migration em produção **após** P0–P6 e backup prod (via deploy normal do Render, que roda `migrate`; confirmar no Supabase advisor `get_advisors type=security` que nenhum `rls_disabled` apareceu e que as tabelas sumiram).

## Arquivos a criar / modificar

**Criar (sub-sessão A):**
- `frontend/lib/api/hooks/use-owners.ts` — hook slim `useOwners()` lendo `/persons/`.
- `frontend/lib/schemas/owner.schema.ts` — `ownerSchema` (`id`, `name`).
- `frontend/lib/api/hooks/__tests__/use-owners.test.tsx` — teste do hook (MSW na fronteira HTTP).

**Modificar (sub-sessão A):**
- `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx` — `usePersons`→`useOwners` (linhas 39,71, JSX do select).
- `frontend/app/(dashboard)/finances/employees/_components/employee-form-modal.tsx` — `usePersons`→`useOwners` (linhas 37,83, JSX 278-281).
- `frontend/lib/api/query-keys.ts` — adicionar `owners` (sub-sessão A); remover chaves legadas (sub-sessão B).

**Deletar (sub-sessão B):** diretório `frontend/app/(dashboard)/financial/`; 17-19 hooks em `frontend/lib/api/hooks/` + testes; 13 schemas em `frontend/lib/schemas/`; utilitários legado-exclusivos. **Modificar:** `sidebar.tsx`, `mobile-nav.tsx`, `constants.ts`, `query-keys.ts`.

**Deletar (sub-sessão C):** `core/services/base.py`, `cash_flow_service.py`, `daily_control_service.py`, `expense_service.py`, `financial_dashboard_service.py`, `month_advance_service.py`, `person_payment_schedule_service.py`, `simulation_service.py`; `core/viewsets/financial_dashboard_views.py`, `core/viewsets/month_advance_views.py`. **Modificar:** `core/models.py`, `core/serializers.py`, `core/viewsets/financial_views.py`, `core/viewsets/__init__.py`, `core/services/__init__.py`, `core/signals.py`, `core/urls.py`, `core/admin.py` (se aplicável). **Criar:** `core/migrations/0050_remove_legacy_financial_models.py`. **Deletar testes:** ver TDD.

## TDD — cenários de teste

> Regra do projeto: a remoção é validada pela **ausência de regressão** nos caminhos mantidos + pela suíte continuar verde após deletar os testes do legado. Não se escreve teste novo para código deletado; escreve-se o teste de regressão que prova que o substituto cobre o caso e que o KEEP-set não quebrou.

**Frontend (sub-sessão A — vitest + MSW na fronteira HTTP):**
- `useOwners retorna lista de owners do endpoint /persons/` — MSW responde envelope paginado; assert `id`+`name` parseados.
- `useOwners desempacota array não-paginado` — edge case do `extractResults`.
- `apartment-form-modal popula o select de owner via useOwners (não usePersons)` — render + assert opções; regressão que prova o desacoplamento 1.
- `employee-form-modal (finances) popula o select de person via useOwners` — regressão que prova o desacoplamento 2.

**Frontend (sub-sessão B — regressão):**
- `sidebar não renderiza o grupo "Financeiro"` e `sidebar ainda renderiza "Condomínio"` (`__tests__/sidebar.test.tsx`).
- Suíte `npm run type-check` passa sem nenhuma referência órfã a `ROUTES.FINANCIAL*`/`queryKeys.persons`/schemas deletados (o type-check é o teste de regressão de imports quebrados).

**Backend (sub-sessão C — regressão, pytest):**
- `test_legacy_financial_endpoints_return_404` — `GET /api/expenses/`, `/api/incomes/`, `/api/cash-flow/monthly/`, `/api/financial-dashboard/overview/`, `/api/month-advance/...` retornam 404 (rotas removidas).
- `test_persons_endpoint_still_works` — `GET /api/persons/` 200 (KEEP — alimenta owner select).
- `test_rent_payments_endpoint_still_works` e `test_financial_settings_endpoint_still_works` — 200 (KEEP).
- `test_apartment_owner_fk_intact` — criar `Apartment` com `owner=Person` e ler `owner` nested via `ApartmentSerializer`.
- `test_finances_employee_person_fk_intact` — criar `finances.Employee` com `person=Person`; `finances` continua íntegro (rodar a suíte `tests/integration/test_finances/` + `tests/unit/test_finances/` como regressão dirigida).
- `test_migration_0050_forward_and_reverse` — aplicar 0050 e reverter; após reverse, as 11 tabelas voltam **com RLS habilitado** (consultar `pg_class.relrowsecurity` ou advisor).
- **Deletar** (não migrar): `tests/integration/test_expense_api.py`, `test_cash_flow_api.py`, `test_daily_control_api.py`, `test_financial_dashboard_api.py`, `test_financial_dashboard_extended.py`, `test_financial_dashboard_views.py`, `test_income_payment_api.py`, `test_month_advance_api.py`; `tests/unit/test_base_service.py`, `test_expense_service.py`, `test_month_advance_service.py`, `tests/unit/test_financial/` (cash_flow, daily_control, financial_dashboard, person_payment_schedule, simulation). **Manter** `tests/integration/test_finances/` e `tests/unit/test_finances/`.

## Migrations / dados

- **Migration:** `core/migrations/0050_remove_legacy_financial_models.py` — `DeleteModel` para `CreditCard, ExpenseCategory, Expense, ExpenseInstallment, Income, EmployeePayment, PersonIncome, PersonPayment, PersonPaymentSchedule, ExpenseMonthSkip, MonthSnapshot` (drop das tabelas `core_creditcard … core_monthsnapshot`). Ordem dos `DeleteModel` respeita FKs (filhos antes dos pais: `ExpenseInstallment` antes de `Expense`; `CreditCard` referencia `Person` mantido, sem problema).
- **RLS no reverse:** primeira operação da migration = `migrations.RunSQL(sql=migrations.RunSQL.noop, reverse_sql="ALTER TABLE public.core_creditcard ENABLE ROW LEVEL SECURITY; … (11 tabelas)")` com **SQL estático** (sem f-string, evita ruff S608), garantindo que o rollback restaure o invariante "toda tabela public tem RLS" após o Django recriar as tabelas.
- **Backup ANTES:** `python scripts/backup_db.py` (local) + `pg_dump` do `public` de produção (`.claude/rules/database.md`). Sem backup bem-sucedido, abortar. Migration de produção só após P0–P6 concluídos.
- **Dado vivo:** os dados das 11 tabelas legadas são **descartados** (módulo substituído pelo `finances/`, que tem seus próprios dados já seedados em prod). Confirmar com o usuário que o `finances/` cobre 100% antes de dropar — esta é a única operação irreversível de dados do roadmap.
- **Pós-deploy prod:** rodar `get_advisors type=security` no Supabase; confirmar ausência de `rls_disabled` (CRITICAL) e que as 11 tabelas sumiram de `list_tables`.

## Constraints (o que NÃO fazer)

- NÃO remover `Person`, `RentPayment`, `FinancialSettings`, `Apartment.owner`, nem `PersonSimpleSerializer`/`PersonSerializer`/`RentPaymentSerializer`/`FinancialSettingsSerializer`/`FinalizedMonthProtectionMixin` — são load-bearing para o app NOVO `finances/` e para `core` patrimonial.
- NÃO deletar `PersonViewSet`, `RentPaymentViewSet`, `FinancialSettingsViewSet` nem suas rotas (`persons`, `rent-payments`, `financial-settings`).
- NÃO tocar em nada de `finances/`, `tests/**/test_finances/`, nem nos schemas/hooks de `schemas/finances` (módulo NOVO).
- NÃO iniciar a remoção (sub-sessões B/C) antes de o `finances/` cobrir 100% os casos restantes e antes de P3.2 (mobile legado removido — senão `mobile/lib/api/hooks/use-admin-financial.ts` quebra contra os endpoints deletados).
- NÃO rodar migrate destrutivo sem backup verde. NÃO usar `flush`/`reset_db`. NÃO refatorar a fundo o que sobra — só remover.
- NÃO usar `# noqa`/`# type: ignore`/`eslint-disable`/`@ts-ignore` para silenciar imports órfãos — deletar a referência de fato.
- NÃO reusar `queryKeys.persons`/`person.schema.ts` no hook novo `useOwners` (eles serão deletados) — criar `owners`/`owner.schema.ts`.

## Critérios de aceite (binários)

- [ ] `useOwners` criado; `apartment-form-modal` e `finances/employees/employee-form-modal` não importam mais `use-persons`.
- [ ] Diretório `frontend/app/(dashboard)/financial/` removido por completo.
- [ ] Sidebar sem grupo "Financeiro"; grupo "Condomínio" intacto. `ROUTES.FINANCIAL*` e `queryKeys` legadas removidas, zero importadores órfãos.
- [ ] 11 models legados removidos de `core/models.py`; `Person`/`RentPayment`/`FinancialSettings`/`Apartment.owner` intactos.
- [ ] 8 services + 2 viewsets legados deletados; `BaseService` e seu re-export removidos. `PersonViewSet`/`RentPaymentViewSet`/`FinancialSettingsViewSet` mantidos.
- [ ] Rotas legadas (`expenses`, `incomes`, `cash-flow`, `financial-dashboard`, `daily-control`, `month-advance`, etc.) retornam 404; `persons`/`rent-payments`/`financial-settings` retornam 200.
- [ ] Migration `0050` aplica (forward) e reverte (com RLS reabilitado nas 11 tabelas no reverse). Backup feito antes.
- [ ] `finances/` continua íntegro: `tests/**/test_finances/` 100% verde.
- [ ] Testes do legado deletados; suíte restante sem referências órfãs.
- [ ] Advisor de segurança Supabase sem `rls_disabled` após deploy prod.

## Gate de verificação

```bash
# Frontend (sub-sessões A e B)
cd frontend && npm run lint && npm run type-check && npm run test:unit

# Backend (sub-sessão C) — escopado nos arquivos editados + regressão dirigida finances + core CRUD
ruff check core/ && ruff format --check core/
mypy core/ && pyright
python -m pytest tests/integration/test_finances/ tests/unit/test_finances/ \
  tests/integration/test_apartment_api.py tests/integration/test_lease_api.py \
  tests/migrations/ -q
# Regressão de rotas removidas/mantidas:
python -m pytest tests/integration/test_legacy_removal.py -q
```

Zero erros E zero warnings (Ruff, mypy, Pyright, ESLint, TypeScript, pytest). A suíte cheia tem flakiness pré-existente de xdist/Redis — não é bloqueio; rodar escopado + regressão dirigida.

## Handoff

**Commit (3 commits, um por sub-sessão):**
- `refactor(frontend): decouple apartment/employee owner select from legacy use-persons (useOwners)`
- `refactor(frontend): remove legacy personal-financial module (financial/ routes, hooks, schemas, sidebar)`
- `refactor(backend): remove legacy personal-financial models/services/viewsets + migration 0050`

Todos terminando com:
```
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

**Docs/estado a atualizar:**
- `docs/LESSONS_LEARNED.md` — marcar o módulo financeiro pessoal como **histórico/removido** (não apagar o aprendizado; anotar que foi substituído pelo `finances/` e quando).
- `CLAUDE.md` (raiz) — atualizar o Modelo de Dados (remover os models legados da seção "Módulo Financeiro") e a lista de rotas em "API Base" (remover `persons`-CRUD legado-exclusivo etc.; manter `persons`/`rent-payments`/`financial-settings`).
- `docs/plans/2026-06-11-audit-remediation-roadmap.md` — marcar P7.1 como concluído.

**O próximo plano assume:** o módulo financeiro pessoal legado não existe mais (frontend, backend, mobile); `Person`/`RentPayment`/`FinancialSettings` permanecem como infraestrutura compartilhada do `finances/`; o roadmap segue para P8 (features novas) sobre o `finances/` como única superfície financeira.
