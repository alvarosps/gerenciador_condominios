# Fable Audit — Findings

## STATUS PÓS-FASE 2 (2026-07-13, branch audit/fase-2-correcoes @ 835359c)

**CORRIGIDOS (14 lotes, 16 commits):** B1-B19 (todos os backend confirmados exceto deferidos abaixo), F1-F12, U1-U9, U11, P1-P2, P4-P6, P8-P11, A1, A3, A7, I3-I11, T1-T5, D2, D3, D5, D6, + 2 falhas vitest do baseline. Detalhes e evidência de verificação: `audit/verification-log.md`.

**DEFERIDOS (decisão registrada, não são "esquecidos"):**
| Item | Motivo | Destino |
|---|---|---|
| D1 next 14→16 | upgrade major breaking (5 CVEs) | projeto dedicado pós-audit |
| D4 xlsx | sem fix upstream; troca por exceljs é projeto | pós-audit |
| A2/P7.1 remoção financeiro legado | bloqueado por paridade finances/ + mobile | roadmap P7 |
| A5 branch 202 + A6 endpoints órfãos | workstream Celery/contract-PDF + fluxos planejados | plano 2026-06-09 |
| A8 kebab-case actions | renomear quebraria mobile/PWA (fora do escopo) | junto com P3 mobile |
| I1 Celery broker real + I2 S3/Supabase Storage | exigem infra/credenciais fora do repo | OPS (render.yaml já preparado) |
| P3 tela moderação, P7 composer avisos, U10 central notificações | telas NOVAS | Fase 4 |
| Mobile (24 achados) | fora do escopo por decisão do usuário | roadmap P3 |

--- Snapshot original da Fase 1 abaixo ---

Baseline: master `f0a1323` (P4+P5+P6 mergeados, 2026-07-12). Escopo: backend + frontend web (mobile fora).
Fonte incremental: `docs/plans/2026-07-10-full-audit-report.md` (backend confirmado com quórum; bloco frontend/portal/infra/testes re-verificado nesta auditoria).

## Status da coleta

- [x] Dependências (backend limpo; frontend 29 vulns — ver §D)
- [x] Estática backend: ruff check LIMPO, ruff format LIMPO, pyright LIMPO, mypy core/+finances/ LIMPO (118 arquivos)
- [x] Testes backend: **2600/2600 passed, 0 warnings, coverage 92.35%** (exit 0, ~5min28)
- [x] Frontend: lint LIMPO, type-check LIMPO, build OK (49 rotas, shared 89.1 kB); vitest **943/945 — 2 falhas**: `combined-calendar-section.test.tsx` (teste sensível a data, previsto no P8 do roadmap) e `convert-deferred-dialog.test.tsx` (act warning); warnings: 3× DialogContent sem aria-describedby, 3× act()
- [x] Re-verificação: Consistência de API (8/8 em escopo CONFIRMADOS; 3 mobile-only fora — ver §A)
- [x] Re-verificação: Frontend admin — correção (12/12 CONFIRMADOS — ver §F)
- [x] Re-verificação: Frontend admin — UX (11/11 CONFIRMADOS — ver §U)
- [x] Re-verificação: Portal do inquilino (10/10 CONFIRMADOS — ver §P)
- [x] Re-verificação: Infra/deploy (9 CONFIRMADOS + 2 parcialmente corrigidos — ver §I)
- [x] Re-verificação: Testes + Docs (4 CONFIRMADOS, 3 JÁ CORRIGIDOS por P5/P6, 1 parcial — ver §T)

## D. Dependências (2026-07-12)

Backend (pip-audit): **0 vulnerabilidades, 0 major atrás** ✅

Frontend (npm audit): **29 vulnerabilidades — 5 critical, 14 high, 8 moderate, 2 low**

