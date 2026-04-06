# Comprehensive Application Review — Implementation Plan

**Data:** 2026-04-06
**Escopo:** 85 issues across 8 review domains — Backend, Frontend, Financial, Security, Testing, UI/UX, Performance, Market
**Sessões:** 10, organizadas por domínio funcional com dependências respeitadas

---

## Decisões do Usuário

| Pergunta | Resposta |
|----------|---------|
| Fórmula de multa (F3) — código ou docstring correto? | **Código correto** — docstring tem exemplo errado |
| activate_pending_adjustments — cron, Celery, ou endpoint? | **Endpoint dedicado POST** com `IsAdminUser` |
| OAuth token leak — code exchange, cookies, ou fragment? | **One-time code exchange** (padrão authorization code) |
| Dead routes /settings e /register — remover, placeholder, ou implementar? | **Implementar** as páginas |
| /settings escopo? | **Perfil básico** — nome, email, avatar, trocar senha |
| /register escopo? | **Só admin cria** — rota /admin/users/new com IsAdminUser |
| Estratégia de sprints? | **Por domínio com dependências** — Opção C |

---

## Grafo de Dependências

```
01 Foundation ──┬──→ 03 Financial Correctness ──→ 04 Financial Data ──┐
                │                                                      ├──→ 09 Tests Backend
05 Cache ───────┴──→ 06 Performance ──────────────────────────────────┘
02 Security (independente) ───────────────────────────────────────────→ 09 Tests Backend
07 Frontend Cleanup ──→ 08 Frontend Features ─────────────────────────→ 10 Tests Frontend
```

---

## Sessão 01: Foundation — Models, Mixins, Coding Standards

**Issues:** B1, B2, B3, B6, B8, B12, F8, P8

### 1.1 — SoftDeleteMixin.delete() e restore() — updated_at (B3, B8)

**Arquivo:** `core/models.py:147-184`

`delete()` e `restore()` usam `update_fields` que bypassa `AuditMixin.save()`, deixando `updated_at` stale.

**Fix:** Setar `self.updated_at = timezone.now()` antes do `save()` e incluir `"updated_at"` em `update_fields`, em ambos os métodos.

### 1.2 — Expense.clean() vs CheckConstraint (B6)

**Arquivo:** `core/models.py:1076-1088`

`CheckConstraint` usa `total_amount__gte=0` (permite zero), `clean()` rejeita zero. Inconsistente.

**Fix:** Mudar `CheckConstraint` para `total_amount__gt=0` (alinhar com `clean()`).

### 1.3 — Tenant.save() full_clean com update_fields (B12)

**Arquivo:** `core/models.py:469-472`

`full_clean()` roda incondicionalmente, mesmo com `update_fields` — re-valida CPF quando só `due_day` mudou.

**Fix:** Guard com `if not kwargs.get("update_fields"): self.full_clean()`. Aplicar mesmo fix em `Lease.save()` (linha 667-670) que tem o mesmo pattern incondicional.

### 1.4 — Remover `from __future__ import annotations` (B2)

**Arquivos:** `core/services/template_management_service.py:10`, `core/infrastructure/pdf_generator.py:16`

**Fix:** Remover a linha. Ajustar forward references se necessário.

### 1.5 — Remover `HAS_DJANGO_REDIS` e `HAS_BOTO3` patterns (B1, P8)

**Arquivos:** `core/cache.py:33-38`, `core/infrastructure/storage.py:27-30`

**Fix:** Importar `django_redis.get_redis_connection` e `boto3` direto no top-level. Remover `try/except ImportError` e flags `HAS_*`.

### 1.6 — EmployeePayment.total_paid ignora rent_offset (F8)

**Arquivo:** `core/models.py:1288-1290`

**Fix:** `return self.base_salary + self.variable_amount - self.rent_offset`

### Verificação:
- `ruff check && ruff format --check`
- `mypy core/`
- `python -m pytest tests/unit/ -x`

