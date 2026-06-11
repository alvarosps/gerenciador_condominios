# Plano P6.2 — Sincronização de documentação com a realidade

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P6 · **Branch sugerida:** `docs/sync-with-reality` · **Depende de:** idealmente apos P2–P5 (a doc deve refletir o estado final pos-fixes); pode rodar em paralelo com P6.1 e P6.3

## Objetivo

A documentacao do repo (CLAUDE.md raiz, README, `.claude/rules/*`, `.env*.example`, `tests/CLAUDE.md`, `frontend/CLAUDE.md`, `docs/STATUS.md`, `prompts/SESSION_STATE.md` + `ROADMAP.md` e headers de `docs/plans/`) divergiu da realidade do codigo: nao documenta o app `finances/` nem o `mobile/`, lista rotas de auth inexistentes, mantem o model `LeaseTenant` (DELETADO na migration 0004) e o recurso CRUD `dependents` (inexistente) como CRITICAL, tem `.env` templates dessincronizados de `settings.py`, README com flake8/black/isort e `DATABASE_URL`, valores de tag fee errados em `financial.md`, e estado de planos/roadmap desatualizado (features mergeadas marcadas como pendentes; planos executados como "EM REVISAO — nao executar", risco de re-rodar seeds nao-idempotentes). Este plano sincroniza **toda** a documentacao com o codigo atual, cria `docs/FINANCES.md` consolidando os invariantes do modulo novo, e estabelece a convencao de "marcar EXECUTADO no merge" para fechar o estado de roadmap/sessions/planos. Como `.claude/rules/*` e CLAUDE.md sao carregados como instrucoes do agente, documentacao errada faz o agente operar com premissas falsas — corrigi-la e pre-requisito de qualidade de todo o trabalho futuro.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MEDIO | CLAUDE.md raiz nao documenta o app `finances/` nem `mobile/` (arvore, modelo de dados, `/api/finances/*`) | `CLAUDE.md:7-21,23-51,102-113` | Adicionar `finances/` + `mobile/` na arvore, secao "Modelo de Dados — finances" e bloco de rotas `/api/finances/*` |
| MEDIO | `LeaseTenant`/`core_lease_tenant_details` documentado como CRITICAL "NAO renomear" mas o model foi **DELETADO** na migration 0004 (tabela nao existe) | `CLAUDE.md:79,117` · `.claude/rules/database.md` (secao M2M) | Remover todas as mencoes a `LeaseTenant`/`core_lease_tenant_details`; descrever o M2M real `Lease.tenants` (through auto) |
| MEDIO | `dependents` listado como recurso CRUD inexistente (nao ha router register; dependentes sao aninhados no `TenantSerializer`) | `CLAUDE.md:104` · `README.md:320` | Remover `dependents` da lista de CRUD; documentar que dependentes sao geridos via payload aninhado do Tenant; incluir `rent-adjustments` (CRUD real) |
| MEDIO | Rotas de auth erradas (`/api/token/`, `/api/auth/google/`) — reais sao `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/oauth/*` | `CLAUDE.md:105` · `README.md:288,301` · `.claude/rules/security.md:4` | Corrigir as 3 docs para as rotas reais + completar a allowlist de endpoints publicos |
| MEDIO | Secao do modulo financeiro legado do core nao marcada como DEPRECATED | `CLAUDE.md:31-40,110-113` | Marcar Person/Expense/RentPayment/cash-flow/daily-control/financial-dashboard como DEPRECATED (substituido por `finances/`) |
| MEDIO | `.env.example`: nome errado de var JWT correto mas faltam `DATABASE_URL`(N/A), `CELERY_BROKER_URL`, `TWILIO_*`, `AUTH_COOKIE_SAMESITE`; vars orfas `REDIS_PASSWORD`/`LOG_LEVEL`/comentario pyppeteer | `.env.example:40,176,219,228-233` | Sincronizar 1:1 com `config(...)` de `settings.py`; remover orfas; pyppeteer→Playwright |
| MEDIO | `.env.production.example`: vars JWT com nome errado (`JWT_ACCESS_TOKEN_LIFETIME` sem `_MINUTES`; `JWT_REFRESH_TOKEN_LIFETIME` sem `_DAYS`); faltam `CELERY_BROKER_URL`/`TWILIO_*`/`AUTH_COOKIE_SAMESITE`; vars orfas `BACKUP_*`/`HEALTH_*`/`USE_S3`/AWS | `.env.production.example:83-84,158-172` | Corrigir nomes JWT; adicionar vars reais; remover orfas nao lidas por `settings.py` |
| BAIXO | `frontend/.env.example` cita porta 6000 (real 4000) em instrucoes OAuth | `frontend/.env.example:43,47` | Trocar 6000→4000 nos exemplos de origin/callback do frontend |
| MEDIO | README com flake8/black/isort (→ruff), `npm run test` (→`test:unit`), `DATABASE_URL` local (→`DB_*`), runserver sem porta, backup `.backup`/`pg_restore` (→`.sql`/`restore_db.py`/`psql`), badges e estrutura sem `finances`/`mobile` | `README.md:5-12,65-74,143,175-193,222-253,271-280,352-381` | Reescrever README alinhado ao stack/comandos reais + `finances`+`mobile` |
| BAIXO | `tests/CLAUDE.md` cita cobertura 60% (real `--cov-fail-under` e maior; meta do projeto e 90%) e `-n auto` (config real difere) | `tests/CLAUDE.md:35-37` | Alinhar threshold/meta (90%) e flags do pytest ao `pytest.ini` real |
| BAIXO | `frontend/CLAUDE.md` sem `finances`/`financial`/portal `tenant`/`admin`/proxy `/api`/PWA | `frontend/CLAUDE.md:5-19,43-48` | Adicionar `finances/` (Condominio), marcar `financial/` DEPRECATED, documentar portal inquilino, admin, proxy same-origin e PWA/offline |
| MEDIO | `.claude/rules/architecture.md` so cobre `core/` (file-placement leva codigo de `finances/` para o lugar errado) | `.claude/rules/architecture.md:3-8,34-39` | Generalizar as camadas e o file-placement para `core/` **e** `finances/` |
| BAIXO | `coding-standards.md` cita Python 3.14 (PEP 649) mas `pyproject.toml` exige `>=3.12` | `.claude/rules/coding-standards.md:13` · `pyproject.toml:9` | Alinhar a versao citada ao `requires-python` real (3.12) |
| BAIXO | `.claude/rules/financial.md` tag fee R$50/R$80 errado (real R$20/R$40) e `max_digits=10` | `.claude/rules/financial.md:14,16` | Corrigir para R$20/R$40 (defaults `settings.py:501-502`) e nota de `max_digits` |
| MEDIO | `SESSION_STATE.md`/`ROADMAP.md`/headers de `docs/plans/` desatualizados (features mergeadas como pendentes; planos executados como "EM REVISAO — nao executar" → risco de re-rodar seed nao-idempotente) | `prompts/SESSION_STATE.md` · `prompts/ROADMAP.md` · `docs/plans/2026-06-08*`,`2026-06-09*` | Fechar status (convencao "EXECUTADO (PR/data) no merge"); marcar planos ja mergeados |
| BAIXO | `docs/STATUS.md` congelado em 2026-03-21 (sem finances/mobile/condo-utilities) | `docs/STATUS.md:1-30` | Atualizar para o estado real (finances no ar, condo-utilities seedado, legado em depreciacao) |
| MEDIO | Nao existe doc consolidado do `finances/` (LESSONS_LEARNED so cobre o legado) | (novo) `docs/FINANCES.md` | Criar `docs/FINANCES.md` com modelo de dados, invariantes monetarios, fechamento, RLS e API |

