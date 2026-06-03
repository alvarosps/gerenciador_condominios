export const meta = {
  name: 'review-diff',
  description: 'Multi-lens review of the current git diff against gerenciador_condominios conventions (design principles, Django/DRF architecture, soft-delete/cache data-safety, security/permissions, types & lint, tests/mock-policy), with adversarial verification. Read-only.',
  phases: [
    { title: 'Review', detail: 'one reviewer per lens, over the working diff' },
    { title: 'Verify', detail: 'adversarially confirm each finding is real before reporting' },
  ],
}

// Invoke: /review-diff            (reviews uncommitted diff vs HEAD)
//         /review-diff master     (reviews diff vs the given base ref, passed as args)
const base = typeof args === 'string' && args.trim() ? args.trim() : ''
const diffCmd = base ? `git diff ${base}...HEAD` : 'git diff HEAD'

const FINDINGS = {
  type: 'object', additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'file', 'severity', 'detail'],
        properties: {
          title: { type: 'string' },
          file: { type: 'string', description: 'file:line' },
          severity: { type: 'string', enum: ['CRITICAL', 'WARNING', 'SUGGESTION'] },
          detail: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT = {
  type: 'object', additionalProperties: false,
  required: ['isReal', 'reason'],
  properties: { isReal: { type: 'boolean' }, reason: { type: 'string' } },
}

const LENSES = [
  { key: 'design-principles', prompt: 'Design principles (MANDATORY, see .claude/rules/design-principles.md): SOLID/DRY/KISS/YAGNI; no workarounds or quick-wins; no backwards-compat shims; no re-exports/barrel files; complete refactors (ALL consumers updated); and zero inline suppression — no `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore` (the actual code must be fixed).' },
  { key: 'architecture', prompt: 'Django/DRF architecture (.claude/rules/architecture.md): dependency direction Views -> Services -> Models (never reverse); ALL business logic in core/services/ (never in views or serializers); serializer dual pattern (nested read; `_id` write via PrimaryKeyRelatedField source=...; M2M write via `_ids`); new endpoints registered in core/urls.py; new models add cache-invalidation signal handlers in core/signals.py.' },
  { key: 'data-safety', prompt: 'Soft delete & data safety (.claude/rules/database.md): default querysets exclude soft-deleted — must use .with_deleted() when deleted rows are needed; no hard_delete without justification; LeaseTenant keeps db_table="core_lease_tenant_details"; destructive migrations/ops require a pg_dump backup first (scripts/backup_db.py); never flush/reset on real data; new business models declare AuditMixin/SoftDeleteMixin unless intentionally exempt (IPCAIndex, MonthSnapshot, FinancialSettings, Notification, DeviceToken, WhatsAppVerification, OAuthExchangeCode, ExpenseMonthSkip).' },
  { key: 'security', prompt: 'Security (.claude/rules/security.md): JWT auth required on all endpoints except /api/token*, /api/auth/google; financial writes use the FinancialReadOnly permission (only is_staff writes); no raw SQL or string-formatted queries (Django ORM / parameterized only); no secrets/tokens/credentials in code or logs; CPF/CNPJ validated via core/validators on relevant fields.' },
  { key: 'types-lint', prompt: 'Types & lint (.claude/rules/coding-standards.md): backend must pass ruff check, ruff format, mypy (strict), pyright (strict) with ZERO warnings; frontend must pass eslint (strict-type-checked) and tsc (strict + noUncheckedIndexedAccess); use `import type`; `??` over `||` for nullables; null-guard array index access; no `as` assertions or `!` non-null assertions — narrow types properly.' },
  { key: 'tests', prompt: 'Tests & mock policy (tests/CLAUDE.md): mock ONLY external boundaries (Chrome/PDF, external HTTP via responses/MSW, filesystem, time via freezegun) — NEVER mock Django ORM, internal services, serializers, model methods, or library code; use factory-boy/model-bakery (not raw ORM); prefer integration tests (view->service->model); every bug fix has a regression test; frontend uses a real QueryClient + per-test server.use() overrides.' },
]

phase('Review')
const results = await pipeline(
  LENSES,
  (l) => agent(
    `Review the current diff for the "${l.key}" lens of gerenciador_condominios (Django 5.2 + DRF backend, Next.js 14 frontend).\nRun: \`${diffCmd}\` (and read surrounding files for context as needed).\nProject rules for this lens: ${l.prompt}\nReport ONLY genuine issues introduced or touched by THIS diff, each with file:line. If the diff is clean for this lens, return an empty findings array.`,
    { label: `review:${l.key}`, phase: 'Review', agentType: 'claude', schema: FINDINGS },
  ),
  (review, l) => parallel((review?.findings || []).map((f) => () =>
    agent(
      `Adversarially verify this code-review finding against the actual code. Try to REFUTE it. Mark isReal=false if it is a false positive, not actually changed by the diff, already handled elsewhere, or not a real violation of the stated rule.\n\nFinding: ${JSON.stringify(f)}`,
      { label: `verify:${f.file}`, phase: 'Verify', agentType: 'Explore', schema: VERDICT },
    ).then((v) => ({ ...f, lens: l.key, verdict: v }))
  )),
)

const confirmed = results.flat().filter(Boolean).filter((f) => f.verdict?.isReal)
const order = { CRITICAL: 0, WARNING: 1, SUGGESTION: 2 }
confirmed.sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))

log(`Confirmed ${confirmed.length} finding(s) across ${LENSES.length} lenses.`)
return { confirmed }