| # | Sev | Pacote | Problema | Fix |
|---|-----|--------|----------|-----|
| D1 | 🔴 | next 14.2.14 | 5 advisories críticos (authorization bypass GHSA-7gfc-8cq8-jh5f, middleware SSRF, cache key confusion, DoS server actions, dev origin) | 16.2.10 (breaking, 2 majors) |
| D2 | 🔴 | vitest 3.2.4 | GHSA-5xrq-8626-4rwp arbitrary file read/exec (dev-only) | 3.2.6+ |
| D3 | 🟠 | axios 1.12.2 | 25 CVEs (SSRF NO_PROXY bypass, proto pollution auth bypass, DoS) | 1.18.1 |
| D4 | 🟠 | xlsx | proto pollution + ReDoS — **sem fix upstream** | trocar lib (exceljs) ou aceitar risco |
| D5 | 🟡 | form-data, linkify-it, picomatch, rollup, vite, ws, minimatch | high transitivas | npm audit fix |
| D6 | 🟡 | dompurify, follow-redirects, markdown-it, postcss, yaml, happy-dom, js-yaml | moderate | npm audit fix (happy-dom breaking) |

Outdated (major): next 14→16, react 18→19, antd 5→6, eslint 8→10, typescript 5→7, vitest 3→4, lucide-react 0→1, react-day-picker 9→10, happy-dom 16→20, jsdom 27→29, @types/node 22→26.

## F. Frontend admin — correção (re-verificados 2026-07-12, 12/12 CONFIRMADOS)

| # | Sev | Arquivo:linha | Achado |
|---|-----|---------------|--------|
| F1 | 🔴 | `frontend/app/(dashboard)/financial/expenses/details/_components/expense-edit-modal.tsx:251-256,281-286` | due_dates via `new Date(iso)`+`setMonth`+`toISOString` — drift de data em meses curtos/UTC-3 |
| F2 | 🔴 | `expense-edit-modal.tsx:232,253-267,316-317` | Criação parcelada não-atômica (1 POST + N POSTs) + catch genérico induz retry duplicado |
| F3 | 🟠 | `daily-timeline.tsx:55-57` + cópia em `day-detail-drawer.tsx:60-62`; `daily-balance-chart.tsx:45` | `isOverdueExit`/`isFuture` parseiam YYYY-MM-DD com `new Date()` — vence-hoje vira "Atrasado" (e função duplicada, DRY) |
| F4 | 🟠 | `quick-payment-modal.tsx:54`; `person-payment-form-modal.tsx:60`; `person-income-form-modal.tsx:65`; `expense-edit-modal.tsx:275` | `payment_date` default `new Date().toISOString()` (UTC) — pagamento noturno cai no dia seguinte |
| F5 | 🟠 | `use-daily-control.ts:102-107` | `useMarkItemPaid` não invalida expenseInstallments/incomes/personPayments/Schedules |
| F6 | 🟠 | `financial/expenses/details/page.tsx:98-101` | `handleSaved` não invalida expenseInstallments/cashFlow/dailyControl pós-rebuild |
| F7 | 🟠 | `use-month-advance.ts:196-199,220-223` | advance/rollback não invalidam employeePayments/Schedules/rentPayments/expenses/dailyControl |
| F8 | 🟠 | `use-leases.ts:142-145,313-316,333-336` | patch/transfer/terminate não invalidam rentCalendar nem dashboard |
| F9 | 🟠 | `use-financial-settings.ts:27-29` | settings só invalida financialSettings — dashboards stale |
| F10 | 🟠 | 26 ocorrências `} catch {` em 20 arquivos de `app/(dashboard)` (ex.: `tenant-lease-modal.tsx:289-291`) | Catches genéricos descartam mensagem de erro do backend |
| F11 | 🟠 | `components/layouts/main-layout.tsx:27-33` | fetch `/auth/me/` sem `.catch` — falha deixa user nulo para sempre |
| F12 | 🟡 | `lib/api/client.ts:22,29,34` (3× eslint-disable, viola CRITICAL); 0 `parseList`; `tenant-lease-modal.tsx:255,283` | Deferidos P4.3: unwrap heurístico, sem parseList compartilhado, lease+dependente não-atômico |

## U. Frontend admin — UX (re-verificados 2026-07-12, 11/11 CONFIRMADOS)