---

## Sessão 02: Security — OAuth, Permissions, Middleware

**Issues:** S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, B4, B11

### 2.1 — OAuth one-time code exchange (S1)

**Arquivo:** `core/auth.py:85-145`

**Novo model** `OAuthExchangeCode`: `code` (UUID unique), `user` (FK), `access_token`, `refresh_token`, `created_at`, `is_used`. TTL 60 segundos.

**handle_callback** cria `OAuthExchangeCode` e redireciona com `?code=uuid` (sem tokens).

**Novo endpoint** `POST /api/auth/exchange/`: recebe `{code}`, valida (existe, não usado, <60s), retorna tokens. Se inválido → 400 genérico.

**Frontend** callback page: lê `?code=`, POST para `/api/auth/exchange/`, armazena tokens.

### 2.2 — Remover exception leaks (S2)

**Arquivo:** `core/auth.py:144,211`

**Fix:** Substituir `str(e)` por mensagens genéricas fixas. Log continua com `exc_info=True`.

### 2.3 — Proteger OpenAPI schema (S3)

**Arquivo:** `condominios_manager/urls.py:45`

**Fix:** Mover endpoint schema para dentro do bloco `if settings.DEBUG`.

### 2.4 — SecurityMiddleware primeiro (S4)

**Arquivo:** `condominios_manager/settings.py:64-75`

**Fix:** Reordenar MIDDLEWARE: SecurityMiddleware primeiro, depois CorsMiddleware, depois logging.

### 2.5 — Remover/proteger endpoints de enumeração (S5, S6)

**Arquivo:** `core/auth.py:166-252`

- `link_oauth_account` → `@permission_classes([IsAuthenticated])`, operar sobre `request.user`
- `oauth_status` → `@permission_classes([IsAdminUser])`

### 2.6 — Inline permission checks → permission_classes (B4)

**Arquivo:** `core/views.py:493-519`

**Fix:** `terminate` e `transfer` actions: remover `if not request.user.is_staff`, adicionar `permission_classes=[IsAdminUser]` no `@action`.

### 2.7 — Cookie JWT → flag boolean (S7, S8)

**Arquivos:** `frontend/lib/api/hooks/use-auth.ts`, `frontend/store/auth-store.ts`, `frontend/lib/api/client.ts`

- Remover `document.cookie = \`access_token=...\``
- Substituir por cookie boolean `is_authenticated=1`
- Zustand store é single source of truth
- `client.ts` interceptor lê de `useAuthStore.getState().token`

### 2.8 — Upload file validation (S9)

**Arquivo:** `core/serializers.py` (PaymentProofSerializer)

**Fix:** Adicionar `validate_file` — max 10MB, allowed types: JPEG, PNG, PDF.

### 2.9 — OTP verify_code lockout (S10)

**Arquivo:** `core/viewsets/auth_views.py`

**Fix:** Check `verification.attempts >= _MAX_VERIFY_ATTEMPTS` antes de verificar código. Return 429.

### 2.10 — Endpoint POST para activate_pending_adjustments (B11)

**Arquivo:** `core/views.py:615-638`

- Remover chamada de `activate_pending_adjustments()` do GET `financial_summary`
- Novo endpoint `POST /api/rent-adjustments/activate/` com `IsAdminUser`
- Frontend chama uma vez no mount do dashboard

### Verificação:
- `ruff check && ruff format --check && mypy core/`
- `python -m pytest tests/unit/test_permissions.py tests/unit/test_auth.py tests/integration/test_auth_api.py -x`
- Testar manualmente: OAuth flow, upload, dashboard

---

## Sessão 03: Financial Correctness — Fórmulas, Serializers, Race Conditions

**Issues:** F1, F2, F3, F6, F11, B9, B10

### 3.1 — Double `@staticmethod` (F1)