## Abordagem técnica

Documentacao-apenas: **nenhuma mudanca de codigo, migration ou dado**. Cada arquivo e editado para casar exatamente o codigo atual (verificado lendo os fontes — ver "Fatos verificados" abaixo). Ordem sugerida: fontes-de-verdade primeiro (CLAUDE.md, rules), depois templates de env, depois README, depois status/roadmap, por fim o doc novo `docs/FINANCES.md`.

### Fatos verificados no codigo (base das correcoes — nao readivinhar)

- **Auth real** (`condominios_manager/urls.py:56-66`): `POST /api/auth/token/`, `POST /api/auth/token/refresh/`, `GET /api/auth/me/`, `POST /api/auth/register/`, `POST /api/auth/logout/`, `GET/POST /api/auth/oauth/google/callback/`, `POST /api/auth/oauth/exchange/`, `GET /api/auth/oauth/status/`. Allauth em `/accounts/`. **NAO existem** `/api/token/` nem `/api/auth/google/`. Rotas WhatsApp/portal em `core/urls.py:106-134`.
- **`LeaseTenant` foi DELETADO** na migration `core/migrations/0004_add_validators_and_indexes.py:136-138` (`migrations.DeleteModel(name="LeaseTenant")`). Em `core/models.py` o M2M e simples: `tenants = models.ManyToManyField(Tenant, related_name="leases", ...)` (`core/models.py:640-642`) — **sem** `through=` e **sem** `db_table`. A unica ocorrencia de `lease_tenant` no codigo e o nome de indice nao relacionado `lease_tenant_date_idx` (`core/models.py:728`). O inquilino responsavel e `Lease.responsible_tenant` (FK).
- **`dependents` NAO e recurso CRUD**: `core/urls.py:46-82` registra `buildings, furnitures, apartments, tenants, leases, dashboard, templates, landlords, rules, persons, credit-cards, expense-categories, financial-settings, expenses, expense-installments, incomes, rent-payments, employee-payments, person-incomes, person-payments, financial-dashboard, cash-flow, daily-control, person-payment-schedules, expense-month-skips, month-advance, admin/proofs, admin/notifications, admin/users, devices, web-push, rent-adjustments`. **Nao ha** `dependents`. Dependentes sao criados/editados/removidos via payload aninhado do `TenantSerializer`. `rent-adjustments` (real) esta ausente da doc.
- **App `finances/` (rotas)** (`finances/urls.py:26-39`, montado em `/api/finances/`): `finance-categories, billing-accounts, bills, bill-skips, payments, installment-plans, installments, employees, reserves, reserve-movements, income-entries, condo-month-closes, finance-dashboard, finance-cash-flow`.
- **App `finances/` (models)** (`finances/models.py`): `Category, BillingAccount, Bill, BillLineItem, Payment, PaymentAllocation, BillSkip, InstallmentPlan, Installment, Employee, Reserve, ReserveMovement, IncomeEntry, CondoMonthClose, WaterBillStatement, ElectricityBillStatement` + enums (`BillBehavior, BillLifecycleState, BillingAccountState, BillingAccountType{WATER,ELECTRICITY,IPTU,INTERNET,GENERIC}, SupplyStatus, FundedFrom, InstallmentPlanState, EmployeePaymentType, ReserveMovementKind, CondoMonthCloseStatus`). `Condominium` e o tenancy-root (`Building.condominium` FK, migration 0048). `Bill` usa `SET_NULL` em fontes para nunca apagar historico; dinheiro via `Bill.objects.with_amounts(today)`; `BillLineItem.is_offset` armazenado POSITIVO e subtraido.
- **Env vars reais** (`condominios_manager/settings.py`, via `config(...)`): `SECRET_KEY, DEBUG, ALLOWED_HOSTS, DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_CONN_MAX_AGE, REDIS_URL, CACHE_TIMEOUT, CACHE_MIDDLEWARE_SECONDS, CORS_ALLOWED_ORIGINS, CORS_ALLOW_CREDENTIALS, PAGE_SIZE, JWT_ACCESS_TOKEN_LIFETIME_MINUTES, JWT_REFRESH_TOKEN_LIFETIME_DAYS, JWT_ROTATE_REFRESH_TOKENS, JWT_BLACKLIST_AFTER_ROTATION, JWT_ALGORITHM, ADMIN_GOOGLE_EMAILS, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, FRONTEND_URL, FRONTEND_AUTH_CALLBACK_PATH, CSRF_TRUSTED_ORIGINS, AUTH_COOKIE_SAMESITE, CHROME_EXECUTABLE_PATH, PDF_OUTPUT_DIR, PDF_GENERATION_TIMEOUT, DEFAULT_TAG_FEE_SINGLE(20.00), DEFAULT_TAG_FEE_MULTIPLE(40.00), LATE_FEE_PERCENTAGE, DAYS_PER_MONTH, TWILIO_ACCOUNT_SID/AUTH_TOKEN/WHATSAPP_FROM, TWILIO_TEMPLATE_VERIFICATION/RENT_ADJUSTMENT/GENERIC, VAPID_PUBLIC_KEY/PRIVATE_KEY/SUBJECT, CELERY_BROKER_URL`. **NAO existe** `DATABASE_URL`; `settings.py` NAO le `REDIS_PASSWORD`, `LOG_LEVEL`, `BACKUP_*`, `HEALTH_*`, `USE_S3`, `AWS_*`, `SENTRY_*`, `EMAIL_*`, `STATIC_ROOT`, `MEDIA_ROOT` (orfas nos templates — remover ou mover para "futuro/nao-lido").
- **Python**: `pyproject.toml:9` `requires-python = ">=3.12"`.
- **Tag fee real**: `settings.py:501-502` defaults `20.00`/`40.00` (CLAUDE.md:84 ja correto; `financial.md:14` errado).

