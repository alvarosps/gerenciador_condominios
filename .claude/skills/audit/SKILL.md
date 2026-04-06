---
name: audit
description: Use at the end of every implementation session to verify completeness against the original plan. Compares what was implemented vs what was specified, finds gaps, and fixes them before closing the session. Never skip this.
---

# Session Audit — Verificação de Completude

Current branch: !`git branch --show-current`
Recent commits: !`git log --oneline -10`

## The Rule

**Every implementation session MUST end with an audit.** No session is complete until the audit passes. No exceptions.

---

## Audit Process

### 1. Identify the Plan

Determine which plan/prompt was being executed:

- Check `prompts/SESSION_STATE.md` for current session
- Read the original prompt file (e.g., `prompts/03-backend-viewsets-simple.md`)
- Read the design doc if referenced: `docs/plans/2026-03-21-financial-module-design.md`

### 2. Extract Acceptance Criteria

From the original plan, extract EVERY:
- [ ] File that should have been **created**
- [ ] File that should have been **modified**
- [ ] Feature/function that should have been **implemented**
- [ ] Test scenario that should have been **covered**
- [ ] Acceptance criterion listed (the `## Critérios de Aceite` section)

### 3. Verify Each Item — One by One

For EACH item from the plan, verify it was actually done:

```
For each file to create:
  → Does it exist? Read it.
  → Does it contain what the plan specified?
  → Is it complete or partial?

For each file to modify:
  → Was it modified? Check git diff.
  → Were ALL specified changes made?

For each feature/function:
  → Does it exist in the code?
  → Does it implement the FULL specification, not a subset?
  → Does it handle all edge cases mentioned in the plan?

For each test scenario:
  → Does a test exist for it?
  → Does the test actually verify the behavior (not just assert True)?
  → Does the test pass?
```

### 4. Run Full Verification

```bash
# Backend
ruff check
ruff format --check
python -m pytest tests/ -v --tb=short

# Frontend (if touched)
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

ALL must pass with zero errors.

### 5. Gap Analysis

List every gap found:

```markdown
## Gaps Found

| # | What was specified | What was implemented | Gap |
|---|-------------------|---------------------|-----|
| 1 | PersonViewSet with 5 filters | PersonViewSet with 3 filters | Missing: is_owner, is_employee filters |
| 2 | Test: singleton returns same instance | No test for this | Missing test |
| 3 | ... | ... | ... |
```

### 6. Fix ALL Gaps

For EACH gap:
1. Implement what's missing — following the original specification exactly
2. Run tests after each fix
3. Mark the gap as resolved

**DO NOT:**
- Skip a gap because "it's minor"
- Implement a workaround instead of the specified solution
- Add `# TODO` comments instead of implementing
- Simplify the specification to match what was built
- Close the session with any gap remaining

### 7. Final Verification

After all gaps are fixed:
1. Re-run the full verification suite (step 4)
2. Re-check every acceptance criterion from the plan
3. Only proceed if ALL criteria pass

### 8. Update State

```bash
# Update SESSION_STATE.md with:
# - Session marked as "concluída"
# - Files created/modified listed
# - Any architectural decisions noted
# - Known issues (pre-existing only, not new gaps)
```

### 9. Commit

```bash
git add <specific files>
git commit -m "feat(scope): complete session NN — [description]

Audit: all acceptance criteria verified
- [N] files created
- [N] files modified
- [N] tests passing
- Zero gaps remaining"
```

---

## Anti-Patterns — What Audit Must Catch

| Anti-Pattern | How to detect | Fix |
|-------------|--------------|-----|
| **Partial implementation** | Function exists but doesn't handle all cases from spec | Complete it |
| **Missing validation** | Serializer validate() doesn't check all rules from spec | Add missing checks |
| **Placeholder tests** | Test exists but asserts `True` or just checks existence | Write real assertions |
| **Missing edge case** | Plan says "handle prepaid leases" but code doesn't check `prepaid_until` | Implement the check |
| **Wrong error message** | Plan says Portuguese, code uses English | Fix language |
| **Missing filter** | ViewSet should have 9 filters, only has 6 | Add the 3 missing |
| **Skipped acceptance criterion** | Criterion not checked because "it's obvious" | Verify explicitly |
| **Workaround** | Plan says "use ORM aggregation", code uses raw Python loop | Rewrite with ORM |