**Arquivo:** `core/services/financial_dashboard_service.py:842`

**Fix:** Remover duplicata. Buscar todas as ocorrências no arquivo.

### 3.2 — Unguarded `int()` (F2)

**Arquivo:** `core/viewsets/financial_dashboard_views.py:113`

**Fix:** Envolver em `try/except ValueError` → return 400.

### 3.3 — Late fee docstring incorreto (F3)

**Arquivo:** `core/services/fee_calculator.py:72-77`

**Fix:** Corrigir o exemplo no docstring para mostrar o resultado correto (R$12,50 para 5 dias). Atualizar CLAUDE.md e LESSONS_LEARNED.md se descrevem a fórmula incorretamente.

### 3.4 — ExpenseSerializer.validate quebrado em partial updates (F11)

**Arquivo:** `core/serializers.py:863-894`

**Fix:** Para campos não enviados no PATCH, consultar `self.instance` como fallback. Distinguir entre "não enviado" (`key not in attrs`) e "enviado como null" (`attrs[key] is None`).

### 3.5 — Credit card bulk-pay race condition (F6)

**Arquivo:** `core/services/daily_control_service.py:274-291`

**Fix:** Envolver em `transaction.atomic()` + `select_for_update()` antes do `update()`.

### 3.6 — change_due_date business logic na view (B9)

**Arquivo:** `core/views.py:453-457`

**Fix:** Extrair `change_tenant_due_day()` para `core/services/lease_service.py`. O service chama `full_clean()` explicitamente antes do save (necessário após fix B12).

### 3.7 — Expense.restore() restaura installments deletados individualmente (B10)

**Arquivo:** `core/models.py:1112-1119`

**Fix:** Capturar `original_deleted_at` antes do `super().restore()`, depois filtrar installments por `deleted_at` dentro de ±2 segundos do `original_deleted_at`.

### Verificação:
- `ruff check && ruff format --check && mypy core/`
- `python -m pytest tests/unit/test_financial/ tests/unit/test_fee_calculator.py -x`
- `python -m pytest tests/integration/test_expense_api.py tests/integration/test_financial_api_simple.py -x`

---

## Sessão 04: Financial Data — Cash Flow, Dashboard Service, Filtering

**Issues:** F4, F5, F7, F9, F10

### 4.1 — Projected stipends ignoram start_date/end_date (F4)

**Arquivo:** `core/services/cash_flow_service.py:688-693`

**Fix:** Adicionar `.filter(start_date__lte=month_start).exclude(end_date__lt=month_start)` — mesmo pattern de `_collect_person_stipends`.

### 4.2 — get_person_summary stipends ignoram date window (F7)

**Arquivo:** `core/services/cash_flow_service.py:817-830`

**Fix:** Mesmo filtro de data que 4.1.

### 4.3 — Owner repayments ignoram prepaid_until e is_salary_offset (F5)

**Arquivo:** `core/services/cash_flow_service.py:157-183`

**Fix:** Adicionar `.exclude(prepaid_until__gte=month_start).exclude(is_salary_offset=True)`. Aplicar mesmo fix no equivalente projetado (~linha 679).

### 4.4 — Projected expenses double-count debt installments (F9)

**Arquivo:** `core/services/cash_flow_service.py:696-704`

**Fix:** Em `_get_projected_utility_average()`, adicionar `is_debt_installment=False` ao filtro para excluir dívidas já contadas em installments.

### 4.5 — Category breakdown usa expense_date em vez de installment due dates (F10)

**Arquivo:** `core/services/financial_dashboard_service.py:327-349`

**Fix:** Separar query em duas: expenses diretas (sem installments) por `expense_date`, e installments por `due_date`. Merge por categoria. Formato de saída idêntico ao atual.

### Verificação:
- `ruff check && ruff format --check && mypy core/`
- `python -m pytest tests/unit/test_financial/test_cash_flow_service.py tests/unit/test_financial/test_financial_dashboard_service.py -x`
- Verificar manualmente dashboard financeiro, cash flow, category chart