| # | Sev | Arquivo:linha | Achado |
|---|-----|---------------|--------|
| U1 | 🟠 | `finances/month-close/page.tsx:87-95`; `finances/viewsets/crud_views.py:749` | Impossível fechar mês pela 1ª vez (botão só em linha `open`, que nunca existe antes do 1º close) |
| U2 | 🟠 | `mobile-nav.tsx:37-39`; `sidebar.tsx:129-132,161-162` | MobileNav fecha Sheet ao tocar em grupo — submenus inacessíveis no celular |
| U3 | 🟡 | `sidebar.tsx:45-59`; `lib/utils/constants.ts` | `/financial/month-advance` órfã (sem link/ROUTES/busca) |
| U4 | 🟡 | grep só `use-users.ts` + a página; `header.tsx:110-115` | `/admin/users` órfã — CRUD completo sem nenhum link |
| U5 | 🟡 | `lease-table-columns.tsx:300-424` | 8 botões-ícone/linha, width 240 + `fixed:'right'` inócuo, Excluir sem hierarquia |
| U6 | 🟡 | `data-table.tsx:34-35` (declarados; 0 leituras) | Props `fixed`/`align` da Column nunca aplicados |
| U7 | 🟡 | `expense-detail-table.tsx:31-32`; `overdue-section.tsx:60-61` | Tabelas 7-9 colunas sem overflow-x-auto |
| U8 | 🟡 | `sidebar.tsx:50/56/55/58` vs `:65-71` vs `:123-126` | Grupos "Financeiro"×"Condomínio" com filhos homônimos + 2 conceitos de fechamento |
| U9 | ⚪ | `sidebar.tsx:230` | "API Documentation" em inglês |
| U10 | ⚪ | `header.tsx:72-82` | Sino de notificações morto (sem onClick) |
| U11 | ⚪ | `sidebar.tsx:43,156-165` | Grupos não auto-expandem na rota ativa |

## I. Infra/deploy (re-verificados 2026-07-12: 9 CONFIRMADOS, 2 parciais)

| # | Sev | Arquivo:linha | Achado |
|---|-----|---------------|--------|
| I1 | 🔴 | `settings.py:526-528`; `core/views.py:428` | Celery eager sem broker — generate_contract roda Chromium no worker gunicorn (OOM em prod) |
| I2 | 🔴 | `settings_production.py:73-83` | USE_S3=False — PDFs de contrato + comprovantes PIX em disco efêmero do Render (somem a cada deploy) |
| I3 | 🟠 | comandos existem; sem render.yaml/Procfile/CELERY_BEAT | Crons de notificação sem schedule versionado — alertas nunca disparam se não configurados no dashboard |
| I4 | 🟠 | `settings.py:127,138,242` | Throttling fail-open + prod sem REDIS_URL — rate limit de auth (10/min) nunca aplicado |
| I5 | 🟠 | `settings_production.py:107-114` | Override de DATABASES OPTIONS descarta `sslmode=require` |
| I6 | 🟡 | `logging_config.py`; `logging_middleware.py:18-19`; `settings_production.py:195-216` | logging_config morto; loggers access/performance sem handler |
| I7 | 🟡 | só `render_build.sh` versionado | Deploy Render não versionado (start command/env só no dashboard) |
| I8 | 🟡 | residual: DATABASE_URL/ADMIN_EMAIL/SERVER_EMAIL/APP_VERSION ausentes dos examples | PARCIALMENTE corrigido no P6.2 (TWILIO/AUTH_COOKIE_SAMESITE documentados) |
| I9 | 🟡 | residual: LOG_LEVEL/REDIS_PASSWORD/BACKUP_*/HEALTH_CHECK_PATH mortos; JWT prod hardcoded `settings_production.py:295-300` | PARCIALMENTE corrigido (JWT names + CELERY_RESULT_BACKEND anotados) |
| I10 | ⚪ | `settings_production.py:271-274,290-292` | DEFAULT_RENDERER_CLASSES atribuído 2× |
| I11 | ⚪ | `settings_production.py:11,17` | Supressões inline (`# pyrefly: ignore`, `# noqa: F403`) violam regra CRITICAL |

## A. Consistência de API (re-verificados 2026-07-12: 8/8 em escopo CONFIRMADOS)

