# Implementation Plan — Full Application Fix

**Baseado no:** `docs/reviews/2026-04-05-full-application-review.md`
**Total de issues:** ~88 verificados
**Estratégia:** Agrupar por dependência e área de código para minimizar conflitos de merge e maximizar eficiência.

---

## Sessão 1: Security Hardening — Settings & Secrets

**Branch:** `fix/security-settings`
**Estimativa:** 2-3h
**Issues cobertos:** SEC-01 (parcial), SEC-02, SEC-03, DEV-03, DEV-08, SEC-12

### Tarefas:

1. **settings.py — Remover defaults inseguros**
   - `SECRET_KEY = config("SECRET_KEY")` — sem default, falha se não setado
   - `DEBUG = config("DEBUG", default=False, cast=bool)` — default False
   - JWT: `ACCESS_TOKEN_LIFETIME = timedelta(minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15, cast=int))`
   - JWT: `REFRESH_TOKEN_LIFETIME = timedelta(days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int))`
   - JWT: `ROTATE_REFRESH_TOKENS = True`, `BLACKLIST_AFTER_ROTATION = True`
   - Adicionar: `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_HTTPONLY`, `SESSION_COOKIE_HTTPONLY` (condicionais a não-DEBUG)

2. **.env.example — Alinhar nomes de variáveis**
   - Renomear `JWT_ACCESS_TOKEN_LIFETIME` → `JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15`
   - Renomear `JWT_REFRESH_TOKEN_LIFETIME` → `JWT_REFRESH_TOKEN_LIFETIME_DAYS=7`
   - Adicionar `SECRET_KEY=change-me-in-production`
   - Adicionar `REDIS_PASSWORD=`

3. **docker-compose.yml — Fix env var names**
   - `DJANGO_SECRET_KEY` → `SECRET_KEY`
   - Garantir todas as vars alinham com settings.py

4. **docker-compose.prod.yml — Fix settings module e Redis**
   - `DJANGO_SETTINGS_MODULE=condominios_manager.settings_production` (linhas 57, 116, 143)
   - Redis: `requirepass ${REDIS_PASSWORD}` (sem default vazio)

5. **settings_production.py — Adicionar security headers**
   - `SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'`
   - Verificar HSTS, SSL redirect, CONTENT_TYPE_NOSNIFF já presentes

6. **Testes:** Verificar que app falha ao iniciar sem SECRET_KEY setado.

---

## Sessão 2: Security Hardening — Auth Flow

**Branch:** `fix/security-auth`
**Estimativa:** 4-5h
**Issues cobertos:** SEC-01 (tokens), SEC-05, FE-01, FE-02, FE-03
**Pré-requisito:** Sessão 1

### Tarefas:

1. **Backend — Tokens via httpOnly cookies**
   - `core/auth.py` — OAuth callback: substituir tokens na URL por Set-Cookie headers
   - Criar endpoint `/api/auth/set-cookies/` para converter tokens em cookies (se necessário para fluxo mobile)
   - Configurar cookie: `secure=True` (prod), `httponly=True`, `samesite='Lax'`

2. **Backend — Rate limiting**
   - Instalar `django-ratelimit` ou usar DRF throttling
   - Configurar em settings.py: `DEFAULT_THROTTLE_RATES = {'anon': '100/hour', 'user': '1000/hour', 'auth': '10/hour'}`
   - Aplicar throttle em: token, token/refresh, whatsapp/request, whatsapp/verify

3. **Frontend — Token refresh deduplication**
   - `frontend/lib/api/client.ts` — Implementar refresh queue:
     - Variable `refreshPromise: Promise | null = null`
     - Se refresh já em andamento, retornar promise existente
     - Limpar promise após conclusão

4. **Frontend — Cookie max-age alignment**
   - `frontend/lib/api/hooks/use-auth.ts` — Alinhar cookie max-age com JWT expiry (900s para access)