---

## Sessão 05: Cache & Infra

**Issues:** P4, P5, P6, P7, P13, P14, P15

### 5.1 — cache_result no-op para None (P4)

**Arquivo:** `core/cache.py:158-168`

**Fix:** Usar `_SENTINEL = object()` para distinguir "não cacheado" de "cacheou None".

### 5.2 — Redis KEYS → SCAN (P5)

**Arquivo:** `core/cache.py:240-243`

**Fix:** Usar `cache.delete_pattern()` do django-redis (usa SCAN internamente). Se django-redis < 5.0, usar `redis_client.scan_iter()` manualmente.

### 5.3 — Cache keys sem data para métodos time-sensitive (P6)

**Arquivo:** `core/services/financial_dashboard_service.py` — múltiplos decorators

**Fix:** Adicionar `year`/`month` como params opcionais aos métodos que usam `timezone.now()` internamente. `cache_result` já inclui args na key automaticamente. Ajustar callers nos viewsets.

### 5.4 — Cachear get_cash_flow_projection (P7)

**Arquivo:** `core/services/cash_flow_service.py`

**Fix:** Adicionar `@cache_result(timeout=300, key_prefix="cash-flow-projection")`.

### 5.5 — Cachear DashboardService methods (P13)

**Arquivo:** `core/services/dashboard_service.py`

**Fix:** Adicionar `@cache_result` aos 5 métodos com TTLs apropriados. Adicionar invalidação via signals.

### 5.6 — FinancialSettings.objects.first() N vezes em loop (P14)

**Arquivo:** `core/services/financial_dashboard_service.py:423`

**Fix:** Fetch uma vez antes do loop, passar como parâmetro para `_get_person_waterfall`.

### Verificação:
- `ruff check && ruff format --check && mypy core/`
- `python -m pytest tests/unit/test_cache.py tests/unit/test_financial/ -x`
- `redis-cli MONITOR` — confirmar ausência de `KEYS`

---

## Sessão 06: Performance — Queries, N+1, Async PDF

**Issues:** B5, P1, P2, P3, P9, P10, P11, P12

### 6.1 — get_lease_metrics() Python loop → DB annotation (B5)

**Arquivo:** `core/services/dashboard_service.py:183-195`

**Fix:** Usar `RawSQL` annotation com `aggregate(Count("id", filter=Q(...)))`. De N queries + loop → 1 query.

### 6.2 — get_debt_by_person() N+1 → single query (P1)

**Arquivo:** `core/services/financial_dashboard_service.py:138-195`

**Fix:** Uma query com `values("expense__person_id").annotate()` usando conditional `Sum(filter=Q(...))`. De 5N → 1 query.

### 6.3 — _calc_person_expense_total() consolidação (P3)

**Arquivo:** `core/services/financial_dashboard_service.py:491-612`

**Fix:** Novo método `_calc_all_person_expenses(person_ids, months)` que retorna `dict[(person_id, month_start), total]` via 2 queries agrupadas. `_build_overdue_previous_months` chama uma vez e itera o dict. De 8×N×M → 2 queries.

### 6.4 — get_late_payment_summary() otimização (P10)

**Arquivo:** `core/services/dashboard_service.py:304-368`

**Fix:** Inline a fórmula simples de late fee em vez de chamar `FeeCalculatorService` por lease. Já protegido por `@cache_result` da Sessão 05.

### 6.5 — Endpoint activate_pending_adjustments (P2)

Já implementado na Sessão 02 (2.10). Aqui adicionar o frontend: hook mutation chamado uma vez no mount do dashboard.

### 6.6 — Frontend refetchInterval excessivo (P11)

**Arquivos:** `frontend/lib/api/hooks/use-dashboard.ts`, `use-financial-dashboard.ts`

