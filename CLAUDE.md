# Condominios Manager

Sistema de gestão de imóveis para locação no Brasil — Django 5.2 + DRF (backend), Next.js 14 + React 18 (frontend), PostgreSQL (Supabase 17 em prod, 18 local).

## Arquitetura

```
core/                    # Django app principal (models, serializers, views, services)
core/services/           # Camada de serviços (contract, dashboard, fees, dates, templates)
core/viewsets/           # Viewsets especializados (template_views.py)
core/cache.py            # Redis caching (CacheManager, @cache_result decorator)
core/signals.py          # Django signals — invalidação automática de cache
core/validators/         # Validação CPF/CNPJ
core/middleware/         # Request/response logging, slow request warnings (>1s)
core/templates/          # Contract template HTML + backups/
finances/                # App do CONDOMÍNIO (outflow/saldo/reserva/distribuição) — substitui o
                         #   financeiro pessoal legado do core. Ver docs/FINANCES.md. finances → core (unidirecional)
mobile/                  # App Expo (React Native) separado que consome /api/ (ver project memory)
contracts/               # PDFs gerados por prédio
frontend/                # Next.js 14 App Router (ver frontend/CLAUDE.md)
tests/                   # pytest test suite (ver tests/CLAUDE.md)
scripts/                 # backup_db, restore_db, deploy, generate_metrics, setup_windows
condominios_manager/     # Django settings
```

## Modelo de Dados

```
Building (street_number unique) → Apartment (number unique per building)
Apartment → Lease (OneToOne) → Tenant (responsible FK + tenants M2M auto — Lease.tenants)
Tenant (cpf_cnpj unique) → Dependent (FK)
Furniture ↔ Apartment (M2M), Furniture ↔ Tenant (M2M)

--- Módulo Condomínio (`finances/`) — ATUAL. Ver docs/FINANCES.md ---
Condominium (tenancy-root, core/models.py) → Building.condominium (FK)
BillingAccount (tipada: water/electricity/iptu/internet/generic) → Bill → BillLineItem (is_offset POSITIVO, subtraído)
Payment → PaymentAllocation; InstallmentPlan → Installment; Employee; Reserve → ReserveMovement
IncomeEntry; CondoMonthClose (snapshot mensal congelado); Water/ElectricityBillStatement (1:1 c/ Bill, só leituras); BillSkip
Dinheiro via Bill.objects.with_amounts(today) (nunca property Python); today_sp() (timezone SP)

--- Módulo Financeiro PESSOAL (LEGADO/DEPRECATED — só corrigir bugs de dinheiro; remoção em P7; ver docs/LESSONS_LEARNED.md) ---
Person → CreditCard (1:N), PersonIncome (1:N), PersonPayment (1:N), EmployeePayment (1:N)
Expense → ExpenseInstallment (1:N), vinculado opcionalmente a Person, CreditCard, Building, ExpenseCategory
ExpenseCategory → subcategorias (self FK via parent)
Income, RentPayment, FinancialSettings (singleton)
Apartment.owner → Person (kitnets com owner = receita repassada, não do condomínio)
Lease.prepaid_until, Lease.is_salary_offset — casos especiais de aluguel
Expense.is_offset — descontos (subtraídos do total da pessoa, SEMPRE filtrar com is_offset=False)
Expense.end_date — data fim para gastos fixos recorrentes
ExpenseMonthSkip — marca despesa como não cobrada em mês específico (sem SoftDelete)

--- Reajuste / Locador / Contrato ---
Lease → RentAdjustment (1:N) — reajustes anuais; IPCAIndex (índice IBGE mensal, sem mixins) alimenta o reajuste
Landlord — locador (singleton, get_active()); ContractRule — regras de condomínio exibidas nos contratos
PersonPaymentSchedule (1:N ← Person) — cronograma de pagamentos por pessoa/mês
MonthSnapshot — snapshot imutável do fechamento mensal (AuditMixin, SEM SoftDelete)

--- Mobile / Auth / Notificações ---
Lease → PaymentProof (1:N) — comprovante PIX do inquilino (status pending/approved/rejected)
Notification, DeviceToken (Expo push), WhatsAppVerification, OAuthExchangeCode (TTL 60s) — app mobile + auth
```

**Mixins (maioria dos models):** `AuditMixin` (created/updated_at/by), `SoftDeleteMixin` (is_deleted, deleted_at/by). Sem SoftDelete: `IPCAIndex`, `MonthSnapshot`, `FinancialSettings`, `Notification`, `DeviceToken`, `WhatsAppVerification`, `OAuthExchangeCode`, `ExpenseMonthSkip`, `CondoMonthClose`, `BillSkip`.
- `Model.objects.all()` exclui deletados; `.with_deleted()` inclui; `.deleted_only()` só deletados