### Passo 1 — CLAUDE.md raiz (fonte-de-verdade do agente)

1. **Arvore** (`CLAUDE.md:7-21`): adicionar `finances/` ("App Django do condominio — outflow/saldo/reserva/distribuicao; substitui o financeiro legado do core") e `mobile/` ("App Expo separado que consome `/api/`"). Manter os blocos `core/*` existentes.
2. **Modelo de Dados** (`CLAUDE.md:23-51`): (a) marcar o bloco "Modulo Financeiro" + "Reajuste/Locador/Contrato" do core como **DEPRECATED** (legado em depreciacao — ver P7; so corrigir bugs reais de dinheiro). (b) Adicionar bloco novo "Modulo Condominio (`finances/`)" listando `Condominium → Building`, `BillingAccount → Bill → BillLineItem`, `Payment → PaymentAllocation`, `InstallmentPlan → Installment`, `Employee`, `Reserve → ReserveMovement`, `IncomeEntry`, `CondoMonthClose` (snapshot mensal congelado), `Water/ElectricityBillStatement` (1:1 com Bill, so leituras), `BillSkip`. Apontar para `docs/FINANCES.md`.
3. **Restricoes Criticas** (`CLAUDE.md:79`): **remover** a linha `LeaseTenant ... core_lease_tenant_details`. Em `CLAUDE.md:117` (Migrations) remover a mesma frase.
4. **API Base** (`CLAUDE.md:102-113`): (a) corrigir Auth para as rotas reais (lista do passo "Fatos verificados"). (b) remover `dependents` da linha de CRUD; adicionar `rent-adjustments`. (c) marcar as linhas "Financeiro CRUD/Dashboard/Cash Flow/Controle Diario" como DEPRECATED. (d) adicionar bloco "Condominio (`finances/`) — `/api/finances/`" com os 14 recursos reais.
5. **Mixins** (`CLAUDE.md:53`): acrescentar `CondoMonthClose` e `BillSkip` a lista "Sem SoftDelete" se aplicavel (`CondoMonthClose` so tem AuditMixin; `BillSkip` so AuditMixin — confirmar em `finances/models.py:439,784`).