---

## Design Principles Audit — MANDATORY

In EVERY audit, verify compliance with SOLID, DRY, KISS, YAGNI, and Clean Code. This is not optional. Search for and fix ALL violations.

### What to Check

| Violation | How to detect | Fix |
|-----------|--------------|-----|
| **Re-exports** | Module imports from X and re-exports it (`from x import Y` then `__all__ = [Y]`, or barrel `index.ts` files) | Remove re-export, update all consumers to import from the source |
| **Backwards compatibility shims** | Old function/class kept alongside new one, deprecated wrappers, renamed `_old_name` vars | Delete old code, update all callers to use the new interface |
| **Workarounds / quick wins** | Comments like "workaround", "hack", "temporary", "quick fix"; code that patches symptoms instead of root cause | Rewrite properly at the root cause |
| **TODO/FIXME/HACK comments** | `grep -r "TODO\|FIXME\|HACK\|XXX"` in changed files | Fix the issue now or remove the comment |
| **DRY violations** | Duplicated logic across functions/files (similar blocks of 3+ lines) | Extract into shared utility or base class |
| **SRP violations** | Class/function doing multiple unrelated things; function > 30 lines with multiple sections | Split into focused units |
| **Dead code** | Unused imports, unreachable branches, commented-out code, unused variables | Delete completely |
| **Partial refactoring** | Interface changed but some callers still use old signature; renamed function but old name still referenced | Complete the refactoring across the entire codebase |
| **God classes/functions** | Single class with too many responsibilities; function with too many parameters (>5) | Decompose into smaller, focused units |
| **Circular dependencies** | Module A imports from B which imports from A | Restructure to break the cycle |
| **Magic values** | Hardcoded numbers/strings without explanation | Extract to named constants |
| **Over-engineering** | Abstractions used only once; patterns without justification; "just in case" code | Simplify to what is actually needed |
| **Missing dependency registration** | New `import` of a third-party package not present in `requirements.txt`/`requirements-dev.txt` AND `pyproject.toml` | Add to all required files: `requirements.txt` or `requirements-dev.txt`, AND `pyproject.toml` |

### How to Run Design Principles Check

```bash
# Search for re-exports in Python
rg "from .+ import .+" --glob "**/__init__.py" | grep -v "^#"

# Search for workaround/hack comments
rg -i "workaround|hack|temporary|quick.?fix|FIXME|TODO|XXX|HACK" --glob "*.py" --glob "*.ts" --glob "*.tsx"

# Search for dead imports
ruff check --select F401

# Search for duplicated code patterns
# Manual review: look for similar blocks across files touched in this session

# Search for re-exports in TypeScript (barrel files)
rg "export \{.*\} from" --glob "*.ts" --glob "*.tsx" | grep "index\."
rg "export \*" --glob "*.ts" --glob "*.tsx"

# Verify new dependencies are registered in ALL places
# For each new third-party import in changed files, check it exists in:
# 1. requirements.txt (runtime) or requirements-dev.txt (dev/test)
# 2. pyproject.toml [project.dependencies] or [project.optional-dependencies.dev]
# If missing from ANY file, add it.
```

### Fix Protocol

For EVERY violation found:
1. Fix the violation properly — no workarounds, no "we'll fix it later"
2. Update ALL affected files across the codebase
3. Run linting and tests after each fix
4. Verify no new violations were introduced by the fix

**DO NOT:**
- Skip a violation because "it's pre-existing" — if you touched the file, fix it
- Add a TODO instead of fixing
- Create a compatibility shim instead of updating callers
- Leave partial refactoring "for the next session"

---

## Audit Mindset

Think like a QA engineer reviewing a contractor's work against the SOW (Statement of Work):
- Every line item must be delivered
- "Close enough" is not delivered
- If the plan says X, the code must do X — not Y that's "similar"
- If something is genuinely wrong in the plan, flag it and fix BOTH the plan and the code
