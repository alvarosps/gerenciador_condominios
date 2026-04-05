# Full Application Review — 2026-04-05

## Overview

4 rounds of review, 16 specialized agents, full codebase coverage (~15,000+ lines backend, ~7,000+ frontend, 52 backend test files, 326 frontend test files).

**Total issues found: ~88 verified** (after removing 3 false positives)

---

## 1. CRITICAL (11 issues)

### SEC-01: JWT token lifetime 365 dias + token em URL/localStorage
- **Onde:** `condominios_manager/settings.py:291-318`, `core/auth.py:136-140`, `frontend/lib/api/client.ts:16-20`, `frontend/store/auth-store.ts:77-88`
- **O quê:** Access/refresh token com lifetime padrão de 365 dias. Token rotation desabilitada. OAuth callback passa tokens como query parameters. Frontend armazena em localStorage (vulnerável a XSS).
- **Fix:** Access=15min, refresh=7d, rotation=True, blacklist=True. Tokens via httpOnly cookies. Remover tokens da URL.

### SEC-02: SECRET_KEY com fallback hardcoded público
- **Onde:** `condominios_manager/settings.py:31`
- **O quê:** SECRET_KEY tem valor default no código-fonte. Se .env não configurado, qualquer pessoa pode forjar tokens JWT.
- **Fix:** Remover default, falhar se não setado.

### SEC-03: DEBUG default=True
- **Onde:** `condominios_manager/settings.py:36`
- **O quê:** `DEBUG = config("DEBUG", default=True, cast=bool)`. Se env var não setada, produção roda com DEBUG=True.
- **Fix:** `default=False`.

### DEV-01: docker-compose.prod.yml usa settings ao invés de settings_production
- **Onde:** `docker-compose.prod.yml:57, 116, 143`
- **O quê:** `DJANGO_SETTINGS_MODULE=condominios_manager.settings` ao invés de `settings_production`. Security hardening (HSTS, SSL redirect) ignorado.
- **Fix:** Trocar para `condominios_manager.settings_production`.

### DEV-02: Dependências de produção ausentes
- **Onde:** `requirements.txt` vs `condominios_manager/settings_production.py`
- **O quê:** `sentry-sdk`, `whitenoise`, `django-storages`, `boto3` importados em settings_production mas ausentes de requirements.txt e pyproject.toml.
- **Fix:** Adicionar a requirements.txt E pyproject.toml.

### DEV-03: docker-compose.yml env var DJANGO_SECRET_KEY vs SECRET_KEY
- **Onde:** `docker-compose.yml:44` vs `condominios_manager/settings.py:31`
- **O quê:** Docker passa `DJANGO_SECRET_KEY`, settings lê `SECRET_KEY`. Usa hardcoded default.
- **Fix:** Alinhar nomes.

### SEC-04: Path traversal no storage.py
- **Onde:** `core/infrastructure/storage.py:163, 190, 219, 261`
- **O quê:** file_path não validado contra `../`. Possível ler/escrever fora do base_path.
- **Fix:** Adicionar validação com `resolve()` e `startswith()`.

### DAT-01: Person CASCADE delete apaga histórico financeiro
- **Onde:** `core/models.py:906, 1080, 1151, 1177`
- **O quê:** CreditCard, PersonIncome, EmployeePayment, PersonPayment usam CASCADE. Deletar Person apaga todo histórico.
- **Fix:** Trocar para PROTECT.

### PERF-01: N+1 queries no financial dashboard (120+ queries/request)
- **Onde:** `core/services/financial_dashboard_service.py` (múltiplas linhas)
- **O quê:** 12 queries separadas por Person. 10 persons = 120+ queries.
- **Fix:** Aggregates condicionais em query única.

### PERF-02: LeaseViewSet filtra datas em Python
- **Onde:** `core/views.py:253-289`
- **O quê:** Carrega TODOS os leases em memória para filtrar por status.
- **Fix:** `annotate()` com date arithmetic no banco.