### Passo 2 — `.claude/rules/*`

1. **security.md:4**: trocar a allowlist publica para `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/oauth/google/callback/`, `/api/auth/oauth/exchange/`, `/api/auth/register/` e `/accounts/` (allauth). Remover `/api/token/`, `/api/auth/google/`.
2. **database.md** (secao "M2M Relationships"): **remover** a linha `LeaseTenant: db_table='core_lease_tenant_details'`. Descrever `Lease.tenants` (M2M auto) + `Lease.responsible_tenant` (FK). Manter Furniture↔Apartment/Tenant.
3. **architecture.md:3-8,34-39**: generalizar "Backend Layers" e "File Placement" para `core/` **e** `finances/` (ex.: "New business logic: `core/services/` **ou** `finances/services/`"; "New API endpoints: `core/views.py`/`core/viewsets/` **ou** `finances/viewsets/`"). Adicionar a regra documentada `core` NAO importa `finances` (dependencia unidirecional `finances → core`).
4. **coding-standards.md:13**: trocar "Python 3.14 — PEP 649" pela versao real. Como `requires-python>=3.12`, reescrever a regra de `from __future__ import annotations` sem afirmar 3.14 (manter a proibicao, justificando por convencao do projeto / import direto de tipos), ou citar a versao efetivamente usada — **nao** afirmar uma versao que o `pyproject` nao garante.
5. **financial.md:14,16**: tag fee → `R$20 (1 inquilino) / R$40 (2+)`; nota: campos monetarios variam (`max_digits=10` no legado patrimonial, `12` no financeiro/`finances`) — nao afirmar um valor unico. Marcar o arquivo como regra do **modulo legado** (paths no front-matter ja apontam para `core/services/*` legados).

### Passo 3 — `.env` templates (sincronizar 1:1 com `settings.py`)

1. **`.env.example`**: (a) trocar comentario "pyppeteer" (`:40`) por "Playwright (Chromium headless)". (b) adicionar bloco `TWILIO_*` (6 vars), `AUTH_COOKIE_SAMESITE=Lax`, `CELERY_BROKER_URL` (descomentado/documentado). (c) remover/realocar orfas nao lidas por `settings.py`: `REDIS_PASSWORD`, `LOG_LEVEL`, `STATIC_ROOT/MEDIA_ROOT` comentados — mover para uma secao "NAO lido por settings.py (referencia/futuro)" ou remover. As vars JWT ja estao corretas (`_MINUTES`/`_DAYS`) — manter.
2. **`.env.production.example`**: (a) corrigir `JWT_ACCESS_TOKEN_LIFETIME` → `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` e `JWT_REFRESH_TOKEN_LIFETIME=1440` → `JWT_REFRESH_TOKEN_LIFETIME_DAYS` (settings le **dias**, nao minutos — `1440` dias e absurdo; usar p.ex. `7`). (b) adicionar `TWILIO_*`, `AUTH_COOKIE_SAMESITE`, `CELERY_BROKER_URL`, `VAPID_*` (ja presente). (c) remover orfas nao lidas: `BACKUP_*`, `ENABLE_HEALTH_CHECKS/HEALTH_CHECK_PATH`, `USE_S3`/`AWS_*`, `SENTRY_*`, `EMAIL_*` — ou mover para secao "NAO lido por settings.py". Manter `DB_*` (settings usa campos, nao `DATABASE_URL`).
3. **`frontend/.env.example`**: trocar as portas `6000` por `4000` nos exemplos de origin/callback (`:43,47`) para casar o dev real (frontend em 4000).

### Passo 4 — README.md (reescrita alinhada)