5. **Frontend — Auth store fixes**
   - `setToken()` deve setar `isAuthenticated = true`
   - `setTokens()` deve limpar `user: null` para forçar refetch

6. **Testes:** Testar fluxo OAuth end-to-end, token refresh, rate limiting.

---

## Sessão 3: Security Hardening — Infrastructure

**Branch:** `fix/security-infra`
**Estimativa:** 2-3h
**Issues cobertos:** SEC-04, SEC-07, SEC-10, SEC-11, SEC-13, SEC-14, DEV-11

### Tarefas:

1. **storage.py — Path traversal fix**
   - Adicionar método `_validate_path()` em todas as classes de storage
   - Validar com `resolve()` + `startswith(base_path)`

2. **docker-entrypoint.sh — Fix shell injection**
   - Substituir interpolação shell por `os.environ.get()` no Python inline
   - Usar `python -c "import os; ..."` ao invés de `'$VAR'`

3. **Nginx — Enable HSTS**
   - Descomentar `Strict-Transport-Security` header
   - Adicionar `X-Content-Type-Options: nosniff`

4. **urls.py — Swagger condicional**
   - Wrap endpoints de schema em `if settings.DEBUG:`

5. **permissions.py — Fix IsTenantOrAdmin**
   - Adicionar `if not request.user or not request.user.is_authenticated: return False`

6. **urls.py — Criar /api/health/ endpoint**
   - Endpoint simples que verifica DB e Redis connectivity
   - Atualizar docker-compose health checks

7. **Testes:** Testar path traversal prevention, health endpoint.

---

## Sessão 4: Data Integrity — Models & Constraints

**Branch:** `fix/data-integrity-models`
**Estimativa:** 3-4h
**Issues cobertos:** DAT-01, DAT-05, DAT-06, DAT-10, DAT-11, PERF-10

### Tarefas:

1. **Migration — CASCADE → PROTECT em Person FKs**
   - CreditCard.person: `on_delete=PROTECT`
   - PersonIncome.person: `on_delete=PROTECT`
   - EmployeePayment.person: `on_delete=PROTECT`
   - PersonPayment.person: `on_delete=PROTECT`

2. **Migration — Soft delete unique constraints**
   - RentPayment: `UniqueConstraint(fields=["lease", "reference_month"], condition=Q(is_deleted=False))`
   - ExpenseInstallment: idem
   - EmployeePayment: idem
   - CreditCard: idem
   - Remover `unique_together` correspondentes

3. **Migration — CHECK constraints**
   - `Apartment.rental_value >= 0`
   - `Expense.total_amount >= 0`
   - `RentPayment.amount_paid > 0`
   - Todos os DecimalField monetários

4. **Migration — DecimalField max_digits consistente**
   - Padronizar todos os campos monetários para `max_digits=12, decimal_places=2`

5. **Models — Soft delete cascade**
   - Apartment.delete() override: cascade soft-delete para Leases
   - Building.delete() override: cascade soft-delete para Apartments

6. **Models — clean() validation**
   - RentPayment.clean(): `amount_paid > 0`, `payment_date >= reference_month`
   - EmployeePayment.clean(): `base_salary >= 0`, reference_month is first of month
   - CreditCard.clean(): `due_day` entre 1-31, `closing_day` entre 1-31

7. **Testes:** Migration tests, constraint violation tests, cascade tests.

---

## Sessão 5: Data Integrity — Signals & Cache

**Branch:** `fix/data-integrity-signals`
**Estimativa:** 2-3h
**Issues cobertos:** DAT-02, PERF-08

### Tarefas:

1. **signals.py — Adicionar handlers para Expense**
   - `post_save(Expense)` → `_invalidate_financial_caches()`
   - `post_delete(Expense)` → `_invalidate_financial_caches()`

2. **signals.py — Adicionar handlers para ExpenseInstallment**
   - `post_save(ExpenseInstallment)` → `_invalidate_financial_caches()`
   - `post_delete(ExpenseInstallment)` → `_invalidate_financial_caches()`