### DEV-04: Python 3.11 no Docker vs requires-python>=3.12
- **Onde:** `Dockerfile:3,25`, `.github/workflows/ci.yml:35,81,174`
- **O quê:** pyproject.toml requer 3.12+, Docker e CI usam 3.11.
- **Fix:** Atualizar para python:3.12-slim.

---

## 2. HIGH (22 issues)

### SEC-05: Missing rate limiting em auth endpoints
- **Onde:** Token, token/refresh, whatsapp/verify
- **Fix:** django-ratelimit ou DRF throttling.

### SEC-06: Missing Content-Security-Policy header
- **Onde:** `condominios_manager/settings_production.py`
- **Fix:** Adicionar CSP via django-csp ou Nginx.

### SEC-07: Shell injection em docker-entrypoint.sh
- **Onde:** `docker-entrypoint.sh:29-30`
- **O quê:** Env vars não escapadas no Python inline.
- **Fix:** Usar variáveis de ambiente via os.environ no Python, não interpolação shell.

### DAT-02: Missing Expense/ExpenseInstallment cache invalidation signals
- **Onde:** `core/signals.py` — ausência de handlers
- **O quê:** Nenhum cache invalidado quando expenses são criados/modificados/deletados.
- **Fix:** Adicionar post_save/post_delete handlers.

### DAT-03: Race conditions em 6 mark_paid endpoints (sem select_for_update)
- **Onde:** `core/services/daily_control_service.py:256-268, 291-303, 306-318`, `core/viewsets/financial_views.py:193-201, 353-364, 523-533`
- **Fix:** `select_for_update()` + `transaction.atomic`.

### DAT-04: generate_installments() sem transaction
- **Onde:** `core/viewsets/financial_views.py:204-253`
- **Fix:** Wrap em `@transaction.atomic`.

### DAT-05: Soft delete NÃO cascata para filhos (Apartment→Leases, Building→Apartments)
- **Onde:** `core/models.py:147-170` (SoftDeleteMixin.delete)
- **Fix:** Override delete() em Apartment e Building para cascade soft-delete.

### DAT-06: Soft delete unique constraints inconsistentes
- **Onde:** RentPayment, ExpenseInstallment, EmployeePayment, CreditCard usam unique_together sem filtro is_deleted=False
- **Fix:** Migrar para UniqueConstraint com condition.

### DAT-07: activate_pending_adjustments() sem transaction
- **Onde:** `core/services/rent_adjustment_service.py:113-164`
- **Fix:** Wrap em `@transaction.atomic` + `select_for_update()`.

### DAT-08: Month advance rollback só deleta pagamentos não-pagos
- **Onde:** `core/services/month_advance_service.py:150-157`
- **Fix:** Track auto-created records separately ou deletar todos.

### DAT-09: Import script sem rollback em falha parcial
- **Onde:** `scripts/import_financial_data.py:73-99`
- **Fix:** Wrap em `transaction.atomic()`.

### PERF-03: N+1 queries em cash_flow_service (owner repayments, stipends)
- **Onde:** `core/services/cash_flow_service.py:156-203`
- **Fix:** `select_related("apartment__owner")`, `select_related("person")`.

### PERF-04: N+1 em contract_service.calculate_lease_furniture()
- **Onde:** `core/services/contract_service.py:126-140`
- **Fix:** `prefetch_related('apartment__furnitures', 'tenants__furnitures')`.

### PERF-05: Missing indexes
- **Onde:** `core/models.py`
- **O quê:** `Apartment.is_rented`, `Expense(person, expense_type)`, `Expense(person, expense_date)`, `ExpenseInstallment(expense, due_date, is_paid)`
- **Fix:** Migration com AddIndex.

### DEV-05: CI usa black/isort/flake8 mas projeto usa ruff
- **Onde:** `.github/workflows/ci.yml:87-101`
- **Fix:** Substituir por ruff check + ruff format.

### DEV-06: CI continue-on-error em testes frontend e mypy
- **Onde:** `.github/workflows/ci.yml:106, 137`
- **Fix:** Remover continue-on-error.

### DEV-07: mypy.ini referenciado no CI não existe
- **Onde:** `.github/workflows/ci.yml:105`
- **Fix:** `--config-file=pyproject.toml` e testar todo o projeto.