1. **Badges** (`:5-12`): Python `3.12+`, Django `5.2`, PostgreSQL `17/18`; remover numeros de teste/cobertura fixos (apodrecem) ou substituir por "ver gate".
2. **Tech Stack / Testing** (`:46-66`): manter Django 5.2 + Playwright; remover contagens fixas de teste.
3. **Backend Setup** (`:85-111`): `uv` (nao `venv`/`pip`) conforme convencao do projeto; `runserver` → `python manage.py runserver` (porta 8008 documentada); `cp .env.example .env`.
4. **Env Vars** (`:139-157`): trocar `DATABASE_URL=...` por `DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`.
5. **Database Management** (`:160-193`): backup → `python scripts/backup_db.py` (gera `.sql`); restore → `python scripts/restore_db.py <dump> --yes`; substituir `pg_restore -c *.backup` por `psql`/`pg_dump ... -F p`; adicionar nota do sync prod→Supabase (`--schema=public --no-owner --no-acl`).
6. **Tests** (`:222-253`): backend `python -m pytest` + escopo; frontend `npm run test:unit` (nao `npm run test`).
7. **Code Quality / Linting** (`:271-280`): `ruff check && ruff format --check && mypy core/ && pyright` (remover flake8/black/isort); frontend `npm run lint && npm run type-check`.
8. **API docs** (`:288,301,320-329`): corrigir auth para `/api/auth/token/`; remover `dependents` de "Available Resources"; adicionar `finances`.
9. **Project Structure** (`:352-381`): adicionar `finances/`, `mobile/`, `prompts/`, `docs/`.
10. Remover "Development Guidelines: Follow PEP 8" (o projeto usa Ruff) e atualizar para o gate canonico.

### Passo 5 — `tests/CLAUDE.md` e `frontend/CLAUDE.md`

1. **tests/CLAUDE.md:35-37**: alinhar a config de `pytest.ini` real (ler `pytest.ini` antes de escrever os flags exatos `-n`/`--cov-fail-under`); a meta do projeto e **90%** de cobertura (memoria + roadmap) — corrigir "manter acima de 60%" para a meta real, citando que o `--cov-fail-under` do `pytest.ini` e o piso de CI (nao a meta).
2. **frontend/CLAUDE.md:5-19**: adicionar `app/(dashboard)/finances/` (sidebar "Condominio": `bills, categories, distribution, employees, income-entries, installment-plans, month-close, projection, reserve`); marcar `app/(dashboard)/financial/` (sidebar "Financas") como **DEPRECATED**; documentar `app/(dashboard)/admin/` (admin), portal do inquilino, o proxy same-origin `app/api/[...route]/route.ts` (`NEXT_PUBLIC_API_URL=/api` em prod) e PWA/offline (`app/sw.ts`, manifest, Serwist). Na secao "Modulo Financeiro (frontend)" (`:43-48`) marcar como legado e apontar para `finances/`.

### Passo 6 — Status / Roadmap / headers de planos

1. **Convencao** (documentar uma vez no topo do `ROADMAP.md` e `SESSION_STATE.md`): "Ao mergear um plano/feature, marcar `EXECUTADO (PR #…, data)` no header do doc e fechar a linha correspondente no `SESSION_STATE.md`. Planos ja mergeados NUNCA ficam como 'EM REVISAO — nao executar' (risco de re-rodar seed nao-idempotente)."
2. **SESSION_STATE.md**: fechar como **MERGEADO/EXECUTADO** as features ja no `master` (condo-utility-bills S56–64 — ja marcada concluida local; confirmar merge e anotar o seed PROD ja aplicado conforme MEMORY; rent-payment-calendar; mobile-pwa-offline; condo-finance S34–50). Onboarding S51–55 permanece "prompts escritos — nao executado" (esta correto).
3. **Headers de `docs/plans/`**: nos planos **ja executados/mergeados** (ex.: `2026-06-08-condo-utility-bills-parser-iptu-design.md`, `2026-06-09-condo-bills-fixes-and-utility-faturas-plan.md`, `2026-06-09-contract-pdf-prod-fix-plan.md`, `2026-06-04-*`, `2026-06-02-*`) trocar qualquer marca "EM REVISAO — nao executar" por `EXECUTADO (data)`; deixar **explicito** que os seeds (`seed_condo_utilities`, faturas agua/luz) **ja foram aplicados** (local+PROD) e NAO devem ser re-rodados cegamente (sao idempotentes por chave natural, mas a re-execucao deve ser consciente). Planos `2026-06-11-pXY-*` permanecem `PLANEJADO`.
4. **docs/STATUS.md**: atualizar `Ultima atualizacao` e o corpo: backend/frontend com `finances/` no ar + condo-utilities seedado; modulo financeiro legado do core em **depreciacao** (P7); proximos passos = executar o roadmap de remediacao `docs/plans/2026-06-11-audit-remediation-roadmap.md`.

### Passo 7 — `docs/FINANCES.md` (novo, consolidado)