3. **signals.py — Adicionar handlers para Income**
   - `post_save(Income)` → `_invalidate_financial_caches()`
   - `post_delete(Income)` → `_invalidate_financial_caches()`

4. **signals.py — Adicionar handlers para EmployeePayment**
   - `post_save(EmployeePayment)` → `_invalidate_financial_caches()`
   - `post_delete(EmployeePayment)` → `_invalidate_financial_caches()`

5. **signals.py — Refinar invalidation scope**
   - Building save: invalidar apenas apartments daquele building, não todos
   - Implementar invalidação granular por FK

6. **Testes:** Verificar que cache é invalidado após cada operação.

---

## Sessão 6: Data Integrity — Transactions & Concurrency

**Branch:** `fix/data-integrity-transactions`
**Estimativa:** 3-4h
**Issues cobertos:** DAT-03, DAT-04, DAT-07, DAT-08, DAT-09, DAT-13, DAT-14, DAT-15

### Tarefas:

1. **financial_views.py — generate_installments() com transaction**
   - Wrap em `@transaction.atomic`

2. **financial_views.py — mark_paid endpoints com select_for_update**
   - `ExpenseInstallmentViewSet.mark_paid`: `select_for_update().get(pk=pk)`
   - `ExpenseViewSet.mark_paid`: idem
   - `ExpenseInstallmentViewSet.bulk_mark_paid`: transaction + select_for_update
   - `RentPaymentViewSet.mark_received`: idem

3. **daily_control_service.py — mark_paid com select_for_update**
   - `_mark_installment_paid`: `select_for_update().get(pk=item_id)`
   - `_mark_expense_paid`: idem
   - `_mark_income_received`: idem

4. **rent_adjustment_service.py — select_for_update + transaction**
   - `apply_adjustment()`: `select_for_update()` no Lease
   - `activate_pending_adjustments()`: wrap em `@transaction.atomic`

5. **month_advance_service.py — Fix rollback scope**
   - `rollback_month()`: deletar todos os EmployeePayments auto-criados, não apenas não-pagos
   - Adicionar flag `auto_created` ou tracking separado

6. **person_payment_schedule_service.py — transaction em bulk_configure**
   - Wrap em `@transaction.atomic`
   - Validar due_day entre 1-31

7. **lease_service.py — Validar IDs existem**
   - `transfer_lease()`: verificar responsible_tenant_id e tenant_ids existem antes de criar
   - Validar validity_months > 0

8. **import_financial_data.py — transaction wrapper**
   - Wrap `run()` em `@transaction.atomic`

9. **Testes:** Testes de concorrência, testes de rollback.

---

## Sessão 7: Performance — Query Optimization

**Branch:** `fix/performance-queries`
**Estimativa:** 6-8h
**Issues cobertos:** PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06, PERF-07, PERF-09

### Tarefas:

1. **financial_dashboard_service.py — Refatorar aggregations**
   - Substituir 12 queries/person por aggregate condicional único
   - Usar `Exists()` + `OuterRef()` para has_income/has_apartments
   - Target: 120 queries → 2-5 queries

2. **views.py — LeaseViewSet date filtering no banco**
   - Usar `annotate(end_date=...)` com `ExpressionWrapper` para date arithmetic
   - Remover Python-side filtering

3. **cash_flow_service.py — select_related fixes**
   - `_collect_owner_repayments`: add `select_related("apartment__owner")`
   - `_collect_person_stipends`: add `select_related("person")`

4. **contract_service.py — prefetch_related**
   - `calculate_lease_furniture`: `prefetch_related('apartment__furnitures', 'tenants__furnitures')`

5. **Migration — Add missing indexes**
   - `Apartment(is_rented)` idx
   - `Expense(person, expense_type)` idx
   - `Expense(person, expense_date)` idx
   - `ExpenseInstallment(expense, due_date, is_paid)` idx

6. **cash_flow_service.py — Decimal serialization**
   - Substituir `float()` por `str()` ou DecimalField serializer

