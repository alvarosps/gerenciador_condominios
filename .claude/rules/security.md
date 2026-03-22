# Security Rules

## Authentication
- All API endpoints require JWT auth except: `/api/token/`, `/api/token/refresh/`, `/api/auth/google/`
- Token blacklisting on logout via `rest_framework_simplejwt.token_blacklist`
- Never log tokens, passwords, or secrets

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