### DEV-08: JWT env var name mismatch (.env.example vs settings.py)
- **Onde:** `.env.example:62` vs `condominios_manager/settings.py:295`
- **Fix:** Alinhar nomes de variáveis.

### DEV-09: Coverage threshold mismatch (pytest.ini 90% vs CI 60%)
- **Onde:** `pytest.ini:26` vs `.github/workflows/ci.yml:61`
- **Fix:** Unificar threshold.

### DEV-10: Node.js 18 no CI (deveria ser 20+)
- **Onde:** `.github/workflows/ci.yml:121, 152`
- **Fix:** Atualizar para node 20.

### FE-01: Token refresh race condition
- **Onde:** `frontend/lib/api/client.ts:38-64`
- **Fix:** Implementar refresh queue com promise deduplication.

### FE-02: Cookie max-age (1 ano) vs JWT expiry mismatch
- **Onde:** `frontend/lib/api/hooks/use-auth.ts:50-54`
- **Fix:** Alinhar cookie max-age com JWT expiry.

---

## 3. MEDIUM (35 issues)

### SEC-08: CORS config inclui ports de dev sem validação de ambiente
- **Onde:** `condominios_manager/settings.py:210-216`

### SEC-09: Missing Referrer-Policy header
- **Onde:** `condominios_manager/settings_production.py`

### SEC-10: HSTS desabilitado no Nginx
- **Onde:** `nginx/conf.d/condominios.conf:39-40`

### SEC-11: Swagger/Redoc sempre habilitado em produção
- **Onde:** `condominios_manager/urls.py:35-41`

### SEC-12: Missing CSRF/Session cookie security settings
- **Onde:** `condominios_manager/settings.py`

### SEC-13: Redis sem senha em produção (default vazio)
- **Onde:** `docker-compose.prod.yml:32`

### SEC-14: Permissions — IsTenantOrAdmin sem check de authenticated
- **Onde:** `core/permissions.py:74-102`

### DAT-10: Missing CHECK constraints no banco (valores negativos possíveis)
- **Onde:** Todos os DecimalField monetários

### DAT-11: Missing clean() em RentPayment, EmployeePayment, CreditCard
- **Onde:** `core/models.py`

### DAT-12: PersonPaymentSchedule.get_schedules_for_month não filtra soft deletes
- **Onde:** `core/services/person_payment_schedule_service.py:187-192`

### DAT-13: Race condition em MonthAdvanceService (idempotency bypass)
- **Onde:** `core/services/month_advance_service.py:74-80`

### DAT-14: Person payment schedule bulk_configure sem transaction
- **Onde:** `core/services/person_payment_schedule_service.py:128-142`

### DAT-15: Lease service transfer não valida tenant IDs existem
- **Onde:** `core/services/lease_service.py:37-38`

### BIZ-01: date.today() vs timezone.now().date() em 9 arquivos
- **Onde:** daily_control_service, rent_adjustment_service, date_calculator, fee_calculator, financial_dashboard_service, cash_flow_service, ipca_service, lease_service, serializers

### BIZ-02: fee_calculator sem validação de rental_value <= 0
- **Onde:** `core/services/fee_calculator.py:28-43`

### BIZ-03: WhatsApp service sem rate limiting
- **Onde:** `core/services/whatsapp_service.py:40-69`

### BIZ-04: Notification service ignora falhas silenciosamente
- **Onde:** `core/services/notification_service.py:71-79`

### BIZ-05: Notification N queries para N admins
- **Onde:** `core/services/notification_service.py:90-102`

### PERF-06: Float precision loss (Decimal→float) em projeções
- **Onde:** `core/services/cash_flow_service.py:597-639`

### PERF-07: Missing service-level caching no financial dashboard
- **Onde:** `core/services/financial_dashboard_service.py`

### PERF-08: Cache over-broad invalidation
- **Onde:** `core/signals.py` — Building update invalida TODOS Apartments

### PERF-09: Serializer payloads inflados (LeaseSerializer inclui TenantSerializer completo)
- **Onde:** `core/serializers.py`