| # | Sev | Arquivo:linha | Achado |
|---|-----|---------------|--------|
| A1 | 🟠 | `global-search.tsx:47-52`; `core/views.py:94-106,146-191,109-122,394-405` | Busca global manda `?search=` a 5 endpoints; só Tenant filtra — resultados sem relação com o termo |
| A2 | 🟠 | `urls.py:70-72`; `core/urls.py:58-71`; `finances/urls.py:26-39` | Financeiro legado (core) e novo (finances) 100% ativos em paralelo; frontend consome ambos (P7.1 pendente) |
| A3 | 🟠 | `core/pagination.py:16-18` (cap 500); `client.ts:19-36` descarta count/next; 29× `page_size:10000` em 28 hooks | Truncamento silencioso >500 itens; `LargePageNumberPagination` só em Bills |
| A4 | 🟡 | 149 sites `{"error"}` em 17 arquivos; consumidores `.error` hardcoded (`contract-template/page.tsx:82,111,145`; `auth/callback/page.tsx:52`) | Shape de erro dividido vs regra DRF `detail` (sweep foi DROPPED como test-locked — decisão registrada, violação persiste) |
| A5 | 🟡 | `core/views.py:437-441`; 0 matches `tasks/` em frontend; `use-leases.ts:158-176` | Branch 202+task_id do generate_contract sem consumidor; frontend trata 202 como sucesso |
| A6 | 🟡 | `rule_views.py:144`; `core/views.py:963`; `crud_views.py:382`; `core/urls.py:109`; `urls.py:54` | 5 endpoints órfãos (rules/active, activate_pending, bulk_pay, set-password, tasks/status) |
| A7 | 🟡 | `CLAUDE.md:119`; `architecture.md:27`; 0 rotas export no backend | Docs prometem `/export/excel|csv/` inexistentes (export real é client-side em `use-export.ts`) |
| A8 | ⚪ | `web_push_views.py:32`, `notification_views.py:55`, `tenant_views.py:197,403,518`, `month_advance_views.py:133` | 6 actions kebab-case vs regra de underscores |

## T. Testes + Docs (re-verificados 2026-07-12)

| # | Sev | Veredito | Achado |
|---|-----|----------|--------|
| T1 | 🔴 | CONFIRMADO | `change_due_date` com `new_due_day == due_day` cobra ~1 mês de taxa (`fee_calculator.py:150`, `core/views.py:549-568`); branch de igualdade sem nenhum teste |
| T2 | 🟡 | CONFIRMADO | `test_rent_adjustment.py:90,155,317,397,416` depende do relógio real (sem freeze_time) — flake estrutural |
| T3 | 🟡 | CONFIRMADO (reduzido 30+→11) | `vi.mock` de hooks internos em 11 arquivos legado/admin (P6.1 migrou finances p/ MSW) |
| T4 | 🟡 | CONFIRMADO | `SESSION_STATE.md:16,134,139` desatualizado (seed PROD feito; S51 mergeada) |
| T5 | 🟡 | PARCIAL | README saneado no P6.2, mas `docs/STATUS.md:3` congelado em 2026-03-21 |
| T6 | ⚪ | JÁ CORRIGIDO | HTTP real ao IBGE em testes (P5.1 tirou fetch do request path) |
| T7 | ⚪ | JÁ CORRIGIDO | Mock interno em test_tenant_auth_api (agora patcheia fronteira Twilio) |
| T8 | ⚪ | JÁ CORRIGIDO | Tag fee R$50/80 em rules/financial.md (agora R$20/40) |

## P. Portal do inquilino (re-verificados 2026-07-12: 10/10 CONFIRMADOS)