7. **financial_dashboard_service.py — Service-level caching**
   - Adicionar `@cache_result` decorator em métodos pesados
   - Cache key inclui year + month

8. **serializers.py — Criar TenantSummarySerializer**
   - Campos: `id, name, cpf_cnpj`
   - Usar em LeaseSerializer para read (ao invés do TenantSerializer completo)

9. **Testes:** Benchmark antes/depois, verificar query count com assertNumQueries.

---

## Sessão 8: Business Logic Fixes

**Branch:** `fix/business-logic`
**Estimativa:** 3-4h
**Issues cobertos:** BIZ-01, BIZ-02, BIZ-03, BIZ-04, BIZ-05, BIZ-06 a BIZ-12, DAT-12

### Tarefas:

1. **Timezone — Substituir date.today() em 9 arquivos**
   - `from django.utils import timezone`
   - `date.today()` → `timezone.now().date()` em:
     - daily_control_service.py
     - rent_adjustment_service.py
     - date_calculator.py
     - fee_calculator.py
     - financial_dashboard_service.py (5 locais)
     - cash_flow_service.py
     - ipca_service.py
     - lease_service.py
     - serializers.py

2. **fee_calculator.py — Validação de inputs**
   - `calculate_daily_rate()`: `if rental_value <= 0: raise ValueError`
   - `calculate_late_fee()`: validar rental_value > 0, days_late >= 0

3. **whatsapp_service.py — Rate limiting + retry**
   - Adicionar rate limiter com backoff exponencial
   - Validar template variables contra schema esperado

4. **notification_service.py — Delivery tracking + bulk create**
   - Separar status de "criado" vs "enviado com sucesso"
   - `notify_new_proof()`: bulk_create + bulk fetch tokens

5. **person_payment_schedule_service.py — Fix soft delete filter**
   - `get_schedules_for_month()`: garantir que usa manager que exclui soft-deleted

6. **Validações menores**
   - Due day validation (1-31) em bulk_configure
   - Lease transfer validity_months > 0
   - CPF/CNPJ validator: normalizar empty string → None
   - Phone validator: log warning se > 11 dígitos

7. **Testes:** Testes de edge cases (rental_value=0, negative, timezone boundary).

---

## Sessão 9: DevOps — CI/CD & Docker

**Branch:** `fix/devops`
**Estimativa:** 3-4h
**Issues cobertos:** DEV-04 a DEV-16

### Tarefas:

1. **Dockerfile — Python 3.12**
   - `FROM python:3.12-slim as builder`
   - `FROM python:3.12-slim`

2. **CI workflow — Reescrever .github/workflows/ci.yml**
   - Python 3.12 (não 3.11)
   - Node 20 (não 18)
   - `pip install -r requirements.txt -r requirements-dev.txt`
   - Substituir black/isort/flake8 por `ruff check && ruff format --check`
   - mypy: `mypy core/ condominios_manager/` (sem --config-file=mypy.ini)
   - Remover `continue-on-error: true` de testes e type checking
   - Unificar coverage threshold com pytest.ini

3. **requirements.txt — Adicionar dependências de produção**
   - `sentry-sdk>=2.0.0,<3.0`
   - `whitenoise>=6.8.0,<7.0`
   - `django-storages[s3]>=1.14.0,<2.0`
   - Adicionar também em pyproject.toml

4. **Docker — Otimizações**
   - Separar Chromium em container worker (ou mover PDF generation para Celery)
   - collectstatic no build, não no runtime
   - Criar /api/health/ endpoint
   - Atualizar health checks nos docker-compose files

5. **logging_config.py — Fix JsonFormatter path**
   - `pythonjsonlogger.json.JsonFormatter` → `pythonjsonlogger.jsonlogger.JsonFormatter`

6. **next.config.js — Ajustar timeout**
   - `staticPageGenerationTimeout: 120` (2 minutos)

7. **Testes:** CI pipeline deve passar com todas as mudanças.

---