## Comandos

```bash
# Backend
python manage.py runserver                    # http://localhost:8008
python -m pytest                              # Todos os testes (parallel, reuse-db)
python -m pytest tests/unit/                  # Só unit tests
python -m pytest --cov=core --cov-report=html # Com coverage
ruff check && ruff format --check              # Lint/format (replaces black, isort, flake8)
mypy core/                                     # Type checking with django-stubs
pyright                                        # Strict type checking (pyrightconfig.json)

# Frontend (cd frontend/)
npm run dev                                   # http://localhost:4000
npm run build                                 # Production build
npm run test:unit                             # Vitest
npm run lint && npm run type-check            # ESLint + TypeScript
```

## Restrições Críticas

- IMPORTANT: Serializers usam padrão dual — FK read com nested (`building = BuildingSerializer(read_only=True)`), write com `_id` (`building_id = PrimaryKeyRelatedField(write_only=True, source='building')`)
- IMPORTANT: M2M segue mesmo padrão — read com nested list, write com `_ids`
- IMPORTANT: `Lease.tenants` é M2M auto (sem `through`/`db_table`); `Lease.responsible_tenant` é o inquilino responsável (FK). O antigo model `LeaseTenant`/`core_lease_tenant_details` foi DELETADO na migration 0004 — não existe mais.
- IMPORTANT: PDF generation requer Chrome instalado — path detection Windows-specific em `contract_service.py`
- CRITICAL: Default querysets excluem soft-deleted records — usar `with_deleted()` quando necessário
- IMPORTANT: Redis cache com invalidação automática via signals — ao mudar models/signals, verificar impacto no cache
- IMPORTANT: `CacheManager.invalidate_pattern("<prefix>*")` (chaves hifenizadas) — cache invalida automaticamente em save/delete via signals; receivers do core mapeiam model→prefixos reais em `_CORE_MODEL_CACHE_PREFIXES` (P4.2; o antigo `invalidate_model`/`*Model*` foi removido por nunca casar)
- Tag fee: R$20 (1 tenant) / R$40 (2+), não-reembolsável (a tag é de propriedade do inquilino; perdeu, compra outra a R$20/un.) — `FeeCalculatorService.calculate_tag_fee` em `core/services/fee_calculator.py` (valores via `settings.DEFAULT_TAG_FEE_SINGLE/MULTIPLE`)
- Late fee: 5% ao dia × (rental_value ÷ 30) × days_late — lógica em `fee_calculator.py`
- Furniture no contrato = Apartment furniture − Tenant furniture
- PDFs salvos em: `contracts/{building_number}/contract_apto_{apt_number}_{lease_id}.pdf`

## Princípios de Design — OBRIGATÓRIO

- CRITICAL: **SOLID, DRY, KISS, YAGNI, Clean Code** — sem workarounds, sem quick wins, sem backwards-compat, sem re-exports, refatoração sempre completa (todos os consumidores atualizados).
- Fonte canônica (mandatória, não repetida aqui): `.claude/rules/design-principles.md`.

## Convenções

- Backend: Ruff (100 chars, replaces black+isort+flake8+pylint) + mypy strict (django-stubs) — enforced via pre-commit (run `pre-commit install` once after cloning)
- Frontend: ESLint strict-type-checked + Prettier + TypeScript strict (noUncheckedIndexedAccess) — lint-staged, run by the root pre-commit hook (`frontend-lint-staged`), not husky
- CRITICAL: Never use `# noqa`, `# type: ignore`, or `eslint-disable` comments — always fix the actual code
- Validação brasileira: CPF (11 dígitos), CNPJ (14 dígitos), moeda R$ 1.500,00, data DD/MM/YYYY
- Estado civil: Solteiro(a), Casado(a), Divorciado(a), Viúvo(a), União Estável

## API Base: `/api/`