**Fix:** Remover `refetchInterval` de todos os hooks. Habilitar `refetchOnWindowFocus: true` no query client. Manter polling (10min) apenas em late_payment_summary.

### 6.7 — CONN_MAX_AGE duplicado (P12)

**Arquivo:** `condominios_manager/settings_production.py:233`

**Fix:** Remover a linha module-level (sem efeito).

### 6.8 — PDF síncrono → Celery task (P9)

**Novo arquivo:** `core/tasks.py`

Task `generate_contract_pdf(lease_id)` via `@shared_task`. View retorna 202 com `task_id`. Novo endpoint `GET /api/tasks/{task_id}/status/`. Frontend poll até conclusão.

### Verificação:
- `ruff check && ruff format --check && mypy core/`
- `python -m pytest tests/ -x`
- Comparar tempo de resposta do dashboard
- Testar geração de PDF async

---

## Sessão 07: Frontend Cleanup — Dead code, patterns, aliases

**Issues:** FE1, FE3, FE4, FE5, FE6, FE7, FE8, FE9, FE10, FE11, FE13

### 7.1 — Toast error → useEffect (FE1)

12 páginas CRUD: mover `toast.error` para `useEffect` com `[error]` dependency.

### 7.2 — Raw query keys → queryKeys.* (FE3)

4 arquivos: substituir strings por constantes de `queryKeys`.

### 7.3 — Remover re-export barrel tenant-form-wizard.tsx (FE4)

Redirecionar imports para `./wizard`, deletar arquivo.

### 7.4 — Remover aliases formatCPFOrCNPJ / formatBrazilianPhone (FE5)

Substituir em todos os consumers, remover aliases e testes.

### 7.5 — console.error → handleError (FE6)

13+ catch blocks + error boundaries.

### 7.6 — Deletar financial-employees-temp/ (FE8)

Deletar diretório inteiro.

### 7.7 — Remover dead actions setTokens/setToken (FE9)

Verificar consumers, remover da interface e implementação. Remover `useRefreshToken` se unused.

### 7.8 — retry: 3 → filtrar 401/403 (FE10)

`query-client.ts`: retry function que retorna `false` para 401/403.

### 7.9 — null id fallback query key (FE11)

5 hooks: usar `queryKeys.*.detail(id ?? 0)` com `enabled: Boolean(id)`.

### 7.10 — useCurrentUser side effect em queryFn (FE7/FE13)

Remover `setUser(data)` do `queryFn`. Usar `placeholderData` em vez de `initialData`.

### Verificação:
- `cd frontend && npm run lint && npm run type-check && npm run build && npm run test:unit`
- Buscar resíduos: `rg "console\.(error|warn|log)" frontend/app/ --type ts`

---

## Sessão 08: Frontend Features — Settings, Register, UI fixes

**Issues:** U1, U2, U3, U4, U5, U6, U7, FE2, FE12

### 8.1 — Página /settings (U1)

**Novo:** `frontend/app/(dashboard)/settings/page.tsx`

Perfil básico: nome, email (read-only), avatar, trocar senha. Backend: `PATCH /api/auth/me/`, `POST /api/auth/change-password/`. Hook `use-settings.ts`, schema `settings.ts`. Corrigir links em header.tsx e sidebar.tsx.

### 8.2 — Página /admin/users (U2)

**Novos:** `frontend/app/(dashboard)/admin/users/page.tsx`, `user-form-modal.tsx`

Backend: `UserAdminViewSet` com `IsAdminUser`. CRUD de users (nome, email, senha, is_staff, is_active). Remover botão "Criar nova conta" do login.

### 8.3 — Inline error UI (U3)

Alert component com `AlertCircle` quando `error && !data`, em todas as páginas CRUD.

### 8.4 — Dirty-state warning (U4)

Hook reutilizável `use-unsaved-changes.ts` + `ConfirmDiscardDialog` component. Aplicar em ~15 form modals.