## Sessão 10: Frontend — Error Handling & Validation

**Branch:** `fix/frontend-quality`
**Estimativa:** 4-5h
**Issues cobertos:** FE-04 a FE-13

### Tarefas:

1. **Schemas — Conditional validation com .refine()**
   - `expense.schema.ts`: adicionar `.refine()` para regras condicionais (person_id required para card_purchase, etc.)
   - `person-payment.schema.ts`: date format validation com regex
   - `income.schema.ts`: alinhar validações com expense schema

2. **Currency — Fix floating-point**
   - `expense-form-modal.tsx`: usar schema transform com `Math.round(val * 100) / 100` consistentemente
   - Nunca fazer arithmetic em float para dinheiro no frontend

3. **Dates — Usar date-fns**
   - `daily-timeline.tsx:436`: substituir `substring(0,7) + '-01'` por `format(parseISO(day.date), 'yyyy-MM-01')`
   - Audit todos os locais com string manipulation de datas

4. **Error boundaries**
   - Criar `app/(dashboard)/error.tsx` com UI adequada
   - `error-boundary.tsx`: esconder stack trace em produção (verificar `process.env.NODE_ENV`)

5. **Accessibility**
   - Adicionar `aria-expanded` em collapse buttons do daily-timeline
   - Adicionar focus trap em modais (usar @radix-ui/react-focus-scope)
   - Verificar todas as modais de form

6. **Query invalidation**
   - `use-leases.ts`: invalidar por queryKey específico, não broad
   - Estabelecer query key factory pattern

7. **State management**
   - `daily/page.tsx`: combinar month/year em single state ou usar reducer
   - Remover nested setState calls

8. **Testes:** Testes de componentes básicos (pelo menos 5 componentes críticos).

---

## Sessão 11: Code Quality — DRY & SRP

**Branch:** `fix/code-quality`
**Estimativa:** 5-6h
**Issues cobertos:** QUAL-01 a QUAL-04, PERF-11

### Tarefas:

1. **cash_flow_service.py — Extrair _collect_installments() genérico**
   - Criar método base que aceita filtros e field mapping
   - Refatorar _collect_card_installments, _collect_loan_installments, etc. para usar base
   - Reduzir ~500 linhas duplicadas

2. **financial_dashboard_service.py — Dividir em services menores**
   - `FinancialOverviewService` — overview, summary
   - `DebtAnalysisService` — debt_by_person, debt_by_type
   - `InstallmentTrackingService` — upcoming, overdue
   - `CategoryAnalysisService` — category_breakdown
   - Manter `FinancialDashboardService` como facade

3. **Frontend — Extrair componentes das páginas**
   - `tenants/page.tsx` (618→~150 linhas): extrair TenantTable, TenantFilters
   - `leases/page.tsx` (517→~150 linhas): extrair LeaseTable, LeaseFilters
   - `apartments/page.tsx` (452→~150 linhas): extrair ApartmentTable, ApartmentFilters
   - `contract-template/page.tsx` (478→~150 linhas): extrair TemplateEditor, TemplatePreview

4. **Frontend — Form modal template**
   - Criar HOC ou composable pattern para os 19 form modals idênticos
   - Extrair: dialog wrapper, form setup, submit handling, error display

5. **Backend — Pagination max_page_size**
   - `core/pagination.py`: `max_page_size = 500` (reduzir de 10000)

6. **Testes:** Verificar que refatoração não quebrou nenhum teste existente.

---

## Sessão 12: Testing — Coverage Gaps

**Branch:** `fix/testing-coverage`
**Estimativa:** 6-8h
**Issues cobertos:** TEST-01 a TEST-04

### Tarefas:

1. **Backend — Unit tests faltando**
   - `tests/unit/test_fee_calculator.py`:
     - rental_value=0, negativo, muito grande
     - days_late=0, negativo
     - due_date no futuro
   - `tests/unit/test_ipca_service.py`:
     - Index fetch success/failure
     - Date edge cases
   - `tests/unit/test_rent_adjustment_service.py`:
     - Isolado do banco
     - Cálculos com IPCA/IGPM

