---
name: refactor
description: Safe refactoring with tests as safety net
---

# Refactor Workflow

## 1. Pre-check
- Run ALL tests first: `python -m pytest && cd frontend && npm run test:unit`
- If tests fail, fix them BEFORE refactoring
- Tests are your safety net — they must be green

## 2. Scope
- Define exactly what you're refactoring and why
- Identify all files that will be affected
- Check for callers: `grep -r "function_name" --include="*.py"` or `*.ts`

## 3. Execute (incremental)
- Make ONE change at a time
- After each change, run tests immediately
- If tests break: revert the change, try a different approach
- Don't mix refactoring with feature changes

## 4. Common Refactors

### Extract Service
1. Move business logic from view/serializer to `core/services/`
2. Update view to call service
3. Update tests to test service directly

### Extract Component
1. Identify reusable UI in a page component
2. Create new component in `components/` with props
3. Replace inline code with component usage
4. Verify with type-check

### Rename/Move
1. Rename in definition
2. Update all imports/references (grep thoroughly)
3. Update tests
4. Run full lint + type-check

## 5. Verify
- Run full test suite
- Run lint: `pre-commit run --all-files` + `cd frontend && npm run lint && npm run type-check`
- Commit: `refactor(scope): description`