- CRUD para: `buildings`, `apartments`, `tenants`, `leases`, `furnitures`, `rent-adjustments` (dependentes são geridos via payload aninhado do `TenantSerializer` — NÃO há recurso `dependents`)
- Auth: `/api/auth/token/` (login), `/api/auth/token/refresh/`, `/api/auth/me/`, `/api/auth/register/`, `/api/auth/logout/`, `/api/auth/oauth/google/callback/`, `/api/auth/oauth/exchange/`, `/api/auth/oauth/status/`; WhatsApp OTP `/api/auth/whatsapp/{request,verify}/`; allauth em `/accounts/`
- Lease actions: `generate_contract/`, `calculate_late_fee/`, `change_due_date/`
- Templates: `/api/templates/current/`, `save/`, `backups/`, `restore/`, `preview/`
- Dashboard: `financial_summary/`, `late_payment_summary/`, `lease_metrics/`, `tenant_statistics/`, `building_statistics/`
- Export: `/api/{resource}/export/excel/`, `/api/{resource}/export/csv/`
- **Condomínio (`finances/`) — `/api/finances/` (ATUAL):** `finance-categories`, `billing-accounts`, `bills`, `bill-skips`, `payments`, `installment-plans`, `installments`, `employees`, `reserves`, `reserve-movements`, `income-entries`, `condo-month-closes`, `finance-dashboard`, `finance-cash-flow`. Actions: `bills/{id}/{pay,suspend}/`, `bills/{bulk_pay,generate_month,create_with_lines,parse_invoice}/`, `condo-month-closes/{id}/{close,reopen}/`, `finance-dashboard/{overview,monthly_balance,iptu_alerts,overdue,combined_calendar}`, `finance-cash-flow/projection`.
- Financeiro PESSOAL (LEGADO/DEPRECATED — remoção em P7): `persons`, `credit-cards`, `expense-categories`, `expenses`, `expense-installments`, `incomes`, `rent-payments`, `employee-payments`, `person-incomes`, `person-payments`, `financial-settings`; `financial-dashboard/*`; `cash-flow/*`; `daily-control/*`.

## Migrations

Sequenciais. Rode `python manage.py showmigrations core` para o estado atual — NÃO fixar números aqui (apodrecem). Hooks bloqueiam edição de migrations existentes; crie novas via `makemigrations`. **Backup antes de qualquer migrate destrutivo:** `python scripts/backup_db.py`.

## Env Vars

- Backend `.env`: `SECRET_KEY`, `DEBUG`, `DB_PORT` (default 5432, atualmente 5433), `GOOGLE_CLIENT_ID/SECRET`
- Frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8008/api`
- CORS: `localhost:4000`, `localhost:6000`

## Produção / Supabase (regras canônicas: `.claude/rules/database.md` + `security.md`)

- Prod = Supabase (projeto `kaukiwhbmvnjjekodcmq`, us-west-2, Postgres 17); local = Postgres `localhost:5433` DB `condominio` (PG 18). Ambos conectam como role `postgres` (`rolbypassrls=true`).
- CRITICAL: **RLS habilitado em TODAS as tabelas `public`** (Supabase expõe `public` via Data API a `anon`/`authenticated`; o app só usa o backend Django, que faz bypass). RLS sem policies = deny-all aos roles da API — o aviso `rls_enabled_no_policy` (INFO) é o estado correto. Toda tabela nova habilita RLS na mesma migration (padrão: `core/migrations/0047_enable_row_level_security.py`).
- Backup/sync prod→local: `pg_dump "<uri>" --schema=public --no-owner --no-acl` → `scripts/restore_db.py <dump> --yes` (mirror exato; NÃO rodar `migrate` depois). O MCP do Supabase NÃO faz `pg_dump` nem expõe a senha — pegar a connection string no Dashboard → Connect.

## Skills — Plugin vs Projeto

**Quando um skill do plugin Superpowers for invocado, SEMPRE carregar também o skill equivalente do projeto (`.claude/skills/`).** Os skills do plugin são genéricos; os do projeto têm regras específicas deste sistema (Django+DRF, serializers dual pattern, soft delete, cache invalidation, mock policy). Ambos devem ser seguidos — as regras do projeto têm precedência em caso de conflito.

| Plugin skill | Skill do projeto para também carregar |
| --- | --- |
| `superpowers:brainstorming` | `/brainstorming` (architecture gate com regras Django/DRF) |
| `superpowers:writing-plans` | `/prompt-writing` (TDD, context engineering, exemplar index) |
| `superpowers:executing-plans` | `/prompt-session` (TDD + audit + SESSION_STATE.md) |
| `superpowers:verification-before-completion` | `/audit` (verifica completude contra plano) |
| `superpowers:test-driven-development` | TDD integrado em `/prompt-session` e `/new-feature` |

## Documentação do Módulo Financeiro

- **Condomínio (ATUAL):** `docs/FINANCES.md` — modelo de dados, invariantes monetários, fechamento, RLS, permissões e API do app `finances/`
- **Pessoal (LEGADO/DEPRECATED):** `docs/LESSONS_LEARNED.md` — contexto completo do negócio, todas as regras, armadilhas, e decisões arquiteturais do módulo legado do `core`
- Design doc: `docs/plans/2026-03-21-financial-module-design.md`
- Prompts de sessão: arquivos numerados em `prompts/` (ver `SESSION_STATE.md` para o intervalo/estado atual)
- Estado das sessões: `prompts/SESSION_STATE.md`
- Dados iniciais: `scripts/data/financial_data_template.json`
- Script importação: `scripts/import_financial_data.py` (suporta `--dry-run` e `--clear-first`)
- Parser faturas Itaú: `scripts/parse_itau_fatura.py`
