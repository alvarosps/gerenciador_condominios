# Fable Audit — Verification Log (Fase 2)

Branch: `audit/fase-2-correcoes` (base master f0a1323). Cada lote: spec do orquestrador → code-fixer → verificação escopada → review do diff → commit.

## Lote 1 — Backend finances: integridade do caixa (B3, B4, B5, B8, B9, B10)
Status: ✅ COMMITADO `7005dd7` (23 arquivos, 33 testes de regressão novos)

Verificação (revisado pelo orquestrador — hunks pay/unpay guard, with_amounts, convert_deferred, reserve withdraw inspecionados):
```
ruff check finances/ tests/   → All checks passed!
ruff format --check           → 211 files already formatted
mypy finances/                → Success (38 files)
pyright finances/             → 0 errors, 0 warnings
pytest finances scoped        → 695 passed
```
Nota: "achado colateral" do fixer sobre `except X, Y:` é FALSO POSITIVO — PEP 758 (Python 3.14) permite except sem parênteses; ast.parse/suite confirmam.

## Lote 3 — Frontend UX (U1-U9, U11)
Status: ✅ COMMITADO `f2ac1f3` (30 arquivos)
```
npm run lint → ✔ 0 warnings | type-check → exit 0 | vitest → 126 files, 970/970
```
Decisões extras do fixer (aceitas): "Usuários" como item top-level staff-only (sem seção nova); aria-labels redundantes removidos no month-close (colisão de nome acessível).

## Lote 5 — Docs drift (A7, T4, T5)
Status: ✅ COMMITADO `95b629d` (4 arquivos de docs)

## Lote 4 — Backend core segurança (B1, B2, B7, B14)
Status: ✅ COMMITADO `7c20422` (17 arquivos)
```
ruff/format/mypy(80 files) limpos | pytest scoped 625 + integration 1027 passed | FE type-check limpo
```
B1: IsAdminUser em Building/Apartment/Furniture (grep confirmou zero consumo tenant). B2: enforce_csrf no caminho cookie (espelha SessionAuthentication), csrftoken emitido em login/refresh/register/oauth, axios xsrf configurado — Bearer isento. Risco residual: sessões pré-deploy só ganham csrftoken no próximo refresh (~15min). B7: log estruturado de handover. B14: validate_tenant_deletable.

## Lote 6 — Portal do inquilino (P1, P4, P5, P6, P8, P9, P10, P11)
Status: ✅ COMMITADO `159a143` (24 arquivos)
```
ruff/mypy/pyright limpos | pytest scoped 366 | FE lint/tsc limpos | vitest FULL 991/991
```
Verify OTP agora emite os mesmos cookies do login por senha + {user}; GET lista de comprovantes; aprovação → RentPayment idempotente via SSOT; empty-states sem lease; Twilio 400 sem queimar rate limit; telefone editável; contrato via contract_generated.

## Lote 7 — MSW migration (T3)
Status: ✅ COMMITADO `9859589` (11 arquivos de teste)
Zero `vi.mock` de lib/api/hooks no repo (grep prova). +`9923800` chore: uv.lock regen (requires-python 3.14 + pyright pin).

## Lote 8 — Timezone/money core (B6, B11, B12, T1, B15, B19) — ✅ `0ddd64f`
unit 1584 + integration 1048 + e2e 59; ~13 testes pré-existentes movidos p/ freeze_time noon-UTC.

## Lote 13 — Deps frontend — ✅ `f542f88`
29 → 6 vulns (restantes: só next@14 deferido + xlsx sem fix); axios 1.18.1, vitest 3.2.7, happy-dom 20; gates 4/4 verdes.

## Lote 10 — client.ts refactor (F12, P2, A3-cliente) — ✅ `7391117`
Unwrap heurístico removido (3 eslint-disable eliminados); parse-list.ts canônico (isolamento por item); 27 hooks + global-search migrados; lib/types/api.ts morto deletado; vitest 998/998.

## Lote 9 — Cache/search/pagination (B17, A1, A3, T2) — ✅ `aa32ff5`
on_commit deferral + fallback seletivo via tracked keys (nunca mais cache.clear()); make_key; Tenant→finance-*; SearchFilter nos 4 viewsets; max_page_size 10000 (LargePageNumberPagination deletada); test_rent_adjustment 27 testes congelados; 2651 unit+integration. +fix pyright do Lote 6 (orquestrador).