2. **Backend — Integration tests**
   - Concurrent mark_paid test
   - Soft delete cascade test
   - Permission edge cases (tenant acessando dados de outro tenant)
   - Error response format validation

3. **Backend — Fix assertions**
   - Substituir `>=` por `==` em financial_dashboard tests onde valor exato é esperado
   - Adicionar fixtures com Factory Boy para dados dinâmicos

4. **Frontend — Component tests**
   - Criar pelo menos 5 testes de componentes:
     - DataTable (renderização, sorting)
     - ExpenseFormModal (validação, submit)
     - DailyTimeline (collapse, mark paid)
     - LoginPage (credential handling, error display)
     - Sidebar (navigation, active state)

5. **Frontend — MSW handler validation**
   - Adicionar validação básica nos handlers (CPF format, required fields)
   - Handlers devem retornar 400 para dados inválidos

6. **conftest.py — Fixtures compostas**
   - `building_with_apartment()`
   - `rented_lease()`
   - `person_with_credit_card()`

---

## Sessão 13: Feature Gaps — Quick Infrastructure

**Branch:** `feature/infra-improvements`
**Estimativa:** 2-3h
**Issues cobertos:** Infraestrutura para features futuras

### Tarefas:

1. **RBAC foundation**
   - Avaliar django-role-permissions ou django-guardian
   - Definir roles: admin, property_manager, owner, tenant
   - Criar Permission matrix document

2. **Mobile navigation fix**
   - Sidebar responsiva com hamburger menu em mobile
   - Sheet component para menu lateral em telas pequenas

3. **Celery setup**
   - Descomentar e configurar Celery no docker-compose.prod.yml
   - Mover PDF generation para task assíncrona
   - Mover email/WhatsApp notifications para tasks

---

## Ordem de Execução

```
Sessão 1: Security Settings          ← PRIMEIRO (blocking para tudo)
    ↓
Sessão 2: Security Auth              ← depende de S1
    ↓
Sessão 3: Security Infra             ← depende de S1
    ↓
Sessão 4: Data Integrity Models      ← independente (migration)
    ↓
Sessão 5: Signals & Cache            ← depende de S4 (models)
    ↓
Sessão 6: Transactions & Concurrency ← depende de S4, S5
    ↓
Sessão 7: Performance                ← depende de S4, S5, S6
    ↓
Sessão 8: Business Logic             ← independente
    ↓
Sessão 9: DevOps                     ← independente
    ↓
Sessão 10: Frontend Quality          ← independente
    ↓
Sessão 11: Code Quality              ← depende de S7 (performance refactors)
    ↓
Sessão 12: Testing                   ← ÚLTIMO (testa tudo)
    ↓
Sessão 13: Feature Infra             ← após tudo estabilizado
```

## Sessões Paralelizáveis

```
[Sessão 1] → [Sessão 2] → [Sessão 6]
         ↘ [Sessão 3]
[Sessão 4] → [Sessão 5] → [Sessão 7] → [Sessão 11]
[Sessão 8] (independente)
[Sessão 9] (independente)
[Sessão 10] (independente)
[Sessão 12] (após todas as outras)
[Sessão 13] (após S12)
```

**Estimativa total: 45-55h de implementação**

## Checklist de Validação Final

Após todas as sessões, verificar:
- [ ] `ruff check && ruff format --check` passa
- [ ] `mypy core/ condominios_manager/` passa
- [ ] `pyright` passa
- [ ] `python -m pytest` passa com coverage >= 60%
- [ ] `cd frontend && npm run lint && npm run type-check && npm run build` passa
- [ ] `cd frontend && npm run test:unit` passa
- [ ] Docker build funciona com Python 3.12
- [ ] docker-compose.prod.yml inicia com settings_production
- [ ] Health check endpoint responde
- [ ] CI pipeline passa sem continue-on-error