Espelhar a profundidade de `docs/LESSONS_LEARNED.md` (que cobre so o legado), agora para o app `finances/`. Secoes:
- **Visao geral / por que existe** (substitui o financeiro pessoal do core; foco no caixa do condominio).
- **Modelo de dados** (lista de models do passo "Fatos verificados" + relacoes + `Condominium` tenancy-root + `Building.condominium`).
- **Invariantes monetarios**: dinheiro via `Bill.objects.with_amounts(today)` (nunca property Python); `quantize_money`/fronteira monetaria unica; `BillLineItem.is_offset` armazenado POSITIVO e subtraido; geracao mensal idempotente e race-safe; `today_sp()` (timezone SP, helper do app).
- **Fechamento mensal** (`CondoMonthClose`): snapshot congelado, "frozen figures win", invariante "snapshot nunca difere do dashboard on-read por 1 centavo"; cuidado com reopen→close em cascata (ver P2.3).
- **Contas tipadas + statements** (water/electricity/iptu/...): statements 1:1 so leituras; parser DMAE/CEEE em memoria sem anexar PDF; alerta IPTU (banner + push agregado SP-aware via `send_finance_alerts`).
- **Permissoes**: `FinancialReadOnly` (read autenticado, write so `is_staff`) em todos os viewsets.
- **RLS**: toda tabela nova habilita RLS na mesma migration (padrao 0047/0048; migrations `finances/0004–0006`).
- **Dependencia**: `core` NAO importa `finances`; `finances` pode importar `core`.
- **API**: os 14 recursos `/api/finances/*` + actions (`bills/{id}/pay/`, `update_with_lines/`, `parse_invoice/`, `condo-month-closes/{id}/close|reopen/`, `finance-dashboard/{overview,monthly_balance,iptu_alerts}`, `finance-cash-flow/projection`).
- **Apontar** `docs/FINANCES.md` em CLAUDE.md (secao "Documentacao") e linkar de volta o LESSONS_LEARNED como "legado".

## Arquivos a criar / modificar

- **CLAUDE.md** (modificar): arvore + `finances`/`mobile`; modelo de dados (legado DEPRECATED + bloco `finances`); remover `LeaseTenant`/`core_lease_tenant_details` (linhas 79 e 117); auth real; remover `dependents` e add `rent-adjustments`; bloco `/api/finances/*`; mixins; apontar `docs/FINANCES.md`.
- **README.md** (modificar): badges, setup `uv`, env `DB_*`, backup `.sql`/`restore_db.py`, tests `test:unit`, lint `ruff`, auth real, resources sem `dependents`, estrutura com `finances`/`mobile`.
- **.claude/rules/security.md** (modificar): allowlist de auth real.
- **.claude/rules/database.md** (modificar): remover `LeaseTenant`/`core_lease_tenant_details`; descrever M2M real.
- **.claude/rules/architecture.md** (modificar): generalizar camadas + file-placement para `core/`+`finances/`; regra `finances→core`.
- **.claude/rules/coding-standards.md** (modificar): versao Python alinhada a `>=3.12`.
- **.claude/rules/financial.md** (modificar): tag fee 20/40; marcar como regra do legado.
- **.env.example** (modificar): pyppeteer→Playwright; add `TWILIO_*`/`AUTH_COOKIE_SAMESITE`/`CELERY_BROKER_URL`; tratar orfas.
- **.env.production.example** (modificar): JWT `_MINUTES`/`_DAYS`; add `TWILIO_*`/`AUTH_COOKIE_SAMESITE`/`CELERY_BROKER_URL`; remover orfas.
- **frontend/.env.example** (modificar): portas 6000→4000.
- **tests/CLAUDE.md** (modificar): threshold/meta 90% + flags reais do `pytest.ini`.
- **frontend/CLAUDE.md** (modificar): `finances/` (Condominio), `financial/` DEPRECATED, admin, portal inquilino, proxy, PWA.
- **prompts/SESSION_STATE.md** (modificar): convencao + fechar features mergeadas.
- **prompts/ROADMAP.md** (modificar): convencao "EXECUTADO no merge".
- **docs/STATUS.md** (modificar): estado real + proximos passos = roadmap de remediacao.
- **docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md**, **2026-06-09-condo-bills-fixes-and-utility-faturas-plan.md**, **2026-06-09-contract-pdf-prod-fix-plan.md** (e demais ja mergeados) (modificar): header → `EXECUTADO (data)`; nota anti-re-seed.
- **docs/FINANCES.md** (criar): doc consolidado do modulo novo.

Sem arquivos de teste (mudanca documental). Ver "Gate de verificacao" para as checagens automatizaveis.

## TDD — cenários de teste

Documentacao nao tem teste unitario, mas ha verificacoes automatizaveis (links + grep de anti-padroes). Adicionar/rodar como parte do gate:

- **docs_no_stale_leasetenant**: `rg -n "core_lease_tenant_details|LeaseTenant" CLAUDE.md README.md .claude/ docs/` retorna **zero** (exceto historico imutavel de migration). — prova a remocao do achado.
- **docs_auth_routes_real**: `rg -n "/api/token/|/api/auth/google/" CLAUDE.md README.md .claude/rules/security.md` retorna **zero**; `rg "/api/auth/token/"` presente nos 3.
- **docs_no_dependents_crud**: `rg -n "dependents`" na lista de recursos CRUD de CLAUDE.md/README nao aparece como recurso (so como conceito aninhado).
- **docs_env_in_sync**: para cada var citada em `.env.example`/`.env.production.example`, ela aparece em `config("...")` de `settings.py` **ou** esta numa secao explicitamente marcada "NAO lido por settings.py"; e cada `config("X")` de `settings.py` (sem default obrigatorio sensivel) aparece nos templates. (checagem manual assistida por grep; opcional: script `scripts/check_env_template_sync.py` — YAGNI se feito a mao).
- **docs_finances_documented**: `rg -n "finances" CLAUDE.md` e `rg -n "FINANCES.md"` presentes; `docs/FINANCES.md` existe e cita os 16 models + 14 rotas.
- **docs_links_valid**: todos os caminhos relativos citados (ex.: `docs/FINANCES.md`, `docs/LESSONS_LEARNED.md`, `prompts/SESSION_STATE.md`) existem no disco.
- **docs_python_version_consistent**: `rg "3\.14" .claude/rules/coding-standards.md` retorna zero (ou nao afirma versao que conflita com `pyproject:9`).
- **docs_tag_fee_correct**: `rg "R\$?50|R\$?80" .claude/rules/financial.md` (no contexto de tag fee) retorna zero; `20`/`40` presentes.

(Frontend/MSW: N/A — sem mudanca de codigo executavel.)

## Migrations / dados

N/A. Plano puramente documental — nenhuma migration, nenhuma alteracao de schema, nenhuma alteracao de dado vivo. Os planos de seed (`seed_condo_utilities`, faturas agua/luz) sao apenas **descritos** como ja executados; este plano NAO re-roda seed algum.

## Constraints (o que NÃO fazer)

- **Nenhuma mudanca de codigo, migration, schema ou dado.** Se durante a escrita surgir a tentacao de "consertar tambem o codigo", isso pertence a outro plano (P1–P5) — apenas documentar a realidade atual.
- **Nao inventar** rotas/models/vars: tudo o que entrar na doc deve ter sido lido no fonte (urls/models/settings). Em duvida, ler de novo, nao readivinhar.
- **Nao fixar numeros que apodrecem** (contagem de testes, % de cobertura exata, numero da ultima migration) — usar "ver gate"/"rode showmigrations".
- **Nao refatorar o modulo legado** nem remove-lo aqui — apenas marca-lo DEPRECATED (a remocao e P7).
- **Nao remover** o `LESSONS_LEARNED.md` (segue valido para o legado) — apenas linka-lo como "legado" e criar o `FINANCES.md` para o novo.
- **Sem supressao** de lint em qualquer snippet de codigo embutido na doc; sem `from __future__ import annotations` em exemplos.
- **Nao reescrever** `.claude/rules/design-principles.md`, `coding-standards` gate, ou `database.md`/`security.md` alem do estritamente listado (RLS-sem-policy e o estado correto — nao "consertar").

## Critérios de aceite (binários)

- [ ] `rg -n "core_lease_tenant_details|name=\"LeaseTenant\"" CLAUDE.md README.md .claude/ docs/ prompts/` = 0 (fora de `core/migrations/`).
- [ ] `rg -n "/api/token/|/api/auth/google/" CLAUDE.md README.md .claude/rules/security.md` = 0; `/api/auth/token/` presente nos 3.
- [ ] `dependents` nao aparece como recurso CRUD em CLAUDE.md nem README; `rent-adjustments` aparece em CLAUDE.md.
- [ ] CLAUDE.md tem `finances/` e `mobile/` na arvore, secao de modelo de dados `finances` e bloco `/api/finances/*` (14 recursos), e o financeiro legado marcado DEPRECATED.
- [ ] `.env.example` e `.env.production.example`: toda var citada existe em `config(...)` de `settings.py` ou esta marcada "NAO lido por settings.py"; nomes JWT do prod corrigidos (`_MINUTES`/`_DAYS`); `TWILIO_*`/`AUTH_COOKIE_SAMESITE`/`CELERY_BROKER_URL` presentes; pyppeteer→Playwright.
- [ ] `frontend/.env.example` nao cita porta 6000 em exemplos de origin/callback.
- [ ] README sem flake8/black/isort/`DATABASE_URL`/`npm run test` (sem `:unit`)/`pg_restore -c *.backup`; com `uv`, `DB_*`, `restore_db.py`, `test:unit`, `ruff`, porta 8008, `finances`+`mobile`.
- [ ] `coding-standards.md` nao afirma Python 3.14 conflitando com `pyproject` (`>=3.12`).
- [ ] `financial.md` tag fee = R$20/R$40.
- [ ] `architecture.md` cobre `core/` e `finances/` em camadas e file-placement.
- [ ] `tests/CLAUDE.md` reflete a meta 90% e os flags reais do `pytest.ini`.
- [ ] `frontend/CLAUDE.md` documenta `finances/` (Condominio), `financial/` DEPRECATED, admin, portal inquilino, proxy, PWA.
- [ ] `docs/FINANCES.md` existe, lista os 16 models + 14 rotas + invariantes monetarios + fechamento + RLS + permissoes, e e referenciado por CLAUDE.md.
- [ ] `SESSION_STATE.md`/`ROADMAP.md` tem a convencao "EXECUTADO no merge"; features mergeadas nao estao como pendentes; nenhum plano mergeado fica "EM REVISAO — nao executar".
- [ ] `docs/STATUS.md` atualizado (data + estado real + proximos passos = roadmap de remediacao).
- [ ] Todos os caminhos relativos citados nas docs existem no disco.