### PERF-10: DecimalField max_digits inconsistente (10 vs 12) para campos monetários
- **Onde:** `core/models.py`

### FE-03: Auth store setToken() não atualiza isAuthenticated
- **Onde:** `frontend/store/auth-store.ts`

### FE-04: Floating-point arithmetic em currency no frontend
- **Onde:** `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx:369-372`

### FE-05: Date manipulation via string substring
- **Onde:** `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx:436`

### FE-06: Error boundary faltando no dashboard layout
- **Onde:** Missing `app/(dashboard)/error.tsx`

### FE-07: Error details (stack trace) expostos em produção
- **Onde:** `frontend/components/shared/error-boundary.tsx:50-54`

### FE-08: Missing conditional validation em Zod schemas (.refine())
- **Onde:** `frontend/lib/schemas/expense.schema.ts`

### FE-09: Missing date format validation em schemas
- **Onde:** `frontend/lib/schemas/person-payment.schema.ts:8`

### FE-10: Query invalidation overly broad
- **Onde:** `frontend/lib/api/hooks/use-leases.ts:89-94`

### FE-11: Nested state updates no daily page (setMonth + setYear)
- **Onde:** `frontend/app/(dashboard)/financial/daily/page.tsx:61-79`

### FE-12: Missing focus trap em modais
- **Onde:** Expense edit modal e outros

### FE-13: Missing aria-expanded em collapse buttons
- **Onde:** `frontend/app/(dashboard)/financial/daily/_components/daily-timeline.tsx:441`

### DEV-11: Health check endpoint /health/ não existe
- **Onde:** `condominios_manager/urls.py` (ausência), `docker-compose.prod.yml:74`, `nginx/conf.d/condominios.conf:50`

---

## 4. LOW (~20 issues)

### DEV-12: Chromium no container de produção (+200MB)
### DEV-13: collectstatic roda a cada restart
### DEV-14: JsonFormatter path errado em logging_config.py
### DEV-15: Frontend staticPageGenerationTimeout muito agressivo (1s)
### DEV-16: Management command send_scheduled_notifications sem error handling no loop
### BIZ-06: Temp file cleanup edge case em contract_service
### BIZ-07: WhatsApp template variables não validadas
### BIZ-08: PIX merchant name truncation silenciosa
### BIZ-09: Brazilian phone validator não enforça '9' em mobile
### BIZ-10: CPF/CNPJ validator retorna "" ao invés de None para vazio
### BIZ-11: Due day validation faltando em PersonPaymentSchedule bulk_configure
### BIZ-12: Lease service transfer não valida validity_months
### PERF-11: Pagination max_page_size=10000 no backend
### QUAL-01: 500 linhas DRY violation nos _collect_* methods
### QUAL-02: Páginas frontend de 400-600 linhas (SRP)
### QUAL-03: 19 form modals duplicados no frontend
### QUAL-04: financial_dashboard_service.py com 91KB
### TEST-01: IPCAService e FeeCalculatorService sem unit tests
### TEST-02: Frontend zero component tests
### TEST-03: MSW mocks não validam dados
### TEST-04: Assertions com >= ao invés de ==

---

## 5. FALSE POSITIVES (Removidos)

| Claim | Resultado |
|-------|-----------|
| CRC16 bug no pix_service | **CORRETO** — algoritmo validado |
| SoftDeleteMixin.delete() não cascata | **FUNCIONA** para Expense (override existe) |
| .update() no signal causa cache stale | **INTENCIONAL** — cache invalidado por signal separado |

---

## 6. FEATURE GAPS (Mercado Brasileiro 2026)

### Must-Have
- Portal do Inquilino (self-service)
- Integração PIX/Boleto (Pix Automático 2026)
- WhatsApp Automation
- DIMOB Report Export (obrigatório por lei)
- Mobile navigation fix

### Should-Have
- Assinatura digital (ClickSign)
- Portal do Proprietário
- IPCA/IGPM automático
- Reconciliação bancária
- RBAC granular

### Nice-to-Have
- Gestão de manutenção
- Tenant screening
- Integração portais (ZAP/OLX)
- Integração contábil