## Lote 12 — Infra (I3-I11) — ✅ `ba00284`
render.yaml (web + 2 crons SP, secrets sync:false); REDIS_URL obrigatório em prod; sslmode preservado; logging_config morto deletado + loggers access/performance ligados; zero supressões em settings_production; .env examples honestos; JWT lifetimes por env.

## Lote 11 — Performance B16 (11 hotspots) — ✅ `6cf9f0d`
Waterfall batelado (query count independente de N pessoas, teste de equivalência formal); debt_by_person 3 queries fixas; monthly_balance incremental (teste anti-O(n²)); caps; batches; índices Bill/Installment (migration 0009 aditiva, backup local antes do migrate); 2657 testes.

## Lote 14 — Expense modal F1/F2 — ✅ `835359c`
POST /expenses/ atômico com installments_data (rollback provado); addMonthsClamped (string math, clamp fim de mês); modal manda 1 request; e2e bank-loan corrigido (flush on_commit — artefato de teste do deferral do Lote 9); 206 expense + e2e 59 + FE 1011.

## ✅ BATERIA FINAL DA FASE 2 (2026-07-13, commit 835359c)

| Gate | Resultado |
|---|---|
| ruff check / format | ✅ limpos (305 files) |
| mypy core+finances | ✅ 118 files, 0 issues |
| pyright | ✅ 0/0/0 |
| pytest suite COMPLETA | ✅ **2721 passed, coverage 92.40%** (era 2600/92.35% no baseline) |
| eslint / tsc | ✅ 0 warnings / 0 errors |
| vitest | ✅ **1011/1011** (era 943/945 no baseline) |
| next build | ✅ 49 rotas |
| npm audit | 6 vulns restantes — APENAS famílias deferidas (next@14 breaking, xlsx sem fix) |

## PAUSADO A PEDIDO DO USUÁRIO (2026-07-12 ~20:00) — RETOMADO E CONCLUÍDO 2026-07-13

**Estado**: working tree limpo (só `audit/*` e `docs/plans/2026-07-10-*` untracked, intencionais). Branch `audit/fase-2-correcoes` com 8 commits, NÃO pushado.

**Próximos lotes planejados (Fase 2 restante)**:
- Lote 8 — Timezone/money core: B6 (reajuste auto-renew), B11 (late fee UTC/prepaid/effective), B12 (notificações UTC/já pago), T1 (change_due_date dia igual), B15 (defaults UTC legado), B19 (transfer_lease/full_clean/.first())
- Lote 9 — Perf B16 (N+1s/waterfall/índices — CUIDADO: índices exigem migration → backup antes) + cache B17
- Lote 10 — client.ts refactor (F12 + P2): remover unwrap heurístico/eslint-disable, parseList compartilhado, ~30 hooks, atomicidade lease+dependente; F1/F2 expense modal (endpoint atômico backend + datas)
- Lote 11 — API: A1 (search backend), A3 (pagination cap → 10000), A5/A6 (decisões 202/órfãos), F2-backend
- Lote 12 — Infra: I4 (REDIS_URL obrigatório em prod), I5 (sslmode merge), I6 (logging morto), I10, I11, render.yaml (I3/I7), .env residuais (I8/I9)
- Lote 13 — deps: npm audit fix não-breaking + axios 1.18.1 + vitest 3.2.6; T2 (freeze_time em test_rent_adjustment)
- Verificação final da fase: bateria completa via audit-runner → checkpoint humano
- DEFERIDOS (decisão do usuário no checkpoint): Next 14→16, xlsx→exceljs, A8 kebab-case, P3/P7/U10 (telas novas → Fase 4), A2/P7.1 (remoção legado), I1/I2 (Celery broker + S3 — precisam de infra/credenciais)

## Lote 2 — Frontend: datas/invalidations/erros/testes (F3-F11 + 2 testes quebrados + aria warnings)
Status: ✅ COMMITADO `4c5e498` (41 arquivos)

Verificação (code-fixer, revisado pelo orquestrador — hunks de auth-bootstrap, teste de calendário e catch-sweep inspecionados):
```
npm run lint        → ✔ No ESLint warnings or errors
npm run type-check  → exit 0
npm run test:unit   → Test Files 125 passed | Tests 957 passed (0 warnings act/aria)
```
Catches genéricos restantes em app/(dashboard): 0. Testes novos: helpers de data (7 casos), invalidations (11 asserções), MainLayout bootstrap.