| # | Sev | Arquivo:linha | Achado |
|---|-----|---------------|--------|
| P1 | 🔴 | `core/viewsets/auth_views.py:203-210`; `use-tenant-auth.ts:37-41`; `middleware.ts:56,68` | Login web OTP quebrado: verify não seta cookies HttpOnly, frontend lê `responseData.user` inexistente → loop de redirect |
| P2 | 🟠 | `client.ts:24-36`; `use-tenant-payments.ts:35-36`; `use-tenant-notifications.ts:21-24` | Unwrap paginado quebra histórico de pagamentos e notificações do tenant (`data.results` vira undefined) |
| P3 | 🟠 | `proof_views.py:32-98` (backend pronto); 0 UI web; `sw.ts:46-49` push cai na home | Sem tela web de moderação de comprovantes |
| P4 | 🟠 | `use-tenant-payments.ts:64` único uso; `proof/page.tsx:197,225` useState local; `core/urls.py:118-127` sem GET list | `/tenant/payments/proof` órfã + lista de enviados some no reload (sem endpoint de listagem) |
| P5 | 🟠 | `proof/page.tsx:93,124-130` (`type="month"`); `core/serializers.py:1344-1376` (DateField) | Upload web de comprovante sempre 400 ('YYYY-MM' vs DateField) |
| P6 | 🟠 | `proof_review_service.py:38-46` | Aprovar comprovante NÃO cria RentPayment nem chama toggle — admin tem que registrar manualmente |
| P7 | 🟡 | `core/models.py:2029` (choice morto); 0 produtores; `tenant/page.tsx:44` promete comunicados | `admin_notice` sem endpoint/UI de composição |
| P8 | 🟡 | `tenant_views.py:106-125` (lease condicional); `use-tenant-portal.ts:13-28` (não-opcional); `tenant/page.tsx:73,84`; `profile/page.tsx:99-102` | Home/Perfil crasham para inquilino sem lease ativa |
| P9 | 🟡 | `auth_views.py:112,115-120,122`; `whatsapp_service.py:21,26,59-61`; `exceptions.py:33-41` | Falha Twilio vira 500 e queima rate limit (create antes do send) |
| P10 | 🟡 | `profile/page.tsx:56-127`; `profile_views.py:26-73`; `auth_views.py:194-198`; `tenant-layout.tsx:41-43` | Perfil read-only (sem editar telefone do OTP); user OTP sem nome → header vazio |
| P11 | ⚪ | `tenant/contract/page.tsx:39-46`; `tenant_views.py:118` (`contract_generated` disponível) | Card 'contrato.pdf' com check verde estático mesmo sem contrato |

## B. Backend — confirmados com quórum na auditoria 2026-07-10 (não re-verificados: nenhuma remediação executada desde então; apenas P5/P6 mergeados, que não tocam estes itens)

Fonte detalhada: `docs/plans/2026-07-10-full-audit-report.md` §4 + roadmap P0.3/P1/P2/P6/P7. Itens-chave:

| # | Sev | Arquivo:linha | Achado |
|---|-----|---------------|--------|
| B1 | 🔴 | `core/views.py:134` (e buildings/furnitures) | Inquilino autenticado lê portfólio inteiro + PII de proprietários via `/api/apartments/` |
| B2 | 🔴 | `core/authentication.py:22` | Cookie-JWT sem validação CSRF, `SameSite=None` em prod |
| B3 | 🔴 | `finances/services/bill_payment_service.py:69` | pay/unpay/bulk_pay só checam `competence_month` — pagamento retrodatado muda caixa de mês FECHADO |
| B4 | 🔴 | (report §4 ALTA) | Deletar/cancelar/suspender conta PAGA não bloqueado — Payment/ReserveMovement órfãos contando no caixa |
| B5 | 🔴 | `finances/viewsets/installment_payroll_views.py:32` | InstallmentPlan criado pela API não materializa Installments (casca inerte) |
| B6 | 🔴 | `core/services/rent_adjustment_service.py:57,243` | Reajuste bloqueado/oculto para leases auto-renovadas (admin nunca alertado) |
| B7 | 🟠 | `core/viewsets/device_views.py:51` | DeviceToken permite apropriar push token de outro usuário |
| B8 | 🟠 | `finances/viewsets/crud_views.py:748`; `bill_generation_service.py:68,317` | Furos de guard de mês fechado (IncomeEntry destroy/update; generate_month; Bill de parcela órfã) |
| B9 | 🟠 | `installment_plan_service.py:110` | convert_deferred parcela `amount_total` em vez de `amount_remaining` (cobrança em dobro) |
| B10 | 🟠 | `reserve_service.py:84`; `finances/models.py:240`; `condo_balance_service.py:123`; `condo_projection_service.py:159` | Reserva/agregados: withdraw com saldo agregado; with_amounts confia no cascade; visão por prédio mista; projeção ignora Bills futuras |
| B11 | 🟠 | `core/views.py:489,492`; `fee_calculator.py:143,150` | Multa/taxas com data UTC + ignora prepaid/salary-offset/effective_rental_value; taxa de ~1 mês com dia igual (=T1) |
| B12 | 🟠 | `rent_adjustment_service.py:131`; `send_scheduled_notifications.py:60,110` | Reajuste/notificações em UTC; lembrete enviado para aluguel já pago |
| B13 | 🟠 | `tenant_views.py` (PIX) | PIX do portal usa `rental_value` cru (errado com reajuste pendente/prepago) |
| B14 | 🟠 | (report §4) | Soft-delete de Tenant responsável por lease ativa não bloqueado |
| B15 | 🟡 | `financial_views.py:200`; `financial_dashboard_service.py:62`; `model_validators.py:100`; `expense_service.py:93` | Legado: defaults UTC persistidos, "hoje" misto, date.today(), arredondamento última parcela |
| B16 | 🟡 | `financial_dashboard_service.py:902,744,382,138`; `month_advance_service.py:205`; `rent_schedule_service.py:191`; `dashboard_views.py:146`; `finances/models.py:317` | Perf: waterfall por pessoa, N+1s, scan duplo, monthly_balance O(n²), índices faltantes |
| B17 | 🟡 | `expense_service.py:117`; `signals.py:74,86`; `cache.py:187,207,212`; `finances/apps.py:18` | Cache: bulk_create sem invalidação; Tenant→finance-*; Lease/Apt/Building→financial-dashboard-*; invalidação fora de on_commit; fallback zera throttle; versão hardcoded; ready() engole falha |
| B18 | 🟡 | `core/views.py:415` + `settings_production.py:111` | Ligar broker Celery quebraria generate_contract/task_status; sslmode descartado (=I5) |
| B19 | 🟡 | (report §4 BAIXA) | transfer_lease sem validar apartment_id (500/soft-deleted aceito); lease >10 anos ineditável (full_clean); portal escolhe lease arbitrária (.first()) |

## Consolidação — contagens (achados ABERTOS, escopo backend+frontend web)

| Bloco | 🔴 | 🟠 | 🟡 | ⚪ | Total |
|-------|----|----|----|----|-------|
| B. Backend confirmado 07-10 (§4 do report: 6 ALTA + 31 MÉDIA + 25 BAIXA) | 6 | ~26 | ~30 | — | 62 |
| A. Consistência de API | — | 3 | 4 | 1 | 8 |
| F. Frontend correção | 2 | 9 | 1 | — | 12 |
| U. Frontend UX | — | 2 | 6 | 3 | 11 |
| P. Portal do inquilino | 1 | 5 | 4 | 1 | 11 |
| I. Infra/deploy | 2 | 3 | 4 | 2 | 11 |
| T. Testes/Docs (abertos) | 1 | — | 4 | — | 5 |
| D. Dependências | 2 | 2 | 2 | — | 6 |
| Novos (bateria 2026-07-12): 2 falhas vitest + 3 aria-describedby + 3 act() | — | — | 2 | — | 2 |
| **Total aberto** | **14** | **~50** | **~57** | **7** | **~128** |

Fechados nesta re-verificação: T6/T7/T8 (JÁ CORRIGIDOS por P5.1/P6.1/P6.2), I8/I9 parciais, 1 REFUTADO na auditoria original (Dependent.cpf_cnpj). Mobile (24 achados) fora do escopo desta auditoria por decisão do usuário.

## Gates (2026-07-12, master f0a1323)

Backend: ruff ✅ · ruff format ✅ · mypy core+finances ✅ · pyright ✅ · pytest 2600/2600, cov 92.35%, 0 warnings ✅
Frontend: eslint ✅ · tsc ✅ · build ✅ (49 rotas, shared 89.1 kB) · vitest **943/945 ❌** (2 falhas: combined-calendar date-sensitive; convert-deferred act)
Dependências: pip-audit ✅ · npm audit ❌ (29 vulns: 5 critical / 14 high / 8 moderate / 2 low)