## Gate de verificação

Mudanca documental — o gate de codigo (ruff/mypy/pyright/pytest/eslint) **nao se aplica** por nao haver codigo alterado, mas deve ser confirmado que nada de codigo mudou:

```bash
# 1. Confirmar que NADA de codigo/migration/dado mudou (so .md / .env*.example):
git diff --name-only | rg -v '\.(md|example)$' ; # deve sair VAZIO

# 2. Anti-padroes resolvidos (todos devem retornar 0):
rg -n "core_lease_tenant_details" CLAUDE.md README.md .claude/ docs/ prompts/
rg -n "/api/token/|/api/auth/google/" CLAUDE.md README.md .claude/rules/security.md
rg -n "flake8|black|isort|DATABASE_URL" README.md
rg -n "3\.14" .claude/rules/coding-standards.md

# 3. Presencas exigidas (todas devem ter match):
rg -n "/api/finances/|finances/|mobile/" CLAUDE.md
rg -n "FINANCES.md" CLAUDE.md
test -f docs/FINANCES.md

# 4. Links relativos validos (script ou checagem manual):
#    para cada `docs/...`, `prompts/...`, `frontend/...` citado, confirmar `test -f`.

# 5. (Opcional) Sanidade do markdown: rodar o prettier do frontend so nos .md, se configurado,
#    ou um linter de markdown disponivel — sem introduzir dependencia nova (YAGNI).
```

Como P6.2 idealmente roda **apos** P2–P5, reconfirmar, antes de fechar, que as rotas/vars/comandos descritos continuam batendo com o codigo (re-grep em `urls.py`/`settings.py`) — se algum fix anterior mudou um contrato, a doc deve refletir o estado final.

## Handoff

- **Commit sugerido** (unico, documental):
  ```
  docs: sync all docs with reality (finances/mobile, real auth routes, env templates)

  - CLAUDE.md: add finances/ + mobile/ to tree + data model + /api/finances/*;
    mark legacy core-financial DEPRECATED; remove deleted LeaseTenant + nonexistent
    dependents CRUD; add rent-adjustments; fix auth routes
  - README: ruff (drop flake8/black/isort), test:unit, DB_* (drop DATABASE_URL),
    runserver :8008, restore_db.py/.sql, finances+mobile
  - .claude/rules: real auth allowlist (security), generalize layers to finances
    (architecture), Python >=3.12 (coding-standards), tag fee R$20/R$40 (financial),
    drop LeaseTenant (database)
  - .env*.example: sync with settings.config(); fix JWT prod var names; add
    TWILIO_*/AUTH_COOKIE_SAMESITE/CELERY_BROKER_URL; pyppeteer->Playwright; ports 6000->4000
  - tests/CLAUDE.md + frontend/CLAUDE.md: 90% target, finances (Condominio) + PWA + portal
  - STATUS/SESSION_STATE/ROADMAP + executed plan headers: mark EXECUTED-on-merge;
    stop marking merged plans "EM REVISAO"
  - new docs/FINANCES.md: consolidated invariants of the new condo-finance module

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- **Atualizar estado**: ao mergear, anotar `EXECUTADO (PR #…, 2026-…)` no header **deste** plano e no `audit-remediation-roadmap.md` (linha P6.2), e marcar a linha de docs no "Gate global de pronto-para-producao".
- **O proximo plano assume**: a documentacao agora reflete o estado pos-fixes — P6.3 (CI/build) pode incluir `finances/` e `pyright` no gate de CI citando as docs ja corrigidas; P7 (remocao do legado) usa as marcacoes DEPRECATED como inventario do que deletar; agentes futuros leem CLAUDE.md/rules corretas (sem premissas falsas de `LeaseTenant`/`dependents`/rotas).
