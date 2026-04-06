# Testing Rules

## Mock Policy — CRITICAL

Mock ONLY external boundaries. Never mock internal application code or library internals.

### What to mock (external boundaries):
- **HTTP APIs**: Use MSW (frontend) or `responses` library (backend) to intercept network calls
- **Chrome/PDF generation**: Mock the browser process, not our PDF service code
- **File system I/O**: Only when tests would create real files (e.g., PDF output directories)
- **Email/SMS services**: External notification providers
- **Redis**: Use Django's LocMemCache in tests (configured in conftest.py)
- **Time**: Use `freezegun` to control datetime.now() — this mocks the system clock, not our code

### What NEVER to mock:
- Django ORM queries — use a real test database (--reuse-db)
- Application services (CashFlowService, DashboardService, etc.) — test them with real dependencies
- Serializer validation — test with real serializer instances
- Model methods — test with real model instances
- Internal utility functions — test with real implementations
- Library code (Django, DRF, TanStack Query) — use the real library

### Why:
Mocking internal methods creates tests that pass even when the real code is broken. Tests must exercise the actual code path to catch real bugs. If a test is hard to write without mocking internals, that's a signal the code needs better design (dependency injection, smaller functions), not more mocks.

## Backend (pytest)

- Test file naming: `test_<module>.py` in `tests/unit/` or `tests/integration/`
- Use `factory-boy` or `model-bakery` for test data — never create objects manually with raw ORM
- Use fixtures from `conftest.py` (sample_building_data, mock_pdf_generation, etc.)
- Mark tests: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.pdf`
- Test services with real database — mock only external HTTP calls and Chrome process
- Coverage must stay above 60%

## Frontend (Vitest + MSW)

- Test file naming: `<hook-name>.test.tsx` in `lib/api/hooks/__tests__/`
- Use MSW handlers from `tests/mocks/handlers.ts` to intercept API calls — this mocks the network boundary, not our code
- Use custom render from `tests/test-utils.tsx` (wraps providers)
- Override MSW handlers per test with `server.use()` for edge cases
- Test hooks behavior, not implementation details
- Never mock TanStack Query internals — use real QueryClient with short cache times

## General

- Every bug fix must include a regression test
- Test the behavior, not the implementation
- Don't test framework code (Django ORM, React rendering)
- Prefer integration tests that exercise the full stack (view → service → model) over isolated unit tests
- Unit tests are for complex business logic in services (fee calculations, date logic, cash flow projections)