### 8.5 — FinancialSummaryWidget formatCurrency (U5)

Substituir `toFixed(2)` + `prefix="R$ "` por `formatCurrency()`.

### 8.6 — global-error.tsx (U6)

Usar `Button` component, mensagem genérica, não expor `error.message`.

### 8.7 — DataTable checkbox indeterminate (U7)

`checked={someSelected && !allSelected ? 'indeterminate' : allSelected}`.

### 8.8 — Direct apiClient → hooks com useMutation (FE2)

7+ componentes: extrair para hooks com `useMutation`, substituir `isSaving` manual por `mutation.isPending`.

### 8.9 — EXPENSE_TYPES duplicado (FE12)

Extrair para `lib/utils/constants.ts`, importar e filtrar em cada modal.

### Verificação:
- `cd frontend && npm run lint && npm run type-check && npm run build && npm run test:unit`
- Testar manualmente: /settings, /admin/users, dirty-state dialog, formatação R$

---

## Sessão 09: Testing Backend

**Issues:** T3, T4, T5, T6, T7, T9, T10, T11, T12

### 9.1 — FinancialReadOnly permission tests (T3)

**Novo:** `tests/integration/test_financial_permissions.py` — parametrize POST em todos os financial endpoints, assert 403 para non-admin, assert != 403 para admin.

### 9.2 — Export endpoint tests (T4)

**Novo:** `tests/integration/test_export_endpoints.py` — parametrize resources, verify Content-Type e non-empty response.

### 9.3 — RentAdjustmentService edge cases (T5)

**Novo:** `tests/unit/test_financial/test_rent_adjustment_edge_cases.py` — None IPCA factor, decimal rounding, zero/negative percentage.

### 9.4 — MonthAdvanceService rollback (T6)

**Expandir:** `tests/unit/test_month_advance_service.py` — rollback sem snapshot, advance+rollback=original, atomicity.

### 9.5 — Lease.prepaid_until boundaries (T7)

**Novo:** `tests/unit/test_financial/test_prepaid_lease.py` — past/today/future prepaid_until, dashboard exclusion.

### 9.6 — Soft-delete cascade (T9)

**Expandir:** `tests/integration/test_soft_delete.py` — Building→Apartments cascade, Lease delete→apartment.is_rented=False.

### 9.7 — Converter fixtures → model_bakery (T10)

**Arquivo:** `tests/conftest.py` — converter fixtures centrais de `Model.objects.create()` para `baker.make()`.

### 9.8 — WhatsApp send test (T11)

**Expandir:** `tests/unit/test_whatsapp_service.py` — usar `responses` library para mock HTTP externo, assert payload correto.

### 9.9 — Remover cleanup_test_contracts (T12)

**Arquivo:** `tests/conftest.py:281-287` — deletar fixture no-op.

### Verificação:
- `python -m pytest tests/ -x --tb=short`
- `python -m pytest --cov=core --cov-report=term-missing`

---

## Sessão 10: Testing Frontend

**Issues:** T1, T2, T8

### 10.1 — Reescrever use-contract-template.test.tsx (T1)

Adicionar `templateHandlers` ao MSW. Reescrever testes usando `createWrapper()` + MSW. Remover `vi.mock('@/lib/api/client')`.

### 10.2 — Reescrever use-auth.test.tsx (T2)

Adicionar `authHandlers` ao MSW. Testar com Zustand real (reset entre testes). Remover `vi.mock('@/store/auth-store')`.

### 10.3 — MSW handlers para financial endpoints (T8)

Adicionar handlers para: `/api/financial-dashboard/*`, `/api/cash-flow/*`, `/api/daily-control/*`. Adicionar error-state tests nos hooks existentes.

### Verificação:
- `cd frontend && npm run test:unit -- --run`
- Verificar zero `vi.mock` de módulos internos
- `npm run lint && npm run type-check`
