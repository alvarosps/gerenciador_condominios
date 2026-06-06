# Security Rules

## Authentication
- All API endpoints require JWT auth except: `/api/token/`, `/api/token/refresh/`, `/api/auth/google/`
- Token blacklisting on logout via `rest_framework_simplejwt.token_blacklist`
- Never log tokens, passwords, or secrets

## Authorization
- Financial module: `FinancialReadOnly` permission — authenticated users can read, only is_staff can write
- Existing CRUD: `IsAuthenticatedOrReadOnly`, `IsAdminUser`, `IsOwnerOrAdmin`, `IsTenantOrAdmin`
- Permission classes defined in `core/permissions.py` — always use these, never inline permission checks
- Frontend must hide create/edit/delete UI for non-admin users (conditional rendering based on user.is_staff)

## Data Validation
- CPF/CNPJ validation is mandatory — use validators from `core/validators/`
- Always validate user input at serializer level
- Never trust client-side validation alone

## Sensitive Files
- Never read, log, or commit: `.env`, `.env.local`, credentials, API keys
- Never hardcode secrets — use `python-decouple` / environment variables
- `detect-private-key` pre-commit hook is active

## CORS
- Only allow configured origins (localhost:4000, localhost:6000)
- Never use `CORS_ALLOW_ALL_ORIGINS = True` in production

## SQL Injection
- Always use Django ORM or parameterized queries — never raw SQL with string formatting

## Row Level Security (Supabase / Production)
- Production runs on Supabase (project `kaukiwhbmvnjjekodcmq`), which exposes the `public` schema through the PostgREST Data API to the `anon`/`authenticated` roles. This app does NOT use the Data API — all access is via the Django backend, which connects as the `postgres` role (`rolbypassrls = true`, table owner) and therefore bypasses RLS.
- CRITICAL: **RLS must stay ENABLED on every `public` table.** With RLS enabled and no policies, the Data API roles are denied while the Django backend is unaffected. This is the intended end state — the Supabase advisor's `rls_enabled_no_policy` (INFO) is expected and must NOT be "fixed" by adding permissive policies.
- CRITICAL: **Every new table needs RLS enabled in the same migration that creates it.** Add `migrations.RunSQL("ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;", reverse_sql="ALTER TABLE public.<table> DISABLE ROW LEVEL SECURITY;")` — pattern established in `core/migrations/0047_enable_row_level_security.py`. Use static SQL (no f-strings) to avoid ruff S608.
- After any DDL on prod, run the Supabase security advisor (`get_advisors type=security`) and confirm no `rls_disabled` (CRITICAL) entries appear.
- Do NOT add `FORCE ROW LEVEL SECURITY` — it would make even the owner/`postgres` role subject to RLS and break the backend.
